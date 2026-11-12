from pathlib import Path
import argparse,hashlib,json,re,zipfile,datetime

root=Path(__file__).resolve().parents[1]
run=root/'runs/brev-20261110-main-01';out=root/'output/submission/final'
parser=argparse.ArgumentParser();parser.add_argument('--preview',action='store_true');args=parser.parse_args()
if not args.preview:
 proof=json.loads((run/'backup_verification.json').read_text())
 assert proof['all_artifact_hashes_match'] and proof['cloud_state']=='STOPPED'
name='supporting_files-preview.zip' if args.preview else 'supporting_files.zip'
archive=out/name
assert not archive.exists(),archive
files={}
def add(src,dest):
 src=Path(src)
 if src.is_file():
  assert dest not in files,dest
  files[dest]=src
for folder in ['code','data','results','evidence','artifacts/adapter']:
 for src in (run/folder).rglob('*'):
  if src.is_file() and src.suffix not in ['.npz','.pt','.pyc'] and not any(x in src.parts for x in ['.cache','__pycache__']):
   add(src,str(src.relative_to(run)))
for src in run.glob('*.json'):add(src,src.name)
for src in root.glob('*.md'):add(src,'docs/'+src.name)
for pattern in ['*.py','*.json','soup_task/*.py','scripts/*.py','scripts/*.sh','tests/*.py','licenses/*']:
 for src in root.glob(pattern):add(src,'reviewed_code/'+str(src.relative_to(root)))
for src in [root/'requirements.txt',root/'pytest.ini',root/'.gitignore']:
 add(src,'reviewed_code/'+src.name)
for src in root.glob('evidence/local-checks/*'):
 if src.is_file():add(src,'evidence/post-run-local-checks/'+src.name)
add(root/'Soup_Submission.ipynb','Soup_Submission.ipynb')
add(root/'Soup-Task-01-AI-Engineer.pdf','assignment/Soup-Task-01-AI-Engineer.pdf')
add(root/'tmp/reviewed_tools.zip','evidence/source-versions/cloud-reviewed-source.zip')
add(root/'tmp/current_source_manifest.json','evidence/source-versions/current_source_manifest.json')
for src in root.glob('licenses/*'):add(src,'licenses/'+src.name)
for src in [out/'report.pdf',out/'report_metadata.json',out/'REFLECTION.md',out/'EMAIL_DRAFT.txt']:
 add(src,'submission/'+src.name)
for src in [run/'submission/report.pdf',run/'submission/report_metadata.json',run/'submission/REFLECTION.md']:
 add(src,'evidence/original-assessment/'+src.name)
