# -*- coding: utf-8 -*-
"""
SpatialiteFilterExecutor.cleanup_resources runs at the end of every task (the registry's
cleanup_all). It called ``cleanup_session_temp_tables()`` without arguments (a TypeError
logged as a warning each time). The temp table a task has just made is read by the subset
the main thread applies afterwards: the end of a task never drops it. Tables are dropped
only when the caller names the session, and never those a layer is still filtered through.
"""
import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_FILE = Path(__file__).resolve().parents[5] / "adapters" / "backends" / "spatialite" / "executor_wrapper.py"


def _method():
    tree = ast.parse(_FILE.read_text(encoding="utf-8"))
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == "cleanup_resources":
                calls = []
                import logging
                ns = {"cleanup_session_temp_tables": lambda *a, **k: calls.append((a, k)) or 2,
                      "logger": logging.getLogger("t"), "Optional": __import__("typing").Optional,
                      "Iterable": __import__("typing").Iterable, "List": __import__("typing").List}
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(_FILE), "exec"), ns)
                return ns["cleanup_resources"], calls
    raise AssertionError("cleanup_resources not found")


def test_the_end_of_a_task_drops_nothing():
    cleanup, calls = _method()

    assert cleanup(object()) == 0 and calls == []


def test_an_explicit_session_is_cleaned_with_the_tables_in_use_kept():
    cleanup, calls = _method()

    assert cleanup(object(), session_id="ab12cd34", db_paths=["/d/a.gpkg", "/d/b.gpkg"],
                   exclude_referenced_by=["x"]) == 4
    assert calls == [(("/d/a.gpkg", "ab12cd34"), {"exclude_referenced_by": ["x"]}),
                     (("/d/b.gpkg", "ab12cd34"), {"exclude_referenced_by": ["x"]})]
