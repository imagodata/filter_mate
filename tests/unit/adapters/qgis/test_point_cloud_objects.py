# -*- coding: utf-8 -*-
"""FilterMate 5 object detection on a point cloud: the cluster of points of a class under a click."""
import importlib.util
import math
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
        assert grid.region.sum() == 10 * 12  # the roof: closed, then shrunk back (2026-11-11)
        assert grid.points == len(cloud.xs)
        grown = objects.grow_object(cloud.read, 105.2, 106.3, 1.0, erode_cells=0)
        assert grown.region.sum() == (10 + 2) * (12 + 2) - 4  # the roof, a cell around it, no corner
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

    def test_shrunk_back_a_roof_is_its_cells(self):
        """2026-11-11: closed and shrunk back, the object is not grown by a cell on each side."""
        cloud = Cloud((100, 100, 110, 112))
        grid = objects.grow_object(cloud.read, 105.2, 106.3, 1.0, erode_cells=1)
        assert grid.region.sum() == 10 * 12 and grid.points == len(cloud.xs)

    def test_shrunk_back_a_gap_of_two_cells_stays_closed(self):
        cloud = Cloud((100, 100, 110, 110), (112, 100, 122, 110))
        grid = objects.grow_object(cloud.read, 105.0, 105.0, 1.0, erode_cells=1)
        assert grid.points == len(cloud.xs)

    def test_shrunk_back_a_neck_of_one_grown_cell_is_cut(self):
        # The roofs face each other across two cells on one row only: the grown cells bridge them by one row.
        cloud = Cloud((100, 100, 110, 110), (112, 109, 122, 119))
        assert objects.grow_object(cloud.read, 105.0, 105.0, 1.0, erode_cells=0).points == len(cloud.xs)
        grid = objects.grow_object(cloud.read, 105.0, 105.0, 1.0, erode_cells=1)
        assert grid.points == len(cloud.xs) // 2 and grid.region.sum() == 100

    def test_shrunk_back_sparse_points_stay_one_object(self):
        # A point every other cell: the holes are filled before shrinking, the roof stays whole and not grown.
        cloud = Cloud((100.3, 100.3, 110.3, 110.3), step=2.0)  # points at 101.3, 103.3 … 109.3, inside their cells
        grown = objects.grow_object(cloud.read, 105.0, 105.0, 1.0, erode_cells=0)
        grid = objects.grow_object(cloud.read, 105.0, 105.0, 1.0, erode_cells=1)
        left, top = grid.geotransform[0], grid.geotransform[3]
        rows, cols = np.nonzero(grid.region)
        assert (cols + left).min() == 101 and (cols + left).max() == 109  # the cells of the points, no more
        assert (top - rows - 1).min() == 101 and (top - rows - 1).max() == 109
        assert grid.region.sum() == 9 * 9 < grown.region.sum() and grid.points == len(cloud.xs)

    def test_shrunk_back_a_hedge_with_gaps_of_one_cell_stays_whole(self):
        # 2026-11-11 review: eroded alone, the grown cells between two points went and the hedge fell apart.
        xs, ys = np.arange(100.5, 140, 2.0), np.full(20, 100.5)  # a point every other cell along a row

        def read(xmin, ymin, xmax, ymax):
            inside = (xs > xmin) & (xs < xmax)
            return xs[inside], ys[inside]

        grid = objects.grow_object(read, 120.5, 100.5, 1.0, erode_cells=1)
        assert grid.points == len(xs) and grid.region.sum() == 39  # the row itself, not the cells beside it

    def test_shrunk_back_a_diagonal_row_stays_whole(self):
        xs = np.arange(100.5, 120, 1.0)
        ys = xs.copy()  # each point in the cell diagonal to the last one
        read = lambda xmin, ymin, xmax, ymax: (xs, ys)  # noqa: E731
        grid = objects.grow_object(read, 110.5, 110.5, 1.0, erode_cells=1)
        assert grid.points == len(xs) and grid.region.sum() == len(xs) + 2 * (len(xs) - 1)  # the two cells of a step

    def test_shrunk_back_a_gap_of_two_cells_in_a_row_is_cut(self):
        # Two grown cells between two points look like the neck between two buildings: cut, as there.
        xs, ys = np.array([100.5, 103.5]), np.array([100.5, 100.5])
        read = lambda xmin, ymin, xmax, ymax: (xs, ys)  # noqa: E731
        assert objects.grow_object(read, 100.5, 100.5, 1.0, erode_cells=0).points == 2
        assert objects.grow_object(read, 100.5, 100.5, 1.0, erode_cells=1).points == 1

    def test_the_object_cut_is_said_on_the_final_object(self):
        # A long hedge read to the largest window is cut there, and still said so once shrunk back.
        xs, ys = np.arange(0.5, 400, 1.0), np.full(400, 10.5)

        def read(xmin, ymin, xmax, ymax):
            inside = (xs > xmin) & (xs < xmax)
            return xs[inside], ys[inside]

        assert objects.grow_object(read, 200.5, 10.5, 1.0, erode_cells=1).truncated

    def test_a_long_building_grows_the_window(self):
        cloud = Cloud((100, 100, 200, 110))  # 100 m long: past the 64 m window
        grid = objects.grow_object(cloud.read, 105.0, 105.0, 1.0, limit=128.0)
        assert len(cloud.reads) == 2 and not grid.truncated and grid.half == 128.0
        # With the default limit (a window of 128 m) it is cut: the click is 95 m from its far end.
        cloud = Cloud((100, 100, 200, 110))
        assert objects.grow_object(cloud.read, 105.0, 105.0, 1.0).truncated
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
        assert grid.region.sum() == 30 * 30  # the ring and its courtyard, shrunk back
        assert objects.grow_object(cloud.read, 102.0, 102.0, 1.0, erode_cells=0).region.sum() == 32 * 32 - 4

    def test_geographic_cells(self):
        cell = 1.0 / 111320.0
        xs, ys = _grid_points(0, 0, 10, 10)
        cloud = types.SimpleNamespace(reads=[])

        def read(xmin, ymin, xmax, ymax):
            cloud.reads.append((xmin, ymin, xmax, ymax))
            return 2.0 + xs * cell, 45.0 + ys * cell

        grid = objects.grow_object(read, 2.0 + 5 * cell, 45.0 + 5 * cell, cell, 32 * cell, 128 * cell)
        assert grid is not None and grid.region.sum() == 10 * 10 and len(cloud.reads) == 1


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
    """The scenes are laid out on cells of 1 m, the default since 2026-11-11 (2 m before)."""

    def test_the_class_of_the_click_only(self, qgis_fakes):
        roof = [(x + 0.25, y + 0.25, 6) for x in np.arange(100, 110, 0.5) for y in np.arange(100, 110, 0.5)]
        tree = [(x + 0.25, y + 0.25, 5) for x in np.arange(108, 116, 0.5) for y in np.arange(100, 108, 0.5)]
        layer = FakeLayer(roof + tree)
        found = objects.object_footprint(layer, 105.0, 105.0, 6)
        assert found.geometry == "object geometry" and found.points == len(roof) and not found.truncated
        region, geotransform, tolerance = qgis_fakes[0]
        assert region.sum() == 10 * 10 and tolerance == 0.5  # the tree over the roof is another object
        assert geotransform[1] == 1.0 and found.cell_size == 1.0

    def test_classification_as_text(self, qgis_fakes):
        layer = FakeLayer([(105.25, 105.25, "6 (Building)")])
        assert objects.object_footprint(layer, 105.0, 105.0, 6).points == 1

    def test_no_point_of_the_class(self, qgis_fakes):
        layer = FakeLayer([(105.25, 105.25, 2)])
        found = objects.object_footprint(layer, 105.0, 105.0, 6)
        assert found.points == 0 and not found.message and qgis_fakes == []

    def test_the_points_limit_cuts_the_object(self, qgis_fakes):
        roof = [(x + 0.25, y + 0.25, 6) for x in np.arange(100, 110, 0.5) for y in np.arange(100, 110, 0.5)]
        found = objects.object_footprint(FakeLayer(roof), 100.5, 105.0, 6, points_limit=50, resolution=1.0)
        assert found.points == 50 and found.truncated
        found = objects.object_footprint(FakeLayer(roof), 105.0, 105.0, 6, points_limit=50, resolution=1.0)
        assert found.points == 0 and found.truncated  # nothing found: the limit says why

    def test_a_virtual_point_cloud_is_refused(self, qgis_fakes):
        found = objects.object_footprint(FakeLayer([], provider="vpc"), 0.0, 0.0, 6)
        assert "VPC" in found.message

    def test_a_cloud_not_indexed_is_refused(self, qgis_fakes):
        layer = FakeLayer([])
        layer.provider.valid = False
        assert "indexed" in objects.object_footprint(layer, 0.0, 0.0, 6).message


