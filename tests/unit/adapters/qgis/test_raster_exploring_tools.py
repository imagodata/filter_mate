# -*- coding: utf-8 -*-
"""FilterMate 5 raster EXPLORING tools: range extent bounds and style link rescaling (pure parts)."""
import importlib
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_raster_tools_test"


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.domain", _ROOT / "core" / "domain"),
                       (".adapters", _ROOT / "adapters"), (".adapters.qgis", _ROOT / "adapters" / "qgis"),
                       (".adapters.qgis.coverage_layers", _ROOT / "adapters" / "qgis" / "coverage_layers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.adapters.qgis.coverage_layers.raster_adapter")


adapter = _load()


class TestRescale:
    def test_stops_follow_the_new_range(self):
        assert adapter.rescale_values([0.0, 50.0, 100.0], 0.0, 100.0, 200.0, 260.0) == [200.0, 230.0, 260.0]

    def test_flat_ramp_is_spread(self):
        assert adapter.rescale_values([5.0, 5.0, 5.0], 5.0, 5.0, 0.0, 10.0) == [0.0, 5.0, 10.0]


class TestMaskBounds:
    def test_bounds_of_true_cells(self):
        np = pytest.importorskip("numpy")
        mask = np.zeros((5, 6), dtype=bool)
        mask[1, 2] = mask[3, 4] = True
        assert adapter.mask_bounds(mask) == (1, 3, 2, 4)

    def test_empty_mask(self):
        np = pytest.importorskip("numpy")
        assert adapter.mask_bounds(np.zeros((3, 3), dtype=bool)) is None


class TestNumericExpressions:
    @pytest.mark.parametrize("width,height,budget", [(1, 10**9, 1000), (10**9, 1, 10), (1, 10**9, 1), (500, 500, 400)])
    def test_sampling_grid_stays_within_budget_for_narrow_rasters(self, width, height, budget):
        cols, rows = adapter._grid_for(None, width, height, budget)
        assert cols >= 1 and rows >= 1 and cols * rows <= budget
        assert cols <= width and rows <= height

    def test_constant_band_has_a_histogram_instead_of_being_reported_missing(self, monkeypatch):
        np = pytest.importorskip("numpy")
        layer = types.SimpleNamespace(extent=lambda: None, width=lambda: 3, height=lambda: 1, dataProvider=lambda: None)
        monkeypatch.setattr(adapter, "band_range", lambda *a: (7.0, 7.0, 7.0))
        monkeypatch.setattr(adapter, "read_band_array", lambda *a: np.array([[7.0, np.nan, 7.0]]))
        counts, low, high = adapter.band_histogram(layer, 1, bins=4)
        assert counts == [2, 0, 0, 0] and (low, high) == (7.0, 7.0)

    def test_histogram_keeps_zero_and_negative_values(self, monkeypatch):
        np = pytest.importorskip("numpy")
        monkeypatch.setattr(adapter, "expression_array", lambda *a: np.array([[-1, 0, 1, np.nan, np.inf]]))
        counts, low, high = adapter.expression_histogram(None, '"img@1" / 100', bins=2)
        assert sum(counts) == 3 and (low, high) == (-1.0, 1.0)

    def test_constant_and_invalid_formula_histograms(self, monkeypatch):
        np = pytest.importorskip("numpy")
        monkeypatch.setattr(adapter, "expression_array", lambda *a: np.array([[0, 0]]))
        counts, low, high = adapter.expression_histogram(None, "0", bins=4)
        assert sum(counts) == 2 and low == high == 0
        monkeypatch.setattr(adapter, "expression_array", lambda *a: None)
        assert adapter.expression_histogram(None, "broken(") == ([], 0.0, 0.0)

    def test_numeric_array_excludes_nodata_of_referenced_bands(self, monkeypatch):
        np = pytest.importorskip("numpy")
        source, calculated = object(), object()
        layer = types.SimpleNamespace(dataProvider=lambda: source, extent=lambda: object(),
                                      width=lambda: 3, height=lambda: 1, bandCount=lambda: 2)
        virtual = types.SimpleNamespace(dataProvider=lambda: calculated)
        monkeypatch.setattr(adapter, "selection_virtual_layer", lambda *a: virtual)
        monkeypatch.setattr(adapter, "raster_reference", lambda layer: "img")
        monkeypatch.setattr(adapter, "_grid_for", lambda *a: (3, 1))
        monkeypatch.setattr(adapter, "read_band_array", lambda provider, *a:
                            np.array([[0.0, 1, -1]]) if provider is calculated else np.array([[10, np.nan, 20]]))
        array = adapter.expression_array(layer, '"img@2" / 10')
        assert array[0, 0] == 0 and np.isnan(array[0, 1]) and array[0, 2] == -1

    def test_identify_normalizes_nonfinite_values(self):
        result = types.SimpleNamespace(isValid=lambda: True, results=lambda: {1: float("nan"), 2: float("inf"), 3: 0})
        layer = types.SimpleNamespace(dataProvider=lambda: types.SimpleNamespace(identify=lambda *a: result))
        assert adapter.identify_values(layer, None) == {1: None, 2: None, 3: 0.0}


