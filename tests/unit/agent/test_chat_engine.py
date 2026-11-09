# -*- coding: utf-8 -*-
"""The non-blocking conversation: order of the steps, stale events, cancelling, undo points."""
import pytest

from core.agent.chat_engine import ChatEngine
from core.agent.messages import (
    ROLE_ASSISTANT, STOP_END, STOP_MAX_TOKENS, STOP_TOOL_USE, Message, ProviderError, StreamFailure, TextDelta, TextPart,
    ToolCallPart, TurnComplete,
)
from core.agent.providers import create_provider
from core.agent.providers.base import ProviderConfig
from core.agent.session import AgentSession
from core.agent.tool_catalog import ToolSpec
from core.agent.tool_executor import ToolExecutor

pytestmark = pytest.mark.unit

READ = ToolSpec("read", "Read something here.", {"type": "object", "properties": {}}, read_only=True)
WRITE = ToolSpec("write", "Change something here.", {"type": "object", "properties": {}})
EXPORT = ToolSpec("export", "Write a file there.", {"type": "object", "properties": {}}, destructive=True)


def call(name, call_id="c1"):
    return ToolCallPart(call_id, name, {})


def turn(stop, *parts):
    return TurnComplete(Message(ROLE_ASSISTANT, parts), stop)


class Handle:
    def __init__(self):
        self.aborted = False

    def abort(self):
        self.aborted = True


class Transport:
    """Each ``start`` waits until the test feeds it."""

    def __init__(self):
        self.starts = []

    def start(self, request, parser, on_event):
        handle = Handle()
        self.starts.append((request, on_event, handle))
        return handle

    def emit(self, *events, index=-1):
        for event in events:
            self.starts[index][1](event)


class Listener:
    def __init__(self, accept=True):
        self.log = []
        self.outcomes = []
        self.accept = accept
        self.hook = None

    def on_text(self, text):
        self.log.append(("text", text))

    def on_tool_start(self, c):
        self.log.append(("start", c.name))
        if self.hook:
            self.hook()

    def on_tool_end(self, c, result):
        self.log.append(("end", c.name, result.is_error))

    def confirm(self, c):
        self.log.append(("confirm", c.name))
        return self.accept

    def on_finished(self, outcome):
        self.outcomes.append(outcome)


class Checkpoint:
    def __init__(self):
        self.begins = 0
        self.commits = 0
        self.fail = False

    def begin(self):
        if self.fail:
            raise RuntimeError("no")
        self.begins += 1

    def commit(self):
        self.commits += 1
        return ("layer",) if self.begins else ()


@pytest.fixture
def setup():
    tools = [READ, WRITE, EXPORT]
    session = AgentSession(create_provider(ProviderConfig("anthropic", "m")), tools, "S")
    seen = []
    handlers = {tool.name: (lambda name: lambda a: seen.append(name) or {"ok": True})(tool.name) for tool in tools}
    transport, listener, checkpoint = Transport(), Listener(), Checkpoint()
    engine = ChatEngine(session, ToolExecutor(tools, handlers), transport, listener, checkpoint)
    return engine, session, transport, listener, checkpoint, seen


def test_text_only(setup):
    engine, _, transport, listener, checkpoint, _ = setup
    assert engine.send("hello") and engine.busy
    transport.emit(TextDelta("Bon"), TextDelta("jour"), turn(STOP_END, TextPart("Bonjour")))
    assert not engine.busy
    assert listener.log == [("text", "Bon"), ("text", "jour")]
    assert listener.outcomes[0].status == "done" and listener.outcomes[0].changed_layers == ()
    assert checkpoint.begins == 0


@pytest.mark.parametrize("text", ["", "   "])
def test_nothing_to_send(setup, text):
    assert setup[0].send(text) is False


def test_one_request_at_a_time(setup):
    engine, _, transport, _, _, _ = setup
    assert engine.send("a")
    assert engine.send("b") is False
    assert len(transport.starts) == 1


def test_tools_then_answer_and_undo_point_before_the_first_write(setup):
    engine, session, transport, listener, checkpoint, seen = setup
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, call("read", "1"), call("write", "2"), call("write", "3")))
    assert seen == ["read", "write", "write"]
    assert checkpoint.begins == 2  # the checkpoint itself keeps only the first capture
    assert len(transport.starts) == 2
    assert len(session.messages[2].parts) == 3
    transport.emit(turn(STOP_END, TextPart("done")))
    assert listener.outcomes[0].changed_layers == ("layer",) and checkpoint.commits == 1


def test_no_undo_point_no_change(setup):
    engine, session, transport, _, checkpoint, seen = setup
    checkpoint.fail = True
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, call("write")))
    assert seen == [] and session.messages[2].parts[0].is_error


@pytest.mark.parametrize("accept", [True, False])
def test_export_is_confirmed(setup, accept):
    engine, session, transport, listener, _, seen = setup
    listener.accept = accept
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, call("export")))
    assert ("confirm", "export") in listener.log
    assert bool(seen) is accept
    assert session.messages[2].parts[0].is_error is (not accept)


