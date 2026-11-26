# -*- coding: utf-8 -*-
"""Keep a conversation from one project session to the next, and take it up again (core/agent/session_io.py)."""
import json

import pytest

from core.agent.messages import (
    ROLE_ASSISTANT, ROLE_USER, STOP_END, STOP_TOOL_USE, Message, OpaquePart, TextPart, ToolCallPart, ToolResultPart,
    TurnComplete, Usage,
)
from core.agent.providers import create_provider
from core.agent.providers.base import ProviderConfig
from core.agent.session import AgentLimits, AgentSession
from core.agent.session_io import MAX_STORED_CHARS, SavedSession, dump, parse, resumable
from core.agent.tool_catalog import ToolSpec

pytestmark = pytest.mark.unit

READ = ToolSpec("read", "Read something here.", {"type": "object", "properties": {}}, read_only=True)


def make_session():
    return AgentSession(create_provider(ProviderConfig("anthropic", "m")), [READ], "S", AgentLimits(12))


def user(text):
    return Message(ROLE_USER, (TextPart(text),))


def exchange():
    """A request, a tool call, its result and an answer: what a resumed conversation holds."""
    return [user("filter the communes"),
            Message(ROLE_ASSISTANT, (ToolCallPart("c1", "read", {"layer": "communes"}),)),
            Message(ROLE_USER, (ToolResultPart("c1", "3 features"),)),
            Message(ROLE_ASSISTANT, (TextPart("done"),))]


def accept(session, messages):
    for message in messages:
        if message.role == ROLE_ASSISTANT and message.tool_calls:
            session.accept_turn(TurnComplete(message, STOP_TOOL_USE))
        elif message.role == ROLE_ASSISTANT:
            session.accept_turn(TurnComplete(message, STOP_END))
        elif any(isinstance(part, ToolResultPart) for part in message.parts):
            session.add_tool_results([part for part in message.parts if isinstance(part, ToolResultPart)])
        else:
            session.add_user_text(message.text)


def test_round_trip_keeps_every_part_usage_and_counts():
    session = make_session()
    accept(session, exchange())
    saved = parse(dump(session.messages, session.usage + Usage(10, 20, 30, 40), 3, "anthropic", "m"))
    assert isinstance(saved, SavedSession)
    assert (saved.preset, saved.model, saved.summarized) == ("anthropic", "m", 3)
    assert saved.usage == Usage(10, 20, 30, 40)
    assert [message.text for message in saved.messages] == ["filter the communes", "", "", "done"]
    assert saved.messages[1].tool_calls == (ToolCallPart("c1", "read", {"layer": "communes"}),)
    assert isinstance(saved.messages[2].parts[0], ToolResultPart)


def test_opaque_blocks_and_call_details_survive():
    messages = [user("think about this"),
                Message(ROLE_ASSISTANT, (OpaquePart("anthropic", {"thinking": "hmm"}),
                                         ToolCallPart("c9", "read", {"a": [1, {"b": None}]}, "bad json"),))]
    saved = parse(dump(messages, preset="anthropic", model="m"))
    assert saved.messages == tuple(messages)


def test_images_are_never_stored():
    messages = [user("show me the map"),
                Message(ROLE_USER, (ToolResultPart("c1", "map", images=(("image/png", "aGVsbG8="),)),))]
    saved = parse(dump(messages))
    assert saved.messages[1].parts == (ToolResultPart("c1", "map"),)


def test_odd_input_is_dropped_never_raised():
    assert parse("") is None
    assert parse("not json") is None
    assert parse(json.dumps({"version": 999, "messages": []})) is None
    assert parse(json.dumps({"version": 1, "messages": "nope"})) is None
    assert parse(json.dumps({"version": 1, "messages": []})) is None
    assert parse(json.dumps({"version": 1, "messages": [{"role": "user", "parts": [{"type": "text"}]},
                                                        "odd", {"role": "evil", "parts": []}]})) is None


def test_resume_only_for_the_same_destination():
    text = dump(exchange(), preset="anthropic", model="m")
    assert resumable(text, "anthropic", "m")
    assert not resumable(text, "openai", "m")
    assert not resumable(text, "anthropic", "other")
    assert not resumable("not json", "anthropic", "m")
    assert not resumable(dump([]), "anthropic", "m")


def test_a_resumed_session_goes_on_like_the_original():
    first = make_session()
    accept(first, exchange())
    text = dump(first.messages, first.usage, first.summarized, "anthropic", "m")

    second = make_session()
    saved = parse(text)
    assert second.restore_history(saved.messages, saved.usage, saved.summarized)
    assert second.messages == first.messages
    assert second.usage == first.usage
    # The project may have changed meanwhile: the next request carries the whole state again.
    assert second.rewritten is True
    second.add_user_text("and now export them", "full state")
    assert second.messages[-1].text == "and now export themfull state"
    assert second.messages[-2:] != first.messages[-2:]


def test_resume_never_mixes_two_conversations():
    session = make_session()
    session.add_user_text("hello")
    assert session.restore_history(exchange()) is False
    assert [message.text for message in session.messages] == ["hello"]
    assert session.restore_history([]) is False


def test_dump_keeps_the_newest_requests_whole_when_too_long():
    messages = []
    for number in range(30):
        messages += [user(f"request {number} " + "x" * 20000),
                     Message(ROLE_USER, (ToolResultPart(f"c{number}", "y" * 20000),))]
    text = dump(messages, preset="anthropic", model="m")
    assert len(text) <= MAX_STORED_CHARS
    saved = parse(text)
    assert saved is not None
    from core.agent.compaction import is_request
    requests = [message.text for message in saved.messages if is_request(message)]
    assert len(requests) >= 2 and requests[0].startswith("request ")
    assert requests[-1].startswith("request 29 ")
    assert resumable(text, "anthropic", "m")


def test_dump_of_nothing_keeps_nothing():
    assert dump([]) == ""
    assert parse("") is None


def test_dump_parse_resume_dump_is_stable():
    """Keep, take up again, keep: the second dump holds the same conversation (minus nothing)."""
    first = make_session()
    accept(first, exchange())
    saved = parse(dump(first.messages, first.usage, first.summarized, "anthropic", "m"))
    second = make_session()
    assert second.restore_history(saved.messages, saved.usage, saved.summarized)
    again = parse(dump(second.messages, second.usage, second.summarized, "anthropic", "m"))
    assert again.messages == saved.messages and again.usage == saved.usage


def test_a_slice_starting_mid_request_is_not_kept():
    """A provider wants alternating roles from a request: a dangling result resumes nothing."""
    assert dump([Message(ROLE_USER, (ToolResultPart("c1", "orphan"),))]) == ""
