# -*- coding: utf-8 -*-
"""Where the keys of a hybrid source subset are read, by combination (``AttributeFilterExecutor._native_subset``).

2026-11-18: a GeoPackage filtered by ``bounds_width($geometry) > 1`` got a list of keys; filtered again by
``> 2`` (the new subset replacing the first), the features were read through the first subset, so no list was
written and the former conversion's ``bounds_width("geom") > 2`` was refused by SQLite. Keys are now read on the
whole layer whenever the new subset is not ANDed with the subset the layer has (replace, OR, AND with another
one), still never under AND NOT. Under OR with the subset the layer shows, the keys it keeps are not listed again.
Methods extracted with ast (the module needs the plugin package).
"""
import ast
import logging
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import pytest

pytestmark = pytest.mark.unit

_PATH = Path(__file__).resolve().parents[4] / "core" / "tasks" / "executors" / "attribute_filter_executor.py"
_PACKAGE = "fm_second_filter_keys_test"
_METHODS = ("_native_subset", "_keys_may_be_evaluated", "_keys_read_on_whole_layer", "_shown_features_kept",
            "_current_subset")


def _namespace():
    tree = ast.parse(_PATH.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "AttributeFilterExecutor")
    nodes = [item for item in cls.body if isinstance(item, ast.FunctionDef) and item.name in _METHODS]
    namespace = {"__name__": _PACKAGE + ".core.tasks.executors.attribute_filter_executor",
                 "__package__": _PACKAGE + ".core.tasks.executors",
                 "logger": logging.getLogger("fm.test.second_filter_keys"), "Optional": Optional}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(_PATH), "exec"), namespace)
    return namespace


NS = _namespace()
OLD = '"fid" IS NOT NULL AND "fid" IN (1, 2, 3, 4, 5)'


class _Layer:
    def __init__(self, subset):
        self._subset = subset

    def subsetString(self):
        if self._subset is RuntimeError:
            raise RuntimeError("wrapped C/C++ object has been deleted")
        return self._subset


def _executor(current, old, operator):
    executor = SimpleNamespace(layer=_Layer(current), primary_key="fid", old_subset=old, combine_operator=operator)
    for name in _METHODS:
        setattr(executor, name, types.MethodType(NS[name], executor))
    return executor


@pytest.fixture
def calls(monkeypatch):
    """subset_for_layer as the executor imports it, recording its arguments."""
    recorded = []
    names = [_PACKAGE, _PACKAGE + ".adapters", _PACKAGE + ".adapters.qgis"]
    for name in names:
        package = types.ModuleType(name)
        package.__path__ = []
        monkeypatch.setitem(sys.modules, name, package)
    translation = types.ModuleType(_PACKAGE + ".adapters.qgis.native_filter_translation")
    translation.subset_for_layer = lambda layer, expression, **options: recorded.append(options) or "subset"
    monkeypatch.setitem(sys.modules, translation.__name__, translation)
    return recorded


@pytest.mark.parametrize("current, old, operator, evaluate, whole_layer, shown_kept", [
    ("", None, None, True, False, False),          # the first filter: the layer is the whole layer
    ("", None, "OR", True, False, False),
    (OLD, OLD, "AND", True, False, False),         # ANDed with the subset the layer has: through it (unchanged)
    (OLD, OLD, None, True, True, False),           # replaced: the second filter of the defect
    (OLD, OLD, "OR", True, True, True),            # ORed: the keys the old subset keeps are left out
    (OLD, '"pop" > 2', "OR", True, True, False),   # ORed with another subset than the layer's
    (OLD, '"pop" > 2', "AND", True, True, False),  # ANDed with another subset than the layer's
    (OLD, None, "AND", True, True, False),         # no old subset: the new expression alone
    (OLD, OLD, "AND NOT", False, True, False),     # never a list under NOT (FALSE and NULL differ)
    ("", None, "AND NOT", False, False, False),
    (RuntimeError, OLD, None, False, False, False),  # a deleted layer
])
def test_where_the_keys_are_read(calls, current, old, operator, evaluate, whole_layer, shown_kept):
    executor = _executor(current, old, operator)

    assert executor._native_subset(' bounds_width($geometry) > 2') == "subset"
    assert len(calls) == 1
    options = calls[0]
    assert (options["evaluate"], options["whole_layer"], options["shown_kept"]) == (evaluate, whole_layer, shown_kept)
    assert options["negated"] == ("NOT" in (operator or ""))
    assert options["key_name"] == "fid"
