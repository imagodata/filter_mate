# -*- coding: utf-8 -*-
"""
TaskManagementService.safe_cancel_all_tasks runs on a project change, on F5 and
when the plugin unloads: it must cancel FilterMate's tasks only. It canceled any
task of the QGIS task manager (Processing in the background, other plugins) whose
id was below the task count, since ``QgsTaskManager.task()`` takes an id, not an
index; FilterMate's own tasks, with larger ids, were mostly left running.
"""
from unittest.mock import MagicMock

import pytest

from core.services import task_management_service as tms


class _Task:
    def __init__(self, task_id, description, can_cancel=True):
        self.task_id = task_id
        self._description = description
        self._can_cancel = can_cancel
        self.canceled = False

    def description(self):
        return self._description

    def canCancel(self):
        return self._can_cancel

    def cancel(self):
        self.canceled = True


def _task_class(name, module):
    return type(name, (_Task,), {"__module__": module})


FilterEngineTask = _task_class("FilterEngineTask", f"{tms._PLUGIN_PACKAGE}.core.tasks.filter_task")
LayersManagementEngineTask = _task_class(
    "LayersManagementEngineTask", f"{tms._PLUGIN_PACKAGE}.core.tasks.layer_management_task")
OtherPluginTask = _task_class("ExportTask", "other_plugin.tasks")
ProcessingTask = _task_class("QgsProcessingAlgRunnerTask", "qgis._core")


class _TaskManager:
    def __init__(self, tasks):
        self._tasks = list(tasks)

    def tasks(self):
        return list(self._tasks)

    def count(self):
        return len(self._tasks)

    def task(self, task_id):
        return next((t for t in self._tasks if t.task_id == task_id), None)


@pytest.fixture
def task_manager(monkeypatch):
    def install(tasks):
        manager = _TaskManager(tasks)
        monkeypatch.setattr(tms, "QgsApplication", MagicMock(taskManager=lambda: manager))
        return manager
    return install


@pytest.mark.unit
class TestSafeCancelAllTasks:

    def test_only_filtermate_tasks_are_canceled(self, task_manager):
        processing = ProcessingTask(0, "Buffer")  # a low id: task(0) used to reach it
        other = OtherPluginTask(1, "Exporting tiles")
        layers = LayersManagementEngineTask(57, "Adding layers")
        filtering = FilterEngineTask(58, "Filtrage des données")  # translated description
        export = OtherPluginTask(59, "FilterMate: export")  # raster / point cloud task description
        task_manager([processing, other, layers, filtering, export])

        tms.TaskManagementService().safe_cancel_all_tasks()

        assert not processing.canceled and not other.canceled
        assert layers.canceled and filtering.canceled and export.canceled

    def test_tasks_that_cannot_be_canceled_are_left(self, task_manager):
        task = FilterEngineTask(3, "Filtering data", can_cancel=False)
        task_manager([task])

        tms.TaskManagementService().safe_cancel_all_tasks()

        assert not task.canceled

    def test_a_deleted_task_does_not_stop_the_others(self, task_manager):
        deleted = OtherPluginTask(4, "x")
        deleted.description = MagicMock(side_effect=RuntimeError("wrapped C/C++ object deleted"))
        task = FilterEngineTask(5, "Filtering data")
        task_manager([task, deleted])

        tms.TaskManagementService().safe_cancel_all_tasks()

        assert task.canceled and not deleted.canceled


@pytest.mark.unit
class TestIsFilterMateTask:

    def test_plugin_classes(self):
        assert tms.is_filtermate_task(FilterEngineTask(1, "")) is True

    def test_description_prefix(self):
        assert tms.is_filtermate_task(OtherPluginTask(1, "FilterMate: height above dem")) is True

    def test_other_tasks(self):
        assert tms.is_filtermate_task(OtherPluginTask(1, "Filtering")) is False
        assert tms.is_filtermate_task(ProcessingTask(1, "Clip")) is False
