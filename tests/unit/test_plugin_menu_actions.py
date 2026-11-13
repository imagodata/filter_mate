# -*- coding: utf-8 -*-
"""
The entries of Vector > FilterMate after a language change while QGIS runs (filter_mate.py, methods extracted
with ast: the module cannot be imported outside QGIS).

2026-11-13: retranslate_actions renamed the entries by their place in the list. "Set up FilterMate with the
agent" had been added between the panel and the reset: it took the name "Reset configuration and database",
still started the setup (a request to the provider), and the real reset kept the words of the old language.
"""
import ast
import os
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_PLUGIN = Path(__file__).resolve().parents[2] / "filter_mate.py"
_NAMES = ["add_action", "_add_menu_actions", "retranslate_actions"]


class _Action:
    """What the plugin does with a QAction: its text and its tip."""

    def __init__(self, icon, text, parent):
        self.text, self.tip, self.triggered = text, "", MagicMock()

    def setText(self, text):  # noqa: N802 - Qt name
        self.text = text

    def setStatusTip(self, tip):  # noqa: N802 - Qt name
        self.tip = tip

    def setEnabled(self, enabled):  # noqa: N802 - Qt name
        pass


def _plugin():
    tree = ast.parse(_PLUGIN.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "FilterMate")
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in _NAMES]
    assert sorted(n.name for n in methods) == sorted(_NAMES)
    namespace = {"logger": MagicMock(), "QIcon": MagicMock(), "QAction": _Action, "os": os}
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(_PLUGIN), "exec"), namespace)
    plugin = types.SimpleNamespace(iface=MagicMock(), toolbar=MagicMock(), actions=[], menu="&FilterMate",
                                   plugin_dir="/plugin", tr=lambda message: message)
    for name in ("run", "setup_with_agent", "reset_configuration"):
        setattr(plugin, name, MagicMock(name=name))
    for name in _NAMES:
        setattr(plugin, name, types.MethodType(namespace[name], plugin))
    return plugin


@pytest.mark.unit
def test_each_entry_keeps_its_own_words_after_a_language_change():
    plugin = _plugin()
    plugin._add_menu_actions()
    english = {action.text: action for action in plugin.actions}
    assert set(english) == {"FilterMate", "Set up FilterMate with the agent", "Reset configuration and database"}

    plugin.tr = lambda message: "FR:" + message  # the language changed while QGIS runs
    plugin.retranslate_actions()

    for text, action in english.items():
        assert action.text == "FR:" + text
        assert action.tip.startswith("FR:")
    assert len({action.text for action in plugin.actions}) == 3  # no two entries under one name


@pytest.mark.unit
def test_the_entries_of_an_extension_are_left_alone():
    """Extensions add their own actions to the list: they are not the entries of FilterMate, wherever they sit."""
    plugin = _plugin()
    extension = _Action(None, "QFieldCloud", None)
    plugin.actions.append(extension)
    plugin._add_menu_actions()
    plugin.tr = lambda message: "FR:" + message
    plugin.retranslate_actions()
    assert extension.text == "QFieldCloud"
    assert sorted(action.text for action in plugin.actions if action is not extension) == [
        "FR:FilterMate", "FR:Reset configuration and database", "FR:Set up FilterMate with the agent"]
