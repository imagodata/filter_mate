# -*- coding: utf-8 -*-
"""Web basemaps the agent can add: tiles drawn by a server, addressed by a template. Pure, no QGIS, no network.

A basemap is an image under the data: nothing of it is filtered, read or exported. Its server sees the areas the
map shows, as with a basemap the user adds from the browser of QGIS; so only the ones the user ticked are added,
and a model names one of them, it never writes an address.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import urlsplit

DEFAULT_ZMAX = 19
SAMPLE_ZOOM = 10
_LOOPBACK = ("127.0.0.1", "localhost", "::1")
# What QGIS replaces in the template of an XYZ layer: {-y} counts the rows from the south (TMS), {q} is a quadkey.
_ROWS = ("{y}", "{-y}")
_IMAGES = (b"\x89PNG", b"\xff\xd8", b"RIFF", b"GIF8")
# The Géoplateforme serves its WMTS tiles by plain parameters: a template as any other, in the Web Mercator pyramid.
_GEOPF = ("https://data.geopf.fr/wmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&LAYER={layer}&STYLE=normal"
          "&FORMAT={image}&TILEMATRIXSET=PM&TILEMATRIX={{z}}&TILEROW={{y}}&TILECOL={{x}}")


@dataclass(frozen=True)
class Basemap:
    """One basemap of the list. ``official`` says who serves it: a public agency, or a company or a community."""

    id: str
    title: str
    url: str
    attribution: str
    note: str
    zmax: int = DEFAULT_ZMAX
    official: bool = False


# Each one was checked to serve a tile without an account when it was added (2026-11-14). The terms are those of
# each server: the note says what the user should know before ticking it.
BASEMAPS: Tuple[Basemap, ...] = (
    Basemap("osm_tiles", "OpenStreetMap", "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            "© OpenStreetMap contributors", "Worldwide street map, in colours. Run by volunteers: no heavy use"),
    Basemap("carto_light", "Carto Light (neutral, with names)", "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
            "© OpenStreetMap contributors © CARTO",
            "Worldwide, light grey: a neutral background. Free for non-commercial use (terms of CARTO)", 20),
    Basemap("carto_light_nolabels", "Carto Light (neutral, no names)",
            "https://basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png", "© OpenStreetMap contributors © CARTO",
            "Worldwide, light grey with no place names: under layers that have their own labels. "
            "Free for non-commercial use (terms of CARTO)", 20),
    Basemap("carto_dark", "Carto Dark", "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
            "© OpenStreetMap contributors © CARTO",
            "Worldwide, dark: for bright symbols. Free for non-commercial use (terms of CARTO)", 20),
    Basemap("carto_voyager", "Carto Voyager", "https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png",
            "© OpenStreetMap contributors © CARTO",
            "Worldwide street map in soft colours. Free for non-commercial use (terms of CARTO)", 20),
    Basemap("ign_plan", "IGN Plan (France)", _GEOPF.format(layer="GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2", image="image/png"),
            "© IGN", "France, the reference map of IGN (open licence)", 19, True),
    Basemap("ign_ortho", "IGN aerial photographs (France)",
            _GEOPF.format(layer="ORTHOIMAGERY.ORTHOPHOTOS", image="image/jpeg"),
            "© IGN", "France, aerial photographs of IGN (open licence)", 19, True),
    Basemap("opentopomap", "OpenTopoMap", "https://tile.opentopomap.org/{z}/{x}/{y}.png",
            "© OpenStreetMap contributors, SRTM | © OpenTopoMap (CC-BY-SA)",
            "Worldwide topographic map with contours. Run by volunteers: no heavy use", 17),
)
_BY_URL = {basemap.url: basemap for basemap in BASEMAPS}
_BY_ID = {basemap.id: basemap for basemap in BASEMAPS}


def known(url: str) -> Optional[Basemap]:
    """The basemap of the list served at this template, for its title, its deepest zoom and its attribution."""
    return _BY_URL.get(url)


def template_problem(url: str) -> str:
    """Why this address is no tile template QGIS can read; "" when it is one."""
    url = (url or "").strip()
    if not url or any(ord(char) < 33 for char in url):
        return "this address cannot be read"
    try:
        parts = urlsplit(url)
        host = parts.hostname
    except ValueError:
        return "this address cannot be read"
    if not host or not (parts.scheme == "https" or (parts.scheme == "http" and host in _LOOPBACK)):
        return "a basemap is read over https, or on this machine"
    if "{s}" in url:
        return "QGIS does not replace {s}: write one server name instead (often a)"
    by_cell = "{x}" in url and "{z}" in url and any(row in url for row in _ROWS)
    if not by_cell and "{q}" not in url:
        return "a basemap address holds {z}, {x} and {y}: https://server/{z}/{x}/{y}.png"
    return ""


def xyz_uri(url: str, zmax: int = DEFAULT_ZMAX) -> str:
    """The source of an XYZ layer for the wms provider of QGIS, which reads ``&`` and ``=`` as its own separators.

    What is not ASCII is escaped too: QGIS 3.22 reads the source as Latin-1 and turned any other letter into ``?``.
    """
    escaped = "".join(char if char not in "%&=" and 32 < ord(char) < 127
                      else "".join(f"%{byte:02X}" for byte in char.encode("utf-8")) for char in url)
    return f"type=xyz&url={escaped}&zmax={max(0, min(int(zmax), 24))}&zmin=0"


def tile_url(url: str, zoom: int, column: int, row: int) -> str:
    """The address of one tile of the template; ``row`` counts from the north, as ``{y}`` does."""
    quadkey = "".join(str(((column >> bit) & 1) + 2 * ((row >> bit) & 1)) for bit in range(zoom - 1, -1, -1))
    return (url.replace("{z}", str(zoom)).replace("{x}", str(column)).replace("{y}", str(row))
            .replace("{-y}", str(2 ** zoom - 1 - row)).replace("{q}", quadkey))


def tile_at(longitude: float, latitude: float, zoom: int) -> Tuple[int, int]:
    """Column and row of the Web Mercator tile that holds a place, at a zoom."""
    count = 2 ** zoom
    latitude = math.radians(max(-85.0511, min(85.0511, latitude)))
    column = int((longitude + 180.0) / 360.0 * count)
    row = int((1.0 - math.asinh(math.tan(latitude)) / math.pi) / 2.0 * count)
    return max(0, min(count - 1, column)), max(0, min(count - 1, row))


def sample_tiles(url: str, place: Optional[Tuple[float, float]] = None, zmax: int = DEFAULT_ZMAX) -> Tuple[str, ...]:
    """Tiles to ask, the first that comes as an image is enough: where the map is, then a quarter of the world.

    A server of one country, or one that starts at a deeper zoom, has no tile for a quarter of the world; a map
    elsewhere has none where it is.
    """
    asked = []
    if place is not None:
        zoom = min(SAMPLE_ZOOM, zmax)
        asked.append(tile_url(url, zoom, *tile_at(place[0], place[1], zoom)))
    asked.append(tile_url(url, 1, 0, 0))
    return tuple(asked)


def is_image(content: bytes) -> bool:
    """A tile is a PNG, a JPEG, a WebP or a GIF; an error page served with a 200 is not."""
    return bytes(content[:4]).startswith(_IMAGES)


def shown(platform: str, short: bool = False) -> str:
    """What the user reads of a basemap a model named: its title and its server, or the address the user added."""
    listed = _BY_ID.get((platform or "").strip().lower())
    if listed is not None:
        return listed.title if short else f"{listed.title} · {default_title(listed.url)}"
    platform = " ".join((platform or "").split())
    return default_title(platform) if short and "://" in platform else platform[:300]


def default_title(url: str) -> str:
    """The name of a layer made of a template the list does not know: the name of its server."""
    try:
        return urlsplit(url).hostname or "Basemap"
    except ValueError:
        return "Basemap"
