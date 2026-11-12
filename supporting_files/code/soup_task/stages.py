"""Measured GPU stages. No real APIs are called by generated tool proposals."""
from __future__ import annotations

import gc
import json
import math
import random
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch
from huggingface_hub import snapshot_download
from peft import LoraConfig, PeftModel, get_peft_model
from transformers import BitsAndBytesConfig

from .core import (append_json, digest_json, encode_row, event, read_json,
                   sha256_file, utc, write_json)
from .data import verify_frozen_inputs
from .runtime import (adapter_snapshot, batch_for, environment, evaluate_model, load_model,
                      quantization_inventory, require_t4, response_loss, seed_everything,
                      tokenizer_for, update_stats)


def run_command(run, name, args):
    dest = Path(run)/'evidence/soup'
    dest.mkdir(parents=True, exist_ok=True)
    path = dest/f'{name}.raw.log'
    event('external_command', name=name, command=args)
    started = utc()
    with path.open('x') as f:
        f.write(f'{started} COMMAND {json.dumps(args)}\n')
        f.flush()
        result = subprocess.run(args, stdout=f, stderr=subprocess.STDOUT, timeout=300, check=False)
        f.write(f'\n{utc()} EXIT {result.returncode}\n')
    return {'name': name, 'command': args, 'returncode': result.returncode,
            'started_at': started, 'finished_at': utc(), 'log': str(path.relative_to(run))}


def preflight(run, c):
    run = Path(run)
    require_t4(c.get('runtime_provider','colab'))
    if c.get('runtime_provider') == 'brev' and not c.get('fallback_reason'):
        raise ValueError('Brev requires an explicit preserved Colab failure and fallback reason')
    verify_frozen_inputs(run)
    review = read_json(run/'reference_review.json')
    if review.get('audit_sha256') != sha256_file(run/'data/audit_sample.json') or not review.get('reviewer'):
        raise ValueError('Reference audit is missing or stale')
    env = environment()
    env['provider_declared'] = c.get('runtime_provider','colab')
    env['fallback_reason'] = c.get('fallback_reason')
    write_json(run/'evidence/colab_environment.json', env)
    with (run/'evidence/pip-freeze.txt').open('x') as f:
        subprocess.run([sys.executable, '-m', 'pip', 'freeze'], stdout=f, check=True)
    snapshot_download(c['model'], revision=c['model_revision'], local_dir=run/'artifacts/base',
                      allow_patterns=['*.safetensors', '*.safetensors.index.json'], token=False)
    checks = []
    # These commands inspect Soup's actual behavior; its mask implementation is not ours.
    checks.append(run_command(run, 'doctor', [sys.executable, '-m', 'soup_cli', 'doctor']))
    checks.append(run_command(run, 'data-doctor', [sys.executable, '-m', 'soup_cli', 'data', 'doctor',
        str(run/'data/train_chat.jsonl'), '--model', str(run/'artifacts/base'),
        '--format', 'chatml', '--max-length', str(c['max_length']), '--sample', '1000',
        '--show-mask', '1', '--output', str(run/'evidence/soup/data-doctor.json')]))
    checks.append(run_command(run, 'profile', [sys.executable, '-m', 'soup_cli', 'profile',
        '--model', str(run/'artifacts/base'), '--seq', str(c['max_length']), '--batch', '1',
        '--method', 'lora', '--lora-r', str(c['lora_rank']), '--gradient-checkpointing', 'full', '--json']))
    # Audit an equivalent config, while explicitly not claiming Soup trained our model.
    config = {'base': str(run/'artifacts/base'), 'task': 'sft',
              'data': {'train': str(run/'data/train_chat.jsonl'), 'format': 'chatml',
                       'max_length': c['max_length'], 'train_on_responses_only': True},
              'training': {'epochs': 1, 'lr': c['learning_rate'], 'batch_size': 1,
                           'gradient_accumulation_steps': c['gradient_accumulation'],
                           'gradient_checkpointing': True, 'quantization': 'none',
                           'lora': {'r': c['lora_rank'], 'alpha': c['lora_alpha'],
                                    'target_modules': c['target_modules']}},
              'output': str(run/'unused-soup-training-output')}
    import yaml
    (run/'soup.yaml').write_text(yaml.safe_dump(config))
    checks.append(run_command(run, 'doctor-config', [sys.executable, '-m', 'soup_cli',
                                                   'doctor', '--config', str(run/'soup.yaml')]))
    return {'commands': checks, 'note': 'Nonzero Soup diagnostics are preserved and investigated; '
            'they do not silently change our collator or imply equivalent mask semantics.'}


