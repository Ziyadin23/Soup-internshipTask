"""Colab entry point. Every measured phase uses the run's frozen source snapshot."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from soup_task.core import event, read_json, sha256_file, utc, write_json

ROOT = Path(__file__).resolve().parent
PHASES = ['preflight', 'train', 'merge', 'quantize', 'probes-adapter', 'probes-merged',
          'eval-base', 'eval-merged', 'eval-quantized', 'soup-controls']


def initialize(run, config_path):
    run.mkdir(parents=True, exist_ok=False)
    (run/'evidence').mkdir()
    config = read_json(config_path)
    write_json(run/'config.json', config)
    write_json(run/'policy_before_training.json', {'committed_at': utc(), 'policy': config['policy'],
        'deployment_validation': 'Not performed by this offline study; remains a separate release requirement.'})
    files = [*ROOT.glob('*.py'), *ROOT.glob('*.json'), *ROOT.glob('*.md'),
             ROOT/'requirements.txt', ROOT/'pytest.ini', *ROOT.glob('soup_task/*.py'), *ROOT.glob('tests/*.py'),
             *ROOT.glob('scripts/*.py'), *ROOT.glob('scripts/*.sh'), *ROOT.glob('*.ipynb')]
    for src in files:
        if src.is_file():
            dst = run/'code'/src.relative_to(ROOT)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    manifest = {str(p.relative_to(run/'code')): sha256_file(p)
                for p in sorted((run/'code').rglob('*')) if p.is_file()}
    write_json(run/'code_manifest.json', manifest)
    write_json(run/'run.json', {'created_at': utc(), 'run_id': run.name,
                               'status': 'initialized; no measured model results yet'})


def execute_phase(run, phase):
    result_file = run/f'results/{phase}.json'
    if result_file.exists():
        event('completed_phase_retained', phase=phase)
        return
    # Completed or failed measurements are immutable. Do not overwrite an interrupted attempt.
    if (run/f'evidence/{phase}/memory.json').exists():
        raise RuntimeError(f'{phase} has a failed measurement. Preserve this run and use a new run ID.')
    for name, expected in read_json(run/'code_manifest.json').items():
        if sha256_file(run/'code'/name) != expected:
            raise ValueError(f'Frozen source changed: {name}')
    log_path = run/f'evidence/{phase}.timestamped.log'
    if log_path.exists():
        raise FileExistsError(f'Previous attempt exists: {log_path}; use a new run ID')
    cmd = [sys.executable, '-u', str(run/'code/experiment.py'), '_stage', phase, '--run-dir', str(run)]
    with log_path.open('x') as log:
        log.write(f'{utc()} COMMAND {json.dumps(cmd)}\n')
        log.flush()
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, bufsize=1)
        try:
            for line in process.stdout:
                line = f'{utc()} {line.rstrip()}\n'
                log.write(line)
                log.flush()
                print(line, end='', flush=True)
            rc = process.wait()
        except BaseException:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            log.write(f'{utc()} INTERRUPTED\n')
            raise
        log.write(f'{utc()} EXIT {rc}\n')
    if rc != 0:
        raise RuntimeError(f'{phase} failed with exit {rc}; raw output preserved in {log_path}')


def artifact_manifest(run):
    artifacts = {}
    for folder in ['base', 'untrained_adapter', 'zero_lr_adapter', 'adapter', 'merged', 'quantized']:
        root = run/'artifacts'/folder
        artifacts[folder] = {str(p.relative_to(root)): {'sha256': sha256_file(p), 'bytes': p.stat().st_size}
                             for p in sorted(root.glob('*')) if p.is_file()}
        if not artifacts[folder]:
            raise ValueError(f'Missing artifact: {folder}')
    write_json(run/'artifact_manifest.json', {'created_at': utc(), 'artifacts': artifacts})


def stage_main(run, phase):
    from soup_task.runtime import load_credentials, measure, require_t4, seed_everything
    load_credentials()
    c = read_json(run/'config.json')
    seed_everything(c['seed'])
    if phase == 'prepare':
        from soup_task.data import prepare
        with measure(run, phase, gpu=False):
            result = prepare(run)
    else:
        from soup_task import stages
        require_t4(c.get('runtime_provider','colab'))
        with measure(run, phase):
            if phase == 'preflight': result = stages.preflight(run, c)
            elif phase == 'train': result = stages.train(run, c)
            elif phase == 'merge': result = stages.merge(run, c)
            elif phase == 'quantize': result = stages.quantize(run, c)
            elif phase.startswith('probes-'): result = stages.probes(run, c, phase.split('-',1)[1])
            elif phase.startswith('eval-'): result = stages.evaluate(run, c, phase.split('-',1)[1])
            elif phase == 'soup-controls': result = stages.soup_controls(run, c)
            else: raise ValueError(f'Unknown phase {phase}')
    write_json(run/f'results/{phase}.json', result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'approve-audit', 'run', '_stage', 'package'])
    parser.add_argument('phase', nargs='?')
    parser.add_argument('--run-dir', required=True)
    parser.add_argument('--config', default=str(ROOT/'config.json'))
    parser.add_argument('--reviewer')
    parser.add_argument('--notes')
    args = parser.parse_args()
    run = Path(args.run_dir).resolve()
    from soup_task.runtime import load_credentials
    load_credentials()
    if args.command == 'prepare':
        initialize(run, args.config)
        execute_phase(run, 'prepare')
        event('reference_review_required', audit=str(run/'data/AUDIT.md'),
              next_command=f'python experiment.py approve-audit --run-dir {run} --reviewer NAME --notes NOTES')
    elif args.command == 'approve-audit':
        from soup_task.data import verify_frozen_inputs
        verify_frozen_inputs(run)
        if not args.reviewer or not args.notes:
            parser.error('Review requires a reviewer identity and nonempty findings; do not auto-approve.')
        write_json(run/'reference_review.json', {'reviewed_at': utc(), 'reviewer': args.reviewer,
                   'notes': args.notes, 'audit_sha256': sha256_file(run/'data/audit_sample.json'),
                   'reviewed_ids': [r['id'] for r in read_json(run/'data/audit_sample.json')]})
    elif args.command == '_stage':
        stage_main(run, args.phase)
    elif args.command == 'run':
        for phase in PHASES:
            execute_phase(run, phase)
        if not (run/'artifact_manifest.json').exists():
            artifact_manifest(run)
        verification = subprocess.run([sys.executable, str(run/'code/verify.py'), '--run-dir', str(run),
                                       '--recorded'], check=False)
        if verification.returncode not in (0, 2):
            raise RuntimeError('Verification runtime failed; do not invent a report from missing results')
        from soup_task.reporting import create_report, package
        create_report(run)
        package(run)
        event('experiment_complete', run_dir=str(run), verdict=read_json(run/'results/verification.json')['verdict'])
    else:
        from soup_task.reporting import package
        package(run)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        event('failed', exception_type=type(exc).__name__, message=str(exc))
        raise
