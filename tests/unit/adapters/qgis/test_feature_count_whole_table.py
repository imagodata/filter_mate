# -*- coding: utf-8 -*-
"""2026-11-18: a GeoPackage table of 100 000 rows or more without ``gpkg_ogr_contents`` is counted, not told as
``MAX(fid) - MIN(fid) + 1`` (``adapters/qgis/feature_count.py``: "exact, or not told")."""
import importlib.util
import pathlib
import sqlite3
import time
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit

_PATH = pathlib.Path(__file__).resolve().parents[4] / "adapters" / "qgis" / "feature_count.py"
_SPEC = importlib.util.spec_from_file_location("fm_feature_count_whole_table", _PATH)
counts = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(counts)


def _gpkg(path, rows, holes=(), contents=False):
    database = sqlite3.connect(path)
    database.execute("CREATE TABLE troncon (fid INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT)")
    database.executemany("INSERT INTO troncon (fid, nom) VALUES (?, 'x')", [(fid,) for fid in range(1, rows + 1)])
    database.executemany("DELETE FROM troncon WHERE fid = ?", [(fid,) for fid in holes])
    if contents:
        database.execute("CREATE TABLE gpkg_ogr_contents (table_name TEXT, feature_count INTEGER)")
    database.commit()
    database.close()


def _layer(path, said):
    """A GeoPackage layer as QGIS tells it: no subset, and the count it estimated from the fids."""
    return SimpleNamespace(
        providerType=lambda: "ogr", dataProvider=lambda: SimpleNamespace(storageType=lambda: "GPKG"),
        subsetString=lambda: "", featureCount=lambda: said, isModified=lambda: False,
        source=lambda: f"{path}|layername=troncon")


def test_holes_in_the_fids_do_not_make_the_count(tmp_path):
    path = str(tmp_path / "holes.gpkg")
    _gpkg(path, 1500, holes=range(5, 1001, 5))  # 200 deleted
    counts.APPROX_FROM = 1000
    assert counts.exact_feature_count(_layer(path, 1500)) == 1300


def test_a_table_below_the_threshold_keeps_the_count_of_qgis(tmp_path):
    path = str(tmp_path / "small.gpkg")
    _gpkg(path, 50)
    counts.APPROX_FROM = 1000
    assert counts.exact_feature_count(_layer(path, 50)) == 50


def test_the_table_of_counts_of_gdal_is_trusted(tmp_path):
    path = str(tmp_path / "contents.gpkg")
    _gpkg(path, 1200, contents=True)
    counts.APPROX_FROM = 1000
    assert counts.exact_feature_count(_layer(path, 1234)) == 1234  # what QGIS read from it


def test_no_number_when_the_budget_is_spent_or_the_file_cannot_be_read(tmp_path):
    path = str(tmp_path / "holes.gpkg")
    _gpkg(path, 1500, holes=[7])
    counts.APPROX_FROM = 1000
    counts._CACHE.clear()
    assert counts.exact_feature_count(_layer(path, 1500), budget=0) is None
    gone = str(tmp_path / "gone.gpkg")
    assert counts._count_rows(gone, "troncon", 0, 1.0) is None
    assert counts._count_rows(path, "nope", 0, 1.0) is None


def test_the_statement_is_interrupted_once_the_budget_is_spent(tmp_path, monkeypatch):
    """COUNT(*) cannot be cut by a progress handler: the connection is interrupted from a timer, and no number
    comes of it."""
    path = str(tmp_path / "holes.gpkg")
    _gpkg(path, 1500, holes=[7])
    seen = []

    class Slow:
        """A connection whose first statement lasts longer than the budget; it ends when interrupted."""

        def __init__(self, database):
            self.database, self.interrupted = database, False

        def execute(self, *arguments):
            time.sleep(0.4)
            if self.interrupted:
                raise sqlite3.OperationalError("interrupted")
            return self.database.execute(*arguments)

        def interrupt(self):
            self.interrupted = True
            seen.append("interrupt")

        def close(self):
            self.database.close()

    real = sqlite3.connect
    monkeypatch.setattr(counts.sqlite3, "connect", lambda *a, **k: Slow(real(*a, **k)))
    assert counts._count_rows(path, "troncon", 0, 0.05) is None and seen == ["interrupt"]
