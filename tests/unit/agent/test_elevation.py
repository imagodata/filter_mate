# -*- coding: utf-8 -*-
"""Elevation of the agent (``core/agent/elevation.py``): the tiles an area needs, the grid it is written on, contours."""
import pytest

from core.agent.elevation import (
    MAX_LEVELS, MAX_MESSAGE, MAX_PIXELS, MAX_TILES, NO_DATA, SOURCES, bbox_problem, contour_problem, ground_size,
    is_index, empty_note, gdal_srs, known, metric_grid, quiet_message, resolution_for, tile_name, tile_url, tiles_for,
    tiles_for_grid, utm_authid,
)
from core.agent.open_data import KIND_ELEVATION, NO_DATA_KINDS, resolve_platform
from core.agent.sources import BUILT_IN, describe_enabled

pytestmark = pytest.mark.unit
LYON = [4.78, 45.70, 4.92, 45.80]


def test_every_elevation_source_is_a_source_and_a_platform_that_holds_no_data_to_search():
    sources = {source.id: source for source in BUILT_IN}
    for source in SOURCES:
        assert source.base.startswith("https://") and source.attribution and source.note
        assert sources[source.id].kind == KIND_ELEVATION and sources[source.id].address == source.base
        assert resolve_platform(source.id) == (KIND_ELEVATION, source.base)
        assert known(source.id.upper()) is source
    assert KIND_ELEVATION in NO_DATA_KINDS
    assert known("srtm") is None and known("") is None


def test_an_elevation_source_is_named_apart_from_the_platforms_searched():
    enabled = [source for source in BUILT_IN if source.id in ("copernicus_dem", "datagouv")]
    names = describe_enabled(enabled)
    assert names["elevation"] == ["copernicus_dem"]
    assert names["platforms"] == ["datagouv"]


@pytest.mark.parametrize("latitude, longitude, name", [
    (45, 4, "Copernicus_DSM_COG_10_N45_00_E004_00_DEM"),
    (-1, -1, "Copernicus_DSM_COG_10_S01_00_W001_00_DEM"),
    (0, 0, "Copernicus_DSM_COG_10_N00_00_E000_00_DEM"),
    (-34, 151, "Copernicus_DSM_COG_10_S34_00_E151_00_DEM"),
    (64, -22, "Copernicus_DSM_COG_10_N64_00_W022_00_DEM"),
])
def test_a_tile_is_named_by_its_south_west_corner(latitude, longitude, name):
    assert tile_name(latitude, longitude) == name
    assert tile_url(SOURCES[0], latitude, longitude) == f"{SOURCES[0].base}/{name}/{name}.tif"


@pytest.mark.parametrize("bbox, tiles", [
    (LYON, [(45, 4)]),
    ([4.9, 45.9, 5.1, 46.1], [(45, 4), (45, 5), (46, 4), (46, 5)]),
    ([-0.5, -0.5, 0.5, 0.5], [(-1, -1), (-1, 0), (0, -1), (0, 0)]),
    ([4.0, 45.0, 5.0, 46.0], [(45, 4)]),  # an edge on a whole degree needs no tile beyond it
    ([179.5, 10.0, 180.0, 10.5], [(10, 179)]),
])
def test_the_tiles_an_area_touches(bbox, tiles):
    assert tiles_for(bbox) == tiles


@pytest.mark.parametrize("bbox", [
    [5.0, 45.0, 4.0, 46.0], [4.0, 46.0, 5.0, 45.0], [4.0, 45.0, 4.0, 46.0], [-181.0, 0.0, 1.0, 1.0],
    [0.0, 0.0, 1.0, 91.0], [0.0, 0.0, 1.0], [0.0, 0.0, float("nan"), 1.0], [0.0, 0.0, float("inf"), 1.0],
    ["4", 45.0, 5.0, 46.0],
])
def test_bounds_that_are_none_are_refused(bbox):
    assert bbox_problem(bbox)
    with pytest.raises(ValueError):
        tiles_for(bbox)


def test_an_area_of_too_many_tiles_is_refused_with_the_limit():
    assert len(tiles_for([0.0, 40.0, 4.0, 44.0])) == MAX_TILES
    with pytest.raises(ValueError, match=str(MAX_TILES)):
        tiles_for([0.0, 40.0, 4.5, 44.0])


@pytest.mark.parametrize("longitude, latitude, authid", [
    (4.84, 45.76, "EPSG:32631"), (2.35, 48.85, "EPSG:32631"), (-73.6, 45.5, "EPSG:32618"),
    (151.2, -33.9, "EPSG:32756"), (-180.0, 10.0, "EPSG:32601"), (180.0, 10.0, "EPSG:32660"),
])
def test_the_utm_zone_of_a_place(longitude, latitude, authid):
    assert utm_authid(longitude, latitude) == authid


def test_elevation_is_written_on_the_crs_of_the_project_only_when_it_keeps_distances():
    assert metric_grid("EPSG:2154", projected=True, metres=True)
    assert not metric_grid("EPSG:3857", projected=True, metres=True)  # the metres of the equator
    assert not metric_grid("epsg:3857", projected=True, metres=True)
    assert not metric_grid("EPSG:4326", projected=False, metres=False)
    assert not metric_grid("EPSG:2227", projected=True, metres=False)  # feet


