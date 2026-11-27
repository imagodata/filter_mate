# -*- coding: utf-8 -*-
"""The requests of the welcome of AGENT: drawn at random over the sources and the state of the project, never the same
set twice in a row, and never one that is not true of the project now."""
import itertools
import json
import random
import re
from pathlib import Path

import pytest

from core.agent import example_prompts as ex
from core.agent.tool_catalog import CHAT_ONLY

PANEL = Path(__file__).resolve().parents[3] / "ui" / "widgets" / "agent_panel.py"
TOOLS = {tool["name"] for tool in json.loads(
    (Path(__file__).resolve().parents[3] / "core" / "agent" / "tool_catalog.json").read_text(encoding="utf-8"))["tools"]}
TOOLS |= {tool.name for tool in CHAT_ONLY}  # the welcome is the chat's: its own tools (create_widget) carry requests too
NEEDS = {"layers", "no_layers", "data", "no_data", "no_basemap", "several", "vector", "many_vectors", "raster",
         "point_cloud", "polygons", "elevation", "active_vector", "active_raster", "active_point_cloud",
         "active_elevation", "active_local", "selection", "local_selection", "filter", "remote",
         "numeric_field", "text_field", "style_field"}


def _by_key():
    return {example.key: example for example in ex.CATALOG}


def test_keys_are_unique_and_every_one_has_its_words_in_the_panel():
    assert len(set(ex.KEYS)) == len(ex.KEYS)
    words = dict(re.findall(r'^\s+"(\w+)": _tr\("([^"]+)"\),$', PANEL.read_text(encoding="utf-8"), re.MULTILINE))
    assert set(words) == set(ex.KEYS)
    assert all(len(text) <= 70 for text in words.values()), "the recipe stays short; the button elides its context"


@pytest.mark.parametrize("locale", ['fr_FR', 'fr_CA', 'en_GB', 'pt_BR', 'de', 'ja_Jpan_JP', 'zh_Hans_CN', '', None])
def test_a_ui_locale_never_restricts_discovery_destinations(locale):
    assert ex.eligible(locale) == ex.eligible('en_US')


def test_enrichment_uses_project_geography_instead_of_ui_language():
    from core.agent.example_places import view_place
    kyoto = facts(vectors=1, active="vector", focus=view_place((135.76, 35.00, 135.78, 35.02)))
    assert "jp_shelters" in {example.key for example in ex.eligible("fr_FR", kyoto)}
    assert "fr_flood" not in {example.key for example in ex.eligible("fr_FR", kyoto)}
    assert not any(example.regions for example in ex.eligible("fr_FR", facts(vectors=1)))
    assert ex.eligible("fr_FR", kyoto) == ex.eligible("en_US", kyoto)
    assert "fr_flood" in {example.key for example in ex.eligible("en_US", facts())}


def facts(**given):
    """Facts the way the controller reads them, from the counts alone."""
    values = dict(known=True, layers=0, tiles=0, vectors=0, rasters=0, point_clouds=0, active="", selected=0,
                  filtered=0, remote=0, elevations=0, polygons=0, active_elevation=False, active_local=True)
    values.update(given)
    if values["active"] == "vector":
        values.setdefault("active_fields", (("usage", "text"), ("height", "numeric")))
    values.setdefault("selected_local", values["selected"])
    if values["active"] == "raster" and "active_elevation" not in given and "elevations" not in given:
        values["elevations"], values["active_elevation"] = values["rasters"], True  # a raster is a terrain model here
    values["layers"] = max(values["layers"], values["tiles"] + values["vectors"] + values["rasters"]
                           + values["point_clouds"])
    return ex.Facts(**values)


def _states():
    """Every combination of what the requests care about, as a project can be."""
    for vectors, rasters, clouds, tiles, active, selected, filtered, remote in itertools.product(
            (0, 1, 2), (0, 1), (0, 1), (0, 1), ("", "vector", "raster", "point_cloud", "other"), (0, 3), (0, 1), (0, 1)):
        if (active == "vector" and not vectors) or (active == "raster" and not rasters) \
                or (active == "point_cloud" and not clouds) or (selected and not vectors) or (remote and not vectors) \
                or (filtered and not (vectors or clouds)):
            continue
        yield facts(vectors=vectors, rasters=rasters, point_clouds=clouds, tiles=tiles, active=active,
                    selected=selected, filtered=filtered, remote=remote)