readme='''# Soup task submission bundle

The final two-page report and reflection are under submission/. The standalone PDF attached to the email is the same report. docs/ contains the completed decision record, journal, memory/error analyses, AI-use record and source-version explanation. assignment/ preserves the original task.

code/ is the exact original measured source, with code_manifest.json. reviewed_code/ contains the corrected gate and later diagnostic/report/reproduction hardening. The immutable cloud-reviewed ZIP and its historical manifest are under evidence/source-versions/; the verifier and core gate used in the corrected replay match reviewed_code byte for byte. Model data/runtime/stages and core outside the release gate are unchanged from the measured source. See docs/SOURCE_VERSIONS.md.

Both original verification.json and the separately named corrected verification replay are preserved in results/. The reviewed pointer identifies the result used for the final PDF. An exact five-point boundary was incorrectly flagged by the original custom gate; the corrected replay removes that one false flag, while DON'T SHIP remains supported by the other conditions. Source changes are not represented as the source used for original training.

Raw timestamped phase logs, nvidia-smi output, individual predictions, Soup controls and setup failures are under evidence/. Synthetic local controls and real model measurements are explicitly identified. No real external tool was executed. The notebook is an unexecuted reproduction notebook with a separately labeled table read from archived Brev results, not a completed Colab transcript.

Large base/merged/NF4 model weights, full probe arrays and optimizer checkpoints are retained separately in the full run, not this email ZIP. Model file hashes are in artifact_manifest.json; omitted-array hashes are in evidence/probe_array_manifest.json. Publication copies of data/train.json and data/train_chat.jsonl redact a credential-like default from two public source schemas. DATA_REDACTIONS.json records original and packaged hashes; no validity/authentication test was performed. The original measured run remains unchanged. Restore those two private original data files as well as the omitted full artifacts before frozen-input replay; the redacted publication copies deliberately do not match frozen_inputs.json. For a new release run, sanitize tool schemas before training and create a fresh run. Otherwise reproduce the measured reference privately using the pinned source and instructions in docs/README.md.

On a complete run: python reviewed_code/verify.py --run-dir <full-run> --recorded checks hashes and replays evidence; without --recorded it reloads models and reruns inference on the declared T4. Replay is not fresh inference. Exit 2 means an integrity check failed; a release DON'T SHIP verdict alone is not a crash.

For a new reproduction use reviewed_code/experiment.py with the recorded config and a fresh run directory, review the references explicitly, then run the pipeline. Keep CUDA-enabled torch, the pinned libraries and a C compiler on a clean VM. Do not reuse failed run IDs. Respect the retained model/dataset attributions and source-card limitations.

AI assistance and independent applicant review status are described in docs/AI_USE.md. No email was sent automatically. Review the attachments and reply in the original task email thread.
'''
manifest={};overrides={};redactions={}
credential_pattern=re.compile(rb'(?:hf_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})')
source_token_fingerprint='6b70010961f24eea44c155f490e3bbccfdc02c0a3cb050ef39de7e54b2d599d7'
for dest,src in sorted(files.items()):
 parts=Path(dest).parts
 assert not Path(dest).is_absolute() and '..' not in parts
 assert not any(p.startswith('.env') or p in ['.venv','.ssh','.brev'] for p in parts)
 assert not dest.endswith(('.npz','.pt','.pem'))
 if dest.endswith('.safetensors'):assert dest.startswith('artifacts/adapter/')
 data=src.read_bytes()
 found=credential_pattern.findall(data)
 if found:
  assert dest in ['data/train.json','data/train_chat.jsonl'],f'Unexpected token-like content in {dest}'
  assert len(found)==2 and all(hashlib.sha256(value).hexdigest()==source_token_fingerprint for value in found)
  original_hash=hashlib.sha256(data).hexdigest()
  data=credential_pattern.sub(b'[REDACTED_SOURCE_SCHEMA_CREDENTIAL]',data)
  assert not credential_pattern.search(data)
  overrides[dest]=data
  redactions[dest]={'original_sha256':original_hash,'packaged_sha256':hashlib.sha256(data).hexdigest(),'occurrences':len(found)}
 manifest[dest]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
assert set(redactions)=={'data/train.json','data/train_chat.jsonl'}
redaction_data=(json.dumps({'source_ids':['17135','43443'],'source_token_sha256':source_token_fingerprint,'replacement':'[REDACTED_SOURCE_SCHEMA_CREDENTIAL]','files':redactions,'notice':'Publication copies only. Original measured inputs are unchanged and retained privately. Restore original training files before frozen-input verification. Credential validity was not tested; it was never used for authentication.'},indent=2)+'\n').encode()
manifest['DATA_REDACTIONS.json']={'bytes':len(redaction_data),'sha256':hashlib.sha256(redaction_data).hexdigest()}
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
 for dest,src in sorted(files.items()):
  if dest in overrides:z.writestr(dest,overrides[dest])
  else:z.write(src,dest)
 z.writestr('DATA_REDACTIONS.json',redaction_data)
 z.writestr('README.md',readme)
 z.writestr('FILE_MANIFEST.json',json.dumps({'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'preview':args.preview,'files':manifest},indent=2)+'\n')
assert archive.stat().st_size<20*1024**2,'Keep email attachments below the planned size'
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
meta={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'preview':args.preview,'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':len(manifest),'credential_scan_passed':True,'source_schema_redactions':redactions,'large_models_included':False}
(out/(name+'.json')).write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps({'archive':str(archive),**meta}))
