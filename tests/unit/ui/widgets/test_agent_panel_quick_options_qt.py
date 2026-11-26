# -*- coding: utf-8 -*-
"""Sources, model and the MCP server in the menu "⋯" of the AGENT panel, on real Qt5/Qt6 widgets (offscreen): one
submenu per group of sources, a tick per source, the providers set up with the current one checked (2026-11-16).

Loaded under a private package with ``qgis.PyQt`` pointing at the installed binding for the import only (the root
conftest mocks Qt for the other tests), and ``qgis.core`` mocked. Skipped without Qt (run in a qgis/qgis image).
"""
import importlib
import os
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

try:
    from PyQt6 import QtCore, QtGui, QtTest, QtWidgets
except ImportError:
    QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
    from PyQt5 import QtCore, QtGui, QtTest

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_agent_panel_quick_options_test"


def _load():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    qt = {"qgis.PyQt": types.ModuleType("qgis.PyQt"), "qgis.PyQt.QtCore": QtCore, "qgis.PyQt.QtGui": QtGui,
          "qgis.PyQt.QtWidgets": QtWidgets, "qgis.PyQt.QtNetwork": MagicMock(), "qgis.PyQt.QtXml": MagicMock()}
    if "qgis.core" not in sys.modules:
        qt["qgis.core"] = MagicMock()
    saved = {name: sys.modules.get(name) for name in qt}
    sys.modules.update(qt)  # for the imports only: the modules loaded keep the real Qt classes
    try:
        for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.agent", _ROOT / "core" / "agent"),
                           (".adapters", _ROOT / "adapters"), (".adapters.agent", _ROOT / "adapters" / "agent"),
                           (".ui", _ROOT / "ui"), (".ui.widgets", _ROOT / "ui" / "widgets"),
                           (".ui.styles", _ROOT / "ui" / "styles")):
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]
            sys.modules[_PKG + name] = package
        return app, importlib.import_module(f"{_PKG}.ui.widgets.agent_panel")
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


_APP, panel_module = _load()


@pytest.fixture(autouse=True)
def real_qt_icons(monkeypatch):
    qt_svg = importlib.import_module(QtWidgets.__package__ + ".QtSvg")
    for name, module in (("QtCore", QtCore), ("QtGui", QtGui), ("QtWidgets", QtWidgets), ("QtSvg", qt_svg)):
        monkeypatch.setitem(sys.modules, "qgis.PyQt." + name, module)
    yield
    for widget in _APP.topLevelWidgets():
        if isinstance(widget, QtWidgets.QMenu):
            widget.hide()


GROUPS = [("Open data platforms", [("datagouv", "data.gouv.fr", True), ("ign_wfs", "IGN (WFS)", False)]),
          ("MCP connectors", [("osm_mcp", "OpenStreetMap (MCP)", False)])]
PROVIDERS = [("anthropic · claude-haiku-5-5", True, "anthropic\nclaude-haiku-5-5\n"),
             ("ollama · qwen3:8b", False, "ollama\nqwen3:8b\nhttp://localhost:11434")]


def _filled():
    panel = panel_module.AgentPanel()
    panel.fill_options(GROUPS, PROVIDERS, False)
    return panel


def _texts(menu):
    return [action.text() for action in menu.actions() if not action.isSeparator()]


def test_the_menu_lists_groups_and_ticks():
    panel = _filled()
    groups = [action.menu() for action in panel.sources_menu.actions() if action.menu() is not None]
    assert [menu.title() for menu in groups] == ["Open data platforms", "MCP connectors"]
    ticks = {action.text(): action.isChecked() for action in groups[0].actions()}
    assert ticks == {"data.gouv.fr": True, "IGN (WFS)": False}
    assert panel.mcp_action.isCheckable() and not panel.mcp_action.isChecked()


def test_a_tick_emits_the_source():
    panel = _filled()
    seen = []
    panel.source_toggled.connect(lambda source_id, on: seen.append((source_id, on)))
    group = next(action.menu() for action in panel.sources_menu.actions() if action.menu() is not None)
    next(action for action in group.actions() if action.text() == "IGN (WFS)").trigger()
    assert seen == [("ign_wfs", True)]


def test_the_current_provider_is_checked_and_another_is_chosen():
    panel = _filled()
    chosen = []
    panel.provider_chosen.connect(chosen.append)
    entries = [action for action in panel.models_menu.actions() if action.isCheckable()]
    assert [(action.text(), action.isChecked()) for action in entries] == [(label, on) for label, on, _ident in PROVIDERS]
    entries[1].trigger()
    assert chosen == [PROVIDERS[1][2]]  # the provider itself, not its rank in a list that may change


