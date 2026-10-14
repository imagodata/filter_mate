# -*- coding: utf-8 -*-
"""
FilterMate 5 coverage widgets: the pure logic of the range histogram, the
raster EXPLORING panel and the point cloud EXPLORING panel.

The modules are loaded by path under a private synthetic package whose
``core`` and ``ui`` sub-packages point at the real directories without
running their ``__init__`` files: the real (pure) domain modules are used and
the Qt / QGIS imports resolve to the shared mocks of the root conftest.
"""
import importlib
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[5]
_PKG = "fm_coverage_widgets_test"


def _load_modules():
    for name, path in (
        ("", _PROJECT_ROOT),
        (".core", _PROJECT_ROOT / "core"),
        (".core.domain", _PROJECT_ROOT / "core" / "domain"),
        (".ui", _PROJECT_ROOT / "ui"),
        (".ui.widgets", _PROJECT_ROOT / "ui" / "widgets"),
        (".ui.widgets.coverage_panels", _PROJECT_ROOT / "ui" / "widgets" / "coverage_panels"),
    ):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        package.__package__ = _PKG + name
        sys.modules[_PKG + name] = package
    prefix = f"{_PKG}.ui.widgets.coverage_panels."
    return (
        importlib.import_module(prefix + "histogram_widget"),
        importlib.import_module(prefix + "raster_exploring_panel"),
        importlib.import_module(prefix + "point_cloud_exploring_panel"),
    )


hist, raster, cloud = _load_modules()
RasterSelection = raster.RasterSelection
RasterSelectionMode = raster.RasterSelectionMode


# ---------------------------------------------------------------------------
# Histogram: pixel <-> value
# ---------------------------------------------------------------------------

class TestPixelValueConversion:
    def test_value_at_edges_and_middle(self):
        assert hist.value_at(0, 200, 100.0, 300.0) == 100.0
        assert hist.value_at(200, 200, 100.0, 300.0) == 300.0
        assert hist.value_at(50, 200, 100.0, 300.0) == pytest.approx(150.0)

    def test_value_at_is_clamped(self):
        assert hist.value_at(-40, 200, 100.0, 300.0) == 100.0
        assert hist.value_at(250, 200, 100.0, 300.0) == 300.0

    def test_value_at_degenerate_plot(self):
        assert hist.value_at(10, 0, 5.0, 9.0) == 5.0
        assert hist.value_at(10, 100, 5.0, 5.0) == 5.0

    def test_x_of_is_the_inverse_of_value_at(self):
        for x in (0.0, 13.0, 99.5, 200.0):
            assert hist.x_of(hist.value_at(x, 200, -12.5, 840.0), 200, -12.5, 840.0) == pytest.approx(x)

    def test_x_of_is_clamped_and_degenerate_safe(self):
        assert hist.x_of(-1000.0, 200, 0.0, 10.0) == 0.0
        assert hist.x_of(1000.0, 200, 0.0, 10.0) == 200.0
        assert hist.x_of(3.0, 200, 4.0, 4.0) == 0.0


class TestBarHeights:
    def test_linear_scale(self):
        assert hist.bar_heights([0, 5, 10], 100) == [0.0, 50.0, 100.0]

    def test_sqrt_scale(self):
        heights = hist.bar_heights([1, 4, 100], 100, sqrt_scale=True)
        assert heights == pytest.approx([10.0, 20.0, 100.0])

    def test_empty_or_null_counts(self):
        assert hist.bar_heights([], 50) == []
        assert hist.bar_heights([0, 0], 50) == [0.0, 0.0]
        assert hist.bar_heights([-3, 4], 40) == [0.0, 40.0]

    def test_sqrt_scale_detection(self):
        assert hist.needs_sqrt_scale([10, 12, 11, 9, 5000])
        assert not hist.needs_sqrt_scale([10, 12, 11, 9, 50])
        assert not hist.needs_sqrt_scale([0, 0, 7])

    def test_bins_in_range_use_bin_centres(self):
        # 4 bins over [0, 40]: centres 5, 15, 25, 35
        assert hist.bins_in_range(4, 0.0, 40.0, 10.0, 30.0) == [False, True, True, False]
        assert hist.bins_in_range(4, 0.0, 40.0, None, None) == [True] * 4
        assert hist.bins_in_range(4, 0.0, 40.0, 20.0, None) == [False, False, True, True]
        assert hist.bins_in_range(0, 0.0, 40.0, None, None) == []


