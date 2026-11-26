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


@pytest.fixture(autouse=True)
def real_qt_icons(monkeypatch):
    """The icon renderer imports Qt lazily; use real Qt for each test, including QtSvg."""
    qt_svg = importlib.import_module(QtWidgets.__package__ + ".QtSvg")
    for name, module in (("QtCore", QtCore), ("QtGui", QtGui), ("QtWidgets", QtWidgets), ("QtSvg", qt_svg)):
        monkeypatch.setitem(sys.modules, "qgis.PyQt." + name, module)


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


def test_new_conversation_stays_in_place_and_follows_the_thread():
    panel = _ready_panel()
    seen = []
    panel.new_conversation_requested.connect(lambda: seen.append(True))
    assert panel.new_button.isVisibleTo(panel) and not panel.new_button.isEnabled()
    panel.add_user("garde les communes")
    assert panel.new_button.isVisibleTo(panel) and panel.new_button.isEnabled()
    panel.set_working(True)
    assert not panel.new_button.isEnabled()
    panel.set_working(False)
    panel.new_button.click()
    assert seen == [True]
    panel.clear_thread()
    assert panel.new_button.isVisibleTo(panel) and not panel.new_button.isEnabled()


def test_navigation_is_icon_only_with_tooltips_and_accessible_names():
    panel = _ready_panel()
    for button, title in ((panel.history_button, "History"), (panel.recipes_button, "Recipes"),
                          (panel.new_button, "New conversation")):
        assert button.text() == "" and not button.icon().isNull()
        assert button.toolTip().splitlines()[0] == title
        assert button.accessibleName()
        assert button.size().width() >= 30 and button.size().height() >= 30
    assert panel.mode_button.text()  # the posture stays explicit beside the icon actions


def test_history_state_follows_the_page_and_back_button():
    panel = _ready_panel()
    panel.history_requested.connect(panel.show_history)
    panel.history_button.click()
    assert panel.history_shown and panel.history_button.isChecked()
    panel.back_button.click()
    assert not panel.history_shown and not panel.history_button.isChecked()


def test_navigation_and_menu_icons_refresh_together_when_the_theme_changes():
    panel = _ready_panel()
    panel._dark = lambda: False
    panel._refresh_look()
    light = panel.history_button.icon().cacheKey()
    assert light == panel.history_action.icon().cacheKey()
    panel._dark = lambda: True
    panel._refresh_look()
    assert panel.history_button.icon().cacheKey() != light
    assert panel.history_button.icon().cacheKey() == panel.history_action.icon().cacheKey()
    assert panel.recipes_button.icon().cacheKey() == panel.recipes_menu.icon().cacheKey()
    assert panel.new_button.icon().cacheKey() == panel.new_action.icon().cacheKey()


def test_recipe_menu_keeps_its_labels_and_actions_with_icons():
    panel = _ready_panel()
    panel.set_recipes([{"id": "r1", "name": "Filter communes", "steps": [{"label": "Filter"}]}], True)
    run, remove = panel.recipe_actions["r1"]
    assert not run.icon().isNull() and not remove.icon().isNull()
    assert run.text() == "Run without the model"
    assert not panel.save_recipe_action.icon().isNull()
    seen = []
    panel.recipe_run_requested.connect(seen.append)
    run.trigger()
    assert seen == ["r1"]


def test_toolbar_fits_a_narrow_panel():
    panel = _ready_panel()
    panel.add_user("Filter the buildings")
    panel.resize(280, 480)
    panel.show()
    _APP.processEvents()
    assert panel.width() == 280
    for button in (panel.history_button, panel.recipes_button, panel.new_button, panel.mode_button):
        assert panel.rect().contains(button.geometry())
    panel.close()


def test_long_model_name_is_elided_but_stays_available_in_the_tooltip():
    panel = _ready_panel()
    model = "Claude · a very long model name that cannot fit beside the navigation"
    panel.set_ready(True, model)
    panel.resize(280, 480)
    panel.show()
    _APP.processEvents()
    assert panel.destination.text().endswith("…")
    assert model in panel.destination.toolTip()
    assert model in panel.destination.accessibleName()
    panel.close()


def test_effort_is_hidden_without_support_and_offers_only_supported_levels():
    panel = _ready_panel()
    assert not panel.effort_button.isVisibleTo(panel)
    seen = []
    panel.effort_changed.connect(seen.append)
    panel.set_effort_options(('low', 'medium', 'high'), 'medium')
    assert panel.effort_button.isVisibleTo(panel)
    assert not panel.effort_button.icon().isNull()
    assert list(panel._effort_actions) == ['', 'low', 'medium', 'high']
    assert panel._effort_action_group.isExclusive()
    assert panel._effort_actions['medium'].isChecked()
    assert 'Medium' in panel.effort_button.toolTip()
    assert seen == []  # displaying the control never sets a level
    panel._effort_actions['high'].trigger()
    assert seen == ['high'] and panel._effort_actions['high'].isChecked()
    assert sum(action.isChecked() for action in panel._effort_actions.values()) == 1
    panel._effort_actions[''].trigger()
    assert seen == ['high', '']
    panel.set_effort_options((), 'high')
    assert not panel.effort_button.isVisibleTo(panel) and panel._effort == ''


def test_effort_cannot_change_during_a_running_request():
    panel = _ready_panel()
    panel.set_effort_options(('low', 'medium', 'high'), 'low')
    seen = []
    panel.effort_changed.connect(seen.append)
    panel.set_working(True)
    assert not panel.effort_button.isEnabled()
    panel._effort_actions['high'].trigger()
    assert seen == [] and panel._effort == 'low'
    assert panel._effort_actions['low'].isChecked() and not panel._effort_actions['high'].isChecked()
    panel.set_working(False)
    assert panel.effort_button.isEnabled()


def test_effort_control_keeps_a_narrow_panel_usable():
    panel = _ready_panel()
    panel.set_effort_options(('low', 'medium', 'high'), 'high')
    panel.resize(280, 480)
    panel.show()
    _APP.processEvents()
    assert panel.width() == 280
    assert panel.effort_button.text() == '' and panel.effort_button.accessibleName()
    for button in (panel.mode_button, panel.effort_button, panel.history_button,
                   panel.recipes_button, panel.new_button):
        assert panel.rect().contains(button.geometry())
    panel.close()


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
