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

The other way round, QGIS Qt5 builds only alias these classes in
`qgis.PyQt.QtGui` since 3.34.2: `from qgis.PyQt.QtGui import QAction` stopped
the plugin from loading on QGIS 3.22-3.34.1 (found by the QGIS Docker CI job,
October 2026). Every QtGui import of one of these symbols therefore sits in a
`try` whose `except ImportError` imports it from QtWidgets, and that fallback
is the only QtWidgets import allowed:

    try:
        from qgis.PyQt.QtGui import QAction
    except ImportError:  # QGIS < 3.34.2 (Qt5): QAction is in QtWidgets
        from qgis.PyQt.QtWidgets import QAction
"""
import ast
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

EXCLUDED_DIRS = {
    "tests", ".git", "__pycache__", ".claude",
    "_bmad", "_bmad-output", "website", "docs", "knowledge", "dist", "build",
}
# Not shipped in the release zip, run on a known QGIS: no Qt5 fallback needed.
UNSHIPPED_DIRS = EXCLUDED_DIRS | {"scripts"}

RELOCATED_SYMBOLS = {
    "QAction", "QActionGroup", "QFileSystemModel",
    "QShortcut", "QUndoCommand", "QUndoGroup", "QUndoStack",
}
# A missing name raises a plain ImportError ("cannot import name"), never ModuleNotFoundError.
IMPORT_ERRORS = {"ImportError", "Exception", "BaseException"}


def _plugin_python_files(excluded=EXCLUDED_DIRS):
    for path in PLUGIN_ROOT.rglob("*.py"):
        if any(part in excluded for part in path.relative_to(PLUGIN_ROOT).parts):
            continue
        yield path


def _relocated_imports(nodes, module_suffix):
    """``(lineno, symbol)`` of the relocated symbols imported from ``module_suffix`` under ``nodes``."""
    found = set()
    for root in nodes:
        for node in ast.walk(root):
            if isinstance(node, ast.ImportFrom) and (node.module or "").endswith(module_suffix):
                found |= {(node.lineno, alias.name) for alias in node.names if alias.name in RELOCATED_SYMBOLS}
    return found


def _catches_import_error(handler):
    kinds = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    return any(kind is None or (isinstance(kind, ast.Name) and kind.id in IMPORT_ERRORS) for kind in kinds)


def _only_relocated_imports(statements, module_suffix):
    """The set of symbols when ``statements`` only import relocated symbols from ``module_suffix``, else None.

    Anything else in the ``try`` (another name, another statement) would be skipped, or undefined, when the
    QtGui import fails on QGIS < 3.34.2.
    """
    symbols = set()
    for statement in statements:
        if not (isinstance(statement, ast.ImportFrom) and (statement.module or "").endswith(module_suffix)):
            return None
        names = {alias.asname or alias.name for alias in statement.names}
        if not {alias.name for alias in statement.names} <= RELOCATED_SYMBOLS:
            return None
        symbols |= names
    return symbols or None


def _guarded_pairs(tree):
    """QtGui imports that have a QtWidgets fallback, and those fallbacks."""
    guarded = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        symbols = _only_relocated_imports(node.body, "QtGui")
        if symbols is None:
            continue
        for handler in node.handlers:
            if _catches_import_error(handler) and _only_relocated_imports(handler.body, "QtWidgets") == symbols:
                guarded |= _relocated_imports(node.body, "QtGui") | _relocated_imports(handler.body, "QtWidgets")
    return guarded


def _module_aliases(tree, module):
    """Names bound to the ``module`` module (``QtGui`` / ``QtWidgets``), whatever the import form."""
    names = {module}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names |= {alias.asname or alias.name for alias in node.names if alias.name == module}
        elif isinstance(node, ast.Import):
            names |= {alias.asname for alias in node.names if alias.asname and alias.name.endswith("." + module)}
    return names


def _attribute_uses(tree, module):
    """``QtGui.QAction``, ``G.QAction`` (alias) and ``qgis.PyQt.QtGui.QAction``."""
    aliases = _module_aliases(tree, module)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in RELOCATED_SYMBOLS:
            value = node.value
            if (isinstance(value, ast.Name) and value.id in aliases) or (
                    isinstance(value, ast.Attribute) and value.attr == module):
                found.append((node.lineno, node.attr))
    return found


def _star_imports(tree):
    """``from qgis.PyQt.QtGui import *``: whether QAction comes along depends on the Qt version."""
    return [(node.lineno, "*") for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and (node.module or "").endswith(("QtGui", "QtWidgets"))
            and any(alias.name == "*" for alias in node.names)]


def _find_offenses(tree):
    guarded = _guarded_pairs(tree)
    return sorted(_relocated_imports([tree], "QtWidgets") - guarded) + _attribute_uses(tree, "QtWidgets")


def _qtgui_attributes(tree):
    """``QtGui.QAction(...)``: an AttributeError on QGIS < 3.34.2, import with the fallback instead."""
    return _attribute_uses(tree, "QtGui") + _star_imports(tree)


def _parsed(excluded=EXCLUDED_DIRS):
    for path in _plugin_python_files(excluded):
        source = path.read_text(encoding="utf-8")
        if any(sym in source for sym in RELOCATED_SYMBOLS):
            yield path, ast.parse(source, filename=str(path))


@pytest.mark.unit
def test_no_relocated_qtwidgets_symbols():
    """QAction/QShortcut/QUndoStack/... must be imported from QtGui, not QtWidgets, for Qt6."""
    violations = [f"{path.relative_to(PLUGIN_ROOT)}:{lineno} ({name})"
                  for path, tree in _parsed() for lineno, name in _find_offenses(tree)]
    assert not violations, (
        "QtWidgets symbols relocated to QtGui under Qt6 (breaks on QGIS 4.x): "
        + ", ".join(violations)
    )


@pytest.mark.unit
def test_relocated_qtgui_symbols_fall_back_to_qtwidgets():
    """QGIS < 3.34.2 (Qt5) has no QAction/QShortcut/... in qgis.PyQt.QtGui: each import needs the fallback."""
    violations = []
    for path, tree in _parsed(UNSHIPPED_DIRS):
        missing = sorted(_relocated_imports([tree], "QtGui") - _guarded_pairs(tree)) + _qtgui_attributes(tree)
        violations += [f"{path.relative_to(PLUGIN_ROOT)}:{lineno} ({name})" for lineno, name in missing]
    assert not violations, (
        "QtGui imports of symbols that QGIS < 3.34.2 only has in QtWidgets (plugin fails to load): "
        + ", ".join(violations)
    )


@pytest.mark.unit
@pytest.mark.parametrize("source, offenses, missing", [
    ("from qgis.PyQt.QtWidgets import QAction\n", 1, 0),
    ("from qgis.PyQt.QtGui import QAction\n", 0, 1),
    ("try:\n    from qgis.PyQt.QtGui import QAction\nexcept ImportError:\n"
     "    from qgis.PyQt.QtWidgets import QAction\n", 0, 0),
    # The fallback must import the same symbol, from a handler that catches ImportError.
    ("try:\n    from qgis.PyQt.QtGui import QAction\nexcept ImportError:\n"
     "    from qgis.PyQt.QtWidgets import QShortcut\n", 1, 1),
    ("try:\n    from qgis.PyQt.QtGui import QAction\nexcept ValueError:\n"
     "    from qgis.PyQt.QtWidgets import QAction\n", 1, 1),
    ("import qgis.PyQt.QtWidgets as QtWidgets\nQtWidgets.QAction()\n", 1, 0),
    ("from qgis.PyQt import QtGui\nQtGui.QShortcut()\n", 0, 1),
    # ModuleNotFoundError is never raised for a missing name: no fallback.
    ("try:\n    from qgis.PyQt.QtGui import QAction\nexcept ModuleNotFoundError:\n"
     "    from qgis.PyQt.QtWidgets import QAction\n", 1, 1),
    # QIcon would be undefined on QGIS < 3.34.2.
    ("try:\n    from qgis.PyQt.QtGui import QAction, QIcon\nexcept ImportError:\n"
     "    from qgis.PyQt.QtWidgets import QAction\n", 1, 1),
    ("try:\n    from qgis.PyQt.QtGui import QAction\n    x = 1\nexcept ImportError:\n"
     "    from qgis.PyQt.QtWidgets import QAction\n", 1, 1),
    ("from qgis.PyQt import QtGui as G\nG.QAction()\n", 0, 1),
    ("import qgis.PyQt.QtGui as G\nG.QAction()\n", 0, 1),
    ("import qgis.PyQt.QtGui\nqgis.PyQt.QtGui.QAction()\n", 0, 1),
    ("from qgis.PyQt import QtWidgets as W\nW.QAction()\n", 1, 0),
    ("from qgis.PyQt.QtGui import *\nQAction()\n", 0, 1),
    ("try:\n    from qgis.PyQt.QtGui import QAction, QShortcut\nexcept ImportError:\n"
     "    from qgis.PyQt.QtWidgets import QAction, QShortcut\n", 0, 0),
])
def test_guard_rules(source, offenses, missing):
    tree = ast.parse(source)
    assert len(_find_offenses(tree)) == offenses
    assert len(_relocated_imports([tree], "QtGui") - _guarded_pairs(tree)) + len(_qtgui_attributes(tree)) == missing
