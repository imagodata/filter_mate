# -*- coding: utf-8 -*-
"""FilterMate 5 object detection of the pipette: the patch under a click, read in a growing window."""
import importlib.util
import pathlib
import sys

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
raster_adapter = fk.load("raster_adapter")
geometry_tools = fk.load("geometry_tools")
criteria = fk.load("core.domain.raster_filter_criteria")
RasterSelection = criteria.RasterSelection
RasterSelectionMode = criteria.RasterSelectionMode


class TestFloodFill:
    def test_only_the_patch_under_the_seed(self):
        mask = np.array([[1, 1, 0, 1],
                         [0, 1, 0, 1],
                         [0, 0, 0, 1]], dtype=bool)
        region = raster_adapter.flood_fill(mask, [(0, 0)])
        assert region.tolist() == [[True, True, False, False],
                                   [False, True, False, False],
                                   [False, False, False, False]]

    def test_corners_do_not_connect(self):
        mask = np.array([[1, 0],
                         [0, 1]], dtype=bool)
        assert int(raster_adapter.flood_fill(mask, [(0, 0)]).sum()) == 1

    def test_winding_patch_is_followed(self):
        # A U shape: the fill goes down, across and up again.
        mask = np.zeros((5, 5), dtype=bool)
        mask[:, 0] = mask[4, :] = mask[:, 4] = True
        region = raster_adapter.flood_fill(mask, [(0, 0)])
        assert region.sum() == mask.sum() and region[0, 4]

    def test_seed_on_a_dropped_pixel_or_off_the_grid(self):
        mask = np.array([[1, 0]], dtype=bool)
        assert not raster_adapter.flood_fill(mask, [(0, 1)]).any()
        assert not raster_adapter.flood_fill(mask, [(5, 5), (-1, 0)]).any()

    def test_holes_are_filled_but_not_the_outside(self):
        ring = np.ones((5, 5), dtype=bool)
        ring[2, 2] = False  # a ladder in a pool
        ring[0, 0] = False  # a notch on the edge: outside, not a hole
        filled = raster_adapter.fill_holes(ring)
        assert filled[2, 2] and not filled[0, 0]


class TestMorphology:
    """2026-10-18: opening (numpy only) cutting the pixel-wide bridges of the object modes."""

    def test_dilate_grows_a_diamond_and_erode_shrinks_it_back(self):
        dot = np.zeros((5, 5), dtype=bool)
        dot[2, 2] = True
        grown = geometry_tools.dilate_mask(dot)
        assert int(grown.sum()) == 5 and grown[1, 2] and grown[2, 1] and not grown[1, 1]
        assert geometry_tools.erode_mask(grown).tolist() == dot.tolist()
        assert int(geometry_tools.dilate_mask(dot, 2).sum()) == 13
        assert geometry_tools.dilate_mask(dot, 0).tolist() == dot.tolist()

    def test_erosion_keeps_the_edge_cells_of_the_grid(self):
        # The outside counts as set: a patch on the raster edge is not eaten from that side.
        full = np.ones((3, 4), dtype=bool)
        assert geometry_tools.erode_mask(full).all()

    def test_the_cores_cut_a_bridge_and_keep_the_blobs(self):
        mask = np.zeros((7, 15), dtype=bool)
        mask[1:6, 1:6] = True  # a pool
        mask[3, 6:10] = True  # a line of pixels of its colour
        mask[1:6, 10:14] = True  # the lawn
        cores = geometry_tools.patch_cores(mask)
        assert not cores[3, 6:10].any()
        assert cores[1:6, 1:6].sum() == 25 - 4 and cores[1:6, 10:14].sum() == 20 - 4  # the corners go
        # The opening alone gives the ends of the line back (a line of two pixels would join them again).
        opened = geometry_tools.open_mask(mask)
        assert opened[3, 6] and opened[3, 9] and not opened[3, 7:9].any()

    def test_a_line_of_any_length_is_cut(self):
        for length in (1, 2, 3):
            mask = np.zeros((7, 12 + length), dtype=bool)
            mask[1:6, 1:6] = True
            mask[3, 6:6 + length] = True
            mask[1:6, 6 + length:11 + length] = True
            cores = geometry_tools.patch_cores(mask)
            assert not cores[3, 6:6 + length].any(), length
            assert int(raster_adapter.flood_fill(cores, [(3, 3)]).sum()) == 21, length

    def test_a_corridor_two_cells_wide_is_cut_by_the_opening(self):
        mask = np.zeros((8, 16), dtype=bool)
        mask[1:7, 1:6] = True
        mask[3:5, 6:10] = True  # two cells wide, four long
        mask[1:7, 10:15] = True
        cores = geometry_tools.patch_cores(mask)
        assert not cores[3:5, 7:9].any() and not raster_adapter.flood_fill(cores, [(3, 3)])[1:7, 10:15].any()

    def test_a_thin_patch_has_no_core(self):
        line = np.zeros((5, 9), dtype=bool)
        line[2, 1:8] = True
        assert not geometry_tools.patch_cores(line).any()
        assert not geometry_tools.open_mask(line).any()

    def test_compactness(self):
        assert abs(geometry_tools.compactness(_Part(100.0, 40.0)) - 0.785) < 0.01  # a square of 10
        assert abs(geometry_tools.compactness(_Part(100.0, 104.0)) - 0.116) < 0.01  # a road of 50 x 2
        assert geometry_tools.compactness(_Part(0.0, 0.0)) == 0.0
        assert geometry_tools.compactness(None) == 0.0
        if fk.ogr is not None:
            square = fk.FakeGeometry.fromWkt("POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))")
            assert abs(geometry_tools.compactness(square) - 0.785) < 0.01


