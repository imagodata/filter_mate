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
        assert raster.format_percent(0.00012) == "0.012 %"  # a pipette colour: a few pools of an orthophoto

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


class TestDerivativeInTheState:
    def test_range_carries_the_derivative(self):
        selection = raster.build_raster_selection({"mode": "range", "maximum": 15.0, "derivative": "slope_degrees"})
        assert selection.derivative.value == "slope_degrees"

    def test_classes_and_expression_ignore_it(self):
        classes = raster.build_raster_selection({"mode": "classes", "classes": [1], "derivative": "aspect"})
        expression = raster.build_raster_selection({"mode": "expression", "expression": "1", "derivative": "aspect"})
        assert classes.derivative.value == expression.derivative.value == "value"

    def test_unknown_derivative_is_the_value(self):
        assert raster.parse_raster_state({"derivative": "curvature"})["derivative"].value == "value"
        assert raster.parse_raster_state(None)["derivative"].value == "value"

    def test_presets_are_ordered_and_bounded(self):
        for derivative in raster.RasterDerivative:
            for key, low, high in raster.derivative_presets(derivative):
                assert key and (low is None or high is None or low < high)
        assert raster.derivative_presets(raster.RasterDerivative.VALUE) == []
        assert raster.derivative_presets(raster.RasterDerivative.ROUGHNESS) == []

    def test_aspect_has_no_north_that_would_wrap(self):
        keys = [key for key, _low, _high in raster.derivative_presets(raster.RasterDerivative.ASPECT)]
        assert "north" not in keys

    def test_preset_text(self):
        assert raster.format_preset("Flat", None, 5.0, " °") == "Flat (< 5 °)"
        assert raster.format_preset("Steep", 30.0, None, " %") == "Steep (> 30 %)"
        assert raster.format_preset("Gentle", 5.0, 15.0) == "Gentle (5–15)"


class TestSpectralPresets:
    def test_layouts_offer_the_presets_their_colours_allow(self):
        assert raster.spectral_presets_for("rgb") == ["exg_vegetation"]
        assert raster.spectral_presets_for("irc") == ["ndvi_vegetation", "ndvi_bare", "ndwi_water"]
        assert raster.spectral_presets_for("rgbn") == ["ndvi_vegetation", "ndvi_bare", "ndwi_water", "exg_vegetation"]
        assert raster.spectral_presets_for("unknown") == []

    def test_ndvi_on_an_irc_image_uses_bands_one_and_two(self):
        assert raster.spectral_expression("ndvi_vegetation", "irc", "ortho") == (
            '("ortho@1" - "ortho@2") / ("ortho@1" + "ortho@2") > 0.3')

    def test_ndvi_on_rgbn_uses_the_fourth_band_for_the_infrared(self):
        assert raster.spectral_expression("ndvi_vegetation", "rgbn", "img") == (
            '("img@4" - "img@1") / ("img@4" + "img@1") > 0.3')

    def test_water_index_is_green_against_infrared(self):
        assert raster.spectral_expression("ndwi_water", "irc", "o") == '("o@3" - "o@1") / ("o@3" + "o@1") > 0.1'

    def test_missing_colour_gives_nothing(self):
        assert raster.spectral_expression("ndvi_vegetation", "rgb", "o") == ""
        assert raster.spectral_expression("nope", "rgb", "o") == ""

    def test_layout_guess(self):
        assert raster.default_band_layout(["Red", "Green", "Blue"]) == "rgb"
        assert raster.default_band_layout(["R", "G", "B", "N"]) == "rgbn"
        assert raster.default_band_layout(["Band 1"]) == "rgb"


class TestPipetteReviewFixes:
    def test_alpha_is_not_an_infrared_band(self):
        assert raster.default_band_layout(["Red", "Green", "Blue", "Alpha"]) == "rgb"
        assert raster.layouts_for(["Red", "Green", "Blue", "Alpha"]) == ["rgb", "irc"]
        assert raster.layouts_for(["R", "G", "B", "N"]) == ["rgb", "irc", "rgbn"]

    def test_one_tolerance_per_band(self):
        text = raster.color_similarity_expression("o", [1, 2], [(10, 20)], [5, 500])
        assert text == '(abs("o@1" - 10) <= 5 AND abs("o@2" - 20) <= 500)'

    def test_numbers_are_not_rounded_to_six_digits(self):
        text = raster.color_similarity_expression("o", [1], [(123456789,)], 0)
        assert '"o@1" - 123456789)' in text
        assert '0.123456789' in raster.color_similarity_expression("o", [1], [(0.123456789,)], 0)

    def test_picks_survive_the_state(self):
        parsed = raster.parse_raster_state({"pipette_kind": "color", "pipette_picks": [[20, 120, 200], [200, 40, 40], "x"]})
        assert parsed["pipette_kind"] == "color" and parsed["pipette_picks"] == [[20.0, 120.0, 200.0], [200.0, 40.0, 40.0]]
        assert raster.parse_raster_state({"pipette_kind": "weird", "pipette_picks": "1"})["pipette_kind"] == ""
        assert raster.parse_raster_state({"pipette_picks": [1300.5, 2]})["pipette_picks"] == [1300.5, 2]

    def test_odd_values_in_a_state_do_not_raise(self):
        parsed = raster.parse_raster_state({"expression": 42, "layout": ["rgb"]})
        assert parsed["expression"] == "" and parsed["layout"] == ""


