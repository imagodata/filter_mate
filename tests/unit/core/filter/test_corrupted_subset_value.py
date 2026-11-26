# -*- coding: utf-8 -*-
"""``FilterOrchestrator._is_corrupted_subset`` ignores ``__source`` in a value (lot 7, 2026-11-24).

A subset comparing a field with the text ``__source`` (``"name" = '__source'``)
holds no alias: clearing it as corrupted wiped a valid filter. Only the code
outside the single-quoted literals decides.
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
    f"{ROOT}.core.filter._fm_test_value_source_orchestrator",
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

is_corrupted = orchestrator_module.FilterOrchestrator._is_corrupted_subset

EXISTS = (
    'EXISTS (SELECT 1 FROM "ign"."troncon_de_route" AS __source '
    'WHERE ST_DWithin("batiment"."geometrie", __source."geometrie", 20.0) AND (__source."fid" IN (1, 2)))'
)


def test_value_holding_dunder_source_is_kept():
    assert not is_corrupted("\"name\" = '__source'")


def test_value_holding_dunder_source_twice_is_kept():
    assert not is_corrupted("\"comment\" = 'from __source to __source'")


def test_value_with_escaped_quote_holding_dunder_source_is_kept():
    assert not is_corrupted("\"comment\" = 'it''s __source'")


def test_bare_alias_without_exists_is_still_corrupted():
    assert is_corrupted('SELECT 1 FROM "ign"."commune" AS __source WHERE "fid" > 5')


def test_well_formed_exists_is_still_kept():
    assert not is_corrupted(EXISTS)


def test_empty_subset_is_kept():
    assert not is_corrupted(None)
    assert not is_corrupted("")
