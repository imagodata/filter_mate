# -*- coding: utf-8 -*-
"""Compare on the history page of the AGENT section, on real Qt widgets (PyQt5, offscreen): shown only when the dock
can compare, on for a request applied or one of its steps, and asking for it by its rank in the history of the agent.

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
_PKG = "fm_agent_panel_compare_test"


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

TURNS = [{"time": 100, "request": "first", "layers": ["roads"], "applied": True, "steps": ["old step"]},
         {"time": 200, "request": "second", "layers": ["roads"], "applied": True, "steps": ["filter", "again"]},
         {"time": 300, "request": "undone", "layers": ["dem"], "applied": False, "steps": []}]


def _panel(can_compare=True):
    panel = panel_module.AgentPanel()
    asked = []
    panel.compare_requested.connect(lambda turn, step: asked.append((turn, step)))
    panel.set_can_compare(can_compare)
    panel.set_history(TURNS, True, True)
    return panel, asked


def _rows(panel):
    """The rows of the history: request (or step label) -> item."""
    rows = {}
    for index in range(panel.history_list.count()):
        item = panel.history_list.item(index)
        step = item.data(QtCore.Qt.UserRole + 1)
        rows[item.data(QtCore.Qt.UserRole) if step is None else f"step {step}"] = item
    return rows


def test_compare_is_hidden_when_the_dock_cannot_compare():
    panel, _asked = _panel(can_compare=False)
    panel.history_list.setCurrentItem(_rows(panel)["second"])
    assert panel.compare_button.isHidden()


def test_compare_is_shown_but_off_without_a_selection():
    panel, _asked = _panel()
    panel.history_list.clearSelection()
    assert not panel.compare_button.isHidden() and not panel.compare_button.isEnabled()


def test_a_request_applied_is_asked_by_its_rank_whole():
    panel, asked = _panel()
    panel.history_list.setCurrentItem(_rows(panel)["first"])
    assert panel.compare_button.isEnabled()
    panel.compare_button.click()
    panel.history_list.setCurrentItem(_rows(panel)["second"])
    panel.compare_button.click()
    assert asked == [(0, -1), (1, -1)]


def test_a_step_is_asked_with_the_rank_of_its_request():
    panel, asked = _panel()
    rows = _rows(panel)
    assert "step 0" in rows and "step 1" in rows  # the steps of the last request applied only
    panel.history_list.setCurrentItem(rows["step 1"])
    assert panel.compare_button.isEnabled() and not panel.step_button.isHidden()
    panel.compare_button.click()
    assert asked == [(1, 1)]


def test_a_request_undone_cannot_be_compared():
    panel, asked = _panel()
    panel.history_list.setCurrentItem(_rows(panel)["undone"])
    assert not panel.compare_button.isEnabled()
    panel.compare_button.click()
    assert asked == []


def test_nothing_is_compared_while_the_agent_works():
    panel, asked = _panel()
    panel.history_list.setCurrentItem(_rows(panel)["second"])
    panel.set_working(True)
    assert not panel.compare_button.isEnabled()
    panel._compare_selected()  # a click that reached it all the same
    panel.set_working(False)
    assert asked == [] and panel.compare_button.isEnabled()
