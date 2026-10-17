# -*- coding: utf-8 -*-
"""
Every text-mode ``open()`` in the plugin names its encoding.

Without it Python uses the platform one (cp1252 on Windows): the Configuration
tab "revert" read config.json that way, while the plugin writes UTF-8, and a
non-ASCII setting (a language name, a path) came back garbled or raised.
"""
import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]
_SKIPPED_DIRS = {"tests", "scripts", "_bmad", "_bmad-output", "website", "docs", "knowledge", "dist", "build",
                 ".git", ".claude", ".serena", "__pycache__", "node_modules"}
# lock files of the coverage cache: opened only to hold an OS lock, never read as text
_ALLOWED = {("adapters/qgis/coverage_layers/cache.py", 206), ("adapters/qgis/coverage_layers/cache.py", 244)}


def _python_files():
    for path in _ROOT.rglob("*.py"):
        if not set(path.relative_to(_ROOT).parts[:-1]) & _SKIPPED_DIRS:
            yield path


def _offenders():
    found = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "open"):
                continue
            mode = node.args[1].value if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else "r"
            if "b" in str(mode) or any(k.arg == "encoding" for k in node.keywords) or any(
                    k.arg == "mode" and "b" in str(getattr(k.value, "value", "")) for k in node.keywords):
                continue
            rel = path.relative_to(_ROOT).as_posix()
            if (rel, node.lineno) not in _ALLOWED:
                found.append(f"{rel}:{node.lineno}")
    return found


def test_every_text_open_names_its_encoding():
    assert _offenders() == []
