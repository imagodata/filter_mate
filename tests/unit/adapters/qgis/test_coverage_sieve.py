# -*- coding: utf-8 -*-
"""FilterMate 5 raster selection polygons: the 4-pixel sieve never empties nor shrinks a small selection."""
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
RasterSelection = fk.load("core.domain.raster_filter_criteria").RasterSelection
RasterSelectionMode = fk.load("core.domain.raster_filter_criteria").RasterSelectionMode


def _gdal_arrays():
    """GDAL, and gdal_array built for this numpy (``python3 -s`` on a machine with a newer user numpy)."""
    try:
        from osgeo import gdal_array  # noqa: F401
    except ImportError as exc:
        pytest.skip(f"osgeo.gdal_array unavailable: {exc}")


@pytest.fixture
def sieves(monkeypatch):
    """selection_geometry with the polygonization recorded (sieve size, grid)."""
    calls = []

    def mask_to_geometry(mask, geotransform, crs_wkt, sieve_pixels=0, simplify_tolerance=0.0):
        calls.append(sieve_pixels)
        return object()  # the polygons, not looked at here

    monkeypatch.setattr(geometry_tools, 'mask_to_geometry', mask_to_geometry)
    return calls


def _select(monkeypatch, data, native, max_pixels=4000000):
    def read_band_array(provider, band, extent, width, height):
        assert (height, width) == data.shape, "the test array is the grid read"
        return data.astype('float64')

    monkeypatch.setattr(raster_adapter, 'read_band_array', read_band_array)
    selection = RasterSelection(mode=RasterSelectionMode.CLASSES, band=1, classes=(7,))
    return raster_adapter.selection_geometry(None, selection, fk.FakeRectangle(0, 0, native[1], native[0]),
                                             native[1], native[0], '', max_pixels=max_pixels)


class TestSieveChoice:
    def test_small_selection_is_not_sieved(self, monkeypatch, sieves):
        data = np.ones((200, 200))
        data[10, 10] = data[50, 60] = data[51, 60] = 7  # a rare class: three pixels
        result = _select(monkeypatch, data, (200, 200))
        assert sieves == [0] and result.kept_pixels == 3

    def test_large_selection_read_pixel_for_pixel_is_sieved(self, monkeypatch, sieves):
        data = np.ones((200, 200))
        data[:100, :] = 7  # 20 000 pixels
        _select(monkeypatch, data, (200, 200))
        assert sieves == [4]

    def test_subsampled_grid_loses_lone_cells_only(self, monkeypatch, sieves):
        """Over max_pixels each cell stands for several pixels: 4 cells are not speckle, a lone cell is."""
        data = np.ones((200, 200))
        data[:100, :] = 7
        _select(monkeypatch, data, (800, 800), max_pixels=40000)
        assert sieves == [2]

    def test_small_subsampled_selection_is_not_sieved(self, monkeypatch, sieves):
        data = np.ones((100, 100))
        data[:50, :] = 7  # 5 000 cells
        _select(monkeypatch, data, (400, 400), max_pixels=10000)
        assert sieves == [0]


class TestSieveNeverEmpties:
    """mask_to_geometry itself (GDAL SieveFilter + Polygonize)."""

    @pytest.fixture
    def polygons(self, monkeypatch):
        _gdal_arrays()
        monkeypatch.setattr(geometry_tools, 'QgsGeometry', fk.FakeGeometry)

    def test_only_small_patches_are_kept(self, polygons):
        mask = np.zeros((10, 10), dtype='uint8')
        mask[2, 2] = mask[2, 3] = mask[7, 7] = 1
        geometry = geometry_tools.mask_to_geometry(mask, (0, 1, 0, 10, 0, -1), '', sieve_pixels=4)
        assert geometry.area() == pytest.approx(3.0)

    def test_speckle_of_a_large_patch_is_removed(self, polygons):
        mask = np.zeros((20, 20), dtype='uint8')
        mask[:10, :10] = 1
        mask[15, 15] = 1
        geometry = geometry_tools.mask_to_geometry(mask, (0, 1, 0, 20, 0, -1), '', sieve_pixels=4)
        assert geometry.area() == pytest.approx(100.0)
