# -*- coding: utf-8 -*-
"""
Internal import guard (October 2026 audit).

An AST pass found 22 ``from X import name`` pointing at a module or a name that
does not exist (wrong path after the hexagonal refactor, deleted helpers). Most
sat inside ``try / except ImportError`` and silently turned a feature off for
months (persistent Spatialite cache, auto-optimizer, GDAL error handler, ...).

This test resolves STATICALLY every ``from .x import y`` / ``from ..x import y``
of the plugin (no QGIS needed): the target module must be a file or a package of
the plugin, and each imported name must be defined at module level, imported
into it, be a sub-module, or come from a ``from m import *`` / module
``__getattr__``.

It also forbids absolute ``filter_mate.`` imports: the plugin folder name is
chosen by whoever installs it (``filter_mate-main`` from a GitHub zip), so
absolute imports make the plugin unloadable there.
"""
import ast
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_DIRS = {
    "tests", ".git", "__pycache__", "website", "scripts", "docs", "_bmad", "_bmad-output",
    "knowledge", "dist", "build", "node_modules", ".claude", ".venv", "venv", "logs",
}
PACKAGE_NAME = "filter_mate"

# "relative/path.py: imported name" -> why the unresolved import is acceptable.
# Keep this EMPTY unless a name is created dynamically (globals()[...] = ...)
# and cannot be seen by a static pass.
KNOWN_UNRESOLVED = {}


def _plugin_python_files():
    for path in sorted(PLUGIN_ROOT.rglob("*.py")):
        rel = path.relative_to(PLUGIN_ROOT)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        yield path


def _module_file(parts):
    """The ``.py`` / ``__init__.py`` of dotted ``parts`` (relative to the plugin root), or None."""
    base = PLUGIN_ROOT.joinpath(*parts) if parts else PLUGIN_ROOT
    if (base.parent / (base.name + ".py")).is_file() and parts:
        return base.parent / (base.name + ".py")
    if (base / "__init__.py").is_file():
        return base / "__init__.py"
    return None


def _is_package_dir(parts):
    return PLUGIN_ROOT.joinpath(*parts).is_dir() if parts else True


_TREE_CACHE = {}


def _tree(path):
    if path not in _TREE_CACHE:
        _TREE_CACHE[path] = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return _TREE_CACHE[path]


def _top_level_statements(statements):
    """Statements executed when the module loads: nested in if / try / with / for, never in def / class."""
    for stmt in statements:
        yield stmt
        if isinstance(stmt, ast.If):
            yield from _top_level_statements(stmt.body)
            yield from _top_level_statements(stmt.orelse)
        elif isinstance(stmt, ast.Try):
            yield from _top_level_statements(stmt.body)
            for handler in stmt.handlers:
                yield from _top_level_statements(handler.body)
            yield from _top_level_statements(stmt.orelse)
            yield from _top_level_statements(stmt.finalbody)
        elif isinstance(stmt, (ast.With, ast.For, ast.While)):
            yield from _top_level_statements(stmt.body)
            yield from _top_level_statements(getattr(stmt, "orelse", []))


def _target_names(target):
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            yield from _target_names(elt)
    elif isinstance(target, ast.Starred):
        yield from _target_names(target.value)


def _package_of(path):
    """Dotted package parts (relative to the plugin root) that relative imports of ``path`` start from."""
    rel = path.relative_to(PLUGIN_ROOT)
    parts = list(rel.parts[:-1])
    return parts


def _resolve_from(path, node):
    """Dotted parts of the module a ``from`` import targets, or None when it leaves the plugin."""
    if node.level == 0:
        module = (node.module or "").split(".")
        if module[0] != PACKAGE_NAME:
            return None
        return module[1:]
    package = _package_of(path)
    up = node.level - 1
    if up > len(package):
        return ["<outside the plugin>"]
    base = package[:len(package) - up]
    return base + (node.module.split(".") if node.module else [])


def _defined_names(module_path, seen=None):
    """(names defined at module level, accepts_anything) of a module file.

    ``accepts_anything`` is True with a module ``__getattr__`` or a ``from x import *``
    whose source cannot be followed.
    """
    seen = seen or set()
    if module_path in seen:
        return set(), False
    seen.add(module_path)
    names, anything = set(), False
    for stmt in _top_level_statements(_tree(module_path).body):
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(stmt.name)
            if stmt.name == "__getattr__":
                anything = True
        elif isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                names.update(_target_names(target))
        elif isinstance(stmt, (ast.AnnAssign, ast.AugAssign)):
            names.update(_target_names(stmt.target))
        elif isinstance(stmt, ast.Import):
            for alias in stmt.names:
                names.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(stmt, ast.ImportFrom):
            for alias in stmt.names:
                if alias.name != "*":
                    names.add(alias.asname or alias.name)
                    continue
                target = _resolve_from(module_path, stmt)
                target_file = _module_file(target) if target is not None else None
                if target_file is None:
                    anything = True  # star import of an external module (qgis, ...)
                else:
                    star_names, star_anything = _defined_names(target_file, seen)
                    names.update(star_names)
                    anything = anything or star_anything
        elif isinstance(stmt, (ast.For, ast.With)):
            for sub in ast.walk(stmt):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                    names.add(sub.id)
        elif isinstance(stmt, ast.Expr) and _is_globals_write(stmt.value):
            anything = True
        if isinstance(stmt, ast.Assign) and any(_is_globals_subscript(t) for t in stmt.targets):
            anything = True
    return names, anything


