# -*- coding: utf-8 -*-
"""
Tests for core.domain.point_cloud_filter_criteria.

PURE PYTHON tests -- no QGIS dependency. Output formats of
``to_subset_string`` are checked character by character because the
resulting text is handed verbatim to ``QgsPointCloudLayer.setSubsetString``.
"""
import ast
import inspect
import json

import pytest

import core.domain as domain_pkg
import core.domain.point_cloud_filter_criteria as criteria_module
from core.domain.point_cloud_filter_criteria import (
    AttributeRange,
    PointCloudAttributeSummary,
    PointCloudFilterCriteria,
    PointCloudFilterResult,
    PointCloudLayerSummary,
    format_number,
)


def _imported_modules(module) -> set:
    tree = ast.parse(inspect.getsource(module))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
    return names


# =========================================================================
# Module hygiene
# =========================================================================

class TestModuleHygiene:
    """The module must stay pure Python."""

    def test_no_qgis_import(self):
        for name in _imported_modules(criteria_module):
            assert not name.startswith("qgis"), name

    def test_package_reexports(self):
        for name in (
            "AttributeRange",
            "PointCloudFilterCriteria",
            "PointCloudAttributeSummary",
            "PointCloudLayerSummary",
            "PointCloudFilterResult",
        ):
            assert name in domain_pkg.__all__
            assert getattr(domain_pkg, name) is getattr(criteria_module, name)


# =========================================================================
# format_number
# =========================================================================

class TestFormatNumber:
    """Numeric rendering inside expressions."""

    @pytest.mark.parametrize("value,expected", [
        (2, "2"),
        (2.0, "2"),
        (10.5, "10.5"),
        (0.123456789, "0.123457"),
        (-3.25, "-3.25"),
        (0, "0"),
        (0.0, "0"),
        (-0.0, "0"),
        (1000000, "1000000"),
        (150.000001, "150.000001"),
        (0.0000001, "0"),
        (1e-7, "0"),
        (99.9999999, "100"),
    ])
    def test_formats(self, value, expected):
        assert format_number(value) == expected

    def test_nan_raises(self):
        with pytest.raises(ValueError, match="non-finite"):
            format_number(float("nan"))

    def test_infinity_raises(self):
        with pytest.raises(ValueError, match="non-finite"):
            format_number(float("inf"))


# =========================================================================
# AttributeRange
# =========================================================================

