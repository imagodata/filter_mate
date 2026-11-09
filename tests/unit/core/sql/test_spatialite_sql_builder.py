# -*- coding: utf-8 -*-
"""filtermate_core's SpatialiteSqlBuilder, without QGIS nor GDAL, writes the SQL the plugin writes in QGIS.

spatialite_qgis_answers.jsonl holds build_expression outputs of the plugin
(``adapters.backends.spatialite.expression_builder.SpatialiteExpressionBuilder``)
run in QGIS 3.44 and 4.3 on 2026-10-28 against GeoPackages written by GDAL,
which agreed, and agreed with the builder before it moved into the core
(12 990 inputs). The cases keep what the core's host defaults answer as
QGIS: a GeoPackage source in the target CRS (no reprojection of the bounding
box without a host), linear WKT. The GeoPackage is rebuilt here with sqlite3:
the R-tree of 400 road segments GDAL wrote (integer coordinates, exact in its
float32 R-tree).
"""
import json
import sqlite3
from pathlib import Path

import pytest

from filtermate_core.sql.spatialite import expression_builder as core
from filtermate_core.sql.spatialite.expression_builder import SpatialiteSqlBuilder, USE_OGR_FALLBACK

pytestmark = pytest.mark.unit

_CASES = [json.loads(line) for line in
          (Path(__file__).with_name('spatialite_qgis_answers.jsonl')).read_text(encoding='utf-8').splitlines()]


def _gpkg(path):
    """The R-tree GDAL writes for the 400 segments of the differential (see the module docstring)."""
    connection = sqlite3.connect(str(path))
    connection.execute("CREATE TABLE gpkg_extensions (table_name TEXT, column_name TEXT, extension_name TEXT)")
    connection.execute("INSERT INTO gpkg_extensions VALUES ('roads', 'geom', 'gpkg_rtree_index')")
    connection.execute("CREATE TABLE rtree_roads_geom (id INTEGER, minx REAL, maxx REAL, miny REAL, maxy REAL)")
    for i in range(400):
        x, y = 700000 + 37 * i, 6600000 + 23 * (i % 50)
        connection.execute("INSERT INTO rtree_roads_geom VALUES (?, ?, ?, ?, ?)", (i + 1, x, x + 7, y, y + 3))
    connection.commit()
    connection.close()
    return path


class _Crs:
    def __init__(self, srid):
        self._authid = f'EPSG:{srid}'

    def isValid(self):
        return True

    def authid(self):
        return self._authid


class _Provider:
    def __init__(self, uri):
        self._uri = uri

    def dataSourceUri(self):
        return self._uri

    def geometryColumn(self):
        return ''


class _Layer:
    """A duck-typed layer: what the builder reads of a layer."""

    def __init__(self, provider_type, source, srid):
        self._type, self._source, self._crs = provider_type, source, _Crs(srid)
        self._provider = _Provider(source)

    def providerType(self):
        return self._type

    def source(self):
        return self._source

    def dataProvider(self):
        return self._provider

    def crs(self):
        return self._crs

    def name(self):
        return 'target'


class _Builder(SpatialiteSqlBuilder):
    """The smallest host; its OGR backend has JSON1, as GDAL's SQLite had in the QGIS run."""

    def supports_layer(self, layer):
        return True

    def apply_filter(self, layer, expression, old_subset=None, combine_operator=None):
        return True

    def _json1_available(self):
        return True


@pytest.fixture(scope='module')
def layers(tmp_path_factory):
    folder = tmp_path_factory.mktemp('fm_sl')
    gpkg = _gpkg(folder / 'roads_l93.gpkg')
    return {
        'gpkg_l93': ('ogr', f'{gpkg}|layername=roads'),
        'spatialite': ('spatialite', "dbname='/tmp/x.sqlite' table=\"roads\" (geometry)"),
        'shp': ('ogr', str(folder / 'roads.shp')),
        'gpkg_missing': ('ogr', f'{folder / "nowhere.gpkg"}|layername=roads'),
    }


@pytest.fixture(autouse=True)
def _fresh_rtree_cache():
    core.clear_rtree_cache()
    yield
    core.clear_rtree_cache()


def _build(case, layers):
    provider_type, source = layers[case['layer']]
    builder = _Builder({
        'buffer_endcap_style': 'round', 'centroid_mode': 'point_on_surface',
        'infos': {'layer_crs_authid': case['infos_authid'], 'buffer_state': {'applied_in_wkt': case['applied_in_wkt']}},
    })
    kwargs = {} if case['source_srid'] is None else {'source_srid': case['source_srid']}
    return builder.build_expression(
        layer_props={'layer': _Layer(provider_type, source, case['layer_srid']), 'layer_name': 'target',
                     'layer_geometry_field': 'geom'},
        predicates=case['predicates'], source_geom=case['wkt'], buffer_value=case['buffer_value'],
        buffer_expression=case['buffer_expression'], use_centroids=case['use_centroids'], **kwargs)


def test_the_fixture_covers_the_strategies():
    expected = [c['expected'] for c in _CASES]
    assert any('ROWID IN (SELECT id FROM "rtree_roads_geom"' in (e or '') for e in expected)  # R-tree prefilter
    assert USE_OGR_FALLBACK in expected
    assert '1 = 0' in expected
    assert {c['layer'] for c in _CASES} == {'gpkg_l93', 'spatialite', 'shp', 'gpkg_missing'}


@pytest.mark.parametrize('case', _CASES, ids=[f'case{i}' for i in range(len(_CASES))])
def test_same_sql_as_the_plugin_in_qgis(case, layers):
    assert _build(case, layers) == case['expected']


def test_apply_filter_and_supports_layer_are_the_hosts():
    with pytest.raises(TypeError):
        SpatialiteSqlBuilder({})


class TestHostHooks:
    def test_bounds_in_the_source_crs_only(self):
        builder = _Builder({})
        wkt = 'LINESTRING (0 0, 10 5)'
        assert SpatialiteSqlBuilder._wkt_bounds_in_target_crs(builder, wkt, 2154, 2154) == (0.0, 0.0, 10.0, 5.0)
        # a reprojected box needs the host's geometry library: no prefilter rather than a wrong one
        assert SpatialiteSqlBuilder._wkt_bounds_in_target_crs(builder, wkt, 4326, 2154) is None

    def test_no_json1_by_default(self):
        assert SpatialiteSqlBuilder._json1_available(_Builder({})) is False

    def test_curves_get_no_prefilter_box(self):
        builder = _Builder({})
        assert builder._source_bbox('CIRCULARSTRING (0 0, 1 1, 2 0)', 2154, 2154, None) is None
