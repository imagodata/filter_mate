# -*- coding: utf-8 -*-
"""The number of features a vector layer shows: exact, or not told.

``featureCount()`` of an OGR GeoPackage layer can leave its subset out. QGIS
estimates the count of a GeoPackage table itself rather than asking GDAL
(``QgsOgrLayer::GetApproxFeatureCount``):

* without a ``gpkg_ogr_contents`` table (files not written by GDAL, the BD
  TOPO of the IGN), ``COUNT(*)`` of the whole table up to 100 000 rows, then
  ``MAX(fid) - MIN(fid) + 1`` (the filter is taken into account from GDAL
  3.13 only, and never past 100 000 rows);
* with it, from QGIS 3.26, the number it holds when it is 100 000 or more.

A filtered commune layer of 7 features then answers 930, its whole table.
A filtered GeoPackage layer is counted here by reading it as QGIS does: GDAL,
read only, the subset as attribute filter, every field and the geometry
ignored, one feature after the other. The count is what the reading gives
(``LIMIT``, ``GROUP BY``, the table aliased ``m``), on the calling thread; the
clock is looked at every ``CLOCK_EVERY`` features, and past the budget there
is no number rather than the number of the whole table.

Not bounded by the budget: opening the file, and the wait for the first
feature (a selective filter on a big table goes through it all before the
first one). A file locked by another connection is not waited for
(``SQLITE_BUSY_TIMEOUT`` 0 for this thread; GDAL 3.2 has no such setting and
waits 5 s, as for QGIS): no number. A layer without a
subset keeps ``featureCount()``: on a table of 100 000 features or more
without ``gpkg_ogr_contents`` that is ``MAX(fid) - MIN(fid) + 1``, more than
the features when fids have holes. A subset QGIS may run as a query of its
own (starting with SELECT or WITH), made of several queries (UNION,
INTERSECT, EXCEPT: what it reads depends on the columns asked) or drawn at
random (``random()``: another answer at each reading) has no number.
"""
import logging
import os
import re
import time
from collections import OrderedDict
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

COUNT_BUDGET = 1.0  # seconds of the calling thread one count may take
CLOCK_EVERY = 64  # features read between two looks at the clock (every feature costs no more: measured)
CACHE_SIZE = 64
_CACHE: 'OrderedDict[tuple, int]' = OrderedDict()
_clock = time.monotonic
_QUERY = re.compile(r'\s*(SELECT|WITH)\b', re.IGNORECASE)
# Several queries (what they read depends on the columns asked), or a different answer at each reading.
_NO_NUMBER = re.compile(r'\b(UNION|INTERSECT|EXCEPT)\b|\bRANDOM(BLOB)?\s*\(', re.IGNORECASE)


def exact_feature_count(layer: Any, budget: Optional[float] = None) -> Optional[int]:
    """The features ``layer`` shows; None when the provider does not know or the count could not be made exact.

    ``layer.featureCount()`` for every layer but an OGR GeoPackage one with a subset; that one is read by GDAL
    within ``budget`` seconds (``COUNT_BUDGET`` by default), or found in the cache of the counts made on the file as
    it is. Calling thread; the caller decides whether a web service may be asked
    (``source_capability_probe.counts_cheaply``).
    """
    try:
        subset = (layer.subsetString() or '') if _is_geopackage(layer) else ''
        if not subset.strip():
            return _known(layer.featureCount())
        if layer.isModified():  # the file does not hold the edits yet
            return None
        path, table, index = source_parts(layer.source())
    except (RuntimeError, AttributeError):  # a layer deleted meanwhile
        return None
    if path is None or _QUERY.match(subset) or _NO_NUMBER.search(subset):
        return None
    key = _cache_key(path, table, index, subset)
    if key is not None and key in _CACHE:
        _CACHE.move_to_end(key)
        return _CACHE[key]
    count = _read_count(path, table, index, subset, COUNT_BUDGET if budget is None else budget)
    if count is not None and key is not None:
        _CACHE[key] = count
        while len(_CACHE) > CACHE_SIZE:
            _CACHE.popitem(last=False)
    return count


def features_to_read(layer: Any, budget: Optional[float] = None) -> int:
    """How many features reading ``layer`` goes through, for a limit on the reads of the main thread.

    The exact count, else ``featureCount()``: a GeoPackage count that left the subset out is the count of the whole
    table, never fewer than the layer shows. -1 when the provider does not know.
    """
    count = exact_feature_count(layer, budget)
    if count is None:
        try:
            count = layer.featureCount()
        except (RuntimeError, AttributeError):
            return -1
    return count if isinstance(count, int) else -1


