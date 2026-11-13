# -*- coding: utf-8 -*-
"""Families of tools: the tools of one kind of task, offered to the chat once the agent loads its skill.

Plain Python. An option of the agent (on by default): fewer tools in each request. The
tools that filter and read (``FILTERING_TOOLS``) are always offered, and load_skill; the other tools a skill of the
plugin names come with that skill, when the chat can load it. A tool no such skill names stays offered, and a skill
from elsewhere unlocks nothing (its tools are ignored, ``skills.set_extra``). Other applications (MCP) always get
every tool.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Set

from .skills import Skill
from .tool_catalog import FILTERING_TOOLS, LOAD_SKILL, ToolSpec

ALWAYS = frozenset(FILTERING_TOOLS) | {LOAD_SKILL}


def bringing(tools: Sequence[ToolSpec], skills: Iterable[Skill]) -> Dict[str, List[str]]:
    """The tools offered later (``hidden_tools``), each with the names of the skills that bring it.

    Only a skill the chat can load counts: written for the chat, with the tools it requires offered. 2026-11-13: a
    tool named by a skill of another application alone, or by pyqgis without the expert mode, was hidden for good."""
    names = {tool.name for tool in tools}
    found: Dict[str, List[str]] = {}
    for skill in skills:
        if skill.trust == "builtin" and "chat" in skill.audience and set(skill.requires) <= names:
            for name in sorted((set(skill.tools) | set(skill.requires)) & (names - ALWAYS)):
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
