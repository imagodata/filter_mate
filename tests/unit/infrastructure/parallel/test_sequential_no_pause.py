# -*- coding: utf-8 -*-
"""
PERF 2026-09-12: the sequential cascade no longer pauses between layers of the
same SQLite/GeoPackage file; only a genuine lock error is retried once.

``parallel_executor`` imports ``..logging`` relatively, so it is loaded inside
a private package whose ``logging`` module is a stub.
"""

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_INFRA = Path(__file__).resolve().parents[4] / "infrastructure"
_PKG = "fmtest_parallel_pkg"


def _load():
    full = f"{_PKG}.parallel.parallel_executor"
    if full in sys.modules:
        return sys.modules[full]
    root = types.ModuleType(_PKG)
    root.__path__ = [str(_INFRA)]
    root.__package__ = _PKG
    sys.modules[_PKG] = root
    import logging as _logging
    stub_logging = types.ModuleType(f"{_PKG}.logging")
    stub_logging.get_logger = lambda name: _logging.getLogger(f"fmtest.{name}")
    sys.modules[stub_logging.__name__] = stub_logging
    pkg = types.ModuleType(f"{_PKG}.parallel")
    pkg.__path__ = [str(_INFRA / "parallel")]
    pkg.__package__ = f"{_PKG}.parallel"
    sys.modules[pkg.__name__] = pkg
    sys.modules.setdefault("qgis", MagicMock())
    sys.modules.setdefault("qgis.core", MagicMock())
    spec = importlib.util.spec_from_file_location(full, _INFRA / "parallel" / "parallel_executor.py")
    module = importlib.util.module_from_spec(spec)
    module.__package__ = f"{_PKG}.parallel"
    sys.modules[full] = module
    spec.loader.exec_module(module)
    return module


def _layer(name, source):
    layer = MagicMock()
    layer.name.return_value = name
    layer.id.return_value = f"{name}_id"
    layer.isValid.return_value = True
    layer.source.return_value = source
    layer.featureCount.return_value = 10
    return layer


@pytest.mark.unit
class TestSequentialCascade:

    def test_no_pause_between_layers_of_the_same_file(self):
        mod = _load()
        executor = mod.ParallelFilterExecutor(max_workers=1)
        layers = [(_layer(f"l{i}", "/data/world.gpkg|layername=l%d" % i), {}) for i in range(12)]
        filter_func = MagicMock(return_value=True)

        with patch.object(mod.time, "sleep") as mock_sleep:
            results = executor._filter_sequential(layers, filter_func, None, None)

        mock_sleep.assert_not_called()
        assert len(results) == 12 and all(r.success for r in results)
        assert filter_func.call_count == 12

    def test_lock_error_on_shared_file_is_retried_once(self):
        mod = _load()
        executor = mod.ParallelFilterExecutor(max_workers=1)
        first = _layer("a", "/data/world.gpkg|layername=a")
        second = _layer("b", "/data/world.gpkg|layername=b")
        attempts = {"b": 0}

        def filter_func(provider_type, layer, props):
            if layer is second:
                attempts["b"] += 1
                if attempts["b"] == 1:
                    raise RuntimeError("OGR error: sqlite3_step(): unable to open database file")
            return True

        with patch.object(mod.time, "sleep") as mock_sleep:
            results = executor._filter_sequential([(first, {}), (second, {})], filter_func, None, None)

        mock_sleep.assert_called_once_with(0.3)
        assert attempts["b"] == 2
        assert [r.success for r in results] == [True, True]

    def test_lock_error_on_a_different_file_is_not_retried(self):
        mod = _load()
        executor = mod.ParallelFilterExecutor(max_workers=1)
        first = _layer("a", "/data/a.gpkg|layername=a")
        second = _layer("b", "/data/b.gpkg|layername=b")
        filter_func = MagicMock(side_effect=lambda p, layer, props: (_ for _ in ()).throw(RuntimeError("database is locked")) if layer is second else True)

        with patch.object(mod.time, "sleep") as mock_sleep:
            results = executor._filter_sequential([(first, {}), (second, {})], filter_func, None, None)

        mock_sleep.assert_not_called()
        assert [r.success for r in results] == [True, False]

    def test_other_failures_are_not_retried(self):
        mod = _load()
        executor = mod.ParallelFilterExecutor(max_workers=1)
        layers = [(_layer(f"l{i}", "/data/world.gpkg|layername=x"), {}) for i in range(2)]
        filter_func = MagicMock(side_effect=[True, RuntimeError("syntax error")])

        with patch.object(mod.time, "sleep") as mock_sleep:
            results = executor._filter_sequential(layers, filter_func, None, None)

        mock_sleep.assert_not_called()
        assert [r.success for r in results] == [True, False]
        assert filter_func.call_count == 2

    def test_lock_message_detection(self):
        mod = _load()
        assert mod._is_sqlite_lock_message("OGR error: sqlite3_step(): unable to open database file")
        assert mod._is_sqlite_lock_message("Database Is Locked")
        assert not mod._is_sqlite_lock_message("syntax error near IN")
        assert not mod._is_sqlite_lock_message(None)
