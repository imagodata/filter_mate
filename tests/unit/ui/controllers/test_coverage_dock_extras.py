# -*- coding: utf-8 -*-
"""
FilterMate 5 dock additions (mockup): layer card, kind tools and source
geometry line - the pure text builders of ``coverage_dock_extras`` and the
zone statistics of the raster panel.

Loaded by path under a private synthetic package, like the coverage widget
tests: the real domain modules are used, Qt / QGIS resolve to the root mocks.
"""
import importlib
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_cov_extras_test"


def _load_modules():
    for name, path in (
        ("", _ROOT),
        (".core", _ROOT / "core"),
        (".core.domain", _ROOT / "core" / "domain"),
        (".ui", _ROOT / "ui"),
        (".ui.controllers", _ROOT / "ui" / "controllers"),
        (".ui.widgets", _ROOT / "ui" / "widgets"),
        (".ui.widgets.coverage_panels", _ROOT / "ui" / "widgets" / "coverage_panels"),
    ):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        package.__package__ = _PKG + name
        sys.modules[_PKG + name] = package
    return (
        importlib.import_module(f"{_PKG}.ui.controllers.coverage_dock_extras"),
        importlib.import_module(f"{_PKG}.ui.widgets.coverage_panels.raster_exploring_panel"),
    )


extras, raster = _load_modules()


class TestNumbers:
    def test_trailing_zeros_are_dropped(self):
        assert extras.format_number(1.0) == "1"
        assert extras.format_number(0.5) == "0.5"
        assert extras.format_number(141.84) == "141.84"
        assert extras.format_number(-99999.0, 3) == "-99999"

    def test_rounding_to_zero_has_no_sign(self):
        assert extras.format_number(-0.001) == "0"

    def test_invalid_values_give_an_empty_text(self):
        assert extras.format_number(None) == ""
        assert extras.format_number(float("nan")) == ""
        assert extras.format_number("abc") == ""


class TestPixelSize:
    def test_square_pixel(self):
        assert extras.pixel_size_text(1.0, 1.0, "m") == "1 m"

    def test_rectangular_pixel(self):
        assert extras.pixel_size_text(0.5, 0.25, "m") == "0.5 × 0.25 m"
        assert extras.pixel_size_text(0.125, 0.125, "m") == "0.125 m"

    def test_geographic_pixel_keeps_six_decimals(self):
        assert extras.pixel_size_text(0.000278, 0.000278, "°") == "0.000278 °"

    def test_unknown_size(self):
        assert extras.pixel_size_text(0.0, 1.0, "m") == ""
        assert extras.pixel_size_text(None, 1.0) == ""

    def test_no_unit(self):
        assert extras.pixel_size_text(5.0, 5.0) == "5"


class TestRasterCard:
    def test_single_band_dtm(self):
        text = extras.raster_card_text([("Float32", -99999.0)], 1.0, 1.0, "m")
        assert text == "1 band · Float32 · 1 m · NoData -99999"

    def test_rgb_without_nodata(self):
        text = extras.raster_card_text([("Byte", None)] * 3, 0.2, 0.2, "m")
        assert text == "3 bands · Byte · 0.2 m"

    def test_mixed_data_types(self):
        text = extras.raster_card_text([("Byte", None), ("Float32", None)], 1.0, 1.0)
        assert text == "2 bands · Byte / Float32 · 1"

    def test_translation_function_is_used(self):
        text = extras.raster_card_text([("Byte", None)], 1.0, 1.0, "m", translate=lambda t: t.replace("band", "bande"))
        assert text.startswith("1 bande")


class TestPointCloudCard:
    def test_count_and_elevation(self):
        assert extras.point_cloud_card_text(38_400_000, (141.8, 318.7)) == "38.4 M points · Z 141.8 → 318.7"

    def test_unknown_count(self):
        assert extras.point_cloud_card_text(-1, (0.0, 12.5)) == "Z 0 → 12.5"

    def test_nothing_known(self):
        assert extras.point_cloud_card_text(None, None) == ""


class TestTools:
    def test_raster_tools(self):
        assert extras.tools_for("raster") == ["pushButton_checkable_exploring_raster_hover",
                                              "pushButton_checkable_exploring_raster_zone",
                                              "pushButton_checkable_exploring_raster_link"]

    def test_point_cloud_tools(self):
        assert extras.tools_for("point_cloud") == ["pushButton_exploring_point_cloud_profile",
                                                   "pushButton_exploring_point_cloud_3d"]

    def test_vector_has_no_extra_tool(self):
        assert extras.tools_for("vector") == []

    def test_names_match_the_dock_style_selectors(self):
        for kind in ("raster", "point_cloud"):
            for name in extras.tools_for(kind):
                assert name.startswith(("pushButton_exploring_", "pushButton_checkable_exploring_"))

    def test_every_tool_has_an_icon(self):
        assert all(body.strip().startswith("<") for body in (extras.ICON_HOVER, extras.ICON_ZONE, extras.ICON_LINK_STYLE,
                                                            extras.ICON_PROFILE, extras.ICON_3D))


class TestZone:
    def test_pixel_estimate(self):
        assert extras.zone_pixel_estimate(100.0, 50.0, 1.0, 1.0) == 5000
        assert extras.zone_pixel_estimate(100.0, 50.0, 0.0, 1.0) is None

    def test_statistics_text(self):
        text = raster.format_zone_statistics(198.4, 251.07, 221.3, 12450, 3)
        assert text == "min 198.400 · max 251.070 · mean 221.300 · 12450 px"

    def test_integer_band_mean_keeps_one_decimal(self):
        assert raster.format_zone_statistics(2.0, 9.0, 4.25, None, 0) == "min 2 · max 9 · mean 4.2"

    def test_empty_zone(self):
        assert raster.format_zone_statistics(None, None, None, 0, 3) == ""


def test_svg_document_carries_the_color():
    document = extras._svg_document(extras.ICON_3D, "#e0e0e0")
    assert 'stroke="#e0e0e0"' in document and document.endswith("</svg>")


def test_3d_action_tries_the_qgis_4_name_first():
    assert extras.ACTION_NEW_3D_VIEW[0] == "mActionNew3DMapCanvas"
    assert "mActionNew3DMapView" in extras.ACTION_NEW_3D_VIEW
    assert extras.ACTION_ELEVATION_PROFILE == ("mActionElevationProfile",)


def test_float32_nodata_is_short():
    text = extras.raster_card_text([("Float32", -3.4028234663852886e38)], 1.0, 1.0, "m")
    assert text.endswith("NoData -3.40282e+38")


def test_nan_nodata_is_left_out():
    assert "NoData" not in extras.raster_card_text([("Float32", float("nan"))], 1.0, 1.0, "m")


class TestVectorCard:
    def test_geometry_and_count(self):
        assert extras.vector_card_text("Line", 12438) == "Line · 12 438 features"

    def test_unknown_count(self):
        assert extras.vector_card_text("Polygon", -1) == "Polygon"
        assert extras.vector_card_text("", None) == ""

    def test_card_html_escapes_and_colors(self):
        html = extras.card_html("a<b", "Vector", "Line", "#6fb1f0", square=False)
        assert "a&lt;b" in html and "#6fb1f0" in html and "●" in html and "Vector · Line" in html
        assert "■" in extras.card_html("mnt", "Raster", "", "#f0b35a", square=True)
