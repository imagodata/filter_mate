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
from urllib.parse import parse_qs, urlsplit

DEFAULT_ZMAX = 19
SAMPLE_ZOOM = 10
_LOOPBACK = ("127.0.0.1", "localhost", "::1")
# What QGIS replaces in the template of an XYZ layer: {-y} counts the rows from the south (TMS), {q} is a quadkey.
_ROWS = ("{y}", "{-y}")
_IMAGES = (b"\x89PNG", b"\xff\xd8", b"RIFF", b"GIF8")
# The Géoplateforme serves its WMTS tiles by plain parameters: a template as any other, in the Web Mercator pyramid.
_GEOPF = ("https://data.geopf.fr/wmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&LAYER={layer}&STYLE=normal"
          "&FORMAT={image}&TILEMATRIXSET=PM&TILEMATRIX={{z}}&TILEROW={{y}}&TILECOL={{x}}")
_ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/{service}/MapServer/tile/{{z}}/{{y}}/{{x}}"
_CARTO_KEY_NOTE = ("API key required: add an XYZ source with ?key=YOUR_KEY (https://www.carto.com/basemaps/apikey/), "
                   "or choose an Esri background instead")


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
    # A covered (longitude, latitude) in EPSG:4326 for regional checks; it never moves the user's map.
    sample_place: Optional[Tuple[float, float]] = None


