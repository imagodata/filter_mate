# -*- coding: utf-8 -*-
"""FilterMate 5 object detection on a point cloud: the cluster of points of a class under a click."""
import importlib.util
import pathlib
import sys
import types

import pytest

np = pytest.importorskip("numpy")

pytestmark = pytest.mark.unit


def _fakes():
    if "fm_coverage_fakes" not in sys.modules:
        spec = importlib.util.spec_from_file_location("fm_coverage_fakes", pathlib.Path(__file__).with_name("coverage_fakes.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules["fm_coverage_fakes"] = module
        spec.loader.exec_module(module)
    return sys.modules["fm_coverage_fakes"]


fk = _fakes()
objects = fk.load("point_cloud_objects")
footprint = fk.load("point_cloud_footprint")
geometry_tools = fk.load("geometry_tools")


def _grid_points(x0, y0, x1, y1, step=0.5):
    """Points every ``step`` over a rectangle (a roof read at the level of detail of 1 m)."""
    xs, ys = np.meshgrid(np.arange(x0 + step / 2, x1, step), np.arange(y0 + step / 2, y1, step))
    return xs.ravel(), ys.ravel()


class Cloud:
    """The points of one class; ``read`` answers :func:`grow_object` and records the rectangles read."""

    def __init__(self, *rectangles, step=0.5):
        parts = [_grid_points(*rectangle, step=step) for rectangle in rectangles]
        self.xs = np.concatenate([p[0] for p in parts]) if parts else np.zeros(0)
        self.ys = np.concatenate([p[1] for p in parts]) if parts else np.zeros(0)
        self.reads = []

    def read(self, xmin, ymin, xmax, ymax):
        self.reads.append((xmin, ymin, xmax, ymax))
        inside = (self.xs > xmin) & (self.xs < xmax) & (self.ys > ymin) & (self.ys < ymax)
        return self.xs[inside], self.ys[inside]


class TestWindow:
    def test_the_clicked_cell_is_the_centre(self):
        left, top, size = objects.object_window(1000.4, 2000.7, 32.0, 1.0)
        assert size == 65
        assert (left + 32, top - 33) == (1000.0, 2000.0)  # the clicked cell: [1000, 1001] x [2000, 2001]

    def test_the_cells_keep_their_bounds_when_the_window_grows(self):
        small = objects.object_window(1000.4, 2000.7, 32.0, 1.0)
        large = objects.object_window(1000.4, 2000.7, 128.0, 1.0)
        assert large[2] == 257
        assert (small[0] - large[0]) == 96.0 and (large[1] - small[1]) == 96.0  # whole cells apart

    def test_negative_coordinates(self):
        left, top, size = objects.object_window(-0.5, -0.5, 2.0, 1.0)
        assert (left, top, size) == (-3.0, 2.0, 5)


class TestBinning:
    def test_cells_with_points_and_their_neighbours(self):
        mask, rows, cols = objects.bin_points([2.5], [2.5], 0.0, 5.0, 1.0, 5, dilate_cells=1)
        assert mask.sum() == 5 and mask[2, 2] and mask[1, 2] and mask[2, 3] and not mask[1, 1]  # a diamond
        assert (rows.tolist(), cols.tolist()) == ([2], [2])

    def test_points_just_outside_grow_the_border(self):
        mask, rows, cols = objects.bin_points([-0.5], [2.5], 0.0, 5.0, 1.0, 5, dilate_cells=1)
        assert mask[2, 0] and mask.sum() == 1
        assert (rows.tolist(), cols.tolist()) == ([-1], [-1])  # not in the grid itself

    def test_far_points_are_left_out(self):
        mask, _rows, _cols = objects.bin_points([50.0, -20.0], [2.5, 2.5], 0.0, 5.0, 1.0, 5)
        assert not mask.any()

    def test_without_dilation(self):
        mask, _rows, _cols = objects.bin_points([0.5, 4.5], [4.5, 0.5], 0.0, 5.0, 1.0, 5, dilate_cells=0)
        assert mask.sum() == 2 and mask[0, 0] and mask[4, 4]


class TestSeed:
    def test_the_clicked_cell_when_it_holds_points(self):
        mask = np.zeros((5, 5), dtype=bool)
        mask[2, 2] = True
        assert objects.seed_cell(mask, 2, 2, 0) == (2, 2)

    def test_the_nearest_cell_within_the_radius(self):
        mask = np.zeros((7, 7), dtype=bool)
        mask[3, 5] = mask[0, 3] = True
        assert objects.seed_cell(mask, 3, 3, 2) == (3, 5)
        assert objects.seed_cell(mask, 3, 3, 1) is None

    def test_the_radius_is_a_circle(self):
        mask = np.zeros((7, 7), dtype=bool)
        mask[1, 1] = True  # 2.83 cells away: in the square of radius 2, not in its circle
        assert objects.seed_cell(mask, 3, 3, 2) is None
        assert objects.seed_cell(mask, 3, 3, 3) == (1, 1)


class TestGrowObject:
    def test_a_house_is_read_in_the_first_window(self):
        cloud = Cloud((100, 100, 110, 112))
        grid = objects.grow_object(cloud.read, 105.2, 106.3, 1.0)
        assert grid is not None and not grid.truncated and len(cloud.reads) == 1
        assert grid.region.sum() == (10 + 2) * (12 + 2) - 4  # the roof, a cell around it, no corner
        assert grid.points == len(cloud.xs)
        left, cell, _r1, top, _r2, minus = grid.geotransform
        assert (cell, minus) == (1.0, -1.0) and left == 105 - 32 and top == 107 + 32

    def test_only_the_clicked_object(self):
        cloud = Cloud((100, 100, 110, 110), (114, 100, 124, 110))  # 4 m apart
        grid = objects.grow_object(cloud.read, 105.0, 105.0, 1.0)
        assert grid.points == len(cloud.xs) // 2

    def test_a_gap_of_two_cells_is_closed(self):
        # Two cells of gap are bridged by the closing of one cell on each side: one object.
        cloud = Cloud((100, 100, 110, 110), (112, 100, 122, 110))
        grid = objects.grow_object(cloud.read, 105.0, 105.0, 1.0)
        assert grid.points == len(cloud.xs)

    def test_a_long_building_grows_the_window(self):
        cloud = Cloud((100, 100, 200, 110))  # 100 m long: past the 64 m window
        grid = objects.grow_object(cloud.read, 105.0, 105.0, 1.0)
        assert len(cloud.reads) == 2 and not grid.truncated and grid.half == 128.0
        assert grid.points == len(cloud.xs)

    def test_a_forest_is_cut_at_the_largest_window(self):
        cloud = Cloud((0, 0, 400, 20), step=1.0)
        grid = objects.grow_object(cloud.read, 200.0, 10.0, 1.0)
        assert grid.truncated and len(cloud.reads) == 2
        assert grid.region[:, 0].any() and grid.region[:, -1].any()

    def test_a_click_beside_the_object(self):
        cloud = Cloud((100, 100, 110, 110))
        assert objects.grow_object(cloud.read, 112.5, 105.0, 1.0, seed_radius=2) is not None  # 1.5 cells off the closing
        assert objects.grow_object(cloud.read, 130.0, 105.0, 1.0, seed_radius=2) is None
        assert len(cloud.reads) == 2  # no growth without an object

    def test_a_courtyard_is_filled(self):
        # A ring of buildings around a courtyard of 10 x 10 m.
        cloud = Cloud((100, 100, 130, 105), (100, 125, 130, 130), (100, 105, 105, 125), (125, 105, 130, 125))
        grid = objects.grow_object(cloud.read, 102.0, 102.0, 1.0)
        assert grid.region.sum() == 32 * 32 - 4

    def test_geographic_cells(self):
        cell = 1.0 / 111320.0
        xs, ys = _grid_points(0, 0, 10, 10)
        cloud = types.SimpleNamespace(reads=[])

        def read(xmin, ymin, xmax, ymax):
            cloud.reads.append((xmin, ymin, xmax, ymax))
            return 2.0 + xs * cell, 45.0 + ys * cell

        grid = objects.grow_object(read, 2.0 + 5 * cell, 45.0 + 5 * cell, cell, 32 * cell, 128 * cell)
        assert grid is not None and grid.region.sum() == 12 * 12 - 4 and len(cloud.reads) == 1


class FakeProvider:
    """identify() of a point cloud: every class, a dict per point (strict bounds like QgsGeos::contains)."""

    def __init__(self, points, valid=True):
        self.points, self.valid, self.calls = points, valid, 0

    def hasValidIndex(self):
        return self.valid

    def identify(self, resolution, geometry, zrange, limit):
        self.calls += 1
        box = geometry.rect
        inside = [{"X": x, "Y": y, "Z": 0.0, "Classification": c} for x, y, c in self.points
                  if box.x0 < x < box.x1 and box.y0 < y < box.y1]
        return inside[:limit]


class FakeLayer:
    def __init__(self, points, provider="copc", valid=True):
        self.provider = FakeProvider(points)
        self._provider_type, self._valid = provider, valid

    def providerType(self):
        return self._provider_type

    def isValid(self):
        return self._valid

    def dataProvider(self):
        return self.provider

    def crs(self):
        return fk.FakeCrs("EPSG:2154")


@pytest.fixture
def qgis_fakes(monkeypatch):
    regions = []

    def mask_to_geometry(region, geotransform, crs_wkt, sieve_pixels=0, simplify_tolerance=0.0):
        regions.append((region.copy(), geotransform, simplify_tolerance))
        return "object geometry"

    monkeypatch.setattr(geometry_tools, "mask_to_geometry", mask_to_geometry)
    monkeypatch.setattr(objects, "QgsRectangle", fk.FakeRectangle)
    monkeypatch.setattr(footprint, "QgsGeometry", types.SimpleNamespace(fromRect=lambda rect: types.SimpleNamespace(rect=rect)))
    return regions


class TestObjectFootprint:
    def test_the_class_of_the_click_only(self, qgis_fakes):
        roof = [(x + 0.25, y + 0.25, 6) for x in np.arange(100, 110, 0.5) for y in np.arange(100, 110, 0.5)]
        tree = [(x + 0.25, y + 0.25, 5) for x in np.arange(108, 116, 0.5) for y in np.arange(100, 108, 0.5)]
        layer = FakeLayer(roof + tree)
        found = objects.object_footprint(layer, 105.0, 105.0, 6)
        assert found.geometry == "object geometry" and found.points == len(roof) and not found.truncated
        region, geotransform, tolerance = qgis_fakes[0]
        assert region.sum() == 12 * 12 - 4 and tolerance == 0.5  # the tree over the roof is another object

    def test_classification_as_text(self, qgis_fakes):
        layer = FakeLayer([(105.25, 105.25, "6 (Building)")])
        assert objects.object_footprint(layer, 105.0, 105.0, 6).points == 1

    def test_no_point_of_the_class(self, qgis_fakes):
        layer = FakeLayer([(105.25, 105.25, 2)])
        found = objects.object_footprint(layer, 105.0, 105.0, 6)
        assert found.points == 0 and not found.message and qgis_fakes == []

    def test_the_points_limit_cuts_the_object(self, qgis_fakes):
        roof = [(x + 0.25, y + 0.25, 6) for x in np.arange(100, 110, 0.5) for y in np.arange(100, 110, 0.5)]
        found = objects.object_footprint(FakeLayer(roof), 100.5, 105.0, 6, points_limit=50)
        assert found.points == 50 and found.truncated
        found = objects.object_footprint(FakeLayer(roof), 105.0, 105.0, 6, points_limit=50)
        assert found.points == 0 and found.truncated  # nothing found: the limit says why

    def test_a_virtual_point_cloud_is_refused(self, qgis_fakes):
        found = objects.object_footprint(FakeLayer([], provider="vpc"), 0.0, 0.0, 6)
        assert "VPC" in found.message

    def test_a_cloud_not_indexed_is_refused(self, qgis_fakes):
        layer = FakeLayer([])
        layer.provider.valid = False
        assert "indexed" in objects.object_footprint(layer, 0.0, 0.0, 6).message


class Part:
    def __init__(self, area, filled=None):
        self._area, self._filled = float(area), filled

    def area(self):
        return self._area

    def isEmpty(self):
        return False

    def removeInteriorRings(self):
        return self._filled if self._filled is not None else self


class Multi:
    def __init__(self, parts):
        self.parts = parts

    def isEmpty(self):
        return not self.parts

    def isMultipart(self):
        return True

    def asGeometryCollection(self):
        return self.parts


class TestSimilarObjects:
    def test_parts_within_the_area_ratios(self):
        parts = [Part(40), Part(100), Part(210), Part(5)]
        kept, total = objects.similar_parts(Multi(parts), [100.0], (0.5, 2.0))
        assert [part.area() for part in kept] == [100.0] and total == 4
        kept, _total = objects.similar_parts(Multi(parts), [100.0, 30.0], (0.5, 2.0))
        assert [part.area() for part in kept] == [40.0, 100.0]  # 15 to 200

    def test_a_courtyard_counts_in_the_area(self):
        # A ring of 90 m² around a courtyard of 30 m²: measured filled, as the clicked objects are.
        ring = Part(90, filled=Part(120))
        kept, _total = objects.similar_parts(Multi([ring]), [100.0], (0.9, 1.3))
        assert [part.area() for part in kept] == [120.0]

    def test_without_reference_nothing_is_kept(self):
        kept, total = objects.similar_parts(Multi([Part(10)]), [], (0.5, 2.0))
        assert kept == [] and total == 1

    def test_the_class_is_read_through_the_filter_of_the_layer(self):
        assert objects.class_subset(6) == "(Classification = 6)"
        assert objects.class_subset(6, "Z > 10 -- high") == "(Z > 10 -- high\n) AND (Classification = 6)"

    def test_the_similar_objects_of_a_footprint_read_before(self, monkeypatch):
        monkeypatch.setattr(geometry_tools, "union_geometries", lambda parts: ("union", len(parts)))
        read = types.SimpleNamespace(geometry=Multi([Part(40), Part(100), Part(150)]), truncated=True, coarse=False,
                                     cell_size=1.0)
        found = objects.similar_objects_footprint(None, 6, [100.0], (0.5, 2.0), footprint=read)
        assert found.geometry == ("union", 2) and len(found.parts) == 2 and found.total == 3 and found.truncated