class TestPipetteGroupState:
    def test_pipette_mode_round_trip(self):
        parsed = raster.parse_raster_state({"mode": "pipette", "pipette_selection": {"mode": "classes", "classes": [3]}})
        assert parsed["mode"] is raster.PIPETTE

    def test_pipette_selection_is_its_own(self):
        state = {"mode": "pipette", "minimum": 1.0, "maximum": 9.0,
                 "pipette_selection": {"band": 1, "mode": "range", "minimum": 200.0, "maximum": 260.0}}
        selection = raster.build_raster_selection(state)
        assert (selection.minimum, selection.maximum) == (200.0, 260.0)  # not the range group

    def test_slope_range_picked(self):
        selection = raster.build_raster_selection({"mode": "pipette", "pipette_selection": {
            "mode": "range", "maximum": 12.0, "derivative": "slope_degrees"}})
        assert selection.derivative.value == "slope_degrees"

    def test_nothing_picked_selects_nothing(self):
        assert raster.build_raster_selection({"mode": "pipette"}) is None
        assert raster.build_raster_selection({"mode": "pipette", "pipette_selection": {"mode": "nope"}}) is None


class TestObjectDetectionState:
    def test_seeds_and_target_survive_the_state(self):
        parsed = raster.parse_raster_state({"pipette_seeds": [[1, 2, [20, 120, 200]], [1, 2, 7], ["x", 3, 1],
                                                              [4, 5], [7.5, 8, 6], [9, 9, "no"]],
                                            "pipette_target": "object"})
        assert parsed["pipette_seeds"] == [(1.0, 2.0, (20.0, 120.0, 200.0)), (7.5, 8.0, 6)]
        assert parsed["pipette_target"] == raster.PICK_OBJECT
        assert raster.parse_raster_state({"pipette_target": "weird"})["pipette_target"] == raster.PICK_SIMILAR

    def test_detected_object_selection_from_the_state(self):
        selection = raster.build_raster_selection({"mode": "pipette", "pipette_selection": {
            "mode": "expression", "expression": '"o@1" > 3', "seeds": [[10, 20]]}})
        assert selection.seeds == ((10.0, 20.0),)

    def test_similar_objects_target_and_ratio_in_the_state(self):
        parsed = raster.parse_raster_state({"pipette_target": "similar_objects", "pipette_similar": [3, 0.25]})
        assert parsed["pipette_target"] == raster.PICK_SIMILAR_OBJECTS and parsed["pipette_similar"] == (0.25, 3.0)
        assert raster.parse_raster_state({"pipette_similar": [0, 2]})["pipette_similar"] == raster.DEFAULT_SIMILAR_RATIO
        assert raster.parse_raster_state({"pipette_similar": "x"})["pipette_similar"] == raster.DEFAULT_SIMILAR_RATIO
        assert raster.parse_raster_state({})["pipette_shape"] is True  # a state before the shape: on
        assert raster.parse_raster_state({"pipette_shape": False})["pipette_shape"] is False

    def test_similar_selection_from_the_state(self):
        selection = raster.build_raster_selection({"mode": "pipette", "pipette_selection": {
            "mode": "classes", "classes": [3], "seeds": [[10, 20]], "similar": [0.5, 2.0]}})
        assert selection.similar == (0.5, 2.0) and selection.seeds == ((10.0, 20.0),)

    def test_area_text(self):
        assert raster.format_area(125.4) == "125 m²"
        assert raster.format_area(2.34) == "2.3 m²"
        assert raster.format_area(34000) == "3.4 ha"
        assert raster.format_area(2150000) == "2.15 km²"
        assert raster.format_area(None) == "" and raster.format_area(float("nan")) == ""


class TestColorPipette:
    def test_one_color_within_a_tolerance(self):
        assert raster.color_similarity_expression("ortho", [1, 2, 3], [(12, 100, 180)], 30) == (
            '(abs("ortho@1" - 12) <= 30 AND abs("ortho@2" - 100) <= 30 AND abs("ortho@3" - 180) <= 30)')

    def test_several_colors_are_ored(self):
        text = raster.color_similarity_expression("o", [1, 2], [(1, 2), (3, 4)], 5)
        assert text == '(abs("o@1" - 1) <= 5 AND abs("o@2" - 2) <= 5) OR (abs("o@1" - 3) <= 5 AND abs("o@2" - 4) <= 5)'

    def test_no_sample_no_expression(self):
        assert raster.color_similarity_expression("o", [1], [], 5) == ""

    def test_tolerance_is_a_share_of_the_range(self):
        assert raster.tolerance_value(12, 255) == 30.6
        assert raster.tolerance_value(0, 255) == 0.0
        assert raster.tolerance_value(-5, 255) == 0.0

    def test_alpha_is_not_part_of_a_color(self):
        assert raster.color_bands(["Red", "Green", "Blue", "Alpha"]) == [1, 2, 3]
        assert raster.color_bands(["R", "G", "B", "N", "Alpha"]) == [1, 2, 3, 4]
        assert raster.color_bands(["Gray", "Alpha"]) == [1]