def test_every_key_has_a_known_need_and_a_tool_that_carries_it_out():
    for example in ex.CATALOG:
        assert example.tools, example.key
        assert set(example.tools) <= TOOLS, (example.key, set(example.tools) - TOOLS)
        assert set(example.needs) <= NEEDS, example.key
        assert example.group in (ex.PROJECT, ex.DATA)
        # The requests about the project suppose a layer; those that bring data in can come on an empty map.
        if example.group == ex.PROJECT:
            assert example.needs, example.key
            assert "no_layers" not in example.needs


@pytest.mark.parametrize("locale", ["fr_FR", "en_US", "en_GB", "ja_JP", "pt_BR", "zz"])
def test_no_layer_offers_only_ways_to_bring_data_in(locale):
    catalog = _by_key()
    empty = facts()
    for seed in range(200):
        keys = ex.pick(locale, facts=empty, rng=random.Random(seed))
        assert len(keys) == ex.SHOWN == len(set(keys))
        picked = [catalog[key] for key in keys]
        assert all(example.group == ex.DATA for example in picked)
        assert not any({"layers", "data", "vector", "raster", "selection", "filter"} & set(example.needs)
                       for example in picked)
        kinds = [example.kind for example in picked]
        assert len(set(kinds)) == len(kinds)


def test_a_basemap_is_offered_on_an_empty_map_and_a_dark_one_under_layers():
    seen_empty = {key for seed in range(300) for key in ex.pick("en_US", facts=facts(), rng=random.Random(seed))}
    assert "add_basemap" in seen_empty and "dark_basemap" not in seen_empty
    drawn = {key for seed in range(300)
             for key in ex.pick("en_US", facts=facts(vectors=1, active="vector"), rng=random.Random(seed))}
    assert "dark_basemap" in drawn and "add_basemap" not in drawn


def test_a_project_with_only_a_basemap_is_still_a_project_without_data():
    catalog = _by_key()
    for seed in range(100):
        keys = ex.pick("en_US", facts=facts(tiles=1), rng=random.Random(seed))
        assert all(catalog[key].group == ex.DATA for key in keys)


@pytest.mark.parametrize("locale", ["fr_FR", "en_US", "en_GB", "ja_JP", "pt_BR", "zz"])
def test_with_layers_three_project_requests_and_one_enrichment(locale):
    catalog = _by_key()
    for state in (facts(vectors=1, active="vector"), facts(vectors=2, rasters=1, active="raster"),
                  facts(point_clouds=1, active="point_cloud"), facts(vectors=1, selected=2, active="vector")):
        counts = set()
        for seed in range(200):
            keys = ex.pick(locale, facts=state, rng=random.Random(seed))
            assert len(keys) == ex.SHOWN == len(set(keys))
            picked = [catalog[key] for key in keys]
            counts.add([example.group for example in picked].count(ex.PROJECT))
            kinds = [example.kind for example in picked]
            assert len(set(kinds)) == len(kinds)
            assert not any(example.regions for example in picked)  # unknown project country
        assert counts == {3}


def test_every_request_is_true_of_the_state_whatever_the_state_and_the_seed():
    catalog = _by_key()
    for state in _states():
        tokens = state.tokens()
        for seed in range(6):
            keys = ex.pick("fr_FR", facts=state, rng=random.Random(seed))
            assert len(keys) == ex.SHOWN == len(set(keys)), (state, keys)
            for key in keys:
                assert set(catalog[key].needs) <= tokens, (key, state)
            kinds = [catalog[key].kind for key in keys]
            assert len(set(kinds)) == len(kinds), (state, keys)


def test_unknown_facts_offer_only_requests_that_suppose_nothing():
    catalog = _by_key()
    for seed in range(100):
        for unknown in (ex.Facts.unknown(), ex.Facts(), None):
            keys = ex.pick("en_US", facts=unknown, rng=random.Random(seed))
            assert len(keys) == ex.SHOWN and not any(catalog[key].needs for key in keys)
        assert ex.pick("en_US", rng=random.Random(seed)) == ex.pick("en_US", facts=None, rng=random.Random(seed))
    assert ex.Facts.unknown().tokens() == frozenset()
    assert ex.Facts(layers=3, vectors=3, selected=2).tokens() == frozenset()  # not known: not trusted


def test_a_raster_active_gives_raster_requests_and_none_about_a_vector_layer_alone():
    catalog = _by_key()
    state = facts(rasters=1, active="raster")
    for seed in range(200):
        keys = ex.pick("en_US", facts=state, rng=random.Random(seed))
        needs = [set(catalog[key].needs) for key in keys]
        assert any({"active_raster", "active_elevation"} & need for need in needs), keys
        assert not any({"vector", "active_vector", "many_vectors", "selection", "remote"} & need for need in needs)


