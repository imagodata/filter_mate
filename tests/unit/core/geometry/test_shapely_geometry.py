# -*- coding: utf-8 -*-
"""filtermate_core.geometry: IGeometry on shapely and the union semantics of the spatial filter.

The union cases are the ones where testing each source feature alone gives
another answer (the bug the SQL backends fixed on 2026-10-17): a target
spanning two adjacent sources is within their union, a target holding one
source does not contain the union, a target touching one source is not
disjoint from the union.
"""
import pytest

from filtermate_core.domain.filter_expression import SpatialPredicate
from filtermate_core.ports.qgis_port import BoundingBox, CoordinateReferenceSystem, GeometryType, IGeometry

shapely = pytest.importorskip("shapely")

from filtermate_core.geometry import shapely_geometry as sg  # noqa: E402
from filtermate_core.geometry import ShapelyGeometry, matches, normalize_predicate, source_union  # noqa: E402

pytestmark = pytest.mark.unit

WGS84 = CoordinateReferenceSystem("EPSG:4326", "WGS 84", True)
LAMBERT93 = CoordinateReferenceSystem("EPSG:2154", "RGF93 v1 / Lambert-93", False)

LEFT = "POLYGON ((0 0, 10 0, 10 10, 0 10, 0 0))"
RIGHT = "POLYGON ((10 0, 20 0, 20 10, 10 10, 10 0))"


def g(wkt, crs=None):
    return ShapelyGeometry.from_wkt(wkt, crs)


class TestGeometryPort:
    def test_is_an_igeometry(self):
        assert isinstance(g("POINT (1 2)"), IGeometry)

    @pytest.mark.parametrize("wkt, expected", [
        ("POINT (1 2)", GeometryType.POINT),
        ("LINESTRING (0 0, 1 1)", GeometryType.LINE),
        (LEFT, GeometryType.POLYGON),
        ("MULTIPOINT ((0 0), (1 1))", GeometryType.MULTI_POINT),
        ("MULTILINESTRING ((0 0, 1 1), (2 2, 3 3))", GeometryType.MULTI_LINE),
        ("MULTIPOLYGON (((0 0, 1 0, 1 1, 0 0)))", GeometryType.MULTI_POLYGON),
        ("GEOMETRYCOLLECTION (POINT (0 0))", GeometryType.GEOMETRY_COLLECTION),
        ("POINT Z (1 2 3)", GeometryType.POINT),
        ("POLYGON EMPTY", GeometryType.UNKNOWN),
    ])
    def test_geometry_type(self, wkt, expected):
        assert g(wkt).geometry_type() is expected

    def test_empty_behaves_as_the_qgis_adapter(self):
        empty = g("POLYGON EMPTY")
        assert empty.is_empty() and not empty.is_valid()
        assert empty.as_wkt() == "" and empty.as_wkb() == b""
        assert empty.bounding_box() == BoundingBox(0.0, 0.0, 0.0, 0.0)
        assert empty.buffer(5).is_empty()

    def test_invalid_polygon(self):
        bowtie = g("POLYGON ((0 0, 10 10, 10 0, 0 10, 0 0))")
        assert not bowtie.is_valid() and not bowtie.is_empty()

    def test_wkt_and_wkb_round_trip_at_full_precision(self):
        point = g("POINT (1.123456789012 2.5)", WGS84)
        assert ShapelyGeometry.from_wkt(point.as_wkt()) == ShapelyGeometry(point.shape)
        assert ShapelyGeometry.from_wkb(point.as_wkb(), WGS84) == point

    def test_bounding_box(self):
        assert g(RIGHT).bounding_box() == BoundingBox(10.0, 0.0, 20.0, 10.0)

    def test_buffer_counts_segments_per_quarter_circle(self):
        disc = g("POINT (0 0)").buffer(1.0, segments=5)
        assert len(disc.shape.exterior.coords) == 4 * 5 + 1
        assert disc.geometry_type() is GeometryType.POLYGON

    def test_buffer_keeps_the_crs(self):
        assert g("POINT (0 0)", LAMBERT93).buffer(10).crs == LAMBERT93

    def test_other_operand_may_be_another_igeometry(self):
        class Foreign(IGeometry):
            """Another implementation: only its WKB is read."""
            def __init__(self, wkt):
                self._wkb = shapely.from_wkt(wkt).wkb

            def as_wkb(self):
                return self._wkb

            is_valid = is_empty = geometry_type = as_wkt = buffer = intersects = contains = None
            bounding_box = transform = None

        assert g(LEFT).intersects(Foreign("POINT (5 5)"))
        assert not g(LEFT).contains(Foreign("POINT (50 5)"))


