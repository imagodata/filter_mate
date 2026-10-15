# -*- coding: utf-8 -*-
"""Spacers go into a layout with ``insertSpacerItem`` / ``addItem``, never ``insertItem``.

PyQt5 5.15.6 (the QGIS 3.22-3.34 builds) has no /Transfer/ on ``QBoxLayout.insertItem``: after
``layout.insertItem(1, QSpacerItem(...))`` Python still owned the spacer, deleted it at once, and the
dangling item crashed QGIS when the dock opened (found by tests/qgis_headless/run_gui_smoke.py;
``sip.ispyowned`` is True after insertItem on 5.15.6, False after insertSpacerItem / addItem).
A spacer kept in an attribute is only safe while that object lives.
"""
import ast
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_DIRS = {"tests", ".git", "__pycache__", ".claude", "_bmad", "_bmad-output", "website", "docs",
                 "knowledge", "dist", "build", "scripts"}


def _is_spacer(node):
    if not isinstance(node, ast.Call):
        return False
    name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
    return name == "QSpacerItem"


def _offenses(tree):
    """``insertItem(index, spacer)``: a QSpacerItem built inline or held by a name / attribute set from one."""
    spacers = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and _is_spacer(node.value):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            spacers |= {ast.unparse(target) for target in targets}
    found = []
    for call in ast.walk(tree):
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and call.func.attr == "insertItem" and len(call.args) == 2):
            continue
        item = call.args[1]
        if _is_spacer(item) or ast.unparse(item) in spacers:
            found.append((call.lineno, ast.unparse(item)[:60]))
    return found


@pytest.mark.unit
def test_spacers_are_inserted_with_insert_spacer_item():
    violations = []
    for path in PLUGIN_ROOT.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in path.relative_to(PLUGIN_ROOT).parts):
            continue
        source = path.read_text(encoding="utf-8")
        if ".insertItem(" not in source:
            continue
        violations += [f"{path.relative_to(PLUGIN_ROOT)}:{line} ({item})" for line, item in _offenses(ast.parse(source))]
    assert not violations, "spacer inserted with insertItem (use insertSpacerItem): " + ", ".join(violations)


@pytest.mark.unit
@pytest.mark.parametrize("source, count", [
    ("layout.insertItem(1, QSpacerItem(1, 2))", 1),
    ("layout.insertItem(1, QtWidgets.QSpacerItem(1, 2))", 1),
    ("s = QSpacerItem(1, 2)\nlayout.insertItem(1, s)\n", 1),
    ("self._spacer = QSpacerItem(1, 2)\nlayout.insertItem(0, self._spacer)\n", 1),
    ("layout.insertSpacerItem(1, QSpacerItem(1, 2))", 0),
    ("combo.insertItem(0, 'text')", 0),
    ("def f(name):\n    combo.insertItem(0, name)\n", 0),  # QComboBox.insertItem(int, str)
    ("lst.insertItem(0, QListWidgetItem('x'))", 0),  # QListWidget.insertItem transfers
])
def test_guard_rules(source, count):
    assert len(_offenses(ast.parse(source))) == count