# ---------------------------------------------------------------------------
# Live preview: transparent value ranges, matched the way QGIS matches them
# ---------------------------------------------------------------------------

RasterSelection = adapter.RasterSelection
RasterSelectionMode = adapter.RasterSelectionMode
_EPSILON = 4 * sys.float_info.epsilon  # qgsDoubleNear default tolerance (absolute)


def _near(a, b):
    return abs(a - b) <= _EPSILON


class PixelSince330:
    """QgsRasterTransparency.TransparentSingleValuePixel of QGIS >= 3.30 (opacity, bound flags)."""

    def __init__(self, minimum=0.0, maximum=0.0, opacity=0.0, includeMinimum=True, includeMaximum=True):  # noqa: N803
        self.min, self.max, self.opacity = minimum, maximum, opacity
        self.includeMinimum, self.includeMaximum = includeMinimum, includeMaximum

    @staticmethod
    def hides(pixels, value):  # QgsRasterTransparency::opacityForValue
        for p in pixels:
            if (p.min < value < p.max) or (p.includeMinimum and _near(value, p.min)) or \
                    (p.includeMaximum and _near(value, p.max)):
                return p.opacity <= 0.0
        return False


class PixelBefore330:
    """The 3-field struct of QGIS 3.22 - 3.28: ranges inclusive on both sides, percent transparent."""

    __slots__ = ("min", "max", "percentTransparent")

    def __init__(self):
        self.min = self.max = self.percentTransparent = 0.0

    @staticmethod
    def hides(pixels, value):  # QgsRasterTransparency::alphaValue
        for p in pixels:
            if (p.min <= value <= p.max) or _near(value, p.min) or _near(value, p.max):
                return p.percentTransparent >= 100.0
        return False


def _transparency_class(pixel_class):
    class Transparency:
        TransparentSingleValuePixel = pixel_class

        def __init__(self):
            self.pixels = []

        def setTransparentSingleValuePixelList(self, pixels):  # noqa: N802
            self.pixels = list(pixels)

        def transparentSingleValuePixelList(self):  # noqa: N802
            return list(self.pixels)

    return Transparency


class FakeRenderer:
    def __init__(self, transparency, kind="singlebandgray"):
        self.transparency, self.kind = transparency, kind

    def rasterTransparency(self):  # noqa: N802
        return self.transparency

    def setRasterTransparency(self, transparency):  # noqa: N802
        self.transparency = transparency

    def type(self):
        return self.kind

    def clone(self):
        return FakeRenderer(self.transparency, self.kind)


class FakeRasterLayer:
    def __init__(self, transparency, layer_id="mnt"):
        self._id = layer_id
        self.properties = {}
        self._renderer = FakeRenderer(transparency)

    def id(self):
        return self._id

    def renderer(self):
        return self._renderer

    def setRenderer(self, renderer):  # noqa: N802
        self._renderer = renderer

    def customProperty(self, key):  # noqa: N802
        return self.properties.get(key)

    def setCustomProperty(self, key, value):  # noqa: N802
        self.properties[key] = value

    def removeCustomProperty(self, key):  # noqa: N802
        self.properties.pop(key, None)

    def triggerRepaint(self):  # noqa: N802
        pass


@pytest.fixture(params=[PixelSince330, PixelBefore330], ids=["qgis>=3.30", "qgis<3.30"])
def preview_layer(request, monkeypatch):
    transparency_class = _transparency_class(request.param)
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsRasterTransparency", transparency_class, raising=False)
    layer = FakeRasterLayer(transparency_class())

    def hidden(values):
        pixels = layer.renderer().rasterTransparency().transparentSingleValuePixelList()
        return [value for value in values if request.param.hides(pixels, value)]

    layer.hidden = hidden
    return layer


