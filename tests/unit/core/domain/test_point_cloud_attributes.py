# -*- coding: utf-8 -*-
"""
Tests for core.domain.point_cloud_attributes: the attribute registry and the
chained attribute conditions of the point cloud EXPLORING panel.

PURE PYTHON tests -- no QGIS dependency. Expressions are checked character
by character: they are handed verbatim to ``QgsPointCloudLayer.setSubsetString``.
"""
import ast
import inspect

import pytest

import core.domain.point_cloud_attributes as attributes_module
from core.domain.point_cloud_attributes import (
    FALLBACK_CONDITION_ATTRIBUTES,
    KNOWN_ATTRIBUTES,
    PointCloudAttribute,
    attribute_info,
    canonical_attribute_name,
    condition_attributes,
    condition_clause,
    conditions_criteria,
    conditions_expression,
    conditions_have_or,
    normalize_operator,
    parse_condition,
    parse_conditions,
    quote_attribute,
)
from core.domain.point_cloud_filter_criteria import AttributeRange, PointCloudFilterCriteria

pytestmark = pytest.mark.unit


def _c(attribute, op="between", low=None, high=None, join="AND"):
    return parse_condition({"attribute": attribute, "op": op, "low": low, "high": high, "join": join})


class TestModuleHygiene:
    def test_no_qgis_import(self):
        tree = ast.parse(inspect.getsource(attributes_module))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("qgis")
            elif isinstance(node, ast.Import):
                assert not any(alias.name.startswith("qgis") for alias in node.names)


class TestRegistry:
    def test_known_names_are_unique(self):
        names = [item.name.lower() for item in KNOWN_ATTRIBUTES]
        assert len(names) == len(set(names))

    @pytest.mark.parametrize("name", [
        "X", "Y", "Z", "Intensity", "ReturnNumber", "NumberOfReturns", "Classification", "ScanAngleRank",
        "UserData", "PointSourceId", "GpsTime", "Red", "Green", "Blue", "Infrared", "ScanDirectionFlag",
        "EdgeOfFlightLine", "Synthetic", "KeyPoint", "Withheld", "Overlap", "ScannerChannel", "ClassFlags",
        "HeightAboveGround",
    ])
    def test_usual_las_dimensions_are_registered(self, name):
        assert canonical_attribute_name(name) == name

    def test_integer_attributes_have_no_decimals(self):
        info = attribute_info("Intensity")
        assert (info.integer, info.decimals, info.label) == (True, 0, "Intensity")
        assert attribute_info("ReturnNumber").label == "Return number"

    def test_float_attributes(self):
        z = attribute_info("Z")
        assert (z.integer, z.decimals, z.unit) == (False, 3, "m")
        assert attribute_info("HeightAboveGround").decimals == 2
        assert attribute_info("GpsTime").decimals == 6

    def test_unknown_attribute_gets_the_defaults(self):
        assert attribute_info("Amplitude") == PointCloudAttribute("Amplitude", "Amplitude", "", 3, False)

    def test_aliases_and_case_keep_the_layer_spelling(self):
        info = attribute_info("ScanAngle")
        assert (info.name, info.label, info.unit) == ("ScanAngle", "Scan angle", "°")
        assert attribute_info("gpstime").name == "gpstime"
        assert attribute_info("gpstime").decimals == 6
        assert canonical_attribute_name("ScanChannel") == "ScannerChannel"
        assert canonical_attribute_name("Amplitude") is None


class TestConditionAttributes:
    def test_layer_order_without_x_y(self):
        # Classification is a condition too: "class AND height above the DTM" goes through it
        names = ("X", "Y", "Z", "Classification", "Intensity", "Amplitude", "Z")
        assert condition_attributes(names) == ["Z", "Classification", "Intensity", "Amplitude"]

    def test_unknown_schema_falls_back(self):
        assert condition_attributes(()) == list(FALLBACK_CONDITION_ATTRIBUTES)
        assert condition_attributes((), ["GpsTime", "Z"]) == ["GpsTime", "Z", "Intensity", "ReturnNumber", "NumberOfReturns"]


class TestParseCondition:
    def test_full_condition(self):
        assert parse_condition({"attribute": " Z ", "op": "between", "low": 50, "high": "10", "join": "or"}) == {
            "attribute": "Z", "op": "between", "low": 10.0, "high": 50.0, "join": "OR"}

    def test_operator_aliases(self):
        assert normalize_operator("≠") == normalize_operator("!=") == "<>"
        assert normalize_operator("≥") == ">="
        assert normalize_operator("BETWEEN") == "between"
        assert normalize_operator("LIKE") is None

    def test_missing_operator_is_between(self):
        assert parse_condition({"attribute": "Z", "low": 1})["op"] == "between"

    def test_unusable_conditions(self):
        assert parse_condition(None) is None
        assert parse_condition({"attribute": "", "op": "="}) is None
        assert parse_condition({"attribute": "Z", "op": "~"}) is None

    def test_one_value_operators_keep_low_only(self):
        assert _c("Intensity", ">=", 100, 900) == {
            "attribute": "Intensity", "op": ">=", "low": 100.0, "high": None, "join": "AND"}

    def test_attribute_operand(self):
        assert _c("ReturnNumber", "=", "NumberOfReturns")["low"] == "NumberOfReturns"
        assert _c("ReturnNumber", "=", "3")["low"] == 3.0
        assert _c("Z", "between", "NumberOfReturns", 4)["low"] is None

    def test_non_finite_values_are_dropped(self):
        assert _c("Z", "between", float("nan"), float("inf")) == _c("Z")

    def test_idempotent(self):
        once = _c("Scan Angle", "<>", -2.5, join="OR")
        assert parse_condition(once) == once

    def test_list_drops_junk_and_starts_with_and(self):
        parsed = parse_conditions([{"attribute": "Z", "join": "OR"}, "junk", {"op": "="}])
        assert [c["join"] for c in parsed] == ["AND"]
        assert parse_conditions(None) == []


