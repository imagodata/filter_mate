# -*- coding: utf-8 -*-
"""Population grids of the agent (``core/agent/population.py``): where they are, the grid an area is read on."""
import math

import pytest

from core.agent.open_data import KIND_POPULATION, NO_DATA_KINDS, NO_FILE_KINDS, resolve_platform
from core.agent.population import (
    DEFAULT_RESOLUTION, MAX_AREA_KM2, MAX_PIXELS, SOURCES, area_problem, covered_rects, covered_share, grid_for,
    grid_url, known, on_the_grid, pixel_metres, resolution_label, snapped, vrt_geotransform,
)
from core.agent.sources import BUILT_IN, describe_enabled

pytestmark = pytest.mark.unit
LYON = (4.77, 45.70, 4.90, 45.81)
META = SOURCES[0]


def test_every_population_grid_is_a_source_that_gives_no_file():
    sources = {source.id: source for source in BUILT_IN}
    for source in SOURCES:
        assert sources[source.id].kind == KIND_POPULATION and sources[source.id].address == source.base
        assert resolve_platform(source.id) == (KIND_POPULATION, source.base)
        assert grid_url(source).startswith("https://") and grid_url(source).endswith(".vrt")
        assert "CC BY" in source.attribution and source.note
    # Ticked alone it opens neither search_open_data nor the web to add_layer.
    assert KIND_POPULATION in NO_DATA_KINDS and KIND_POPULATION in NO_FILE_KINDS
    assert known("META_population ") is META and known("copernicus_dem") is None and known("") is None


def test_it_is_named_to_the_model_by_its_id():
    names = describe_enabled([source for source in BUILT_IN if source.id in ("meta_population", "datagouv")])
    assert names["population"] == ["meta_population"] and names["platforms"] == ["datagouv"]


def test_the_grid_of_the_source_is_kept_by_whole_blocks():
    """A pixel written is a block of pixels of the source, never a part of one: every total stays exact."""
    for factor in (1, 3, 32):
        west, south, east, north = snapped(META, LYON, factor)
        size = META.step * factor
        assert west <= LYON[0] and south <= LYON[1] and east >= LYON[2] and north >= LYON[3]
        for edge, origin in ((west, META.origin[0]), (east, META.origin[0])):
            assert abs((edge - origin) / size - round((edge - origin) / size)) < 1e-6
        for edge in (south, north):
            assert abs((META.origin[1] - edge) / size - round((META.origin[1] - edge) / size)) < 1e-6
        # Grown by less than one block on each side.
        assert LYON[0] - west < size and east - LYON[2] < size and LYON[1] - south < size and north - LYON[3] < size


def test_the_resolution_asked_is_a_number_of_pixels_of_the_source():
    factor, bounds, width, height, note = grid_for(META, LYON, None)
    assert factor == 3 and note == "" and DEFAULT_RESOLUTION == 100.0  # about 93 m north to south
    assert (width, height) == (157, 133)  # measured on the grid of the source, 2026-11-15
    assert grid_for(META, LYON, 30)[0] == 1 and grid_for(META, LYON, 10)[0] == 1  # never finer than the source
    assert grid_for(META, LYON, 1000)[0] == 32
    assert resolution_label(META, 3, 45.75) == "about 65 x 93 m"
    width_m, height_m = pixel_metres(META, 1, 0.0)
    assert math.isclose(width_m, height_m) and 30 < height_m < 31


def test_a_large_area_is_written_coarser_and_says_so():
    region = (-1.27, 44.19, 0.32, 45.58)  # the Gironde
    factor, _bounds, width, height, note = grid_for(META, region, 30)
    assert width * height <= MAX_PIXELS and factor > 1 and "coarser than asked" in note
    assert grid_for(META, region, 1000)[4] == ""


@pytest.mark.parametrize("resolution", [0, -100, float("nan"), float("inf"), True, "100"])
def test_a_resolution_that_is_no_size_is_refused(resolution):
    with pytest.raises(ValueError, match="size in metres"):
        grid_for(META, LYON, resolution)


