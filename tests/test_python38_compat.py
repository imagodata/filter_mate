# -*- coding: utf-8 -*-
"""
Python 3.8 / 3.9 guard (QGIS 3.22 ships Python 3.8; 3.22 - 3.28 builds run 3.8 or 3.9).

CI runs the unit tests on Python 3.10 and 3.12 only, so a ``dict[str, int]``
annotation or a ``str | None`` evaluated at import time crashed the plugin
on QGIS 3.22 without any test noticing (``adapters/filter_result_handler.py``,
``core/ports/cache_port.py``, October 2026). This test is the stand-in for a
Python 3.9 CI job:

1. every plugin file must parse with the Python 3.8 grammar
   (``ast.parse(..., feature_version=(3, 8))``);
2. nothing evaluated at import or call time may use a builtin generic
   (``list[int]``, ``dict[K, V]``, ``tuple[...]``, ``set[...]``), a ``X | Y``
   type union, or a ``typing`` name / stdlib API added after 3.8. Annotations
   are not evaluated when the module starts with
   ``from __future__ import annotations`` (nor are annotations of local
   variables); everything else (defaults, aliases, ``isinstance``) is.
"""
import ast
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_DIRS = {
    "tests", ".git", "__pycache__", "website", "scripts", "docs", "_bmad", "_bmad-output",
    "knowledge", "dist", "build", "node_modules", ".claude", ".venv", "venv",
}

BUILTIN_GENERICS = {"list", "dict", "tuple", "set", "frozenset", "type"}
TYPING_GENERICS = {"List", "Dict", "Tuple", "Set", "FrozenSet", "Optional", "Union", "Callable", "Type"}
# Names that make ``A | B`` a type union (a bare ``Qt.A | Qt.B`` flag mix is fine on every version).
TYPE_NAMES = BUILTIN_GENERICS | {"str", "int", "float", "bool", "bytes", "complex", "object", "bytearray"}
# typing names missing from Python 3.8
TYPING_AFTER_38 = {
    "Annotated", "ParamSpec", "ParamSpecArgs", "ParamSpecKwargs", "TypeAlias", "Concatenate", "TypeGuard",
    "Self", "Never", "LiteralString", "Required", "NotRequired", "Unpack", "TypeVarTuple", "assert_never",
    "assert_type", "reveal_type", "override", "dataclass_transform", "get_overloads", "clear_overloads",
}
# The MCP server runs outside QGIS, on the machine of the MCP client (Python 3.10+, requirements-mcp.txt).
RUNTIME_EXEMPT = ("filtermate_api/mcp/",)
MODULES_AFTER_38 = {"zoneinfo", "graphlib", "tomllib"}
METHODS_AFTER_38 = {"removeprefix", "removesuffix"}  # str, 3.9
KEYWORDS_AFTER_38 = {("zip", "strict"), ("dataclass", "slots"), ("dataclass", "kw_only")}


def _plugin_python_files():
    for path in sorted(PLUGIN_ROOT.rglob("*.py")):
        rel = path.relative_to(PLUGIN_ROOT)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        yield path


def _has_future_annotations(tree):
    return any(
        isinstance(node, ast.ImportFrom) and node.module == "__future__"
        and any(alias.name == "annotations" for alias in node.names)
        for node in tree.body
    )


def _is_type_checking_test(test):
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING")


def _name_of(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_type_union_operand(side):
    if isinstance(side, ast.Constant):
        return side.value is None
    if isinstance(side, ast.Name):
        return side.id in TYPE_NAMES
    if isinstance(side, ast.Subscript):
        return _name_of(side.value) in BUILTIN_GENERICS | TYPING_GENERICS
    return False


def _runtime_unsafe(node, annotation, generics=frozenset(BUILTIN_GENERICS)):
    """Yield ``(lineno, what)`` for 3.8-hostile constructs inside the expression ``node``.

    ``annotation`` is True when ``node`` is an annotation that Python evaluates:
    every ``|`` is then a type union.
    """
    for sub in ast.walk(node):
        if isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name) and sub.value.id in generics:
            yield sub.lineno, f"{sub.value.id}[...] is evaluated at runtime (Python < 3.9)"
        elif isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.BitOr):
            if annotation or _is_type_union_operand(sub.left) or _is_type_union_operand(sub.right):
                yield sub.lineno, "X | Y type union is evaluated at runtime (Python < 3.10)"


