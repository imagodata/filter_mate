# -*- coding: utf-8 -*-
"""
PERF 2026-09-12: ``InterruptibleSQLiteQuery`` wakes up as soon as the worker
thread finishes instead of sleeping a full polling interval, and still honours
timeouts and cancellation.

Runs against a real in-memory sqlite3 database (no QGIS involved).
"""

import importlib.util
import sqlite3
import sys
import time
from pathlib import Path

import pytest

_MODULE_PATH = (Path(__file__).resolve().parents[5]
                / "adapters" / "backends" / "spatialite" / "interruptible_query.py")


def _load_module():
    name = "fmtest_interruptible_query"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    connection.executemany("INSERT INTO t (v) VALUES (?)", [(f"row{i}",) for i in range(50)])
    connection.commit()
    yield connection
    connection.close()


@pytest.mark.unit
class TestInterruptibleQuery:

    def test_fast_query_returns_without_polling_penalty(self, conn):
        mod = _load_module()
        query = mod.InterruptibleSQLiteQuery(conn, "SELECT count(*) FROM t")

        start = time.perf_counter()
        results, error = query.execute(timeout=5)
        elapsed = time.perf_counter() - start

        assert error is None
        assert results == [(50,)]
        # Before: at least one full SPATIALITE_INTERRUPT_CHECK_INTERVAL (0.5 s)
        assert elapsed < mod.SPATIALITE_INTERRUPT_CHECK_INTERVAL / 2

    def test_sql_error_is_reported(self, conn):
        mod = _load_module()
        query = mod.InterruptibleSQLiteQuery(conn, "SELECT nope FROM missing_table")
        results, error = query.execute(timeout=5)
        assert results == []
        assert isinstance(error, sqlite3.Error)

    def test_cancellation_interrupts_long_query(self, conn):
        mod = _load_module()
        slow_sql = (
            "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c WHERE x < 50000000) "
            "SELECT count(*) FROM c"
        )
        query = mod.InterruptibleSQLiteQuery(conn, slow_sql)

        start = time.perf_counter()
        results, error = query.execute(timeout=30, cancel_check=lambda: True)
        elapsed = time.perf_counter() - start

        assert results == []
        assert error is not None and "cancel" in str(error).lower()
        assert elapsed < 5
        # The worker must be stopped before we hand the connection back
        assert query._thread is not None and not query._thread.is_alive()

    def test_timeout_interrupts_long_query(self, conn):
        mod = _load_module()
        slow_sql = (
            "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c WHERE x < 50000000) "
            "SELECT count(*) FROM c"
        )
        query = mod.InterruptibleSQLiteQuery(conn, slow_sql)

        start = time.perf_counter()
        results, error = query.execute(timeout=0.6)
        elapsed = time.perf_counter() - start

        assert results == []
        assert error is not None and "timeout" in str(error).lower()
        assert elapsed < 5
        assert query._thread is not None and not query._thread.is_alive()