def test_a_provider_is_forgotten_by_what_the_action_carries():
    panel = _filled()
    forgotten = []
    panel.provider_forgotten.connect(forgotten.append)
    forget = next(action.menu() for action in panel.models_menu.actions() if action.menu() is not None)
    forget.actions()[0].trigger()
    assert forgotten == [PROVIDERS[1][2]]


def test_options_are_asked_when_the_menu_opens():
    panel = panel_module.AgentPanel()
    asked = []
    panel.options_requested.connect(lambda: asked.append(True))
    panel.more_button.menu().aboutToShow.emit()
    assert asked == [True]


def _open_group(panel):
    root = panel.more_button.menu()
    root.popup(QtCore.QPoint(20, 20))
    root.setActiveAction(panel.sources_menu.menuAction())
    panel.sources_menu.popup(root.mapToGlobal(root.actionGeometry(panel.sources_menu.menuAction()).topRight()))
    group = next(action.menu() for action in panel.sources_menu.actions() if action.menu() is not None)
    panel.sources_menu.setActiveAction(group.menuAction())
    group.popup(panel.sources_menu.mapToGlobal(panel.sources_menu.actionGeometry(group.menuAction()).topRight()))
    _APP.processEvents()
    return root, group


def _click(menu, action):
    QtTest.QTest.mouseClick(menu, QtCore.Qt.MouseButton.LeftButton, pos=menu.actionGeometry(action).center())
    _APP.processEvents()


def test_several_sources_can_be_checked_and_unchecked_without_closing_the_menu_chain():
    panel = _filled()
    seen = []
    panel.source_toggled.connect(lambda source_id, on: seen.append((source_id, on)))
    root, group = _open_group(panel)
    first, second = group.actions()
    _click(group, second)
    _click(group, first)
    _click(group, second)
    assert seen == [("ign_wfs", True), ("datagouv", False), ("ign_wfs", False)]
    assert not first.isChecked() and not second.isChecked()
    assert all(menu.isVisible() for menu in (root, panel.sources_menu, group))


@pytest.mark.parametrize("key", [QtCore.Qt.Key.Key_Space, QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter])
def test_source_toggles_stay_open_with_the_keyboard(key):
    panel = _filled()
    seen = []
    panel.source_toggled.connect(lambda source_id, on: seen.append((source_id, on)))
    root, group = _open_group(panel)
    group.setActiveAction(group.actions()[1])
    QtTest.QTest.keyClick(group, key)
    group.setActiveAction(group.actions()[0])
    QtTest.QTest.keyClick(group, key)
    assert seen == [("ign_wfs", True), ("datagouv", False)]
    assert root.isVisible() and group.isVisible()


def test_escape_closes_the_source_submenu():
    panel = _filled()
    _root, group = _open_group(panel)
    QtTest.QTest.keyClick(group, QtCore.Qt.Key.Key_Escape)
    assert not group.isVisible()


def test_clicking_outside_closes_the_menu_chain():
    panel = _filled()
    root, group = _open_group(panel)
    QtTest.QTest.mouseClick(group, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(-10, -10))
    assert not group.isVisible() and not root.isVisible()


def test_the_mcp_toggle_stays_open_but_opening_settings_closes_the_menu():
    panel = _filled()
    toggles, settings = [], []
    panel.mcp_toggled.connect(toggles.append)
    panel.settings_requested.connect(lambda: settings.append(True))
    root = panel.more_button.menu()
    root.popup(QtCore.QPoint(20, 20))
    _click(root, panel.mcp_action)
    _click(root, panel.mcp_action)
    assert root.isVisible() and toggles == [True, False]
    _click(root, panel.settings_action)
    assert not root.isVisible() and settings == [True]


def test_refreshing_live_recipes_preserves_the_open_menu_and_does_not_emit_another_toggle():
    panel = _filled()
    recipe = {"id": "r1", "name": "Roads & buildings", "steps": [{"label": "Filter"}], "live": False}
    panel.set_recipes([recipe], True)
    seen = []

    def refresh(ident, on):
        seen.append((ident, on))
        panel.set_recipes([dict(recipe, live=on)], True)

    panel.recipe_live_toggled.connect(refresh)
    entry = panel._recipe_menus[0]
    action = panel.recipe_live["r1"]
    entry.popup(QtCore.QPoint(20, 20))
    _click(entry, action)
    assert entry.isVisible() and panel._recipe_menus[0] is entry
    assert panel.recipe_live["r1"] is action and action.isChecked()
    assert entry.title() == "Roads && buildings (1 steps) · live"
    _click(entry, action)
    assert entry.isVisible() and not action.isChecked()
    assert seen == [("r1", True), ("r1", False)]