def test_a_raster_next_to_vectors_still_has_a_raster_request_first():
    state = facts(rasters=1, vectors=2, active="raster")
    catalog = _by_key()
    for seed in range(200):
        needs = [set(catalog[key].needs) for key in ex.pick("en_US", facts=state, rng=random.Random(seed))]
        assert any({"active_raster", "active_elevation", "raster", "elevation"} & need for need in needs)
        assert not any("active_vector" in need for need in needs)


def test_a_selection_brings_selection_requests():
    catalog = _by_key()
    state = facts(vectors=2, active="vector", selected=4)
    shown = set()
    for seed in range(200):
        keys = ex.pick("en_US", facts=state, rng=random.Random(seed))
        assert any({"selection", "local_selection"} & set(catalog[key].needs) and catalog[key].group == ex.PROJECT
                   for key in keys), keys
        shown.update(keys)
    assert {"zoom_selection", "sel_radius", "sel_other_layers", "people_selected"} <= shown
    no_selection = {key for seed in range(200)
                    for key in ex.pick("en_US", facts=facts(vectors=2, active="vector"), rng=random.Random(seed))}
    assert not no_selection & {"zoom_selection", "sel_radius", "sel_other_layers", "people_selected"}


def test_a_filter_brings_filter_requests():
    catalog = _by_key()
    state = facts(vectors=1, active="vector", filtered=1)
    shown = set()
    for seed in range(200):
        keys = ex.pick("en_US", facts=state, rng=random.Random(seed))
        assert any("filter" in catalog[key].needs for key in keys), keys
        shown.update(keys)
    assert {"filter_state", "clear_all", "export_gpkg", "zoom_filtered"} <= shown
    plain = {key for seed in range(200)
             for key in ex.pick("en_US", facts=facts(vectors=1, active="vector"), rng=random.Random(seed))}
    assert not plain & {"filter_state", "clear_all", "export_gpkg", "zoom_filtered"}


def test_a_point_cloud_gets_its_own_requests():
    catalog = _by_key()
    for seed in range(100):
        keys = ex.pick("en_US", facts=facts(point_clouds=1, active="point_cloud"), rng=random.Random(seed))
        assert any({"point_cloud", "active_point_cloud"} & set(catalog[key].needs) for key in keys)


def test_a_server_layer_brings_its_request_and_a_file_does_not():
    state = facts(vectors=1, active="vector", remote=1)
    assert any("export_remote" in ex.pick("en_US", facts=state, rng=random.Random(seed)) for seed in range(300))
    assert not any("export_remote" in ex.pick("en_US", facts=facts(vectors=1, active="vector"),
                                              rng=random.Random(seed)) for seed in range(300))


def test_the_signature_follows_what_the_requests_depend_on_and_nothing_finer():
    assert facts(vectors=1, selected=1, active="vector").signature() == facts(
        vectors=1, selected=40, active="vector").signature()
    assert facts(vectors=3).signature() == facts(vectors=7).signature()
    base = facts(vectors=1, active="vector")
    for other in (facts(), facts(vectors=1), facts(vectors=1, active="vector", selected=1),
                  facts(vectors=1, active="vector", filtered=1), facts(vectors=2, active="vector"),
                  facts(vectors=1, rasters=1, active="vector"), facts(vectors=1, active="vector", remote=1),
                  facts(tiles=1), ex.Facts.unknown()):
        assert other.signature() != base.signature()
    assert facts(vectors=1, tiles=1).tokens() >= {"layers", "data", "vector"}
    assert "data" not in facts(tiles=2).tokens() and "layers" in facts(tiles=2).tokens()


def test_discoveries_are_worldwide_in_every_ui_language():
    for seed in range(30):
        assert ex.pick('fr_FR', facts=facts(), rng=random.Random(seed)) == ex.pick(
            'ja_JP', facts=facts(), rng=random.Random(seed))
        picked = [_by_key()[key] for key in ex.pick('fr_FR', facts=facts(), rng=random.Random(seed))]
        assert sum(bool(example.regions) for example in picked) <= 1


@pytest.mark.parametrize("locale", ["fr_FR", "en_US", "en_GB"])
def test_the_next_set_shares_nothing_with_the_one_before_but_the_only_request_of_a_country(locale):
    catalog = _by_key()
    alone = sum(1 for example in ex.eligible(locale) if example.regions) == 1
    rng = random.Random(7)
    previous = ex.pick(locale, rng=rng)
    for _ in range(300):
        keys = ex.pick(locale, previous, rng=rng)
        assert all(alone and catalog[key].regions for key in set(keys) & set(previous))
        previous = keys


