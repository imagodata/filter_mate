# -*- coding: utf-8 -*-
"""FilterMate 5 raster selection polygons, read tile by tile (2026-10-18).

* the 4-pixel sieve never empties nor shrinks a small selection;
* a tiled read gives the cells of the whole grid read at once: the margin
  covers the neighbours of a slope and the patches the sieve looks at;
* the NoData pixels of a band an expression reads are not kept;
* the read stops between tiles when the task is canceled, and reports its progress.
"""
import importlib.util
import logging
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
raster_adapter = fk.load("raster_adapter")
geometry_tools = fk.load("geometry_tools")
_criteria = fk.load("core.domain.raster_filter_criteria")
RasterSelection, RasterSelectionMode = _criteria.RasterSelection, _criteria.RasterSelectionMode


def _gdal_arrays():
    """GDAL, and gdal_array built for this numpy (``python3 -s`` on a machine with a newer user numpy)."""
    try:
        from osgeo import gdal_array  # noqa: F401
    except ImportError as exc:
        pytest.skip(f"osgeo.gdal_array unavailable: {exc}")


class Raster:
    """Bands of the grid read, over (0, 0, width, height): one value per cell of 1 x 1.

    The selection asks for whole cells only (asserted): at the native resolution
    a cell is a pixel; over the pixel limit, ``k`` x ``k`` pixels with ``k`` a
    power of two, which GDAL reads alike from a tile or the whole raster (checked
    in QGIS by the coarse read probe). This stand-in therefore holds the cells.
    """

    def __init__(self, **bands):
        self.bands = {int(name[1:]): np.asarray(array, dtype='float64') for name, array in bands.items()}
        self.height, self.width = next(iter(self.bands.values())).shape
        self.reads = []

    def read(self, band, extent, width, height):
        self.reads.append((band, width, height))
        for edge in (extent.xMinimum(), extent.xMaximum(), extent.yMinimum(), extent.yMaximum()):
            assert edge == int(edge), f"window off the cells: {extent}"
        assert (extent.width(), extent.height()) == (width, height), "one value per cell"
        data = self.bands[band]
        xs = extent.xMinimum() + (np.arange(width) + 0.5) * extent.width() / width
        ys = extent.yMaximum() - (np.arange(height) + 0.5) * extent.height() / height
        cols = np.floor(xs).astype(int)
        rows = np.floor(self.height - ys).astype(int)
        return data[np.ix_(rows, cols)].copy()


def _lone_cells_removed(mask):
    """Stand-in for the GDAL sieve: a cell without a true 8-neighbour goes (local, like the real one)."""
    padded = np.pad(mask, 1)
    neighbours = sum(padded[1 + dy:1 + dy + mask.shape[0], 1 + dx:1 + dx + mask.shape[1]]
                     for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx)
    return mask & (neighbours > 0)


class CellSet(frozenset):
    """The merged geometry: the (column, row) of its cells; its vertices are their corners."""

    def isEmpty(self):
        return not self

    def constGet(self):
        return self

    def nCoordinates(self):
        if not self:
            return 0
        cols, rows = zip(*self)
        mask = np.zeros((max(rows) + 1, max(cols) + 1), dtype=bool)
        mask[list(rows), list(cols)] = True
        return raster_adapter.mask_corners(mask)


class Cell:
    """A polygon of one cell, in cell coordinates."""

    def __init__(self, x, y):
        self.xy = (x, y)

    def boundingBox(self):
        return fk.FakeRectangle(self.xy[0], self.xy[1], self.xy[0] + 1, self.xy[1] + 1)


@pytest.fixture
def cells(monkeypatch):
    """Polygonization replaced by cell sets: the result geometry is the set of (column, row) kept."""
    calls = {'sieve': [], 'edge': 0}

    def sieve_mask(mask, sieve_pixels):
        calls['sieve'].append(sieve_pixels)
        return _lone_cells_removed(mask != 0)

    def polygonize_mask(mask, cells_transform):
        col, _, _, row, _, _ = cells_transform
        rows, cols = np.nonzero(mask)
        return [Cell(int(col) + c, int(row) + r) for r, c in zip(rows, cols)]

    def merge_tile_polygons(inner, edge):
        calls['edge'] += len(edge)
        return CellSet(cell.xy for cell in list(inner) + list(edge))

    monkeypatch.setattr(geometry_tools, 'sieve_mask', sieve_mask)
    monkeypatch.setattr(geometry_tools, 'polygonize_mask', polygonize_mask)
    monkeypatch.setattr(geometry_tools, 'merge_tile_polygons', merge_tile_polygons)
    monkeypatch.setattr(geometry_tools, 'pixel_to_map', lambda geometry, transform: geometry)
    monkeypatch.setattr(geometry_tools, 'make_valid', lambda geometry: geometry)
    monkeypatch.setattr(raster_adapter, 'QgsRectangle', fk.FakeRectangle)
    monkeypatch.setattr(raster_adapter, 'crs_kind', lambda crs: 'projected')
    monkeypatch.setattr(raster_adapter, 'QgsCoordinateReferenceSystem', _CRS)
    return calls


