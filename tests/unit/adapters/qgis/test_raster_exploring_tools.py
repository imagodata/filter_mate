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