class _Part:
    """A polygon known by its area and perimeter (no OGR needed)."""

    def __init__(self, area, perimeter):
        self._area, self._perimeter = float(area), float(perimeter)

    def area(self):
        return self._area

    def length(self):
        return self._perimeter

    def isEmpty(self):
        return self._area <= 0

    def isMultipart(self):
        return False


class _Multi:
    """A multipolygon of :class:`_Part`."""

    def __init__(self, parts):
        self.parts = list(parts)

    def isEmpty(self):
        return not self.parts

    def isMultipart(self):
        return True

    def asGeometryCollection(self):
        return list(self.parts)


class TestObjectRegion:
    """The patch under the click without the bridges that leave it."""

    @staticmethod
    def _scene():
        mask = np.zeros((7, 15), dtype=bool)
        mask[1:6, 1:6] = True  # a pool
        mask[3, 6:10] = True  # a line of pixels of its colour, along the shady edge
        mask[1:6, 10:14] = True  # the lawn
        return mask

    def test_the_pool_stays_apart_from_the_lawn_and_keeps_its_corners(self):
        mask = self._scene()
        region = raster_adapter.object_region(mask, (3, 3))
        assert region[1:6, 1:6].all()  # the corners are given back
        assert not region[1:6, 10:14].any()  # the lawn is another object
        assert region[3, 6] and not region[3, 7:10].any()  # the first pixel of the line stays with the pool
        assert int(region.sum()) == 26

    def test_a_click_on_a_corner_starts_from_the_nearest_core(self):
        # The corner (1, 1) is no core: the object is the pool all the same, not the whole mask.
        mask = self._scene()
        region = raster_adapter.object_region(mask, (1, 1))
        assert int(region.sum()) == 26 and not region[1:6, 10:14].any()
        assert raster_adapter._core_seed(mask, geometry_tools.patch_cores(mask), (1, 1)) in ((1, 2), (2, 1))  # an edge cell
        assert raster_adapter._core_seed(mask, geometry_tools.patch_cores(mask), (3, 3)) == (3, 3)
        # The ring of a diagonal edge: its inner neighbour.
        diamond = np.zeros((9, 9), dtype=bool)
        for row in range(9):
            for col in range(9):
                diamond[row, col] = abs(row - 4) + abs(col - 4) <= 4
        cores = geometry_tools.patch_cores(diamond)
        assert not cores[0, 4] and raster_adapter._core_seed(diamond, cores, (0, 4)) == (1, 4)
        assert int(raster_adapter.object_region(diamond, (0, 4)).sum()) == int(diamond.sum())

    def test_a_corner_next_to_another_patch_stays_in_its_own(self):
        # The nearest core must be of the clicked patch: a lawn one cell away across a gap is not it.
        mask = np.zeros((8, 8), dtype=bool)
        mask[1:4, 1:4] = True  # a 3 x 3 patch: its corners are no cores
        mask[1:7, 5:8] = True  # another patch, two cells from its corner
        assert raster_adapter._core_seed(mask, geometry_tools.patch_cores(mask), (3, 3)) in ((2, 3), (3, 2))
        assert int(raster_adapter.object_region(mask, (3, 3)).sum()) == 9

    def test_without_the_opening_the_pool_leaks(self):
        mask = self._scene()
        assert int(raster_adapter.object_region(mask, (3, 3), opening=0).sum()) == int(mask.sum())

    def test_the_opened_patch_without_its_outline(self):
        mask = self._scene()
        region = raster_adapter.object_region(mask, (3, 3), reconstruct=False)
        assert int(region.sum()) == 25 - 4 and not region[1, 1]

    def test_a_thin_object_is_followed_as_it_is(self):
        mask = np.zeros((5, 9), dtype=bool)
        mask[2, 1:8] = True  # a path: too thin to survive the opening
        region = raster_adapter.object_region(mask, (2, 4))
        assert int(region.sum()) == 7

    def test_a_click_on_a_dropped_pixel_finds_nothing(self):
        assert not raster_adapter.object_region(self._scene(), (0, 0)).any()


