# -*- coding: utf-8 -*-
"""Adaptive WKT simplification of a spatial-filter source.

2026-09-13: regression coverage for the "20 m buffer around roads became a
convex hull" bug (the extent-based first tolerance exceeded the maximum and
skipped the loop).

2026-10-16: regression coverage for the "Cross on 691 Toulouse rivers"
bug: the source was generalized by up to 100 m (10 km for "extreme"
reductions), then replaced by a convex hull, so Cross returned 1,181 roads
instead of ~747. Now vertex-level predicates keep the source exact, the
tolerance never exceeds 1 m (or a tenth of the buffer), and there is no
envelope fallback any more.

QGIS is mocked; the geometry is a duck-typed fake whose WKT shrinks with the
simplification tolerance.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from unittest.mock import MagicMock

import pytest

for _name in ("qgis", "qgis.core", "qgis.PyQt", "qgis.PyQt.QtCore"):
    sys.modules.setdefault(_name, MagicMock())

_MODULE_PATH = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "adapters", "qgis", "geometry_preparation.py"
))
_spec = importlib.util.spec_from_file_location("fm_test_geometry_preparation", _MODULE_PATH)
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)

GeometryPreparationAdapter = _mod.GeometryPreparationAdapter
SOURCE_SIMPLIFY_MAX_TOLERANCE = _mod.SOURCE_SIMPLIFY_MAX_TOLERANCE

# The conftest exposes the QGIS classes as the MagicMock type itself; the
# simplification loop needs callable class methods on these two.
_mod.QgsWkbTypes = MagicMock()
_mod.QgsWkbTypes.geometryType = lambda wkb_type: wkb_type
_mod.QgsGeometry = MagicMock()


class _FakeCrs:
    """QgsCoordinateReferenceSystem stand-in: what QGIS answers for these codes."""

    GEOGRAPHIC = {"EPSG:4326", "EPSG:4258", "EPSG:6318", "EPSG:7844", "IGNF:WGS84G", "IGNF:RGF93G"}
    PROJECTED = {"EPSG:2154", "EPSG:3857", "EPSG:4087", "EPSG:4647", "EPSG:4491", "EPSG:4839", "ESRI:102110", "IGNF:LAMB93"}

    def __init__(self, authid=""):
        self._authid = authid

    def isValid(self):
        return self._authid in self.GEOGRAPHIC | self.PROJECTED

    def isGeographic(self):
        return self._authid in self.GEOGRAPHIC


_mod.QgsCoordinateReferenceSystem = _FakeCrs

INTERSECTS = ["ST_Intersects"]
VERTEX_EXACT_PREDICATES = [
    "ST_Crosses", "ST_Touches", "ST_Equals", "ST_Overlaps", "ST_Within", "ST_Contains",
    "ST_Covers", "ST_CoveredBy", "Cross", "Touch", "Equal", "Overlap", "Are within", "Contain",
    "crosses", "touches",
]


class _Rect:
    def __init__(self, size):
        self._size = size

    def width(self):
        return self._size

    def height(self):
        return self._size

    def isEmpty(self):
        return False


class _FakeGeometry:
    """WKT length = ``base // (1 + tolerance * shrink)``; ``floor`` is the size below which it cannot go.

    Every tolerance passed to ``simplify()`` is recorded in ``calls`` (shared
    by the whole family of simplified copies).
    """

    def __init__(self, base, extent=20000.0, tolerance=0.0, shrink=0.05, floor=0, kind="line", calls=None):
        self.base = base
        self.extent = extent
        self.tolerance = tolerance
        self.shrink = shrink
        self.floor = floor
        self.kind = kind
        self.calls = [] if calls is None else calls

    def isEmpty(self):
        return False

    def wkbType(self):
        return 1

    def boundingBox(self):
        return _Rect(self.extent)

    def asWkt(self, precision=None):
        length = max(int(self.base // (1 + self.tolerance * self.shrink)), self.floor)
        return "L" * length

    def simplify(self, tolerance):
        self.calls.append(tolerance)
        return _FakeGeometry(self.base, self.extent, tolerance, self.shrink, self.floor, self.kind, self.calls)

    def convexHull(self):
        return _FakeGeometry(120, self.extent, kind="hull")

    def orientedMinimumBoundingBox(self):
        return (_FakeGeometry(100, self.extent, kind="obb"), 0, 0, 0, 0)


@pytest.fixture
def adapter():
    return GeometryPreparationAdapter(project=MagicMock())


class TestSimplifyGeometryAdaptive:
    def test_first_tolerance_above_maximum_no_longer_skips_the_loop(self, adapter):
        # 200 km extent: the extent-based first guess (200 m × scale) is far
        # above the cap. It used to skip the loop and go to the convex hull;
        # now exactly one attempt is made, at the cap, and the best real
        # simplification is kept although the target is not reached.
        geometry = _FakeGeometry(base=300_000, extent=200_000.0, shrink=0.05)
        result = adapter.simplify_geometry_adaptive(
            geometry, max_wkt_length=100_000, crs_authid="EPSG:2154", predicates=INTERSECTS
        )
        assert geometry.calls == [SOURCE_SIMPLIFY_MAX_TOLERANCE]
        assert result.success
        assert result.geometry.kind == "line"
        assert result.geometry.tolerance == SOURCE_SIMPLIFY_MAX_TOLERANCE
        assert 100_000 < len(result.wkt) < 300_000

    def test_reaches_target_below_the_cap_when_it_can(self, adapter):
        # Small source: the first guess is under the cap and already fits.
        geometry = _FakeGeometry(base=150_000, extent=100.0, shrink=10.0)
        result = adapter.simplify_geometry_adaptive(
            geometry, max_wkt_length=100_000, crs_authid="EPSG:2154", predicates=INTERSECTS
        )
        assert len(result.wkt) <= 100_000
        assert result.geometry.tolerance < SOURCE_SIMPLIFY_MAX_TOLERANCE

    def test_buffer_caps_the_tolerance_and_keeps_best_effort(self, adapter):
        # Cannot reach 100 KB with a 0.5 m tolerance (a tenth of the 5 m
        # buffer): the best simplification is kept, not a convex hull.
        geometry = _FakeGeometry(base=600_000, extent=20_000.0, shrink=0.05)
        result = adapter.simplify_geometry_adaptive(
            geometry, max_wkt_length=100_000, crs_authid="EPSG:2154", buffer_value=5.0, predicates=INTERSECTS
        )
        assert result.success
        assert result.geometry.kind == "line"
        assert result.geometry.tolerance == pytest.approx(0.5)
        assert len(result.wkt) > 100_000

    def test_no_envelope_fallback_even_for_huge_sources(self, adapter, monkeypatch):
        # The 2026-09-13 version replaced this source by its convex hull.
        warned = []
        monkeypatch.setattr(GeometryPreparationAdapter, "_warn_simplified_source",
                            staticmethod(lambda *args: warned.append(args)))
        geometry = _FakeGeometry(base=5_000_000, extent=20_000.0, shrink=0.0001, floor=2_000_000)
        result = adapter.simplify_geometry_adaptive(
            geometry, max_wkt_length=100_000, crs_authid="EPSG:2154", predicates=INTERSECTS
        )
        assert result.success
        assert result.geometry.kind == "line"
        assert result.geometry.tolerance <= SOURCE_SIMPLIFY_MAX_TOLERANCE
        # The warning names the tolerance that was used.
        assert warned and warned[0][3] == result.geometry.tolerance

    def test_small_geometry_returned_untouched(self, adapter):
        geometry = _FakeGeometry(base=5_000)
        result = adapter.simplify_geometry_adaptive(geometry, max_wkt_length=100_000, predicates=INTERSECTS)
        assert result.success
        assert result.geometry is geometry
        assert geometry.calls == []


class TestVertexExactPredicatesKeepTheSource:
    """(a) Cross / Touch / ... sources are never simplified."""

    @pytest.mark.parametrize("predicate", VERTEX_EXACT_PREDICATES)
    def test_vertex_predicate_keeps_source_exact(self, adapter, predicate):
        # The Toulouse rivers: 236,398 chars of WKT, 100 KB target.
        geometry = _FakeGeometry(base=236_398, extent=30_000.0)
        result = adapter.simplify_geometry_adaptive(
            geometry, max_wkt_length=100_000, crs_authid="EPSG:2154", predicates=[predicate]
        )
        assert result.success
        assert result.geometry is geometry
        assert len(result.wkt) == 236_398
        assert geometry.calls == []

    def test_cross_with_intersects_keeps_source_exact(self, adapter):
        geometry = _FakeGeometry(base=236_398)
        result = adapter.simplify_geometry_adaptive(
            geometry, max_wkt_length=100_000, predicates={"ST_Intersects": "ST_Intersects", "ST_Crosses": "ST_Crosses"}
        )
        assert result.geometry is geometry
        assert geometry.calls == []

    @pytest.mark.parametrize("predicates", [None, [], {}])
    def test_unknown_predicates_keep_source_exact(self, adapter, predicates):
        geometry = _FakeGeometry(base=236_398)
        result = adapter.simplify_geometry_adaptive(geometry, max_wkt_length=100_000, predicates=predicates)
        assert result.geometry is geometry
        assert geometry.calls == []

    def test_features_to_wkt_path_forwards_predicates(self, adapter, monkeypatch):
        seen = {}

        def _fake_simplify(**kwargs):
            seen.update(kwargs)
            return _mod.GeometryPreparationResult(success=True, geometry=kwargs["geometry"], wkt="X")

        monkeypatch.setattr(adapter, "simplify_geometry_adaptive", _fake_simplify)
        monkeypatch.setattr(adapter, "_get_wkt_precision", lambda crs: 3)
        feature = MagicMock()
        feature.hasGeometry.return_value = True
        _mod.QgsGeometry = lambda geom: _FakeGeometry(base=236_398)
        try:
            adapter._config.validate_geometries = False
            adapter.features_to_wkt_with_simplification(
                [feature], dissolve=False, max_wkt_length=100_000, predicates=["ST_Crosses"]
            )
        finally:
            _mod.QgsGeometry = MagicMock()
        assert seen["predicates"] == ["ST_Crosses"]

    @pytest.mark.parametrize("predicates, allowed", [
        (["ST_Intersects"], True),
        (["Intersect"], True),
        (["intersects", "disjoint"], True),
        (["ST_Disjoint"], True),
        (["Disjoint"], True),
        (["ST_Crosses"], False),
        (["Cross"], False),
        (["Touch"], False),
        (["ST_Intersects", "ST_Touches"], False),
        (["ST_DWithin"], False),
        (None, False),
    ])
    def test_source_simplification_allowed(self, predicates, allowed):
        assert _mod.source_simplification_allowed(predicates) is allowed


class TestToleranceNeverExceedsTheCap:
    """(b) every tolerance tried stays within 1 m (or a tenth of the buffer)."""

    @pytest.mark.parametrize("extent", [500.0, 20_000.0, 200_000.0, 2_000_000.0])
    @pytest.mark.parametrize("base", [150_000, 1_500_000, 50_000_000])
    @pytest.mark.parametrize("buffer_value", [None, 0.5, 20.0, 500.0, -30.0])
    def test_projected(self, adapter, extent, base, buffer_value):
        geometry = _FakeGeometry(base=base, extent=extent, shrink=0.001, floor=base // 3)
        adapter.simplify_geometry_adaptive(
            geometry, max_wkt_length=100_000, crs_authid="EPSG:2154",
            buffer_value=buffer_value, predicates=INTERSECTS,
        )
        cap = SOURCE_SIMPLIFY_MAX_TOLERANCE
        if buffer_value:
            cap = min(cap, abs(buffer_value) / 10.0)
        assert geometry.calls, "an Intersects source above the target is simplified"
        assert max(geometry.calls) <= cap + 1e-12
        # The cap itself is tried before giving up.
        assert max(geometry.calls) == pytest.approx(cap)

    @pytest.mark.parametrize("extent", [0.01, 1.0, 20.0])
    def test_geographic(self, adapter, extent):
        geometry = _FakeGeometry(base=1_500_000, extent=extent, shrink=0.0, floor=1_000_000)
        adapter.simplify_geometry_adaptive(
            geometry, max_wkt_length=100_000, crs_authid="EPSG:4326", predicates=INTERSECTS
        )
        assert geometry.calls
        assert max(geometry.calls) <= SOURCE_SIMPLIFY_MAX_TOLERANCE / 111000.0 + 1e-15

    def test_toulouse_rivers_intersects(self, adapter):
        # 236 KB of rivers over ~30 km: the old code jumped to 100 m.
        geometry = _FakeGeometry(base=236_398, extent=30_000.0, shrink=0.05)
        result = adapter.simplify_geometry_adaptive(
            geometry, max_wkt_length=100_000, crs_authid="EPSG:2154", predicates=INTERSECTS
        )
        assert max(geometry.calls) <= SOURCE_SIMPLIFY_MAX_TOLERANCE
        assert result.geometry.tolerance <= SOURCE_SIMPLIFY_MAX_TOLERANCE


class TestGeographicCrsDetection:
    """2026-10-16: QGIS decides; the 4000 < srid < 5000 guess was wrong both ways."""

    @pytest.mark.parametrize("authid", ["EPSG:4326", "EPSG:6318", "EPSG:7844", "IGNF:WGS84G", "IGNF:RGF93G"])
    def test_geographic(self, adapter, authid):
        assert adapter._is_geographic_crs(authid) is True
        assert adapter._get_wkt_precision_from_authid(authid) == 8

    @pytest.mark.parametrize("authid", ["EPSG:2154", "EPSG:4087", "EPSG:4647", "EPSG:4491", "EPSG:4839", "ESRI:102110", "IGNF:LAMB93"])
    def test_projected(self, adapter, authid):
        assert adapter._is_geographic_crs(authid) is False
        assert adapter._get_wkt_precision_from_authid(authid) == 3

    @pytest.mark.parametrize("authid", [None, "", "FOO:1"])
    def test_unknown_gets_the_safe_answer(self, adapter, authid):
        # Finest precision, smallest tolerance.
        assert adapter._is_geographic_crs(authid) is True

    def test_ignf_geographic_source_tolerance_is_in_degrees(self, adapter):
        geometry = _FakeGeometry(base=1_500_000, extent=0.5, shrink=0.0, floor=1_000_000)
        adapter.simplify_geometry_adaptive(geometry, max_wkt_length=100_000, crs_authid="IGNF:WGS84G", predicates=INTERSECTS)
        assert max(geometry.calls) <= SOURCE_SIMPLIFY_MAX_TOLERANCE / 111000.0 + 1e-15
