# -*- coding: utf-8 -*-
"""
2026-10-17: canceling a filter task only raises its flag; the worker closes its connections.

``FilterEngineTask.cancel()`` runs on the main thread. It dropped the
materialized views (a DROP waiting for the worker's query: QGIS frozen) and
closed the task's connections, among them sqlite3 connections the worker had
created: ``sqlite3.ProgrammingError`` (not caught) left ``super().cancel()``
unreached, the task was never canceled.

Review of the fix: the interruption (PQcancel, which waits for the server) runs
in a thread of its own and never after the worker released its connections; the
worker rolls back then closes (an interrupted statement aborts the transaction),
and drops nothing: the views of a canceled task are handled by finished(), which
drops only those the task created and nothing uses. The methods are extracted
from filter_task.py with ast, the plugin module itself is never imported.
"""
import ast
import sqlite3
import threading
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parents[4]
_METHODS = ("cancel", "_interrupt_queries", "_release_worker_resources", "_close_main_thread_connections",
            "_cleanup_canceled_task_views", "_drop_deferred_views", "_execute_postgresql_commands")
_DEFERRED = {}


class _QgsTask:
    def __init__(self):
        self.canceled = False

    def cancel(self):
        self.canceled = True

    def isCanceled(self):
        return self.canceled

    def description(self):
        return "Filtering data"


class _Thread:
    """threading.Thread run at once (the test sees the interruption)."""
    started = []

    def __init__(self, target, args=(), name=None, daemon=None):
        self.target, self.args, self.daemon = target, args, daemon

    def start(self):
        _Thread.started.append(self)
        self.target(*self.args)


def _created_view_pattern():
    tree = ast.parse((PLUGIN_ROOT / "core" / "tasks" / "filter_task.py").read_text(encoding="utf-8"))
    node = next(node for node in tree.body if isinstance(node, ast.Assign)
                and any(getattr(target, "id", "") == "_CREATED_VIEW" for target in node.targets))
    namespace = {"re": __import__("re")}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "filter_task.py", "exec"), namespace)
    return namespace["_CREATED_VIEW"]


def _task_class(project_layers=None, active_tasks=()):
    tree = ast.parse((PLUGIN_ROOT / "core" / "tasks" / "filter_task.py").read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterEngineTask")
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in _METHODS]
    assert len(methods) == len(_METHODS)
    holder = ast.ClassDef(name="_Task", bases=[ast.Name(id="QgsTask", ctx=ast.Load())], keywords=[],
                          body=methods, decorator_list=[])
    project = types.SimpleNamespace(mapLayers=lambda: dict(project_layers or {}))
    namespace = {"QgsTask": _QgsTask, "logger": MagicMock(), "DEFAULT_TEMP_SCHEMA": "filtermate_temp",
                 "threading": types.SimpleNamespace(Thread=_Thread, Lock=threading.Lock),
                 "QgsProject": types.SimpleNamespace(instance=lambda: project), "_DEFERRED_VIEW_DROPS": _DEFERRED,
                 "_CREATED_VIEW": _created_view_pattern(), "List": list, "Any": object}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[holder], type_ignores=[])), "filter_task.py", "exec"),
         namespace)
    return namespace["_Task"]


def _task(*connections, **kwargs):
    task = _task_class(**kwargs)()
    task.active_connections = list(connections)
    task._connections_lock = threading.Lock()
    task._connections_released = False
    task._ps_manager = object()
    task._task_postgresql_connection = connections[0] if connections else None
    _Thread.started = []
    return task


def _worker_sqlite_connection():
    """An sqlite3 connection created in another thread, as the subset handler does in run()."""
    box = {}
    thread = threading.Thread(target=lambda: box.setdefault("conn", sqlite3.connect(":memory:")))
    thread.start()
    thread.join()
    return box["conn"]


def _pg_connection():
    conn = MagicMock(spec=["cancel", "close", "closed", "cursor", "rollback"])
    conn.closed = 0
    return conn


def test_cancel_with_a_worker_sqlite_connection_cancels_the_task():
    conn = _worker_sqlite_connection()
    task = _task(conn)
    task.cancel()  # raised sqlite3.ProgrammingError before
    assert task.isCanceled()
    assert task.active_connections == [conn]  # left to the worker
    assert _Thread.started == []  # nothing to interrupt


def test_cancel_interrupts_the_postgresql_query_from_its_own_thread():
    conn = _pg_connection()
    task = _task(conn)
    task.cancel()
    assert len(_Thread.started) == 1 and _Thread.started[0].daemon  # PQcancel off the main thread
    conn.cancel.assert_called_once_with()
    conn.close.assert_not_called()
    assert task.isCanceled()


def test_no_interruption_once_the_worker_released_its_connections():
    conn = _pg_connection()
    task = _task(conn)
    task._release_worker_resources()
    conn.closed = 1
    task._interrupt_queries([conn])  # a late cancel thread
    conn.cancel.assert_not_called()


def test_a_failing_interrupt_still_cancels():
    conn = _pg_connection()
    conn.cancel.side_effect = RuntimeError("server gone")
    task = _task(conn)
    task.cancel()
    assert task.isCanceled()


