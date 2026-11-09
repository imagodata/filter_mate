# -*- coding: utf-8 -*-
"""
Regression: after a vector layer change the single-selection picker showed
no feature.

Two causes, both on the layer-change path:

1. The link filter of the previous layer survives on the picker.
   ``ExploringController.exploring_link_widgets`` sets a filter expression
   on the single-selection ``QgsFeaturePickerWidget`` (built from the
   multiple-selection features of the current layer, e.g. ``"pk_a" IN
   (...)``). That filter is a property of the widget: ``setLayer()`` does
   not clear it, and ``_reload_exploration_widgets`` never cleared it
   either, so the new layer was fetched through the previous layer's
   filter (unknown field -> empty model). The reload must clear it; the
   link logic re-applies one for the new layer when relevant.

2. ``fieldChanged("")`` during a layer change emptied the stored
   expression. ``_disconnect_layer_signals`` clears the expression
   widgets (``setExpression("")``); the direct ``fieldChanged``
   connection still fires and ``_refresh_feature_pickers_for_field_change``
   wrote the empty value into ``PROJECT_LAYERS`` before its
   "layer change in progress" early-return. While a layer change runs,
   the handler must not write the layer properties at all -- the reload
   step owns them.
"""
import ast
import logging
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = "fm_single_picker_pkg"
_CLEARED = "no feature"


def _extract_method(path, class_name, method_name, namespace):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body
               if isinstance(node, ast.ClassDef) and node.name == class_name)
    method = next(node for node in cls.body
                  if isinstance(node, ast.FunctionDef) and node.name == method_name)
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), "exec"), namespace)
    return namespace[method_name]


class _Layer:
    def __init__(self, layer_id, name):
        self._id, self._name = layer_id, name

    def id(self):
        return self._id

    def name(self):
        return self._name


class _Picker:
    """Stateful stand-in for the QgsFeaturePickerWidget of single selection."""

    def __init__(self, layer, filter_expression):
        self._layer = layer
        self._filter = filter_expression
        self.set_layer_calls = []
        self.set_filter_calls = []
        self.set_feature_calls = []
        self.display_expression = None

    def feature(self):
        return types.SimpleNamespace(isValid=lambda: False, id=lambda: None)

    def layer(self):
        return self._layer

    def setLayer(self, layer):
        self.set_layer_calls.append(layer)
        self._layer = layer

    def setFilterExpression(self, expression):
        self.set_filter_calls.append(expression)
        self._filter = expression

    def filterExpression(self):
        return self._filter

    def setFeature(self, fid):
        self.set_feature_calls.append(fid)

    def setDisplayExpression(self, expression):
        self.display_expression = expression

    def setFetchGeometry(self, value):
        pass

    def setShowBrowserButtons(self, value):
        pass

    def setAllowNull(self, value):
        pass

    def update(self):
        pass

    def repaint(self):
        pass


def _expression_widget():
    widget = MagicMock()
    widget.expression.return_value = "name_b"
    return widget


def _button():
    button = MagicMock()
    button.clicked.disconnect.side_effect = TypeError("not connected")
    return button


