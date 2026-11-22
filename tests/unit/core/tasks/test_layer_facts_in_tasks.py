# -*- coding: utf-8 -*-
"""
2026-11-20: a layer is read by the thread it lives in.

- The tasks read their layers on the main thread, in ``__init__`` (``capture_layer_facts``), and give the
  layers back in ``finished()``; nothing captures in ``run()``.
- ``cleanup_memory_layer`` (called by ``finished()``, main thread) leaves the source layer the worker made:
  it lives in the worker's thread and is in no project. QGIS 4.3 reported its ``providerType()`` called from
  the main thread after every filter (the 3 FAIL of run_lifecycle_check.py on qgis/qgis:latest).

Modules tested: core.tasks.task_completion_handler, and the source of core.tasks.filter_task /
core.tasks.layer_management_task (their modules are too heavy to import here).
"""
import ast
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.tasks import task_completion_handler as _tch

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parents[4]
MAIN, WORKER = object(), object()


class Layer:
    def __init__(self, lives_in, provider="memory", layer_id="source_from_task_1"):
        self._lives_in, self._provider, self._id = lives_in, provider, layer_id
        self.reads = []

    def thread(self):
        return self._lives_in

    def isValid(self):
        self.reads.append("isValid")
        return True

    def providerType(self):
        self.reads.append("providerType")
        return self._provider

    def id(self):
        self.reads.append("id")
        return self._id


@pytest.fixture
def project(monkeypatch):
    found = MagicMock()
    found.map_layer.return_value = object()  # in the project
    monkeypatch.setattr(_tch, "get_qgis_factory", lambda: types.SimpleNamespace(get_project=lambda: found))
    monkeypatch.setattr(_tch, "QThread", types.SimpleNamespace(currentThread=lambda: MAIN))
    monkeypatch.setattr(_tch, "QGIS_PROVIDER_MEMORY", "memory")
    return found


def test_the_layer_the_worker_made_is_not_read_from_the_main_thread(project):
    layer = Layer(WORKER)
    _tch.cleanup_memory_layer(layer)
    assert layer.reads == []
    project.map_layer.assert_not_called()
    project.remove_map_layer.assert_not_called()


def test_a_layer_whose_thread_ended_is_not_read_either(project):
    """QObject.thread() of a layer made in a pool thread that ended is None."""
    layer = Layer(None)
    _tch.cleanup_memory_layer(layer)
    assert layer.reads == []
    project.remove_map_layer.assert_not_called()


def test_a_memory_layer_of_the_main_thread_is_handled_as_before(project):
    layer = Layer(MAIN)
    _tch.cleanup_memory_layer(layer)
    assert layer.reads[:2] == ["isValid", "providerType"]
    project.remove_map_layer.assert_called_once_with("source_from_task_1")


def test_another_provider_of_the_main_thread_is_left_in_the_project(project):
    layer = Layer(MAIN, provider="ogr")
    _tch.cleanup_memory_layer(layer)
    assert layer.reads == ["isValid", "providerType"]
    project.remove_map_layer.assert_not_called()


def test_no_layer_and_a_deleted_layer_do_not_raise(project):
    _tch.cleanup_memory_layer(None)
    deleted = MagicMock()
    deleted.thread.side_effect = RuntimeError("wrapped C/C++ object of type QgsVectorLayer has been deleted")
    deleted.isValid.side_effect = RuntimeError("wrapped C/C++ object of type QgsVectorLayer has been deleted")
    _tch.cleanup_memory_layer(deleted)
    project.remove_map_layer.assert_not_called()


def _methods(relative_path, class_name):
    tree = ast.parse((PLUGIN_ROOT / relative_path).read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    return {node.name: node for node in cls.body if isinstance(node, ast.FunctionDef)}


def _calls(node):
    names = set()
    for call in (item for item in ast.walk(node) if isinstance(item, ast.Call)):
        function = call.func
        names.add(function.attr if isinstance(function, ast.Attribute) else getattr(function, "id", ""))
    return names


@pytest.mark.parametrize("relative_path, class_name", [
    ("core/tasks/filter_task.py", "FilterEngineTask"),
    ("core/tasks/layer_management_task.py", "LayersManagementEngineTask"),
])
def test_a_task_reads_its_layers_when_it_is_created_and_gives_them_back_when_it_ends(relative_path, class_name):
    methods = _methods(relative_path, class_name)
    assert "capture_layer_facts" in _calls(methods["__init__"])  # main thread: the task is created there
    assert "release" in _calls(methods["finished"])  # main thread again
    elsewhere = [name for name, node in methods.items()
                 if name != "__init__" and "capture_layer_facts" in _calls(node)]
    assert elsewhere == []  # never in run(): that is the worker
