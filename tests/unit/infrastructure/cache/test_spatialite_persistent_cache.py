# -*- coding: utf-8 -*-
"""End-to-end tests for SpatialitePersistentCache.

Guards against the 2026-04-29 P0-A regression: 8 SQL templates lost their
``f`` prefix during a 2026-02-10 ``# nosec B608`` cleanup pass, leaving the
literal ``{CACHE_TABLE_NAME}`` token in the SQL. SQLite rejected ``{`` →
``OperationalError`` → swallowed silently at startup, cache disabled for
~100 days. No previous test exercised store→retrieve.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from infrastructure.cache import spatialite_persistent_cache as cache_mod
from infrastructure.cache.spatialite_persistent_cache import (
    SpatialitePersistentCache,
)


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    """Return a fresh SpatialitePersistentCache backed by a tmp DB file."""
    db_dir = tmp_path / "filtermate"
    db_dir.mkdir()

    def _fake_db_path() -> str:
        return str(db_dir / "filtermate_cache.db")

    monkeypatch.setattr(cache_mod, "_get_cache_db_path", _fake_db_path)
    SpatialitePersistentCache.reset_instance()
    instance = SpatialitePersistentCache.get_instance()
    yield instance
    SpatialitePersistentCache.reset_instance()


def _fake_layer(layer_id: str = "layer-1", name: str = "TestLayer") -> MagicMock:
    layer = MagicMock()
    layer.id.return_value = layer_id
    layer.source.return_value = f"/tmp/{name}.gpkg"
    layer.name.return_value = name
    return layer


# ---------------------------------------------------------------------------
# Init / schema
# ---------------------------------------------------------------------------


class TestInitDatabase:
    def test_init_creates_db_file(self, isolated_cache):
        assert os.path.exists(isolated_cache.db_path)

    def test_init_creates_tables_with_resolved_name(self, isolated_cache):
        """Regression: P0-A f-string fix.

        If ``{CACHE_TABLE_NAME}`` were still literal, no ``filter_cache`` table
        would exist and the schema introspection would return an empty list.
        """
        import sqlite3
        conn = sqlite3.connect(isolated_cache.db_path)
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        finally:
            conn.close()
        names = [r[0] for r in rows]
        assert "filter_cache" in names, (
            f"P0-A regression: filter_cache table not created. Tables found: {names}"
        )
        assert "filter_steps" in names
        assert "filter_sessions" in names
        assert not any("{" in n for n in names), (
            "Literal '{' in table name — SQL template not interpolated"
        )


# ---------------------------------------------------------------------------
# Store / retrieve roundtrip — the core P0-A guard
# ---------------------------------------------------------------------------


class TestStoreRetrieveRoundtrip:
    def test_store_then_get_returns_same_fids(self, isolated_cache):
        layer = _fake_layer()
        wkt = "POINT(0 0)"
        predicates = ["intersects"]
        fids = [1, 2, 3, 42, 100]

        isolated_cache.store_filter_result(
            layer=layer,
            fids=fids,
            source_geom_wkt=wkt,
            predicates=predicates,
            buffer_value=0.0,
            use_centroids=False,
        )
        retrieved = isolated_cache.get_cached_fids(
            layer=layer,
            source_geom_wkt=wkt,
            predicates=predicates,
            buffer_value=0.0,
            use_centroids=False,
        )
        assert retrieved == set(fids)

    def test_get_with_different_predicates_misses(self, isolated_cache):
        layer = _fake_layer()
        wkt = "POINT(0 0)"
        isolated_cache.store_filter_result(
            layer=layer, fids=[1], source_geom_wkt=wkt,
            predicates=["intersects"], buffer_value=0.0,
        )
        miss = isolated_cache.get_cached_fids(
            layer=layer, source_geom_wkt=wkt,
            predicates=["contains"], buffer_value=0.0,
        )
        assert miss is None

    def test_get_with_different_buffer_misses(self, isolated_cache):
        layer = _fake_layer()
        wkt = "POINT(0 0)"
        isolated_cache.store_filter_result(
            layer=layer, fids=[1], source_geom_wkt=wkt,
            predicates=["intersects"], buffer_value=10.0,
        )
        miss = isolated_cache.get_cached_fids(
            layer=layer, source_geom_wkt=wkt,
            predicates=["intersects"], buffer_value=20.0,
        )
        assert miss is None

    def test_get_with_unknown_layer_returns_none(self, isolated_cache):
        result = isolated_cache.get_cached_fids(
            layer=_fake_layer("never-stored"),
            source_geom_wkt="POINT(0 0)",
            predicates=["intersects"],
            buffer_value=0.0,
        )
        assert result is None


# ---------------------------------------------------------------------------
# Cleanup paths — exercise the DELETE templates
# ---------------------------------------------------------------------------


class TestCleanupOperations:
    def test_clear_layer_cache_removes_only_target_layer(self, isolated_cache):
        layer_a = _fake_layer("a")
        layer_b = _fake_layer("b", "B")
        for layer in (layer_a, layer_b):
            isolated_cache.store_filter_result(
                layer=layer, fids=[1], source_geom_wkt="POINT(0 0)",
                predicates=["intersects"], buffer_value=0.0,
            )

        deleted = isolated_cache.clear_layer_cache("a")
        assert deleted == 1
        assert isolated_cache.get_cached_fids(
            layer=layer_a, source_geom_wkt="POINT(0 0)",
            predicates=["intersects"], buffer_value=0.0,
        ) is None
        assert isolated_cache.get_cached_fids(
            layer=layer_b, source_geom_wkt="POINT(0 0)",
            predicates=["intersects"], buffer_value=0.0,
        ) == {1}

    def test_clear_all_cache_empties_table(self, isolated_cache):
        layer = _fake_layer()
        isolated_cache.store_filter_result(
            layer=layer, fids=[1, 2], source_geom_wkt="POINT(0 0)",
            predicates=["intersects"], buffer_value=0.0,
        )
        deleted = isolated_cache.clear_all_cache()
        assert deleted == 1

        stats = isolated_cache.get_cache_stats()
        assert stats["total_entries"] == 0


# ---------------------------------------------------------------------------
# Stats — exercises the COUNT(*) and SUM templates
# ---------------------------------------------------------------------------


class TestGetCacheStats:
    def test_stats_count_matches_stored_entries(self, isolated_cache):
        for i in range(3):
            isolated_cache.store_filter_result(
                layer=_fake_layer(f"layer-{i}"),
                fids=list(range(i + 1)),
                source_geom_wkt=f"POINT({i} 0)",
                predicates=["intersects"],
                buffer_value=0.0,
            )
        stats = isolated_cache.get_cache_stats()
        assert stats["total_entries"] == 3
        # 1 + 2 + 3 = 6 total fids
        assert stats["total_fids_cached"] == 6
        assert "db_size_mb" in stats
