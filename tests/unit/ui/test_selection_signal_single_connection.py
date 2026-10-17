# -*- coding: utf-8 -*-
"""
2026-10-17: the current layer's selectionChanged is connected to the dock once, whatever the path.

At each layer change the dock disconnected the previous layer once, the layer
sync controller connected the new one unconditionally and the exploring reload
disconnected once and connected again; the dock's own fallback and the
coverage controller did the same. A duplicate survived each layer change and
the previous layer kept a connection: its selection drove the panel of the
new current layer. The methods are extracted with ast, the plugin modules
are never imported.
"""
import ast
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]


class _Signal:
    """A Qt signal: one entry per connect(), disconnect(slot) removes one or raises TypeError."""

    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def disconnect(self, slot):
        if slot not in self.slots:
            raise TypeError("disconnect() failed between 'selectionChanged' and 'on_layer_selection_changed'")
        self.slots.remove(slot)


class _Layer:
    def __init__(self, layer_id):
        self._id = layer_id
        self.selectionChanged = _Signal()

    def id(self):
        return self._id

    def name(self):
        return self._id

    def isValid(self):
        return True


class _Raster:
    def id(self):
        return "dem"

    def isValid(self):
        return True


def _methods(relative, class_name, names, namespace):
    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(methods) == len(names)
    holder = ast.ClassDef(name="_Holder", bases=[], keywords=[], body=methods, decorator_list=[])
    exec(compile(ast.fix_missing_locations(ast.Module(body=[holder], type_ignores=[])), relative, "exec"), namespace)
    return namespace["_Holder"]


class _Dock(_methods("filter_mate_dockwidget.py", "FilterMateDockWidget",
                     ["_ensure_layer_signals_connected", "_disconnect_layer_selection_signal"],
                     {"QgsVectorLayer": _Layer, "logger": MagicMock(), "_MAX_SELECTION_CONNECTIONS": 32})):
    def __init__(self):
        self.current_layer = None
        self.current_layer_selection_connection = None

    def on_layer_selection_changed(self, selected, deselected, clear_and_select):
        pass


_LayerSync = _methods("ui/controllers/layer_sync_controller.py", "LayerSyncController",
                      ["_connect_layer_selection_signal"], {"logger": MagicMock()})


def _coverage_disconnect():
    tree = ast.parse((ROOT / "ui/controllers/coverage_mode_controller.py").read_text(encoding="utf-8"))
    same = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_same_layer")
    namespace = {"logger": MagicMock(), "Any": object}
    exec(compile(ast.Module(body=[same], type_ignores=[]), "coverage_mode_controller.py", "exec"), namespace)
    holder = _methods("ui/controllers/coverage_mode_controller.py", "CoverageModeController",
                      ["_disconnect_previous_vector_selection"], namespace)
    return holder._disconnect_previous_vector_selection


def _connections(dock, layer):
    return layer.selectionChanged.slots.count(dock.on_layer_selection_changed)


def _change_layer(dock, layer, reload_first=True):
    """What a layer change does: the dock's step 1, then the exploring reload (which logged
    "selectionChanged NOT connected ... reconnected") and the layer sync, in either order."""
    if dock.current_layer is not None:
        dock._disconnect_layer_selection_signal(dock.current_layer)
        dock.current_layer_selection_connection = None
    dock.current_layer = layer
    sync = _LayerSync()
    sync.dockwidget = dock
    if reload_first:
        dock._ensure_layer_signals_connected(layer)
        sync._connect_layer_selection_signal()
    else:
        sync._connect_layer_selection_signal()
        dock._ensure_layer_signals_connected(layer)


@pytest.mark.parametrize("reload_first", [True, False])
def test_three_layer_changes_leave_one_connection(reload_first):
    dock = _Dock()
    zones, roads, rivers = _Layer("zones"), _Layer("roads"), _Layer("rivers")
    for layer in (zones, roads, rivers):
        _change_layer(dock, layer, reload_first)
    assert _connections(dock, rivers) == 1
    assert _connections(dock, zones) == 0 and _connections(dock, roads) == 0  # nothing left behind
    assert dock.current_layer_selection_connection is True


def test_back_to_a_layer_still_one_connection():
    dock = _Dock()
    zones, roads = _Layer("zones"), _Layer("roads")
    for layer in (zones, roads, zones, zones):
        _change_layer(dock, layer)
    assert _connections(dock, zones) == 1 and _connections(dock, roads) == 0


def test_duplicates_are_all_removed():
    dock = _Dock()
    zones = _Layer("zones")
    for _ in range(3):
        zones.selectionChanged.connect(dock.on_layer_selection_changed)
    zones.selectionChanged.connect(print)  # another receiver stays
    dock._ensure_layer_signals_connected(zones)
    assert _connections(dock, zones) == 1 and print in zones.selectionChanged.slots
    dock._disconnect_layer_selection_signal(zones)
    assert _connections(dock, zones) == 0 and print in zones.selectionChanged.slots


def test_a_raster_has_no_selection_to_connect():
    dock = _Dock()
    assert dock._ensure_layer_signals_connected(_Raster()) is False
    dock._disconnect_layer_selection_signal(_Raster())  # no selectionChanged: nothing raised


def test_a_deleted_layer_stops_the_disconnect_loop():
    dock = _Dock()
    layer = MagicMock()
    layer.selectionChanged.disconnect.side_effect = RuntimeError("wrapped C/C++ object has been deleted")
    dock._disconnect_layer_selection_signal(layer)
    assert layer.selectionChanged.disconnect.call_count == 1


def test_the_coverage_controller_disconnects_every_connection_whatever_the_flag():
    disconnect = _coverage_disconnect()
    dock = _Dock()
    zones, dem = _Layer("zones"), _Layer("dem")
    zones.selectionChanged.connect(dock.on_layer_selection_changed)
    zones.selectionChanged.connect(dock.on_layer_selection_changed)
    dock.current_layer = zones
    dock.current_layer_selection_connection = None  # the flag lied: connections were there
    disconnect(dock, dem)
    assert _connections(dock, zones) == 0
