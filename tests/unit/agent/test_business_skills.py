"""Domain evaluation projects must exercise their own schemas, with no state leaking between cases."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
DOMAINS = ('telecom-fiber', 'electric-networks', 'water-networks', 'asset-maintenance')


@pytest.fixture(scope='module')
def bench():
    spec = importlib.util.spec_from_file_location('business_skills_eval_bench', ROOT / 'scripts/agent_eval.py')
    module = importlib.util.module_from_spec(spec)
    original = list(sys.path)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = original
    return module


@pytest.mark.parametrize('domain', DOMAINS)
def test_domain_inventory_reads_its_schema_by_name_or_id_and_uses_its_groups(bench, domain):
    case = json.loads((ROOT / 'skills' / domain / 'evals.json').read_text())['cases'][0]
    project = bench.SimulatedProject(case['setup'])
    handlers = project.handlers()
    layer_name, schema = next(iter(case['setup']['layers'].items()))
    described = handlers['describe_layer']({'layer': schema['id']})
    assert described['name'] == layer_name
    assert {field['name'] for field in described['fields']} == set(schema['fields'])
    assert 'communes' not in project.layers and not project.selected
    view = handlers['map_context']({})
    assert view['active_layer_name'] == layer_name and view['active_layer_id'] == schema['id']
    query = next(step['call_args'] for step in case['expect'][0] if step['tool'] == 'layer_statistics')
    result = handlers['layer_statistics'](query)
    assert result['feature_count'] == schema['count']
    assert [group['value'] for group in result['groups']] == schema['fields'][query['group_by']]
    # A field added in one simulated run must not contaminate the saved fixture or the next run.
    handlers['add_field']({'layer': layer_name, 'name': 'scenario_only', 'type': 'text'})
    assert 'scenario_only' not in schema['fields']
    assert 'scenario_only' not in bench.SimulatedProject(case['setup']).layers[layer_name]['fields']


def test_default_project_is_preserved_and_explicitly_empty_project_stays_empty(bench):
    default = bench.SimulatedProject()
    assert set(default.layers) == set(bench.LAYERS) and default.selected == ['communes']
    empty = bench.SimulatedProject({'layers': {}})
    assert empty.handlers()['list_layers']({}) == {'layers': []}
    assert not empty.selected and not empty.by_ref
    assert empty.handlers()['map_context']({})['active_layer_name'] == ''
