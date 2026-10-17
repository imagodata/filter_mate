# -*- coding: utf-8 -*-
"""qgis_expression_to_spatialite (dynamic buffer expressions) keeps names and values.

2026-10-17, the SpatiaLite twin of qgis_expression_to_postgis had the same
defects: function names replaced with str.replace anywhere (``"buffer_m"`` ->
``"Buffer_m"``, ``"area_ha"`` -> ``"ST_Area_ha"``), length(string) turned into
ST_Length, ``CAST(... AS REAL)`` added before any comparison (a text compared
with a text became 0 compared with a text), keywords and spaces rewritten
inside values, and ``"nom" ILIKE 'a%'`` rewritten ``"LOWER(nom" LIKE
LOWER('a%'`` (unbalanced).
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[5]
_PKG = "fmtest_sl_executor_pkg"


def _package(name, path):
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    sys.modules[name] = module


@pytest.fixture(scope="module")
def to_spatialite():
    for name, path in ((_PKG, _ROOT), (f"{_PKG}.core", _ROOT / "core"),
                       (f"{_PKG}.core.filter", _ROOT / "core" / "filter"),
                       (f"{_PKG}.adapters", _ROOT / "adapters"),
                       (f"{_PKG}.adapters.backends", _ROOT / "adapters" / "backends"),
                       (f"{_PKG}.adapters.backends.spatialite", _ROOT / "adapters" / "backends" / "spatialite")):
        _package(name, path)
    name = f"{_PKG}.adapters.backends.spatialite.filter_executor"
    spec = importlib.util.spec_from_file_location(name, _ROOT / "adapters" / "backends" / "spatialite" / "filter_executor.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    yield module.qgis_expression_to_spatialite
    for key in [key for key in sys.modules if key == _PKG or key.startswith(f"{_PKG}.")]:
        sys.modules.pop(key, None)


@pytest.mark.parametrize("expression", [
    '"buffer_m"',
    '"area_ha"',
    '"length_m"',
    "\"nature\" <> 'Route'",
    "\"nom\" > 'M'",
    "length(\"nom\") * 2",
    "CASE WHEN \"nom\" = 'Case-Pilote' THEN 10 ELSE 5 END",
    "CASE WHEN \"nom\" = 'Saint  Jean' THEN 10 ELSE 5 END",
])
def test_names_and_values_are_kept(to_spatialite, expression):
    assert to_spatialite(expression) == expression


@pytest.mark.parametrize("expression, expected", [
    ('"buffer_m" * 2', 'CAST("buffer_m" AS REAL) * 2'),
    ('"w" >= 1.5', 'CAST("w" AS REAL) >= 1.5'),
    ('buffer($geometry, 10)', 'Buffer("geometry", 10)'),
    ('area($geometry) / 1000', 'ST_Area("geometry") / 1000'),
    ('length($geometry) / 2', 'ST_Length("geometry") / 2'),
    ("\"nom\" ILIKE 'a%'", "LOWER(\"nom\") LIKE LOWER('a%')"),
    ("\"nom\" NOT ILIKE '%l''ariège%'", "LOWER(\"nom\") NOT LIKE LOWER('%l''ariège%')"),
    ('"x"::numeric * 2', 'CAST("x" AS REAL) * 2'),
    ("if(\"nature\" = 'Route, chemin', 10, 5)", "CASE WHEN \"nature\" = 'Route, chemin' THEN 10 ELSE 5 END"),
])
def test_conversions(to_spatialite, expression, expected):
    assert to_spatialite(expression) == expected