def test_the_worker_rolls_back_then_closes_and_drops_nothing():
    conn = _pg_connection()
    task = _task(conn)
    task._cleanup_postgresql_materialized_views = MagicMock()
    task.cancel()
    task._release_worker_resources()
    task._cleanup_postgresql_materialized_views.assert_not_called()  # no DROP from the worker
    assert [call[0] for call in conn.method_calls][-2:] == ["rollback", "close"]
    assert task.active_connections == [] and task._ps_manager is None
    assert task._task_postgresql_connection is None  # never handed out again, aborted or closed


def test_the_worker_closes_its_sqlite_connections_after_a_normal_run():
    conn = sqlite3.connect(":memory:")
    task = _task(conn)
    task._release_worker_resources()
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("select 1")  # closed
    assert task.active_connections == []


def test_a_failing_rollback_still_closes():
    conn = _pg_connection()
    conn.rollback.side_effect = Exception("InFailedSqlTransaction")
    task = _task(conn)
    task._release_worker_resources()
    conn.close.assert_called_once_with()


def _layer(layer_id, subset=""):
    layer = MagicMock()
    layer.id.return_value = layer_id
    layer.subsetString.return_value = subset
    return layer


def _canceled_task(created, subsets):
    layers = {f"l{index}": _layer(f"l{index}", subset) for index, subset in enumerate(subsets)}
    task = _task(project_layers=layers)
    task.source_layer = _layer("src")
    task.param_all_layers = [_layer("tgt")]
    task._created_mv_names = set(created)
    task._cleanup_handler = MagicMock()
    task._cleanup_handler.drop_task_materialized_views.return_value = []
    task._get_valid_postgresql_connection = MagicMock()
    return task


def _qgis_core(monkeypatch, active):
    qgis_core = types.SimpleNamespace(QgsApplication=types.SimpleNamespace(
        taskManager=lambda: types.SimpleNamespace(activeTasks=lambda: list(active))))
    monkeypatch.setitem(__import__("sys").modules, "qgis.core", qgis_core)


def test_a_canceled_task_drops_only_its_views_nothing_uses(monkeypatch):
    _DEFERRED.clear()
    _qgis_core(monkeypatch, [])
    task = _canceled_task({"fm_temp_mv_a", "fm_temp_mv_b"}, ['"id" IN (SELECT pk FROM "t"."fm_temp_mv_b")', ''])
    task._cleanup_canceled_task_views()
    task._cleanup_handler.drop_task_materialized_views.return_value = ["fm_temp_mv_a"]
    task._drop_deferred_views()
    args, kwargs = task._cleanup_handler.drop_task_materialized_views.call_args
    assert args[0] == {"fm_temp_mv_a", "fm_temp_mv_b"} and args[1] == ["src", "tgt"]
    assert kwargs["in_use_fn"]("fm_temp_mv_b") is True  # read by a subset in place: kept
    assert kwargs["in_use_fn"]("fm_temp_mv_a") is False
    assert _DEFERRED == {}  # dropped or read: nothing left for later


def test_views_wait_while_another_filter_task_runs(monkeypatch):
    """The second click: the first task's finished() runs while the second one fills its views."""
    class FilterEngineTask:
        pass

    _DEFERRED.clear()
    _qgis_core(monkeypatch, [FilterEngineTask()])
    task = _canceled_task({"fm_temp_mv_a"}, [''])
    task._cleanup_canceled_task_views()
    task._drop_deferred_views()
    task._cleanup_handler.drop_task_materialized_views.assert_not_called()
    assert "fm_temp_mv_a" in _DEFERRED
    _qgis_core(monkeypatch, [])  # the second task's finished(): nothing runs any more
    later = _canceled_task(set(), [''])
    later._cleanup_handler.drop_task_materialized_views.return_value = ["fm_temp_mv_a"]
    later._drop_deferred_views()
    assert later._cleanup_handler.drop_task_materialized_views.call_args.args[0] == {"fm_temp_mv_a"}
    assert _DEFERRED == {}


def test_the_views_a_task_creates_are_recorded():
    task = _task()
    task._mv_handler = MagicMock()
    task._execute_postgresql_commands(MagicMock(), [
        'DROP MATERIALIZED VIEW IF EXISTS "filter_mate_temp"."fm_temp_mv_old" CASCADE;',
        'CREATE MATERIALIZED VIEW IF NOT EXISTS "filter_mate_temp"."fm_temp_mv_session_ab_12" AS SELECT 1',
    ])
    assert task._created_mv_names == {"fm_temp_mv_session_ab_12"}  # created, not the one dropped


def test_finished_closes_the_connections_it_opened():
    conn = _pg_connection()
    task = _task(conn)
    task._close_main_thread_connections()
    conn.close.assert_called_once_with()
    assert task.active_connections == [] and task._task_postgresql_connection is None


def test_run_releases_the_worker_resources_whatever_happens():
    tree = ast.parse((PLUGIN_ROOT / "core" / "tasks" / "filter_task.py").read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterEngineTask")
    run = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "run")
    tries = [node for node in run.body if isinstance(node, ast.Try)]
    assert tries, "run() has no try block"
    final = ast.dump(ast.Module(body=tries[-1].finalbody, type_ignores=[]))
    assert "_release_worker_resources" in final
