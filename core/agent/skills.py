# -*- coding: utf-8 -*-
"""Skills of the agent: instructions for one kind of task, loaded when the task comes (``load_skill``).

Plain Python. A skill keeps the system prompt short: its text reaches the model only in the conversations that need
it. Each skill is a folder ``skills/<name>/`` of the plugin (the standard is ``skills/README.md``):

- ``SKILL.md``: a header between ``---`` lines, then the instructions (Markdown, English, for the model). The header
  is the one of an Agent Skill (``name``, ``description``) with ``title`` and the fields of FilterMate under
  ``metadata``;
- ``evals.json``: its cases for ``scripts/agent_eval.py`` (three at least, one of them a trap).

The same text is served by the MCP server of the plugin as a prompt, and written as an Agent Skill for an application
that talks to that server (``skills/export/``, by ``scripts/export_agent_skills.py``). The header is read here, without
YAML: QGIS does not always ship it, and a skill header is a few plain lines.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"
EXPORT_DIR = "export"
NAME = re.compile(r"[a-z][a-z0-9-]{1,39}")
VERSION = re.compile(r"\d+\.\d+\.\d+")
AUDIENCES = ("chat", "mcp")
RISKS = ("read", "change")
TRUSTS = ("builtin", "user", "project")
TOP_KEYS = ("name", "title", "description")
META_KEYS = ("version", "plugin_min", "audience", "tools", "risk", "trust", "requires")
MAX_DESCRIPTION = 300
MAX_BODY = 9000  # characters, about 2,300 tokens: what one load_skill costs a request


class SkillError(ValueError):
    """A skill that does not follow the standard."""


@dataclass(frozen=True)
class Skill:
    name: str
    title: str
    # One line: when to load it (the tool description and the MCP prompt list show it).
    summary: str
    body: str
    version: int = 1
    plugin_min: str = "5.1.0"
    audience: Tuple[str, ...] = AUDIENCES
    tools: Tuple[str, ...] = ()
    risk: str = "read"
    trust: str = "builtin"
    # Tools that must be offered for the skill to be offered (run_pyqgis: the expert mode).
    requires: Tuple[str, ...] = ()
    folder: Optional[Path] = field(default=None, compare=False)


def _list(value: str) -> Tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def parse(text: str, folder: Optional[Path] = None, trust: Optional[str] = None) -> Skill:
    """A skill from the text of its ``SKILL.md``; ``SkillError`` saying what does not follow the standard."""
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        raise SkillError("SKILL.md starts with a header between --- lines")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise SkillError("the header of SKILL.md has no closing ---") from None
    top: Dict[str, str] = {}
    meta: Dict[str, str] = {}
    in_meta = False
    for number, line in enumerate(lines[1:end], 2):
        if not line.strip():
            continue
        indented = line.startswith("  ")
        key, colon, value = line.strip().partition(":")
        if not colon:
            raise SkillError(f"line {number} of the header is not 'key: value'")
        key, value = key.strip(), value.strip()
        if not indented:
            in_meta = key == "metadata"
            if in_meta:
                if value:
                    raise SkillError("metadata holds indented lines")
                continue
            if key not in TOP_KEYS:
                raise SkillError(f"unknown header key {key!r}")
            top[key] = value
        elif in_meta:
            if key not in META_KEYS:
                raise SkillError(f"unknown metadata key {key!r}")
            meta[key] = value
        else:
            raise SkillError(f"line {number} of the header is indented outside metadata")
    for key in TOP_KEYS:
        if not top.get(key):
            raise SkillError(f"the header has no {key}")
    name = top["name"]
    if not NAME.fullmatch(name):
        raise SkillError(f"name {name!r}: 2 to 40 lower case letters, digits or dashes, starting with a letter")
    if len(top["description"]) > MAX_DESCRIPTION:
        raise SkillError(f"description: {MAX_DESCRIPTION} characters at most")
    body = "\n".join(lines[end + 1:]).strip() + "\n"
    if len(body) > MAX_BODY:
        raise SkillError(f"the instructions are {len(body)} characters: {MAX_BODY} at most")
    try:
        version = int(meta.get("version", "1"))
    except ValueError:
        raise SkillError("version is a whole number") from None
    plugin_min = meta.get("plugin_min", "5.1.0")
    if not VERSION.fullmatch(plugin_min):
        raise SkillError("plugin_min is a version like 5.1.0")
    audience = _list(meta.get("audience", "chat, mcp"))
    if not audience or set(audience) - set(AUDIENCES):
        raise SkillError(f"audience is among {', '.join(AUDIENCES)}")
    risk = meta.get("risk", "read")
    if risk not in RISKS:
        raise SkillError(f"risk is {' or '.join(RISKS)}")
    declared = meta.get("trust", "builtin")
    if declared not in TRUSTS:
        raise SkillError(f"trust is among {', '.join(TRUSTS)}")
    # Where a skill comes from decides its trust, never its own header: a skill of a project cannot say it is built in.
    return Skill(name=name, title=top["title"], summary=top["description"], body=body, version=version,
                 plugin_min=plugin_min, audience=audience, tools=_list(meta.get("tools", "")), risk=risk,
                 trust=trust or declared, requires=_list(meta.get("requires", "")), folder=folder)


def read_folder(folder: Path, trust: str = "builtin") -> Dict[str, Skill]:
    """The skills of ``folder`` (one sub-folder each, holding SKILL.md), by name; ``export`` and ``_x`` left out."""
    found: Dict[str, Skill] = {}
    if not folder.is_dir():
        return found
    for sub in sorted(folder.iterdir()):
        if not sub.is_dir() or sub.name == EXPORT_DIR or sub.name.startswith(("_", ".")):
            continue
        source = sub / "SKILL.md"
        if not source.is_file():
            continue
        skill = parse(source.read_text(encoding="utf-8"), sub, trust)
        if skill.name != sub.name:
            raise SkillError(f"{sub.name}/SKILL.md is named {skill.name!r}: the folder and the name are the same")
        found[skill.name] = skill
    return found


SKILLS: Dict[str, Skill] = read_folder(SKILLS_DIR)


def for_audience(audience: str, offered: Optional[set] = None) -> List[Skill]:
    """The skills of ``audience`` (chat or mcp) whose required tools are all offered."""
    return [skill for skill in SKILLS.values() if audience in skill.audience
            and (offered is None or set(skill.requires) <= offered)]


NAMES: Tuple[str, ...] = tuple(skill.name for skill in for_audience("chat"))


def skill_list(offered: Optional[set] = None) -> str:
    """The skills, one per line, as the description of load_skill lists them."""
    return "; ".join(f"{skill.name}: {skill.summary}" for skill in for_audience("chat", offered))


def load(name: str) -> Dict[str, str]:
    """The answer of load_skill; ``KeyError`` for an unknown skill."""
    skill = SKILLS[name]
    if "chat" not in skill.audience:
        raise KeyError(name)
    return {"skill": skill.name, "title": skill.title, "instructions": skill.body}


MCP_PREAMBLE = ("Needs the MCP server of FilterMate: in QGIS, Agent settings (menu ⋯ of the AGENT panel), tab Other "
                "applications: turn it on and copy the configuration for this application. Its tools carry the names "
                "below.\n\n")


def agent_skill_file(skill: Skill) -> str:
    """``SKILL.md`` of an Agent Skill for an application connected to the MCP server of FilterMate."""
    description = (f"{skill.title} through the MCP server of the FilterMate QGIS plugin: {skill.summary}. Use when "
                   f"the user asks for it in QGIS with FilterMate.")
    return (f"---\nname: filtermate-{skill.name}\ndescription: {description}\n---\n\n"
            f"<!-- Generated from skills/{skill.name}/SKILL.md by scripts/export_agent_skills.py: do not edit by hand. -->"
            "\n\n" + MCP_PREAMBLE + skill.body)