class Part:
    def __init__(self, area, filled=None, perimeter=None):
        self._area, self._filled = float(area), filled
        # A square by default: compactness pi / 4
        self._perimeter = float(perimeter) if perimeter is not None else 4.0 * self._area ** 0.5

    def area(self):
        return self._area

    def length(self):
        return self._perimeter

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

    def test_same_shape_keeps_the_compact_ones_as_on_a_raster(self):
        # 2026-11-11: a hedge of the area of a tree (100 m², 1 x 100 m: compactness 0.06) against a square of 100 m²
        hedge, square = Part(100, perimeter=202), Part(100)
        kept, _total = objects.similar_parts(Multi([hedge, square]), [100.0], (0.5, 2.0))
        assert kept == [hedge, square]  # the area alone
        kept, _total = objects.similar_parts(Multi([hedge, square]), [100.0], (0.5, 2.0), [math.pi / 4])
        assert kept == [square]

    def test_the_shape_of_a_courtyard_is_measured_filled(self):
        ring = Part(90, filled=Part(120), perimeter=1000)  # its rings would make it look like a line
        kept, _total = objects.similar_parts(Multi([ring]), [100.0], (0.5, 2.0), [math.pi / 4])
        assert [part.area() for part in kept] == [120.0]

    def test_the_class_is_read_through_the_filter_of_the_layer(self):
        assert objects.class_subset(6) == "(Classification = 6)"
        assert objects.class_subset(6, "Z > 10 -- high") == "(Z > 10 -- high\n) AND (Classification = 6)"

    def test_the_similar_objects_of_a_footprint_read_before(self, monkeypatch):
        monkeypatch.setattr(geometry_tools, "union_geometries", lambda parts: ("union", len(parts)))
        read = types.SimpleNamespace(geometry=Multi([Part(40), Part(100), Part(150)]), truncated=True, coarse=False,
                                     cell_size=1.0)
        found = objects.similar_objects_footprint(None, 6, [100.0], (0.5, 2.0), footprint=read)
        assert found.geometry == ("union", 2) and len(found.parts) == 2 and found.total == 3 and found.truncated