class TestAttributeRange:
    """Range constraint on a single attribute."""

    def test_create_basic(self):
        rng = AttributeRange("Z", 10, 150)
        assert rng.attribute == "Z"
        assert rng.minimum == 10
        assert rng.maximum == 150
        assert rng.is_empty is False

    def test_defaults_are_empty(self):
        rng = AttributeRange("Intensity")
        assert rng.minimum is None
        assert rng.maximum is None
        assert rng.is_empty is True

    def test_to_clauses_both_bounds(self):
        assert AttributeRange("Z", 10, 150).to_clauses() == ("Z >= 10", "Z <= 150")

    def test_to_clauses_minimum_only(self):
        assert AttributeRange("Z", minimum=10).to_clauses() == ("Z >= 10",)

    def test_to_clauses_maximum_only(self):
        assert AttributeRange("Z", maximum=150).to_clauses() == ("Z <= 150",)

    def test_to_clauses_empty(self):
        assert AttributeRange("Z").to_clauses() == ()

    def test_to_clauses_float_formatting(self):
        assert AttributeRange("Z", 10.5, 150.0).to_clauses() == ("Z >= 10.5", "Z <= 150")
        assert AttributeRange("GpsTime", 0.123456789).to_clauses() == ("GpsTime >= 0.123457",)

    def test_to_clauses_negative_bounds(self):
        assert AttributeRange("Z", -5.5, -1).to_clauses() == ("Z >= -5.5", "Z <= -1")

    def test_equal_bounds_allowed(self):
        assert AttributeRange("ReturnNumber", 1, 1).to_clauses() == ("ReturnNumber >= 1", "ReturnNumber <= 1")

    def test_empty_attribute_raises(self):
        with pytest.raises(ValueError, match="identifier"):
            AttributeRange("")

    @pytest.mark.parametrize("bad", ["1Z", "Z value", "Z-1", "Z;DROP", "Z.x", " Z", "Z(", None, 5])
    def test_invalid_identifier_raises(self, bad):
        with pytest.raises(ValueError, match="identifier"):
            AttributeRange(bad)

    @pytest.mark.parametrize("good", ["Z", "_z", "Z1", "Number_Of_Returns", "x_9"])
    def test_valid_identifiers(self, good):
        assert AttributeRange(good).attribute == good

    def test_minimum_greater_than_maximum_raises(self):
        with pytest.raises(ValueError, match="minimum"):
            AttributeRange("Z", 150, 10)

    def test_non_numeric_bound_raises(self):
        with pytest.raises(ValueError, match="minimum"):
            AttributeRange("Z", minimum="10")
        with pytest.raises(ValueError, match="maximum"):
            AttributeRange("Z", maximum=True)

    def test_non_finite_bound_raises(self):
        with pytest.raises(ValueError, match="finite"):
            AttributeRange("Z", minimum=float("nan"))
        with pytest.raises(ValueError, match="finite"):
            AttributeRange("Z", maximum=float("inf"))

    def test_frozen_immutability(self):
        rng = AttributeRange("Z", 0, 1)
        with pytest.raises(AttributeError):
            rng.minimum = 5

    def test_hashable_and_equal_by_value(self):
        assert AttributeRange("Z", 1, 2) == AttributeRange("Z", 1, 2)
        assert len({AttributeRange("Z", 1, 2), AttributeRange("Z", 1, 2)}) == 1

    def test_dict_round_trip(self):
        rng = AttributeRange("Intensity", 20, None)
        data = rng.to_dict()
        assert data == {"attribute": "Intensity", "minimum": 20, "maximum": None}
        assert AttributeRange.from_dict(data) == rng

    def test_from_dict_invalid(self):
        with pytest.raises(ValueError, match="dict"):
            AttributeRange.from_dict(["Z", 1, 2])
        with pytest.raises(ValueError, match="identifier"):
            AttributeRange.from_dict({"minimum": 1})


# =========================================================================
# PointCloudFilterCriteria
# =========================================================================