class TestSelectionPreview:
    """Constats 3 / 7: the preview hides exactly the pixels the filter drops, on both QGIS APIs."""

    def test_classes_keep_every_selected_class(self, preview_layer):
        selection = RasterSelection(mode=RasterSelectionMode.CLASSES, classes=frozenset({2, 5, 6}))
        assert adapter.apply_selection_preview(preview_layer, selection, 0.0, 10.0)
        assert preview_layer.hidden([float(v) for v in range(11)]) == [0.0, 1.0, 3.0, 4.0, 7.0, 8.0, 9.0, 10.0]

    def test_classes_round_like_the_filter(self, preview_layer):
        selection = RasterSelection(mode=RasterSelectionMode.CLASSES, classes=frozenset({2}))
        adapter.apply_selection_preview(preview_layer, selection, 0.0, 10.0)
        assert preview_layer.hidden([1.4, 1.6, 2.4, 2.6]) == [1.4, 2.6]

    def test_range_keeps_its_bounds(self, preview_layer):
        selection = RasterSelection(minimum=3.0, maximum=7.0)
        adapter.apply_selection_preview(preview_layer, selection, 0.0, 10.0)
        values = [0.0, 2.9999, 3.0, 5.0, 7.0, 7.0001, 10.0]
        assert preview_layer.hidden(values) == [0.0, 2.9999, 7.0001, 10.0]

    def test_float32_values_next_to_the_bounds(self, preview_layer):
        np = pytest.importorskip("numpy")
        below = float(np.nextafter(np.float32(1240.0), np.float32(0)))
        above = float(np.nextafter(np.float32(1270.0), np.float32(2000)))
        adapter.apply_selection_preview(preview_layer, RasterSelection(minimum=1240.0, maximum=1270.0), 1189.0, 1359.0)
        assert preview_layer.hidden([below, 1240.0, 1270.0, above]) == [below, above]

    def test_open_range_and_zero_bound(self, preview_layer):
        adapter.apply_selection_preview(preview_layer, RasterSelection(minimum=0.0), None, None)
        assert preview_layer.hidden([-1.0, -1e-6, 0.0, 1e6]) == [-1.0, -1e-6]

    def test_expression_or_empty_selection_shows_every_pixel_again(self, preview_layer):
        adapter.apply_selection_preview(preview_layer, RasterSelection(minimum=3.0), 0.0, 10.0)
        assert preview_layer.hidden([1.0])
        expression = RasterSelection(mode=RasterSelectionMode.EXPRESSION, expression='"mnt@1" > 3')
        assert adapter.apply_selection_preview(preview_layer, expression, 0.0, 10.0) is False
        assert preview_layer.hidden([1.0]) == [] and preview_layer.properties == {}
        adapter.apply_selection_preview(preview_layer, RasterSelection(minimum=3.0), 0.0, 10.0)
        assert adapter.apply_selection_preview(preview_layer, RasterSelection(), 0.0, 10.0) is False
        assert preview_layer.hidden([1.0]) == []

    def test_previous_transparency_is_restored(self, preview_layer):
        transparency = preview_layer.renderer().rasterTransparency()
        own = adapter._transparent_pixel(-9999.0, -9999.0, True, True)  # the user's NoData-like range
        transparency.setTransparentSingleValuePixelList([own])
        adapter.apply_selection_preview(preview_layer, RasterSelection(minimum=3.0), 0.0, 10.0)
        adapter.clear_selection_preview(preview_layer)
        assert preview_layer.hidden([-9999.0, 1.0]) == [-9999.0]

    def test_pixels_beyond_the_sampled_statistics_are_hidden(self, preview_layer):
        # Statistics read on a sample (0 -> 10) of a raster holding -50 and 500.
        adapter.apply_selection_preview(preview_layer, RasterSelection(minimum=3.0, maximum=7.0), 0.0, 10.0)
        assert preview_layer.hidden([-50.0, 5.0, 500.0, 1e30]) == [-50.0, 500.0, 1e30]
        adapter.apply_selection_preview(preview_layer, RasterSelection(mode=RasterSelectionMode.CLASSES,
                                                                       classes=frozenset({2})), 0.0, 0.0)
        assert preview_layer.hidden([-3.0, 2.0, 40.0]) == [-3.0, 40.0]

    @pytest.mark.parametrize("value", [0.001, 1e-5])
    def test_small_float32_bounds(self, preview_layer, value):
        np = pytest.importorskip("numpy")
        bound = np.float32(value)
        below, above = (float(np.nextafter(bound, np.float32(direction))) for direction in (-1, 1))
        adapter.apply_selection_preview(preview_layer, RasterSelection(minimum=float(bound)))
        assert preview_layer.hidden([below, float(bound), above]) == [below]
        adapter.apply_selection_preview(preview_layer, RasterSelection(maximum=float(bound)))
        assert preview_layer.hidden([below, float(bound), above]) == [above]

    def test_user_transparency_still_applies_to_the_kept_pixels(self, preview_layer):
        own = adapter._transparent_pixel(-9999.0, -9999.0, True, True)  # a NoData-like value of the user
        half = adapter._transparent_pixel(0.0, 100.0, True, True)  # half transparent range of the user
        if hasattr(half, "opacity"):
            half.opacity = 0.5
        else:
            half.percentTransparent = 50.0
        preview_layer.renderer().rasterTransparency().setTransparentSingleValuePixelList([own, half])
        adapter.apply_selection_preview(preview_layer, RasterSelection(minimum=-10000.0, maximum=60.0))
        # -9999 is selected but stays transparent; 80 is not selected: hidden, not half transparent.
        assert preview_layer.hidden([-9999.0, 20.0, 80.0]) == [-9999.0, 80.0]


