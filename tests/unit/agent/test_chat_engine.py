# -*- coding: utf-8 -*-
"""The non-blocking conversation: order of the steps, stale events, cancelling, undo points, what a request that
breaks off keeps, new tries."""
import json
import math

import pytest

from core.agent.chat_engine import MAX_RETRY_WAIT, NO_RETRY_ABOVE, ChatEngine
from core.agent.messages import (
    ROLE_ASSISTANT, ROLE_USER, STOP_END, STOP_MAX_TOKENS, STOP_REFUSAL, STOP_TOOL_USE, Message, ProviderError,
    StreamFailure, TextDelta, TextPart, ToolCallPart, TurnComplete,
)
from core.agent.providers import create_provider
from core.agent.providers.base import ProviderConfig
from core.agent.session import NOT_RUN, AgentSession
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

    def begin(self, call=None):
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
    assert len(transport.starts) == 1
    # The call that ran stays, with its result; the other one is answered as not run, so the turn stays valid.
    assert [m.role for m in session.messages] == [ROLE_USER, ROLE_ASSISTANT, ROLE_USER]
    first, second, note = session.messages[2].parts
    assert (first.call_id, first.is_error) == ("1", False)
    assert (second.call_id, second.content, second.is_error) == ("2", NOT_RUN, True)
    assert "the user clicked Stop" in note.text
    assert listener.outcomes[0].kept_steps == 1


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


# --- a request that breaks off keeps what it ran ------------------------------------------------------------------

PROVIDERS = {
    "anthropic": ProviderConfig("anthropic", "m"),
    "openai": ProviderConfig("openai_compatible", "m", base_url="https://api.example.com/v1"),
    "ollama": ProviderConfig("ollama", "m", base_url="http://localhost:11434"),
}


def _engine(config=PROVIDERS["anthropic"], delays=None):
    """An engine with the three tools; ``delays`` gets ``(seconds, step)`` of each new try instead of running it."""
    tools = [READ, WRITE, EXPORT]
    session = AgentSession(create_provider(config), tools, "S")
    seen = []
    handlers = {tool.name: (lambda name: lambda a: seen.append(name) or {"ok": True})(tool.name) for tool in tools}
    transport, listener = Transport(), RetryListener()
    delay = (lambda seconds, step: delays.append((seconds, step))) if delays is not None else (
        lambda seconds, step: step())
    engine = ChatEngine(session, ToolExecutor(tools, handlers), transport, listener, Checkpoint(), delay=delay)
    return engine, session, transport, listener, seen


class RetryListener(Listener):
    def __init__(self):
        super().__init__()
        self.retries = []

    def on_retry(self, seconds, error):
        self.retries.append((seconds, error.kind))


def check_wire(kind, body):
    """The request is one each provider takes: every call answered right after it, no empty message, and roles
    that alternate for the user (Anthropic: all roles; OpenAI and Ollama: never two messages of the user in a row).
    Returns the end of the last message of the user."""
    if kind == "anthropic":
        messages = body["messages"]
        roles = [message["role"] for message in messages]
        assert roles[0] == "user" and all(a != b for a, b in zip(roles, roles[1:]))
        for position, message in enumerate(messages):
            assert message["content"]
            uses = [block["id"] for block in message["content"] if block["type"] == "tool_use"]
            if uses:
                following = messages[position + 1]["content"]
                assert [block.get("tool_use_id") for block in following[:len(uses)]] == uses
        return messages[-1]["content"][-1]["text"]
    messages = body["messages"][1:]  # after the system message
    roles = [message["role"] for message in messages]
    assert roles[0] == "user" and not any(a == b == "user" for a, b in zip(roles, roles[1:]))
    for position, message in enumerate(messages):
        if message["role"] == "tool":
            before = [m for m in messages[:position] if m["role"] != "tool"][-1]
            assert before["role"] == "assistant" and before.get("tool_calls")
        if message["role"] != "assistant":
            continue
        calls = message.get("tool_calls") or []
        assert message["content"] or calls
        answers = messages[position + 1:position + 1 + len(calls)]
        assert [answer["role"] for answer in answers] == ["tool"] * len(calls)
        if kind == "openai":
            assert [answer["tool_call_id"] for answer in answers] == [c["id"] for c in calls]
        else:
            assert [answer["tool_name"] for answer in answers] == [c["function"]["name"] for c in calls]
    return messages[-1]["content"]