def test_sets_vary():
    rng = random.Random(3)
    assert len({ex.pick("en_US", rng=rng) for _ in range(50)}) > 30
    assert len({key for _ in range(200) for key in ex.pick("en_US", rng=rng)}) == len(ex.eligible("en_US"))


def test_unknown_previous_keys_are_ignored():
    keys = ex.pick("en", ["", "gone", "layers"], rng=random.Random(1))
    assert "layers" not in keys and len(keys) == ex.SHOWN


@pytest.mark.parametrize("state", [facts(), facts(vectors=1, active="vector"), facts(rasters=1, active="raster"),
                                   facts(vectors=2, selected=2, active="vector", filtered=1)])
def test_the_next_set_keeps_clear_of_the_one_before_in_every_state(state):
    rng = random.Random(11)
    previous = ex.pick("en_US", facts=state, rng=rng)
    for _ in range(100):
        keys = ex.pick("en_US", previous, facts=state, rng=rng)
        assert not set(keys) & set(previous)
        assert len(keys) == ex.SHOWN
        previous = keys


def test_field_recipes_require_the_actual_schema():
    unknown = _drawn(facts(vectors=1, active='vector', active_fields=()))
    assert not unknown & {'numeric_summary', 'slider_histogram', 'color_by', 'labels', 'stats_active'}
    numeric = _drawn(facts(vectors=1, active='vector', active_fields=(('area_m2', 'numeric'),)))
    assert {'numeric_summary', 'slider_histogram', 'color_by'} <= numeric
    assert not numeric & {'labels', 'stats_active'}
    text = _drawn(facts(vectors=1, active='vector', active_fields=(('usage', 'text'),)))
    assert {'color_by', 'labels', 'stats_active'} <= text
    assert not text & {'numeric_summary', 'slider_histogram'}
    assert not {'tall_buildings', 'roads_inside'} & set(ex.KEYS)


@pytest.mark.parametrize("active, state", [("vector", dict(vectors=2, rasters=1)), ("raster", dict(vectors=2, rasters=1)),
                                           ("point_cloud", dict(vectors=1, point_clouds=1))])
def test_the_active_layer_comes_first_when_nothing_else_moved(active, state):
    catalog = _by_key()
    for seed in range(200):
        keys = ex.pick("en_US", facts=facts(active=active, **state), rng=random.Random(seed))
        assert any(f"active_{active}" in catalog[key].needs or (active == "raster" and "active_elevation" in catalog[key].needs)
                   for key in keys), (active, keys)


TERRAIN = {"slope", "hillshade", "contours", "slope_filter"}


def _drawn(state, seeds=300, locale="en_US"):
    return {key for seed in range(seeds) for key in ex.pick(locale, facts=state, rng=random.Random(seed))}


def test_terrain_requests_need_a_raster_that_can_be_a_terrain_model():
    """2026-11-22: an orthophoto or a scanned map was offered "Map the slope of the active raster"."""
    picture = facts(rasters=1, vectors=1, active="raster", elevations=0, active_elevation=False)
    assert not _drawn(picture) & TERRAIN
    assert {"raster_ramp", "raster_stats"} <= _drawn(picture)  # style and statistics fit any raster
    dem = facts(rasters=1, vectors=1, active="raster", elevations=1, active_elevation=True)
    assert {"slope", "hillshade", "contours", "slope_filter"} <= _drawn(dem)
    # A terrain model is in the project, another raster is active: no request on the active one, a filter by slope.
    other = facts(rasters=2, vectors=1, active="raster", elevations=1, active_elevation=False)
    assert not _drawn(other) & {"slope", "hillshade", "contours"} and "slope_filter" in _drawn(other)


def test_a_service_layer_is_not_offered_what_its_tools_refuse():
    """layer_statistics refuses a web service and sample_features reads a WFS without its selection."""
    wfs = facts(vectors=1, active="vector", selected=3, selected_local=0, active_local=False)
    assert not _drawn(wfs) & {"stats_active", "sel_stats", "sel_attributes"}
    assert {"zoom_selection", "sel_radius", "fields", "color_by"} <= _drawn(wfs)  # what does work on a service
    mixed = facts(vectors=2, active="vector", selected=3, selected_local=1)
    assert {"sel_stats", "sel_attributes"} <= _drawn(mixed) and "stats_active" in _drawn(mixed)


def test_polygons_are_for_the_statistics_of_a_raster_by_polygon():
    points = facts(rasters=1, vectors=1, active="raster", polygons=0)
    assert "zonal" not in _drawn(points)
    assert "zonal" in _drawn(facts(rasters=1, vectors=1, active="raster", polygons=1))