# The terms are those of each server: the note says what the user should know before ticking it. CARTO changed its
# access policy in 2026: without a key its HTTP 200 PNG is an "API KEY REQUIRED" notice, not a map.
BASEMAPS: Tuple[Basemap, ...] = (
    Basemap("osm_tiles", "OpenStreetMap", "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            "© OpenStreetMap contributors", "Worldwide street map, in colours. Run by volunteers: no heavy use"),
    Basemap("carto_light", "Carto Light (API key required)", "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
            "© OpenStreetMap contributors © CARTO",
            "Worldwide, light grey with place names. " + _CARTO_KEY_NOTE, 20),
    Basemap("carto_light_nolabels", "Carto Light, no names (API key required)",
            "https://basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png", "© OpenStreetMap contributors © CARTO",
            "Worldwide, light grey without place names. " + _CARTO_KEY_NOTE, 20),
    Basemap("carto_dark", "Carto Dark (API key required)", "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
            "© OpenStreetMap contributors © CARTO",
            "Worldwide, dark: for bright symbols. " + _CARTO_KEY_NOTE, 20),
    Basemap("carto_voyager", "Carto Voyager (API key required)",
            "https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png",
            "© OpenStreetMap contributors © CARTO",
            "Worldwide street map in soft colours. " + _CARTO_KEY_NOTE, 20),
    Basemap("ign_plan", "IGN Plan (France)", _GEOPF.format(layer="GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2", image="image/png"),
            "© IGN", "France, the reference map of IGN (open licence)", 19, True),
    Basemap("ign_ortho", "IGN aerial photographs (France)",
            _GEOPF.format(layer="ORTHOIMAGERY.ORTHOPHOTOS", image="image/jpeg"),
            "© IGN", "France, aerial photographs of IGN (open licence)", 19, True),
    Basemap("google_satellite", "Google Satellite", "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
            "© Google", "Worldwide satellite and aerial photographs. The terms of Google Maps apply: read them "
            "before a commercial or a heavy use", 20),
    Basemap("opentopomap", "OpenTopoMap", "https://tile.opentopomap.org/{z}/{x}/{y}.png",
            "© OpenStreetMap contributors, SRTM | © OpenTopoMap (CC-BY-SA)",
            "Worldwide topographic map with contours. Run by volunteers: no heavy use", 17),
    # Checked 2026-11-26 against the service metadata and in QGIS; access is subject to Esri's terms.
    Basemap("esri_light_gray", "Esri Light Gray (neutral)", _ESRI.format(service="Canvas/World_Light_Gray_Base"),
            "Esri, HERE, Garmin, © OpenStreetMap contributors, and the GIS user community",
            "Worldwide neutral light-grey base without a key. The terms of Esri apply", 23),
    Basemap("esri_dark_gray", "Esri Dark Gray (neutral)", _ESRI.format(service="Canvas/World_Dark_Gray_Base"),
            "Esri, HERE, Garmin, © OpenStreetMap contributors, and the GIS user community",
            "Worldwide neutral dark-grey base without a key. The terms of Esri apply", 23),
    Basemap("esri_imagery", "Esri World Imagery", _ESRI.format(service="World_Imagery"),
            "Esri, Vantor, Earthstar Geographics, and the GIS User Community",
            "Worldwide satellite and aerial photographs. Detail varies by area; the terms of Esri apply", 23),
    Basemap("esri_topo", "Esri World Topographic Map", _ESRI.format(service="World_Topo_Map"),
            "Esri, HERE, Garmin, Intermap, increment P Corp., GEBCO, USGS, FAO, NPS, NRCAN, GeoBase, IGN, "
            "Kadaster NL, Ordnance Survey, Esri Japan, METI, Esri China (Hong Kong), © OpenStreetMap contributors, "
            "and the GIS User Community",
            "Worldwide topographic reference map with relief. Detail varies by area; the terms of Esri apply", 23),
    Basemap("esri_streets", "Esri World Street Map", _ESRI.format(service="World_Street_Map"),
            "Esri, HERE, Garmin, USGS, Intermap, INCREMENT P, NRCan, Esri Japan, METI, Esri China (Hong Kong), "
            "Esri Korea, Esri (Thailand), NGCC, © OpenStreetMap contributors, and the GIS User Community",
            "Worldwide street map. Detail varies by area; the terms of Esri apply", 23),
)

# Official regional backgrounds: verified on 2026-11-26, each with a known covered point.
REGIONAL_BASEMAPS: Tuple[Basemap, ...] = (
    Basemap("swisstopo_map", "Swisstopo national map (Switzerland)",
            "https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.pixelkarte-farbe/default/current/3857/{z}/{x}/{y}.jpeg",
            "© swisstopo",
            "Switzerland only. Official public background without an API key; provider terms apply.",
            18, True, sample_place=(7.447, 46.948)),
    Basemap("swisstopo_gray", "Swisstopo grey map (Switzerland)",
            "https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.pixelkarte-grau/default/current/3857/{z}/{x}/{y}.jpeg",
            "© swisstopo",
            "Switzerland only. Official public background without an API key; provider terms apply.",
            18, True, sample_place=(7.447, 46.948)),
    Basemap("swisstopo_ortho", "Swisstopo SWISSIMAGE (Switzerland)",
            "https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.swissimage/default/current/3857/{z}/{x}/{y}.jpeg",
            "© swisstopo",
            "Switzerland only. Official public background without an API key; provider terms apply.",
            18, True, sample_place=(7.447, 46.948)),
    Basemap("basemap_at", "basemap.at standard (Austria)",
            "https://maps.wien.gv.at/basemap/geolandbasemap/normal/google3857/{z}/{y}/{x}.png",
            "© basemap.at",
            "Austria only. Official public background without an API key; provider terms apply.",
            20, True, sample_place=(16.373, 48.208)),
    Basemap("basemap_at_gray", "basemap.at grey (Austria)",
            "https://maps.wien.gv.at/basemap/bmapgrau/normal/google3857/{z}/{y}/{x}.png",
            "© basemap.at",
            "Austria only. Official public background without an API key; provider terms apply.",
            20, True, sample_place=(16.373, 48.208)),
    Basemap("basemap_at_ortho", "basemap.at orthophoto (Austria)",
            "https://maps.wien.gv.at/basemap/bmaporthofoto30cm/normal/google3857/{z}/{y}/{x}.jpeg",
            "© basemap.at",
            "Austria only. Official public background without an API key; provider terms apply.",
            20, True, sample_place=(16.373, 48.208)),
    Basemap("pdok_brt", "PDOK BRT standard (Netherlands)",
            "https://service.pdok.nl/kadaster/brt-achtergrondkaart/wmts/v2_0/standaard/EPSG:3857/{z}/{x}/{y}.png",
            "© Kadaster / PDOK",
            "Netherlands only. Official public background without an API key; provider terms apply.",
            19, True, sample_place=(4.895, 52.37)),
    Basemap("pdok_brt_gray", "PDOK BRT grey (Netherlands)",
            "https://service.pdok.nl/kadaster/brt-achtergrondkaart/wmts/v2_0/grijs/EPSG:3857/{z}/{x}/{y}.png",
            "© Kadaster / PDOK",
            "Netherlands only. Official public background without an API key; provider terms apply.",
            19, True, sample_place=(4.895, 52.37)),
    Basemap("pdok_brt_pastel", "PDOK BRT pastel (Netherlands)",
            "https://service.pdok.nl/kadaster/brt-achtergrondkaart/wmts/v2_0/pastel/EPSG:3857/{z}/{x}/{y}.png",
            "© Kadaster / PDOK",
            "Netherlands only. Official public background without an API key; provider terms apply.",
            19, True, sample_place=(4.895, 52.37)),
    Basemap("pdok_ortho", "PDOK aerial photographs (Netherlands)",
            "https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0/Actueel_ortho25/EPSG:3857/{z}/{x}/{y}.jpeg",
            "© PDOK / Beeldmateriaal Nederland",
            "Netherlands only. Official public background without an API key; provider terms apply.",
            21, True, sample_place=(4.895, 52.37)),
    Basemap("ign_es_map", "IGN national topographic map (Spain)",
            "https://www.ign.es/wmts/mapa-raster?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&LAYER=MTN&"
            "STYLE=default&FORMAT=image/png&TILEMATRIXSET=GoogleMapsCompatible&TILEMATRIX={z}&TILEROW={y}&"
            "TILECOL={x}",
            "© Instituto Geográfico Nacional de España",
            "Spain only. Official public background without an API key; provider terms apply.",
            20, True, sample_place=(-3.704, 40.417)),
    Basemap("ign_es_ortho", "IGN PNOA orthophoto (Spain)",
            "https://www.ign.es/wmts/pnoa-ma?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&"
            "LAYER=OI.OrthoimageCoverage&STYLE=default&FORMAT=image/jpeg&TILEMATRIXSET=GoogleMapsCompatible&"
            "TILEMATRIX={z}&TILEROW={y}&TILECOL={x}",
            "© Instituto Geográfico Nacional de España",
            "Spain only. Official public background without an API key; provider terms apply.",
            20, True, sample_place=(-3.704, 40.417)),
    Basemap("euskadi_map", "GeoEuskadi topographic map (Basque Country)",
            "https://www.geo.euskadi.eus/geoeuskadi/rest/services/U11/WMTS_TOPO/MapServer/WMTS/tile/1.0.0/"
            "U11_WMTS_TOPO/default/GoogleMapsCompatible/{z}/{y}/{x}.png",
            "© Eusko Jaurlaritza / Gobierno Vasco, geoEuskadi",
            "Basque Country only. Official public background without an API key; provider terms apply.",
            18, True, sample_place=(-1.982, 43.319)),
    Basemap("euskadi_ortho", "GeoEuskadi orthophoto (Basque Country)",
            "https://www.geo.euskadi.eus/geoeuskadi/rest/services/U11/WMTS_ORTO/MapServer/WMTS/tile/1.0.0/"
            "U11_WMTS_ORTO/default/GoogleMapsCompatible/{z}/{y}/{x}",
            "© Eusko Jaurlaritza / Gobierno Vasco, geoEuskadi",
            "Basque Country only. Official public background without an API key; provider terms apply.",
            18, True, sample_place=(-1.982, 43.319)),
    Basemap("gsi_map", "GSI standard map (Japan)",
            "https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png",
            "Geospatial Information Authority of Japan (GSI)",
            "Japan only. Official public background without an API key; provider terms apply. Detailed tiles "
            "from zoom 5.",
            18, True, sample_place=(139.767, 35.681)),
    Basemap("gsi_pale", "GSI pale map (Japan)",
            "https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png",
            "Geospatial Information Authority of Japan (GSI)",
            "Japan only. Official public background without an API key; provider terms apply. Detailed tiles "
            "from zoom 5.",
            18, True, sample_place=(139.767, 35.681)),
    Basemap("gsi_ortho", "GSI seamless orthophoto (Japan)",
            "https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg",
            "Geospatial Information Authority of Japan (GSI)",
            "Japan only. Official public background without an API key; provider terms apply.",
            18, True, sample_place=(139.767, 35.681)),
    Basemap("usgs_topo", "USGS The National Map (United States)",
            "https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}",
            "USGS The National Map, U.S. Census Bureau, USFS, Natural Earth and NOAA",
            "United States only. Official public background without an API key; provider terms apply.",
            23, True, sample_place=(-77.037, 38.907)),
    Basemap("geobretagne_ortho", "GéoBretagne orthophoto (Brittany, France)",
            "https://tile.geobretagne.fr/photo/wmts/HR.ORTHOIMAGERY.ORTHOPHOTO/PM/{z}/{x}/{y}.png",
            "© GéoBretagne, IGN and partners",
            "Brittany, France only. Official public background without an API key; provider terms apply.",
            19, True, sample_place=(-1.6778, 48.1173)),
)
BASEMAPS += REGIONAL_BASEMAPS
_BY_URL = {basemap.url: basemap for basemap in BASEMAPS}
_BY_ID = {basemap.id: basemap for basemap in BASEMAPS}


def known(url: str) -> Optional[Basemap]:
    """The basemap of the list served at this template, for its title, its deepest zoom and its attribution."""
    return _BY_URL.get(url)


def access_problem(url: str) -> str:
    """A known key requirement, even when a server disguises it as a successful image response.

    Custom CARTO templates with the user's key stay available. Neither the key nor its URL is returned in errors.
    """
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    carto = host == "basemaps.cartocdn.com" or host.endswith(".basemaps.cartocdn.com")
    if carto and not any(value.strip() for value in parse_qs(parts.query).get("key", [])):
        return "CARTO: " + _CARTO_KEY_NOTE
    return ""


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


def sample_tiles(url: str, place: Optional[Tuple[float, float]] = None, zmax: int = DEFAULT_ZMAX,
                 fallback_place: Optional[Tuple[float, float]] = None) -> Tuple[str, ...]:
    """At most two samples: where the map is, then a known covered point or a quarter of the world.

    A server of one country, or one that starts at a deeper zoom, has no tile for a quarter of the world; a map
    elsewhere has none where it is. A catalogued regional source can be tested without moving the user's map.
    """
    asked = []
    zoom = min(SAMPLE_ZOOM, zmax)
    if place is not None:
        asked.append(tile_url(url, zoom, *tile_at(place[0], place[1], zoom)))
    fallback = (tile_url(url, zoom, *tile_at(fallback_place[0], fallback_place[1], zoom))
                if fallback_place is not None else tile_url(url, 1, 0, 0))
    if fallback not in asked:
        asked.append(fallback)
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
