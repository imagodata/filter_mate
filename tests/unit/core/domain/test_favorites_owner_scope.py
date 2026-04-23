# -*- coding: utf-8 -*-
"""
Tests for the v5.1 favorites owner/scope feature.

Covers:
- ``owner`` schema migration (ALTER TABLE + backfill to current user)
- Auto-stamp on ``add_favorite`` via ``resolve_current_user`` cascade
- ``list_by_scope`` combinations of (project × owner)
- ``FilterFavorite`` round-trip preserves ``owner``
"""

from __future__ import annotations

import json
import os
import sqlite3
from unittest.mock import patch

import pytest

from core.domain.favorites_manager import (
    FavoriteScope,
    FavoritesManager,
    FilterFavorite,
    GLOBAL_PROJECT_UUID,
)


# ---------------------------------------------------------------------------
# Dataclass round-trip
# ---------------------------------------------------------------------------


class TestFilterFavoriteOwner:
    def test_owner_roundtrips_through_to_dict(self):
        fav = FilterFavorite(name="x", expression="TRUE", owner="alice")
        d = fav.to_dict()
        assert d["owner"] == "alice"

    def test_owner_defaults_to_none(self):
        fav = FilterFavorite()
        assert fav.owner is None

    def test_from_dict_preserves_owner(self):
        fav = FilterFavorite.from_dict({
            "name": "x", "expression": "TRUE", "owner": "bob",
        })
        assert fav.owner == "bob"

    def test_from_dict_without_owner_stays_none(self):
        fav = FilterFavorite.from_dict({"name": "x", "expression": "TRUE"})
        assert fav.owner is None


# ---------------------------------------------------------------------------
# Fixtures for sqlite-backed manager
# ---------------------------------------------------------------------------


PROJECT_A = "11111111-1111-1111-1111-111111111111"
PROJECT_B = "22222222-2222-2222-2222-222222222222"


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "favorites.sqlite")


@pytest.fixture
def manager(db_path):
    """Fresh FavoritesManager bound to PROJECT_A with no identity."""
    mgr = FavoritesManager(db_path=db_path, project_uuid=PROJECT_A)
    # Pin identity explicitly to make tests deterministic — no reliance
    # on whatever the current OS user happens to be.
    mgr.set_current_user("alice")
    return mgr


# ---------------------------------------------------------------------------
# Auto-stamp on add_favorite
# ---------------------------------------------------------------------------


class TestAutoStampOwner:
    def test_new_favorite_gets_current_user(self, manager):
        fav = FilterFavorite(name="f1", expression="TRUE")
        assert manager.add_favorite(fav) is True
        stored = manager.get_favorite_by_name("f1")
        assert stored.owner == "alice"

    def test_explicit_owner_is_preserved(self, manager):
        fav = FilterFavorite(name="f1", expression="TRUE", owner="bob")
        manager.add_favorite(fav)
        assert manager.get_favorite_by_name("f1").owner == "bob"

    def test_no_identity_results_in_null_owner(self, db_path):
        mgr = FavoritesManager(db_path=db_path, project_uuid=PROJECT_A)
        mgr.set_current_user(None)
        fav = FilterFavorite(name="f1", expression="TRUE")
        mgr.add_favorite(fav)
        assert mgr.get_favorite_by_name("f1").owner is None

    def test_preserve_timestamps_path_skips_auto_stamp(self, manager):
        """Import/restore paths must not overwrite a bundled owner."""
        fav = FilterFavorite(
            name="imported", expression="TRUE",
            owner="charlie", created_at="2020-01-01T00:00:00",
        )
        manager.add_favorite(fav, preserve_timestamps=True)
        stored = manager.get_favorite_by_name("imported")
        assert stored.owner == "charlie"

    def test_persists_owner_to_sqlite(self, manager, db_path):
        manager.add_favorite(FilterFavorite(name="f1", expression="TRUE"))
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT owner FROM fm_favorites WHERE name = ?", ("f1",),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "alice"


# ---------------------------------------------------------------------------
# Migration: pre-v5.1 DB has no ``owner`` column
# ---------------------------------------------------------------------------