class TestLinkedStyles:
    """Constat 4: saved styles never outlive their layer, and come back when the plugin unloads."""

    def test_forget_removed_layers_or_all(self, monkeypatch):
        monkeypatch.setattr(adapter, "_LINKED_RENDERERS", {"a": object(), "b": object()})
        adapter.forget_linked_styles(["a", "unknown"])
        assert list(adapter._LINKED_RENDERERS) == ["b"]
        adapter.forget_linked_styles()
        assert adapter._LINKED_RENDERERS == {}

    def test_unload_gives_every_layer_its_style_back(self, monkeypatch):
        monkeypatch.setattr(sys.modules["qgis.core"], "QgsRasterTransparency",
                            _transparency_class(PixelSince330), raising=False)
        layer = FakeRasterLayer(_transparency_class(PixelSince330)())
        saved = FakeRenderer(layer.renderer().rasterTransparency(), kind="singlebandpseudocolor")
        monkeypatch.setattr(adapter, "_LINKED_RENDERERS", {"mnt": saved, "gone": object()})
        project = types.SimpleNamespace(mapLayer={"mnt": layer}.get)
        assert adapter.unlink_all_styles(project) == 1
        assert layer.renderer().type() == "singlebandpseudocolor" and adapter._LINKED_RENDERERS == {}


# ---------------------------------------------------------------------------
# Virtual raster URI of a source whose CRS has no authority id
# ---------------------------------------------------------------------------

class _Crs:
    def __init__(self, authid, wkt='PROJCS["EPSG:2154",GEOGCS["unknown"]]', valid=True):
        self._authid, self._wkt, self._valid = authid, wkt, valid

    def authid(self):
        return self._authid

    def toWkt(self):
        return self._wkt

    def isValid(self):
        return self._valid


class _Params:
    def __init__(self, crs):
        self.crs = crs


class TestVirtualUriCrs:
    _TAIL = "extent%3D0%2C0%2C1%2C1%26formula%3D1"

    def _encode(self, monkeypatch, crs, encoded):
        provider = types.SimpleNamespace(encodeVirtualRasterProviderUri=lambda params: encoded)
        monkeypatch.setattr(adapter, "QgsRasterDataProvider", provider)
        return adapter._encode_virtual_uri(_Params(crs))

    def test_custom_crs_is_written_as_wkt(self, monkeypatch):
        uri = self._encode(monkeypatch, _Crs(""), "%3Fcrs%26" + self._TAIL)
        assert uri == ("%3Fcrs%3DPROJCS%5B%22EPSG%3A2154%22%2CGEOGCS%5B%22unknown%22%5D%5D%26" + self._TAIL)

    def test_authority_id_is_left_as_encoded(self, monkeypatch):
        encoded = "%3Fcrs%3DEPSG%3A2154%26" + self._TAIL
        assert self._encode(monkeypatch, _Crs("EPSG:2154"), encoded) == encoded

    def test_invalid_crs_is_left_as_encoded(self, monkeypatch):
        encoded = "%3Fcrs%26" + self._TAIL
        assert self._encode(monkeypatch, _Crs("", valid=False), encoded) == encoded


class TestBandStatistics:
    def test_statistics_are_requested_on_the_extent_and_sample(self):
        calls = []
        provider = types.SimpleNamespace(bandStatistics=lambda *args: calls.append(args) or "stats")
        assert adapter.band_statistics(provider, 2, "extent", 1000) == "stats"
        assert calls == [(2, adapter._all_stats(), "extent", 1000)]
