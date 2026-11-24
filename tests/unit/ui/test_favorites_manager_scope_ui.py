# -*- coding: utf-8 -*-
"""
Tests for the scope-related UI helpers in ``ui/dialogs/favorites_manager.py``.

These tests target the *pure* helpers that don't require a running Qt
event loop: the scope-kind classifier and the filter predicate built on
top of it. The dialog itself needs QGIS and is exercised via manual
smoke tests — a headless Qt-only test would duplicate the domain tests
without catching real UI bugs.
"""

from __future__ import annotations

import pytest

from core.domain.favorites_manager import (
    FilterFavorite,
    GLOBAL_PROJECT_UUID,
)


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


@pytest.fixture
def classify():
    """Import the UI-level helper defensively — it lives alongside Qt
    imports, so we skip the test when the module can't be loaded
    headless (ImportError on QtWidgets).
    """
    try:
        from ui.dialogs.favorites_manager import _favorite_scope_kind
    except ImportError as exc:
        pytest.skip(f"UI module not importable in this env: {exc}")
    return _favorite_scope_kind


class TestScopeKind:
    def test_mine_on_project(self, classify):
        fav = FilterFavorite(name="f", owner="alice")
        assert classify(fav, "alice", "proj-1", GLOBAL_PROJECT_UUID) == "mine_here"

    def test_mine_global(self, classify):
        fav = FilterFavorite(name="f", owner="alice")
        assert classify(
            fav, "alice", GLOBAL_PROJECT_UUID, GLOBAL_PROJECT_UUID,
        ) == "mine_global"

    def test_shared_on_project(self, classify):
        fav = FilterFavorite(name="f", owner=None)
        assert classify(fav, "alice", "proj-1", GLOBAL_PROJECT_UUID) == "shared_here"

    def test_shared_global(self, classify):
        fav = FilterFavorite(name="f", owner=None)
        assert classify(
            fav, "alice", GLOBAL_PROJECT_UUID, GLOBAL_PROJECT_UUID,
        ) == "shared_global"

    def test_foreign_when_owner_is_another_user(self, classify):
        fav = FilterFavorite(name="f", owner="bob")
        # Alice viewing Bob's favorite: "foreign" regardless of project dim
        assert classify(fav, "alice", "proj-1", GLOBAL_PROJECT_UUID) == "foreign"
        assert classify(
            fav, "alice", GLOBAL_PROJECT_UUID, GLOBAL_PROJECT_UUID,
        ) == "foreign"

    def test_no_identity_treats_owner_as_foreign(self, classify):
        """When no current user resolves, any owned favorite is foreign."""
        fav = FilterFavorite(name="f", owner="bob")
        assert classify(fav, None, "proj-1", GLOBAL_PROJECT_UUID) == "foreign"

    def test_no_identity_null_owner_is_shared(self, classify):
        """NULL owner stays shared even without a current user — matches
        the filter semantics ("Shared" = owner IS NULL, independent of
        identity)."""
        fav = FilterFavorite(name="f", owner=None)
        assert classify(fav, None, "proj-1", GLOBAL_PROJECT_UUID) == "shared_here"


# ---------------------------------------------------------------------------
# Global kinds (the list shows them with the globe icon)
# ---------------------------------------------------------------------------


class TestGlobalKinds:
    def test_global_kinds_are_the_classifier_global_outputs(self):
        try:
            from ui.dialogs.favorites_manager import _GLOBAL_SCOPE_KINDS
        except ImportError as exc:
            pytest.skip(f"UI module not importable: {exc}")
        assert _GLOBAL_SCOPE_KINDS == {"shared_global", "mine_global"}



class TestScopeKeys:
    def test_every_scope_combo_key_maps_to_a_classifier_kind(self):
        try:
            from ui.dialogs.favorites_manager import _SCOPE_KEY_KINDS
        except ImportError as exc:
            pytest.skip(f"UI module not importable: {exc}")
        from core.domain.favorites_manager import FavoriteScope
        assert set(_SCOPE_KEY_KINDS) == {scope.value for scope in FavoriteScope} - {"all"}
        assert set(_SCOPE_KEY_KINDS.values()) == {"shared_here", "shared_global", "mine_here", "mine_global"}
