import re

import pytest

from core.agent.json_schema import validate
from core.agent.tool_catalog import ADD_NOTE, REMOVE_NOTE, chat_tools


@pytest.mark.parametrize("memory", ["m1", "m999999999999", "m1000000000000"])
def test_cross_project_memory_can_be_addressed_without_a_project_note_number(memory):
    tool = next(tool for tool in chat_tools() if tool.name == REMOVE_NOTE)
    assert not validate({"memory": memory}, tool.input_schema)


@pytest.mark.parametrize("memory", ["m0", "m01", "M1", "m-1", "m10000000000000", "m1\n"])
def test_noncanonical_memory_ids_do_not_match_the_declared_pattern(memory):
    tool = next(tool for tool in chat_tools() if tool.name == REMOVE_NOTE)
    assert re.fullmatch(tool.input_schema["properties"]["memory"]["pattern"], memory) is None


@pytest.mark.parametrize("scope", ["project", "user", "source"])
def test_notes_accept_the_scope_requested_by_the_user(scope):
    tool = next(tool for tool in chat_tools() if tool.name == ADD_NOTE)
    assert not validate({"text": "A user explanation", "scope": scope, "layer": "Buildings"}, tool.input_schema)
    assert validate({"text": "A user explanation", "scope": "connector"}, tool.input_schema)
