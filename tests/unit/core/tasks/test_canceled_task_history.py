# -*- coding: utf-8 -*-
"""2026-11-18: the history rows a canceled filter task inserted are deleted by its finished(), its own only.

A second click on Filter cancels the running task A and starts B. A's run() may have inserted its entry
already; A's subsets are dropped, but its entry stayed: after B, Unfilter applied A's filter, never set.
The methods of FilterEngineTask are extracted from filter_task.py with ast (the plugin module is never
imported), with the real history modules and a real sqlite file.
"""
import ast
import importlib.util
import sqlite3
import threading
import types
import typing
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from filtermate_core.domain.layer_facts import id_of

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parents[4]
_METHODS = ("_insert_subset_history", "_execute_geometric_filtering_recorded", "_discard_canceled_history",
            "_discard_refused_source_history", "_discard_own_history_of")


def _load(name, relative):
    spec = importlib.util.spec_from_file_location(name, PLUGIN_ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def env(tmp_path):
    repo = _load("fm_canceled_history_repo", "adapters/repositories/history_repository.py")
    snapshot = _load("fm_canceled_history_snapshot", "core/tasks/history_snapshot.py")
    db = str(tmp_path / "filterMate_db.sqlite")
    with sqlite3.connect(db) as conn:
        conn.execute("""CREATE TABLE fm_subset_history (id TEXT PRIMARY KEY, _updated_at DATETIME NOT NULL,
            fk_project TEXT NOT NULL, layer_id TEXT NOT NULL, layer_source_id TEXT NOT NULL,
            seq_order INTEGER NOT NULL, subset_string TEXT NOT NULL)""")
        conn.execute("INSERT INTO fm_subset_history VALUES ('f0', datetime(), 'p', 'cables', 'zones', 1, 'F0')")

    tree = ast.parse((PLUGIN_ROOT / "core" / "tasks" / "filter_task.py").read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterEngineTask")
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in _METHODS]
    assert len(methods) == len(_METHODS)
    holder = ast.ClassDef(name="_Task", bases=[], keywords=[], body=methods, decorator_list=[])
    namespace = {"uuid": uuid, "List": typing.List, "logger": MagicMock(), "HistoryRepository": repo.HistoryRepository,
                 "id_of": id_of,
                 "create_prepared_statements": lambda conn, provider_type: None,  # the repository path
                 "note_history_insert": repo.note_history_insert,
                 "recording_history_inserts": repo.recording_history_inserts,
                 "discard_history_rows": snapshot.discard_history_rows}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[holder], type_ignores=[])), "filter_task.py", "exec"),
         namespace)

    def task(ps_manager=None):
        instance = namespace["_Task"]()
        instance.db_file_path, instance.project_uuid = db, "p"
        instance.source_layer = types.SimpleNamespace(id=lambda: "zones")
        instance._ps_manager = ps_manager
        instance._history_inserted_ids = []  # what run() sets before execute_task_run

        def execute_geometric_filtering(provider_type, layer, props):
            conn = sqlite3.connect(db)
            try:
                instance._insert_subset_history(conn.cursor(), conn, layer, props["subset"], 2)
            finally:
                conn.close()
            return True
        instance.execute_geometric_filtering = execute_geometric_filtering
        return instance

    def subsets():
        with sqlite3.connect(db) as conn:
            return [row[0] for row in conn.execute(
                "SELECT subset_string FROM fm_subset_history WHERE layer_id = 'cables' ORDER BY seq_order")]

    return types.SimpleNamespace(task=task, subsets=subsets, db=db, record=repo.recording_history_inserts)


def _in_worker(fn, *args):
    """As the parallel filtering runs it: in a thread of its own."""
    outcome = []
    worker = threading.Thread(target=lambda: outcome.append(fn(*args)))
    worker.start()
    worker.join()
    return outcome[0]


_CABLES = types.SimpleNamespace(id=lambda: "cables")


