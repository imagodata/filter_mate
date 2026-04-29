"""T2 — coverage for auto_zoom helpers beyond the H1 token guard.

H1 covered :func:`bump_subset_change_token` and the ``expected_token``
short-circuit in :func:`auto_zoom_to_filtered`. T2 closes the rest of
the surface:

- :func:`_read_global_auto_zoom_flag` — config lookup with fallbacks.
- :func:`_is_tracking` — per-layer override resolution.
- :func:`_layer_extent` — dockwidget custom extent vs raw layer extent.
- :func:`auto_zoom_to_filtered` end-to-end paths: iface/canvas missing,
  empty layers refresh, global-off tracking-on subset, union extent
  computation, isEmpty union refresh.

The module is loaded via importlib (same harness as test_auto_zoom_token)
so QGIS imports stay fake.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from unittest.mock import MagicMock

import pytest


_PKG = "filter_mate_t2"
_PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)


def _install_stubs() -> None:
    if _PKG in sys.modules:
        return

    root = types.ModuleType(_PKG)
    root.__path__ = [_PROJECT_ROOT]
    sys.modules[_PKG] = root

    for sub in ("adapters", "infrastructure", "infrastructure.logging", "config"):
        full = f"{_PKG}.{sub}"
        if full not in sys.modules:
            mod = types.ModuleType(full)
            mod.__path__ = [os.path.join(_PROJECT_ROOT, *sub.split("."))]
            sys.modules[full] = mod

    qgis_mocks = {
        "qgis": MagicMock(),
        "qgis.core": MagicMock(),
        "qgis.utils": MagicMock(),
    }
    for name, m in qgis_mocks.items():
        sys.modules.setdefault(name, m)

    class _FakeRect:
        def __init__(self, src=None):
            if src is None:
                self._empty = True
                self._tag = "default"
            elif isinstance(src, _FakeRect):
                self._empty = src._empty
                self._tag = src._tag
            else:
                # Caller passes a sentinel object — non-empty by default.
                self._empty = False
                self._tag = repr(src)

        def combineExtentWith(self, other):
            self._empty = self._empty and other._empty

        def isEmpty(self):
            return self._empty

    sys.modules["qgis.core"].QgsRectangle = _FakeRect
    sys.modules["qgis.core"].QgsVectorLayer = MagicMock
    sys.modules["qgis.utils"].iface = MagicMock()

    import logging as _logging

    sys.modules[f"{_PKG}.infrastructure.logging"].get_app_logger = (
        lambda: _logging.getLogger("filter_mate_t2_auto_zoom")
    )

    config_mod = types.ModuleType(f"{_PKG}.config.config")
    config_mod.ENV_VARS = {"CONFIG_DATA": {}}
    config_mod._get_option_value = lambda v, default=None: (
        v if v is not None else default
    )
    sys.modules[f"{_PKG}.config.config"] = config_mod
    sys.modules[f"{_PKG}.config"].config = config_mod

    full_name = f"{_PKG}.adapters.auto_zoom"
    path = os.path.join(_PROJECT_ROOT, "adapters", "auto_zoom.py")
    spec = importlib.util.spec_from_file_location(full_name, path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = f"{_PKG}.adapters"
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)


_install_stubs()
auto_zoom_mod = sys.modules[f"{_PKG}.adapters.auto_zoom"]
config_mod = sys.modules[f"{_PKG}.config.config"]


def _make_layer(layer_id="L1", with_extent=True, raises_extents=False):
    layer = MagicMock()
    layer.id.return_value = layer_id
    if raises_extents:
        layer.updateExtents.side_effect = RuntimeError("destroyed")
    else:
        layer.updateExtents = MagicMock()
    if with_extent:
        rect = auto_zoom_mod.QgsRectangle(object())  # non-empty
        layer.extent.return_value = rect
    else:
        empty = auto_zoom_mod.QgsRectangle()
        empty._empty = True
        layer.extent.return_value = empty
    return layer


@pytest.fixture
def fake_iface():
    canvas = MagicMock()
    canvas.zoomToFeatureExtent = MagicMock()
    canvas.refresh = MagicMock()
    iface = MagicMock()
    iface.mapCanvas.return_value = canvas
    return iface, canvas


@pytest.fixture(autouse=True)
def reset_config():
    """Reset the config dict to default-empty between tests."""
    config_mod.ENV_VARS = {"CONFIG_DATA": {}}
    yield
    config_mod.ENV_VARS = {"CONFIG_DATA": {}}


# ---------------------------------------------------------------------------
# _read_global_auto_zoom_flag
# ---------------------------------------------------------------------------


class TestReadGlobalAutoZoomFlag:
    def test_default_true_when_config_empty(self):
        assert auto_zoom_mod._read_global_auto_zoom_flag() is True

    def test_returns_configured_true(self):
        config_mod.ENV_VARS = {
            "CONFIG_DATA": {
                "APP": {"OPTIONS": {"EXPLORATION": {"auto_zoom_on_filter": True}}}
            }
        }
        assert auto_zoom_mod._read_global_auto_zoom_flag() is True

    def test_returns_configured_false(self):
        config_mod.ENV_VARS = {
            "CONFIG_DATA": {
                "APP": {"OPTIONS": {"EXPLORATION": {"auto_zoom_on_filter": False}}}
            }
        }
        assert auto_zoom_mod._read_global_auto_zoom_flag() is False

    def test_missing_section_falls_back_true(self):
        # Partial path: APP exists but OPTIONS does not.
        config_mod.ENV_VARS = {"CONFIG_DATA": {"APP": {}}}
        assert auto_zoom_mod._read_global_auto_zoom_flag() is True

    def test_typeerror_during_lookup_falls_back_true(self):
        # Mutate ENV_VARS to a non-dict so .get() raises AttributeError.
        config_mod.ENV_VARS = "not-a-dict"
        assert auto_zoom_mod._read_global_auto_zoom_flag() is True


# ---------------------------------------------------------------------------
# _is_tracking
# ---------------------------------------------------------------------------


class TestIsTracking:
    def test_empty_layer_id_returns_false(self):
        assert auto_zoom_mod._is_tracking("", {"L1": {}}) is False

    def test_empty_project_layers_returns_false(self):
        assert auto_zoom_mod._is_tracking("L1", {}) is False

    def test_missing_key_returns_false(self):
        assert auto_zoom_mod._is_tracking("L1", {"L2": {}}) is False

    def test_non_mapping_props_returns_false(self):
        assert auto_zoom_mod._is_tracking("L1", {"L1": "not-a-mapping"}) is False

    def test_missing_exploring_section_returns_false(self):
        assert auto_zoom_mod._is_tracking("L1", {"L1": {"other": {}}}) is False

    def test_non_mapping_exploring_returns_false(self):
        assert (
            auto_zoom_mod._is_tracking("L1", {"L1": {"exploring": "string"}}) is False
        )

    def test_tracking_true_returns_true(self):
        project_layers = {"L1": {"exploring": {"is_tracking": True}}}
        assert auto_zoom_mod._is_tracking("L1", project_layers) is True

    def test_tracking_false_returns_false(self):
        project_layers = {"L1": {"exploring": {"is_tracking": False}}}
        assert auto_zoom_mod._is_tracking("L1", project_layers) is False

    def test_tracking_missing_returns_false(self):
        project_layers = {"L1": {"exploring": {}}}
        assert auto_zoom_mod._is_tracking("L1", project_layers) is False


# ---------------------------------------------------------------------------
# _layer_extent
# ---------------------------------------------------------------------------


class TestLayerExtent:
    def test_returns_layer_extent_when_no_dockwidget(self):
        layer = _make_layer()
        ext = auto_zoom_mod._layer_extent(layer, dockwidget=None)
        assert ext is not None
        assert ext.isEmpty() is False
        layer.updateExtents.assert_called_once()

    def test_returns_none_when_update_extents_raises(self):
        layer = _make_layer(raises_extents=True)
        ext = auto_zoom_mod._layer_extent(layer)
        assert ext is None

    def test_returns_none_when_layer_extent_is_empty(self):
        layer = _make_layer(with_extent=False)
        ext = auto_zoom_mod._layer_extent(layer)
        assert ext is None

    def test_dockwidget_custom_extent_wins_over_layer_extent(self):
        layer = _make_layer()
        dw = MagicMock()
        custom = auto_zoom_mod.QgsRectangle(object())
        dw.get_filtered_layer_extent.return_value = custom

        ext = auto_zoom_mod._layer_extent(layer, dockwidget=dw)

        assert ext is custom
        dw.get_filtered_layer_extent.assert_called_once_with(layer)
        # Layer fallback NOT consulted when dockwidget gave a usable extent.
        layer.extent.assert_not_called()

    def test_dockwidget_returning_none_falls_back_to_layer(self):
        layer = _make_layer()
        dw = MagicMock()
        dw.get_filtered_layer_extent.return_value = None

        ext = auto_zoom_mod._layer_extent(layer, dockwidget=dw)

        assert ext is not None  # falls back to layer.extent()
        layer.extent.assert_called_once()

    def test_dockwidget_returning_empty_falls_back_to_layer(self):
        layer = _make_layer()
        dw = MagicMock()
        empty = auto_zoom_mod.QgsRectangle()
        empty._empty = True
        dw.get_filtered_layer_extent.return_value = empty

        ext = auto_zoom_mod._layer_extent(layer, dockwidget=dw)

        assert ext is not None
        assert ext.isEmpty() is False  # the layer.extent() fallback

    def test_dockwidget_method_raising_falls_back_to_layer(self):
        layer = _make_layer()
        dw = MagicMock()
        dw.get_filtered_layer_extent.side_effect = RuntimeError("bad")

        ext = auto_zoom_mod._layer_extent(layer, dockwidget=dw)

        assert ext is not None  # the layer.extent() fallback

    def test_dockwidget_without_method_uses_layer_extent(self):
        # hasattr(dw, 'get_filtered_layer_extent') is False — skip the
        # custom-extent branch entirely.
        layer = _make_layer()
        dw = object()  # no method at all

        ext = auto_zoom_mod._layer_extent(layer, dockwidget=dw)

        assert ext is not None


# ---------------------------------------------------------------------------
# auto_zoom_to_filtered — end-to-end paths beyond the token guard
# ---------------------------------------------------------------------------


class TestAutoZoomEndToEnd:
    def test_no_iface_returns_false(self):
        # iface_obj=None and the default iface is also None — return False.
        layer = _make_layer()
        # Force the module-level default to None for this test.
        original = auto_zoom_mod.default_iface
        auto_zoom_mod.default_iface = None
        try:
            result = auto_zoom_mod.auto_zoom_to_filtered([layer])
        finally:
            auto_zoom_mod.default_iface = original
        assert result is False

    def test_iface_without_mapcanvas_returns_false(self):
        iface = object()  # has no mapCanvas attribute
        layer = _make_layer()
        result = auto_zoom_mod.auto_zoom_to_filtered([layer], iface_obj=iface)
        assert result is False

    def test_canvas_none_returns_false(self):
        iface = MagicMock()
        iface.mapCanvas.return_value = None
        layer = _make_layer()
        result = auto_zoom_mod.auto_zoom_to_filtered([layer], iface_obj=iface)
        assert result is False

    def test_global_off_no_tracking_skips_zoom(self, fake_iface):
        config_mod.ENV_VARS = {
            "CONFIG_DATA": {
                "APP": {"OPTIONS": {"EXPLORATION": {"auto_zoom_on_filter": False}}}
            }
        }
        iface, canvas = fake_iface
        layer = _make_layer("L1")
        result = auto_zoom_mod.auto_zoom_to_filtered(
            [layer], project_layers={}, iface_obj=iface
        )
        # No extent collected → refresh-only path.
        assert result is False
        canvas.refresh.assert_called_once()
        canvas.zoomToFeatureExtent.assert_not_called()

    def test_global_off_per_layer_tracking_zooms_only_tracked(self, fake_iface):
        config_mod.ENV_VARS = {
            "CONFIG_DATA": {
                "APP": {"OPTIONS": {"EXPLORATION": {"auto_zoom_on_filter": False}}}
            }
        }
        iface, canvas = fake_iface
        tracked = _make_layer("L_tracked")
        ignored = _make_layer("L_ignored")
        project_layers = {
            "L_tracked": {"exploring": {"is_tracking": True}},
            "L_ignored": {"exploring": {"is_tracking": False}},
        }
        result = auto_zoom_mod.auto_zoom_to_filtered(
            [tracked, ignored], project_layers, iface_obj=iface
        )
        assert result is True
        canvas.zoomToFeatureExtent.assert_called_once()
        # Tracked layer's extent was consulted; ignored never touched.
        tracked.extent.assert_called_once()
        ignored.extent.assert_not_called()

    def test_filters_out_none_layers(self, fake_iface):
        iface, canvas = fake_iface
        good = _make_layer("good")
        result = auto_zoom_mod.auto_zoom_to_filtered(
            [None, good, None], iface_obj=iface
        )
        assert result is True
        good.extent.assert_called_once()

    def test_only_none_layers_refreshes_only(self, fake_iface):
        iface, canvas = fake_iface
        result = auto_zoom_mod.auto_zoom_to_filtered(
            [None, None], iface_obj=iface
        )
        assert result is False
        canvas.refresh.assert_called_once()

    def test_layer_id_raises_skips_layer(self, fake_iface):
        iface, canvas = fake_iface
        broken = MagicMock()
        broken.id.side_effect = RuntimeError("destroyed")
        good = _make_layer("good")
        result = auto_zoom_mod.auto_zoom_to_filtered(
            [broken, good], iface_obj=iface
        )
        assert result is True
        # The good layer was zoomed; the broken one was silently skipped.
        good.extent.assert_called_once()

    def test_union_extent_combines_multiple_layers(self, fake_iface):
        iface, canvas = fake_iface
        a = _make_layer("A")
        b = _make_layer("B")
        c = _make_layer("C")
        result = auto_zoom_mod.auto_zoom_to_filtered([a, b, c], iface_obj=iface)
        assert result is True
        canvas.zoomToFeatureExtent.assert_called_once()
        # All three layers had their extent fetched.
        a.extent.assert_called_once()
        b.extent.assert_called_once()
        c.extent.assert_called_once()

    def test_empty_union_falls_back_to_refresh(self, fake_iface):
        # All layers report empty extents → union stays empty → refresh.
        iface, canvas = fake_iface
        a = _make_layer("A", with_extent=False)
        b = _make_layer("B", with_extent=False)
        result = auto_zoom_mod.auto_zoom_to_filtered([a, b], iface_obj=iface)
        # No extents collected at all (all None) → refresh path.
        assert result is False
        canvas.refresh.assert_called_once()
        canvas.zoomToFeatureExtent.assert_not_called()

    def test_project_layers_none_falls_back_to_empty(self, fake_iface):
        # project_layers=None must not raise; it normalises to {} so the
        # tracking lookup returns False without errors.
        config_mod.ENV_VARS = {
            "CONFIG_DATA": {
                "APP": {"OPTIONS": {"EXPLORATION": {"auto_zoom_on_filter": False}}}
            }
        }
        iface, canvas = fake_iface
        layer = _make_layer("L1")
        result = auto_zoom_mod.auto_zoom_to_filtered(
            [layer], project_layers=None, iface_obj=iface
        )
        assert result is False
        canvas.refresh.assert_called_once()
