# -*- coding: utf-8 -*-
"""Families of tools (core/agent/families.py): the tools of a task offered once its skill is loaded."""
from core.agent import skills
from core.agent.families import ALWAYS, hidden_tools, unlocked
from core.agent.messages import ToolCallPart
from core.agent.session import AgentSession
from core.agent.tool_catalog import FILTERING_TOOLS, LOAD_SKILL, ToolSpec, chat_tools
from core.agent.tool_executor import ToolExecutor

TOOLS = [tool for tool in chat_tools() if tool.name not in ("run_pyqgis", "view_map")]


def test_the_tools_that_filter_and_load_skill_are_always_offered():
    hidden = hidden_tools(TOOLS, skills.SKILLS.values())
    names = {tool.name for tool in TOOLS}
    assert not hidden & ALWAYS and LOAD_SKILL in names - hidden
    assert (FILTERING_TOOLS & names) <= names - hidden
    assert {"set_layer_style", "run_algorithm", "create_layout", "delete_features"} <= hidden
    # a tool no skill names stays offered
    assert all(any(name in skill.tools or name in skill.requires for skill in skills.SKILLS.values())
               for name in hidden)


def test_a_skill_brings_its_own_tools_only():
    hidden = hidden_tools(TOOLS, skills.SKILLS.values())
    cartography = unlocked(skills.SKILLS["cartography"], hidden)
    assert {"set_layer_style", "create_layout", "map_theme"} <= cartography
    assert "run_algorithm" not in cartography and cartography <= hidden


def test_a_skill_from_elsewhere_unlocks_nothing():
    skill = skills.Skill(name="team", title="Team", summary="x", body="b", tools=("run_algorithm",), trust="project")
    assert unlocked(skill, {"run_algorithm"}) == set()
    assert hidden_tools(TOOLS, [skill]) == set()


class _Provider:
    def build_request(self, system, messages, tools):
        return [tool.name for tool in tools]


def test_the_session_and_the_executor_take_more_tools_after_the_others():
    first, later = ToolSpec("a", "A"), ToolSpec("b", "B")
    session = AgentSession(_Provider(), [first], "system")
    session.offer([later, first])
    assert session.tool_names == ("a", "b") and session.next_request() == ["a", "b"]
    executor = ToolExecutor([first], {"a": lambda arguments: "A", "b": lambda arguments: "B"})
    assert executor.execute(ToolCallPart("1", "b", {})).is_error  # not offered yet
    executor.hold({"b"})
    held = executor.execute(ToolCallPart("2", "b", {}))
    assert held.is_error and "load_skill" in held.content
    executor.offer([later])
    assert executor.execute(ToolCallPart("3", "b", {})).content == '"B"'
