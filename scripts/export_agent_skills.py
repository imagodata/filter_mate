#!/usr/bin/env python3
"""Regenerate ``skills/export/filtermate-<name>/SKILL.md`` from the skills of the agent (``skills/<name>/``).

These Agent Skills are for an application connected to the MCP server of FilterMate (Claude Code, Claude Desktop...):
the same instructions the chat loads with load_skill. ``--check`` fails when a file is out of date, or when a folder
``filtermate-<name>`` is left by a skill renamed, removed or of the chat alone (for the tests); without it, such a
folder is removed.

    python scripts/export_agent_skills.py [--check]
"""
import importlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "skills" / "export"


def _module():
    """Import the plain-Python agent package without core/__init__.py, which requires QGIS."""
    sys.path.insert(0, str(ROOT / 'core'))
    return importlib.import_module('agent.skills')


def main(argv) -> int:
    skills = _module()
    stale = []
    for skill in skills.for_audience("mcp"):
        path = OUTPUT / f"filtermate-{skill.name}" / "SKILL.md"
        text = skills.agent_skill_file(skill)
        if "--check" in argv:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(str(path.relative_to(ROOT)))
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"{path.relative_to(ROOT)}: written")
    exported = {f"filtermate-{skill.name}" for skill in skills.for_audience("mcp")}
    for folder in sorted(OUTPUT.glob("filtermate-*")):
        if folder.name in exported or not folder.is_dir():
            continue
        if "--check" in argv:
            stale.append(f"{folder.relative_to(ROOT)} (no skill of that name for MCP)")
            continue
        shutil.rmtree(folder)
        print(f"{folder.relative_to(ROOT)}: removed")
    if stale:
        print(f"out of date: {', '.join(stale)}: run python scripts/export_agent_skills.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
