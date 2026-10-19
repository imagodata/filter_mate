# -*- coding: utf-8 -*-
"""2026-10-17: the legacy adapter's new-backend path queues the subset for the main thread.

``BaseLegacyAdapter._apply_filter_new`` (every PostgreSQL target: the PostgreSQL adapter
always takes it) called setSubsetString from the task's worker. Found by
run_postgis_check.py: on a second click on Filter, the canceled first task, still running,
wrote its subset on the target after the second task's (an outdated filter shown, the second
task's view left unread). Queued, the subset of a canceled task is never applied
(finished() drops its requests), and setSubsetString runs on the main thread as for the
other backends.
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


legacy_module = _load(
    f"{ROOT}.adapters.backends._fm_test_legacy_adapter_queue",
    PLUGIN_ROOT / "adapters" / "backends" / "legacy_adapter.py",
    {},
)


def _adapter(task_params):
    adapter = legacy_module.LegacyPostgreSQLAdapter.__new__(legacy_module.LegacyPostgreSQLAdapter)
    adapter.task_params = task_params
    adapter._use_new_backend = True
    adapter._new_backend = MagicMock()
    adapter._legacy_backend = MagicMock()
    return adapter


@pytest.fixture
def sql_utils(monkeypatch):
    """The in-place setter of the path without a task (sql_utils is imported inside the method)."""
    module = types.ModuleType(f"{ROOT}.infrastructure.database.sql_utils")
    module.safe_set_subset_string = MagicMock(return_value=True)
    for name in (ROOT, f"{ROOT}.infrastructure", f"{ROOT}.infrastructure.database"):
        monkeypatch.setitem(sys.modules, name, sys.modules.get(name) or _package(name))
    monkeypatch.setitem(sys.modules, module.__name__, module)
    return module


def test_a_task_subset_is_queued_not_set_from_the_worker(sql_utils):
    queue = MagicMock()
    layer = MagicMock()
    adapter = _adapter({"_subset_queue_callback": queue})

    assert adapter.apply_filter(layer, '"id" IN (1)', '"kind" = 2', "AND") is True

    queue.assert_called_once_with(layer, '("kind" = 2) AND ("id" IN (1))')
    sql_utils.safe_set_subset_string.assert_not_called()
    layer.setSubsetString.assert_not_called()


def test_replace_strategy_is_queued_alone(sql_utils):
    queue = MagicMock()
    layer = MagicMock()
    assert _adapter({"_subset_queue_callback": queue}).apply_filter(layer, '"id" IN (1)', '"kind" = 2', None)
    queue.assert_called_once_with(layer, '"id" IN (1)')


def test_without_a_task_the_subset_is_set_in_place(sql_utils):
    layer = MagicMock()
    assert _adapter({}).apply_filter(layer, '"id" IN (1)') is True
    sql_utils.safe_set_subset_string.assert_called_once_with(layer, '"id" IN (1)')


def test_remote_warnings_cross_the_real_legacy_adapter_boundary():
    adapter = _adapter({})
    adapter._legacy_backend.user_warnings = ['Partial result: feature limit reached.']
    assert adapter.user_warnings is adapter._legacy_backend.user_warnings
    adapter.user_warnings = []
    assert adapter._legacy_backend.user_warnings == []


def test_remote_outcome_is_visible_through_the_legacy_adapter():
    adapter = _adapter({})
    outcome = object()
    adapter._legacy_backend.remote_materialization_outcome = outcome
    assert adapter.remote_materialization_outcome is outcome
