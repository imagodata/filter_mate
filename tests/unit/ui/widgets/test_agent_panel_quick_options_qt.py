# -*- coding: utf-8 -*-
"""Sources, model and the MCP server in the menu "⋯" of the AGENT panel, on real Qt widgets (PyQt5, offscreen): one
submenu per group of sources, a tick per source, the providers set up with the current one checked (2026-11-16).

Loaded under a private package with ``qgis.PyQt`` pointing at PyQt5 for the import only (the root conftest mocks Qt
for the other tests), and ``qgis.core`` mocked. Skipped without PyQt5 (run it in a qgis/qgis image).
"""
import importlib
import os
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
from PyQt5 import QtCore, QtGui  # noqa: E402

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


GROUPS = [("Open data platforms", [("datagouv", "data.gouv.fr", True), ("ign_wfs", "IGN (WFS)", False)]),
          ("MCP connectors", [("osm_mcp", "OpenStreetMap (MCP)", False)])]
PROVIDERS = [("anthropic · claude-haiku-5-5", True), ("ollama · qwen3:8b", False)]


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
    assert [(action.text(), action.isChecked()) for action in entries] == PROVIDERS
    entries[1].trigger()
    assert chosen == [1]


def test_options_are_asked_when_the_menu_opens():
    panel = panel_module.AgentPanel()
    asked = []
    panel.options_requested.connect(lambda: asked.append(True))
    panel.more_button.menu().aboutToShow.emit()
    assert asked == [True]
