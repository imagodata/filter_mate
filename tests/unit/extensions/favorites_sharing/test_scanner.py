# -*- coding: utf-8 -*-
"""
Tests for ResourceSharingScanner.

Builds a fake Resource Sharing tree on disk and asserts the scanner
returns the expected SharedFavorite objects with proper provenance.
"""

import json
import os
import tempfile

import pytest

from extensions.favorites_sharing.scanner import (
    ResourceSharingScanner,
    SharedFavorite,
    SharedFavoriteSource,
)


# ─── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def collection_root(tmp_path):
    """Build a fake Resource Sharing collection tree.

    Structure::

        collections/
          pack-collection/
            collection.json
            filter_mate/favorites/bundle.fmfav-pack.json
          snippet-collection/
            filter_mate/favorites/one.fmfav.json
          unrelated/
            other/nothing.json
    """
    root = tmp_path / "collections"
    root.mkdir()

    # Pack collection
    pack = root / "pack-collection" / "filter_mate" / "favorites"
    pack.mkdir(parents=True)
    (root / "pack-collection" / "collection.json").write_text(json.dumps({
        "name": "Pack Collection",
        "author": "someone",
        "license": "MIT",
    }))
    (pack / "bundle.fmfav-pack.json").write_text(json.dumps({
        "schema": "filter_mate.favorites",
        "schema_version": 3,
        "collection": {"name": "Pack Collection", "tags": ["t1"]},
        "favorites": [
            {"name": "One", "expression": "TRUE"},
            {"name": "Two", "expression": "FALSE"},
        ],
    }))

    # Snippet collection
    snippet = root / "snippet-collection" / "filter_mate" / "favorites"
    snippet.mkdir(parents=True)
    (snippet / "one.fmfav.json").write_text(json.dumps({
        "name": "Lone",
        "expression": "1=1",
    }))

    # Unrelated collection — has nothing in filter_mate/favorites
    unrelated = root / "unrelated" / "other"
    unrelated.mkdir(parents=True)
    (unrelated / "nothing.json").write_text(json.dumps({"x": 1}))

    return str(root)


# ─── Tests ───────────────────────────────────────────────────────────────


def test_scanner_finds_pack_bundle(collection_root):
    """A .fmfav-pack.json bundle yields one SharedFavorite per payload."""
    scanner = ResourceSharingScanner(collections_root=collection_root)
    items = scanner.scan()
    names = {f.name for f in items}
    assert "One" in names
    assert "Two" in names


def test_scanner_finds_bare_snippet(collection_root):
    """A .fmfav.json with a bare favorite payload is detected."""
    scanner = ResourceSharingScanner(collections_root=collection_root)
    items = scanner.scan()
    assert any(f.name == "Lone" for f in items)


def test_scanner_skips_unrelated_directories(collection_root):
    """Files outside filter_mate/favorites/ are ignored."""
    scanner = ResourceSharingScanner(collections_root=collection_root)
    items = scanner.scan()
    # unrelated/ has one JSON but it's not under filter_mate/favorites
    assert all(f.source.collection_name != "unrelated" for f in items)


def test_scanner_provenance(collection_root):
    """SharedFavoriteSource carries collection name and metadata."""
    scanner = ResourceSharingScanner(collections_root=collection_root)
    items = scanner.scan()
    one = next(f for f in items if f.name == "One")
    assert one.source.collection_name == "pack-collection"
    assert one.source.collection_metadata.get("author") == "someone"
    assert one.source.collection_metadata.get("license") == "MIT"
    # Envelope-level collection metadata is merged in
    assert "Pack Collection" == one.source.collection_metadata.get("name")


def test_scanner_cache_is_reused(collection_root):
    """scan() returns cached result unless force_refresh=True."""
    scanner = ResourceSharingScanner(collections_root=collection_root)
    first = scanner.scan()
    # Delete a file — cached result should be unaffected
    target = os.path.join(
        collection_root, "snippet-collection", "filter_mate", "favorites", "one.fmfav.json"
    )
    os.remove(target)
    second = scanner.scan()
    assert len(first) == len(second)
    # After invalidation the cache is re-read and the removed file is gone
    scanner.invalidate_cache()
    third = scanner.scan()
    assert len(third) < len(first)


def test_scanner_handles_missing_root(tmp_path):
    """No Resource Sharing tree → empty scan, no crash."""
    scanner = ResourceSharingScanner(
        collections_root=str(tmp_path / "does-not-exist")
    )
    assert scanner.scan() == []


def test_scanner_ignores_malformed_bundle(tmp_path):
    """A bundle with unreadable JSON is logged and skipped, not raised."""
    root = tmp_path / "collections"
    favdir = root / "broken" / "filter_mate" / "favorites"
    favdir.mkdir(parents=True)
    (favdir / "bad.fmfav.json").write_text("{not valid json")
    (favdir / "good.fmfav.json").write_text(json.dumps({
        "name": "Good", "expression": "TRUE"
    }))

    scanner = ResourceSharingScanner(collections_root=str(root))
    items = scanner.scan()
    assert len(items) == 1
    assert items[0].name == "Good"