class TestDerivedValueText:
    def test_unit_follows_the_quantity(self):
        D = raster.RasterDerivative
        assert raster.format_derived_value(D.SLOPE_DEGREES, 12.345) == "12.35 °" or raster.format_derived_value(D.SLOPE_DEGREES, 12.345) == "12.34 °"
        assert raster.format_derived_value(D.SLOPE_PERCENT, 30.0) == "30.00 %"
        assert raster.format_derived_value(D.ASPECT, 270.0) == "270.00 °"
        assert raster.format_derived_value(D.HILLSHADE, 180.0) == "180.00"  # no unit
        assert raster.format_derived_value(D.ROUGHNESS, 0.5) == "0.50"

    def test_missing_value(self):
        assert raster.format_derived_value(raster.RasterDerivative.ASPECT, None) == "NoData"
        assert raster.format_derived_value(raster.RasterDerivative.ASPECT, None, "n/a") == "n/a"


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


class TestClassQuickSelection:
    def test_invert_keeps_list_order(self):
        assert cloud.inverted_codes([2, 3, 5, 6], [3, 6]) == (2, 5)
        assert cloud.inverted_codes([2, 3], [2, 3]) == ()
        assert cloud.inverted_codes([2, 3], []) == (2, 3)

    def test_pipette_click_replaces_the_classes(self):
        assert cloud.picked_class_codes([2, 5], 6, extend=False) == (6,)

    def test_pipette_ctrl_click_adds_the_class(self):
        assert cloud.picked_class_codes([2, 5], 6, extend=True) == (2, 5, 6)
        assert cloud.picked_class_codes([2, 6], 6, extend=True) == (2, 6)

    def test_summary_with_counts(self):
        assert cloud.class_selection_summary(3, 12, 9_800_000, 38_400_000) == "3 / 12 · 9.8 M / 38.4 M (25.5 %)"

    def test_summary_without_counts(self):
        assert cloud.class_selection_summary(0, 12, None, None) == "0 / 12"
        assert cloud.class_selection_summary(2, 12, None, 100) == "2 / 12"


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


class TestReturnShortcuts:
    def test_available_with_the_attributes(self):
        assert cloud.return_presets_available(("Z", "ReturnNumber", "NumberOfReturns")) == ("first", "last", "single")
        assert cloud.return_presets_available(("Z", "ReturnNumber")) == ("first",)
        assert cloud.return_presets_available(("Z", "NumberOfReturns")) == ("single",)
        assert cloud.return_presets_available(("Z",)) == ()
        assert cloud.return_presets_available(()) == ("first", "last", "single")  # unknown schema

    def test_conditions(self):
        def expression(key):
            return cloud.pc_attributes.conditions_expression([cloud.return_preset_condition(key)])
        assert expression("first") == "ReturnNumber = 1"
        assert expression("last") == "ReturnNumber = NumberOfReturns"
        assert expression("single") == "NumberOfReturns = 1"
        assert cloud.return_preset_condition("last", "OR")["join"] == "OR"

    def test_preset_of_a_condition(self):
        assert cloud.return_preset_of({"attribute": "ReturnNumber", "op": "=", "low": 1}) == "first"
        assert cloud.return_preset_of({"attribute": "ReturnNumber", "op": "=", "low": "NumberOfReturns"}) == "last"
        assert cloud.return_preset_of({"attribute": "NumberOfReturns", "op": "=", "low": 1, "join": "OR"}) == "single"
        assert cloud.return_preset_of({"attribute": "ReturnNumber", "op": "=", "low": 2}) is None
        assert cloud.return_preset_of({"attribute": "Z", "op": "between"}) is None
        assert cloud.return_preset_of("junk") is None


class TestAttributeAliases:
    def test_panel_constants_come_from_the_registry(self):
        assert cloud.Z_ATTRIBUTE == cloud.pc_attributes.Z == "Z"
        assert cloud.HAG_ATTRIBUTE == cloud.pc_attributes.HEIGHT_ABOVE_GROUND == "HeightAboveGround"
        assert cloud.RETURN_NUMBER_ATTRIBUTE == "ReturnNumber"
        assert cloud.NUMBER_OF_RETURNS_ATTRIBUTE == "NumberOfReturns"

    def test_every_registry_label_is_in_the_translation_catalog(self):
        source = (_PROJECT_ROOT / "ui" / "widgets" / "coverage_panels" / "point_cloud_exploring_panel.py").read_text(
            encoding="utf-8")
        for item in cloud.pc_attributes.KNOWN_ATTRIBUTES:
            if item.label not in ("X", "Y", "Z"):
                assert f'self.tr("{item.label}")' in source, item.label


class TestOpenBounds:
    def test_between_bounds_at_the_data_edges_are_dropped(self):
        condition = cloud.pc_attributes.parse_condition({"attribute": "Z", "op": "between", "low": 12.0, "high": 190.0})
        assert cloud.drop_open_bounds(condition, 12.5, 187.0) == dict(condition, low=None, high=None)
        inner = dict(condition, low=20.0, high=100.0)
        assert cloud.drop_open_bounds(inner, 12.5, 187.0) == inner

    def test_one_sided_operators(self):
        at_least = {"attribute": "Intensity", "op": ">=", "low": 0.0, "high": None, "join": "AND"}
        assert cloud.drop_open_bounds(at_least, 0.0, 4095.0)["low"] is None
        at_most = dict(at_least, op="<=", low=4095.0)
        assert cloud.drop_open_bounds(at_most, 0.0, 4095.0)["low"] is None
        assert cloud.drop_open_bounds(dict(at_most, low=200.0), 0.0, 4095.0)["low"] == 200.0

    def test_other_operators_are_kept(self):
        strict = {"attribute": "Intensity", "op": ">", "low": 0.0, "high": None, "join": "AND"}
        assert cloud.drop_open_bounds(strict, 0.0, 4095.0) == strict
        last = {"attribute": "ReturnNumber", "op": "<=", "low": "NumberOfReturns", "high": None, "join": "AND"}
        assert cloud.drop_open_bounds(last, 1.0, 5.0) == last