@pytest.mark.parametrize("kind", sorted(PROVIDERS))
def test_a_failure_at_the_second_turn_keeps_the_first_and_the_next_request_is_valid(kind):
    engine, session, transport, listener, seen = _engine(PROVIDERS[kind])
    engine.send("add the parks")
    transport.emit(turn(STOP_TOOL_USE, TextPart("Adding."), call("read", "1"), call("write", "2")))
    transport.emit(StreamFailure(ProviderError("stream", "The response was cut before its end.")))
    outcome = listener.outcomes[0]
    assert outcome.status == "failed" and outcome.kept_steps == 1 and seen == ["read", "write"]  # a reading is no step
    assert [m.role for m in session.messages] == [ROLE_USER, ROLE_ASSISTANT, ROLE_USER]
    assert "the request to the model failed" in session.messages[-1].text
    engine.send("go on")
    body = json.loads(transport.starts[-1][0].body)
    assert check_wire(kind, body).endswith("go on")  # OpenAI and Ollama: in one message with the note
    assert "broke off here" in json.dumps(body)


@pytest.mark.parametrize("kind", sorted(PROVIDERS))
def test_a_stop_during_a_tool_leaves_a_valid_conversation(kind):
    engine, session, transport, listener, seen = _engine(PROVIDERS[kind])
    listener.hook = engine.cancel
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, call("write", "1"), call("export", "2"), call("read", "3")))
    assert seen == ["write"] and listener.outcomes[0].kept_steps == 1
    engine.send("go on")
    assert check_wire(kind, json.loads(transport.starts[-1][0].body)).endswith("go on")


def test_the_note_replaces_the_turns_left_note():
    engine, session, transport, listener, _ = _engine()
    session._limits = type(session._limits)(max_model_turns=3, warn_turns_left=2)
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, call("write", "1")))
    assert "model turns left" in session.messages[-1].text
    engine.cancel()
    texts = [part.text for part in session.messages[-1].parts if isinstance(part, TextPart)]
    assert len(texts) == 1 and "broke off here" in texts[0]


def test_a_stop_before_the_tools_of_a_turn_ran_drops_that_turn_and_keeps_the_ones_before():
    pending = []
    tools = [READ, WRITE]
    session = AgentSession(create_provider(PROVIDERS["anthropic"]), tools, "S")
    executor = ToolExecutor(tools, {"read": lambda a: 1, "write": lambda a: 1})
    transport, listener = Transport(), Listener()
    engine = ChatEngine(session, executor, transport, listener, Checkpoint(), defer=pending.append)
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, call("write", "1")))
    pending.pop(0)()  # the tools ran
    pending.pop(0)()  # the next request left
    transport.emit(turn(STOP_TOOL_USE, call("write", "2")))  # its tools wait for the event loop: Stop comes first
    engine.cancel()
    pending.pop(0)()
    assert [m.role for m in session.messages] == [ROLE_USER, ROLE_ASSISTANT, ROLE_USER]
    assert session.messages[-1].parts[0].call_id == "1" and listener.outcomes[0].kept_steps == 1


def test_a_stop_while_streaming_after_tools_keeps_them(setup):
    engine, session, transport, listener, _, _ = setup
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, call("write", "1")))
    transport.emit(TextDelta("And now"))
    engine.cancel()
    assert transport.starts[1][2].aborted and listener.outcomes[0].status == "cancelled"
    assert listener.outcomes[0].kept_steps == 1 and len(session.messages) == 3


def test_a_refusal_after_tools_keeps_them(setup):
    engine, session, transport, listener, _, _ = setup
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, call("write", "1")))
    transport.emit(turn(STOP_REFUSAL, TextPart("No.")))
    outcome = listener.outcomes[0]
    assert outcome.status == "stopped" and outcome.reason == "refused" and outcome.kept_steps == 1
    assert "the model declined to go on" in session.messages[-1].text and len(session.messages) == 3


def test_failed_steps_forget_the_request(setup):
    engine, session, transport, listener, checkpoint, _ = setup
    checkpoint.fail = True  # the write is refused before it runs
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, call("write", "1")))
    transport.emit(StreamFailure(ProviderError("auth", "bad")))
    assert listener.outcomes[0].kept_steps == 0 and session.messages == ()


def test_declined_steps_forget_the_request(setup):
    engine, session, transport, listener, _, seen = setup
    listener.accept = False  # the export is refused by the user
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, call("export", "1")))
    transport.emit(StreamFailure(ProviderError("auth", "bad")))
    assert seen == [] and listener.outcomes[0].kept_steps == 0 and session.messages == ()


