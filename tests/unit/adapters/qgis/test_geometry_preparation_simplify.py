# -*- coding: utf-8 -*-
"""Adaptive WKT simplification limits (2026-09-13).

Regression coverage for the "20 m buffer around roads became a convex hull"
bug: the extent-based first tolerance exceeded the maximum and skipped the
loop, and any source over the target size fell back to an envelope. QGIS is
mocked; the geometry is a duck-typed fake whose WKT shrinks with the
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

# The conftest exposes the QGIS classes as the MagicMock type itself; the
# simplification loop needs callable class methods on these two.
_mod.QgsWkbTypes = MagicMock()
_mod.QgsWkbTypes.geometryType = lambda wkb_type: wkb_type
_mod.QgsGeometry = MagicMock()


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
    """WKT length = ``base // (1 + tolerance * shrink)``; ``floor`` is the size below which it cannot go."""

    def __init__(self, base, extent=20000.0, tolerance=0.0, shrink=0.05, floor=0, kind="line"):
        self.base = base
        self.extent = extent
        self.tolerance = tolerance
        self.shrink = shrink
        self.floor = floor
        self.kind = kind

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
        return _FakeGeometry(self.base, self.extent, tolerance, self.shrink, self.floor, self.kind)

    def convexHull(self):
        return _FakeGeometry(120, self.extent, kind="hull")

    def orientedMinimumBoundingBox(self):
        return (_FakeGeometry(100, self.extent, kind="obb"), 0, 0, 0, 0)


@pytest.fixture
def adapter():
    return GeometryPreparationAdapter(project=MagicMock())


class TestSimplifyGeometryAdaptive:
    def test_first_tolerance_above_maximum_no_longer_skips_the_loop(self, adapter):
        # 200 km extent: extent-based first guess (200 m × scale) > 100 m maximum.
        geometry = _FakeGeometry(base=300_000, extent=200_000.0)
        result = adapter.simplify_geometry_adaptive(geometry, max_wkt_length=100_000, crs_authid="EPSG:2154")
        assert result.success
        assert result.geometry.kind == "line"
        assert 0 < result.geometry.tolerance <= 100.0
        assert len(result.wkt) <= 100_000

    def test_buffer_caps_the_tolerance_and_keeps_best_effort(self, adapter):
        # Cannot reach 100 KB with a 2 m tolerance: the best simplification is
        # kept (under the hard limit), not a convex hull.
        geometry = _FakeGeometry(base=600_000, extent=20_000.0, shrink=0.05)
        result = adapter.simplify_geometry_adaptive(
            geometry, max_wkt_length=100_000, crs_authid="EPSG:2154", buffer_value=20.0
        )
        assert result.success
        assert result.geometry.kind == "line"
        assert result.geometry.tolerance <= 2.0
        assert 100_000 < len(result.wkt) <= 1_000_000

    def test_envelope_fallback_only_beyond_the_hard_limit(self, adapter, monkeypatch):
        warned = []
        monkeypatch.setattr(GeometryPreparationAdapter, "_warn_approximate_filter",
                            staticmethod(lambda length, limit: warned.append((length, limit))))
        geometry = _FakeGeometry(base=5_000_000, extent=20_000.0, shrink=0.0001, floor=2_000_000)
        result = adapter.simplify_geometry_adaptive(geometry, max_wkt_length=100_000, crs_authid="EPSG:2154")
        assert result.success
        assert result.geometry.kind == "hull"
        assert warned and warned[0][1] == 1_000_000

    def test_small_geometry_returned_untouched(self, adapter):
        geometry = _FakeGeometry(base=5_000)
        result = adapter.simplify_geometry_adaptive(geometry, max_wkt_length=100_000)
        assert result.success
        assert result.geometry is geometry
