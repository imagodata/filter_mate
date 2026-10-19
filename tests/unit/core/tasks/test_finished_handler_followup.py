# -*- coding: utf-8 -*-
"""FinishedHandler, 2026-10-17: refused filters reach the message bar; task caches are released."""
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


def _package(name):
    module = types.ModuleType(name)
    module.__path__ = []
    return module


def _load():
    log_module = types.ModuleType(f"{ROOT}.infrastructure.logging")
    log_module.setup_logger = lambda *args, **kwargs: logging.getLogger("fm_test_finished")
    config_module = types.ModuleType(f"{ROOT}.config.config")
    config_module.ENV_VARS = {}
    completion = types.ModuleType(f"{ROOT}.core.tasks.task_completion_handler")
    for name in ("display_warning_messages", "should_skip_subset_application", "apply_pending_subset_requests",
                 "schedule_canvas_refresh", "cleanup_memory_layer"):
        setattr(completion, name, MagicMock())
    stubs = {
        ROOT: _package(ROOT),
        f"{ROOT}.core": _package(f"{ROOT}.core"),
        f"{ROOT}.core.tasks": _package(f"{ROOT}.core.tasks"),
        f"{ROOT}.core.tasks.task_completion_handler": completion,
        f"{ROOT}.infrastructure": _package(f"{ROOT}.infrastructure"),
        f"{ROOT}.infrastructure.logging": log_module,
        f"{ROOT}.config": _package(f"{ROOT}.config"),
        f"{ROOT}.config.config": config_module,
    }
    saved = {key: sys.modules.get(key) for key in stubs}
    sys.modules.update(stubs)
    try:
        spec = importlib.util.spec_from_file_location(
            f"{ROOT}.core.tasks._fm_test_finished_handler", PLUGIN_ROOT / "core" / "tasks" / "finished_handler.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for key, value in saved.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


FinishedHandler = _load().FinishedHandler


def test_refused_filters_reach_the_message_bar():
    iface = MagicMock()
    FinishedHandler._display_apply_failures(["troncon_de_route: no such table: json_each"], iface)
    iface.messageBar.return_value.pushWarning.assert_called_once()


def test_task_caches_are_released():
    task = types.SimpleNamespace(_filtermate_task_caches={"ogr_source_geometry": {"k": "union"}})
    params = {"_parent_task": task, "_ogr_source_union_cache": {}, "_spatialite_source_bbox_cache": {}}
    selected = ["original selection"]
    params["task"] = {"features": selected, "_bounded_remote_source_features": ["raw copy"]}
    FinishedHandler._release_task_caches(params)
    assert not hasattr(task, "_filtermate_task_caches")
    assert "_ogr_source_union_cache" not in params and "_spatialite_source_bbox_cache" not in params
    assert params["task"] == {"features": selected}
    assert params["task"]["features"] is selected
