# -*- coding: utf-8 -*-
"""A buffer given by an expression on a PostgreSQL source of more than 10,000 features.

2026-11-12: above 10,000 source features (or an unknown count),
prepare_postgresql_source_geom named
a materialized view "<schema>"."fm_temp_mv_<session>_<table>_buffer_expr_dump"
instead of the source table. Broken three ways:

- nothing created it (the orchestrator read a ``buffer_expression`` key that no
  task parameter holds, and a buffer expression read before its initialisation);
- once created it would have held the OLD subset of the source (the new one is
  only queued while the task runs);
- the distant filter takes the table and geometry column of that reference and
  applies the buffer expression and the source selection itself
  (``__source."radius"``, ``__source."id" IN ...``): the view, a ST_Union of the
  buffers, has neither column, and would have been buffered twice.

The buffer expression is now applied as for a smaller source: the reference
names the source table, the distant filter buffers each selected row (through
its pre-computed buffer table when it has a connection).
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

from filtermate_core.sql.postgresql.expression_builder import PostgreSQLSqlBuilder

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[5]
_PKG = "fmtest_buffer_expr_large"
_PG_DIR = _ROOT / "adapters" / "backends" / "postgresql"


def _package(name, path=None):
    module = types.ModuleType(name)
    module.__path__ = [str(path)] if path else []
    sys.modules[name] = module
    return module


@pytest.fixture(scope="module")
def executor():
    _package(_PKG, _ROOT)
    _package(f"{_PKG}.adapters", _ROOT / "adapters")
    _package(f"{_PKG}.adapters.backends", _ROOT / "adapters" / "backends")
    _package(f"{_PKG}.adapters.backends.postgresql", _PG_DIR)
    _package(f"{_PKG}.infrastructure", _ROOT / "infrastructure")
    _package(f"{_PKG}.infrastructure.database")
    sql_utils = types.ModuleType(f"{_PKG}.infrastructure.database.sql_utils")
    sql_utils.sanitize_sql_identifier = lambda name: name
    sys.modules[sql_utils.__name__] = sql_utils
    name = f"{_PKG}.adapters.backends.postgresql.filter_executor"
    spec = importlib.util.spec_from_file_location(name, _PG_DIR / "filter_executor.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    yield module
    for key in [key for key in sys.modules if key == _PKG or key.startswith(f"{_PKG}.")]:
        sys.modules.pop(key, None)


def _source_geom(executor, feature_count):
    return executor.prepare_postgresql_source_geom(
        source_table="src", source_schema="ref", source_geom="geom", buffer_expression='"homecount" * 2',
        session_id="s01", mv_schema="filter_mate_temp", source_feature_count=feature_count,
    )


class _Crs:
    def postgisSrid(self):
        return 2154


class _Provider:
    def dataSourceUri(self):
        return ("dbname='gis' host=nowhere.invalid port=1 key='fid' srid=2154 type=MultiPolygon "
                "table=\"public\".\"roads\" (geom) sql=")

    def crs(self):
        return _Crs()

    def geometryColumn(self):
        return ''


class _Layer:
    def dataProvider(self):
        return _Provider()

    def crs(self):
        return _Crs()

    def name(self):
        return 'roads'


class _Builder(PostgreSQLSqlBuilder):
    def supports_layer(self, layer):
        return True

    def apply_filter(self, layer, expression, old_subset=None, combine_operator=None):
        return True


def _distant_filter(source_geom):
    builder = _Builder({'buffer_endcap_style': 'round', 'buffer_segments': 5, 'centroid_mode': 'point_on_surface',
                        'infos': {'layer_crs_authid': 'EPSG:2154'}, 'task': {'session_id': 's01'}})
    props = {'layer': _Layer(), 'layer_name': 'roads', 'layer_schema': 'public',
             'layer_table_name': 'roads', 'layer_geometry_field': 'geom'}
    return builder.build_expression(
        layer_props=props, predicates={'intersects': True}, source_geom=source_geom, buffer_value=None,
        buffer_expression='"homecount" * 2', source_filter='"fid" IN (1, 2)', use_centroids=False,
        source_table_name='src', source_feature_count=500)


@pytest.mark.parametrize("feature_count", [5000, 50000, None])
def test_the_buffer_expression_is_applied_to_the_source_table_whatever_its_size(executor, feature_count):
    geom, view = _source_geom(executor, feature_count)

    assert view is None
    assert '"ref"."src"."geom"' in geom and 'fm_temp_mv' not in geom


def test_the_size_of_the_source_does_not_change_its_reference(executor):
    assert _source_geom(executor, 50000) == _source_geom(executor, 5000)


def test_the_distant_filter_of_a_large_source_reads_the_source_rows(executor):
    sql = _distant_filter(_source_geom(executor, 50000)[0])

    assert 'FROM "ref"."src" AS __source' in sql
    assert 'ST_Buffer(__source."geom", __source."homecount"::numeric * 2' in sql
    assert '("fid" IN (1, 2))' in sql and 'fm_temp_mv' not in sql
    assert sql == _distant_filter(_source_geom(executor, 5000)[0])
