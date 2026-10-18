# -*- coding: utf-8 -*-
"""The pure geometry of the Zone tool (the shapes of the QGIS selection tools)."""
import importlib.util
import math
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]


def _load():
    name = "fm_zone_tools_test"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _ROOT / "ui" / "tools" / "zone_tools.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


zone = _load()


def test_circle_points_close_on_the_first_vertex():
    points = zone.circle_points(10.0, 20.0, 5.0, 8)
    assert len(points) == 9 and points[0] == points[-1]
    assert all(abs(math.hypot(x - 10.0, y - 20.0) - 5.0) < 1e-9 for x, y in points)


def test_polygon_wkt_closes_the_ring_and_drops_repeats():
    assert zone.polygon_wkt([(0, 0), (1, 0), (1, 0), (1, 1), (0, 0)]) == "POLYGON((0.0 0.0, 1.0 0.0, 1.0 1.0, 0.0 0.0))"


def test_polygon_wkt_needs_three_distinct_vertices():
    assert zone.polygon_wkt([(0, 0), (1, 1)]) == ""
    assert zone.polygon_wkt([(0, 0), (0, 0), (1, 1), (1, 1)]) == ""


def test_shapes_are_the_qgis_selection_ones():
    assert zone.SHAPES == ("rectangle", "polygon", "freehand", "radius")
