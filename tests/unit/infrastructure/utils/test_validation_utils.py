# -*- coding: utf-8 -*-
"""
Regression tests for validation_utils.is_filter_expression and
should_skip_expression_for_filtering.

Focus: 2026-04-23 fix for operator characters trapped inside SQL string
literals (`'<NULL>'`) being mistaken for top-level comparison operators.
That false positive made the favorites controller push a standalone
COALESCE display expression into the filter widget, which then reached
PostgreSQL as `WHERE COALESCE(...)` → "argument of WHERE must be type
boolean".

Module tested: infrastructure.utils.validation_utils
"""
# NOTE: importing ``infrastructure.utils.validation_utils`` through the
# package triggers ``infrastructure/utils/__init__.py``, which in turn imports
# ``provider_utils`` with a triple-dot relative import that requires the
# plugin to be loaded under its parent package (``filter_mate.*``).
# In the unit-test environment pytest uses the plugin dir as the rootdir, so
# that parent package doesn't exist and the collection fails.
# We load ``validation_utils.py`` straight from disk to sidestep the chain.
import importlib.util
from pathlib import Path

_VALIDATION_UTILS_PATH = (
    Path(__file__).resolve().parents[4]
    / "infrastructure" / "utils" / "validation_utils.py"
)
_spec = importlib.util.spec_from_file_location(
    "filter_mate_validation_utils_under_test", _VALIDATION_UTILS_PATH
)
_validation_utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_validation_utils)

_blank_sql_string_literals = _validation_utils._blank_sql_string_literals
is_filter_expression = _validation_utils.is_filter_expression
should_skip_expression_for_filtering = _validation_utils.should_skip_expression_for_filtering


class TestBlankSqlStringLiterals:
    """_blank_sql_string_literals preserves quotes but clears literal content."""

    def test_no_quotes_is_identity(self):
        assert _blank_sql_string_literals('"field" > 1000') == '"field" > 1000'

    def test_single_literal_blanked(self):
        # Contents blanked, outer quotes kept, length preserved.
        src = "COALESCE(\"id\", '<NULL>')"
        out = _blank_sql_string_literals(src)
        assert len(out) == len(src)
        assert out == "COALESCE(\"id\", '      ')"

    def test_multiple_literals_blanked(self):
        src = "a = 'foo' OR b = 'bar'"
        out = _blank_sql_string_literals(src)
        assert out == "a = '   ' OR b = '   '"

    def test_escaped_quote_stays_in_literal(self):
        # '' inside a literal is an escape, not a terminator.
        src = "name = 'O''Brien'"
        out = _blank_sql_string_literals(src)
        assert len(out) == len(src)
        # The whole 'O''Brien' literal is blanked (including the escape),
        # and we do NOT exit the literal on the doubled quote.
        assert out == "name = '        '"


class TestIsFilterExpressionFalsePositive:
    """Display expressions with operator-looking literal content must NOT
    be misreported as filter expressions."""

    def test_coalesce_with_null_placeholder_is_not_a_filter(self):
        # Exact shape from the 2026-04-23 bug report.
        expr = "COALESCE( \"identifier\", '<NULL>' )"
        assert is_filter_expression(expr) is False

    def test_coalesce_with_inequality_literal_is_not_a_filter(self):
        expr = "COALESCE(\"label\", '>invalid<')"
        assert is_filter_expression(expr) is False

    def test_concat_with_operator_literal_is_not_a_filter(self):
        expr = "CONCAT(\"a\", ' != ', \"b\")"
        assert is_filter_expression(expr) is False


class TestIsFilterExpressionValidFilters:
    """Valid boolean filters (including ones with literal content that
    *looks* like an operator) must still be recognised."""

    def test_simple_comparison(self):
        assert is_filter_expression('"population" > 1000') is True

    def test_equality(self):
        assert is_filter_expression('"status" = 1') is True

    def test_in_clause(self):
        assert is_filter_expression('"id" IN (1, 2, 3)') is True

    def test_is_not_null(self):
        assert is_filter_expression('"name" IS NOT NULL') is True

    def test_like_with_literal_containing_angle_brackets(self):
        # The '<' inside the literal was previously the only trigger; now
        # only the actual LIKE operator should drive the decision.
        assert is_filter_expression("\"desc\" LIKE '<prefix>%'") is True

    def test_equality_against_placeholder_literal(self):
        # Real filter with the same '<NULL>' placeholder as a comparison value.
        assert is_filter_expression("\"code\" = '<NULL>'") is True

    def test_and_combined(self):
        assert is_filter_expression('"a" = 1 AND "b" > 2') is True

    def test_coalesce_inside_a_comparison_still_a_filter(self):
        # COALESCE used as a value inside a real predicate: the outer '='
        # makes it a filter. Unchanged by the fix.
        expr = "COALESCE(\"label\", '<NULL>') = 'foo'"
        assert is_filter_expression(expr) is True


class TestShouldSkipExpressionForFiltering:
    """should_skip_expression_for_filtering must short-circuit the favorites
    controller path for standalone display expressions, even when the literal
    carries characters that look like operators."""

    def test_standalone_coalesce_with_null_placeholder_is_skipped(self):
        # Regression for the 2026-04-23 favorite-load bug: the favorites
        # controller calls this to decide whether to drop the expression
        # before pushing it to the filtering widget.
        expr = "COALESCE( \"identifier\", '<NULL>' )"
        skip, reason = should_skip_expression_for_filtering(expr)
        assert skip is True
        assert 'COALESCE' in reason

    def test_real_filter_is_not_skipped(self):
        skip, _ = should_skip_expression_for_filtering('"population" > 1000')
        assert skip is False

    def test_empty_expression_is_skipped(self):
        skip, _ = should_skip_expression_for_filtering('')
        assert skip is True
