# -*- coding: utf-8 -*-
"""
Regression test for the Qt6 QtWidgets -> QtGui relocations.

PyQt6 (Qt6) moved several classes out of QtWidgets into QtGui:
QAction, QActionGroup, QFileSystemModel, QShortcut, QUndoCommand,
QUndoGroup, QUndoStack. Code that does
`from qgis.PyQt.QtWidgets import QShortcut` (or `QtWidgets.QShortcut(...)`)
imports fine under PyQt5/QGIS3 but raises ImportError/AttributeError under
PyQt6/QGIS4 -- found in `filter_mate_dockwidget.py` and
`ui/widgets/json_view/searchable_view.py` during the QGIS 4.2 port.

Every reference to one of these symbols via QtWidgets must instead go
through QtGui.
"""
import ast
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

EXCLUDED_DIRS = {
    "tests", "video_toolkit", "video_automation", ".git", "__pycache__",
    "_bmad", "_bmad-output", "website", "docs", "knowledge", "dist", "build",
}

RELOCATED_SYMBOLS = {
    "QAction", "QActionGroup", "QFileSystemModel",
    "QShortcut", "QUndoCommand", "QUndoGroup", "QUndoStack",
}


def _plugin_python_files():
    for path in PLUGIN_ROOT.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in path.relative_to(PLUGIN_ROOT).parts):
            continue
        yield path


def _find_offenses(tree):
    offenses = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.endswith("QtWidgets"):
                for alias in node.names:
                    if alias.name in RELOCATED_SYMBOLS:
                        offenses.append((node.lineno, alias.name))
        elif isinstance(node, ast.Attribute):
            if node.attr in RELOCATED_SYMBOLS and isinstance(node.value, ast.Name) and node.value.id == "QtWidgets":
                offenses.append((node.lineno, node.attr))
    return offenses


@pytest.mark.unit
def test_no_relocated_qtwidgets_symbols():
    """QAction/QShortcut/QUndoStack/... must be imported from QtGui, not QtWidgets, for Qt6."""
    violations = []
    for path in _plugin_python_files():
        source = path.read_text(encoding="utf-8")
        if not any(sym in source for sym in RELOCATED_SYMBOLS):
            continue
        tree = ast.parse(source, filename=str(path))
        for lineno, name in _find_offenses(tree):
            violations.append(f"{path.relative_to(PLUGIN_ROOT)}:{lineno} ({name})")

    assert not violations, (
        "QtWidgets symbols relocated to QtGui under Qt6 (breaks on QGIS 4.x): "
        + ", ".join(violations)
    )