class TestRangeArithmetic:
    def test_clamp_range_clamps_and_orders(self):
        assert hist.clamp_range(-5.0, 50.0, 0.0, 40.0) == (0.0, 40.0)
        assert hist.clamp_range(30.0, 10.0, 0.0, 40.0) == (10.0, 30.0)
        assert hist.clamp_range(None, 12.0, 0.0, 40.0) == (None, 12.0)

    def test_normalize_range_drops_bounds_that_keep_everything(self):
        assert hist.normalize_range(0.0, 40.0, 0.0, 40.0) == (None, None)
        assert hist.normalize_range(-1.0, 50.0, 0.0, 40.0) == (None, None)
        assert hist.normalize_range(5.0, 35.0, 0.0, 40.0) == (5.0, 35.0)

    def test_normalize_range_without_data_bounds(self):
        assert hist.normalize_range(5.0, None, None, None) == (5.0, None)

    def test_snap_rounds_interior_values_only(self):
        assert hist.snap(12.6, 0, 11.6, 90.0) == 13.0
        assert hist.snap(11.6, 0, 11.6, 90.0) == 11.6  # the edge stays exact -> "unbounded"
        assert hist.snap(90.0, 0, 11.6, 90.0) == 90.0
        assert hist.snap(1.23456, None, 0.0, 9.0) == 1.23456
        assert hist.snap(11.7, 0, 11.6, 11.9) == 11.9  # rounding never leaves the data

    def test_spin_bounds_round_outwards(self):
        low, high = hist.spin_bounds(12.3456, 187.0004, 3)
        assert low == pytest.approx(12.345) and high == pytest.approx(187.001)
        assert low <= 12.3456 and high >= 187.0004

    def test_spin_bounds_keep_the_exact_data_bounds_unbounded(self):
        # The spin box sitting on its own bound must mean "no bound".
        low, high = hist.spin_bounds(12.3456, 187.0004, 3)
        assert hist.normalize_range(low, high, 12.3456, 187.0004) == (None, None)
        assert hist.normalize_range(12.346, high, 12.3456, 187.0004) == (12.346, None)

    def test_spin_bounds_integer_and_unknown(self):
        assert hist.spin_bounds(-3.5, 254.2, 0) == (-4.0, 255.0)
        assert hist.spin_bounds(None, 4.0, 0) == (-hist.SPIN_BOX_LIMIT, hist.SPIN_BOX_LIMIT)


class TestHandles:
    def test_nearest_handle(self):
        assert hist.nearest_handle(5, 20, 80) == hist.LOW_HANDLE
        assert hist.nearest_handle(95, 20, 80) == hist.HIGH_HANDLE
        assert hist.nearest_handle(30, 20, 80) == hist.LOW_HANDLE
        assert hist.nearest_handle(70, 20, 80) == hist.HIGH_HANDLE

    def test_drag_inside(self):
        assert hist.drag_handle(hist.LOW_HANDLE, 15.0, 10.0, 30.0) == (hist.LOW_HANDLE, 15.0, 30.0)
        assert hist.drag_handle(hist.HIGH_HANDLE, 25.0, 10.0, 30.0) == (hist.HIGH_HANDLE, 10.0, 25.0)

    def test_drag_past_the_other_handle_swaps(self):
        assert hist.drag_handle(hist.LOW_HANDLE, 40.0, 10.0, 30.0) == (hist.HIGH_HANDLE, 30.0, 40.0)
        assert hist.drag_handle(hist.HIGH_HANDLE, 5.0, 10.0, 30.0) == (hist.LOW_HANDLE, 5.0, 10.0)

    def test_coincident_handles_can_be_pulled_apart_both_ways(self):
        for grabbed in (hist.LOW_HANDLE, hist.HIGH_HANDLE):
            _, low, high = hist.drag_handle(grabbed, 5.0, 20.0, 20.0)
            assert (low, high) == (5.0, 20.0)
            _, low, high = hist.drag_handle(grabbed, 35.0, 20.0, 20.0)
            assert (low, high) == (20.0, 35.0)


# ---------------------------------------------------------------------------
# Raster panel
# ---------------------------------------------------------------------------

