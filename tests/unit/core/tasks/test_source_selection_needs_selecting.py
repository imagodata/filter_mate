# -*- coding: utf-8 -*-
"""After a filter, the source features are selected only when IS_SELECTING is on.

2026-11-13: FilterEngineTask._restore_source_layer_selection selected the exploring
features of the source layer after every filter, unfilter and reset, whatever the
state of the IS_SELECTING button: the source feature turned selected on the map
although the user never asked FilterMate to drive the QGIS selection.
Method extracted with ast.
"""
import ast
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[4]
_MODULE = _ROOT / "core" / "tasks" / "filter_task.py"
_FIDS = [3, 7]


def _restore():
    tree = ast.parse(_MODULE.read_text(encoding="utf-8"))
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == "_restore_source_layer_selection":
                ns = {"logger": MagicMock(), "is_valid_layer": lambda layer: True, "__package__": "core.tasks"}
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(_MODULE), "exec"), ns)
                return ns["_restore_source_layer_selection"]
    raise AssertionError("method not found")


@pytest.fixture(autouse=True)
def local_source(monkeypatch):
    """The source is a local layer: its FIDs are stable."""
    capability = types.ModuleType("core.domain.source_capability")
    capability.classify_layer = lambda layer: types.SimpleNamespace(requires_server_translation=False)
    monkeypatch.setitem(sys.modules, "core.domain.source_capability", capability)


def _task(task_section, exploring=None):
    collector = MagicMock()
    params = {"task": {"feature_fids": _FIDS, **task_section}}
    if exploring is not None:
        params["exploring"] = exploring
    task = types.SimpleNamespace(source_layer=MagicMock(), task_parameters=params,
                                 _get_feature_collector=lambda: collector)
    return task, collector


def test_the_source_is_not_selected_when_selecting_is_off():
    task, collector = _task({"is_selecting": False}, exploring={"is_selecting": True})

    _restore()(task)

    collector.restore_layer_selection.assert_not_called()


def test_the_source_is_selected_again_when_selecting_is_on():
    task, collector = _task({"is_selecting": True}, exploring={"is_selecting": False})

    _restore()(task)

    collector.restore_layer_selection.assert_called_once_with(task.source_layer, _FIDS)


@pytest.mark.parametrize("exploring, selected", [
    ({"is_selecting": True}, True),
    ({"is_selecting": False}, False),
    ({}, False),
    (None, False),
])
def test_without_the_task_flag_the_layer_settings_decide(exploring, selected):
    """Parameters built elsewhere than the dock fall back to the layer's IS_SELECTING."""
    task, collector = _task({}, exploring=exploring)

    _restore()(task)

    assert collector.restore_layer_selection.called is selected