def test_a_town_is_written_at_the_resolution_of_the_source():
    width, height = ground_size(LYON)
    assert 10_500 < width < 11_200 and 11_000 < height < 11_300
    assert resolution_for(LYON, None, 30.0) == (30.0, "")


def test_a_large_area_is_written_coarser_and_says_so():
    bbox = [3.0, 44.0, 6.5, 47.0]
    resolution, note = resolution_for(bbox, None, 30.0)
    width, height = ground_size(bbox)
    assert resolution > 30.0 and resolution % 30.0 == 0 and "rather than 30 m" in note
    assert width * height / resolution ** 2 <= MAX_PIXELS
    assert width * height / (resolution - 30.0) ** 2 > MAX_PIXELS  # the finest that fits


def test_a_resolution_asked_is_kept_or_refused_with_one_that_fits():
    assert resolution_for(LYON, 90.0, 30.0) == (90.0, "")
    resolution, note = resolution_for(LYON, 10.0, 30.0)
    assert resolution == 10.0 and "no detail" in note
    with pytest.raises(ValueError, match="or more"):
        resolution_for([3.0, 44.0, 6.5, 47.0], 30.0, 30.0)
    for wrong in (0.0, -30.0, 5.0, 10_000.0, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            resolution_for(LYON, wrong, 30.0)


def test_contour_intervals():
    assert contour_problem(151.0, 608.0, 25.0, 100.0) == ""
    assert contour_problem(151.0, 608.0, 25.0, None) == ""
    assert contour_problem(0.0, 500.0, 2.5, 10.0) == ""
    for interval in (0.0, -5.0, float("nan"), float("inf")):
        assert "interval" in contour_problem(0.0, 500.0, interval, None)
    assert "multiple" in contour_problem(0.0, 500.0, 25.0, 60.0)
    assert "multiple" in contour_problem(0.0, 500.0, 25.0, 25.0)  # every contour an index contour says nothing
    assert "index_interval" in contour_problem(0.0, 500.0, 25.0, 0.0)


def test_too_many_levels_are_refused_with_an_interval_that_fits():
    problem = contour_problem(0.0, 4800.0, 1.0, None)
    assert str(MAX_LEVELS) in problem and "ask for 10 or more" in problem
    assert contour_problem(0.0, 4800.0, 10.0, None) == ""
    # A raster whose statistics could not be read is not judged on them.
    assert contour_problem(float("nan"), float("nan"), 1.0, None) == ""


@pytest.mark.parametrize("elevation, index, expected", [
    (100.0, 100.0, True), (300.0, 100.0, True), (125.0, 100.0, False), (0.0, 100.0, True), (-200.0, 100.0, True),
    (12.5, 2.5, True), (11.0, 2.5, False), (0.30000000000000004, 0.1, True),
])
def test_an_index_contour_is_a_whole_number_of_index_intervals(elevation, index, expected):
    assert is_index(elevation, index) is expected


def test_a_refusal_names_no_height_when_the_values_are_not_shared():
    told = contour_problem(1234.5, 4321.0, 1.0, None)
    quiet = contour_problem(1234.5, 4321.0, 1.0, None, tell_heights=False)
    assert "1234.5" in told and "4321" in told and "or more" in told
    assert quiet and not any(char.isdigit() for char in quiet.replace("an interval of 1 ", "").replace(str(MAX_LEVELS), ""))
    # What says nothing of the raster is said the same.
    assert contour_problem(0.0, 500.0, 25.0, 60.0, tell_heights=False) == contour_problem(0.0, 500.0, 25.0, 60.0)


@pytest.mark.parametrize("said, kept, gone", [
    ("`/vsicurl/https://bucket.example.org/a/b.tif?X-Amz-Signature=SECRET' does not exist in the file system",
     "does not exist", ("example.org", "SECRET", "vsicurl", "https")),
    ("Attempt to create new tiff file `/home/simon/.local/share/QGIS/QGIS3/profiles/default/filtermate/open_data/"
     "elevation-ab12/copernicus_dem_30m.tif' failed: No space left on device",
     "copernicus_dem_30m.tif' failed: No space left on device", ("/home", "simon", "profiles")),
    ("C:\\Users\\Simon\\AppData\\Roaming\\QGIS\\QGIS4\\dem.tif: Permission denied", "dem.tif: Permission denied",
     ("Users", "Simon", "AppData")),
    ("/vsizip//vsicurl/http://127.0.0.1:8080/a.zip/dem.tif not recognized as a supported file format",
     "not recognized", ("127.0.0.1", "vsizip", "a.zip")),
    ("HTTP error code : 503", "HTTP error code : 503", ()),
])
def test_what_a_library_said_goes_to_a_model_without_an_address_nor_a_folder(said, kept, gone):
    message = quiet_message(said)
    assert kept in message
    for word in gone:
        assert word not in message, (word, message)


@pytest.mark.parametrize("said, kept, gone", [
    # The folders of a path hold the name of the person and of their clients, spaces included.
    ("C:\\Users\\Jean Dupont\\AppData\\Local\\Temp\\x.tif: No such file or directory",
     "x.tif: No such file or directory", ("Jean", "Dupont", "AppData", "Users")),
    ("Cannot open /vsis3/my-private-bucket/dir/key.tif", "key.tif", ("my-private-bucket", "vsis3", "dir")),
    ("D:/projets/client secret/dem.tif: Permission denied", "dem.tif: Permission denied",
     ("projets", "client", "secret")),
    ("\\\\serveur\\partage compta\\mnt.tif: not recognized", "mnt.tif: not recognized", ("serveur", "compta")),
    ("`/home/jean dupont/data/mnt.tif' not recognized", "mnt.tif' not recognized", ("jean", "dupont", "/home")),
    ("Cannot open data/clients/dem.tif", "Cannot open dem.tif", ("data", "clients")),
    # What a driver says of a connection: no host, no user, no password.
    ("PG: dbname='ign' host=db.client.example port=5432 user=jean password='s3 cret' sslmode=require",
     "a database connection", ("ign", "client", "5432", "jean", "s3 cret", "password")),
    ("PQconnectdb failed: dbname=ign host=10.0.0.5 password=hunter2 refused", "refused", ("hunter2", "10.0.0.5", "ign")),
    # Not paths: what is said as a sentence stays.
    ("the read/write mode is 50 / 60", "the read/write mode is 50 / 60", ()),
])
def test_a_message_keeps_the_name_of_a_file_and_no_folder_nor_connection(said, kept, gone):
    message = quiet_message(said)
    assert kept in message, message
    for word in gone:
        assert word not in message, (word, message)


def test_a_message_is_one_short_line_and_never_empty():
    assert quiet_message("") == quiet_message(None) == "no reason given"
    assert quiet_message("a\n  b\tc") == "a b c"
    assert len(quiet_message("x" * 5000)) == MAX_MESSAGE


def test_the_corners_of_a_grid_in_metres_are_read_from_the_squares_they_fall_in():
    """[4.5, 45, 5, 45.5] sits on the south edge of N45: its UTM 31N rectangle reaches down into N44 (measured on the
    real model: 2.5 % of the grid written at 0 m)."""
    asked = [4.5, 45.0, 5.0, 45.5]
    assert tiles_for(asked) == [(45, 4)]
    envelope = [4.48, 44.98, 5.02, 45.52]  # what cs2cs gives for the rectangle of the area in UTM 31N, give or take
    assert tiles_for_grid(asked, envelope) == [(44, 4), (44, 5), (45, 4), (45, 5)]
    # Inside a square, the corners stay in it: nothing more is read.
    assert tiles_for_grid([4.3, 45.3, 4.7, 45.7], [4.29, 45.29, 4.71, 45.71]) == [(45, 4)]
    # The globe is not left: the antimeridian is clipped, no square of E180 is asked.
    assert tiles_for_grid([179.0, 60.0, 180.0, 61.0], [178.9, 59.9, 180.4, 61.1]) == [
        (row, column) for row in (59, 60, 61) for column in (178, 179)]


def test_the_corners_stay_empty_when_they_would_need_more_squares_than_one_call_reads():
    asked = [0.1, 40.1, 3.9, 43.9]  # 4 x 4 squares
    assert len(tiles_for(asked)) == MAX_TILES
    assert tiles_for_grid(asked, [-0.2, 39.8, 4.2, 44.2]) == tiles_for(asked)
    with pytest.raises(ValueError, match="16 at most"):
        tiles_for_grid([0, 40, 9, 49], [0, 40, 9, 49])


def test_what_no_tile_reaches_is_said_by_its_share():
    assert NO_DATA < -1000  # below any height of the earth: the Dead Sea is at -430 m
    assert empty_note(0, 1000, "has no tile") == "" and empty_note(5, 0, "has no tile") == ""
    note = empty_note(25_000, 100_000, "has no tile there")
    assert note.startswith("25 % of the grid is empty (no data)") and "minimum, maximum and mean" in note
    assert "has no tile there" in note
    assert empty_note(40, 100_000, "x").startswith("under 1 %")


@pytest.mark.parametrize("authid, expected", [
    ("EPSG:32631", "EPSG:32631"), ("epsg:2154", "epsg:2154"), ("ESRI:102003", "ESRI:102003"), ("IGNF:LAMB93", "IGNF:LAMB93"),
    # A CRS of the user has an authid of QGIS alone, which GDAL refuses: its WKT is given.
    ("USER:100000", "WKT"), ("", "WKT"), (None, "WKT"), ("PROJ:foo", "WKT"), ("EPSG:", "WKT"),
])
def test_gdal_is_told_a_crs_by_its_authid_only_when_it_knows_the_authority(authid, expected):
    assert gdal_srs(authid, lambda: "WKT") == expected


def test_the_wkt_is_asked_for_only_when_it_is_needed():
    def never():
        raise AssertionError("the WKT of a CRS GDAL knows is not computed")
    assert gdal_srs("EPSG:2154", never) == "EPSG:2154"
