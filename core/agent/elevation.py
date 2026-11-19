# -*- coding: utf-8 -*-
"""Elevation the agent can bring in: the tiles of a worldwide model, which ones cover an area, on which grid.

Pure, no QGIS, no network. An elevation model is served as one GeoTIFF per square degree; only the part an area
needs is read from each (the files are read by parts), warped on a grid in metres and written as one local file.
A model names a source of the list, and an area: it never writes an address.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

# What one call may cost: the squares of one degree read, and the pixels written (float32: 4 bytes each).
MAX_TILES = 16
MAX_PIXELS = 16_000_000
MIN_RESOLUTION = 10.0
MAX_RESOLUTION = 5000.0
# What a contour run may read and make.
MAX_CONTOUR_PIXELS = 25_000_000
MAX_LEVELS = 500
_METRES_PER_DEGREE = 111_320.0
# The methods of projection (the PROJ name QGIS gives: ``QgsCoordinateReferenceSystem.operation().id()``) that keep the
# angles, so that a slope read on the grid is the slope of the ground, to the scale of the projection (near 1 where the
# CRS is made for): transverse Mercator and UTM, Lambert conformal conic, stereographic (polar, oblique), the Swiss
# oblique Mercator, the Krovak of the Czech national grid, Hotine oblique Mercator (Malaysia), Laborde (Madagascar) and
# the New Zealand map grid. (UPS is named stere by PROJ; no CRS probed was named lcca.) Not Mercator, Web Mercator
# included (its scale grows as 1 / cos(latitude)), nor an equal-area, equidistant or compromise projection (Equal Earth, Plate Carree, Mollweide,
# Lambert azimuthal equal area): their scale differs along the two axes, or from one place to the next.
CONFORMAL_METHODS = frozenset(("utm", "tmerc", "etmerc", "lcc", "stere", "sterea", "somerc", "krovak", "omerc", "labrd",
                               "nzmg"))


@dataclass(frozen=True)
class ElevationSource:
    """One elevation model of the list: where its tiles are, their grid, and what must be said of it."""

    id: str
    title: str
    base: str
    resolution: float  # metres, the finest worth asking for
    attribution: str
    note: str
    official: bool = False


# Checked to serve its tiles without an account, by parts, when it was added (2026-11-14): 43 MB for N45 E004.
SOURCES: Tuple[ElevationSource, ...] = (
    ElevationSource(
        "copernicus_dem", "Copernicus DEM (elevation, 30 m)", "https://copernicus-dem-30m.s3.amazonaws.com", 30.0,
        "© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by the "
        "European Union and ESA; all rights reserved",
        "Worldwide elevation at 30 m (Copernicus GLO-30), free, on AWS. A surface model: buildings and trees are in "
        "it"),
)
_BY_ID = {source.id: source for source in SOURCES}


def known(identifier: str) -> Optional[ElevationSource]:
    """The source of the list a model named."""
    return _BY_ID.get((identifier or "").strip().lower())


def tile_name(latitude: int, longitude: int) -> str:
    """The name of the Copernicus GLO-30 tile whose south-west corner is at these whole degrees."""
    north = f"{'N' if latitude >= 0 else 'S'}{abs(latitude):02d}_00"
    east = f"{'E' if longitude >= 0 else 'W'}{abs(longitude):03d}_00"
    return f"Copernicus_DSM_COG_10_{north}_{east}_DEM"


def tile_url(source: ElevationSource, latitude: int, longitude: int) -> str:
    name = tile_name(latitude, longitude)
    return f"{source.base}/{name}/{name}.tif"


def bbox_problem(bbox: Sequence[float]) -> str:
    """Why these are no bounds in degrees; "" when they are: west, south, east, north."""
    if len(bbox) != 4 or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in bbox):
        return "the area cannot be read"
    west, south, east, north = bbox
    if not (-180.0 <= west < east <= 180.0 and -90.0 <= south < north <= 90.0):
        return "the area is not on the globe: west, south, east, north in degrees"
    return ""


def tiles_for(bbox: Sequence[float]) -> List[Tuple[int, int]]:
    """The south-west corners (latitude, longitude) of the squares of one degree an area touches.

    Raises:
        ValueError: Bounds that are none, or an area of more squares than one call reads.
    """
    problem = bbox_problem(bbox)
    if problem:
        raise ValueError(problem)
    west, south, east, north = bbox
    # An edge that falls on a whole degree belongs to the square before it: 5.0 east needs no tile of E005.
    rows = range(math.floor(south), max(math.ceil(north), math.floor(south) + 1))
    columns = range(math.floor(west), max(math.ceil(east), math.floor(west) + 1))
    if len(rows) * len(columns) > MAX_TILES:
        raise ValueError(f"this area spans {len(rows) * len(columns)} squares of one degree, {MAX_TILES} at most: "
                         "ask for a smaller area")
    return [(latitude, longitude) for latitude in rows for longitude in columns]


def tiles_for_grid(bbox: Sequence[float], envelope: Sequence[float]) -> List[Tuple[int, int]]:
    """The squares to read for a grid written in a metric CRS: those of the area asked, and those its corners reach.

    ``envelope`` is the bounds of the grid, in degrees: wider than ``bbox`` because a rectangle of a UTM zone or of a
    national grid is not one in longitude and latitude. A corner that falls in a square nobody read would be written
    empty (2026-11-18: [4.5, 45, 5, 45.5] in UTM 31N left 2.5 % of the grid at 0 m, along its south edge). When
    these squares are more than one call reads, those of the area asked are read, and the corners stay empty.

    Raises:
        ValueError: Bounds that are none, or an area of more squares than one call reads.
    """
    asked = tiles_for(bbox)
    west, south, east, north = envelope
    wider = [max(west, -180.0), max(south, -90.0), min(east, 180.0), min(north, 90.0)]
    try:
        return sorted(set(asked) | set(tiles_for(wider)))
    except ValueError:
        return asked


def utm_authid(longitude: float, latitude: float) -> str:
    """The UTM zone of a place, as an EPSG code: metres, and little distortion over a town or a region."""
    zone = int(math.floor((max(-180.0, min(179.999, longitude)) + 180.0) / 6.0)) + 1
    return f"EPSG:{(32600 if latitude >= 0 else 32700) + zone}"


_GDAL_AUTHORITIES = re.compile(r"(?:EPSG|ESRI|IGNF):[A-Za-z0-9_.]+", re.IGNORECASE)


def gdal_srs(authid: str, wkt: Callable[[], str]) -> str:
    """The text that names a CRS to GDAL: its authid when GDAL has that authority (EPSG, ESRI, IGNF), its WKT otherwise.

    A CRS the user defined has an authid of QGIS alone (``USER:100000``), which GDAL does not know: it refused it, and
    the elevation was said not to be readable from its server. ``wkt`` is called only then.
    """
    authid = (authid or "").strip()
    return authid if _GDAL_AUTHORITIES.fullmatch(authid) else wkt()


def metric_grid(method: str, projected: bool, metres: bool) -> bool:
    """Whether elevation is warped on the CRS of the project: one in metres whose projection keeps the angles.

    ``method``: its projection as PROJ names it ("utm", "lcc"; "" when QGIS does not say). Not Web Mercator: its metres
    are those of the equator (1.43 times too long at 45 degrees), nor Equal Earth, Plate Carree, Mollweide or an
    equal-area projection, whose metres differ along the two axes: they flatten or steepen every slope computed from
    the grid (``CONFORMAL_METHODS``).
    """
    return bool(projected and metres and (method or "").strip().lower() in CONFORMAL_METHODS)


def ground_size(bbox: Sequence[float]) -> Tuple[float, float]:
    """Width and height of an area in metres, on the ground, at its middle latitude."""
    west, south, east, north = bbox
    middle = math.radians((south + north) / 2.0)
    return ((east - west) * _METRES_PER_DEGREE * max(math.cos(middle), 0.01), (north - south) * _METRES_PER_DEGREE)


def resolution_for(bbox: Sequence[float], asked: Optional[float], finest: float) -> Tuple[float, str]:
    """The pixel size, in metres, an area is written at, and what to say when it is not the one of the source.

    Not asked: the finest of the source, or the first multiple of it that keeps the grid under ``MAX_PIXELS``.

    Raises:
        ValueError: A size out of range, or one asked that makes too large a grid (the message gives one that fits).
    """
    width, height = ground_size(bbox)
    needed = math.sqrt(width * height / MAX_PIXELS)
    fitting = finest * max(1, math.ceil(needed / finest))
    if asked is None:
        note = "" if fitting <= finest else (f"the area is large: written at {fitting:g} m rather than {finest:g} m; "
                                             "ask for a smaller area for the full detail")
        return fitting, note
    if not math.isfinite(asked) or not MIN_RESOLUTION <= asked <= MAX_RESOLUTION:
        raise ValueError(f"resolution goes from {MIN_RESOLUTION:g} to {MAX_RESOLUTION:g} metres")
    if asked < needed:
        raise ValueError(f"at {asked:g} m this area makes a grid of more than {MAX_PIXELS // 1_000_000} million "
                         f"pixels: ask for {fitting:g} m or more, or for a smaller area")
    note = "" if asked >= finest else f"the source measures every {finest:g} m: a finer grid adds no detail"
    return float(asked), note


NO_DATA = -9999.0  # what the grid holds where no tile of the model reaches: written as its no-data value


def empty_note(empty: int, pixels: int, why: str) -> str:
    """What a model must know when part of a grid holds no elevation: said by its share, and left out of the figures
    (minimum, maximum, mean) and of every slope, shade or contour drawn from it. "" when nothing is empty."""
    if empty <= 0 or pixels <= 0:
        return ""
    share = 100.0 * empty / pixels
    shown = f"{share:.0f} %" if share >= 1 else "under 1 %"
    return f"{shown} of the grid is empty (no data), left out of minimum, maximum and mean: the model {why}"


def contour_problem(minimum: float, maximum: float, interval: float, index_interval: Optional[float],
                    tell_heights: bool = True) -> str:
    """Why contours cannot be drawn with these intervals over this range of elevations; "" when they can.

    ``tell_heights`` False: the message names no height of the raster, nor an interval computed from them (the
    values of a layer of the user are not sent when they said so).
    """
    if not math.isfinite(interval) or interval <= 0:
        return "interval is a height above zero, in the units of the raster (25 for a contour every 25 m)"
    if math.isfinite(minimum) and math.isfinite(maximum) and (maximum - minimum) / interval > MAX_LEVELS:
        if not tell_heights:
            return (f"an interval of {interval:g} makes more than {MAX_LEVELS} levels over the heights of this "
                    "raster: ask for a larger one")
        fitting = _round_up((maximum - minimum) / MAX_LEVELS)
        return (f"an interval of {interval:g} makes more than {MAX_LEVELS} levels between {minimum:g} and "
                f"{maximum:g}: ask for {fitting:g} or more")
    if index_interval is not None:
        if not math.isfinite(index_interval) or index_interval <= 0:
            return "index_interval is a height above zero (100 for an index contour every 100 m)"
        ratio = index_interval / interval
        if abs(ratio - round(ratio)) > 1e-6 or round(ratio) < 2:
            return (f"index_interval ({index_interval:g}) is a multiple of interval ({interval:g}): every fourth or "
                    "fifth contour is usual")
    return ""


def _round_up(value: float) -> float:
    """``value`` rounded up to 1, 2, 2.5 or 5 times a power of ten: an interval people read."""
    if value <= 0:
        return 1.0
    power = 10.0 ** math.floor(math.log10(value))
    for step in (1.0, 2.0, 2.5, 5.0, 10.0):
        if value <= step * power:
            return step * power
    return 10.0 * power


def is_index(elevation: float, index_interval: float) -> bool:
    """Whether a contour at ``elevation`` is an index contour: a whole number of times ``index_interval``."""
    ratio = elevation / index_interval
    return abs(ratio - round(ratio)) < 1e-6


# An address: any scheme, with the /vsi... prefixes GDAL reads it through.
_ADDRESS = re.compile(r"(?:/vsi[a-z0-9_]+/)*[a-z][a-z0-9+.-]*://[^\s'\"`<>]+", re.IGNORECASE)
# One key=value of a connection: the value is quoted, or runs to the next space.
_PAIR = r"""[A-Za-z_]+\s*=\s*(?:'(?:[^'\\]|\\.)*'|"[^"]*"|\S+)"""
# A database connection (GDAL "PG:dbname=... password=..."): its host, its user and its password are not for a model.
_CONNECTION = re.compile(rf"\b(?:PG|MSSQL|MYSQL|OCI|ODBC)\s*:\s*(?:{_PAIR}\s*)+", re.IGNORECASE)
# What names an account, wherever it is written (a connection string of QGIS, the message of a driver). Not the
# words that are tags of OpenStreetMap too (service=driveway).
_SECRET = re.compile(r"\b(?:host|hostaddr|dbname|user|username|password|passwd|pwd|authcfg|token|"
                     r"apikey|api_key|secret|sslkey|sslcert)\s*=\s*(?:'(?:[^'\\]|\\.)*'|\"[^\"]*\"|\S+)", re.IGNORECASE)
