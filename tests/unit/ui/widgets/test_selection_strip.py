# -*- coding: utf-8 -*-
"""
FilterMate 5 selection strip between EXPLORING and FILTERING (mockup): the
pure text builders of ``ui/widgets/selection_strip.py``.

Loaded by path under a private synthetic package, like the coverage widget
tests: Qt / QGIS resolve to the root mocks.
"""
import importlib
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_selection_strip_test"


def _load():
    for name, path in (
        ("", _ROOT),
        (".core", _ROOT / "core"),
        (".core.domain", _ROOT / "core" / "domain"),
        (".ui", _ROOT / "ui"),
        (".ui.widgets", _ROOT / "ui" / "widgets"),
        (".ui.widgets.coverage_panels", _ROOT / "ui" / "widgets" / "coverage_panels"),
    ):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        package.__package__ = _PKG + name
        sys.modules[_PKG + name] = package
    return (importlib.import_module(f"{_PKG}.ui.widgets.selection_strip"),
            importlib.import_module(f"{_PKG}.core.domain.raster_filter_criteria"))


strip, criteria = _load()
RasterSelection, Mode, Derivative = criteria.RasterSelection, criteria.RasterSelectionMode, criteria.RasterDerivative


class TestVectorValue:
    def test_counted_features(self):
        assert strip.vector_strip_value("multiple_selection", 3) == "3 feature(s)"
        assert strip.vector_strip_value("custom_selection", 12438) == "12 438 feature(s)"

    def test_single_selection_without_feature_stops_the_filter(self):
        assert strip.vector_strip_value("single_selection", 0) == "no feature selected"

    def test_no_selection_uses_the_whole_layer(self):
        assert strip.vector_strip_value("multiple_selection", 0) == "whole layer"
        assert strip.vector_strip_value("custom_selection", None) == "whole layer"

    def test_custom_expression_not_evaluated_yet(self):
        assert strip.vector_strip_value("custom_selection", None, has_expression=True) == "expression"

    def test_translation_function_is_used(self):
        assert strip.vector_strip_value("multiple_selection", 2, translate=lambda t: t.replace("feature(s)", "entité(s)")) \
            == "2 entité(s)"


class TestRasterValue:
    def test_range_with_kept_share(self):
        selection = RasterSelection(minimum=200.0, maximum=260.0)
        assert strip.raster_strip_value(selection, 0.389) == "200 – 260 · 38.9 %"

    def test_open_ranges(self):
        assert strip.raster_strip_value(RasterSelection(minimum=2.5), None) == "≥ 2.5"
        assert strip.raster_strip_value(RasterSelection(maximum=10.0), None) == "≤ 10"

    def test_terrain_derivative_keeps_its_unit(self):
        selection = RasterSelection(minimum=0.0, maximum=15.0, derivative=Derivative.SLOPE_PERCENT)
        assert strip.raster_strip_value(selection, 0.5) == "0 – 15 % · 50.0 %"

    def test_classes(self):
        selection = RasterSelection(mode=Mode.CLASSES, classes=frozenset({1, 4, 7}))
        assert strip.raster_strip_value(selection, 0.12) == "3 class(es) · 12.0 %"

    def test_expression_has_no_share(self):
        selection = RasterSelection(mode=Mode.EXPRESSION, expression='"mnt@1" > 200')
        assert strip.raster_strip_value(selection, None) == "raster expression"

    def test_no_selection(self):
        assert strip.raster_strip_value(None, None) == "no constraint"


class TestPointCloudValue:
    def test_counted_classes(self):
        assert strip.point_cloud_strip_value(18_900_000, 38_400_000) == "18.9 M / 38.4 M (49.2 %)"

    def test_height_above_the_dtm_makes_it_an_upper_bound(self):
        assert strip.point_cloud_strip_value(9_800_000, 38_400_000, at_most=True).startswith("≤ 9.8 M")

    def test_uncounted_criteria_show_the_expression(self):
        assert strip.point_cloud_strip_value(None, 38_400_000, " Z >= 200 ") == "Z >= 200"

    def test_no_criteria_keeps_every_point(self):
        assert strip.point_cloud_strip_value(None, 38_400_000, "") == "all points · 38.4 M"
        assert strip.point_cloud_strip_value(None, None, "") == "all points"


def test_names_match_the_dock_style_selectors():
    qss = (_ROOT / "resources" / "styles" / "mockup.qss").read_text(encoding="utf-8")
    for name in (strip.STRIP_NAME, strip.VALUE_NAME):
        assert f"#{name}" in qss
    for kind in ("raster", "point_cloud"):
        assert f'{strip.KIND_PROPERTY}="{kind}"' in qss


def test_every_strip_token_has_a_light_and_a_dark_value():
    qss = (_ROOT / "resources" / "styles" / "mockup.qss").read_text(encoding="utf-8")
    design = (_ROOT / "ui" / "styles" / "mockup_design.py").read_text(encoding="utf-8")
    for kind in ("vector", "raster", "point_cloud"):
        for part in ("bg", "border", "text"):
            token = f"fm_strip_{kind}_{part}"
            assert "{" + token + "}" in qss
            assert design.count(f"'{token}'") == 2  # dark and light
