# -*- coding: utf-8 -*-
"""Preview veil of an expression selection (colour pipette): NoData, CRS fit (2026-10-18)."""
import importlib
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_preview_overlay_test"


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.domain", _ROOT / "core" / "domain"),
                       (".adapters", _ROOT / "adapters"), (".adapters.qgis", _ROOT / "adapters" / "qgis"),
                       (".adapters.qgis.coverage_layers", _ROOT / "adapters" / "qgis" / "coverage_layers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.adapters.qgis.coverage_layers.preview_overlay")


overlay = _load()
_criteria = importlib.import_module(f"{_PKG}.core.domain.raster_filter_criteria")
RasterSelection, RasterSelectionMode = _criteria.RasterSelection, _criteria.RasterSelectionMode


class FakeRect:
    def __init__(self, x0, y0, x1, y1):
        self.box = (x0, y0, x1, y1)

    def xMinimum(self):
        return self.box[0]

    def yMinimum(self):
        return self.box[1]

    def xMaximum(self):
        return self.box[2]

    def yMaximum(self):
        return self.box[3]

    def width(self):
        return self.box[2] - self.box[0]

    def height(self):
        return self.box[3] - self.box[1]


class FakeCrs:
    def __init__(self, name, valid=True):
        self.name, self.valid = name, valid

    def authid(self):
        return "" if self.name == "custom" else f"EPSG:{self.name}"

    def isValid(self):
        return self.valid

    def __eq__(self, other):
        return isinstance(other, FakeCrs) and other.name == self.name

    def __hash__(self):
        return hash(self.name)


class FakePoint:
    def __init__(self, x, y):
        self._x, self._y = x, y

    def x(self):
        return self._x

    def y(self):
        return self._y


def _surface(crs, cell_size=1.0):
    return types.SimpleNamespace(crs=crs, cell_size=cell_size, extent=FakeRect(0.0, 0.0, 1000.0, 1000.0))


def _shift(dx, dy):
    """QgsCoordinateTransform stand-in moving every point by (dx, dy)."""
    class Transform:
        def __init__(self, *_args):
            pass

        def transform(self, point):
            return FakePoint(point.x() + dx, point.y() + dy)
    return Transform


class TestReferencedBands:
    def test_bands_of_the_layer_only(self):
        expression = '(abs("ortho_RVB@1" - 98) <= 27.96 AND abs("ortho_RVB@3" - 228) <= 27) OR "other@2" > 1'
        assert overlay.referenced_bands(expression, "ortho_RVB") == [1, 3]

    def test_reference_with_regex_characters(self):
        assert overlay.referenced_bands('"a.b@2" > 0 AND "aXb@4" > 0', "a.b") == [2]


class TestFitsCanvas:
    """The real fits_canvas, QGIS classes replaced by fakes."""

    @pytest.fixture(autouse=True)
    def _qgis(self, monkeypatch):
        monkeypatch.setattr(overlay, "QgsPointXY", FakePoint)
        monkeypatch.setattr(overlay, "QgsProject", types.SimpleNamespace(instance=lambda: None))

    def test_same_crs(self, monkeypatch):
        monkeypatch.setattr(overlay, "QgsCoordinateTransform", _shift(1e6, 0))  # never called
        assert overlay.fits_canvas(_surface(FakeCrs("2154")), FakeCrs("2154"))

    def test_custom_crs_drawn_at_the_same_place(self, monkeypatch):
        # Lambert-93 GeoTIFF whose datum GDAL does not name: no authid, same coordinates.
        monkeypatch.setattr(overlay, "QgsCoordinateTransform", _shift(0.0001, -0.0001))
        assert overlay.fits_canvas(_surface(FakeCrs("custom")), FakeCrs("2154"))

    def test_another_projection(self, monkeypatch):
        monkeypatch.setattr(overlay, "QgsCoordinateTransform", _shift(-6e5, 4e6))
        assert not overlay.fits_canvas(_surface(FakeCrs("2154")), FakeCrs("3857"))

    def test_invalid_crs_never_fit(self, monkeypatch):
        monkeypatch.setattr(overlay, "QgsCoordinateTransform", _shift(0, 0))
        assert not overlay.fits_canvas(_surface(FakeCrs("", valid=False)), FakeCrs("", valid=False))
        assert not overlay.fits_canvas(_surface(FakeCrs("2154")), FakeCrs("", valid=False))

    def test_non_finite_corner(self, monkeypatch):
        monkeypatch.setattr(overlay, "QgsCoordinateTransform", _shift(float("inf"), 0))
        assert not overlay.fits_canvas(_surface(FakeCrs("custom")), FakeCrs("2154"))

    def test_transformation_error(self, monkeypatch):
        class Failing:
            def __init__(self, *_args):
                pass

            def transform(self, point):
                raise RuntimeError("QgsCsException")
        monkeypatch.setattr(overlay, "QgsCoordinateTransform", Failing)
        assert not overlay.fits_canvas(_surface(FakeCrs("custom")), FakeCrs("2154"))

    def test_corners_stay_within_half_a_cell(self):
        assert overlay.corners_stay([(0.0, 0.0, 0.4, -0.4)], 0.5)
        assert not overlay.corners_stay([(0.0, 0.0, 0.6, 0.0)], 0.5)
        assert not overlay.corners_stay([(0.0, 0.0, float("nan"), 0.0)], 0.5)


class TestExpressionSurfaceNoData:
    """The virtual raster has no NoData: 255 (NoData of the orthophoto) passes a pool's blue test."""

    def test_nodata_pixels_are_neither_kept_nor_counted(self, monkeypatch):
        np = pytest.importorskip("numpy")
        nan = float("nan")
        bands = {
            1: np.array([[98.0, 98.0], [98.0, 10.0]]),
            3: np.array([[228.0, nan], [228.0, 228.0]]),  # NoData (255 in the file) on the blue band
        }
        virtual = np.array([[1.0, 1.0], [0.0, 0.0]])  # the comparison kept the NoData pixel
        providers = {"virtual": "virtual", "base": "base"}

        def read(provider, band, extent, width, height):
            return virtual.copy() if provider == providers["virtual"] else bands.get(band, np.ones((2, 2))).copy()

        layer = types.SimpleNamespace(extent=lambda: FakeRect(0.0, 0.0, 2.0, 2.0), width=lambda: 2, height=lambda: 2,
                                      source=lambda: "/data/ortho.tif", crs=lambda: FakeCrs("custom"),
                                      dataProvider=lambda: providers["base"], bandCount=lambda: 3)
        monkeypatch.setattr(overlay, "QgsRectangle", lambda extent: extent)
        monkeypatch.setattr(overlay, "QgsCoordinateReferenceSystem", lambda crs: crs)
        monkeypatch.setattr(overlay, "raster_reference", lambda layer: "ortho")
        monkeypatch.setattr(sys.modules[f"{_PKG}.adapters.qgis.coverage_layers.raster_adapter"], "read_band_array", read)
        monkeypatch.setattr(overlay, "selection_virtual_layer", lambda layer, selection: types.SimpleNamespace(
            dataProvider=lambda: providers["virtual"]))
        selection = RasterSelection(mode=RasterSelectionMode.EXPRESSION,
                                    expression='(abs("ortho@1" - 98) <= 28 AND abs("ortho@3" - 228) <= 27)')
        surface = overlay.ExpressionSurface(layer, selection)
        assert surface.mask.tolist() == [[True, False], [False, False]]
        assert surface.kept_ratio == pytest.approx(1 / 3)  # 3 pixels with a value, 1 kept
