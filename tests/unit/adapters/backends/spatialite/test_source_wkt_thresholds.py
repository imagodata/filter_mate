# -*- coding: utf-8 -*-
"""One source-WKT simplification threshold for the SpatiaLite chain (2026-10-16).

The executor simplified the source above the 100 KB PostgreSQL EXISTS
threshold (``exists_subquery_threshold``) while the expression builder used
SPATIALITE_WKT_SIMPLIFY_THRESHOLD (1 MB) and interruptible_query defined a
third, unused 30 KB value. A 236 KB river network was generalized by 100 m
and Cross returned 1,181 roads instead of ~747. These checks read the source,
so they need no QGIS.
"""
import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parents[5]
SPATIALITE_DIR = PLUGIN_ROOT / "adapters" / "backends" / "spatialite"
EXCLUDED_DIRS = {
    "tests", ".git", "__pycache__", ".claude",
    "_bmad", "_bmad-output", "website", "docs", "knowledge", "dist", "build", "scripts",
}


def _tree(path):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _assigned_names(tree):
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            names += [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.append(node.target.id)
    return names


def _plugin_python_files():
    for path in PLUGIN_ROOT.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in path.relative_to(PLUGIN_ROOT).parts):
            continue
        yield path


def test_simplify_threshold_defined_once():
    owners = [
        str(path.relative_to(PLUGIN_ROOT))
        for path in _plugin_python_files()
        if "SPATIALITE_WKT_SIMPLIFY_THRESHOLD" in _assigned_names(_tree(path))
    ]
    assert owners == [str(Path("adapters/backends/spatialite/expression_builder.py"))]


def test_executor_uses_the_builder_threshold():
    source = (SPATIALITE_DIR / "filter_executor.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "expression_builder" and node.level == 1
        for alias in node.names
    ]
    assert "SPATIALITE_WKT_SIMPLIFY_THRESHOLD" in imported
    assert "exists_subquery_threshold" not in source


def test_builder_never_simplifies_nor_envelopes():
    tree = _tree(SPATIALITE_DIR / "expression_builder.py")
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not calls & {"simplify", "convexHull", "orientedMinimumBoundingBox", "fromRect"}


def test_source_preparation_has_no_envelope_fallback():
    tree = _tree(PLUGIN_ROOT / "adapters" / "qgis" / "geometry_preparation.py")
    methods = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert "_try_simplification_fallbacks" not in methods
    calls = {
        node.func.attr
        for node in ast.walk(methods["simplify_geometry_adaptive"])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not calls & {"convexHull", "orientedMinimumBoundingBox", "fromRect"}
    constants = {
        node.targets[0].id: node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Constant)
    }
    assert 0 < constants["SOURCE_SIMPLIFY_MAX_TOLERANCE"] <= 1.0
