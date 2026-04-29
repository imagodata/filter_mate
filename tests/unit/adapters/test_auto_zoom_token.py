"""H1 — auto_zoom subset-change token guards stale post-task zooms.

Audit 2026-04-29 (H1): a filter task scheduled at T=0 may finish at T=15s
and call auto_zoom_to_filtered on the main thread. If the user applied a
favorite at T=10 in the meantime, the favorite's synchronous zoom owns
the canvas now — the filter task's finish() callback would clobber it
with the stale extent computed from the older subset.

bump_subset_change_token() is the seam: each subset apply (filter task
__init__, favorite apply) bumps the global counter and snapshots the
new value. auto_zoom_to_filtered(expected_token=...) refuses to zoom
when the global counter has since advanced past the snapshot.

Loaded via importlib so we don't pull QGIS at module import time.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from unittest.mock import MagicMock

import pytest


_PKG = "filter_mate_h1"
_PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)


def _install_stubs() -> None:
    if _PKG in sys.modules:
        return

    root = types.ModuleType(_PKG)
    root.__path__ = [_PROJECT_ROOT]
    sys.modules[_PKG] = root

    # Parent packages
    for sub in ("adapters", "infrastructure", "infrastructure.logging", "config"):
        full = f"{_PKG}.{sub}"
        if full not in sys.modules:
            mod = types.ModuleType(full)
            mod.__path__ = [os.path.join(_PROJECT_ROOT, *sub.split("."))]
            sys.modules[full] = mod

    # Stub QGIS imports the module performs.
    qgis_mocks = {
        "qgis": MagicMock(),
        "qgis.core": MagicMock(),
        "qgis.utils": MagicMock(),
    }
    for name, m in qgis_mocks.items():
        sys.modules.setdefault(name, m)

    # QgsRectangle stub: combineExtentWith / isEmpty have to behave.
    class _FakeRect:
        def __init__(self, src=None):
            if src is None:
                self._empty = True
            elif isinstance(src, _FakeRect):
                self._empty = src._empty
            else:
                self._empty = False

        def combineExtentWith(self, other):
            self._empty = self._empty and other._empty

        def isEmpty(self):
            return self._empty

    sys.modules["qgis.core"].QgsRectangle = _FakeRect
    sys.modules["qgis.core"].QgsVectorLayer = MagicMock
    sys.modules["qgis.utils"].iface = MagicMock()

    # infrastructure.logging.get_app_logger
    import logging as _logging

    sys.modules[f"{_PKG}.infrastructure.logging"].get_app_logger = lambda: _logging.getLogger(
        "filter_mate_h1_auto_zoom"
    )

    # config.config — only needed for _read_global_auto_zoom_flag
    config_mod = types.ModuleType(f"{_PKG}.config.config")
    config_mod.ENV_VARS = {"CONFIG_DATA": {}}
    config_mod._get_option_value = lambda v, default=None: (
        v if v is not None else default
    )
    sys.modules[f"{_PKG}.config.config"] = config_mod
    sys.modules[f"{_PKG}.config"].config = config_mod

    # Load the real module under the stub package.
    full_name = f"{_PKG}.adapters.auto_zoom"
    path = os.path.join(_PROJECT_ROOT, "adapters", "auto_zoom.py")
    spec = importlib.util.spec_from_file_location(full_name, path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = f"{_PKG}.adapters"
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)


_install_stubs()
auto_zoom_mod = sys.modules[f"{_PKG}.adapters.auto_zoom"]
bump_subset_change_token = auto_zoom_mod.bump_subset_change_token
current_subset_change_token = auto_zoom_mod.current_subset_change_token
auto_zoom_to_filtered = auto_zoom_mod.auto_zoom_to_filtered


@pytest.fixture
def fake_layer():
    layer = MagicMock()
    layer.id.return_value = "L1"
    rect = auto_zoom_mod.QgsRectangle(object())  # non-empty
    layer.extent.return_value = rect
    layer.updateExtents = MagicMock()
    return layer


@pytest.fixture
def fake_iface_with_canvas():
    canvas = MagicMock()
    canvas.zoomToFeatureExtent = MagicMock()
    canvas.refresh = MagicMock()
    iface = MagicMock()
    iface.mapCanvas.return_value = canvas
    return iface, canvas


class TestBumpToken:
    def test_bump_returns_monotonically_increasing_value(self):
        a = bump_subset_change_token()
        b = bump_subset_change_token()
        c = bump_subset_change_token()
        assert b == a + 1
        assert c == b + 1

    def test_current_returns_last_bumped_without_advancing(self):
        bump_subset_change_token()
        before = current_subset_change_token()
        after = current_subset_change_token()
        assert before == after


class TestExpectedTokenGuard:
    def test_no_token_means_no_check(self, fake_layer, fake_iface_with_canvas):
        # Bump some tokens to make sure the global counter moves.
        bump_subset_change_token()
        bump_subset_change_token()

        iface, canvas = fake_iface_with_canvas
        result = auto_zoom_to_filtered([fake_layer], iface_obj=iface)

        # Without expected_token, the call always proceeds.
        assert result is True
        canvas.zoomToFeatureExtent.assert_called_once()

    def test_matching_token_zooms(self, fake_layer, fake_iface_with_canvas):
        my_token = bump_subset_change_token()
        iface, canvas = fake_iface_with_canvas

        result = auto_zoom_to_filtered(
            [fake_layer], iface_obj=iface, expected_token=my_token
        )

        assert result is True
        canvas.zoomToFeatureExtent.assert_called_once()

    def test_advanced_token_skips_zoom(self, fake_layer, fake_iface_with_canvas):
        # Filter task captures token at T=0
        filter_token = bump_subset_change_token()
        # Favorite applied at T=10 bumps further
        bump_subset_change_token()
        # Filter finished at T=15 — token now stale
        iface, canvas = fake_iface_with_canvas

        result = auto_zoom_to_filtered(
            [fake_layer], iface_obj=iface, expected_token=filter_token
        )

        assert result is False
        # Neither zoom nor refresh should fire — the canvas already shows
        # the favorite's extent.
        canvas.zoomToFeatureExtent.assert_not_called()
        canvas.refresh.assert_not_called()

    def test_zero_expected_token_with_no_bumps_passes(
        self, fake_layer, fake_iface_with_canvas
    ):
        # Edge case: caller uses expected_token=0 (sentinel-ish), no bumps.
        # Token should not have advanced past 0 unless bumps happened.
        # We can't reset the global token cleanly across tests, so just
        # verify the relative behaviour: snapshot then check.
        snap = current_subset_change_token()
        iface, canvas = fake_iface_with_canvas

        result = auto_zoom_to_filtered(
            [fake_layer], iface_obj=iface, expected_token=snap
        )

        # No bumps between snap and call → token still <= snap → zoom proceeds.
        assert result is True


class TestNoLayersRefreshOnly:
    def test_empty_layers_with_advanced_token_does_not_refresh(
        self, fake_iface_with_canvas
    ):
        # Token check happens BEFORE the empty-layers refresh path. A
        # superseded zoom must not even refresh — it would be a no-op
        # but it costs a canvas redraw.
        snap = bump_subset_change_token()
        bump_subset_change_token()  # someone else moved on
        iface, canvas = fake_iface_with_canvas

        result = auto_zoom_to_filtered([], iface_obj=iface, expected_token=snap)

        assert result is False
        canvas.refresh.assert_not_called()

    def test_empty_layers_with_matching_token_refreshes(
        self, fake_iface_with_canvas
    ):
        snap = bump_subset_change_token()
        iface, canvas = fake_iface_with_canvas

        result = auto_zoom_to_filtered([], iface_obj=iface, expected_token=snap)

        # Empty-layers path returns False but does refresh.
        assert result is False
        canvas.refresh.assert_called_once()
