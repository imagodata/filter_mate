# -*- coding: utf-8 -*-
"""Similar features of a vector layer: the expression built from the clicked value (2026-10-18)."""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location("fm_similar_features", ROOT / "ui/tools/similar_features_tool.py")
similar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(similar)


class TestQuotedValue:
    def test_strings_are_quoted_and_escaped(self):
        assert similar.quoted_value("Llo") == "'Llo'"
        assert similar.quoted_value("l'Église") == "'l''Église'"

    def test_numbers_and_booleans_are_literals(self):
        assert similar.quoted_value(66) == "66"
        assert similar.quoted_value(2.5) == "2.5"
        assert similar.quoted_value(True) == "TRUE"

    def test_none_is_null(self):
        assert similar.quoted_value(None) == "NULL"


class TestEqualityExpression:
    def test_a_field_compares_its_value(self):
        assert similar.equality_expression('"commune"', "Llo") == "(\"commune\") = 'Llo'"

    def test_an_expression_is_parenthesised(self):
        assert similar.equality_expression("round(\"surface\" / 100)", 12) == "(round(\"surface\" / 100)) = 12"

    def test_a_null_value_uses_is_null(self):
        assert similar.equality_expression('"nature"', None) == '("nature") IS NULL'

    def test_no_expression_gives_nothing(self):
        assert similar.equality_expression("", 3) == ""
        assert similar.equality_expression("   ", None) == ""


def test_the_tool_needs_qgis_but_the_helpers_do_not():
    # Without QGIS the module still imports; with it the map tool class exists.
    assert hasattr(similar, "equality_expression")
    assert (similar.QgsMapTool is None) == (not hasattr(similar, "SimilarFeaturesTool"))
