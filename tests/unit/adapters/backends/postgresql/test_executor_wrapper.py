# -*- coding: utf-8 -*-
"""
PostgreSQLFilterExecutor (the FilterExecutorPort the BackendRegistry hands out).

Audit October 2026: ``_check_availability`` imported ``.postgresql_availability``
from the wrong package (the module lives in ``adapters/backends/``), so the
executor was never available, and ``cleanup_resources`` imported a
``cleanup_materialized_views`` that no longer exists and logged a warning on
every registry cleanup.
"""
import importlib
import logging
import sys
import types
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[5]
PKG = "fmtest_pg_executor"


def _load():
    for name, rel in (("", ""), (".core", "core"), (".core.ports", "core/ports"), (".adapters", "adapters"),
                      (".adapters.backends", "adapters/backends"),
                      (".adapters.backends.postgresql", "adapters/backends/postgresql")):
        if PKG + name not in sys.modules:
            package = types.ModuleType(PKG + name)
            package.__path__ = [str(ROOT / rel) if rel else str(ROOT)]
            sys.modules[PKG + name] = package
    return importlib.import_module(f"{PKG}.adapters.backends.postgresql.executor_wrapper")


def test_the_executor_is_available_and_cleanup_is_quiet(caplog):
    module = _load()
    executor = module.PostgreSQLFilterExecutor()
    assert executor._available is True
    with caplog.at_level(logging.WARNING, logger="FilterMate"):
        executor.cleanup_resources()
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []
