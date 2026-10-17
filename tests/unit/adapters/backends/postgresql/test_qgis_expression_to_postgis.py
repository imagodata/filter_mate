# -*- coding: utf-8 -*-
"""qgis_expression_to_postgis (dynamic buffer expressions) keeps names and values.

2026-10-17: the function names were replaced with str.replace, anywhere:
``"buffer_m"`` became ``"ST_Buffer_m"``, ``"area_ha"`` ``"ST_Area_ha"``,
``'Route du perimeter'`` was rewritten too, and ``length("nom")`` became
ST_Length (length(string) is a string function in QGIS). The ``::numeric``
cast was added after any quote followed by an operator, so ``"nature" <>
'Route'`` became ``"nature"::numeric <> 'Route'``, and keywords / spaces were
rewritten inside values.
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[5]
_PKG = "fmtest_pg_executor_pkg"


def _package(name, path):
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    sys.modules[name] = module


@pytest.fixture(scope="module")
def to_postgis():
    # core.filter as a bare package: its __init__ pulls QGIS-only modules,
    # the converter only needs core/filter/sql_quotes.py.
    for name, path in ((_PKG, _ROOT), (f"{_PKG}.core", _ROOT / "core"),
                       (f"{_PKG}.core.filter", _ROOT / "core" / "filter"),
                       (f"{_PKG}.adapters", _ROOT / "adapters"),
                       (f"{_PKG}.adapters.backends", _ROOT / "adapters" / "backends"),
                       (f"{_PKG}.adapters.backends.postgresql", _ROOT / "adapters" / "backends" / "postgresql")):
        _package(name, path)
    name = f"{_PKG}.adapters.backends.postgresql.filter_executor"
    spec = importlib.util.spec_from_file_location(name, _ROOT / "adapters" / "backends" / "postgresql" / "filter_executor.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    yield module.qgis_expression_to_postgis
    for key in [key for key in sys.modules if key == _PKG or key.startswith(f"{_PKG}.")]:
        sys.modules.pop(key, None)


@pytest.mark.parametrize("expression", [
    '"buffer_m"',
    '"area_ha"',
    '"length_m"',
    '"perimeter"',
    "\"nature\" <> 'Route'",
    "length(\"nom\") * 2",
    "CASE WHEN \"nom\" = 'Route du perimeter' THEN 10 ELSE 5 END",
    "CASE WHEN \"nom\" = 'buffer(1)' THEN 10 ELSE 5 END",
    "CASE WHEN \"nom\" = 'Case-Pilote' THEN 10 ELSE 5 END",
    "CASE WHEN \"nom\" = 'Saint  Jean' THEN 10 ELSE 5 END",
])
def test_names_and_values_are_kept(to_postgis, expression):
    assert to_postgis(expression) == expression


@pytest.mark.parametrize("expression, expected", [
    ('"buffer_m" * 2', '"buffer_m"::numeric * 2'),
    ('"area_ha" / 10', '"area_ha"::numeric / 10'),
    ('"w" + 1.5', '"w"::numeric + 1.5'),
    ('buffer($geometry, 10)', 'ST_Buffer("geometry", 10)'),
    ('area($geometry) / 1000', 'ST_Area("geometry") / 1000'),
    ('perimeter( $geometry )', 'ST_Perimeter( "geometry" )'),
    ('$area / 100', 'ST_Area("geometry") / 100'),
    ('length($geometry) / 2', 'ST_Length("geometry") / 2'),
    ("if(\"nature\" = 'Route, chemin', 10, 5)", "CASE WHEN \"nature\" = 'Route, chemin' THEN 10 ELSE 5 END"),
])
def test_conversions(to_postgis, expression, expected):
    assert to_postgis(expression) == expected


@pytest.mark.parametrize("expression, expected", [
    # a buffer distance is numeric: arithmetic between columns casts both sides (as before)
    ('"x" - "y"', '"x"::numeric - "y"::numeric'),
    ('"w" * "k" / 2', '"w"::numeric * "k"::numeric / 2'),
    ('length(buffer($geometry, 1))', 'ST_Length(ST_Buffer("geometry", 1))'),
    ("if(\"nom\" = 'l\\'eau', 10, 5)", "CASE WHEN \"nom\" = 'l''eau' THEN 10 ELSE 5 END"),
])
def test_conversions_review(to_postgis, expression, expected):
    assert to_postgis(expression) == expected


def _layer(**numeric_by_name):
    from unittest.mock import MagicMock
    fields = []
    for name, numeric in numeric_by_name.items():
        field = MagicMock()
        field.name.return_value = name
        field.isNumeric.return_value = numeric
        fields.append(field)
    layer = MagicMock()
    layer.fields.return_value = fields
    return layer


@pytest.mark.parametrize("expression, layer_fields, expected", [
    ('"pop" > 100', {}, '"pop"::numeric > 100'),
    ('"pop" = 100', {}, '"pop"::numeric = 100'),                      # type unknown: as before
    ('"pop" = 100', {'pop': True}, '"pop"::numeric = 100'),
    ('"insee_dep" = 75', {'insee_dep': False}, '"insee_dep" = 75'),   # text column: no cast for =
    ('"insee_dep" > 75', {'insee_dep': False}, '"insee_dep"::numeric > 75'),
    ("\"nom\" = '\"x\" = 1'", {}, "\"nom\" = '\"x\" = 1'"),           # inside a value
    ('"x"::numeric < 5 AND "x" < 5', {}, '"x"::numeric < 5 AND "x"::numeric < 5'),
])
def test_apply_postgresql_type_casting(to_postgis, expression, layer_fields, expected):
    module = sys.modules[f"{_PKG}.adapters.backends.postgresql.filter_executor"]
    assert module.apply_postgresql_type_casting(expression, _layer(**layer_fields)) == expected
