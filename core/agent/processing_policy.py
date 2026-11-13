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
- the few algorithms that make a layer from code or SQL a model would write, or send data out, are refused by name;
- a parameter that would write the sources of the layers in the output is set by FilterMate, never by the model.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

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
_CODE = "it runs code or SQL written by the model"
_NETWORK = "it sends a request out of this machine, to an address or with data the model chose"
_SOURCES = ("it writes the source of each layer (a path of this machine, the host and the user of a database) in a "
            "layer the model would then read")
# Refused by name, each with what it does: they make a layer from SQL or Python written by the model, or from a
# database or a web server, or send data out.
DENIED: Dict[str, str] = {
    "qgis:executesql": _CODE, "native:executesql": _CODE, "qgis:advancedpythonfieldcalculator": _CODE,
    "qgis:postgisexecuteandloadsql": _CODE, "native:postgisexecuteandloadsql": _CODE,
    "native:httprequest": _NETWORK, "native:filedownloader": _NETWORK, "native:downloadvectortiles": _NETWORK,
    "native:batchnominatimgeocoder": _NETWORK,  # the addresses of a layer, to the Nominatim server of OpenStreetMap
    # It makes no layer, refused by name all the same.
    "native:openurl": "it hands a URL or a file to the system",
    "native:zonalstatistics": "it adds fields to the source of its input, in place",
    "native:exportlayersinformation": _SOURCES,  # audit of 12/11/2026
}
# Set by FilterMate whatever the model gives, and not offered to it. An algorithm is refused where QGIS has no such
# parameter. native:mergevectorlayers adds "layer" and "path" (the source of each layer) to its output unless
# ADD_SOURCE_FIELDS is off (seen in QGIS 3.44 on 13/11/2026; older versions always add them).
FORCED: Dict[str, Dict[str, Any]] = {
    "native:mergevectorlayers": {"ADD_SOURCE_FIELDS": False},
}

Parameter = Tuple[str, str, bool]  # name, type, optional


def refusal(algorithm_id: str, provider_id: str, parameters: Sequence[Parameter], deprecated: bool = False) -> str:
    """Why a model may not run this algorithm; "" when it may."""
    if provider_id not in PROVIDERS:
        return (f"only the algorithms of QGIS itself (providers {', '.join(PROVIDERS)}) can be run, not those of "
                f"'{provider_id}'")
    if algorithm_id in DENIED:
        return DENIED[algorithm_id]
    if any(name not in {given for given, _, _ in parameters} for name in forced_values(algorithm_id)):
        return f"in this version of QGIS {_SOURCES}"
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


def forced_values(algorithm_id: str) -> Dict[str, Any]:
    """The parameters of ``algorithm_id`` FilterMate sets itself, with their values; {} for most algorithms."""
    return dict(FORCED.get(algorithm_id, {}))


def matches(query: str, texts: Iterable[Optional[str]]) -> bool:
    """Every word of ``query`` is in one of ``texts``, case and accents aside (a plain lower case here)."""
    haystack = " ".join(text for text in texts if text).casefold()
    return all(word in haystack for word in query.casefold().split())
