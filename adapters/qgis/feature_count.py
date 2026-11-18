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

A plain filter (a condition, with none of the words below) is read by
batches where GDAL has them and was compared (``ARROW_FROM``): the same
reading done in GDAL rather than feature after feature from Python, ten times
as fast, so ten times as many features counted within the budget. A filter
with LIMIT, ORDER BY, GROUP BY or a query of its own keeps the reading
feature after feature: by batches GDAL leaves those words out and counts more
(2026-11-14: ``"numero" >= 20 LIMIT 10`` read 10 features one way, 270 000 the
other).

Not bounded by the budget: opening the file, and the wait for the first
feature (a selective filter on a big table goes through it all before the
first one). A file locked by another connection is not waited for
(``SQLITE_BUSY_TIMEOUT`` 0 for this thread; GDAL 3.2 has no such setting and
waits 5 s, as for QGIS): no number. A layer without a
subset keeps ``featureCount()``, but for a table of 100 000 features or more
without ``gpkg_ogr_contents``: that count is ``MAX(fid) - MIN(fid) + 1``, more
than the features when fids have holes (deleted features), so the table is
counted (``SELECT COUNT(*)``, read only, within the budget: the statement is
interrupted past it) and there is no number past the budget. A subset QGIS may run as a query of its
own (starting with SELECT or WITH), made of several queries (UNION,
INTERSECT, EXCEPT: what it reads depends on the columns asked) or drawn at
random (``random()``: another answer at each reading) has no number.
"""
import logging
import os
import re
import sqlite3
import threading
import time
from collections import OrderedDict
from contextlib import closing
from typing import Any, Optional, Tuple
from urllib.request import pathname2url

logger = logging.getLogger(__name__)

APPROX_FROM = 100_000  # rows of a table from which QGIS stops counting it (without gpkg_ogr_contents, by its fids)
COUNT_BUDGET = 1.0  # seconds of the calling thread one count may take
CLOCK_EVERY = 64  # features read between two looks at the clock (every feature costs no more: measured)
CACHE_SIZE = 64
_CACHE: 'OrderedDict[tuple, int]' = OrderedDict()
# Counts made on a copy of a layer under a filter about to be set on it: (path, table, index, subset) -> (count,
# when). See ``note_trial``.
TRIAL_WINDOW = 3.0  # seconds such a count stays good for the layer the same filter is then set on
TRIALS_KEPT = 8
_TRIALS: 'OrderedDict[tuple, Tuple[int, float]]' = OrderedDict()
_clock = time.monotonic
_QUERY = re.compile(r'\s*(SELECT|WITH)\b', re.IGNORECASE)
# Several queries (what they read depends on the columns asked), or a different answer at each reading.
_NO_NUMBER = re.compile(r'\b(UNION|INTERSECT|EXCEPT)\b|\bRANDOM(BLOB)?\s*\(', re.IGNORECASE)
# More than a condition: read feature after feature, as QGIS reads it. Inside a text too ('limit 3'): only slower.
_NOT_PLAIN = re.compile(r'\b(SELECT|WITH|LIMIT|OFFSET|ORDER|GROUP|HAVING|WINDOW|UNION|INTERSECT|EXCEPT)\b|;|--|/\*',
                        re.IGNORECASE)
ARROW_FROM = 3100000  # GDAL 3.10: batches and features were compared in 3.10 and 3.12 (QGIS 4.2, 3.44, 4.3)
ARROW_BATCH = 2048  # features of a batch: the clock is looked at after each


def exact_feature_count(layer: Any, budget: Optional[float] = None) -> Optional[int]:
    """The features ``layer`` shows; None when the provider does not know or the count could not be made exact.

    ``layer.featureCount()`` for every layer but an OGR GeoPackage one with a subset; that one is read by GDAL
    within ``budget`` seconds (``COUNT_BUDGET`` by default), or found in the cache of the counts made on the file as
    it is. Calling thread; the caller decides whether a web service may be asked
    (``source_capability_probe.counts_cheaply``).
    """
    try:
        geopackage = _is_geopackage(layer)
        subset = (layer.subsetString() or '') if geopackage else ''
        if not subset.strip():
            count = _known(layer.featureCount())
            if geopackage and count is not None and count >= APPROX_FROM:
                return _whole_table(layer, count, COUNT_BUDGET if budget is None else budget)
            return count
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


def _whole_table(layer: Any, count: int, budget: float) -> Optional[int]:
    """The features of a GeoPackage table with no subset, ``count`` being what ``featureCount()`` says of it.

    From ``APPROX_FROM`` rows QGIS does not count a table without ``gpkg_ogr_contents``: it answers
    ``MAX(fid) - MIN(fid) + 1``, too many when fids have holes. ``count`` is kept when the table has that table of
    counts (GDAL keeps it right), or when it is not one this module reads (a layer of one geometry type out of a mixed
    table, QGIS counts it by reading); else the table is counted, None past ``budget`` or when it cannot be.
    """
    try:
        if layer.isModified():  # the file does not hold the edits yet
            return None
        path, table, index = source_parts(layer.source())
    except (RuntimeError, AttributeError):  # a layer deleted meanwhile
        return None
    if path is None:
        return count
    key = _cache_key(path, table, index, '')
    if key is not None and key in _CACHE:
        _CACHE.move_to_end(key)
        return _CACHE[key]
    counted = _count_rows(path, table, index, budget)
    if counted is _HAS_CONTENTS:
        return count
    if counted is not None and key is not None:
        _CACHE[key] = counted
        while len(_CACHE) > CACHE_SIZE:
            _CACHE.popitem(last=False)
    return counted


_HAS_CONTENTS = object()  # the table of counts of GDAL is there: what QGIS reads from it is right


def _count_rows(path: str, table: str, index: int, budget: float) -> Any:
    """``SELECT COUNT(*)`` of a table of the GeoPackage at ``path``, read only, stopped past ``budget`` seconds; None
    then or on an error, ``_HAS_CONTENTS`` when the file holds ``gpkg_ogr_contents``."""
    if budget <= 0:
        return None
    deadline = _clock() + budget
    if not table:
        table = _table_name(path, index)
        if not table:
            return None
    try:
        # Not waited for when another connection locks the file (timeout 0), as for the reading of a subset.
        with closing(sqlite3.connect(f"file:{pathname2url(path)}?mode=ro", uri=True, timeout=0)) as database:
            # COUNT(*) is one step of SQLite that a progress handler cannot cut: the statement is interrupted from
            # another thread once the budget is spent.
            timer = threading.Timer(max(deadline - _clock(), 0.0), database.interrupt)
            timer.daemon = True
            timer.start()
            try:
                if database.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' "
                                    "AND name = 'gpkg_ogr_contents'").fetchone():
                    return _HAS_CONTENTS
                row = database.execute('SELECT COUNT(*) FROM "%s"' % table.replace('"', '""')).fetchone()
            finally:
                timer.cancel()
                timer.join()  # before the connection is closed: an interrupt of a closed one raises
    except sqlite3.Error:  # interrupted past the budget, locked, no such table, not a database
        return None
    return row[0] if row and isinstance(row[0], int) else None


def _table_name(path: str, index: int) -> str:
    """The name of the layer of the GeoPackage at ``path`` that QGIS opens when its source names none."""
    try:
        from osgeo import gdal
    except ImportError:
        return ''
    gdal.PushErrorHandler('CPLQuietErrorHandler')
    dataset = layer = None
    try:
        dataset = gdal.OpenEx(path, gdal.OF_VECTOR | gdal.OF_READONLY, allowed_drivers=['GPKG'])
        layer = None if dataset is None else dataset.GetLayer(index)
        return layer.GetName() if layer is not None else ''
    except RuntimeError:  # GDAL exceptions turned on by someone else
        return ''
    finally:
        layer = dataset = None
        gdal.PopErrorHandler()


def _counted_table(layer: Any) -> Optional[Tuple[str, str, int, str]]:
    """``(path, table, index, subset)`` of a filtered GeoPackage layer counted here; None for any other."""
    try:
        subset = (layer.subsetString() or '') if _is_geopackage(layer) else ''
        if not subset.strip() or layer.isModified():
            return None
        path, table, index = source_parts(layer.source())
    except (RuntimeError, AttributeError):
        return None
    if path is None or _QUERY.match(subset) or _NO_NUMBER.search(subset):
        return None
    return path, table, index, subset


def note_trial(trial: Any, count: int) -> None:
    """``count`` features were just read on ``trial``, a private copy of a layer under the filter it is about to get.

    Setting a filter on a GeoPackage layer makes QGIS (3.28 and later) reopen its file, which rewrites the header:
    the file is no longer "as it was", and the count made a moment ago on the copy was read a second time, then a
    third by whoever asked next (2026-11-14: three readings of 60 000 features for one filter). ``adopt_trial``
    gives the count to the layer once the filter is set.
    """
    table = _counted_table(trial)
    if table is None or _known(count) is None:
        return
    _TRIALS[table] = (count, _clock())
    _TRIALS.move_to_end(table)
    while len(_TRIALS) > TRIALS_KEPT:
        _TRIALS.popitem(last=False)


def adopt_trial(layer: Any) -> None:
    """The filter of ``layer`` was just set: a count made on its copy under that very filter within
    ``TRIAL_WINDOW`` seconds is kept for the file as it is now. Nothing is read."""
    table = _counted_table(layer)
    found = _TRIALS.pop(table, None) if table is not None else None
    if found is None or _clock() - found[1] > TRIAL_WINDOW:
        return
    key = _cache_key(*table)
    if key is not None:
        _CACHE[key] = found[0]
        _CACHE.move_to_end(key)
        while len(_CACHE) > CACHE_SIZE:
            _CACHE.popitem(last=False)


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
        if _by_batches(gdal, layer, subset):
            count = _count_batches(layer, deadline)
            if count is not _FEATURE_BY_FEATURE:
                return None if count is None or _failed(gdal) else count
            layer.ResetReading()
            gdal.ErrorReset()
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


_FEATURE_BY_FEATURE = object()  # no batches here after all: read the features


def _by_batches(gdal: Any, layer: Any, subset: str) -> bool:
    """Whether ``subset`` is a plain condition and this GDAL reads it by batches as it reads it by features."""
    if _NOT_PLAIN.search(subset) or not hasattr(layer, 'GetArrowStream'):
        return False
    try:
        return int(gdal.VersionInfo('VERSION_NUM')) >= ARROW_FROM
    except (AttributeError, TypeError, ValueError):
        return False


def _count_batches(layer: Any, deadline: float) -> Any:
    """The features of ``layer`` under its filter, read by batches of ``ARROW_BATCH``; None past ``deadline``,
    ``_FEATURE_BY_FEATURE`` when GDAL gives no batches for this layer."""
    stream = layer.GetArrowStream([f'MAX_FEATURES_IN_BATCH={ARROW_BATCH}'])
    if stream is None:
        return _FEATURE_BY_FEATURE
    count = 0
    while True:
        batch = stream.GetNextRecordBatch()
        if batch is None:
            return count
        count += batch.GetLength()
        if _clock() > deadline:
            return None


def _failed(gdal) -> bool:
    """Whether GDAL failed in this thread since the last ``ErrorReset``."""
    return gdal.GetLastErrorType() >= gdal.CE_Failure
