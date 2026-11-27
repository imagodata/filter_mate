# -*- coding: utf-8 -*-
"""The AGENT panel made easier to read (2026-11-24), on real Qt widgets (PyQt5, offscreen): the steps of a request
folded rather than taken away, the line to ask that says the mode, a link to a new conversation, the icon menu in three
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
    from PyQt6 import QtCore, QtGui, QtTest, QtWidgets
except ImportError:
    QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
    from PyQt5 import QtCore, QtGui, QtTest

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


@pytest.mark.parametrize('dark', [False, True])
def test_designer_shortcuts_preserve_draft_and_posture_without_sending(dark):
    panel = _ready_panel()
    panel._dark = lambda: dark
    panel._refresh_look()
    panel.resize(280, 560)
    panel.show()
    events, sent = [], []
    panel.designer_mode_changed.connect(events.append)
    panel.send_requested.connect(sent.append)
    posture = panel._posture
    assert not panel.designer_mode and not panel.designer_frame.isVisible()
    panel.designer_action.trigger()
    _APP.processEvents()
    assert events == [True] and panel.designer_frame.isVisible()
    assert panel.width() == 280
    for kind, button in panel.designer_buttons.items():
        panel.input.setText('My existing draft')
        button.click()
        text = panel.input.text()
        assert text.startswith('My existing draft\n\n') and len(text) > len('My existing draft\n\n')
        button.click()
        assert panel.input.text() == text and button.accessibleName()
    assert not sent and panel._posture == posture
    panel.set_working(True)
    assert not panel.designer_action.isEnabled()
    panel.set_working(False)
    before = panel.input.text()
    panel.set_designer_mode(False)
    assert not panel.designer_frame.isVisible() and panel.input.text() == before
    assert events == [True]  # rendering a persisted preference does not emit another user choice
    panel.close()


def test_network_icon_follows_drafts_voice_and_paused_queue_without_hiding_after_work():
    panel = _ready_panel()
    panel.show()
    _APP.processEvents()
    icon = panel.activity_icon
    assert icon.isVisible() and icon.display_phase == 'idle' and not icon._renderer.animated()
    panel.input.setText('my request')
    assert icon.display_phase == 'drafting' and not icon._renderer.animated()
    panel.set_working(True)
    panel.set_activity_phase('exporting')
    panel.input.setText('a correction while exporting')
    assert icon.display_phase == 'exporting'
    panel.queue_message('next request', 'respond')
    panel.pause_queued()
    panel.input.clear()
    panel.set_working(False)
    assert icon.display_phase == 'queued' and icon.isVisible() and not icon._renderer.animated()
    panel.cancel_queued()
    assert icon.display_phase == 'drafting'
    panel.input.clear()
    panel.set_speech_state('recording')
    assert icon.display_phase == 'listening' and icon._renderer.animated()
    panel.set_speech_state('transcribing')
    assert icon.display_phase == 'transcribing' and icon._renderer.animated()
    panel.set_speech_state('idle')
    assert icon.display_phase == 'complete' and not icon._renderer.animated()
    panel.close()


@pytest.mark.parametrize('paused', [False, True])
def test_native_interface_handoff_holds_automatic_followups_until_the_dialog_closes(paused):
    panel = _ready_panel()
    sent = []
    panel.queued_send_requested.connect(lambda text, posture: sent.append((text, posture)))
    panel.set_working(True)
    panel.queue_message('next request', 'respond')
    if paused:
        panel.pause_queued()
    with panel.hold_queued():
        panel.set_working(False)
        _APP.processEvents()
        with panel.hold_queued():
            panel._send_queued()
            assert not sent
        _APP.processEvents()
        assert not sent and panel.queued == 'next request'
    _APP.processEvents()
    assert sent == ([] if paused else [('next request', 'respond')])


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


def test_push_mode_sends_to_the_active_request_without_touching_the_queue():
    panel = _ready_panel()
    panel.set_followup_mode("queue")
    pushed = []
    panel.push_requested.connect(pushed.append)
    panel.set_working(True)
    assert panel.followup_button.isEnabled()
    panel.input.setText("waiting")
    panel._on_send()
    panel.set_followup_mode("push")
    panel.input.setText("correction")
    panel.send_button.click()
    assert pushed == ["correction"] and panel.queued == "waiting"
    assert panel.input.text() == "correction"  # a rejected send must leave the draft intact
    panel.set_working(False)
    assert panel.followup_button.isEnabled()


def test_push_is_the_default_and_the_user_can_keep_queue_as_the_default(monkeypatch):
    settings = {}
    monkeypatch.setattr(panel_module, "QSettings", lambda: types.SimpleNamespace(
        value=lambda key, default="": settings.get(key, default), setValue=settings.__setitem__))
    panel = _ready_panel()
    assert panel._followup_mode == "push" and panel._followup_actions["push"].isChecked()
    panel._followup_actions["queue"].trigger()
    assert panel._followup_mode == "queue" and panel._followup_actions["queue"].isChecked()
    assert not panel._followup_actions["push"].isChecked()
    restored = _ready_panel()
    assert restored._followup_mode == "queue"


def test_ctrl_shift_enter_inverts_the_followup_mode():
    panel = _ready_panel()
    pushed = []
    panel.push_requested.connect(pushed.append)
    qt_test = importlib.import_module(QtWidgets.__package__ + ".QtTest")
    qt = QtCore.Qt
    modifiers = qt.KeyboardModifier.ControlModifier | qt.KeyboardModifier.ShiftModifier
    panel.set_followup_mode("push")
    panel.set_working(True)
    panel.input.setText("wait until later")
    qt_test.QTest.keyClick(panel.input, qt.Key.Key_Return, modifiers)
    assert not pushed and panel.queued == "wait until later" and panel.input.text() == ""
    panel.set_followup_mode("queue")
    panel.input.setText("correct the active request")
    qt_test.QTest.keyClick(panel.input, qt.Key.Key_Return, modifiers)
    assert pushed == ["correct the active request"] and panel.queued == "wait until later"


def test_enter_and_send_button_push_with_a_draft_and_stop_without_one():
    panel = _ready_panel()
    pushed, stopped = [], []
    panel.push_requested.connect(pushed.append)
    panel.stop_requested.connect(lambda: stopped.append(True))
    qt_test = importlib.import_module(QtWidgets.__package__ + ".QtTest")
    panel.set_followup_mode("push")
    panel.set_working(True)
    assert panel._send_stops
    panel.input.setText("correction")
    assert not panel._send_stops and panel.send_button.toolTip() == "Send to the running agent (Enter)"
    qt_test.QTest.keyClick(panel.input, QtCore.Qt.Key.Key_Return)
    panel.send_button.click()
    assert pushed == ["correction", "correction"] and not stopped and not panel.queued
    panel.input.clear()
    panel.send_button.click()
    assert stopped == [True] and panel._send_stops


def test_send_now_promotes_a_queued_message_without_changing_the_draft():
    panel = _ready_panel()
    promoted = []
    panel.queued_push_requested.connect(lambda text, posture: promoted.append((text, posture)))
    panel.set_followup_mode("queue")
    panel.set_working(True)
    panel.input.setText("first")
    panel._on_send()
    panel.input.setText("second")
    panel._on_send()
    panel.input.setText("unfinished draft")
    panel.queue_push.click()
    assert promoted == [("first", "act")] and panel.queued == "second"
    assert panel.input.text() == "unfinished draft"


def test_ctrl_enter_pushes_while_enter_queues_and_shift_enter_adds_a_line():
    panel = _ready_panel()
    panel.set_followup_mode("queue")
    pushed, sent = [], []
    panel.push_requested.connect(pushed.append)
    panel.send_requested.connect(sent.append)
    qt_test = importlib.import_module(QtWidgets.__package__ + ".QtTest")
    qt = QtCore.Qt
    panel.set_working(True)
    panel.input.setText("correction")
    qt_test.QTest.keyClick(panel.input, qt.Key.Key_Return, qt.KeyboardModifier.ControlModifier)
    assert pushed == ["correction"] and not panel.queued and not sent
    qt_test.QTest.keyClick(panel.input, qt.Key.Key_Return)
    assert panel.queued == "correction" and panel.input.text() == ""
    qt_test.QTest.keyClick(panel.input, qt.Key.Key_Return, qt.KeyboardModifier.ShiftModifier)
    assert panel.input.text() == "\n" and pushed == ["correction"]
    panel.pause_queued()
    panel.set_working(False)
    panel.input.setText("new request")
    qt_test.QTest.keyClick(panel.input, qt.Key.Key_Return, qt.KeyboardModifier.ControlModifier)
    assert sent == ["new request"]


def test_push_respects_dictation_review():
    panel = _ready_panel()
    pushed = []
    panel.push_requested.connect(pushed.append)
    panel.set_working(True)
    panel.set_speech_state("transcribing")
    panel.input.setText("unreviewed")
    panel.send_button.click()
    assert not pushed and panel.input.text() == "unreviewed"
    panel.set_speech_state("idle")
    panel._on_push()
    assert pushed == ["unreviewed"]


def test_push_fits_a_narrow_panel_while_working():
    panel = _ready_panel()
    panel.set_working(True)
    panel.resize(280, 480)
    panel.show()
    _APP.processEvents()
    assert panel.width() == 280
    for widget in (panel.input, panel.followup_button, panel.send_button, panel.activity_icon):
        assert panel.rect().contains(widget.geometry())
    panel.close()


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
    menu = panel.activity_icon.menu()
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


@pytest.mark.parametrize('keyboard', [False, True])
def test_network_icon_opens_the_actions_menu_with_mouse_or_keyboard(keyboard):
    panel = _ready_panel()
    panel.show()
    _APP.processEvents()
    icon = panel.activity_icon
    menu = icon.menu()
    opened = []
    panel.options_requested.connect(lambda: opened.append(True))
    assert panel.findChild(QtWidgets.QToolButton, 'toolButton_agent_more') is None
    assert icon.accessibleName() == 'More actions'
    icon.setFocus()
    QtCore.QTimer.singleShot(50, menu.close)
    if keyboard:
        QtTest.QTest.keyClick(icon, QtCore.Qt.Key.Key_Space)
    else:
        QtTest.QTest.mouseClick(icon, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(16, 16))
    assert opened == [True]
    panel.set_working(True)
    assert not icon.isEnabled() and icon._renderer.animated()
    panel.close()


def test_dictation_offers_an_explicit_stop_then_a_cancellable_transcription_without_sending():
    panel = _ready_panel()
    panel.resize(280, 560)
    panel.show()
    panel.input.setText('Keep this draft')
    stopped, cancelled, sent = [], [], []
    panel.microphone_requested.connect(lambda: stopped.append(True))
    panel.microphone_cancel_requested.connect(lambda: cancelled.append(True))
    panel.send_requested.connect(sent.append)
    panel.set_speech_state('recording', 'Requesting microphone access…', can_transcribe=False)
    assert not panel.speech_finish.isEnabled() and not panel.microphone_button.isEnabled()
    panel.speech_finish.click()
    assert not stopped
    panel.set_speech_state('recording', 'Recording… 0:02 / 5:00 · Local service')
    _APP.processEvents()
    assert panel.speech_finish.isVisible() and panel.speech_finish.isEnabled()
    assert panel.speech_finish.accessibleName() == 'Stop recording and transcribe'
    assert not panel.speech_progress.isVisible() and not panel.send_button.isEnabled()
    assert panel.width() == 280 and panel.rect().contains(panel.speech_row.geometry())
    panel.speech_finish.click()
    assert stopped == [True]
    panel.set_speech_state('transcribing', 'Transcribing…')
    _APP.processEvents()
    assert not panel.speech_finish.isVisible() and panel.speech_progress.isVisible()
    assert panel.speech_label.text().startswith('Transcribing')
    assert panel.speech_cancel.text() == 'Cancel' and panel.speech_cancel.toolTip() == 'Cancel transcription'
    panel._on_send()
    assert not sent and panel.input.text() == 'Keep this draft'
    panel.speech_cancel.click()
    assert cancelled == [True]
    panel.set_speech_state('idle')
    assert not panel.speech_row.isVisible() and panel.send_button.isEnabled()
    assert panel.input.text() == 'Keep this draft'
    panel.close()


def test_a_local_model_is_said_on_the_welcome():
    panel = panel_module.AgentPanel()
    panel.set_ready(True, "Ollama (local) · qwen3:8b", local=True)
    assert panel.welcome_local.isVisibleTo(panel) and "this computer" in panel.welcome_local.text()
    panel.set_ready(True, "Claude · haiku-5-5")
    assert not panel.welcome_local.isVisibleTo(panel)
    panel.set_ready(False, "", local=True)  # no provider set up: nothing to say yet
    assert not panel.welcome_local.isVisibleTo(panel)
