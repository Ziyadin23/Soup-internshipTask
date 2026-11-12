from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import subprocess,json,time,gzip,shutil,datetime
ROOT=Path(__file__).resolve().parents[1]
REMOTE='/home/ubuntu/soup_submission/transfer_exports/'
DEST=ROOT/'tmp/export_backups';DEST.mkdir(exist_ok=True)
RUN=ROOT/'runs/brev-20261110-main-01'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
for attempt in range(60):
 result=subprocess.run(['ssh','-T','-o','BatchMode=yes','soup-internship-t4','cat '+REMOTE+'manifest.json'],capture_output=True,text=True)
 if result.returncode==0:
  rows=json.loads(result.stdout);break
 print(now(),'Waiting for immutable export compression',flush=True);time.sleep(10)
else:raise RuntimeError('Export compression did not finish')
(DEST/'manifest.json').write_text(json.dumps(rows,indent=2))
rows.sort(key=lambda r:r['transfer_bytes'],reverse=True)
print(now(),'Starting export backup',len(rows),'files',sum(r['transfer_bytes'] for r in rows),'transfer bytes',flush=True)
def copy(row):
 name=row['transfer'];assert Path(name).name==name
 folder=row['folder'];assert folder in ['merged','quantized']
 original=row['original'];assert Path(original).name==original
 local=DEST/name
 for attempt in range(3):
  cmd=['rsync','-a','--partial','--info=stats2','-e','ssh -T -o BatchMode=yes','soup-internship-t4:'+REMOTE+name,str(local)]
  with (DEST/(name+'.transfer.log')).open('a') as log:result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
  if result.returncode==0:break
  time.sleep(5)
 else:raise RuntimeError('Transfer failed: '+name)
 assert local.stat().st_size==row['transfer_bytes']
 target=RUN/'artifacts'/folder/original;target.parent.mkdir(parents=True,exist_ok=True)
 part=target.with_name(target.name+'.backup-part')
 if name.endswith('.gz'):
  with gzip.open(local,'rb') as source,part.open('wb') as dest:shutil.copyfileobj(source,dest,1024*1024)
 else:shutil.copy2(local,part)
 assert part.stat().st_size==row['original_bytes']
 part.replace(target)
 print(now(),'BACKED_UP',folder,original,row['original_bytes'],flush=True)
 return folder+'/'+original
completed=[]
try:
 with ThreadPoolExecutor(max_workers=4) as pool:
  for result in as_completed([pool.submit(copy,row) for row in rows]):completed.append(result.result())
 status={'finished_at':now(),'success':True,'files':completed,'note':'Bytes restored; final artifact-manifest SHA256 verification is still required.'}
except Exception as exc:
 status={'finished_at':now(),'success':False,'completed':completed,'error':str(exc)}
 raise
finally:(ROOT/'tmp/artifact_backup_STATUS.json').write_text(json.dumps(status,indent=2))
print(now(),'All model exports copied; ready for full SHA256 comparison.',flush=True)