class TestOwnerMigration:
    def _build_legacy_db(self, path):
        """Create a pre-v5.1 fm_favorites table (no owner column) with one row."""
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE fm_favorites (
                id TEXT PRIMARY KEY,
                project_uuid TEXT NOT NULL,
                name TEXT NOT NULL,
                expression TEXT NOT NULL
            )
        """)
        cursor.execute(
            "INSERT INTO fm_favorites (id, project_uuid, name, expression) "
            "VALUES (?, ?, ?, ?)",
            ("pre-v5-fav", PROJECT_A, "legacy", "TRUE"),
        )
        conn.commit()
        conn.close()

    def test_migration_adds_owner_column(self, db_path):
        self._build_legacy_db(db_path)

        with patch(
            "core.domain.user_identity.resolve_current_user",
            return_value="alice",
        ):
            FavoritesManager(db_path=db_path, project_uuid=PROJECT_A)

        conn = sqlite3.connect(db_path)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(fm_favorites)")}
        owner = conn.execute(
            "SELECT owner FROM fm_favorites WHERE id = 'pre-v5-fav'"
        ).fetchone()[0]
        conn.close()
        assert "owner" in cols
        # User-locked choice: legacy rows are stamped with the current user
        assert owner == "alice"

    def test_migration_leaves_null_when_no_identity(self, db_path):
        self._build_legacy_db(db_path)

        with patch(
            "core.domain.user_identity.resolve_current_user",
            return_value=None,
        ):
            FavoritesManager(db_path=db_path, project_uuid=PROJECT_A)

        conn = sqlite3.connect(db_path)
        owner = conn.execute(
            "SELECT owner FROM fm_favorites WHERE id = 'pre-v5-fav'"
        ).fetchone()[0]
        conn.close()
        # No identity → stays NULL (i.e. shared with every DB user)
        assert owner is None

    def test_migration_is_idempotent(self, db_path):
        self._build_legacy_db(db_path)

        # Migrate once
        with patch(
            "core.domain.user_identity.resolve_current_user",
            return_value="alice",
        ):
            FavoritesManager(db_path=db_path, project_uuid=PROJECT_A)

        # Manually NULL one row, and re-open the manager with a DIFFERENT user.
        # The second open must NOT re-backfill — the column already exists, so
        # the backfill step is skipped entirely.
        conn = sqlite3.connect(db_path)
        conn.execute("UPDATE fm_favorites SET owner = NULL")
        conn.commit()
        conn.close()

        with patch(
            "core.domain.user_identity.resolve_current_user",
            return_value="bob",
        ):
            FavoritesManager(db_path=db_path, project_uuid=PROJECT_A)

        conn = sqlite3.connect(db_path)
        owner = conn.execute(
            "SELECT owner FROM fm_favorites WHERE id = 'pre-v5-fav'"
        ).fetchone()[0]
        conn.close()
        # The column pre-existed the second open, so backfill is skipped
        # and the hand-nulled row stays NULL — proves idempotence.
        assert owner is None


# ---------------------------------------------------------------------------
# list_by_scope
# ---------------------------------------------------------------------------


class TestListByScope:
    """Builds a cache with a mix of owners and queries by scope."""

    def _seed(self, manager):
        manager.add_favorite(
            FilterFavorite(name="alice-personal", expression="TRUE", owner="alice"),
        )
        # Force a shared favorite (no owner) — bypass auto-stamp by
        # using preserve_timestamps=True to simulate an import.
        manager.add_favorite(
            FilterFavorite(
                name="team-favorite", expression="TRUE", owner=None,
                created_at="2024-01-01T00:00:00",
            ),
            preserve_timestamps=True,
        )
        manager.add_favorite(
            FilterFavorite(name="bob-favorite", expression="TRUE", owner="bob"),
            preserve_timestamps=True,
        )

    def test_all_returns_everything(self, manager):
        self._seed(manager)
        favs = manager.list_by_scope(FavoriteScope.ALL)
        names = {f.name for f in favs}
        assert names == {"alice-personal", "team-favorite", "bob-favorite"}

    def test_project_mine_filters_by_user(self, manager):
        self._seed(manager)
        favs = manager.list_by_scope(FavoriteScope.PROJECT_MINE)
        names = {f.name for f in favs}
        assert names == {"alice-personal"}

    def test_project_shared_filters_to_null_owner(self, manager):
        self._seed(manager)
        favs = manager.list_by_scope(FavoriteScope.PROJECT_SHARED)
        names = {f.name for f in favs}
        assert names == {"team-favorite"}

    def test_explicit_current_user_override(self, manager):
        """Callers can pin a different identity for a single query."""
        self._seed(manager)
        favs = manager.list_by_scope(
            FavoriteScope.PROJECT_MINE, current_user="bob",
        )
        names = {f.name for f in favs}
        assert names == {"bob-favorite"}

    def test_global_scope_when_manager_is_on_project_returns_empty(self, manager):
        """Manager pinned to PROJECT_A only caches PROJECT_A rows → the
        GLOBAL_MINE / GLOBAL_SHARED scopes have no matches."""
        self._seed(manager)
        assert manager.list_by_scope(FavoriteScope.GLOBAL_MINE) == []
        assert manager.list_by_scope(FavoriteScope.GLOBAL_SHARED) == []


# ---------------------------------------------------------------------------
# Strip owner on publish bundle
# ---------------------------------------------------------------------------


class TestStripOwnerOnPublish:
    def _bundle(self, tmp_path, favorites_payload):
        bundle_path = tmp_path / "bundle.fmfav-pack.json"
        bundle_path.write_text(json.dumps({
            "schema_version": 3,
            "favorites": favorites_payload,
        }), encoding="utf-8")
        return str(bundle_path)

    def test_strips_owner_from_list_envelope(self, tmp_path):
        from extensions.favorites_sharing.service import FavoritesSharingService
        bundle = self._bundle(tmp_path, [
            {"name": "a", "owner": "alice"},
            {"name": "b"},
        ])
        FavoritesSharingService._strip_owner_from_bundle(bundle)
        with open(bundle, "r", encoding="utf-8") as f:
            data = json.load(f)
        for fav in data["favorites"]:
            assert "owner" not in fav

    def test_strips_owner_from_dict_envelope(self, tmp_path):
        from extensions.favorites_sharing.service import FavoritesSharingService
        bundle = self._bundle(tmp_path, {
            "id-1": {"name": "a", "owner": "alice"},
            "id-2": {"name": "b", "owner": "bob"},
        })
        FavoritesSharingService._strip_owner_from_bundle(bundle)
        with open(bundle, "r", encoding="utf-8") as f:
            data = json.load(f)
        for fav in data["favorites"].values():
            assert "owner" not in fav

    def test_malformed_bundle_is_left_untouched(self, tmp_path):
        from extensions.favorites_sharing.service import FavoritesSharingService
        path = tmp_path / "bad.json"
        path.write_text("not json", encoding="utf-8")
        # Must not raise
        FavoritesSharingService._strip_owner_from_bundle(str(path))
        assert path.read_text() == "not json"