def _is_globals_subscript(target):
    return (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Call)
            and isinstance(target.value.func, ast.Name) and target.value.func.id == "globals")


def _is_globals_write(value):
    return (isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute)
            and isinstance(value.func.value, ast.Call) and isinstance(value.func.value.func, ast.Name)
            and value.func.value.func.id == "globals")


def find_broken_imports():
    """``[(relative file, line, description)]`` of every unresolvable internal import."""
    broken = []
    for path in _plugin_python_files():
        rel = path.relative_to(PLUGIN_ROOT).as_posix()
        for node in ast.walk(_tree(path)):
            if not isinstance(node, ast.ImportFrom):
                continue
            target = _resolve_from(path, node)
            if target is None:
                continue  # an external package
            spelled = "." * node.level + (node.module or "")
            if target == ["<outside the plugin>"]:
                broken.append((rel, node.lineno, f"from {spelled} import ...: leaves the plugin folder"))
                continue
            module_file = _module_file(target)
            if module_file is None and not (node.module is None and _is_package_dir(target)):
                broken.append((rel, node.lineno, f"from {spelled} import ...: no such module"))
                continue
            if module_file is None:
                names, anything = set(), False
            else:
                names, anything = _defined_names(module_file)
            for alias in node.names:
                if alias.name == "*" or anything or alias.name in names:
                    continue
                if _module_file(target + [alias.name]) is not None:
                    continue  # a sub-module
                if _is_package_dir(target + [alias.name]) and (PLUGIN_ROOT.joinpath(*target, alias.name)).is_dir():
                    continue  # a namespace-like sub-folder
                if f"{rel}: {alias.name}" in KNOWN_UNRESOLVED:
                    continue
                broken.append((rel, node.lineno, f"from {spelled} import {alias.name}: name not defined there"))
    return broken


def find_absolute_plugin_imports():
    found = []
    for path in _plugin_python_files():
        rel = path.relative_to(PLUGIN_ROOT).as_posix()
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.ImportFrom) and node.level == 0 and (node.module or "").split(".")[0] == PACKAGE_NAME:
                found.append((rel, node.lineno, f"from {node.module} import ..."))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] == PACKAGE_NAME:
                        found.append((rel, node.lineno, f"import {alias.name}"))
    return found


@pytest.mark.unit
def test_every_internal_import_resolves():
    broken = find_broken_imports()
    assert broken == [], "Internal imports that cannot work (wrong path or deleted name):\n" + "\n".join(
        f"{rel}:{lineno} {what}" for rel, lineno, what in broken)


@pytest.mark.unit
def test_no_absolute_import_of_the_plugin_package():
    found = find_absolute_plugin_imports()
    assert found == [], (
        "The plugin folder name is not 'filter_mate' once installed from a GitHub zip (filter_mate-main): "
        "use relative imports.\n" + "\n".join(f"{rel}:{lineno} {what}" for rel, lineno, what in found))


@pytest.mark.unit
class TestResolver:
    """The resolver itself, on a throw-away tree."""

    @pytest.fixture
    def tree(self, tmp_path, monkeypatch):
        import sys
        module = sys.modules[__name__]
        monkeypatch.setattr(module, "PLUGIN_ROOT", tmp_path)
        monkeypatch.setattr(module, "_TREE_CACHE", {})
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg" / "__init__.py").write_text("from .impl import exported\n__all__ = ['exported']\n")
        (tmp_path / "pkg" / "impl.py").write_text("def exported(): pass\nCONST = 1\ntry:\n    from x import Opt\nexcept ImportError:\n    Opt = None\n")
        (tmp_path / "pkg" / "sub").mkdir()
        (tmp_path / "pkg" / "sub" / "__init__.py").write_text("from ..impl import *\n")
        (tmp_path / "pkg" / "sub" / "leaf.py").write_text("")
        (tmp_path / "pkg" / "user.py").write_text("")
        return tmp_path

    def _broken(self, tree, source):
        (tree / "pkg" / "user.py").write_text(source)
        return [what for _, _, what in find_broken_imports()]

    def test_valid_imports_pass(self, tree):
        assert self._broken(tree, "from .impl import exported, CONST, Opt\nfrom . import impl, sub\n"
                                  "from .sub import leaf, CONST\nfrom .sub.leaf import anything_missing_is_checked\n") == [
            "from .sub.leaf import anything_missing_is_checked: name not defined there"]

    def test_missing_name_module_and_escape_are_reported(self, tree):
        broken = self._broken(tree, "from .impl import gone\nfrom .nowhere import x\nfrom ... import y\n")
        assert len(broken) == 3
        assert "name not defined" in broken[0] and "no such module" in broken[1] and "leaves the plugin" in broken[2]

    def test_absolute_plugin_import_is_reported(self, tree):
        (tree / "pkg" / "user.py").write_text("from filter_mate.pkg.impl import exported\nimport filter_mate.pkg\n")
        assert len(find_absolute_plugin_imports()) == 2
