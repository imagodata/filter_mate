#!/usr/bin/env python3
"""Regenerate ``skills/filtermate-<name>/SKILL.md`` from the skills of the agent (``core/agent/skills.py``).

These Agent Skills are for an application connected to the MCP server of FilterMate (Claude Code, Claude Desktop...):
the same instructions the chat loads with load_skill. ``--check`` fails when a file is out of date (for the tests).

    python scripts/export_agent_skills.py [--check]
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "skills"


def _module():
    """``core/agent/skills.py`` alone: ``core`` imports its domain package on import."""
    spec = importlib.util.spec_from_file_location("agent_skills", ROOT / "core" / "agent" / "skills.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look their module up there
    spec.loader.exec_module(module)
    return module


def main(argv) -> int:
    skills = _module()
    stale = []
    for skill in skills.SKILLS.values():
        path = OUTPUT / f"filtermate-{skill.name}" / "SKILL.md"
        text = skills.agent_skill_file(skill)
        if "--check" in argv:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(str(path.relative_to(ROOT)))
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"{path.relative_to(ROOT)}: written")
    if stale:
        print(f"out of date: {', '.join(stale)}: run python scripts/export_agent_skills.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
