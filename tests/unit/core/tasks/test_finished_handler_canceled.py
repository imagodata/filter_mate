# -*- coding: utf-8 -*-
"""
2026-10-17: a canceled filter task applies nothing and reports nothing, even when its run() completed.

A second click on Filter cancels the running task; it completed anyway and
its finished() applied the subsets it had queued (before or after the new
task's), and showed its success message. A PostgreSQL query interrupted by
the cancel is no error to show either.
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


def _package(name):
    module = types.ModuleType(name)
    module.__path__ = []
    return module


def _load():
    log_module = types.ModuleType(f"{ROOT}.infrastructure.logging")
    log_module.setup_logger = lambda *args, **kwargs: logging.getLogger("fm_test_finished_canceled")
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
            f"{ROOT}.core.tasks._fm_test_finished_canceled", PLUGIN_ROOT / "core" / "tasks" / "finished_handler.py"
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


@pytest.fixture
def finished(monkeypatch):
    module = _load()
    apply = MagicMock(return_value=1)
    monkeypatch.setattr(module, "apply_pending_subset_requests", apply)
    iface = MagicMock()
    qgis_utils = types.ModuleType("qgis.utils")
    qgis_utils.iface = iface
    monkeypatch.setitem(sys.modules, "qgis.utils", qgis_utils)
    handler = module.FinishedHandler()
    for name in ("_release_task_caches", "_log_task_bridge_metrics"):
        monkeypatch.setattr(handler, name, MagicMock())

    cleanup_mv, cleanup_canceled = MagicMock(), MagicMock()

    project = MagicMock()
    project.mapLayer.side_effect = lambda layer_id: MagicMock()  # every target still in the project
    monkeypatch.setattr(module, "QgsProject", MagicMock(instance=MagicMock(return_value=project)))
    monkeypatch.setattr(module, "QCoreApplication",
                        types.SimpleNamespace(translate=lambda context, text: text), raising=False)

    def run(canceled, result=True, exception=None, task_action="filter", pending=None, task_parameters=None):
        handler.handle_finished(
            result=result, task_action=task_action, message_category="FilterLayers",
            is_canceled_fn=lambda: canceled, warning_messages=[],
            pending_subset_requests=pending if pending is not None else [(MagicMock(), '"id" > 3')],
            safe_set_subset_fn=MagicMock(), is_complex_filter_fn=MagicMock(), single_canvas_refresh_fn=MagicMock(),
            cleanup_mv_fn=cleanup_mv, ogr_source_geom=None, exception=exception, task_message=None,
            source_layer=MagicMock(), task_parameters=task_parameters or {}, failed_layer_names=[], layers_count=1,
            task_description="Filtering data", restore_selection_fn=MagicMock(), task_bridge=None,
            cleanup_safe_intersect_fn=MagicMock(), cleanup_canceled_mv_fn=cleanup_canceled,
        )

    return types.SimpleNamespace(run=run, apply=apply, iface=iface, handler=handler, cleanup_mv=cleanup_mv,
                                 cleanup_canceled=cleanup_canceled, project=project)


def test_a_completed_task_applies_its_subsets(finished, monkeypatch):
    monkeypatch.setattr(finished.handler, "_display_success_message", MagicMock())
    finished.run(canceled=False)
    finished.apply.assert_called_once()
    finished.handler._display_success_message.assert_called_once()


def test_a_canceled_task_that_completed_applies_nothing(finished, monkeypatch):
    monkeypatch.setattr(finished.handler, "_display_success_message", MagicMock())
    finished.run(canceled=True, result=True)
    finished.apply.assert_not_called()
    finished.handler._display_success_message.assert_not_called()


def test_an_interrupted_query_of_a_canceled_task_is_no_error(finished):
    finished.run(canceled=True, result=False, exception=RuntimeError("canceling statement due to user request"))
    finished.apply.assert_not_called()
    finished.iface.messageBar.return_value.pushMessage.assert_not_called()


def _task_scoped_parameters():
    tree = ast.parse((PLUGIN_ROOT / "core" / "tasks" / "filter_task.py").read_text(encoding="utf-8"))
    nodes = [node for node in tree.body
             if (isinstance(node, ast.FunctionDef) and node.name == "task_scoped_parameters")
             or (isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "_SHARED_TASK_PARAMETER_KEYS"
                                                      for t in node.targets))]
    assert len(nodes) == 2
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "filter_task.py", "exec"), namespace)
    return namespace["task_scoped_parameters"]


def test_each_task_owns_its_parameters():
    """The worker writes into the task's parameters; the PROJECT_LAYERS entry stays as it was."""
    copy = _task_scoped_parameters()
    feature, layer, config = object(), object(), {"APP": {"OPTIONS": {}}}
    live = {"infos": {"layer_id": "zones"}, "filtering": {"layers_to_filter": ["roads"]},
            "task": {"features": [feature], "layers": [{"layer_id": "roads", "layer": layer}],
                     "config_data": config}}
    params = copy(live)
    params["_subset_queue_callback"] = print
    params["infos"]["source_geom_wkt"] = "POINT(0 0)"
    params["filtering"]["layers_to_filter"].append("rivers")
    params["task"]["layers"][0]["layer_name"] = "roads"
    assert live == {"infos": {"layer_id": "zones"}, "filtering": {"layers_to_filter": ["roads"]},
                    "task": {"features": [feature], "layers": [{"layer_id": "roads", "layer": layer}],
                             "config_data": config}}
    assert params["task"]["features"][0] is feature  # QGIS objects are shared, never copied
    assert params["task"]["layers"][0]["layer"] is layer
    assert params["task"]["config_data"] is config  # the app's settings, read only


