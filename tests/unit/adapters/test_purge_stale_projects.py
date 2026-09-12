# -*- coding: utf-8 -*-
"""
PERF 2026-09-12: ``purge_stale_projects`` removes FilterMate rows of unsaved
projects (no name, no path) older than the threshold, and nothing else.

``database_manager`` is loaded in a private package whose two-dot imports
(task_utils, feedback) are stubbed, so the real module body runs against an
in-memory sqlite database.
"""

import importlib.util
import sqlite3
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_REPO = Path(__file__).resolve().parents[3]
_PKG = "fmtest_dbm_pkg"


def _register(name, path=None):
    mod = types.ModuleType(name)
    mod.__path__ = [path] if path else []
    mod.__package__ = name
    sys.modules[name] = mod
    return mod


def _load_database_manager():
    full = f"{_PKG}.adapters.database_manager"
    if full in sys.modules:
        return sys.modules[full]
    _register(_PKG)
    _register(f"{_PKG}.adapters", str(_REPO / "adapters"))
    _register(f"{_PKG}.infrastructure")
    _register(f"{_PKG}.infrastructure.utils")
    task_utils = MagicMock()
    task_utils.sqlite_connect = MagicMock()
    sys.modules[f"{_PKG}.infrastructure.utils.task_utils"] = task_utils
    feedback = MagicMock()
    feedback.show_error = MagicMock()
    sys.modules[f"{_PKG}.infrastructure.feedback"] = feedback

    spec = importlib.util.spec_from_file_location(full, _REPO / "adapters" / "database_manager.py")
    module = importlib.util.module_from_spec(spec)
    module.__package__ = f"{_PKG}.adapters"
    sys.modules[full] = module
    spec.loader.exec_module(module)
    return module


_DDL = """
CREATE TABLE fm_projects (
    project_id TEXT NOT NULL PRIMARY KEY,
    _created_at DATETIME NOT NULL,
    _updated_at DATETIME NOT NULL,
    project_name TEXT NOT NULL,
    project_path TEXT NOT NULL,
    project_settings TEXT NOT NULL
);
CREATE TABLE fm_subset_history (
    id TEXT NOT NULL PRIMARY KEY,
    _updated_at DATETIME NOT NULL,
    fk_project TEXT NOT NULL,
    layer_id TEXT NOT NULL,
    layer_source_id TEXT NOT NULL,
    seq_order INTEGER NOT NULL,
    subset_string TEXT NOT NULL
);
CREATE TABLE fm_project_layers_properties (
    id TEXT NOT NULL PRIMARY KEY,
    _updated_at DATETIME NOT NULL,
    fk_project TEXT NOT NULL,
    layer_id TEXT NOT NULL,
    meta_type TEXT NOT NULL,
    meta_key TEXT NOT NULL,
    meta_value TEXT NOT NULL
);
"""


def _add_project(cur, pid, name, path, days_old, n_props=3, n_hist=1):
    cur.execute(
        "INSERT INTO fm_projects VALUES (?, datetime('now', ?), datetime('now', ?), ?, ?, '{}')",
        (pid, f"-{days_old} days", f"-{days_old} days", name, path),
    )
    for i in range(n_props):
        cur.execute(
            "INSERT INTO fm_project_layers_properties VALUES (?, datetime('now'), ?, 'layer', 'infos', ?, 'v')",
            (f"{pid}-p{i}", pid, f"key{i}"),
        )
    for i in range(n_hist):
        cur.execute(
            "INSERT INTO fm_subset_history VALUES (?, datetime('now'), ?, 'layer', 'src', ?, 'x = 1')",
            (f"{pid}-h{i}", pid, i),
        )


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(_DDL)
    yield conn
    conn.close()


def _count(conn, table, pid=None):
    if pid is None:
        return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]  # nosec B608 - test DDL names
    col = "project_id" if table == "fm_projects" else "fk_project"
    return conn.execute(f"SELECT count(*) FROM {table} WHERE {col} = ?", (pid,)).fetchone()[0]  # nosec B608


