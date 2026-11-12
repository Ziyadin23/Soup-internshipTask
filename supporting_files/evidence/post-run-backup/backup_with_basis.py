"""Resume operational backup using rsync's checksum matching; never rerun a merge."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import datetime, hashlib, json, shutil, subprocess, time

root = Path(__file__).resolve().parents[1]
run = root/'runs/brev-20261110-main-01'
manifest = json.loads((run/'artifact_manifest.json').read_text())['artifacts']
remote = '/home/ubuntu/soup_submission/runs/brev-20261110-main-01/artifacts/'
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
logs = root/'tmp/basis_transfer_logs'; logs.mkdir(exist_ok=True)
def matches(path, expected):
    if not path.is_file() or path.stat().st_size != expected['bytes']:
        return False
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest() == expected['sha256']

def copy(folder, name, expected):
    assert folder in ['merged', 'quantized'] and Path(name).name == name
    target = run/'artifacts'/folder/name
    if matches(target, expected):
        print(now(), 'ALREADY_VERIFIED', folder, name, flush=True)
        return folder+'/'+name
    if folder == 'merged' and name.endswith('.safetensors'):
        scratch = root/'tmp/merged_rsync_basis'/name
        assert scratch.is_file() and scratch.stat().st_size == expected['bytes']
    elif folder == 'quantized' and name.endswith('.safetensors'):
        scratch = root/'tmp/export_backups'/('quantized__'+name)
    else:
        scratch = logs/(folder+'__'+name)
    cmd = ['rsync', '-aI', '--partial', '--inplace', '--info=stats2',
           '-e', 'ssh -T -S none -o ControlMaster=no -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30 -o ServerAliveCountMax=3',
           'soup-internship-t4:'+remote+folder+'/'+name, str(scratch)]
    for attempt in range(3):
        with (logs/(folder+'__'+name+'.raw.log')).open('a') as log:
            result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode == 0:
            break
        time.sleep(5)
    else:
        raise RuntimeError('Transfer failed: '+folder+'/'+name)
    assert matches(scratch, expected), 'Original cloud hash mismatch: '+folder+'/'+name
    target.parent.mkdir(parents=True, exist_ok=True)
    scratch.replace(target)
    print(now(), 'BACKED_UP_HASH_MATCH', folder, name, expected['bytes'], flush=True)
    return folder+'/'+name

rows = [(folder, name, details) for folder in ['merged', 'quantized']
        for name, details in manifest[folder].items()]
rows.sort(key=lambda item: item[2]['bytes'], reverse=True)
print(now(), 'Starting checksum-based backup', len(rows), 'files', flush=True)
completed = []
try:
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(copy, *row) for row in rows]
        for future in as_completed(futures):
            completed.append(future.result())
    status = {'finished_at': now(), 'success': True, 'files': completed,
              'method': 'Pinned FP32 base as rsync basis; actual trained bytes from cloud; all original hashes checked.'}
except Exception as exc:
    status = {'finished_at': now(), 'success': False, 'completed': completed, 'error': str(exc)}
    raise
finally:
    (root/'tmp/artifact_backup_STATUS.json').write_text(json.dumps(status, indent=2)+'\n')
print(now(), 'All export files match the original cloud manifest.', flush=True)