@pytest.mark.parametrize("task_action", ["reset", "unfilter"])
def test_a_canceled_reset_keeps_the_views_the_layers_read(finished, monkeypatch, task_action):
    """2026-10-17 review: its subsets were not applied, the layers still read those views."""
    monkeypatch.setattr(finished.handler, "_display_success_message", MagicMock())
    finished.run(canceled=True, result=True, task_action=task_action)
    finished.cleanup_mv.assert_not_called()
    finished.cleanup_canceled.assert_called_once_with()  # only its own unused views


@pytest.mark.parametrize("task_action", ["reset", "unfilter"])
def test_a_completed_reset_drops_the_views(finished, monkeypatch, task_action):
    monkeypatch.setattr(finished.handler, "_display_success_message", MagicMock())
    finished.run(canceled=False, task_action=task_action)
    finished.cleanup_mv.assert_called_once_with()
    finished.cleanup_canceled.assert_not_called()


def test_a_completed_filter_keeps_its_views(finished, monkeypatch):
    monkeypatch.setattr(finished.handler, "_display_success_message", MagicMock())
    finished.run(canceled=False, task_action="filter")
    finished.cleanup_mv.assert_not_called()
    finished.cleanup_canceled.assert_not_called()


def test_a_target_removed_during_the_filter_is_left_out_with_a_warning(finished, monkeypatch):
    """2026-10-17 review: the filter depends on its source only; the other targets get their subsets."""
    monkeypatch.setattr(finished.handler, "_display_success_message", MagicMock())
    kept, removed = MagicMock(), MagicMock()
    removed.id.side_effect = RuntimeError("wrapped C/C++ object of type QgsVectorLayer has been deleted")
    finished.project.mapLayer.side_effect = lambda layer_id: None if layer_id == "rivers" else MagicMock()
    finished.run(canceled=False, pending=[(kept, '"id" > 3'), (removed, '"id" < 2')],
                 task_parameters={"task": {"layers": [{"layer_id": "roads", "layer_name": "roads"},
                                                      {"layer_id": "rivers", "layer_name": "rivers"}]}})
    applied = finished.apply.call_args.args[0]
    assert applied == [(kept, '"id" > 3')]
    warning = finished.iface.messageBar.return_value.pushWarning.call_args.args[1]
    assert "rivers" in warning and "roads" not in warning
