# -*- coding: utf-8 -*-
"""
Regression tests for PostgreSQLBackend._execute_direct.

History:
    Audit 2026-04-23 (C1) found the direct-execution query template was a
    triple-quoted string without the `f` prefix, so `{pk_column}`, `{table_name}`
    and `{expression.sql}` were sent as literal text to PostgreSQL. The path is
    reachable whenever _should_use_mv() returns False (MV disabled or dataset
    below threshold), but no test exercised it.

These tests protect against regression of that format-string bug and of the
two `_get_table_name` / `_get_pk_column` calls whose return values were
previously discarded.
"""
import importlib.util
import os
import sys
import types
from unittest.mock import MagicMock

import pytest


ROOT = "filter_mate"


def _install_module_stubs():
    """Register minimal stubs for the imports backend.py performs at module load."""
    if ROOT not in sys.modules:
        pkg = types.ModuleType(ROOT)
        pkg.__path__ = []
        pkg.__package__ = ROOT
        sys.modules[ROOT] = pkg

    # Stub the core and sibling modules that backend.py imports.
    stub_paths = [
        f"{ROOT}.core",
        f"{ROOT}.core.ports",
        f"{ROOT}.core.ports.backend_port",
        f"{ROOT}.core.domain",
        f"{ROOT}.core.domain.filter_expression",
        f"{ROOT}.core.domain.filter_result",
        f"{ROOT}.core.domain.layer_info",
        f"{ROOT}.adapters",
        f"{ROOT}.adapters.backends",
        f"{ROOT}.adapters.backends.postgresql",
        f"{ROOT}.adapters.backends.postgresql.mv_manager",
        f"{ROOT}.adapters.backends.postgresql.optimizer",
        f"{ROOT}.adapters.backends.postgresql.cleanup",
    ]
    for name in stub_paths:
        sys.modules.setdefault(name, MagicMock())

    # Names imported by `from X import Y` must exist as attributes on the stubs.
    sys.modules[f"{ROOT}.core.ports.backend_port"].BackendPort = object
    sys.modules[f"{ROOT}.core.ports.backend_port"].BackendInfo = MagicMock
    sys.modules[f"{ROOT}.core.ports.backend_port"].BackendCapability = MagicMock
    sys.modules[f"{ROOT}.core.domain.filter_expression"].FilterExpression = MagicMock
    sys.modules[f"{ROOT}.core.domain.filter_expression"].ProviderType = MagicMock
    sys.modules[f"{ROOT}.core.domain.filter_result"].FilterResult = MagicMock
    sys.modules[f"{ROOT}.core.domain.layer_info"].LayerInfo = MagicMock
    sys.modules[f"{ROOT}.adapters.backends.postgresql.mv_manager"].MaterializedViewManager = MagicMock
    sys.modules[f"{ROOT}.adapters.backends.postgresql.mv_manager"].MVConfig = MagicMock
    sys.modules[f"{ROOT}.adapters.backends.postgresql.mv_manager"].create_mv_manager = MagicMock()
    sys.modules[f"{ROOT}.adapters.backends.postgresql.optimizer"].QueryOptimizer = MagicMock
    sys.modules[f"{ROOT}.adapters.backends.postgresql.optimizer"].create_optimizer = MagicMock()
    sys.modules[f"{ROOT}.adapters.backends.postgresql.cleanup"].create_cleanup_service = MagicMock()


_install_module_stubs()


# Load sql_safety.py for real — it has zero deps and the backend imports it
# at runtime via `from .sql_safety import ...` to validate WHERE clauses (S2).
_sql_safety_path = os.path.normpath(os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "..", "..",
    "adapters", "backends", "postgresql", "sql_safety.py",
))
_sql_safety_spec = importlib.util.spec_from_file_location(
    f"{ROOT}.adapters.backends.postgresql.sql_safety",
    _sql_safety_path,
)
_sql_safety_mod = importlib.util.module_from_spec(_sql_safety_spec)
_sql_safety_mod.__package__ = f"{ROOT}.adapters.backends.postgresql"
sys.modules[_sql_safety_mod.__name__] = _sql_safety_mod
_sql_safety_spec.loader.exec_module(_sql_safety_mod)


_backend_path = os.path.normpath(os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "..", "..",
    "adapters", "backends", "postgresql", "backend.py",
))

_spec = importlib.util.spec_from_file_location(
    f"{ROOT}.adapters.backends.postgresql.backend",
    _backend_path,
)
_mod = importlib.util.module_from_spec(_spec)
_mod.__package__ = f"{ROOT}.adapters.backends.postgresql"
sys.modules[_mod.__name__] = _mod
_spec.loader.exec_module(_mod)

PostgreSQLBackend = _mod.PostgreSQLBackend


@pytest.fixture
def backend():
    """Instantiate without running __init__ (skips MV manager / optimizer setup)."""
    return object.__new__(PostgreSQLBackend)