def train(run, c):
    run = Path(run)
    verify_frozen_inputs(run)
    seed_everything(c['seed'])
    tokenizer = tokenizer_for(run)
    rows = read_json(run/'data/train.json')
    validation = read_json(run/'data/validation.json')
    encoded = [encode_row(tokenizer, r) for r in rows]
    model = get_peft_model(load_model(run/'artifacts/base'), LoraConfig(
        r=c['lora_rank'], lora_alpha=c['lora_alpha'], lora_dropout=0., bias='none',
        target_modules=c['target_modules'], task_type='CAUSAL_LM'))
    model.peft_config['default'].base_model_name_or_path = c['model']
    model.peft_config['default'].revision = c['model_revision']
    model.config.use_cache = False
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    model.enable_input_require_grads()
    parameters = [p for p in model.parameters() if p.requires_grad]
    if not parameters or any(p.dtype != torch.float32 for p in parameters):
        raise ValueError('LoRA optimizer must operate on FP32 adapter parameters only')
    if any('lora_' not in n for n,p in model.named_parameters() if p.requires_grad):
        raise ValueError('A frozen base parameter is unexpectedly trainable')
    initial = adapter_snapshot(model)
    initial_stats = update_stats(model)
    model.save_pretrained(run/'artifacts/untrained_adapter', safe_serialization=True)
    tokenizer.save_pretrained(run/'artifacts/untrained_adapter')
    scaler = torch.amp.GradScaler('cuda')

    def validation_loss():
        model.eval()
        results = [response_loss(model, tokenizer, r) for r in validation]
        model.train()
        return sum(x['response_nll']*x['response_tokens'] for x in results)/sum(x['response_tokens'] for x in results)

    def optimizer_step(group, optimizer):
        optimizer.zero_grad(set_to_none=True)
        total_tokens = sum(sum(x != -100 for x in item['labels'][1:]) for item in group)
        loss_sum, input_tokens = 0., 0
        for item in group:
            batch = batch_for(item, 'cuda:0')
            count = int((batch['labels'][:, 1:] != -100).sum())
            with torch.autocast('cuda', dtype=torch.float16):
                out = model(**batch, use_cache=False)
                loss = out.loss * (count/total_tokens)
            if not torch.isfinite(loss):
                raise ValueError('Non-finite training loss; stopping instead of logging a misleading run')
            scaler.scale(loss).backward()
            loss_sum += float(out.loss.detach())*count
            input_tokens += len(item['input_ids'])
            del out, loss, batch
        scaler.unscale_(optimizer)
        norm = torch.nn.utils.clip_grad_norm_(parameters, 1.)
        if not torch.isfinite(norm):
            raise ValueError('Non-finite adapter gradient')
        previous_scale = scaler.get_scale()
        scaler.step(optimizer)
        scaler.update()
        if scaler.get_scale() < previous_scale:
            raise ValueError('AMP skipped an optimizer update; preserve failure and investigate')
        return loss_sum/total_tokens, float(norm), total_tokens, input_tokens

    before_nll = validation_loss()
    # A real backward/optimizer run with lr=0 demonstrates completion without an update.
    control_optimizer = torch.optim.AdamW(parameters, lr=0.)
    model.train()
    control_loss, control_grad, _, _ = optimizer_step(encoded[:c['gradient_accumulation']], control_optimizer)
    control = update_stats(model, initial)
    if control['changed_tensor_count'] != 0 or any(x['effective_delta_norm'] != 0 for x in control['modules']):
        raise ValueError('Zero-learning-rate control unexpectedly changed parameters')
    model.save_pretrained(run/'artifacts/zero_lr_adapter', safe_serialization=True)
    tokenizer.save_pretrained(run/'artifacts/zero_lr_adapter')
    write_json(run/'evidence/zero_lr_control.json', {'deliberate_control': True,
        'optimizer_steps': 1, 'learning_rate': 0., 'loss': control_loss, 'gradient_norm': control_grad,
        'adapter': control, 'conclusion': 'Backward and optimizer completed but adapter did not change.'})
    del control_optimizer
    gc.collect()
    optimizer = torch.optim.AdamW(parameters, lr=c['learning_rate'], weight_decay=.01)
    order = list(range(len(encoded)))
    random.Random(c['seed']).shuffle(order)
    started = time.perf_counter()
    input_total = supervised_total = steps = 0
    model.train()
    for offset in range(0, len(order), c['gradient_accumulation']):
        group = [encoded[i] for i in order[offset:offset+c['gradient_accumulation']]]
        loss, grad, supervised, input_tokens = optimizer_step(group, optimizer)
        steps += 1
        input_total += input_tokens
        supervised_total += supervised
        record = {'optimizer_step': steps, 'examples_seen': min(offset+len(group),len(order)),
                  'response_loss': loss, 'gradient_norm_before_clipping': grad,
                  'supervised_tokens': supervised, 'input_tokens': input_tokens,
                  'learning_rate': c['learning_rate'], 'amp_scale': scaler.get_scale()}
        append_json(run/'evidence/train/steps.jsonl', record)
        event('training_step', **record)
        if steps % 25 == 0:
            checkpoint = run/f'artifacts/checkpoints/step-{steps:04d}'
            model.save_pretrained(checkpoint, safe_serialization=True)
            torch.save({'optimizer': optimizer.state_dict(), 'scaler': scaler.state_dict(),
                        'optimizer_step': steps, 'order': order, 'next_offset': offset+len(group)},
                       checkpoint/'optimizer_state.pt')
    torch.cuda.synchronize()
    elapsed = time.perf_counter()-started
    final_stats = update_stats(model, initial)
    after_nll = validation_loss()
    model.save_pretrained(run/'artifacts/adapter', safe_serialization=True)
    tokenizer.save_pretrained(run/'artifacts/adapter')
    return {'initial_adapter': initial_stats, 'final_adapter': final_stats,
            'optimizer_steps': steps, 'expected_optimizer_steps': math.ceil(len(rows)/c['gradient_accumulation']),
            'train_examples': len(rows), 'validation_nll_before': before_nll,
            'validation_nll_after': after_nll, 'training_seconds': elapsed,
            'input_tokens': input_total, 'supervised_tokens': supervised_total,
            'input_tokens_per_second': input_total/elapsed,
            'timing_note': 'Main loop includes checkpoint IO; excludes download, zero-LR control and validation.',
            'optimizer_state_bytes': sum(v.numel()*v.element_size() for state in optimizer.state.values()
                                         for v in state.values() if torch.is_tensor(v))}


