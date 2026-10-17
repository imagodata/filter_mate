# -*- coding: utf-8 -*-
"""
2026-10-17: the materialized views of a filter stay while a target uses them.

The materialized view handler registered the users of a source MV through
``hasattr(self.task, 'param_all_layers')``, an attribute nothing defined:
only the source layer was recorded. Unfiltering the source then found no
other user and ran ``DROP MATERIALIZED VIEW ... CASCADE`` on views the
distant layers' subsets still referenced. An export, which creates no MV,
ran the same cleanup.
"""
import ast
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


def _filter_task_property(name):
    tree = ast.parse((PLUGIN_ROOT / "core" / "tasks" / "filter_task.py").read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterEngineTask")
    prop = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)
    holder = ast.ClassDef(name="_Task", bases=[], keywords=[], body=[prop], decorator_list=[])
    namespace = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[holder], type_ignores=[])), "filter_task.py", "exec"),
         namespace)
    return namespace["_Task"]


def _layer(layer_id):
    layer = MagicMock()
    layer.id.return_value = layer_id
    return layer


def test_task_exposes_its_target_layers():
    task_cls = _filter_task_property("param_all_layers")
    task = task_cls()
    ducts, sheaths, roads = _layer("ducts"), _layer("sheaths"), _layer("roads")
    task.layers = {"postgresql": [(ducts, {}), (sheaths, {})], "ogr": [(roads, {})]}
    assert task.param_all_layers == [ducts, sheaths, roads]


def test_layer_deleted_meanwhile_is_left_out():
    task = _filter_task_property("param_all_layers")()
    deleted = MagicMock()
    deleted.id.side_effect = RuntimeError("wrapped C/C++ object has been deleted")
    kept = _layer("ducts")
    task.layers = {"postgresql": [(deleted, {}), (kept, {})]}
    assert task.param_all_layers == [kept]


def test_task_without_organized_layers_has_none():
    task = _filter_task_property("param_all_layers")()
    assert task.param_all_layers == []
    task.layers = None
    assert task.param_all_layers == []


def _load_tracker():
    spec = importlib.util.spec_from_file_location(
        "fm_test_mv_reference_tracker",
        PLUGIN_ROOT / "adapters" / "backends" / "postgresql" / "mv_reference_tracker.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.MVReferenceTracker


def test_unfiltering_the_source_keeps_the_mv_of_the_targets():
    """What the handler registers with param_all_layers, and what the cleanup frees."""
    tracker = _load_tracker()()
    task = _filter_task_property("param_all_layers")()
    task.layers = {"postgresql": [(_layer("ducts"), {}), (_layer("sheaths"), {})]}

    # registration as materialized_view_handler does it
    tracker.add_reference("fm_temp_mv_s_src", "source")
    for layer in task.param_all_layers:
        tracker.add_reference("fm_temp_mv_s_src", layer.id())

    # unfilter of the source alone: the targets still use the view
    assert tracker.remove_all_references_for_layer("source") == set()
    assert tracker.is_referenced("fm_temp_mv_s_src")


def _load_finished_handler():
    log_module = types.ModuleType(f"{ROOT}.infrastructure.logging")
    log_module.setup_logger = lambda *args, **kwargs: logging.getLogger("fm_test_finished_mv")
    config_module = types.ModuleType(f"{ROOT}.config.config")
    config_module.ENV_VARS = {}
    completion = types.ModuleType(f"{ROOT}.core.tasks.task_completion_handler")
    for name in ("display_warning_messages", "apply_pending_subset_requests",
                 "schedule_canvas_refresh", "cleanup_memory_layer"):
        setattr(completion, name, MagicMock())
    completion.should_skip_subset_application = MagicMock(return_value=False)

    def package(name):
        module = types.ModuleType(name)
        module.__path__ = []
        return module

    stubs = {
        ROOT: package(ROOT),
        f"{ROOT}.core": package(f"{ROOT}.core"),
        f"{ROOT}.core.tasks": package(f"{ROOT}.core.tasks"),
        f"{ROOT}.core.tasks.task_completion_handler": completion,
        f"{ROOT}.infrastructure": package(f"{ROOT}.infrastructure"),
        f"{ROOT}.infrastructure.logging": log_module,
        f"{ROOT}.config": package(f"{ROOT}.config"),
        f"{ROOT}.config.config": config_module,
    }
    saved = {key: sys.modules.get(key) for key in stubs}
    sys.modules.update(stubs)
    try:
        spec = importlib.util.spec_from_file_location(
            f"{ROOT}.core.tasks._fm_test_finished_handler_mv",
            PLUGIN_ROOT / "core" / "tasks" / "finished_handler.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.FinishedHandler
    finally:
        for key, value in saved.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


@pytest.mark.parametrize("task_action, cleans", [
    ("export", False), ("filter", False), ("unfilter", True), ("reset", True),
])
def test_mv_cleanup_only_when_filters_are_removed(task_action, cleans, monkeypatch):
    handler = _load_finished_handler()()
    for name in ("_handle_result_messages", "_cleanup_ogr_temp_layers", "_release_task_caches",
                 "_log_task_bridge_metrics"):
        monkeypatch.setattr(handler, name, MagicMock())
    monkeypatch.setitem(sys.modules, "qgis.utils", MagicMock())
    cleanup_mv = MagicMock()
    handler.handle_finished(
        result=True, task_action=task_action, message_category="FilterMate",
        is_canceled_fn=lambda: False, warning_messages=[], pending_subset_requests=[],
        safe_set_subset_fn=MagicMock(), is_complex_filter_fn=MagicMock(), single_canvas_refresh_fn=MagicMock(),
        cleanup_mv_fn=cleanup_mv, ogr_source_geom=None, exception=None, task_message=None,
        source_layer=None, task_parameters={}, failed_layer_names=[], layers_count=1,
        task_description="", restore_selection_fn=MagicMock(), task_bridge=None,
        cleanup_safe_intersect_fn=MagicMock(),
    )
    assert cleanup_mv.called is cleans
