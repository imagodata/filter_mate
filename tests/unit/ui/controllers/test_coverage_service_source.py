# -*- coding: utf-8 -*-
"""A web service source of raster / point cloud targets is never read on the GUI thread (review of #193, M5).

EXPLORING reads the selection of a service in a task and the Filter waits
for it: when it is not there, the coverage targets are skipped with their
message, the service is not read again here.
"""
import ast
import sys
import types
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

_MODULE = Path(__file__).resolve().parents[4] / "ui" / "controllers" / "coverage_mode_controller.py"


class Feature:
    def __init__(self, fid, geometry=False):
        self._fid, self._geometry = fid, geometry

    def id(self):
        return self._fid

    def hasGeometry(self):
        return self._geometry


def _method(monkeypatch, cheap):
    core = types.ModuleType('qgis.core')
    core.QgsFeature = Feature
    core.QgsExpression = MagicMock()
    core.QgsFeatureRequest = MagicMock()
    monkeypatch.setitem(sys.modules, 'qgis.core', core)
    probe = types.ModuleType('filter_mate.adapters.qgis.source_capability_probe')
    probe.counts_cheaply = lambda layer: cheap
    monkeypatch.setitem(sys.modules, probe.__name__, probe)
    tree = ast.parse(_MODULE.read_text(encoding="utf-8"))
    node = next(node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name == '_vector_source_features')
    namespace = {'__name__': 'filter_mate.ui.controllers.coverage_mode_controller',
                 '__package__': 'filter_mate.ui.controllers', 'logger': MagicMock(), 'MAX_SOURCE_FEATURES': 100,
                 'Any': object}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(_MODULE), 'exec'), namespace)
    return namespace['_vector_source_features']


@pytest.mark.parametrize('features,expression', [([], '"id" > 3'), ([Feature(4)], '')])
def test_a_service_source_without_read_geometries_is_not_read_again(monkeypatch, features, expression):
    method = _method(monkeypatch, cheap=False)
    source = MagicMock()
    controller = SimpleNamespace(dockwidget=SimpleNamespace(get_current_features=lambda: (features, expression)))
    assert MethodType(method, controller)(source) == []
    source.getFeatures.assert_not_called()


def test_a_local_source_still_reloads_its_selection(monkeypatch):
    method = _method(monkeypatch, cheap=True)
    source = MagicMock()
    source.getFeatures.return_value = [Feature(4, geometry=True)]
    controller = SimpleNamespace(dockwidget=SimpleNamespace(get_current_features=lambda: ([Feature(4)], '')))
    assert [feature.id() for feature in MethodType(method, controller)(source)] == [4]
    source.getFeatures.assert_called_once()
