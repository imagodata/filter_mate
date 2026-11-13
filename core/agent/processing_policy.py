# -*- coding: utf-8 -*-
"""Which Processing algorithms a model may run, and how each of their parameters may be given.

Plain Python: the caller reads the registry of QGIS and passes what it found. The rule is a list of what is
accepted, not of what is refused:

- the algorithms of QGIS itself (``native``, ``qgis``), which run inside QGIS. GDAL, GRASS, SAGA, PDAL and the
  scripts and models of the user start other programs or run code that nobody here has read;
- an algorithm that makes at least one layer, written by FilterMate to a temporary file and added to the project
  (undoing the turn removes it), or one of a few that only answer values (statistics). What acts on the project or
  on a data source in place (selection, style, projection, index, truncation, import into a database, upload,
  download) makes no layer, and is left out by this rule alone;
- only parameters of a type known here: layers of the project, an extent, a point, a CRS, a formula, an option, the
  rows of an interpolation (each a layer of the project), and plain values. Any other type (a file or a folder, a
  database connection, a layout, a map theme, a PROJ operation, which names a grid by path or URL, or a type this
  list does not know) is refused when required and stays unset when optional. An output is a temporary layer;
- the few algorithms that make a layer from code or SQL a model would write, or send data out, are refused by name.
"""
from __future__ import annotations

from typing import Iterable, Optional, Sequence, Tuple

PROVIDERS = ("native", "qgis")
# What makes a layer: FilterMate gives each a temporary file, never a path from the model.
LAYER_DESTINATIONS = frozenset({"sink", "vectorDestination", "rasterDestination", "pointCloudDestination"})
# What writes a file or a folder of the model's choosing: refused when required, left unset when optional.
FILE_DESTINATIONS = frozenset({"fileDestination", "folderDestination", "vectorTileDestination"})
# Parameters that take layers: only layers of the project, by id or name, never a path or a URL.
LAYER_INPUTS = frozenset({"source", "vector", "raster", "layer", "pointcloud", "mesh"})
MULTI_LAYER_INPUTS = frozenset({"multilayer"})
# The inputs of an interpolation (IDW, TIN): rows "source::~::value source::~::field index::~::source type" joined by
# "::|::". QGIS opens each source from its text, a path or a URL included: FilterMate writes each row again, its source
# a vector layer of the project given by its id, the rest integers.
INTERPOLATION_DATA = "idw_interpolation_data"
# Read by FilterMate before QGIS sees them.
CHECKED_TYPES = LAYER_INPUTS | MULTI_LAYER_INPUTS | frozenset({"extent", "point", "crs", "expression", "enum",
                                                               INTERPOLATION_DATA})
# Plain values QGIS takes as they are: numbers, texts, field names, flags, tables of values, colours, dates, ranges,
# a geometry as WKT, the bands or dataset groups of an input. Nothing that names a file, a URL or a layer.
PLAIN_TYPES = frozenset({
    "number", "distance", "area", "volume", "scale", "duration", "band", "field", "string", "boolean", "matrix",
    "color", "datetime", "range", "geometry", "raster_calc_expression", "relief_colors", "meshdatasetgroups",
    "meshdatasettime",
    "attribute", "pointcloudattribute",  # an attribute of a point cloud input, by name
})
# What a model may give; any other parameter is refused when required, left unset when optional.
GIVEN_TYPES = CHECKED_TYPES | PLAIN_TYPES
# Algorithms that only answer values, and make no layer.
VALUE_ALGORITHMS = frozenset({
    "native:basicstatisticsforfields", "qgis:basicstatisticsforfields", "native:rasterlayerstatistics",
    "qgis:rasterlayerstatistics", "native:rasterlayerproperties", "native:rasterlayeruniquevaluesreport",
    "native:listuniquevalues", "qgis:listuniquevalues", "native:rastersurfacevolume",
})
# They make a layer, from SQL or Python written by the model, or from a database or a web server, or send data out.
DENIED = frozenset({
    "qgis:executesql", "native:executesql", "qgis:advancedpythonfieldcalculator",
    "qgis:postgisexecuteandloadsql", "native:postgisexecuteandloadsql",
    "native:httprequest", "native:filedownloader", "native:downloadvectortiles",
    "native:batchnominatimgeocoder",  # sends the addresses of a layer to the Nominatim server of OpenStreetMap
    "native:openurl",  # hands a URL or a file to the system (it makes no layer, refused by name all the same)
    "native:zonalstatistics",  # "in place": it adds fields to the source of its input
    # A layer of the sources of the layers given: the paths of this machine, the hosts and users of its databases,
    # which the model would then read (audit of 12/11/2026)
    "native:exportlayersinformation",
})

Parameter = Tuple[str, str, bool]  # name, type, optional


def refusal(algorithm_id: str, provider_id: str, parameters: Sequence[Parameter], deprecated: bool = False) -> str:
    """Why a model may not run this algorithm; "" when it may."""
    if provider_id not in PROVIDERS:
        return (f"only the algorithms of QGIS itself (providers {', '.join(PROVIDERS)}) can be run, not those of "
                f"'{provider_id}'")
    if algorithm_id in DENIED:
        return "it runs code, SQL or a network request written by the model"
    if deprecated:
        return "it is deprecated in this version of QGIS"
    forbidden = sorted({kind for _, kind, optional in parameters if not optional and kind not in GIVEN_TYPES
                        and kind not in LAYER_DESTINATIONS and kind not in FILE_DESTINATIONS})
    if forbidden:
        return f"it needs {', '.join(forbidden)} parameters, which are not given by a model"
    files = sorted({kind for _, kind, optional in parameters if kind in FILE_DESTINATIONS and not optional})
    if files:
        return "it writes a file or a folder of its own; only layers can be made"
    if not any(kind in LAYER_DESTINATIONS for _, kind, _ in parameters) and algorithm_id not in VALUE_ALGORITHMS:
        return "it makes no layer: it acts on the project or on a data source in place"
    return ""


def matches(query: str, texts: Iterable[Optional[str]]) -> bool:
    """Every word of ``query`` is in one of ``texts``, case and accents aside (a plain lower case here)."""
    haystack = " ".join(text for text in texts if text).casefold()
    return all(word in haystack for word in query.casefold().split())
