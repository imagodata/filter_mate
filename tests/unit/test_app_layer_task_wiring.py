# -*- coding: utf-8 -*-
"""FilterMateApp hands LayerTaskCompletionHandler the ids a layer task registered or
unregistered (LayersManagementEngineTask.changed_layer_ids), so overlapping add / remove
tasks are merged into the current PROJECT_LAYERS instead of replacing it.

The methods are extracted from filter_mate_app.py with ast (the module needs QGIS)."""
import ast
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_APP = pathlib.Path(__file__).resolve().parents[2] / "filter_mate_app.py"
_PKG = "_fm_wiring_pkg"


def _extract(names, namespace):
    tree = ast.parse(_APP.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterMateApp")
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(methods) == len(names)
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(_APP), "exec"), namespace)
    return namespace


class _Signal:
    def __init__(self):
        self.slots = []

    def connect(self, slot, *args):
        self.slots.append(slot)


class _FakeTask:
    def __init__(self, description, task_action, task_parameters):
        self.changed_layer_ids = []
        self.resultingLayers = _Signal()
        self.savingLayerVariable = _Signal()
        self.removingLayerVariable = _Signal()
        self.taskTerminated = _Signal()
        self.begun = _Signal()

    def setDependentLayers(self, layers):
        pass


@pytest.fixture
def tasks_package(monkeypatch):
    package = types.ModuleType(_PKG)
    package.__path__ = []
    core = types.ModuleType(f"{_PKG}.core")
    core.__path__ = []
    core_tasks = types.ModuleType(f"{_PKG}.core.tasks")
    core_tasks.LayersManagementEngineTask = _FakeTask
    for module in (package, core, core_tasks):
        monkeypatch.setitem(sys.modules, module.__name__, module)
    return core_tasks


def test_the_completion_receives_the_ids_the_task_changed(tasks_package):
    task_manager = MagicMock()
    namespace = _extract(["_execute_layer_task"], {
        "__package__": _PKG, "Qt": MagicMock(),
        "QgsApplication": MagicMock(taskManager=lambda: task_manager),
    })
    app = types.SimpleNamespace(appTasks={}, tasks_descriptions={"remove_layers": "Removing layers"},
                                dockwidget=None, on_remove_layer_task_begun=MagicMock(),
                                layer_management_engine_task_completed=MagicMock())
    namespace["_execute_layer_task"](app, "remove_layers", {"task": {"layers": ["B"]}})
    task = app.appTasks["remove_layers"]

    task.changed_layer_ids.append("B")  # filled by run(), before resultingLayers is emitted
    task.resultingLayers.slots[0]({"A": {}})

    app.layer_management_engine_task_completed.assert_called_once_with({"A": {}}, "remove_layers", ["B"])


def test_the_ids_reach_the_handler():
    handler = MagicMock()
    namespace = _extract(["layer_management_engine_task_completed"], {
        "init_env_vars": lambda: None, "ENV_VARS": {"PROJECT": object()}, "logger": MagicMock(),
    })
    app = types.SimpleNamespace(_layer_task_completion_handler=handler, _loading_new_project=False)

    namespace["layer_management_engine_task_completed"](app, {"A": {}}, "remove_layers", ["B"])
    namespace["layer_management_engine_task_completed"](app, {"A": {}}, "add_layers")

    first, second = handler.handle_task_completion.call_args_list
    assert first.kwargs["changed_layer_ids"] == ["B"]
    assert second.kwargs["changed_layer_ids"] is None
