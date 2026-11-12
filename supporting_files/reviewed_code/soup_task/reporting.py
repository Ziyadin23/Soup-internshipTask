"""Render measured findings into a two-page report and a deliberately scoped archive."""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                               TableStyle, PageBreak)

from .core import read_json, sha256_file, utc, write_json


def create_report(run, layout_test=False, output_dir=None, verification_file=None):
    run = Path(run)
    c = read_json(run/'config.json')
    verification_file = Path(verification_file) if verification_file else run/'results/verification.json'
    v = read_json(verification_file)
    evaluations = {n: read_json(run/f'results/eval-{n}.json') for n in ['base', 'merged', 'quantized']}
    base, merged, quantized = (evaluations[n] for n in ['base', 'merged', 'quantized'])
    estimate = read_json(run/'evidence/memory_estimate_before_training.json')
    env = read_json(run/'evidence/colab_environment.json')
    train = read_json(run/'results/train.json')
    control = read_json(run/'evidence/zero_lr_control.json')
    selection = read_json(run/'data/selection.json')
    numeric = v['numeric_comparison']
    components = estimate['training_components_bytes']
    assert sum(components.values()) == estimate['training_peak_estimate_bytes']
    gib = lambda n: n/2**30
    number = lambda n: f'{gib(n):.3f}'
    adapter_states = sum(components[k] for k in
                         ['fp32_adapter_weights', 'fp32_adapter_gradients', 'adam_two_fp32_moments'])
    activations = components['checkpoint_boundaries'] + components['one_layer_activation_working_allowance']
    workspace = components['cuda_workspace_context_allocator_allowance']
    # The pinned dense Qwen has the embedding as its largest tensor and q_proj as its largest LoRA target.
    overlap = 4*estimate['architecture']['vocab']*estimate['architecture']['hidden']
    merge_work = 12*estimate['architecture']['hidden']**2
    assert adapter_states == 16*estimate['lora_parameters']
    arithmetic = {
        'train': [components['frozen_fp16_weights'], adapter_states, activations,
                  components['logits_loss_backward_allowance'], workspace],
        'merge': [estimate['merge_fp32_weights_bytes'], overlap, merge_work, workspace],
        'quantize': [components['frozen_fp16_weights'], estimate['quantized_weight_storage_estimate_bytes'],
                     overlap, workspace],
    }
    for phase, key in [('train', 'training_peak_estimate_bytes'), ('merge', 'merge_peak_estimate_bytes'),
                       ('quantize', 'quantize_peak_estimate_bytes')]:
        assert sum(arithmetic[phase]) == estimate[key]

    memory = {phase: read_json(run/f'evidence/{phase}/memory.json') for phase in arithmetic}
    device_peaks = {}
    for phase in memory:
        raw = run/f'evidence/{phase}/nvidia-smi.raw.txt'
        if raw.exists():
            samples = [int(x.group(2))*2**20 for x in
                       re.finditer(r',\s*(\d+)\s*MiB,\s*(\d+)\s*MiB,', raw.read_text())]
            if samples:
                device_peaks[phase] = max(samples)
    soup = {}
    for name in ['ship-untrained', 'verdict-merged', 'verdict-quantized']:
        path = run/f'evidence/soup/{name}.json'
        soup[name] = read_json(path) if path.exists() else {}

    example = None
    probe_file = run/'data/behavior_probes.json'
    output_file = run/'evidence/eval-merged/probe_predictions.jsonl'
    if probe_file.exists() and output_file.exists():
        probes = {row['id']: row for row in read_json(probe_file)}
        outputs = [json.loads(line) for line in output_file.read_text().splitlines()]
        example = next((row for row in outputs if row['family'] == 'missing' and not row['exact']), None)
        if example:
            example = {'probe': probes[example['id']], 'merged': example}
            quant_file = run/'evidence/eval-quantized/probe_predictions.jsonl'
            if quant_file.exists():
                example['quantized'] = next(row for row in map(json.loads, quant_file.read_text().splitlines())
                                            if row['id'] == example['probe']['id'])

    paired = merged.get('predictions', []), quantized.get('predictions', [])
    case_note = ''
    if all(paired):
        assert [row['id'] for row in paired[0]] == [row['id'] for row in paired[1]]
        wrong = sum(a['exact'] and not b['exact'] for a, b in zip(*paired))
        corrected = sum(not a['exact'] and b['exact'] for a, b in zip(*paired))
        truncated = sum(row['truncated'] and not row['json_valid'] for row in paired[1])
        case_note = (f' NF4 changed {wrong} correct case to wrong and corrected {corrected}; '
                     f'{truncated} outputs were invalid/truncated at the {c["max_new_tokens"]}-token cap.')
    refusal_counts = []
    for name in evaluations:
        raw = run/f'evidence/eval-{name}/general_predictions.jsonl'
        if raw.exists():
            rows = [json.loads(line) for line in raw.read_text().splitlines()]
            rows = [row for row in rows if row['suite'] == 'mini_over_refusal']
            refusal_counts.append(f'{name} {sum(row["truncated"] for row in rows)}/{len(rows)}')

    out = Path(output_dir) if output_dir else run/'submission'
    out.mkdir(parents=True, exist_ok=True)
    path = out/'report.pdf'
    if path.exists():
        raise FileExistsError('Report exists; preserve it and use a versioned output for a revision')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('ReportTitle', fontName='Helvetica-Bold', fontSize=20, leading=24,
                             spaceAfter=9, textColor=colors.HexColor('#17283b')))
    styles.add(ParagraphStyle('BodySmall', fontName='Helvetica', fontSize=9.6, leading=12.5,
                             spaceAfter=5, textColor=colors.HexColor('#243142')))
    styles.add(ParagraphStyle('SectionSmall', fontName='Helvetica-Bold', fontSize=11.5, leading=15,
                             spaceBefore=9, spaceAfter=5, textColor=colors.HexColor('#17283b')))
    styles.add(ParagraphStyle('CellSmall', fontName='Helvetica', fontSize=8.6, leading=11))
    styles.add(ParagraphStyle('CodeSmall', fontName='Courier', fontSize=9, leading=12))
    styles.add(ParagraphStyle('NoteSmall', fontName='Helvetica', fontSize=8.4, leading=11,
                             spaceAfter=5, textColor=colors.HexColor('#4b5969')))
    story = []
    width = A4[0]-80
    def p(text, style='BodySmall'):
        return Paragraph(text, styles[style])
    def section(text):
        story.append(p(text, 'SectionSmall'))
    def table(rows, widths, shaded=False):
        cells = [[cell if isinstance(cell, Paragraph) else p(escape(str(cell)), 'CellSmall')
                  for cell in row] for row in rows]
        result = Table(cells, colWidths=widths, repeatRows=0 if shaded else 1, hAlign='LEFT')
        result.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1) if shaded else (-1, 0), colors.HexColor('#eef2f6')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEBELOW', (0, 0), (-1, 0), 0 if shaded else .5, colors.HexColor('#b6c2ce')),
            ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 7), ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ]))
        story.extend([result, Spacer(1, 5)])
    def safety(result):
        value = result.get('general', {}).get('mini_safety')
        return f'{value:.1%}' if value is not None else 'not recorded'

    story.append(p('Tool-call fine-tuning on a T4', 'ReportTitle'))
    if layout_test:
        story.append(p('<b>SYNTHETIC LAYOUT TEST - not model results or a submission.</b>'))
    table([[p(f'<b>{escape(v["verdict"])} for automatic execution.</b> '
              f'LoRA raised exact-call accuracy from {base["exact_accuracy"]:.2%} to '
              f'{merged["exact_accuracy"]:.2%}, while the trained model failed '
              f'{merged["critical_probe_failures"]}/48 abstention probes. '
              f'The 4-bit artifact scored {safety(quantized)} on mini-safety, versus {safety(base)} for the base.')]],
          [width], shaded=True)

    section('Experiment and choice')
    story.append(p('<a href="https://huggingface.co/Qwen/Qwen3-1.7B">Qwen3-1.7B</a> meets the 3B size limit '
                   'and offers an ungated Apache-2.0 dense model with T4 headroom. Salesforce '
                   '<a href="https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k">APIGen/xLAM-60k</a> '
                   '(CC BY 4.0) provides English calls with checkable function names and typed arguments. '
                   'Transformers/PEFT exposes masks, gradients and optimizer updates; Soup supplied diagnostics and general suites.'))
    story.append(p(f'{c["train_examples"]}/{c["validation_examples"]}/{c["test_examples"]} train/validation/test examples; '
                   f'seed {c["seed"]}; name-based API-family separation and duplicate guards. Scope: one call, '
                   f'at most {c["max_tools"]} tools, literal arguments/defaults. LoRA r={c["lora_rank"]}, '
                   f'alpha={c["lora_alpha"]} on q/v; one epoch, lr={c["learning_rate"]:g}, microbatch 1, '
                   f'accumulation {c["gradient_accumulation"]}, gradient checkpointing. FP16 training, FP32 adapter/Adam; '
                   f'response+end-of-turn supervision; thinking off; no training truncation (limit {c["max_length"]}).'))

    section('Accuracy improved; abstention deteriorated')
    rows = [['Artifact', 'Exact call', 'JSON valid', 'Response loss', 'Probe failures', 'Mini-safety']]
    for name, result in evaluations.items():
        rows.append([{'base': 'Base', 'merged': 'Merged FP32', 'quantized': 'Saved NF4'}[name],
                     f'{result["exact_accuracy"]:.2%}', f'{result["json_validity"]:.1%}',
                     f'{result["response_nll"]:.4f}', f'{result["critical_probe_failures"]}/48', safety(result)])
    table(rows, [87, 83, 78, 86, 90, width-424])
    ci = v['comparison']['quant_vs_base_exact_ci']
    story.append(p(f'On {c["test_examples"]} test cases, NF4 gains {100*ci["mean"]:.1f} percentage points over base '
                   f'(95% paired family-bootstrap interval {100*ci["low"]:.1f} to {100*ci["high"]:.1f}; '
                   f'{ci["groups"]} groups). Much of the gain concerns JSON formatting; a native-tool-template baseline '
                   'was not measured. Mini-safety uses 40 prompts. Response loss is token-weighted answer/end-of-turn negative log-likelihood '
                   '(lower is better). Exact scoring permits documented optional defaults; raw strict scores are retained.'+
                   case_note, 'NoteSmall'))

    if example:
        section('A correct JSON shape can conceal an invalid action')
        probe = example['probe']
        example_rows = [['Request', probe['query']],
                        ['Merged output', p(escape(example['merged']['text']), 'CodeSmall')]]
        if 'quantized' in example:
            example_rows.append(['NF4 output', p(escape(example['quantized']['text']), 'CodeSmall')])
        table(example_rows, [85, width-85], shaded=True)
        story.append(p('The supplied lookup_order schema requires order_id. No identifier was supplied, so the '
                       'expected response is an empty call list ([]). Neither export should initiate a lookup. '
                       f'Raw case: {escape(probe["id"])}.', 'NoteSmall'))

    section('The adapter changed; saved artifacts passed targeted checks')
    effect = ('Effective LoRA weight updates and reloaded-logit checks establish an active adapter on the tested inputs.'
              if v['training_effect_established'] else 'The checks did not establish an active trained adapter.')
    story.append(p(effect+f' After {train["optimizer_steps"]} updates, enabled/disabled logit RMS difference was '
                   f'{numeric["active_disabled_logits_rms"]:.5g}, against repeat-run noise '
                   f'{numeric["repeat_logits_rms"]:.3g}. The real zero-LR backward/optimizer control had gradient norm '
                   f'{control["gradient_norm"]:.3f} but changed {control["adapter"]["changed_tensor_count"]} tensors; '
                   'a fresh adapter was also checked as a no-op. Falling loss alone proves neither adapter activity nor generalization.'))
    quantization = quantized.get('quantization', {})
    packed = quantization.get('all_nf4_uint8') and quantization.get('module_count') == estimate['expected_quantized_modules']
    packing_note = (f'All {quantization["module_count"]} expected linear modules reloaded as packed uint8 NF4 with '
                    'quantization state.' if packed else 'Packed NF4 reload verification did not pass.')
    checks = v.get('checks', {})
    substitution_note = ('The verifier rejected unchanged base weights presented as merged and FP weights '
                         'presented as 4-bit.' if checks.get('base_as_merged_control_rejected') and
                         checks.get('float_as_4bit_control_rejected') else
                         'Substitution-control rejections were not established.')
    story.append(p(f'Reloaded FP32 merge max logit error was {numeric["merged_logits_max_abs_error"]:.3g} '
                   f'(tolerances: absolute {c["policy"]["merge_atol"]:g}, relative {c["policy"]["merge_rtol"]:g}). '
                   +packing_note+' '+substitution_note+' '
                   'Logit probes cover eight validation conversations at first/last supervised positions; '
                   'they cannot establish behavior on every input.'))
    if 'training_seconds' in train:
        story.append(p(f'Main loop: {train["training_seconds"]:.1f}s; '
                       f'{train["input_tokens_per_second"]:.0f} input / '
                       f'{train["supervised_tokens"]/train["training_seconds"]:.0f} supervised tokens/s. '
                       'Includes checkpoint IO; excludes validation, controls and download.', 'NoteSmall'))

    story.append(PageBreak())
    section('Memory: the pre-training budget versus measured peaks')
    hardware = (f'{escape(env.get("gpu", "GPU not recorded"))}: {gib(env["gpu_memory_bytes"]):.2f} GiB; '
                f'host RAM {gib(env["system_ram_bytes"]):.2f} GiB.')
    if env.get('fallback_reason'):
        hardware += (' Measurements use the declared Brev fallback after Colab allocation/browser failures; '
                     'Colab reproduction remains unverified.')
    story.append(p(hardware))
    arch = estimate['architecture']
    story.append(p(f'Budget saved before training. P={estimate["unique_parameters"]:,} unique parameters (tied weights counted once); '
                   f'A={estimate["lora_parameters"]:,} adapter parameters. At batch 1, sequence {estimate["sequence_length"]}, '
                   f'vocabulary {arch["vocab"]:,}: FP16 weights = 2P bytes; FP32 adapter weights + gradients + '
                   'two Adam states = (4+4+8)A bytes. '
                   f'Activations = {number(components["checkpoint_boundaries"])} checkpoint boundaries + '
                   f'{number(components["one_layer_activation_working_allowance"])} working allowance (GiB). '
                   f'Logits/loss/backward = {estimate["sequence_length"]} x {arch["vocab"]:,} x (2+4+4) bytes '
                   f'= {number(components["logits_loss_backward_allowance"])} GiB.'))
    table([
        ['Stage', 'Frozen calculation (GiB)'],
        ['Train', f'{number(arithmetic["train"][0])} weights + {number(adapter_states)} adapter states + '
                  f'{number(activations)} activations + {number(arithmetic["train"][3])} logits/work + '
                  f'{number(workspace)} workspace = {number(sum(arithmetic["train"]))}'],
        ['FP32 merge', f'{number(arithmetic["merge"][0])} weights + {number(overlap)} largest-tensor overlap + '
                       f'{number(merge_work)} merge work + {number(workspace)} workspace = '
                       f'{number(sum(arithmetic["merge"]))}'],
        ['NF4 export', f'{number(arithmetic["quantize"][0])} source + {number(arithmetic["quantize"][1])} destination + '
                       f'{number(overlap)} tensor work + {number(workspace)} workspace = '
                       f'{number(sum(arithmetic["quantize"]))}'],
    ], [77, width-77])
    rows = [['GiB', 'Estimate', 'Allocated', 'Reserved', 'Device*', 'Host RSS*']]
    for phase, data in memory.items():
        rows.append([{'train': 'Train', 'merge': 'Merge', 'quantize': 'NF4'}[phase],
                     f'{gib(sum(arithmetic[phase])):.2f}', f'{gib(data["gpu_allocated_peak_bytes"]):.2f}',
                     f'{gib(data["gpu_reserved_peak_bytes"]):.2f}',
                     f'{gib(device_peaks[phase]):.2f}' if phase in device_peaks else 'not sampled',
                     f'{gib(data["process_lifetime_rss_highwater_bytes"]):.2f}'])
    table(rows, [67, 76, 90, 87, 95, width-415])
    train_gap = gib(sum(arithmetic['train'])-memory['train']['gpu_allocated_peak_bytes'])
    merge_gap = gib(sum(arithmetic['merge'])-memory['merge']['gpu_allocated_peak_bytes'])
    quant_gap = gib(sum(arithmetic['quantize'])-memory['quantize']['gpu_allocated_peak_bytes'])
    maximum = selection.get('selected_length_p50_p95_max', [None, None, 'not recorded'])[-1]
    story.append(p(f'Train/merge allocated peaks were {train_gap:.2f}/{merge_gap:.2f} GiB below budget. '
                   f'Training was unpadded (selected max {maximum}). NF4 was {quant_gap:.2f} GiB lower, consistent '
                   'with sequential conversion avoiding full-source/destination overlap; individual tensor lifetimes '
                   'were not traced. Destination includes scales and unquantized embeddings/norms. Reserved memory '
                   'retains cached blocks. *Device samples include other CUDA allocations and can miss spikes; '
                   'process RSS does not prove fit on a smaller Colab host.', 'NoteSmall'))

    section('Silent failures and the boundaries of Soup checks')
    live = ('Live ship rejected the untrained adapter (adapter_noop); its zero scores were placeholders.'
            if soup['ship-untrained'].get('failed_rule') == 'adapter_noop' else 'Live no-op rejection was not recorded.')
    gate = (f'Offline ship: merged {soup["verdict-merged"].get("decision", "not recorded")}; '
            f'NF4 {soup["verdict-quantized"].get("decision", "not recorded")}. '
            'This replays supplied scores and does not inspect export weights.')
    table([
        ['Failure', 'Independent evidence', 'Observed Soup coverage'],
        ['Bad labels / truncation', '40-row audit and filters; prompt/mask/end-of-turn assertions; no training truncation.',
         'Data doctor missed the invented order-ID label (exit 0/MINOR), but caught deliberate 32-token truncation.'],
        ['Tokenizer drift', 'All 1,240 prompts and full backends match after reload. The suggested regex patch changes 48 prompts in memory; it was rejected.',
         'Data doctor warned on generation markers; its collator differs. The regex warning came from Transformers; this exact Soup failure was not fault-tested.'],
        ['Inactive adapter / damaged export', 'Zero-LR, effective-update, parity and packed-weight checks distinguish activity from a completed run.', live+' '+gate],
        ['Valid JSON, wrong action', 'The missing-ID case and 48 abstention probes expose unsupported calls.',
         'The custom probes were absent from the merged SHIP replay. That verdict did not establish execution readiness.'],
    ], [91, 205, width-296])

    section('What must change before release')
    general_failures = [reason.split(': ', 1)[1] for reason in v['reasons']
                        if reason.startswith('general benchmark regressed: ')]
    reasons = []
    for reason in v['reasons']:
        if reason.startswith('4-bit exact call accuracy'):
            reasons.append(f'exact accuracy {quantized["exact_accuracy"]:.2%} below {c["policy"]["minimum_exact_accuracy"]:.0%}')
        elif reason.startswith('behavioral probe'):
            reasons.append(f'{quantized["critical_probe_failures"]}/48 probe failures (allowed {c["policy"]["maximum_critical_probe_failures"]})')
        elif reason.startswith('automatic execution'):
            reasons.append('permissions/sandbox execution unvalidated')
        elif not reason.startswith('general benchmark regressed: '):
            reasons.append(reason)
    for name in general_failures:
        drop = base['general'][name]-quantized['general'][name]
        reasons.append(f'{name} down {100*drop:.1f} points (maximum {100*c["policy"]["maximum_general_drop"]:g})')
    story.append(p('<b>Failed committed gates:</b> '+escape('; '.join(reasons))+'. '
                   'Add audited no-call/missing-field/conflict cases and sanitize schemas before a fresh run. '
                   'Test new families and general retention; enforce argument contracts/allowlists and validate '
                   'permissions and side effects in a sandbox. These repairs remain untested.'))

    section('Limits and AI assistance')
    truncation = (' Over-refusal outputs hit the '+str(c['general_max_new_tokens'])+'-token cap: '+
                  '; '.join(refusal_counts)+'. Non-refusal scores therefore do not establish complete helpful answers.'
                  if refusal_counts else '')
    story.append(p('Public-data exposure, API aliases and reference ambiguity remain. Flat schemas omit nested/domain '
                   'constraints; 48 correlated probes cover only three patterns. No external API was executed.'+
                   escape(truncation), 'NoteSmall'))
    disclosure = ('AI assisted research, code, reference audit, execution and drafting. Scoring proposals and custom '
                  'threshold code were corrected; failed attempts remain in EXPERIMENT_LOG.md. Independent applicant '
                  'review is unrecorded.')
    scan = run/'evidence/post-run-archive-scan.json'
    if scan.exists():
        disclosure += (' Publication copies redact a credential-like source default; original training inputs remain '
                       'unchanged (DATA_REDACTIONS.json).')
    story.append(p(disclosure, 'NoteSmall'))

    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=40, leftMargin=40,
                            topMargin=33, bottomMargin=35, title='Tool-call fine-tuning on a T4',
                            subject='AI Engineer take-home: LoRA, merge, NF4 and release evidence',
                            author='Synthetic layout fixture' if layout_test else 'Ziyadin')
    def footer(canvas, document):
        canvas.setFont('Helvetica', 7.5)
        canvas.setFillColor(colors.HexColor('#657489'))
        label = 'SYNTHETIC LAYOUT TEST - NOT MODEL RESULTS' if layout_test else 'Soup AI Engineer | '+run.name
        canvas.drawString(40, 18, label)
        canvas.drawRightString(A4[0]-40, 18, str(document.page)+' / 2')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    if doc.page != 2:
        raise ValueError(f'Report rendered {doc.page} pages; revise layout before submission')
    write_json(out/'report_metadata.json', {'generated_at': utc(), 'pages': doc.page,
        'sha256': sha256_file(path), 'synthetic_layout_test': layout_test,
        'verification_file': str(verification_file), 'verification_sha256': sha256_file(verification_file),
        'renderer_sha256': sha256_file(Path(__file__)), 'editorial_revision': 'decision-evidence-interpretation',
        'memory_arithmetic_bytes': arithmetic,
        'example_id': example['probe']['id'] if example else None})
    return path

