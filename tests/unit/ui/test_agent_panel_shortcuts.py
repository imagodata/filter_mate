# -*- coding: utf-8 -*-
"""Ctrl+Z and Ctrl+Y typed in the QGIS panel of AGENT walk the steps of the agent (2026-11-18 audit).

``agent_has_focus`` is false as soon as AGENT leaves the dock (Undo and Redo of the action bar keep to the filters),
and the shortcuts of a panel (``keyboard_shortcuts_for``) ran the filters' Undo whatever panel had the focus.
"""
import ast
import pathlib
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_NAMES = ("_agent_panel_has_focus", "_on_undo_shortcut", "_on_redo_shortcut")


def _methods(focus):
    tree = ast.parse((_ROOT / "filter_mate_dockwidget.py").read_text(encoding="utf-8"))
    owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterMateDockWidget")
    wanted = [node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name in _NAMES]
    assert {node.name for node in wanted} == set(_NAMES)
    application = types.SimpleNamespace(focusWidget=lambda: focus)
    namespace = {"QtWidgets": types.SimpleNamespace(QApplication=application)}
    exec(compile(ast.fix_missing_locations(ast.Module(body=wanted, type_ignores=[])), "filter_mate_dockwidget.py",
                 "exec"), namespace)
    return namespace


class _Panel:
    def __init__(self, members, inside=()):
        self.members, self._inside = list(members), list(inside)

    def isAncestorOf(self, widget):  # noqa: N802 - Qt name
        return widget in self._inside


def _dock(focus, panel, chat=True):
    undo, redo = MagicMock(), MagicMock()
    undo.isEnabled.return_value = redo.isEnabled.return_value = True
    namespace = _methods(focus)
    dock = types.SimpleNamespace(
        _agent_chat=MagicMock() if chat else None, _fm_panels=types.SimpleNamespace(panel=lambda key: panel),
        widgets={"ACTION": {"UNDO_FILTER": {"WIDGET": undo}, "REDO_FILTER": {"WIDGET": redo}}},
        launchTaskEvent=MagicMock())
    for name in _NAMES:
        setattr(dock, name, types.MethodType(namespace[name], dock))
    return dock


def test_the_shortcuts_typed_in_the_panel_of_agent_walk_the_steps_of_the_agent():
    field = object()
    dock = _dock(field, _Panel(["agent"], [field]))
    dock._on_undo_shortcut()
    dock._on_redo_shortcut()
    dock._agent_chat._on_undo.assert_called_once_with()
    dock._agent_chat._on_redo.assert_called_once_with()
    dock.launchTaskEvent.assert_not_called()


def test_typed_anywhere_else_they_walk_the_filters():
    dock = _dock(object(), _Panel(["agent"], []))  # the focus is in the dock, or another panel
    dock._on_undo_shortcut()
    dock._on_redo_shortcut()
    assert [call.args for call in dock.launchTaskEvent.call_args_list] == [(False, "undo"), (False, "redo")]
    dock._agent_chat._on_undo.assert_not_called()


def test_with_agent_in_the_dock_there_is_no_panel_of_its_own_to_look_at():
    dock = _dock(object(), None)
    dock._on_undo_shortcut()
    dock.launchTaskEvent.assert_called_once_with(False, "undo")


def test_filtering_in_the_same_panel_keeps_the_filters():
    field = object()
    dock = _dock(field, _Panel(["agent", "filtering"], [field]))
    dock._on_undo_shortcut()
    dock.launchTaskEvent.assert_called_once_with(False, "undo")
    dock._agent_chat._on_undo.assert_not_called()


def test_without_the_agent_nothing_goes_to_it():
    field = object()
    dock = _dock(field, _Panel(["agent"], [field]), chat=False)
    dock._on_undo_shortcut()
    dock.launchTaskEvent.assert_called_once_with(False, "undo")


def test_no_focus_is_not_the_panel_of_agent():
    dock = _dock(None, _Panel(["agent"], []))
    dock._on_undo_shortcut()
    dock.launchTaskEvent.assert_called_once_with(False, "undo")
