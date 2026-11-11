# -*- coding: utf-8 -*-
"""The expert mode: a tool of the chat alone, always confirmed, and the one place of the plugin that runs code."""
import re
from pathlib import Path

import pytest

from core.agent.tool_catalog import RUN_PYTHON, chat_tools

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
SKIPPED = {"tests", ".git", ".claude", "website", "scripts", "docs", "free-quota-proxy", "_bmad", "_bmad-output", "dist",
           "build", "node_modules", "__pycache__", "i18n", "resources"}


def test_run_pyqgis_is_confirmed_and_never_served_to_another_application():
    tool = {item.name: item for item in chat_tools()}[RUN_PYTHON]
    assert tool.chat_only and tool.destructive and tool.requires_confirmation and not tool.read_only
    assert tool.input_schema["required"] == ["purpose", "code"]


def test_the_expert_mode_is_the_one_place_that_runs_code():
    found = []
    for path in ROOT.rglob("*.py"):
        if SKIPPED & set(path.relative_to(ROOT).parts):
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            code = line.split("#", 1)[0]
            if re.search(r"(?<![\w.])(exec|eval)\(", code) and not re.match(r"\s*def ", code):
                found.append(f"{path.relative_to(ROOT)}:{number}")
    assert len(found) == 1 and found[0].startswith("adapters/agent/expert_python.py:"), found