def _select(monkeypatch, raster, selection, native=None, **kwargs):
    monkeypatch.setattr(raster_adapter, 'read_band_array', lambda provider, band, extent, width, height:
                        provider.read(band, extent, width, height))
    height, width = native or (raster.height, raster.width)
    extent = fk.FakeRectangle(0, 0, raster.width, raster.height)
    return raster_adapter.selection_geometry(raster, selection, extent, width, height, '', **kwargs)


def _cells_of(mask):
    rows, cols = np.nonzero(mask)
    return frozenset(zip(cols.tolist(), rows.tolist()))


_CRS = types.SimpleNamespace(fromWkt=lambda wkt: fk.FakeCrs('EPSG:2154'))
CLASS_7 = RasterSelection(mode=RasterSelectionMode.CLASSES, band=1, classes=(7,))


class TestOpening:
    """2026-10-18: the similar objects cut each tile at its pixel-wide bridges (patch cores) before polygonizing."""

    def test_the_bridge_goes_and_the_hole_stays(self, cells, monkeypatch):
        grid = np.zeros((12, 20))
        grid[2:9, 2:9] = 7  # a pool
        grid[5, 5] = 0  # a ladder in it: a hole, kept (filled tile by tile it would be half filled on an edge)
        grid[5, 9:12] = 7  # a line of its colour to the lawn
        grid[2:9, 12:18] = 7  # the lawn
        raster = Raster(b1=grid)
        plain = _select(monkeypatch, raster, CLASS_7, sieve_pixels=0).geometry
        opened = _select(monkeypatch, raster, CLASS_7, sieve_pixels=0, opening=1).geometry
        assert plain == _cells_of(grid == 7)
        expected = grid == 7
        expected[5, 9:12] = False  # the line goes, the corners of the patches too
        for row, col in ((2, 2), (2, 8), (8, 2), (8, 8), (2, 12), (2, 17), (8, 12), (8, 17)):
            expected[row, col] = False
        assert opened == _cells_of(expected)

    def test_a_coarse_read_keeps_the_cells(self, cells, monkeypatch):
        grid = np.zeros((12, 20))
        grid[2:9, 2:9] = 7
        grid[5, 5] = 0
        grid[5, 9:12] = 7  # a cell-wide line: two pixels wide at the native resolution, kept
        grid[2:9, 12:18] = 7
        raster = Raster(b1=grid)
        result = _select(monkeypatch, raster, CLASS_7, native=(24, 40), max_pixels=240, sieve_pixels=0, opening=1)
        assert result.coarse and result.decimation == 2
        assert result.geometry == _cells_of(grid == 7)

    def test_without_the_opening_nothing_changes(self, cells, monkeypatch):
        grid = np.zeros((6, 6))
        grid[1, 1:5] = 7  # a thin line: opened away, kept without
        raster = Raster(b1=grid)
        assert _select(monkeypatch, raster, CLASS_7, sieve_pixels=0).geometry == _cells_of(grid == 7)
        assert _select(monkeypatch, raster, CLASS_7, sieve_pixels=0, opening=1).geometry == frozenset()


class TestTiles:
    def test_tiles_cover_the_grid_row_by_row(self):
        assert list(raster_adapter._tiles(5, 3, 2)) == [(0, 0, 2, 2), (0, 2, 2, 2), (0, 4, 2, 1),
                                                         (2, 0, 1, 2), (2, 2, 1, 2), (2, 4, 1, 1)]

    def test_polygons_on_a_shared_edge_go_through_the_union(self):
        inner, edge = [], []
        # Tile (row 0, col 10, 10 x 10) of a 20 x 20 grid: its left and bottom edges are shared.
        shared = (10, None, None, 10)
        raster_adapter._sort_tile_polygons([Cell(10, 3), Cell(15, 5), Cell(19, 0), Cell(12, 9)], shared, (inner, edge))
        assert [c.xy for c in inner] == [(15, 5), (19, 0)]  # the raster border is no shared edge
        assert [c.xy for c in edge] == [(10, 3), (12, 9)]


