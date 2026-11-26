# -*- coding: utf-8 -*-
"""Skill instructions survive reuse, history trimming and session persistence without duplicating their bodies."""
import json

import pytest

from core.agent.compaction import compact, trim_results
from core.agent.messages import (
    ROLE_ASSISTANT, ROLE_USER, STOP_END, STOP_TOOL_USE, Message, TextPart, ToolCallPart, ToolResultPart, TurnComplete,
)
from core.agent.providers import create_provider
from core.agent.providers.base import ProviderConfig
from core.agent.session import AgentSession
from core.agent.session_io import dump, parse
from core.agent.skills import MAX_ACTIVE_SKILLS, MAX_BODY, loaded_skills
from core.agent.tool_catalog import ToolSpec
from core.agent.tool_executor import MAX_RESULT_CHARS, MAX_SKILL_RESULT_CHARS, ToolExecutor

pytestmark = pytest.mark.unit
LOAD = ToolSpec("load_skill", "Load a skill.", {"type": "object", "properties": {"name": {"type": "string"}},
                                              "required": ["name"]}, read_only=True)


def session():
    return AgentSession(create_provider(ProviderConfig("anthropic", "m")), [LOAD], "S")


def load(chat, name="styling", body="Important instructions. " * 100, **extra):
    chat.add_user_text("Use " + name)
    call = ToolCallPart("call_0", "load_skill", {"name": name})
    chat.accept_turn(TurnComplete(Message(ROLE_ASSISTANT, (call,)), STOP_TOOL_USE))
    content = json.dumps(dict(skill=name, title=name, instructions=body, **extra))
    chat.add_tool_results([ToolResultPart(call.call_id, content)])
    result = chat.messages[-1].parts[0]
    chat.accept_turn(TurnComplete(Message(ROLE_ASSISTANT, (TextPart("Done"),)), STOP_END))
    return result


def test_a_repeated_skill_keeps_new_tool_metadata_and_omits_only_identical_instructions():
    chat = session()
    first = load(chat, tools_now_offered=["set_layer_style"])
    second = load(chat, tools_now_offered=[])
    answer = json.loads(second.content)
    assert answer["already_loaded"] and answer["tools_now_offered"] == []
    assert "instructions" not in answer and len(second.content) < len(first.content) / 5
    assert len(loaded_skills(chat.messages)) == 1


def test_changed_instructions_and_different_skills_are_sent_in_full():
    chat = session()
    load(chat)
    assert "instructions" in json.loads(load(chat, body="A corrected procedure.").content)
    assert "instructions" in json.loads(load(chat, name="configuration").content)


def test_a_resumed_conversation_reuses_the_instructions_it_actually_kept():
    first = session()
    load(first)
    saved = parse(dump(first.messages))
    resumed = session()
    resumed.restore_history(saved.messages)
    assert json.loads(load(resumed).content)["already_loaded"]


def test_recent_skill_bodies_survive_trimming_and_a_discarded_body_is_loaded_again():
    chat = session()
    for rank in range(MAX_ACTIVE_SKILLS + 1):
        load(chat, name=f"skill-{rank}")
    chat.add_user_text("another task")
    chat.add_user_text("one more")
    chat._messages, count = trim_results(chat.messages)
    assert count == 1
    assert list(loaded_skills(chat.messages)) == [f"skill-{rank}" for rank in range(1, MAX_ACTIVE_SKILLS + 1)]
    assert "instructions" in json.loads(load(chat, name="skill-0").content)


def test_reusing_a_skill_makes_its_original_body_recent_again():
    chat = session()
    for rank in range(MAX_ACTIVE_SKILLS + 1):
        load(chat, name=f"skill-{rank}")
    assert json.loads(load(chat, name="skill-0").content)["already_loaded"]
    chat.add_user_text("another task")
    chat.add_user_text("one more")
    chat._messages, _count = trim_results(chat.messages)
    assert "skill-0" in loaded_skills(chat.messages)
    assert "skill-1" not in loaded_skills(chat.messages)


def test_compaction_names_the_skills_to_reload_and_does_not_claim_the_body_is_still_present():
    chat = session()
    load(chat)
    chat.add_user_text("a new task " + "x" * 3000)
    chat._messages, count = compact(chat.messages, 3200)
    assert count and "skills requested (reload if needed): styling" in chat.messages[0].text
    assert "instructions" in json.loads(load(chat).content)


def test_only_a_successful_matching_load_skill_result_counts_as_instructions():
    content = json.dumps({"skill": "styling", "instructions": "x" * 2000})
    for tool, arguments, error in (("list_layers", {}, False), ("load_skill", {"name": "different"}, False),
                                   ("load_skill", {"name": "styling"}, True)):
        messages = [Message(ROLE_ASSISTANT, (ToolCallPart("call_0", tool, arguments),)),
                    Message(ROLE_USER, (ToolResultPart("call_0", content, is_error=error),))]
        assert loaded_skills(messages) == {}


def test_a_maximum_length_skill_reaches_the_model_whole_even_with_json_escaping():
    body = '"' * MAX_BODY
    answer = {"skill": "styling", "title": "Styling", "instructions": body}
    executor = ToolExecutor([LOAD], {"load_skill": lambda args: answer})
    result = executor.execute(ToolCallPart("c", "load_skill", {"name": "styling"}))
    assert not result.is_error and json.loads(result.content)["instructions"] == body
    assert MAX_RESULT_CHARS < len(result.content) <= MAX_SKILL_RESULT_CHARS