class TestTransform:
    def test_lambert93_origin(self):
        pytest.importorskip("pyproj")
        # Lambert-93 is defined with (3° E, 46.5° N) at (700000, 6600000)
        projected = g("POINT (3 46.5)", WGS84).transform(LAMBERT93)
        assert projected.crs == LAMBERT93
        x, y = projected.shape.coords[0]
        assert x == pytest.approx(700000.0, abs=1e-3)
        assert y == pytest.approx(6600000.0, abs=1e-3)

    def test_polygon_and_z_survive(self):
        pytest.importorskip("pyproj")
        square = g("POLYGON ((3 46, 3.1 46, 3.1 46.1, 3 46.1, 3 46))", WGS84).transform(LAMBERT93)
        assert square.geometry_type() is GeometryType.POLYGON
        assert len(square.shape.exterior.coords) == 5
        point = g("POINT Z (3 46.5 120)", WGS84).transform(LAMBERT93)
        assert point.shape.has_z and point.shape.coords[0][2] == pytest.approx(120.0)

    def test_same_crs_is_a_copy(self):
        point = g("POINT (3 46.5)", WGS84)
        assert point.transform(WGS84) == point

    def test_unknown_source_crs_is_refused(self):
        # the QGIS adapter silently returns a copy; reprojecting without a
        # source CRS would only move the error further
        with pytest.raises(ValueError):
            g("POINT (3 46.5)").transform(LAMBERT93)

    def test_without_pyproj(self, monkeypatch):
        monkeypatch.setattr(sg, "PYPROJ_AVAILABLE", False)
        with pytest.raises(RuntimeError, match="pyproj"):
            g("POINT (3 46.5)", WGS84).transform(LAMBERT93)


class TestPredicateNames:
    @pytest.mark.parametrize("name, expected", [
        ("intersects", "intersects"),
        ("ST_Intersects", "intersects"),
        ("ST_CoveredBy", "coveredby"),
        ("covered_by", "coveredby"),
        ("ST_DWithin", "dwithin"),
        (SpatialPredicate.TOUCHES, "touches"),
        (" Disjoint ", "disjoint"),
    ])
    def test_normalize(self, name, expected):
        assert normalize_predicate(name) == expected

    def test_every_domain_predicate_is_known(self):
        for predicate in SpatialPredicate:
            normalize_predicate(predicate)

    @pytest.mark.parametrize("name", ["near", "ST_Nearby", ""])
    def test_unknown(self, name):
        with pytest.raises(ValueError):
            normalize_predicate(name)


