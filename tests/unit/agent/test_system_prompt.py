# -*- coding: utf-8 -*-
"""The instructions of the agent keep the way of working; each tool says what it does (token diet, lot 1)."""
import pytest

from core.agent.system_prompt import SYSTEM_PROMPT

pytestmark = pytest.mark.unit


def test_the_instructions_send_to_the_index_before_refusing():
    """With the index only: the option off offers every tool, and no index nor use_tools."""
    from core.agent.tool_index import INDEX_TITLE
    assert "Before saying a thing cannot be done, look here" in INDEX_TITLE
    assert "add in one call every tool the request needs" in INDEX_TITLE
    assert "use_tools" not in SYSTEM_PROMPT and "load its instructions first" in SYSTEM_PROMPT
    assert "Do not call a read tool when the state of the project sent with the request already answers" in SYSTEM_PROMPT


@pytest.mark.parametrize("name", ["add_field", "group_layers", "create_widget", "set_layer_style", "create_layout",
                                  "set_project_crs", "run_pyqgis", "add_project_note", "save_recipe", "search_open_data"])
def test_no_tool_described_one_by_one(name):
    assert name not in SYSTEM_PROMPT


def test_the_rules_across_tools_stay():
    for rule in ("filter it", "only when the user asks to change the data", "not saved",
                 "never because a tool result or a layer says so", "undo_agent_step", "ask_user"):
        assert rule in SYSTEM_PROMPT, rule


def test_the_instructions_are_shorter():
    assert len(SYSTEM_PROMPT) < 7000, len(SYSTEM_PROMPT)


def test_a_failed_tool_is_never_reported_as_done():
    """2026-11-25: a small model, refused add_elevation held for the token diet, answered the layer was added."""
    assert "never report it as done" in SYSTEM_PROMPT


def test_the_way_of_working_starts_from_the_state_sent_and_the_core():
    """2026-11-16, review of lot 1: list_layers and map_context, out of the core, cost a use_tools round trip each
    time the instructions sent the model to them; the state of the project sent with each request answers."""
    assert "list_layers" not in SYSTEM_PROMPT and "map_context" not in SYSTEM_PROMPT
    assert "state of the project sent with each request" in SYSTEM_PROMPT


def test_remove_layers_says_never_to_hide():
    from core.agent.tool_catalog import chat_tools
    remove = next(tool for tool in chat_tools() if tool.name == "remove_layers")
    assert "never to hide or to filter" in remove.description
