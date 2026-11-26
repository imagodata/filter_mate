# -*- coding: utf-8 -*-
"""The AGENT panel made easier to read (2026-11-24), on real Qt widgets (PyQt5, offscreen): the steps of a request
folded rather than taken away, the line to ask that says the mode, a link to a new conversation, the menu "⋯" in three
groups.

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

try:
    from PyQt6 import QtCore, QtGui, QtWidgets
except ImportError:
    QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
    from PyQt5 import QtCore, QtGui

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_agent_panel_ux_test"


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


def _ready_panel():
    panel = panel_module.AgentPanel()
    panel.set_ready(True, "Claude")
    return panel


def test_the_steps_fold_into_one_line_that_opens_them():
    panel = _ready_panel()
    panel.add_user("garde les communes")
    panel.add_step("Reading communes")
    panel.add_step("Filter on communes")
    panel.finish_steps(True)
    panel.clear_steps()
    thread = panel.thread
    toggle = thread.findChild(QtWidgets.QPushButton, "pushButton_agent_steps")
    assert toggle is not None and toggle.text().startswith("\u25b8") and "Steps: 2" in toggle.text()
    steps = [item.widget for item in thread._items if item.kind == "step_kept"]
    assert len(steps) == 2 and not any(widget.isVisibleTo(thread) for widget in steps)
    order = [item.kind for item in thread._items]
    assert order.index("steps") < order.index("step_kept")  # the line sits above the steps it folds
    toggle.click()
    assert all(widget.isVisibleTo(thread) for widget in steps) and toggle.text().startswith("\u25be")
    toggle.click()
    assert not any(widget.isVisibleTo(thread) for widget in steps)
    # A next request starts its own steps: the folded ones are not marked again, nor folded twice.
    panel.add_user("et les bâtiments")
    panel.add_step("Filter on batiments")
    panel.clear_steps()
    assert len(thread.findChildren(QtWidgets.QPushButton, "pushButton_agent_steps")) == 2
    panel.clear_thread()
    assert thread.is_empty()


def test_a_failed_step_is_said_on_the_folded_line():
    panel = _ready_panel()
    panel.add_step("Download")
    panel.finish_steps(False)
    panel.clear_steps()
    toggle = panel.thread.findChild(QtWidgets.QPushButton, "pushButton_agent_steps")
    assert "one failed" in toggle.text()


def test_no_step_no_line():
    panel = _ready_panel()
    panel.clear_steps()
    assert panel.thread.findChild(QtWidgets.QPushButton, "pushButton_agent_steps") is None


def test_the_line_to_ask_says_the_mode():
    panel = _ready_panel()
    panel.set_mode(panel_module.ACT)
    assert panel.input.placeholderText() == "Ask the agent…"
    panel.set_mode(panel_module.ASK)
    assert panel.input.placeholderText() == "Ask a question about the project…"
    panel.set_mode(panel_module.PLAN)
    assert panel.input.placeholderText() == "Describe what to plan…"
    panel.set_ready(False)
    assert panel.input.placeholderText() == "Connect a provider to start"


def test_act_draws_its_chip_in_the_accent():
    panel = _ready_panel()
    panel.set_mode(panel_module.ACT)
    assert "font-weight: 600" in panel.styleSheet()
    panel.set_mode(panel_module.ASK)
    assert "font-weight: 600; }QToolButton" not in panel.styleSheet()


def test_the_new_conversation_link_follows_the_thread():
    panel = _ready_panel()
    seen = []
    panel.new_conversation_requested.connect(lambda: seen.append(True))
    assert not panel.new_button.isVisibleTo(panel)
    panel.add_user("garde les communes")
    assert panel.new_button.isVisibleTo(panel) and panel.new_button.isEnabled()
    panel.set_working(True)
    assert not panel.new_button.isEnabled()
    panel.set_working(False)
    panel.new_button.click()
    assert seen == [True]
    panel.clear_thread()
    assert not panel.new_button.isVisibleTo(panel)


def test_the_menu_has_three_groups_new_conversation_first():
    panel = _ready_panel()
    menu = panel.more_button.menu()
    groups, current = [], []
    for action in menu.actions():
        if action.isSeparator():
            groups.append(current)
            current = []
        else:
            current.append(action.text())
    groups.append(current)
    assert [len(group) > 0 for group in groups] == [True, True, True]
    assert groups[0][0] == "New conversation"
    assert "Agent settings" in groups[1] and "Feedback" in groups[2]


def test_a_local_model_is_said_on_the_welcome():
    panel = panel_module.AgentPanel()
    panel.set_ready(True, "Ollama (local) · qwen3:8b", local=True)
    assert panel.welcome_local.isVisibleTo(panel) and "this computer" in panel.welcome_local.text()
    panel.set_ready(True, "Claude · haiku-5-5")
    assert not panel.welcome_local.isVisibleTo(panel)
    panel.set_ready(False, "", local=True)  # no provider set up: nothing to say yet
    assert not panel.welcome_local.isVisibleTo(panel)