def test_the_rows_inserted_in_a_worker_thread_are_taken_back(env):
    task_a, task_b = env.task(), env.task()
    assert _in_worker(task_a._execute_geometric_filtering_recorded, "spatialite", _CABLES, {"subset": "F1"})
    _in_worker(task_b._execute_geometric_filtering_recorded, "spatialite", _CABLES, {"subset": "F2"})
    assert env.subsets() == ["F0", "F1", "F2"]
    task_a._discard_canceled_history()  # A canceled by the second click
    assert env.subsets() == ["F0", "F2"]


def test_the_rows_of_the_prepared_statement_are_recorded_too(env):
    class _Prepared:
        def __init__(self, path):
            self.path = path

        def insert_subset_history(self, history_id, project_uuid, layer_id, source_layer_id, seq_order,
                                  subset_string):
            with sqlite3.connect(self.path) as conn:
                conn.execute("INSERT INTO fm_subset_history VALUES (?, datetime(), ?, ?, ?, ?, ?)",
                             (history_id, project_uuid, layer_id, source_layer_id, seq_order, subset_string))
            return True

    task_a = env.task(ps_manager=_Prepared(env.db))
    _in_worker(task_a._execute_geometric_filtering_recorded, "spatialite", _CABLES, {"subset": "F1"})
    assert len(task_a._history_inserted_ids) == 1
    task_a._discard_canceled_history()
    assert env.subsets() == ["F0"]


def test_outside_run_nothing_is_recorded(env):
    task = env.task()
    task._history_inserted_ids = None  # never ran
    assert task._execute_geometric_filtering_recorded("spatialite", _CABLES, {"subset": "F1"})
    task._discard_canceled_history()
    assert env.subsets() == ["F0", "F1"]


# 2026-11-19: a source refused (SourceSelectionError) leaves the queue, and now its history row too, the rows of
# the targets staying; a deferred subset refused after finished() deletes this task's rows only.

def _insert(env, task, layer_id, subset):
    layer = types.SimpleNamespace(id=lambda: layer_id)
    conn = sqlite3.connect(env.db)
    try:
        with env.record(task._history_inserted_ids):   # as run() records its inserts
            task._insert_subset_history(conn.cursor(), conn, layer, subset, 2)
    finally:
        conn.close()


def _all(env):
    with sqlite3.connect(env.db) as conn:
        return sorted(conn.execute("SELECT layer_id, subset_string FROM fm_subset_history").fetchall())


def test_a_refused_source_loses_the_row_run_wrote_for_it_not_those_of_the_targets(env):
    task = env.task()
    task.source_layer = types.SimpleNamespace(id=lambda: "zones")
    _insert(env, task, "zones", "SRC")      # a PostgreSQL source: its row is written before the refusal
    _insert(env, task, "cables", "TARGET")
    task._discard_refused_source_history()
    assert _all(env) == [("cables", "F0"), ("cables", "TARGET")]


def test_a_refused_source_does_not_touch_the_rows_of_an_older_task(env):
    older = env.task()
    older.source_layer = types.SimpleNamespace(id=lambda: "zones")
    _insert(env, older, "zones", "OLDER")
    task = env.task()
    _insert(env, task, "zones", "SRC")
    task._discard_refused_source_history()
    assert _all(env) == [("cables", "F0"), ("zones", "OLDER")]


def test_a_deferred_refusal_deletes_this_tasks_row_and_keeps_the_newer_one(env):
    """[F0, FA, FB] -> [F0] before: the timer of A put back A's snapshot over the row B wrote since."""
    task_a, task_b = env.task(), env.task()
    _insert(env, task_a, "cables", "FA")
    _insert(env, task_b, "cables", "FB")           # B started after A's finished(), before A's timer
    task_a._discard_own_history_of(["cables"])
    assert _all(env) == [("cables", "F0"), ("cables", "FB")]


def test_a_deferred_refusal_of_another_layer_leaves_the_row(env):
    task = env.task()
    _insert(env, task, "cables", "FA")
    task._discard_own_history_of(["conduits"])
    assert _all(env) == [("cables", "F0"), ("cables", "FA")]
