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
