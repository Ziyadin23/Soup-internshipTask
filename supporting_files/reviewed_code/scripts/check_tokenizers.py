"""Targeted post-export check prompted by a Transformers 4.57.6 regex warning."""
import argparse
import json
from pathlib import Path

from transformers import AutoTokenizer
from soup_task.core import digest_json, messages, read_json, utc, write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir',required=True)
    args=parser.parse_args();run=Path(args.run_dir).resolve()
    tokenizers={name:AutoTokenizer.from_pretrained(run/'artifacts'/name,local_files_only=True,
                trust_remote_code=False) for name in ['base','merged','quantized']}
    identity=lambda t:digest_json(json.loads(t.backend_tokenizer.to_str()))
    backends={name:identity(t) for name,t in tokenizers.items()}
    assert len(set(backends.values()))==1,'Serialized tokenizer backend drift'
    rows=sum([read_json(run/f'data/{name}.json') for name in ['train','validation','test']],[])
    rows+=read_json(run/'data/behavior_probes.json')
    changed=[]
    fixed=AutoTokenizer.from_pretrained(run/'artifacts/merged',local_files_only=True,
                                      trust_remote_code=False,fix_mistral_regex=True)
    for row in rows:
        ids=lambda t:t.apply_chat_template(messages(row),tokenize=True,
                                          add_generation_prompt=True,enable_thinking=False)
        original=ids(tokenizers['base'])
        assert all(ids(t)==original for t in tokenizers.values()),row['id']
        if ids(fixed)!=original:changed.append(row['id'])
    result={'checked_at':utc(),'prompts_checked':len(rows),'original_backends':backends,
            'original_token_ids_identical':True,'deliberate_control':'Apply Mistral-specific regex fix to Qwen in memory only; no saved artifact changed.',
            'fixed_backend_differs':identity(fixed)!=backends['base'],
            'fixed_prompts_changed':len(changed),'first_changed_ids':changed[:10],
            'limit':'Equivalence and drift detection do not prove universal tokenizer correctness.'}
    assert result['fixed_backend_differs'],'Negative control did not alter the backend'
    write_json(run/'evidence/tokenizer-regex-control.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