class TestLegacyStateMigration:
    def test_z_intensity_and_number_return(self):
        state = {"ranges_enabled": True, "z": [10.5, None], "intensity_enabled": True, "intensity": [100, 900],
                 "return": 2}
        assert cloud.parse_point_cloud_state(state)["conditions"] == [
            {"attribute": "Z", "op": "between", "low": 10.5, "high": None, "join": "AND"},
            {"attribute": "Intensity", "op": "between", "low": 100.0, "high": 900.0, "join": "AND"},
            {"attribute": "ReturnNumber", "op": "=", "low": 2.0, "high": None, "join": "AND"},
        ]

    @pytest.mark.parametrize("choice,expected", [
        ("first", "ReturnNumber = 1"), ("last", "ReturnNumber = NumberOfReturns"), ("single", "NumberOfReturns = 1"),
    ])
    def test_return_shortcuts(self, choice, expected):
        conditions = cloud.parse_point_cloud_state({"return": choice})["conditions"]
        assert cloud.pc_attributes.conditions_expression(conditions) == expected

    def test_unchecked_intensity_unbounded_z_and_junk_give_nothing(self):
        state = {"z": [None, None], "intensity_enabled": False, "intensity": [1, 2], "return": 99}
        assert cloud.parse_point_cloud_state(state)["conditions"] == []
        assert cloud.parse_point_cloud_state({"return": [1]})["conditions"] == []
        assert cloud.parse_point_cloud_state({"return": True})["conditions"] == []

    def test_old_keys_are_not_kept(self):
        parsed = cloud.parse_point_cloud_state({"z": [1, 2], "intensity_enabled": True, "return": "first"})
        assert not {"z", "intensity", "intensity_enabled", "return"} & set(parsed)

    def test_conditions_win_over_old_keys(self):
        state = {"z": [1, 2], "conditions": [{"attribute": "Intensity", "op": ">=", "low": 5}]}
        assert [c["attribute"] for c in cloud.parse_point_cloud_state(state)["conditions"]] == ["Intensity"]
        assert cloud.parse_point_cloud_state(dict(state, conditions=[]))["conditions"] == []

    def test_old_hag_keys_keep_working(self):
        state = {"classes_enabled": False, "ranges_enabled": True, "z": [None, 150], "hag_enabled": True,
                 "hag_min": 3, "hag_layer_id": "dtm"}
        assert cloud.build_point_cloud_expression(state) == "Z <= 150 AND HeightAboveGround >= 3"
        assert cloud.hag_from_state(state) == ("dtm", 3.0)


class TestPointCloudCriteriaFromState:
    def test_default_state_is_empty(self):
        criteria = cloud.build_point_cloud_criteria({})
        assert criteria.is_empty
        assert criteria.to_subset_string() == ""
        assert cloud.parse_point_cloud_state({})["conditions"] == []

    def test_classes_count_only_when_the_group_is_checked(self):
        assert cloud.build_point_cloud_criteria({"classes": [6, 2]}).to_subset_string() == "Classification IN (2, 6)"
        assert cloud.build_point_cloud_criteria({"classes_enabled": False, "classes": [2]}).is_empty

    def test_conditions_count_only_when_the_group_is_checked(self):
        state = {"z": [10.5, None], "intensity_enabled": True, "intensity": [100, 900], "return": 1}
        assert cloud.build_point_cloud_criteria(state).is_empty
        state["ranges_enabled"] = True
        assert cloud.build_point_cloud_criteria(state).to_subset_string() == (
            "Z >= 10.5 AND Intensity >= 100 AND Intensity <= 900 AND (ReturnNumber = 1)")

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

    def test_and_chain_keeps_ranges(self):
        state = {"classes_enabled": False, "ranges_enabled": True, "conditions": [
            {"attribute": "Z", "op": "between", "low": 1, "high": 5},
            {"attribute": "Intensity", "op": "<=", "low": 900}]}
        criteria = cloud.build_point_cloud_criteria(state)
        assert [item.attribute for item in criteria.ranges] == ["Z", "Intensity"]
        assert criteria.extra_clauses == ()

    def test_or_chain_is_one_extra_clause(self):
        state = {"classes_enabled": False, "ranges_enabled": True, "conditions": [
            {"attribute": "Z", "op": "between", "low": 1, "high": 5},
            {"attribute": "Intensity", "op": ">=", "low": 100, "join": "OR"}]}
        criteria = cloud.build_point_cloud_criteria(state)
        assert criteria.ranges == ()
        assert criteria.extra_clauses == ("(Z >= 1 AND Z <= 5) OR (Intensity >= 100)",)

    def test_exact_bounds_are_not_rounded(self):
        state = {"ranges_enabled": True, "z": [12.3456, 187.0004]}
        assert cloud.build_point_cloud_criteria(state).to_subset_string() == "Z >= 12.3456 AND Z <= 187.0004"

    def test_inverted_bounds_and_junk_are_tolerated(self):
        parsed = cloud.parse_point_cloud_state({"z": [5, 1], "classes": [2, 2.5, 300, "x"], "return": 99,
                                                "hag_min": "x", "hag_layer_id": 3})
        assert parsed["conditions"] == [{"attribute": "Z", "op": "between", "low": 1.0, "high": 5.0, "join": "AND"}]
        assert parsed["classes"] == [2]
        assert (parsed["hag_min"], parsed["hag_layer_id"]) == (cloud.DEFAULT_HAG_MIN, None)

    def test_parse_is_idempotent(self):
        state = {"classes": [6, 2], "ranges_enabled": True, "z": [1, 2], "return": "single",
                 "hag_enabled": True, "hag_min": 3, "hag_layer_id": "dtm", "expression": "Z > 2"}
        once = cloud.parse_point_cloud_state(state)
        assert cloud.parse_point_cloud_state(once) == once

    def test_conditions_round_trip(self):
        conditions = [
            {"attribute": "Z", "op": "between", "low": 1.5, "high": None, "join": "AND"},
            {"attribute": "Scan Angle", "op": "<>", "low": 0.0, "high": None, "join": "OR"},
            {"attribute": "ReturnNumber", "op": "=", "low": "NumberOfReturns", "high": None, "join": "AND"},
        ]
        state = {"layer_id": "lidar", "classes_enabled": False, "classes": [], "ranges_enabled": True,
                 "conditions": conditions, "hag_enabled": False, "hag_min": 2.0, "hag_layer_id": None,
                 "expression_enabled": False, "expression": "", "apply_to_tiles": True,
                 "pick_attribute": "Z", "pick_tolerance": 5.0, "zone_wkt": "",
                 "objects": {"target": "object", "ratio": [0.5, 2.0], "items": [], "detected": None}}
        assert cloud.parse_point_cloud_state(state) == state