@pytest.fixture
def scene(monkeypatch):
    """A 1000 x 1000 raster of 1 m pixels; the mask is what the selection keeps, the windows read are recorded."""
    mask = np.zeros((1000, 1000), dtype=bool)
    windows, regions = [], []

    def selection_mask_over(provider, selection, rect, width, height, crs_wkt):
        col0, row0 = int(round(rect.xMinimum())), int(round(1000 - rect.yMaximum()))
        windows.append((col0, row0, width, height))
        return mask[row0:row0 + height, col0:col0 + width].copy()

    def mask_to_geometry(region, geotransform, crs_wkt, sieve_pixels=0, simplify_tolerance=0.0):
        regions.append((region.copy(), geotransform))
        return fk.FakeGeometry.fromWkt("POINT(0 0)") if fk.ogr is not None else _Shape()

    monkeypatch.setattr(raster_adapter, "_selection_mask_over", selection_mask_over)
    monkeypatch.setattr(raster_adapter, "QgsRectangle", fk.FakeRectangle)
    monkeypatch.setattr(raster_adapter, "QgsGeometry", _Shape)
    monkeypatch.setattr(geometry_tools, "mask_to_geometry", mask_to_geometry)
    monkeypatch.setattr(geometry_tools, "union_geometries", lambda geometries: geometries[0])
    return mask, windows, regions


class _Shape:
    def isEmpty(self):
        return False

    def constGet(self):  # the vertex budget counts it: a light outline
        return self

    def nCoordinates(self):
        return 4


def _detect(seeds, **kwargs):
    selection = RasterSelection(mode=RasterSelectionMode.CLASSES, classes=frozenset({1}), seeds=tuple(seeds))
    return raster_adapter.object_geometry(None, selection, fk.FakeRectangle(0, 0, 1000, 1000), 1000, 1000, "",
                                          **kwargs)


