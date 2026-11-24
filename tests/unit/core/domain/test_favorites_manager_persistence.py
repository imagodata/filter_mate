# -*- coding: utf-8 -*-
"""
Integration-style tests for FavoritesManager against a real SQLite DB.

Covers the audit fixes that are only meaningful end-to-end:
    - CRIT-1 : add_favorite(preserve_timestamps=True) keeps created_at/updated_at
    - HIGH-3 : increment_use_count does not bump updated_at
    - HIGH-1 : _backfill_remote_layer_signatures rewrites legacy rows
    - LOW-4  : composite index idx_favorites_project_name is created
    - MED-5  : remove_favorite raises FavoritesNotInitialized when DB
               not initialised (F16 phase 2 — was a silent ``return False``)

These tests use tempfile SQLite — they do NOT need QGIS runtime.
"""

import importlib.util
import os
import sqlite3
import tempfile
import time

import pytest


def _load_favorites_module():
    import sys
    import types

    plugin_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )))

    # favorites_manager.py uses relative imports (from .schema_constants).
    # Register a stand-in parent package so those imports resolve when the
    # module is loaded outside the real plugin namespace.
    pkg_name = "_fm_fav_persist_pkg"
    if pkg_name not in sys.modules:
        pkg = types.ModuleType(pkg_name)
        pkg.__path__ = [os.path.join(plugin_root, "core", "domain")]
        sys.modules[pkg_name] = pkg

    sc_full = f"{pkg_name}.schema_constants"
    if sc_full not in sys.modules:
        sc_path = os.path.join(plugin_root, "core", "domain", "schema_constants.py")
        sc_spec = importlib.util.spec_from_file_location(sc_full, sc_path)
        sc_module = importlib.util.module_from_spec(sc_spec)
        sys.modules[sc_full] = sc_module
        sc_spec.loader.exec_module(sc_module)

    fm_full = f"{pkg_name}.favorites_manager"
    path = os.path.join(plugin_root, "core", "domain", "favorites_manager.py")
    spec = importlib.util.spec_from_file_location(fm_full, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[fm_full] = module
    sys.modules["_fm_fav_persist"] = module  # legacy alias
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


# ─── MED-5 / F16 phase 2 : surface DB-not-initialised vs. unknown-id ────


def test_remove_favorite_raises_when_uninitialised(favorites_module):
    """F16 phase 2: bootstrap precondition raises rather than silently
    returning False — the previous silent return masked an UI-vs-DB
    divergence that's now surfaced via Qt's exception hook.
    """
    mgr = favorites_module.FavoritesManager()  # no db_path → not initialised
    assert mgr._initialized is False
    with pytest.raises(favorites_module.FavoritesNotInitialized):
        mgr.remove_favorite("anything")


def test_remove_favorite_returns_false_for_unknown_id(manager):
    """Unknown id stays a soft return-False — innocent lookup miss
    (stale UI reference / external DB delete). F16 phase 2 split this
    from the bootstrap-precondition case which now raises.
    """
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


# ─── 2026-11-24 : the project is the truth for its favorites ──────────


def test_replace_project_favorites_mirrors_the_list_and_keeps_the_ids(manager, favorites_module):
    """The favorites of the .qgz replace those of the project in the SQLite, under the ids the project gave them."""
    fav = favorites_module.FilterFavorite
    manager.add_favorite(fav(name="removed elsewhere", expression="TRUE"))
    kept = fav(id="kept-id", name="kept", expression="TRUE")
    manager.add_favorite(kept)
    manager.replace_project_favorites([
        fav(id="kept-id", name="kept, renamed elsewhere", expression="TRUE", use_count=3),
        fav(id="new-id", name="added elsewhere", expression="FALSE", created_at="2026-11-01T10:00:00",
            updated_at="2026-11-02T10:00:00"),
    ])
    assert sorted(f.name for f in manager.get_all_favorites()) == ["added elsewhere", "kept, renamed elsewhere"]
    assert manager.get_favorite("new-id").updated_at == "2026-11-02T10:00:00"
    # read back from the SQLite, not only the cache
    manager.set_database(manager._db_path, manager._project_uuid)
    assert sorted(f.id for f in manager.get_all_favorites()) == ["kept-id", "new-id"]
    assert manager.get_favorite("kept-id").use_count == 3


def test_replace_project_favorites_leaves_a_row_of_another_project_with_the_same_id(manager, favorites_module):
    """A copied .qgz carries ids the SQLite already has under the original project (``id`` is the primary key). Review
    of 2026-11-24: the row was taken from the original, whose favorites were lost when its file did not list them.
    The copy takes an id derived from it, the same at each opening."""
    fav = favorites_module.FilterFavorite
    manager.add_favorite(fav(id="shared-id", name="in the original", expression="TRUE"))
    copy = favorites_module.FavoritesManager(db_path=manager._db_path, project_uuid="test-project-uuid-2")
    copy.replace_project_favorites([fav(id="shared-id", name="in the copy", expression="TRUE")])
    [taken] = copy.get_all_favorites()
    assert taken.name == "in the copy" and taken.id != "shared-id"
    copy.replace_project_favorites([fav(id="shared-id", name="in the copy", expression="TRUE")])
    assert [f.id for f in copy.get_all_favorites()] == [taken.id]
    manager.set_database(manager._db_path, manager._project_uuid)
    assert [f.name for f in manager.get_all_favorites()] == ["in the original"]


def test_the_ids_of_the_project_file_are_remembered_per_project(manager, favorites_module):
    assert manager.known_file_ids() == []
    manager.remember_file_ids(["b", "a", "a"])
    other = favorites_module.FavoritesManager(db_path=manager._db_path, project_uuid="test-project-uuid-2")
    assert other.known_file_ids() == []
    manager.set_database(manager._db_path, manager._project_uuid)
    assert manager.known_file_ids() == ["a", "b"]


def test_replace_project_favorites_leaves_the_global_favorites(manager, favorites_module):
    fav = favorites_module.FilterFavorite
    manager.add_favorite(fav(name="local", expression="TRUE"))
    global_id = manager.copy_to_global(manager.get_all_favorites()[0].id)
    manager.replace_project_favorites([])
    assert manager.get_all_favorites() == []
    assert global_id in [f.id for f in manager.get_global_favorites()]


def test_remove_global_favorite_deletes_only_a_global_one(manager, favorites_module):
    fav = favorites_module.FilterFavorite
    manager.add_favorite(fav(name="local", expression="TRUE"))
    local_id = manager.get_all_favorites()[0].id
    global_id = manager.copy_to_global(local_id)

    assert manager.remove_global_favorite(local_id) is False  # a project favorite stays
    assert manager.get_favorite(local_id) is not None
    assert manager.remove_global_favorite(global_id) is True
    assert manager.get_global_favorites() == []
    assert manager.remove_global_favorite(global_id) is False


def test_remove_global_favorite_before_set_database_raises(favorites_module):
    from _fm_fav_persist_pkg.exceptions import FavoritesNotInitialized
    with pytest.raises(FavoritesNotInitialized):
        favorites_module.FavoritesManager().remove_global_favorite("x")


def test_global_favorites_carry_their_owner(manager, favorites_module):
    manager.set_current_user("alice")
    manager.add_favorite(favorites_module.FilterFavorite(name="local", expression="TRUE"))
    manager.copy_to_global(manager.get_all_favorites()[0].id)
    assert [f.owner for f in manager.get_global_favorites()] == ["alice"]
