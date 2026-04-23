# -*- coding: utf-8 -*-
"""
Integration-style tests for FavoritesManager against a real SQLite DB.

Covers the audit fixes that are only meaningful end-to-end:
    - CRIT-1 : add_favorite(preserve_timestamps=True) keeps created_at/updated_at
    - HIGH-3 : increment_use_count does not bump updated_at
    - HIGH-1 : _backfill_remote_layer_signatures rewrites legacy rows
    - LOW-4  : composite index idx_favorites_project_name is created
    - MED-5  : remove_favorite returns False when DB not initialised

These tests use tempfile SQLite — they do NOT need QGIS runtime.
"""

import importlib.util
import os
import sqlite3
import tempfile
import time

import pytest


def _load_favorites_module():
    plugin_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )))
    path = os.path.join(plugin_root, "core", "domain", "favorites_manager.py")
    spec = importlib.util.spec_from_file_location("_fm_fav_persist", path)
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules["_fm_fav_persist"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def favorites_module():
    return _load_favorites_module()


@pytest.fixture
def manager(favorites_module, tmp_path):
    """Fresh FavoritesManager bound to a per-test SQLite file."""
    db = tmp_path / "test_favorites.sqlite"
    mgr = favorites_module.FavoritesManager(
        db_path=str(db),
        project_uuid="test-project-uuid-1",
    )
    assert mgr._initialized, "FavoritesManager failed to initialise"
    return mgr


# ─── CRIT-1 : timestamps preservation ──────────────────────────────────


def test_add_favorite_stamps_timestamps_by_default(manager, favorites_module):
    """Default behaviour: created_at / updated_at are set to now()."""
    fav = favorites_module.FilterFavorite(
        name="A", expression="TRUE",
        created_at="", updated_at="",
    )
    assert manager.add_favorite(fav) is True
    assert fav.created_at  # was empty, now set
    assert fav.updated_at == fav.created_at


def test_add_favorite_preserves_timestamps_when_asked(manager, favorites_module):
    """preserve_timestamps=True + non-empty timestamps → untouched."""
    original_created = "2025-01-15T10:00:00"
    original_updated = "2025-01-20T11:00:00"
    fav = favorites_module.FilterFavorite(
        name="B", expression="TRUE",
        created_at=original_created,
        updated_at=original_updated,
    )
    assert manager.add_favorite(fav, preserve_timestamps=True) is True
    assert fav.created_at == original_created
    assert fav.updated_at == original_updated


def test_add_favorite_preserve_with_empty_timestamps_still_stamps(manager, favorites_module):
    """preserve_timestamps=True but empty timestamps → set to now() anyway."""
    fav = favorites_module.FilterFavorite(
        name="C", expression="TRUE",
        created_at="", updated_at="",
    )
    assert manager.add_favorite(fav, preserve_timestamps=True) is True
    assert fav.created_at != ""
    assert fav.updated_at == fav.created_at


# ─── HIGH-3 : increment_use_count doesn't bump updated_at ──────────────


def test_increment_use_count_does_not_bump_updated_at(manager, favorites_module):
    fav = favorites_module.FilterFavorite(name="D", expression="TRUE")
    manager.add_favorite(fav)

    original_updated_at = fav.updated_at

    # Sleep a tick so any accidental now() call would produce a different value
    time.sleep(0.05)

    assert manager.increment_use_count(fav.id) is True
    refreshed = manager.get_favorite(fav.id)
    assert refreshed.use_count == 1
    assert refreshed.updated_at == original_updated_at, (
        "increment_use_count must not mutate updated_at "
        f"(was {original_updated_at}, now {refreshed.updated_at})"
    )
    assert refreshed.last_used_at is not None


def test_update_favorite_still_bumps_updated_at_by_default(manager, favorites_module):
    fav = favorites_module.FilterFavorite(name="E", expression="TRUE")
    manager.add_favorite(fav)

    original_updated_at = fav.updated_at
    time.sleep(0.05)

    assert manager.update_favorite(fav.id, description="changed") is True
    refreshed = manager.get_favorite(fav.id)
    assert refreshed.description == "changed"
    assert refreshed.updated_at != original_updated_at, (
        "Real edits must still bump updated_at"
    )


# ─── HIGH-1 : signature backfill on init ───────────────────────────────


def test_backfill_preserves_legacy_remote_layers_when_no_qgis(tmp_path, favorites_module):
    """Without a running QgsProject the backfill bails out cleanly — legacy
    rows must remain readable (not rewritten, not corrupted).
    """
    db = tmp_path / "legacy.sqlite"
    import json
    # Seed a legacy-shape row (name-keyed remote_layers, no signature)
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE fm_favorites (
            id TEXT PRIMARY KEY,
            project_uuid TEXT NOT NULL,
            name TEXT NOT NULL,
            expression TEXT NOT NULL,
            layer_name TEXT,
            layer_id TEXT,
            layer_provider TEXT,
            description TEXT,
            tags TEXT,
            created_at TEXT,
            updated_at TEXT,
            use_count INTEGER DEFAULT 0,
            last_used_at TEXT,
            remote_layers TEXT,
            spatial_config TEXT
        );
    """)
    cur.execute(
        "INSERT INTO fm_favorites (id, project_uuid, name, expression, remote_layers) "
        "VALUES (?, ?, ?, ?, ?)",
        ("legacy-1", "test-project-uuid-1", "Legacy",
         "TRUE",
         json.dumps({"Old Name": {"expression": "x=1", "layer_id": "gone"}})),
    )
    conn.commit()
    conn.close()

    # Now let FavoritesManager migrate / load — without QGIS, backfill is a no-op
    mgr = favorites_module.FavoritesManager(
        db_path=str(db), project_uuid="test-project-uuid-1"
    )
    assert mgr._initialized

    fav = mgr.get_favorite("legacy-1")
    assert fav is not None
    # from_dict normalizes: adds display_name default when missing
    assert "Old Name" in fav.remote_layers
    assert fav.remote_layers["Old Name"]["display_name"] == "Old Name"


# ─── LOW-4 : composite index creation ──────────────────────────────────


def test_composite_index_is_created(manager):
    """idx_favorites_project_name must exist after _initialize_database."""
    conn = sqlite3.connect(manager._db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='index'")
    index_names = {row[0] for row in cur.fetchall()}
    conn.close()

    assert "idx_favorites_project" in index_names, \
        "Legacy project-only index must remain"
    assert "idx_favorites_project_name" in index_names, \
        "LOW-4 composite index must be created"


# ─── MED-5 : graceful failure when DB not initialised ──────────────────


def test_remove_favorite_returns_false_when_uninitialised(favorites_module):
    mgr = favorites_module.FavoritesManager()  # no db_path → not initialised
    assert mgr._initialized is False
    assert mgr.remove_favorite("anything") is False


def test_remove_favorite_returns_false_for_unknown_id(manager):
    assert manager.remove_favorite("this-id-does-not-exist") is False


# ─── End-to-end: add → export shape → reload ────────────────────────────


def test_full_cycle_add_reload(manager, favorites_module):
    """Add, close manager, re-open pointing at same DB — favorite survives."""
    fav = favorites_module.FilterFavorite(
        name="Zone",
        expression='"z" = 1',
        tags=["a", "b"],
        description="desc",
    )
    manager.add_favorite(fav)
    fav_id = fav.id
    db_path = manager._db_path

    # New manager instance on the same file
    mgr2 = favorites_module.FavoritesManager(
        db_path=db_path, project_uuid="test-project-uuid-1"
    )
    reloaded = mgr2.get_favorite(fav_id)
    assert reloaded is not None
    assert reloaded.name == "Zone"
    assert reloaded.tags == ["a", "b"]
    assert reloaded.description == "desc"
    assert reloaded.expression == '"z" = 1'
