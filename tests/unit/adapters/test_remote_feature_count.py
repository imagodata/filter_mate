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


@pytest.mark.parametrize("provider, source, expected", [WFS + (-1,), OAPIF + (-1,), ("ogr", "/data/x.shp", 12)])
def test_history_does_not_count_remote_layers(provider, source, expected):
    module = _load("undo_redo_handler")
    layer = _Layer(provider, source)
    assert module._history_count(layer) == expected
    assert layer.counted == (0 if expected == -1 else 1)


def _dock_method(name):
    """A FilterMateDockWidget method extracted with ast, its relative imports in this test package."""
    import ast
    path = _ROOT / "filter_mate_dockwidget.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterMateDockWidget")
    node = next(item for item in cls.body if isinstance(item, ast.FunctionDef) and item.name == name)
    _load("filter_result_handler")  # the test package and its adapters / core
    namespace = {"__name__": f"{_PKG}._dock", "__package__": _PKG, "ASYNC_EXPRESSION_AVAILABLE": True,
                 "QgsRectangle": object, "QgsFeatureRequest": object}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
    return namespace[name]


@pytest.mark.parametrize("provider, source, count, expected", [
    ("WFS", WFS[1], 10, True),          # not counted: async
    ("ogr", "/data/x.shp", -1, True),   # unknown count: a large layer
    ("ogr", "/data/x.shp", 10, False),
    ("ogr", "/data/x.shp", 50000, True),
])
def test_async_expression_for_remote_and_uncounted_layers(provider, source, count, expected):
    method = _dock_method("should_use_async_expression")
    layer = _Layer(provider, source, count=count)
    dock = types.SimpleNamespace(_expression_manager=object(), current_layer=layer, _async_expression_threshold=10000)
    assert method(dock, '"nom" = 1') is expected
    assert layer.counted == (0 if provider == "WFS" else 1)


def test_filtered_extent_of_a_web_service_is_not_scanned():
    method = _dock_method("get_filtered_layer_extent")
    layer = _Layer(*WFS)
    layer.extent = lambda: "provider extent"
    layer.updateExtents = lambda: (_ for _ in ()).throw(AssertionError("updateExtents of a web service"))
    assert method(None, layer) == "provider extent"
    assert layer.counted == 0
