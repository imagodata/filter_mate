# -*- coding: utf-8 -*-
"""
2026-10-17: a filter task QGIS canceled (a layer of the task being removed) is no error.

The worker then meets the deleted layer: ``RuntimeError: wrapped C/C++ object
... has been deleted``. CallbackActionHandler logged it at ERROR with its
traceback; a canceled task logs it at INFO. Any other failure stays an error.
"""
import importlib.util
import logging
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parents[4]


def _module():
    spec = importlib.util.spec_from_file_location(
        "fm_test_action_dispatcher", PLUGIN_ROOT / "core" / "tasks" / "dispatchers" / "action_dispatcher.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(failure, canceled, caplog):
    module = _module()

    def execute():
        raise failure

    handler = module.CallbackActionHandler(module.TaskAction.FILTER, execute)
    context = module.ActionContext(task_parameters={}, source_layer=None, layers={}, layers_count=1,
                                   is_canceled=lambda: canceled)
    with caplog.at_level(logging.INFO):
        result = handler.execute(context)
    assert result.success is False
    return [record.levelno for record in caplog.records]


def test_a_deleted_layer_in_a_canceled_task_is_no_error(caplog):
    levels = _run(RuntimeError("wrapped C/C++ object of type QgsVectorLayer has been deleted"), True, caplog)
    assert logging.ERROR not in levels and logging.INFO in levels


def test_the_same_failure_in_a_running_task_is_an_error(caplog):
    levels = _run(RuntimeError("wrapped C/C++ object of type QgsVectorLayer has been deleted"), False, caplog)
    assert logging.ERROR in levels


def test_another_failure_of_a_canceled_task_is_an_error(caplog):
    levels = _run(ValueError("bad expression"), True, caplog)
    assert logging.ERROR in levels