class TestSimilarObjects:
    """2026-10-18: every patch of the raster whose area is like the clicked objects' (similar objects mode)."""

    def test_area_bounds_follow_the_clicked_objects(self):
        assert raster_adapter.similar_area_bounds([100.0, 400.0], (0.5, 2.0)) == (50.0, 800.0)
        assert raster_adapter.similar_area_bounds([100.0], (2.0, 0.5)) == (50.0, 200.0)
        assert raster_adapter.similar_area_bounds([], (0.5, 2.0)) is None
        assert raster_adapter.similar_area_bounds([0.0, None], (0.5, 2.0)) is None
        assert raster_adapter.similar_area_bounds([100.0], ()) is None

    def test_parts_of_a_geometry(self):
        if fk.ogr is None:
            pytest.skip("OGR fakes")
        multi = fk.FakeGeometry.fromWkt("MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)), ((5 5, 7 5, 7 7, 5 7, 5 5)))")
        parts = raster_adapter.geometry_parts(multi)
        assert len(parts) == 2 and sorted(round(p.area()) for p in parts) == [1, 4]
        single = fk.FakeGeometry.fromWkt("POLYGON((0 0, 2 0, 2 2, 0 2, 0 0))")
        assert len(raster_adapter.geometry_parts(single)) == 1
        assert raster_adapter.geometry_parts(None) == []

    def test_patches_within_the_bounds_are_kept(self, monkeypatch):
        if fk.ogr is None:
            pytest.skip("OGR fakes")
        clicked = fk.FakeGeometry.fromWkt("POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))")  # 100 m²
        patches = fk.FakeGeometry.fromWkt(
            "MULTIPOLYGON(((0 0, 10 0, 10 10, 0 10, 0 0)), ((20 20, 28 20, 28 28, 20 28, 20 20)), "
            "((40 40, 41 40, 41 41, 40 41, 40 40)), ((60 60, 90 60, 90 90, 60 90, 60 60)))")  # 100, 64, 1, 900 m²
        calls = []
        monkeypatch.setattr(raster_adapter, "object_geometry",
                            lambda *a, **k: raster_adapter.SelectionGeometryResult(clicked, 100, 10000, 1.0, False, 1))
        monkeypatch.setattr(raster_adapter, "selection_geometry", lambda provider, plain, *a, **k: calls.append(plain)
                            or raster_adapter.SelectionGeometryResult(patches, 1065, 10000, 1.0, grid=(100, 100)))
        monkeypatch.setattr(raster_adapter, "QgsGeometry", fk.FakeGeometry)
        monkeypatch.setattr(geometry_tools, "union_geometries", lambda parts: fk.FakeGeometry.fromWkt(
            "MULTIPOLYGON(" + ", ".join("((" + ", ".join(f"{x} {y}" for x, y in p.exterior_coords()) + "))" for p in parts) + ")")
                            if hasattr(parts[0], "exterior_coords") else parts[0])
        selection = RasterSelection(mode=RasterSelectionMode.CLASSES, classes=frozenset({1}), seeds=((5.0, 5.0),),
                                    similar=(0.5, 2.0))
        result = raster_adapter.similar_objects_geometry(None, selection, fk.FakeRectangle(0, 0, 100, 100), 100, 100, "",
                                                         max_pixels=4000000)
        assert result.objects == 2  # 100 and 64 m²: not the 1 m² speck, not the 900 m² field
        assert result.kept_pixels == 164 and result.total_pixels == 10000
        plain = calls[0]
        assert plain.seeds == () and plain.similar == () and plain.classes == frozenset({1})

    def test_shape_bounds_follow_the_clicked_objects_up_to_a_disc(self):
        assert raster_adapter.similar_shape_bounds([0.8, 0.6], (0.5, 2.0)) == (0.3, 1.0)
        assert raster_adapter.similar_shape_bounds([0.2], (0.5, 2.0)) == (0.1, 0.4)
        assert raster_adapter.similar_shape_bounds([], (0.5, 2.0)) is None

    def test_the_shape_keeps_the_pools_and_drops_the_road(self, monkeypatch):
        clicked = _Part(100.0, 40.0)  # a square pool of 10 m: compactness 0.79
        # The same pool, a pool of 9 m (81 m²), a road of 50 x 2 m (100 m², compactness 0.12).
        patches = _Multi([_Part(100.0, 40.0), _Part(81.0, 36.0), _Part(100.0, 104.0)])
        seen = {}

        def object_geometry(*_args, **kwargs):
            seen.update(kwargs)
            return raster_adapter.SelectionGeometryResult(clicked, 100, 10000, 1.0, False, 1)

        def selection_geometry(_provider, _plain, *_args, **kwargs):
            seen.update(opening=kwargs.get("opening"))
            return raster_adapter.SelectionGeometryResult(patches, 281, 10000, 1.0, grid=(100, 100))

        monkeypatch.setattr(raster_adapter, "object_geometry", object_geometry)
        monkeypatch.setattr(raster_adapter, "selection_geometry", selection_geometry)
        monkeypatch.setattr(raster_adapter, "QgsGeometry", _Shape)
        monkeypatch.setattr(geometry_tools, "union_geometries", _Multi)
        kwargs = dict(mode=RasterSelectionMode.CLASSES, classes=frozenset({1}), seeds=((5.0, 5.0),), similar=(0.5, 2.0))
        extent = fk.FakeRectangle(0, 0, 100, 100)
        with_shape = raster_adapter.similar_objects_geometry(None, RasterSelection(shape=True, **kwargs), extent, 100, 100, "")
        assert with_shape.objects == 2 and with_shape.kept_pixels == 181
        assert seen["reconstruct"] is False and seen["opening"] == raster_adapter.OBJECT_OPENING
        assert seen["fill"] is False and seen["simplify"] is False  # measured as the patches are
        without = raster_adapter.similar_objects_geometry(None, RasterSelection(**kwargs), extent, 100, 100, "")
        assert without.objects == 3
        # Read on coarse cells (over the pixel limit), the patches keep their outline: the clicked objects too.
        raster_adapter.similar_objects_geometry(None, RasterSelection(**kwargs), extent, 100, 100, "", max_pixels=2500)
        assert seen["reconstruct"] is True

    def test_no_clicked_object_gives_nothing(self, monkeypatch):
        monkeypatch.setattr(raster_adapter, "object_geometry",
                            lambda *a, **k: raster_adapter.SelectionGeometryResult(_Shape(), 0, 10000, 1.0, False, 0))
        monkeypatch.setattr(raster_adapter, "geometry_parts", lambda geometry: [])
        monkeypatch.setattr(raster_adapter, "QgsGeometry", _Shape)
        selection = RasterSelection(mode=RasterSelectionMode.CLASSES, classes=frozenset({1}), seeds=((5.0, 5.0),),
                                    similar=(0.5, 2.0))
        result = raster_adapter.similar_objects_geometry(None, selection, fk.FakeRectangle(0, 0, 100, 100), 100, 100, "")
        assert result.objects == 0 and result.kept_pixels == 0

    def test_selection_geometry_routes_similar_selections(self, monkeypatch):
        seen = []
        monkeypatch.setattr(raster_adapter, "similar_objects_geometry", lambda *a, **k: seen.append(k) or "similar")
        monkeypatch.setattr(raster_adapter, "object_geometry", lambda *a, **k: "object")
        selection = RasterSelection(mode=RasterSelectionMode.CLASSES, classes=frozenset({1}), seeds=((5.0, 5.0),),
                                    similar=(0.5, 2.0))
        assert raster_adapter.selection_geometry(None, selection, fk.FakeRectangle(0, 0, 100, 100), 100, 100, "",
                                                 max_pixels=123) == "similar"
        assert seen[0]["max_pixels"] == 123 and seen[0]["patch_provider"] is None
        plain = RasterSelection(mode=RasterSelectionMode.CLASSES, classes=frozenset({1}), seeds=((5.0, 5.0),))
        assert raster_adapter.selection_geometry(None, plain, fk.FakeRectangle(0, 0, 100, 100), 100, 100, "") == "object"


