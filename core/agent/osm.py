# -*- coding: utf-8 -*-
"""OpenStreetMap features the agent can bring in: what is asked of an Overpass server, and how its answer is read.

Pure, no QGIS, no network. A model names tags (``amenity=hospital``, ``building``) and an area; the query sent to the
server is written here, from tags checked one by one, so that nothing of a model is ever a piece of a query language.
The answer is OpenStreetMap XML, read by the OSM driver of GDAL with a configuration written here too: the keys asked
become columns, and a feature is kept when one of the tags asked is on it.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

MAX_TAGS = 10
MAX_AREA_KM2 = 10_000.0  # 100 km by 100 km: the hospitals of a region; the size of the answer bounds the rest
MAX_BYTES = 64 * 1024 * 1024
SERVER_TIMEOUT_S = 60  # what the server may spend on the query
ATTRIBUTION = "© OpenStreetMap contributors (ODbL)"
GEOMETRIES = ("as_mapped", "points", "lines", "polygons")
# The layers of the OSM driver of GDAL, and the kind of layer each one fills here.
LAYER_KINDS = {"points": "points", "lines": "lines", "multilinestrings": "lines", "multipolygons": "polygons"}
OSM_TYPES = {"points": "node", "lines": "way", "multilinestrings": "relation"}
_KEY = re.compile(r"[A-Za-z][A-Za-z0-9_:.-]{0,59}")
# A value goes between double quotes in the query: no quote, no backslash, nothing that does not print.
_VALUE = re.compile(r"[^\"\\\x00-\x1f\x7f]{1,80}")
# A closed way is an area when it carries one of these keys (the list of GDAL, less the keys the table below decides
# value by value: GDAL ranks a way of its keys as an area whatever the value, a natural=tree_row or an
# aeroway=taxiway that closes included). The keys asked are added, but those of what is drawn as a line even when it
# closes (a roundabout, a fence, a ring road): for these the rules of OpenStreetMap decide, tag by tag, in
# ``closed_way_is_area``.
_AREA_KEYS = ("amenity", "boundary", "building", "craft", "geological", "historic", "landuse", "leisure", "military",
              "office", "place", "shop", "sport", "tourism", "highway=platform", "public_transport=platform")
_LINE_KEYS = frozenset({"highway", "waterway", "railway", "barrier", "aerialway", "route", "power", "man_made",
                        "name", "ref", "bridge", "tunnel", "oneway", "surface", "maxspeed", "lanes"})
# "A closed way is an area": the table of the wiki (Key:area) and of osmtogeojson (polygon-features), by key. Every
# value makes an area; or only the values of a list (a closed highway=residential is a loop of street, a
# highway=services a car park); or every value but those of a list (a closed natural=cliff is a line).
_AREA_ANY = frozenset({"building", "landuse", "amenity", "leisure", "area", "boundary", "place", "shop", "tourism",
                       "historic", "public_transport", "office", "building:part", "military", "ruins", "area:highway",
                       "craft", "golf", "indoor"})
_AREA_ONLY = {
    "highway": frozenset({"services", "rest_area", "escape", "elevator"}),
    "waterway": frozenset({"riverbank", "dock", "boatyard", "dam"}),
    "barrier": frozenset({"city_wall", "ditch", "hedge", "retaining_wall", "wall", "spikes"}),
    "railway": frozenset({"station", "turntable", "roundhouse", "platform"}),
    "power": frozenset({"plant", "substation", "generator", "transformer"}),
}
_AREA_BUT = {
    "natural": frozenset({"coastline", "cliff", "ridge", "arete", "tree_row"}),
    "man_made": frozenset({"cutline", "embankment", "pipeline"}),
    "aeroway": frozenset({"taxiway"}),
}
# The columns every layer made has, which a key asked cannot be.
OWN_COLUMNS = ("osm_id", "osm_type", "other_tags")
# Names a column of a key cannot take, whatever their case: a GeoPackage tells no column from another by its
# case. 2026-11-15: the key OSM_ID replaced the identifier of every feature, Other_Tags lost its column, and with
# GDAL 3.4 the layer could not be opened at all (duplicate column name).
_RESERVED = frozenset(OWN_COLUMNS + ("osm_way_id", "fid", "ogc_fid", "geom", "geometry"))
_GDAL_LAYERS = ("points", "lines", "multipolygons", "multilinestrings", "other_relations")
_METRES_PER_DEGREE = 111_320.0


@dataclass(frozen=True)
class OverpassServer:
    """One Overpass server of the list: who runs it, and what the user should know before ticking it."""

    id: str
    title: str
    url: str
    note: str


# Checked to answer without an account when they were added (2026-11-15). They are run by volunteers, for people at
# their keyboard: a query at a time, bounded in size and in time. The first is the one a call names by default:
# measured that day on the hospitals of Lyon, it answered in 2 s each time, while the main server answered busy
# (502, 429) twice out of three and in 28 s the third.
SERVERS: Tuple[OverpassServer, ...] = (
    OverpassServer("overpass_fr", "OpenStreetMap, Overpass (openstreetmap.fr)",
                   "https://overpass.openstreetmap.fr/api/interpreter",
                   "Worldwide: roads, buildings, shops, hospitals, land use... by tags. Run by OpenStreetMap France, "
                   "volunteers: no heavy use"),
    OverpassServer("overpass_de", "OpenStreetMap, Overpass (overpass-api.de)", "https://overpass-api.de/api/interpreter",
                   "Worldwide, the same data, the main server. Run by volunteers: no heavy use; often busy"),
)
DEFAULT_SERVER = SERVERS[0].id


@dataclass(frozen=True)
class Tag:
    """One tag asked: a key, and a value or "" for any value."""

    key: str
    value: str = ""

    @property
    def column(self) -> str:
        """The name of its column in the layers made: GDAL writes ``addr:street`` as ``addr_street``."""
        return self.key.replace(":", "_")

    def shown(self) -> str:
        return f"{self.key}={self.value}" if self.value else self.key


def read_tags(tags: object) -> List[Tag]:
    """The tags a model gave, checked: ``[{"key": "amenity", "value": "hospital"}, {"key": "building"}]``.

    Raises:
        ValueError: None, too many, or one that is not a key and a value OpenStreetMap could hold.
    """
    if not isinstance(tags, (list, tuple)) or not tags:
        raise ValueError('tags is a list such as [{"key": "amenity", "value": "hospital"}]')
    if len(tags) > MAX_TAGS:
        raise ValueError(f"{MAX_TAGS} tags at most")
    read: List[Tag] = []
    for item in tags:
        key = item.get("key") if isinstance(item, Mapping) else None
        value = item.get("value", "") if isinstance(item, Mapping) else None
        if not isinstance(key, str) or not _KEY.fullmatch(key):
            raise ValueError("a key is written as OpenStreetMap writes it, in letters, digits and : _ . - (amenity, "
                             "building, addr:street)")
        if key.replace(":", "_").casefold() in _RESERVED:
            raise ValueError(f"{key} is the name of a column every layer has: it cannot be a key asked")
        if value is None:
            value = ""
        if not isinstance(value, str) or (value and not _VALUE.fullmatch(value)) or value.strip() != value:
            raise ValueError(f"the value of {key} is a plain text of 80 characters at most, without a quote nor a "
                             "backslash; leave it empty for any value")
        tag = Tag(key, value)
        if tag not in read:
            read.append(tag)
    taken = {"name": "name"}  # column, whatever its case -> the key that makes it
    for tag in read:
        column = tag.column.casefold()
        if taken.setdefault(column, tag.key) != tag.key:
            raise ValueError(f"{taken[column]} and {tag.key} would share a column (as addr:street and addr_street, "
                             "or Building and building): ask for one")
    return read


def closed_way_is_area(tags: Mapping[str, str]) -> bool:
    """Whether a closed way with these tags (all of them, by key) is an area, by the rules OpenStreetMap writes.

    ``area=no`` makes a line of it whatever else it carries, and ``area=yes`` an area; otherwise one tag of the table
    (``_AREA_ANY``, ``_AREA_ONLY``, ``_AREA_BUT``) is enough, and a value of ``no`` (``building=no``) counts for
    nothing. GDAL reads the whole key or nothing, so a way whose key is only an area for some values (``power``,
    ``railway``, ``man_made``) is left a line by it, and is turned into an area from this.
    """
    if tags.get("area") == "no":
        return False
    for key, value in tags.items():
        if value in (None, "", "no"):
            continue
        if key in _AREA_ANY:
            return True
        if key in _AREA_ONLY and value in _AREA_ONLY[key]:
            return True
        if key in _AREA_BUT and value not in _AREA_BUT[key]:
            return True
    return False


_HSTORE = re.compile(r'"((?:[^"\\]|\\.)*)"\s*=>\s*"((?:[^"\\]|\\.)*)"')
_UNESCAPE = re.compile(r"\\(.)")


def way_tags(values: Mapping[str, Optional[str]], asked: Sequence[Tag]) -> Dict[str, str]:
    """Every tag of a feature read, by key: the columns of the keys asked, and the ``other_tags`` GDAL keeps the rest
    in (``"power"=>"substation","area"=>"no"``)."""
    found: Dict[str, str] = {}
    for key, value in _HSTORE.findall(values.get("other_tags") or ""):
        found[_UNESCAPE.sub(r"\1", key)] = _UNESCAPE.sub(r"\1", value)
    for tag in asked:
        value = values.get(tag.column)
        if value not in (None, ""):
            found[tag.key] = value
    return found


def area_km2(bbox: Sequence[float]) -> float:
    """The surface of ``[west, south, east, north]`` in square kilometres, on the ground at its middle latitude."""
    west, south, east, north = bbox
    middle = math.radians((south + north) / 2.0)
    width = (east - west) * _METRES_PER_DEGREE * max(math.cos(middle), 0.01)
    return width * (north - south) * _METRES_PER_DEGREE / 1e6


def area_problem(bbox: Sequence[float]) -> str:
    """Why this area is too large to ask an Overpass server for; "" when it is not."""
    surface = area_km2(bbox)
    if surface > MAX_AREA_KM2:
        return (f"this area covers {surface:,.0f} km2, {MAX_AREA_KM2:,.0f} at most: ask for a smaller one (a town, a "
                "district), or for a layer of a WFS service for a whole region")
    return ""


def overpass_query(tags: Sequence[Tag], bbox: Sequence[float], timeout: int = SERVER_TIMEOUT_S,
                   max_bytes: int = MAX_BYTES) -> str:
    """The query for the nodes, ways and relations that carry one of ``tags`` in ``[west, south, east, north]``.

    The nodes of the ways come with them, and everything in the order of an OpenStreetMap file (nodes, ways,
    relations): GDAL builds no line nor area from a way read before its nodes (2026-11-15: 0 area for the hospitals of
    Lyon in the order Overpass gives by default).
    """
    west, south, east, north = (float(value) for value in bbox)
    box = f"({south:.7f},{west:.7f},{north:.7f},{east:.7f})"
    lines = [f'  nwr["{tag.key}"="{tag.value}"]{box};' if tag.value else f'  nwr["{tag.key}"]{box};' for tag in tags]
    return (f"[out:xml][timeout:{int(timeout)}][maxsize:{int(max_bytes)}];\n(\n" + "\n".join(lines)
            + "\n);\n(._;>;);\nout body;\n")


def gdal_config(tags: Sequence[Tag]) -> str:
    """The configuration of the OSM driver of GDAL for these tags: each key asked is a column of every layer, the
    other tags stay together in ``other_tags``.

    GDAL turns a closed way into an area from a whole key. A key that is an area for some values only
    (``power=substation``, not ``power=line``; ``natural=wood``, not ``natural=tree_row``) is left to
    ``closed_way_is_area``, read from the tags of the feature: no ``key=value`` is added to the list, GDAL 3.4.1 honours
    those of its own list (``highway=platform``) but loses them all as soon as a key has two values listed
    (2026-11-18: ``power=substation,power=plant`` left even ``highway=platform`` a line).

    Written without a ``[general]`` section, which GDAL 3.4 does not know and GDAL 3.12 does not need.
    """
    keys = list(dict.fromkeys(["name"] + [tag.key for tag in tags]))
    # A key asked that the table knows is decided by ``closed_way_is_area`` (a value at a time); one it does not know
    # (healthcare) is an area as a whole, as the keys of GDAL are.
    known_keys = _LINE_KEYS | _AREA_ANY | frozenset(_AREA_ONLY) | frozenset(_AREA_BUT) | frozenset(_AREA_KEYS)
    areas = list(_AREA_KEYS) + [tag.key for tag in tags if tag.key not in known_keys]
    text = [f"closed_ways_are_polygons={','.join(dict.fromkeys(areas))}", "attribute_name_laundering=yes"]
    for layer in _GDAL_LAYERS:
        text += [f"[{layer}]", "osm_id=yes"]
        if layer == "multipolygons":
            text.append("osm_way_id=yes")
        text += [f"attributes={','.join(keys)}", f"other_tags={'no' if layer == 'other_relations' else 'yes'}"]
    return "\n".join(text) + "\n"


def columns(tags: Sequence[Tag]) -> List[str]:
    """The columns the keys asked make, ``name`` first."""
    return list(dict.fromkeys(["name"] + [tag.column for tag in tags]))


def matches(tags: Sequence[Tag], values: Mapping[str, Optional[str]]) -> bool:
    """Whether a feature read (its values by column) carries one of the tags asked.

    An answer holds more than what was asked: the nodes of a way come with their own tags (a door, a traffic light),
    and they carry none of these.
    """
    for tag in tags:
        value = values.get(tag.column)
        if value is not None and value != "" and (not tag.value or value == tag.value):
            return True
    return False


_REMARK = re.compile(rb"<remark>\s*(.*?)\s*</remark>", re.DOTALL)


def remark_problem(tail: bytes) -> str:
    """Why the server stopped before its answer was whole, from the end of what it sent; "" when it did not.

    An Overpass server answers 200 and ends its document with a remark when a query ran out of time or of memory:
    the features before it are only a part of what was asked.
    """
    found = _REMARK.search(tail or b"")
    if not found:
        return ""
    said = found.group(1).decode("utf-8", "replace").lower()
    if "timed out" in said or "timeout" in said:
        return "the server ran out of time on this query: ask for a smaller area, or for fewer tags"
    if "memory" in said or "maxsize" in said:
        return "the answer would be too large for the server: ask for a smaller area, or for fewer tags"
    return "the server stopped before its answer was whole: ask for a smaller area, or try again later"


def cut_problem(tail: bytes) -> str:
    """Why an answer is not a whole OpenStreetMap document, from its end; "" when it is one."""
    return "" if b"</osm>" in (tail or b"") else "the answer was cut before its end: try again, or ask another server"


REDIRECTS = (301, 302, 303, 307, 308)
ANOTHER = "ask another OpenStreetMap server of the list when one is enabled, or try again in a minute"


def status_problem(status: int) -> str:
    """What an HTTP status of an Overpass server means; "" for 200."""
    if status == 200:
        return ""
    if status in REDIRECTS:
        return (f"the server sends the request to another address ({status}), which is not followed: its address "
                "has changed")
    if status == 400:
        return "the server refused the query (400)"
    if status == 429:
        return "the server answers that it got too many requests (429)"
    if status in (502, 503, 504):
        return f"the server is busy ({status})"
    return f"the server answered with an error ({status})"


def status_refusal(platform: str, status: int) -> str:
    """What a model reads of a status that is not 200: the problem, then what can be done about it.

    Asking another server changes nothing to a query refused (400). The address of a server of the list cannot be
    corrected by the user: when it has moved, the other one is asked; one the user added is corrected in the
    Sources tab.
    """
    problem = f"{platform}: {status_problem(status)}"
    if status == 400:
        return problem
    if status in REDIRECTS and platform not in {server.id for server in SERVERS}:
        return f"{problem}; it is corrected in the Sources tab"
    return f"{problem}; {ANOTHER}"


def layer_title(name: str, kind: str, several: bool) -> str:
    """The name of a layer made: the one given, with its kind when a request makes several."""
    return f"{name} ({kind})" if several else name


def default_name(tags: Sequence[Tag]) -> str:
    """The name of what was asked, when the user gave none: its tags."""
    return ("OSM " + ", ".join(tag.shown() for tag in tags[:3]) + ("..." if len(tags) > 3 else ""))[:120]


def summary(counts: Mapping[str, int]) -> Dict[str, int]:
    """The features kept by kind, the kinds with none left out."""
    return {kind: count for kind, count in counts.items() if count}
