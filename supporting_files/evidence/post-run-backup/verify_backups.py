from pathlib import Path
import json,time,datetime,hashlib
root=Path(__file__).resolve().parents[1];run=root/'runs/brev-20261110-main-01'
manifest=json.loads((run/'artifact_manifest.json').read_text())['artifacts']
expected={f'{folder}/{name}':details for folder,files in manifest.items() for name,details in files.items()}
verified={};started=datetime.datetime.now(datetime.timezone.utc).isoformat();deadline=time.monotonic()+5*3600
while time.monotonic()<deadline:
 for name,details in expected.items():
  if name in verified:continue
  p=run/'artifacts'/name
  if not p.is_file() or p.stat().st_size!=details['bytes']:continue
  h=hashlib.sha256()
  with p.open('rb') as f:
   for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
  if h.hexdigest()!=details['sha256']:raise RuntimeError('Backup hash mismatch: '+name)
  verified[name]=details
  print(datetime.datetime.now(datetime.timezone.utc).isoformat(),'HASH_OK',name,details['bytes'],flush=True)
 status={'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verified_files':len(verified),'expected_files':len(expected),'verified_bytes':sum(d['bytes'] for d in verified.values()),'expected_bytes':sum(d['bytes'] for d in expected.values())}
 (root/'tmp/backup_hash_progress.json').write_text(json.dumps(status,indent=2)+'\n')
 if len(verified)==len(expected):
  proof={'started_at':started,'verified_at':status['updated_at'],'all_artifact_hashes_match':True,'artifact_files':len(verified),'bytes':status['expected_bytes'],'original_manifest_sha256':hashlib.sha256((run/'artifact_manifest.json').read_bytes()).hexdigest(),'cloud_state':'STOP_PENDING','state_history':[{'at':status['updated_at'],'state':'All local artifacts verified; Brev stop pending.'}]}
  (run/'backup_verification.json').write_text(json.dumps(proof,indent=2)+'\n')
  print(json.dumps(proof),flush=True);break
 failed=root/'tmp/artifact_backup_STATUS.json'
 if failed.exists() and not json.loads(failed.read_text()).get('success',False):raise RuntimeError('Transfer process reported failure')
 time.sleep(30)
else:raise RuntimeError('Backup verification timed out; incomplete artifacts are preserved')
