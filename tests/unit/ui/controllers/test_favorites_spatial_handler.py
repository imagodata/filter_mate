"""T1 — FavoritesSpatialHandler.restore_spatial_config regression coverage.

Audit 2026-04-29 (T1): the F4 step-3 stages 1-5 extracted ~900 LOC from the
dockwidget into ``FavoritesSpatialHandler`` without writing any tests for
the new class. ``restore_spatial_config`` is the single most risky method:
it pushes feature IDs back into a ``QgsVectorLayer`` selection, and the
2026-04-21 cross-layer FID guard is what stops a foreign favorite from
corrupting the active layer's selection.

These tests pin the cross-layer guard, the happy path, the buffer/predicate
restoration, and the edge cases (no spatial_config, no current_layer,
exception swallowing).

The handler module has zero direct QGIS imports at the top level — the
helpers and the Protocol it depends on are pure-typing — so we can load
it via :mod:`importlib` without the heavy QGIS stub setup other UI tests
need. ``favorite_matches_current_layer`` is exercised for real (not
patched) so the matching contract is also tested end-to-end.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest


_PKG = "filter_mate_t1_handler"
_PROJECT_ROOT = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", ".."
))


def _install_stubs() -> None:
    """Register a synthetic package + the bare imports the handler needs."""
    if _PKG in sys.modules:
        return

    # Synthetic root package and parent layers so relative imports resolve.
    root = types.ModuleType(_PKG)
    root.__path__ = [_PROJECT_ROOT]
    sys.modules[_PKG] = root

    ui_mod = types.ModuleType(f"{_PKG}.ui")
    ui_mod.__path__ = [os.path.join(_PROJECT_ROOT, "ui")]
    sys.modules[f"{_PKG}.ui"] = ui_mod

    ctrl_mod = types.ModuleType(f"{_PKG}.ui.controllers")
    ctrl_mod.__path__ = [os.path.join(_PROJECT_ROOT, "ui", "controllers")]
    sys.modules[f"{_PKG}.ui.controllers"] = ctrl_mod

    # The handler does ``from ...core.services.favorites_service import
    # FilterFavorite`` only under TYPE_CHECKING — we don't need the real
    # type, so a placeholder package is enough to keep importlib happy if
    # any other import path tries to walk it.
    core_mod = types.ModuleType(f"{_PKG}.core")
    core_mod.__path__ = [os.path.join(_PROJECT_ROOT, "core")]
    sys.modules[f"{_PKG}.core"] = core_mod

    # Load the three handler-side modules in dependency order.
    for mod_name in (
        "favorites_dockwidget_surface",
        "favorites_spatial_helpers",
        "favorites_spatial_handler",
    ):
        full_name = f"{_PKG}.ui.controllers.{mod_name}"
        path = os.path.join(_PROJECT_ROOT, "ui", "controllers", f"{mod_name}.py")
        spec = importlib.util.spec_from_file_location(full_name, path)
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = f"{_PKG}.ui.controllers"
        sys.modules[full_name] = mod
        spec.loader.exec_module(mod)


_install_stubs()

_handler_mod = sys.modules[f"{_PKG}.ui.controllers.favorites_spatial_handler"]
FavoritesSpatialHandler = _handler_mod.FavoritesSpatialHandler


# --- Fakes -------------------------------------------------------------


class _FakeLayer:
    """Minimal stand-in for QgsVectorLayer.

    ``selectByIds`` and ``getFeature`` are spied on; ``getFeature`` returns
    a lightweight feature whose ``isValid()`` toggles per-FID via a
    pre-seeded mapping.
    """

    def __init__(
        self,
        layer_id: str,
        name: str = "test_layer",
        valid_features: Optional[List[int]] = None,
    ) -> None:
        self._id = layer_id
        self._name = name
        self._valid_features = set(valid_features or [])
        self.selectByIds = MagicMock()
        self.getFeature = MagicMock(side_effect=self._get_feature)

    def id(self) -> str:
        return self._id

    def name(self) -> str:
        return self._name

    def _get_feature(self, fid: int) -> Any:
        feat = MagicMock()
        feat.isValid.return_value = fid in self._valid_features
        return feat


class _FakeBufferWidget:
    def __init__(self) -> None:
        self._value: float = 0.0
        self.setValue = MagicMock(side_effect=self._set_value)

    def _set_value(self, v: float) -> None:
        self._value = float(v)


class _FakeExpressionWidget:
    def __init__(self) -> None:
        self._expression: Optional[str] = None
        self.setExpression = MagicMock(side_effect=self._set_expr)

    def _set_expr(self, expr: str) -> None:
        self._expression = expr


class _FakeDockwidget:
    """Implements just the slice of DockwidgetSurface that the handler
    reads/writes — see ui/controllers/favorites_dockwidget_surface.py."""

    def __init__(self, current_layer: Optional[_FakeLayer]) -> None:
        self.current_layer = current_layer
        self.widgets_initialized = True
        self.current_exploring_groupbox = None
        self.widgets: Dict[str, Dict[str, Any]] = {
            "EXPLORING": {"CUSTOM_SELECTION_EXPRESSION": {"WIDGET": _FakeExpressionWidget()}},
        }
        self.PROJECT_LAYERS: Dict[str, Any] = {}
        self._restored_task_features: Optional[Any] = None
        self._restored_predicates: Optional[Dict[str, bool]] = None
        self.mQgsDoubleSpinBox_filtering_buffer_value = _FakeBufferWidget()
        self.mQgsFieldExpressionWidget_filtering_active_expression = _FakeExpressionWidget()
        self.comboBox_filtering_current_layer = MagicMock()
        self.favorites_indicator_label = MagicMock()
        self._restore_groupbox_ui_state = MagicMock()

    def get_current_features(self) -> Any:
        return ([], [])


class _FakeController:
    def __init__(self, dockwidget: _FakeDockwidget) -> None:
        self.dockwidget = dockwidget
        self._favorites_manager = MagicMock()

    def _show_warning(self, msg: str) -> None:
        pass

    def tr(self, source: str, *args: Any, **kwargs: Any) -> str:
        return source


def _make_favorite(
    name: str = "fav1",
    layer_id: str = "L1",
    layer_name: str = "test_layer",
    spatial_config: Optional[Dict[str, Any]] = None,
) -> Any:
    fav = types.SimpleNamespace()
    fav.name = name
    fav.layer_id = layer_id
    fav.layer_name = layer_name
    fav.spatial_config = spatial_config
    return fav


# --- Tests --------------------------------------------------------------


class TestNoSpatialConfig:
    def test_returns_false_when_spatial_config_missing(self):
        layer = _FakeLayer("L1")
        handler = FavoritesSpatialHandler(_FakeController(_FakeDockwidget(layer)))
        favorite = _make_favorite(spatial_config=None)
        assert handler.restore_spatial_config(favorite) is False

    def test_returns_false_when_spatial_config_empty_dict(self):
        layer = _FakeLayer("L1")
        handler = FavoritesSpatialHandler(_FakeController(_FakeDockwidget(layer)))
        favorite = _make_favorite(spatial_config={})
        assert handler.restore_spatial_config(favorite) is False


class TestCrossLayerFidGuard:
    """The 2026-04-21 fix: do NOT push feature_ids onto a layer the favorite
    was not captured against — foreign FIDs would corrupt the selection.
    """

    def test_same_layer_id_pushes_fids(self):
        layer = _FakeLayer("L1", "communes", valid_features=[10, 20])
        handler = FavoritesSpatialHandler(_FakeController(_FakeDockwidget(layer)))
        favorite = _make_favorite(
            layer_id="L1",
            layer_name="communes",
            spatial_config={"task_feature_ids": [10, 20]},
        )

        ok = handler.restore_spatial_config(favorite)

        assert ok is True
        layer.selectByIds.assert_called_once_with([10, 20])
        assert layer.getFeature.call_count == 2

    def test_different_layer_id_skips_selectbyids(self):
        # Cross-layer apply: favorite was captured on L1 but the user is
        # now on L99. The handler must not call selectByIds.
        layer = _FakeLayer("L99", "other_layer")
        handler = FavoritesSpatialHandler(_FakeController(_FakeDockwidget(layer)))
        favorite = _make_favorite(
            layer_id="L1",
            layer_name="communes",
            spatial_config={"task_feature_ids": [10, 20]},
        )

        ok = handler.restore_spatial_config(favorite)

        assert ok is True
        layer.selectByIds.assert_not_called()
        layer.getFeature.assert_not_called()
        assert _dw(handler)._restored_task_features is None

    def test_layer_name_fallback_match(self):
        # No matching id, but matching name (last-chance fuzzy match).
        layer = _FakeLayer("L99", "communes", valid_features=[42])
        handler = FavoritesSpatialHandler(_FakeController(_FakeDockwidget(layer)))
        favorite = _make_favorite(
            layer_id="L1",
            layer_name="communes",
            spatial_config={"task_feature_ids": [42]},
        )

        ok = handler.restore_spatial_config(favorite)

        assert ok is True
        layer.selectByIds.assert_called_once_with([42])

    def test_signature_match_wins_over_id_mismatch(self):
        # source_layer_signature is the strongest match (portable across
        # projects). Patch the helper's signature function for this test.
        from filter_mate_t1_handler.ui.controllers import favorites_spatial_helpers as _h

        original = _h.layer_signature_for
        _h.layer_signature_for = lambda lyr: "sig-shared"
        try:
            layer = _FakeLayer("L99", "renamed", valid_features=[7])
            handler = FavoritesSpatialHandler(_FakeController(_FakeDockwidget(layer)))
            favorite = _make_favorite(
                layer_id="L1",
                layer_name="communes",
                spatial_config={
                    "source_layer_signature": "sig-shared",
                    "task_feature_ids": [7],
                },
            )

            ok = handler.restore_spatial_config(favorite)

            assert ok is True
            layer.selectByIds.assert_called_once_with([7])
        finally:
            _h.layer_signature_for = original


class TestNoCurrentLayer:
    def test_skips_fid_restore_when_current_layer_is_none(self):
        # Predicates and buffer should still be restored — only the
        # FID-pushing branch needs the layer.
        handler = FavoritesSpatialHandler(_FakeController(_FakeDockwidget(None)))
        favorite = _make_favorite(
            spatial_config={
                "task_feature_ids": [1, 2, 3],
                "predicates": {"intersects": True},
                "buffer_value": 7.5,
            }
        )

        ok = handler.restore_spatial_config(favorite)

        assert ok is True
        assert _dw(handler)._restored_predicates == {"intersects": True}
        assert _dw(handler).mQgsDoubleSpinBox_filtering_buffer_value._value == 7.5


class TestRestorePredicatesAndBuffer:
    def test_predicates_stored_on_dockwidget(self):
        layer = _FakeLayer("L1", valid_features=[1])
        handler = FavoritesSpatialHandler(_FakeController(_FakeDockwidget(layer)))
        favorite = _make_favorite(
            spatial_config={"predicates": {"intersects": True, "contains": False}}
        )

        ok = handler.restore_spatial_config(favorite)

        assert ok is True
        assert _dw(handler)._restored_predicates == {
            "intersects": True,
            "contains": False,
        }

    def test_buffer_value_pushed_to_widget(self):
        layer = _FakeLayer("L1")
        handler = FavoritesSpatialHandler(_FakeController(_FakeDockwidget(layer)))
        favorite = _make_favorite(spatial_config={"buffer_value": 12.5})

        ok = handler.restore_spatial_config(favorite)

        assert ok is True
        widget = _dw(handler).mQgsDoubleSpinBox_filtering_buffer_value
        widget.setValue.assert_called_once_with(12.5)
        assert widget._value == 12.5

    def test_groupbox_state_restored_first(self):
        layer = _FakeLayer("L1")
        dw = _FakeDockwidget(layer)
        handler = FavoritesSpatialHandler(_FakeController(dw))
        favorite = _make_favorite(
            spatial_config={"exploring_groupbox": "single_selection"}
        )

        ok = handler.restore_spatial_config(favorite)

        assert ok is True
        dw._restore_groupbox_ui_state.assert_called_once_with("single_selection")

    def test_custom_selection_expression_repopulated(self):
        layer = _FakeLayer("L1")
        dw = _FakeDockwidget(layer)
        handler = FavoritesSpatialHandler(_FakeController(dw))
        favorite = _make_favorite(
            spatial_config={"custom_selection_expression": '"foo" = 1'}
        )

        ok = handler.restore_spatial_config(favorite)

        assert ok is True
        widget = dw.widgets["EXPLORING"]["CUSTOM_SELECTION_EXPRESSION"]["WIDGET"]
        widget.setExpression.assert_called_once_with('"foo" = 1')
        assert widget._expression == '"foo" = 1'


class TestInvalidFeatures:
    def test_invalid_features_logged_but_not_stored(self):
        # getFeature returns invalid for all FIDs → no _restored_task_features
        # set so the task picks up the empty state cleanly.
        layer = _FakeLayer("L1", valid_features=[])  # all features invalid
        handler = FavoritesSpatialHandler(_FakeController(_FakeDockwidget(layer)))
        favorite = _make_favorite(spatial_config={"task_feature_ids": [10, 20]})

        ok = handler.restore_spatial_config(favorite)

        assert ok is True
        layer.selectByIds.assert_called_once_with([10, 20])
        # FID iteration happened but produced zero valid features.
        assert _dw(handler)._restored_task_features is None

    def test_partial_invalid_features_still_stores_valid_ones(self):
        layer = _FakeLayer("L1", valid_features=[10])  # 20 is invalid
        handler = FavoritesSpatialHandler(_FakeController(_FakeDockwidget(layer)))
        favorite = _make_favorite(spatial_config={"task_feature_ids": [10, 20]})

        ok = handler.restore_spatial_config(favorite)

        assert ok is True
        stored = _dw(handler)._restored_task_features
        assert stored is not None
        assert len(stored) == 1


class TestExceptionSafety:
    def test_unexpected_failure_returns_false(self):
        # Force a failure deep in the restore path: making spatial_config
        # not subscriptable triggers an exception inside the try block,
        # which the handler swallows and converts to ``return False``.
        layer = _FakeLayer("L1")
        handler = FavoritesSpatialHandler(_FakeController(_FakeDockwidget(layer)))

        class ExplodingDict(dict):
            def get(self, key, default=None):
                raise RuntimeError("boom")

        favorite = _make_favorite(spatial_config=ExplodingDict({"task_feature_ids": [1]}))

        ok = handler.restore_spatial_config(favorite)

        assert ok is False


# --- Helpers ------------------------------------------------------------


def _dw(handler: Any) -> _FakeDockwidget:
    """Tiny accessor so tests don't reach into ``_controller`` directly."""
    return handler._controller.dockwidget