class TestFinalWindow:
    def test_a_small_window_at_the_limit_does_not_cut_the_object(self, qgis_fakes):
        """The first window of a long building saturated the points limit: the final window did not."""
        roof = [(x + 0.25, y + 0.25, 6) for x in np.arange(100, 200, 0.5) for y in np.arange(100, 104, 0.5)]
        layer = FakeLayer(roof)
        first = {"done": False}
        identify = layer.provider.identify

        def saturated_once(resolution, geometry, zrange, limit):
            points = identify(resolution, geometry, zrange, limit)
            if not first["done"]:
                first["done"] = True
                return points + [{"X": 150.0, "Y": 150.0, "Classification": 2}] * (limit - len(points))
            return points

        layer.provider.identify = saturated_once
        found = objects.object_footprint(layer, 150.0, 102.0, 6, resolution=1.0, points_limit=len(roof) + 100)
        assert found.points == len(roof) and not found.truncated


class TestSameCellsAsTheFootprint:
    """2026-10-18 review: the object and the footprint of its class are measured on the same cells."""

    def _footprint_cells(self, monkeypatch, layer, cell, erode_cells=0):
        grids = []

        def mask_to_geometry(region, geotransform, crs_wkt, sieve_pixels=0, simplify_tolerance=0.0):
            grids.append((region.copy(), geotransform))
            return "footprint geometry"

        monkeypatch.setattr(geometry_tools, "mask_to_geometry", mask_to_geometry)
        monkeypatch.setattr(footprint, "QgsRectangle", fk.FakeRectangle)
        footprint.footprint_geometry(layer, cell, erode_cells=erode_cells)
        return grids[0]

    @pytest.mark.parametrize("cell", [1.0, 2.0])
    @pytest.mark.parametrize("erode_cells", [0, 1])
    @pytest.mark.parametrize("offset", [0.0, 0.3, 0.7, 1.4])
    def test_a_tree_has_the_same_cells(self, qgis_fakes, monkeypatch, offset, erode_cells, cell):
        tree = [(x + offset, y + offset, 5) for x in np.arange(1000.1, 1005, 0.4) for y in np.arange(2000.1, 2005, 0.4)]
        layer = FakeLayer(tree)
        layer.extent = lambda: fk.FakeRectangle(987.3, 1981.9, 1031.7, 2033.2)  # an extent off the cells
        objects.object_footprint(layer, 1002.5 + offset, 2002.5 + offset, 5, resolution=cell, erode_cells=erode_cells)
        region, object_transform = qgis_fakes[0][:2]
        grid, transform = self._footprint_cells(monkeypatch, layer, cell, erode_cells)
        assert transform[0] % cell == 0 and transform[3] % cell == 0  # cells on the multiples of their size
        assert (object_transform[0] - transform[0]) % cell == 0 and (object_transform[3] - transform[3]) % cell == 0
        assert int(region.sum()) == int(grid.sum())

    @staticmethod
    def _cells(region, transform, cell):
        rows, cols = np.nonzero(region)
        col0, row0 = int(round(transform[0] / cell)), int(round(transform[3] / cell))
        return set(zip((col0 + cols).tolist(), (row0 - 1 - rows).tolist()))

    @pytest.mark.parametrize("seed", range(6))
    def test_each_clicked_object_is_its_part_of_the_footprint(self, qgis_fakes, monkeypatch, seed):
        """2026-11-11 review: crowns and roofs scattered at random, shrunk back; the object is the part under it."""
        raster_adapter = fk.load("raster_adapter")
        rng = np.random.default_rng(seed)
        points, clicks = [], []
        for _ in range(25):
            if seed % 2:  # roofs of points at random densities
                x0, y0, w, h = rng.uniform(0, 100), rng.uniform(0, 100), rng.uniform(4, 20), rng.uniform(4, 15)
                n = int(w * h * rng.uniform(0.3, 2))
                xs, ys = rng.uniform(x0, x0 + w, n), rng.uniform(y0, y0 + h, n)
            else:  # crowns
                cx, cy, r = rng.uniform(0, 120), rng.uniform(0, 120), rng.uniform(1.5, 6)
                n = int(rng.uniform(0.3, 1.2) * r * r * 3.14)
                angle, distance = rng.uniform(0, 2 * np.pi, n), r * np.sqrt(rng.uniform(0, 1, n))
                xs, ys = cx + distance * np.cos(angle), cy + distance * np.sin(angle)
            points += [(float(x), float(y), 5) for x, y in zip(xs, ys)]
            clicks.append((float(xs[0]), float(ys[0])))
        layer = FakeLayer(points)
        layer.extent = lambda: fk.FakeRectangle(-10.3, -10.7, 140.1, 140.9)
        clicked = []
        for x, y in clicks:
            qgis_fakes.clear()
            objects.object_footprint(layer, x, y, 5, resolution=1.0, erode_cells=1)
            region, object_transform = qgis_fakes[0][:2]
            clicked.append(self._cells(region, object_transform, 1.0))
        grid, transform = self._footprint_cells(monkeypatch, layer, 1.0, erode_cells=1)
        grid = np.asarray(grid, dtype=bool)
        parts = []
        while grid.any():
            part = raster_adapter.flood_fill(grid, [tuple(np.argwhere(grid)[0])])
            parts.append(self._cells(raster_adapter.fill_holes(part), transform, 1.0))
            grid &= ~part
        for cells in clicked:
            assert [part for part in parts if part & cells] == [cells]


