# -*- coding: utf-8 -*-
"""
PERF 2026-09-14: on PostgreSQL an ORDER BY on the limited feature-list request
is not pushed to the server; QGIS fetched and sorted the whole table before
the limit (13.6 s on 370 690 rows, 24 ms without ORDER BY). The widget only
asks for a server order on the other providers. Method extracted with ast so
the Qt widget module is never imported.
"""
import ast
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_MODULE = Path(__file__).resolve().parents[4] / "ui" / "widgets" / "custom_widgets.py"


def _orders_server_side():
    tree = ast.parse(_MODULE.read_text(encoding="utf-8"))
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == "_orders_server_side":
                ns = {}
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(_MODULE), "exec"), ns)
                return ns["_orders_server_side"]
    raise AssertionError("_orders_server_side not found")


def _widget(provider):
    widget = types.SimpleNamespace(layer=MagicMock())
    widget.layer.providerType.return_value = provider
    widget._orders_server_side = types.MethodType(_orders_server_side(), widget)
    return widget


@pytest.mark.unit
@pytest.mark.parametrize("provider,expected", [
    ("postgres", False), ("ogr", True), ("spatialite", True), ("memory", True),
])
def test_server_order_only_outside_postgresql(provider, expected):
    assert _widget(provider)._orders_server_side() is expected


@pytest.mark.unit
def test_deleted_layer_defaults_to_server_order():
    widget = _widget("postgres")
    widget.layer.providerType.side_effect = RuntimeError("wrapped C/C++ object has been deleted")
    assert widget._orders_server_side() is True