class TestObjectGeometry:
    def test_window_grows_until_the_object_fits(self, scene):
        mask, windows, regions = scene
        mask[400:701, 450:461] = True  # a long, narrow object
        mask[500, 455] = False  # a hole inside it
        mask[100:110, 100:110] = True  # another patch of the same colour, elsewhere
        result = _detect([(455.5, 1000 - 550.5)], start=16)
        assert [w[2] for w in windows] == [33, 129, 513]  # grown while it touched a side
        region, geotransform = regions[-1]
        assert int(region.sum()) == 301 * 11  # the hole is filled, the other patch is not taken
        assert result.kept_pixels == 301 * 11 and not result.truncated
        assert result.total_pixels == 1000 * 1000
        col0, row0 = windows[-1][:2]
        assert geotransform == (col0, 1.0, 0.0, 1000 - row0, 0.0, -1.0)

    def test_an_object_larger_than_the_limit_is_cut(self, scene):
        mask, windows, _regions = scene
        mask[:, :] = True
        result = _detect([(500.5, 499.5)], start=16, limit=64)
        assert windows[-1][2] == 129 and result.truncated

    def test_the_raster_edge_does_not_make_it_grow(self, scene):
        mask, windows, _regions = scene
        mask[0:10, 0:10] = True  # in the corner of the raster
        result = _detect([(0.5, 999.5)], start=16)
        assert len(windows) == 1 and not result.truncated and result.kept_pixels == 100

    def test_a_click_on_a_dropped_pixel_or_off_the_raster_finds_nothing(self, scene):
        _mask, windows, regions = scene
        result = _detect([(10.5, 10.5), (2000.0, 10.0)])
        assert not regions and result.kept_pixels == 0
        assert len(windows) == 1  # the point off the raster is not read

    def test_each_click_is_an_object(self, scene):
        mask, _windows, regions = scene
        mask[100:110, 100:110] = True
        mask[800:805, 800:805] = True
        result = _detect([(105.5, 1000 - 105.5), (802.5, 1000 - 802.5)])
        assert len(regions) == 2 and result.kept_pixels == 125 and result.objects == 2

    def test_a_click_on_the_right_or_bottom_edge_is_the_last_pixel(self, scene):
        mask, _windows, _regions = scene
        mask[990:1000, 990:1000] = True
        assert _detect([(1000.0, 0.0)]).kept_pixels == 100

    def test_no_native_size_finds_nothing(self, scene):
        selection = RasterSelection(mode=RasterSelectionMode.CLASSES, classes=frozenset({1}), seeds=((1.0, 1.0),))
        result = raster_adapter.object_geometry(None, selection, fk.FakeRectangle(0, 0, 10, 10), 0, 0, "")
        assert result.kept_pixels == 0 and result.objects == 0

    def test_a_click_in_an_object_already_found_adds_nothing(self, scene, monkeypatch):
        mask, _windows, regions = scene
        mask[100:110, 100:110] = True

        class Found(_Shape):
            def contains(self, _point):
                return True

        monkeypatch.setattr(fk.FakeGeometry, "contains", lambda self, point: True, raising=False)
        monkeypatch.setattr(raster_adapter, "QgsPointXY", lambda x, y: (x, y))
        monkeypatch.setattr(geometry_tools, "mask_to_geometry", lambda region, *a, **k: regions.append(region) or Found())
        result = _detect([(105.5, 1000 - 105.5), (106.5, 1000 - 106.5)])
        assert len(regions) == 1 and result.kept_pixels == 100 and result.objects == 1

    def test_each_object_is_read_with_its_own_criterion(self, scene):
        mask, windows, regions = scene
        read = []
        pool = RasterSelection(mode=RasterSelectionMode.CLASSES, classes=frozenset({1}), seeds=((105.5, 894.5),))
        roof = RasterSelection(mode=RasterSelectionMode.CLASSES, classes=frozenset({2}), seeds=((802.5, 197.5),))
        selection = RasterSelection(mode=RasterSelectionMode.CLASSES, classes=frozenset({1, 2}), objects=(pool, roof))
        assert selection.seeds == ((105.5, 894.5), (802.5, 197.5))
        mask[100:110, 100:110] = True
        mask[800:805, 800:805] = True

        def provider_for(criterion):
            read.append(criterion.classes)
            return "provider"

        raster_adapter.object_geometry(None, selection, fk.FakeRectangle(0, 0, 1000, 1000), 1000, 1000, "",
                                       provider_for=provider_for)
        assert read == [frozenset({1}), frozenset({2})] and len(regions) == 2


