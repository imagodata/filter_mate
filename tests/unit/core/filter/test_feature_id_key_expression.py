# -*- coding: utf-8 -*-
"""
Source-layer key list of the selected features (2026-10-17).

A layer without a unique key field is registered with the pseudo key '$id'
(core.domain.stable_key). AttributeFilterExecutor.build_feature_id_expression
read ``feature['fid']`` (KeyError on a Shapefile / memory layer); it now uses
the feature ids (``fid`` in OGR SQL, ``$id`` for the providers whose subset is
a QGIS expression), refuses a key list on a web service / virtual layer
keyed by feature id and beyond the web-service limit (the refusal is kept in
``last_refusal`` for the message bar), splits Oracle lists by 1000 and writes
QGIS-expression literals where the subset is one. Methods extracted with ast
(the module needs the plugin package).
"""
import ast
import logging
import types
from pathlib import Path
from types import SimpleNamespace
from typing import List, Optional

import pytest

pytestmark = pytest.mark.unit

_PATH = Path(__file__).resolve().parents[4] / "core" / "tasks" / "executors" / "attribute_filter_executor.py"
WFS_URI = "typename='ADMINEXPRESS-COG.LATEST:commune' url='https://data.geopf.fr/wfs/ows'"


def _namespace():
    tree = ast.parse(_PATH.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "AttributeFilterExecutor")
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "translate"]
    nodes += [item for item in cls.body if isinstance(item, ast.FunctionDef)
              and item.name in ("build_feature_id_expression", "_key_list_refusal")]
    namespace = {"__name__": "core.tasks.executors._fm_test_fid_key", "__package__": "core.tasks.executors",
                 "logger": logging.getLogger("fm.test.fid_key"), "PROVIDER_POSTGRES": "postgresql",
                 "List": List, "Optional": Optional, "QgsFeature": object}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(_PATH), "exec"), namespace)
    return namespace


NS = _namespace()


class _Feature:
    def __init__(self, fid, attributes=None):
        self._fid, self._attributes = fid, attributes or {}

    def id(self):
        return self._fid

    def __getitem__(self, name):
        return self._attributes[name]


class _Null:
    def isNull(self):
        return True


def _executor(provider, source, provider_type, field_names, primary_key="$id"):
    layer = SimpleNamespace(providerType=lambda: provider, source=lambda: source, name=lambda: "communes")
    executor = SimpleNamespace(layer=layer, provider_type=provider_type, primary_key=primary_key, table_name=None,
                               old_subset=None, combine_operator=None, field_names=list(field_names))
    executor._key_list_refusal = types.MethodType(NS["_key_list_refusal"], executor)
    return executor


def build(executor, features, is_numeric):
    return NS["build_feature_id_expression"](executor, features, is_numeric=is_numeric)


@pytest.mark.parametrize("primary_key", ["$id", "fid"])
def test_shapefile_without_key_lists_its_feature_ids(primary_key):
    executor = _executor("ogr", "/data/communes.shp", "ogr", ["nom", "population"], primary_key)
    assert build(executor, [_Feature(4), _Feature(9)], is_numeric=True) == "fid IN (4, 9)"


def test_memory_layer_without_key_uses_dollar_id():
    executor = _executor("memory", "Point?crs=EPSG:2154", "memory", ["nom"])
    assert build(executor, [_Feature(1), _Feature(2)], is_numeric=True) == "$id IN (1, 2)"


@pytest.mark.parametrize("provider, source, text", [
    ("WFS", WFS_URI, "web service"),
    ("virtual", "?query=SELECT * FROM t", "virtual layer"),
])
def test_feature_ids_are_refused_where_they_cannot_be_listed(provider, source, text):
    executor = _executor(provider, source, "ogr", ["nom", "population"])
    assert build(executor, [_Feature(1)], is_numeric=True) is None
    assert text in executor.last_refusal


@pytest.mark.parametrize("count, refused", [(500, False), (501, True)])
def test_web_service_key_list_is_bounded(count, refused):
    executor = _executor("WFS", WFS_URI, "ogr", ["cleabs", "population"], "cleabs")
    features = [_Feature(i, {"cleabs": f"COMMUNE_{i}"}) for i in range(count)]
    expression = build(executor, features, is_numeric=False)
    assert (expression is None) is refused
    assert bool(executor.last_refusal) is refused


def test_oracle_lists_are_split_by_1000():
    executor = _executor("oracle", "dbname='x' table=\"A\".\"T\"", "ogr", ["ID"], "ID")
    expression = build(executor, [_Feature(i, {"ID": i}) for i in range(2001)], is_numeric=True)
    assert expression.count('"ID" IN (') == 3 and expression.startswith('("ID" IN (0, 1')


def test_real_key_field_keeps_its_values_and_null_qvariants():
    executor = _executor("ogr", "/data/communes.shp", "ogr", ["nom", "insee"], primary_key="insee")
    features = [_Feature(1, {"insee": "01001"}), _Feature(2, {"insee": "L'Isle"}), _Feature(3, {"insee": _Null()})]
    assert build(executor, features, is_numeric=False) == "\"insee\" IN ('01001', 'L''Isle', NULL)"


def test_memory_text_key_is_a_qgis_expression_literal():
    executor = _executor("memory", "Point?crs=EPSG:2154", "memory", ["nom"], primary_key="nom")
    expression = build(executor, [_Feature(1, {"nom": "b\\c"})], is_numeric=False)
    assert expression == '"nom" IN (' + "'b" + "\\" * 2 + "c')"
