"""Synthetic report/archive QA. Fixture values must never be treated as model results."""
from pathlib import Path

from soup_task.core import read_json, write_json
from soup_task.reporting import create_report, package


def make_layout_fixture(run):
    run = Path(run)
    run.mkdir(parents=True)
    c = read_json(Path(__file__).resolve().parents[1]/'config.json')
    write_json(run/'config.json',c)
    v = {'verdict': "DON'T SHIP", 'reasons': ['Synthetic layout test only; no model result is represented.'],
         'training_effect_established': True, 'task_improvement_established': False,
         'export_faithful': True, 'comparison': {'quant_vs_base_exact_ci':
          {'mean': .01, 'low': -.03, 'high': .05, 'groups': 32}},
         'numeric_comparison': {'active_disabled_logits_rms': .03, 'repeat_logits_rms': 0.,
                                'merged_logits_max_abs_error': .00001}}
    write_json(run/'results/verification.json',v)
    for name in ['base','merged','quantized']:
        write_json(run/f'results/eval-{name}.json',{'response_nll': 1., 'exact_accuracy': .5,
            'json_validity': .8,'schema_validity': .7,'critical_probe_failures': 20})
    write_json(run/'results/train.json',{'optimizer_steps':125})
    write_json(run/'data/selection.json',{'synthetic':True})
    write_json(run/'evidence/colab_environment.json',{'gpu':'SYNTHETIC - no GPU measurement',
        'gpu_memory_bytes':16*2**30,'system_ram_bytes':12*2**30})
    write_json(run/'evidence/memory_estimate_before_training.json',{
        'unique_parameters':1720574976,'lora_parameters':1605632,
        'training_components_bytes':{'frozen_fp16_weights':3441149952},
        'training_peak_estimate_bytes':6364841984,'merge_peak_estimate_bytes':9251033088,
        'quantize_peak_estimate_bytes':7109136384})
    for phase in ['train','merge','quantize']:
        write_json(run/f'evidence/{phase}/memory.json',{'gpu_allocated_peak_bytes':6*2**30,
            'gpu_reserved_peak_bytes':7*2**30,'process_lifetime_rss_highwater_bytes':3*2**30})


def test_report_is_exactly_two_pages_and_labeled_synthetic(tmp_path):
    run = tmp_path/'fixture'
    make_layout_fixture(run)
    path = create_report(run,layout_test=True)
    assert path.is_file() and path.stat().st_size > 1000
    metadata = read_json(run/'submission/report_metadata.json')
    assert metadata['pages'] == 2 and metadata['synthetic_layout_test']


def test_archive_does_not_include_credentials_or_full_weights(tmp_path):
    import zipfile
    run = tmp_path/'fixture'
    make_layout_fixture(run)
    (run/'.env').write_text('HF_TOKEN=SECRET_CANARY_DO_NOT_PACKAGE\n')
    for path in ['artifacts/base/model.safetensors','artifacts/merged/model.safetensors',
                 'artifacts/quantized/model.safetensors','artifacts/adapter/adapter_model.safetensors']:
        p=run/path; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b'fixture')
    archive = package(run)
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        assert not any('.env' in n for n in names)
        assert 'artifacts/adapter/adapter_model.safetensors' in names
        assert not any(n.startswith(('artifacts/base/','artifacts/merged/','artifacts/quantized/')) for n in names)
        assert all(b'SECRET_CANARY_DO_NOT_PACKAGE' not in z.read(n) for n in names)
