# -*- coding: utf-8 -*-
"""2026-10-17: the empty-target probe runs only on a subset applied in place.

A filter task queues the PostgreSQL subsets for the main thread (the legacy adapter set
them from the worker): in the worker, the layer still holds its previous subset, which the
probe would have read ("empty after filtering" about the old filter).
"""
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parents[4]
ROOT = "filter_mate"


def _package(name):
    module = types.ModuleType(name)
    module.__path__ = []
    return module


def _load():
    ports = types.ModuleType(f"{ROOT}.core.ports")
    ports.get_backend_services = MagicMock()
    exceptions = types.ModuleType(f"{ROOT}.core.domain.exceptions")
    exceptions.BackendError = type("BackendError", (Exception,), {})
    constants = types.ModuleType(f"{ROOT}.infrastructure.constants")
    constants.PROVIDER_POSTGRES = "postgresql"
    constants.PROVIDER_SPATIALITE = "spatialite"
    constants.PROVIDER_OGR = "ogr"
    constants.PROVIDER_MEMORY = "memory"
    constants.QGIS_PROVIDER_POSTGRES = "postgres"
    stubs = {
        ROOT: _package(ROOT),
        f"{ROOT}.core": _package(f"{ROOT}.core"),
        f"{ROOT}.core.filter": _package(f"{ROOT}.core.filter"),
        f"{ROOT}.core.ports": ports,
        f"{ROOT}.core.domain": _package(f"{ROOT}.core.domain"),
        f"{ROOT}.core.domain.exceptions": exceptions,
        f"{ROOT}.infrastructure": _package(f"{ROOT}.infrastructure"),
        f"{ROOT}.infrastructure.constants": constants,
    }
    saved = {key: sys.modules.get(key) for key in stubs}
    sys.modules.update(stubs)
    try:
        name = f"{ROOT}.core.filter._fm_test_empty_target_probe"
        spec = importlib.util.spec_from_file_location(name, PLUGIN_ROOT / "core" / "filter" / "filter_orchestrator.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for key, value in saved.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


orchestrator_module = _load()


def _pg_layer():
    layer = MagicMock()
    layer.name.return_value = "pts"
    layer.providerType.return_value = "postgres"
    layer.subsetString.return_value = '"id" > 5'  # the subset before this filter
    return layer


def _orchestrator(queue):
    return orchestrator_module.FilterOrchestrator(
        task_parameters={}, subset_queue_callback=queue, parent_task=MagicMock(),
        get_predicates_callback=lambda: {},
    )


def test_queued_subset_is_not_probed(monkeypatch):
    orchestrator = _orchestrator(MagicMock())

    def _probe(layer):
        raise AssertionError("probed the previous subset")

    monkeypatch.setattr(orchestrator, "_has_any_feature", _probe)
    orchestrator._log_filter_success(_pg_layer(), "postgresql")
    assert orchestrator.empty_target_layers == []


def test_subset_applied_in_place_is_probed(monkeypatch):
    orchestrator = _orchestrator(None)
    monkeypatch.setattr(orchestrator, "_has_any_feature", lambda layer: False)
    orchestrator._log_filter_success(_pg_layer(), "postgresql")
    assert orchestrator.empty_target_layers == ["pts"]
