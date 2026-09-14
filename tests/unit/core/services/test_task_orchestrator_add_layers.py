# -*- coding: utf-8 -*-
"""
2026-09-14: TaskOrchestrator kept its own add_layers counter, incremented on
every dispatch and decremented by nobody. After the first add_layers of a
session every later one (project switch, layer added to the project) was
queued for ever ("Queueing add_layers - 1 task(s) in progress") and the panel
stayed empty. FilterMateApp.manage_task is the single add_layers queue now.
"""
from unittest.mock import MagicMock

import pytest

from core.services.task_orchestrator import TaskOrchestrator


def _orchestrator(handle_layer_task):
    dockwidget = MagicMock()
    dockwidget.widgets_initialized = True
    orchestrator = TaskOrchestrator(
        get_dockwidget=lambda: dockwidget,
        get_project_layers=lambda: {},
        get_config_data=lambda: {},
        get_project=lambda: MagicMock(),
        check_reset_stale_flags=lambda: False,
        set_loading_flag=lambda v: None,
        set_initializing_flag=lambda v: None,
        get_task_parameters=lambda name, data: {"task": {"layers": data}},
        handle_filter_task=MagicMock(),
        handle_layer_task=handle_layer_task,
        handle_undo=MagicMock(),
        handle_redo=MagicMock(),
        force_reload_layers=MagicMock(),
        handle_remove_all_layers=MagicMock(),
        handle_project_initialization=MagicMock(),
    )
    orchestrator._log_current_state = lambda: None  # imports sip (QGIS only)
    return orchestrator


@pytest.mark.unit
class TestAddLayersIsNeverQueuedByTheOrchestrator:

    def test_consecutive_add_layers_all_reach_the_layer_task(self):
        handle_layer_task = MagicMock()
        orchestrator = _orchestrator(handle_layer_task)
        orchestrator.widgets_ready = True

        first = orchestrator.dispatch_task('add_layers', ['project A layers'])
        second = orchestrator.dispatch_task('add_layers', ['project B layers'])

        assert (first, second) == (True, True)
        assert [c.args[1]["task"]["layers"] for c in handle_layer_task.call_args_list] == [
            ['project A layers'], ['project B layers']]
        assert orchestrator._add_layers_queue == []
        assert orchestrator._pending_add_layers_tasks == 0

    def test_missing_task_parameters_do_not_dispatch(self):
        handle_layer_task = MagicMock()
        orchestrator = _orchestrator(handle_layer_task)
        orchestrator.widgets_ready = True
        orchestrator._get_task_parameters = lambda name, data: None

        assert orchestrator.dispatch_task('add_layers', ['x']) is False
        handle_layer_task.assert_not_called()
