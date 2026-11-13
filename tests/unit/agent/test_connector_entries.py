# -*- coding: utf-8 -*-
"""The connectors as entries of load_skill: connector-<id>, listed after the skills, a name no skill can take."""
import pytest

from core.agent import skills
from core.agent.connectors import USER_ADDED, connector_entries
from core.agent.sources import BUILT_IN, Source
from core.agent.tool_catalog import skill_tool


def test_each_enabled_connector_is_an_entry_with_its_title_and_note():
    found = connector_entries(BUILT_IN)
    assert [entry.name for entry in found] == ["connector-" + source.id for source in BUILT_IN if source.is_connector]
    assert found[0].name == "connector-datagouv_mcp" and found[0].source.id == "datagouv_mcp"
    assert found[0].line == "data.gouv.fr (MCP): Datasets, data services and table queries"


@pytest.mark.parametrize("title, line", [
    ("Team; data", "Team, data: " + USER_ADDED),           # ";" parts the entries of the list
    ("Team​data", "mcp.example.org: " + USER_ADDED),  # a character that does not show: the host instead
    ("\U000e0041bc", "mcp.example.org: " + USER_ADDED),
    ("T" * 150, "T" * 100 + ": " + USER_ADDED),            # skills.MAX_TITLE
])
def test_a_connector_the_user_added_is_named_by_its_own_title_bounded(title, line):
    source = Source("mcp_mcp_example_org_mcp_abc123", title, "mcp", "https://mcp.example.org/mcp")
    assert connector_entries([source])[0].line == line


def test_load_skill_lists_the_connectors_after_the_skills():
    plain = skill_tool(None)
    tool = skill_tool(None, connectors=[("connector-a", "A: data")])
    assert tool.input_schema["properties"]["name"]["enum"] == \
        plain.input_schema["properties"]["name"]["enum"] + ["connector-a"]
    assert tool.description.startswith(plain.description[:-1]) and tool.description.endswith("connector-a: A: data.")
    assert "connector" not in plain.description  # unchanged without connectors: the bench and the cache see the same


def test_load_skill_for_the_connectors_alone():
    tool = skill_tool(None, connectors=[("connector-a", "A: data")], with_skills=False)
    assert tool.input_schema["properties"]["name"]["enum"] == ["connector-a"] and "configuration" not in tool.description


def test_a_skill_from_elsewhere_cannot_take_a_connector_name():
    skill = skills.Skill(name="connector-geocontext", title="T", summary="s", body="b\n", trust="user")
    try:
        left_out = skills.set_extra({skill.name: skill})
        assert skill.name not in skills.EXTRA and left_out == ["connector-geocontext: a name kept for the connectors"]
    finally:
        skills.set_extra({})


def test_no_skill_of_the_plugin_starts_like_a_connector():
    assert not [name for name in skills.SKILLS if name.startswith(skills.CONNECTOR_PREFIX)]
