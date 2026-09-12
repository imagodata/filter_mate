# -*- coding: utf-8 -*-
"""
Unit tests for PostgreSQL Schema Manager.

Tests the pure functions in schema_manager.py:
- validate_connection(): Connection object validation
- ensure_temp_schema_exists(): Schema creation with fallbacks
- schema_exists(): Schema existence check
- ensure_table_stats(): Statistics management
- execute_commands(): Transaction handling
- cleanup_session_materialized_views(): Session cleanup
- get_session_prefixed_name(): Name generation
- create_simple_materialized_view_sql(): SQL generation
- parse_case_to_where_clauses(): CASE parsing

All database operations are mocked.
"""
import sys
import types
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Mock setup
# ---------------------------------------------------------------------------

def _ensure_schema_mocks():
    ROOT = "filter_mate"
    if ROOT not in sys.modules:
        fm = types.ModuleType(ROOT)
        fm.__path__ = []
        fm.__package__ = ROOT
        sys.modules[ROOT] = fm

    mocks = {
        f"{ROOT}.infrastructure": MagicMock(),
        f"{ROOT}.infrastructure.database": MagicMock(),
        f"{ROOT}.infrastructure.database.sql_utils": MagicMock(),
    }
    # Provide a real sanitize function for testing
    mocks[f"{ROOT}.infrastructure.database.sql_utils"].sanitize_sql_identifier = lambda x: x

    for name, mock_obj in mocks.items():
        if name not in sys.modules:
            sys.modules[name] = mock_obj


_ensure_schema_mocks()

# Import via importlib
import importlib.util
import os

_schema_path = os.path.normpath(os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "..", "..",
    "adapters", "backends", "postgresql", "schema_manager.py"
))

_spec = importlib.util.spec_from_file_location(
    "filter_mate.adapters.backends.postgresql.schema_manager",
    _schema_path,
)
_mod = importlib.util.module_from_spec(_spec)
_mod.__package__ = "filter_mate.adapters.backends.postgresql"
sys.modules[_mod.__name__] = _mod
_spec.loader.exec_module(_mod)

validate_connection = _mod.validate_connection
ensure_temp_schema_exists = _mod.ensure_temp_schema_exists
schema_exists = _mod.schema_exists
ensure_table_stats = _mod.ensure_table_stats
execute_commands = _mod.execute_commands
cleanup_session_materialized_views = _mod.cleanup_session_materialized_views
get_session_prefixed_name = _mod.get_session_prefixed_name
create_simple_materialized_view_sql = _mod.create_simple_materialized_view_sql
parse_case_to_where_clauses = _mod.parse_case_to_where_clauses


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def mock_connexion():
    """Create a mock psycopg2 connection."""
    conn = MagicMock()
    conn.closed = False
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn


@pytest.fixture
def mock_cursor(mock_connexion):
    """Return the cursor mock from the connexion fixture."""
    return mock_connexion.cursor.return_value.__enter__.return_value


# ===========================================================================
# Tests -- validate_connection
# ===========================================================================

class TestValidateConnection:
    def test_none_connection(self):
        valid, msg = validate_connection(None)
        assert valid is False
        assert "None" in msg

    def test_string_connection(self):
        valid, msg = validate_connection("host=localhost dbname=test")
        assert valid is False
        assert "string" in msg

    def test_missing_cursor_method(self):
        obj = object()
        valid, msg = validate_connection(obj)
        assert valid is False
        assert "cursor" in msg

    def test_closed_connection(self):
        conn = MagicMock()
        conn.closed = True
        valid, msg = validate_connection(conn)
        assert valid is False
        assert "closed" in msg

    def test_valid_connection(self):
        conn = MagicMock()
        conn.closed = False
        valid, msg = validate_connection(conn)
        assert valid is True
        assert msg is None

    def test_connection_without_closed_attribute(self):
        """Connection object without 'closed' attr should still be valid."""
        conn = MagicMock(spec=["cursor"])
        del conn.closed  # Remove the attribute
        valid, msg = validate_connection(conn)
        assert valid is True


# ===========================================================================
# Tests -- ensure_temp_schema_exists
# ===========================================================================

