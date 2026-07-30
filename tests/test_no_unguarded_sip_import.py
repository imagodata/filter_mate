# -*- coding: utf-8 -*-
"""
Regression test for GitHub issue #47.

`import sip` at module top level (outside a try/except) crashes on
environments where the standalone `sip` package isn't importable even
though a PyQt-bundled `sip` (e.g. PyQt6.sip) is available -- this is
exactly what broke dockable panel creation on QGIS 4.0.1 / Windows.

Every `import sip` in the plugin source must be guarded by a try/except
(or be a local import already inside a guarded context).
"""
import ast
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

EXCLUDED_DIRS = {
    "tests", "video_toolkit", "video_automation", ".git", "__pycache__",
    "_bmad", "_bmad-output", "website", "docs", "knowledge", "dist", "build",
}


def _plugin_python_files():
    for path in PLUGIN_ROOT.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in path.relative_to(PLUGIN_ROOT).parts):
            continue
        yield path


def _find_unguarded_sip_imports(tree, module):
    """Return line numbers of `import sip` statements not inside a Try node."""
    guarded_lines = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Try):
            for child in ast.walk(node):
                if isinstance(child, ast.Import):
                    for alias in child.names:
                        if alias.name == "sip":
                            guarded_lines.add(child.lineno)

    offenders = []
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "sip" and node.lineno not in guarded_lines:
                    offenders.append(node.lineno)
    return offenders


@pytest.mark.unit
def test_no_unguarded_top_level_sip_import():
    """`import sip` must always be wrapped in a try/except (see issue #47)."""
    violations = []
    for path in _plugin_python_files():
        source = path.read_text(encoding="utf-8")
        if "import sip" not in source:
            continue
        tree = ast.parse(source, filename=str(path))
        for lineno in _find_unguarded_sip_imports(tree, tree):
            violations.append(f"{path.relative_to(PLUGIN_ROOT)}:{lineno}")

    assert not violations, (
        "Unguarded `import sip` found (crashes when only PyQt6.sip is "
        "available, e.g. QGIS 4.x on Windows -- see issue #47): "
        + ", ".join(violations)
    )
