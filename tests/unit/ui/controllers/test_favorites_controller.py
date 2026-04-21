# -*- coding: utf-8 -*-
"""Unit tests for FavoritesController groupbox capture/restore helpers.

Focused on the 2026-04-21 fix: favorites must survive a project reopen even
when the source feature that was selected at save-time is no longer pinned
on the feature picker. The tests exercise:

- _should_downgrade_single_selection (pure predicate — no QGIS needed once the
  class is importable).
- _ensure_applicable_groupbox_for_favorite (thin wrapper that dispatches the
  predicate through a MagicMock dockwidget).

QGIS/Qt dependencies are mocked the same way as in
test_filtering_controller.py so the class can be imported in a plain
Python 3 runner.
"""
import sys
import types
import pathlib
import importlib.util
from unittest.mock import MagicMock

import pytest


_project_root = pathlib.Path(__file__).resolve().parents[4]


def _ensure_favorites_mocks():
    """Install the minimum set of mocks needed to import FavoritesController."""
    ROOT = "filter_mate"
    if ROOT not in sys.modules:
        fm = types.ModuleType(ROOT)
        fm.__path__ = [str(_project_root)]
        fm.__package__ = ROOT
        sys.modules[ROOT] = fm

    _packages = {
        f"{ROOT}.ui": _project_root / "ui",
        f"{ROOT}.ui.controllers": _project_root / "ui" / "controllers",
        f"{ROOT}.infrastructure": _project_root / "infrastructure",
    }
    for pkg_name, pkg_dir in _packages.items():
        if pkg_name not in sys.modules:
            pkg = types.ModuleType(pkg_name)
            pkg.__path__ = [str(pkg_dir)]
            pkg.__package__ = pkg_name
            sys.modules[pkg_name] = pkg

    # Core Qt/QGIS mocks
    qgis_mocks = {
        "qgis": MagicMock(),
        "qgis.core": MagicMock(),
        "qgis.PyQt": MagicMock(),
        "qgis.PyQt.QtCore": MagicMock(),
        "qgis.PyQt.QtGui": MagicMock(),
        "qgis.PyQt.QtWidgets": MagicMock(),
        "qgis.utils": MagicMock(),
    }
    for name, mock_obj in qgis_mocks.items():
        sys.modules.setdefault(name, mock_obj)

    # pyqtSignal returns a callable that yields a MagicMock descriptor
    sys.modules["qgis.PyQt.QtCore"].pyqtSignal = MagicMock(side_effect=lambda *a, **kw: MagicMock())
    sys.modules["qgis.PyQt.QtCore"].QObject = object

    # Provide a FakeBaseController so we don't hit the QObject/ABCMeta metaclass
    # conflict that arises when QObject is a MagicMock.
    class FakeBaseController:
        def __init__(self, dockwidget, filter_service=None, signal_manager=None):
            self._dockwidget = dockwidget
            self._filter_service = filter_service
            self._signal_manager = signal_manager
            self._is_active = False

        @property
        def dockwidget(self):
            return self._dockwidget

        def setup(self): pass
        def teardown(self): pass

        def tr(self, text):
            return text

        def _show_success(self, *a, **kw): pass
        def _show_warning(self, *a, **kw): pass
        def _show_error(self, *a, **kw): pass

    base_mod = types.ModuleType("filter_mate.ui.controllers.base_controller")
    base_mod.__package__ = "filter_mate.ui.controllers"
    base_mod.BaseController = FakeBaseController
    base_mod.QObjectABCMeta = type
    sys.modules["filter_mate.ui.controllers.base_controller"] = base_mod

    # Also install it under the path favorites_controller will actually import
    # from (relative `.base_controller`). We create a shim package that matches.
    shim_pkg_name = "_fm_test_ctrl_pkg"
    if shim_pkg_name not in sys.modules:
        shim_pkg = types.ModuleType(shim_pkg_name)
        shim_pkg.__path__ = [str(_project_root / "ui" / "controllers")]
        shim_pkg.__package__ = shim_pkg_name
        sys.modules[shim_pkg_name] = shim_pkg
        sys.modules[f"{shim_pkg_name}.base_controller"] = base_mod