@pytest.mark.unit
class TestPurgeStaleProjects:

    def test_only_old_unsaved_projects_are_removed(self, db):
        dbm = _load_database_manager()
        cur = db.cursor()
        _add_project(cur, "saved-old", "bdd.qgz", "C:/proj", days_old=400)
        _add_project(cur, "unsaved-old", "", "", days_old=60)
        _add_project(cur, "unsaved-recent", "", "", days_old=2)
        _add_project(cur, "current-session", "", "", days_old=90)
        db.commit()

        purged = dbm.purge_stale_projects(cur, keep_project_uuid="current-session", max_age_days=30)
        db.commit()

        assert purged == 1
        assert _count(db, "fm_projects", "unsaved-old") == 0
        assert _count(db, "fm_project_layers_properties", "unsaved-old") == 0
        assert _count(db, "fm_subset_history", "unsaved-old") == 0
        for kept in ("saved-old", "unsaved-recent", "current-session"):
            assert _count(db, "fm_projects", kept) == 1
            assert _count(db, "fm_project_layers_properties", kept) == 3
            assert _count(db, "fm_subset_history", kept) == 1

    def test_nothing_to_purge(self, db):
        dbm = _load_database_manager()
        cur = db.cursor()
        _add_project(cur, "saved", "a.qgz", "/tmp/a", days_old=900)  # nosec B108
        assert dbm.purge_stale_projects(cur) == 0
        assert _count(db, "fm_projects") == 1

    def test_large_batches_are_chunked(self, db):
        dbm = _load_database_manager()
        cur = db.cursor()
        for i in range(450):
            _add_project(cur, f"ghost-{i}", "", "", days_old=45, n_props=1, n_hist=0)
        # "alive" is both the session project and the newest unsaved row
        _add_project(cur, "alive", "", "", days_old=10, n_props=1, n_hist=0)
        db.commit()

        assert dbm.purge_stale_projects(cur, keep_project_uuid="alive", max_age_days=30) == 450
        assert _count(db, "fm_projects") == 1
        assert _count(db, "fm_project_layers_properties") == 1

    def test_newest_unsaved_project_survives_even_when_old(self, db):
        """_load_or_create_project reuses the most recent unsaved row: never purge it."""
        dbm = _load_database_manager()
        cur = db.cursor()
        _add_project(cur, "saved", "a.qgz", "/tmp/a", days_old=1)  # nosec B108
        _add_project(cur, "orphan-older", "", "", days_old=90)
        _add_project(cur, "orphan-newest", "", "", days_old=45)
        db.commit()

        assert dbm.purge_stale_projects(cur, keep_project_uuid="saved", max_age_days=30) == 1
        assert _count(db, "fm_projects", "orphan-newest") == 1
        assert _count(db, "fm_project_layers_properties", "orphan-newest") == 3
        assert _count(db, "fm_projects", "orphan-older") == 0

    def test_failure_rolls_back_every_delete(self, db):
        dbm = _load_database_manager()
        cur = db.cursor()
        _add_project(cur, "orphan-a", "", "", days_old=90)
        _add_project(cur, "orphan-b", "", "", days_old=80)
        _add_project(cur, "orphan-newest", "", "", days_old=70)
        db.commit()
        # Break the second DELETE target so the purge fails half-way
        cur.execute("DROP TABLE fm_subset_history")

        with pytest.raises(sqlite3.OperationalError):
            dbm.purge_stale_projects(cur, max_age_days=30)
        db.commit()

        assert _count(db, "fm_projects") == 3
        assert _count(db, "fm_project_layers_properties") == 9

    def test_default_threshold_constant(self):
        dbm = _load_database_manager()
        assert dbm.STALE_PROJECT_MAX_AGE_DAYS == 30