@pytest.fixture
def reload_widgets(monkeypatch):
    """ExploringController._reload_exploration_widgets bound to a fake dock.

    The picker still holds the link filter of the previous layer (pk_a),
    the new layer (B) is being reloaded.
    """
    for name in (PACKAGE, f"{PACKAGE}.ui", f"{PACKAGE}.ui.controllers",
                 f"{PACKAGE}.infrastructure", "qgis", "qgis.core"):
        package = types.ModuleType(name)
        package.__path__ = []
        monkeypatch.setitem(sys.modules, name, package)

    utils = types.ModuleType(f"{PACKAGE}.infrastructure.utils")
    utils.get_best_display_field = lambda layer: "name_b"
    utils.is_layer_valid = lambda layer: True
    monkeypatch.setitem(sys.modules, utils.__name__, utils)

    class _QgsExpression:
        def __init__(self, expression):
            self._expression = expression or ""

        def isField(self):
            return True

        def isValid(self):
            return bool(self._expression)

    sys.modules["qgis.core"].QgsExpression = _QgsExpression

    layer_a, layer_b = _Layer("a", "A"), _Layer("b", "B")
    picker = _Picker(layer_a, '"pk_a" IN (1, 2, 3)')
    multiple = MagicMock()
    multiple.checkedItems.return_value = []

    layer_props = {
        "infos": {"primary_key_name": "id_b"},
        "exploring": {
            "single_selection_expression": "name_b",
            "multiple_selection_expression": "name_b",
            "custom_selection_expression": "name_b",
        },
    }
    dock = types.SimpleNamespace(
        widgets_initialized=True,
        widgets={"EXPLORING": {
            "SINGLE_SELECTION_FEATURES": {"WIDGET": picker},
            "MULTIPLE_SELECTION_FEATURES": {"WIDGET": multiple},
            "SINGLE_SELECTION_EXPRESSION": {"WIDGET": _expression_widget()},
            "MULTIPLE_SELECTION_EXPRESSION": {"WIDGET": _expression_widget()},
            "CUSTOM_SELECTION_EXPRESSION": {"WIDGET": _expression_widget()},
        }},
        PROJECT_LAYERS={"b": layer_props},
        manageSignal=MagicMock(),
        settingLayerVariable=MagicMock(),
        pushButton_exploring_identify=_button(),
        pushButton_exploring_zoom=_button(),
        pushButton_exploring_reset_layer_properties=_button(),
        exploring_identify_clicked=MagicMock(),
        exploring_zoom_clicked=MagicMock(),
        resetLayerVariableEvent=MagicMock(),
        _connect_feature_picker_layer_deletion=MagicMock(),
        _ensure_layer_signals_connected=MagicMock(),
        _setup_expression_widget_direct_connections=MagicMock(),
    )
    controller = types.SimpleNamespace(_dockwidget=dock)
    method = _extract_method(
        ROOT / "ui" / "controllers" / "exploring_controller.py",
        "ExploringController", "_reload_exploration_widgets",
        {"__package__": f"{PACKAGE}.ui.controllers",
         "logger": logging.getLogger("test_single_picker"),
         "apply_feature_picker_fetch_limit": lambda widget: None,
         "clear_feature_picker_feature": lambda widget: widget.setFeature(_CLEARED)})
    controller.reload = types.MethodType(method, controller)
    return types.SimpleNamespace(controller=controller, picker=picker,
                                 layer_b=layer_b, layer_props=layer_props)


@pytest.fixture
def reload_minimal_props(monkeypatch):
    """Same reload harness, but the layer properties carry no "exploring"
    section yet and the layer is absent from PROJECT_LAYERS (a layer
    caught mid-registration): the reload must fall back to the best
    field instead of dying on a KeyError with the picker left behind."""
    for name in (PACKAGE, f"{PACKAGE}.ui", f"{PACKAGE}.ui.controllers",
                 f"{PACKAGE}.infrastructure", "qgis", "qgis.core"):
        package = types.ModuleType(name)
        package.__path__ = []
        monkeypatch.setitem(sys.modules, name, package)

    utils = types.ModuleType(f"{PACKAGE}.infrastructure.utils")
    utils.get_best_display_field = lambda layer: "name_b"
    utils.is_layer_valid = lambda layer: True
    monkeypatch.setitem(sys.modules, utils.__name__, utils)

    class _QgsExpression:
        def __init__(self, expression):
            self._expression = expression or ""

        def isField(self):
            return True

        def isValid(self):
            return bool(self._expression)

    sys.modules["qgis.core"].QgsExpression = _QgsExpression

    layer_a, layer_b = _Layer("a", "A"), _Layer("b", "B")
    picker = _Picker(layer_a, "")
    multiple = MagicMock()
    multiple.checkedItems.return_value = []

    layer_props = {"infos": {"primary_key_name": "id_b"}}
    dock = types.SimpleNamespace(
        widgets_initialized=True,
        widgets={"EXPLORING": {
            "SINGLE_SELECTION_FEATURES": {"WIDGET": picker},
            "MULTIPLE_SELECTION_FEATURES": {"WIDGET": multiple},
            "SINGLE_SELECTION_EXPRESSION": {"WIDGET": _expression_widget()},
            "MULTIPLE_SELECTION_EXPRESSION": {"WIDGET": _expression_widget()},
            "CUSTOM_SELECTION_EXPRESSION": {"WIDGET": _expression_widget()},
        }},
        PROJECT_LAYERS={},
        manageSignal=MagicMock(),
        settingLayerVariable=MagicMock(),
        pushButton_exploring_identify=_button(),
        pushButton_exploring_zoom=_button(),
        pushButton_exploring_reset_layer_properties=_button(),
        exploring_identify_clicked=MagicMock(),
        exploring_zoom_clicked=MagicMock(),
        resetLayerVariableEvent=MagicMock(),
        _connect_feature_picker_layer_deletion=MagicMock(),
        _ensure_layer_signals_connected=MagicMock(),
        _setup_expression_widget_direct_connections=MagicMock(),
    )
    controller = types.SimpleNamespace(_dockwidget=dock)
    method = _extract_method(
        ROOT / "ui" / "controllers" / "exploring_controller.py",
        "ExploringController", "_reload_exploration_widgets",
        {"__package__": f"{PACKAGE}.ui.controllers",
         "logger": logging.getLogger("test_single_picker"),
         "apply_feature_picker_fetch_limit": lambda widget: None,
         "clear_feature_picker_feature": lambda widget: widget.setFeature(_CLEARED)})
    controller.reload = types.MethodType(method, controller)
    return types.SimpleNamespace(controller=controller, picker=picker,
                                 layer_b=layer_b, layer_props=layer_props)