def merge(run, c):
    run = Path(run)
    verify_frozen_inputs(run)
    model = PeftModel.from_pretrained(load_model(run/'artifacts/base', dtype=torch.float32),
                                     run/'artifacts/adapter')
    merged = model.merge_and_unload(safe_merge=True)
    if any(p.dtype != torch.float32 or not torch.isfinite(p).all() for p in merged.parameters()):
        raise ValueError('Merged parameters must be finite FP32')
    merged.save_pretrained(run/'artifacts/merged', safe_serialization=True, max_shard_size='1GB')
    tokenizer_for(run).save_pretrained(run/'artifacts/merged')
    return {'merged_at': utc(), 'dtype': 'float32', 'device': 'cuda:0', 'safe_merge': True,
            'shard_budget': '1GB (an individual tensor may be larger)',
            'bytes_on_disk': sum(p.stat().st_size for p in (run/'artifacts/merged').glob('*') if p.is_file())}


def quantize(run, c):
    run = Path(run)
    model = load_model(run/'artifacts/merged', quantization_config=BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type='nf4', bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.float16, bnb_4bit_quant_storage=torch.uint8))
    inventory = quantization_inventory(model)
    expected = read_json(run/'evidence/memory_estimate_before_training.json')['expected_quantized_modules']
    if not inventory['all_nf4_uint8'] or inventory['module_count'] != expected:
        raise ValueError('Quantization did not replace all expected Linear layers with packed NF4')
    model.save_pretrained(run/'artifacts/quantized', safe_serialization=True, max_shard_size='1GB')
    tokenizer_for(run).save_pretrained(run/'artifacts/quantized')
    return {'quantized_at': utc(), **inventory,
            'bytes_on_disk': sum(p.stat().st_size for p in (run/'artifacts/quantized').glob('*') if p.is_file())}


@torch.inference_mode()
def capture_probes(model, tokenizer, rows):
    outputs = []
    model.eval()
    for row in rows:
        encoded = encode_row(tokenizer, row)
        positions = [i-1 for i,x in enumerate(encoded['labels']) if x != -100 and i > 0]
        positions = sorted(set(positions[:2]+positions[-2:]))
        batch = batch_for(encoded, model.device)
        logits = model(input_ids=batch['input_ids'], attention_mask=batch['attention_mask'],
                       use_cache=False).logits[0, positions].float().cpu().numpy()
        if not np.isfinite(logits).all():
            raise ValueError('Non-finite probe logits')
        outputs.append(logits)
    return np.concatenate(outputs)