class TestPointCloudFilterCriteria:
    """Criteria value object and its subset string rendering."""

    def test_defaults_are_empty(self):
        criteria = PointCloudFilterCriteria()
        assert criteria.classification_codes == frozenset()
        assert criteria.ranges == ()
        assert criteria.return_number is None
        assert criteria.extra_clauses == ()
        assert criteria.is_empty is True
        assert criteria.to_subset_string() == ""

    def test_single_classification(self):
        criteria = PointCloudFilterCriteria(classification_codes={2})
        assert criteria.to_subset_string() == "Classification = 2"

    def test_multiple_classifications_sorted(self):
        criteria = PointCloudFilterCriteria(classification_codes=[6, 2])
        assert criteria.to_subset_string() == "Classification IN (2, 6)"

    def test_many_classifications(self):
        criteria = PointCloudFilterCriteria(classification_codes=(9, 2, 6, 5))
        assert criteria.to_subset_string() == "Classification IN (2, 5, 6, 9)"

    def test_duplicate_codes_collapse(self):
        criteria = PointCloudFilterCriteria(classification_codes=[2, 2, 2])
        assert criteria.classification_codes == frozenset({2})
        assert criteria.to_subset_string() == "Classification = 2"

    def test_range_only(self):
        criteria = PointCloudFilterCriteria(ranges=(AttributeRange("Z", 10, 150),))
        assert criteria.to_subset_string() == "Z >= 10 AND Z <= 150"

    def test_return_number_only(self):
        criteria = PointCloudFilterCriteria(return_number=1)
        assert criteria.to_subset_string() == "ReturnNumber = 1"

    def test_extra_clause_only(self):
        criteria = PointCloudFilterCriteria(extra_clauses=("Red > 100 OR Blue > 100",))
        assert criteria.to_subset_string() == "(Red > 100 OR Blue > 100)"

    def test_extra_clauses_are_stripped(self):
        criteria = PointCloudFilterCriteria(extra_clauses=("  NIR > 0  ",))
        assert criteria.extra_clauses == ("NIR > 0",)
        assert criteria.to_subset_string() == "(NIR > 0)"

    def test_full_combination_order(self):
        criteria = PointCloudFilterCriteria(
            classification_codes={6, 2},
            ranges=(AttributeRange("Z", 10, 150), AttributeRange("Intensity", minimum=20)),
            return_number=1,
            extra_clauses=("Red > 100", "NumberOfReturns <> 3"),
        )
        assert criteria.to_subset_string() == (
            "Classification IN (2, 6) AND Z >= 10 AND Z <= 150 AND Intensity >= 20"
            " AND ReturnNumber = 1 AND (Red > 100) AND (NumberOfReturns <> 3)"
        )

    def test_ranges_rendered_in_given_order(self):
        criteria = PointCloudFilterCriteria(
            ranges=[AttributeRange("Intensity", 0, 255), AttributeRange("Z", maximum=5.5)],
        )
        assert criteria.ranges == (AttributeRange("Intensity", 0, 255), AttributeRange("Z", maximum=5.5))
        assert criteria.to_subset_string() == "Intensity >= 0 AND Intensity <= 255 AND Z <= 5.5"

    def test_empty_ranges_render_nothing(self):
        criteria = PointCloudFilterCriteria(ranges=(AttributeRange("Z"),), return_number=2)
        assert criteria.is_empty is False
        assert criteria.to_subset_string() == "ReturnNumber = 2"

    def test_only_empty_ranges_is_empty(self):
        criteria = PointCloudFilterCriteria(ranges=(AttributeRange("Z"), AttributeRange("Intensity")))
        assert criteria.is_empty is True
        assert criteria.to_subset_string() == ""

    def test_no_between_keyword(self):
        criteria = PointCloudFilterCriteria(ranges=(AttributeRange("Z", 1, 2),))
        assert "BETWEEN" not in criteria.to_subset_string()

    @pytest.mark.parametrize("bad", [-1, 256, 1000])
    def test_classification_out_of_range_raises(self, bad):
        with pytest.raises(ValueError, match="classification code"):
            PointCloudFilterCriteria(classification_codes={bad})

    @pytest.mark.parametrize("bad", ["2", 2.0, True, None])
    def test_classification_non_int_raises(self, bad):
        with pytest.raises(ValueError, match="classification code"):
            PointCloudFilterCriteria(classification_codes=[bad])

    def test_classification_boundaries(self):
        criteria = PointCloudFilterCriteria(classification_codes={0, 255})
        assert criteria.to_subset_string() == "Classification IN (0, 255)"

    @pytest.mark.parametrize("bad", [0, 16, -3])
    def test_return_number_out_of_range_raises(self, bad):
        with pytest.raises(ValueError, match="return_number"):
            PointCloudFilterCriteria(return_number=bad)

    @pytest.mark.parametrize("bad", ["1", 1.0, True])
    def test_return_number_non_int_raises(self, bad):
        with pytest.raises(ValueError, match="return_number"):
            PointCloudFilterCriteria(return_number=bad)

    def test_return_number_boundaries(self):
        assert PointCloudFilterCriteria(return_number=1).to_subset_string() == "ReturnNumber = 1"
        assert PointCloudFilterCriteria(return_number=15).to_subset_string() == "ReturnNumber = 15"

    def test_invalid_range_item_raises(self):
        with pytest.raises(ValueError, match="AttributeRange"):
            PointCloudFilterCriteria(ranges=("Z >= 1",))

    @pytest.mark.parametrize("bad", ["", "   ", None, 5])
    def test_invalid_extra_clause_raises(self, bad):
        with pytest.raises(ValueError, match="extra clauses"):
            PointCloudFilterCriteria(extra_clauses=(bad,))

    def test_containers_normalised_to_immutable(self):
        criteria = PointCloudFilterCriteria(
            classification_codes=[2, 6],
            ranges=[AttributeRange("Z")],
            extra_clauses=["Red > 0"],
        )
        assert isinstance(criteria.classification_codes, frozenset)
        assert isinstance(criteria.ranges, tuple)
        assert isinstance(criteria.extra_clauses, tuple)

    def test_frozen_immutability(self):
        criteria = PointCloudFilterCriteria(classification_codes={2})
        with pytest.raises(AttributeError):
            criteria.return_number = 1

    def test_hashable_and_equal_by_value(self):
        a = PointCloudFilterCriteria(classification_codes=[2, 6], ranges=[AttributeRange("Z", 1, 2)])
        b = PointCloudFilterCriteria(classification_codes=(6, 2), ranges=(AttributeRange("Z", 1, 2),))
        assert a == b
        assert hash(a) == hash(b)

    def test_to_dict_is_json_compatible(self):
        criteria = PointCloudFilterCriteria(
            classification_codes={6, 2},
            ranges=(AttributeRange("Z", 10, 150.5), AttributeRange("Intensity", minimum=20)),
            return_number=1,
            extra_clauses=("Red > 100",),
        )
        data = criteria.to_dict()
        assert data == {
            "classification_codes": [2, 6],
            "ranges": [
                {"attribute": "Z", "minimum": 10, "maximum": 150.5},
                {"attribute": "Intensity", "minimum": 20, "maximum": None},
            ],
            "return_number": 1,
            "extra_clauses": ["Red > 100"],
        }
        assert json.loads(json.dumps(data)) == data

    def test_dict_round_trip(self):
        criteria = PointCloudFilterCriteria(
            classification_codes={2, 6, 9},
            ranges=(AttributeRange("Z", 10, 150), AttributeRange("GpsTime", maximum=1.5)),
            return_number=3,
            extra_clauses=("NIR > 0",),
        )
        restored = PointCloudFilterCriteria.from_dict(json.loads(json.dumps(criteria.to_dict())))
        assert restored == criteria
        assert restored.to_subset_string() == criteria.to_subset_string()

    def test_empty_round_trip(self):
        data = PointCloudFilterCriteria().to_dict()
        assert data == {"classification_codes": [], "ranges": [], "return_number": None, "extra_clauses": []}
        assert PointCloudFilterCriteria.from_dict(data) == PointCloudFilterCriteria()

    def test_from_dict_missing_keys_use_defaults(self):
        assert PointCloudFilterCriteria.from_dict({}) == PointCloudFilterCriteria()
        assert PointCloudFilterCriteria.from_dict({"classification_codes": [2]}).to_subset_string() == "Classification = 2"

    def test_from_dict_null_values_use_defaults(self):
        data = {"classification_codes": None, "ranges": None, "return_number": None, "extra_clauses": None}
        assert PointCloudFilterCriteria.from_dict(data) == PointCloudFilterCriteria()

    def test_from_dict_accepts_range_instances(self):
        criteria = PointCloudFilterCriteria.from_dict({"ranges": [AttributeRange("Z", 1, 2)]})
        assert criteria.ranges == (AttributeRange("Z", 1, 2),)

    def test_from_dict_validates(self):
        with pytest.raises(ValueError, match="dict"):
            PointCloudFilterCriteria.from_dict([2, 6])
        with pytest.raises(ValueError, match="classification code"):
            PointCloudFilterCriteria.from_dict({"classification_codes": [300]})
        with pytest.raises(ValueError, match="identifier"):
            PointCloudFilterCriteria.from_dict({"ranges": [{"attribute": "bad name"}]})


