# -*- coding: utf-8 -*-
"""
2026-10-17: a layer picked while the dock runs a layer change is applied after it.

Found by the dock smoke test on the QGIS nightly ("a late refresh keeps the layer the
user picked", picked=dem shown=zones) and reproduced by run_lifecycle_check.py: the
start-up safety refresh deferred a layer change of the QGIS active layer, replayed
150 ms later; the user's pick came while that change ran (events are processed during
it) and current_layer_changed dropped it ("Already updating, skipping"). The combo box
showed the picked layer, the panel kept the other one. Methods extracted with ast.
"""
import ast
import types
import weakref
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_DOCK = Path(__file__).resolve().parents[2] / "filter_mate_dockwidget.py"


class _Layer:
    def __init__(self, layer_id):
        self._id = layer_id

    def id(self):
        return self._id

    def name(self):
        return self._id


class _Timer:
    calls = []

    @classmethod
    def singleShot(cls, delay, callback):
        cls.calls.append(callback)


def _dock(layers):
    tree = ast.parse(_DOCK.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterMateDockWidget")
    names = ("current_layer_changed", "_run_layer_change_after_update")
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in names]
    project = types.SimpleNamespace(mapLayer=lambda layer_id: layers.get(layer_id))
    namespace = {"logger": MagicMock(), "QTimer": _Timer, "weakref": weakref, "QgsVectorLayer": _Layer,
                 "QgsProject": types.SimpleNamespace(instance=lambda: project)}
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(_DOCK), "exec"), namespace)

    class Dock:
        pass

    for name in names:
        setattr(Dock, name, namespace[name])
    dock = Dock()
    dock._updating_current_layer = True  # a layer change is running
    dock._filtering_in_progress = dock._plugin_busy = False
    _Timer.calls = []
    return dock


def test_a_pick_during_a_layer_change_runs_after_it():
    layers = {"dem": _Layer("dem"), "pts": _Layer("pts")}
    dock = _dock(layers)
    dock.current_layer_changed(layers["dem"], manual_change=True)  # dropped before
    assert dock._layer_change_after_update[:2] == ("dem", True)

    applied = []
    dock._updating_current_layer = False
    dock.current_layer_changed = lambda layer, manual_change=False: applied.append((layer.id(), manual_change))
    dock._run_layer_change_after_update(layers["pts"])  # the running change (pts) ends
    for callback in _Timer.calls:
        callback()
    assert applied == [("dem", True)]


def test_an_automatic_change_does_not_replace_a_pick():
    layers = {"dem": _Layer("dem"), "pts": _Layer("pts")}
    dock = _dock(layers)
    dock.current_layer_changed(layers["dem"], manual_change=True)
    dock.current_layer_changed(layers["pts"], manual_change=False)
    assert dock._layer_change_after_update[:2] == ("dem", True)


def test_nothing_runs_again_for_the_layer_just_applied():
    layers = {"pts": _Layer("pts")}
    dock = _dock(layers)
    dock.current_layer_changed(layers["pts"], manual_change=False)
    dock._run_layer_change_after_update(layers["pts"])
    assert _Timer.calls == [] and not hasattr(dock, "_layer_change_after_update")


def test_an_automatic_change_gives_way_to_a_later_pick():
    layers = {"dem": _Layer("dem"), "pts": _Layer("pts"), "zones": _Layer("zones")}
    dock = _dock(layers)
    dock.current_layer_changed(layers["zones"], manual_change=False)
    applied = []
    dock._updating_current_layer = False
    dock.current_layer_changed = lambda layer, manual_change=False: applied.append(layer.id())
    dock._run_layer_change_after_update(layers["pts"])
    import time
    dock._user_layer_pick = (time.perf_counter(), "dem")  # the user picked dem after the request
    for callback in _Timer.calls:
        callback()
    assert applied == []


def test_an_older_pick_does_not_cancel_the_request():
    """2026-10-17 review: _user_layer_pick is never reset; a pick made before the request must not win."""
    import time
    layers = {"pts": _Layer("pts"), "zones": _Layer("zones")}
    dock = _dock(layers)
    dock._user_layer_pick = (time.perf_counter(), "dem")  # long before
    dock.current_layer_changed(layers["zones"], manual_change=False)
    applied = []
    dock._updating_current_layer = False
    dock.current_layer_changed = lambda layer, manual_change=False: applied.append(layer.id())
    dock._run_layer_change_after_update(layers["pts"])
    for callback in _Timer.calls:
        callback()
    assert applied == ["zones"]
