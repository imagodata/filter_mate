# -*- coding: utf-8 -*-
"""
A dock opened on a raster or web active layer applied no layer.

The registration refreshes the active layer only when it is a vector one. Otherwise
the combo box showed its first layer, but the panel had no current layer, no layer card,
and no Zone or "more" button on the rail (built by ``show_vector``).
"""
import ast
import types
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_DOCK = Path(__file__).resolve().parents[2] / "filter_mate_dockwidget.py"


def _method(name):
    tree = ast.parse(_DOCK.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body
               if isinstance(node, ast.ClassDef) and node.name == "FilterMateDockWidget")
    method = next(node for node in cls.body
                  if isinstance(node, ast.FunctionDef) and node.name == name)
    namespace = {}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(_DOCK), "exec"), namespace)
    return namespace[name]


show = _method("_show_combo_layer_when_none")


def _dock(current=None, shown="first", awaited=None):
    applied = []
    return types.SimpleNamespace(
        current_layer=current, _awaited_vector_pick=awaited, applied=applied,
        comboBox_filtering_current_layer=types.SimpleNamespace(currentLayer=lambda: shown),
        current_layer_changed=applied.append)


def test_no_current_layer_applies_the_layer_of_the_combo_box():
    dock = _dock()
    show(dock)
    assert dock.applied == ["first"]


def test_a_current_layer_stays():
    dock = _dock(current="zones")
    show(dock)
    assert dock.applied == []


def test_a_layer_waiting_for_its_registration_is_not_replaced():
    dock = _dock(awaited=("b", 1.0, True))
    show(dock)
    assert dock.applied == []


def test_an_empty_combo_box_applies_nothing():
    dock = _dock(shown=None)
    show(dock)
    assert dock.applied == []
