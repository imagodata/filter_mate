# -*- coding: utf-8 -*-
"""The waiting request never eats what was typed (audit of 2026-11-24, lot 4).

- A draft typed while a request waits stays behind it when the waiting one goes (it was overwritten, and after
  a provider error the returned request too);
- a second Enter while one waits joins it in sight (it replaced the first one without a trace).

The two methods are read off ``AgentPanel`` by AST and run on a stub (no Qt).
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
    """What ``_on_send`` / ``_send_queued`` touch: the line, the working flag, the waiting request."""

    def __init__(self):
        self.sent = []
        self.input = Line()
        self._working = False
        self._queued = ""
        self._queue_paused = False
        self.queue_label = SimpleNamespace(full="", set_full_text=lambda text: setattr(self.queue_label, "full", text),
                                           setToolTip=lambda text: None)
        self.queue_row = SimpleNamespace(visible=False, setVisible=lambda visible: setattr(
            self.queue_row, "visible", visible))
        self.queue_cancel = SimpleNamespace(setToolTip=lambda text: None)
        self.send_requested = SimpleNamespace(emit=self.sent.append)
        for name in ("_on_send", "_send_queued", "pause_queued", "cancel_queued"):
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
    assert panel._queued == "first" and panel.input.text() == "" and panel.queue_row.visible


def test_second_enter_joins_in_sight(panel):
    panel._working = True
    send(panel, "first")
    send(panel, "second")
    assert panel._queued == "first\nsecond"
    assert "first" in panel.queue_label.full and "second" in panel.queue_label.full


def test_draft_typed_meanwhile_waits_behind(panel):
    panel._working = True
    send(panel, "waiting")
    panel._working = False
    panel.input.setText("draft")
    panel._send_queued()
    assert panel.sent == ["waiting"]
    assert panel._queued == "draft" and panel.queue_row.visible
    assert "draft" in panel.queue_label.full


def test_nothing_typed_nothing_queued_behind(panel):
    panel._working = True
    send(panel, "waiting")
    panel._working = False
    panel._send_queued()
    assert panel.sent == ["waiting"] and panel._queued == "" and not panel.queue_row.visible


def test_stopped_queue_does_not_go_by_itself(panel):
    panel._working = True
    send(panel, "waiting")
    panel.pause_queued()
    panel._working = False
    panel._send_queued()
    assert panel.sent == [] and panel._queued == "waiting"
