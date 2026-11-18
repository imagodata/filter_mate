# -*- coding: utf-8 -*-
"""Population grids the agent can bring in: where they are, the grid an area is read on, and what is said of them.

Pure, no QGIS, no network. A grid of people per pixel is summed, never averaged: a pixel of 1 km holds the people of
the 30 m pixels inside it. So a grid is read on the grid of its source (longitude and latitude, whole pixels) and
made coarser by whole blocks of pixels, which keeps every total exact; it is not warped to metres, which would cut
pixels at the edges and lose or add people (2026-11-15, Lyon at 1 km: 3 % lost in GDAL 3.12, 8 % in GDAL 3.4).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple
from xml.etree import ElementTree

from .osm import area_km2

MAX_AREA_KM2 = 50_000.0  # a large department or a small region: every pixel of the source is read, about 1 s for 1,000 km2
MAX_PIXELS = 16_000_000  # what is written, at the resolution asked
DEFAULT_RESOLUTION = 100.0  # metres: a block of 3 x 3 pixels of the source, the scale of a street
_METRES_PER_DEGREE = 111_320.0


@dataclass(frozen=True)
class PopulationSource:
    """A population grid of the list: where it is, its grid, and what the user should know before ticking it."""

    id: str
    title: str
    base: str
    path: str
    origin: Tuple[float, float]  # longitude, latitude of the top left corner of its grid
    step: float  # degrees per pixel
    attribution: str
    note: str
    official: bool = False


# Checked to be read by parts without an account (2026-11-15): one VRT of 110 KB over cloud optimized GeoTIFFs,
# worldwide, France included; the people of Lyon in 1.7 s, of Pune in 1.7 s, of the Gironde in 10 s.
SOURCES: Tuple[PopulationSource, ...] = (
    PopulationSource(
        "meta_population", "Population (Meta High Resolution Settlement Layer, 30 m)",
        "https://dataforgood-fb-data.s3.amazonaws.com", "hrsl-cogs/hrsl_general/hrsl_general-latest.vrt",
        (-180.00041666666667, 71.330694444444433), 2.7777777777800118e-04,
        "Data for Good at Meta and CIESIN, High Resolution Settlement Layer (CC BY 4.0)",
        "People per pixel of 30 m, estimated from a census and the buildings seen on satellite images (2015 to 2020 "
        "by country). Most of the world, not every country (China, Russia, Iran are left out). Free, on AWS"),
)
_BY_ID = {source.id: source for source in SOURCES}


def known(identifier: str) -> Optional[PopulationSource]:
    """The source of the list a model named."""
    return _BY_ID.get((identifier or "").strip().lower())


def grid_url(source: PopulationSource) -> str:
    return f"{source.base}/{source.path}"


def area_problem(bbox: Sequence[float]) -> str:
    """Why this area is too large to read a population grid for; "" when it is not."""
    surface = area_km2(bbox)
    if surface > MAX_AREA_KM2:
        return (f"this area covers {surface:,.0f} km2, {MAX_AREA_KM2:,.0f} at most: ask for a smaller one (a "
                "department, a city)")
    return ""


def pixel_metres(source: PopulationSource, factor: int, latitude: float) -> Tuple[float, float]:
    """The size on the ground, in metres (width, height), of a pixel of ``factor`` x ``factor`` pixels of the source
    at ``latitude``."""
    height = source.step * factor * _METRES_PER_DEGREE
    return height * max(math.cos(math.radians(latitude)), 0.01), height


def snapped(source: PopulationSource, bbox: Sequence[float], factor: int) -> Tuple[float, float, float, float]:
    """``[west, south, east, north]`` grown to whole pixels of ``factor`` x ``factor`` pixels of the source grid."""
    west, south, east, north = bbox
    left, top = source.origin
    size = source.step * factor
    return (left + math.floor((west - left) / size) * size, top - math.ceil((top - south) / size) * size,
            left + math.ceil((east - left) / size) * size, top - math.floor((top - north) / size) * size)


def grid_for(source: PopulationSource, bbox: Sequence[float],
             resolution: Optional[float]) -> Tuple[int, Tuple[float, float, float, float], int, int, str]:
    """``(factor, bounds, width, height, note)``: the blocks of pixels of the source one pixel written holds, the
    bounds on that grid, its size, and why it is coarser than asked ("" when it is not).

    ``resolution``: metres on the ground, north to south (the default: a street); the finest is the source's.

    Raises:
        ValueError: A resolution that is not a size.
    """
    if resolution is not None and (isinstance(resolution, bool) or not isinstance(resolution, (int, float))
                                   or not math.isfinite(resolution) or resolution <= 0):
        raise ValueError("resolution is a size in metres")
    native = source.step * _METRES_PER_DEGREE
    factor = max(1, int(round((resolution or DEFAULT_RESOLUTION) / native)))
    asked = factor
    while True:
        bounds = snapped(source, bbox, factor)
        size = source.step * factor
        width = max(1, int(round((bounds[2] - bounds[0]) / size)))
        height = max(1, int(round((bounds[3] - bounds[1]) / size)))
        if width * height <= MAX_PIXELS:
            break
        factor = max(factor + 1, int(math.ceil(factor * math.sqrt(width * height / MAX_PIXELS))))
    note = ""
    if factor != asked:
        note = (f"written with pixels of about {factor * native:,.0f} m, coarser than asked: the area is large "
                "for that resolution")
    return factor, bounds, width, height, note


EXCESS = 1.1  # a layer that covers more than this many times the area asked says so


def native_pixels(source: PopulationSource, bbox: Sequence[float]) -> int:
    """How many pixels of the source ``bbox`` covers, on the grid of the source (whole pixels)."""
    west, south, east, north = snapped(source, bbox, 1)
    return max(1, int(round((east - west) / source.step))) * max(1, int(round((north - south) / source.step)))


def exact_total_fits(source: PopulationSource, bbox: Sequence[float]) -> bool:
    """Whether the people of ``bbox`` can be summed on the pixels of the source, within the pixels one call may read
    (``MAX_PIXELS``)."""
    return native_pixels(source, bbox) <= MAX_PIXELS


def extent_note(source: PopulationSource, bbox: Sequence[float], written: Sequence[float], factor: int,
                counted: Optional[Sequence[float]]) -> str:
    """What a model must know about the surface a total covers; "" when it is no wider than the area asked.

    A pixel written is a block of ``factor`` x ``factor`` pixels of the source, on the grid of the source: the layer
    reaches to the blocks around the area, up to 40 times its surface at 10 km (2026-11-18, a district of 3.5 km2:
    1.1 times at 100 m, 2.4 at 1 km, 40 at 10 km). ``counted``: the bounds the total was summed on, on the pixels of
    the source whatever the resolution (the whole pixels the area touches); None when it is the sum of the layer.
    """
    asked, covered = area_km2(bbox), area_km2(written)
    size = f"about {factor * source.step * _METRES_PER_DEGREE:,.0f} m"
    if counted is None:
        if covered <= asked * EXCESS:
            return ""
        return (f"total is the sum of the whole layer, {covered:,.2f} km2 against the {asked:,.2f} km2 asked "
                f"({covered / asked:,.1f} times): its pixels are blocks of {size}, so it counts the people of that "
                "larger rectangle, not of the area asked")
    summed = area_km2(counted)
    if covered <= asked * EXCESS and summed <= asked * EXCESS:
        return ""
    notes = [f"total counts the whole pixels of the source (30 m) that the area touches, {summed:,.2f} km2 for the "
             f"{asked:,.2f} km2 asked, whatever the resolution"]
    if covered > summed * EXCESS:
        notes.append(f"the pixels of the layer are blocks of {size} and cover {covered:,.2f} km2, so the sum of the "
                     "layer is larger than total")
    return "; ".join(notes)


_FILE = re.compile(r'[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*\.tif')
NOT_COVERED = ("the population grid does not cover this area: it leaves out some countries (among them China, Russia "
               "and Iran)")
_REFUSED = "the population grid sent by its server names a file that is not its own: refused"
_UNREADABLE = "the population grid sent by its server cannot be read as one"
# What a VRT that only lists GeoTIFFs holds (measured on the real one, 2026-11-18: 13 kinds of element). GDAL reads
# the names of elements and attributes without regard to case, and a VRT can name files in more places than its
# sources (a warped or derived band): anything else is refused rather than looked through for a file.
_ELEMENTS = frozenset((
    "VRTDataset", "SRS", "GeoTransform", "VRTRasterBand", "NoDataValue", "ColorInterp", "ComplexSource", "SimpleSource",
    "SourceFilename", "SourceBand", "SourceProperties", "SrcRect", "DstRect", "NODATA", "Metadata", "MDI",
    "Description", "Offset", "Scale", "UnitType"))
_SOURCES = ("ComplexSource", "SimpleSource")


@dataclass(frozen=True)
class VerifiedVrt:
    """A VRT checked to list GeoTIFFs of its own folder, and written so that nothing else can be read from it."""

    text: str  # its sources named by their whole address: it is read from memory, no longer from its server
    rects: Tuple[Tuple[int, int, int, int], ...]  # the pixels each file fills, ``(column, row, width, height)``


def verify_vrt(vrt_xml: str, folder: str) -> VerifiedVrt:
    """Parse a VRT and keep only what is known to be safe: the files it names are GeoTIFFs of its own folder.

    The text is parsed, not searched: GDAL reads an attribute or an element whatever the case of its name, and
    accepts files that a pattern over the text does not see (``relativetoVRT="0"``, ``shared="0"``). Every element
    must be of the kinds a list of GeoTIFFs holds, each source names one file relative to the VRT with a name made of
    letters, digits and ``_.-`` between slashes, and the text returned names them by ``folder`` (the address of its
    folder) so that the VRT read is the VRT checked, not a second reading of the server.

    Args:
        vrt_xml: The text of the VRT as its server sent it.
        folder: The address of the folder that holds it, without a trailing slash, as GDAL opens it
            (``/vsicurl/https://...``); the files are read from there.

    Raises:
        ValueError: A VRT that cannot be read as a list of GeoTIFFs, or that names a file elsewhere than beside it (a
            path of this machine, a parent folder, an address, a file that is no GeoTIFF).
    """
    if re.search(r"<!\s*(DOCTYPE|ENTITY)", vrt_xml, re.IGNORECASE):  # entities: a text that grows when it is parsed
        raise ValueError(_UNREADABLE)
    try:
        root = ElementTree.fromstring(vrt_xml)
    except ElementTree.ParseError:
        raise ValueError(_UNREADABLE) from None
    if root.tag != "VRTDataset" or len(root.findall("GeoTransform")) != 1:
        raise ValueError(_UNREADABLE)
    for element in root.iter():
        if not isinstance(element.tag, str) or element.tag not in _ELEMENTS:
            raise ValueError(_REFUSED)
        if any(key.lower() == "subclass" for key in element.attrib):  # a warped or derived dataset or band
            raise ValueError(_REFUSED)
    names = [element for element in root.iter("SourceFilename")]
    sources = [element for tag in _SOURCES for element in root.iter(tag)]
    rects = []
    for source in sources:
        files, rectangles = source.findall("SourceFilename"), source.findall("DstRect")
        if len(files) != 1 or len(rectangles) != 1:
            raise ValueError(_UNREADABLE)
        named, rectangle = files[0], rectangles[0]
        name = named.text or ""
        if (named.attrib.get("relativeToVRT") != "1" or set(named.attrib) - {"relativeToVRT", "shared"}
                or named.attrib.get("shared", "0") not in ("0", "1") or len(named) or not _FILE.fullmatch(name)
                or ".." in name.split("/") or "." in name.split("/")):
            raise ValueError(_REFUSED)
        try:
            rects.append(tuple(int(rectangle.attrib[key]) for key in ("xOff", "yOff", "xSize", "ySize")))
        except (KeyError, ValueError):
            raise ValueError(_UNREADABLE) from None
        named.attrib.clear()
        named.set("relativeToVRT", "0")
        named.text = f"{folder}/{name}"
    if not rects or len(names) != len(sources):  # a SourceFilename out of a source is a file nothing here counted
        raise ValueError(_UNREADABLE)
    return VerifiedVrt(ElementTree.tostring(root, encoding="unicode"), tuple(rects))


def covered_rects(vrt_xml: str) -> List[Tuple[int, int, int, int]]:
    """The pixels of the grid its files fill, ``(column, row, width, height)``, from the text of its VRT.

    Raises:
        ValueError: A VRT that names a file elsewhere than beside it, or that cannot be read (see ``verify_vrt``).
    """
    return list(verify_vrt(vrt_xml, ".").rects)


_GEOTRANSFORM = re.compile(r"<GeoTransform>([^<]*)</GeoTransform>")
MAX_VRT_BYTES = 4 * 1024 * 1024  # 110 KB measured on 2026-11-15


def vrt_geotransform(vrt_xml: str) -> Tuple[float, float, float, float, float, float]:
    """The geotransform a VRT writes: its top left corner and the size of its pixels.

    Raises:
        ValueError: A VRT without one.
    """
    found = _GEOTRANSFORM.search(vrt_xml)
    try:
        values = tuple(float(value) for value in found.group(1).split(",")) if found else ()
    except ValueError:
        values = ()
    if len(values) != 6 or not all(math.isfinite(value) for value in values):
        raise ValueError("the population grid sent by its server cannot be read as one")
    return values


def on_the_grid(source: PopulationSource, left: float, top: float, step: float, minus: float) -> bool:
    """Whether a raster of top left corner (``left``, ``top``) and pixels of ``step`` x ``minus`` degrees has the
    pixels of ``source``: the same size, and its corner on a corner of a pixel of it."""
    if abs(step - source.step) > 1e-12 or abs(minus + source.step) > 1e-12:
        return False
    columns = (left - source.origin[0]) / source.step
    rows = (source.origin[1] - top) / source.step
    return abs(columns - round(columns)) < 1e-3 and abs(rows - round(rows)) < 1e-3


def covered_share(rects: Sequence[Tuple[int, int, int, int]], origin: Tuple[float, float], step: float,
                  bounds: Sequence[float], samples: int = 64) -> float:
    """The share, 0 to 1, of ``bounds`` (degrees) that the files of a VRT fill, their rectangles counted in pixels
    of ``step`` from ``origin``, its top left corner: tested on ``samples`` x ``samples`` points."""
    west, south, east, north = bounds
    left, top = origin
    inside = 0
    for row in range(samples):
        latitude = north - (row + 0.5) * (north - south) / samples
        y = (top - latitude) / step
        for column in range(samples):
            longitude = west + (column + 0.5) * (east - west) / samples
            x = (longitude - left) / step
            if any(x0 <= x < x0 + width and y0 <= y < y0 + height for x0, y0, width, height in rects):
                inside += 1
    return inside / float(samples * samples)


def resolution_label(source: PopulationSource, factor: int, latitude: float) -> str:
    """The size of a pixel written, as a model reads it: "about 90 x 65 m"."""
    width, height = pixel_metres(source, factor, latitude)
    return f"about {width:,.0f} x {height:,.0f} m"