class TestEnsureTempSchemaExists:
    def test_raises_on_none_connection(self):
        with pytest.raises(Exception, match="None"):
            ensure_temp_schema_exists(None, "filtermate_temp")

    def test_raises_on_string_connection(self):
        with pytest.raises(Exception, match="string"):
            ensure_temp_schema_exists("host=localhost", "filtermate_temp")

    def test_raises_on_invalid_object(self):
        with pytest.raises(Exception, match="not a valid connection object"):
            ensure_temp_schema_exists(object(), "filtermate_temp")

    def test_raises_on_closed_connection(self):
        conn = MagicMock()
        conn.closed = True
        with pytest.raises(Exception, match="closed"):
            ensure_temp_schema_exists(conn, "filtermate_temp")

    def test_returns_schema_if_already_exists(self, mock_connexion, mock_cursor):
        mock_cursor.fetchone.return_value = ("filtermate_temp",)
        result = ensure_temp_schema_exists(mock_connexion, "filtermate_temp")
        assert result == "filtermate_temp"

    def test_creates_schema_successfully(self, mock_connexion, mock_cursor):
        # Schema doesn't exist yet
        mock_cursor.fetchone.return_value = None
        result = ensure_temp_schema_exists(mock_connexion, "filtermate_temp")
        assert result == "filtermate_temp"

    def test_falls_back_to_public_on_all_failures(self):
        """If all CREATE SCHEMA attempts fail, returns 'public'."""
        conn = MagicMock()
        conn.closed = False
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        # Schema check says it doesn't exist
        cursor.fetchone.return_value = None
        # All CREATE SCHEMA attempts raise
        cursor.execute.side_effect = Exception("permission denied")

        result = ensure_temp_schema_exists(conn, "filtermate_temp")
        assert result == "public"


# ===========================================================================
# Tests -- schema_exists
# ===========================================================================

class TestSchemaExists:
    def test_returns_true_when_exists(self, mock_connexion, mock_cursor):
        mock_cursor.fetchone.return_value = ("filtermate_temp",)
        assert schema_exists(mock_connexion, "filtermate_temp") is True

    def test_returns_false_when_not_exists(self, mock_connexion, mock_cursor):
        mock_cursor.fetchone.return_value = None
        assert schema_exists(mock_connexion, "filtermate_temp") is False

    def test_returns_false_on_error(self, mock_connexion, mock_cursor):
        mock_cursor.execute.side_effect = Exception("connection lost")
        assert schema_exists(mock_connexion, "filtermate_temp") is False


# ===========================================================================
# Tests -- execute_commands
# ===========================================================================

class TestExecuteCommands:
    def test_executes_all_commands(self, mock_connexion, mock_cursor):
        commands = ["SELECT 1", "SELECT 2", "SELECT 3"]
        result = execute_commands(mock_connexion, commands)
        assert result is True
        assert mock_cursor.execute.call_count == 3

    def test_empty_commands(self, mock_connexion):
        result = execute_commands(mock_connexion, [])
        assert result is True

    def test_returns_false_on_error(self, mock_connexion, mock_cursor):
        mock_cursor.execute.side_effect = Exception("syntax error")
        result = execute_commands(mock_connexion, ["BAD SQL"])
        assert result is False


# ===========================================================================
# Tests -- get_session_prefixed_name
# ===========================================================================

class TestGetSessionPrefixedName:
    def test_with_session_id(self):
        result = get_session_prefixed_name("my_layer", "abc12345")
        assert result == "abc12345_my_layer"

    def test_without_session_id(self):
        result = get_session_prefixed_name("my_layer", None)
        assert result == "my_layer"

    def test_empty_session_id(self):
        result = get_session_prefixed_name("my_layer", "")
        assert result == "my_layer"


# ===========================================================================
# Tests -- create_simple_materialized_view_sql
# ===========================================================================

class TestCreateSimpleMaterializedViewSql:
    def test_generates_valid_sql(self):
        sql = create_simple_materialized_view_sql(
            schema="filtermate_temp",
            name="abc_layer1",
            sql_subset_string="SELECT * FROM public.roads WHERE type = 'highway'"
        )
        assert "CREATE MATERIALIZED VIEW" in sql
        assert "fm_temp_mv_abc_layer1" in sql
        assert "filtermate_temp" in sql
        assert "WITH DATA" in sql

    def test_raises_on_empty_subset(self):
        with pytest.raises(ValueError, match="empty"):
            create_simple_materialized_view_sql("s", "n", "")

    def test_raises_on_none_subset(self):
        with pytest.raises(ValueError):
            create_simple_materialized_view_sql("s", "n", None)

    def test_raises_on_whitespace_only(self):
        with pytest.raises(ValueError, match="empty"):
            create_simple_materialized_view_sql("s", "n", "   ")


# ===========================================================================
# Tests -- parse_case_to_where_clauses
# ===========================================================================