def test_a_failure_after_readings_only_forgets_the_request(setup):
    engine, session, transport, listener, _, seen = setup
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, call("read", "1"), call("read", "2")))
    transport.emit(StreamFailure(ProviderError("auth", "bad")))
    assert seen == ["read", "read"]
    assert listener.outcomes[0].status == "failed" and listener.outcomes[0].kept_steps == 0
    assert session.messages == ()
    engine.send("again")  # the request is sent again whole: the conversation starts clean
    assert [m.role for m in session.messages] == [ROLE_USER]


def test_a_stop_after_readings_only_forgets_the_request(setup):
    engine, session, transport, listener, _, _ = setup
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, call("read", "1")))
    engine.cancel()
    assert listener.outcomes[0].status == "cancelled" and listener.outcomes[0].kept_steps == 0
    assert session.messages == ()


def test_a_reading_beside_a_change_is_kept_but_not_counted(setup):
    engine, session, transport, listener, _, _ = setup
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, call("read", "1"), call("write", "2")))
    transport.emit(StreamFailure(ProviderError("auth", "bad")))
    assert listener.outcomes[0].kept_steps == 1 and len(session.messages) == 3


@pytest.mark.parametrize("kind", sorted(PROVIDERS))
def test_a_bad_request_after_a_change_forgets_the_request_but_counts_the_step(kind):
    engine, session, transport, listener, seen = _engine(PROVIDERS[kind])
    engine.send("add the parks")
    transport.emit(turn(STOP_TOOL_USE, call("write", "1")))
    transport.emit(StreamFailure(ProviderError("bad_request", "Too long for the model.", status=400)))
    outcome = listener.outcomes[0]
    assert outcome.status == "failed" and outcome.error.kind == "bad_request"
    assert seen == ["write"] and outcome.kept_steps == 1
    assert session.messages == ()  # nothing of it stays: it would be refused again with every later request
    engine.send("go on")
    assert [m.role for m in session.messages] == [ROLE_USER]
    assert check_wire(kind, json.loads(transport.starts[-1][0].body)) == "go on"


def test_another_failure_after_a_change_keeps_the_request(setup):
    engine, session, transport, listener, _, _ = setup
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, call("write", "1")))
    transport.emit(StreamFailure(ProviderError("auth", "bad")))
    assert listener.outcomes[0].kept_steps == 1 and len(session.messages) == 3


@pytest.mark.parametrize("kind", ["openai", "ollama"])
def test_the_roles_alternate_for_the_user_after_a_request_that_broke_off(kind):
    engine, session, transport, listener, _ = _engine(PROVIDERS[kind])
    engine.send("add the parks")
    transport.emit(turn(STOP_TOOL_USE, call("write", "1")))
    transport.emit(StreamFailure(ProviderError("auth", "bad")))  # the step stays, with the note
    engine.send("go on")
    body = json.loads(transport.starts[-1][0].body)
    last = check_wire(kind, body)  # also checks that no two messages of the user follow each other
    assert last.startswith("This request broke off here") and last.endswith("\n\ngo on")
    assert [m["role"] for m in body["messages"][1:]] == ["user", "assistant", "tool", "user"]


# --- a provider busy for a moment is asked again ------------------------------------------------------------------


def test_a_busy_provider_is_asked_again_without_showing_anything_twice():
    delays = []
    engine, session, transport, listener, _ = _engine(delays=delays)
    engine.send("hello")
    transport.emit(StreamFailure(ProviderError("server", "Overloaded", status=529)))
    assert engine.busy and listener.outcomes == [] and listener.retries == [(2.0, "server")]
    seconds, step = delays.pop(0)
    step()
    assert len(transport.starts) == 2
    transport.emit(TextDelta("Bonjour"), turn(STOP_END, TextPart("Bonjour")))
    assert listener.outcomes[0].status == "done"
    assert listener.log == [("text", "Bonjour")]
    assert [m.role for m in session.messages] == [ROLE_USER, ROLE_ASSISTANT]


def test_a_late_event_of_the_failed_response_is_ignored():
    delays = []
    engine, _, transport, listener, _ = _engine(delays=delays)
    engine.send("hello")
    transport.emit(StreamFailure(ProviderError("rate_limit", "slow down", status=429)))
    transport.emit(TextDelta("stale"), index=0)
    assert listener.log == []