def probes(run, c, kind):
    run = Path(run)
    tokenizer = tokenizer_for(run)
    rows = read_json(run/'data/validation.json')[:8]
    if kind == 'adapter':
        model = PeftModel.from_pretrained(load_model(run/'artifacts/base', dtype=torch.float32),
                                         run/'artifacts/adapter')
        active = capture_probes(model, tokenizer, rows)
        repeat = capture_probes(model, tokenizer, rows)
        with model.disable_adapter():
            disabled = capture_probes(model, tokenizer, rows)
        model.load_adapter(run/'artifacts/untrained_adapter', adapter_name='untrained')
        model.set_adapter('untrained')
        untrained = capture_probes(model, tokenizer, rows)
        np.savez_compressed(run/'evidence/probes-adapter.npz', active=active, repeat=repeat,
                            disabled=disabled, untrained=untrained)
        return {'rows': [r['id'] for r in rows], 'shape': list(active.shape),
                'dtype': 'float32', 'coverage': 'first two and last two supervised prediction positions; full vocabulary'}
    model = load_model(run/'artifacts/merged', dtype=torch.float32)
    logits = capture_probes(model, tokenizer, rows)
    np.savez_compressed(run/'evidence/probes-merged.npz', merged=logits)
    return {'rows': [r['id'] for r in rows], 'shape': list(logits.shape), 'dtype': 'float32'}


def evaluate(run, c, name):
    run = Path(run)
    verify_frozen_inputs(run)
    folder = {'base': 'base', 'merged': 'merged', 'quantized': 'quantized'}[name]
    model = load_model(run/f'artifacts/{folder}')
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(run/f'artifacts/{folder}', local_files_only=True)
    original = tokenizer_for(run)
    def identity(t):
        return digest_json({'vocab': t.get_vocab(), 'template': t.chat_template,
                            'pad': t.pad_token_id, 'eos': t.eos_token_id})
    if identity(tokenizer) != identity(original):
        raise ValueError(f'{name}: tokenizer/template drift')
    result = evaluate_model(run, name, model, tokenizer, c)
    result['tokenizer_identity'] = identity(tokenizer)
    result['quantization'] = quantization_inventory(model)
    return result


def soup_controls(run, c):
    run = Path(run)
    checks = []
    # A live negative control: Soup can reject the zero-B adapter before measuring scores.
    checks.append(run_command(run, 'ship-untrained-live', [sys.executable, '-m', 'soup_cli', 'ship',
        '--base', str(run/'artifacts/base'), '--adapter', str(run/'artifacts/untrained_adapter'),
        '--task-eval', str(run/'data/soup_task_eval.jsonl'), '--device', 'cuda',
        '--output', str(run/'evidence/soup/ship-untrained.json')]))
    # An input truncation diagnostic; this is deliberately not our actual sequence budget.
    checks.append(run_command(run, 'doctor-truncation-control', [sys.executable, '-m', 'soup_cli',
        'data', 'doctor', str(run/'data/train_chat.jsonl'), '--model', str(run/'artifacts/base'),
        '--format', 'chatml', '--max-length', '32', '--sample', '1000',
        '--output', str(run/'evidence/soup/doctor-truncation-control.json')]))
    for name in ['merged', 'quantized']:
        base = read_json(run/'results/eval-base.json')
        after = read_json(run/f'results/eval-{name}.json')
        scores = {'task': {'mode': 'metric', 'base': base['exact_accuracy'], 'tuned': after['exact_accuracy']},
                  'benchmarks': {k: {'base': v, 'tuned': after['general'][k]}
                                 for k,v in base['general'].items()}}
        write_json(run/f'evidence/soup/scores-{name}.json', scores)
        checks.append(run_command(run, f'ship-{name}-offline', [sys.executable, '-m', 'soup_cli',
            'ship', '--evidence', str(run/f'evidence/soup/scores-{name}.json'),
            '--output', str(run/f'evidence/soup/verdict-{name}.json')]))
    return {'commands': checks, 'note': 'Offline SHIP only applies Soup policy to our measured scores; '
            'it does not establish production execution safety or inspect the merged/4-bit weights.'}
