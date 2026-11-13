# -*- coding: utf-8 -*-
"""The custom selection of EXPLORING reads the project and layer variables (2026-11-12).

``FilterMateDockWidget.exploring_custom_selection`` read a local source with a
bare ``QgsFeatureRequest().setFilterExpression(expression)``: a request has no
expression context of its own, so ``"id" > @seuil`` read the variable as NULL
and selected nothing, while the filter task (which evaluates in the global,
project and layer scopes) filtered. The method is extracted with ast and run
against recording fakes.
"""
import ast
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

_DOCK = Path(__file__).resolve().parents[3] / "filter_mate_dockwidget.py"


class Request:
    def __init__(self):
        self.expression = None
        self.context = None

    def setFilterExpression(self, expression):
        self.expression = expression
        return self

    def setExpressionContext(self, context):
        self.context = context
        return self


class Layer:
    def __init__(self):
        self.requests = []

    def id(self):
        return 'routes'

    def getFeatures(self, request):
        self.requests.append(request)
        # QGIS: the variable is NULL without the layer's context, "id" > NULL keeps nothing
        return iter(['feature'] if request.context is not None else [])


@pytest.fixture
def method(monkeypatch):
    core = types.ModuleType('qgis.core')
    core.QgsFeatureRequest = Request
    core.QgsExpressionContextUtils = SimpleNamespace(globalProjectLayerScopes=lambda layer: ('global', 'project',
                                                                                             layer.id()))
    core.QgsExpressionContext = lambda scopes: ('context',) + tuple(scopes)
    monkeypatch.setitem(sys.modules, 'qgis', types.ModuleType('qgis'))
    monkeypatch.setitem(sys.modules, 'qgis.core', core)
    for name, attrs in (('filter_mate', {}), ('filter_mate.infrastructure', {}),
                        ('filter_mate.infrastructure.utils',
                         {'should_skip_expression_for_filtering': lambda expression: (False, '')}),
                        ('filter_mate.adapters', {}), ('filter_mate.adapters.qgis', {}),
                        ('filter_mate.adapters.qgis.source_capability_probe', {'counts_cheaply': lambda layer: True})):
        module = types.ModuleType(name)
        module.__path__ = []
        for key, value in attrs.items():
            setattr(module, key, value)
        monkeypatch.setitem(sys.modules, name, module)
    tree = ast.parse(_DOCK.read_text(encoding='utf-8'))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'FilterMateDockWidget')
    node = next(item for item in cls.body if isinstance(item, ast.FunctionDef)
                and item.name == 'exploring_custom_selection')
    namespace = {'__name__': 'filter_mate.filter_mate_dockwidget', '__package__': 'filter_mate',
                 'logger': SimpleNamespace(debug=lambda *a, **k: None, info=lambda *a, **k: None,
                                           error=lambda *a, **k: None)}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(_DOCK), 'exec'), namespace)
    return namespace['exploring_custom_selection']


def test_the_custom_selection_reads_the_variables_of_the_layer(method):
    layer = Layer()
    dock = SimpleNamespace(
        widgets_initialized=True, current_layer=layer, _exploring_ctrl=None,
        PROJECT_LAYERS={'routes': {'exploring': {'custom_selection_expression': '"id" > @seuil'}}},
        _get_cached_expression_result=lambda layer_id, expression: None,
        _set_cached_expression_result=lambda layer_id, expression, features: None)

    features, expression = method(dock)

    assert features == ['feature'] and expression == '"id" > @seuil'
    assert layer.requests[0].context == ('context', 'global', 'project', 'routes')
