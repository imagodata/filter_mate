# -*- coding: utf-8 -*-
"""domain.wkt_bounds: where it answers, it answers QgsGeometry.fromWkt(wkt).boundingBox().

The QGIS values were produced by QGIS 3.44 and 4.3 (identical) on 2026-10-28.
On 20 000 random linear WKT (spacing and case variants included) the reader
answered every one; it equalled QGIS on all those without interior rings and
contained QGIS's box on the others: QGIS boxes a polygon by its exterior ring
only, which a hole outside the shell (an invalid polygon) can exceed once made
valid. A larger box only adds R-tree candidates; a smaller one drops features.
"""
import pytest

from filtermate_core.domain.wkt_bounds import wkt_bounds

pytestmark = pytest.mark.unit

# (wkt, QgsGeometry bounding box)
QGIS_ANSWERED = [
    ('POINT (3 46.5)', (3.0, 46.5, 3.0, 46.5)),
    ('POINT(0 0)', (0.0, 0.0, 0.0, 0.0)),
    ('POINT (-1.5e3 2E-2)', (-1500.0, 0.02, -1500.0, 0.02)),
    ('point (1 2)', (1.0, 2.0, 1.0, 2.0)),
    ('  POINT  (  1   2  )  ', (1.0, 2.0, 1.0, 2.0)),
    ('POINT Z (1 2 3)', (1.0, 2.0, 1.0, 2.0)),
    ('POINT M (1 2 3)', (1.0, 2.0, 1.0, 2.0)),
    ('POINT ZM (1 2 3 4)', (1.0, 2.0, 1.0, 2.0)),
    ('POINT (1 2 3)', (1.0, 2.0, 1.0, 2.0)),
    ('LINESTRING (0 0, 10 5, -3 7)', (-3.0, 0.0, 10.0, 7.0)),
    ('LINESTRING Z (0 0 100, 10 5 -100)', (0.0, 0.0, 10.0, 5.0)),
    ('POLYGON ((0 0, 10 0, 10 10, 0 10, 0 0))', (0.0, 0.0, 10.0, 10.0)),
    ('POLYGON ((0 0, 10 0, 10 10, 0 0), (2 1, 3 1, 3 2, 2 1))', (0.0, 0.0, 10.0, 10.0)),
    ('MULTIPOINT ((1 2), (3 4))', (1.0, 2.0, 3.0, 4.0)),
    ('MULTIPOINT (1 2, 3 4)', (1.0, 2.0, 3.0, 4.0)),
    ('MULTILINESTRING ((0 0, 1 1), (5 5, 6 -6))', (0.0, -6.0, 6.0, 5.0)),
    ('MULTIPOLYGON (((0 0, 1 0, 1 1, 0 0)), ((5 5, 6 5, 6 6, 5 5)))', (0.0, 0.0, 6.0, 6.0)),
    ('GEOMETRYCOLLECTION (POINT (1 2), LINESTRING (5 5, 9 -1))', (1.0, -1.0, 9.0, 5.0)),
    ('LINESTRING (0 0)', (0.0, 0.0, 0.0, 0.0)),
    ('POINT (700000.123456789 6600000.987654321)', (700000.123456789, 6600000.987654321, 700000.123456789, 6600000.987654321)),
    ('POLYGON ((0 0, 0 0, 0 0, 0 0))', (0.0, 0.0, 0.0, 0.0)),
    ('LINESTRING (5 5, 5 5)', (5.0, 5.0, 5.0, 5.0)),
]

# (wkt, QgsGeometry bounding box or None): the reader does not answer for these
NOT_ANSWERED = [
    ('POINTZ (1 2 3)', (1.0, 2.0, 1.0, 2.0)),
    ('POINT EMPTY', None),
    ('POLYGON EMPTY', None),
    ('GEOMETRYCOLLECTION EMPTY', None),
    ('', None),
    ('MULTIPOINT (EMPTY, (1 2))', None),
    ('GEOMETRYCOLLECTION (POINT EMPTY, POINT (4 4))', (4.0, 4.0, 4.0, 4.0)),
    ('CIRCULARSTRING (0 0, 1 1, 2 0)', (0.0, 0.0, 2.0, 1.0)),
    ('COMPOUNDCURVE ((0 0, 1 0), CIRCULARSTRING (1 0, 2 1, 3 0))', (0.0, 0.0, 3.0, 1.0)),
    ('CURVEPOLYGON (CIRCULARSTRING (0 0, 4 0, 4 4, 0 4, 0 0))', (-0.8284271247461903, -0.8284271247461903, 4.82842712474619, 4.82842712474619)),
    ('MULTICURVE ((0 0, 1 1))', (0.0, 0.0, 1.0, 1.0)),
    ('MULTISURFACE (((0 0, 1 0, 1 1, 0 0)))', (0.0, 0.0, 1.0, 1.0)),
    ('TRIANGLE ((0 0, 1 0, 0 1, 0 0))', (0.0, 0.0, 1.0, 1.0)),
    ('POLYHEDRALSURFACE Z (((0 0 0, 0 1 0, 1 1 0, 0 0 0)))', (0.0, 0.0, 1.0, 1.0)),
    ('TIN (((0 0 0, 0 1 0, 1 1 0, 0 0 0)))', (0.0, 0.0, 1.0, 1.0)),
    ('SRID=4326;POINT (1 2)', None),
    ('POINT (1 2', (1.0, 2.0, 1.0, 2.0)),
    ('POINT (a b)', None),
    ('NOT A WKT', None),
    ('POINT (nan 1)', None),
    ('POINT (inf 1)', None),
    ('POINT (1e400 1)', (float('inf'), 1.0, float('inf'), 1.0)),
]


@pytest.mark.parametrize("wkt, qgis", QGIS_ANSWERED)
def test_same_box_as_qgis(wkt, qgis):
    assert wkt_bounds(wkt) == qgis


@pytest.mark.parametrize("wkt, qgis", NOT_ANSWERED)
def test_not_answered(wkt, qgis):
    # curves (their box follows the arcs), EMPTY parts, EWKT, NaN, malformed text
    assert wkt_bounds(wkt) is None


def test_a_hole_outside_the_shell_widens_the_box():
    # QGIS: (0, 0, 10, 10), the exterior ring; made valid, the hole is a polygon of its own
    wkt = 'POLYGON ((0 0, 10 0, 10 10, 0 10, 0 0), (20 20, 30 20, 30 30, 20 30, 20 20))'
    assert wkt_bounds(wkt) == (0.0, 0.0, 30.0, 30.0)


@pytest.mark.parametrize("wkt", [
    'POINT (1 2) POINT (3 4)', 'MULTIPOINT (POINT (1 2))', 'POINT ((1 2))', 'LINESTRING (1, 2)',
    'POINT (1 2 3 4 5)', 'POINT (1)', 'POLYGON (0 0, 1 0, 1 1, 0 0)', None, 42, '   ',
    # QGIS and SpatiaLite read neither Unicode digits nor non-ASCII spaces
    'POINT (\u0661 \u0662)', 'POINT (1\xa02)', 'POINT (1\u20282)',
    'POINT(1.2.3 4)', 'POINT (1e5.5 2)',
])
def test_malformed_or_not_text(wkt):
    assert wkt_bounds(wkt) is None


def test_deep_nesting_answers_none():
    wkt = 'GEOMETRYCOLLECTION (' * 5000 + 'POINT (1 2)' + ')' * 5000
    assert wkt_bounds(wkt) is None
