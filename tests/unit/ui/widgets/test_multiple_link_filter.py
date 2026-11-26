# -*- coding: utf-8 -*-
"""Lot 2 (audit 24/11/2026): the EXPLORING multiple list reads rows filtered
by the link expression, ANDed with the text search.

The widget module needs Qt/QGIS, so the pure combiner is extracted with ast
(same harness as test_feature_list_server_order) and its contract is locked:
each part kept in parentheses (an OR inside a part must not leak out), empty
parts dropped.
"""
import ast
from pathlib import Path

import pytest

_MODULE = Path(__file__).resolve().parents[4] / "ui" / "widgets" / "custom_widgets.py"
_CLASS = "QgsCheckableComboBoxFeaturesListPickerWidget"
_METHOD = "_combine_filter_expressions"


def _combine():
    tree = ast.parse(_MODULE.read_text(encoding="utf-8"))
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == _CLASS):
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == _METHOD:
                ns = {"__name__": "fm_test_multiple_link_filter"}
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(_MODULE), "exec"), ns)
                fn = ns[_METHOD]
                return getattr(fn, "__func__", fn)
    raise AssertionError(f"{_CLASS}.{_METHOD} not found")


combine = _combine()


@pytest.mark.unit
def test_no_parts_is_no_filter():
    assert combine() == ""


@pytest.mark.unit
def test_blank_parts_are_dropped():
    assert combine("", "   ", None) == ""


@pytest.mark.unit
def test_single_part_kept_in_parentheses():
    assert combine("\"name\" LIKE 'east%'") == "(\"name\" LIKE 'east%')"


@pytest.mark.unit
def test_link_expression_anded_with_the_text_search():
    assert combine("\"name\" LIKE 'east%'", "upper(\"name\") LIKE '%FOO%'") == \
        "(\"name\" LIKE 'east%') AND (upper(\"name\") LIKE '%FOO%')"


@pytest.mark.unit
def test_parentheses_keep_an_or_inside_its_part():
    assert combine("a OR b", "c") == "(a OR b) AND (c)"
