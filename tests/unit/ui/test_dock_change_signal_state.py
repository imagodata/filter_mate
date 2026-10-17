# -*- coding: utf-8 -*-
"""
FilterMateDockWidget.changeSignalState (2026-10-17).

The checkable buttons of _setup_conditional_widget_states carry a second slot on
'toggled'; isSignalConnected() then stayed True after disconnect(func) and the
registry handler was never connected again after the first layer change. Only
these signals track the registry's own handler: the force / direct
reconnections of other widgets keep the "any slot" test (no duplicate handler).

The method is extracted with ast, so the dock module is never imported; the fake
signal behaves like PyQt (disconnect(f) raises TypeError when f is not connected).
"""
import ast
import types
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_DOCK = Path(__file__).resolve().parents[3] / "filter_mate_dockwidget.py"


def _method():
    tree = ast.parse(_DOCK.read_text(encoding="utf-8"))
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == "changeSignalState":
                namespace = {"SignalStateChangeError": type("SignalStateChangeError", (Exception,), {})}
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(_DOCK), "exec"), namespace)
                return namespace["changeSignalState"]
    raise AssertionError("changeSignalState not found")


class FakeSignal:
    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def disconnect(self, slot=None):
        if slot is None:
            self.slots.clear()
            return
        if slot not in self.slots:
            raise TypeError("disconnect() failed between 'toggled' and its slot")
        self.slots.remove(slot)


class FakeButton:
    def __init__(self):
        self.toggled = FakeSignal()

    def isSignalConnected(self, signal):
        return bool(signal.slots)


def _dock(button, conditional):
    dock = types.SimpleNamespace(
        widgets={"FILTERING": {"HAS": {"WIDGET": button}}},
        _layer_tree_view_signal_connected=False,
        getSignal=lambda widget, name: getattr(widget, name),
    )
    if conditional:
        dock._conditional_state_buttons = [button]
    dock.changeSignalState = types.MethodType(_method(), dock)
    return dock


def handler(_checked):
    pass


def conditional_slot(_checked):
    pass


def test_conditional_button_gets_its_handler_back_once():
    button = FakeButton()
    dock = _dock(button, conditional=True)
    assert dock.changeSignalState(["FILTERING", "HAS"], "toggled", handler, "connect") is True
    button.toggled.connect(conditional_slot)  # _setup_conditional_widget_states, after the first connect
    assert dock.changeSignalState(["FILTERING", "HAS"], "toggled", handler, "disconnect") is False
    assert button.toggled.slots == [conditional_slot]
    assert dock.changeSignalState(["FILTERING", "HAS"], "toggled", handler, "connect") is True
    assert dock.changeSignalState(["FILTERING", "HAS"], "toggled", handler, "connect") is True
    assert button.toggled.slots.count(handler) == 1


def test_force_reconnected_widget_keeps_a_single_handler():
    """A global disconnect() then a direct handler (force_reconnect_* pattern): no registry duplicate."""
    button = FakeButton()
    dock = _dock(button, conditional=False)
    dock.changeSignalState(["FILTERING", "HAS"], "toggled", handler, "connect")
    button.toggled.disconnect()

    def direct(_checked):
        pass

    button.toggled.connect(direct)
    dock.changeSignalState(["FILTERING", "HAS"], "toggled", handler, "disconnect")
    dock.changeSignalState(["FILTERING", "HAS"], "toggled", handler, "connect")
    assert button.toggled.slots == [direct]