class TestRasterFormatting:
    def test_decimals_follow_the_data_type(self):
        assert raster.decimals_for("Byte") == 0
        assert raster.decimals_for("Int32") == 0
        assert raster.decimals_for("Float32") == 3
        assert raster.decimals_for("Unknown") == 3

    def test_band_label(self):
        assert raster.band_label(1, "elevation", "Float32") == "1 — elevation (Float32)"
        assert raster.band_label(2, "", "Byte") == "2 (Byte)"

    def test_pixel_value(self):
        assert raster.format_pixel_value(123.45678, 3) == "123.457"
        assert raster.format_pixel_value(12.0, 0) == "12"
        assert raster.format_pixel_value(None, 3, "NoData") == "NoData"

    def test_class_value(self):
        assert raster.format_class_value(3.0) == "3"
        assert raster.format_class_value(2.5) == "2.5"

    def test_coordinate_decimals_follow_the_pixel_size(self):
        assert raster.coordinate_decimals(25.0) == 1
        assert raster.coordinate_decimals(0.5) == 2
        assert raster.coordinate_decimals(0.0001) == 5
        assert raster.coordinate_decimals(0.0) == 2

    def test_percent(self):
        assert raster.format_percent(0.3124) == "31.2 %"
        assert raster.format_percent(None) == "–"

    def test_reference_and_range_formula(self):
        assert raster.sanitize_reference("MNT 5m-2024") == "MNT_5m_2024"
        assert raster.sanitize_reference("") == raster.DEFAULT_REFERENCE
        assert raster.range_formula(1, 200.0, 260.5, "mnt") == '("mnt@1" >= 200 AND "mnt@1" <= 260.5)'
        assert raster.range_formula(2, None, 15.0, "pente") == '("pente@2" <= 15)'
        assert raster.range_formula(1, 30.0, 10.0, "r") == '("r@1" >= 10 AND "r@1" <= 30)'
        assert raster.range_formula(1, None, None, "mnt") == ""


class TestRasterPicking:
    def test_extend_an_unset_range_starts_on_the_value(self):
        assert raster.extend_range(None, None, 212.5) == (212.5, 212.5)

    def test_extend_grows_only(self):
        assert raster.extend_range(100.0, 200.0, 250.0) == (100.0, 250.0)
        assert raster.extend_range(100.0, 200.0, 50.0) == (50.0, 200.0)
        assert raster.extend_range(100.0, 200.0, 150.0) == (100.0, 200.0)

    def test_extend_keeps_an_unbounded_side(self):
        assert raster.extend_range(None, 200.0, 250.0) == (None, 250.0)
        assert raster.extend_range(None, 200.0, 50.0) == (None, 200.0)

    def test_history_is_newest_first_and_bounded(self):
        history = []
        for value in range(7):
            history = raster.push_history(history, value)
        assert history == [6, 5, 4, 3, 2]


class TestRasterSelectionFromState:
    def test_range(self):
        selection = raster.build_raster_selection({"mode": "range", "band": 2, "minimum": 200.0, "maximum": 260.0})
        assert selection == RasterSelection(band=2, mode=RasterSelectionMode.RANGE, minimum=200.0, maximum=260.0)

    def test_inverted_range_is_reordered(self):
        selection = raster.build_raster_selection({"mode": "range", "minimum": 260.0, "maximum": 200.0})
        assert (selection.minimum, selection.maximum) == (200.0, 260.0)

    def test_empty_selections_are_none(self):
        assert raster.build_raster_selection({"mode": "range"}) is None
        assert raster.build_raster_selection({"mode": "classes", "classes": []}) is None
        assert raster.build_raster_selection({"mode": "expression", "expression": "   "}) is None
        assert raster.build_raster_selection(None) is None

    def test_classes(self):
        selection = raster.build_raster_selection({"mode": "classes", "classes": [3.0, 1, "7"]})
        assert selection.mode is RasterSelectionMode.CLASSES
        assert selection.classes == frozenset({1, 3, 7})

    def test_expression_is_stripped(self):
        selection = raster.build_raster_selection({"mode": "expression", "expression": ' "mnt@1" > 200 '})
        assert selection.expression == '"mnt@1" > 200'

    def test_only_the_active_mode_counts(self):
        state = {"mode": "classes", "minimum": 1.0, "maximum": 2.0, "classes": [4], "expression": "x"}
        assert raster.build_raster_selection(state).to_calc_formula("r") == '("r@1" = 4)'

    def test_invalid_entries_get_defaults(self):
        parsed = raster.parse_raster_state({"mode": "bogus", "band": "x", "minimum": "nan", "maximum": True,
                                            "classes": ["a", None, 2]})
        assert parsed["mode"] is RasterSelectionMode.RANGE
        assert parsed["band"] == 1
        assert (parsed["minimum"], parsed["maximum"]) == (None, None)
        assert parsed["classes"] == [2]
        assert parsed["preview"] is False

    def test_round_trip_through_the_domain_dict(self):
        original = RasterSelection(band=3, mode=RasterSelectionMode.RANGE, minimum=None, maximum=15.5)
        assert raster.build_raster_selection(original.to_dict()) == original