class _Visitor(ast.NodeVisitor):
    def __init__(self, future_annotations, generics=frozenset(BUILTIN_GENERICS)):
        self.future = future_annotations
        self.generics = generics
        self.offences = []
        self._function_depth = 0

    def _report(self, items):
        self.offences.extend(items)

    def _annotation(self, node):
        if node is not None and not self.future:
            self._report(_runtime_unsafe(node, True, self.generics))

    def visit_If(self, node):
        if _is_type_checking_test(node.test):  # the body never runs
            for child in node.orelse:
                self.visit(child)
            return
        self.generic_visit(node)

    def visit_Try(self, node):
        # 'try: from typing import Annotated / except ImportError: <fallback>' is the fix, not a defect.
        guarded = any(_name_of(h.type) in ("ImportError", "ModuleNotFoundError") for h in node.handlers
                      if h.type is not None and not isinstance(h.type, ast.Tuple)) or any(
            _name_of(elt) in ("ImportError", "ModuleNotFoundError")
            for h in node.handlers if isinstance(h.type, ast.Tuple) for elt in h.type.elts)
        for child in node.body:
            if guarded and isinstance(child, (ast.Import, ast.ImportFrom)):
                continue
            self.visit(child)
        for part in (node.handlers, node.orelse, node.finalbody):
            for child in part:
                self.visit(child)

    def _visit_function(self, node):
        args = node.args
        every_arg = args.posonlyargs + args.args + args.kwonlyargs + [a for a in (args.vararg, args.kwarg) if a]
        for arg in every_arg:
            self._annotation(arg.annotation)
        self._annotation(node.returns)
        for default in args.defaults + [d for d in args.kw_defaults if d is not None]:
            self.visit(default)
        for decorator in node.decorator_list:
            self.visit(decorator)
        self._function_depth += 1
        for child in node.body:
            self.visit(child)
        self._function_depth -= 1

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function

    def visit_AnnAssign(self, node):
        if self._function_depth == 0:  # annotations of local variables are never evaluated
            self._annotation(node.annotation)
        if node.value is not None:
            self.visit(node.value)

    def visit_Subscript(self, node):
        self._report(_runtime_unsafe(node, False, self.generics))
        self.generic_visit(node)

    def visit_BinOp(self, node):
        if isinstance(node.op, ast.BitOr):
            self._report(_runtime_unsafe(node, False, self.generics))
        self.generic_visit(node)

    def visit_Call(self, node):
        name = _name_of(node.func)
        if name in ("isinstance", "issubclass") and len(node.args) == 2:
            for sub in ast.walk(node.args[1]):
                if isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.BitOr):
                    self._report([(sub.lineno, "isinstance(x, A | B) needs Python 3.10")])
        if isinstance(node.func, ast.Attribute) and node.func.attr in METHODS_AFTER_38:
            self._report([(node.lineno, f".{node.func.attr}() needs Python 3.9")])
        for keyword in node.keywords:
            if (name, keyword.arg) in KEYWORDS_AFTER_38:
                self._report([(node.lineno, f"{name}({keyword.arg}=...) needs Python 3.10")])
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.level == 0 and node.module in ("typing", "collections.abc"):
            for alias in node.names:
                if node.module == "typing" and alias.name in TYPING_AFTER_38:
                    self._report([(node.lineno, f"typing.{alias.name} needs a newer Python")])
        if node.level == 0 and node.module == "functools" and any(alias.name == "cache" for alias in node.names):
            self._report([(node.lineno, "functools.cache needs Python 3.9")])
        if node.level == 0 and (node.module or "").split(".")[0] in MODULES_AFTER_38:
            self._report([(node.lineno, f"{node.module} needs a newer Python")])

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name.split(".")[0] in MODULES_AFTER_38:
                self._report([(node.lineno, f"import {alias.name} needs a newer Python")])


