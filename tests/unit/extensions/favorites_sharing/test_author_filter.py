# -*- coding: utf-8 -*-
"""
Tests for the per-author filter on shared favorites.

Covers:
- ``SharedFavorite.author`` falls back gracefully when collection
  metadata has no ``author`` field;
- ``FavoritesSharingService.list_authors`` returns the distinct,
  sorted, non-empty set of authors;
- ``FavoritesSharingService.list_shared(author=...)`` filters by
  author (exact, case-insensitive);
- author + search filters compose (both must match).
"""

from __future__ import annotations

import json
import os

import pytest

from extensions.favorites_sharing.scanner import (
    ResourceSharingScanner,
    SharedFavorite,
    SharedFavoriteSource,
)
from extensions.favorites_sharing.service import FavoritesSharingService


# ─── Fixtures ────────────────────────────────────────────────────────────


def _write_collection(root, name, author, fav_names):
    """Create a Resource Sharing-style collection on disk."""
    coll_dir = os.path.join(root, name)
    fav_dir = os.path.join(coll_dir, "filter_mate", "favorites")
    os.makedirs(fav_dir, exist_ok=True)
    # collection.json carries the author at the collection level
    with open(os.path.join(coll_dir, "collection.json"), 'w') as f:
        json.dump({"name": name, "author": author}, f)
    # one bundle per collection — ships all favorites listed
    bundle = {
        "schema": "filter_mate.favorites",
        "schema_version": 3,
        "collection": {"name": name, "author": author},
        "favorites": [
            {"name": fn, "expression": "TRUE"} for fn in fav_names
        ],
    }
    with open(os.path.join(fav_dir, "bundle.fmfav-pack.json"), 'w') as f:
        json.dump(bundle, f)


@pytest.fixture
def populated_service(tmp_path):
    """Scanner + service over three collections, two distinct authors."""
    root = tmp_path / "collections"
    root.mkdir()
    _write_collection(str(root), "acme-zones", "ACME Inc.", ["Zone A", "Zone B"])
    _write_collection(str(root), "imago-tools", "imagodata", ["Snippet 1"])
    _write_collection(str(root), "anonymous-set", "", ["Anon Fav"])

    scanner = ResourceSharingScanner(collections_root=str(root))
    return FavoritesSharingService(scanner)


# ─── SharedFavorite.author property ──────────────────────────────────────


class TestAuthorProperty:
    def test_author_from_collection_metadata(self):
        src = SharedFavoriteSource(
            file_path="/x/y.json",
            collection_name="acme",
            collection_metadata={"author": "ACME Inc."},
        )
        fav = SharedFavorite(payload={"name": "X"}, source=src)
        assert fav.author == "ACME Inc."

    def test_author_empty_when_no_metadata(self):
        src = SharedFavoriteSource(
            file_path="/x/y.json",
            collection_name="anon",
            collection_metadata={},
        )
        fav = SharedFavorite(payload={"name": "X"}, source=src)
        assert fav.author == ""

    def test_author_strips_whitespace(self):
        src = SharedFavoriteSource(
            file_path="/x/y.json",
            collection_name="acme",
            collection_metadata={"author": "  ACME  "},
        )
        fav = SharedFavorite(payload={"name": "X"}, source=src)
        assert fav.author == "ACME"


# ─── list_authors ────────────────────────────────────────────────────────


class TestListAuthors:
    def test_returns_distinct_sorted_non_empty_authors(self, populated_service):
        authors = populated_service.list_authors()
        assert authors == ["ACME Inc.", "imagodata"]
        # Empty/anonymous authors must NOT appear in the dropdown source
        assert "" not in authors

    def test_empty_when_no_collections(self, tmp_path):
        root = tmp_path / "empty"
        root.mkdir()
        scanner = ResourceSharingScanner(collections_root=str(root))
        svc = FavoritesSharingService(scanner)
        assert svc.list_authors() == []


# ─── list_shared(author=...) ─────────────────────────────────────────────


class TestListSharedAuthorFilter:
    def test_filters_by_exact_author(self, populated_service):
        items = populated_service.list_shared(author="ACME Inc.")
        names = sorted(f.name for f in items)
        assert names == ["Zone A", "Zone B"]

    def test_filter_is_case_insensitive(self, populated_service):
        items = populated_service.list_shared(author="acme inc.")
        assert {f.name for f in items} == {"Zone A", "Zone B"}

    def test_none_returns_all(self, populated_service):
        items = populated_service.list_shared(author=None)
        # 4 favorites total across the three fixtures
        assert len(items) == 4

    def test_empty_string_returns_all(self, populated_service):
        items = populated_service.list_shared(author="")
        assert len(items) == 4

    def test_unknown_author_returns_empty(self, populated_service):
        assert populated_service.list_shared(author="ghost-team") == []


# ─── Author + search compose ─────────────────────────────────────────────


class TestAuthorAndSearchCompose:
    def test_both_filters_must_match(self, populated_service):
        items = populated_service.list_shared(
            author="ACME Inc.", search_query="Zone A",
        )
        assert [f.name for f in items] == ["Zone A"]

    def test_search_against_author_field(self, populated_service):
        # The search query is matched against the author field too
        items = populated_service.list_shared(search_query="imagodata")
        assert {f.name for f in items} == {"Snippet 1"}
