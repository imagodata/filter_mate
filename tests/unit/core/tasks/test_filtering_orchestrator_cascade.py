# -*- coding: utf-8 -*-
"""
PERF 2026-09-12: the worker-side cascade over the target layers no longer
calls ``featureCount()`` before or after each layer. On PostgreSQL each call
was a real COUNT query per target (the cache is invalidated by every subset
change), and once every backend queues its subset for the main thread the
"after" number was stale anyway. Per-layer and total timings replace them.

``filtering_orchestrator`` imports ``...infrastructure`` and ``...config``
relatively, so it is loaded inside a private package made of stubs.
"""
import importlib.util
import logging
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[4]
_PKG = "fmtest_ftorch_pkg"
_LOGGER_NAME = "FilterMate.Tasks.FilteringOrchestrator"
_PERF_LOGGER = "FilterMate.Perf"


def _capture(caplog):
    caplog.set_level(logging.INFO, logger=_LOGGER_NAME)
    caplog.set_level(logging.INFO, logger=_PERF_LOGGER)


def _module(name, path=None, **attrs):
    mod = types.ModuleType(name)
    if path is not None:
        mod.__path__ = [str(path)]
    mod.__package__ = name
    for key, value in attrs.items():
        setattr(mod, key, value)
    sys.modules[name] = mod
    return mod


class _FakeExecutor:
    """Stands in for ParallelFilterExecutor and returns canned results."""

    results = []

    def __init__(self, max_workers=None):
        self.max_workers = max_workers

    def filter_layers_parallel(self, layers, filter_func, task_parameters,
                               progress_callback=None, cancel_check=None):
        return list(type(self).results)


def _load():
    full = f"{_PKG}.core.tasks.filtering_orchestrator"
    if full in sys.modules:
        return sys.modules[full]
    sys.modules.setdefault("qgis", MagicMock())
    sys.modules.setdefault("qgis.core", MagicMock())
    _module(_PKG, _ROOT)
    _module(f"{_PKG}.core", _ROOT / "core")
    _module(f"{_PKG}.core.tasks", _ROOT / "core" / "tasks")
    _module(f"{_PKG}.infrastructure", _ROOT / "infrastructure")
    _module(f"{_PKG}.infrastructure.logging",
            setup_logger=lambda name, *args, **kwargs: logging.getLogger(name))
    _module(f"{_PKG}.infrastructure.constants", PROVIDER_POSTGRES="postgresql")
    _module(f"{_PKG}.infrastructure.utils", is_layer_valid=lambda layer: True)
    _module(f"{_PKG}.infrastructure.parallel",
            ParallelFilterExecutor=_FakeExecutor,
            ParallelConfig=lambda **kwargs: SimpleNamespace(**kwargs))
    _module(f"{_PKG}.config", _ROOT / "config")
    _module(f"{_PKG}.config.config", ENV_VARS={})
    # _log_filtering_summary imports ..optimization.logging_utils lazily
    _module(f"{_PKG}.core.optimization")
    _module(f"{_PKG}.core.optimization.logging_utils", log_filtering_summary=MagicMock())
    spec = importlib.util.spec_from_file_location(full, _ROOT / "core" / "tasks" / "filtering_orchestrator.py")
    module = importlib.util.module_from_spec(spec)
    module.__package__ = f"{_PKG}.core.tasks"
    sys.modules[full] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _reset_fake_executor():
    _FakeExecutor.results = []
    yield
    _FakeExecutor.results = []


def _layer(name):
    layer = MagicMock()
    layer.name.return_value = name
    layer.id.return_value = f"{name}_id"
    return layer


def _result(name, ms, success=True):
    return SimpleNamespace(
        layer_id=f"{name}_id", layer_name=name, success=success, feature_count=0,
        execution_time_ms=ms, error_message=None if success else "boom",
    )


def _run_parallel(mod, layers, callback=None):
    return mod.FilteringOrchestrator()._filter_all_layers_parallel(
        layers=layers, layers_count=sum(len(v) for v in layers.values()), max_workers=0,
        execute_geometric_filtering_callback=callback or MagicMock(return_value=True),
        is_canceled_callback=lambda: False,
        set_progress_callback=lambda percent: None,
        set_description_callback=lambda text: None,
    )


def _run_sequential(mod, layers, callback):
    return mod.FilteringOrchestrator()._filter_all_layers_sequential(
        layers=layers, layers_count=sum(len(v) for v in layers.values()),
        execute_geometric_filtering_callback=callback,
        is_canceled_callback=lambda: False,
        set_progress_callback=lambda percent: None,
        set_description_callback=lambda text: None,
    )