class TestPointCloudExpression:
    def test_generated_expression(self):
        assert cloud.build_point_cloud_expression({"classes": [2]}) == "Classification = 2"

    def test_or_chain_is_not_double_parenthesised(self):
        state = {"classes_enabled": False, "ranges_enabled": True, "conditions": [
            {"attribute": "Z", "op": "between", "low": 1, "high": 5},
            {"attribute": "Intensity", "op": ">=", "low": 100, "join": "OR"}]}
        assert cloud.build_point_cloud_expression(state) == "(Z >= 1 AND Z <= 5) OR (Intensity >= 100)"
        assert cloud.generated_expression(state) == "(Z >= 1 AND Z <= 5) OR (Intensity >= 100)"

    def test_lone_shortcut_is_bare(self):
        state = {"classes_enabled": False, "ranges_enabled": True, "return": "last"}
        assert cloud.build_point_cloud_expression(state) == "ReturnNumber = NumberOfReturns"

    def test_or_chain_is_wrapped_before_the_height(self):
        state = {"classes_enabled": False, "ranges_enabled": True, "hag_enabled": True, "hag_min": 2,
                 "hag_layer_id": "dtm", "conditions": [
                     {"attribute": "Z", "op": ">", "low": 300},
                     {"attribute": "Intensity", "op": "<", "low": 50, "join": "OR"}]}
        assert cloud.build_point_cloud_expression(state) == (
            "((Z > 300) OR (Intensity < 50)) AND HeightAboveGround >= 2")
        assert cloud.build_point_cloud_expression(state, hag_available=False) == "(Z > 300) OR (Intensity < 50)"

    def test_classes_and_or_chain(self):
        state = {"classes": [6], "ranges_enabled": True, "conditions": [
            {"attribute": "Z", "op": ">", "low": 300}, {"attribute": "Intensity", "op": "<", "low": 50, "join": "OR"}]}
        assert cloud.build_point_cloud_expression(state) == "Classification = 6 AND ((Z > 300) OR (Intensity < 50))"

    def test_height_above_dtm_is_appended(self):
        state = {"classes": [5], "ranges_enabled": True, "hag_enabled": True, "hag_min": 2.5, "hag_layer_id": "dtm"}
        assert cloud.build_point_cloud_expression(state) == "Classification = 5 AND HeightAboveGround >= 2.5"
        assert cloud.hag_from_state(state) == ("dtm", 2.5)

    def test_height_needs_layer_and_availability_whatever_the_active_group(self):
        # 2026-10-18: HEIGHT / DTM is its own group, ANDed whatever the active group.
        base = {"classes": [5], "ranges_enabled": True, "hag_enabled": True, "hag_layer_id": "dtm"}
        assert cloud.build_point_cloud_expression(base, hag_available=False) == "Classification = 5"
        assert cloud.hag_from_state(dict(base, ranges_enabled=False)) == ("dtm", cloud.DEFAULT_HAG_MIN)
        assert cloud.build_point_cloud_expression(dict(base, ranges_enabled=False)) == (
            "Classification = 5 AND HeightAboveGround >= 2")
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


