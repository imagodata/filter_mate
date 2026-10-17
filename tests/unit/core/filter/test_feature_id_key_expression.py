# -*- coding: utf-8 -*-
"""
Source-layer key list of the selected features, keyed by the QGIS feature id (2026-10-17).

A layer without a unique key field is registered with the pseudo key 'fid'
(core.domain.stable_key). AttributeFilterExecutor.build_feature_id_expression
read ``feature['fid']`` (KeyError on a Shapefile / memory layer); it now uses
the feature ids, ``$id`` for the providers whose subset is a QGIS expression,
and no key list at all on a web service (its feature ids mean nothing to the
server). The method is extracted with ast (the module needs the plugin package).
"""
import ast
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import List, Optional

import pytest

pytestmark = pytest.mark.unit

_PATH = Path(__file__).resolve().parents[4] / "core" / "tasks" / "executors" / "attribute_filter_executor.py"


def _method():
    tree = ast.parse(_PATH.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "AttributeFilterExecutor")
    node = next(item for item in cls.body
                if isinstance(item, ast.FunctionDef) and item.name == "build_feature_id_expression")
    namespace = {"__name__": "core.tasks.executors._fm_test_fid_key", "__package__": "core.tasks.executors",
                 "logger": logging.getLogger("fm.test.fid_key"), "PROVIDER_POSTGRES": "postgresql",
                 "List": List, "Optional": Optional, "QgsFeature": object}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(_PATH), "exec"), namespace)
    return namespace["build_feature_id_expression"]


BUILD = _method()


class _Feature:
    def __init__(self, fid, attributes=None):
        self._fid, self._attributes = fid, attributes or {}

    def id(self):
        return self._fid

    def __getitem__(self, name):
        return self._attributes[name]


def _executor(provider, source, provider_type, field_names, primary_key="fid"):
    layer = SimpleNamespace(providerType=lambda: provider, source=lambda: source, name=lambda: "communes")
    return SimpleNamespace(layer=layer, provider_type=provider_type, primary_key=primary_key, table_name=None,
                           old_subset=None, combine_operator=None, field_names=list(field_names))


def test_shapefile_without_key_lists_its_feature_ids():
    executor = _executor("ogr", "/data/communes.shp", "ogr", ["nom", "population"])
    assert BUILD(executor, [_Feature(4), _Feature(9)], is_numeric=True) == "fid IN (4, 9)"


def test_memory_layer_without_key_uses_dollar_id():
    executor = _executor("memory", "Point?crs=EPSG:2154", "memory", ["nom"])
    assert BUILD(executor, [_Feature(1), _Feature(2)], is_numeric=True) == "$id IN (1, 2)"


def test_web_service_without_key_gets_no_key_list():
    executor = _executor("WFS", "typename='x' url='https://data.geopf.fr/wfs/ows'", "ogr", ["nom", "population"])
    assert BUILD(executor, [_Feature(1)], is_numeric=True) is None


def test_real_key_field_keeps_its_values():
    executor = _executor("ogr", "/data/communes.shp", "ogr", ["nom", "insee"], primary_key="insee")
    features = [_Feature(1, {"insee": "01001"}), _Feature(2, {"insee": "L'Isle"})]
    assert BUILD(executor, features, is_numeric=False) == "\"insee\" IN ('01001', 'L''Isle')"
