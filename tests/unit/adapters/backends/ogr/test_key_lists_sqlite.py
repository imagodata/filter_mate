# -*- coding: utf-8 -*-
"""Key-list subsets run by a real SQLite engine (Python's sqlite3), 2026-10-17.

GeoPackage subsets are SQLite SQL. These tests execute what the OGR backend
writes - the JSON key literal, its Disjoint complement, the combination with
an attribute filter - and the JSON1 probe with and without json_each.
"""
import importlib.util
import json
import sqlite3
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parents[5]
ROOT = "filter_mate"


class _FakePort:
    def __init__(self, task_params):
        self.task_params = task_params

    def log_debug(self, msg): pass
    def log_info(self, msg): pass
    def log_warning(self, msg): pass
    def log_error(self, msg): pass


def _package(name):
    module = types.ModuleType(name)
    module.__path__ = []
    return module


def _load(name, path, stubs):
    saved = {key: sys.modules.get(key) for key in stubs}
    sys.modules.update(stubs)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for key, value in saved.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


_port = types.ModuleType(f"{ROOT}.core.ports.geometric_filter_port")
_port.GeometricFilterPort = _FakePort
_sql_utils = types.ModuleType(f"{ROOT}.infrastructure.database.sql_utils")
_sql_utils.safe_set_subset_string = MagicMock(return_value=True)
ogr_builder = _load(
    f"{ROOT}.adapters.backends.ogr._fm_test_sqlite_expression_builder",
    PLUGIN_ROOT / "adapters" / "backends" / "ogr" / "expression_builder.py",
    {
        ROOT: _package(ROOT),
        f"{ROOT}.core": _package(f"{ROOT}.core"),
        f"{ROOT}.core.ports": _package(f"{ROOT}.core.ports"),
        f"{ROOT}.core.ports.geometric_filter_port": _port,
        f"{ROOT}.infrastructure": _package(f"{ROOT}.infrastructure"),
        f"{ROOT}.infrastructure.database": _package(f"{ROOT}.infrastructure.database"),
        f"{ROOT}.infrastructure.database.sql_utils": _sql_utils,
        f"{ROOT}.adapters": _package(f"{ROOT}.adapters"),
        f"{ROOT}.adapters.backends": _package(f"{ROOT}.adapters.backends"),
        f"{ROOT}.adapters.backends.ogr": _package(f"{ROOT}.adapters.backends.ogr"),
    },
)
capabilities = _load(
    "fm_test_sqlite_capabilities",
    PLUGIN_ROOT / "infrastructure" / "database" / "sqlite_capabilities.py",
    {},
)

BIG = 2 ** 60 + 7  # beyond 2^53: a float round-trip would change it


@pytest.fixture
def table():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE roads (fid INTEGER PRIMARY KEY, cleabs TEXT, nature TEXT)")
    rows = [(i, f"TRON{i}", "Route" if i % 2 else "Chemin") for i in range(1, 5001)]
    rows.append((BIG, "TRON'BIG", "Route"))
    con.executemany("INSERT INTO roads VALUES (?, ?, ?)", rows)
    yield con
    con.close()


def _count(con, where):
    return con.execute(f"SELECT count(*) FROM roads WHERE {where}").fetchone()[0]  # nosec B608 - test SQL


def _builder():
    return ogr_builder.OGRExpressionBuilder(task_params={})


def test_json_key_list_selects_exactly_the_keys(table):
    keys = list(range(1, 3001)) + [BIG]
    clause = _builder()._json_key_clause('"fid"', keys, numeric=True)
    assert _count(table, clause) == 3001
    assert table.execute(f"SELECT max(fid) FROM roads WHERE {clause}").fetchone()[0] == BIG  # nosec B608


def test_json_text_keys_with_quotes(table):
    clause = _builder()._json_key_clause('"cleabs"', ["TRON'BIG", "TRON1", "missing"], numeric=False)
    assert _count(table, clause) == 2


def test_disjoint_complement_and_combinations(table):
    builder = _builder()
    keys = builder._json_key_clause('"fid"', list(range(1, 2001)), numeric=True)
    complement = f"NOT ({keys})"
    assert _count(table, complement) == 5001 - 2000
    old = '"nature" = \'Route\''  # 2,500 odd fids + BIG
    assert _count(table, builder._combine_with_old_subset(old, "AND", keys)) == 1000
    assert _count(table, builder._combine_with_old_subset(old, "OR", keys)) == 2501 + 1000
    assert _count(table, builder._combine_with_old_subset(old, "AND NOT", keys)) == 2501 - 1000
    # empty selection: same rules
    assert _count(table, builder._combine_with_old_subset(old, "OR", "1 = 0")) == 2501
    assert _count(table, builder._combine_with_old_subset(old, "AND NOT", "1 = 0")) == 2501
    assert _count(table, builder._combine_with_old_subset(old, "AND", "1 = 0")) == 0


def _fake_osgeo(json1: bool):
    class _Feature:
        def GetField(self, index):
            return 2

    class _Result:
        def GetNextFeature(self):
            return _Feature()

    class _Dataset:
        def ExecuteSQL(self, sql):
            if not json1:
                raise RuntimeError("sqlite3_prepare_v2(): no such table: json_each")
            con = sqlite3.connect(":memory:")
            con.execute(sql)  # the real json_each of Python's SQLite
            return _Result()

        def ReleaseResultSet(self, result):
            pass

    driver = types.SimpleNamespace(CreateDataSource=lambda path: _Dataset())
    ogr = types.SimpleNamespace(GetDriverByName=lambda name: driver)
    gdal = types.SimpleNamespace(Unlink=lambda path: 0)
    return types.SimpleNamespace(ogr=ogr, gdal=gdal)


@pytest.mark.parametrize("json1", [True, False])
def test_json1_probe_with_and_without_json_each(monkeypatch, json1):
    osgeo = _fake_osgeo(json1)
    monkeypatch.setitem(sys.modules, "osgeo", osgeo)
    monkeypatch.setitem(sys.modules, "osgeo.ogr", osgeo.ogr)
    monkeypatch.setitem(sys.modules, "osgeo.gdal", osgeo.gdal)
    capabilities.reset_json1_probe()
    try:
        assert capabilities.gdal_sqlite_json1_available() is json1
        # probed once: a later change of the fake is not seen
        monkeypatch.setitem(sys.modules, "osgeo", None)
        assert capabilities.gdal_sqlite_json1_available() is json1
    finally:
        capabilities.reset_json1_probe()


def test_json1_probe_without_gdal_bindings(monkeypatch):
    monkeypatch.setitem(sys.modules, "osgeo", None)
    capabilities.reset_json1_probe()
    try:
        assert capabilities.gdal_sqlite_json1_available() is False
    finally:
        capabilities.reset_json1_probe()


def test_python_sqlite_has_json_each():
    """The engine of these tests evaluates the JSON form (JSON1 built in since SQLite 3.38)."""
    con = sqlite3.connect(":memory:")
    assert con.execute("SELECT count(*) FROM json_each(?)", (json.dumps([1, 2, 3]),)).fetchone()[0] == 3
