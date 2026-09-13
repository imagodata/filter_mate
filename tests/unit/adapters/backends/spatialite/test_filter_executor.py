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


# ===========================================================================
# 2026-09-13: static buffer applied once in QGIS, SUBSET-mode retry
# ===========================================================================

_apply_static_buffer = _mod._apply_static_buffer
_build_buffer_state = _mod._build_buffer_state
_geometry_only_features = _mod._geometry_only_features


class _FakeGeometry:
    def __init__(self, empty=False, raise_on_buffer=False):
        self.calls = []
        self._empty = empty
        self._raise = raise_on_buffer

    def buffer(self, *args):
        self.calls.append(args)
        if self._raise:
            raise RuntimeError("GEOS failure")
        return _FakeGeometry(empty=self._empty)

    def isEmpty(self):
        return self._empty


class TestApplyStaticBuffer:
    def test_no_buffer_value_leaves_sql_in_charge(self):
        geom = _FakeGeometry()
        ctx = SpatialiteSourceContext(param_buffer_value=None)
        assert _apply_static_buffer(geom, ctx) is None
        assert geom.calls == []

    def test_dynamic_expression_leaves_sql_in_charge(self):
        geom = _FakeGeometry()
        ctx = SpatialiteSourceContext(param_buffer_value=20.0, param_buffer_expression='"width" * 2')
        assert _apply_static_buffer(geom, ctx) is None
        assert geom.calls == []

    def test_static_buffer_is_applied_with_segments(self):
        geom = _FakeGeometry()
        ctx = SpatialiteSourceContext(param_buffer_value=20.0, param_buffer_segments=8, param_buffer_type=0)
        buffered = _apply_static_buffer(geom, ctx)
        assert buffered is not None and buffered is not geom
        assert len(geom.calls) == 1
        assert geom.calls[0][0] == 20.0
        assert geom.calls[0][1] == 8

    def test_empty_result_falls_back_to_sql(self):
        geom = _FakeGeometry(empty=True)
        ctx = SpatialiteSourceContext(param_buffer_value=-500.0)
        assert _apply_static_buffer(geom, ctx) is None

    def test_failure_falls_back_to_sql(self):
        geom = _FakeGeometry(raise_on_buffer=True)
        ctx = SpatialiteSourceContext(param_buffer_value=20.0)
        assert _apply_static_buffer(geom, ctx) is None


class TestBuildBufferState:
    def test_flag_reports_buffer_applied_in_wkt(self):
        ctx = SpatialiteSourceContext(param_buffer_value=20.0, task_parameters={"infos": {}})
        ctx.buffer_applied_in_wkt = True
        state = _build_buffer_state(ctx)
        assert state["applied_in_wkt"] is True
        assert state["has_buffer"] is True
        assert state["buffer_value"] == 20.0
        assert state["is_pre_buffered"] is False

    def test_flag_false_without_static_buffer(self):
        ctx = SpatialiteSourceContext(param_buffer_value=0, task_parameters={})
        state = _build_buffer_state(ctx)
        assert state["applied_in_wkt"] is False
        assert state["has_buffer"] is False

    def test_multi_step_reuse_kept(self):
        ctx = SpatialiteSourceContext(
            param_buffer_value=20.0,
            task_parameters={"infos": {"buffer_state": {"is_pre_buffered": True, "buffer_value": 20.0}}},
        )
        state = _build_buffer_state(ctx)
        assert state["is_pre_buffered"] is True
        assert state["buffer_column"] == "geom_buffered"
        assert state["previous_buffer_value"] == 20.0


class _FakeSubsetLayer:
    """getFeatures() returns nothing for the first request, rows afterwards."""

    def __init__(self, rows):
        self._rows = rows
        self.requests = 0

    def getFeatures(self, request=None):
        self.requests += 1
        return iter([] if self.requests == 1 else self._rows)

    def isValid(self):
        return True

    def featureCount(self):
        return len(self._rows)

    def subsetString(self):
        return "ROWID IN (1, 2)"


class TestGeometryOnlyFeaturesRetry:
    def test_empty_first_answer_is_retried_with_plain_request(self):
        layer = _FakeSubsetLayer(rows=["f1", "f2"])
        assert _geometry_only_features(layer) == ["f1", "f2"]
        assert layer.requests == 2

    def test_non_empty_answer_is_not_retried(self):
        class _Layer(_FakeSubsetLayer):
            def getFeatures(self, request=None):
                self.requests += 1
                return iter(self._rows)
        layer = _Layer(rows=["f1"])
        assert _geometry_only_features(layer) == ["f1"]
        assert layer.requests == 1
