# -*- coding: utf-8 -*-
"""The sanitizer never rewrites the text of a value or of a column name.

2026-10-17: every subset reaches setSubsetString through
safe_set_subset_string -> sanitize_subset_string. Its regular expressions ran
on the whole string, so values were rewritten and the filter silently matched
other features (or none):

- ``'Plages, dunes et sable'`` -> ``'Plages, dunes AND sable'`` (French
  operator phase, case-insensitive, inside the literal);
- ``"nom" IN ('a', 'b)')`` lost the ``)`` of its value (parentheses counted
  inside literals);
- ``'Saint  Jean'`` lost one of its two spaces (whitespace phase);
- ``... AND ( "actif" )`` lost a real boolean condition.

Module tested: core.filter.expression_sanitizer, core.filter.sql_quotes
"""
import pytest

from core.filter.expression_sanitizer import sanitize_subset_string
from core.filter.sql_quotes import mask_quoted, map_outside_quotes, qgis_literals_to_sql, unmask_quoted


class TestSqlQuotes:
    @pytest.mark.parametrize("text", [
        "\"nom\" = 'l''Ariège'",
        "\"a \"\"b\"\"\" = 'x'",
        "\"l'x\" = 'say \"hi\"'",
        "'unterminated",
        "no quotes at all",
        "",
    ])
    def test_mask_then_unmask_is_identity(self, text):
        masked, parts = mask_quoted(text)
        assert unmask_quoted(masked, parts) == text
        assert "'" not in masked and '"' not in masked

    def test_doubled_quotes_stay_inside_their_literal(self):
        masked, parts = mask_quoted("\"nom\" = 'l''ET'' ' ET \"x\" = 1")
        assert list(parts) == ['"nom"', "'l''ET'' '", '"x"']
        assert ' ET ' in masked

    def test_transform_only_sees_unquoted_text(self):
        result = map_outside_quotes("\"et\" = 'et' et 1", lambda s: s.replace('et', 'AND'))
        assert result == "\"et\" = 'et' AND 1"

    def test_backslash_escaped_quote_stays_inside_its_literal(self):
        masked, parts = mask_quoted("\"nom\" = 'it\\'s et' ET \"x\" = 1")
        assert list(parts) == ['"nom"', "'it\\'s et'", '"x"']
        assert ' ET ' in masked

    @pytest.mark.parametrize("text, hidden", [
        ("\"a\" = 1 -- et ou\n AND \"b\" = 2", "-- et ou\n"),
        ("\"a\" = 1 /* et ou */ AND \"b\" = 2", "/* et ou */"),
        ("\"a\" = $$it's et$$ AND \"b\" = 1", "$$it's et$$"),
        ("\"a\" = $q$it's$q$ AND \"b\" = 1", "$q$it's$q$"),
    ])
    def test_comments_and_dollar_quotes_are_hidden(self, text, hidden):
        masked, parts = mask_quoted(text)
        assert hidden in parts
        assert unmask_quoted(masked, parts) == text

    @pytest.mark.parametrize("text", [
        "\"a\" = 1 AND \x020\x03",
        "x = '\x020\x03' AND y = \x027\x03",
        "\x05\x04",
    ])
    def test_placeholder_characters_in_the_text_are_restored_verbatim(self, text):
        masked, parts = mask_quoted(text)
        assert unmask_quoted(masked, parts) == text
        assert sanitize_subset_string(text) is not None  # no IndexError

    def test_qgis_backslash_escapes_become_sql_ones(self):
        assert qgis_literals_to_sql(["'it\\'s'", "'C:\\\\'", '"x\\\'"', "'plain'"]) == [
            "'it''s'", "'C:\\'", '"x\\\'"', "'plain'"]


class TestCommentsKeepTheirContent:
    def test_operators_in_a_line_comment_are_not_rewritten(self):
        subset = "\"a\" = 1 -- et ou non\nAND \"b\" = 2"
        assert sanitize_subset_string(subset) == subset

    def test_newline_ending_a_comment_survives_whitespace_cleanup(self):
        result = sanitize_subset_string("\"a\" = 1   -- c\n\n   AND \"b\" = 2")
        assert result == "\"a\" = 1 -- c\n AND \"b\" = 2"


