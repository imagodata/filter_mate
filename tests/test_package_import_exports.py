# -*- coding: utf-8 -*-
"""
Static guard: every name a plugin module imports from one of the plugin's own
packages (``from ...some.package import name``) must really be provided by
that package's ``__init__.py``, unless the import sits inside a ``try`` block
(deliberate fallback).

Regression for the v4.8.8 pre-release incident: ``layer_management_task``
imported ``safe_set_layer_variables_batch`` from ``infrastructure.utils``
while the new function had only been added to ``signal_utils``. The unit
suite could not see it because the tasks conftest stubs the whole
``infrastructure`` tree; QGIS failed at plugin load with
"cannot import name ...".
"""

import ast
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SKIP_PARTS = {'tests', 'dist', '_bmad', '_bmad-output',
               '.git', 'website', '__pycache__', 'filtermate_api', 'knowledge', 'scripts'}


def _names_provided_by(init_path: Path) -> set:
    src = init_path.read_text(encoding='utf-8')
    names = set(re.findall(r"^\s+'([A-Za-z_][A-Za-z0-9_]*)',", src, flags=re.M))
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add((alias.asname or alias.name).split('.')[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _import_lines_inside_try(tree: ast.AST) -> set:
    lines = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            for sub in ast.walk(node):
                if isinstance(sub, ast.ImportFrom):
                    lines.add(sub.lineno)
    return lines


def _unguarded_package_imports():
    cache = {}
    for py in sorted(_ROOT.rglob('*.py')):
        if any(part in _SKIP_PARTS for part in py.parts):
            continue
        try:
            tree = ast.parse(py.read_text(encoding='utf-8'))
        except (SyntaxError, UnicodeDecodeError):
            continue
        guarded = _import_lines_inside_try(tree)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.ImportFrom) and node.level >= 1 and node.module):
                continue
            if node.lineno in guarded:
                continue
            base = py.parent
            for _ in range(node.level - 1):
                base = base.parent
            target = base.joinpath(*node.module.split('.'))
            init = target / '__init__.py'
            if not init.exists() or target.with_suffix('.py').exists():
                continue  # a module, not a package, or outside the tree
            if init not in cache:
                cache[init] = _names_provided_by(init)
            for alias in node.names:
                if alias.name == '*' or alias.name in cache[init]:
                    continue
                if (target / f"{alias.name}.py").exists() or (target / alias.name / '__init__.py').exists():
                    continue  # importing a submodule is always fine
                yield py.relative_to(_ROOT), node.lineno, node.module, alias.name


@pytest.mark.unit
def test_every_unguarded_package_import_is_exported():
    missing = [f"{path}:{line} from {module} import {name}"
               for path, line, module, name in _unguarded_package_imports()]
    assert not missing, (
        "Names imported from a plugin package that its __init__.py does not provide "
        "(QGIS would fail with 'cannot import name'):\n  " + "\n  ".join(missing)
    )


def _unguarded_relative_imports_of_missing_modules():
    """Relative imports (outside try blocks) whose target module or package does not exist."""
    for py in sorted(_ROOT.rglob('*.py')):
        if any(part in _SKIP_PARTS for part in py.parts):
            continue
        try:
            tree = ast.parse(py.read_text(encoding='utf-8'))
        except (SyntaxError, UnicodeDecodeError):
            continue
        guarded = _import_lines_inside_try(tree)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.ImportFrom) and node.level >= 1):
                continue
            if node.lineno in guarded:
                continue
            base = py.parent
            for _ in range(node.level - 1):
                base = base.parent
            target = base.joinpath(*node.module.split('.')) if node.module else base
            if target.with_suffix('.py').exists() or (target / '__init__.py').exists():
                continue
            yield py.relative_to(_ROOT), node.lineno, '.' * node.level + (node.module or '')


@pytest.mark.unit
def test_every_unguarded_relative_import_targets_an_existing_module():
    """Regression for PR #52: utils/type_utils.py moved to infrastructure/utils/ but
    core/tasks/layer_management_task.py kept importing ``...utils.type_utils`` — the
    plugin failed at add_layers with "No module named 'filter_mate.utils'"."""
    missing = [f"{path}:{line} from {module} import ..." for path, line, module in _unguarded_relative_imports_of_missing_modules()]
    assert not missing, (
        "Relative imports of modules that no longer exist (QGIS would fail with 'No module named'):\n  "
        + "\n  ".join(missing)
    )