@pytest.mark.unit
class TestParallelCascade:

    def test_no_feature_count_and_timings_logged(self, caplog):
        mod = _load()
        batiment, route = _layer("batiment"), _layer("route")
        _FakeExecutor.results = [_result("batiment", 450.0), _result("route", 12.0)]
        _capture(caplog)

        res = _run_parallel(mod, {"postgresql": [(batiment, {}), (route, {})]})

        assert res["success"] is True
        batiment.featureCount.assert_not_called()
        route.featureCount.assert_not_called()
        messages = [record.getMessage() for record in caplog.records]
        assert any(m.startswith("⏱ layer_filter: 450 ms (batiment)") for m in messages)
        assert not any(m.startswith("⏱ layer_filter") and "route" in m for m in messages)
        cascade = [m for m in messages if m.startswith("⏱ cascade_filter: ")]
        assert len(cascade) == 1
        assert "2 layer(s) in the worker, slowest: batiment 450 ms" in cascade[0]

    def test_failed_layer_is_reported_without_counting(self):
        mod = _load()
        batiment = _layer("batiment")
        _FakeExecutor.results = [_result("batiment", 5.0, success=False)]

        res = _run_parallel(mod, {"postgresql": [(batiment, {})]})

        assert res["success"] is False
        assert res["failed_layer_names"] == ["batiment"]
        batiment.featureCount.assert_not_called()


@pytest.mark.unit
class TestSequentialCascade:

    def test_no_feature_count_and_timings_logged(self, caplog, monkeypatch):
        mod = _load()
        monkeypatch.setattr(mod, "LAYER_FILTER_LOG_THRESHOLD_MS", 0)
        batiment, route = _layer("batiment"), _layer("route")
        callback = MagicMock(return_value=True)
        _capture(caplog)

        res = _run_sequential(mod, {"postgresql": [(batiment, {}), (route, {})]}, callback)

        assert res["success"] is True
        assert callback.call_count == 2
        batiment.featureCount.assert_not_called()
        route.featureCount.assert_not_called()
        messages = [record.getMessage() for record in caplog.records]
        per_layer = [m for m in messages if m.startswith("⏱ layer_filter: ")]
        assert [m.split("(")[1].rstrip(")") for m in per_layer] == ["batiment", "route"]
        cascade = [m for m in messages if m.startswith("⏱ cascade_filter: ")]
        assert len(cascade) == 1 and "2 layer(s) in the worker" in cascade[0]

    def test_slow_layer_only_gets_its_own_line(self, caplog, monkeypatch):
        mod = _load()
        monkeypatch.setattr(mod, "LAYER_FILTER_LOG_THRESHOLD_MS", 10 ** 9)
        layer = _layer("route")
        _capture(caplog)

        _run_sequential(mod, {"postgresql": [(layer, {})]}, MagicMock(return_value=True))

        messages = [record.getMessage() for record in caplog.records]
        assert not any(m.startswith("⏱ layer_filter") for m in messages)
        assert any(m.startswith("⏱ cascade_filter: ") for m in messages)

    def test_exception_marks_layer_failed_without_counting(self):
        mod = _load()
        batiment, route = _layer("batiment"), _layer("route")
        callback = MagicMock(side_effect=[True, RuntimeError("boom")])

        res = _run_sequential(mod, {"postgresql": [(batiment, {}), (route, {})]}, callback)

        assert res["success"] is False
        assert res["failed_layer_names"] == ["route"]
        route.featureCount.assert_not_called()

    def test_skipped_invalid_layer_is_not_counted_in_cascade_line(self, caplog, monkeypatch):
        mod = _load()
        monkeypatch.setattr(mod, "is_layer_valid", lambda layer: layer.name() != "ghost")
        _capture(caplog)
        res = _run_sequential(mod, {"ogr": [(_layer("ghost"), {}), (_layer("route"), {})]},
                              MagicMock(return_value=True))

        assert res["success"] is False
        cascade = [r.getMessage() for r in caplog.records if r.getMessage().startswith("⏱ cascade_filter: ")]
        assert len(cascade) == 1 and "1 layer(s) in the worker" in cascade[0]

    def test_cancel_still_logs_the_cascade_line(self, caplog):
        mod = _load()
        _capture(caplog)
        res = mod.FilteringOrchestrator()._filter_all_layers_sequential(
            layers={"ogr": [(_layer("route"), {}), (_layer("haie"), {})]}, layers_count=2,
            execute_geometric_filtering_callback=MagicMock(return_value=True),
            is_canceled_callback=lambda: True,
            set_progress_callback=lambda percent: None,
            set_description_callback=lambda text: None,
        )

        assert res["success"] is False
        cascade = [r.getMessage() for r in caplog.records if r.getMessage().startswith("⏱ cascade_filter: ")]
        assert len(cascade) == 1 and "1 layer(s) in the worker" in cascade[0]


@pytest.mark.unit
class TestProgressWithoutTargets:

    def test_no_target_layer_is_complete_not_a_crash(self):
        mod = _load()
        assert mod._progress_percent(1, 0) == 100.0
        assert mod._progress_percent(2, 4) == 50.0

    def test_sequential_cascade_with_no_layer(self):
        mod = _load()
        res = _run_sequential(mod, {}, MagicMock(return_value=True))
        assert res["success"] is True
