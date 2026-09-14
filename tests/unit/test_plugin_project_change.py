# -*- coding: utf-8 -*-
"""
Project switch with the panel open (2026-09-14): FilterMate._handle_project_change
cleans the previous project's state, then reinitializes the app for the new
project after a short delay. The method is extracted from filter_mate.py with
ast (the plugin entry module cannot be imported outside QGIS).
"""
import ast
import gc
import sys
import types
import weakref
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_PLUGIN = Path(__file__).resolve().parents[2] / "filter_mate.py"


def _extract(name):
    tree = ast.parse(_PLUGIN.read_text(encoding="utf-8"))
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                ns = {"logger": MagicMock(), "weakref": weakref}
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(_PLUGIN), "exec"), ns)
                return ns[name]
    raise AssertionError(f"{name} not found")


class _Plugin:
    """Weak-referenceable stand-in for the FilterMate plugin object."""


class _FakeTimer:
    scheduled = []

    @classmethod
    def singleShot(cls, delay, callback):
        cls.scheduled.append((delay, callback))


def _app(project_layers=None):
    app = MagicMock()
    app._initializing_project = False
    app._loading_new_project = False
    app.PROJECT_LAYERS = dict(project_layers or {"old": object()})
    app._add_layers_queue = ["stale"]
    app._pending_add_layers_tasks = 2
    app.dockwidget = MagicMock()
    app.dockwidget.widgets_initialized = True
    return app


@pytest.fixture
def qgis(monkeypatch):
    _FakeTimer.scheduled = []
    monkeypatch.setattr(sys.modules["qgis.PyQt.QtCore"], "QTimer", _FakeTimer)
    qgs_project = MagicMock()
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsProject", qgs_project)
    return qgs_project


def _plugin(app):
    plugin = _Plugin()
    plugin.app = app
    plugin._handle_project_change = types.MethodType(_extract("_handle_project_change"), plugin)
    return plugin


def _vector_layers(count):
    layers = {}
    for i in range(count):
        layer = MagicMock()  # isinstance(layer, QgsVectorLayer) holds: the stub class is MagicMock
        layer.name.return_value = f"layer{i}"
        layers[f"id{i}"] = layer
    return layers


@pytest.mark.unit
class TestHandleProjectChange:

    def test_cleans_previous_state_then_reinitializes_after_the_delay(self, qgis):
        app = _app()
        qgis.instance.return_value.mapLayers.return_value = _vector_layers(3)
        plugin = _plugin(app)

        plugin._handle_project_change()

        app._stop_pending_layer_additions.assert_called_once()
        app._safe_cancel_all_tasks.assert_called_once()
        assert app.PROJECT_LAYERS == {} and app._add_layers_queue == [] and app._pending_add_layers_tasks == 0
        app.dockwidget.comboBox_filtering_current_layer.setLayer.assert_called_with(None)
        app.dockwidget.comboBox_filtering_current_layer.clear.assert_not_called()
        app.dockwidget.mFeaturePickerWidget_exploring_single_selection.setLayer.assert_called_with(None)
        assert app.dockwidget.current_layer is None and app.dockwidget.has_loaded_layers is False
        app._handle_project_initialization.assert_not_called()  # deferred

        assert [d for d, _ in _FakeTimer.scheduled] == [300]
        _FakeTimer.scheduled[0][1]()
        app._handle_project_initialization.assert_called_once_with('project_read')

    def test_project_without_vector_layer_disables_the_panel(self, qgis):
        app = _app()
        qgis.instance.return_value.mapLayers.return_value = {}
        plugin = _plugin(app)

        plugin._handle_project_change()

        app.dockwidget.set_widgets_enabled_state.assert_called_once_with(False)
        assert _FakeTimer.scheduled == []
        app._handle_project_initialization.assert_not_called()

    def test_skipped_while_the_app_is_still_initializing(self, qgis):
        app = _app()
        app._initializing_project = True
        qgis.instance.return_value.mapLayers.return_value = _vector_layers(2)
        plugin = _plugin(app)

        plugin._handle_project_change()

        app._stop_pending_layer_additions.assert_not_called()
        assert _FakeTimer.scheduled == []

    def test_reinitialization_error_resets_the_flags(self, qgis):
        app = _app()
        app._handle_project_initialization.side_effect = RuntimeError("boom")
        qgis.instance.return_value.mapLayers.return_value = _vector_layers(1)
        plugin = _plugin(app)
        plugin._handle_project_change()

        _FakeTimer.scheduled[0][1]()  # must not raise

        app._set_loading_flag.assert_called_with(False)
        app._set_initializing_flag.assert_called_with(False)

    def test_unloaded_plugin_is_not_reinitialized(self, qgis):
        app = _app()
        qgis.instance.return_value.mapLayers.return_value = _vector_layers(1)
        plugin = _plugin(app)
        plugin._handle_project_change()
        callback = _FakeTimer.scheduled[0][1]
        del plugin
        gc.collect()

        callback()

        app._handle_project_initialization.assert_not_called()