class TestFootprintCells:
    """2026-11-11: the footprint of a class in cells of 1 m when it is light enough, else of 2 m."""

    def test_a_light_class_is_read_again_in_the_cells_of_the_clicks(self):
        assert objects.footprint_resolution(25781) == objects.OBJECT_RESOLUTION == 1.0  # buildings of the tile
        assert objects.footprint_resolution(objects.FINE_CLASS_POINTS) == 1.0

    def test_a_dense_class_keeps_the_coarse_cells(self):
        assert objects.footprint_resolution(182406) == objects.COARSE_RESOLUTION == 2.0  # its high vegetation
        assert objects.footprint_resolution(10, coarse_truncated=True) == 2.0

    def _read(self, monkeypatch, points_at_2m, fine=None):
        reads = []

        class Copy(FakeLayer):
            def setSubsetString(self, subset):
                return True

        def footprint_geometry(layer, resolution, points_limit=0, dilate_cells=1, erode_cells=0, check=None):
            reads.append((resolution, dilate_cells, erode_cells))
            points = points_at_2m if resolution == 2.0 else points_at_2m * 4
            result = footprint.FootprintResult("geometry", points, resolution)
            if resolution != 2.0 and fine:
                for name, value in fine.items():
                    setattr(result, name, value)
            return result

        monkeypatch.setattr(footprint, "open_point_cloud", lambda source, name, provider: Copy([]))
        monkeypatch.setattr(footprint, "footprint_geometry", footprint_geometry)
        layer = FakeLayer([])
        layer.source, layer.name = (lambda: "/data/tile.copc.laz"), (lambda: "tile")
        return objects.class_footprint(layer, 6), reads

    def test_the_footprint_of_a_light_class_in_cells_of_1_m(self, monkeypatch):
        result, reads = self._read(monkeypatch, 25781)
        assert reads == [(2.0, 1, 1), (1.0, 1, 1)] and result.resolution == 1.0 and result.cell_size == 1.0

    def test_the_footprint_of_a_dense_class_read_once(self, monkeypatch):
        result, reads = self._read(monkeypatch, 182406)
        assert reads == [(2.0, 1, 1)] and result.resolution == 2.0 and result.objects == {}

    @pytest.mark.parametrize("fine", [{"truncated": True}, {"coarse": True, "cell_size": 1.3}])
    def test_a_fine_read_cut_or_widened_keeps_the_coarse_one(self, monkeypatch, fine):
        result, reads = self._read(monkeypatch, 25781, fine)
        assert len(reads) == 2 and result.resolution == 2.0 and result.cell_size == 2.0


