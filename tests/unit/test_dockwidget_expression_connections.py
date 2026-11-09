# -*- coding: utf-8 -*-
"""
2026-11-06 (R5): reconnecting the expression widgets must keep one direct
handler per widget without dropping the other fieldChanged receivers.

``_setup_expression_widget_direct_connections`` runs on every layer
change. It used a bare ``fieldChanged.disconnect()``, which removed every
receiver — including the truncation tooltips connected once by
``_setup_truncation_tooltips``. Only the previous direct handler may be
disconnected, and repeated calls must not stack handlers.
"""
import ast
import logging
import types
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_DOCK = Path(__file__).resolve().parents[2] / "filter_mate_dockwidget.py"

_ATTRS = (
    "mFieldExpressionWidget_exploring_single_selection",
    "mFieldExpressionWidget_exploring_multiple_selection",
    "mFieldExpressionWidget_exploring_custom_selection",
)


class _Signal:
    """Minimal pyqtBoundSignal stand-in; a bare disconnect() fails the test."""

    def __init__(self):
        self.receivers = []

    def connect(self, slot):
        self.receivers.append(slot)

    def disconnect(self, slot=None):
        if slot is None:
            raise AssertionError("bare disconnect() must not be used on fieldChanged")
        try:
            self.receivers.remove(slot)
        except ValueError:
            raise TypeError("not connected") from None

    def emit(self, *args):
        for receiver in list(self.receivers):
            receiver(*args)


def _setup_method():
    tree = ast.parse(_DOCK.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body
               if isinstance(node, ast.ClassDef) and node.name == "FilterMateDockWidget")
    method = next(node for node in cls.body
                  if isinstance(node, ast.FunctionDef)
                  and node.name == "_setup_expression_widget_direct_connections")
    namespace = {"logger": logging.getLogger("test_expression_connections")}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(_DOCK), "exec"), namespace)
    return namespace["_setup_expression_widget_direct_connections"]


@pytest.fixture
def dock():
    widgets = {attr: types.SimpleNamespace(fieldChanged=_Signal()) for attr in _ATTRS}
    tooltip_calls, refresh_calls, schedule_calls = [], [], []
    instance = types.SimpleNamespace(
        _refresh_feature_pickers_for_field_change=lambda group, field: refresh_calls.append((group, field)),
        _schedule_expression_change=lambda group, field: schedule_calls.append((group, field)),
        tooltip_calls=tooltip_calls,
        refresh_calls=refresh_calls,
        schedule_calls=schedule_calls,
    )
    for attr, widget in widgets.items():
        setattr(instance, attr, widget)
    instance.setup = types.MethodType(_setup_method(), instance)
    return instance


def test_other_receivers_survive_the_reconnect(dock):
    for attr in _ATTRS:
        getattr(dock, attr).fieldChanged.connect(
            lambda field, _attr=attr: dock.tooltip_calls.append((_attr, field)))
    dock.setup()
    for attr in _ATTRS:
        getattr(dock, attr).fieldChanged.emit("name")
    assert sorted(dock.tooltip_calls) == sorted((attr, "name") for attr in _ATTRS)


def test_repeated_setup_does_not_stack_handlers(dock):
    dock.setup()
    dock.setup()
    dock.setup()
    for attr in _ATTRS:
        getattr(dock, attr).fieldChanged.emit("name")
    assert len(dock.refresh_calls) == len(_ATTRS)
    assert len(dock.schedule_calls) == len(_ATTRS)
    groups = sorted(group for group, _ in dock.refresh_calls)
    assert groups == ["custom_selection", "multiple_selection", "single_selection"]


def test_missing_widgets_do_not_break_the_others(dock):
    del dock.mFieldExpressionWidget_exploring_multiple_selection
    dock.setup()  # must not raise
    dock.mFieldExpressionWidget_exploring_single_selection.fieldChanged.emit("name")
    assert dock.refresh_calls == [("single_selection", "name")]
