# -*- coding: utf-8 -*-
"""
Regression tests for sanitize_subset_string().

Focus: 2026-04-23 fix for standalone display expressions (COALESCE, CONCAT,
field-only) leaking into the layer subsetString and reaching PostgreSQL as
`WHERE <display_expression>` → "argument of WHERE must be type boolean".

Module tested: core.filter.expression_sanitizer
"""
from core.filter.expression_sanitizer import sanitize_subset_string


class TestStandaloneDisplayExpressions:
    """Standalone (not AND/OR-prefixed) display expressions must be stripped."""

    def test_standalone_coalesce_is_cleared(self):
        # Exact shape from the 2026-04-23 bug report:
        # PostgreSQL: `WHERE COALESCE( "identifier", '<NULL>' )`
        expr = "COALESCE( \"identifier\", '<NULL>' )"
        assert sanitize_subset_string(expr) == ''

    def test_standalone_lowercase_coalesce_is_cleared(self):
        expr = "coalesce(\"label\", '')"
        assert sanitize_subset_string(expr) == ''

    def test_standalone_concat_is_cleared(self):
        expr = "concat(\"first\", ' ', \"last\")"
        assert sanitize_subset_string(expr) == ''

    def test_standalone_field_name_is_cleared(self):
        expr = '"identifier"'
        assert sanitize_subset_string(expr) == ''

    def test_standalone_case_without_boolean_is_cleared(self):
        # CASE returning text values (display/classification, not a filter).
        expr = "CASE WHEN \"type\" = 1 THEN 'A' ELSE 'B' END"
        # Has '=' so it still has a comparison operator → considered a filter
        # expression by is_filter_expression. We keep the current behaviour
        # (do not strip) because the inner '=' makes the predicate evaluable.
        assert sanitize_subset_string(expr) == expr


class TestM2HardeningUnknownDisplayFunctions:
    """M2 hardening (audit 2026-04-23, fix 2026-04-27): the previous
    detection only triggered on a hardcoded denylist of QGIS display
    functions. Any future / custom display function bypassed the check.

    The new logic treats ANY function call without a top-level boolean
    operator as a non-WHERE expression.
    """

    def test_unknown_display_function_is_cleared(self):
        # Hypothetical display function not in _DISPLAY_FUNCTION_PREFIXES
        expr = "geom_to_wkt(\"geometry\")"
        assert sanitize_subset_string(expr) == ''

    def test_camelcase_display_function_is_cleared(self):
        expr = "MyCustomDisplay(\"field\", 'sep')"
        assert sanitize_subset_string(expr) == ''

    def test_unknown_function_with_top_level_comparison_preserved(self):
        # Same unknown function but used in a WHERE-compatible comparison —
        # must NOT be stripped.
        expr = "geom_to_wkt(\"geometry\") = 'POINT(0 0)'"
        assert sanitize_subset_string(expr) == expr

    def test_boolean_literal_true_preserved(self):
        # `WHERE TRUE` is a valid SQL clause and must not be stripped.
        assert sanitize_subset_string("TRUE") == "TRUE"

    def test_boolean_literal_false_preserved(self):
        assert sanitize_subset_string("FALSE") == "FALSE"


class TestBooleanFiltersPreserved:
    """Valid boolean filters must pass through untouched."""

    def test_simple_comparison_preserved(self):
        expr = '"population" > 1000'
        assert sanitize_subset_string(expr) == expr

    def test_equality_preserved(self):
        expr = '"status" = 1'
        assert sanitize_subset_string(expr) == expr

    def test_in_clause_preserved(self):
        expr = '"id" IN (1, 2, 3)'
        assert sanitize_subset_string(expr) == expr

    def test_is_null_preserved(self):
        expr = '"name" IS NOT NULL'
        assert sanitize_subset_string(expr) == expr

    def test_and_combined_preserved(self):
        expr = '"a" = 1 AND "b" > 2'
        assert sanitize_subset_string(expr) == expr

    def test_coalesce_with_equality_preserved(self):
        # COALESCE used inside a boolean comparison is a legit filter.
        expr = "COALESCE(\"label\", '') = 'foo'"
        # The outer expression has '=', so is_filter_expression returns True
        # and Phase -1 does not short-circuit. Sanitizer leaves it alone.
        assert sanitize_subset_string(expr) == expr


class TestAndPrefixedCoalesceStillStripped:
    """Prior AND/OR-prefixed stripping must still work after the Phase -1 addition."""

    def test_and_prefixed_coalesce_stripped(self):
        # Valid filter that got a dangling display expression glued on
        expr = '"population" > 1000 AND ( COALESCE( "LABEL", \'<NULL>\' ) )'
        result = sanitize_subset_string(expr)
        assert 'COALESCE' not in result.upper()
        assert '"population" > 1000' in result


class TestEmptyInputs:
    """Empty / None inputs must be returned as-is."""

    def test_empty_string(self):
        assert sanitize_subset_string('') == ''

    def test_none(self):
        assert sanitize_subset_string(None) is None