class TestBandRoles:
    """2026-10-18: the BANDS block, the roles of the bands read from the renderer or guessed."""

    def test_roles_from_the_multiband_renderer_are_known(self):
        roles, guessed = raster.default_roles(["Band 1", "Band 2", "Band 3", "Band 4"], (),
                                              {"R": 2, "G": 3, "B": 4})
        assert roles == {2: "R", 3: "G", 4: "B", 1: "NIR"} and guessed is False

    def test_rgba_renderer_leaves_the_alpha_band_without_a_role(self):
        roles, guessed = raster.default_roles(["Band 1", "Band 2", "Band 3", "Band 4"], {4}, {"R": 1, "G": 2, "B": 3})
        assert roles == {1: "R", 2: "G", 3: "B"} and guessed is False

    def test_without_a_colour_renderer_the_roles_are_guessed(self):
        roles, guessed = raster.default_roles(["Band 1", "Band 2", "Band 3"], (), {"gray": 1})
        assert roles == {1: "R", 2: "G", 3: "B"} and guessed is True
        roles, guessed = raster.default_roles(["R", "G", "B", "N"], ())
        assert roles == {1: "R", 2: "G", 3: "B", 4: "NIR"} and guessed is True

    def test_a_band_named_infrared_takes_the_nir_role(self):
        roles, guessed = raster.default_roles(["NIR", "Red", "Green"], ())
        assert roles == {1: "NIR", 2: "R", 3: "G"} and guessed is True

    def test_a_single_band_has_no_role(self):
        assert raster.default_roles(["elevation"], ()) == ({}, False)
        assert raster.default_roles(["Gray", "Alpha"], {2}) == ({}, False)

    def test_layouts_and_roles_round_trip(self):
        assert raster.roles_from_layout("irc", [1, 2, 3]) == {1: "NIR", 2: "R", 3: "G"}
        assert raster.roles_from_layout("rgbn", [1, 2, 3]) == {1: "R", 2: "G", 3: "B"}  # no fourth band: no NIR
        assert raster.layout_from_roles({1: "NIR", 2: "R", 3: "G"}) == "irc"
        assert raster.layout_from_roles({1: "R", 2: "G", 3: "B", 4: "NIR"}) == "rgbn"
        assert raster.layout_from_roles({2: "R", 3: "G", 4: "B", 1: "NIR"}) == ""  # a custom arrangement
        assert raster.layout_from_roles({}) == ""

    def test_spectral_presets_follow_the_roles(self):
        roles = {2: "R", 3: "G", 4: "B", 1: "NIR"}
        assert raster.spectral_presets_for(roles) == ["ndvi_vegetation", "ndvi_bare", "ndwi_water", "exg_vegetation"]
        assert raster.spectral_expression("ndvi_vegetation", roles, "o") == '("o@1" - "o@2") / ("o@1" + "o@2") > 0.3'
        assert raster.spectral_presets_for({1: "R", 2: "G", 3: "B"}) == ["exg_vegetation"]

    def test_roles_in_the_state(self):
        parsed = raster.parse_raster_state({"roles": {"1": "NIR", "2": "R", "x": "G", "3": "R", "4": "weird"},
                                            "roles_chosen": True, "pipette_bands": [1, 2, 2, "3", 0]})
        assert parsed["roles"] == {1: "NIR", 2: "R"} and parsed["roles_chosen"] is True
        assert parsed["pipette_bands"] == [1, 2, 3]

    def test_a_saved_layout_becomes_roles(self):
        parsed = raster.parse_raster_state({"layout": "irc"})
        assert parsed["roles"] == {1: "NIR", 2: "R", 3: "G"} and parsed["roles_chosen"] is True

    def test_short_band_name(self):
        assert raster.short_band_name(1, "Band 1: idw") == "idw"
        assert raster.short_band_name(2, "Band 2") == ""
        assert raster.short_band_name(3, "elevation") == "elevation"

    def test_expression_starts_from_the_previous_group(self):
        D = raster.RasterSelectionMode
        assert raster.previous_group_formula(RasterSelection(band=1, mode=D.RANGE, minimum=200.0, maximum=260.0), "mnt") == (
            '("mnt@1" >= 200 AND "mnt@1" <= 260)')
        assert raster.previous_group_formula(RasterSelection(band=1, mode=D.EXPRESSION, expression=' "a@1" > 1 '), "a") == '"a@1" > 1'
        assert raster.previous_group_formula(RasterSelection(band=1, mode=D.RANGE, maximum=12.0,
                                                             derivative=raster.RasterDerivative.SLOPE_DEGREES), "m") == ""
        assert raster.previous_group_formula(None, "m") == ""

    def test_classes_mode_in_a_saved_state_still_builds_a_selection(self):
        # The CLASSES group is gone from the panel; a saved selection of that mode stays readable.
        selection = raster.build_raster_selection({"mode": "classes", "classes": [3]})
        assert selection.mode is RasterSelectionMode.CLASSES

    def test_pipette_on_is_part_of_the_state(self):
        assert raster.parse_raster_state({"pipette_on": True})["pipette_on"] is True
        assert raster.parse_raster_state({})["pipette_on"] is False


