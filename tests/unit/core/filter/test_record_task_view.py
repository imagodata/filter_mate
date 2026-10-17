# -*- coding: utf-8 -*-
"""2026-10-17: the source selection views of the PostgreSQL backend are recorded as the task's own.

A canceled filter task drops the views it created that no subset reads; the view a
second click on Filter left behind (found on PostGIS by run_postgis_check.py) came
from the source selection path, unknown to the task.
"""
import ast
import types
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_MODULE = Path(__file__).resolve().parents[4] / "core" / "filter" / "expression_builder.py"


def _record():
    tree = ast.parse(_MODULE.read_text(encoding="utf-8"))
    node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "record_task_view")
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(_MODULE), "exec"), namespace)
    return namespace["record_task_view"]


def test_the_view_name_reaches_the_parent_task():
    task = types.SimpleNamespace()
    _record()({"_parent_task": task}, '"filter_mate_temp"."fm_temp_mv_session_ab12_cd34"')
    assert task._created_mv_names == {"fm_temp_mv_session_ab12_cd34"}


def test_no_task_no_record():
    _record()({}, '"s"."v"')
    _record()(None, '"s"."v"')
    _record()({"_parent_task": object()}, '"s"."v"')  # no __dict__: ignored
