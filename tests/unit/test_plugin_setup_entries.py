# -*- coding: utf-8 -*-
"""
Vector > FilterMate > Set up FilterMate and How FilterMate works when they open the panel themselves and the
dialog of what is new is shown on the way (filter_mate.py, methods extracted with ast: the module cannot be
imported outside QGIS).

2026-11-16, review: the dialog has a button that starts the setup. Clicked while the entry of the menu was
opening the panel, the setup started twice (two introductions, a first card closed as stopped), or the tour was
written under the cards of the setup.
"""
import ast
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_PLUGIN = Path(__file__).resolve().parents[2] / "filter_mate.py"
_NAMES = ["_chat_of_agent", "setup_with_agent", "show_how_it_works"]


def _plugin(dialog_asks_setup):
    tree = ast.parse(_PLUGIN.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "FilterMate")
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in _NAMES]
    assert sorted(n.name for n in methods) == sorted(_NAMES)
    namespace = {"logger": MagicMock()}
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(_PLUGIN), "exec"), namespace)
    chat = types.SimpleNamespace(start_setup=MagicMock(return_value=True), show_tour=MagicMock(return_value=True))
    plugin = types.SimpleNamespace(iface=MagicMock(), pluginIsActive=False, app=None, tr=lambda message: message,
                                   _setup_asked=False, _from_menu=False, chat=chat, seen_from_menu=[])

    def run():
        """As FilterMate.run(): the panel made, the dialog shown; what it asked is started here unless an entry of
        the menu opened the panel."""
        plugin.pluginIsActive = True
        plugin.app = types.SimpleNamespace(dockwidget=types.SimpleNamespace(isVisible=lambda: True, _agent_chat=chat))
        plugin._setup_asked = dialog_asks_setup
        plugin.seen_from_menu.append(plugin._from_menu)
        if plugin._setup_asked and not plugin._from_menu:
            plugin.setup_with_agent()

    plugin.run = run
    for name in _NAMES:
        setattr(plugin, name, types.MethodType(namespace[name], plugin))
    return plugin


@pytest.mark.unit
def test_the_setup_asked_in_the_dialog_and_from_the_menu_starts_once():
    plugin = _plugin(dialog_asks_setup=True)
    plugin.setup_with_agent()
    assert plugin.seen_from_menu == [True] and plugin._from_menu is False
    plugin.chat.start_setup.assert_called_once_with()
    assert plugin._setup_asked is False


@pytest.mark.unit
def test_the_tour_gives_way_to_the_setup_asked_in_the_dialog():
    plugin = _plugin(dialog_asks_setup=True)
    plugin.show_how_it_works()
    plugin.chat.start_setup.assert_called_once_with()
    plugin.chat.show_tour.assert_not_called()
    assert plugin._setup_asked is False


@pytest.mark.unit
def test_the_tour_is_told_when_the_dialog_asked_nothing():
    plugin = _plugin(dialog_asks_setup=False)
    plugin.show_how_it_works()
    plugin.chat.show_tour.assert_called_once_with()
    plugin.chat.start_setup.assert_not_called()


@pytest.mark.unit
def test_a_panel_already_open_is_not_opened_again():
    plugin = _plugin(dialog_asks_setup=False)
    plugin.run()
    plugin.run = MagicMock()
    plugin.setup_with_agent()
    plugin.run.assert_not_called()
    plugin.chat.start_setup.assert_called_once_with()


@pytest.mark.unit
def test_the_section_turned_off_is_said_not_started():
    plugin = _plugin(dialog_asks_setup=False)
    plugin.run()
    plugin.app.dockwidget._agent_chat = None
    plugin.setup_with_agent()
    plugin.show_how_it_works()
    assert plugin.iface.messageBar().pushInfo.call_count == 2
    plugin.chat.start_setup.assert_not_called()
