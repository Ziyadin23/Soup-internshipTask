"""Pinned data preparation, auditable filtering, and pre-training memory arithmetic."""
from __future__ import annotations

import gc
import json
import random
import os
from collections import Counter, defaultdict
from pathlib import Path

import torch
from accelerate import init_empty_weights
from huggingface_hub import hf_hub_download, snapshot_download
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

from .core import (digest_json, encode_row, event, family, make_behavior_probes,
                   normalize_prompt, normalize_row, partition, read_json, literal_grounded,
                   sha256_file, utc, write_json)


def estimate_memory(base_dir, config):
    architecture = AutoConfig.from_pretrained(base_dir, local_files_only=True)
    with init_empty_weights():
        model = AutoModelForCausalLM.from_config(architecture)
    model.tie_weights()
    unique = sum(p.numel() for p in model.parameters())
    linears = [(n, m) for n, m in model.named_modules() if isinstance(m, torch.nn.Linear)
               and n != 'lm_head']
    targets = [(n, m) for n, m in linears if n.split('.')[-1] in config['target_modules']]
    adapter = sum(config['lora_rank']*(m.in_features+m.out_features) for _, m in targets)
    quantized = sum(m.weight.numel() for _, m in linears)
    largest = max(p.numel() for p in model.parameters())
    target_max = max(m.weight.numel() for _, m in targets)
    seq, hidden, intermediate = config['max_length'], architecture.hidden_size, architecture.intermediate_size
    layers, vocab = architecture.num_hidden_layers, architecture.vocab_size
    components = {
        'frozen_fp16_weights': unique*2,
        'fp32_adapter_weights': adapter*4,
        'fp32_adapter_gradients': adapter*4,
        'adam_two_fp32_moments': adapter*8,
        'checkpoint_boundaries': layers*seq*hidden*2,
        'one_layer_activation_working_allowance': seq*(12*hidden+8*intermediate)*2,
        'logits_loss_backward_allowance': seq*vocab*(2+4+4),
        'cuda_workspace_context_allocator_allowance': 1024**3,
    }
    # NF4 payload + first-level uint8 scales + nested FP32 scales; embeddings/head are not all 4-bit.
    qweights = quantized/2 + quantized/64 + quantized/64/256*4 + (unique-quantized)*2
    result = {'estimated_at': utc(), 'before_training': True, 'unique_parameters': unique,
              'lora_parameters': adapter, 'lora_modules': len(targets),
              'expected_quantized_modules': len(linears), 'quantized_logical_parameters': quantized,
              'unquantized_parameters': unique-quantized,
              'architecture': {'layers': layers, 'hidden': hidden, 'intermediate': intermediate,
                               'vocab': vocab, 'heads': architecture.num_attention_heads,
                               'kv_heads': architecture.num_key_value_heads},
              'microbatch': 1, 'sequence_length': seq, 'training_components_bytes': components,
              'training_peak_estimate_bytes': sum(components.values()),
              'merge_fp32_weights_bytes': unique*4,
              'merge_peak_estimate_bytes': unique*4+largest*4+target_max*12+1024**3,
              'quantized_weight_storage_estimate_bytes': int(qweights),
              'quantize_peak_estimate_bytes': int(unique*2+qweights+largest*4+1024**3),
              'host_ram_note': 'Sharded loading/saving is required. Measure RSS and system RAM; '
                               'the GPU estimate does not establish host fit.',
              'formula_notes': [
                  'All byte counts use unique tied parameters; GiB = bytes / 2**30.',
                  'Frozen base has no optimizer state or gradients; adapter and Adam states use FP32.',
                  'Gradient accumulation changes effective batch size, not simultaneous activation batch.',
                  'Activation/logit/workspace figures are analytical allowances, not exact tensor accounting.',
                  'Merge: FP32 base + one largest tensor for loading/tie/save overlap + per-target merge work.',
                  'Quantization uses sequential conversion; conservative peak allows FP16 source + destination + work.',
                  'Inference adds KV cache: 2 * layers * batch * sequence * KV_heads * head_dim * dtype_bytes.',
                  'Allocator fragmentation, kernels, CUDA context, and checkpoint recomputation explain gaps.'
              ]}
    del model
    gc.collect()
    return result


