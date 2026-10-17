# -*- coding: utf-8 -*-
"""
2026-10-17: filter and export tasks carry the user's configuration.

Nothing put the configuration into the task parameters; the readers
(PARALLEL_FILTERING, STREAMING_EXPORT, OPTIMIZATION_THRESHOLDS,
GEOMETRY_SIMPLIFICATION) all fell back to their defaults. The method is
extracted from filter_mate_app.py with ast, like the other app tests, so the
plugin module itself is never imported.
"""
import ast
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

_APP = Path(__file__).resolve().parents[2] / "filter_mate_app.py"


def _get_task_parameters():
    tree = ast.parse(_APP.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterMateApp")
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "get_task_parameters")
    namespace = {"logger": logging.getLogger("test"), "is_layer_source_available": lambda layer: True,
                 "_get_option_value": lambda value, default: default}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(_APP), "exec"), namespace)
    return namespace["get_task_parameters"]


def _app(config):
    layer = MagicMock()
    layer.id.return_value = "layer-1"
    builder = MagicMock()
    builder.validate_current_layer_for_task.return_value = None
    builder.sync_ui_to_project_layers.return_value = {"infos": {}}
    builder.get_and_validate_features.return_value = ([], "")
    builder.determine_skip_source_filter.return_value = False
    builder.build_export_params.return_value = {"task": {"EXPORTING": {}}}
    return SimpleNamespace(
        tasks_descriptions={"filter": "Filtering", "export": "Exporting", "add_layers": "Adding"},
        dockwidget=SimpleNamespace(current_layer=layer, forced_backends={}),
        _get_task_builder=lambda: builder,
        _build_layers_to_filter=lambda current_layer: [],
        _build_common_task_params=lambda features, expression, layers, include_history: {"session_id": "s"},
        _initialize_filter_history=lambda *args: None,
        PROJECT_LAYERS={"layer-1": {}}, PROJECT=MagicMock(), session_id="s",
        CONFIG_DATA=config,
    )


@pytest.mark.unit
@pytest.mark.parametrize("task_name", ["filter", "export"])
def test_task_parameters_carry_the_configuration(task_name):
    config = {"APP": {"OPTIONS": {"PARALLEL_FILTERING": {"enabled": {"value": False}}}}}
    params = _get_task_parameters()(_app(config), task_name)
    assert params["task"]["config_data"] is config
