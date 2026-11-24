# -*- coding: utf-8 -*-
"""The history of the AGENT panel in two tabs (2026-11-24), on real Qt widgets (PyQt5, offscreen): the turns of the
open project with their buttons, the requests of every project with Send again and Empty the list.
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
_PKG = "fm_agent_panel_history_tabs_test"


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


TURNS = [{"time": 1, "request": "garde les communes", "layers": ["communes"], "applied": True, "steps": []}]
ENTRIES = [
    {"time": 1_700_000_000, "request": "les routes de Sarlat", "project": "Sarlat", "path": "/p/sarlat.qgz",
     "layers": ["routes"], "outcome": "changed"},
    {"time": 1_700_000_100, "request": "quelles couches ?", "project": "Toulouse", "path": "/p/toulouse.qgz",
     "layers": [], "outcome": "unchanged"},
]


def _panel():
    panel = panel_module.AgentPanel()
    panel.set_ready(True, "Claude")
    panel.set_can_compare(True)
    panel.set_history(TURNS, True, False)
    panel.set_global_history(ENTRIES, "/p/toulouse.qgz")
    panel.show_history()
    panel.show()
    return panel


def test_two_tabs_this_project_first():
    panel = _panel()
    assert [panel.history_tabs.tabText(i) for i in range(panel.history_tabs.count())] == ["This project", "All projects"]
    assert panel.history_tabs.currentIndex() == panel_module.HISTORY_PROJECT
    assert panel.history_pages.currentWidget() is panel.history_list and panel.history_list.count() == 1
    assert panel.history_count.text() == "this project · 1 turn(s)"
    assert panel.history_undo_button.isVisibleTo(panel) and not panel.clear_global_button.isVisibleTo(panel)


def test_all_projects_lists_every_request_and_its_project():
    panel = _panel()
    panel.history_tabs.setCurrentIndex(panel_module.HISTORY_ALL)
    assert panel.history_pages.currentWidget() is panel.global_list and panel.global_list.count() == 2
    assert panel.history_count.text() == "all projects · 2 request(s)"
    texts = [" ".join(label.text() for label in panel.global_list.itemWidget(panel.global_list.item(i)).findChildren(
        QtWidgets.QLabel)) for i in range(2)]
    assert "Sarlat · routes" in texts[0] and "this project · no change" in texts[1]
    # Undo, Redo and Compare act on the open project only: not in this tab.
    assert not panel.history_undo_button.isVisibleTo(panel) and not panel.history_redo_button.isVisibleTo(panel)
    assert not panel.compare_button.isVisibleTo(panel)
    assert panel.clear_global_button.isVisibleTo(panel) and panel.clear_global_button.isEnabled()


def test_send_again_from_all_projects():
    panel = _panel()
    sent = []
    panel.resend_requested.connect(sent.append)
    panel.history_tabs.setCurrentIndex(panel_module.HISTORY_ALL)
    assert not panel.resend_button.isEnabled()
    panel.global_list.setCurrentRow(0)
    assert panel.resend_button.isEnabled()
    panel.resend_button.click()
    assert sent == ["les routes de Sarlat"]


def test_empty_the_list_asks_the_controller():
    panel = _panel()
    asked = []
    panel.history_clear_requested.connect(lambda: asked.append(True))
    panel.history_tabs.setCurrentIndex(panel_module.HISTORY_ALL)
    panel.clear_global_button.click()
    assert asked == [True]
    panel.set_global_history([], "")
    assert panel.global_list.count() == 0 and not panel.clear_global_button.isEnabled()
    assert panel.history_count.text() == "all projects · 0 request(s)"


def test_back_to_this_project_brings_its_buttons_back():
    panel = _panel()
    panel.history_tabs.setCurrentIndex(panel_module.HISTORY_ALL)
    panel.history_tabs.setCurrentIndex(panel_module.HISTORY_PROJECT)
    assert panel.history_undo_button.isVisibleTo(panel) and panel.compare_button.isVisibleTo(panel)
    assert panel.history_count.text() == "this project · 1 turn(s)"
