# -*- coding: utf-8 -*-
"""
Dock controllers across a close / reopen and an unload (FilterMate 5).

- Closing the dock (its X) only hides it: run() shows the same dock again.
  closeEvent used to tear the controllers down, so the reopened dock lost its
  raster / point cloud mode (a raster picked then left the vector layer
  current). The controllers now go when the plugin unloads.
- unload() removes and deletes the dock without a closeEvent: it tears the
  controllers down itself, before removeDockWidget, so the raster / point
  cloud controller disconnects from the project signals.

The methods are extracted from filter_mate_dockwidget.py / filter_mate.py with
ast (those modules cannot be imported outside QGIS).
"""
import ast
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]


class FakeVectorLayer:
    def id(self):
        return "zones"


def _extract(path, class_name, name, namespace):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name):
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
                return namespace[name]
    raise AssertionError(f"{class_name}.{name} not found in {path.name}")


def _dock_method(name):
    namespace = {"logger": MagicMock(), "QgsVectorLayer": FakeVectorLayer, "_active_dockwidget": None}
    return _extract(_ROOT / "filter_mate_dockwidget.py", "FilterMateDockWidget", name, namespace)


def _dock(current_layer=None):
    dock = MagicMock()
    dock.widgets_initialized = True
    dock.current_layer = current_layer
    return dock


def test_closing_the_dock_keeps_the_controllers():
    dock, event = _dock(), MagicMock()
    _dock_method("closeEvent")(dock, event)
    dock._controller_integration.teardown.assert_not_called()
    dock._controller_integration.on_dock_closed.assert_called_once_with()
    dock.closingPlugin.emit.assert_called_once_with()
    event.accept.assert_called_once_with()


def test_unload_tears_the_controllers_down_before_removing_the_dock():
    unload = _extract(_ROOT / "filter_mate.py", "FilterMate", "unload", {"logger": MagicMock()})
    plugin, steps = MagicMock(), MagicMock()
    plugin.actions = []
    dock = plugin.app.dockwidget
    steps.attach_mock(dock._controller_integration.teardown, "teardown")
    steps.attach_mock(plugin.iface.removeDockWidget, "removeDockWidget")
    unload(plugin)
    assert steps.mock_calls == [call.teardown(), call.removeDockWidget(dock)]
