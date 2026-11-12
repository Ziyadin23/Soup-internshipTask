"""Build rsync bases from pinned weights; only original cloud hashes establish backups."""
from contextlib import ExitStack
from pathlib import Path
import argparse, base64, hashlib, json, struct
import torch
from safetensors import safe_open

root = Path(__file__).resolve().parents[1]
run = root / 'runs/brev-20261110-main-01'
parser = argparse.ArgumentParser()
parser.add_argument('headers')
parser.add_argument('--check-first', action='store_true')
args = parser.parse_args()
headers = json.loads(Path(args.headers).read_text())
index = json.loads((run/'artifacts/base/model.safetensors.index.json').read_text())['weight_map']
manifest = json.loads((run/'artifact_manifest.json').read_text())['artifacts']['merged']
dest = root/'tmp/merged_rsync_basis'
dest.mkdir(exist_ok=True)
torch.set_num_threads(2)
with ExitStack() as stack:
    sources = {name: stack.enter_context(safe_open(str(run/'artifacts/base'/name), framework='pt', device='cpu'))
               for name in set(index.values())}
    for name, encoded in sorted(headers.items()):
        assert Path(name).name == name and name in manifest
        if args.check_first and name != 'model-00001-of-00007.safetensors':
            continue
        raw = base64.b64decode(encoded)
        size = struct.unpack('<Q', raw[:8])[0]
        assert len(raw) == 8 + size
        metadata = json.loads(raw[8:])
        target = dest/name
        with target.open('wb') as f:
            f.write(raw)
            tensors = sorted(((key, value) for key, value in metadata.items() if key != '__metadata__'),
                             key=lambda pair: pair[1]['data_offsets'][0])
            for key, value in tensors:
                start, end = value['data_offsets']
                assert value['dtype'] == 'F32' and f.tell() == len(raw) + start
                tensor = sources[index[key]].get_tensor(key)
                assert list(tensor.shape) == value['shape'] and end-start == 4*tensor.numel()
                flat = tensor.reshape(-1)
                for offset in range(0, flat.numel(), 1024*1024):
                    f.write(flat[offset:offset+1024*1024].float().numpy().tobytes())
                assert f.tell() == len(raw) + end
        assert target.stat().st_size == manifest[name]['bytes']
        if args.check_first:
            # The embedding-only shard has no LoRA updates, so it is an independent exact-byte control.
            digest = hashlib.file_digest(target.open('rb'), 'sha256').hexdigest()
            assert digest == manifest[name]['sha256'], (name, digest)
            print('EXACT_UNCHANGED_SHARD_CONTROL', name, digest, flush=True)
        else:
            print('RSYNC_BASIS_ONLY', name, target.stat().st_size, flush=True)