def test_a_basemap_alone_is_not_data_and_is_not_missing_either():
    only_basemap = facts(tiles=1)
    drawn = _drawn(only_basemap)
    assert "add_basemap" not in drawn and "dark_basemap" not in drawn
    mesh = facts(layers=1)  # a mesh: a layer, no data, no basemap
    assert "add_basemap" in _drawn(mesh) and not any(
        {c.key for c in ex.CATALOG if c.group == ex.PROJECT} & {key for key in _drawn(mesh)})
    assert "add_basemap" in _drawn(facts()) and "dark_basemap" not in _drawn(facts())
    assert "dark_basemap" in _drawn(facts(vectors=1, active="vector"))


def _transitions():
    states = list(_states())
    rng = random.Random(4)
    for _ in range(400):
        yield rng.choice(states), rng.choice(states)


def test_adjust_never_shows_a_request_that_is_false_and_fills_the_places():
    catalog = _by_key()
    for index, (before, now) in enumerate(_transitions()):
        rng = random.Random(index)
        current = ex.pick("fr_FR", facts=before, rng=rng)
        keys = ex.adjust("fr_FR", current, current, before, now, rng=rng)
        assert len(keys) == ex.SHOWN == len(set(keys)), (before, now, current, keys)
        assert all(set(catalog[key].needs) <= now.tokens() for key in keys), (now, keys)
        assert sum(catalog[key].group == ex.PROJECT for key in keys) <= ex.MAX_PROJECT
        # A request still true stays where it was, but for the one that makes room for what the change brings.
        moved = [place for place, key in enumerate(current)
                 if set(catalog[key].needs) <= now.tokens() and keys[place] != key]
        if ('data' in before.tokens()) == ('data' in now.tokens()):
            assert len(moved) <= 1, (before, now, current, keys)


def test_adjust_without_a_change_changes_nothing():
    for state in list(_states())[:80]:
        current = ex.pick("en_US", facts=state, rng=random.Random(2))
        assert ex.adjust("en_US", current, current, state, state, rng=random.Random(3)) == current


def test_a_selection_changes_one_request_and_keeps_the_others_in_place():
    catalog = _by_key()
    before, now = facts(vectors=2, active="vector"), facts(vectors=2, active="vector", selected=3)
    for seed in range(200):
        current = ex.pick("en_US", facts=before, rng=random.Random(seed))
        keys = ex.adjust("en_US", current, current, before, now, rng=random.Random(seed))
        assert any(set(catalog[key].needs) & {"selection", "local_selection"} for key in keys), (current, keys)
        assert sum(a != b for a, b in zip(current, keys)) <= 2, (current, keys)  # one in, and at most one more out
        assert sum(1 for key in keys if key in current) >= 2


def test_a_selection_ended_removes_what_depended_on_it_and_nothing_else():
    catalog = _by_key()
    before, now = facts(vectors=2, active="vector", selected=3), facts(vectors=2, active="vector")
    for seed in range(200):
        current = ex.pick("en_US", facts=before, rng=random.Random(seed))
        keys = ex.adjust("en_US", current, current, before, now, rng=random.Random(seed))
        assert not any(set(catalog[key].needs) & {"selection", "local_selection"} for key in keys)
        gone = [place for place, key in enumerate(current) if set(catalog[key].needs) & {"selection", "local_selection"}]
        assert all(keys[place] == key for place, key in enumerate(current) if place not in gone), (current, keys)


def test_loading_project_data_prioritizes_work_on_that_project():
    catalog = _by_key()
    unknown, now = ex.Facts.unknown(), facts(vectors=1, active="vector")
    for seed in range(100):
        current = ex.pick("en_US", facts=unknown, rng=random.Random(seed))
        keys = ex.adjust("en_US", current, current, unknown, now, rng=random.Random(seed))
        assert sum(catalog[key].group == ex.PROJECT for key in keys) == 3


def test_a_new_active_kind_gets_a_place_even_when_three_generic_project_recipes_stay_valid():
    before = facts(vectors=2, rasters=1)
    now = facts(vectors=2, rasters=1, active='raster')
    current = ('layers', 'layout', 'cross_near', 'osm_trees')
    for seed in range(20):
        keys = ex.adjust('fr_FR', current, (), before, now, rng=random.Random(seed))
        assert any({'active_raster', 'active_elevation'} & set(_by_key()[key].needs) for key in keys)
        assert sum(a != b for a, b in zip(current, keys)) == 1
