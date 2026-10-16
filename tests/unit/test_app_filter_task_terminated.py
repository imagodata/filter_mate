# -*- coding: utf-8 -*-
"""A filter task that fails or is canceled ends the protection of the current-layer combo box.

_set_filter_protection_flags blocks the combo box, disconnects its handler and sets the filtering flag when a
filter / unfilter / reset task starts; only the completion (FilterResultHandler) undid it, so after a failed or
canceled task the panel ignored every layer change. The methods are extracted from filter_mate_app.py with ast,
the plugin module itself is never imported.
"""
import ast
import sys
import time
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_APP = Path(__file__).resolve().parents[2] / "filter_mate_app.py"
_PKG = "fm_app_task_terminated_test"
_METHODS = ["_execute_filter_task", "_save_current_layer_before_filter", "_set_filter_protection_flags",
            "_filter_engine_task_terminated"]


class _Signal:
    def __init__(self):
        self.slots = []

    def connect(self, slot, *args):
        self.slots.append(slot)

    def emit(self):
        for slot in self.slots:
            slot()


class _Task:
    def __init__(self, description, task_name, task_parameters, backend_registry=None):
        self._description = description
        self.taskCompleted, self.taskTerminated = _Signal(), _Signal()

    def description(self):
        return self._description


def _extract():
    tree = ast.parse(_APP.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterMateApp")
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in _METHODS]
    assert len(methods) == len(_METHODS)
    tasks = types.ModuleType(_PKG + ".core.tasks")
    tasks.FilterEngineTask = _Task
    for name in ("", ".core"):
        package = types.ModuleType(_PKG + name)
        package.__path__ = []
        sys.modules.setdefault(_PKG + name, package)
    sys.modules[_PKG + ".core.tasks"] = tasks
    namespace = {"__package__": _PKG, "__name__": _PKG + ".filter_mate_app", "logger": MagicMock(),
                 "iface": MagicMock(), "QCoreApplication": MagicMock(), "perf_mark_start": lambda name: None,
                 "QgsApplication": MagicMock()}
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(_APP), "exec"), namespace)
    return namespace


@pytest.fixture
def app():
    namespace = _extract()
    zones = MagicMock()
    zones.id.return_value = "zones"
    combo = MagicMock()
    combo.signalsBlocked.return_value = False
    combo.blockSignals.side_effect = lambda flag: setattr(combo.signalsBlocked, "return_value", flag)
    dock = types.SimpleNamespace(current_layer=zones, manageSignal=MagicMock(), comboBox_filtering_current_layer=combo)
    instance = types.SimpleNamespace(
        dockwidget=dock, PROJECT=MagicMock(), _backend_registry=None, tasks_descriptions={"filter": "Filter"},
        appTasks={}, _current_layer_id_before_filter=None, _filter_result_handler=MagicMock(),
        _show_filter_start_message=MagicMock(), filter_engine_task_completed=MagicMock(),
        _cancel_conflicting_tasks=MagicMock(), _freeze_canvas_for_task=MagicMock(return_value=1),
        _unfreeze_canvas_after_task=MagicMock(),
    )
    for name in _METHODS:
        setattr(instance, name, types.MethodType(namespace[name], instance))
    return instance


def _launch(app):
    app._execute_filter_task("filter", {"task": {"layers": []}})
    return app.appTasks["filter"]


def test_task_start_blocks_the_combo_box_and_stamps_the_time(app):
    before = time.perf_counter()
    _launch(app)
    assert app.dockwidget._filtering_in_progress is True
    app.dockwidget.comboBox_filtering_current_layer.blockSignals.assert_called_once_with(True)
    assert before <= app.dockwidget._combo_blocked_at <= time.perf_counter()  # picks from then on: applied after


def test_a_terminated_task_ends_its_protection(app):
    task = _launch(app)
    task.taskTerminated.emit()
    app._filter_result_handler.handle_task_terminated.assert_called_once_with("zones")


def test_a_task_canceled_by_a_relaunch_leaves_the_new_protection_alone(app):
    first = _launch(app)
    second = _launch(app)  # a second click on Filter cancels the running task
    first.taskTerminated.emit()
    app._filter_result_handler.handle_task_terminated.assert_not_called()
    second.taskTerminated.emit()
    app._filter_result_handler.handle_task_terminated.assert_called_once_with("zones")


def test_a_terminated_task_does_nothing_while_the_plugin_unloads(app):
    task = _launch(app)
    app._unloading = True
    task.taskTerminated.emit()
    app._filter_result_handler.handle_task_terminated.assert_not_called()


def test_a_relaunch_keeps_the_start_of_the_task_it_cancels(app):
    """A layer picked during the canceled task was never applied: it counts for the new one."""
    _launch(app)
    started = app.dockwidget._combo_blocked_at
    _launch(app)
    assert app.dockwidget._combo_blocked_at == started


def test_a_task_after_the_protection_ended_starts_afresh(app):
    _launch(app)
    started = app.dockwidget._combo_blocked_at
    app.dockwidget.comboBox_filtering_current_layer.blockSignals(False)  # the post-filter window ended
    _launch(app)
    assert app.dockwidget._combo_blocked_at > started


def test_a_task_canceled_by_the_project_closing_leaves_no_protection(app):
    """No post-filter window over the closing project's layers, but the next project must find the panel free
    (get_project_layers_from_app skips its update while the filtering flag is set)."""
    task = _launch(app)
    app._removing_all_layers = True
    task.taskTerminated.emit()
    app._filter_result_handler.handle_task_terminated.assert_not_called()
    assert app.dockwidget._filtering_in_progress is False
    assert app.dockwidget.comboBox_filtering_current_layer.signalsBlocked() is False