def test_reload_with_minimal_props_falls_back_to_the_best_field(reload_minimal_props):
    env = reload_minimal_props
    env.controller.reload(env.layer_b, env.layer_props)
    assert env.picker.set_layer_calls[-1] is env.layer_b
    assert env.picker.display_expression == "name_b"
    assert env.layer_props["exploring"]["single_selection_expression"] == "name_b"
    assert env.layer_props["exploring"]["multiple_selection_expression"] == "name_b"


def test_reload_clears_the_previous_layers_filter_from_the_single_picker(reload_widgets):
    env = reload_widgets
    env.controller.reload(env.layer_b, env.layer_props)
    # The reload did run on the new layer...
    assert env.picker.set_layer_calls[-1] is env.layer_b
    assert env.picker.display_expression == "name_b"
    # ...and the filter inherited from layer A is gone, so the model
    # fetches the features of B instead of none.
    assert env.picker.set_filter_calls == [""]
    assert env.picker.filterExpression() == ""


def test_field_change_during_a_layer_change_keeps_the_stored_expression():
    layer_props = {"exploring": {"single_selection_expression": "name_b"}}
    dock = types.SimpleNamespace(
        current_layer=_Layer("b", "B"),
        PROJECT_LAYERS={"b": layer_props},
        _updating_current_layer=True,
        _is_layer_valid=lambda: True,
    )
    method = _extract_method(
        ROOT / "filter_mate_dockwidget.py",
        "FilterMateDockWidget", "_refresh_feature_pickers_for_field_change",
        {"logger": logging.getLogger("test_single_picker")})
    dock.refresh = types.MethodType(method, dock)
    # What _disconnect_layer_signals provokes on every layer change:
    # setExpression("") on the widget, then this handler with "".
    dock.refresh("single_selection", "")
    assert layer_props["exploring"]["single_selection_expression"] == "name_b"


def _picks(env, fid):
    """The picker holds a feature (it survives setLayer, as the real widget does)."""
    env.picker.feature = lambda: types.SimpleNamespace(isValid=lambda: True, id=lambda: fid)


def test_a_feature_of_the_previous_layer_is_not_carried_over(reload_widgets):
    """The picker keeps its fid across setLayer: fid 3 of layer A showed the
    unrelated fid 3 of layer B as selected, and it was filtered on."""
    env = reload_widgets
    _picks(env, 3)
    env.controller.reload(env.layer_b, env.layer_props)
    assert env.picker.set_feature_calls == [_CLEARED]


def test_a_reload_on_the_same_layer_keeps_the_feature(reload_widgets):
    env = reload_widgets
    env.picker._layer = env.layer_b
    _picks(env, 3)
    env.controller.reload(env.layer_b, env.layer_props)
    assert env.picker.set_feature_calls == [3]


def test_a_picker_detached_from_the_previous_layer_is_not_restored_on_the_new_one(reload_widgets):
    """Subset change window: setLayer(None), the feature stays, the connection names its layer."""
    env = reload_widgets
    env.picker._layer = None
    env.controller._dockwidget._feature_picker_layer_connection = _Layer("a", "A")
    _picks(env, 3)
    env.controller.reload(env.layer_b, env.layer_props)
    assert env.picker.set_feature_calls == [_CLEARED]


def test_a_picker_detached_from_the_same_layer_is_restored(reload_widgets):
    env = reload_widgets
    env.picker._layer = None
    env.controller._dockwidget._feature_picker_layer_connection = env.layer_b
    _picks(env, 3)
    env.controller.reload(env.layer_b, env.layer_props)
    assert env.picker.set_feature_calls == [3]


def test_a_feature_of_unknown_origin_is_not_restored(reload_widgets):
    env = reload_widgets
    env.picker._layer = None
    _picks(env, 3)
    env.controller.reload(env.layer_b, env.layer_props)
    assert env.picker.set_feature_calls == [_CLEARED]


def test_no_feature_means_no_call_on_the_picker(reload_widgets):
    env = reload_widgets
    env.controller.reload(env.layer_b, env.layer_props)
    assert env.picker.set_feature_calls == []