_ensure_favorites_mocks()


def _load_favorites_controller():
    """Load favorites_controller.py as a module inside the shim package so
    its `from .base_controller import BaseController` resolves to the fake.
    """
    mod_name = "_fm_test_ctrl_pkg.favorites_controller"
    if mod_name in sys.modules:
        return sys.modules[mod_name]

    src = _project_root / "ui" / "controllers" / "favorites_controller.py"
    spec = importlib.util.spec_from_file_location(mod_name, str(src))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


favorites_controller = _load_favorites_controller()
FavoritesController = favorites_controller.FavoritesController


# ---------------------------------------------------------------------------
# _should_downgrade_single_selection — pure predicate
# ---------------------------------------------------------------------------

class TestShouldDowngradeSingleSelection:
    def test_downgrades_when_single_selection_has_no_source_feature(self):
        assert FavoritesController._should_downgrade_single_selection(
            current_groupbox='single_selection',
            has_restored_features=False,
            picker_feature_valid=False,
            selected_feature_count=0,
        ) is True

    def test_no_downgrade_if_picker_has_valid_feature(self):
        assert FavoritesController._should_downgrade_single_selection(
            current_groupbox='single_selection',
            has_restored_features=False,
            picker_feature_valid=True,
            selected_feature_count=0,
        ) is False

    def test_no_downgrade_if_restored_task_features_available(self):
        assert FavoritesController._should_downgrade_single_selection(
            current_groupbox='single_selection',
            has_restored_features=True,
            picker_feature_valid=False,
            selected_feature_count=0,
        ) is False

    def test_no_downgrade_if_layer_has_selected_features(self):
        assert FavoritesController._should_downgrade_single_selection(
            current_groupbox='single_selection',
            has_restored_features=False,
            picker_feature_valid=False,
            selected_feature_count=3,
        ) is False

    def test_no_downgrade_in_multiple_selection_mode(self):
        assert FavoritesController._should_downgrade_single_selection(
            current_groupbox='multiple_selection',
            has_restored_features=False,
            picker_feature_valid=False,
            selected_feature_count=0,
        ) is False

    def test_no_downgrade_in_custom_selection_mode(self):
        assert FavoritesController._should_downgrade_single_selection(
            current_groupbox='custom_selection',
            has_restored_features=False,
            picker_feature_valid=False,
            selected_feature_count=0,
        ) is False

    def test_no_downgrade_when_groupbox_unset(self):
        assert FavoritesController._should_downgrade_single_selection(
            current_groupbox=None,
            has_restored_features=False,
            picker_feature_valid=False,
            selected_feature_count=0,
        ) is False


# ---------------------------------------------------------------------------
# _ensure_applicable_groupbox_for_favorite — MagicMock dockwidget
# ---------------------------------------------------------------------------

def _make_controller_with_dw(**dw_attrs):
    """Build a FavoritesController wired to a MagicMock dockwidget.

    Bypasses __init__ (which wires services) — we only need `self.dockwidget`
    resolved correctly for the helper under test.
    """
    ctrl = FavoritesController.__new__(FavoritesController)
    dw = MagicMock()
    for attr, value in dw_attrs.items():
        setattr(dw, attr, value)
    ctrl._dockwidget = dw
    return ctrl, dw


def _make_favorite(name="fav"):
    fav = MagicMock()
    fav.name = name
    return fav


