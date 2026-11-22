# -*- coding: utf-8 -*-
"""The requests offered on the welcome of AGENT: a catalog over the sources of the agent, drawn at random.

Plain Python, no QGIS. Each new conversation shows a few requests drawn from the catalog, among those that are true of
the project now (``Facts``): with no layer open, only requests that bring data in (elevation, OpenStreetMap,
population, basemaps, open data...); with layers, one or two about them, chosen from the kind of the active layer, the
selection and the filters, and the others each from another kind of source. None of the set shown before when the
catalog allows it. A request about the data of one country (IGN, Géorisques, GovData...) is drawn only when the locale
of QGIS points to that country. The words are in ui/widgets/agent_panel.py (``example_text``), translated; here, only
their keys, what each supposes (``needs``) and the tools of the agent that carry it out (``tools``).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import FrozenSet, Iterable, List, Optional, Sequence, Tuple

PROJECT = "project"  # about the layers already in the project
DATA = "data"  # brings data in from a source of the agent

SHOWN = 4  # requests on the welcome


@dataclass(frozen=True)
class Facts:
    """What is true of QGIS and the project now, as far as the requests care: counts and flags, never a feature count.

    ``known`` False is a reading that failed or was never made: only the requests that suppose nothing are offered.
    """

    known: bool = False
    layers: int = 0  # every layer of the project
    tiles: int = 0  # of them, the web map images (XYZ, WMS...): a basemap is not data to work on
    vectors: int = 0
    rasters: int = 0  # not the web map images
    point_clouds: int = 0
    active: str = ""  # kind of the active layer: "vector", "raster", "point_cloud", "other"; "" when there is none
    selected: int = 0  # features selected, all vector layers together
    filtered: int = 0  # layers with a filter (a subset string) set
    remote: int = 0  # vector layers read from a server or a database

    @classmethod
    def unknown(cls) -> "Facts":
        return cls()

    def tokens(self) -> FrozenSet[str]:
        """What these facts make true, in the words of ``Example.needs``; nothing when they are unknown."""
        if not self.known:
            return frozenset()
        found = {"layers" if self.layers else "no_layers"}
        flags = (("data", self.layers > self.tiles), ("several", self.layers - self.tiles > 1),
                 ("vector", self.vectors > 0), ("many_vectors", self.vectors > 1), ("raster", self.rasters > 0),
                 ("point_cloud", self.point_clouds > 0), ("selection", self.selected > 0),
                 ("filter", self.filtered > 0), ("remote", self.remote > 0),
                 ("active_vector", self.active == "vector"), ("active_raster", self.active == "raster"),
                 ("active_point_cloud", self.active == "point_cloud"))
        found.update(name for name, true in flags if true)
        return frozenset(found)

    def signature(self) -> Tuple[str, ...]:
        """What the set shown depends on: it is drawn again only when this changes, not at each feature selected."""
        return ("known",) + tuple(sorted(self.tokens())) if self.known else ("unknown",)


@dataclass(frozen=True)
class Example:
    """One request: its key, what it is about (``PROJECT`` or ``DATA``), its kind, what it supposes, the countries it
    needs, and the tools of the agent that carry it out (names of core/agent/tool_catalog.json).

    ``needs`` are words of ``Facts.tokens``: layers, no_layers, data (a layer that is not a web map image), several
    (two such layers), vector, many_vectors, raster, point_cloud, active_vector, active_raster, active_point_cloud,
    selection, filter, remote."""

    key: str
    group: str
    kind: str
    regions: Tuple[str, ...] = ()  # empty: anywhere
    needs: Tuple[str, ...] = ()
    tools: Tuple[str, ...] = ()


def _p(key: str, kind: str, needs: Tuple[str, ...], *tools: str) -> Example:
    return Example(key, PROJECT, kind, needs=needs, tools=tools)


def _d(key: str, kind: str, regions: Tuple[str, ...] = (), needs: Tuple[str, ...] = (), *tools: str) -> Example:
    return Example(key, DATA, kind, regions, needs, tools)


CATALOG: Tuple[Example, ...] = (
    _p("layers", "layers", ("data",), "list_layers"),
    _p("fields", "layers", ("active_vector",), "describe_layer"),
    _p("lidar_describe", "layers", ("active_point_cloud",), "describe_layer"),
    _p("tall_buildings", "filter", ("vector",), "apply_filter"),
    _p("visible", "filter", ("vector",), "map_context", "geometry_filter"),
    _p("roads_inside", "cross", ("selection",), "cross_filter"),
    _p("sel_other_layers", "cross", ("selection", "several"), "cross_filter"),
    _p("sel_radius", "near", ("selection",), "cross_filter"),
    _p("cross_near", "near", ("many_vectors",), "cross_filter"),
    _p("zoom_selection", "zoom", ("selection",), "zoom_to"),
    _p("zoom_filtered", "zoom", ("filter",), "filter_state", "zoom_to"),
    _p("sel_attributes", "attributes", ("selection",), "sample_features"),
    _p("sel_stats", "stats", ("selection",), "layer_statistics"),
    _p("stats_active", "stats", ("active_vector",), "layer_statistics"),
    _p("filter_state", "filters", ("filter",), "filter_state", "layer_statistics"),
    _p("clear_all", "unfilter", ("filter",), "clear_filters"),
    _p("color_by", "style", ("active_vector",), "set_layer_style"),
    _p("raster_ramp", "style", ("active_raster",), "set_layer_style"),
    _p("labels", "labels", ("active_vector",), "set_labels"),
    _p("export_gpkg", "export", ("filter",), "export_layers"),
    _p("export_active", "export", ("active_vector",), "export_layers"),
    _p("export_remote", "export", ("remote",), "export_layers"),
    _p("lidar_export", "export", ("point_cloud",), "export_layers"),
    _p("slope", "terrain", ("active_raster",), "run_algorithm"),
    _p("hillshade", "shade", ("active_raster",), "duplicate_layer", "set_layer_style"),
    _p("contours", "contours", ("active_raster",), "contour_lines"),
    _p("raster_stats", "raster_stats", ("active_raster",), "run_algorithm"),
    _p("slope_filter", "terrain_filter", ("raster", "vector"), "cross_filter"),
    _p("zonal", "zonal", ("raster", "vector"), "run_algorithm"),
    _p("lidar_ground", "cloud_filter", ("point_cloud",), "point_cloud_filter"),
    _p("lidar_inside", "cloud_cross", ("point_cloud", "selection"), "cross_filter"),
    _p("join", "join", ("many_vectors",), "join_layers"),
    _p("buffer_zone", "buffer", ("active_vector",), "run_algorithm"),
    _p("layout", "layout", ("data",), "create_layout"),
    _d("relief", "elevation", (), (), "find_place", "add_elevation", "set_layer_style", "contour_lines"),
    _d("elevation_view", "elevation", (), (), "add_elevation"),
    _d("people_selected", "population", (), ("selection",), "add_population", "run_algorithm"),
    _d("population_grid", "population", (), (), "add_population"),
    _d("osm_cafes", "osm", (), (), "add_osm_features"),
    _d("osm_cycle", "osm", (), (), "add_osm_features"),
    _d("osm_trees", "osm", (), (), "add_osm_features"),
    _d("dark_basemap", "basemap", (), ("layers",), "add_basemap"),
    _d("add_basemap", "basemap", (), ("no_layers",), "add_basemap"),
    _d("sentinel", "satellite", (), (), "search_imagery", "add_layer"),
    _d("zoom_park", "places", (), (), "find_place", "zoom_to"),
    _d("ods_toilets", "open_data", (), (), "search_open_data", "add_layer"),
    _d("eurostat", "statistics", (), (), "search_open_data", "add_layer"),
    _d("fr_communes", "open_data", ("fr",), (), "search_open_data", "add_layer"),
    _d("fr_bikes", "open_data", ("fr",), (), "search_open_data", "add_layer"),
    _d("fr_buildings", "reference", ("fr",), (), "search_open_data", "add_service_layer"),
    _d("fr_photos_1950", "imagery", ("fr",), (), "search_open_data", "add_service_layer"),
    _d("fr_flood", "risks", ("fr",), (), "search_open_data", "add_service_layer"),
    _d("fr_clay", "risks", ("fr",), (), "search_open_data", "add_service_layer"),
    _d("fr_town_hall", "places", ("fr",), (), "find_place", "zoom_to"),
    _d("gb_flood", "open_data", ("gb",), (), "search_open_data", "add_layer"),
    _d("ca_parks", "open_data", ("ca",), (), "search_open_data", "add_layer"),
    _d("au_bushfire", "open_data", ("au",), (), "search_open_data", "add_layer"),
    _d("de_charging", "open_data", ("de",), (), "search_open_data", "add_layer"),
    _d("it_schools", "open_data", ("it",), (), "search_open_data", "add_layer"),
    _d("nl_bike_parking", "open_data", ("nl",), (), "search_open_data", "add_layer"),
    _d("jp_shelters", "open_data", ("jp",), (), "search_open_data", "add_layer"),
    _d("br_municipalities", "reference", ("br",), (), "search_open_data", "add_service_layer"),
    _d("pl_municipalities", "reference", ("pl",), (), "search_open_data", "add_service_layer"),
)
KEYS: Tuple[str, ...] = tuple(example.key for example in CATALOG)
_COUNTRIES = frozenset(region for example in CATALOG for region in example.regions)
# A language that is spoken in one of these countries mostly: "fr" alone is France, "fr_CA" is Canada.
_LANGUAGE_COUNTRY = {"fr": "fr", "de": "de", "it": "it", "nl": "nl", "ja": "jp", "pl": "pl"}


def regions(locale: str) -> FrozenSet[str]:
    """The countries a locale of QGIS points to: ``fr_FR`` and ``fr`` give France, ``en_GB`` the United Kingdom,
    ``pt_BR`` Brazil, ``fr_CA`` Canada only, ``en`` and ``en_US`` none of the catalog."""
    text = str(locale or "").replace("-", "_").split(".")[0].split("@")[0].strip()
    language, *rest = text.split("_")
    # The country is the part of two letters after the language: a script comes between them (``zh_Hans_CN``).
    countries = [part.lower() for part in rest if len(part) == 2 and part.isalpha()]
    if countries:
        country = "gb" if countries[-1] == "uk" else countries[-1]
        return frozenset({country} & _COUNTRIES)
    if rest:  # a region the catalog cannot read (``es_419``): no country
        return frozenset()
    found = _LANGUAGE_COUNTRY.get(language.lower())
    return frozenset({found}) if found else frozenset()


def eligible(locale: str, facts: Optional[Facts] = None) -> Tuple[Example, ...]:
    """The requests that can be offered under this locale and in this state; with no ``facts`` (unknown), only those
    that suppose nothing."""
    here = regions(locale)
    tokens = (facts or Facts.unknown()).tokens()
    return tuple(example for example in CATALOG
                 if (not example.regions or set(example.regions) & here) and set(example.needs) <= tokens)


# What a request supposes beyond a layer being there: the selection or a filter (the state moved), then the kind of
# the active layer (what the user looks at); the others (a layer, a vector layer) are for any project.
_MOVED = frozenset({"selection", "filter"})
_ACTIVE = frozenset({"active_vector", "active_raster", "active_point_cloud"})  # all true or false together with the kind
_PRESENCE = frozenset({"layers", "data", "several", "vector", "many_vectors"})


def pick(locale: str, previous: Iterable[str] = (), count: int = SHOWN, rng: Optional[random.Random] = None,
         facts: Optional[Facts] = None) -> Tuple[str, ...]:
    """The keys of ``count`` requests for a new conversation, in a random order, all true of ``facts``.

    With no layer, only requests that bring data in. With layers, one or two about the project (two when a selection
    or a filter is there): first one that follows the selection or the filters, else the active layer, else the kinds
    of layers there are; the others bring data in. Each is of another kind; none was in ``previous`` (the set shown before) when enough are left
    without them. A request about the data of the country of the locale always takes one of the places, even one
    shown in the set before when it is the only one of its country."""
    rng = rng or random.Random()  # nosec B311 - which requests are shown, nothing secret
    facts = facts or Facts.unknown()
    seen = set(previous)
    offered = eligible(locale, facts)
    fresh = [example for example in offered if example.key not in seen]
    pool = fresh if len(fresh) >= count else list(offered)
    chosen: List[Example] = []

    def take(candidates: Sequence[Example], strict: bool = False) -> None:
        kinds = {example.kind for example in chosen}
        left = [example for example in candidates if example not in chosen and example.kind not in kinds]
        if not left and not strict:
            left = [example for example in candidates if example not in chosen]
        if left and len(chosen) < count:
            chosen.append(rng.choice(left))

    project = [example for example in pool if example.group == PROJECT]
    if project:
        moved = [example for example in project if _MOVED & set(example.needs)]
        about_active = [example for example in project if _ACTIVE & set(example.needs)]
        specific = [example for example in project if set(example.needs) - _PRESENCE - _MOVED]
        take(moved or about_active or specific or project)
        if moved or rng.random() < 0.5:
            take(specific or project, strict=True)
    # The country of the locale always has its place, even when its only request was in the set before.
    take([example for example in pool if example.regions] or [example for example in offered if example.regions])
    while len(chosen) < count:
        before = len(chosen)
        take([example for example in pool if example.group == DATA] or pool)
        if len(chosen) == before:
            take(pool)
        if len(chosen) == before:
            break
    rng.shuffle(chosen)
    return tuple(example.key for example in chosen)