class TestTiledReadIsTheWholeRead:
    def test_range_with_sieve(self, monkeypatch, cells):
        rng = np.random.default_rng(1)
        data = rng.random((150, 130)) * 100
        data[10:40, 5:30] = 90
        selection = RasterSelection(band=1, minimum=45.0)
        whole = _select(monkeypatch, Raster(b1=data), selection, tile_size=10000)
        tiled = _select(monkeypatch, Raster(b1=data), selection, tile_size=16)
        assert tiled.tiles == 90 and whole.tiles == 1
        assert whole.kept_pixels >= raster_adapter.SIEVE_MIN_KEPT_PIXELS  # the sieve applies
        assert tiled.geometry == whole.geometry == _cells_of(_lone_cells_removed(data >= 45.0)) != _cells_of(data >= 45.0)
        assert tiled.kept_pixels == whole.kept_pixels == int((data >= 45.0).sum())
        assert cells['edge'] > 0

    def test_slope_reads_the_neighbours_across_the_tile_edges(self, monkeypatch, cells):
        terrain = fk.load("terrain")
        rng = np.random.default_rng(2)
        rows, cols = np.mgrid[0:50, 0:70]
        dtm = 100 + 0.8 * rows + 3 * np.sin(cols / 4.0) + rng.random((50, 70)) * 2
        selection = RasterSelection(band=1, minimum=40.0, derivative='slope_degrees')
        whole = _select(monkeypatch, Raster(b1=dtm), selection, tile_size=10000, sieve_pixels=0)
        tiled = _select(monkeypatch, Raster(b1=dtm), selection, tile_size=9, sieve_pixels=0)
        slope = terrain.derive(dtm, selection.derivative, 1.0, 1.0)
        assert whole.geometry == _cells_of(slope >= 40.0)
        assert 0 < len(tiled.geometry) < dtm.size
        assert tiled.geometry == whole.geometry

    def test_slope_with_sieve(self, monkeypatch, cells):
        terrain = fk.load("terrain")
        rng = np.random.default_rng(3)
        dtm = rng.random((150, 150)) * 3  # rough: the slope changes from pixel to pixel
        slope = terrain.derive(dtm, _criteria.RasterDerivative.SLOPE_DEGREES, 1.0, 1.0)
        threshold = float(np.median(slope))
        selection = RasterSelection(band=1, minimum=threshold, derivative='slope_degrees')
        whole = _select(monkeypatch, Raster(b1=dtm), selection, tile_size=10000)
        tiled = _select(monkeypatch, Raster(b1=dtm), selection, tile_size=11)
        assert whole.kept_pixels >= raster_adapter.SIEVE_MIN_KEPT_PIXELS  # the sieve applies
        assert whole.geometry == _cells_of(_lone_cells_removed(slope >= threshold)) != _cells_of(slope >= threshold)
        assert tiled.geometry == whole.geometry


