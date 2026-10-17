# -*- coding: utf-8 -*-
"""No featureCount() of a web service on the main thread after a filter (2026-10-17).

QGIS counts a WFS / OGC API Features / ArcGIS layer with a request to the
server. The post-filter handler, the canvas refresh and the completion
messages counted the source layer on the main thread; they now show "?".
"""
import importlib
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_PKG = "fm_remote_feature_count_test"


def _load(module_name):
    for name, path in (("", _ROOT), (".adapters", _ROOT / "adapters"), (".infrastructure", _ROOT / "infrastructure"),
                       (".config", _ROOT / "config"), (".core", _ROOT / "core")):
        if _PKG + name not in sys.modules:
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]
            sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.adapters.{module_name}")


class _Layer:
    def __init__(self, provider, source, count=12):
        self._provider, self._source, self._count = provider, source, count
        self.counted = 0

    def id(self):
        return f"{self._provider}-layer"

    def name(self):
        return "communes"

    def providerType(self):
        return self._provider

    def source(self):
        return self._source

    def featureCount(self):
        self.counted += 1
        return self._count


WFS = ("WFS", "typename='ADMINEXPRESS-COG.LATEST:commune' url='https://data.geopf.fr/wfs/ows'")
OAPIF = ("OAPIF", "url='https://example.org/ogcapi' typename='communes'")
MSSQL = ("mssql", "dbname='x' table=\"dbo\".\"communes\" (geom)")


@pytest.mark.parametrize("module_name", ["filter_result_handler", "layer_refresh_manager"])
@pytest.mark.parametrize("provider, source", [WFS, OAPIF, MSSQL])
def test_remote_layers_are_not_counted(module_name, provider, source):
    module = _load(module_name)
    layer = _Layer(provider, source)
    assert module._feature_count_or_none(layer) is None
    assert layer.counted == 0


@pytest.mark.parametrize("module_name", ["filter_result_handler", "layer_refresh_manager"])
def test_local_layers_are_counted(module_name):
    module = _load(module_name)
    layer = _Layer("ogr", "/data/communes.shp", count=1234)
    assert module._feature_count_or_none(layer) == 1234


def test_unknown_count_reads_as_a_question_mark():
    module = _load("filter_result_handler")
    assert module._count_text(None) == "?"
    assert module._count_text(-1) == "?"
    assert module._count_text(12438) == "12,438"
