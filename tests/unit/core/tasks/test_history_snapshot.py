# -*- coding: utf-8 -*-
"""The filter history of a layer whose filter the provider refused is put back (2026-11-16).

A task writes fm_subset_history in run(), before its subsets are applied on the main thread: a filter
adds an entry, an unfilter deletes the last one, a reset deletes them all. When the provider then
refuses the subset (a PostgreSQL server gone), the layer keeps its previous filter but its history
had moved: the next unfilter went one step too far back.
"""
import importlib.util
import pathlib
import sqlite3

import pytest

pytestmark = pytest.mark.unit

_PATH = pathlib.Path(__file__).resolve().parents[4] / "core" / "tasks" / "history_snapshot.py"


def _load():
    spec = importlib.util.spec_from_file_location("fm_history_snapshot_test", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def hs():
    return _load()


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "filterMate_db.sqlite")
    with sqlite3.connect(path) as conn:
        conn.execute("""CREATE TABLE fm_subset_history (
            id VARYING CHARACTER(255) NOT NULL PRIMARY KEY, _updated_at DATETIME NOT NULL,
            fk_project VARYING CHARACTER(255) NOT NULL, layer_id VARYING CHARACTER(255) NOT NULL,
            layer_source_id VARYING CHARACTER(255) NOT NULL, seq_order INTEGER NOT NULL,
            subset_string TEXT NOT NULL)""")
        rows = [("a1", "2026-11-16 10:00:00", "p", "cables", "zones", 1, '"id" > 1'),
                ("a2", "2026-11-16 10:01:00", "p", "cables", "zones", 2, '"id" > 2'),
                ("b1", "2026-11-16 10:00:00", "p", "conduits", "zones", 1, '"id" > 5'),
                ("c1", "2026-11-16 10:00:00", "other", "cables", "zones", 1, 'x')]
        conn.executemany("INSERT INTO fm_subset_history VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    return path


def _rows(path, layer_id, project="p"):
    with sqlite3.connect(path) as conn:
        return conn.execute("SELECT id, subset_string FROM fm_subset_history WHERE fk_project = ? AND layer_id = ? "
                            "ORDER BY seq_order", (project, layer_id)).fetchall()


def test_an_unfilter_refused_gets_its_last_entry_back(hs, db):
    snapshot = hs.take_history_snapshot(db, "p", ["cables", "conduits"])
    with sqlite3.connect(db) as conn:  # what the unfilter of both layers did in run()
        conn.execute("DELETE FROM fm_subset_history WHERE id IN ('a2', 'b1')")
    restored = hs.restore_history(db, "p", snapshot, ["cables"])  # only cables was refused
    assert restored == ["cables"]
    assert _rows(db, "cables") == [("a1", '"id" > 1'), ("a2", '"id" > 2')]
    assert _rows(db, "conduits") == []  # applied: its deletion stays


def test_a_refused_filter_loses_the_entry_it_added(hs, db):
    snapshot = hs.take_history_snapshot(db, "p", ["cables"])
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO fm_subset_history VALUES ('a3', '2026-11-16 11:00:00', 'p', 'cables', 'zones', 3, 'y')")
    hs.restore_history(db, "p", snapshot, ["cables"])
    assert _rows(db, "cables") == [("a1", '"id" > 1'), ("a2", '"id" > 2')]


def test_a_refused_reset_gets_the_whole_history_back(hs, db):
    snapshot = hs.take_history_snapshot(db, "p", ["cables"])
    with sqlite3.connect(db) as conn:
        conn.execute("DELETE FROM fm_subset_history WHERE fk_project = 'p' AND layer_id = 'cables'")
    hs.restore_history(db, "p", snapshot, ["cables"])
    assert _rows(db, "cables") == [("a1", '"id" > 1'), ("a2", '"id" > 2')]


def test_other_projects_are_left_alone(hs, db):
    snapshot = hs.take_history_snapshot(db, "p", ["cables"])
    hs.restore_history(db, "p", snapshot, ["cables"])
    assert _rows(db, "cables", project="other") == [("c1", "x")]


def test_a_layer_not_in_the_snapshot_is_not_touched(hs, db):
    snapshot = hs.take_history_snapshot(db, "p", ["conduits"])
    assert hs.restore_history(db, "p", snapshot, ["cables"]) == []
    assert len(_rows(db, "cables")) == 2


@pytest.mark.parametrize("path", [None, "", "/nowhere/filterMate_db.sqlite"])
def test_no_database_no_snapshot(hs, path):
    assert hs.take_history_snapshot(path, "p", ["cables"]) is None
    assert hs.restore_history(path, "p", None, ["cables"]) == []


def test_a_database_without_the_table(hs, tmp_path):
    path = str(tmp_path / "empty.sqlite")
    sqlite3.connect(path).close()
    assert hs.take_history_snapshot(path, "p", ["cables"]) is None


# 2026-11-18: a task canceled by a second click (filter A, then filter B) applies nothing, yet its run()
# may have inserted its entry already. Its finished() deletes exactly the rows it inserted, by the ids
# recorded when they were written, in whatever order the two tasks write and finish.

_REPO_PATH = pathlib.Path(__file__).resolve().parents[4] / "adapters" / "repositories" / "history_repository.py"


@pytest.fixture
def repo():
    spec = importlib.util.spec_from_file_location("fm_history_repository_test", _REPO_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Task:
    """What a filter task does with the history: snapshot when run() starts, rows inserted, finished()."""

    def __init__(self, hs, repo, db, layer="cables"):
        self.hs, self.repo, self.db, self.layer = hs, repo, db, layer
        self.inserted = []
        self.snapshot = None

    def start(self):
        self.snapshot = self.hs.take_history_snapshot(self.db, "p", [self.layer])

    def write(self, subset, seq_order):
        """The insert of run(), in a thread of its own, recorded as run() records it."""
        import threading

        def insert():
            with self.repo.recording_history_inserts(self.inserted):
                conn = sqlite3.connect(self.db)
                try:
                    self.repo.HistoryRepository(conn).insert("p", self.layer, subset, seq_order, "zones")
                finally:
                    conn.close()
        worker = threading.Thread(target=insert)
        worker.start()
        worker.join()

    def finish_canceled(self):
        self.hs.discard_history_rows(self.db, "p", self.inserted)

    def finish_refused(self):
        self.hs.restore_history(self.db, "p", self.snapshot, [self.layer])


def _subsets(path):
    return [subset for _id, subset in _rows(path, "cables")]


def test_the_inserts_of_a_thread_are_recorded_in_its_list_only(repo, db):
    import threading
    mine = []
    with repo.recording_history_inserts(mine):
        conn = sqlite3.connect(db)
        row_id = repo.HistoryRepository(conn).insert("p", "cables", "x", 3, "zones")
        worker = threading.Thread(target=lambda: repo.HistoryRepository(sqlite3.connect(db)).insert(
            "p", "cables", "y", 4, "zones"))  # another thread, not recording: not in my list
        worker.start()
        worker.join()
        conn.close()
    assert mine == [row_id]
    assert repo.recorded_history_inserts() is None  # the recording ends with the block


@pytest.mark.parametrize("b_refused", [False, True])
def test_a_canceled_task_finished_before_the_newer_one_writes(hs, repo, db, b_refused):
    """A writes F1, B starts (its snapshot holds F1), A's finished(), then B writes F2."""
    task_a, task_b = _Task(hs, repo, db), _Task(hs, repo, db)
    task_a.start()
    task_a.write("F1", 3)
    task_b.start()
    assert "F1" in [row[-1] for row in task_b.snapshot["cables"]]
    task_a.finish_canceled()
    task_b.write("F2", 3)
    if b_refused:
        task_b.finish_refused()  # its snapshot holds F1: not written back
        assert _subsets(db) == ['"id" > 1', '"id" > 2']
    else:
        assert _subsets(db) == ['"id" > 1', '"id" > 2', "F2"]


@pytest.mark.parametrize("b_refused", [False, True])
def test_a_canceled_task_finished_after_the_newer_one(hs, repo, db, b_refused):
    """A writes F1, B starts and writes F2 and finishes, then A's finished() comes (its run() was longer)."""
    task_a, task_b = _Task(hs, repo, db), _Task(hs, repo, db)
    task_a.start()
    task_a.write("F1", 3)
    task_b.start()
    task_b.write("F2", 4)
    if b_refused:
        task_b.finish_refused()  # puts back its snapshot: F0 and F1
    task_a.finish_canceled()  # B's F2 stays, A's F1 goes
    assert _subsets(db) == ['"id" > 1', '"id" > 2'] + ([] if b_refused else ["F2"])


@pytest.mark.parametrize("b_refused", [False, True])
def test_a_canceled_task_that_writes_after_the_newer_one(hs, repo, db, b_refused):
    """A is canceled before its insert: B starts and writes F2 first, A's run() writes F1 late."""
    task_a, task_b = _Task(hs, repo, db), _Task(hs, repo, db)
    task_a.start()
    task_b.start()
    task_b.write("F2", 3)
    task_a.write("F1", 3)  # same seq_order: both read the history before the other's insert
    if b_refused:
        task_b.finish_refused()
    task_a.finish_canceled()
    assert _subsets(db) == ['"id" > 1', '"id" > 2'] + ([] if b_refused else ["F2"])


def test_without_the_history_file_the_ids_are_still_remembered(hs, repo, db):
    """The rows cannot be deleted now (file gone): a later restore still leaves them out."""
    task_a, task_b = _Task(hs, repo, db), _Task(hs, repo, db)
    task_a.start()
    task_a.write("F1", 3)
    task_b.start()
    assert hs.discard_history_rows("/nowhere/filterMate_db.sqlite", "p", task_a.inserted) == 0
    task_b.finish_refused()
    assert _subsets(db) == ['"id" > 1', '"id" > 2']


def test_a_canceled_task_leaves_the_rows_of_other_tasks(hs, db):
    assert hs.discard_history_rows(db, "p", []) == 0
    assert hs.discard_history_rows(db, "p", ["unknown"]) == 0
    assert len(_rows(db, "cables")) == 2


# 2026-11-19: the deletion runs on the main thread, where the file may be locked for writing by the run() of
# the next task: it waited 5.1 s and the row stayed. A short wait now, and the row is deleted at a later finished().

def _locked(path):
    """A connection holding the write lock, as the run() of the next task does while it inserts."""
    conn = sqlite3.connect(path, timeout=0.1, isolation_level=None)
    conn.execute("BEGIN IMMEDIATE")
    return conn


def test_a_locked_file_does_not_block_the_interface(hs, db):
    import time
    locker = _locked(db)
    try:
        started = time.monotonic()
        assert hs.discard_history_rows(db, "p", ["a2"]) == 0
        assert time.monotonic() - started < 2.0   # 5.1 s before
    finally:
        locker.rollback()
        locker.close()
    assert [row[0] for row in _rows(db, "cables")] == ["a1", "a2"]


def test_what_a_locked_file_kept_is_deleted_at_the_next_finished(hs, db):
    locker = _locked(db)
    try:
        hs.discard_history_rows(db, "p", ["a2"])
        assert hs.retry_pending_discards() == 0   # still locked: kept for later
    finally:
        locker.rollback()
        locker.close()
    assert hs.retry_pending_discards() == 1
    assert [row[0] for row in _rows(db, "cables")] == ["a1"]
    assert hs.retry_pending_discards() == 0       # nothing left to retry


def test_a_pending_row_is_not_written_back_by_a_refused_task_meanwhile(hs, db):
    snapshot = hs.take_history_snapshot(db, "p", ["cables"])
    locker = _locked(db)
    try:
        hs.discard_history_rows(db, "p", ["a2"])
    finally:
        locker.rollback()
        locker.close()
    hs.restore_history(db, "p", snapshot, ["cables"])   # the snapshot still holds a2
    hs.retry_pending_discards()
    assert [row[0] for row in _rows(db, "cables")] == ["a1"]


def test_only_the_rows_of_the_given_layers_are_deleted(hs, db):
    assert hs.discard_history_rows(db, "p", ["a2", "b1"], layer_ids=["conduits"]) == 1
    assert [row[0] for row in _rows(db, "cables")] == ["a1", "a2"]
    assert _rows(db, "conduits") == []
    assert hs.discard_history_rows(db, "p", ["a2"], layer_ids=[]) == 0


def test_a_row_of_another_layer_is_not_forgotten_for_the_restore(hs, db):
    """The ids of the layers left out are not remembered as deleted: a refused task puts them back."""
    snapshot = hs.take_history_snapshot(db, "p", ["cables"])
    hs.discard_history_rows(db, "p", ["a2", "b1"], layer_ids=["conduits"])
    hs.restore_history(db, "p", snapshot, ["cables"])
    assert [row[0] for row in _rows(db, "cables")] == ["a1", "a2"]