class TestEveryBandMode:
    """2026-10-18: the value range may apply to every colour band at once (ANDed), as an expression."""

    def test_expression_ands_the_range_of_every_band(self):
        assert raster.all_bands_range_expression([1, 2, 3], 10.0, 50.0, "o") == (
            '("o@1" >= 10 AND "o@1" <= 50) AND ("o@2" >= 10 AND "o@2" <= 50) AND ("o@3" >= 10 AND "o@3" <= 50)')
        assert raster.all_bands_range_expression([1, 2], None, 50.0, "o") == '("o@1" <= 50) AND ("o@2" <= 50)'
        assert raster.all_bands_range_expression([1, 2], None, None, "o") == ""
        assert raster.all_bands_range_expression([], 1.0, 2.0, "o") == ""

    def test_state_builds_an_expression_selection(self):
        state = {"mode": "range", "band": 1, "minimum": 10.0, "maximum": 50.0, "all_bands": True,
                 "range_bands": [1, 2, 3], "reference": "ortho"}
        selection = raster.build_raster_selection(state)
        assert selection.mode is RasterSelectionMode.EXPRESSION and selection.band == 1
        assert selection.expression.startswith('("ortho@1" >= 10 AND "ortho@1" <= 50) AND ("ortho@2"')

    def test_one_band_stays_a_plain_range(self):
        state = {"mode": "range", "band": 2, "minimum": 10.0, "all_bands": True, "range_bands": [2]}
        selection = raster.build_raster_selection(state)
        assert selection.mode is RasterSelectionMode.RANGE and selection.band == 2

    def test_state_keys_are_parsed(self):
        parsed = raster.parse_raster_state({"all_bands": 1, "range_bands": [3, "1", 3]})
        assert parsed["all_bands"] is True and parsed["range_bands"] == [3, 1]
        assert raster.parse_raster_state({})["all_bands"] is False


class TestValuePipetteAndZone:
    """2026-10-18: the tools of ATTRIBUTES write conditions."""

    def test_value_condition_uses_the_observed_range(self):
        condition = cloud.value_condition("Z", 1245.0, 5.0, (1189.0, 1389.0))
        assert condition["attribute"] == "Z" and condition["op"] == "between"
        assert (condition["low"], condition["high"]) == (1235.0, 1255.0) and condition["join"] == "AND"

    def test_value_condition_without_bounds_uses_the_value(self):
        condition = cloud.value_condition("Intensity", 200.0, 10.0, None, "OR")
        assert (condition["low"], condition["high"]) == (180.0, 220.0) and condition["join"] == "OR"
        assert cloud.value_condition("Z", 0.0, 10.0, None)["high"] == 0.1  # a span of at least 1

    def test_zone_conditions_are_x_and_y_between(self):
        conditions = cloud.zone_conditions(10.0, 30.0, 5.0, 20.0)
        assert [c["attribute"] for c in conditions] == ["X", "Y"]
        assert (conditions[0]["low"], conditions[0]["high"]) == (5.0, 10.0)
        assert (conditions[1]["low"], conditions[1]["high"]) == (20.0, 30.0)
        assert all(c["join"] == "AND" for c in conditions)

    def test_zone_conditions_make_a_subset_string(self):
        state = {"classes_enabled": False, "ranges_enabled": True, "conditions": cloud.zone_conditions(1, 2, 3, 4)}
        assert cloud.build_point_cloud_expression(state) == "X >= 1 AND X <= 3 AND Y >= 2 AND Y <= 4"

    def test_pick_settings_in_the_state(self):
        parsed = cloud.parse_point_cloud_state({"pick_attribute": "Intensity", "pick_tolerance": 12.5})
        assert (parsed["pick_attribute"], parsed["pick_tolerance"]) == ("Intensity", 12.5)
        parsed = cloud.parse_point_cloud_state({"pick_attribute": 3, "pick_tolerance": -1})
        assert (parsed["pick_attribute"], parsed["pick_tolerance"]) == ("Z", cloud.DEFAULT_PICK_TOLERANCE)


def _object(code, box, x=None, y=None, wkt="POLYGON((0 0,1 0,1 1,0 0))", truncated=False):
    return {"x": box[0] if x is None else x, "y": box[1] if y is None else y, "code": code, "box": list(box),
            "wkt": wkt, "truncated": truncated}


