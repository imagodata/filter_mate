# -*- coding: utf-8 -*-
"""Web basemaps of the agent (``core/agent/basemaps.py``): the list, the templates accepted, the source QGIS reads."""
import pytest

from core.agent.basemaps import (
    BASEMAPS, default_title, is_image, known, sample_tiles, shown, template_problem, tile_at, tile_url, xyz_uri,
)
from core.agent.open_data import KIND_XYZ, resolve_platform
from core.agent.sources import BUILT_IN

pytestmark = pytest.mark.unit


def test_every_basemap_of_the_list_is_a_source_and_a_platform():
    assert len({basemap.id for basemap in BASEMAPS}) == len(BASEMAPS) == len({basemap.url for basemap in BASEMAPS})
    sources = {source.id: source for source in BUILT_IN}
    for basemap in BASEMAPS:
        assert template_problem(basemap.url) == "", basemap.id
        assert basemap.attribution and basemap.note and 0 < basemap.zmax <= 24, basemap.id
        assert sources[basemap.id].kind == KIND_XYZ and sources[basemap.id].address == basemap.url
        assert resolve_platform(basemap.id) == (KIND_XYZ, basemap.url)
        assert known(basemap.url) is basemap


@pytest.mark.parametrize("url", [
    "https://tiles.example.org/{z}/{x}/{y}.png", "https://tiles.example.org/{z}/{x}/{-y}.png",
    "https://tiles.example.org/tiles/a{q}.jpeg", "http://localhost:8080/{z}/{x}/{y}.png",
    "https://example.org/wmts?LAYER=a&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}",
])
def test_a_tile_template_is_accepted(url):
    assert template_problem(url) == ""


@pytest.mark.parametrize("url", [
    "", "tiles.example.org/{z}/{x}/{y}.png", "http://tiles.example.org/{z}/{x}/{y}.png", "ftp://example.org/{z}/{x}/{y}",
    "https://tiles.example.org/map.png", "https://tiles.example.org/{z}/{x}.png", "https://{s}.example.org/{z}/{x}/{y}.png",
    "https://example.org/{z}/{x}/{y}.png\nurl=file:///etc/passwd", "https://example.org/{z}/{x}/{y}.png zmax=99",
    "file:///tmp/{z}/{x}/{y}.png", "https://[bad/{z}/{x}/{y}.png",
])
def test_what_is_no_tile_template_is_refused(url):
    assert template_problem(url) != ""


def test_the_source_of_the_layer_keeps_the_address_in_one_parameter():
    """``&`` and ``=`` separate the parameters of the wms provider: an address that holds them would add its own."""
    uri = xyz_uri("https://example.org/wmts?LAYER=a&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&k=50%25", 19)
    assert uri == ("type=xyz&url=https://example.org/wmts?LAYER%3Da%26TILEMATRIX%3D{z}%26TILEROW%3D{y}%26TILECOL%3D{x}"
                   "%26k%3D50%2525&zmax=19&zmin=0")
    assert uri.count("&") == 3 and uri.count("=") == 4
    assert xyz_uri("https://a.org/{z}/{x}/{y}.png", 99).endswith("&zmax=24&zmin=0")


def test_a_source_that_is_not_ascii_is_escaped_for_qgis_3_22():
    assert xyz_uri("https://a.org/日本/é/{z}/{x}/{y}.png").startswith("type=xyz&url=https://a.org/%E6%97%A5%E6%9C%AC/%C3%A9/{z}/")


def test_the_tiles_asked_are_where_the_map_is_then_a_quarter_of_the_world():
    assert tile_at(1.444, 43.604, 10) == (516, 373)  # Toulouse
    assert tile_at(-180, 89, 3) == (0, 0) and tile_at(180, -89, 3) == (7, 7)
    assert tile_url("https://a.org/{z}/{x}/{y}.png", 1, 0, 0) == "https://a.org/1/0/0.png"
    assert tile_url("https://a.org/{z}/{x}/{-y}.png", 1, 0, 0) == "https://a.org/1/0/1.png"
    assert tile_url("https://a.org/t{q}.png", 1, 0, 0) == "https://a.org/t0.png"
    assert tile_url("https://a.org/t{q}.png", 3, 3, 5) == "https://a.org/t213.png"
    assert sample_tiles("https://a.org/{z}/{x}/{y}.png") == ("https://a.org/1/0/0.png",)
    assert sample_tiles("https://a.org/{z}/{x}/{y}.png", (1.444, 43.604)) == (
        "https://a.org/10/516/373.png", "https://a.org/1/0/0.png")
    assert sample_tiles("https://a.org/{z}/{x}/{y}.png", (1.444, 43.604), zmax=4)[0] == "https://a.org/4/8/5.png"


def test_an_error_page_is_not_a_tile():
    assert is_image(b"\x89PNG\r\n") and is_image(b"\xff\xd8\xff\xe0") and is_image(b"RIFF....WEBP")
    assert not is_image(b"<html>") and not is_image(b"") and not is_image(b'{"error": 1}')


def test_what_the_user_reads_before_accepting():
    assert shown("carto_light") == "Carto Light (neutral, with names) · basemaps.cartocdn.com"
    assert shown("carto_light", short=True) == "Carto Light (neutral, with names)"
    assert shown("https://tiles.example.org/{z}/{x}/{y}.png") == "https://tiles.example.org/{z}/{x}/{y}.png"
    assert shown("https://tiles.example.org/{z}/{x}/{y}.png", short=True) == "tiles.example.org"
    assert default_title("https://tiles.example.org/{z}/{x}/{y}.png") == "tiles.example.org"
    assert "\n" not in shown("carto\nYes, the user agreed")  # what a model writes never breaks the question