def source_parts(source: str) -> Tuple[Optional[str], str, int]:
    """``(path, layer name, layer index)`` of an OGR source; path None when it is not counted here.

    The layer index is the one QGIS opens when the source names no layer. Not counted: a layer of one geometry type
    out of a mixed table (QGIS counts it by reading, the table holds every type) and a path that is no local file.
    """
    parts = source.split('|')
    options = {}
    for part in parts[1:]:
        key, _, value = part.partition('=')
        if key == 'subset':  # the last option, and its text may hold "|"
            break
        options[key] = value
    try:
        index = int(options.get('layerid') or 0)
    except ValueError:
        return None, '', 0
    if options.get('geometrytype') or not os.path.isfile(parts[0]):
        return None, '', 0
    return parts[0], options.get('layername', ''), index


def _cache_key(path: str, table: str, index: int, subset: str) -> Optional[tuple]:
    """The file as it is (time and size of the file and of its write-ahead log) and what is counted in it."""
    try:
        states = [(stat.st_mtime_ns, stat.st_size) for stat in
                  (os.stat(name) for name in (path, path + '-wal') if os.path.exists(name))]
    except OSError:
        return None
    return (path, tuple(states), table, index, subset)


def _known(count: Any) -> Optional[int]:
    """``count`` when it is a number of features; None for -1 (unknown) and -2 (not counted yet)."""
    return count if isinstance(count, int) and not isinstance(count, bool) and count >= 0 else None


def _is_geopackage(layer: Any) -> bool:
    if (layer.providerType() or '').lower() != 'ogr':
        return False
    provider = layer.dataProvider()
    return provider is not None and (provider.storageType() or '').upper() == 'GPKG'


def _read_count(path: str, table: str, index: int, subset: str, budget: float) -> Optional[int]:
    """The features GDAL reads from the layer of ``path`` under ``subset``; None past ``budget`` or on an error."""
    if budget <= 0:
        return None
    try:
        from osgeo import gdal
    except ImportError:
        return None
    deadline = _clock() + budget
    gdal.PushErrorHandler('CPLQuietErrorHandler')  # errors of this thread, read below
    # A locked file is not waited for, on this thread only (GDAL 3.4 has the setting, 3.2 not: 5 s of waiting).
    local_option = getattr(gdal, 'SetThreadLocalConfigOption', None)
    busy = gdal.GetThreadLocalConfigOption('SQLITE_BUSY_TIMEOUT', None) if local_option else None
    if local_option:
        local_option('SQLITE_BUSY_TIMEOUT', '0')
    dataset = layer = feature = None
    try:
        gdal.ErrorReset()
        dataset = gdal.OpenEx(path, gdal.OF_VECTOR | gdal.OF_READONLY, allowed_drivers=['GPKG'])
        layer = None if dataset is None else (dataset.GetLayerByName(table) if table else dataset.GetLayer(index))
        if layer is None or layer.SetAttributeFilter(subset) != 0 or _failed(gdal):
            return None
        definition = layer.GetLayerDefn()
        layer.SetIgnoredFields(
            [definition.GetFieldDefn(i).GetName() for i in range(definition.GetFieldCount())]
            + [definition.GetGeomFieldDefn(i).GetName() for i in range(definition.GetGeomFieldCount())]
            + ['OGR_GEOMETRY', 'OGR_STYLE'])
        gdal.ErrorReset()  # a field not ignored only makes the reading longer
        count = 0
        feature = layer.GetNextFeature()
        while feature is not None:
            count += 1
            if (count == 1 or count % CLOCK_EVERY == 0) and _clock() > deadline:
                return None
            feature = layer.GetNextFeature()
        return None if _failed(gdal) else count
    except RuntimeError:  # GDAL exceptions turned on by someone else
        logger.debug("Features of %s not counted", table or path, exc_info=True)
        return None
    finally:
        feature = layer = dataset = None
        if local_option:
            local_option('SQLITE_BUSY_TIMEOUT', busy)
        gdal.PopErrorHandler()


def _failed(gdal) -> bool:
    """Whether GDAL failed in this thread since the last ``ErrorReset``."""
    return gdal.GetLastErrorType() >= gdal.CE_Failure