class TestPointCloudObjects:
    """2026-10-18: the object detector of CLASSES; each object keeps its class and its box goes to the subset."""

    def test_default_objects_state(self):
        assert cloud.parse_objects_state(None) == {"target": "object", "ratio": [0.5, 2.0], "items": [], "detected": None}

    def test_objects_state_is_normalised_and_idempotent(self):
        state = {"target": "similar_objects", "ratio": [3, 0.25],
                 "items": [_object(6, (10, 20, 5, 30)), {"x": "a", "y": 1, "code": 6, "box": [0, 0, 1, 1]},
                           _object(300, (0, 0, 1, 1)), _object(5, (0, 0, 1, 1), x=float("nan"))],
                 "detected": {"wkt": "MULTIPOLYGON(...)", "boxes": [[6, 0, 0, 1, 1], [6, "x", 0, 1, 1], [7, 0, 0]],
                              "count": 4, "area": -2, "truncated": 1}}
        parsed = cloud.parse_objects_state(state)
        assert parsed["target"] == "similar_objects" and parsed["ratio"] == [0.25, 3.0]
        assert [item["code"] for item in parsed["items"]] == [6]  # the invalid ones are dropped
        assert parsed["items"][0]["box"] == [5.0, 20.0, 10.0, 30.0]  # sides ordered
        assert parsed["detected"] == {"wkt": "MULTIPOLYGON(...)", "boxes": [[6, 0.0, 0.0, 1.0, 1.0]], "count": 4,
                                      "area": None, "truncated": True}
        assert cloud.parse_objects_state(parsed) == parsed

    def test_unknown_target_and_bad_ratio(self):
        parsed = cloud.parse_objects_state({"target": "pool", "ratio": [0, 2]})
        assert parsed["target"] == "object" and parsed["ratio"] == [0.5, 2.0]

    def test_detection_without_object_is_dropped(self):
        assert cloud.parse_objects_state({"detected": {"wkt": "POLYGON(...)"}})["detected"] is None

    def test_one_object_is_its_class_in_its_box(self):
        assert cloud.object_expression([[6, 1, 2, 3, 4.5]]) == (
            "Classification = 6 AND X >= 1 AND X <= 3 AND Y >= 2 AND Y <= 4.5")

    def test_objects_are_ored_each_with_its_class(self):
        assert cloud.object_expression([[6, 0, 0, 1, 1], [5, 10, 10, 12, 12]]) == (
            "(Classification = 6 AND X >= 0 AND X <= 1 AND Y >= 0 AND Y <= 1) OR "
            "(Classification = 5 AND X >= 10 AND X <= 12 AND Y >= 10 AND Y <= 12)")

    def test_many_objects_keep_one_box_per_class(self):
        boxes = [[6, i, i, i + 1, i + 1] for i in range(5)] + [[2, 50, 60, 51, 61]]
        assert cloud.object_expression(boxes, limit=4) == (
            "(Classification = 2 AND X >= 50 AND X <= 51 AND Y >= 60 AND Y <= 61) OR "
            "(Classification = 6 AND X >= 0 AND X <= 5 AND Y >= 0 AND Y <= 5)")
        assert cloud.object_expression([]) == ""

    def test_objects_replace_their_classes_in_the_subset(self):
        state = {"classes_enabled": True, "classes": [6], "objects": {"items": [_object(6, (0, 0, 1, 1))]}}
        assert cloud.build_point_cloud_expression(state) == "Classification = 6 AND X >= 0 AND X <= 1 AND Y >= 0 AND Y <= 1"

    def test_the_detected_boxes_win_over_the_clicks(self):
        objects = {"target": "similar_objects", "items": [_object(6, (0, 0, 1, 1))],
                   "detected": {"wkt": "", "boxes": [[6, 0, 0, 1, 1], [6, 5, 5, 6, 6]], "count": 2}}
        state = {"classes_enabled": True, "classes": [6], "objects": objects}
        assert cloud.build_point_cloud_expression(state).count("Classification = 6") == 2

    def test_objects_are_wrapped_before_the_height(self):
        state = {"classes_enabled": True, "classes": [5, 6], "hag_enabled": True, "hag_min": 2, "hag_layer_id": "dtm",
                 "objects": {"items": [_object(6, (0, 0, 1, 1)), _object(5, (2, 2, 3, 3))]}}
        expression = cloud.build_point_cloud_expression(state)
        assert expression.startswith("((Classification = 6") and expression.endswith(") AND HeightAboveGround >= 2")

    def test_objects_apply_with_classes_only(self):
        state = {"classes_enabled": False, "ranges_enabled": True, "conditions": cloud.zone_conditions(1, 2, 3, 4),
                 "objects": {"items": [_object(6, (0, 0, 1, 1))]}}
        assert cloud.build_point_cloud_expression(state) == "X >= 1 AND X <= 3 AND Y >= 2 AND Y <= 4"

    def test_object_summary(self):
        assert cloud.object_summary(3, 1250.0, False) == "3 object(s) · 1250 m²"
        assert cloud.object_summary(1, None, True) == "1 object(s) · cut at the window read"


class TestPointCloudClassLists:
    def test_present_and_absent_classes(self):
        present, absent = cloud.split_classes([(2, 100), (6, 0), (9, -1), (5, 3)])
        assert present == [(2, 100), (9, -1), (5, 3)] and absent == [(6, 0)]

    def test_weight_share(self):
        assert cloud.weight_share(50, 100) == 0.5
        assert cloud.weight_share(200, 100) == 1.0
        assert cloud.weight_share(-1, 100) == 0.0 and cloud.weight_share(5, 0) == 0.0


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


class TestDtmLayerCombo:
    """PDAL hag_dem reads a file through GDAL: the DTM list leaves out WMS / XYZ / WCS like the layer
    lists, and the virtual / PostGIS rasters."""

    def test_rasters_pdal_cannot_read_are_excluded(self, monkeypatch):
        for name, path in ((".adapters", _PROJECT_ROOT / "adapters"),
                           (".adapters.qgis", _PROJECT_ROOT / "adapters" / "qgis")):
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]  # the real modules, without running the package __init__
            monkeypatch.setitem(sys.modules, _PKG + name, package)
        capability = f"{_PKG}.adapters.qgis.point_cloud_capability"
        excluded = ["ogr"]
        combo = types.SimpleNamespace(excludedProviders=lambda: list(excluded),
                                      setExcludedProviders=lambda providers: excluded.__init__(providers))
        try:
            cloud._dtm_rasters_only(combo)
        finally:
            sys.modules.pop(capability, None)
        assert excluded[0] == "ogr"
        assert {"wms", "wcs", "arcgismapserver", "virtualraster", "postgresraster"} <= set(excluded)
        assert "gdal" not in excluded and len(excluded) == len(set(excluded))

    def test_the_dtm_combo_uses_it(self):
        import ast
        path = _PROJECT_ROOT / "ui" / "widgets" / "coverage_panels" / "point_cloud_exploring_panel.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        build = next(node for node in ast.walk(tree)
                     if isinstance(node, ast.FunctionDef) and node.name == "_build_hag_group")  # HEIGHT / DTM group
        assert "_dtm_rasters_only(self._hag_layer_combo)" in ast.unparse(build)
