# -*- coding: utf-8 -*-
"""A layer change deferred while the plugin is busy (FilterMateDockWidget._defer_layer_change).

A manual change deferred stays manual, and the same change deferred twice (the pick detector of the combo box applies
a pick the panel did not take) is replayed once; a deferred change gives way to another layer the user picked since
(an automatic one replayed 150 ms later switched the panel back over the pick, QGIS 4.2 dock smoke). The method
is extracted from filter_mate_dockwidget.py with ast, the module itself is never imported.
"""
import ast
import sys
import time
import types
import weakref
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_DOCK = Path(__file__).resolve().parents[2] / "filter_mate_dockwidget.py"


def _method():
    tree = ast.parse(_DOCK.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterMateDockWidget")
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "_defer_layer_change")
    namespace = {"weakref": weakref}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(_DOCK), "exec"), namespace)
    return namespace["_defer_layer_change"]


class _Layer:
    def __init__(self, layer_id):
        self._id = layer_id

    def id(self):
        return self._id


class _Dock:
    """Weak-referenceable stand-in for the dock."""


@pytest.fixture
def dock(monkeypatch):
    timers = []
    layers = {"zones": _Layer("zones"), "dem": _Layer("dem")}
    monkeypatch.setattr(sys.modules["qgis.PyQt.QtCore"], "QTimer",
                        types.SimpleNamespace(singleShot=lambda delay, slot: timers.append(slot)), raising=False)
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsProject",
                        types.SimpleNamespace(instance=lambda: types.SimpleNamespace(mapLayer=layers.get)), raising=False)
    d = _Dock()
    d.layers, d.timers = layers, timers
    d.current_layer = layers["zones"]
    d.current_layer_changed = MagicMock()
    d._defer_layer_change = types.MethodType(_method(), d)
    return d


def _replay(d):
    while d.timers:
        d.timers.pop(0)()


def test_an_automatic_change_is_replayed(dock):
    dock._defer_layer_change(dock.layers["dem"])
    _replay(dock)
    dock.current_layer_changed.assert_called_once_with(dock.layers["dem"], manual_change=False)


def test_a_user_pick_stays_a_manual_change(dock):
    dock._defer_layer_change(dock.layers["dem"], True)
    _replay(dock)
    dock.current_layer_changed.assert_called_once_with(dock.layers["dem"], manual_change=True)


def test_the_same_pick_deferred_twice_is_replayed_once(dock):
    """The combo's handler deferred it, then the pick detector asked again (the panel was on another layer)."""
    dock._defer_layer_change(dock.layers["dem"], True)
    dock._defer_layer_change(dock.layers["dem"], True)
    _replay(dock)
    dock.current_layer_changed.assert_called_once_with(dock.layers["dem"], manual_change=True)
    dock._defer_layer_change(dock.layers["dem"], True)  # replayed: a new deferral is a new change
    _replay(dock)
    assert dock.current_layer_changed.call_count == 2


def test_an_automatic_change_gives_way_to_a_later_pick(dock):
    """A refresh deferred zones; the user picked dem 80 ms later: the replay used to switch back to zones."""
    dock._defer_layer_change(dock.layers["zones"])
    dock._user_layer_pick = (time.perf_counter(), "dem")
    dock.current_layer = dock.layers["dem"]
    _replay(dock)
    dock.current_layer_changed.assert_not_called()


def test_a_pick_not_looked_at_yet_is_looked_at_first(dock):
    """The replay and the key press fall due in one pass of the event loop: the replay runs before the call the
    pick detector posted."""
    dock._defer_layer_change(dock.layers["zones"])
    dock._record_pending_layer_pick = lambda: setattr(dock, "_user_layer_pick", (time.perf_counter(), "dem"))
    _replay(dock)
    dock.current_layer_changed.assert_not_called()


def test_a_pick_before_the_deferral_does_not_cancel_it(dock):
    dock._user_layer_pick = (time.perf_counter() - 5, "dem")
    dock._defer_layer_change(dock.layers["zones"])
    _replay(dock)
    dock.current_layer_changed.assert_called_once_with(dock.layers["zones"], manual_change=False)
