# -*- coding: utf-8 -*-
"""The OGR-fallback sentinel is a hand-over, never an expression (2026-10-16).

SpatialiteExpressionBuilder returns ``__USE_OGR_FALLBACK__`` for a source WKT
too large to inline (the 236 KB Toulouse river network), a
GeometryCollection or a dynamic buffer. The orchestrator passed it to
``apply_filter()``, which logged "SPATIALITE backend FAILED" before the OGR
fallback, and the legacy adapter's new-backend path would have written it
into the layer's subset string.
"""
import importlib.util
import logging
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parents[4]
ROOT = "filter_mate"
SENTINEL = "__USE_OGR_FALLBACK__"


def _package(name):
    module = types.ModuleType(name)
    module.__path__ = []
    return module


def _load(name, path, stubs):
    saved = {key: sys.modules.get(key) for key in stubs}
    sys.modules.update(stubs)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for key, value in saved.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


class _BackendError(Exception):
    pass


_ports = types.ModuleType(f"{ROOT}.core.ports")
_ports.get_backend_services = MagicMock()
_exceptions = types.ModuleType(f"{ROOT}.core.domain.exceptions")
_exceptions.BackendError = _BackendError
_constants = types.ModuleType(f"{ROOT}.infrastructure.constants")
_constants.PROVIDER_POSTGRES = "postgresql"
_constants.PROVIDER_SPATIALITE = "spatialite"
_constants.PROVIDER_OGR = "ogr"
_constants.PROVIDER_MEMORY = "memory"
_constants.QGIS_PROVIDER_POSTGRES = "postgres"

orchestrator_module = _load(
    f"{ROOT}.core.filter._fm_test_filter_orchestrator",
    PLUGIN_ROOT / "core" / "filter" / "filter_orchestrator.py",
    {
        ROOT: _package(ROOT),
        f"{ROOT}.core": _package(f"{ROOT}.core"),
        f"{ROOT}.core.filter": _package(f"{ROOT}.core.filter"),
        f"{ROOT}.core.ports": _ports,
        f"{ROOT}.core.domain": _package(f"{ROOT}.core.domain"),
        f"{ROOT}.core.domain.exceptions": _exceptions,
        f"{ROOT}.infrastructure": _package(f"{ROOT}.infrastructure"),
        f"{ROOT}.infrastructure.constants": _constants,
    },
)
legacy_module = _load(
    f"{ROOT}.adapters.backends._fm_test_legacy_adapter",
    PLUGIN_ROOT / "adapters" / "backends" / "legacy_adapter.py",
    {},
)


def test_orchestrator_sentinel_matches_the_spatialite_builder():
    assert orchestrator_module.OGR_FALLBACK_SENTINEL == SENTINEL
    assert legacy_module._OGR_FALLBACK_SENTINEL == SENTINEL
    source = (PLUGIN_ROOT / "adapters" / "backends" / "spatialite" / "expression_builder.py").read_text(encoding="utf-8")
    assert f'USE_OGR_FALLBACK = "{SENTINEL}"' in source


def test_sentinel_goes_straight_to_the_ogr_fallback(monkeypatch, caplog):
    orchestrator = orchestrator_module.FilterOrchestrator(
        task_parameters={}, subset_queue_callback=MagicMock(), parent_task=MagicMock(),
        get_predicates_callback=lambda: {"ST_Crosses": "ST_Crosses"},
    )
    backend = MagicMock()
    backend.get_backend_name.return_value = "Spatialite"
    monkeypatch.setattr(orchestrator, "_select_backend", lambda layer, provider: (backend, "spatialite", "spatialite"))
    monkeypatch.setattr(orchestrator, "_clean_corrupted_subsets", lambda layer: None)
    fallback_calls = []

    def _fallback(**kwargs):
        fallback_calls.append(kwargs)
        return True

    monkeypatch.setattr(orchestrator, "_try_fallback_backend", _fallback)
    layer = MagicMock()
    layer.name.return_value = "troncon_de_route"
    builder = MagicMock()
    builder.build_backend_expression.return_value = SENTINEL

    with caplog.at_level(logging.WARNING):
        result = orchestrator.orchestrate_geometric_filter(
            layer=layer, layer_provider_type="spatialite", layer_props={"layer_name": "troncon_de_route"},
            source_geometries={"spatialite": "MULTILINESTRING((0 0, 1 1))", "ogr": MagicMock()},
            expression_builder=builder,
        )

    assert result is True
    backend.apply_filter.assert_not_called()
    assert len(fallback_calls) == 1 and fallback_calls[0]["requested"] is True
    assert not any("FAILED" in record.getMessage() for record in caplog.records)


def test_requested_fallback_is_logged_as_a_hand_over(monkeypatch, caplog):
    orchestrator = orchestrator_module.FilterOrchestrator(
        task_parameters={"actual_backends": {}}, subset_queue_callback=MagicMock(), parent_task=MagicMock(),
        get_predicates_callback=lambda: {},
    )
    ogr_backend = MagicMock()
    ogr_backend.apply_filter.return_value = True
    monkeypatch.setattr(orchestrator_module.BackendFactory, "get_backend", lambda *args: ogr_backend)
    monkeypatch.setattr(orchestrator, "_determine_subset_strategy", lambda layer: (None, None))
    monkeypatch.setattr(orchestrator, "_collect_backend_warnings", lambda backend: None)
    builder = MagicMock()
    builder.build_backend_expression.return_value = '{"predicates": ["ST_Crosses"]}'
    layer = MagicMock()
    layer.name.return_value = "troncon_de_route"

    with caplog.at_level(logging.INFO):
        assert orchestrator._try_fallback_backend(
            layer=layer, layer_props={}, backend_name="spatialite",
            source_geometries={"ogr": MagicMock()}, expression_builder=builder, requested=True,
        ) is True

    messages = [record.getMessage() for record in caplog.records]
    assert any("hands the layer to the OGR backend" in m for m in messages)
    assert not any("failed" in m.lower() for m in messages)
    ogr_backend.apply_filter.assert_called_once()


def test_legacy_adapter_never_applies_the_sentinel(monkeypatch):
    adapter = legacy_module.LegacySpatialiteAdapter.__new__(legacy_module.LegacySpatialiteAdapter)
    adapter.task_params = {}
    adapter._use_new_backend = True
    adapter._new_backend = MagicMock()
    adapter._legacy_backend = MagicMock()

    def _explode(*args):
        raise AssertionError("the sentinel reached a subset string")

    monkeypatch.setattr(adapter, "_apply_filter_new", _explode)
    assert adapter.apply_filter(MagicMock(), SENTINEL) is False
    adapter._legacy_backend.apply_filter.assert_not_called()
