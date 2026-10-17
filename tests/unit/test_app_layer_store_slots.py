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


def _full_app():
    """The app's connection, project switch and teardown of its layer-store slots."""
    names = ["_connect_layer_store_slots", "_disconnect_layer_store_slots", "_connect_layer_store_signals",
             "_handle_project_initialization", "_disconnect_all_signals"]
    ns = _extract(names, {"logger": MagicMock(), "ENV_VARS": {}, "STABILITY_CONSTANTS": {}})
    store = _Store()
    service = MagicMock()
    app = types.SimpleNamespace(
        _on_layers_added=MagicMock(), manage_task=MagicMock(), MapLayerStore=store, _signals_connected=False,
        _dockwidget_signals_connected=False, dockwidget=None,
        PROJECT=types.SimpleNamespace(layerStore=lambda: store),
        _get_layer_lifecycle_service=lambda: service, _datasource_manager=None,
        _initializing_project=False, _loading_new_project=False, app_postgresql_temp_schema="filtermate_temp",
        _check_and_reset_stale_flags=MagicMock(), _set_initializing_flag=MagicMock(), _set_loading_flag=MagicMock(),
        _safe_cancel_all_tasks=MagicMock(), init_filterMate_db=MagicMock(),
    )
    app.service = service
    for name in names:
        setattr(app, name, types.MethodType(ns[name], app))
    return app, store


def _app_initializer_connect():
    path = Path(__file__).resolve().parents[2] / "core" / "services" / "app_initializer.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "AppInitializer")
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef)
                  and node.name == "_connect_layer_store_signals")
    namespace = {"logger": MagicMock()}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), "exec"), namespace)
    return namespace["_connect_layer_store_signals"]


@pytest.mark.unit
class TestOneSetOfLayerStoreSlots:
    """2026-10-17: the AppInitializer connected its own anonymous slots (never remembered), the first
    project switch connected the app's next to them: every layer addition / removal ran twice."""

    def test_connecting_twice_keeps_one_set(self):
        app = _app()
        store = _Store()
        app._connect_layer_store_slots(store)
        app._connect_layer_store_slots(store)
        assert len(store.layersAdded.slots) == 1 and len(store.allLayersRemoved.slots) == 1

    def test_the_app_initializer_connects_through_the_app(self):
        app, store = _full_app()
        initializer = types.SimpleNamespace(_connect_layer_store_signals_callback=app._connect_layer_store_signals,
                                            _get_signals_connected=lambda: app._signals_connected)
        _app_initializer_connect()(initializer)
        app._connect_layer_store_signals()  # FilterMateApp.run() connects again after the initializer
        assert store.layersAdded.slots == [app._on_layers_added]

    @pytest.mark.parametrize("switches", [1, 3])
    def test_project_switches_keep_one_set(self, switches):
        app, store = _full_app()
        app._connect_layer_store_signals()
        for _ in range(switches):
            app._handle_project_initialization("project_read")
        assert app.service.handle_project_initialization.call_count == switches  # the switch went through
        assert len(store.layersAdded.slots) == 1
        assert len(store.layersWillBeRemoved.slots) == 1 and len(store.allLayersRemoved.slots) == 1

    def test_cleanup_disconnects_them(self):
        app, store = _full_app()
        qgis_receiver = object()
        store.layersAdded.connect(qgis_receiver)
        app._connect_layer_store_signals()
        app._disconnect_all_signals()
        assert store.layersAdded.slots == [qgis_receiver] and store.allLayersRemoved.slots == []
        assert app._signals_connected is False
