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


def _method(name):
    tree = ast.parse(_MODULE.read_text(encoding="utf-8"))
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                # A module name: the relative import of the method falls back to the absolute one.
                ns = {"__name__": "fm_test_feature_list_server_order", "QgsExpression": _QgsExpression}
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(_MODULE), "exec"), ns)
                return ns[name]
    raise AssertionError(f"{name} not found")


def _orders_server_side():
    return _method("_orders_server_side")


class _QgsExpression:
    @staticmethod
    def quotedValue(value):
        return "'" + str(value).replace("'", "''") + "'"


def _widget(provider, source="/data/roads.gpkg|layername=roads"):
    widget = types.SimpleNamespace(layer=MagicMock())
    widget.layer.providerType.return_value = provider
    widget.layer.source.return_value = source
    for name in ("_orders_server_side", "_search_expression", "_displays_remote_text_field"):
        setattr(widget, name, types.MethodType(_method(name), widget))
    return widget


@pytest.mark.unit
@pytest.mark.parametrize("provider,expected", [
    ("postgres", False), ("ogr", True), ("spatialite", True), ("memory", True),
])
def test_server_order_only_outside_postgresql(provider, expected):
    assert _widget(provider)._orders_server_side() is expected


WFS_URI = "typename='ADMINEXPRESS-COG.LATEST:commune' url='https://data.geopf.fr/wfs/ows' version='auto'"


@pytest.mark.unit
@pytest.mark.parametrize("provider,source", [
    ("WFS", WFS_URI),
    ("OAPIF", "url='https://example.org/ogcapi' typename='communes'"),
    ("arcgisfeatureserver", "url='https://example.org/arcgis/rest/services/x/FeatureServer/0'"),
    ("ogr", "/vsicurl/https://example.org/communes.fgb"),
])
def test_no_server_order_for_remote_sources(provider, source):
    """2026-10-17: QGIS sorts a web layer client-side: the limited request downloaded the whole layer."""
    assert _widget(provider, source)._orders_server_side() is False


def _text_field_layer(widget, numeric=False):
    field = MagicMock()
    field.isNumeric.return_value = numeric
    field.isDateOrTime.return_value = False
    widget.layer.fields.return_value.indexOf.side_effect = lambda name: 0 if name == "nom" else -1
    widget.layer.fields.return_value.at.return_value = field


@pytest.mark.unit
def test_remote_text_search_is_a_server_side_ilike():
    widget = _widget("WFS", WFS_URI)
    _text_field_layer(widget)
    assert widget._search_expression('"nom"', "L'Isle") == "\"nom\" ILIKE '%L''Isle%'"


@pytest.mark.unit
@pytest.mark.parametrize("provider,source,display,numeric", [
    ("ogr", "/data/communes.shp", '"nom"', False),        # local: unchanged
    ("WFS", WFS_URI, '("nom" || \' \' || "insee")', False),  # an expression, not a field
    ("WFS", WFS_URI, '"nom"', True),                      # a numeric field
])
def test_other_text_searches_keep_the_client_side_form(provider, source, display, numeric):
    widget = _widget(provider, source)
    _text_field_layer(widget, numeric=numeric)
    assert widget._search_expression(display, "Auch") == f"lower(to_string({display})) LIKE '%auch%'"


@pytest.mark.unit
def test_deleted_layer_defaults_to_server_order():
    widget = _widget("postgres")
    widget.layer.providerType.side_effect = RuntimeError("wrapped C/C++ object has been deleted")
    assert widget._orders_server_side() is True
