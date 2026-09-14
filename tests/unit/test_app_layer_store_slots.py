# -*- coding: utf-8 -*-
"""
2026-09-14: the app disconnects only its own three layer-store slots when a
project is switched, never every receiver of the QgsMapLayerStore signals.
Methods extracted from filter_mate_app.py with ast (see test_app_canvas_freeze).
"""
import ast
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_APP = Path(__file__).resolve().parents[2] / "filter_mate_app.py"


def _extract(names, namespace):
    tree = ast.parse(_APP.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(methods) == len(names)
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(_APP), "exec"), namespace)
    return namespace


class _Signal:
    def __init__(self):
        self.slots = []
        self.bare_disconnects = 0

    def connect(self, slot):
        self.slots.append(slot)

    def disconnect(self, slot=None):
        if slot is None:
            self.bare_disconnects += 1
            self.slots.clear()
            return
        if slot not in self.slots:
            raise TypeError("not connected")
        self.slots.remove(slot)


class _Store:
    def __init__(self):
        self.layersAdded = _Signal()
        self.layersWillBeRemoved = _Signal()
        self.allLayersRemoved = _Signal()


def _app():
    ns = _extract(["_connect_layer_store_slots", "_disconnect_layer_store_slots"],
                  {"logger": MagicMock()})
    app = types.SimpleNamespace(_on_layers_added=MagicMock(), manage_task=MagicMock())
    app._connect_layer_store_slots = types.MethodType(ns["_connect_layer_store_slots"], app)
    app._disconnect_layer_store_slots = types.MethodType(ns["_disconnect_layer_store_slots"], app)
    return app


@pytest.mark.unit
class TestLayerStoreSlots:

    def test_only_the_plugin_slots_are_removed(self):
        app = _app()
        store = _Store()
        qgis_receiver = object()  # QgsProject's own forwarding connection
        for signal in (store.layersAdded, store.layersWillBeRemoved, store.allLayersRemoved):
            signal.connect(qgis_receiver)

        app._connect_layer_store_slots(store)
        assert len(store.layersAdded.slots) == 2

        app._disconnect_layer_store_slots(store)

        for signal in (store.layersAdded, store.layersWillBeRemoved, store.allLayersRemoved):
            assert signal.slots == [qgis_receiver]
            assert signal.bare_disconnects == 0
        assert app._layer_store_slots == {}

    def test_disconnect_tolerates_a_store_that_forgot_the_slot(self):
        app = _app()
        store = _Store()
        app._connect_layer_store_slots(store)
        store.layersAdded.slots.clear()  # e.g. the store was recreated
        app._disconnect_layer_store_slots(store)  # no exception
        assert store.layersWillBeRemoved.slots == []

    def test_reconnect_after_project_switch_registers_fresh_slots(self):
        app = _app()
        old_store, new_store = _Store(), _Store()
        app._connect_layer_store_slots(old_store)
        app._disconnect_layer_store_slots(old_store)
        app._connect_layer_store_slots(new_store)
        assert old_store.layersAdded.slots == []
        assert new_store.layersAdded.slots == [app._on_layers_added]
        new_store.allLayersRemoved.slots[0]()
        app.manage_task.assert_called_once_with('remove_all_layers')