def test_failure_forgets_the_request(setup):
    engine, session, transport, listener, _, _ = setup
    engine.send("go")
    transport.emit(StreamFailure(ProviderError("auth", "bad")))
    assert not engine.busy and session.messages == ()
    assert listener.outcomes[0].status == "failed" and listener.outcomes[0].error.kind == "auth"


def test_truncated_tool_calls_stop(setup):
    engine, _, transport, listener, _, seen = setup
    engine.send("go")
    transport.emit(turn(STOP_MAX_TOKENS, call("write")))
    assert seen == [] and listener.outcomes[0].status == "stopped" and listener.outcomes[0].reason == "truncated"


def test_cancel_while_streaming(setup):
    engine, session, transport, listener, _, _ = setup
    engine.send("go")
    engine.cancel()
    assert transport.starts[0][2].aborted and not engine.busy and session.messages == ()
    assert listener.outcomes[0].status == "cancelled"


def test_an_event_after_cancel_is_ignored(setup):
    engine, _, transport, listener, _, _ = setup
    engine.send("go")
    engine.cancel()
    transport.emit(TextDelta("late"), turn(STOP_END, TextPart("late")))
    assert listener.log == [] and len(listener.outcomes) == 1


def test_an_event_of_an_earlier_request_is_ignored(setup):
    engine, _, transport, listener, _, _ = setup
    engine.send("a")
    engine.cancel()
    engine.send("b")
    transport.emit(TextDelta("old"), index=0)
    assert listener.log == [] and engine.busy


def test_cancel_during_a_tool_waits_for_it_and_runs_no_other(setup):
    engine, session, transport, listener, _, seen = setup
    listener.hook = engine.cancel  # a tool spins the event loop, the user clicks Stop
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, call("write", "1"), call("write", "2")))
    assert seen == ["write"]
    assert not engine.busy and listener.outcomes[0].status == "cancelled"
    assert len(transport.starts) == 1 and session.messages == ()


def test_what_changed_before_a_cancel_is_reported(setup):
    engine, _, transport, listener, _, _ = setup
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, call("write")))
    engine.cancel()
    assert listener.outcomes[0].status == "cancelled" and listener.outcomes[0].changed_layers == ("layer",)


def test_a_request_that_cannot_be_sent_is_a_failure(setup):
    engine, session, transport, listener, _, _ = setup

    def broken(*args):
        raise RuntimeError("no")

    transport.start = broken
    assert engine.send("go")
    assert not engine.busy and listener.outcomes[0].status == "failed" and session.messages == ()


def test_a_transport_answering_at_once(setup):
    engine, session, transport, listener, _, _ = setup

    def immediate(request, parser, on_event):
        on_event(turn(STOP_END, TextPart("now")))
        return Handle()

    transport.start = immediate
    engine.send("go")
    assert not engine.busy and listener.outcomes[0].status == "done"
    engine.cancel()
    assert len(listener.outcomes) == 1


def _deferred_engine():
    tools = [READ, WRITE]
    session = AgentSession(create_provider(ProviderConfig("anthropic", "m")), tools, "S")
    executor = ToolExecutor(tools, {"read": lambda a: 1, "write": lambda a: 1})
    transport, listener, pending = Transport(), Listener(), []
    return ChatEngine(session, executor, transport, listener, Checkpoint(), defer=pending.append), transport, pending, listener


def test_no_request_leaves_after_stop():
    engine, transport, pending, listener = _deferred_engine()
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, call("read")))
    pending.pop(0)()  # the tools ran; the next request waits for the event loop
    engine.cancel()   # the click on Stop was queued before it
    pending.pop(0)()
    assert len(transport.starts) == 1 and listener.outcomes[0].status == "cancelled"


def test_stop_then_send_makes_one_request():
    engine, transport, pending, _ = _deferred_engine()
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, call("read")))
    pending.pop(0)()
    engine.cancel()
    engine.send("again")
    pending.pop(0)()  # the step of the first request
    assert len(transport.starts) == 2


@pytest.mark.parametrize("method", ["on_text", "on_tool_start", "on_tool_end", "on_finished", "confirm"])
def test_a_broken_interface_never_leaves_it_stuck(setup, method):
    engine, _, transport, listener, checkpoint, _ = setup

    def broken(*args):
        raise RuntimeError("widget deleted")

    setattr(listener, method, broken)
    engine.send("go")
    transport.emit(TextDelta("a"), turn(STOP_TOOL_USE, call("export", "1"), call("write", "2")))
    transport.emit(turn(STOP_END, TextPart("done")))
    assert not engine.busy and checkpoint.commits == 1


def test_defer_is_used_between_steps():
    tools = [READ]
    session = AgentSession(create_provider(ProviderConfig("anthropic", "m")), tools, "S")
    executor = ToolExecutor(tools, {"read": lambda a: 1})
    transport, listener = Transport(), Listener()
    pending = []
    engine = ChatEngine(session, executor, transport, listener, Checkpoint(), defer=pending.append)
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, call("read")))
    assert listener.log == []  # the tools wait for the event loop
    pending.pop(0)()
    assert listener.log and len(transport.starts) == 1
    pending.pop(0)()
    assert len(transport.starts) == 2