# A path of this machine or of a store (a drive, a share, a root, ~, .. : C:\Users\..., /vsis3/bucket/..., after a
# colon too: GPKG:C:\...\a.gpkg:roads). A folder may hold spaces (the name of a person, of a client) and a message does
# not say where the path ends: it ends after the first part that has an extension (the file), else at a colon or a
# quote. Only that last part is kept: the folders hold the name of the user and of their clients.
_STOP = r"""[^\\/:'"`<>|*?\r\n]"""
_FILE = rf"""{_STOP}*?\.[A-Za-z][A-Za-z0-9]{{0,4}}(?=[\s,;:'"`)\]>]|$)"""
_PATH = re.compile(rf"""(?:(?<![A-Za-z0-9_])[A-Za-z]:[\\/]|(?<![\w.\\/~-])(?:\\\\|/(?=[^\s\\/:])|~[\\/]|\.{{1,2}}[\\/]))"""
                   rf"""(?:(?:{_STOP}*[\\/])*?{_FILE}|[^:'"`<>|*?\r\n]*)""")
# A name with folders between quotes (GDAL quotes what it opens): 'Clients ACME/x.tif'.
_QUOTED = re.compile(rf"""(['"`])[^'"`\r\n]*[\\/]({_STOP}*?\.[A-Za-z][A-Za-z0-9]{{0,4}})(?=['"`])""")
# A relative path whose first part has no space (Projet/Client ACME.qgz, data/sub/x.tif); "read/write" is none: its
# last part has no extension.
_RELATIVE = re.compile(rf"""(?<![\w.:\\/~-])[^\s'"`<>:|*?\\/]+[\\/](?:{_STOP}*[\\/])*?({_FILE})""")
MAX_MESSAGE = 300


def _last_part(found: "re.Match[str]") -> str:
    return re.split(r"[\\/]", found.group(0))[-1]


def quiet_message(text: str) -> str:
    """What a library said of a failure, in one short line a model may read: no address (it may hold the key of an
    account, or be the source of a layer of the user), no connection to a database, and of a path only the name of
    its file: the folders hold the name of the user and of their clients."""
    text = _ADDRESS.sub("its address", text or "")
    text = _CONNECTION.sub("a database connection ", text)
    text = _SECRET.sub("", text)
    text = _QUOTED.sub(lambda found: found.group(0)[0] + found.group(2), text)
    text = _PATH.sub(_last_part, text)
    text = _RELATIVE.sub(lambda found: found.group(1), text)
    return " ".join(text.split())[:MAX_MESSAGE] or "no reason given"
