# -*- coding: utf-8 -*-
"""
Dock controllers on unload (FilterMate 5).

- unload() removes and deletes the dock without a closeEvent: it tears the
  controllers down itself, before removeDockWidget, so the raster / point
  cloud controller disconnects from the project signals.

The method is extracted from filter_mate.py with ast (the plugin entry module
cannot be imported outside QGIS).
"""
import ast
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]


def _extract(path, class_name, name, namespace):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name):
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
                return namespace[name]
    raise AssertionError(f"{class_name}.{name} not found in {path.name}")


def test_unload_tears_the_controllers_down_before_removing_the_dock():
    unload = _extract(_ROOT / "filter_mate.py", "FilterMate", "unload", {"logger": MagicMock()})
    plugin, steps = MagicMock(), MagicMock()
    plugin.actions = []
    dock = plugin.app.dockwidget
    steps.attach_mock(dock._controller_integration.teardown, "teardown")
    steps.attach_mock(plugin.iface.removeDockWidget, "removeDockWidget")
    unload(plugin)
    assert steps.mock_calls == [call.teardown(), call.removeDockWidget(dock)]
