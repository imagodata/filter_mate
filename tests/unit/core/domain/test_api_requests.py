# -*- coding: utf-8 -*-
"""FilterMate 5 - parameters shared by the public API, Processing and the REST API."""
import pytest

from core.domain.api_requests import (
    OPERATORS,
    PREDICATES,
    OperationReport,
    normalize_operator,
    normalize_predicates,
    parse_class_codes,
    point_cloud_criteria_from_dict,
    point_cloud_criteria_from_values,
    raster_selection_from_dict,
    raster_selection_from_values,
    relation_numbers,
)
from core.domain.raster_filter_criteria import RasterSelectionMode


class TestClassCodes:
    @pytest.mark.parametrize("value, expected", [
        (None, set()), ("", set()), ("6", {6}), ("3, 4,5", {3, 4, 5}), ("3 4;5", {3, 4, 5}),
        (6, {6}), ([2, 2, 9], {2, 9}), ("6.0", {6}),
    ])
    def test_parses(self, value, expected):
        assert parse_class_codes(value) == frozenset(expected)

    @pytest.mark.parametrize("value", ["a", "3,b", "2.5", [1.5]])
    def test_rejects_non_integers(self, value):
        with pytest.raises(ValueError):
            parse_class_codes(value)


class TestOperatorsAndPredicates:
    def test_operator_labels_and_indexes(self):
        assert normalize_operator(None) is None
        assert normalize_operator("replace") is None
        assert normalize_operator(" and   not ") == "AND NOT"
        assert normalize_operator("or") == "OR"
        assert [normalize_operator(i) for i in range(len(OPERATORS))] == list(OPERATORS)

    @pytest.mark.parametrize("value", ["XOR", 9, -1])
    def test_operator_rejects(self, value):
        with pytest.raises(ValueError):
            normalize_operator(value)

    def test_predicates(self):
        assert normalize_predicates(None) == ("Intersect",)
        assert normalize_predicates([]) == ("Intersect",)
        assert normalize_predicates("Disjoint") == ("Disjoint",)
        assert normalize_predicates(["intersects", "within", "Intersect"]) == ("Intersect", "Are within")
        assert normalize_predicates([2, 0]) == ("Disjoint", "Intersect")
        assert len(PREDICATES) == 8

    @pytest.mark.parametrize("value", [["Near"], [8], ["touch me"]])
    def test_predicates_reject(self, value):
        with pytest.raises(ValueError):
            normalize_predicates(value)


class TestRasterSelection:
    def test_range(self):
        selection = raster_selection_from_values(band=2, minimum=1200, maximum="1300")
        assert selection.mode is RasterSelectionMode.RANGE
        assert (selection.band, selection.minimum, selection.maximum) == (2, 1200.0, 1300.0)

    def test_classes_from_string_and_index(self):
        selection = raster_selection_from_values(mode=1, classes="6, 7")
        assert selection.mode is RasterSelectionMode.CLASSES and selection.classes == frozenset({6, 7})

    def test_expression_drops_unrelated_values(self):
        selection = raster_selection_from_values(mode="expression", expression=' "mnt@1" > 1200 ', minimum=3)
        assert selection.expression == '"mnt@1" > 1200' and selection.minimum == 3.0
        assert selection.classes == frozenset()

    @pytest.mark.parametrize("kwargs", [
        {}, {"mode": "classes"}, {"mode": "expression", "expression": "  "}, {"mode": "slope", "minimum": 1},
        {"mode": 7, "minimum": 1}, {"minimum": 5, "maximum": 1}, {"band": 0, "minimum": 1},
    ])
    def test_rejects(self, kwargs):
        with pytest.raises(ValueError):
            raster_selection_from_values(**kwargs)

    def test_from_dict(self):
        assert raster_selection_from_dict(None) is None
        assert raster_selection_from_dict({}) is None
        selection = raster_selection_from_dict({"band": 1, "mode": "range", "minimum": None, "maximum": 15})
        assert selection.maximum == 15.0 and selection.minimum is None
        with pytest.raises(ValueError):
            raster_selection_from_dict({"minimum": 1, "colour": "red"})
        with pytest.raises(ValueError):
            raster_selection_from_dict(["range"])


