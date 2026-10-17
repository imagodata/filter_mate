# -*- coding: utf-8 -*-
"""
2026-10-17: the alpha band of an RGBA orthophoto is recognised by its colour interpretation.

The raster EXPLORING panel left a band out of the colours when its NAME held
"alpha", but QGIS names the bands of a GeoTIFF "Band 1" ... "Band 4": an
RGBA orthophoto was taken for RGB + infrared, its default layout was "rgbn"
and the NDVI preset used the alpha band as the infrared band. The adapter
now reads ``provider.colorInterpretation(band)`` (as ``_sync_alpha_band``
does) into ``RasterBandInfo.is_alpha``, and the panel helpers take the alpha
band numbers.
"""
import importlib
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_raster_alpha_test"


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.domain", _ROOT / "core" / "domain"),
                       (".adapters", _ROOT / "adapters"), (".adapters.qgis", _ROOT / "adapters" / "qgis"),
                       (".adapters.qgis.coverage_layers", _ROOT / "adapters" / "qgis" / "coverage_layers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.adapters.qgis.coverage_layers.raster_adapter")


adapter = _load()
ALPHA = adapter.Qgis.RasterColorInterpretation.AlphaBand


def _rgba_layer():
    provider = MagicMock()
    provider.colorInterpretation.side_effect = lambda band: ALPHA if band == 4 else MagicMock(name=f"colour{band}")
    provider.sourceHasNoDataValue.return_value = False
    provider.dataType.return_value = 1
    layer = MagicMock()
    layer.dataProvider.return_value = provider
    layer.bandCount.return_value = 4
    layer.bandName.side_effect = lambda band: f"Band {band}"
    layer.width.return_value = layer.height.return_value = 10
    return layer


def test_summary_flags_the_alpha_band_whatever_its_name():
    summary = adapter.read_raster_summary(_rgba_layer())
    assert [info.name for info in summary.bands] == ["Band 1", "Band 2", "Band 3", "Band 4"]
    assert [info.is_alpha for info in summary.bands] == [False, False, False, True]


def test_is_alpha_band_falls_back_to_the_pre_3_30_value(monkeypatch):
    monkeypatch.setattr(adapter, "Qgis", types.SimpleNamespace())  # no Qgis.RasterColorInterpretation
    provider = MagicMock()
    provider.colorInterpretation.return_value = 6  # QgsRaster.AlphaBand
    assert adapter.is_alpha_band(provider, 4) is True
    provider.colorInterpretation.return_value = 3
    assert adapter.is_alpha_band(provider, 1) is False


def _load_panel():
    for name, path in ((".ui", _ROOT / "ui"), (".ui.widgets", _ROOT / "ui" / "widgets"),
                       (".ui.widgets.coverage_panels", _ROOT / "ui" / "widgets" / "coverage_panels")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.ui.widgets.coverage_panels.raster_exploring_panel")


@pytest.fixture(scope="module")
def raster():
    return _load_panel()


class TestPanelHelpers:

    NAMES = ["Band 1", "Band 2", "Band 3", "Band 4"]

    def test_rgba_is_rgb(self, raster):
        assert raster.color_bands(self.NAMES, alpha_bands={4}) == [1, 2, 3]
        assert raster.default_band_layout(self.NAMES, alpha_bands={4}) == "rgb"
        assert raster.layouts_for(self.NAMES, alpha_bands={4}) == ["rgb", "irc"]

    def test_four_colour_bands_still_offer_infrared(self, raster):
        assert raster.default_band_layout(self.NAMES) == "rgbn"
        assert raster.layouts_for(self.NAMES) == ["rgb", "irc", "rgbn"]

    def test_alpha_named_band_still_left_out(self, raster):
        assert raster.color_bands(["Red", "Green", "Blue", "Alpha"]) == [1, 2, 3]
