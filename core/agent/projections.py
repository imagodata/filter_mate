# -*- coding: utf-8 -*-
"""Which projection for which map: suggest_crs, from where the data lies and what the map is for.

Plain Python. ``suggest`` takes the extent of the data in degrees (WGS 84) and a purpose, and ranks candidates: the
official system of a country or territory that holds the data, the UTM zone, the Lambert zone of France (CC) for a
small area, the projections of the world and of the poles, and projections computed for the data themselves (centred
on them, the standard parallels of a cone at a sixth and five sixths of their span), given as ``PROJ:`` strings that
set_project_crs takes as they are.

Each candidate says what it keeps: the areas (equal-area, for densities and areas measured), the shapes and angles
(conformal, for local maps and navigation), the distances from its centre (equidistant), or a compromise (world maps).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

PURPOSES = ("general", "areas", "distances", "shapes", "world", "web")
EQUAL_AREA, CONFORMAL, EQUIDISTANT, COMPROMISE = "equal-area", "conformal", "equidistant", "compromise"
MAX_SUGGESTED = 6


@dataclass(frozen=True)
class Territory:
    """The official projected system of a country or territory, and the box (degrees) it is made for."""

    name: str
    crs: str
    keeps: str
    box: Tuple[float, float, float, float]  # west, south, east, north


TERRITORIES: Tuple[Territory, ...] = (
    Territory("France (Lambert-93)", "EPSG:2154", CONFORMAL, (-5.5, 41.2, 10.0, 51.2)),
    Territory("Réunion (UTM 40S)", "EPSG:2975", CONFORMAL, (55.1, -21.5, 56.0, -20.7)),
    Territory("Martinique, Guadeloupe (UTM 20N)", "EPSG:5490", CONFORMAL, (-62.0, 14.3, -60.7, 18.2)),
    Territory("Guyane (UTM 22N)", "EPSG:2972", CONFORMAL, (-54.7, 2.0, -51.5, 5.9)),
    Territory("Mayotte (UTM 38S)", "EPSG:4471", CONFORMAL, (44.9, -13.1, 45.4, -12.5)),
    Territory("Nouvelle-Calédonie (Lambert)", "EPSG:3163", CONFORMAL, (163.4, -22.9, 168.3, -19.4)),
    Territory("Polynésie française, Tahiti (UTM 6S)", "EPSG:3297", CONFORMAL, (-152.0, -18.5, -148.0, -16.0)),
    Territory("Saint-Pierre-et-Miquelon (UTM 21N)", "EPSG:4467", CONFORMAL, (-56.6, 46.7, -56.0, 47.2)),
    Territory("Belgium (Lambert 2008)", "EPSG:3812", CONFORMAL, (2.5, 49.4, 6.5, 51.6)),
    Territory("Netherlands (RD New)", "EPSG:28992", CONFORMAL, (3.2, 50.7, 7.3, 53.7)),
    Territory("Luxembourg (LUREF)", "EPSG:2169", CONFORMAL, (5.7, 49.4, 6.6, 50.2)),
    Territory("Switzerland (LV95)", "EPSG:2056", CONFORMAL, (5.9, 45.8, 10.6, 47.9)),
    Territory("Germany (UTM 32N)", "EPSG:25832", CONFORMAL, (5.8, 47.2, 15.1, 55.1)),
    Territory("Austria (Lambert)", "EPSG:31287", CONFORMAL, (9.5, 46.3, 17.2, 49.1)),
    Territory("Spain (UTM 30N)", "EPSG:25830", CONFORMAL, (-9.5, 35.9, 4.4, 43.9)),
    Territory("Portugal (TM06)", "EPSG:3763", CONFORMAL, (-9.6, 36.9, -6.1, 42.2)),
    Territory("Italy (RDN2008 Italy zone)", "EPSG:7794", CONFORMAL, (6.6, 35.4, 18.6, 47.1)),
    Territory("United Kingdom (British National Grid)", "EPSG:27700", CONFORMAL, (-8.7, 49.8, 1.8, 60.9)),
    Territory("Ireland (ITM)", "EPSG:2157", CONFORMAL, (-10.6, 51.4, -5.4, 55.4)),
    Territory("Sweden (SWEREF99 TM)", "EPSG:3006", CONFORMAL, (10.9, 55.3, 24.2, 69.1)),
    Territory("Finland (TM35FIN)", "EPSG:3067", CONFORMAL, (19.0, 59.5, 31.6, 70.1)),
    Territory("Poland (CS92)", "EPSG:2180", CONFORMAL, (14.1, 49.0, 24.2, 54.9)),
    Territory("Czechia, Slovakia (Krovak)", "EPSG:5514", CONFORMAL, (12.0, 47.7, 22.6, 51.1)),
    Territory("Greece (Greek Grid)", "EPSG:2100", CONFORMAL, (19.3, 34.8, 29.7, 41.8)),
    Territory("Europe (LAEA)", "EPSG:3035", EQUAL_AREA, (-31.0, 27.0, 45.0, 72.0)),
    Territory("Europe (LCC)", "EPSG:3034", CONFORMAL, (-31.0, 27.0, 45.0, 72.0)),
    Territory("United States, 48 states (Albers)", "EPSG:5070", EQUAL_AREA, (-125.0, 24.0, -66.0, 50.0)),
    Territory("Alaska (Albers)", "EPSG:3338", EQUAL_AREA, (-180.0, 51.0, -129.0, 72.0)),
    Territory("Canada (Atlas Lambert)", "EPSG:3978", CONFORMAL, (-141.0, 41.7, -52.0, 83.0)),
    Territory("Mexico (LCC)", "EPSG:6372", CONFORMAL, (-118.4, 14.5, -86.7, 32.7)),
    Territory("Brazil (Polyconic)", "EPSG:5880", COMPROMISE, (-74.0, -34.0, -34.8, 5.3)),
    Territory("Australia (Albers)", "EPSG:3577", EQUAL_AREA, (112.0, -44.0, 154.0, -10.0)),
    Territory("New Zealand (NZTM)", "EPSG:2193", CONFORMAL, (166.0, -47.4, 178.6, -34.1)),
    Territory("India (NSF LCC)", "EPSG:7755", CONFORMAL, (68.0, 6.0, 97.5, 37.0)),
)

WORLD = (
    ("World, Equal Earth", "EPSG:8857", EQUAL_AREA, "the areas of the world kept, a familiar look: thematic maps"),
    ("World, Robinson", "ESRI:54030", COMPROMISE, "a balanced look of the world, neither areas nor shapes exact"),
    ("World, EASE-Grid 2.0 (cylindrical equal-area)", "EPSG:6933", EQUAL_AREA,
     "areas kept on a rectangle, shapes stretched near the poles"),
)
WEB = ("Web Mercator", "EPSG:3857", CONFORMAL,
       "the projection of web basemaps; areas swell towards the poles: never for measuring")
POLAR = {
    "north": ("Arctic, polar stereographic (NSIDC)", "EPSG:3413", CONFORMAL, "the Arctic seen from the pole"),
    "south": ("Antarctica, polar stereographic", "EPSG:3031", CONFORMAL, "Antarctica seen from the pole"),
}


class ProjectionError(ValueError):
    """An extent that cannot be read: the words are for the model."""


def _span(west: float, east: float) -> float:
    """Degrees of longitude from west to east, across the antimeridian when west > east."""
    return east - west if east >= west else east + 360.0 - west


def _centre_lon(west: float, east: float) -> float:
    centre = west + _span(west, east) / 2.0
    return centre - 360.0 if centre > 180.0 else centre


def check_bounds(bounds: Sequence[float]) -> Tuple[float, float, float, float]:
    if len(bounds) != 4 or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in bounds):
        raise ProjectionError("the extent is west, south, east, north in degrees")
    west, south, east, north = (float(value) for value in bounds)
    if not (-180.0 <= west <= 180.0 and -180.0 <= east <= 180.0 and -90.0 <= south < north <= 90.0):
        raise ProjectionError("the extent is not in degrees of longitude and latitude")
    return west, south, east, north


def _inside(bounds, box, share: float = 0.9) -> bool:
    """Whether ``share`` of the box of the data lies in ``box`` (an empty box of a point counts as inside)."""
    west, south, east, north = bounds
    b_west, b_south, b_east, b_north = box
    if east < west:  # across the antimeridian: no territory of the table is
        return False
    width, height = max(east - west, 1e-9), max(north - south, 1e-9)
    overlap_w = max(0.0, min(east, b_east) - max(west, b_west))
    overlap_h = max(0.0, min(north, b_north) - max(south, b_south))
    if east - west < 1e-9:
        overlap_w = width if b_west <= west <= b_east else 0.0
    if north - south < 1e-9:
        overlap_h = height if b_south <= south <= b_north else 0.0
    return (overlap_w * overlap_h) / (width * height) >= share


def utm(lon: float, lat: float) -> Tuple[str, str]:
    """The UTM zone of a point: its CRS (ETRS89 in Europe, else WGS 84) and its name."""
    zone = min(60, max(1, int(math.floor((lon + 180.0) / 6.0)) + 1))
    if lat >= 0 and -16.0 <= lon <= 40.0 and 34.0 <= lat <= 72.0 and 28 <= zone <= 38:
        return f"EPSG:{25800 + zone}", f"ETRS89 / UTM zone {zone}N"
    return (f"EPSG:{32600 + zone}", f"WGS 84 / UTM zone {zone}N") if lat >= 0 else \
        (f"EPSG:{32700 + zone}", f"WGS 84 / UTM zone {zone}S")


CONTINENT_AREA = 900.0  # square degrees: beyond, the box of a continent or of a large country

EDGE_HOME = 0.45  # degrees from the edge of a box: nearer is not home, a neighbour's overlap may be


def _area(box: Tuple[float, float, float, float]) -> float:
    return (box[2] - box[0]) * (box[3] - box[1])


def _edge_margin(box: Tuple[float, float, float, float], lon: float, lat: float) -> float:
    """How deep the point lies in the box: the smallest distance to its sides, in degrees."""
    west, south, east, north = box
    return min(lon - west, east - lon, lat - south, north - lat)


def _round(value: float) -> float:
    return round(value, 2)


def custom(bounds: Tuple[float, float, float, float], keeps: str) -> Tuple[str, str, str]:
    """A projection made for the data: ``(PROJ: string, name, why)``. A cone with its standard parallels at a sixth
    and five sixths of the latitudes for an extent wider than tall away from the equator and the poles; an azimuthal
    projection centred on the data otherwise (a transverse Mercator for a conformal one taller than wide)."""
    west, south, east, north = bounds
    lon, lat = _round(_centre_lon(west, east)), _round((south + north) / 2.0)
    width, height = _span(west, east), north - south
    tail = " +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs"
    conic = width >= height and 15.0 <= abs(lat) <= 75.0 and south * north > 0
    if keeps == EQUIDISTANT:
        return (f"PROJ:+proj=aeqd +lat_0={lat} +lon_0={lon}{tail}", f"Azimuthal equidistant centred on {lat}, {lon}",
                "distances from the centre of the data exact in every direction")
    if conic:
        first, second = _round(south + height / 6.0), _round(north - height / 6.0)
        if keeps == EQUAL_AREA:
            return (f"PROJ:+proj=aea +lat_1={first} +lat_2={second} +lat_0={lat} +lon_0={lon}{tail}",
                    f"Albers equal-area for the data ({first}° and {second}°)",
                    "areas exact, the distortion of the shapes at its least over the data")
        return (f"PROJ:+proj=lcc +lat_1={first} +lat_2={second} +lat_0={lat} +lon_0={lon}{tail}",
                f"Lambert conformal conic for the data ({first}° and {second}°)",
                "shapes and angles exact, the distortion of the areas at its least over the data")
    if keeps == EQUAL_AREA:
        return (f"PROJ:+proj=laea +lat_0={lat} +lon_0={lon}{tail}",
                f"Lambert azimuthal equal-area centred on {lat}, {lon}",
                "areas exact, the shapes kept best near the centre of the data")
    if height > width:
        return (f"PROJ:+proj=tmerc +lat_0=0 +lon_0={lon} +k=0.9996{tail}",
                f"Transverse Mercator on the meridian {lon}",
                "shapes exact along a band north-south through the data")
    return (f"PROJ:+proj=stere +lat_0={lat} +lon_0={lon} +k=1{tail}", f"Stereographic centred on {lat}, {lon}",
            "shapes and angles exact, kept best near the centre of the data")


def _order(purpose: str) -> Tuple[str, ...]:
    """What the purpose wants kept, first to last."""
    return {"areas": (EQUAL_AREA, COMPROMISE, CONFORMAL, EQUIDISTANT),
            "distances": (EQUIDISTANT, CONFORMAL, COMPROMISE, EQUAL_AREA),
            "shapes": (CONFORMAL, COMPROMISE, EQUIDISTANT, EQUAL_AREA)}.get(purpose, ())


def suggest(bounds: Sequence[float], purpose: str = "general") -> Dict[str, object]:
    """Candidates for data within ``bounds`` (west, south, east, north in degrees) and a ``purpose``, best first:
    ``{scale, suggestions: [{crs, name, keeps, why}]}``."""
    if purpose not in PURPOSES:
        raise ProjectionError(f"purpose is one of {', '.join(PURPOSES)}")
    box = check_bounds(bounds)
    west, south, east, north = box
    width, height = _span(west, east), north - south
    lon, lat = _centre_lon(west, east), (south + north) / 2.0
    found: List[Dict[str, str]] = []

    def add(crs: str, name: str, keeps: str, why: str) -> None:
        if all(row["crs"] != crs for row in found):
            found.append({"crs": crs, "name": name, "keeps": keeps, "why": why})

    def add_row(row: Tuple[str, str, str, str]) -> None:  # (name, crs, keeps, why), as the tables hold them
        add(row[1], row[0], row[2], row[3])

    world_scale = width > 100.0 or height > 60.0 or purpose == "world"
    if purpose == "web":
        add_row(WEB)
    if north >= 60.0 and south >= 45.0 and (width > 90.0 or north >= 80.0):
        add_row(POLAR["north"])
    if south <= -60.0 and north <= -45.0:
        add_row(POLAR["south"])
    if world_scale:
        world = list(WORLD)
        if purpose == "general" or purpose == "world":
            world.sort(key=lambda row: row[1] != "ESRI:54030")  # Robinson first for a map of the world to look at
        for row in world:
            add_row(row)
        if purpose != "web":
            add_row(WEB[:3] + ("only for a map over web basemaps",))
        return {"scale": "world", "suggestions": found[:MAX_SUGGESTED]}

    territories = [territory for territory in TERRITORIES if _inside(box, territory.box)]
    # Boxes overlap at borders (Toulouse lies in the box of Spain too, Lille in the one of Belgium, Corsica deep
    # in the one of Italy): the country that holds the data deepest comes first, not the neighbour whose box is
    # centred nearest (audit of 2026-11-24: Strasbourg, Lille and Corsica came out German, Belgian and Italian,
    # and EPSG:2154 was missing). A second overlapping country still shows: more than one country may hold data
    # across a border. Then the local zones, the systems of a continent, the projections made for the data.
    national = sorted(
        (territory for territory in territories if _area(territory.box) < CONTINENT_AREA),
        key=lambda territory: (_edge_margin(territory.box, lon, lat) < EDGE_HOME, -_area(territory.box)))[:2]
    continental = [territory for territory in territories if _area(territory.box) >= CONTINENT_AREA]
    for territory in national[:1]:
        add(territory.crs, territory.name, territory.keeps,
            f"the official system for {territory.name.split(' (')[0]}")
    if national and national[0].crs == "EPSG:2154" and height <= 1.2:
        zone = min(50, max(42, int(math.floor(lat + 0.25))))  # CC43 from 42.25° to 43.75°, as the IGN cuts them
        add(f"EPSG:{3900 + zone}", f"RGF93 / CC{zone}", CONFORMAL,
            "the Lambert zone of France at this latitude: less alteration of lengths than Lambert-93 locally")
    if width <= 6.5 and abs(lat) < 84.0:
        crs, name = utm(lon, lat)
        add(crs, name, CONFORMAL, "the UTM zone of the data: lengths within 0.1 % over 6° of longitude")
    for territory in national[1:2]:  # across the border: after the zones of the country that holds the data
        add(territory.crs, territory.name, territory.keeps,
            f"the official system for {territory.name.split(' (')[0]} too (across the border)")
    for territory in continental:
        add(territory.crs, territory.name, territory.keeps, f"the system for {territory.name.split(' (')[0]}")
    for keeps in (EQUAL_AREA, CONFORMAL, EQUIDISTANT):
        crs, name, why = custom(box, keeps)
        add(crs, name, keeps, why + " (made for these data)")
    order = _order(purpose)
    if order:  # what the purpose keeps first; within a kind, the order above (official systems first)
        found.sort(key=lambda row: order.index(row["keeps"]) if row["keeps"] in order else len(order))
    scale = "local" if max(width, height) <= 2.0 else "regional" if max(width, height) <= 25.0 else "continental"
    return {"scale": scale, "suggestions": found[:MAX_SUGGESTED]}
