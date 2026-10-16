# -*- coding: utf-8 -*-
"""FilterMate 5 operations (``adapters.public_api.operations``) — audit 2026-10.

The module is loaded for real under a synthetic package (its relative
imports reach ``core`` and ``adapters``); QGIS stays mocked by the root
conftest, layers are small stand-ins.
"""
import importlib
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_operations_test"


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.domain", _ROOT / "core" / "domain"),
                       (".core.services", _ROOT / "core" / "services"), (".adapters", _ROOT / "adapters"),
                       (".adapters.public_api", _ROOT / "adapters" / "public_api"),
                       (".adapters.qgis", _ROOT / "adapters" / "qgis"),
                       (".adapters.qgis.coverage_layers", _ROOT / "adapters" / "qgis" / "coverage_layers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    return (importlib.import_module(f"{_PKG}.adapters.public_api.operations"),
            importlib.import_module(f"{_PKG}.core.services.cross_filter_service"))


operations, service_mod = _load()


@pytest.fixture
def idle(monkeypatch):
    """No FilterMate task of the dock runs."""
    monkeypatch.setattr(operations, "_background_tasks_running", lambda: False)
    yield
    operations._RUNNING.clear()


class TestOneAtATime:

    def test_idle_means_not_busy(self, idle):
        assert operations.busy_reason() == ""

    def test_an_operation_refuses_another_one_while_it_runs(self, idle):
        # e.g. a REST call re-entering through processEvents during an export.
        seen = {}

        @operations._exclusive
        def outer():
            seen["reason"] = operations.busy_reason()
            seen["inner"] = operations.clear_filters(["parcelle"], project=MagicMock())
            return operations.OperationReport()

        outer()
        assert "already running outer" in seen["reason"]
        assert seen["inner"].details["busy"] is True
        assert "already running" in seen["inner"].error
        assert operations.busy_reason() == ""  # released once over

    def test_lock_released_when_the_operation_raises(self, idle):
        @operations._exclusive
        def broken():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            broken()
        assert operations.busy_reason() == ""

    def test_export_is_exclusive_too(self, idle):
        operations._RUNNING.append("cross_filter")
        report = operations.export_layers(["parcelle"], "/tmp/x", project=MagicMock())
        assert report.details.get("busy") is True

    @pytest.mark.parametrize("call", [
        lambda: operations.cross_filter("src", ["t"], project=MagicMock()),
        lambda: operations.cross_filter_by_geometry(MagicMock(), None, ["t"], project=MagicMock()),
        lambda: operations.filter_point_clouds(["t"], "Classification = 2", project=MagicMock()),
        lambda: operations.clear_filters(["t"], project=MagicMock()),
        lambda: operations.apply_favorite("fav", service=MagicMock(), project=MagicMock()),
    ])
    def test_every_operation_refused_while_busy(self, monkeypatch, call):
        monkeypatch.setattr(operations, "_background_tasks_running", lambda: True)
        report = call()
        assert report.error == operations.BACKGROUND_BUSY
        assert report.details["busy"] is True


class _Task:
    def __init__(self, description):
        self._description = description

    def description(self):
        return self._description


class TestDockTasksDetected:
    """``_busy`` only saw the cross filter service: a vector filter task of the dock went unnoticed."""

    @pytest.fixture
    def tasks(self, monkeypatch):
        active = []
        manager = MagicMock()
        manager.activeTasks.side_effect = lambda: list(active)
        qgis_core = sys.modules["qgis.core"]
        monkeypatch.setattr(qgis_core, "QgsApplication", MagicMock(taskManager=MagicMock(return_value=manager)),
                            raising=False)
        monkeypatch.setattr(service_mod, "_service", None)
        return active

    def test_no_task(self, tasks):
        assert operations.busy_reason() == ""

    def test_vector_filter_task_of_the_dock(self, tasks):
        task_class = type("FilterEngineTask", (_Task,), {})
        tasks.append(task_class("Filtering data"))  # translated description, no "FilterMate" prefix
        assert operations.busy_reason() == operations.BACKGROUND_BUSY

    def test_filtermate_task(self, tasks):
        tasks.append(_Task("FilterMate: export"))
        assert operations.busy_reason() == operations.BACKGROUND_BUSY

    def test_other_plugin_task_is_ignored(self, tasks):
        tasks.append(_Task("Rendering"))
        assert operations.busy_reason() == ""
