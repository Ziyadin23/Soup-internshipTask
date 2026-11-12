"""Tiny random CPU models exercise real libraries; these are not task-quality results."""
import numpy as np
import pytest
import torch
from peft import LoraConfig, get_peft_model
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace
from transformers import (AutoModelForCausalLM, BitsAndBytesConfig, PreTrainedTokenizerFast,
                          Qwen3Config, Qwen3ForCausalLM)

from soup_task.core import encode_row
from soup_task.runtime import adapter_snapshot, load_model, quantization_inventory, update_stats
from verify import probe_comparison


def tiny_model():
    torch.manual_seed(42)
    return Qwen3ForCausalLM(Qwen3Config(vocab_size=128, hidden_size=64, intermediate_size=128,
        num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=2, head_dim=16,
        max_position_embeddings=128, tie_word_embeddings=True, attention_dropout=0.))


def test_response_mask_uses_template_boundaries_not_token_value_equality():
    backend = Tokenizer(WordLevel({'[UNK]':0, '[PAD]':1, '[EOT]':2, 'system':3,
                                  'user':4, 'assistant':5, 'hello':6}, unk_token='[UNK]'))
    backend.pre_tokenizer = Whitespace()
    t = PreTrainedTokenizerFast(tokenizer_object=backend, unk_token='[UNK]', pad_token='[PAD]', eos_token='[EOT]')
    t.chat_template = ("{% for m in messages %}{{ m['role'] + ' ' + m['content'] + eos_token }}"
                       "{% endfor %}{% if add_generation_prompt %}assistant {% endif %}")
    row = {'query':'hello', 'tools':[], 'answers':[]}
    encoded = encode_row(t,row)
    first = next(i for i,x in enumerate(encoded['labels']) if x != -100)
    assert first == len(encoded['prompt_ids'])
    assert all(x == -100 for x in encoded['labels'][:first])
    trained = [x for x in encoded['labels'] if x != -100]
    assert trained[-1] == t.eos_token_id and trained.count(t.eos_token_id) == 1
    # Several EOT tokens in the prompt stay masked while the response EOT is supervised.
    assert encoded['input_ids'][:first].count(t.eos_token_id) == 2


def test_real_qwen_lora_zero_lr_and_merge_roundtrip(tmp_path):
    torch.set_num_threads(2)
    model = get_peft_model(tiny_model(), LoraConfig(r=4,lora_alpha=8,lora_dropout=0.,
                            target_modules=['q_proj','v_proj'],task_type='CAUSAL_LM'))
    model.eval()
    ids = torch.randint(3,128,(1,24))
    labels = ids.clone(); labels[:,:16] = -100
    initial = adapter_snapshot(model)
    with torch.no_grad(), model.disable_adapter():
        baseline = model(ids).logits.detach().numpy()
    zero = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=0.)
    model(ids,labels=labels).loss.backward(); zero.step(); zero.zero_grad(set_to_none=True)
    control = update_stats(model,initial)
    assert control['changed_tensor_count'] == 0
    assert all(x['effective_delta_norm'] == 0 for x in control['modules'])
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=.01)
    for _ in range(8):
        optimizer.zero_grad(); model(ids,labels=labels).loss.backward(); optimizer.step()
    final = update_stats(model,initial)
    assert final['changed_tensor_count'] > 0
    assert all(x['effective_delta_norm'] > 0 and x['finite'] for x in final['modules'])
    with torch.no_grad(): active = model(ids).logits.detach().numpy()
    assert not np.allclose(active,baseline,atol=1e-3,rtol=1e-4)
    merged = model.merge_and_unload(safe_merge=True)
    merged.save_pretrained(tmp_path/'merged',safe_serialization=True)
    reloaded = AutoModelForCausalLM.from_pretrained(tmp_path/'merged').eval()
    with torch.no_grad(): output = reloaded(ids).logits.detach().numpy()
    result = probe_comparison(active,baseline,active.copy(),output,baseline.copy(),
        {'minimum_logit_rms_delta':1e-4,'noise_multiplier':10,'merge_atol':1e-3,'merge_rtol':1e-4})
    assert result['merge_faithful'] and result['active_adapter_changes_behavior']
    assert result['base_as_merged_control_rejected'] and result['fresh_adapter_is_noop']
    assert not probe_comparison(active,baseline,active.copy(),baseline,baseline,
        {'minimum_logit_rms_delta':1e-4,'noise_multiplier':10,'merge_atol':1e-3,'merge_rtol':1e-4})['merge_faithful']


def test_actual_nf4_save_reload_has_packed_weights_and_forward(tmp_path):
    torch.set_num_threads(2)
    model = tiny_model().eval()
    model.save_pretrained(tmp_path/'base',safe_serialization=True)
    q = load_model(tmp_path/'base',device='cpu',dtype=torch.float32,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.float32))
    inventory = quantization_inventory(q)
    assert inventory['all_nf4_uint8'] and inventory['module_count'] == 14
    q.save_pretrained(tmp_path/'nf4',safe_serialization=True)
    reloaded = load_model(tmp_path/'nf4',device='cpu',dtype=torch.float32)
    assert quantization_inventory(reloaded)['all_nf4_uint8']
    assert quantization_inventory(model)['module_count'] == 0
    ids = torch.tensor([[3,4,5,6]])
    with torch.no_grad():
        before, after = q(ids).logits, reloaded(ids).logits
    assert torch.isfinite(after).all()
    torch.testing.assert_close(before,after,atol=1e-5,rtol=1e-5)
