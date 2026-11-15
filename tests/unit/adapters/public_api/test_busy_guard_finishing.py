# -*- coding: utf-8 -*-
"""Busy guard: a dock task in its ``finished()`` (2026-10-20).

#199 let a dock task in its ``finished()`` (still listed by QGIS, status
Complete or Terminated) pass the guard, so that the dock can install that
task's own server subsets there (ServerSubsetJob). The same tolerant check
also answered ``busy_reason()``: a REST / MCP / Python API call could start
in the middle of that ``finished()``. Only the start of a server filter
tolerates it now.
"""
import ast
import importlib
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_busy_guard_test"


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

RUNNING, COMPLETE, TERMINATED = 2, 3, 4


class _Task:
    def __init__(self, status):
        self._status = status

    def status(self):
        return self._status


@pytest.fixture
def dock_task(monkeypatch):
    """A FilterEngineTask of the dock listed by the task manager, with a settable status."""
    active = []
    manager = MagicMock()
    manager.tasks.side_effect = lambda: list(active)
    # QgsTaskManager::processQueue drops a Complete task from activeTasks() as soon as
    # another task is queued, while its finished() still runs (probed on 3.22 - 4.2).
    manager.activeTasks.side_effect = lambda: [task for task in active if task.status() not in (COMPLETE, TERMINATED)]
    qgis_core = sys.modules["qgis.core"]
    monkeypatch.setattr(qgis_core, "QgsApplication", MagicMock(taskManager=MagicMock(return_value=manager)),
                        raising=False)
    monkeypatch.setattr(qgis_core, "QgsTask", types.SimpleNamespace(
        TaskStatus=types.SimpleNamespace(Complete=COMPLETE, Terminated=TERMINATED)), raising=False)
    monkeypatch.setattr(service_mod, "_service", None)

    def add(status):
        active.append(type("FilterEngineTask", (_Task,), {})(status))

    yield add
    operations._RUNNING.clear()


@pytest.mark.parametrize("status", [COMPLETE, TERMINATED])
def test_an_api_call_waits_for_the_end_of_finished(dock_task, status):
    dock_task(status)
    assert operations._background_tasks_running()
    assert operations.busy_reason() == operations.BACKGROUND_BUSY
    report = operations.clear_filters(["parcelle"], project=MagicMock())
    assert report.details["busy"] is True and report.error == operations.BACKGROUND_BUSY


def test_a_server_filter_queued_in_finished_does_not_free_the_api(dock_task):
    """The server filter queues its own QgsTask: activeTasks() no longer lists the dock task, tasks() does."""
    dock_task(COMPLETE)
    manager = sys.modules["qgis.core"].QgsApplication.taskManager()
    assert manager.activeTasks() == [] and len(manager.tasks()) == 1
    assert operations.busy_reason() == operations.BACKGROUND_BUSY


@pytest.mark.parametrize("status, busy", [(RUNNING, True), (COMPLETE, False), (TERMINATED, False)])
def test_the_server_filter_start_tolerates_the_task_that_applies_it(dock_task, status, busy):
    dock_task(status)
    assert operations._background_tasks_running(allow_finishing=True) is busy


def test_no_task_is_idle_for_both(dock_task):
    assert not operations._background_tasks_running()
    assert not operations._background_tasks_running(allow_finishing=True)
    assert operations.busy_reason() == ""


def test_server_filter_starts_are_the_only_tolerant_callers():
    """Both server filter starts (worker transfer and main-thread setter) run in the dock's finished()."""
    tolerant, strict = [], []
    sources = sorted(_ROOT.glob("*.py"))
    for folder in ("adapters", "core", "infrastructure", "ui", "filtermate_api"):
        sources += sorted((_ROOT / folder).rglob("*.py"))
    for path in sources:
        relative = path.relative_to(_ROOT).as_posix()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", "")) \
                    == "_background_tasks_running":
                allowed = any(keyword.arg == "allow_finishing" and getattr(keyword.value, "value", None) is True
                              for keyword in node.keywords)
                (tolerant if allowed else strict).append((relative, node.lineno))
    assert [name for name, _ in tolerant] == ["adapters/qgis/server_subset_job.py"] * 2
    assert all(name == "adapters/public_api/operations.py" for name, _ in strict), strict


# 2026-11-15: one Filter of the dock with a WFS layer and a web map among its targets. The capture of the web map
# (a CrossFilterTask) still ran when the dock set the filter of the WFS layer, and that filter was refused
# ("A FilterMate task is still reading layers"). A cross filter task that does not touch the layer does not count.

def _cross_task(status, source, *targets):
    task = type("CrossFilterTask", (_Task,), {})(status)
    task.source_job = types.SimpleNamespace(layer_id=source)
    task.target_jobs = [types.SimpleNamespace(layer_id=target) for target in targets]
    return task


@pytest.fixture
def cross_task(dock_task, monkeypatch):
    listed = []
    manager = sys.modules["qgis.core"].QgsApplication.taskManager()
    manager.tasks.side_effect = lambda: list(listed)
    return listed


def test_a_cross_filter_task_on_other_layers_does_not_hold_a_server_filter(cross_task):
    cross_task.append(_cross_task(RUNNING, "zones", "basemap"))
    assert not operations._background_tasks_running(allow_finishing=True, layer_id="wfs")
    assert operations._background_tasks_running(allow_finishing=True, layer_id="basemap")
    assert operations._background_tasks_running(allow_finishing=True, layer_id="zones")


def test_without_a_layer_every_cross_filter_task_counts(cross_task):
    """busy_reason() and the API: any running task, whatever it reads."""
    cross_task.append(_cross_task(RUNNING, "zones", "basemap"))
    assert operations._background_tasks_running()
    assert operations._background_tasks_running(allow_finishing=True)
    assert operations.busy_reason() == operations.BACKGROUND_BUSY


def test_a_cross_filter_task_whose_layers_cannot_be_told_counts(cross_task):
    task = _cross_task(RUNNING, "zones")
    task.source_job = types.SimpleNamespace(layer_id=None)
    cross_task.append(task)
    assert operations._background_tasks_running(allow_finishing=True, layer_id="wfs")


def test_the_engine_task_of_the_dock_still_holds_a_server_filter(cross_task):
    """Only a cross filter task is told apart by its layers; the filter engine task reads them all."""
    cross_task.append(type("FilterEngineTask", (_Task,), {})(RUNNING))
    assert operations._background_tasks_running(allow_finishing=True, layer_id="wfs")


def test_a_cross_filter_task_of_the_service_is_told_apart_too(dock_task, monkeypatch):
    service = types.SimpleNamespace(_running=[_cross_task(RUNNING, "zones", "basemap")])
    monkeypatch.setattr(service_mod, "get_cross_filter_service", lambda: service)
    assert not operations._background_tasks_running(allow_finishing=True, layer_id="wfs")
    assert operations._background_tasks_running(allow_finishing=True, layer_id="basemap")
