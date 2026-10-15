# -*- coding: utf-8 -*-
"""Registering or unregistering a layer never writes a style into the user's data.

The removed ``save_style_from_layer_id`` ran on every layer removal: it put a default style named
``FilterMate_style_<layer>`` in the layer's data source (GeoPackage / PostgreSQL ``layer_styles``)
or a ``.qml`` next to the source file, and nothing read it back.
"""
import ast
import pathlib

import pytest

_TASK = pathlib.Path(__file__).resolve().parents[4] / "core" / "tasks" / "layer_management_task.py"
WRITERS = {"saveStyleToDatabase", "deleteStyleFromDatabase", "saveNamedStyle", "saveDefaultStyle"}


@pytest.mark.unit
def test_layer_management_task_writes_no_style():
    tree = ast.parse(_TASK.read_text(encoding="utf-8"))
    calls = sorted({node.func.attr for node in ast.walk(tree)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in WRITERS})
    assert not calls, f"style written into the user's data source: {calls}"
