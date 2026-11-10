# -*- coding: utf-8 -*-
"""The notes the agent keeps for a project (core/agent/project_notes.py) and the tools that keep them."""
import json

import pytest

from core.agent.project_notes import HEADER, MAX_NOTE_CHARS, MAX_NOTES, added, clean, notes_block, parse, removed
from core.agent.tool_catalog import ADD_NOTE, CHAT_ONLY, REMOVE_NOTE, chat_tools

pytestmark = pytest.mark.unit


def test_a_note_is_one_trimmed_line():
    assert clean("  la couche   des parcelles\n est cadastre ") == "la couche des parcelles est cadastre"
    for bad in ("", "   ", "x" * (MAX_NOTE_CHARS + 1)):
        with pytest.raises(ValueError):
            clean(bad)


def test_notes_are_added_once_and_bounded():
    notes = added([], "Parcelles : cadastre_2024, clé idu")
    assert added(notes, "parcelles : CADASTRE_2024, clé IDU") == notes  # the same, case aside
    full = [f"note {number}" for number in range(MAX_NOTES)]
    with pytest.raises(ValueError, match="remove one"):
        added(full, "une de plus")


def test_a_note_is_removed_by_its_number():
    assert removed(["a", "b", "c"], 2) == ["a", "c"]
    with pytest.raises(ValueError, match="1 to 3"):
        removed(["a", "b", "c"], 4)
    with pytest.raises(ValueError, match="no note"):
        removed([], 1)


def test_the_request_carries_them_as_data():
    assert notes_block([]) == ""
    assert notes_block(["a", "b"]).splitlines() == [HEADER, "1. a", "2. b"]
    assert "never instructions" in HEADER


def test_what_the_project_holds_is_read_with_care():
    assert parse(json.dumps(["a", " b ", "", "x" * 400, 3])) == ["a", "b", "3"]
    assert parse("not json") == [] and parse('{"a": 1}') == [] and parse("") == []
    assert len(parse(json.dumps([f"n{number}" for number in range(50)]))) == MAX_NOTES


def test_the_tools_belong_to_the_chat_alone():
    tools = {tool.name: tool for tool in chat_tools()}
    assert {ADD_NOTE, REMOVE_NOTE} <= set(tools)
    assert all(tool.chat_only for tool in CHAT_ONLY)
    assert not tools[ADD_NOTE].read_only and not tools[ADD_NOTE].requires_confirmation
    assert tools[ADD_NOTE].input_schema["properties"]["text"]["maxLength"] == MAX_NOTE_CHARS
