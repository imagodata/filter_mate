# -*- coding: utf-8 -*-
"""Families of tools (core/agent/families.py): the tools of a task offered once its skill is loaded."""
from core.agent import skills
from core.agent.families import ALWAYS, bringing, hidden_tools, unlocked
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


# --- 2026-11-13: a tool is held only for a skill the chat can load, and the answer names that skill --------------

def test_a_tool_named_by_a_skill_the_chat_cannot_load_stays_offered():
    """A skill of another application, or one whose required tool is not offered, cannot be loaded by the chat: the
    tools it named were hidden for good."""
    for_mcp = skills.Skill(name="served", title="S", summary="x", body="b", tools=("run_algorithm",), audience=("mcp",))
    expert = skills.Skill(name="expert", title="E", summary="x", body="b", tools=("create_layout",),
                          requires=("run_pyqgis",))
    assert hidden_tools(TOOLS, [for_mcp, expert]) == set()
    with_python = TOOLS + [tool for tool in chat_tools() if tool.name == "run_pyqgis"]
    assert hidden_tools(with_python, [for_mcp, expert]) == {"create_layout", "run_pyqgis"}


def test_every_hidden_tool_has_a_skill_the_chat_can_load():
    for tools in (TOOLS, list(chat_tools())):
        names = {tool.name for tool in tools}
        loadable = skills.for_audience("chat", names)
        for name in hidden_tools(tools, skills.SKILLS.values()):
            assert any(name in skill.tools or name in skill.requires for skill in loadable), name


def test_a_tool_held_names_the_skills_that_bring_it():
    """"call load_skill with the skill of that task first (its list says which)": the list does not say which tool
    comes with which skill, so the model guessed."""
    held = bringing(TOOLS, skills.SKILLS.values())
    assert set(held) == hidden_tools(TOOLS, skills.SKILLS.values())
    assert "cartography" in held["create_layout"] and "analysis" in held["run_algorithm"]
    executor = ToolExecutor([tool for tool in TOOLS if tool.name not in held], {})
    executor.hold(held)
    answer = executor.execute(ToolCallPart("1", "create_layout", {})).content
    assert '"cartography"' in answer and "its list says which" not in answer
    assert all(f'"{name}"' in answer for name in held["create_layout"])