def check_splits(splits):
    seen_queries, seen_families, seen_ids = {}, {}, set()
    for split, rows in splits.items():
        for row in rows:
            if row['id'] in seen_ids:
                raise ValueError('duplicate source ID')
            seen_ids.add(row['id'])
            query = normalize_prompt(row['query'])
            if query in seen_queries:
                raise ValueError('duplicate normalized query across selected rows')
            seen_queries[query] = split
            for tool in row['tools']:
                f = family(tool['name'])
                if f in seen_families and seen_families[f] != split:
                    raise ValueError('API family crosses split boundary')
                seen_families[f] = split
    return {'unique_ids': len(seen_ids), 'unique_queries': len(seen_queries),
            'unique_api_families': len(seen_families), 'cross_split_api_families': 0}


def trigrams(text):
    words = normalize_prompt(text).split()
    return set(zip(words, words[1:], words[2:])) or {tuple(words)}


def select_rows(raw, tokenizer, config):
    rng = random.Random(config['seed'])
    order = list(range(len(raw)))
    rng.shuffle(order)
    limits = {s: config[f'{s}_examples'] for s in ('train', 'validation', 'test')}
    chosen = {s: [] for s in limits}
    counts, family_counts = Counter(), Counter()
    prompts, ids, shingles = set(), set(), []
    index = defaultdict(set)
    lengths = []
    for number, source_index in enumerate(order):
        if all(len(chosen[s]) == limits[s] for s in limits):
            break
        counts['rows_examined'] += 1
        try:
            row = normalize_row(raw[source_index], source_index)
        except (ValueError, KeyError, TypeError) as exc:
            counts[f'rejected:{exc}'] += 1
            continue
        if row['id'] in config.get('manual_exclusions', {}):
            counts['manual_audit_exclusion'] += 1
            continue
        if len(row['tools']) > config['max_tools']:
            counts['too_many_tools'] += 1
            continue
        if not literal_grounded(row):
            counts['nonliteral_or_ungrounded_reference'] += 1
            continue
        folds = {partition(t['name'], config['seed']) for t in row['tools']}
        if len(folds) != 1:
            counts['mixed_tool_family_partitions'] += 1
            continue
        split = folds.pop()
        if len(chosen[split]) >= limits[split]:
            counts['partition_already_full'] += 1
            continue
        if family_counts[(split, row['family'])] >= (20 if split == 'train' else 4):
            counts['family_cap'] += 1
            continue
        prompt = normalize_prompt(row['query'])
        if prompt in prompts or row['id'] in ids:
            counts['duplicate_id_or_query'] += 1
            continue
        grams = trigrams(prompt)
        candidates = set().union(*(index[g] for g in grams))
        if any(other_split != split and len(grams & old)/len(grams | old) >= .85
               for old, other_split in (shingles[i] for i in candidates)):
            counts['cross_split_near_duplicate'] += 1
            continue
        try:
            encoded = encode_row(tokenizer, row)
        except ValueError as exc:
            counts[f'template:{exc}'] += 1
            continue
        if len(encoded['input_ids']) > config['max_length']:
            counts['overlength'] += 1
            continue
        supervised = sum(t != -100 for t in encoded['labels'])
        if supervised > config['max_new_tokens']:
            counts['answer_over_generation_budget'] += 1
            continue
        lengths.append(len(encoded['input_ids']))
        row['rendered_tokens'] = len(encoded['input_ids'])
        row['supervised_tokens'] = supervised
        chosen[split].append(row)
        prompts.add(prompt)
        ids.add(row['id'])
        family_counts[(split, row['family'])] += 1
        for gram in grams:
            index[gram].add(len(shingles))
        shingles.append((grams, split))
        if number % 1000 == 0:
            event('selection_progress', examined=number+1,
                  selected={k: len(v) for k, v in chosen.items()})
    if any(len(chosen[s]) != limits[s] for s in limits):
        raise ValueError(f'Insufficient suitable examples: { {s: len(v) for s,v in chosen.items()} }; '
                         'do not truncate or silently substitute another dataset.')
    import numpy as np
    stats = {'source_rows': len(raw), 'selected': {k: len(v) for k,v in chosen.items()},
             'filter_counts': dict(counts), 'selected_length_p50_p95_max':
             [float(np.quantile(lengths, .5)), float(np.quantile(lengths, .95)), max(lengths)],
             'selection_note': 'Seeded candidate scan stops when quotas are full; not a whole-corpus audit.',
             'grounding_note': 'Nonliteral exclusions restrict the supported task; they are not a count of '
                               'factually incorrect source labels. Valid derivations and conversions are excluded too.',
             'family_caps': {'train': 20, 'validation': 4, 'test': 4},
             'split_limit': 'Naming-based API families and 3-gram Jaccard>=0.85 exclusion cannot prove semantic '
                            'independence or absence of pretraining exposure.',
             'integrity': check_splits(chosen)}
    return chosen, stats


