"""Model execution and measurement; each expensive phase runs in a fresh process."""
from __future__ import annotations

import gc
import hashlib
import importlib.metadata
import os
import platform
import resource
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import psutil
import torch
from peft import get_peft_model_state_dict
from transformers import AutoModelForCausalLM, AutoTokenizer

from .core import (append_json, encode_row, event, messages, read_json,
                   score_output, utc, write_json)


def seed_everything(seed):
    import random
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False


def require_t4(provider='colab'):
    if not torch.cuda.is_available():
        raise RuntimeError('This run requires a CUDA T4; CUDA is unavailable.')
    name = torch.cuda.get_device_name(0)
    if 'T4' not in name:
        raise RuntimeError(f'Expected T4, found {name}. Record a hardware decision before changing it.')
    if provider not in ('colab','brev'):
        raise ValueError('Unrecognized declared runtime provider')
    if provider == 'colab' and 'google.colab' not in sys.modules and not os.environ.get('COLAB_RELEASE_TAG'):
        # Colab subprocesses do not necessarily import google.colab themselves.
        if not Path('/content').is_dir():
            raise RuntimeError('Expected Colab /content. Brev is a documented fallback, not the default.')


def load_credentials():
    env = Path(__file__).resolve().parents[1] / '.env'
    if env.is_file():
        for line in env.read_text().splitlines():
            if line.startswith('HF_TOKEN='):
                os.environ.setdefault('HF_TOKEN', line.split('=', 1)[1].strip())


def tokenizer_for(run):
    return AutoTokenizer.from_pretrained(Path(run)/'artifacts/base', local_files_only=True,
                                        trust_remote_code=False)


def load_model(path, device='cuda:0', dtype=torch.float16, quantization_config=None):
    kwargs = {'torch_dtype': dtype, 'device_map': {'': device},
              'attn_implementation': 'sdpa', 'low_cpu_mem_usage': True,
              'trust_remote_code': False, 'local_files_only': True}
    if quantization_config is not None:
        kwargs['quantization_config'] = quantization_config
    return AutoModelForCausalLM.from_pretrained(path, **kwargs)


def environment():
    versions = {}
    for name in ['torch', 'transformers', 'peft', 'accelerate', 'bitsandbytes',
                 'huggingface-hub', 'soup-cli', 'numpy']:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    out = {'recorded_at': utc(), 'python': sys.version, 'platform': platform.platform(),
           'versions': versions, 'system_ram_bytes': psutil.virtual_memory().total,
           'available_ram_bytes': psutil.virtual_memory().available,
           'cuda_available': torch.cuda.is_available(), 'torch_cuda': torch.version.cuda,
           'disk_free_bytes': psutil.disk_usage('.').free,
           'provider': 'Colab' if Path('/content').is_dir() else 'local'}
    if torch.cuda.is_available():
        p = torch.cuda.get_device_properties(0)
        out.update(gpu=p.name, gpu_memory_bytes=p.total_memory,
                   compute_capability=[p.major, p.minor])
    return out