class TestTerrainWindow:
    def test_a_slope_is_read_with_one_more_pixel_around(self, monkeypatch):
        reads = []

        def selection_mask_over(provider, selection, rect, width, height, crs_wkt):
            reads.append((rect.xMinimum(), rect.yMaximum(), width, height))
            return np.arange(width * height).reshape((height, width))

        monkeypatch.setattr(raster_adapter, "_selection_mask_over", selection_mask_over)
        monkeypatch.setattr(raster_adapter, "QgsRectangle", fk.FakeRectangle)
        slope = RasterSelection(maximum=10.0, derivative="slope_degrees")
        mask = raster_adapter._window_mask(None, slope, fk.FakeRectangle(0, 0, 100, 100), 1.0, 1.0,
                                           (10, 20, 15, 23), 100, 100, "")
        assert reads == [(9.0, 81.0, 7, 5)]  # one pixel more on every side
        assert mask.shape == (3, 5) and mask[0, 0] == 1 * 7 + 1  # the window itself, cropped


class TestSelectionGeometryRoute:
    def test_seeds_go_to_object_detection(self, monkeypatch):
        calls = []
        monkeypatch.setattr(raster_adapter, "object_geometry", lambda *args, **kwargs: calls.append(args) or "objects")
        selection = RasterSelection(mode=RasterSelectionMode.CLASSES, classes=frozenset({1}), seeds=((1.0, 2.0),))
        assert raster_adapter.selection_geometry(None, selection, fk.FakeRectangle(0, 0, 10, 10), 10, 10, "") == "objects"
        assert calls
