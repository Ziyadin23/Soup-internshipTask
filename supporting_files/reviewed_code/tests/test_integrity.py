from pathlib import Path

import pytest

from soup_task.core import sha256_file, write_json
from soup_task.data import check_splits, verify_frozen_inputs
from soup_task.runtime import require_t4


def test_split_guard_rejects_duplicates_and_shared_tool_families():
    a={'id':'1','query':'one','tools':[{'name':'weather.now'}]}
    b={'id':'2','query':'two','tools':[{'name':'weather.later'}]}
    with pytest.raises(ValueError,match='family'):
        check_splits({'train':[a],'test':[b]})
    b['tools']=[{'name':'math.add'}]
    assert check_splits({'train':[a],'test':[b]})['cross_split_api_families']==0
    b['query']=' ONE '
    with pytest.raises(ValueError,match='query'):
        check_splits({'train':[a],'test':[b]})


def test_frozen_inputs_reject_post_commit_edits(tmp_path):
    path=tmp_path/'config.json';path.write_text('{"seed":42}')
    write_json(tmp_path/'frozen_inputs.json',{'sha256':{'config.json':sha256_file(path)}})
    verify_frozen_inputs(tmp_path)
    path.write_text('{"seed":43}')
    with pytest.raises(ValueError,match='Frozen input changed'):
        verify_frozen_inputs(tmp_path)


def test_official_run_does_not_silently_fall_back_to_cpu_or_another_gpu(monkeypatch):
    import torch
    monkeypatch.setattr(torch.cuda,'is_available',lambda:False)
    with pytest.raises(RuntimeError,match='CUDA'):
        require_t4()
    monkeypatch.setattr(torch.cuda,'is_available',lambda:True)
    monkeypatch.setattr(torch.cuda,'get_device_name',lambda index:'RTX 3050')
    with pytest.raises(RuntimeError,match='Expected T4'):
        require_t4()


def test_post_export_diagnostic_uses_frozen_source_and_preserves_failure(tmp_path, monkeypatch):
    import sys
    import experiment
    import soup_task.runtime as runtime

    run = tmp_path/'run'
    scripts = run/'code/scripts'
    scripts.mkdir(parents=True)
    (scripts/'__init__.py').write_text('')
    (scripts/'check_tokenizers.py').write_text("raise RuntimeError('DELIBERATE_FROZEN_TOKENIZER_DRIFT')\n")
    (run/'evidence').mkdir()
    monkeypatch.setattr(experiment,'execute_phase',lambda *args:None)
    monkeypatch.setattr(runtime,'load_credentials',lambda:None)
    monkeypatch.setattr(sys,'argv',['experiment.py','run','--run-dir',str(run)])
    with pytest.raises(RuntimeError,match='Tokenizer diagnostic failed'):
        experiment.main()
    log = (run/'evidence/tokenizer-regex-control.raw.log').read_text()
    assert 'DELIBERATE_FROZEN_TOKENIZER_DRIFT' in log and 'EXIT 1' in log
    assert not (run/'artifact_manifest.json').exists()
