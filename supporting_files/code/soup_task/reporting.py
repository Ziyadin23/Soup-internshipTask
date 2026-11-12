"""Render measured findings into a two-page report and a deliberately scoped archive."""
from __future__ import annotations

import json
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


def create_report(run, layout_test=False):
    run = Path(run)
    c = read_json(run/'config.json')
    v = read_json(run/'results/verification.json')
    evaluations = {n: read_json(run/f'results/eval-{n}.json') for n in ['base','merged','quantized']}
    estimate = read_json(run/'evidence/memory_estimate_before_training.json')
    env = read_json(run/'evidence/colab_environment.json')
    train = read_json(run/'results/train.json')
    selection = read_json(run/'data/selection.json')
    out = run/'submission'
    out.mkdir(exist_ok=True)
    path = out/'report.pdf'
    if path.exists():
        raise FileExistsError('Report exists; preserve it and use a versioned output for a revision')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('BodySmall', fontName='Helvetica', fontSize=9.1, leading=12,
                             spaceAfter=6, textColor=colors.HexColor('#202733')))
    styles.add(ParagraphStyle('SectionSmall', fontName='Helvetica-Bold', fontSize=11,
                             leading=14, spaceBefore=9, spaceAfter=5))
    styles.add(ParagraphStyle('CellSmall', fontName='Helvetica', fontSize=8.1, leading=10))
    story = []
    def p(text):
        return Paragraph(text, styles['BodySmall'])
    def section(text):
        story.append(Paragraph(text, styles['SectionSmall']))
    def table(rows, widths):
        cells = [[Paragraph(escape(str(x)), styles['CellSmall']) for x in row] for row in rows]
        t = Table(cells, colWidths=widths, repeatRows=1, hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9edf2')),
            ('VALIGN',(0,0),(-1,-1),'TOP'), ('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#aab5c2')),
            ('BOTTOMPADDING',(0,0),(-1,-1),5), ('TOPPADDING',(0,0),(-1,-1),5),
            ('LEFTPADDING',(0,0),(-1,-1),6), ('RIGHTPADDING',(0,0),(-1,-1),6)]))
        story.extend([t, Spacer(1,6)])
    def gib(n): return f'{n/2**30:.2f}' if n is not None else 'not measured'
    story.append(Paragraph('Soup | AI Engineer experiment', styles['Title']))
    story.append(p(f'<b>{escape(v["verdict"])}</b> for automatic execution. Run: {escape(run.name)}. '
                   f'Generated: {escape(utc())}.'))
    if layout_test:
        story.append(p('<b>SYNTHETIC LAYOUT TEST - not Qwen training results and not a submission.</b>'))
    section('Choice and protocol')
    story.append(p('Qwen3-1.7B provides an ungated Apache-2.0 dense Transformer and a manageable '
                   'T4 footprint. xLAM supplies a concrete function-calling task with independently '
                   'checkable syntax, function selection, and typed arguments. Source: Salesforce '
                   'APIGen/xLAM-60k (CC BY 4.0); source-card limitations remain documented.'))
    story.append(p(f'{c["train_examples"]} train / {c["validation_examples"]} validation / '
                   f'{c["test_examples"]} test; naming-based API families separated, normalized prompts '
                   f'deduplicated, cross-split near duplicates excluded. One call, at most {c["max_tools"]} '
                   f'tools; literal arguments/defaults only. No truncation, length limit {c["max_length"]}. LoRA r={c["lora_rank"]}, '
                   f'alpha={c["lora_alpha"]}, q/v projections; one epoch, lr={c["learning_rate"]}, '
                   f'batch 1, accumulation {c["gradient_accumulation"]}, FP16 compute and FP32 adapter/Adam '
                   'states. Explicit response+EOT supervision; thinking disabled.'))
    story.append(p('PyTorch/Transformers/PEFT exposes masks, gradients, and effective updates directly; '
                   'Soup is separately audited. The alternative stack is an observability choice, '
                   'not evidence of a Soup defect.'))
    section('Measured artifact comparison')
    rows = [['Artifact','Answer NLL','Exact call','JSON valid','Schema valid','Probe failures']]
    for name, result in evaluations.items():
        rows.append([name, f'{result["response_nll"]:.4f}', f'{result["exact_accuracy"]:.1%}',
                     f'{result["json_validity"]:.1%}',f'{result["schema_validity"]:.1%}',
                     f'{result["critical_probe_failures"]}/48'])
    table(rows,[74,70,75,75,75,82])
    ci = v['comparison']['quant_vs_base_exact_ci']
    story.append(p(f'4-bit minus base exact-call change: {ci["mean"]:+.3f}; paired 95% family-bootstrap '
                   f'interval [{ci["low"]:+.3f}, {ci["high"]:+.3f}], {ci["groups"]} groups. '
                   'NLL is response-token weighted; its separate paired intervals use per-example NLL. '
                   'Exact call permits documented optional-default equivalence; raw strict exact is retained.'))
    section('Memory budget made before training')
    if env.get('fallback_reason'):
        story.append(p('<b>Hardware deviation:</b> '+escape(env['fallback_reason'])+
                       ' All model measurements below come from the declared fallback, not Colab.'))
    story.append(p(f'GPU: {escape(env.get("gpu","unknown"))}, {gib(env.get("gpu_memory_bytes"))} GiB; '
                   f'host RAM: {gib(env.get("system_ram_bytes"))} GiB. '
                   f'P={estimate["unique_parameters"]:,} unique parameters; frozen FP16 weights '
                   f'2P={gib(estimate["training_components_bytes"]["frozen_fp16_weights"])} GiB. '
                   f'A={estimate["lora_parameters"]:,}; adapter+gradient+Adam moments = 16A bytes. '
                   'Logits/loss/backward allowance = BSV(2+4+4) bytes, with B=1. '
                   'Checkpoint activations and a 1 GiB workspace/context allowance are added.'))
    rows = [['Stage','Estimate GiB','Peak allocated','Peak reserved','Host RSS highwater']]
    gaps = []
    for phase, key in [('train','training_peak_estimate_bytes'),('merge','merge_peak_estimate_bytes'),
                       ('quantize','quantize_peak_estimate_bytes')]:
        m = read_json(run/f'evidence/{phase}/memory.json')
        rows.append([phase,gib(estimate[key]),gib(m['gpu_allocated_peak_bytes']),
                     gib(m['gpu_reserved_peak_bytes']),gib(m['process_lifetime_rss_highwater_bytes'])])
        if m['gpu_allocated_peak_bytes'] is not None:
            gaps.append(f'{phase}: {(m["gpu_allocated_peak_bytes"]-estimate[key])/2**30:+.2f} GiB')
    table(rows,[65,83,100,100,103])
    story.append(p('Measured allocated minus estimate: '+escape('; '.join(gaps))+'. '
                   'Merge estimate: 4P + largest-tensor overlap + per-projection temporary work + allowance. '
                   'NF4 storage counts packed linear weights, scales, and unquantized embeddings/norms. '
                   'GPU telemetry is sampled each second and can miss spikes; allocator peaks omit external '
                   'CUDA memory. RSS includes imports and file-backed pages. Full component arithmetic, '
                   'stage deltas, and raw device output are in the evidence archive.'))
    story.append(PageBreak())
    section('What proves training, and what the checks miss')
    numeric = v['numeric_comparison']
    story.append(p(f'Training effect established: <b>{v["training_effect_established"]}</b>; '
                   f'task improvement established: <b>{v["task_improvement_established"]}</b>; '
                   f'export faithful: <b>{v["export_faithful"]}</b>. '
                   f'{train["optimizer_steps"]} optimizer steps were recorded. The verifier checks effective '
                   'LoRA BA updates, not merely nonzero randomly initialized A tensors.'))
    story.append(p(f'Enabled/disabled logit RMS difference: {numeric["active_disabled_logits_rms"]:.6g}; '
                   f'repeat-run RMS noise: {numeric["repeat_logits_rms"]:.6g}. '
                   f'Active/merged maximum FP32 logit error: {numeric["merged_logits_max_abs_error"]:.6g}. '
                   'Eight validation conversations probe the first/last supervised positions over the full vocabulary. '
                   'A fresh adapter and a real zero-learning-rate optimizer run are no-op controls. '
                   'The untouched base as a merged artifact and FP weights as a quantized artifact must be rejected.'))
    section('Silent failures: evidence and coverage')
    table([
        ['Failure','Our evidence/check','Soup evidence'],
        ['Wrong masks / truncation','Prefix equality, shifted labels, EOT and no-truncation assertions; synthetic mask tests.','Data-doctor report and deliberate 32-token control retained; its collator is not ours.'],
        ['Run completes without learning','Zero-LR control, initial/final BA norms, active/disabled logits.','Live untrained-adapter ship control; inspect its explicit failed rule, not exit code alone.'],
        ['Adapter lost during merge','Reloaded merged logits vs active adapter; base-as-merged negative control.','Offline ship replays scores and does not itself prove merge parity.'],
        ['Quantization absent or damaging','Packed NF4 inventory, fresh reload, quality deltas; FP-as-4-bit control.','Offline ship applies supplied task/general scores; no independent artifact inspection.'],
        ['JSON looks correct but call is wrong','Typed complete-call scoring, wrong-argument tests, raw outputs.','Our scorer tests are independent; Soup general-suite scorer/version and outputs retained.'],
    ],[111,205,135])
    section('Verdict and changes required')
    reasons = v['reasons'][:5]
    for reason in reasons:
        story.append(p('- '+escape(reason)))
    if len(v['reasons']) > 5:
        story.append(p(f'{len(v["reasons"])-5} additional failed conditions are listed in verification.json.'))
    story.append(p('Before automatic release: resolve failed integrity/quality gates, verify references, '
                   'expand independent API and adversarial coverage, and validate tool permissions, abstention, '
                   'and side effects in a representative sandbox. Do not lower thresholds after seeing test results.'))
    section('Limits and AI use')
    story.append(p('Public-data holdouts cannot rule out prior training exposure. Naming-based groups can miss '
                   'API aliases; exact references can reject equivalent answers. The 48 templated probes are '
                   'correlated. No real external tool was executed. Successful offline tests alone do not establish '
                   'automatic-execution safety.'))
    story.append(p('AI assisted source comparison, implementation, tests, and report drafting. The initial '
                   'Qwen2.5/Dolly proposal and generic exact-match scoring were revised after inspection. '
                   'Concrete checks, corrections, failures, and applicant review status are recorded in '
                   'DECISIONS.md and EXPERIMENT_LOG.md.'))
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=36, leftMargin=36,
                            topMargin=30, bottomMargin=32)
    def footer(canvas, document):
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#6b7280'))
        canvas.drawString(36,18,'SYNTHETIC LAYOUT TEST - NOT MODEL RESULTS' if layout_test else
                          'Source revisions, raw evidence, and detailed limitations accompany this report.')
        canvas.drawRightString(A4[0]-36,18,str(document.page))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    if doc.page != 2:
        raise ValueError(f'Report rendered {doc.page} pages; revise layout before submission')
    write_json(out/'report_metadata.json', {'generated_at': utc(), 'pages': doc.page,
                                           'sha256': sha256_file(path), 'synthetic_layout_test': layout_test})
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