class TestSieveChoice:
    def test_small_selection_is_not_sieved(self, monkeypatch, cells):
        data = np.ones((200, 200))
        data[10, 10] = data[50, 60] = data[51, 60] = 7  # a rare class: three pixels
        result = _select(monkeypatch, Raster(b1=data), CLASS_7)
        assert result.kept_pixels == 3 and result.geometry == {(10, 10), (60, 50), (60, 51)}

    def test_large_selection_read_pixel_for_pixel_is_sieved(self, monkeypatch, cells):
        data = np.ones((200, 200))
        data[:100, :] = 7  # 20 000 pixels
        data[150, 150] = 7  # speckle
        result = _select(monkeypatch, Raster(b1=data), CLASS_7)
        assert set(cells['sieve']) == {4} and (150, 150) not in result.geometry and len(result.geometry) == 20000

    def test_subsampled_grid_loses_lone_cells_only(self, monkeypatch, cells, caplog):
        """Over max_pixels each cell stands for several pixels: 4 cells are not speckle, a lone cell is."""
        data = np.ones((200, 200))
        data[:100, :] = 7
        with caplog.at_level(logging.INFO):
            result = _select(monkeypatch, Raster(b1=data), CLASS_7, native=(800, 800), max_pixels=40000)
        assert set(cells['sieve']) == {2} and result.coarse and result.grid == (200, 200)
        assert any('⏱ [FM5]' in record.getMessage() and 'over the limit of 40000' in record.getMessage()
                   for record in caplog.records)

    def test_native_grid_below_the_limit_is_not_coarse(self, monkeypatch, cells, caplog):
        data = np.ones((100, 100))
        with caplog.at_level(logging.INFO):
            result = _select(monkeypatch, Raster(b1=data), CLASS_7, max_pixels=10000)
        assert not result.coarse and result.grid == (100, 100) and not caplog.records

    def test_small_subsampled_selection_is_not_sieved(self, monkeypatch, cells):
        data = np.ones((100, 100))
        data[:50, :] = 7  # 5 000 cells
        data[80, 80] = 7
        result = _select(monkeypatch, Raster(b1=data), CLASS_7, native=(400, 400), max_pixels=10000)
        assert (80, 80) in result.geometry and len(result.geometry) == 5001

    def test_the_sieve_never_empties_a_selection(self, monkeypatch, cells):
        data = np.ones((300, 300))
        data[::2, ::2] = 7  # 22 500 lone pixels: all speckle
        result = _select(monkeypatch, Raster(b1=data), CLASS_7, tile_size=64)
        assert result.kept_pixels == 22500 and len(result.geometry) == 22500