class TestEnsureApplicableGroupboxForFavorite:
    def test_noop_when_widgets_not_initialized(self):
        ctrl, dw = _make_controller_with_dw(
            widgets_initialized=False,
            current_exploring_groupbox='single_selection',
        )
        ctrl._ensure_applicable_groupbox_for_favorite(_make_favorite())
        dw._restore_groupbox_ui_state.assert_not_called()

    def test_downgrades_when_single_selection_has_no_feature(self):
        # No restored features, picker returns None, no layer selection
        picker = MagicMock()
        picker.feature.return_value = None
        widgets = {
            "EXPLORING": {
                "SINGLE_SELECTION_FEATURES": {"WIDGET": picker},
            }
        }
        layer = MagicMock()
        layer.selectedFeatureCount.return_value = 0

        ctrl, dw = _make_controller_with_dw(
            widgets_initialized=True,
            current_exploring_groupbox='single_selection',
            _restored_task_features=None,
            widgets=widgets,
            current_layer=layer,
        )
        ctrl._ensure_applicable_groupbox_for_favorite(_make_favorite())
        dw._restore_groupbox_ui_state.assert_called_once_with('custom_selection')

    def test_no_downgrade_when_picker_has_valid_feature(self):
        picker_feat = MagicMock()
        picker_feat.isValid.return_value = True
        picker = MagicMock()
        picker.feature.return_value = picker_feat
        widgets = {
            "EXPLORING": {
                "SINGLE_SELECTION_FEATURES": {"WIDGET": picker},
            }
        }
        layer = MagicMock()
        layer.selectedFeatureCount.return_value = 0

        ctrl, dw = _make_controller_with_dw(
            widgets_initialized=True,
            current_exploring_groupbox='single_selection',
            _restored_task_features=None,
            widgets=widgets,
            current_layer=layer,
        )
        ctrl._ensure_applicable_groupbox_for_favorite(_make_favorite())
        dw._restore_groupbox_ui_state.assert_not_called()

    def test_no_downgrade_when_restored_task_features_present(self):
        picker = MagicMock()
        picker.feature.return_value = None
        widgets = {
            "EXPLORING": {
                "SINGLE_SELECTION_FEATURES": {"WIDGET": picker},
            }
        }
        layer = MagicMock()
        layer.selectedFeatureCount.return_value = 0

        ctrl, dw = _make_controller_with_dw(
            widgets_initialized=True,
            current_exploring_groupbox='single_selection',
            _restored_task_features=[MagicMock()],
            widgets=widgets,
            current_layer=layer,
        )
        ctrl._ensure_applicable_groupbox_for_favorite(_make_favorite())
        dw._restore_groupbox_ui_state.assert_not_called()

    def test_no_downgrade_when_layer_has_selection(self):
        picker = MagicMock()
        picker.feature.return_value = None
        widgets = {
            "EXPLORING": {
                "SINGLE_SELECTION_FEATURES": {"WIDGET": picker},
            }
        }
        layer = MagicMock()
        layer.selectedFeatureCount.return_value = 5

        ctrl, dw = _make_controller_with_dw(
            widgets_initialized=True,
            current_exploring_groupbox='single_selection',
            _restored_task_features=None,
            widgets=widgets,
            current_layer=layer,
        )
        ctrl._ensure_applicable_groupbox_for_favorite(_make_favorite())
        dw._restore_groupbox_ui_state.assert_not_called()

    def test_no_downgrade_in_non_single_selection_mode(self):
        ctrl, dw = _make_controller_with_dw(
            widgets_initialized=True,
            current_exploring_groupbox='custom_selection',
            _restored_task_features=None,
            widgets={},
            current_layer=None,
        )
        ctrl._ensure_applicable_groupbox_for_favorite(_make_favorite())
        dw._restore_groupbox_ui_state.assert_not_called()

    def test_tolerates_runtime_error_on_selected_feature_count(self):
        picker = MagicMock()
        picker.feature.return_value = None
        widgets = {
            "EXPLORING": {
                "SINGLE_SELECTION_FEATURES": {"WIDGET": picker},
            }
        }
        layer = MagicMock()
        layer.selectedFeatureCount.side_effect = RuntimeError("C++ object deleted")

        ctrl, dw = _make_controller_with_dw(
            widgets_initialized=True,
            current_exploring_groupbox='single_selection',
            _restored_task_features=None,
            widgets=widgets,
            current_layer=layer,
        )
        # Should still decide to downgrade (no selection detected because the
        # call raised, which we interpret as 0 selected features).
        ctrl._ensure_applicable_groupbox_for_favorite(_make_favorite())
        dw._restore_groupbox_ui_state.assert_called_once_with('custom_selection')