def prepare(run):
    run = Path(run)
    c = read_json(run/'config.json')
    event('pinned_download_started', model=c['model'], dataset=c['dataset'])
    # Gated download first: no need to download model weights before access succeeds.
    source = os.environ.get('XLAM_LOCAL_FILE') or hf_hub_download(
        c['dataset'], c['dataset_file'], repo_type='dataset', revision=c['dataset_revision'])
    if sha256_file(source) != c['dataset_sha256']:
        raise ValueError('Dataset bytes do not match the authorized, pinned source checksum')
    snapshot_download(c['model'], revision=c['model_revision'], local_dir=run/'artifacts/base',
                      allow_patterns=['*.json', '*.txt', 'LICENSE', 'README.md'],
                      ignore_patterns=['*.safetensors*', '*.bin', 'onnx/*'], token=False)
    tokenizer = AutoTokenizer.from_pretrained(run/'artifacts/base', local_files_only=True)
    if tokenizer.pad_token_id == tokenizer.eos_token_id:
        raise ValueError('This protocol expects distinct pad and end-of-turn tokens')
    raw = read_json(source)
    if not isinstance(raw, list):
        raise ValueError('Pinned dataset unexpectedly is not a JSON list')
    splits, stats = select_rows(raw, tokenizer, c)
    for name, rows in splits.items():
        write_json(run/f'data/{name}.json', rows)
        with (run/f'data/{name}_chat.jsonl').open('x') as f:
            from .core import messages
            for row in rows:
                chat = messages(row)+[{'role': 'assistant', 'content': json.dumps(row['answers'])}]
                f.write(json.dumps({'messages': chat})+'\n')
    write_json(run/'data/behavior_probes.json', make_behavior_probes())
    with (run/'data/soup_task_eval.jsonl').open('x') as f:
        from .core import SYSTEM
        for row in splits['test']:
            f.write(json.dumps({'prompt': SYSTEM+json.dumps(row['tools'])+'\nRequest: '+row['query'],
                                'expected': json.dumps(row['answers']), 'scoring': 'exact'})+'\n')
    write_json(run/'data/selection.json', stats)
    audit_rows = splits['train'][:24]+splits['validation'][:8]+splits['test'][:8]
    write_json(run/'data/audit_sample.json', audit_rows)
    with (run/'data/AUDIT.md').open('x') as f:
        f.write('# Reference audit: review before training\n\n'
                'Check query/tool compatibility, required values, ambiguity, and reference correctness. '
                'Record exclusions before freezing a new run; never repair labels after inspecting predictions.\n\n')
        for row in audit_rows:
            f.write(f"## Source {row['id']}\n\n```json\n{json.dumps(row, indent=2)}\n```\n\n")
    budget = estimate_memory(run/'artifacts/base', c)
    write_json(run/'evidence/memory_estimate_before_training.json', budget)
    inputs = {str(p.relative_to(run)): sha256_file(p) for p in sorted((run/'data').glob('*'))
              if p.is_file()}
    inputs['config.json'] = sha256_file(run/'config.json')
    inputs.update({str(p.relative_to(run)): sha256_file(p) for p in sorted((run/'artifacts/base').glob('*'))
                   if p.is_file()})
    inputs['evidence/memory_estimate_before_training.json'] = sha256_file(run/'evidence/memory_estimate_before_training.json')
    write_json(run/'frozen_inputs.json', {'frozen_at': utc(), 'sha256': inputs,
               'source_dataset_sha256': sha256_file(source), 'model_revision': c['model_revision'],
               'dataset_revision': c['dataset_revision'], 'policy_sha256': digest_json(c['policy'])})
    return {'prepared_at': utc(), 'selection': stats, 'requires_reference_review': True}


def verify_frozen_inputs(run):
    run = Path(run)
    frozen = read_json(run/'frozen_inputs.json')
    for name, expected in frozen['sha256'].items():
        if not (run/name).is_file() or sha256_file(run/name) != expected:
            raise ValueError(f'Frozen input changed: {name}')
    return frozen