def _scan(source, filename="<test>"):
    tree = ast.parse(source, filename=filename, feature_version=(3, 8))
    # collections.abc.Callable[...] and friends are subscriptable from Python 3.9 only
    abc_names = {alias.asname or alias.name for node in ast.walk(tree)
                 if isinstance(node, ast.ImportFrom) and node.module == "collections.abc" and node.level == 0
                 for alias in node.names}
    visitor = _Visitor(_has_future_annotations(tree), frozenset(BUILTIN_GENERICS | abc_names))
    visitor.visit(tree)
    return sorted(set(visitor.offences))


@pytest.mark.unit
def test_every_plugin_file_parses_with_the_python_38_grammar():
    broken = []
    for path in _plugin_python_files():
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 8))
        except SyntaxError as exc:
            broken.append(f"{path.relative_to(PLUGIN_ROOT)}:{exc.lineno} {exc.msg}")
    assert broken == [], "Python 3.8 syntax errors (QGIS 3.22):\n" + "\n".join(broken)


@pytest.mark.unit
def test_no_python_39_or_310_construct_evaluated_at_runtime():
    offences = []
    for path in _plugin_python_files():
        if path.relative_to(PLUGIN_ROOT).as_posix().startswith(RUNTIME_EXEMPT):
            continue
        for lineno, what in _scan(path.read_text(encoding="utf-8"), str(path)):
            offences.append(f"{path.relative_to(PLUGIN_ROOT)}:{lineno} {what}")
    assert offences == [], (
        "These constructs raise at import or call time on Python 3.8 / 3.9 (QGIS 3.22 - 3.28). "
        "Add 'from __future__ import annotations' (annotations only) or use typing.List / Dict / "
        "Tuple / Optional:\n" + "\n".join(offences)
    )


@pytest.mark.unit
class TestDetector:
    def test_builtin_generic_annotation_is_flagged_without_the_future_import(self):
        assert _scan("def f(x: tuple[str, bool]): pass")
        assert _scan("def f() -> dict[str, int]: pass")
        assert _scan("class C:\n    x: list[int] = []")

    def test_future_import_makes_annotations_inert(self):
        assert _scan("from __future__ import annotations\ndef f(x: tuple[str, bool]) -> dict[str, int]: pass") == []

    def test_future_import_does_not_protect_runtime_expressions(self):
        source = "from __future__ import annotations\nAlias = dict[str, int]\ndef f(x=list[int]): pass"
        assert len(_scan(source)) == 2
        assert _scan("from __future__ import annotations\nisinstance(x, int | str)")

    def test_local_variable_annotations_are_never_evaluated(self):
        assert _scan("def f():\n    x: list[int] = []") == []

    def test_type_checking_block_is_skipped(self):
        assert _scan("if TYPE_CHECKING:\n    X = dict[str, int]") == []

    def test_type_union_in_annotation(self):
        assert _scan("def f(x: str | None): pass")
        assert _scan("from __future__ import annotations\ndef f(x: str | None): pass") == []

    def test_flag_mixing_is_not_a_union(self):
        assert _scan("x = Qt.AlignLeft | Qt.AlignTop\nmask = 1 | 2") == []
        assert _scan("x = a | None")

    def test_collections_abc_generics_are_flagged(self):
        assert _scan("from collections.abc import Callable\ndef f(x: Callable[[int], int]): pass")
        assert _scan("from __future__ import annotations\nfrom collections.abc import Callable\n"
                     "def f(x: Callable[[int], int]): pass") == []

    def test_import_guarded_by_import_error_is_accepted(self):
        assert _scan("try:\n    from typing import Annotated\nexcept ImportError:\n    from typing_extensions import Annotated") == []

    def test_newer_typing_names_and_string_methods(self):
        assert _scan("from typing import Annotated")
        assert _scan("name.removeprefix('a')")
        assert _scan("from typing import List, Dict") == []
