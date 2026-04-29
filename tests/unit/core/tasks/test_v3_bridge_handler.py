# -*- coding: utf-8 -*-
"""Regression tests for V3BridgeHandler.try_v3_multi_step_filter().

The V3 multi-step path emits a literal placeholder
``"SPATIAL_FILTER(intersects)"`` as the step expression. None of the live
backends (PostgreSQL, OGR, Spatialite) translate this placeholder into a
real spatial expression, so QGIS surfaces ``"Function SPATIAL_FILTER is
not known"`` and the cascade silently no-ops on the target layers.

Until a real V3 spatial implementation lands, the handler must bail out
to the legacy code for every provider that would otherwise hit this bug.
The PostgreSQL guard landed in v4.1.1 (2026-01-17), the OGR guard in
v4.1.2 (2026-01-19); the Spatialite guard landed 2026-04-29 after the
user reported a fully-spatialite project producing no cascade results.
"""

from unittest.mock import MagicMock

import pytest

from core.tasks.v3_bridge_handler import V3BridgeHandler


@pytest.fixture
def handler_with_bridge():
    """Build a V3BridgeHandler whose TaskBridge claims multi-step support.

    The guards under test sit *after* the ``supports_multi_step`` check, so
    the bridge must report True for the test to exercise the provider
    bail-outs rather than the upstream "no bridge" early return.
    """
    task = MagicMock()
    task._task_bridge = MagicMock()
    task._task_bridge.supports_multi_step = MagicMock(return_value=True)
    task.task_parameters = {}
    return V3BridgeHandler(task)


def _layers_dict_for(provider: str):
    """Minimal layers_dict shape: one provider, one (layer, props) entry."""
    layer = MagicMock()
    layer.id.return_value = "layer_id_1"
    layer.name.return_value = f"layer_{provider}"
    return {provider: [(layer, {"predicates": ["intersects"]})]}


class TestV3MultiStepProviderBailouts:
    """Each known-broken provider must short-circuit to legacy."""

    def test_postgresql_returns_none(self, handler_with_bridge):
        result = handler_with_bridge.try_v3_multi_step_filter(
            _layers_dict_for("postgresql")
        )
        assert result is None

    def test_ogr_returns_none(self, handler_with_bridge):
        result = handler_with_bridge.try_v3_multi_step_filter(
            _layers_dict_for("ogr")
        )
        assert result is None

    def test_spatialite_returns_none(self, handler_with_bridge):
        """2026-04-29 regression: spatialite fell through V3 and emitted the
        SPATIAL_FILTER placeholder, breaking all-spatialite cascades."""
        result = handler_with_bridge.try_v3_multi_step_filter(
            _layers_dict_for("spatialite")
        )
        assert result is None

    def test_mixed_includes_spatialite_returns_none(self, handler_with_bridge):
        """A dict mixing a safe-on-paper provider with spatialite must still
        bail out — the guard is per-key existence, not provider exclusivity."""
        layers_dict = _layers_dict_for("spatialite")
        layers_dict["postgresql"] = []  # empty list, len == 0
        result = handler_with_bridge.try_v3_multi_step_filter(layers_dict)
        assert result is None


class TestV3MultiStepEarlyReturns:
    """Pre-existing early-return paths that must not regress."""

    def test_no_bridge_returns_none(self):
        task = MagicMock()
        task._task_bridge = None
        handler = V3BridgeHandler(task)
        assert handler.try_v3_multi_step_filter(_layers_dict_for("spatialite")) is None

    def test_bridge_without_multi_step_support_returns_none(self):
        task = MagicMock()
        task._task_bridge = MagicMock()
        task._task_bridge.supports_multi_step = MagicMock(return_value=False)
        handler = V3BridgeHandler(task)
        assert handler.try_v3_multi_step_filter(_layers_dict_for("spatialite")) is None
