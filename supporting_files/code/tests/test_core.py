import json

import pytest

from soup_task.core import (family, make_behavior_probes, normalize_row, paired_ci,
                            partition, release_verdict, score_output, strict_json, literal_grounded)

TOOLS = [{'name': 'add', 'parameters': {'a': {'type': 'int', 'required': True},
                                     'b': {'type': 'int', 'required': True}}}]
EXPECTED = [{'name': 'add', 'arguments': {'a': 2, 'b': 3}}]


def test_call_semantics_are_not_json_formatting():
    good = '[{"arguments":{"b":3,"a":2},"name":"add"}]'
    assert score_output(good, EXPECTED, TOOLS)['exact']
    wrong = '[{"name":"add","arguments":{"a":2,"b":4}}]'
    s = score_output(wrong, EXPECTED, TOOLS)
    assert s['json_valid'] and s['schema_valid'] and s['function_correct'] and not s['exact']


@pytest.mark.parametrize('text', [
    '[{"name":"subtract","arguments":{"a":2,"b":3}}]',
    '[{"name":"add","arguments":{"a":true,"b":3}}]',
    '[{"name":"add","arguments":{"a":2.0,"b":3}}]',
    '[{"name":"add","arguments":{"a":2}}]',
    '[{"name":"add","arguments":{"a":2,"b":3,"hidden":1}}]',
    '[{"name":"add","arguments":"{a:2,b:3}"}]',
    '[{"name":[],"arguments":{}}]', 'null', '{}',
])
def test_schema_rejects_wrong_types_names_and_extra_values(text):
    assert not score_output(text, EXPECTED, TOOLS)['schema_valid']


@pytest.mark.parametrize('text', ['NaN', 'Infinity', '1e999', '{"x":1,"x":2}',
                                  '```json\n[]\n```', '[] ignore this'])
def test_strict_json_rejects_non_json_and_ambiguous_values(text):
    with pytest.raises(ValueError):
        strict_json(text)


def test_abstention_and_stopping_are_independent():
    assert score_output('[]', [], TOOLS)['exact']
    assert not score_output('[]', EXPECTED, TOOLS)['exact']
    assert not score_output(json.dumps(EXPECTED), EXPECTED, TOOLS, truncated=True)['exact']


def test_omitted_and_explicit_documented_defaults_are_semantically_equivalent():
    tools = [{'name':'lookup','parameters':{'city':{'type':'str'},'limit':{'type':'int','default':'10'}}}]
    expected = [{'name':'lookup','arguments':{'city':'Paris'}}]
    good = '[{"name":"lookup","arguments":{"city":"Paris","limit":10}}]'
    result = score_output(good,expected,tools)
    assert result['exact'] and not result['strict_exact']
    assert not score_output('[{"name":"lookup","arguments":{"city":"Paris","limit":"10"}}]',expected,tools)['exact']
    assert not score_output('[{"name":"lookup","arguments":{}}]',expected,tools)['schema_valid']


def test_literal_grounding_rejects_invented_years_and_catalog_ids():
    row = {'query':'Events the day before my April 5 birthday', 'tools':[{'name':'events','parameters':{'date':{'type':'str'}}}],
           'answers':[{'name':'events','arguments':{'date':'2023-04-04'}}]}
    assert not literal_grounded(row)
    row['query']='Events on 2023-04-04'
    assert literal_grounded(row)
    row={'query':'Spend at most $450,000.', 'tools':[{'name':'search','parameters':{'price':{'type':'int'}}}],
         'answers':[{'name':'search','arguments':{'price':450000}}]}
    assert literal_grounded(row)
    row['answers'][0]['arguments']['price']=45
    assert not literal_grounded(row)


def test_stringified_xlam_fields_and_reference_validation():
    row = normalize_row({'query': 'Add 2 and 3', 'tools': json.dumps(TOOLS),
                         'answers': json.dumps(EXPECTED)}, 7)
    assert row['id'] == '7' and row['answers'] == EXPECTED
    with pytest.raises(ValueError):
        normalize_row({'query': 'Add', 'tools': TOOLS,
                       'answers': [{'name': 'add', 'arguments': {'a': True, 'b': 3}}]}, 7)


def test_related_api_names_stay_in_one_partition():
    assert family('weather.lookup') == family('weather.forecast')
    assert partition('weather.lookup') == partition('weather.forecast')
    assert partition('add_v2') == partition('add_v3')


def test_family_bootstrap_keeps_pairs_and_is_reproducible():
    a = paired_ci([.1, .2, .3, .4], ['a','a','b','b'], samples=200)
    assert a == paired_ci([.1, .2, .3, .4], ['a','a','b','b'], samples=200)
    assert a['low'] > 0 and a['groups'] == 2
    with pytest.raises(ValueError):
        paired_ci([float('nan')], ['a'])


def test_behavior_probes_have_no_executable_reference_calls():
    probes = make_behavior_probes()
    assert len(probes) == 48 and len({p['id'] for p in probes}) == 48
    assert all(p['answers'] == [] for p in probes)


def test_release_policy_separates_benchmarks_from_deployment_readiness():
    policy = {'minimum_exact_accuracy': .99, 'maximum_quant_nll_increase': .1,
              'maximum_quant_accuracy_drop': .01, 'maximum_general_drop': .05,
              'maximum_critical_probe_failures': 0, 'intended_use': 'automatic calls'}
    base = {'exact_accuracy': .8, 'response_nll': 1., 'general': {'g': .8}}
    good = {'exact_accuracy': 1., 'response_nll': .7, 'general': {'g': .8},
            'critical_probe_failures': 0}
    ci = {'quant_vs_base_exact_ci': {'low': .1}}
    assert release_verdict({'integrity': True}, base, good, good, ci, policy)['verdict'] == "DON'T SHIP"
    assert release_verdict({'integrity': True}, base, good, good, ci, policy,
                           deployment_validated=True)['verdict'] == 'SHIP'
    bad = dict(good, critical_probe_failures=1)
    assert release_verdict({'integrity': True}, base, good, bad, ci, policy,
                           deployment_validated=True)['verdict'] == "DON'T SHIP"