@contextmanager
def measure(run, phase, gpu=True):
    dest = Path(run)/'evidence'/phase
    dest.mkdir(parents=True, exist_ok=True)
    if (dest/'memory.json').exists():
        raise FileExistsError(f'{phase} already has measurement evidence; use a new run for retries.')
    stop = threading.Event()
    rss_samples = []

    def sample():
        while not stop.is_set():
            rss_samples.append(psutil.Process().memory_info().rss)
            stop.wait(.05)

    thread = threading.Thread(target=sample, daemon=True)
    thread.start()
    smi = None
    smi_file = (dest/'nvidia-smi.raw.txt').open('x')
    try:
        full = subprocess.run(['nvidia-smi'], capture_output=True, text=True, check=False)
        smi_file.write(full.stdout + full.stderr)
        smi_file.flush()
        smi = subprocess.Popen(['nvidia-smi', '--query-gpu=timestamp,name,memory.total,memory.used,'
                                'utilization.gpu,power.draw', '--format=csv', '-l', '1'],
                               stdout=smi_file, stderr=smi_file)
    except FileNotFoundError:
        smi_file.write('nvidia-smi: executable not found (not a GPU measurement)\n')
    if gpu:
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    timestamp = utc()
    success = False
    event('phase_started', phase=phase)
    try:
        yield
        if gpu:
            torch.cuda.synchronize()
        success = True
    finally:
        elapsed = time.perf_counter()-started
        stop.set()
        thread.join(timeout=2)
        if smi is not None:
            smi.terminate()
            try:
                smi.wait(timeout=5)
            except subprocess.TimeoutExpired:
                smi.kill()
                smi.wait()
        smi_file.close()
        result = {'started_at': timestamp, 'finished_at': utc(), 'phase': phase,
                  'success': success, 'wall_seconds': elapsed,
                  'rss_sample_interval_seconds': .05,
                  'sampled_rss_peak_bytes': max(rss_samples, default=0),
                  'process_lifetime_rss_highwater_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                  'gpu_allocated_peak_bytes': torch.cuda.max_memory_allocated() if gpu else None,
                  'gpu_reserved_peak_bytes': torch.cuda.max_memory_reserved() if gpu else None,
                  'note': 'RSS highwater includes imports; nvidia-smi includes CUDA/context and other processes; '
                          '1-second GPU samples can miss spikes. Allocator peaks exclude non-PyTorch memory.'}
        write_json(dest/'memory.json', result)
        event('phase_finished', **result)


def batch_for(encoded, device):
    ids = torch.tensor([encoded['input_ids']], dtype=torch.long, device=device)
    return {'input_ids': ids, 'attention_mask': torch.ones_like(ids),
            'labels': torch.tensor([encoded['labels']], dtype=torch.long, device=device)}


def tensor_hash(tensor):
    data = tensor.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()
    return hashlib.sha256(data).hexdigest()


def adapter_snapshot(model):
    return {k: v.detach().cpu().clone() for k, v in get_peft_model_state_dict(model).items()}


def update_stats(model, initial=None):
    updates = []
    for name, m in model.named_modules():
        if hasattr(m, 'lora_A') and 'default' in m.lora_A:
            a = m.lora_A['default'].weight.detach().float()
            b = m.lora_B['default'].weight.detach().float()
            delta = (b @ a) * m.scaling['default']
            base_norm = float(m.base_layer.weight.detach().float().norm())
            updates.append({'module': name, 'a_norm': float(a.norm()), 'b_norm': float(b.norm()),
                            'effective_delta_norm': float(delta.norm()),
                            'relative_delta_norm': float(delta.norm())/max(base_norm, 1e-30),
                            'finite': bool(torch.isfinite(delta).all())})
    now = adapter_snapshot(model)
    return {'modules': updates, 'tensor_sha256': {k: tensor_hash(v) for k, v in now.items()},
            'changed_tensor_count': sum(not torch.equal(v, initial[k]) for k, v in now.items())
                                    if initial is not None else None}


def quantization_inventory(model):
    import bitsandbytes as bnb
    modules = []
    for name, m in model.named_modules():
        if isinstance(m, bnb.nn.Linear4bit):
            state = m.weight.quant_state
            modules.append({'name': name, 'dtype': str(m.weight.dtype),
                            'packed_numel': m.weight.numel(), 'logical_numel': m.in_features*m.out_features,
                            'quant_type': getattr(state, 'quant_type', None),
                            'nested': bool(getattr(state, 'nested', False))})
    return {'module_count': len(modules), 'modules': modules,
            'model_footprint_bytes': model.get_memory_footprint(),
            'all_nf4_uint8': bool(modules) and all(m['dtype'] == 'torch.uint8' and m['quant_type'] == 'nf4'
                                                for m in modules)}


@torch.inference_mode()
def generate(model, tokenizer, row, max_new_tokens, chat=None):
    prompt = tokenizer.apply_chat_template(messages(row) if chat is None else chat, tokenize=True,
                                          add_generation_prompt=True, enable_thinking=False)
    ids = torch.tensor([prompt], dtype=torch.long, device=model.device)
    started = time.perf_counter()
    if model.device.type == 'cuda':
        torch.cuda.synchronize()
    out = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids),
                         max_new_tokens=max_new_tokens, do_sample=False, temperature=None,
                         top_p=None, top_k=None, use_cache=True,
                         eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id)
    if model.device.type == 'cuda':
        torch.cuda.synchronize()
    new = out[0, len(prompt):].tolist()
    return {'text': tokenizer.decode(new, skip_special_tokens=True),
            'token_ids': new, 'prompt_tokens': len(prompt), 'generated_tokens': len(new),
            'truncated': tokenizer.eos_token_id not in new,
            'generation_seconds': time.perf_counter()-started}


