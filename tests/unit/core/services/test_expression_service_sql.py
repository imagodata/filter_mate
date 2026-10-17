# -*- coding: utf-8 -*-
"""QGIS -> PostGIS / SpatiaLite conversion keeps values and column names intact.

2026-10-17, ExpressionService._to_postgis / _to_spatialite (the conversion of
the attribute expression of a PostgreSQL / SpatiaLite source layer):

- ``"x"::numeric`` was added whenever a column preceded < > + -, whatever the
  other side: ``"nature" <> 'Route'`` became ``"nature"::numeric <> 'Route'``
  (PostgreSQL: invalid input syntax for type numeric), dates and now() too;
- keywords and spaces were rewritten inside values: ``'Case-Pilote'`` ->
  ``' CASE -Pilote'``, ``'Ce qui est'`` kept but ``'is'`` padded;
- ``length("nom")`` became ``ST_Length`` / ``GLength``: in QGIS length() of a
  string is its number of characters;
- ``ILIKE '%l''ariège%'`` was cut by the ``'([^']+)'`` pattern (SpatiaLite);
- ``'TRUE'`` became ``'1'`` (SpatiaLite).
"""
import pytest

from core.domain.filter_expression import ProviderType
from core.services.expression_service import ExpressionService


def _pg(expression, geometry_column="geom"):
    return ExpressionService().to_sql(expression, ProviderType.POSTGRESQL, geometry_column)


def _sl(expression, geometry_column="geom"):
    return ExpressionService().to_sql(expression, ProviderType.SPATIALITE, geometry_column)


@pytest.mark.parametrize("expression", [
    "\"nature\" <> 'Route'",
    "\"nature\" != 'Route'",
    "\"date_maj\" > '2020-01-01'",
    "\"date_maj\" < now()",
    "\"nom\" = 'Case-Pilote'",
    "\"nom\" = 'Le Bout du Monde'",
    "\"nom\" = 'Saint  Jean'",
    "\"nom\" = 'is not like'",
    "\"a\" + \"b\" = 3",
    "\"end\" = 1",
    "length(\"nom\") > 5",
])
def test_postgis_keeps_the_expression(expression):
    assert _pg(expression) == expression


@pytest.mark.parametrize("expression, expected", [
    ('"population" > 1000', '"population"::numeric > 1000'),
    ('"population" >= 1000.5', '"population"::numeric >= 1000.5'),
    ('"t"."population" < -3', '"t"."population"::numeric < -3'),
    ('"a" - 1 > 2', '"a"::numeric - 1 > 2'),
    ('"a" + 2.5e3 > 2', '"a"::numeric + 2.5e3 > 2'),
    ("\"nom\" ILIKE '%l''ariège%'", "\"nom\"::text ILIKE '%l''ariège%'"),
    ("\"nom\" not like 'a%'", "\"nom\"::text NOT LIKE 'a%'"),
    ('length($geometry) > 100', 'ST_Length("geom") > 100'),
    ('length("geom") > 100', 'ST_Length("geom") > 100'),
    ('$area > 10', 'ST_Area("geom") > 10'),
    ("if(\"nature\" = 'Route, chemin', 1, 0) = 1",
     "CASE WHEN \"nature\" = 'Route, chemin' THEN 1 ELSE 0 END = 1"),
])
def test_postgis_conversion(expression, expected):
    assert _pg(expression) == expected


@pytest.mark.parametrize("expression", [
    "\"nom\" = 'Case-Pilote'",
    "\"x\" = 'TRUE'",
    "\"x\" = 'not false'",
    "length(\"nom\") > 3",
    "\"nom\" = 'Saint  Jean'",
    "\"TRUE\" = 2",
])
def test_spatialite_keeps_the_expression(expression):
    assert _sl(expression) == expression


@pytest.mark.parametrize("expression, expected", [
    ("\"nom\" ILIKE '%l''ariège%'", "LOWER(\"nom\") LIKE LOWER('%l''ariège%')"),
    ("\"nom\" NOT ILIKE 'a%'", "LOWER(\"nom\") NOT LIKE LOWER('a%')"),
    ('"actif" = TRUE', '"actif" = 1'),
    ('length($geometry) > 100', 'GLength("geom") > 100'),
    ('"x"::numeric > 1', 'CAST("x" AS REAL) > 1'),
])
def test_spatialite_conversion(expression, expected):
    assert _sl(expression) == expected


# --- review follow-up (2026-10-17) -------------------------------------------

@pytest.mark.parametrize("expression, expected", [
    # length() of a geometry: $geometry, the geometry column (any case), a geometry function
    ('length(buffer($geometry, 10)) > 5', 'ST_Length(ST_Buffer("geom", 10)) > 5'),
    ('length("GEOM") > 5', 'ST_Length("GEOM") > 5'),
    ('length(st_centroid("geom")) > 0', 'ST_Length(st_centroid("geom")) > 0'),
    ('length(upper("nom")) > 5', 'length(upper("nom")) > 5'),
    # arithmetic compared with a number: every column of the term
    ('"x" - "y" > 0', '"x"::numeric - "y"::numeric > 0'),
    ('"x" * "y" + 1 <= 10', '"x"::numeric * "y"::numeric + 1 <= 10'),
    ('0 < "x"', '0 < "x"::numeric'),
    ('"x" > 10 AND "y" < 5', '"x"::numeric > 10 AND "y"::numeric < 5'),
    ('"x" - "y" = 0', '"x" - "y" = 0'),
    ('"x" <> 5', '"x" <> 5'),
    # QGIS backslash escape -> SQL doubled quote; comments untouched
    ("\"nom\" = 'l\\'eau'", "\"nom\" = 'l''eau'"),
    ("\"a\" = 1 -- c'est case\n AND $area > 3", "\"a\" = 1 -- c'est case\n AND ST_Area(\"geom\") > 3"),
])
def test_postgis_conversion_review(expression, expected):
    assert _pg(expression) == expected


@pytest.mark.parametrize("expression, expected", [
    ('length(buffer($geometry, 10)) > 5', 'GLength(Buffer("geom", 10)) > 5'),
    ('$area > 10', 'ST_Area("geom") > 10'),
    ("\"nom\" = 'l\\'eau'", "\"nom\" = 'l''eau'"),
])
def test_spatialite_conversion_review(expression, expected):
    assert _sl(expression) == expected
