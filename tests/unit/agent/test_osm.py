# -*- coding: utf-8 -*-
"""OpenStreetMap features of the agent (``core/agent/osm.py``): the tags a model may ask, the query written from
them, how the answer is read."""
import pytest

from core.agent.open_data import KIND_OVERPASS, KINDS, NO_DATA_KINDS, NO_FILE_KINDS, parse_extra_domains, resolve_platform
from core.agent.osm import (
    DEFAULT_SERVER, GEOMETRIES, MAX_AREA_KM2, MAX_BYTES, MAX_TAGS, SERVERS, Tag, area_km2, area_problem, columns,
    default_name,
    gdal_config, layer_title, matches, overpass_query, read_tags, remark_problem, status_problem, summary,
)
from core.agent.sources import BUILT_IN, describe_enabled, make_source, model_name, platform_aliases, platform_domains

pytestmark = pytest.mark.unit
LYON = [4.77, 45.70, 4.90, 45.81]


def test_every_overpass_server_is_a_source_and_a_platform_that_gives_no_file():
    sources = {source.id: source for source in BUILT_IN}
    assert len({server.id for server in SERVERS}) == len(SERVERS) >= 2 and DEFAULT_SERVER == SERVERS[0].id == "overpass_fr"
    for server in SERVERS:
        assert server.url.startswith("https://") and server.url.endswith("/api/interpreter") and server.note
        assert sources[server.id].kind == KIND_OVERPASS and sources[server.id].address == server.url
        assert resolve_platform(server.id) == (KIND_OVERPASS, server.url)
    # Ticked alone it opens neither search_open_data nor the web to add_layer; a user can add a server of their own.
    assert KIND_OVERPASS in NO_DATA_KINDS and KIND_OVERPASS in NO_FILE_KINDS and KIND_OVERPASS in KINDS


def test_a_server_the_user_added_is_named_to_the_model_by_its_id():
    mine = make_source("https://overpass.example.org/api/interpreter?key=SECRET", "overpass", "Mine")
    names = describe_enabled([mine, next(source for source in BUILT_IN if source.id == "overpass_fr")])
    assert names["osm"] == [f"{mine.id} (Mine)", "overpass_fr"] and names["platforms"] == []
    assert "SECRET" not in model_name(mine) and "example.org" not in str(names)
    assert platform_aliases([mine]) == {mine.id: "https://overpass.example.org/api/interpreter?key=secret"}
    assert parse_extra_domains(platform_domains([mine])) == {
        "https://overpass.example.org/api/interpreter?key=secret": (KIND_OVERPASS, mine.address)}


def test_tags_are_read_one_by_one():
    tags = read_tags([{"key": "amenity", "value": "hospital"}, {"key": "building"}, {"key": "addr:street", "value": ""},
                      {"key": "amenity", "value": "hospital"}])
    assert tags == [Tag("amenity", "hospital"), Tag("building"), Tag("addr:street")]
    assert [tag.column for tag in tags] == ["amenity", "building", "addr_street"]
    assert [tag.shown() for tag in tags] == ["amenity=hospital", "building", "addr:street"]
    assert read_tags([{"key": "name", "value": "Hôpital Édouard Herriot"}])[0].value == "Hôpital Édouard Herriot"
    assert len(read_tags([{"key": f"k{index}"} for index in range(MAX_TAGS)])) == MAX_TAGS


@pytest.mark.parametrize("tags", [
    [], None, "amenity=hospital", {"key": "amenity"}, [["amenity", "hospital"]], [{"value": "hospital"}],
    [{"key": 'amenity"]'}], [{"key": "amenity](1,2,3,4);node"}], [{"key": "a b"}], [{"key": "1a"}], [{"key": ""}],
    [{"key": "a\\b"}], [{"key": "k" * 61}], [{"key": "osm_id"}], [{"key": "other_tags"}], [{"key": "osm:type"}],
    [{"key": "amenity", "value": 'x"];node(1);out;'}], [{"key": "amenity", "value": "a\\"}],
    [{"key": "amenity", "value": "a\nb"}], [{"key": "amenity", "value": " hospital"}],
    [{"key": "amenity", "value": "v" * 81}], [{"key": "amenity", "value": 3}],
    [{"key": "addr:street"}, {"key": "addr_street"}], [{"key": f"k{index}"} for index in range(MAX_TAGS + 1)],
])
def test_what_is_no_tag_is_refused(tags):
    with pytest.raises(ValueError):
        read_tags(tags)