# ---------------------------------------------------------------------------
# Point cloud panel
# ---------------------------------------------------------------------------

class TestPointCloudFormatting:
    def test_counts(self):
        assert cloud.format_count(950) == "950"
        assert cloud.format_count(1500) == "1.5 k"
        assert cloud.format_count(14_100_000) == "14.1 M"
        assert cloud.format_count(2_300_000_000) == "2.3 G"
        assert cloud.format_count(999_960) == "1.0 M"
        assert cloud.format_count(-1) == ""
        assert cloud.format_count(None) == ""

    def test_kept_over_total(self):
        assert cloud.format_point_counts(9_800_000, 38_400_000) == "9.8 M / 38.4 M (25.5 %)"
        assert cloud.format_point_counts(9_800_000, None) == "9.8 M"
        assert cloud.format_point_counts(9_800_000, 0) == "9.8 M"
        assert cloud.format_point_counts(None, 38_400_000) == ""

    def test_class_item_label(self):
        assert cloud.class_item_label(2, 14_100_000) == "2 - Ground (14.1 M)"
        assert cloud.class_item_label(66, -1) == "66 - Virtual point"

    def test_class_colours(self):
        assert cloud.class_color(2) != cloud.class_color(5)
        assert cloud.class_color(200) == cloud.DEFAULT_CLASS_COLOR


class TestPresets:
    PRESENT = (1, 2, 3, 5, 6, 7, 9, 18, 65, 66)

    def test_preset_keeps_present_codes_only(self):
        assert cloud.preset_codes("Vegetation", self.PRESENT) == (3, 5)
        assert cloud.preset_codes("Ground", self.PRESENT) == (2,)
        assert cloud.preset_codes("Above ground", (2, 6, 17)) == (6, 17)

    def test_without_noise(self):
        assert cloud.preset_codes(cloud.WITHOUT_NOISE_PRESET, self.PRESENT) == (1, 2, 3, 5, 6, 9, 66)

    def test_unknown_or_absent(self):
        assert cloud.preset_codes("Nonsense", self.PRESENT) == ()
        assert cloud.preset_codes("Water", (2, 6)) == ()

    def test_every_domain_preset_is_offered(self):
        for name in cloud.CLASS_PRESETS:
            assert cloud.preset_codes(name, range(256)) == tuple(sorted(cloud.CLASS_PRESETS[name]))


class TestReturns:
    def test_choices(self):
        assert cloud.return_choices(3, True) == [None, "first", "last", "single", 1, 2, 3]
        assert cloud.return_choices(3, False) == [None, "first", 1, 2, 3]
        assert cloud.return_choices(40, False)[-1] == cloud.MAX_RETURN_NUMBERS
        assert cloud.return_choices(0, False) == [None, "first", 1]

    def test_criteria(self):
        assert cloud.return_criteria(None) == (None, ())
        assert cloud.return_criteria("first") == (None, ("ReturnNumber = 1",))
        assert cloud.return_criteria("last") == (None, ("ReturnNumber = NumberOfReturns",))
        assert cloud.return_criteria("single") == (None, ("NumberOfReturns = 1",))
        assert cloud.return_criteria(2) == (2, ())
        assert cloud.return_criteria(True) == (None, ())


