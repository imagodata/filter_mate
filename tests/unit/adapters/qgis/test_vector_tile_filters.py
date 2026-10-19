"""Tile filter composition preserves style rules, bounds payloads and keeps undo state."""
import importlib.util
import pathlib
import sys

import pytest

_PATH = pathlib.Path(__file__).resolve().parents[4] / 'adapters/qgis/coverage_layers/vector_tile_filters.py'


def load():
    spec = importlib.util.spec_from_file_location('fm_tile_filters_test', _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rule_filter_cannot_be_widened_by_or():
    module = load()
    assert module.rule_expression('"kind" = \'road\'', '"height" > 3 OR "height" < 0') == (
        '("kind" = \'road\'\n) AND ("height" > 3 OR "height" < 0\n)')


def test_rule_comment_does_not_swallow_added_filter():
    module = load()
    assert '\n) AND (' in module.rule_expression('TRUE -- original rule', 'FALSE')


def test_empty_filter_keeps_original_rule():
    assert load().rule_expression('"kind" = 1', '') == '"kind" = 1'


def test_vertex_budget_refuses_instead_of_changing_geometry():
    class Shape:
        def constGet(self): return self
        def nCoordinates(self): return 20001
    with pytest.raises(ValueError, match='vertex budget'):
        load().bounded_wkt(Shape())


def test_tile_snapshot_style_is_part_of_history():
    root = _PATH.parents[3]
    spec = importlib.util.spec_from_file_location('fm_tile_snapshot_test', root / 'core/domain/filter_state.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    first = module.LayerSnapshot('id', 'vector_tile', renderer_xml='<renderer/>')
    second = module.LayerSnapshot('id', 'vector_tile', renderer_xml='<renderer filter="false"/>')
    assert not first.same_state(second)
    assert module.LayerSnapshot.from_dict(second.to_dict()) == second


def _snapshots():
    spec = importlib.util.spec_from_file_location('fm_tile_fakes', pathlib.Path(__file__).with_name('coverage_fakes.py'))
    fake = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fake)
    return fake.load('snapshots'), fake.load('core.domain.filter_state').LayerSnapshot


def test_portable_tile_favorite_drops_connection_credentials():
    snapshots, Snapshot = _snapshots()
    state = Snapshot('id', 'vector_tile', source='https://user:password@example.test/{z}?token=secret',
                     provider='xyzvectortiles', derived=True, renderer_xml='<style/>', original_renderer_xml='<base/>')
    portable = snapshots.portable_snapshot(state)
    assert portable.source == portable.provider == ''
    assert portable.renderer_xml == '<style/>'
    assert 'secret' not in str(portable.to_dict())


def test_unfilter_of_bounded_hag_recovers_full_cloud():
    snapshots, Snapshot = _snapshots()
    state = Snapshot('id', 'point_cloud', source='/cache/clipped.copc.laz', provider='copc', derived=True,
                     original_source='/cache/enriched.copc.laz', original_provider='copc',
                     enriched_source='https://example.test/full.copc.laz', enriched_provider='copc',
                     geometry_wkt='POLYGON((0 0,1 0,1 1,0 0))', bounded_enrichment=True)
    base = snapshots.base_snapshot(state)
    assert base.source == 'https://example.test/full.copc.laz'
    assert not base.derived and not base.bounded_enrichment
