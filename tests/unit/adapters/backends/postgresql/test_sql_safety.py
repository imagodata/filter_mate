"""S2 — defense-in-depth WHERE-clause / identifier guards.

Issue: ``_execute_direct`` and ``_execute_with_mv`` f-string the upstream
sanitizer's output straight into ``cursor.execute()``. The sanitizer is
best-effort string surgery (and S3 confirmed at least one ``NOT(...)``
bypass), so a payload like ``NOT(1=1); DROP TABLE x; --`` could survive.
:mod:`sql_safety` adds a strict deny-list immediately before execute.
"""
from __future__ import annotations

import importlib.util
import os

import pytest

# Load sql_safety.py directly: the package's __init__ cascades into adapter
# imports that need a running QGIS, which we don't have in unit tests.
_SAFETY_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..", "..", "..",
        "adapters", "backends", "postgresql", "sql_safety.py",
    )
)
_spec = importlib.util.spec_from_file_location("filter_mate_sql_safety", _SAFETY_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

SqlInjectionAttempt = _mod.SqlInjectionAttempt
validate_identifier = _mod.validate_identifier
validate_where_clause = _mod.validate_where_clause


class TestLegitimateWhereClausesPass:
    """Real expressions QGIS users write must not trip the guard."""

    @pytest.mark.parametrize(
        "expr",
        [
            '"status" = \'active\'',
            '"x" > 5 AND "y" < 10',
            '"name" LIKE \'foo%\'',
            '"col" IN (1, 2, 3)',
            'EXISTS (SELECT 1 FROM other)',
            'NOT ("disabled" = TRUE)',
            '"created_at" >= \'2020-01-01\'',
            # Column names that *contain* DDL keywords as substrings — must pass
            # because the regex uses word boundaries and the identifier is
            # double-quoted (scrubbed before pattern match).
            '"deleted_at" IS NULL',
            '"insert_user" = \'alice\'',
            '"updated_by" IS NOT NULL',
            # Single-quoted string literals containing keywords / semicolons —
            # also legitimate; the scrub pass blanks them out.
            "\"reason\" = 'DROP request from user; admin'",
            "\"comment\" = 'see /* note */ file'",
            # Doubled-quote escapes in a literal.
            "\"label\" = 'O''Brien'",
            # Empty / whitespace — caller's problem, not ours.
            "",
            "   ",
        ],
    )
    def test_legitimate_passes(self, expr):
        validate_where_clause(expr)


class TestStatementSeparator:
    @pytest.mark.parametrize(
        "expr",
        [
            "1=1; DROP TABLE users",
            "NOT(1=1); DELETE FROM y",
            '"col" = 1; SELECT pg_sleep(10)',
        ],
    )
    def test_chained_statement_rejected(self, expr):
        with pytest.raises(SqlInjectionAttempt, match="statement separator"):
            validate_where_clause(expr)

    def test_semicolon_inside_string_literal_passes(self):
        # The semicolon is part of a quoted value, not a separator.
        validate_where_clause("\"label\" = 'a;b'")


class TestComments:
    @pytest.mark.parametrize(
        "expr",
        [
            '"col" = 1 -- AND "secret" = \'x\'',
            '"col" = 1 /* malicious */ OR 1=1',
            '"col" = 1 */ DROP TABLE users',
        ],
    )
    def test_comments_rejected(self, expr):
        with pytest.raises(SqlInjectionAttempt, match="comment"):
            validate_where_clause(expr)

    def test_dashes_inside_string_literal_pass(self):
        validate_where_clause("\"note\" = 'see -- below'")


class TestDdlDmlKeywords:
    @pytest.mark.parametrize(
        "expr,keyword",
        [
            ('"x" = 1 OR DROP TABLE users', "DROP"),
            ('1=1 UNION DELETE FROM y', "DELETE"),
            ('"x" = 1) ; INSERT INTO admins VALUES (1)', "INSERT"),  # also caught by ';'
            ('"x" = TRUNCATE("y")', "TRUNCATE"),
            ('"x" = ALTER("y")', "ALTER"),
            ('"x" = GRANT ALL', "GRANT"),
            ('"x" = EXEC sp_evil()', "EXEC"),
            ('"x" = MERGE INTO bla', "MERGE"),
            ('"x" = REINDEX TABLE bla', "REINDEX"),
        ],
    )
    def test_keyword_rejected(self, expr, keyword):
        with pytest.raises(SqlInjectionAttempt) as exc_info:
            validate_where_clause(expr)
        # Reason mentions the offending keyword (or the ';' separator if also
        # present — both are valid first-failure reports).
        assert keyword in str(exc_info.value) or "separator" in str(exc_info.value)

    def test_keyword_inside_quoted_identifier_passes(self):
        # "DROP" as an identifier is technically legal (it's just a column
        # named DROP). The scrub pass blanks the quoted identifier so the
        # regex doesn't see it.
        validate_where_clause('"DROP" = 1')

    def test_keyword_case_insensitive(self):
        with pytest.raises(SqlInjectionAttempt, match="DROP"):
            validate_where_clause('"x" = 1 OR drop TABLE y')


class TestEscalationFunctions:
    @pytest.mark.parametrize(
        "expr,fn",
        [
            ('1=1 OR pg_sleep(10) IS NULL', "pg_sleep"),
            ('"x" = pg_read_file(\'/etc/passwd\')', "pg_read_file"),
            ('1 = pg_ls_dir(\'/\')', "pg_ls_dir"),
            ('1 = lo_import(\'/etc/shadow\')', "lo_import"),
            ('"x" = dblink(\'host=evil\', \'SELECT 1\')', "dblink"),
            ('1 = copy_from_program(\'curl evil.example\')', "copy_from_program"),
        ],
    )
    def test_dangerous_function_rejected(self, expr, fn):
        with pytest.raises(SqlInjectionAttempt, match=fn):
            validate_where_clause(expr)


class TestSurvivedSanitizerBypasses:
    """Payloads that the upstream NOT(...) sanitizer bypass (S3) would let through."""

    @pytest.mark.parametrize(
        "expr",
        [
            "NOT(1=1); DROP TABLE x; --",
            "NOT(pg_sleep(10) IS NULL)",
            "EXISTS(SELECT 1) ; DELETE FROM users",
        ],
    )
    def test_known_bypass_blocked(self, expr):
        with pytest.raises(SqlInjectionAttempt):
            validate_where_clause(expr)


class TestValidateIdentifier:
    @pytest.mark.parametrize(
        "name",
        ["id", "fid", "feature_id", "Id", "_pk", "col_123", "a" * 63],
    )
    def test_legitimate_identifiers_pass(self, name):
        assert validate_identifier(name) == name

    @pytest.mark.parametrize(
        "name",
        [
            'id"; DROP TABLE x; --',  # quote-injection attempt
            "1bad",                    # leading digit
            "with space",
            "drop;table",
            "",
            "a" * 64,                  # over 63 chars
            None,                      # type tampering
            123,
        ],
    )
    def test_malformed_identifiers_rejected(self, name):
        with pytest.raises(SqlInjectionAttempt):
            validate_identifier(name)

    def test_kind_label_appears_in_error_message(self):
        with pytest.raises(SqlInjectionAttempt, match="primary key column"):
            validate_identifier("1bad", kind="primary key column")
