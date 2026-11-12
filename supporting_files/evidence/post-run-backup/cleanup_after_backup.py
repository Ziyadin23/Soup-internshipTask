from pathlib import Path
import json,time,subprocess,datetime,hashlib,re
root=Path(__file__).resolve().parents[1];run=root/'runs/brev-20261110-main-01'
proof_path=run/'backup_verification.json'
while not proof_path.exists():time.sleep(20)
proof=json.loads(proof_path.read_text());assert proof['all_artifact_hashes_match']
now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
cmd=[str(root/'.venv/bin/python'),str(root/'verify.py'),'--run-dir',str(run),'--recorded']
with (run/'evidence/local-backup-verifier.raw.log').open('x') as f:
 f.write(now()+' COMMAND '+json.dumps(cmd)+'\n');f.flush()
 result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,cwd=root)
 f.write('\n'+now()+' EXIT '+str(result.returncode)+'\n')
assert result.returncode==0,'Copied-artifact verification failed; preserve files and investigate before cleanup'
proof['local_replay_completed_at']=now()
proof['local_replay_exit_code']=result.returncode
log_path=root/'tmp/brev-stop-and-status.raw.log'
with log_path.open('x') as f:
 f.write(now()+' COMMAND brev stop soup-internship-t4\n');f.flush()
 stop=subprocess.run(['brev','stop','soup-internship-t4'],stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,timeout=240)
 f.write('\n'+now()+' EXIT '+str(stop.returncode)+'\n')
 assert stop.returncode==0,'Brev stop returned failure'
 for attempt in range(6):
  status=subprocess.run(['brev','ls'],capture_output=True,text=True,timeout=40)
  f.write('\n'+now()+' COMMAND brev ls\n'+status.stdout+status.stderr+'\n');f.flush()
  clean=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',status.stdout)
  if status.returncode==0 and re.search(r'\bsoup-internship-t4\s+STOPPED\b',clean):break
  time.sleep(10)
 else:raise RuntimeError('Brev STOPPED was not confirmed')
proof['cloud_state']='STOPPED';proof['cloud_state_checked_at']=now()
proof['state_history'].append({'at':proof['cloud_state_checked_at'],'state':'Brev CLI confirmed STOPPED after successful local hash verification and recorded replay.'})
proof['cleanup_log_sha256']=hashlib.sha256(log_path.read_bytes()).hexdigest()
proof['storage_note']='VM is stopped, not deleted. Retained disks can still incur storage charges.'
proof_path.write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(proof),flush=True)
