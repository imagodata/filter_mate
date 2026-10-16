# -*- coding: utf-8 -*-
"""Terrain derivatives of a DTM grid: slope, aspect, hillshade, roughness (pure numpy)."""
import importlib
import math
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

np = pytest.importorskip("numpy")

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_terrain_test"


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.domain", _ROOT / "core" / "domain"),
                       (".adapters", _ROOT / "adapters"), (".adapters.qgis", _ROOT / "adapters" / "qgis"),
                       (".adapters.qgis.coverage_layers", _ROOT / "adapters" / "qgis" / "coverage_layers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    terrain = importlib.import_module(f"{_PKG}.adapters.qgis.coverage_layers.terrain")
    criteria = importlib.import_module(f"{_PKG}.core.domain.raster_filter_criteria")
    return terrain, criteria.RasterDerivative


terrain, D = _load()


def plane(rise_east=0.0, rise_north=0.0, size=6):
    """Grid whose elevation rises by ``rise_east`` per column and ``rise_north`` per row towards the north."""
    rows, cols = np.mgrid[0:size, 0:size].astype("float64")
    return 100.0 + rise_east * cols + rise_north * (size - 1 - rows)


class TestSlope:
    def test_flat_ground(self):
        flat = plane()
        assert np.allclose(terrain.derive(flat, D.SLOPE_DEGREES, 1, 1), 0)
        assert np.allclose(terrain.derive(flat, D.SLOPE_PERCENT, 1, 1), 0)

    def test_forty_five_degrees(self):
        slope = terrain.derive(plane(rise_east=1.0), D.SLOPE_DEGREES, 1.0, 1.0)
        assert np.allclose((slope), 45.0)
        assert np.allclose((terrain.derive(plane(rise_east=1.0), D.SLOPE_PERCENT, 1.0, 1.0)), 100.0)

    def test_pixel_size_scales_the_slope(self):
        # 1 m of rise over a 2 m pixel: 50 %.
        assert np.allclose((terrain.derive(plane(rise_east=1.0), D.SLOPE_PERCENT, 2.0, 2.0)), 50.0)

    def test_anisotropic_pixels(self):
        grid = plane(rise_north=1.0)
        assert np.allclose((terrain.derive(grid, D.SLOPE_PERCENT, 1.0, 4.0)), 25.0)

    def test_border_keeps_the_slope_of_a_plane(self):
        # The edge is extrapolated linearly: a filter "slope > 30" must not drop the outer ring.
        for grid in (plane(rise_east=1.0), plane(rise_north=1.0), plane(rise_east=1.0, rise_north=1.0)):
            slope = terrain.derive(grid, D.SLOPE_DEGREES, 1.0, 1.0)
            assert not np.isnan(slope).any()
            expected = math.degrees(math.atan(math.hypot(*[
                (grid[2, 3] - grid[2, 2]), (grid[2, 2] - grid[3, 2])])))
            assert np.allclose(slope, expected)

    def test_one_pixel_wide_grid_does_not_fail(self):
        assert terrain.derive(np.array([[1.0, 2.0, 3.0]]), D.SLOPE_DEGREES, 1.0, 1.0).shape == (1, 3)


class TestAspect:
    def test_downhill_to_the_west_is_270(self):
        assert np.allclose(terrain.derive(plane(rise_east=1.0), D.ASPECT, 1, 1), 270.0)

    def test_downhill_to_the_east_is_90(self):
        assert np.allclose(terrain.derive(plane(rise_east=-1.0), D.ASPECT, 1, 1), 90.0)

    def test_rising_to_the_north_faces_south(self):
        assert np.allclose(terrain.derive(plane(rise_north=1.0), D.ASPECT, 1, 1), 180.0)

    def test_rising_to_the_south_faces_north(self):
        assert np.allclose(terrain.derive(plane(rise_north=-1.0), D.ASPECT, 1, 1), 0.0, atol=1e-9) or \
            np.allclose(terrain.derive(plane(rise_north=-1.0), D.ASPECT, 1, 1), 360.0)

    def test_flat_has_no_aspect(self):
        assert np.isnan(terrain.derive(plane(), D.ASPECT, 1, 1)).all()


class TestHillshade:
    def test_flat_is_lit_by_the_sun_altitude(self):
        shade = terrain.derive(plane(), D.HILLSHADE, 1, 1)
        assert np.allclose(shade, 255.0 * math.sin(math.radians(terrain.HILLSHADE_ALTITUDE)))

    def test_slope_facing_the_sun_is_brighter_than_the_opposite_one(self):
        # The sun is at 315 deg (north-west): a face looking north-west is lit, a south-east one is not.
        facing_nw = terrain.derive(plane(rise_east=0.5, rise_north=-0.5), D.HILLSHADE, 1, 1)  # higher to the SE
        facing_se = terrain.derive(plane(rise_east=-0.5, rise_north=0.5), D.HILLSHADE, 1, 1)
        assert facing_nw.mean() > facing_se.mean()
        assert facing_nw.max() <= 255.0 and facing_se.min() >= 0.0


class TestRoughness:
    def test_flat(self):
        assert np.allclose(terrain.derive(plane(), D.ROUGHNESS, 1, 1), 0)

    def test_spike(self):
        grid = np.zeros((5, 5))
        grid[2, 2] = 8.0
        rough = terrain.derive(grid, D.ROUGHNESS, 1, 1)
        assert rough[2, 2] == pytest.approx(8.0)  # eight neighbours 8 m below: mean |diff| = 8
        assert rough[1, 1] == pytest.approx(1.0)  # one neighbour (the spike) 8 m above, seven equal


class TestNoData:
    def test_nodata_in_the_window_is_nodata(self):
        grid = plane(rise_east=1.0)
        grid[3, 3] = np.nan
        slope = terrain.derive(grid, D.SLOPE_DEGREES, 1, 1)
        assert np.isnan(slope[2:5, 2:5]).all()  # the pixel and its eight neighbours
        assert not np.isnan(slope[0, 0])

    def test_nodata_pixel_is_nodata_even_with_valid_neighbours(self):
        grid = plane(rise_east=1.0)
        grid[3, 3] = np.nan
        assert np.isnan(terrain.derive(grid, D.ROUGHNESS, 1, 1)[3, 3])


class TestValueAndErrors:
    def test_value_is_the_array_itself(self):
        grid = plane(rise_east=1.0)
        assert terrain.derive(grid, D.VALUE, 1, 1) is grid

    def test_non_positive_pixel_size(self):
        with pytest.raises(ValueError):
            terrain.derive(plane(), D.SLOPE_DEGREES, 0, 1)


class TestGroundCellSize:
    def test_projected_crs_is_unchanged(self):
        assert terrain.ground_cell_size(1.0, -1.0, False) == (1.0, 1.0)

    def test_degrees_become_metres(self):
        size_x, size_y = terrain.ground_cell_size(0.001, 0.001, True, latitude=0.0)
        assert size_x == pytest.approx(111.32) and size_y == pytest.approx(110.574)

    def test_web_mercator_metres_shrink_with_latitude(self):
        assert terrain.ground_cell_size(10.0, 10.0, False, 0.0, mercator=True) == (10.0, 10.0)
        size_x, size_y = terrain.ground_cell_size(10.0, 10.0, False, 60.0, mercator=True)
        assert size_x == pytest.approx(5.0) and size_y == pytest.approx(5.0)

    def test_slope_in_mercator_is_corrected(self):
        # 1 projected metre of rise per projected metre at 60 N is 2 rise per ground metre: ~63.4 deg.
        sx, sy = terrain.ground_cell_size(1.0, 1.0, False, 60.0, mercator=True)
        slope = terrain.derive(plane(rise_east=1.0), D.SLOPE_DEGREES, sx, sy)
        assert np.allclose(slope, math.degrees(math.atan(2.0)))

    def test_longitude_shrinks_with_latitude(self):
        at_equator = terrain.ground_cell_size(0.001, 0.001, True, 0.0)[0]
        at_45 = terrain.ground_cell_size(0.001, 0.001, True, 45.0)[0]
        assert at_45 == pytest.approx(at_equator * math.cos(math.radians(45)))