class TestConditionClause:
    def test_between(self):
        assert condition_clause(_c("Z", "between", 10, 50.5)) == "Z >= 10 AND Z <= 50.5"
        assert condition_clause(_c("Z", "between", None, 50)) == "Z <= 50"
        assert condition_clause(_c("Z", "between", 10)) == "Z >= 10"

    @pytest.mark.parametrize("op,expected", [
        ("=", "Intensity = 300"), ("<>", "Intensity <> 300"), ("!=", "Intensity <> 300"),
        (">=", "Intensity >= 300"), ("<=", "Intensity <= 300"), (">", "Intensity > 300"), ("<", "Intensity < 300"),
    ])
    def test_operators(self, op, expected):
        assert condition_clause(_c("Intensity", op, 300)) == expected

    def test_numbers_like_format_number(self):
        assert condition_clause(_c("GpsTime", ">", 0.1234567)) == "GpsTime > 0.123457"

    def test_quoted_names(self):
        assert condition_clause(_c("Scan Angle", "<", -2)) == '"Scan Angle" < -2'
        assert condition_clause(_c('My"Dim', "=", 1)) == '"My""Dim" = 1'
        assert quote_attribute("Z") == "Z"
        assert quote_attribute("2nd") == '"2nd"'

    def test_attribute_operand(self):
        assert condition_clause(_c("ReturnNumber", "=", "NumberOfReturns")) == "ReturnNumber = NumberOfReturns"
        assert condition_clause(_c("ReturnNumber", "<", "Number Of Returns")) == 'ReturnNumber < "Number Of Returns"'

    def test_incomplete(self):
        assert condition_clause(_c("Z")) == ""
        assert condition_clause(_c("Z", ">=")) == ""


class TestConditionsExpression:
    def test_and_chain(self):
        conditions = [_c("Z", "between", 1, 5), _c("Intensity", ">=", 100)]
        assert conditions_expression(conditions) == "Z >= 1 AND Z <= 5 AND Intensity >= 100"
        assert not conditions_have_or(conditions)

    def test_and_binds_tighter_than_or(self):
        conditions = [_c("Z", "between", 1, 5), _c("Intensity", ">=", 100),
                      _c("ReturnNumber", "=", 1, join="OR"), _c("UserData", "<>", 0, join="AND")]
        assert conditions_expression(conditions) == (
            "(Z >= 1 AND Z <= 5 AND Intensity >= 100) OR (ReturnNumber = 1 AND UserData <> 0)")
        assert conditions_have_or(conditions)

    def test_single_or_group_is_parenthesised(self):
        conditions = [_c("Z", "between", 1, 5), _c("Intensity", ">=", 100, join="OR")]
        assert conditions_expression(conditions) == "(Z >= 1 AND Z <= 5) OR (Intensity >= 100)"

    def test_incomplete_rows_are_ignored(self):
        conditions = [_c("Z"), _c("Intensity", ">=", 100, join="OR"), _c("Z", "between", join="OR"),
                      _c("UserData", "=", 2, join="AND")]
        # The first complete condition starts the chain; the empty OR row does not split it.
        assert conditions_expression(conditions) == "Intensity >= 100 AND UserData = 2"
        assert not conditions_have_or(conditions)

    def test_empty(self):
        assert conditions_expression([]) == ""
        assert conditions_expression([_c("Z")]) == ""


class TestConditionsCriteria:
    def test_and_chain_of_ranges(self):
        ranges, extra = conditions_criteria([_c("Z", "between", 1, 5), _c("Intensity", ">=", 100),
                                             _c("GpsTime", "<=", 9)])
        assert ranges == (AttributeRange("Z", 1, 5), AttributeRange("Intensity", 100, None),
                          AttributeRange("GpsTime", None, 9))
        assert extra == ()

    def test_other_operators_become_extra_clauses(self):
        ranges, extra = conditions_criteria([_c("ReturnNumber", "=", "NumberOfReturns"), _c("Z", ">=", 3),
                                             _c("Scan Angle", "between", 1, 2), _c("Intensity", ">", 4)])
        assert ranges == (AttributeRange("Z", 3, None),)
        assert extra == ("ReturnNumber = NumberOfReturns", '"Scan Angle" >= 1 AND "Scan Angle" <= 2', "Intensity > 4")
        criteria = PointCloudFilterCriteria(ranges=ranges, extra_clauses=extra)
        assert criteria.to_subset_string() == (
            'Z >= 3 AND (ReturnNumber = NumberOfReturns) AND ("Scan Angle" >= 1 AND "Scan Angle" <= 2) AND (Intensity > 4)')

    def test_or_chain_is_one_extra_clause(self):
        ranges, extra = conditions_criteria([_c("Z", "between", 1, 5), _c("Intensity", ">=", 100, join="OR")])
        assert ranges == ()
        assert extra == ("(Z >= 1 AND Z <= 5) OR (Intensity >= 100)",)

    def test_incomplete_only(self):
        assert conditions_criteria([_c("Z"), _c("Intensity", "<=", join="OR")]) == ((), ())