class TestReadThroughACopy:
    def test_class_under_the_click(self, qgis_fakes, monkeypatch):
        monkeypatch.setattr(objects, "QgsGeometry", types.SimpleNamespace(fromRect=lambda rect: types.SimpleNamespace(rect=rect)))
        points = [(10.2, 10.2, 6), (10.4, 10.6, 6), (10.8, 10.1, 2), (30.0, 30.0, 5)]
        layer = FakeLayer(points)
        assert objects.class_under(layer, 10.5, 10.5, 1.0) == 6
        assert objects.class_under(layer, 50.0, 50.0, 1.0) is None

    def test_the_copy_keeps_the_filter_not_the_preview(self, monkeypatch):
        opened = []

        class Copy(FakeLayer):
            def __init__(self):
                super().__init__([])
                self.subsets = []

            def setSubsetString(self, subset):
                self.subsets.append(subset)
                return True

        def open_point_cloud(source, name, provider):
            opened.append((source, provider))
            return Copy()

        monkeypatch.setattr(footprint, "open_point_cloud", open_point_cloud)
        layer = FakeLayer([])
        layer.source, layer.name = (lambda: "/data/tile.copc.laz"), (lambda: "tile")
        assert objects.base_copy(layer, "Z > 0 -- low").subsets == ["(Z > 0 -- low\n)"]
        assert objects.base_copy(layer, "").subsets == []
        assert opened == [("/data/tile.copc.laz", "copc")] * 2
        with pytest.raises(RuntimeError, match="VPC"):
            objects.base_copy(FakeLayer([], provider="vpc"))