@pytest.fixture
def layer_info():
    info = MagicMock()
    info.source_path = "dbname=test user=x table=public.mytable"
    info.table_name = "mytable"
    info.schema_name = "public"
    info.pk_attr = "id"
    info.geometry_column = "geom"
    return info


@pytest.fixture
def expression():
    expr = MagicMock()
    expr.sql = "status = 'active'"
    return expr


@pytest.fixture
def connection():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = [(1,), (2,), (3,)]
    conn.cursor.return_value = cursor
    return conn


class TestExecuteDirectQueryTemplate:
    """Regression guards for C1 (audit 2026-04-23): broken f-string in _execute_direct."""

    def test_query_has_substituted_pk_column(self, backend, expression, layer_info, connection):
        backend._execute_direct(expression, layer_info, connection)
        query = connection.cursor.return_value.execute.call_args[0][0]

        assert "{pk_column}" not in query, (
            "REGRESSION C1: _execute_direct sent a literal '{pk_column}' placeholder "
            "to PostgreSQL. The query template must be an f-string."
        )
        assert '"id"' in query, "Expected quoted pk column 'id' in query"

    def test_query_has_substituted_table_name(self, backend, expression, layer_info, connection):
        backend._execute_direct(expression, layer_info, connection)
        query = connection.cursor.return_value.execute.call_args[0][0]

        assert "{table_name}" not in query, (
            "REGRESSION C1: _execute_direct sent a literal '{table_name}' placeholder"
        )
        assert "public.mytable" in query or '"mytable"' in query

    def test_query_has_substituted_expression(self, backend, expression, layer_info, connection):
        backend._execute_direct(expression, layer_info, connection)
        query = connection.cursor.return_value.execute.call_args[0][0]

        assert "{expression.sql}" not in query, (
            "REGRESSION C1: _execute_direct sent a literal '{expression.sql}' placeholder"
        )
        assert "status = 'active'" in query

    def test_returns_feature_ids_from_cursor(self, backend, expression, layer_info, connection):
        result = backend._execute_direct(expression, layer_info, connection)
        assert result == [1, 2, 3]

    def test_raises_on_cursor_execute_failure(self, backend, expression, layer_info, connection):
        connection.cursor.return_value.execute.side_effect = RuntimeError("syntax error")
        with pytest.raises(RuntimeError, match="syntax error"):
            backend._execute_direct(expression, layer_info, connection)


class TestSqlInjectionGuards:
    """S2 (audit 2026-04-29): defense-in-depth on _execute_direct / _execute_with_mv.

    Even if the upstream sanitizer leaks a malicious payload, sql_safety must
    refuse before cursor.execute() so chained statements / DDL / escalation
    functions cannot reach the database.
    """

    SqlInjectionAttempt = _sql_safety_mod.SqlInjectionAttempt

    @pytest.mark.parametrize(
        "payload",
        [
            "1=1; DROP TABLE users",
            "NOT(1=1); DELETE FROM y",
            '"x" = 1 -- AND "secret" = \'x\'',
            '"x" = 1 OR pg_sleep(10) IS NULL',
            '"x" = pg_read_file(\'/etc/passwd\')',
            "1=1 UNION ALL SELECT lo_import('/etc/shadow')",
        ],
    )
    def test_execute_direct_rejects_payload(
        self, backend, expression, layer_info, connection, payload
    ):
        expression.sql = payload
        with pytest.raises(self.SqlInjectionAttempt):
            backend._execute_direct(expression, layer_info, connection)
        # The cursor must NOT have been touched.
        connection.cursor.return_value.execute.assert_not_called()

    @pytest.mark.parametrize(
        "payload",
        [
            "1=1; DROP TABLE users",
            "NOT(pg_sleep(10) IS NULL)",
        ],
    )
    def test_execute_with_mv_rejects_payload(
        self, backend, expression, layer_info, connection, payload
    ):
        # _execute_with_mv calls into _mv_manager; assigning a bare MagicMock
        # is enough — the validator should fire before any MV interaction.
        backend._mv_manager = MagicMock()
        expression.sql = payload
        with pytest.raises(self.SqlInjectionAttempt):
            backend._execute_with_mv(expression, layer_info, connection)
        backend._mv_manager.create_mv.assert_not_called()

    def test_execute_direct_rejects_malformed_pk_column(
        self, backend, expression, layer_info, connection
    ):
        # Tampered LayerInfo with a hostile pk_attr — the identifier shape
        # check must catch it before f-string concatenation.
        layer_info.pk_attr = 'id"; DROP TABLE x; --'
        with pytest.raises(self.SqlInjectionAttempt, match="primary key column"):
            backend._execute_direct(expression, layer_info, connection)
        connection.cursor.return_value.execute.assert_not_called()

    def test_legitimate_expression_still_executes(
        self, backend, expression, layer_info, connection
    ):
        # Regression: the validator must not break the happy path.
        expression.sql = '"deleted_at" IS NULL AND "x" > 5'
        backend._execute_direct(expression, layer_info, connection)
        connection.cursor.return_value.execute.assert_called_once()
