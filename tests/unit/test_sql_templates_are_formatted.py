# -*- coding: utf-8 -*-
"""Guard against SQL/text templates that lost their ``f`` prefix.

The plugin-checker clean-up of 2026-02-10 stripped the ``f`` prefix of dozens
of triple-quoted SQL templates: the placeholders were then sent verbatim to the
database (``CREATE MATERIALIZED VIEW {full_name} AS`` → ``syntax error at or
near "{"``) and the fast paths silently fell back to slow ones. This test scans
the package for string literals holding ``{identifier}`` placeholders that are
neither f-strings nor ``.format()``-ed.
"""
from __future__ import annotations

import ast
import os
import re
from typing import Iterator, Tuple

PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
SKIP_DIRS = {"tests", "_bmad", "_bmad-output", "dist", "knowledge", ".claude", "docs",
             "__pycache__", "scripts", "filtermate_api", ".git", "venv", ".venv"}
PLACEHOLDER = re.compile(r"\{[a-z_][a-z_0-9]*(\.[a-z_][a-z_0-9]*)*\}")

# Templates formatted somewhere else than in their own function/statement.
ALLOWLIST = {
    ("adapters/backends/postgresql/cleanup.py", "SESSION_VIEW_PATTERN"),
}
# QSS templates use their own ``{token}`` substitution tables.
SKIP_PREFIXES = ("ui/styles/", "ui/layout/")


def _python_files() -> Iterator[str]:
    for dirpath, dirnames, filenames in os.walk(PROJECT_ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def _add_parents(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child._parent = node  # type: ignore[attr-defined]


def _enclosing_function(node: ast.AST) -> ast.AST:
    while node is not None and not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
        node = getattr(node, "_parent", None)
    return node


def _unformatted_templates(path: str) -> Iterator[Tuple[int, str]]:
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    _add_parents(tree)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        if not PLACEHOLDER.search(node.value):
            continue
        parent = getattr(node, "_parent", None)
        # docstrings, f-string parts, dict keys/values (lookup tables)
        if isinstance(parent, (ast.Expr, ast.JoinedStr, ast.Dict)):
            continue
        if isinstance(parent, ast.Attribute) and parent.attr == "format":
            continue
        # logging calls use %-style or are diagnostics
        if isinstance(parent, ast.Call):
            func = parent.func
            if isinstance(func, ast.Attribute) and func.attr in {
                "debug", "info", "warning", "error", "critical", "log", "exception",
                "log_debug", "log_info", "log_warning", "log_error", "translate", "tr",
            }:
                continue
        stmt = parent
        while stmt is not None and not isinstance(stmt, ast.stmt):
            stmt = getattr(stmt, "_parent", None)
        stmt_src = ast.get_source_segment(src, stmt) or ""
        if ".format(" in stmt_src or " % " in stmt_src:
            continue
        if isinstance(parent, ast.Assign) and parent.targets and isinstance(parent.targets[0], ast.Name):
            name = parent.targets[0].id
            rel = os.path.relpath(path, PROJECT_ROOT).replace(os.sep, "/")
            if (rel, name) in ALLOWLIST:
                continue
            fn_src = ast.get_source_segment(src, _enclosing_function(parent)) or ""
            if re.search(rf"\b{re.escape(name)}\.format\(", fn_src) or re.search(rf"\b{re.escape(name)}\s*%\s", fn_src):
                continue
        yield node.lineno, node.value.strip().splitlines()[0][:80]


def test_no_template_left_unformatted():
    offenders = []
    for path in _python_files():
        rel = os.path.relpath(path, PROJECT_ROOT).replace(os.sep, "/")
        if rel.startswith(SKIP_PREFIXES):
            continue
        for lineno, preview in _unformatted_templates(path):
            offenders.append(f"{rel}:{lineno}: {preview!r}")
    assert not offenders, (
        "Placeholders never formatted (missing f prefix or .format()):\n  " + "\n  ".join(offenders)
    )
