"""Build a self-contained notebook from the tested source, with no credential embedding."""
import base64
import io
import json
import textwrap
import zipfile
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]


def build():
    files = [*ROOT.glob('*.py'), *ROOT.glob('*.json'), ROOT/'requirements.txt', ROOT/'pytest.ini',
             *ROOT.glob('*.md'), *ROOT.glob('soup_task/*.py'), *ROOT.glob('tests/*.py'),
             *ROOT.glob('scripts/*.py'), *ROOT.glob('scripts/*.sh')]
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for file in sorted(set(files)):
            if file.is_file():
                z.writestr(str(file.relative_to(ROOT)), file.read_bytes())
    payload = base64.b64encode(data.getvalue()).decode()
    nb = nbf.v4.new_notebook()
    md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
    nb.cells = [
        md('# Soup: evidence-first LoRA experiment\n\n'
           '**Qwen3-1.7B + xLAM; official environment: free Colab T4.**\n\n'
           'Select **Runtime → Change runtime type → T4 GPU**. Run cells in order. '
           'Source is embedded from the locally tested project. No token is embedded. '
           'Access and reference review are explicit checkpoints. All model results below '
           'are produced by the runtime; this distributed notebook has not yet been executed.\n\n'
           'The task is offline call prediction for an automatic-execution verdict. No external '
           'tools are executed. Offline benchmark success does not establish deployment safety.'),
        code("from pathlib import Path\nimport base64, io, os, zipfile, sys, subprocess\n"
             "project = Path('/content/soup_submission')\nproject.mkdir(exist_ok=True)\n"
             'source_payload = """\n'+textwrap.fill(payload, 120)+'\n"""\n'
             "with zipfile.ZipFile(io.BytesIO(base64.b64decode(source_payload))) as z:\n"
             "    z.extractall(project)\n"
             "os.chdir(project)\n"
             "subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-r', 'requirements.txt'], check=True)\n"
             "print('Source installed. Colab CUDA torch was not replaced with a CPU wheel.')"),
        md('## Hardware and local logic checks\n\n'
           'This checks the actual hardware and runs synthetic scorer/model tests. '
           'Synthetic tests are implementation evidence, not xLAM benchmark results.'),
        code("from soup_task.runtime import require_t4, environment\n"
             "from soup_task.core import utc\nimport json\n"
             "require_t4()\nprint(json.dumps(environment(), indent=2))\n"
             "test = subprocess.run([sys.executable, '-m', 'pytest', '-q'], capture_output=True, text=True)\n"
             "print(test.stdout, test.stderr)\n"
             "(project/'LOCAL_TESTS.txt').write_text(utc()+'\\n'+test.stdout+test.stderr)\n"
             "test.check_returncode()"),
        md('## Authorized dataset access\n\n'
           'Accept the conditions on the [xLAM dataset page](https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k) '
           'in your Hugging Face account. Upload an already authorized source JSON (or .json.gz) to /content/, '
           'or enter a read token in the private prompt. '
           'Do not put credentials in a code cell or saved output.'),
        code("from getpass import getpass\nimport gzip, shutil\n"
             "local_dataset = Path('/content/xlam_function_calling_60k.json')\n"
             "compressed_dataset = local_dataset.with_suffix('.json.gz')\n"
             "if compressed_dataset.is_file() and not local_dataset.exists():\n"
             "    with gzip.open(compressed_dataset, 'rb') as source, local_dataset.open('wb') as target:\n"
             "        shutil.copyfileobj(source, target)\n"
             "if local_dataset.is_file():\n"
             "    os.environ['XLAM_LOCAL_FILE'] = str(local_dataset)\n"
             "elif not os.environ.get('HF_TOKEN'):\n"
             "    os.environ['HF_TOKEN'] = getpass('Hugging Face read token (hidden): ')\n"
             "from datetime import datetime, timezone\n"
             "run = project/'runs'/('colab-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))\n"
             "subprocess.run([sys.executable, '-u', 'experiment.py', 'prepare', '--run-dir', str(run)], check=True)\n"
             "(run/'evidence/local_tests.txt').write_text((project/'LOCAL_TESTS.txt').read_text())\n"
             "print('Prepared:', run)"),
        md('## Review references and preserve the pre-training estimate\n\n'
           'Read the 40 references: check required values, tool choice, ambiguity, and labels. '
           'Do not approve an unaudited sample. If references need exclusion, preserve this attempt '
           'and update the selection rules before creating a fresh run. The estimate is immutable.'),
        code("from IPython.display import display, Markdown\n"
             "display(Markdown((run/'data/AUDIT.md').read_text()))\n"
             "print((run/'evidence/memory_estimate_before_training.json').read_text())\n"
             "reviewer = input('Who reviewed these references? State AI assistance if applicable: ').strip()\n"
             "notes = input('Record findings and limitations; enter nothing to stop: ').strip()\n"
             "if not reviewer or not notes:\n    raise RuntimeError('Reference review was not recorded.')\n"
             "subprocess.run([sys.executable, 'experiment.py', 'approve-audit', '--run-dir', str(run),\n"
             "                '--reviewer', reviewer, '--notes', notes], check=True)"),
        md('## Run the measured pipeline\n\n'
           'The stages are pre-flight, LoRA + zero-LR control, GPU FP32 merge, NF4 export, '
           'fresh artifact comparisons, Soup diagnostics, verification, and report packaging. '
           'Each stage gets timestamped logs, allocator/RSS measurements, and raw nvidia-smi output. '
           'A failure stops execution and preserves the attempt. Reconnecting does not guarantee recovery '
           'if Colab deletes the VM; download evidence/checkpoints when available.'),
        code("subprocess.run([sys.executable, '-u', 'experiment.py', 'run', '--run-dir', str(run)], check=True)"),
        md('## Inspect and download evidence\n\n'
           'A negative verdict is an honest result. Read the reasons and raw outputs. '
           'Review the two-page PDF visually, the reflection draft, and AI-use notes before submission. '
           'Save this notebook with outputs after clearing any sensitive accidental input.'),
        code("from google.colab import files\n"
             "print((run/'results/verification.json').read_text())\n"
             "files.download(str(run/'submission/report.pdf'))\n"
             "files.download(str(run/'submission/supporting_files.zip'))\n"
             "display(Markdown((run/'submission/REFLECTION.md').read_text()))"),
        md('## Preserve large artifacts separately\n\n'
           'The email archive contains the adapter, source, data selections, results, and raw logs, '
           'not the multi-gigabyte full weights. Download the merged and NF4 artifacts before releasing '
           'the runtime. Use the cell below on one file at a time to avoid concurrent large browser blobs. '
           'Download all files in each model directory; keep the shard index and tokenizer files. '
           'Compare each downloaded file against `artifact_manifest.json`.'),
        code("for kind in ['merged', 'quantized']:\n"
             "    for path in sorted((run/'artifacts'/kind).glob('*')):\n"
             "        if path.is_file(): print(path, path.stat().st_size, 'bytes')\n"
             "# Set one path from the printed list, then run files.download(str(path)).\n"
             "# Keep the runtime until all required artifacts and evidence are backed up."),
        md('## Independent verification\n\n'
           '`python verify.py --run-dir <run>` reloads models on the T4 and reruns comparisons in a new '
           'verification directory. `--recorded` replays saved predictions/probes and checks artifact '
           'hashes; it must not be described as a fresh model evaluation.\n\n'
           'Submit by replying to **team@trysoup.dev** in the original thread. The notebook never sends email.'),
    ]
    nb.metadata = {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
                   'language_info': {'name': 'python'}, 'accelerator': 'GPU',
                   'colab': {'name': 'Soup_Submission.ipynb', 'provenance': [], 'gpuType': 'T4'}}
    for cell in nb.cells:
        if cell.cell_type == 'code':
            compile(cell.source, '<notebook-cell>', 'exec')
    nbf.validate(nb)
    target = ROOT/'Soup_Submission.ipynb'
    nbf.write(nb, target)
    print(f'Built {target.name}: {len(nb.cells)} cells, {target.stat().st_size} bytes; no execution outputs.')
    return target


if __name__ == '__main__':
    build()