class TestParseCaseToWhereClauses:
    def test_parses_simple_case(self):
        case_expr = "CASE WHEN status = 'active' THEN 1 WHEN status = 'inactive' THEN 0 END"
        result = parse_case_to_where_clauses(case_expr)
        assert len(result) == 2
        assert "status = 'active'" in result[0]
        assert "status = 'inactive'" in result[1]

    def test_empty_case(self):
        result = parse_case_to_where_clauses("")
        # Empty string should not produce meaningful clauses
        assert isinstance(result, list)


# ===========================================================================
# Tests -- cleanup_session_materialized_views
# ===========================================================================

class TestCleanupSessionMaterializedViews:
    def test_returns_zero_on_empty_session_id(self, mock_connexion):
        count = cleanup_session_materialized_views(mock_connexion, "filtermate_temp", "")
        assert count == 0

    def test_returns_zero_on_none_session_id(self, mock_connexion):
        count = cleanup_session_materialized_views(mock_connexion, "filtermate_temp", None)
        assert count == 0

    def test_drops_matching_views(self, mock_connexion, mock_cursor):
        mock_cursor.fetchall.return_value = [
            ("fm_temp_mv_abc123_layer1",),
            ("fm_temp_mv_abc123_layer2",),
        ]
        count = cleanup_session_materialized_views(
            mock_connexion, "filtermate_temp", "abc123"
        )
        assert count == 2

    def test_returns_zero_on_error(self):
        conn = MagicMock()
        conn.closed = False
        conn.cursor.side_effect = Exception("connection lost")
        count = cleanup_session_materialized_views(conn, "filtermate_temp", "abc123")
        assert count == 0


# ===========================================================================
# ensure_table_stats (PERF 2026-09-12)
# ===========================================================================

class TestEnsureTableStats:
    """pg_stat_user_tables lookup, ANALYZE when never analyzed, session cache."""

    @pytest.fixture(autouse=True)
    def _fresh_cache(self):
        _mod.clear_table_stats_cache()
        yield
        _mod.clear_table_stats_cache()

    def test_analyzed_table_needs_no_analyze(self, mock_connexion, mock_cursor):
        mock_cursor.fetchone.return_value = (True,)

        assert ensure_table_stats(mock_connexion, "ign", "commune", "geometrie") is True

        sql_calls = [call.args[0] for call in mock_cursor.execute.call_args_list]
        assert len(sql_calls) == 1
        assert "pg_stat_user_tables" in sql_calls[0]
        assert "pg_stats" not in sql_calls[0].replace("pg_stat_user_tables", "")
        mock_connexion.commit.assert_not_called()

    def test_never_analyzed_table_gets_analyze(self, mock_connexion, mock_cursor):
        mock_cursor.fetchone.return_value = (False,)

        assert ensure_table_stats(mock_connexion, "ign", "commune", "geometrie") is True

        sql_calls = [call.args[0] for call in mock_cursor.execute.call_args_list]
        assert len(sql_calls) == 2
        assert sql_calls[1] == 'ANALYZE "ign"."commune";'
        mock_connexion.commit.assert_called_once()

    def test_unknown_table_is_treated_as_never_analyzed(self, mock_connexion, mock_cursor):
        mock_cursor.fetchone.return_value = None
        assert ensure_table_stats(mock_connexion, "ign", "vue", "geometrie") is True
        assert mock_cursor.execute.call_count == 2

    def test_second_call_is_served_from_cache(self, mock_connexion, mock_cursor):
        mock_cursor.fetchone.return_value = (True,)
        ensure_table_stats(mock_connexion, "ign", "commune", "geometrie")
        ensure_table_stats(mock_connexion, "ign", "commune", "geometrie")
        assert mock_cursor.execute.call_count == 1

        # A different table is a different cache key
        ensure_table_stats(mock_connexion, "ign", "batiment", "geometrie")
        assert mock_cursor.execute.call_count == 2

    def test_cache_can_be_bypassed(self, mock_connexion, mock_cursor):
        mock_cursor.fetchone.return_value = (True,)
        ensure_table_stats(mock_connexion, "ign", "commune", "geometrie")
        ensure_table_stats(mock_connexion, "ign", "commune", "geometrie", use_cache=False)
        assert mock_cursor.execute.call_count == 2

    def test_failure_is_not_cached(self, mock_connexion, mock_cursor):
        mock_cursor.execute.side_effect = RuntimeError("permission denied")
        assert ensure_table_stats(mock_connexion, "ign", "commune", "geometrie") is False
        mock_cursor.execute.side_effect = None
        mock_cursor.fetchone.return_value = (True,)
        assert ensure_table_stats(mock_connexion, "ign", "commune", "geometrie") is True
        assert mock_cursor.execute.call_count == 2