class TestPointCloudCriteria:
    def test_values_render_a_subset(self):
        criteria = point_cloud_criteria_from_values(classes="4,5", z_min=1200, intensity_max=300, return_number=1,
                                                    expression="NumberOfReturns > 1")
        assert criteria.to_subset_string() == ("Classification IN (4, 5) AND Z >= 1200 AND Intensity <= 300 "
                                               "AND ReturnNumber = 1 AND (NumberOfReturns > 1)")

    def test_empty(self):
        assert point_cloud_criteria_from_values().is_empty
        assert point_cloud_criteria_from_dict(None) is None
        assert point_cloud_criteria_from_dict({"classes": [], "expression": ""}) is None

    def test_from_dict_and_expression(self):
        assert point_cloud_criteria_from_dict("Classification = 6").to_subset_string() == "(Classification = 6)"
        criteria = point_cloud_criteria_from_dict({"classes": [6], "z_max": 1300, "z_min": None})
        assert criteria.to_subset_string() == "Classification = 6 AND Z <= 1300"

    @pytest.mark.parametrize("data", [{"classes": [6], "colour": 1}, {"classes": [300]}, {"z_min": 5, "z_max": 1}, 42])
    def test_rejects(self, data):
        with pytest.raises(ValueError):
            point_cloud_criteria_from_dict(data)


class TestOperationReport:
    def test_ok_and_dict(self):
        report = OperationReport()
        report.done["id1"] = "mnt"
        report.skipped["web"] = "not filterable"
        assert report.ok and report.done_ids == ["id1"] and report.done_names == ["mnt"]
        report.failed["lhd"] = "boom"
        data = report.to_dict()
        assert data["ok"] is False and data["done"] == ["mnt"] and data["failed"] == {"lhd": "boom"}
        assert data["skipped"] == {"web": "not filterable"}

    def test_error_is_not_ok(self):
        assert not OperationReport(error="stopped").ok


class TestReviewFindings:
    """Edge cases found by the review of the automation API."""

    @pytest.mark.parametrize("value", ["inf", "nan", [float("inf")]])
    def test_class_codes_reject_non_finite(self, value):
        with pytest.raises(ValueError):
            parse_class_codes(value)

    def test_raster_rejects_nan_bounds_and_float_band(self):
        with pytest.raises(ValueError):
            raster_selection_from_values(minimum=float("nan"))
        with pytest.raises(ValueError):
            raster_selection_from_values(band=1.7, minimum=1)

    def test_classes_ignored_outside_classes_mode(self):
        assert raster_selection_from_values(minimum=1, classes="not, numbers").classes == frozenset()

    def test_lowercase_labels(self):
        assert normalize_predicates(["intersect", "are within", "DISJOINT"]) == ("Intersect", "Are within", "Disjoint")


class TestFiniteNumbers:
    """Audit 2026-10: NaN slips through every comparison, Infinity covers everything."""

    def test_relation_numbers(self):
        assert relation_numbers(None, None) == (0.0, 0.0)
        assert relation_numbers(-5, "50") == (-5.0, 50.0)

    @pytest.mark.parametrize("buffer, coverage", [
        (float("nan"), 0), (float("inf"), 0), (-float("inf"), 0), ("nan", 0), (2e7, 0),
        (0, float("nan")), (0, 101), (0, -1), ("x", 0),
    ])
    def test_relation_numbers_reject(self, buffer, coverage):
        with pytest.raises(ValueError):
            relation_numbers(buffer, coverage)

    @pytest.mark.parametrize("key", ["z_min", "z_max", "intensity_min", "intensity_max"])
    @pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
    def test_point_cloud_bounds_must_be_finite(self, key, value):
        with pytest.raises(ValueError):
            point_cloud_criteria_from_values(**{key: value})
