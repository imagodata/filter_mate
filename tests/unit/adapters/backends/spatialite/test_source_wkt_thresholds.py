# -*- coding: utf-8 -*-
"""One source-WKT simplification threshold for the SpatiaLite chain (2026-10-16).

The executor simplified the source above the PostgreSQL option
``exists_subquery_threshold`` while the expression builder used its own
SPATIALITE_WKT_SIMPLIFY_THRESHOLD (1 MB) and interruptible_query defined a
third, unused 30 KB value. A 236 KB river network was generalized by 100 m
and Cross returned 1,181 roads instead of ~747. Now the source is never
simplified; the builder's limits (defined once) decide whether it is inlined
or filtered by the OGR backend, both exact. These checks read the source, so
they need no QGIS.
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


def test_inline_limits_defined_once():
    for name in ("SPATIALITE_WKT_STATIC_INLINE_LIMIT", "SPATIALITE_WKT_INLINE_MAX_LENGTH"):
        owners = [
            str(path.relative_to(PLUGIN_ROOT))
            for path in _plugin_python_files()
            if name in _assigned_names(_tree(path))
        ]
        assert owners == [str(Path("adapters/backends/spatialite/expression_builder.py"))], name
    assert not any(
        "SPATIALITE_WKT_SIMPLIFY_THRESHOLD" in _assigned_names(_tree(path)) for path in _plugin_python_files()
    )


def test_executor_never_simplifies_the_source():
    """2026-10-17: the source WKT is inlined exact or the OGR backend filters (exact)."""
    source = (SPATIALITE_DIR / "filter_executor.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = {
        node.func.attr for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not calls & {"simplify", "simplify_geometry_adaptive", "convexHull"}
    assert "exists_subquery_threshold" not in source


def test_builder_never_simplifies_nor_envelopes():
    tree = _tree(SPATIALITE_DIR / "expression_builder.py")
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not calls & {"simplify", "convexHull", "orientedMinimumBoundingBox", "fromRect"}


def test_source_preparation_has_no_simplification_left():
    """2026-10-17: the source simplification code is removed, not just unused."""
    tree = _tree(PLUGIN_ROOT / "adapters" / "qgis" / "geometry_preparation.py")
    names = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    assert not names & {"simplify_geometry_adaptive", "features_to_wkt_with_simplification",
                        "_try_simplification_fallbacks", "source_simplification_allowed"}
    handler = _tree(PLUGIN_ROOT / "core" / "tasks" / "geometry_handler.py")
    assert "simplify_geometry_adaptive" not in {n.name for n in ast.walk(handler) if isinstance(n, ast.FunctionDef)}


def _constants(scope):
    return {
        node.targets[0].id: node.value.value
        for node in scope.body
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Constant)
    }


def test_inline_limit_matches_postgresql():
    """Same static WKT size limit for inlining a source in SpatiaLite and PostgreSQL subsets.

    2026-10-17: SpatiaLite may inline more (up to 1 MB) on a GeoPackage
    target whose R-tree count keeps one statement under its time budget.
    """
    spatialite = _constants(_tree(SPATIALITE_DIR / "expression_builder.py"))
    # 2026-10-27: the PostgreSQL SQL generation lives in the host-free core
    pg_tree = _tree(PLUGIN_ROOT / "filtermate_core" / "sql" / "postgresql" / "expression_builder.py")
    pg_class = next(
        node for node in pg_tree.body
        if isinstance(node, ast.ClassDef) and node.name == "PostgreSQLSqlBuilder"
    )
    assert spatialite["SPATIALITE_WKT_STATIC_INLINE_LIMIT"] == _constants(pg_class)["MAX_WKT_LENGTH"] == 100_000


def test_no_envelope_repair_nor_ogr_source_simplification():
    assert not (PLUGIN_ROOT / "adapters" / "backends" / "ogr" / "geometry_optimizer.py").exists()
    for path, function in (
        (PLUGIN_ROOT / "core" / "geometry" / "geometry_repair.py", "aggressive_geometry_repair"),
        (PLUGIN_ROOT / "adapters" / "qgis" / "geometry_preparation.py", "_repair_geometry"),
    ):
        node = next(n for n in ast.walk(_tree(path)) if isinstance(n, ast.FunctionDef) and n.name == function)
        calls = {
            c.func.attr for c in ast.walk(node)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
        }
        assert not calls & {"convexHull", "fromRect", "orientedMinimumBoundingBox"}, path.name


def test_no_post_buffer_simplification():
    """2026-10-16: it ignored the predicate and read an expression buffer from the first feature only."""
    for path in (
        PLUGIN_ROOT / "core" / "geometry" / "buffer_processor.py",
        PLUGIN_ROOT / "core" / "tasks" / "geometry_handler.py",
    ):
        names = {n.name for n in ast.walk(_tree(path)) if isinstance(n, ast.FunctionDef)}
        assert "simplify_buffer_result" not in names, path.name


def _regex_source(path):
    """Source text of the _GEOMETRIC_FILTER_RE assignment."""
    source = path.read_text(encoding="utf-8")
    node = next(
        n for n in _tree(path).body
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "_GEOMETRIC_FILTER_RE"
    )
    return ast.get_source_segment(source, node.value)


def test_both_paths_detect_spatial_filters_alike():
    """2026-10-17: the SQL and the OGR path decide 'replace or combine' with the same pattern."""
    assert _regex_source(SPATIALITE_DIR / "expression_builder.py") == _regex_source(
        PLUGIN_ROOT / "adapters" / "backends" / "ogr" / "expression_builder.py"
    )