class TestUnionSemantics:
    @pytest.fixture
    def adjacent(self):
        return source_union([g(LEFT), g(RIGHT)])

    def test_within_the_union_of_adjacent_sources(self, adjacent):
        spanning = g("POLYGON ((5 2, 15 2, 15 8, 5 8, 5 2))")
        assert matches(spanning, adjacent, {"within": True})
        # feature by feature it is within neither
        assert not any(spanning.satisfies(g(w), "within") for w in (LEFT, RIGHT))

    def test_contains_needs_every_source(self, adjacent):
        holds_left = g("POLYGON ((-1 -1, 11 -1, 11 11, -1 11, -1 -1))")
        assert not matches(holds_left, adjacent, {"contains": True})
        assert holds_left.satisfies(g(LEFT), "contains")

    def test_disjoint_from_every_source(self, adjacent):
        touches_right_only = g("POLYGON ((20 0, 30 0, 30 10, 20 10, 20 0))")
        assert not matches(touches_right_only, adjacent, {"disjoint": True})
        assert touches_right_only.satisfies(g(LEFT), "disjoint")
        assert matches(g("POINT (50 50)"), adjacent, {"disjoint": True})

    def test_predicates_are_ored(self, adjacent):
        outside = g("POINT (50 50)")
        assert not matches(outside, adjacent, {"intersects": True, "touches": True})
        assert matches(outside, adjacent, {"intersects": True, "disjoint": True})
        assert matches(outside, adjacent, ["ST_Intersects", SpatialPredicate.DISJOINT])

    def test_disabled_predicates_are_ignored(self, adjacent):
        assert not matches(g("POINT (50 50)"), adjacent, {"intersects": True, "disjoint": False})

    def test_positive_buffer_grows_the_source(self):
        source = source_union([g("POINT (0 0)")], buffer_distance=10)
        assert matches(g("POINT (5 0)"), source, {"intersects": True})
        assert not matches(g("POINT (15 0)"), source, {"intersects": True})

    def test_negative_buffer_erodes_the_union_not_each_feature(self):
        eroded = source_union([g(LEFT), g(RIGHT)], buffer_distance=-4)
        on_the_shared_edge = g("POINT (10 5)")
        assert matches(on_the_shared_edge, eroded, {"intersects": True})
        # eroding each square alone leaves a gap there
        each = source_union([g(LEFT).buffer(-4).shape, g(RIGHT).buffer(-4).shape])
        assert not matches(on_the_shared_edge, each, {"intersects": True})

    def test_invalid_sources_are_made_valid(self):
        bowtie = g("POLYGON ((0 0, 10 10, 10 0, 0 10, 0 0))")
        union = source_union([bowtie, g(RIGHT)])
        assert union.is_valid()
        assert matches(g("POINT (2 5)"), union, {"intersects": True})

    def test_missing_and_empty_sources_are_skipped(self):
        union = source_union([None, g("POLYGON EMPTY"), g(LEFT)])
        assert union.shape.equals(g(LEFT).shape)

    def test_no_source_keeps_only_disjoint_targets(self):
        nothing = source_union([])
        assert not matches(g("POINT (1 1)"), nothing, {"intersects": True})
        assert matches(g("POINT (1 1)"), nothing, {"disjoint": True})

    def test_union_keeps_the_given_crs(self):
        assert source_union([g(LEFT)], crs=LAMBERT93).crs == LAMBERT93

    @pytest.mark.parametrize("target", [None, "POINT EMPTY"])
    def test_target_without_geometry_is_never_kept(self, adjacent, target):
        geometry = g(target) if target else None
        assert not matches(geometry, adjacent, {"disjoint": True})

    def test_dwithin_needs_a_distance(self, adjacent):
        point = g("POINT (25 5)")
        assert matches(point, adjacent, {"dwithin": True}, distance=6)
        assert not matches(point, adjacent, {"dwithin": True}, distance=4)
        with pytest.raises(ValueError, match="distance"):
            matches(point, adjacent, {"dwithin": True})

    def test_no_predicate_enabled_is_an_error(self, adjacent):
        with pytest.raises(ValueError, match="no spatial predicate"):
            matches(g("POINT (1 1)"), adjacent, {"intersects": False})

    def test_accepts_plain_shapely_geometries(self):
        assert matches(shapely.Point(5, 5), shapely.from_wkt(LEFT), {"intersects": True})


def test_without_shapely(monkeypatch):
    monkeypatch.setattr(sg, "SHAPELY_AVAILABLE", False)
    with pytest.raises(RuntimeError, match="shapely"):
        ShapelyGeometry()
    with pytest.raises(RuntimeError, match="shapely"):
        source_union([])
