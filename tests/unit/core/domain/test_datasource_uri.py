# -*- coding: utf-8 -*-
"""table_from_uri answers what QgsDataSourceUri(uri) answers: schema(), table(), geometryColumn().

The expected values were produced by QGIS itself on these strings, the same
in 3.44 (qgis/qgis:ltr) and 4.3 (qgis/qgis:latest), 2026-10-27/28, quirks
included: a doubled quote is not an escape, a backslash escapes only the
delimiter and itself (bare values: ``'`` and itself), an unclosed parenthesis
keeps the rest of the string, ``sql=`` swallows the rest, the last ``table=``
wins, ``schema=`` sets the schema a ``table=`` without one keeps.
"""
from unittest.mock import MagicMock

import pytest

from filtermate_core.domain.datasource_uri import geometry_column_from_uri, table_from_uri
from filtermate_core.ports.geometric_filter_port import GeometricFilterPort

pytestmark = pytest.mark.unit

QGIS_ANSWERS = [
    ('dbname=\'gis\' host=localhost port=5432 user=\'u\' sslmode=disable key=\'id\' srid=2154 type=MultiPolygon checkPrimaryKeyUnicity=\'1\' table="public"."roads" (geom) sql=',
     'public', 'roads', 'geom'),
    ('dbname=\'gis\' host=db port=5432 key=\'fid\' table="ign"."batiment" (the_geom)',
     'ign', 'batiment', 'the_geom'),
    ('dbname=\'gis\' table="public"."roads" (geom) sql="nature" = \'A\'',
     'public', 'roads', 'geom'),
    ('dbname=\'gis\' table="public"."roads"(geom)',
     'public', 'roads', 'geom'),
    ('dbname=\'gis\' table="public"."roads"  (geom)  sql=',
     'public', 'roads', 'geom'),
    ('dbname=\'gis\' table="public"."my ""odd"" table" (geom)',
     'public', 'my ', ''),
    ('dbname=\'gis\' table="public"."roads" (geo m)',
     'public', 'roads', 'geo m'),
    ('dbname=\'gis\' table="public"."roads" (g\\)eom)',
     'public', 'roads', 'g)eom'),
    ('dbname=\'gis\' table="public"."roads" sql=',
     'public', 'roads', ''),
    ('dbname=\'gis\' table="public"."roads"',
     'public', 'roads', ''),
    ("dbname='gis' table=roads (geom)",
     '', 'roads', 'geom'),
    ('dbname=\'gis\' table="roads" (geom)',
     '', 'roads', 'geom'),
    ('table="public"."roads" (geom) dbname=\'gis\'',
     'public', 'roads', 'geom'),
    ('dbname=\'x (geom)\' table="t" (g)',
     '', 't', 'g'),
    ('dbname=\'gis\' table="public"."roads" () sql=',
     'public', 'roads', ''),
    ('dbname=\'gis\' table="public"."my \\"odd\\" table" (geom)',
     'public', 'my "odd" table', 'geom'),
    ("dbname='gis' table='roads' (geom)",
     '', 'roads', 'geom'),
    ("dbname='gis' table=public.roads (geom)",
     '', 'public.roads', 'geom'),
    ("dbname='gis' table=roads(geom)",
     '', 'roads(geom)', ''),
    ('dbname=\'gis\' table="public" . "roads" (geom)',
     'public', 'roads', 'geom'),
    ('dbname=\'gis\' table="public"."roads" (g\\\\eom)',
     'public', 'roads', 'g\\eom'),
    ('dbname=\'gis\' table="a" (x) table="b" (y)',
     '', 'b', 'y'),
    ('dbname=\'gis\' table="a" (x) table="b"',
     '', 'b', ''),
    ('dbname=\'gis\' sql=table="b" (y)',
     '', '', ''),
    ('dbname=\'gis\' table = "a" (x)',
     '', 'a', 'x'),
    ('= table="a" (x)',
     '', 'a', 'x'),
    ('dbname=\'gis\' table="public"."roads" (geom',
     'public', 'roads', 'geom'),
    ('key=\'id\' table="" (geom)',
     '', '', 'geom'),
    ('table="public".(geom)',
     'public', '(geom)', ''),
    ('dbname="has \'single\' quotes" table="t" (g)',
     '', 't', 'g'),
    ("dbname='gis' table='public'.'roads' (geom)",
     'public', 'roads', 'geom'),
    ('dbname=\'gis\' table="public".roads (geom)',
     'public', 'roads', 'geom'),
    ('dbname=\'gis\' table="Public Schema"."Roads 2024" (geom)',
     'Public Schema', 'Roads 2024', 'geom'),
    ('dbname=\'gis\' table="public"."" (geom)',
     'public', '', 'geom'),
    ('dbname=\'gis\' table=""."roads" (geom)',
     '', 'roads', 'geom'),
    ('dbname=\'gis\' table="a.b"."c.d" (geom)',
     'a.b', 'c.d', 'geom'),
    ('service=\'pg\' key=\'fid\' table="ign"."batiment" (geometrie) sql="etat" = \'En service\'',
     'ign', 'batiment', 'geometrie'),
    ('dbname=\'/data/db.sqlite\' table="roads" (geometry)',
     '', 'roads', 'geometry'),
    ('dbname=\'C:/data/my db.sqlite\' table="roads" (GEOMETRY) sql=',
     '', 'roads', 'GEOMETRY'),
    ('/data/test.gpkg|layername=roads',
     '', '', ''),
    ('/data/test.gpkg|layername=roads|geometryname=geom',
     '', '', ''),
    ('/data/test.shp',
     '', '', ''),
    ("pagingEnabled='true' srsname='EPSG:2154' typename='bdtopo:batiment' url='https://example.org/wfs' version='auto'",
     '', '', ''),
    ('',
     '', '', ''),
    ('table=',
     '', '', ''),
    ('table="a" (',
     '', 'a', ''),
    ('schema=\'s\' table="t" (g)',
     's', 't', 'g'),
    ('table="a"."t" (g) schema=\'s\'',
     's', 't', 'g'),
    ('table="s"."a" table="b"',
     's', 'b', ''),
    ('schema=\'s\' table="x"."t" (g)',
     'x', 't', 'g'),
    ('schema=s table=t (g)',
     's', 't', 'g'),
    ('schema="s" table="t" (g) schema=\'z\'',
     'z', 't', 'g'),
    ('table="t" (g) schema=\'\'',
     '', 't', 'g'),
    ('table="x\\y" (g)',
     '', 'x\\y', 'g'),
    ('table="x\\\\y" (g)',
     '', 'x\\y', 'g'),
    ('table="x\\"y" (g)',
     '', 'x"y', 'g'),
    ("table='x\\'y' (g)",
     '', "x'y", 'g'),
    ('table=\'x\\"y\' (g)',
     '', 'x\\"y', 'g'),
    ('table="x\\\'y" (g)',
     '', "x\\'y", 'g'),
    ('table="x\\" (g)',
     '', 'x" (g)', ''),
    ('table="s\\.x"."t" (g)',
     's\\.x', 't', 'g'),
    ('table="a" (g\\\\h)',
     '', 'a', 'g\\h'),
    ('table="a" (g\\h)',
     '', 'a', 'g\\h'),
    ('table=x\\y (g)',
     '', 'x\\y', 'g'),
    ('table=x\\\\y (g)',
     '', 'x\\y', 'g'),
    ("table=x\\'y (g)",
     '', "x'y", 'g'),
    ('table=x\\"y (g)',
     '', 'x\\"y', 'g'),
    ('table=x\\ y (g)',
     '', 'x\\', ''),
    ('table=x\\',
     '', 'x', ''),
    ('table=x\\ (g)',
     '', 'x\\', 'g'),
    ('schema=s\\t table=t (g)',
     's\\t', 't', 'g'),
]