@torch.inference_mode()
def response_loss(model, tokenizer, row):
    batch = batch_for(encode_row(tokenizer, row), model.device)
    out = model(**batch, use_cache=False)
    if not torch.isfinite(out.loss):
        raise ValueError('non-finite teacher-forced response loss')
    count = int((batch['labels'][:, 1:] != -100).sum())
    return {'response_nll': float(out.loss), 'response_tokens': count}


def evaluate_model(run, name, model, tokenizer, config):
    model.eval()
    rows = read_json(Path(run)/'data/test.json')
    predictions = []
    for row in rows:
        loss = response_loss(model, tokenizer, row)
        prediction = generate(model, tokenizer, row, config['max_new_tokens'])
        scores = score_output(prediction['text'], row['answers'], row['tools'], prediction['truncated'])
        record = {'id': row['id'], 'family': row['family'], 'expected': row['answers'],
                  **loss, **prediction, **scores}
        append_json(Path(run)/f'evidence/eval-{name}/task_predictions.jsonl', record)
        predictions.append(record)
    probes = []
    for row in read_json(Path(run)/'data/behavior_probes.json'):
        prediction = generate(model, tokenizer, row, config['max_new_tokens'])
        scores = score_output(prediction['text'], [], row['tools'], prediction['truncated'])
        record = {'id': row['id'], 'family': row['family'], **prediction, **scores}
        append_json(Path(run)/f'evidence/eval-{name}/probe_predictions.jsonl', record)
        probes.append(record)
    from soup_cli.eval.gate_suites import (DEFAULT_GENERAL_SUITE, score_bundled_suite,
        BUNDLED_SCORER_REVISION, BUNDLED_SCORER_FINGERPRINT)
    general = {}
    for suite in DEFAULT_GENERAL_SUITE:
        errors = []

        def gen(prompt):
            row = {'query': prompt, 'tools': []}
            # General benchmarks must not inherit the tool-only task instruction.
            try:
                result = generate(model, tokenizer, row, config['general_max_new_tokens'],
                                  chat=[{'role': 'user', 'content': prompt}])
                append_json(Path(run)/f'evidence/eval-{name}/general_predictions.jsonl',
                            {'suite': suite, 'prompt': prompt, **result})
                return result['text']
            except Exception as exc:
                errors.append(type(exc).__name__)
                raise

        general[suite] = score_bundled_suite(suite, gen)
        if errors:
            raise RuntimeError(f'{suite}: generation failed; refusing to treat a runtime error as score zero')
    tokens = sum(p['response_tokens'] for p in predictions)
    result = {'artifact': name, 'examples': len(rows),
              'response_nll': sum(p['response_nll']*p['response_tokens'] for p in predictions)/tokens,
              'exact_accuracy': float(np.mean([p['exact'] for p in predictions])),
              'json_validity': float(np.mean([p['json_valid'] for p in predictions])),
              'schema_validity': float(np.mean([p['schema_valid'] for p in predictions])),
              'function_accuracy': float(np.mean([p['function_correct'] for p in predictions])),
              'critical_probe_failures': sum(not p['exact'] for p in probes),
              'general': general, 'predictions': predictions,
              'general_scorer': {'revision': BUNDLED_SCORER_REVISION,
                                'fingerprint': BUNDLED_SCORER_FINGERPRINT,
                                'max_new_tokens': config['general_max_new_tokens']},
              'probe_note': '48 templated synthetic probes are narrow, correlated tests, not broad safety evidence',
              'inference': {'weight_dtype': str(next(model.parameters()).dtype),
                            'greedy': True, 'thinking': False, 'max_new_tokens': config['max_new_tokens']}}
    return result
