"""Copy remaining immutable NF4 byte ranges; accept only original whole-file SHA256s."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import datetime, hashlib, json, shutil, subprocess, time

root = Path(__file__).resolve().parents[1]
run = root/'runs/brev-20261110-main-01'
manifest = json.loads((run/'artifact_manifest.json').read_text())['artifacts']['quantized']
scratch = root/'tmp/nf4_range_backup'; scratch.mkdir(exist_ok=True)
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
files, jobs = [], []
chunk_size = 16*1024**2
for name, expected in manifest.items():
    if not name.endswith('.safetensors'):
        continue
    assert Path(name).name == name
    prefix = root/'tmp/export_backups'/('quantized__'+name)
    start = prefix.stat().st_size
    assert 0 < start < expected['bytes'], (name, start)
    staged = scratch/name
    assert not staged.exists(), staged
    shutil.copyfile(prefix, staged)
    parts = []
    for offset in range(start, expected['bytes'], chunk_size):
        length = min(chunk_size, expected['bytes']-offset)
        part = scratch/(name+'.'+str(offset)+'.part')
        parts.append(part); jobs.append((name, offset, length, part))
    files.append((name, expected, staged, parts))
    print(now(), 'PREFIX_PRESERVED', name, start, 'remaining', expected['bytes']-start, flush=True)

def fetch(job):
    name, offset, length, part = job
    remote = '/home/ubuntu/soup_submission/runs/brev-20261110-main-01/artifacts/quantized/'+name
    cmd = ['ssh', '-T', '-S', 'none', '-o', 'ControlMaster=no', '-o', 'BatchMode=yes',
           '-o', 'ConnectTimeout=15', '-o', 'ServerAliveInterval=30', '-o', 'ServerAliveCountMax=3',
           'soup-internship-t4', 'dd', 'if='+remote, 'bs=1048576', 'skip='+str(offset),
           'count='+str(length), 'iflag=skip_bytes,count_bytes', 'status=none']
    for attempt in range(3):
        with part.open('wb') as output, part.with_suffix('.raw.log').open('a') as log:
            log.write(now()+' offset='+str(offset)+' bytes='+str(length)+'\n'); log.flush()
            result = subprocess.run(cmd, stdout=output, stderr=log, stdin=subprocess.DEVNULL, timeout=600)
        if result.returncode == 0 and part.stat().st_size == length:
            print(now(), 'RANGE_COPIED', name, offset, length, flush=True)
            return
        time.sleep(3)
    raise RuntimeError('Range transfer failed: '+name+' offset='+str(offset))

completed = []
try:
    with ThreadPoolExecutor(max_workers=8) as pool:
        for future in as_completed([pool.submit(fetch, job) for job in jobs]):
            future.result()
    for name, expected, staged, parts in files:
        with staged.open('ab') as dest:
            for part in parts:
                with part.open('rb') as source:
                    shutil.copyfileobj(source, dest, 1024*1024)
        assert staged.stat().st_size == expected['bytes']
        with staged.open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == expected['sha256'], name
        staged.replace(run/'artifacts/quantized'/name)
        completed.append('quantized/'+name)
        print(now(), 'BACKED_UP_HASH_MATCH', name, expected['bytes'], flush=True)
    status = {'finished_at': now(), 'success': True, 'files': completed,
              'note': 'Final two NF4 files completed by parallel range copy; other artifacts were already verified. All original cloud hashes remain required.',
              'previous_transport_log': 'tmp/artifact_backup_v5.raw.log'}
except Exception as exc:
    status = {'finished_at': now(), 'success': False, 'completed': completed, 'error': str(exc)}
    raise
finally:
    (root/'tmp/artifact_backup_STATUS.json').write_text(json.dumps(status, indent=2)+'\n')
