# -*- coding: utf-8 -*-
"""The skills of the sessions that develop FilterMate (.claude/skills/<name>/SKILL.md): a header Claude Code reads."""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SKILLS = sorted((ROOT / ".claude" / "skills").glob("*/SKILL.md"))


def test_there_are_development_skills():
    assert {path.parent.name for path in SKILLS} >= {"qgis-headless-bench", "i18n-pipeline", "pyqgis-qt-pitfalls"}


@pytest.mark.parametrize("path", SKILLS, ids=lambda path: path.parent.name)
def test_each_has_a_name_and_a_description(path):
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    header = text.split("---", 2)[1]
    name = re.search(r"^name: (.+)$", header, re.M)
    description = re.search(r"^description: (.+)$", header, re.M)
    assert name and name.group(1).strip() == path.parent.name
    assert description and 20 <= len(description.group(1)) <= 1024
    # every script or file of the repository the skill names exists
    for relative in re.findall(r"`((?:scripts|tests|ui|core|adapters|i18n)/[\w/.-]+\.(?:py|sh|ts))`", text):
        assert (ROOT / relative).exists(), relative
