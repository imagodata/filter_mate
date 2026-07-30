# -*- coding: utf-8 -*-
"""
Unit tests for Spatialite Filter Executor source-mode resolution.

Regression coverage for the "custom selection with an always-true expression
(e.g. '1')" bug: ``determine_spatialite_source_mode()`` must prefer
FIELD_BASED mode (= use ALL current features of the source layer, respecting
whatever subset it currently has) over a stale/unrelated layer *selection*,
mirroring the guard already present in
``adapters/qgis/source_feature_resolver.SourceFeatureResolver``.

All QGIS dependencies are mocked.
"""
import sys
import types
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Mock setup
# ---------------------------------------------------------------------------

def _ensure_spatialite_filter_executor_mocks():
    ROOT = "filter_mate"
    if ROOT not in sys.modules:
        fm = types.ModuleType(ROOT)
        fm.__path__ = []
        fm.__package__ = ROOT
        sys.modules[ROOT] = fm

    history_repo_mod = types.ModuleType(f"{ROOT}.adapters.repositories.history_repository")
    history_repo_mod.HistoryRepository = MagicMock()

    mocks = {
        f"{ROOT}.adapters": MagicMock(),
        f"{ROOT}.adapters.backends": MagicMock(),
        f"{ROOT}.adapters.backends.spatialite": MagicMock(),
        f"{ROOT}.adapters.repositories": MagicMock(),
        f"{ROOT}.adapters.repositories.history_repository": history_repo_mod,
    }

    for name, mock_obj in mocks.items():
        if name not in sys.modules:
            sys.modules[name] = mock_obj


_ensure_spatialite_filter_executor_mocks()

import importlib.util
import os

_executor_path = os.path.normpath(os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "..", "..",
    "adapters", "backends", "spatialite", "filter_executor.py"
))

_spec = importlib.util.spec_from_file_location(
    "filter_mate.adapters.backends.spatialite.filter_executor",
    _executor_path,
)
_mod = importlib.util.module_from_spec(_spec)
_mod.__package__ = "filter_mate.adapters.backends.spatialite"
sys.modules[_mod.__name__] = _mod
_spec.loader.exec_module(_mod)

SpatialiteSourceContext = _mod.SpatialiteSourceContext
SourceMode = _mod.SourceMode
determine_spatialite_source_mode = _mod.determine_spatialite_source_mode


# ===========================================================================
# Fixtures
# ===========================================================================

class _FakeLayer:
    """Duck-typed stand-in for QgsVectorLayer."""

    def __init__(self, subset="", selected_count=0):
        self._subset = subset
        self._selected_count = selected_count

    def subsetString(self):
        return self._subset

    def selectedFeatureCount(self):
        return self._selected_count


def _context(layer, task_features=None, is_field_expression=None):
    return SpatialiteSourceContext(
        source_layer=layer,
        task_parameters={"task": {"features": task_features or []}},
        is_field_expression=is_field_expression,
    )


# ===========================================================================
# Tests -- determine_spatialite_source_mode
# ===========================================================================

class TestDetermineSpatialiteSourceMode:
    def test_field_based_mode_wins_over_stale_selection(self):
        """Custom Selection with an always-true expression ('1') must use
        ALL current features of the source layer (FIELD_BASED), even when
        the layer happens to have an unrelated leftover selection active.
        """
        layer = _FakeLayer(subset="", selected_count=3)
        context = _context(
            layer,
            task_features=[],
            is_field_expression=(True, "__all_features__"),
        )

        mode, metadata = determine_spatialite_source_mode(context)

        assert mode == SourceMode.FIELD_BASED
        assert metadata["is_field_based_mode"] is True

    def test_field_based_mode_wins_over_stale_selection_with_existing_subset(self):
        """Same as above, but the source layer already has a subset applied
        (e.g. from an earlier filter pass) - SUBSET must still win over a
        stale SELECTION, and field-based intent must not be shadowed."""
        layer = _FakeLayer(subset="homecount > 5", selected_count=2)
        context = _context(
            layer,
            task_features=[],
            is_field_expression=(True, "__all_features__"),
        )

        mode, metadata = determine_spatialite_source_mode(context)

        assert mode == SourceMode.SUBSET

    def test_selection_mode_used_when_not_field_based(self):
        """Outside field-based mode, an active layer selection is still a
        valid, higher-priority source (unchanged behavior)."""
        layer = _FakeLayer(subset="", selected_count=2)
        context = _context(layer, task_features=[], is_field_expression=None)

        mode, metadata = determine_spatialite_source_mode(context)

        assert mode == SourceMode.SELECTION

    def test_field_based_mode_no_selection_no_subset(self):
        layer = _FakeLayer(subset="", selected_count=0)
        context = _context(
            layer,
            task_features=[],
            is_field_expression=(True, "__all_features__"),
        )

        mode, metadata = determine_spatialite_source_mode(context)

        assert mode == SourceMode.FIELD_BASED

    def test_task_params_mode_takes_priority(self):
        layer = _FakeLayer(subset="", selected_count=0)
        context = _context(
            layer,
            task_features=["fake_feature"],
            is_field_expression=None,
        )

        mode, metadata = determine_spatialite_source_mode(context)

        assert mode == SourceMode.TASK_PARAMS

    def test_fallback_mode_when_nothing_matches(self):
        layer = _FakeLayer(subset="", selected_count=0)
        context = _context(layer, task_features=[], is_field_expression=None)

        mode, metadata = determine_spatialite_source_mode(context)

        assert mode == SourceMode.FALLBACK