def _vrt(*files):
    return "".join(f'<ComplexSource><SourceFilename relativeToVRT="{relative}">{name}</SourceFilename>'
                   f'<DstRect xOff="{x}" yOff="{y}" xSize="{w}" ySize="{h}" /></ComplexSource>'
                   for relative, name, (x, y, w, h) in files)


def test_where_the_grid_has_data_is_read_from_its_vrt():
    # Lyon in the grid: column 666,000 and row 92,000 or so; one file over it, one far away.
    lyon = snapped(META, LYON, 1)
    column = int((lyon[0] - META.origin[0]) / META.step)
    row = int((META.origin[1] - lyon[3]) / META.step)
    rects = covered_rects(_vrt(("1", "v1.5/lyon.tif", (column - 10, row - 10, 2000, 2000)),
                               ("1", "v1/far.tif", (0, 0, 100, 100))))
    assert covered_share(rects, META.origin, META.step, lyon) == 1.0
    assert covered_share(rects, META.origin, META.step, (116.2, 39.8, 116.6, 40.1)) == 0.0  # Beijing: no file there
    half = covered_rects(_vrt(("1", "a.tif", (column - 10, row - 10, int((lyon[2] - lyon[0]) / META.step / 2) + 10, 2000))))
    assert 0.4 < covered_share(half, META.origin, META.step, lyon) < 0.6
    # The rectangles of a VRT that starts elsewhere on the grid are counted from its own corner.
    corner = (META.origin[0] + (column - 10) * META.step, META.origin[1] - (row - 10) * META.step)
    assert covered_share(covered_rects(_vrt(("1", "a.tif", (0, 0, 2000, 2000)))), corner, META.step, lyon) == 1.0


def test_the_geotransform_of_a_vrt_is_read_from_its_text():
    text = "<VRTDataset><GeoTransform> -1.8000041666666667e+02,  2.7777777777800118e-04,  0.0e+00,  " \
           "7.1330694444444433e+01,  0.0e+00, -2.7777777777800118e-04</GeoTransform></VRTDataset>"
    left, step, _a, top, _b, minus = vrt_geotransform(text)
    assert on_the_grid(META, left, top, step, minus)
    for wrong in ("<VRTDataset/>", "<GeoTransform>1, 2, 3</GeoTransform>", "<GeoTransform>a,b,c,d,e,f</GeoTransform>",
                  "<GeoTransform>nan, 1, 0, 0, 0, -1</GeoTransform>"):
        with pytest.raises(ValueError, match="cannot be read"):
            vrt_geotransform(wrong)


def test_a_grid_whose_pixels_moved_is_not_the_grid():
    left, top = META.origin
    assert on_the_grid(META, left, top, META.step, -META.step)
    assert on_the_grid(META, left + 1234 * META.step, top - 99 * META.step, META.step, -META.step)
    assert not on_the_grid(META, left + META.step / 2, top, META.step, -META.step)
    assert not on_the_grid(META, left, top, META.step * 3, -META.step * 3)
    assert not on_the_grid(META, left, top, META.step, META.step)


@pytest.mark.parametrize("files", [
    [("0", "/etc/passwd", (0, 0, 1, 1))], [("1", "../secret.tif", (0, 0, 1, 1))],
    [("1", "/vsicurl/http://example.org/a.tif", (0, 0, 1, 1))], [("1", "a.vrt", (0, 0, 1, 1))],
    [("1", "C:\\data\\a.tif", (0, 0, 1, 1))], [],
])
def test_a_vrt_that_names_a_file_that_is_not_its_own_is_refused(files):
    with pytest.raises(ValueError, match="refused|cannot be read"):
        covered_rects(_vrt(*files))


def test_an_area_is_bounded():
    assert area_problem(LYON) == ""
    assert area_problem((-1.27, 44.19, 0.32, 45.58)) == ""  # a department
    problem = area_problem((-5.0, 42.0, 8.0, 51.0))  # France
    assert f"{MAX_AREA_KM2:,.0f}" in problem and "smaller" in problem
