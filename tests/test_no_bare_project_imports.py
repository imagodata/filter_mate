# -*- coding: utf-8 -*-
"""
The plugin root is not on sys.path in QGIS: ``from ui.config import ...`` raises there, whereas the
unit tests have the root on their path and never see it. Such imports made several features fail
or do nothing in QGIS only (the UI_PROFILE setting, a custom expression, the debounce setting...).

A plugin file imports its own modules relatively. An absolute form is accepted only as the fallback
of a relative import (in an ``except`` handler), for files the tests load outside the package.
"""
import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
# processing/ is left out: `processing` at runtime is the QGIS Processing plugin.
PROJECT_PACKAGES = ("adapters", "config", "core", "extensions", "infrastructure", "ui")
SCANNED = PROJECT_PACKAGES + ("processing",)

# Known, inert: each one fails in QGIS and falls back on something that works.
KNOWN = {
    # Falls back on the legacy names just below.
    ("ui/elements/__init__.py", "ui.elements"),
}


def _plugin_files():
    for package in SCANNED:
        yield from (ROOT / package).rglob("*.py")
    yield from ROOT.glob("*.py")


def _is_fallback(node, parents):
    while node in parents:
        node = parents[node]
        if isinstance(node, ast.ExceptHandler):
            return True
        if isinstance(node, ast.If) and "TYPE_CHECKING" in ast.unparse(node.test):
            return True
    return False


def bare_project_imports(source):
    """Modules imported absolutely from the project, outside a fallback."""
    tree = ast.parse(source)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 0:
            modules = [node.module or ""]
        elif isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        else:
            continue
        for module in modules:
            if module.split(".")[0] in PROJECT_PACKAGES and not _is_fallback(node, parents):
                found.append(module)
    return found


def test_the_plugin_imports_its_own_modules_relatively():
    offenders = []
    for path in _plugin_files():
        relative = path.relative_to(ROOT).as_posix()
        for module in bare_project_imports(path.read_text(encoding="utf-8")):
            if (relative, module) not in KNOWN:
                offenders.append(f"{relative}: {module}")
    assert not offenders, "Fails in QGIS, the plugin root is not on sys.path:\n" + "\n".join(offenders)


def test_each_known_exception_still_exists():
    for relative, module in KNOWN:
        assert module in bare_project_imports((ROOT / relative).read_text(encoding="utf-8")), (relative, module)


@pytest.mark.parametrize("source, expected", [
    ("from ui.config import UIConfig", ["ui.config"]),
    ("import core.tasks", ["core.tasks"]),
    ("def f():\n    from config.config import x", ["config.config"]),
    ("try:\n    from ui.config import x\nexcept ImportError:\n    x = None", ["ui.config"]),
    ("try:\n    from ..config import x\nexcept ImportError:\n    from ui.config import x", []),
    ("from ..config import x", []),
    ("from qgis.core import QgsProject", []),
    ("from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from core.tasks import T", []),
])
def test_the_rule(source, expected):
    assert bare_project_imports(source) == expected
