# -*- coding: utf-8 -*-
"""The standard of the skills of the agent (skills/README.md), applied to every skill shipped with the plugin."""
import json
import re
from pathlib import Path

import pytest

from core.agent import skills as skills_module
from core.agent.settings_reference import read_settings
from core.agent.skills import SKILLS, SkillError, parse, read_folder
from core.agent.tool_catalog import MCP_ONLY, chat_tools

ROOT = Path(__file__).resolve().parents[3]
CHAT_TOOLS = {tool.name for tool in chat_tools()}
MCP_TOOLS = {tool.name for tool in chat_tools() if not tool.chat_only and not tool.manages_history} \
    | {tool.name for tool in MCP_ONLY}
# A sentence naming one of these must say never (or not, no).
_BYPASS = re.compile(r"get around|bypass|work around|without (asking|confirm)|skip (the )?(question|confirmation)|"
                     r"ignore (the|a|any) (refusal|level|confirmation|protection)", re.I)
_NEGATION = re.compile(r"\b(never|not|no|don't|do not)\b", re.I)


def _version(text):
    return tuple(int(part) for part in text.split("."))


def _plugin_version():
    for line in (ROOT / "metadata.txt").read_text(encoding="utf-8").splitlines():
        if line.startswith("version="):
            return _version(line.split("=", 1)[1].strip())
    raise AssertionError("no version in metadata.txt")


def test_there_are_skills_and_they_live_in_their_folder():
    assert SKILLS and set(SKILLS) == {path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")
                                      if path.parent.name != "export"}


@pytest.mark.parametrize("name", sorted(SKILLS))
def test_every_skill_follows_the_standard(name):
    skill = SKILLS[name]
    assert skill.trust == "builtin" and skill.folder.name == name
    assert _version(skill.plugin_min) <= _plugin_version()
    allowed = (CHAT_TOOLS if "chat" in skill.audience else set()) | (MCP_TOOLS if "mcp" in skill.audience else set())
    assert set(skill.tools) <= allowed, set(skill.tools) - allowed
    assert set(skill.requires) <= CHAT_TOOLS
    # every tool the text names in backticks or as a call is declared, every setting path exists
    named = {word for word in re.findall(r"\b([a-z]+(?:_[a-z]+)+)\b", skill.body) if word in CHAT_TOOLS | MCP_TOOLS}
    assert named <= set(skill.tools) | set(skill.requires) | {"load_skill", "run_pyqgis", "undo_agent_step"}, \
        named - set(skill.tools)
    paths = {row.path for row in read_settings(None)}
    sections = {path.rsplit(".", 1)[0] for path in paths} | {path.rsplit(".", 2)[0] for path in paths}
    for setting in re.findall(r"APP(?:\.[A-Za-z_]+)+", skill.body):
        assert setting in paths or setting in sections, setting
    for sentence in re.split(r"(?<=[.!?:;])\s+|\n", skill.body):
        if _BYPASS.search(sentence):
            assert _NEGATION.search(sentence), sentence


@pytest.mark.parametrize("name", sorted(SKILLS))
def test_every_skill_has_its_cases_one_of_them_a_trap(name):
    cases = json.loads((ROOT / "skills" / name / "evals.json").read_text(encoding="utf-8"))["cases"]
    assert len(cases) >= 3
    assert any(case.get("trap") and case.get("forbid") for case in cases)
    shared = json.loads((ROOT / "scripts" / "agent_eval_cases.json").read_text(encoding="utf-8"))["cases"]
    ids = [case["id"] for case in shared] + [case["id"] for skill in SKILLS for case in json.loads(
        (ROOT / "skills" / skill / "evals.json").read_text(encoding="utf-8"))["cases"]]
    assert len(ids) == len(set(ids))


GOOD = """---
name: sample
title: A sample
description: when to load it
metadata:
  version: 2
  plugin_min: 5.1.0
  audience: chat
  tools: list_layers, describe_layer
  risk: read
  trust: builtin
---

# Sample

Read the layers.
"""


def test_parse_reads_the_header_and_the_body():
    skill = parse(GOOD)
    assert (skill.name, skill.version, skill.audience, skill.tools) == ("sample", 2, ("chat",),
                                                                        ("list_layers", "describe_layer"))
    assert skill.body.startswith("# Sample")


@pytest.mark.parametrize("change, message", [
    (lambda text: text.replace("---\n", "", 1), "starts with a header"),
    (lambda text: text.replace("name: sample", "name: Sample!"), "name"),
    (lambda text: text.replace("title: A sample\n", ""), "has no title"),
    (lambda text: text.replace("  risk: read", "  risk: delete"), "risk"),
    (lambda text: text.replace("  audience: chat", "  audience: everyone"), "audience"),
    (lambda text: text.replace("  version: 2", "  version: two"), "version"),
    (lambda text: text.replace("  trust: builtin", "  shell: rm -rf"), "unknown metadata key"),
    (lambda text: text.replace("title: A sample", "title: A sample\nallowed-tools: everything"), "unknown header key"),
    (lambda text: text + "x" * skills_module.MAX_BODY, "at most"),
])
def test_parse_refuses_what_does_not_follow_the_standard(change, message):
    with pytest.raises(SkillError, match=message):
        parse(change(GOOD))


def test_trust_comes_from_where_the_skill_comes_from(tmp_path):
    folder = tmp_path / "sample"
    folder.mkdir()
    (folder / "SKILL.md").write_text(GOOD, encoding="utf-8")
    assert read_folder(tmp_path, trust="project")["sample"].trust == "project"  # its header says builtin
    (tmp_path / "other").mkdir()
    (tmp_path / "other" / "SKILL.md").write_text(GOOD, encoding="utf-8")  # named sample in a folder named other
    with pytest.raises(SkillError, match="the folder and the name"):
        read_folder(tmp_path)
