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


def _gpkg(path, rows, holes=(), contents=False, row=True):
    database = sqlite3.connect(path)
    database.execute("CREATE TABLE troncon (fid INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT)")
    database.executemany("INSERT INTO troncon (fid, nom) VALUES (?, 'x')", [(fid,) for fid in range(1, rows + 1)])
    database.executemany("DELETE FROM troncon WHERE fid = ?", [(fid,) for fid in holes])
    if contents:
        database.execute("CREATE TABLE gpkg_ogr_contents (table_name TEXT, feature_count INTEGER)")
        if row:
            database.execute("INSERT INTO gpkg_ogr_contents VALUES ('troncon', ?)", (rows,))
        elif row is None:
            database.execute("INSERT INTO gpkg_ogr_contents VALUES ('troncon', NULL)")
    database.commit()
    database.close()


def _layer(path, said, modified=False):
    """A GeoPackage layer as QGIS tells it: no subset, and the count it estimated from the fids."""
    return SimpleNamespace(
        providerType=lambda: "ogr", dataProvider=lambda: SimpleNamespace(storageType=lambda: "GPKG"),
        subsetString=lambda: "", featureCount=lambda: said, isModified=lambda: modified,
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


@pytest.mark.parametrize("row", [False, None])
def test_the_table_of_counts_needs_a_number_for_this_table(tmp_path, row):
    """QGIS falls back on its fids when ``gpkg_ogr_contents`` has no row for the table, or a NULL one."""
    path = str(tmp_path / "contents.gpkg")
    _gpkg(path, 1500, holes=range(5, 1001, 5), contents=True, row=row)
    counts.APPROX_FROM = 1000
    assert counts.exact_feature_count(_layer(path, 1500)) == 1300


def test_a_layer_being_edited_keeps_the_count_of_qgis_with_its_buffer(tmp_path):
    path = str(tmp_path / "holes.gpkg")
    _gpkg(path, 1500, holes=[7])
    counts.APPROX_FROM = 1000
    assert counts.exact_feature_count(_layer(path, 1503, modified=True)) == 1503


def test_the_table_of_counts_of_gdal_is_trusted(tmp_path):
    path = str(tmp_path / "contents.gpkg")
    _gpkg(path, 1200, contents=True)  # a row of counts for the table
    counts.APPROX_FROM = 1000
    assert counts.exact_feature_count(_layer(path, 1234)) == 1234  # what QGIS read from it


def test_no_number_when_the_budget_is_spent_or_the_file_cannot_be_read(tmp_path, monkeypatch):
    path = str(tmp_path / "holes.gpkg")
    _gpkg(path, 1500, holes=[7])
    counts.APPROX_FROM = 1000
    counts._CACHE.clear()
    monkeypatch.setattr(counts, "TABLE_BUDGET", 0)
    assert counts.exact_feature_count(_layer(path, 1500)) is None
    assert not counts._CACHE  # nothing was tried: nothing is remembered
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


class _Cut:
    """A connection whose statements end 'interrupted' at once, counting how many times the file was opened."""

    opened = 0

    def __init__(self, real):
        type(self).opened += 1
        self.real = real

    def execute(self, *arguments):
        raise sqlite3.OperationalError("interrupted")

    def interrupt(self):
        pass

    def close(self):
        self.real.close()


def test_a_count_cut_by_the_budget_is_not_tried_again_until_the_file_changes(tmp_path, monkeypatch):
    path = str(tmp_path / "cold.gpkg")
    _gpkg(path, 1500, holes=[7])
    counts.APPROX_FROM = 1000
    counts._CACHE.clear()
    _Cut.opened = 0
    real = sqlite3.connect
    monkeypatch.setattr(counts.sqlite3, "connect", lambda *a, **k: _Cut(real(*a, **k)))
    layer = _layer(path, 1500)
    assert counts.exact_feature_count(layer) is None and counts.exact_feature_count(layer) is None
    assert _Cut.opened == 1  # the file is opened once, not at every call
    # The file changes: counted again (here with a connection that answers).
    monkeypatch.setattr(counts.sqlite3, "connect", real)
    database = sqlite3.connect(path)
    database.execute("DELETE FROM troncon WHERE fid = 8")
    database.commit()
    database.close()
    assert counts.exact_feature_count(_layer(path, 1500)) == 1498


def test_a_whole_table_has_a_budget_of_its_own_and_tells_how_long_it_took(tmp_path, monkeypatch):
    path = str(tmp_path / "holes.gpkg")
    _gpkg(path, 1500, holes=[7])
    counts.APPROX_FROM = 1000
    counts._CACHE.clear()
    seen = []
    real = counts._count_rows
    monkeypatch.setattr(counts, "_count_rows", lambda *arguments: seen.append(arguments[3]) or real(*arguments))
    before = counts.table_seconds()
    # The budget of the caller is nearly spent: the table is counted all the same, with the budget of tables.
    assert counts.exact_feature_count(_layer(path, 1500), budget=0.001) == 1499
    assert seen == [counts.TABLE_BUDGET] and counts.table_seconds() > before
