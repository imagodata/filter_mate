# -*- coding: utf-8 -*-
"""
2026-09-14: core/tasks/cleanup_handler.py called BackendServices.execute_commands,
which does not exist (the facade method is execute_postgresql_commands). Every
filter that took the PostgreSQL materialized-view path (source selection of
100 000 features or more) failed at Step 9 on its first attempt with
"'BackendServices' object has no attribute 'execute_commands'". This test
checks statically that every ``self._backend_services.<name>(`` call in the
task handlers names a method of the facade.
"""
import ast
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
FACADE = PLUGIN_ROOT / "core" / "ports" / "backend_services.py"
CALLERS = sorted((PLUGIN_ROOT / "core" / "tasks").rglob("*.py"))


def _facade_methods():
    tree = ast.parse(FACADE.read_text(encoding="utf-8"))
    names = set()
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "BackendServices"):
        for node in cls.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names.add(node.name)
    assert names, "BackendServices class not found"
    return names


def _facade_calls(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute):
            if node.value.attr == "_backend_services":
                yield node.lineno, node.attr


@pytest.mark.unit
def test_every_backend_services_call_exists_on_the_facade():
    methods = _facade_methods()
    offenders = []
    for path in CALLERS:
        for lineno, name in _facade_calls(path):
            if name not in methods:
                offenders.append(f"{path.relative_to(PLUGIN_ROOT)}:{lineno} _backend_services.{name}")
    assert offenders == [], "Unknown BackendServices method(s):\n" + "\n".join(offenders)
