# -*- coding: utf-8 -*-
"""Families of tools: the tools of one kind of task, offered to the chat once the agent loads its skill.

Plain Python. An option of the agent (on by default): fewer tools in each request. The
tools that filter and read (``FILTERING_TOOLS``) are always offered, and load_skill; the other tools a skill of the
plugin names come with that skill, when the chat can load it (find_place is always offered too: finding a place
needs no instructions). A tool no such skill names stays offered, and a skill
from elsewhere unlocks nothing (its tools are ignored, ``skills.set_extra``). Other applications (MCP) always get
every tool.
"""
from __future__ import annotations

from typing import Any, Callable, Collection, Dict, Iterable, List, Mapping, Sequence, Set, Tuple

from .mcp_client import PREFIX as CONNECTOR_TOOL_PREFIX
from .skills import Skill
from .tool_catalog import ASK_USER, LOAD_SKILL, MAX_USE_TOOLS, USE_TOOLS, USE_TOOLS_TOOL, ToolSpec

# Token diet, lot 1 (docs/superpowers/specs/2026-11-16-agent-token-diet-design.md): offered at once, what the most
# common requests need in one turn, and the ways to the others. Measured on 2026-11-16 with
# scripts/agent_request_weight.py --conversation (reference: cost 291,616, largest request 80,432): the 9 tools of a
# filter on a field alone cost 484,919 (each request added a tool, and a tool added rewrites the whole cache of
# Anthropic); with the filter across layers, the statistics, the zoom, the visibility and the export, 211,986 and
# 54,761; the 25 tools offered before, 260,642. preview_filter and field_values stay: the instructions test an
# expression before apply_filter and read the exact spelling of a value.
CORE = frozenset({USE_TOOLS, LOAD_SKILL, ASK_USER, "describe_layer", "field_values", "preview_filter", "apply_filter",
                  "cross_filter", "clear_filters", "layer_statistics", "zoom_to", "set_layers_visibility",
                  "export_layers", "undo_agent_step"})
ALWAYS = CORE  # deprecated name


def bringing(tools: Sequence[ToolSpec], skills: Iterable[Skill]) -> Dict[str, List[str]]:
    """The tools offered later (``hidden_tools``), each with the names of the skills that bring it.

    Only a skill the chat can load counts: written for the chat, with the tools it requires offered. 2026-11-13: a
    tool named by a skill of another application alone, or by pyqgis without the expert mode, was hidden for good."""
    names = {tool.name for tool in tools}
    found: Dict[str, List[str]] = {}
    for skill in skills:
        if skill.trust == "builtin" and "chat" in skill.audience and set(skill.requires) <= names:
            for name in sorted((set(skill.tools) | set(skill.requires)) & (names - CORE)):
                found.setdefault(name, []).append(skill.name)
    return found


def hidden_tools(tools: Sequence[ToolSpec], skills: Iterable[Skill]) -> Set[str]:
    """The tools offered later: named by a skill of the plugin the chat can load, offered now, and not always
    offered."""
    return set(bringing(tools, skills))


def unlocked(skill: Skill, hidden: Set[str]) -> Set[str]:
    """The tools ``skill`` brings, among those still hidden; none from a skill from elsewhere."""
    if skill.trust != "builtin":
        return set()
    return (set(skill.tools) | set(skill.requires)) & hidden


def split_tools(tools: Sequence[ToolSpec]) -> Tuple[List[ToolSpec], List[ToolSpec]]:
    """``(offered at once, available)``: the core of ``tools`` and use_tools, then the others, in their order. A tool
    of a connector (mcp_...) is in neither: it comes with its entry of load_skill."""
    start = [tool for tool in tools if tool.name in CORE and tool.name != USE_TOOLS]
    available = [tool for tool in tools if tool.name not in CORE and not tool.name.startswith(CONNECTOR_TOOL_PREFIX)]
    return start + [USE_TOOLS_TOOL], available


SKILL_NOTE = ("A tool of a new kind of task comes with instructions: load_skill with the skill named for it says how to "
              "use it and what never to do with it.")
NOT_HERE = ("not available in this conversation (its source is not ticked, or a setting or the expert mode is off): "
            "say so to the user, who changes it in the agent settings")


def use_tools_handler(available: Dict[str, ToolSpec], offer: Callable[[List[ToolSpec]], Any], known: Collection[str],
                      refused: Callable[[str], str] = lambda name: "", skills: Mapping[str, Sequence[str]] = {},
                      everything: Collection[str] = ()) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """The handler of use_tools: the tools named leave ``available`` and are ``offer``-ed, in the order asked, all or
    none. ``known``: every tool of the conversation (a name offered already is said so); ``refused``: why a tool may
    not be added now (a rule of the user, read at each call), "" when it may; ``skills``: the skills that bring each
    tool, named in the answer (their rules are not in the index); ``everything``: every tool of the chat, to say why
    one is not in this conversation."""
    from .tool_executor import ToolFailure

    def missing(name: str) -> str:
        if name.startswith(CONNECTOR_TOOL_PREFIX):
            return f"{name}: a tool of a connector: load its entry with load_skill"
        return f"{name}: {NOT_HERE}" if name in everything else f"{name}: no such tool"

    def run(arguments: Dict[str, Any]) -> Dict[str, Any]:
        names = list(dict.fromkeys(str(name) for name in arguments.get("names") or ()))[:MAX_USE_TOOLS]
        problems = [f"{name}: {refused(name)}" for name in names if refused(name)]
        if problems:
            raise ToolFailure("Not added: " + "; ".join(problems))
        unknown = [missing(name) for name in names if name not in available and name not in known]
        if unknown:
            raise ToolFailure("Not added: " + "; ".join(unknown) + ". Use the names of the index at the end of the "
                              "instructions.")
        added = [name for name in names if name in available]
        if added:
            offer([available[name] for name in added])  # raises when it cannot: nothing is marked added then
            for name in added:
                available.pop(name)
        answer: Dict[str, Any] = {"added": added, "already": [name for name in names if name not in added]}
        brought = {name: list(skills[name]) for name in added if skills.get(name)}
        if brought:
            answer.update(skills=brought, note=SKILL_NOTE)
        return answer
    return run
