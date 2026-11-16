# -*- coding: utf-8 -*-
"""A long conversation summed up (core/agent/compaction.py), and the session that does it before a request."""
import json

import pytest

from core.agent.compaction import SUMMARY_HEADER, compact, is_request
from core.agent.messages import ROLE_ASSISTANT, ROLE_USER, Message, TextPart, ToolCallPart, ToolResultPart
from core.agent.providers import create_provider
from core.agent.providers.base import ProviderConfig
from core.agent.session import CAUSE_FAILED, AgentLimits, AgentSession
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
                           AgentLimits(max_history_chars=3000))  # lot 3: tight enough that trimming the old
    for message in conversation(10):                                   # results is not enough
        session._messages.append(message)
    session.add_user_text("encore", "Project when...")
    assert session.summarized >= 1 and session.rewritten
    body = json.loads(session.next_request().body)
    assert body["messages"][0]["content"][0]["text"].startswith(SUMMARY_HEADER)
    assert body["messages"][-1]["content"][0]["text"] == "encore"
    session.interrupt_request(CAUSE_FAILED)  # a failed request that ran nothing takes only itself back
    assert session.messages[-1].parts[0].text == "réponse 10"


# --- lot 3: old tool results go first ----------------------------------------------------------------------------

from core.agent.compaction import TRIMMED, trim_results  # noqa: E402


def _results(messages):
    return [part for message in messages for part in message.parts if isinstance(part, ToolResultPart)]


def test_the_last_two_requests_keep_their_results():
    trimmed, count = trim_results(conversation(4, size=3000))
    contents = [part.content for part in _results(trimmed)]
    assert count == 2 and contents[2:] == ["r" * 3000, "r" * 3000]
    assert contents[0] == TRIMMED.format(3000, "apply_filter")


def test_a_trimmed_result_names_its_tool():
    trimmed, _count = trim_results(conversation(3, size=3000))
    assert "call apply_filter again" in _results(trimmed)[0].content


def test_a_result_trimmed_once_is_left_as_it_is_and_small_ones_stay():
    once, _ = trim_results(conversation(4, size=3000))
    again, count = trim_results(once)
    assert count == 0 and again == once
    small, count = trim_results(conversation(4, size=50))
    assert count == 0


def test_images_and_trimmed_results_together():
    messages = conversation(3, size=3000)
    old = messages[2]
    messages[2] = Message(ROLE_USER, (ToolResultPart("c1", "r" * 3000, images=(("image/png", "AAAA"),)),))
    trimmed, _ = trim_results(messages)
    part = _results(trimmed)[0]
    assert part.images == () and part.content.startswith("(Result of 3000 characters")
    assert old.role == ROLE_USER


def test_old_results_are_trimmed_first_and_enough_summarizes_nothing():
    session = AgentSession(create_provider(ProviderConfig("anthropic", "m")), chat_tools()[:1], "S",
                           AgentLimits(max_history_chars=9000))
    session._messages = conversation(4, size=3000)  # 12,000 characters of results
    session.add_user_text("encore")
    assert session.rewritten and session.summarized == 0
    assert sum(1 for part in _results(session.messages) if part.content.startswith("(Result of")) == 2
