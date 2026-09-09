"""Exercise shutdown signal ordering without constructing a QGIS window."""
import ast
import logging
import weakref
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_methods(filename, class_name, names, namespace):
    tree = ast.parse((ROOT / filename).read_text(encoding='utf-8'))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == class_name)
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef)
               and node.name in names]
    exec(compile(ast.Module(body=methods, type_ignores=[]), filename, 'exec'), namespace)
    return {name: namespace[name] for name in names}


@pytest.fixture
def app():
    namespace = {'logger': logging.getLogger(__name__), 'QTimer': MagicMock(),
                 'weakref': weakref, 'STABILITY_CONSTANTS': {}, 'HEXAGONAL_AVAILABLE': False,
                 'POSTGRESQL_AVAILABLE': False}
    methods = load_methods('filter_mate_app.py', 'FilterMateApp', [
        'manage_task', '_handle_remove_all_layers', '_stop_pending_layer_additions',
        '_on_layers_added', '_process_pending_added_layers',
        '_handle_layer_task_terminated', 'layer_management_engine_task_completed', 'cleanup',
        'filter_engine_task_completed', '_safe_layer_operation',
    ], namespace)
    instance = type('TestApp', (), methods)()
    instance.PROJECT_LAYERS = {str(i): object() for i in range(1000)}
    instance.project_datasources = {'ogr': {'source': object()}}
    instance._pending_added_layers = [object()]
    instance._layers_added_timer = MagicMock()
    instance._add_layers_queue = [[object()]]
    instance._pending_add_layers_tasks = 1
    instance._get_layer_lifecycle_service = MagicMock(return_value=MagicMock())
    instance._safe_cancel_all_tasks = MagicMock()
    instance.dockwidget = SimpleNamespace(widgets_initialized=True, PROJECT_LAYERS={}, CONFIG_DATA={})
    instance._check_and_reset_stale_flags = MagicMock()
    instance._task_orchestrator = MagicMock()
    instance._initializing_project = False
    instance.tasks_descriptions = dict.fromkeys(['remove_layers', 'add_layers', 'new_project', 'project_read'])
    instance.session_id = 'session'
    instance.app_postgresql_temp_schema = 'public'
    return instance


@pytest.mark.unit
def test_bulk_removal_skips_following_layer_tasks_and_late_callbacks(app):
    timer = app._layers_added_timer
    app.manage_task('remove_all_layers')
    # QGIS emits the individual removal signals after allLayersRemoved.
    for i in range(1000):
        app.manage_task('remove_layers', [str(i)])
    app._handle_layer_task_terminated('add_layers')
    app.layer_management_engine_task_completed({'old': object()}, 'add_layers')
    app.filter_engine_task_completed('filter', object(), {})
    app._safe_layer_operation(object(), {}, MagicMock())
    app._process_pending_added_layers()
    app.manage_task('add_layers', [object()])
    app.manage_task('remove_all_layers')
    service = app._get_layer_lifecycle_service.return_value
    service.handle_remove_all_layers.assert_called_once()
    app._task_orchestrator.dispatch_task.assert_not_called()
    timer.stop.assert_called_once()
    assert not app.PROJECT_LAYERS
    assert not app._pending_added_layers
    assert not app._add_layers_queue
    assert app._pending_add_layers_tasks == 0


@pytest.mark.unit
def test_real_addition_resumes_normal_layer_removal(app):
    app.manage_task('remove_all_layers')
    new_layer = object()
    app._on_layers_added([new_layer])
    assert app._pending_added_layers == [new_layer]
    assert not app._removing_all_layers
    app.manage_task('remove_layers', ['new'])
    app._task_orchestrator.dispatch_task.assert_called_once_with('remove_layers', ['new'])


@pytest.mark.unit
@pytest.mark.parametrize('task', ['new_project', 'project_read'])
def test_project_initialization_resumes_after_clear(app, task):
    app.manage_task('remove_all_layers')
    app.manage_task(task)
    app._task_orchestrator.dispatch_task.assert_called_once_with(task, None)
    assert not app._removing_all_layers


@pytest.mark.unit
def test_unload_stops_pending_work_and_is_idempotent(app):
    app.cleanup()
    app.cleanup()
    app._on_layers_added([object()])
    app.manage_task('new_project')
    app.manage_task('remove_layers', ['old'])
    app._handle_layer_task_terminated('add_layers')
    app.layer_management_engine_task_completed({}, 'add_layers')
    app.filter_engine_task_completed('filter', object(), {})
    app._safe_layer_operation(object(), {}, MagicMock())
    app._get_layer_lifecycle_service.return_value.cleanup.assert_called_once()
    app._safe_cancel_all_tasks.assert_called_once()
    app._task_orchestrator.dispatch_task.assert_not_called()
    assert not app._pending_added_layers


@pytest.mark.unit
def test_bulk_widget_cleanup_resets_existing_picker_without_rebuilding():
    from typing import Any, Callable
    iface = MagicMock()
    methods = load_methods('core/services/layer_lifecycle_service.py', 'LayerLifecycleService',
                           ['handle_remove_all_layers'],
                           {'logger': logging.getLogger(__name__), 'iface': iface,
                            'Any': Any, 'Callable': Callable})
    dock = MagicMock()
    dock.PROJECT_LAYERS = {'old': object()}
    picker = dock.checkableComboBoxFeaturesListPickerWidget_exploring_multiple_selection
    picker.blockSignals.return_value = False
    cancel = MagicMock()
    methods['handle_remove_all_layers'](None, cancel, dock)
    cancel.assert_called_once()
    picker.reset.assert_called_once()
    assert picker.blockSignals.call_args_list[-1].args == (False,)
    dock.reset_multiple_checkable_combobox.assert_not_called()
    dock.comboBox_filtering_current_layer.setLayer.assert_called_once_with(None)
    dock.comboBox_filtering_current_layer.clear.assert_not_called()
    assert dock.current_layer is None
    assert not dock.PROJECT_LAYERS
    assert not dock._signals_connected
    assert not dock._layer_tree_view_signal_connected
