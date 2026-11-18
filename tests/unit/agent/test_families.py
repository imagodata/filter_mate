# -*- coding: utf-8 -*-
"""Families of tools (core/agent/families.py): the core offered at once, the others added by use_tools or a skill."""
import pytest

from core.agent import skills
from core.agent.families import CORE, bringing, hidden_tools, split_tools, unlocked, use_tools_handler
from core.agent.messages import ToolCallPart
from core.agent.session import AgentSession
from core.agent.tool_catalog import LOAD_SKILL, USE_TOOLS, USE_TOOLS_TOOL, ToolSpec, chat_tools
from core.agent.tool_executor import ToolExecutor, ToolFailure

TOOLS = [tool for tool in chat_tools() if tool.name not in ("run_pyqgis", "view_map")]


def test_the_core_is_never_held():
    hidden = hidden_tools(TOOLS, skills.SKILLS.values())
    assert not hidden & CORE and {LOAD_SKILL, USE_TOOLS, "apply_filter", "preview_filter"} <= CORE
    assert {"set_layer_style", "run_algorithm", "create_layout", "delete_features"} <= hidden


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
    assert held.is_error and 'call use_tools with "b" first' in held.content
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
    assert 'use_tools with "create_layout"' in answer and 'load_skill with "cartography"' in answer
    assert all(f'"{name}"' in answer for name in held["create_layout"])


# --- token diet, lot 1: only the tools a request needs ------------------------------------------------------------

def _tool(name):
    return ToolSpec(name, f"{name} tool.", summary=f"Do {name}")


def test_split_keeps_the_core_and_the_order():
    tools = [_tool("list_layers"), _tool("apply_filter"), _tool("group_layers"), _tool("describe_layer"), _tool("mcp_x")]
    start, available = split_tools(tools)
    assert [tool.name for tool in start] == ["apply_filter", "describe_layer", USE_TOOLS]
    assert [tool.name for tool in available] == ["list_layers", "group_layers"]
    assert start[-1] is USE_TOOLS_TOOL and USE_TOOLS_TOOL.read_only


def _handler(refused=lambda name: ""):
    offered = []
    available = {name: _tool(name) for name in ("a", "b", "c")}
    run = use_tools_handler(available, offered.extend, known={"a", "b", "c", "apply_filter"}, refused=refused)
    return run, offered, available


def test_use_tools_adds_in_the_order_asked():
    run, offered, available = _handler()
    assert run({"names": ["b", "a"]}) == {"added": ["b", "a"], "already": []}
    assert [tool.name for tool in offered] == ["b", "a"] and set(available) == {"c"}


def test_use_tools_ignores_what_is_already_offered():
    run, offered, _ = _handler()
    run({"names": ["a"]})
    assert run({"names": ["a", "apply_filter", "c"]}) == {"added": ["c"], "already": ["a", "apply_filter"]}


def test_use_tools_refuses_an_unknown_name():
    run, offered, _ = _handler()
    with pytest.raises(ToolFailure, match="nope"):
        run({"names": ["a", "nope"]})
    assert offered == []


def test_use_tools_refuses_a_tool_turned_off():
    run, offered, _ = _handler(refused=lambda name: "turned off by the user" if name == "b" else "")
    with pytest.raises(ToolFailure, match="b: turned off by the user"):
        run({"names": ["a", "b"]})
    assert offered == []


def test_a_held_tool_says_use_tools():
    executor = ToolExecutor([], {})
    executor.hold({"zoom_to": []})
    answer = executor.execute(ToolCallPart("1", "zoom_to", {})).content
    assert answer.startswith('zoom_to is not offered yet: call use_tools with "zoom_to" first')


def test_a_tool_turned_off_is_said_so_even_out_of_the_index():
    """A tool turned off in the Tools tab is not in the conversation at all: use_tools says why, not "No tool"."""
    run, offered, _ = _handler(refused=lambda name: "turned off by the user" if name == "zoom_to" else "")
    with pytest.raises(ToolFailure, match="zoom_to: turned off by the user"):
        run({"names": ["zoom_to"]})


# --- 2026-11-16, review of lot 1 ------------------------------------------------------------------------------------

def test_use_tools_names_the_skill_that_says_how_to_use_a_tool():
    """A tool added from the index skips its skill; the answer names it, so its rules (never remove a layer to hide
    it...) stay within reach."""
    available = {name: _tool(name) for name in ("remove_layers", "zoom")}
    run = use_tools_handler(available, lambda tools: None, known=set(available), skills={"remove_layers": ["open-data"]})
    answer = run({"names": ["remove_layers", "zoom"]})
    assert answer["skills"] == {"remove_layers": ["open-data"]} and "load_skill" in answer["note"]
    assert "skills" not in run({"names": ["zoom"]})


def test_a_tool_out_of_this_conversation_says_why():
    run = use_tools_handler({}, lambda tools: None, known=set(), everything={"view_map"})
    with pytest.raises(ToolFailure, match="view_map: not available in this conversation"):
        run({"names": ["view_map"]})
    with pytest.raises(ToolFailure, match="mcp_search: a tool of a connector: load its entry with load_skill"):
        run({"names": ["mcp_search"]})


def test_nothing_is_marked_added_when_the_offer_fails():
    available = {"a": _tool("a")}

    def offer(tools):
        raise ToolFailure("The conversation is over.")
    run = use_tools_handler(available, offer, known={"a"})
    with pytest.raises(ToolFailure, match="over"):
        run({"names": ["a"]})
    assert "a" in available


def _named(text):
    import re
    return {tool.name for tool in chat_tools() if re.search(r"\b%s\b" % re.escape(tool.name), text)}


def test_the_state_header_names_core_tools_only():
    """Audit 2026-11-18: it named list_layers and filter_state, held until use_tools adds them: a direct call by
    the model cost a round trip (the HELD answer)."""
    from core.agent.project_summary import HEADER
    assert _named(HEADER) and _named(HEADER) <= CORE


def test_the_settings_link_of_the_missing_sources_says_how_to_get_it():
    from core.agent.chat_setup import chat_instructions
    index = [tool for tool in chat_tools() if tool.name not in CORE][:5] + [
        tool for tool in chat_tools() if tool.name == "show_settings_link"]
    with_index, without = chat_instructions([], available=index), chat_instructions([])
    assert "show_settings_link" not in CORE
    # the mention follows the tool, so that "it" cannot be read as the sources
    assert "call show_settings_link (added by use_tools) with target sources;" in with_index
    assert "use_tools" not in without  # the families off: every tool is offered, and use_tools is not
    assert "show_settings_link with target sources;" in without


def test_a_settings_link_turned_off_is_not_sent_for():
    """Review 2026-11-18: use_tools cannot add a tool set to "never": the hint was false, and so was the link."""
    from core.agent.chat_setup import MISSING_TITLE, chat_instructions
    index = [tool for tool in chat_tools() if tool.name == "show_settings_link"]

    def note(text):
        return text.split(MISSING_TITLE)[1]  # the index above lists the tool: only the note is read
    for text in (chat_instructions([], available=index, settings_link=False),
                 chat_instructions([], settings_link=False)):
        assert "show_settings_link" not in note(text) and "never guess coordinates" in note(text)
        assert "ticked in the Sources tab of the settings of the agent;" in note(text)
    # a tool the conversation does not have is no more offered by the note
    assert "show_settings_link" not in note(chat_instructions([], offered=["describe_layer"], available=index))