class TestVertexBudget:
    """The geometry stays light: a dense, speckled tile is smoothed, an isolated object is kept as it is."""

    def test_corners_are_the_vertices_polygonize_draws(self):
        square = np.zeros((5, 5), dtype=bool)
        square[1:4, 1:4] = True
        assert raster_adapter.mask_corners(square) == 4
        ell = square.copy()
        ell[1, 3] = False
        assert raster_adapter.mask_corners(ell) == 6
        diagonal = np.zeros((4, 4), dtype=bool)
        diagonal[1, 1] = diagonal[2, 2] = True
        assert raster_adapter.mask_corners(diagonal) == 8  # two patches touching by a corner
        ring = square.copy()
        ring[2, 2] = False
        assert raster_adapter.mask_corners(ring) == 8

    def test_dense_blocks_keep_the_surface(self):
        mask = np.zeros((4, 6), dtype=bool)
        mask[0:2, 0:2] = True  # a full block
        mask[2, 4] = mask[3, 5] = True  # half a block
        mask[0, 3] = True  # a quarter
        blocks = raster_adapter.dense_blocks(mask, 2)  # 7 cells: the full block and the half one (8 cells)
        assert blocks[0:2, 0:2].all() and blocks[2:4, 4:6].all() and blocks.sum() == 8
        rng = np.random.default_rng(12)
        for density in (0.1, 0.3, 0.5, 0.7):
            noise = rng.random((512, 512)) < density
            for factor in (2, 4, 8, 32):
                share = raster_adapter.dense_blocks(noise, factor).sum() / float(noise.sum())
                assert share == pytest.approx(1.0, abs=factor * factor / (2.0 * noise.sum()) + 1e-9)

    def test_majority_keeps_about_the_area_and_the_isolated_objects(self):
        rng = np.random.default_rng(10)
        mask = np.zeros((120, 200), dtype=bool)
        mask[:, :100] = np.kron(rng.random((15, 13)) < 0.5, np.ones((8, 8), dtype=bool))[:120, :100]
        mask[:, :100] ^= rng.random((120, 100)) < 0.2  # speckle on blobs
        mask[50:56, 160:166] = True  # a pool far away
        smoothed = raster_adapter.majority(mask, 4)
        share = smoothed[:, :100].mean() / mask[:, :100].mean()
        assert 0.7 < share < 1.3  # neither emptied nor filled
        assert raster_adapter.mask_corners(smoothed[:, :100]) < raster_adapter.mask_corners(mask[:, :100]) / 3
        assert (smoothed[:, 120:] == mask[:, 120:]).all()

    def test_dense_tile_smoothed_isolated_object_kept(self, monkeypatch, cells):
        rng = np.random.default_rng(8)
        data = np.zeros((64, 128))
        data[:, :64] = (rng.random((64, 64)) < 0.5) * 7  # vegetation-like speckle on the left tile
        data[20:26, 90:96] = 7  # a pool alone on the right tile
        result = _select(monkeypatch, Raster(b1=data), CLASS_7, tile_size=64, max_vertices=600)
        assert result.smoothing > 0 or result.blocks > 0
        kept = np.zeros(data.shape, dtype=bool)
        for col, row in result.geometry:
            kept[row, col] = True
        assert raster_adapter.mask_corners(kept[:, :64]) <= 300  # the share of the left tile
        assert abs(kept[:, :64].sum() / float((data[:, :64] == 7).sum()) - 1.0) <= 0.10  # the surface stays
        assert (kept[:, 64:] == (data[:, 64:] == 7)).all()  # the pool, cell for cell

    def test_blocks_only_when_the_majority_is_not_enough(self, monkeypatch, cells):
        """Correlated patches (a real NDVI) fit with the majority; white speckle needs coarser blocks."""
        rng = np.random.default_rng(13)
        patches = np.kron(rng.random((8, 8)) < 0.5, np.ones((16, 16), dtype=bool))  # 16-cell patches
        patches ^= rng.random((128, 128)) < 0.05
        smoothed = _select(monkeypatch, Raster(b1=patches * 7.0), CLASS_7, tile_size=128, max_vertices=800)
        assert smoothed.smoothing > 0 and smoothed.blocks == 0
        speckle = (rng.random((128, 128)) < 0.5) * 7.0
        blocky = _select(monkeypatch, Raster(b1=speckle), CLASS_7, tile_size=128, max_vertices=800)
        assert blocky.blocks > 0
        assert abs(len(blocky.geometry) / float((speckle == 7).sum()) - 1.0) <= 0.10

    def test_a_light_selection_is_not_smoothed(self, monkeypatch, cells):
        data = np.zeros((64, 64))
        data[10:30, 5:40] = 7
        result = _select(monkeypatch, Raster(b1=data), CLASS_7)
        assert result.smoothing == 0 and result.geometry == _cells_of(data == 7)

    @pytest.mark.parametrize("value, expected", [
        (None, 100000000), (0, 100000000), ("lots", 100000000), (True, 100000000), (-5, 100000000),
        ("4e8", 400000000), ("400 000 000", 400000000), ("16_000_000", 16000000), (2.5e7, 25000000),
        ({"value": "1e6"}, 1000000), (5, 10000)])
    def test_pixel_limit_read_from_the_settings(self, value, expected):
        assert raster_adapter.source_max_pixels(value) == expected

    @pytest.mark.parametrize("size, limit, k", [((20000, 20000), 400000000, 1), ((20001, 20000), 400000000, 2),
                                                 ((800, 800), 40000, 4), ((801, 800), 40000, 8)])
    def test_decimation_is_a_power_of_two(self, size, limit, k):
        assert raster_adapter._decimation(size[0], size[1], limit) == k


class TestExpressionNoData:
    def test_nodata_of_a_band_read_by_the_expression_is_not_kept(self, monkeypatch, cells):
        """The virtual raster has no NoData: 255 on the blue band passes a pool's blue test."""
        nan = float('nan')
        virtual = Raster(b1=np.ones((4, 4)))  # the comparison kept every pixel
        blue = np.full((4, 4), 228.0)
        blue[0, 0] = blue[3, 2] = nan
        base = Raster(b1=np.full((4, 4), 98.0), b3=blue)
        selection = RasterSelection(mode=RasterSelectionMode.EXPRESSION, expression='"o@3" > 0')
        result = _select(monkeypatch, virtual, selection, nodata_provider=base, nodata_bands=[3], tile_size=3)
        assert result.kept_pixels == 14 and (0, 0) not in result.geometry and (2, 3) not in result.geometry
        unmasked = _select(monkeypatch, virtual, selection, tile_size=3)
        assert unmasked.kept_pixels == 16


class TestCancelAndProgress:
    def test_canceled_between_tiles(self, monkeypatch, cells):
        raster = Raster(b1=np.full((40, 40), 7.0))
        asked = []

        def is_canceled():
            asked.append(1)
            return len(asked) > 2

        result = _select(monkeypatch, raster, CLASS_7, tile_size=10, is_canceled=is_canceled)
        assert result.canceled and len(raster.reads) == 2

    def test_progress_grows_to_100(self, monkeypatch, cells):
        values = []
        _select(monkeypatch, Raster(b1=np.full((40, 40), 7.0)), CLASS_7, tile_size=10, progress=values.append)
        assert len(values) == 18 and values == sorted(values) and values[-1] == 100.0