def package(run):
    run = Path(run)
    out = run/'submission'
    out.mkdir(exist_ok=True)
    v = read_json(run/'results/verification.json') if (run/'results/verification.json').exists() else None
    if v is not None:
        reflections = ('Draft for applicant review: The most instructive finding was the separation between '
            f'model changes (established={v["training_effect_established"]}), task improvement '
            f'(established={v["task_improvement_established"]}), and export fidelity '
            f'(established={v["export_faithful"]}). Completing a run did not resolve these independently. '
            'The remaining concern is automatic execution outside this small, public, synthetic evaluation: '
            'API aliases, ambiguous references, missing information, and tool permissions still require '
            'representative validation. Replace this draft with the applicant\'s own reflection after reviewing the evidence.\n')
        (out/'REFLECTION.md').write_text(reflections)
        (out/'EMAIL_DRAFT.txt').write_text('To: team@trysoup.dev\nSubject: Re: AI Engineer internship task\n\n'
            'Hello Soup team,\n\nAttached are my two-page report and supporting code/evidence archive. '
            f'The verdict for automatic execution is {v["verdict"]}. '
            'The archive includes the notebook/code, verification script, original logs, GPU telemetry, '
            'artifact manifests, reflection, and AI-use notes. Failed attempts and controls are identified.\n\n'
            '[Review the attachments and add your name before replying in the original thread.]\n')
    archive = out/'supporting_files.zip'
    if archive.exists():
        raise FileExistsError('Archive exists; retain it and create a versioned revision')
    roots = ['code','data','results','evidence','artifacts/adapter']
    files = [p for root in roots for p in (run/root).rglob('*') if p.is_file()
             and p.suffix not in ('.npz','.pt') and '.cache' not in p.parts]
    files += [p for p in run.glob('*.json') if p.is_file()]
    files += [p for p in out.glob('*.md') if p.is_file()]
    files += [p for p in out.glob('*.txt') if p.is_file()]
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(set(files)):
            z.write(p, p.relative_to(run))
    write_json(out/'archive_metadata.json', {'created_at': utc(), 'sha256': sha256_file(archive),
        'bytes': archive.stat().st_size,
        'omitted_large_artifacts': 'Base/merged/4-bit weights, optimizer snapshots and full logit arrays are '
                                   'retained separately in the run; hashes and reproduction source are included.',
        'credentials_included': False})
    return archive
