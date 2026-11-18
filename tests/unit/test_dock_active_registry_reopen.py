# -*- coding: utf-8 -*-
"""
2026-11-18 audit: a dock closed then shown again is the active dock again.

``_active_dockwidget`` was set in ``__init__`` only and cleared by ``closeEvent``; ``run()`` only shows the dock
again. ``sql_utils.feature_picker_guard`` then found no dock and left the QgsFeaturePickerWidget attached while the
subset string changed (the sqlite3_bind_int64 crash of February 2026).
"""
import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


def _dock_class():
    """The ``showEvent`` of the dock, on a base class that records what it hands on (the real method, so that
    ``super()`` and the module global work)."""
    tree = ast.parse((ROOT / "filter_mate_dockwidget.py").read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterMateDockWidget")
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "showEvent"]
    assert len(methods) == 1
    module = ast.Module(body=[ast.ClassDef(name="Dock", bases=[ast.Name(id="Base", ctx=ast.Load())], keywords=[],
                                           body=methods, decorator_list=[])], type_ignores=[])
    ast.fix_missing_locations(module)

    class Base:
        def __init__(self):
            self.shown = []

        def showEvent(self, event):  # noqa: N802 - Qt name
            self.shown.append(event)

    namespace = {"Base": Base, "_active_dockwidget": None}
    exec(compile(module, "filter_mate_dockwidget.py", "exec"), namespace)
    return namespace


def test_a_dock_shown_again_is_the_active_dock_again():
    namespace = _dock_class()
    dock = namespace["Dock"]()
    namespace["_active_dockwidget"] = None  # closeEvent took it off the registry
    dock.showEvent("event")
    assert namespace["_active_dockwidget"] is dock
    assert dock.shown == ["event"]  # Qt's own handling still runs


def test_the_close_event_still_leaves_the_registry():
    """The close event takes the dock off the registry (when it is the registered one): the show event above is what
    puts it back."""
    source = (ROOT / "filter_mate_dockwidget.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterMateDockWidget")
    close = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "closeEvent")
    text = ast.get_source_segment(source, close)
    assert "_active_dockwidget = None" in text and "if _active_dockwidget is self" in text


def test_a_dock_released_by_the_unload_does_not_register_again():
    """Unloading: release_qgis_connections empties the registry, then the panels give their sections back and a
    dock that was a tab behind one of them comes to the front: its show event must not take the registry again."""
    namespace = _dock_class()
    dock = namespace["Dock"]()
    dock._released = True  # what release_qgis_connections sets
    namespace["_active_dockwidget"] = None
    dock.showEvent("event")
    assert namespace["_active_dockwidget"] is None
    assert dock.shown == ["event"]


def test_the_release_sets_the_flag_that_the_show_event_reads():
    source = (ROOT / "filter_mate_dockwidget.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterMateDockWidget")
    release = next(node for node in cls.body if isinstance(node, ast.FunctionDef)
                   and node.name == "release_qgis_connections")
    assert "self._released = True" in ast.get_source_segment(source, release)
