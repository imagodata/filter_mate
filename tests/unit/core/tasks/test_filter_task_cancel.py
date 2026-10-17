# -*- coding: utf-8 -*-
"""
2026-10-17: canceling a filter task only raises its flag; the worker cleans up.

``FilterEngineTask.cancel()`` runs on the main thread. It dropped the
materialized views (a DROP waiting for the worker's query: QGIS frozen) and
closed the task's connections, among them sqlite3 connections the worker had
created: ``sqlite3.ProgrammingError`` (not caught) left ``super().cancel()``
unreached, the task was never canceled. The methods are extracted from
filter_task.py with ast, the plugin module itself is never imported.
"""
import ast
import sqlite3
import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parents[4]
_METHODS = ("cancel", "_release_worker_resources")


class _QgsTask:
    def __init__(self):
        self.canceled = False

    def cancel(self):
        self.canceled = True

    def isCanceled(self):
        return self.canceled

    def description(self):
        return "Filtering data"


def _task_class():
    tree = ast.parse((PLUGIN_ROOT / "core" / "tasks" / "filter_task.py").read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterEngineTask")
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in _METHODS]
    assert len(methods) == len(_METHODS)
    holder = ast.ClassDef(name="_Task", bases=[ast.Name(id="QgsTask", ctx=ast.Load())], keywords=[],
                          body=methods, decorator_list=[])
    namespace = {"QgsTask": _QgsTask, "logger": MagicMock()}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[holder], type_ignores=[])), "filter_task.py", "exec"),
         namespace)
    return namespace["_Task"]


def _task(*connections):
    task = _task_class()()
    task.active_connections = list(connections)
    task._ps_manager = object()
    task._cleanup_postgresql_materialized_views = MagicMock()
    return task


def _worker_sqlite_connection():
    """An sqlite3 connection created in another thread, as the subset handler does in run()."""
    box = {}
    thread = threading.Thread(target=lambda: box.setdefault("conn", sqlite3.connect(":memory:")))
    thread.start()
    thread.join()
    return box["conn"]


def _pg_connection():
    conn = MagicMock(spec=["cancel", "close", "closed", "cursor"])
    conn.closed = 0
    return conn


def test_cancel_with_a_worker_sqlite_connection_cancels_the_task():
    conn = _worker_sqlite_connection()
    task = _task(conn)
    task.cancel()  # raised sqlite3.ProgrammingError before
    assert task.isCanceled()
    assert task.active_connections == [conn]  # left to the worker


def test_cancel_interrupts_the_postgresql_query_without_cleaning_up():
    conn = _pg_connection()
    task = _task(conn)
    task.cancel()
    conn.cancel.assert_called_once_with()
    conn.close.assert_not_called()
    task._cleanup_postgresql_materialized_views.assert_not_called()  # no DROP from the main thread
    assert task.isCanceled()


def test_cancel_skips_a_closed_postgresql_connection():
    conn = _pg_connection()
    conn.closed = 1
    task = _task(conn)
    task.cancel()
    conn.cancel.assert_not_called()
    assert task.isCanceled()


def test_a_failing_interrupt_still_cancels():
    conn = _pg_connection()
    conn.cancel.side_effect = RuntimeError("server gone")
    task = _task(conn)
    task.cancel()
    assert task.isCanceled()


def test_the_worker_cleans_up_after_a_cancel():
    conn = _pg_connection()
    task = _task(conn)
    task.cancel()
    task._release_worker_resources()
    task._cleanup_postgresql_materialized_views.assert_called_once_with()
    conn.close.assert_called_once_with()
    assert task.active_connections == [] and task._ps_manager is None


def test_the_worker_closes_its_connections_after_a_normal_run():
    conn = sqlite3.connect(":memory:")
    task = _task(conn)
    task._release_worker_resources()
    task._cleanup_postgresql_materialized_views.assert_not_called()  # the filter's views stay
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("select 1")  # closed
    assert task.active_connections == []


def test_a_failing_cleanup_still_closes_the_connections():
    conn = _pg_connection()
    task = _task(conn)
    task._cleanup_postgresql_materialized_views.side_effect = Exception("connection lost")
    conn.close.side_effect = Exception("already closed")
    task.cancel()
    task._release_worker_resources()
    assert task.active_connections == []


def test_run_releases_the_worker_resources_whatever_happens():
    tree = ast.parse((PLUGIN_ROOT / "core" / "tasks" / "filter_task.py").read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterEngineTask")
    run = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "run")
    tries = [node for node in run.body if isinstance(node, ast.Try)]
    assert tries, "run() has no try block"
    final = ast.dump(ast.Module(body=tries[-1].finalbody, type_ignores=[]))
    assert "_release_worker_resources" in final
