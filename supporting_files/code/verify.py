"""Verify real artifacts; --recorded replays stored measurements and hashes without GPU inference."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np

from soup_task.core import (event, paired_ci, read_json, release_verdict, sha256_file,
                            utc, write_json)


def probe_comparison(active, disabled, repeat, merged, untrained, policy):
    arrays = [active, disabled, repeat, merged, untrained]
    if any(a.shape != active.shape or not np.isfinite(a).all() for a in arrays):
        raise ValueError('Probe shapes/numerics are invalid')
    rms = lambda a,b: float(np.sqrt(np.mean((a.astype(np.float64)-b.astype(np.float64))**2)))
    noise = rms(active, repeat)
    delta = rms(active, disabled)
    threshold = max(policy['minimum_logit_rms_delta'], policy['noise_multiplier']*noise)
    return {'active_adapter_changes_behavior': delta > threshold,
            'merge_faithful': bool(np.allclose(active, merged, atol=policy['merge_atol'], rtol=policy['merge_rtol'])),
            'fresh_adapter_is_noop': bool(np.allclose(untrained, disabled, atol=policy['merge_atol'], rtol=policy['merge_rtol'])),
            'base_as_merged_control_rejected': not bool(np.allclose(active, disabled,
                atol=policy['merge_atol'], rtol=policy['merge_rtol'])),
            'active_disabled_logits_rms': delta, 'repeat_logits_rms': noise, 'active_delta_threshold': threshold,
            'merged_logits_max_abs_error': float(np.max(np.abs(active-merged))),
            'merge_tolerance': {'atol': policy['merge_atol'], 'rtol': policy['merge_rtol']}}


def check_artifacts(run):
    manifest = read_json(run/'artifact_manifest.json')['artifacts']
    for artifact, files in manifest.items():
        for name, details in files.items():
            p = run/'artifacts'/artifact/name
            if not p.is_file() or sha256_file(p) != details['sha256']:
                raise ValueError(f'Artifact bytes changed: {artifact}/{name}')
    return True


def verify(run):
    from soup_task.data import verify_frozen_inputs
    verify_frozen_inputs(run)
    check_artifacts(run)
    c = read_json(run/'config.json')
    adapter = np.load(run/'evidence/probes-adapter.npz')
    merged_probe = np.load(run/'evidence/probes-merged.npz')['merged']
    numeric = probe_comparison(adapter['active'], adapter['disabled'], adapter['repeat'],
                               merged_probe, adapter['untrained'], c['policy'])
    training = read_json(run/'results/train.json')
    control = read_json(run/'evidence/zero_lr_control.json')
    stats = training['final_adapter']
    updates = stats['modules']
    effective = bool(updates) and all(x['finite'] and x['relative_delta_norm'] >
                                     c['policy']['minimum_effective_update_ratio'] for x in updates)
    base, merged, quantized = [read_json(run/f'results/eval-{n}.json')
                              for n in ['base', 'merged', 'quantized']]
    ids = [p['id'] for p in base['predictions']]
    if any([p['id'] for p in m['predictions']] != ids for m in [merged, quantized]):
        raise ValueError('Artifacts were not compared on identical ordered test examples')
    groups = [p['family'] for p in base['predictions']]
    def ci(a, b, field):
        return paired_ci([float(x[field])-float(y[field]) for x,y in zip(a['predictions'],b['predictions'])],
                         groups, c['bootstrap_samples'], c['seed'])
    comparison = {'merged_vs_base_exact_ci': ci(merged, base, 'exact'),
                  'quant_vs_base_exact_ci': ci(quantized, base, 'exact'),
                  'quant_vs_merged_exact_ci': ci(quantized, merged, 'exact'),
                  'merged_vs_base_example_nll_ci': ci(merged, base, 'response_nll'),
                  'quant_vs_merged_example_nll_ci': ci(quantized, merged, 'response_nll')}
    expected = read_json(run/'evidence/memory_estimate_before_training.json')['expected_quantized_modules']
    quant_ok = quantized['quantization']['all_nf4_uint8'] and quantized['quantization']['module_count'] == expected
    checks = {'effective_updates': effective, 'some_saved_adapter_tensors_changed': stats['changed_tensor_count'] > 0,
              'optimizer_steps_completed': training['optimizer_steps'] == training['expected_optimizer_steps'],
              'active_adapter_changes_behavior': numeric['active_adapter_changes_behavior'],
              'merge_faithful': numeric['merge_faithful'], 'fresh_adapter_is_noop': numeric['fresh_adapter_is_noop'],
              'zero_lr_control_is_noop': control['adapter']['changed_tensor_count'] == 0 and
                  all(x['effective_delta_norm'] == 0 for x in control['adapter']['modules']),
              'base_as_merged_control_rejected': numeric['base_as_merged_control_rejected'],
              'saved_4bit_reloaded': quant_ok,
              'float_as_4bit_control_rejected': merged['quantization']['module_count'] == 0,
              'tokenizers_identical': base['tokenizer_identity'] == merged['tokenizer_identity'] == quantized['tokenizer_identity']}
    verdict = release_verdict(checks, base, merged, quantized, comparison, c['policy'], deployment_validated=False)
    result = {'verified_at': utc(), **verdict, 'checks': checks, 'numeric_comparison': numeric,
              'comparison': comparison,
              'training_effect_established': effective and numeric['active_adapter_changes_behavior'],
              'task_improvement_established': comparison['quant_vs_base_exact_ci']['low'] > 0,
              'export_faithful': numeric['merge_faithful'] and quant_ok and
                  quantized['response_nll']-merged['response_nll'] <= c['policy']['maximum_quant_nll_increase'] and
                  merged['exact_accuracy']-quantized['exact_accuracy'] <= c['policy']['maximum_quant_accuracy_drop'],
              'limitations': [
                  'Finite probes examine first/last supervised positions, not all possible inputs or internal behavior.',
                  'Naming-based families and a small public-data holdout cannot establish unseen pretraining content.',
                  'Exact references may reject semantically equivalent calls; list argument order is significant.',
                  'Forty-eight correlated synthetic probes do not establish broad adversarial safety.',
                  'No real tool permissions, side effects, sandbox, or representative production execution were validated.'
              ]}
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-dir', required=True)
    p.add_argument('--recorded', action='store_true', help='Replay recorded predictions/probes; still hash-check weights')
    args = p.parse_args()
    run = Path(args.run_dir).resolve()
    if not args.recorded:
        # Independent fresh reloads into a separate verification directory preserve the original results.
        from soup_task.runtime import require_t4
        require_t4(read_json(run/'config.json').get('runtime_provider','colab'))
        import shutil
        target = run/f'reverification-{utc().replace(":", "-")}'
        target.mkdir()
        for name in ['config.json','frozen_inputs.json','reference_review.json','artifact_manifest.json']:
            shutil.copy2(run/name, target/name)
        for name in ['data','artifacts','code']:
            (target/name).symlink_to(run/name, target_is_directory=True)
        shutil.copytree(run/'results', target/'results')
        (target/'evidence').mkdir()
        shutil.copy2(run/'evidence/memory_estimate_before_training.json', target/'evidence/memory_estimate_before_training.json')
        shutil.copy2(run/'evidence/zero_lr_control.json', target/'evidence/zero_lr_control.json')
        for phase in ['probes-adapter','probes-merged','eval-base','eval-merged','eval-quantized']:
            (target/f'results/{phase}.json').unlink()
            subprocess.run([sys.executable, str(run/'code/experiment.py'), '_stage', phase,
                            '--run-dir', str(target)], check=True)
        run = target
    result = verify(run)
    destination = run/'results/verification.json'
    if destination.exists():
        destination = run/f'results/verification-replay-{utc().replace(":", "-")}.json'
    write_json(destination, result)
    event('verification_summary', trained=result['training_effect_established'],
          improved=result['task_improvement_established'], export_faithful=result['export_faithful'],
          verdict=result['verdict'], checks=result['checks'], output=str(destination))
    # A negative release verdict is data; an integrity failure must fail the verification command.
    return 0 if all(result['checks'].values()) else 2


if __name__ == '__main__':
    raise SystemExit(main())