# =========================================================================
# PointCloudAttributeSummary
# =========================================================================

class TestPointCloudAttributeSummary:
    """Observed range of an attribute."""

    def test_create_basic(self):
        summary = PointCloudAttributeSummary("Z", 10.0, 150.0)
        assert summary.name == "Z"
        assert summary.minimum == 10.0
        assert summary.maximum == 150.0

    def test_defaults(self):
        summary = PointCloudAttributeSummary("Intensity")
        assert summary.minimum is None
        assert summary.maximum is None

    def test_frozen_immutability(self):
        summary = PointCloudAttributeSummary("Z")
        with pytest.raises(AttributeError):
            summary.minimum = 1.0


# =========================================================================
# PointCloudLayerSummary
# =========================================================================

class TestPointCloudLayerSummary:
    """Layer snapshot consumed by the filter panel."""

    def _summary(self, **overrides):
        params = dict(
            layer_id="pc_1",
            layer_name="tile",
            provider="copc",
            point_count=1200,
            attributes=("X", "Y", "Z", "Classification", "Intensity"),
            classes=((6, 40), (2, 100), (5, -1)),
            ranges=(
                PointCloudAttributeSummary("Z", 10.0, 150.0),
                PointCloudAttributeSummary("Intensity", 0.0, 255.0),
            ),
            statistics_available=True,
            current_subset="Classification = 2",
        )
        params.update(overrides)
        return PointCloudLayerSummary(**params)

    def test_create_basic(self):
        summary = self._summary()
        assert summary.layer_id == "pc_1"
        assert summary.layer_name == "tile"
        assert summary.provider == "copc"
        assert summary.point_count == 1200
        assert summary.statistics_available is True
        assert summary.current_subset == "Classification = 2"

    def test_defaults(self):
        summary = PointCloudLayerSummary("id", "name")
        assert summary.provider == ""
        assert summary.point_count == -1
        assert summary.attributes == ()
        assert summary.classes == ()
        assert summary.ranges == ()
        assert summary.statistics_available is False
        assert summary.current_subset == ""
        assert summary.class_codes == ()
        assert summary.range_of("Z") is None
        assert summary.has_attribute("Z") is False

    def test_classes_sorted_by_code(self):
        assert self._summary().classes == ((2, 100), (5, -1), (6, 40))

    def test_class_codes(self):
        assert self._summary().class_codes == (2, 5, 6)

    def test_none_count_becomes_minus_one(self):
        summary = self._summary(classes=[(2, None)])
        assert summary.classes == ((2, -1),)

    def test_has_attribute(self):
        summary = self._summary()
        assert summary.has_attribute("Z") is True
        assert summary.has_attribute("Classification") is True
        assert summary.has_attribute("ReturnNumber") is False
        assert summary.has_attribute("z") is False

    def test_range_of(self):
        summary = self._summary()
        z_range = summary.range_of("Z")
        assert z_range == PointCloudAttributeSummary("Z", 10.0, 150.0)
        assert summary.range_of("Intensity").maximum == 255.0
        assert summary.range_of("GpsTime") is None

    def test_containers_normalised_to_tuples(self):
        summary = self._summary(
            attributes=["X", "Z"],
            classes=[[2, 5], [1, 3]],
            ranges=[PointCloudAttributeSummary("Z")],
        )
        assert summary.attributes == ("X", "Z")
        assert summary.classes == ((1, 3), (2, 5))
        assert summary.ranges == (PointCloudAttributeSummary("Z"),)

    def test_frozen_immutability(self):
        summary = self._summary()
        with pytest.raises(AttributeError):
            summary.point_count = 0


# =========================================================================
# PointCloudFilterResult
# =========================================================================

class TestPointCloudFilterResult:
    """Outcome of a subset application."""

    def test_create_basic(self):
        result = PointCloudFilterResult(True, "Classification = 2", "Z >= 1", "ok")
        assert result.success is True
        assert result.subset_string == "Classification = 2"
        assert result.previous_subset == "Z >= 1"
        assert result.message == "ok"

    def test_defaults(self):
        result = PointCloudFilterResult(success=False, subset_string="")
        assert result.previous_subset == ""
        assert result.message == ""

    def test_frozen_immutability(self):
        result = PointCloudFilterResult(True, "")
        with pytest.raises(AttributeError):
            result.success = False