def test_the_query_is_written_from_the_tags_and_the_bounds_alone():
    query = overpass_query(read_tags([{"key": "amenity", "value": "hospital"}, {"key": "building"}]), LYON)
    assert query == ("[out:xml][timeout:60][maxsize:67108864];\n(\n"
                     '  nwr["amenity"="hospital"](45.7000000,4.7700000,45.8100000,4.9000000);\n'
                     '  nwr["building"](45.7000000,4.7700000,45.8100000,4.9000000);\n'
                     ");\n(._;>;);\nout body;\n")
    assert f"[maxsize:{MAX_BYTES}]" in query
    # The nodes of the ways, and everything in the order of an OpenStreetMap file: GDAL builds no area otherwise.
    assert query.index("(._;>;);") < query.index("out body;") and "out skel" not in query


def test_the_keys_asked_are_columns_of_every_layer():
    config = gdal_config(read_tags([{"key": "healthcare"}, {"key": "highway", "value": "primary"}, {"key": "addr:street"}]))
    assert "[general]" not in config  # GDAL 3.4 does not know the section
    assert config.splitlines()[1] == "attribute_name_laundering=yes"
    for layer in ("points", "lines", "multipolygons", "multilinestrings", "other_relations"):
        assert f"[{layer}]\nosm_id=yes" in config
    assert config.count("attributes=name,healthcare,highway,addr:street") == 5
    areas = config.splitlines()[0].split("=", 1)[1].split(",")
    # A closed way that carries a key asked is an area, but not what is drawn as a line even when it closes.
    assert "healthcare" in areas and "addr:street" in areas and "building" in areas and "highway" not in areas
    assert "highway=platform" in areas
    assert columns(read_tags([{"key": "addr:street"}, {"key": "name"}])) == ["name", "addr_street"]


def test_a_feature_is_kept_when_it_carries_one_of_the_tags():
    tags = read_tags([{"key": "amenity", "value": "hospital"}, {"key": "building"}])
    assert matches(tags, {"amenity": "hospital", "building": None})
    assert matches(tags, {"amenity": "school", "building": "yes"})
    assert not matches(tags, {"amenity": "school", "building": None})
    assert not matches(tags, {"amenity": "", "building": ""})
    assert not matches(tags, {"name": "Entrée", "other_tags": '"entrance"=>"yes"'})  # a node that came with its way


def test_an_area_is_bounded():
    assert 100 < area_km2(LYON) < 130
    assert area_problem(LYON) == ""
    problem = area_problem([4.0, 45.0, 6.0, 47.0])
    assert f"{MAX_AREA_KM2:,.0f}" in problem and "smaller" in problem


@pytest.mark.parametrize("tail, word", [
    (b'</way><remark> runtime error: Query timed out in "query" at line 3 after 61 seconds. </remark></osm>', "time"),
    (b"<remark> runtime error: Query run out of memory using about 2048 MB of RAM. </remark>\n</osm>", "too large"),
    (b"<remark> runtime error: something else </remark></osm>", "before its answer was whole"),
])
def test_an_answer_cut_short_by_its_server_is_said_so(tail, word):
    assert word in remark_problem(tail)


def test_a_whole_answer_has_no_remark():
    assert remark_problem(b"</relation>\n\n</osm>\n") == "" and remark_problem(b"") == ""


def test_what_a_status_means():
    assert status_problem(200) == ""
    assert "too many requests (429)" in status_problem(429)
    assert "busy" in status_problem(504) and "busy" in status_problem(502)
    assert "refused the query" in status_problem(400) and "(500)" in status_problem(500)


def test_names_of_the_layers_made():
    tags = read_tags([{"key": "amenity", "value": "hospital"}, {"key": "building"}])
    assert default_name(tags) == "OSM amenity=hospital, building"
    assert default_name(read_tags([{"key": f"k{index}"} for index in range(5)])) == "OSM k0, k1, k2..."
    assert layer_title("Hôpitaux", "points", several=True) == "Hôpitaux (points)"
    assert layer_title("Hôpitaux", "points", several=False) == "Hôpitaux"
    assert summary({"points": 3, "lines": 0, "polygons": 29}) == {"points": 3, "polygons": 29}
    assert GEOMETRIES[0] == "as_mapped"
