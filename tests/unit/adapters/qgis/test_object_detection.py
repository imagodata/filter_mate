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
