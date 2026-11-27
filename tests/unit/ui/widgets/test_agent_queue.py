# -*- coding: utf-8 -*-
"""The waiting requests never eat what was typed (audit of 2026-11-24, lot 4, pile in S5).

- A draft typed while requests wait stays behind them when the first one goes (it was overwritten, and after
  a provider error the returned request too);
- a second Enter while one waits stacks behind it in sight, numbered (they were joined into one request);
- the first one goes alone when the request under way ends, the rest keeps waiting in order.

The methods are read off ``AgentPanel`` by AST and run on a stub (no Qt).
"""
import ast
from pathlib import Path
from types import MethodType, SimpleNamespace

import pytest

pytestmark = pytest.mark.unit

PATH = Path(__file__).resolve().parents[4] / 'ui' / 'widgets' / 'agent_panel.py'


def _method(name):
    tree = ast.parse(PATH.read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'AgentPanel')
    node = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)
    namespace = {'__name__': 'filter_mate.ui.widgets.agent_panel', '__package__': 'filter_mate.ui.widgets',
                 '_tr': lambda text: text, 'plain_tooltip': lambda text: text}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(PATH), 'exec'), namespace)
    return namespace[name]


class Line:
    """The line to ask: ``text()`` reads, as on the real widget."""

    def __init__(self):
        self._text = ""

    def text(self):
        return self._text

    def setText(self, text):
        self._text = text

    def clear(self):
        self._text = ""


class Panel:
    """What ``_on_send`` / ``_send_queued`` touch: the line, the working flag, the pile waiting."""

    def __init__(self):
        self.sent = []
        self.pushed = []
        self.input = Line()
        self._working = False
        self._followup_mode = "queue"
        self._speech_state = 'idle'
        self._queue = []
        self._queue_paused = False
        self._posture = "act"
        self.queue_label = SimpleNamespace(full="", set_full_text=lambda text: setattr(self.queue_label, "full", text),
                                           setToolTip=lambda text: None)
        self.queue_row = SimpleNamespace(visible=False, setVisible=lambda visible: setattr(
            self.queue_row, "visible", visible))
        self.queue_cancel = SimpleNamespace(setToolTip=lambda text: None)
        self.send_requested = SimpleNamespace(emit=self.sent.append)
        self.push_requested = SimpleNamespace(emit=self.pushed.append)
        self.queued_send_requested = SimpleNamespace(emit=lambda text, posture: self.sent.append((text, posture)))
        self.queued_push_requested = SimpleNamespace(emit=lambda text, posture: self.pushed.append((text, posture)))
        for name in ("_on_send", "_on_push", "_send_queued", "_push_queued", "_refresh_queue_row", "pause_queued", "cancel_queued",
                     "restore_queued"):
            setattr(self, name, MethodType(_method(name), self))


@pytest.fixture
def panel():
    return Panel()


def send(panel, text):
    panel.input.setText(text)
    panel._on_send()


def test_first_enter_queues(panel):
    panel._working = True
    send(panel, "first")
    assert panel._queue == [("first", "act")] and panel.input.text() == "" and panel.queue_row.visible


def test_second_enter_stacks_behind_in_sight(panel):
    panel._working = True
    send(panel, "first")
    send(panel, "second")
    assert panel._queue == [("first", "act"), ("second", "act")]
    assert "first" in panel.queue_label.full and "second" in panel.queue_label.full
    assert "2" in panel.queue_label.full


def test_each_one_goes_alone_in_order(panel):
    panel._working = True
    send(panel, "first")
    send(panel, "second")
    panel._working = False
    panel._send_queued()
    assert panel.sent == [("first", "act")] and panel._queue == [("second", "act")] and panel.queue_row.visible


def test_draft_typed_meanwhile_waits_behind(panel):
    panel._working = True
    send(panel, "waiting")
    panel._working = False
    panel.input.setText("draft")
    panel._send_queued()
    assert panel.sent == [("waiting", "act")]
    assert panel._queue == [] and not panel.queue_row.visible
    assert panel.input.text() == "draft"
    panel._send_queued()
    assert panel.sent == [("waiting", "act")]


def test_nothing_typed_nothing_queued_behind(panel):
    panel._working = True
    send(panel, "waiting")
    panel._working = False
    panel._send_queued()
    assert panel.sent == [("waiting", "act")] and panel._queue == [] and not panel.queue_row.visible


def test_stopped_queue_does_not_go_by_itself(panel):
    panel._working = True
    send(panel, "waiting")
    panel.pause_queued()
    panel._working = False
    panel._send_queued()
    assert panel.sent == [] and panel._queue == [("waiting", "act")]


def test_waiting_requests_keep_the_posture_they_were_sent_with(panel):
    panel._working = True
    panel._posture = "respond"
    send(panel, "read only")
    panel._posture = "act"
    send(panel, "make a map")
    panel._working = False
    panel._send_queued()
    panel._send_queued()
    assert panel.sent == [("read only", "respond"), ("make a map", "act")]


def test_a_request_that_cannot_start_waits_again_without_losing_the_draft(panel):
    panel.input.setText("unfinished draft")
    panel.queued_send_requested.emit = panel.restore_queued
    panel._queue = [("waiting", "propose")]
    panel._send_queued()
    assert panel._queue == [("waiting", "propose")] and panel._queue_paused
    assert panel.input.text() == "unfinished draft"


def test_push_bypasses_the_waiting_queue_and_keeps_the_draft_until_accepted(panel):
    panel._working = True
    send(panel, "waiting")
    panel.input.setText("urgent correction")
    panel._on_push()
    assert panel.pushed == ["urgent correction"] and panel.sent == []
    assert panel._queue == [("waiting", "act")] and panel.input.text() == "urgent correction"


def test_push_while_idle_sends_normally(panel):
    panel.input.setText("new request")
    panel._on_push()
    assert panel.sent == ["new request"] and not panel.pushed


def test_push_mode_sends_enter_to_the_running_request(panel):
    panel._working = True
    panel._followup_mode = "push"
    send(panel, "correction")
    assert panel.pushed == ["correction"] and not panel._queue
    assert panel.input.text() == "correction"  # cleared by the controller after acceptance


@pytest.mark.parametrize("mode", ["push", "queue"])
def test_alternate_send_inverts_the_selected_mode(panel, mode):
    panel._working = True
    panel._followup_mode = mode
    panel.input.setText("follow-up")
    panel._on_send(alternate=True)
    assert bool(panel.pushed) is (mode == "queue")
    assert bool(panel._queue) is (mode == "push")


def test_send_now_promotes_only_the_first_waiting_message_and_keeps_the_draft(panel):
    panel._working = True
    send(panel, "first")
    send(panel, "second")
    panel.input.setText("draft")
    panel._push_queued()
    assert panel.pushed == [("first", "act")] and panel._queue == [("second", "act")]
    assert panel.input.text() == "draft" and panel.queue_row.visible


def test_a_rejected_send_now_restores_the_waiting_message(panel):
    panel._working = True
    send(panel, "waiting")
    panel.input.setText("draft")
    panel.queued_push_requested.emit = panel.restore_queued
    panel._push_queued()
    assert panel._queue == [("waiting", "act")] and panel._queue_paused
    assert panel.input.text() == "draft"


@pytest.mark.parametrize("speech_state", ["recording", "transcribing"])
def test_push_waits_until_dictation_has_been_reviewed(panel, speech_state):
    panel._working = True
    panel._speech_state = speech_state
    panel.input.setText("unreviewed")
    panel._on_push()
    assert not panel.pushed and not panel.sent and panel.input.text() == "unreviewed"
