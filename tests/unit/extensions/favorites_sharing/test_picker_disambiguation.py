# -*- coding: utf-8 -*-
"""
Unit tests for the picker's (name, author) collision detection.

The picker dialog itself is a Qt-heavy QDialog that the headless
harness mocks away, but the disambiguation hook is a pure module-level
function — we test that in isolation without driving the full
QListWidget population path.

M5 (audit 2026-04-27): two collections shipping a "Pylons HT" filter
must produce visually distinguishable rows. ``compute_name_collisions``
returns the count of each (name, author) key so the picker can decide
to append the collection name to ambiguous rows.
"""

from __future__ import annotations

from extensions.favorites_sharing.scanner import (
    SharedFavorite,
    SharedFavoriteSource,
)
from extensions.favorites_sharing.ui.shared_picker_dialog import (
    compute_name_collisions,
)


def _make_fav(name: str, author: str, collection: str) -> SharedFavorite:
    """Build a minimal SharedFavorite — only the fields the collision
    helper reads need to be populated. ``name`` lives in payload,
    ``author`` lives in collection_metadata (per the v3 schema:
    author is a collection-level attribute, not per-favorite)."""
    return SharedFavorite(
        payload={'name': name},
        source=SharedFavoriteSource(
            file_path=f"/tmp/{collection}/file.json",
            collection_name=collection,
            collection_metadata={'author': author} if author else {},
        ),
    )


def test_no_collisions_when_all_names_unique():
    items = [
        _make_fav("filter_a", "imagodata", "infra"),
        _make_fav("filter_b", "imagodata", "infra"),
        _make_fav("filter_c", "acme", "field"),
    ]
    counts = compute_name_collisions(items)
    assert all(v == 1 for v in counts.values())


def test_same_name_different_authors_does_not_collide():
    """Author is part of the disambiguation key — same name from
    different teams is *not* a collision (the author badge already
    tells the user they're different)."""
    items = [
        _make_fav("Pylons HT", "imagodata", "infra-imagodata"),
        _make_fav("Pylons HT", "acme", "infra-acme"),
    ]
    counts = compute_name_collisions(items)
    assert counts[("Pylons HT", "imagodata")] == 1
    assert counts[("Pylons HT", "acme")] == 1


def test_same_name_same_author_across_collections_collides():
    """Same (name, author) across 2+ collections is the case the user
    cannot disambiguate without seeing the collection name."""
    items = [
        _make_fav("Pylons HT", "imagodata", "infra-v1"),
        _make_fav("Pylons HT", "imagodata", "infra-v2"),
        _make_fav("Pylons BT", "imagodata", "infra-v1"),
    ]
    counts = compute_name_collisions(items)
    assert counts[("Pylons HT", "imagodata")] == 2
    assert counts[("Pylons BT", "imagodata")] == 1


def test_anonymous_authors_collide_independently_of_named_ones():
    """Empty author maps to '' — two anonymous favs with the same name
    collide; they don't collide with a named fav of the same name."""
    items = [
        _make_fav("filter_x", "", "shared-a"),
        _make_fav("filter_x", "", "shared-b"),
        _make_fav("filter_x", "imagodata", "infra"),
    ]
    counts = compute_name_collisions(items)
    assert counts[("filter_x", "")] == 2
    assert counts[("filter_x", "imagodata")] == 1


def test_empty_input_returns_empty_dict():
    assert compute_name_collisions([]) == {}
