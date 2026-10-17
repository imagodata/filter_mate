# -*- coding: utf-8 -*-
"""
2026-10-17: after an unload, QGIS no longer calls the unloaded instance.

The dock is removed and deleted without a closeEvent: the layer tree view's
currentLayerChanged, the current layer's selectionChanged and the theme
watcher (a singleton) kept the old dock's slots, its debounce timers could
fire and the module kept it as the active dock. The app's fileNameChanged
slot stayed connected (save_project_variables had no unloading guard), a
canvas frozen by a canceled filter stayed frozen until the task ended, and
the dependency check cleared the whole message bar. Methods are extracted
with ast; the plugin modules are never imported.
"""
import ast
import importlib.util
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


class _Signal:
    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def disconnect(self, slot):
        if slot not in self.slots:
            raise TypeError("not connected")
        self.slots.remove(slot)


def _extract(relative, class_name, names, namespace):
    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(methods) == len(names)
    exec(compile(ast.Module(body=methods, type_ignores=[]), relative, "exec"), namespace)
    return namespace


def _dock():
    namespace = _extract("filter_mate_dockwidget.py", "FilterMateDockWidget",
                         ["release_qgis_connections", "_disconnect_layer_selection_signal"],
                         {"logger": MagicMock(), "_MAX_SELECTION_CONNECTIONS": 32})
    dock = types.SimpleNamespace(
        _feature_picker_debounce_timer=MagicMock(), _expression_debounce_timer=MagicMock(),
        _theme_watcher=MagicMock(), _disconnect_feature_picker_layer_deletion=MagicMock(),
        current_layer=types.SimpleNamespace(selectionChanged=_Signal()), current_layer_selection_connection=True,
        _layer_tree_view_signal_connected=True,
    )
    dock._on_qgis_theme_changed = lambda theme: None
    dock.on_layer_selection_changed = lambda *args: None
    view = types.SimpleNamespace(currentLayerChanged=_Signal())
    tree_slot = lambda layer: None  # noqa: E731 - the configured lambda of ConfigurationManager
    dock.widgets = {"QGIS": {"LAYER_TREE_VIEW": {"WIDGET": view, "SIGNALS": [("currentLayerChanged", tree_slot)]}}}
    for name in ("release_qgis_connections", "_disconnect_layer_selection_signal"):
        setattr(dock, name, types.MethodType(namespace[name], dock))
    namespace["_active_dockwidget"] = dock
    return dock, namespace, view, tree_slot


def test_the_dock_releases_what_ties_it_to_qgis():
    dock, namespace, view, tree_slot = _dock()
    view.currentLayerChanged.connect(tree_slot)
    view.currentLayerChanged.connect(tree_slot)  # connected twice by a reconfiguration
    view.currentLayerChanged.connect(print)  # QGIS's own receiver stays
    dock.current_layer.selectionChanged.connect(dock.on_layer_selection_changed)

    dock.release_qgis_connections()

    assert view.currentLayerChanged.slots == [print]
    assert dock.current_layer.selectionChanged.slots == []
    dock._theme_watcher.remove_callback.assert_called_once_with(dock._on_qgis_theme_changed)
    dock._feature_picker_debounce_timer.stop.assert_called_once_with()
    dock._expression_debounce_timer.stop.assert_called_once_with()
    dock._disconnect_feature_picker_layer_deletion.assert_called_once_with()
    assert namespace["_active_dockwidget"] is None
    assert dock._layer_tree_view_signal_connected is False and dock.current_layer_selection_connection is None


def test_a_dock_never_configured_is_released_too():
    dock, namespace, view, tree_slot = _dock()
    del dock.widgets
    dock.current_layer = None
    dock._theme_watcher = None
    dock.release_qgis_connections()
    assert namespace["_active_dockwidget"] is None


def _app():
    namespace = _extract("filter_mate_app.py", "FilterMateApp",
                         ["save_project_variables", "_disconnect_all_signals", "_disconnect_layer_store_slots",
                          "cleanup"],
                         {"logger": MagicMock(), "ENV_VARS": {}, "HEXAGONAL_AVAILABLE": False,
                          "POSTGRESQL_AVAILABLE": False})
    project = types.SimpleNamespace(fileNameChanged=_Signal())
    app = types.SimpleNamespace(
        PROJECT=project, dockwidget=MagicMock(), _database_manager=MagicMock(), MapLayerStore=None,
        _signals_connected=False, _dockwidget_signals_connected=False, PROJECT_LAYERS={}, project_datasources={},
        _stop_pending_layer_additions=MagicMock(), _safe_cancel_all_tasks=MagicMock(),
        _get_layer_lifecycle_service=lambda: None, _unfreeze_canvas_after_task=MagicMock(),
    )
    for name in ("save_project_variables", "_disconnect_all_signals", "_disconnect_layer_store_slots", "cleanup"):
        setattr(app, name, types.MethodType(namespace[name], app))
    app._project_filename_slot = lambda: app.save_project_variables()
    project.fileNameChanged.connect(app._project_filename_slot)
    return app, project


def test_the_unloaded_app_no_longer_saves_on_file_name_changes():
    app, project = _app()
    app.cleanup()
    assert project.fileNameChanged.slots == []
    app.save_project_variables()  # a late call: nothing saved
    app._database_manager.save_project_variables.assert_not_called()


def test_cleanup_thaws_the_canvas_a_canceled_filter_froze():
    app, project = _app()
    app._canvas_frozen_token = 7
    app.cleanup()
    app._safe_cancel_all_tasks.assert_called_once_with()
    app._unfreeze_canvas_after_task.assert_called_once_with(7)


def test_the_dependency_check_replaces_only_its_own_message():
    """2026-10-17 review: messages were removed by a match on the layer names; only FilterMate's go."""
    source = (ROOT / "filter_mate.py").read_text(encoding="utf-8")
    body = source[source.index("    def _install_message_filter(self):"):source.index("    def _check_geometry_validation_settings")]
    assert ".clearWidgets()" not in body and "remove_message_bar_items" not in body
    assert "bar.popWidget(previous)" in body and "self._dependency_message_item = bar.pushWidget(" in body

