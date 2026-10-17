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
from core.filter.sql_quotes import mask_quoted, map_outside_quotes, unmask_quoted


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
        assert parts == ['"nom"', "'l''ET'' '", '"x"']
        assert ' ET ' in masked

    def test_identifiers_can_stay_visible(self):
        masked, parts = mask_quoted("\"l'x\" = 'a'", identifiers=False)
        assert masked.startswith("\"l'x\" = ")
        assert parts == ["'a'"]

    def test_transform_only_sees_unquoted_text(self):
        result = map_outside_quotes("\"et\" = 'et' et 1", lambda s: s.replace('et', 'AND'))
        assert result == "\"et\" = 'et' AND 1"


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