# ---------------------------------------------------------------------------
# _favorite_matches_current_layer — cross-layer apply guard
# ---------------------------------------------------------------------------

def _make_layer(layer_id="layer-A", name="Foo"):
    layer = MagicMock()
    layer.id.return_value = layer_id
    layer.name.return_value = name
    return layer


class TestFavoriteMatchesCurrentLayer:
    def test_returns_false_when_current_layer_is_none(self):
        ctrl, _ = _make_controller_with_dw()
        fav = MagicMock()
        fav.layer_id = "layer-A"
        assert ctrl._favorite_matches_current_layer(fav, None) is False

    def test_matches_by_signature_when_available(self, monkeypatch):
        ctrl, _ = _make_controller_with_dw()
        layer = _make_layer(layer_id="local-uuid-B", name="Renamed")

        # Force _layer_signature_for to yield the same signature the favorite carries
        monkeypatch.setattr(
            FavoritesController,
            "_layer_signature_for",
            staticmethod(lambda layer: "postgres::public.points"),
        )

        fav = MagicMock()
        fav.spatial_config = {"source_layer_signature": "postgres::public.points"}
        fav.layer_id = "original-uuid-A"  # stale UUID, signature wins
        fav.layer_name = "Points de demande"
        assert ctrl._favorite_matches_current_layer(fav, layer) is True

    def test_matches_by_layer_id_when_no_signature(self):
        ctrl, _ = _make_controller_with_dw()
        layer = _make_layer(layer_id="layer-A", name="Foo")
        fav = MagicMock()
        fav.spatial_config = None
        fav.layer_id = "layer-A"
        fav.layer_name = "Bar"
        assert ctrl._favorite_matches_current_layer(fav, layer) is True

    def test_matches_by_layer_name_as_last_resort(self):
        ctrl, _ = _make_controller_with_dw()
        layer = _make_layer(layer_id="local-uuid", name="MyLayer")
        fav = MagicMock()
        fav.spatial_config = {}
        fav.layer_id = None
        fav.layer_name = "MyLayer"
        assert ctrl._favorite_matches_current_layer(fav, layer) is True

    def test_rejects_cross_layer_apply(self, monkeypatch):
        """Different layer_id, different name, different signature -> reject."""
        ctrl, _ = _make_controller_with_dw()
        layer = _make_layer(layer_id="layer-Z", name="OtherLayer")

        monkeypatch.setattr(
            FavoritesController,
            "_layer_signature_for",
            staticmethod(lambda layer: "ogr::other"),
        )

        fav = MagicMock()
        fav.spatial_config = {"source_layer_signature": "postgres::public.points"}
        fav.layer_id = "layer-A"
        fav.layer_name = "MyLayer"
        assert ctrl._favorite_matches_current_layer(fav, layer) is False

    def test_tolerates_runtime_error_on_layer_id(self):
        """A deleted QGIS layer raises on .id()/.name() — must not crash."""
        ctrl, _ = _make_controller_with_dw()
        layer = MagicMock()
        layer.id.side_effect = RuntimeError("C++ object deleted")
        layer.name.side_effect = RuntimeError("C++ object deleted")
        fav = MagicMock()
        fav.spatial_config = None
        fav.layer_id = "layer-A"
        fav.layer_name = "Foo"
        # No match possible, but the predicate should return False gracefully
        assert ctrl._favorite_matches_current_layer(fav, layer) is False
