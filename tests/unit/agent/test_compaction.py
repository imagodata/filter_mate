# -*- coding: utf-8 -*-
"""A long conversation summed up (core/agent/compaction.py), and the session that does it before a request."""
import json

import pytest

from core.agent.compaction import SUMMARY_HEADER, compact, is_request
from core.agent.messages import ROLE_ASSISTANT, ROLE_USER, Message, TextPart, ToolCallPart, ToolResultPart
from core.agent.providers import create_provider
from core.agent.providers.base import ProviderConfig
from core.agent.session import AgentLimits, AgentSession
from core.agent.tool_catalog import chat_tools

pytestmark = pytest.mark.unit


def exchange(number, size=1000, write=True):
    """A request, a tool call and its result, an answer."""
    call = ToolCallPart(f"c{number}", "apply_filter" if write else "list_layers",
                        {"layer_name": f"couche{number}", "expression": "x"} if write else {})
    return [Message(ROLE_USER, (TextPart(f"demande {number}"), TextPart("Project when... " + "p" * 50))),
            Message(ROLE_ASSISTANT, (TextPart("je regarde"), call)),
            Message(ROLE_USER, (ToolResultPart(f"c{number}", "r" * size),)),
            Message(ROLE_ASSISTANT, (TextPart(f"réponse {number}"),))]


def conversation(count, size=1000):
    return [message for number in range(1, count + 1) for message in exchange(number, size)]


def test_under_the_budget_nothing_changes():
    messages = conversation(3)
    assert compact(messages, 100_000, ["apply_filter"]) == (messages, 0)


def test_the_oldest_requests_become_lines_of_a_summary():
    messages = conversation(10)
    kept, summarized = compact(messages, 6000, ["apply_filter"])
    assert summarized == 7 and len(kept) == 3 * 4
    first = kept[0]
    assert first.role == ROLE_USER and first.parts[0].text.startswith(SUMMARY_HEADER)
    lines = first.parts[0].text.splitlines()[1:]
    assert lines[0] == "- asked: demande 1 | changed: apply_filter couche1 | answered: réponse 1"
    assert len(lines) == 7 and lines[-1].startswith("- asked: demande 7")
    assert [part.text for part in first.parts[1:]][0] == "demande 8"  # the request kept, whole, after it


def test_every_tool_call_keeps_its_result():
    kept, _ = compact(conversation(12, size=3000), 10_000, ["apply_filter"])
    calls = {part.call_id for message in kept for part in message.parts if isinstance(part, ToolCallPart)}
    results = {part.call_id for message in kept for part in message.parts if isinstance(part, ToolResultPart)}
    assert calls == results and calls
    roles = [message.role for message in kept]
    assert all(a != b for a, b in zip(roles, roles[1:]))  # user and assistant alternate


def test_a_second_summary_carries_the_first():
    messages = conversation(10)
    kept, _ = compact(messages, 6000, ["apply_filter"])
    longer = kept + conversation(14)[40:]
    again, summarized = compact(longer, 6000, ["apply_filter"])
    lines = again[0].parts[0].text.splitlines()
    assert lines.count(SUMMARY_HEADER) == 1 and lines[0] == SUMMARY_HEADER
    assert lines[1].startswith("- asked: demande 1 ") and summarized >= 1
    assert all("Project when" not in line for line in lines)


def test_the_last_request_is_always_kept():
    messages = exchange(1, 50_000) + exchange(2, 50_000)
    kept, summarized = compact(messages, 1000, ["apply_filter"])
    assert summarized == 1 and kept[0].parts[1].text == "demande 2" and len(kept) == 4
    assert compact(exchange(1, 50_000), 1000) == (exchange(1, 50_000), 0)


def test_reading_tools_are_not_named_as_changes():
    messages = [message for number in range(1, 6) for message in exchange(number, 2000, write=False)]
    kept, _ = compact(messages, 5000, ["apply_filter"])
    assert "changed:" not in kept[0].parts[0].text


def test_a_tool_result_is_no_request():
    assert not is_request(Message(ROLE_USER, (ToolResultPart("a", "x"), TextPart("3 model turns left"))))
    assert is_request(Message(ROLE_USER, (TextPart("x"),)))


def test_the_session_sums_up_before_a_request():
    session = AgentSession(create_provider(ProviderConfig("anthropic", "m")), chat_tools(), "S",
                           AgentLimits(max_history_chars=6000))
    for message in conversation(10):
        session._messages.append(message)
    session.add_user_text("encore", "Project when...")
    assert session.summarized == 7
    body = json.loads(session.next_request().body)
    assert body["messages"][0]["content"][0]["text"].startswith(SUMMARY_HEADER)
    assert body["messages"][-1]["content"][0]["text"] == "encore"
    session.abandon_request()  # a failed request takes only itself back
    assert session.messages[-1].parts[0].text == "réponse 10"
