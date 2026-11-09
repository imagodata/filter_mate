# -*- coding: utf-8 -*-
"""
Guards of the layer-change path on the dock, run on the real methods.

- An expression echo during a layer change arms nothing, and a change armed
  on the previous layer does not land on the new one.
- The buffer validation has its own call: it used to run only as a side
  effect of the debounced replay these guards removed.
- The reattach after a subset change leaves a picker taken by a layer change
  where it is.
- QgsFeaturePickerWidget keeps its feature id across setLayer(): it has to be
  cleared with FID_NULL (the real widget is exercised by the dock smoke test).
"""
import ast
import logging
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]
_DOCK = _ROOT / "filter_mate_dockwidget.py"
_WIDGETS = _ROOT / "ui" / "widgets" / "custom_widgets.py"


def _dock_method_node(name):
    tree = ast.parse(_DOCK.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body
               if isinstance(node, ast.ClassDef) and node.name == "FilterMateDockWidget")
    return next(node for node in cls.body
                if isinstance(node, ast.FunctionDef) and node.name == name)


def _bound(name, instance, **namespace):
    namespace.setdefault("logger", logging.getLogger("test_layer_change_guards"))
    exec(compile(ast.Module(body=[_dock_method_node(name)], type_ignores=[]), str(_DOCK), "exec"), namespace)
    return types.MethodType(namespace[name], instance)


def _expression_dock(**attrs):
    return types.SimpleNamespace(_pending_expression_change=None, _set_expression_loading_state=MagicMock(),
                                 _expression_debounce_timer=MagicMock(), **attrs)


def test_an_echo_during_a_layer_change_arms_nothing():
    dock = _expression_dock(_updating_current_layer=True)
    _bound("_schedule_expression_change", dock)("single_selection", "")
    assert dock._pending_expression_change is None
    dock._expression_debounce_timer.start.assert_not_called()


def test_a_field_change_outside_a_layer_change_is_debounced():
    dock = _expression_dock(_updating_current_layer=False)
    _bound("_schedule_expression_change", dock)("single_selection", "name")
    assert dock._pending_expression_change == ("single_selection", "name")
    dock._expression_debounce_timer.start.assert_called_once()


def test_a_pending_change_is_cancelled():
    dock = _expression_dock()
    dock._pending_expression_change = ("single_selection", "field_of_a")
    _bound("_cancel_pending_expression_change", dock)()
    assert dock._pending_expression_change is None
    dock._expression_debounce_timer.stop.assert_called_once()
    dock._set_expression_loading_state.assert_called_once_with(False)


def test_nothing_pending_nothing_to_cancel():
    dock = _expression_dock()
    _bound("_cancel_pending_expression_change", dock)()
    dock._set_expression_loading_state.assert_not_called()


def _lines_of_calls(method_name, attr):
    return [node.lineno for node in ast.walk(_dock_method_node(method_name))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == attr]


def test_a_layer_change_cancels_once_validated_and_validates_the_buffer():
    prepare = _lines_of_calls("current_layer_changed", "_validate_and_prepare_layer")
    cancel = _lines_of_calls("current_layer_changed", "_cancel_pending_expression_change")
    validation = _lines_of_calls("current_layer_changed", "_update_buffer_validation")
    reload_widgets = _lines_of_calls("current_layer_changed", "_reload_exploration_widgets")
    assert prepare and cancel and validation and reload_widgets
    # A refused change leaves the current layer in place, and its pending change with it.
    assert prepare[0] < cancel[0] < reload_widgets[0] < validation[0]


class _Layer:
    def isValid(self):
        return True


def _subset_harness(connection):
    timers = []
    picker = MagicMock()
    picker.layer.return_value = connection
    dock = types.SimpleNamespace(_feature_picker_layer_connection=connection,
                                 mFeaturePickerWidget_exploring_single_selection=picker)
    handler = _bound("_on_feature_picker_subset_changed", dock, is_sip_deleted=lambda layer: False,
                     QTimer=types.SimpleNamespace(singleShot=lambda delay, call: timers.append(call)))
    return dock, picker, handler, timers


def test_the_reattach_puts_the_picker_back_on_its_layer():
    layer = _Layer()
    _dock, picker, handler, timers = _subset_harness(layer)
    handler()
    picker.setLayer.assert_called_once_with(None)
    timers[0]()
    assert picker.setLayer.call_args_list[-1].args == (layer,)


def test_the_reattach_leaves_a_picker_taken_by_a_layer_change():
    dock, picker, handler, timers = _subset_harness(_Layer())
    handler()
    dock._feature_picker_layer_connection = _Layer()  # the layer change moved it
    picker.setLayer.reset_mock()
    timers[0]()
    picker.setLayer.assert_not_called()


def _clear_function():
    tree = ast.parse(_WIDGETS.read_text(encoding="utf-8"))
    body = [node for node in tree.body
            if (isinstance(node, ast.FunctionDef) and node.name == "clear_feature_picker_feature")
            or (isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "_FID_NULL")]
    namespace = {"logger": logging.getLogger("test_layer_change_guards")}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(_WIDGETS), "exec"), namespace)
    return namespace["clear_feature_picker_feature"]


def test_the_picker_is_cleared_with_fid_null():
    picker = MagicMock()
    _clear_function()(picker)
    picker.setFeature.assert_called_once_with(-9223372036854775808)


def test_clearing_a_deleted_picker_is_no_error():
    picker = MagicMock()
    picker.setFeature.side_effect = RuntimeError("wrapped C/C++ object has been deleted")
    _clear_function()(picker)
