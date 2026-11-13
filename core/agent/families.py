# -*- coding: utf-8 -*-
"""Families of tools: the tools of one kind of task, offered to the chat once the agent loads its skill.

Plain Python. An option of the agent (on by default): fewer tools in each request. The
tools that filter and read (``FILTERING_TOOLS``) are always offered, and load_skill; the other tools a skill of the
plugin names come with that skill. A tool no skill names stays offered, and a skill from elsewhere unlocks nothing
(its tools are ignored, ``skills.set_extra``). Other applications (MCP) always get every tool.
"""
from __future__ import annotations

from typing import Iterable, Sequence, Set

from .skills import Skill
from .tool_catalog import FILTERING_TOOLS, LOAD_SKILL, ToolSpec

ALWAYS = frozenset(FILTERING_TOOLS) | {LOAD_SKILL}


def hidden_tools(tools: Sequence[ToolSpec], skills: Iterable[Skill]) -> Set[str]:
    """The tools offered later: named by a skill of the plugin, offered now, and not always offered."""
    names = {tool.name for tool in tools}
    owned: Set[str] = set()
    for skill in skills:
        if skill.trust == "builtin":
            owned |= set(skill.tools) | set(skill.requires)
    return (owned & names) - ALWAYS


def unlocked(skill: Skill, hidden: Set[str]) -> Set[str]:
    """The tools ``skill`` brings, among those still hidden; none from a skill from elsewhere."""
    if skill.trust != "builtin":
        return set()
    return (set(skill.tools) | set(skill.requires)) & hidden
