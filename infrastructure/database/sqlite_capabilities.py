# -*- coding: utf-8 -*-
"""
SQLite capabilities of the GDAL build QGIS uses (2026-10-17).

GeoPackage and SQLite subset strings run inside GDAL's SQLite, not Python's
``sqlite3``. FilterMate writes long key lists as ``"fid" IN (SELECT value
FROM json_each('[...]'))`` (a long literal ``IN`` list froze QGIS for more
than 25 min); ``json_each`` needs JSON1, built in only from SQLite 3.38
(Ubuntu 22.04 ships 3.37.2, usually compiled with JSON1, not always).
"""

import logging
import threading

logger = logging.getLogger('FilterMate.Infrastructure.SqliteCapabilities')

_JSON1_LOCK = threading.Lock()
_JSON1_AVAILABLE = None


def gdal_sqlite_json1_available() -> bool:
    """Whether GDAL's SQLite evaluates ``json_each`` (probed once per session).

    Runs ``SELECT count(*) FROM json_each('[1,2]')`` on an in-memory SQLite
    dataset of GDAL. False when GDAL's Python bindings are missing or the
    function is unknown.
    """
    global _JSON1_AVAILABLE
    with _JSON1_LOCK:
        if _JSON1_AVAILABLE is None:
            _JSON1_AVAILABLE = _probe_json1()
            logger.info(f"GDAL SQLite JSON1 (json_each) available: {_JSON1_AVAILABLE}")
        return _JSON1_AVAILABLE


def reset_json1_probe() -> None:
    """Forget the probe result (tests)."""
    global _JSON1_AVAILABLE
    with _JSON1_LOCK:
        _JSON1_AVAILABLE = None


def _probe_json1() -> bool:
    try:
        from osgeo import gdal, ogr
    except ImportError:
        return False
    path = '/vsimem/filtermate_json1_probe.sqlite'
    try:
        driver = ogr.GetDriverByName('SQLite')
        if driver is None:
            return False
        dataset = driver.CreateDataSource(path)
        if dataset is None:
            return False
        try:
            result = dataset.ExecuteSQL("SELECT count(*) FROM json_each('[1,2]')")
            if result is None:
                return False
            try:
                feature = result.GetNextFeature()
                return feature is not None and int(feature.GetField(0)) == 2
            finally:
                dataset.ReleaseResultSet(result)
        finally:
            dataset = None
            gdal.Unlink(path)
    except Exception as exc:  # "no such table: json_each" when JSON1 is missing
        logger.info(f"GDAL SQLite JSON1 probe failed: {exc}")
        return False
