# -*- coding: utf-8 -*-
"""The focus rule of the wheel guard. The event flow runs in the dock smoke test (real widgets)."""
import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_SOURCE = Path(__file__).resolve().parents[4] / "ui" / "widgets" / "wheel_guard.py"


def _has_focus_within():
    tree = ast.parse(_SOURCE.read_text(encoding="utf-8"))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "has_focus_within")
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(_SOURCE), "exec"), namespace)
    return namespace["has_focus_within"]


class _Widget:
    def __init__(self, *children):
        self.children = children

    def isAncestorOf(self, other):
        return other in self.children


def test_no_focus_anywhere_blocks_the_wheel():
    assert _has_focus_within()(_Widget(), None) is False


def test_focus_on_another_widget_blocks_the_wheel():
    assert _has_focus_within()(_Widget(), _Widget()) is False


def test_focus_on_the_widget_lets_the_wheel_through():
    widget = _Widget()
    assert _has_focus_within()(widget, widget) is True


def test_focus_on_its_line_edit_lets_the_wheel_through():
    line_edit = _Widget()
    assert _has_focus_within()(_Widget(line_edit), line_edit) is True
