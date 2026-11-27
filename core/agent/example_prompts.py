# -*- coding: utf-8 -*-
"""Welcome recipes compatible with the project, composed with real layer/field names and geographical anchors.

Plain Python, no QGIS or network. Language controls wording, never destination. With data, prefer three project
requests and one enrichment; without data, combine discovery recipes with the offline gazetteer. The UI translates
the recipes and keeps each rendered request stable until its context changes or the user asks for other ideas.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import FrozenSet, Iterable, List, Optional, Sequence, Tuple

from .example_places import Place

PROJECT = "project"  # about the layers already in the project
DATA = "data"  # brings data in from a source of the agent

SHOWN = 4  # requests on the welcome


@dataclass(frozen=True)
class Facts:
    """What the requests need of QGIS: kinds, names, cached schema and view, never feature counts or attribute values.

    ``known`` False is a reading that failed or was never made: only the requests that suppose nothing are offered.
    """

    known: bool = False
    layers: int = 0  # every valid layer of the project
    tiles: int = 0  # of them, the basemaps: web map images (XYZ, WMS...) and vector tiles, not data to work on
    vectors: int = 0
    rasters: int = 0  # of values or colours a filter can read: not the web map images
    point_clouds: int = 0
    active: str = ""  # kind of the active layer: "vector", "raster", "point_cloud", "other"; "" when there is none
    selected: int = 0  # features selected, all vector layers together
    filtered: int = 0  # layers with a filter: a subset string, or a source FilterMate swapped for a clipped copy
    remote: int = 0  # vector layers read from a server or a database
    # Added for the requests a tool refuses or that only make sense for some layers (appended: positions kept).
    elevations: int = 0  # rasters that can be a terrain model: one band of numbers, not a picture
    polygons: int = 0  # vector layers of polygons
    active_elevation: bool = False  # the active layer is one of them
    active_local: bool = True  # the active layer is not read from a web service (WFS, OGC API, ArcGIS)
    selected_local: int = 0  # features selected on layers that are not web services: the tools read those
    active_id: str = ""
    active_name: str = ""
    active_fields: Tuple[Tuple[str, str], ...] = ()  # (name, numeric/text), schema only, no attribute values
    vector_names: Tuple[str, ...] = ()
    raster_name: str = ""
    elevation_name: str = ""
    cloud_name: str = ""
    selected_names: Tuple[str, ...] = ()
    focus: Optional[Place] = None  # meaningful current map view, never the default view of an empty project

    def field(self, kind: str) -> str:
        return next((name for name, field_kind in self.active_fields if field_kind == kind), "")

    @classmethod
    def unknown(cls) -> "Facts":
        return cls()

    def tokens(self) -> FrozenSet[str]:
        """What these facts make true, in the words of ``Example.needs``; nothing when they are unknown."""
        if not self.known:
            return frozenset()
        found = {"layers" if self.layers else "no_layers"}
        data = self.vectors + self.rasters + self.point_clouds
        flags = (("data", data > 0), ("no_data", data == 0), ("no_basemap", self.tiles == 0), ("several", data > 1),
                 ("vector", self.vectors > 0), ("many_vectors", self.vectors > 1), ("raster", self.rasters > 0),
                 ("point_cloud", self.point_clouds > 0), ("selection", self.selected > 0),
                 ("local_selection", self.selected_local > 0), ("filter", self.filtered > 0),
                 ("remote", self.remote > 0), ("elevation", self.elevations > 0), ("polygons", self.polygons > 0),
                 ("active_vector", self.active == "vector"), ("active_raster", self.active == "raster"),
                 ("active_point_cloud", self.active == "point_cloud"),
                 ("active_elevation", self.active == "raster" and self.active_elevation),
                 ("active_local", bool(self.active) and self.active_local),
                 ("numeric_field", bool(self.field("numeric"))), ("text_field", bool(self.field("text"))),
                 ("style_field", bool(self.active_fields)))
        found.update(name for name, true in flags if true)
        return frozenset(found)

    def signature(self) -> Tuple[str, ...]:
        """What the set shown depends on: it is drawn again only when this changes, not at each feature selected."""
        if not self.known:
            return ("unknown",)
        return (("known",) + tuple(sorted(self.tokens())) +
                (self.active_id, self.active_name, repr(self.active_fields), repr(self.vector_names),
                 self.raster_name, self.elevation_name, self.cloud_name, repr(self.selected_names),
                 self.focus.id if self.focus else ""))


@dataclass(frozen=True)
class Example:
    """One request: its key, what it is about (``PROJECT`` or ``DATA``), its kind, what it supposes, the countries it
    needs, and the tools of the agent that carry it out (names of core/agent/tool_catalog.json).

    ``needs`` are words of ``Facts.tokens``: layers, no_layers, data (a vector, raster or point cloud layer: not a
    basemap), no_data, no_basemap, several (two data layers), vector, many_vectors, raster, point_cloud, polygons,
    elevation (a raster that can be a terrain model), active_vector, active_raster, active_point_cloud,
    active_elevation, active_local (not a web service), selection, local_selection (on layers that are not web
    services), filter, remote."""

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
    _p("numeric_summary", "numeric_stats", ("active_vector", "active_local", "numeric_field"), "layer_statistics"),
    _p("visible", "filter", ("vector",), "map_context", "geometry_filter"),
    _p("sel_other_layers", "cross", ("selection", "several"), "cross_filter"),
    _p("sel_radius", "near", ("selection",), "cross_filter"),
    _p("cross_near", "near", ("many_vectors",), "cross_filter"),
    _p("zoom_selection", "zoom", ("selection",), "zoom_to"),
    _p("zoom_filtered", "zoom", ("filter",), "filter_state", "zoom_to"),
    _p("sel_attributes", "attributes", ("local_selection",), "sample_features"),
    _p("sel_stats", "stats", ("local_selection",), "layer_statistics"),
    _p("stats_active", "stats", ("active_vector", "active_local", "text_field"), "layer_statistics"),
    _p("filter_state", "filters", ("filter",), "filter_state", "layer_statistics"),
    _p("clear_all", "unfilter", ("filter",), "clear_filters"),
    _p("color_by", "style", ("active_vector", "style_field"), "set_layer_style"),
    _p("raster_ramp", "style", ("active_raster",), "set_layer_style"),
    _p("labels", "labels", ("active_vector", "text_field"), "set_labels"),
    _p("export_gpkg", "export", ("filter",), "export_layers"),
    _p("export_active", "export", ("active_vector",), "export_layers"),
    _p("export_remote", "export", ("remote",), "export_layers"),
    _p("lidar_export", "export", ("point_cloud",), "export_layers"),
    _p("slope", "terrain", ("active_elevation",), "run_algorithm"),
    _p("hillshade", "shade", ("active_elevation",), "duplicate_layer", "set_layer_style"),
    _p("contours", "contours", ("active_elevation",), "contour_lines"),
    _p("raster_stats", "raster_stats", ("active_raster",), "run_algorithm"),
    _p("slope_filter", "terrain_filter", ("elevation", "vector"), "cross_filter"),
    _p("zonal", "zonal", ("raster", "polygons"), "run_algorithm"),
    _p("lidar_ground", "cloud_filter", ("point_cloud",), "point_cloud_filter"),
    _p("lidar_inside", "cloud_cross", ("point_cloud", "selection"), "cross_filter"),
    _p("join", "join", ("many_vectors",), "join_layers"),
    _p("buffer_zone", "buffer", ("active_vector",), "run_algorithm"),
    # EXPLORING driven or a slider made for the user, who then works with them (set_exploring, 2026-11-22).
    _p("pick_on_map", "explore", ("active_vector",), "set_exploring"),
    _p("slider_histogram", "widget", ("active_vector", "active_local", "numeric_field"), "create_widget"),
    _p("raster_pipette", "explore", ("active_raster",), "set_exploring"),
    _p("layout", "layout", ("data",), "create_layout"),
    _d("relief", "elevation", (), (), "find_place", "add_elevation", "set_layer_style", "contour_lines"),
    _d("elevation_view", "elevation", (), (), "add_elevation"),
    _d("people_selected", "population", (), ("selection",), "add_population", "run_algorithm"),
    _d("population_grid", "population", (), (), "add_population"),
    _d("osm_cafes", "osm", (), (), "add_osm_features"),
    _d("osm_cycle", "osm", (), (), "add_osm_features"),
    _d("osm_trees", "osm", (), (), "add_osm_features"),
    _d("dark_basemap", "basemap", (), ("data",), "add_basemap"),
    _d("add_basemap", "basemap", (), ("no_data", "no_basemap"), "add_basemap"),
    _d("sentinel", "satellite", (), (), "search_imagery", "add_layer"),
    _d("zoom_place", "places", (), (), "find_place", "zoom_to"),
    _d("ods_toilets", "open_data", (), (), "search_open_data", "add_layer"),
    _d("eurostat", "statistics", ("fr", "de", "it", "nl", "pl", "es"), (), "search_open_data", "add_layer"),
    _d("fr_communes", "open_data", ("fr",), (), "search_open_data", "add_layer"),
    _d("fr_bikes", "open_data", ("fr",), (), "search_open_data", "add_layer"),
    _d("fr_buildings", "reference", ("fr",), (), "search_open_data", "add_service_layer"),
    _d("fr_photos_1950", "imagery", ("fr",), (), "search_open_data", "add_service_layer"),
    _d("fr_flood", "risks", ("fr",), (), "search_open_data", "add_service_layer"),
    _d("fr_clay", "risks", ("fr",), (), "search_open_data", "add_service_layer"),
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


def eligible(locale: str, facts: Optional[Facts] = None) -> Tuple[Example, ...]:
    """The requests that can be offered under this locale and in this state; with no ``facts`` (unknown), only those
    that suppose nothing."""
    facts = facts or Facts.unknown()
    tokens = facts.tokens()
    # An unanchored discovery may travel to any country. An enrichment stays in the project geography; when that
    # country is unknown, use worldwide sources rather than guessing it from the UI language or the project CRS.
    anchored = facts.known and bool(facts.vectors or facts.rasters or facts.point_clouds or facts.focus)
    country = facts.focus.country if facts.focus else ""
    return tuple(example for example in CATALOG
                 if (not example.regions or not anchored or country in example.regions) and set(example.needs) <= tokens)


# What a request supposes beyond a layer being there: the selection or a filter (the state moved), then the kind of
# the active layer (what the user looks at); the others (a layer, a vector layer) are for any project.
_MOVED = frozenset({"selection", "local_selection", "filter"})
_ACTIVE = frozenset({"active_vector", "active_raster", "active_point_cloud", "active_elevation"})
_PRESENCE = frozenset({"layers", "data", "several", "vector", "many_vectors", "active_local"})


def pick(locale: str, previous: Iterable[str] = (), count: int = SHOWN, rng: Optional[random.Random] = None,
         facts: Optional[Facts] = None) -> Tuple[str, ...]:
    """Draw diverse compatible intents; prefer the selection/filter, active layer, then other project work.

    Three project recipes and one enrichment when enough distinct kinds exist. Recently seen intents are avoided
    within each group when possible, without sacrificing relevance to fill places with unrelated discoveries.
    """
    rng = rng or random.Random()  # nosec B311 - which requests are shown, nothing secret
    facts = facts or Facts.unknown()
    seen = set(previous)
    offered = eligible(locale, facts)
    fresh = [example for example in offered if example.key not in seen]
    pool = list(offered)
    for group in (PROJECT, DATA):
        wanted = min(MAX_PROJECT, count - 1) if group == PROJECT else count
        candidates = [example for example in fresh if example.group == group]
        if len({example.kind for example in candidates}) >= wanted:
            pool = [example for example in pool if example.group != group] + candidates
    chosen: List[Example] = []

    def take(candidates: Sequence[Example], strict: bool = False) -> None:
        kinds = {example.kind for example in chosen}
        left = [example for example in candidates if example not in chosen and example.kind not in kinds]
        if any(example.regions for example in chosen):
            left = [example for example in left if not example.regions]
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
        while len(chosen) < min(MAX_PROJECT, max(0, count - 1)):
            before = len(chosen)
            take(project, strict=True)
            if len(chosen) == before:
                break
    while len(chosen) < count:
        before = len(chosen)
        take([example for example in pool if example.group == DATA] or pool)
        if len(chosen) == before:
            take(pool)
        if len(chosen) == before:
            break
    rng.shuffle(chosen)
    return tuple(example.key for example in chosen)


MAX_PROJECT = 3  # leave one place for compatible data enrichment


def adjust(locale: str, current: Sequence[str], previous: Iterable[str], before: Facts, facts: Facts,
           count: int = SHOWN, rng: Optional[random.Random] = None) -> Tuple[str, ...]:
    """The set shown, brought up to date with ``facts`` when the project changed under it, not drawn again.

    Keeps the requests of ``current`` that are still true, each in its place, so that a selection made and unmade does
    not change the three requests that never depended on it. The places left (a request no longer true, or the one
    made room for) take: one request about the project that the change made possible (a selection or a filter first,
    then what ``facts`` newly allow, of a kind not there yet), then the rest of what ``pick`` would draw for ``facts``.
    Every key returned is true of ``facts``.

    Args:
        locale: The locale of QGIS.
        current: The keys on the welcome, in their places.
        previous: The set seen before (kept clear of when the catalog allows it).
        before: The facts ``current`` was drawn for.
        facts: The facts now.
        count: The number of requests.
        rng: The source of randomness (tests).
    """
    rng = rng or random.Random()  # nosec B311 - which requests are shown, nothing secret
    if ("data" in before.tokens()) != ("data" in facts.tokens()):
        return pick(locale, previous, count, rng, facts)
    allowed = {example.key: example for example in eligible(locale, facts)}
    kept = [key for key in dict.fromkeys(current) if key in allowed][:count]
    result = list(kept)

    def kinds() -> set:
        return {allowed[key].kind for key in result}

    def projects() -> int:
        return sum(allowed[key].group == PROJECT for key in result)

    gained = facts.tokens() - before.tokens()
    new = [example for example in allowed.values()
           if example.group == PROJECT and example.key not in result and gained & set(example.needs)]
    moved = [example for example in new if _MOVED & set(example.needs)]
    about_active = [example for example in new if _ACTIVE & set(example.needs)]
    if moved or about_active or (new and projects() < MAX_PROJECT):
        specific = [example for example in new if set(example.needs) - _PRESENCE - _MOVED]
        candidates = [example for example in (moved or about_active or specific or new) if example.kind not in kinds()]
        data = [key for key in result if allowed[key].group == DATA]
        about = [key for key in result if allowed[key].group == PROJECT]
        if candidates and projects() >= MAX_PROJECT and about:
            result.remove(rng.choice(about))  # the selection or the filter takes the place of another request
        elif candidates and len(result) >= count and data:
            result.remove(rng.choice(data))  # room for the request the change brings
        if candidates and len(result) < count:
            result.append(rng.choice(candidates).key)
    for key in pick(locale, previous, count, rng, facts):
        if len(result) >= count:
            break
        if key not in result and allowed[key].kind not in kinds() and (
                allowed[key].group == DATA or projects() < MAX_PROJECT):
            result.append(key)
    for key in allowed:  # a catalog too small for distinct kinds: the places are filled all the same
        if len(result) >= count:
            break
        if key not in result and (allowed[key].group == DATA or projects() < MAX_PROJECT):
            result.append(key)
    # Each request keeps its place; the new ones take the places left.
    slots: List[Optional[str]] = [key if key in result else None for key in list(current)[:count]]
    slots += [None] * (count - len(slots))
    spare = iter(key for key in result if key not in slots)
    ordered = [key if key is not None else next(spare, None) for key in slots]
    return tuple(key for key in ordered if key is not None)