def test_two_new_tries_at_most_then_the_failure_keeps_the_tools_run():
    delays = []
    engine, session, transport, listener, _ = _engine(delays=delays)
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, call("write", "1")))
    for _ in range(2):
        transport.emit(StreamFailure(ProviderError("server", "Overloaded")))
        delays.pop(0)[1]()
    transport.emit(StreamFailure(ProviderError("server", "Overloaded")))
    assert [seconds for seconds, _kind in listener.retries] == [2.0, 6.0] and delays == []
    assert listener.outcomes[0].status == "failed" and listener.outcomes[0].kept_steps == 1
    assert len(transport.starts) == 4 and len(session.messages) == 3


def test_each_model_turn_has_its_own_tries():
    delays = []
    engine, _, transport, listener, _ = _engine(delays=delays)
    engine.send("go")
    transport.emit(StreamFailure(ProviderError("server", "Overloaded")))
    delays.pop(0)[1]()
    transport.emit(turn(STOP_TOOL_USE, call("read", "1")))
    transport.emit(StreamFailure(ProviderError("server", "Overloaded")))
    assert [seconds for seconds, _kind in listener.retries] == [2.0, 2.0]


@pytest.mark.parametrize("status,kind", [(400, "bad_request"), (401, "auth"), (403, "auth"), (404, "bad_request"),
                                         (402, "quota")])
def test_no_new_try_for_what_waiting_does_not_fix(status, kind):
    delays = []
    engine, _, transport, listener, _ = _engine(delays=delays)
    engine.send("hello")
    transport.emit(StreamFailure(ProviderError(kind, "no", status=status)))
    assert delays == [] and listener.retries == [] and listener.outcomes[0].status == "failed"


def test_no_new_try_once_text_was_shown():
    delays = []
    engine, _, transport, listener, _ = _engine(delays=delays)
    engine.send("hello")
    transport.emit(TextDelta("Bon"), StreamFailure(ProviderError("server", "Overloaded")))
    assert delays == [] and listener.outcomes[0].status == "failed"


@pytest.mark.parametrize("transient", [True, False])
def test_a_network_failure_is_tried_again_when_it_may_pass(transient):
    delays = []
    engine, _, transport, listener, _ = _engine(delays=delays)
    engine.send("hello")
    transport.emit(StreamFailure(ProviderError("network", "reset", transient=transient)))
    assert bool(delays) is transient and (listener.outcomes == []) is transient


@pytest.mark.parametrize("retry_after,wait", [(12.0, 12.0), (NO_RETRY_ABOVE, MAX_RETRY_WAIT), (0.0, 0.0),
                                              (-3.0, 2.0), (math.nan, 2.0)])
def test_the_wait_follows_retry_after_up_to_a_bound(retry_after, wait):
    delays = []
    engine, _, transport, listener, _ = _engine(delays=delays)
    engine.send("hello")
    transport.emit(StreamFailure(ProviderError("rate_limit", "slow down", status=429, retry_after=retry_after)))
    assert delays[0][0] == wait and listener.retries == [(wait, "rate_limit")]


@pytest.mark.parametrize("retry_after", [NO_RETRY_ABOVE + 1, 3600.0, math.inf])
@pytest.mark.parametrize("kind", ["rate_limit", "server"])
def test_no_new_try_when_the_provider_asks_to_come_back_much_later(kind, retry_after):
    delays = []
    engine, _, transport, listener, _ = _engine(delays=delays)
    engine.send("hello")
    transport.emit(StreamFailure(ProviderError(kind, "come back tomorrow", status=429, retry_after=retry_after)))
    assert delays == [] and listener.retries == []
    assert not engine.busy and listener.outcomes[0].status == "failed" and listener.outcomes[0].error.kind == kind


def test_stop_during_the_wait_cancels_the_new_try():
    delays = []
    engine, session, transport, listener, _ = _engine(delays=delays)
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, call("write", "1")))
    transport.emit(StreamFailure(ProviderError("server", "Overloaded")))
    engine.cancel()
    assert not engine.busy and listener.outcomes[0].status == "cancelled" and listener.outcomes[0].kept_steps == 1
    delays.pop(0)[1]()  # the timer fires anyway
    assert len(transport.starts) == 2 and len(listener.outcomes) == 1


def test_a_listener_without_on_retry_is_fine():
    session = AgentSession(create_provider(PROVIDERS["anthropic"]), [READ], "S")
    transport, listener = Transport(), Listener()
    engine = ChatEngine(session, ToolExecutor([READ], {"read": lambda a: 1}), transport, listener, Checkpoint())
    engine.send("hello")
    transport.emit(StreamFailure(ProviderError("server", "Overloaded")))
    transport.emit(turn(STOP_END, TextPart("ok")))
    assert listener.outcomes[0].status == "done" and len(transport.starts) == 2
