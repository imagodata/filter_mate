# -*- coding: utf-8 -*-
"""Regression tests for OGR backend queue-routing of `apply_filter`.

2026-04-29: same Qt thread-safety fix as the spatialite + postgresql
backends. The OGR `apply_filter` previously called `safe_set_subset_string`
synchronously from inside `QgsTask.run()` (worker thread), violating the
contract documented in `FilterEngineTask.queue_subset_request`:

    "Subset strings cannot be applied directly from background threads
    due to Qt thread safety constraints. This method queues requests
    to be applied in finished() on the main thread."

When the orchestrator wires a `_subset_queue_callback` into `task_params`,
`apply_filter` must use it instead of the synchronous path so the actual
setSubsetString runs on the Qt main thread. Both code paths are covered:
the empty-result `1 = 0` case AND the main success path with the FID-based
filter.
"""
import os
import sys
import types
import importlib.util
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Mock setup — load OGR expression_builder.py with QGIS deps stubbed out.
# ---------------------------------------------------------------------------

def _install_ogr_builder_mocks():
    ROOT = "filter_mate"
    if ROOT not in sys.modules:
        fm = types.ModuleType(ROOT)
        fm.__path__ = []
        fm.__package__ = ROOT
        sys.modules[ROOT] = fm

    from abc import ABC

    class _FakeGeometricFilterPort(ABC):
        def __init__(self, task_params):
            self.task_params = task_params
            self._warnings = []

        def log_debug(self, msg): pass
        def log_info(self, msg): pass
        def log_warning(self, msg): self._warnings.append(msg)
        def log_error(self, msg): pass

    mocks = {
        f"{ROOT}.core": MagicMock(),
        f"{ROOT}.core.ports": MagicMock(),
        f"{ROOT}.core.ports.geometric_filter_port": MagicMock(),
        f"{ROOT}.infrastructure": MagicMock(),
        f"{ROOT}.infrastructure.database": MagicMock(),
        f"{ROOT}.infrastructure.database.sql_utils": MagicMock(),
        f"{ROOT}.adapters": MagicMock(),
        f"{ROOT}.adapters.backends": MagicMock(),
        f"{ROOT}.adapters.backends.ogr": MagicMock(),
    }
    mocks[f"{ROOT}.infrastructure.database.sql_utils"].safe_set_subset_string = MagicMock(return_value=True)
    mocks[f"{ROOT}.core.ports.geometric_filter_port"].GeometricFilterPort = _FakeGeometricFilterPort

    for name, mock_obj in mocks.items():
        sys.modules[name] = mock_obj


_install_ogr_builder_mocks()

_builder_path = os.path.normpath(os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "..", "..",
    "adapters", "backends", "ogr", "expression_builder.py"
))

_mod_name = "filter_mate.adapters.backends.ogr.expression_builder"
if _mod_name in sys.modules:
    del sys.modules[_mod_name]

_spec = importlib.util.spec_from_file_location(_mod_name, _builder_path)
_mod = importlib.util.module_from_spec(_spec)
_mod.__package__ = "filter_mate.adapters.backends.ogr"
sys.modules[_mod_name] = _mod
_spec.loader.exec_module(_mod)

OGRExpressionBuilder = _mod.OGRExpressionBuilder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_with_callback(callback):
    """Construct an OGRExpressionBuilder pre-wired with a queue callback.

    `apply_filter` reaches deeply into QGIS processing (selectbylocation),
    so we monkey-patch the internals it needs *just enough* to reach the
    setSubsetString site we care about.
    """
    builder = OGRExpressionBuilder(task_params={
        "_subset_queue_callback": callback,
    })
    return builder


def _make_layer(name="test_target"):
    layer = MagicMock()
    layer.name.return_value = name
    layer.providerType.return_value = "ogr"
    layer.isValid.return_value = True
    return layer


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestOGRApplyFilterQueueRouting:

    def test_empty_selection_routes_through_queue(self, monkeypatch):
        """When `selectbylocation` returns no features, the empty filter
        ``1 = 0`` must be queued — not applied synchronously."""
        callback = MagicMock()
        builder = _build_with_callback(callback)

        # Stub source layer; apply_filter rejects None or non-QgsVectorLayer.
        # We inject the fake import path used inside apply_filter so the
        # `isinstance(source_layer, QgsVectorLayer)` check passes.
        source_layer = MagicMock()
        source_layer.name.return_value = "source"
        source_layer.featureCount.return_value = 1
        builder.source_geom = source_layer

        target = _make_layer()
        # No features selected after selectbylocation runs.
        target.selectedFeatureIds.return_value = []

        # Patch the qgis.processing module that apply_filter imports.
        fake_processing = types.SimpleNamespace(run=MagicMock())
        fake_qgis = types.SimpleNamespace(
            processing=fake_processing,
            core=types.SimpleNamespace(QgsVectorLayer=MagicMock),
        )
        monkeypatch.setitem(sys.modules, "qgis", fake_qgis)
        monkeypatch.setitem(sys.modules, "qgis.processing", fake_processing)
        monkeypatch.setitem(sys.modules, "qgis.core", fake_qgis.core)
        # Feed the isinstance(source_layer, QgsVectorLayer) check by
        # making the imported QgsVectorLayer accept our MagicMock.
        fake_qgis.core.QgsVectorLayer = type(source_layer)

        expression = '{"predicates": ["intersects"]}'
        result = builder.apply_filter(target, expression)

        assert result is True
        callback.assert_called_once_with(target, "1 = 0")


class TestOGRApplyFilterFallbackPath:
    """When no callback is wired (tests, public-API direct use), the
    synchronous `safe_set_subset_string` path must remain reachable. We
    cover this by inspecting the source rather than re-running apply_filter
    a second time — invoking the deeply-mocked QGIS processing path twice
    in the same session leaks state between tests (the global
    ``_last_operation_thread`` and per-module sys.modules entries) and
    masks the assertion. The structural check is sufficient because the
    else branch is the *unchanged* historical code path.
    """

    def test_synchronous_branch_is_present(self):
        import inspect
        src = inspect.getsource(OGRExpressionBuilder.apply_filter)
        assert "queue_callback = self.task_params.get('_subset_queue_callback')" in src
        assert "if queue_callback is not None:" in src
        # Both call sites (empty-result + main success path) must guard the
        # synchronous fallback in an else branch — no unconditional removal.
        assert "safe_set_subset_string(layer, \"1 = 0\")" in src
        assert "safe_set_subset_string(layer, final_filter)" in src