@pytest.mark.parametrize("uri, schema, table, column", QGIS_ANSWERS)
def test_same_answers_as_qgis(uri, schema, table, column):
    assert tuple(table_from_uri(uri)) == (schema, table, column)
    assert geometry_column_from_uri(uri) == column


@pytest.mark.parametrize("uri", [None, ''])
def test_empty(uri):
    assert tuple(table_from_uri(uri)) == ('', '', '')
    assert geometry_column_from_uri(uri) == ''


@pytest.mark.parametrize("uri", [42, b"table=t (g)", MagicMock()])
def test_not_a_string_raises_as_qgis(uri):
    # QgsDataSourceUri raises TypeError; the callers fall back to the layer properties on it
    with pytest.raises(TypeError):
        table_from_uri(uri)


class _Port(GeometricFilterPort):
    def build_expression(self, *args, **kwargs):
        return ''

    def apply_filter(self, *args, **kwargs):
        return True

    def supports_layer(self, layer):
        return True


def _layer(provider_column, uri):
    layer = MagicMock()
    layer.dataProvider.return_value.geometryColumn.return_value = provider_column
    layer.dataProvider.return_value.dataSourceUri.return_value = uri
    return layer


@pytest.mark.parametrize("provider_column, uri, expected", [
    ('the_geom', "dbname='gis' table=\"public\".\"roads\" (geom)", 'the_geom'),   # provider first
    ('', "dbname='gis' table=\"public\".\"roads\" (geom)", 'geom'),              # then the URI's table=
    ('', '/data/x.gpkg|layername=roads|geometryname=geometrie', 'geometrie'),   # then geometryname=
    ('', '/data/x.shp', 'fallback'),                                              # then the props
])
def test_detect_geometry_column_without_qgis(provider_column, uri, expected):
    port = _Port({})
    props = {'layer': _layer(provider_column, uri), 'layer_geometry_field': 'fallback'}
    assert port._detect_geometry_column(props) == expected
