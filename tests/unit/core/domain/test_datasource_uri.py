# -*- coding: utf-8 -*-
"""geometry_column_from_uri answers what QgsDataSourceUri(uri).geometryColumn() answers.

The expected values were produced by QGIS itself on these strings, the same
in 3.44 (qgis/qgis:ltr) and 4.3 (qgis/qgis:latest), 2026-10-27, quirks included: a doubled quote is not an escape, an
unclosed parenthesis keeps the rest of the string, ``sql=`` swallows the rest,
the last ``table=`` wins.
"""
from unittest.mock import MagicMock

import pytest

from filtermate_core.domain.datasource_uri import geometry_column_from_uri
from filtermate_core.ports.geometric_filter_port import GeometricFilterPort

pytestmark = pytest.mark.unit

QGIS_ANSWERS = [
    ('dbname=\'gis\' host=localhost port=5432 user=\'u\' sslmode=disable key=\'id\' srid=2154 type=MultiPolygon checkPrimaryKeyUnicity=\'1\' table="public"."roads" (geom) sql=',
     'geom'),
    ('dbname=\'gis\' host=db port=5432 key=\'fid\' table="ign"."batiment" (the_geom)',
     'the_geom'),
    ('dbname=\'gis\' table="public"."roads" (geom) sql="nature" = \'A\'',
     'geom'),
    ('dbname=\'gis\' table="public"."roads"(geom)',
     'geom'),
    ('dbname=\'gis\' table="public"."roads"  (geom)  sql=',
     'geom'),
    ('dbname=\'gis\' table="public"."my ""odd"" table" (geom)',
     ''),
    ('dbname=\'gis\' table="public"."roads" (geo m)',
     'geo m'),
    ('dbname=\'gis\' table="public"."roads" (g\\)eom)',
     'g)eom'),
    ('dbname=\'gis\' table="public"."roads" sql=',
     ''),
    ('dbname=\'gis\' table="public"."roads"',
     ''),
    ("dbname='gis' table=roads (geom)",
     'geom'),
    ('dbname=\'gis\' table="roads" (geom)',
     'geom'),
    ('table="public"."roads" (geom) dbname=\'gis\'',
     'geom'),
    ('dbname=\'x (geom)\' table="t" (g)',
     'g'),
    ('dbname=\'gis\' table="public"."roads" () sql=',
     ''),
    ('dbname=\'gis\' table="public"."my \\"odd\\" table" (geom)',
     'geom'),
    ("dbname='gis' table='roads' (geom)",
     'geom'),
    ("dbname='gis' table=public.roads (geom)",
     'geom'),
    ("dbname='gis' table=roads(geom)",
     ''),
    ('dbname=\'gis\' table="public" . "roads" (geom)',
     'geom'),
    ('dbname=\'gis\' table="public"."roads" (g\\\\eom)',
     'g\\eom'),
    ('dbname=\'gis\' table="a" (x) table="b" (y)',
     'y'),
    ('dbname=\'gis\' table="a" (x) table="b"',
     ''),
    ('dbname=\'gis\' sql=table="b" (y)',
     ''),
    ('dbname=\'gis\' table = "a" (x)',
     'x'),
    ('= table="a" (x)',
     'x'),
    ('dbname=\'gis\' table="public"."roads" (geom',
     'geom'),
    ('key=\'id\' table="" (geom)',
     'geom'),
    ('table="public".(geom)',
     ''),
    ('dbname="has \'single\' quotes" table="t" (g)',
     'g'),
    ('dbname=\'/data/db.sqlite\' table="roads" (geometry)',
     'geometry'),
    ('dbname=\'C:/data/my db.sqlite\' table="roads" (GEOMETRY) sql=',
     'GEOMETRY'),
    ('/data/test.gpkg|layername=roads',
     ''),
    ('/data/test.gpkg|layername=roads|geometryname=geom',
     ''),
    ('/data/test.shp',
     ''),
    ("pagingEnabled='true' srsname='EPSG:2154' typename='bdtopo:batiment' url='https://example.org/wfs' version='auto'",
     ''),
    ('',
     ''),
    ('table=',
     ''),
    ('table="a" (',
     ''),
]


@pytest.mark.parametrize("uri, expected", QGIS_ANSWERS)
def test_same_column_as_qgis(uri, expected):
    assert geometry_column_from_uri(uri) == expected


def test_none_and_empty():
    assert geometry_column_from_uri(None) == ''
    assert geometry_column_from_uri('') == ''


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
