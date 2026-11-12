# -*- coding: utf-8 -*-
"""A filter that raises tells the user why, not only "Task failed".

2026-11-12 (Zones MRO -> 8 layers, Intersect, PostgreSQL): CallbackActionHandler
catches the exception of FilterEngineTask.execute_filtering and returns
``ActionResult(success=False, errors=[str(e)])``; _execute_task_action returned
only ``result.success``, so neither ``task.message`` nor ``task.exception``
carried the error and the message bar showed the generic "Task failed".
Method extracted with ast.
"""
import ast
import importlib.util
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[4]
_MODULE = _ROOT / "core" / "tasks" / "filter_task.py"
_ERROR = "No valid PostgreSQL connection available: could not obtain a connection from the layer."


def _dispatcher_module():
    spec = importlib.util.spec_from_file_location(
        "fm_test_dispatcher_message", _ROOT / "core" / "tasks" / "dispatchers" / "action_dispatcher.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _execute_task_action():
    tree = ast.parse(_MODULE.read_text(encoding="utf-8"))
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == "_execute_task_action":
                ns = {"logger": MagicMock(), "create_action_context_from_task": MagicMock()}
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(_MODULE), "exec"), ns)
                return ns["_execute_task_action"]
    raise AssertionError("method not found")


def _task(callback, message=None):
    """A task whose dispatcher runs ``callback`` through the real CallbackActionHandler."""
    module = _dispatcher_module()
    handler = module.CallbackActionHandler(module.TaskAction.FILTER, callback)
    context = module.ActionContext(task_parameters={}, source_layer=None, layers={}, layers_count=1,
                                   is_canceled=lambda: False)
    dispatcher = MagicMock()
    dispatcher.dispatch.side_effect = lambda action, ctx: handler.execute(context)
    return types.SimpleNamespace(task_action="filter", message=message, exception=None,
                                 _get_action_dispatcher=lambda: dispatcher)


def _raise():
    raise Exception(_ERROR)


def test_the_error_of_a_filter_that_raises_becomes_the_task_message():
    task = _task(_raise)

    assert _execute_task_action()(task) is False
    assert _ERROR in task.message


def test_only_the_first_line_of_a_long_error_reaches_the_message_bar():
    def raise_sql_error():
        raise Exception('relation "zone_mro" does not exist\nLINE 1: SELECT "zone_mro"."id" FROM ...\n        ^')

    task = _task(raise_sql_error)

    assert _execute_task_action()(task) is False
    assert task.message == 'relation "zone_mro" does not exist'


def test_a_message_the_filter_already_set_is_kept():
    task = _task(_raise, message="Failed to filter source layer 'Zones MRO'.")

    assert _execute_task_action()(task) is False
    assert task.message == "Failed to filter source layer 'Zones MRO'."


def test_a_filter_that_returns_false_leaves_the_message_to_the_finished_handler():
    task = _task(lambda: False)

    assert _execute_task_action()(task) is False
    assert task.message is None