class TestPointCloudCriteriaFromState:
    def test_default_state_is_empty(self):
        criteria = cloud.build_point_cloud_criteria({})
        assert criteria.is_empty
        assert criteria.to_subset_string() == ""

    def test_classes_count_only_when_the_group_is_checked(self):
        assert cloud.build_point_cloud_criteria({"classes": [6, 2]}).to_subset_string() == "Classification IN (2, 6)"
        assert cloud.build_point_cloud_criteria({"classes_enabled": False, "classes": [2]}).is_empty

    def test_ranges_count_only_when_the_group_is_checked(self):
        state = {"z": [10.5, None], "intensity_enabled": True, "intensity": [100, 900], "return": 1}
        assert cloud.build_point_cloud_criteria(state).is_empty
        state["ranges_enabled"] = True
        assert cloud.build_point_cloud_criteria(state).to_subset_string() == (
            "Z >= 10.5 AND Intensity >= 100 AND Intensity <= 900 AND ReturnNumber = 1")

    def test_intensity_needs_its_checkbox(self):
        state = {"ranges_enabled": True, "intensity": [100, 900]}
        assert cloud.build_point_cloud_criteria(state).is_empty

    def test_last_return_goes_through_extra_clauses(self):
        state = {"classes": [2, 6], "ranges_enabled": True, "z": [None, 150.25], "return": "last"}
        criteria = cloud.build_point_cloud_criteria(state)
        assert criteria.return_number is None
        assert criteria.extra_clauses == ("ReturnNumber = NumberOfReturns",)
        assert criteria.to_subset_string() == (
            "Classification IN (2, 6) AND Z <= 150.25 AND (ReturnNumber = NumberOfReturns)")

    def test_exact_bounds_are_not_rounded(self):
        state = {"ranges_enabled": True, "z": [12.3456, 187.0004]}
        assert cloud.build_point_cloud_criteria(state).to_subset_string() == "Z >= 12.3456 AND Z <= 187.0004"

    def test_inverted_bounds_and_junk_are_tolerated(self):
        parsed = cloud.parse_point_cloud_state({"z": [5, 1], "classes": [2, 2.5, 300, "x"], "return": 99})
        assert parsed["z"] == (1.0, 5.0)
        assert parsed["classes"] == [2]
        assert parsed["return"] is None

    def test_parse_is_idempotent(self):
        state = {"classes": [6, 2], "ranges_enabled": True, "z": [1, 2], "return": "single",
                 "hag_enabled": True, "hag_min": 3, "hag_layer_id": "dtm", "expression": "Z > 2"}
        once = cloud.parse_point_cloud_state(state)
        assert cloud.parse_point_cloud_state(once) == once


class TestPointCloudExpression:
    def test_generated_expression(self):
        assert cloud.build_point_cloud_expression({"classes": [2]}) == "Classification = 2"

    def test_height_above_dtm_is_appended(self):
        state = {"classes": [5], "ranges_enabled": True, "hag_enabled": True, "hag_min": 2.5, "hag_layer_id": "dtm"}
        assert cloud.build_point_cloud_expression(state) == "Classification = 5 AND HeightAboveGround >= 2.5"
        assert cloud.hag_from_state(state) == ("dtm", 2.5)

    def test_height_needs_group_layer_and_availability(self):
        base = {"classes": [5], "ranges_enabled": True, "hag_enabled": True, "hag_layer_id": "dtm"}
        assert cloud.build_point_cloud_expression(base, hag_available=False) == "Classification = 5"
        assert cloud.hag_from_state(dict(base, ranges_enabled=False)) is None
        assert cloud.hag_from_state(dict(base, hag_layer_id=None)) is None
        assert cloud.hag_from_state(dict(base, hag_enabled=False)) is None

    def test_typed_expression_replaces_the_generated_one(self):
        state = {"classes": [2], "expression_enabled": True, "expression": " Classification = 6 OR Z > 300 "}
        assert cloud.build_point_cloud_expression(state) == "Classification = 6 OR Z > 300"

    def test_typed_expression_is_wrapped_before_the_height(self):
        state = {"expression_enabled": True, "expression": "Classification = 6 OR Z > 300",
                 "ranges_enabled": True, "hag_enabled": True, "hag_min": 2, "hag_layer_id": "dtm"}
        assert cloud.build_point_cloud_expression(state) == (
            "(Classification = 6 OR Z > 300) AND HeightAboveGround >= 2")

    def test_height_alone(self):
        assert cloud.compose_expression("", 1.0) == "HeightAboveGround >= 1"
        assert cloud.compose_expression("Z > 3", None) == "Z > 3"


class TestModulesImportUnderMocks:
    def test_widget_classes_are_defined(self):
        assert hasattr(hist, "RangeHistogramWidget")
        assert hasattr(raster, "RasterExploringPanel")
        assert hasattr(cloud, "PointCloudExploringPanel")


class TestPixelHistory:
    def test_empty_history(self):
        assert raster.history_html([], "LAST PICKS") == ""

    def test_two_columns_and_band(self):
        html = raster.history_html([("572102 · 6278455", "198.400", 1), ("1 · 2", "3", 2)], "LAST PICKS")
        assert html.count("<tr>") == 3 and 'align="right"' in html
        assert "198.400</td>" in html and "3 · b2" in html and "LAST PICKS" in html

    def test_escapes(self):
        assert "&lt;" in raster.history_html([("<x>", "1", 1)], "T")