class TestFrenchOperatorsOutsideQuotes:
    @pytest.mark.parametrize("subset", [
        "\"libelle\" = 'Plages, dunes et sable'",
        "\"libelle\" = 'Plages, dunes ET sable'",
        "\"commune\" = 'Pont ou Rivière'",
        "\"avis\" = 'oui non peut-être'",
        "\"lieu\" IN ('Bois et forêts', 'Prés ou landes')",
        "\"champ et autre\" = 1",
    ])
    def test_literal_and_identifier_text_is_kept(self, subset):
        assert sanitize_subset_string(subset) == subset

    def test_uppercase_operator_outside_quotes_is_normalized(self):
        subset = "\"a\" = 'x et y' ET \"b\" = 2"
        assert sanitize_subset_string(subset) == "\"a\" = 'x et y' AND \"b\" = 2"

    def test_et_non_becomes_and_not(self):
        assert sanitize_subset_string('("a" = 1) ET NON ("b" = 2)') == '("a" = 1) AND NOT ("b" = 2)'

    def test_ou_between_parentheses(self):
        assert sanitize_subset_string('("a" = 1) OU ("b" = 2)') == '("a" = 1) OR ("b" = 2)'

    def test_lowercase_words_outside_quotes_are_not_operators(self):
        # An unquoted lowercase column called "ou" (shapefile) is not an operator.
        subset = '"a" = 1 AND ou = 2'
        assert sanitize_subset_string(subset) == subset


class TestStructuralPhasesOutsideQuotes:
    def test_closing_parenthesis_inside_a_value_is_kept(self):
        subset = "\"nom\" IN ('a', 'b)')"
        assert sanitize_subset_string(subset) == subset

    def test_excess_closing_parenthesis_outside_quotes_is_still_dropped(self):
        assert sanitize_subset_string("(\"nom\" = 'a)'))") == "(\"nom\" = 'a)')"

    def test_spaces_inside_a_value_are_kept(self):
        subset = "\"nom\" = 'Saint  Jean'   AND  \"b\" = 1"
        assert sanitize_subset_string(subset) == "\"nom\" = 'Saint  Jean' AND \"b\" = 1"

    def test_and_or_inside_a_value_are_not_orphan_operators(self):
        subset = "\"nom\" = 'AND '"
        assert sanitize_subset_string(subset) == subset
        subset = "\"nom\" = ' OR OR x'"
        assert sanitize_subset_string(subset) == subset

    def test_boolean_column_condition_is_kept(self):
        subset = '"nature" = \'Route\' AND ( "actif" )'
        assert sanitize_subset_string(subset) == subset

    def test_display_coalesce_still_stripped(self):
        subset = "\"a\" = 1 AND ( COALESCE( \"LABEL\", '<NULL>' ) )"
        assert sanitize_subset_string(subset) == '"a" = 1'


class TestDisplayExpressionPhaseOutsideQuotes:
    """PHASE 1 (COALESCE / CASE glued to a filter) only sees unquoted text."""

    @pytest.mark.parametrize("subset", [
        "\"a\" = 1 AND \"nom\" = 'x AND (coalesce(z))'",
        "\"a\" = 1 AND \"nom\" = 'x AND ( CASE WHEN 1 THEN true END )'",
    ])
    def test_value_that_looks_like_a_display_expression_is_kept(self, subset):
        assert sanitize_subset_string(subset) == subset

    def test_glued_coalesce_with_a_value_containing_a_parenthesis_is_dropped(self):
        assert sanitize_subset_string("\"a\" = 1 AND ( COALESCE( \"LABEL\", 'x)' ) )") == '"a" = 1'


class TestTextColumnOperands:
    """PHASE 2.5: ( "text column" ) operands of a stored subset (2026-10-17 safe version)."""

    @pytest.mark.parametrize("subset, expected", [
        ('( "x" = 1 ) AND ( "importance" )', '( "x" = 1 )'),
        ('( "importance" ) AND ( "x" = 1 )', '( "x" = 1 )'),
        ('( "t"."importance" ) OR "x" = 1', '"x" = 1'),
        ('"x" = 1 AND ( "importance"::text )', '"x" = 1'),
        ('( "x" = 1 AND ( "importance" ) )', '( "x" = 1 )'),
    ])
    def test_text_column_operand_is_dropped(self, subset, expected):
        assert sanitize_subset_string(subset, text_fields={'importance'}) == expected

    @pytest.mark.parametrize("subset", [
        '( "x" = 1 ) AND ( "actif" )',                       # boolean column: a real condition
        '( "x" = 1 ) AND ( "importance" ) = \'1\'',           # compared: not an operand
        "\"x\" = 1 AND \"nom\" = 'AND ( \"importance\" )'",   # inside a value
    ])
    def test_other_operands_are_kept(self, subset):
        assert sanitize_subset_string(subset, text_fields={'importance', 'nom'}) == subset

    def test_without_column_types_nothing_is_dropped(self):
        subset = '( "x" = 1 ) AND ( "importance" )'
        assert sanitize_subset_string(subset) == subset
