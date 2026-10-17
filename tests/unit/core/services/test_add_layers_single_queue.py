# -*- coding: utf-8 -*-
"""
2026-10-17: layers added while an add_layers task runs are registered.

FilterMateApp.manage_task queued them in ``self._add_layers_queue``, but
``_process_add_layers_queue`` delegated to
TaskManagementService.process_add_layers_queue, which popped the service's
OWN queue - always empty (``enqueue_add_layers`` has no caller). The
queued layers never reached PROJECT_LAYERS ("not in PROJECT_LAYERS").
The app method is extracted from filter_mate_app.py with ast, like the
other app tests, so the plugin module itself is never imported.
"""
import ast
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from core.services import task_management_service as tms

pytestmark = pytest.mark.unit

_APP = Path(__file__).resolve().parents[4] / "filter_mate_app.py"


def _app_method(name):
    tree = ast.parse(_APP.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterMateApp")
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)
    namespace = {"logger": logging.getLogger("test")}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(_APP), "exec"), namespace)
    return namespace[name]


def test_queued_layers_reach_manage_task():
    service = tms.TaskManagementService()
    first, second = [MagicMock(name="ortho")], [MagicMock(name="mnt")]
    app = SimpleNamespace(
        _add_layers_queue=[first, second],
        _get_task_management_service=lambda: service,
        _filter_usable_layers=lambda layers: list(layers),
        manage_task=MagicMock(),
    )

    _app_method("_process_add_layers_queue")(app)

    app.manage_task.assert_called_once_with("add_layers", first)
    assert app._add_layers_queue == [second]


def test_layers_removed_while_queued_are_left_out():
    service = tms.TaskManagementService()
    app = SimpleNamespace(
        _add_layers_queue=[[MagicMock(name="removed")]],
        _get_task_management_service=lambda: service,
        _filter_usable_layers=lambda layers: [],
        manage_task=MagicMock(),
    )

    _app_method("_process_add_layers_queue")(app)

    app.manage_task.assert_not_called()
    assert app._add_layers_queue == []


def test_service_processes_the_queue_it_is_given():
    service = tms.TaskManagementService()
    callback = MagicMock()
    queue = [["a"], ["b"]]

    service.process_add_layers_queue(callback, queue=queue)

    callback.assert_called_once_with("add_layers", ["a"])
    assert queue == [["b"]]


def test_service_without_queue_argument_keeps_its_own():
    service = tms.TaskManagementService()
    service.enqueue_add_layers(["x"])
    callback = MagicMock()

    service.process_add_layers_queue(callback)

    callback.assert_called_once_with("add_layers", ["x"])
    assert service.get_queue_size() == 0
