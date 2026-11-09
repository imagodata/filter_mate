# -*- coding: utf-8 -*-
"""filtermate_core's PostgreSQLSqlBuilder, without QGIS, writes the SQL the plugin writes in QGIS.

postgresql_qgis_answers.jsonl holds build_expression outputs of the plugin
(``adapters.backends.postgresql.expression_builder.PostgreSQLExpressionBuilder``)
run in QGIS 3.44 and 4.3 on 2026-10-27, which agreed, and agreed with the
builder before it moved into the core (19 440 inputs). The cases keep EPSG
source CRSs: there the core's CRS defaults answer as the QGIS CRS database.
Without a database connection (the core's default, and the fixture's
unreachable host) there is no pre-computed buffer table: a dynamic buffer is
inlined, or the builder answers None in filter chaining (OGR fallback).
"""
import json
import logging
from pathlib import Path

import pytest

from filtermate_core.sql.postgresql.expression_builder import PostgreSQLSqlBuilder

pytestmark = pytest.mark.unit

_CASES = [json.loads(line) for line in
          (Path(__file__).with_name('postgresql_qgis_answers.jsonl')).read_text(encoding='utf-8').splitlines()]


class _Crs:
    def __init__(self, srid):
        self._srid = srid

    def postgisSrid(self):
        return self._srid


class _Provider:
    def __init__(self, uri, srid):
        self._uri, self._crs = uri, _Crs(srid)

    def dataSourceUri(self):
        return self._uri

    def crs(self):
        return self._crs

    def geometryColumn(self):
        return ''


class _Layer:
    """A duck-typed PostgreSQL layer: what the builder reads of a layer."""

    def __init__(self, uri, srid):
        self._provider = _Provider(uri, srid)

    def dataProvider(self):
        return self._provider

    def crs(self):
        return self._provider.crs()

    def name(self):
        return 'target'


class _Builder(PostgreSQLSqlBuilder):
    """The smallest host: nothing to apply the SQL to."""

    def supports_layer(self, layer):
        return True

    def apply_filter(self, layer, expression, old_subset=None, combine_operator=None):
        return True


def _build(case):
    builder = _Builder({
        'buffer_endcap_style': 'round', 'buffer_segments': 5, 'centroid_mode': 'point_on_surface',
        'infos': {'layer_crs_authid': case['source_authid']}, 'task': {'session_id': 'sess01'},
    })
    props = {'layer': _Layer(case['uri'], case['layer_srid']), 'layer_name': 'target', 'layer_schema': 'public',
             'layer_table_name': 'fallback_t', 'layer_geometry_field': 'fallback_g'}
    source = dict(case['source'])
    return builder.build_expression(
        layer_props=props, predicates=case['predicates'], source_geom=source.pop('source_geom', None),
        buffer_value=case['buffer_value'], buffer_expression=case['buffer_expression'],
        source_filter=source.pop('source_filter', None), use_centroids=case['use_centroids'], **source)


def test_the_fixture_covers_the_strategies():
    sources = {tuple(sorted(c['source'])) for c in _CASES}
    assert any('source_wkt' in s for s in sources)            # simple WKT
    assert any('source_filter' in s for s in sources)         # EXISTS
    assert any('filter_chain_mv_name' in s for s in sources)  # filter chain MV
    assert {c['layer_srid'] for c in _CASES} == {2154, 4326, 3857}
    assert any(c['expected'] is None for c in _CASES)          # OGR fallback answers


@pytest.mark.parametrize('case', _CASES, ids=[f'case{i}' for i in range(len(_CASES))])
def test_same_sql_as_the_plugin_in_qgis(case):
    assert _build(case) == case['expected']


def test_apply_filter_and_supports_layer_are_the_hosts():
    with pytest.raises(TypeError):
        PostgreSQLSqlBuilder({})  # abstract: no layer to put the SQL on


class TestHostHooks:
    def test_no_connection_by_default(self):
        assert _Builder({})._connection_for_layer(_Layer('', 2154)) is None

    def test_user_warning_goes_to_the_log(self, caplog):
        builder = _Builder({})
        with caplog.at_level(logging.WARNING):
            builder._detect_and_warn_complex_query(
                buffer_expression='"homecount" * 2', source_filter='EXISTS (SELECT 1)', layer_name='ducts')
        assert builder._is_complex_query
        assert any("Complex query on 'ducts'" in r.getMessage() for r in caplog.records)

    @pytest.mark.parametrize('authid, srid', [
        ('EPSG:2154', 2154), ('epsg:3857', 3857), (' EPSG:27572 ', 27572),
        # other authorities need a CRS database: the QGIS subclass resolves them
        ('IGNF:LAMB93', None), ('ESRI:102110', None),
        ('', None), (None, None), (42, None), ('EPSG:0', None),
    ])
    def test_authid_to_srid(self, authid, srid):
        assert _Builder._authid_to_srid(authid) == srid

    @pytest.mark.parametrize('srid, geographic', [
        (4326, True), (4258, True), (4269, True), (2154, False), (3857, False), (None, False), (0, False),
    ])
    def test_srid_is_geographic(self, srid, geographic):
        assert _Builder._srid_is_geographic(srid) is geographic