class TestTilePolygonsWithGdal:
    """sieve_mask / polygonize_mask / merge_tile_polygons / pixel_to_map themselves (GDAL, OGR backed geometries)."""

    @pytest.fixture
    def polygons(self, monkeypatch):
        _gdal_arrays()
        fk.install(monkeypatch, geometry_tools, raster_adapter)
        monkeypatch.setattr(raster_adapter, 'crs_kind', lambda crs: 'projected')
        monkeypatch.setattr(raster_adapter, 'QgsCoordinateReferenceSystem', _CRS)
        monkeypatch.setattr(raster_adapter, 'read_band_array', lambda provider, band, extent, width, height:
                            provider.read(band, extent, width, height))

    def _geometry(self, raster, selection, tile_size, sieve_pixels=4):
        extent = fk.FakeRectangle(0, 0, raster.width, raster.height)
        return raster_adapter.selection_geometry(raster, selection, extent, raster.width, raster.height, '',
                                                 tile_size=tile_size, sieve_pixels=sieve_pixels)

    def test_tiles_merge_into_the_polygons_of_the_whole_grid(self, polygons):
        rng = np.random.default_rng(4)
        data = rng.random((90, 70)) * 100
        data[20:70, 10:60] = 95  # one large patch across several tiles
        selection = RasterSelection(band=1, minimum=85.0)
        whole = self._geometry(Raster(b1=data), selection, 10000)
        tiled = self._geometry(Raster(b1=data), selection, 16)
        assert tiled.geometry.isGeosValid() and whole.geometry.isGeosValid()
        assert tiled.geometry.symDifference(whole.geometry).area() == pytest.approx(0.0)
        assert tiled.geometry.area() == pytest.approx(whole.geometry.area())
        big = max(tiled.geometry.asGeometryCollection(), key=lambda part: part.area())
        assert big.area() >= 50 * 50  # the patch is one polygon, not one per tile

    def test_unsieved_area_is_the_pixel_count(self, polygons):
        rng = np.random.default_rng(5)
        data = (rng.random((40, 40)) > 0.7) * 7.0
        result = self._geometry(Raster(b1=data), CLASS_7, 9, sieve_pixels=0)
        assert result.geometry.area() == pytest.approx(float((data == 7).sum()))

    def test_corners_count_the_vertices_gdal_draws(self, polygons):
        rng = np.random.default_rng(9)
        mask = rng.random((60, 70)) < 0.45
        drawn = 0
        for polygon in geometry_tools.polygonize_mask(mask, (0.0, 1.0, 0.0, 0.0, 0.0, 1.0)):
            for index in range(polygon._g.GetGeometryCount()):
                drawn += polygon._g.GetGeometryRef(index).GetPointCount() - 1  # the closing point
        assert raster_adapter.mask_corners(mask) == drawn

    @pytest.mark.parametrize("overviews", [None, [2, 4, 8]])
    def test_cells_over_the_limit_are_read_alike_from_every_tile(self, polygons, tmp_path, overviews):
        """Over the pixel limit a cell is one pixel of k x k (GDAL), whether read in a tile or with the whole raster."""
        from osgeo import gdal
        rows, cols = np.mgrid[0:301, 0:499]
        data = (cols * 1000 + rows).astype('float64')
        path = str(tmp_path / "index.tif")
        dataset = gdal.GetDriverByName('GTiff').Create(path, 499, 301, 1, gdal.GDT_Float64)
        dataset.SetGeoTransform((615999.31, 0.2, 0, 6153000.65, 0, -0.2))
        dataset.GetRasterBand(1).WriteArray(data)
        if overviews:
            dataset.BuildOverviews('NEAREST', overviews)
        dataset = None
        read = raster_adapter.gdal_cell_reader(path)
        k, width, height = 4, 499 // 4, 301 // 4
        whole = read(1, 0, 0, width, height, k)
        if not overviews:
            assert (whole == data[k // 2::k, k // 2::k][:height, :width]).all()  # the pixel at the cell centre
        tiled = np.full((height, width), np.nan)
        for row, col, rr, cc in raster_adapter._tiles(width, height, 16):
            top, left = max(0, row - 3), max(0, col - 3)
            bottom, right = min(height, row + rr + 3), min(width, col + cc + 3)
            cells = read(1, left, top, right - left, bottom - top, k)
            tiled[row:row + rr, col:col + cc] = cells[row - top:row - top + rr, col - left:col - left + cc]
        assert (tiled == whole).all()

    def test_a_geometry_over_the_budget_keeps_its_patches(self, polygons):
        """What the smoothing cannot merge (an object outline, isolated patches) is simplified, never dropped."""
        rows, cols = np.mgrid[0:200, 0:200]
        mask = (rows > cols + 10) | (rows + 7 < cols // 3)  # two staircase outlines
        mask[2:6, 190:194] = True  # an isolated patch
        parts = geometry_tools.polygonize_mask(mask, (0.0, 0.25, 0.0, 50.0, 0.0, -0.25))
        geometry = geometry_tools.merge_tile_polygons(parts, [])
        before = geometry.nCoordinates()
        bounded = raster_adapter._within_budget(geometry, before // 4, cell=0.25)
        assert bounded.nCoordinates() <= before // 4
        assert len(bounded.asGeometryCollection()) == len(geometry.asGeometryCollection())

    def test_cells_are_moved_to_the_map(self, polygons):
        mask = np.zeros((4, 4), dtype=bool)
        mask[1, 2] = True
        cell = geometry_tools.merge_tile_polygons(geometry_tools.polygonize_mask(mask, (0.0, 1.0, 0.0, 0.0, 0.0, 1.0)), [])
        moved = geometry_tools.pixel_to_map(cell, (615999.31, 0.25, 0.0, 6153000.65, 0.0, -0.25))
        box = moved.boundingBox()
        assert (box.xMinimum(), box.xMaximum()) == pytest.approx((615999.81, 616000.06))
        assert (box.yMinimum(), box.yMaximum()) == pytest.approx((6153000.15, 6153000.40))
        assert moved.area() == pytest.approx(0.0625)


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


class TestTaskProgress:
    """The tiles of a raster source fill the first half of the task's bar, the targets the second."""

    @pytest.fixture(autouse=True)
    def _project(self, monkeypatch):
        self.task_module = fk.load("cross_filter_task")
        fk.install(monkeypatch, self.task_module)
        monkeypatch.setattr(fk.FakeProject, 'transformContext', lambda self: None, raising=False)

    def _run(self, source, targets):
        task_module = self.task_module
        task = task_module.CrossFilterTask('t', None, source, targets)
        values = []
        task.setProgress = values.append
        task.isCanceled = lambda: False
        assert task.run(), task.error
        return values

    class Source:
        kind = types.SimpleNamespace(value='raster')
        message, elapsed, details, crs = '', 0.0, {}, None

        def __init__(self, reports):
            self.reports_progress = reports
            self.progress = None

        def compute(self, request, is_canceled, buffer=True):
            self.buffered = buffer
            if self.progress is not None:
                for percent in (50.0, 100.0):
                    self.progress(percent)
            return types.SimpleNamespace(isEmpty=lambda: False)

    class Target:
        layer_name = 'target'
        outcome = types.SimpleNamespace(message='')

        def compute(self, *args):
            pass

    def test_raster_source_then_targets(self):
        assert self._run(self.Source(True), [self.Target(), self.Target()]) == [25.0, 50.0, 75.0, 100.0]

    def test_raster_source_alone_fills_the_bar(self):
        assert self._run(self.Source(True), []) == [50.0, 100.0]

    def test_no_buffer_without_target(self):
        """Without a target the source is masked by the selection as read: its buffer would be lost work."""
        alone, with_targets = self.Source(True), self.Source(True)
        self._run(alone, [])
        self._run(with_targets, [self.Target()])
        assert alone.buffered is False and with_targets.buffered is True

    def test_the_clip_of_the_source_is_prepared_in_the_task(self):
        source = self.Source(True)
        prepared = []
        source.prepare_apply = lambda is_canceled: prepared.append(is_canceled())
        self._run(source, [])
        assert prepared == [False]

    def test_other_sources_leave_the_bar_to_the_targets(self):
        source = self.Source(False)
        assert self._run(source, [self.Target(), self.Target()]) == [50.0, 100.0] and source.progress is None
