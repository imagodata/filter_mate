# -*- coding: utf-8 -*-
"""Unit tests for adapters.task_bridge.

Issue #43 — TaskBridge had no test coverage. These tests pin three contracts:

1. **Pure data shapes** — BridgeResult constructors, metrics scaffolding,
   and the legacy-format dict serialization stay stable.

2. **Security regression (H1, audit 2026-04-23)** — both
   ``execute_attribute_filter`` and ``convert_expression_to_backend`` must
   translate raw QGIS expressions to provider-specific SQL via
   ``ExpressionService.to_sql`` before handing them to the backend.
   A regression here would let raw user input land unescaped in the
   PostgreSQL backend's WHERE clause.

3. **Availability gating** — every public operation short-circuits with
   a ``not_available`` BridgeResult when the bridge wasn't initialized,
   so callers can fall back to legacy code without crashing.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from core.domain.filter_expression import ProviderType


# ---------------------------------------------------------------------------
# Module loading — bypass adapters/__init__.py which triggers the deep import
# chain for adapters.backends.* (relative-import-beyond-top-level outside the
# QGIS plugin context).
# ---------------------------------------------------------------------------

ROOT = "filter_mate"


def _ensure_task_bridge_mocks():
    """Pre-mock parent packages so adapters.task_bridge resolves cleanly."""
    if ROOT not in sys.modules:
        fm = types.ModuleType(ROOT)
        fm.__path__ = []
        fm.__package__ = ROOT
        sys.modules[ROOT] = fm

    mocks_to_install = {
        f"{ROOT}.adapters": types.ModuleType(f"{ROOT}.adapters"),
        f"{ROOT}.adapters.app_bridge": MagicMock(),
        f"{ROOT}.core": types.ModuleType(f"{ROOT}.core"),
        f"{ROOT}.core.domain": types.ModuleType(f"{ROOT}.core.domain"),
    }
    # Inject the real filter_expression module under the namespaced path so
    # `from ..core.domain.filter_expression import ...` inside task_bridge
    # resolves correctly.
    from core.domain import filter_expression as real_filter_expression
    mocks_to_install[f"{ROOT}.core.domain.filter_expression"] = real_filter_expression

    for name, mod in mocks_to_install.items():
        sys.modules.setdefault(name, mod)


_ensure_task_bridge_mocks()

_task_bridge_path = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..",
    "adapters", "task_bridge.py",
))

_spec = importlib.util.spec_from_file_location(
    f"{ROOT}.adapters.task_bridge", _task_bridge_path
)
_mod = importlib.util.module_from_spec(_spec)
_mod.__package__ = f"{ROOT}.adapters"
sys.modules[_mod.__name__] = _mod
_spec.loader.exec_module(_mod)

TaskBridge = _mod.TaskBridge
BridgeResult = _mod.BridgeResult
BridgeStatus = _mod.BridgeStatus
get_task_bridge = _mod.get_task_bridge
reset_task_bridge = _mod.reset_task_bridge


@pytest.fixture(autouse=True)
def _isolate_singleton():
    """Each test gets a clean module-level singleton."""
    reset_task_bridge()
    yield
    reset_task_bridge()


@pytest.fixture(autouse=True)
def _restore_filter_expression_module():
    """Other tests in the suite (notably tests/unit/adapters/public_api/) install
    a MagicMock under ``filter_mate.core.domain.filter_expression`` that
    overrides the real module. TaskBridge does in-function imports of
    ``FilterExpression``, so the mock would silently leak in here. Re-bind to
    the real module before each test."""
    from core.domain import filter_expression as real_filter_expression
    sys.modules[f"{ROOT}.core.domain.filter_expression"] = real_filter_expression
    yield


# ---------------------------------------------------------------------------
# BridgeResult value-object contract
# ---------------------------------------------------------------------------

class TestBridgeResult:
    def test_not_available_factory(self) -> None:
        result = BridgeResult.not_available()
        assert result.status is BridgeStatus.NOT_AVAILABLE
        assert result.success is False
        assert result.feature_ids == []
        assert result.feature_count == 0

    def test_fallback_factory_carries_reason(self) -> None:
        result = BridgeResult.fallback("backend timeout")
        assert result.status is BridgeStatus.FALLBACK
        assert result.success is False
        assert result.error_message == "backend timeout"

    def test_to_legacy_format_round_trip(self) -> None:
        result = BridgeResult(
            status=BridgeStatus.SUCCESS,
            success=True,
            feature_ids=[1, 2, 3],
            feature_count=3,
            expression='"x" > 0',
            execution_time_ms=12.5,
            backend_used="postgresql",
        )
        legacy = result.to_legacy_format()
        assert legacy == {
            "success": True,
            "feature_ids": [1, 2, 3],
            "feature_count": 3,
            "expression": '"x" > 0',
            "execution_time_ms": 12.5,
            "backend": "postgresql",
            "error": "",
        }


# ---------------------------------------------------------------------------
# Availability gating — every op returns NOT_AVAILABLE without crashing
# ---------------------------------------------------------------------------

class TestAvailabilityGating:
    """When the bridge fails to initialize, public ops must degrade gracefully."""

    def setup_method(self) -> None:
        self.bridge = TaskBridge(auto_initialize=False)
        assert not self.bridge.is_available()

    def test_execute_spatial_filter_short_circuits(self) -> None:
        result = self.bridge.execute_spatial_filter(
            source_layer=MagicMock(),
            target_layers=[MagicMock()],
            predicates=["intersects"],
        )
        assert result.status is BridgeStatus.NOT_AVAILABLE
        # Metrics MUST NOT be incremented on the gated path — operations counter
        # is reserved for actual backend calls.
        assert self.bridge.metrics["operations"] == 0

    def test_execute_attribute_filter_short_circuits(self) -> None:
        result = self.bridge.execute_attribute_filter(
            layer=MagicMock(), expression='"x" > 0'
        )
        assert result.status is BridgeStatus.NOT_AVAILABLE
        assert self.bridge.metrics["operations"] == 0

    def test_execute_multi_step_filter_short_circuits(self) -> None:
        result = self.bridge.execute_multi_step_filter(
            source_layer=MagicMock(), steps=[]
        )
        assert result.status is BridgeStatus.NOT_AVAILABLE

    def test_execute_export_short_circuits(self) -> None:
        result = self.bridge.execute_export(
            source_layer=MagicMock(), output_path="/tmp/out.gpkg", format="gpkg"
        )
        assert result.status is BridgeStatus.NOT_AVAILABLE

    def test_convert_expression_returns_input_unchanged(self) -> None:
        sql, backend = self.bridge.convert_expression_to_backend(
            expression='"x" > 0', layer=MagicMock()
        )
        assert sql == '"x" > 0'
        assert backend == "qgis"

    def test_get_backend_for_layer_returns_none(self) -> None:
        assert self.bridge.get_backend_for_layer(MagicMock()) is None


# ---------------------------------------------------------------------------
# Metrics scaffolding
# ---------------------------------------------------------------------------

class TestMetrics:
    def setup_method(self) -> None:
        self.bridge = TaskBridge(auto_initialize=False)

    def test_metrics_initialized_with_zero_counters(self) -> None:
        m = self.bridge.metrics
        assert m["operations"] == 0
        assert m["successes"] == 0
        assert m["fallbacks"] == 0
        assert m["errors"] == 0
        assert set(m["by_type"].keys()) == {
            "attribute",
            "spatial",
            "multi_step",
            "export",
        }

    def test_update_type_metrics_tracks_success(self) -> None:
        self.bridge._update_type_metrics("spatial", success=True, time_ms=10.0)
        self.bridge._update_type_metrics("spatial", success=False, time_ms=5.0)

        spatial = self.bridge.metrics["by_type"]["spatial"]
        assert spatial["count"] == 2
        assert spatial["success"] == 1
        assert spatial["time_ms"] == 15.0

    def test_unknown_op_type_is_silently_ignored(self) -> None:
        # Defensive: the bridge shouldn't blow up on a typo in op_type.
        self.bridge._update_type_metrics("not_a_type", success=True, time_ms=1.0)
        # No new key created
        assert "not_a_type" not in self.bridge.metrics["by_type"]

    def test_reset_metrics_clears_state(self) -> None:
        self.bridge._update_type_metrics("attribute", success=True, time_ms=99.0)
        self.bridge._metrics["operations"] = 7
        self.bridge.reset_metrics()
        m = self.bridge.metrics
        assert m["operations"] == 0
        assert m["by_type"]["attribute"]["count"] == 0


# ---------------------------------------------------------------------------
# Singleton access
# ---------------------------------------------------------------------------

class TestSingletonAccess:
    def test_get_task_bridge_returns_instance_when_auto_init_false(self) -> None:
        bridge = get_task_bridge(auto_init=False)
        assert isinstance(bridge, TaskBridge)
        # Same instance on second call (singleton)
        assert get_task_bridge(auto_init=False) is bridge

    def test_get_task_bridge_filters_unavailable_when_auto_init_true(self) -> None:
        """When auto_init=True the helper returns None unless is_available().

        We simulate a failed init by zeroing out the singleton's flags before
        the assertion: the helper should refuse to hand it back.
        """
        bridge = get_task_bridge(auto_init=False)
        assert bridge is not None
        # Force the bridge to look unavailable (as if init failed).
        bridge._initialized = False
        bridge._backend_factory = None
        # auto_init=True: helper checks is_available() before returning.
        assert get_task_bridge(auto_init=True) is None

    def test_reset_task_bridge_clears_singleton(self) -> None:
        first = get_task_bridge(auto_init=False)
        reset_task_bridge()
        second = get_task_bridge(auto_init=False)
        assert first is not second


# ---------------------------------------------------------------------------
# Security regression — H1 (audit 2026-04-23)
# ---------------------------------------------------------------------------

class TestExpressionTranslationH1:
    """H1: raw QGIS expressions must be translated to provider SQL via
    ExpressionService.to_sql before being handed to the backend.

    Pre-fix bug: FilterExpression was constructed without sql=, so .sql
    silently fell back to .raw and landed unescaped in WHERE clauses.
    """

    def setup_method(self) -> None:
        self.bridge = TaskBridge(auto_initialize=False)
        # Force-enable so the actual code path runs
        self.bridge._initialized = True
        self.bridge._backend_factory = MagicMock()

    def _patch_app_bridge(self, *, layer_info, expression_service):
        """Patch the in-function imports app_bridge.* used by TaskBridge.

        TaskBridge does ``from .app_bridge import ...`` inside each method,
        so we patch the namespaced module the loader registered.
        """
        layer_info_factory = MagicMock(return_value=layer_info)
        expression_service_factory = MagicMock(return_value=expression_service)
        return patch.multiple(
            f"{ROOT}.adapters.app_bridge",
            layer_info_from_qgis_layer=layer_info_factory,
            get_expression_service=expression_service_factory,
        )

    def test_attribute_filter_translates_expression_before_backend(self) -> None:
        # Layer info — minimal mock, only provider_type is read by the bridge.
        layer_info = MagicMock()
        layer_info.provider_type = ProviderType.POSTGRESQL

        # Mock the expression service so we can assert it was called.
        expression_service = MagicMock()
        expression_service.to_sql.return_value = "translated_sql"

        # Backend stub with a successful execute().
        backend = MagicMock()
        backend.execute.return_value = MagicMock(
            is_success=True, feature_ids=[1, 2], count=2, error_message=""
        )
        backend.get_info.return_value.name = "postgresql"
        self.bridge._backend_factory.get_backend.return_value = backend

        with self._patch_app_bridge(
            layer_info=layer_info, expression_service=expression_service
        ):
            result = self.bridge.execute_attribute_filter(
                layer=MagicMock(), expression="raw_qgis_expr"
            )

        # Translation must have happened with the right provider.
        expression_service.to_sql.assert_called_once_with(
            "raw_qgis_expr", ProviderType.POSTGRESQL
        )
        # Backend received the FilterExpression, not the raw string.
        sent_expr = backend.execute.call_args[0][0]
        assert sent_expr.raw == "raw_qgis_expr"
        assert sent_expr.sql == "translated_sql"

        assert result.status is BridgeStatus.SUCCESS
        assert result.success is True

    def test_convert_expression_returns_translated_sql(self) -> None:
        layer_info = MagicMock()
        layer_info.provider_type = ProviderType.POSTGRESQL

        expression_service = MagicMock()
        expression_service.to_sql.return_value = "translated_sql"

        with self._patch_app_bridge(
            layer_info=layer_info, expression_service=expression_service
        ):
            sql, backend = self.bridge.convert_expression_to_backend(
                expression="raw_qgis_expr", layer=MagicMock()
            )

        expression_service.to_sql.assert_called_once_with(
            "raw_qgis_expr", ProviderType.POSTGRESQL
        )
        assert sql == "translated_sql"
        assert backend == ProviderType.POSTGRESQL.value
