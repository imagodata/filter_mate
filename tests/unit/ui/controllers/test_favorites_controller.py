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
    # from. The controller uses `from .base_controller import BaseController`
    # AND `from ..styles.favorites_styles import ...`, so the shim needs a
    # parent ``ui`` package and a ``styles`` sibling for the second import to
    # resolve.
    shim_root = "_fm_test_ui_shim"
    if shim_root not in sys.modules:
        shim_root_mod = types.ModuleType(shim_root)
        shim_root_mod.__path__ = [str(_project_root / "ui")]
        shim_root_mod.__package__ = shim_root
        sys.modules[shim_root] = shim_root_mod

    shim_pkg_name = f"{shim_root}.controllers"
    if shim_pkg_name not in sys.modules:
        shim_pkg = types.ModuleType(shim_pkg_name)
        shim_pkg.__path__ = [str(_project_root / "ui" / "controllers")]
        shim_pkg.__package__ = shim_pkg_name
        sys.modules[shim_pkg_name] = shim_pkg
        sys.modules[f"{shim_pkg_name}.base_controller"] = base_mod

    styles_pkg_name = f"{shim_root}.styles"
    if styles_pkg_name not in sys.modules:
        styles_pkg = types.ModuleType(styles_pkg_name)
        styles_pkg.__path__ = [str(_project_root / "ui" / "styles")]
        styles_pkg.__package__ = styles_pkg_name
        sys.modules[styles_pkg_name] = styles_pkg

        styles_full = f"{styles_pkg_name}.favorites_styles"
        styles_spec = importlib.util.spec_from_file_location(
            styles_full,
            str(_project_root / "ui" / "styles" / "favorites_styles.py"),
        )
        styles_mod = importlib.util.module_from_spec(styles_spec)
        sys.modules[styles_full] = styles_mod
        styles_spec.loader.exec_module(styles_mod)


_ensure_favorites_mocks()


def _load_favorites_controller():
    """Load favorites_controller.py as a module inside the shim package so
    its `from .base_controller import BaseController` resolves to the fake
    and `from ..styles.favorites_styles import ...` reaches the real file.
    """
    mod_name = "_fm_test_ui_shim.controllers.favorites_controller"
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


# ---------------------------------------------------------------------------
# Geometric predicate capture/restore — 2026-04-23 regression
# ---------------------------------------------------------------------------
#
# The favorites controller used to read/write ``PROJECT_LAYERS[id]['filtering']
# ['predicates']`` as a dict — a key that nothing in the code actually writes.
# Favorites therefore lost their predicate configuration on save, and after
# project reopen the filter task ran with ``has_geometric_predicates=False``
# while the combobox still showed ``['Intersect']`` (persisted by QGIS at the
# project level). The tests below pin the capture → serialize → restore
# round-trip against the canonical keys.


def _make_dockwidget_for_predicate_capture(combobox_items, button_checked):
    dw = MagicMock()

    combo = MagicMock()
    combo.checkedItems.return_value = list(combobox_items)
    dw.comboBox_filtering_geometric_predicates = combo

    btn = MagicMock()
    btn.isChecked.return_value = button_checked
    dw.pushButton_checkable_filtering_geometric_predicates = btn

    # Keep _capture_spatial_config from branching into feature / groupbox /
    # custom-expression capture paths we don't care about for this test.
    dw.current_exploring_groupbox = None
    dw.get_current_features.return_value = ([], None)
    dw.widgets = {"EXPLORING": {"CUSTOM_SELECTION_EXPRESSION": {"WIDGET": None}}}
    dw.PROJECT_LAYERS = {}
    dw.current_layer = None

    spinbox = MagicMock()
    spinbox.value.return_value = 0.0
    dw.mQgsDoubleSpinBox_filtering_buffer_value = spinbox

    return dw, combo, btn


class TestCapturePredicates:
    """_capture_spatial_config must write the canonical keys from live widgets."""

    def test_captures_predicates_list_and_flag_from_widgets(self):
        ctrl = FavoritesController.__new__(FavoritesController)
        dw, _, _ = _make_dockwidget_for_predicate_capture(
            combobox_items=['Intersect'], button_checked=True
        )
        ctrl._dockwidget = dw

        config = ctrl._capture_spatial_config()

        assert config is not None
        assert config['geometric_predicates'] == ['Intersect']
        assert config['has_geometric_predicates'] is True
        # Legacy bogus key must not be written anymore.
        assert 'predicates' not in config

    def test_returns_none_when_no_predicates_and_no_other_state(self):
        ctrl = FavoritesController.__new__(FavoritesController)
        dw, _, _ = _make_dockwidget_for_predicate_capture(
            combobox_items=[], button_checked=False
        )
        ctrl._dockwidget = dw

        # Nothing to capture → None so _create_favorite's guard still fires.
        assert ctrl._capture_spatial_config() is None

    def test_captures_multiple_predicates(self):
        ctrl = FavoritesController.__new__(FavoritesController)
        dw, _, _ = _make_dockwidget_for_predicate_capture(
            combobox_items=['Intersect', 'Contain', 'Are within'],
            button_checked=True,
        )
        ctrl._dockwidget = dw

        config = ctrl._capture_spatial_config()
        assert config['geometric_predicates'] == ['Intersect', 'Contain', 'Are within']
        assert config['has_geometric_predicates'] is True

    def test_falls_back_to_project_layers_when_widget_missing(self):
        """Headless contexts (no dockwidget widgets) must still read stored state."""
        ctrl = FavoritesController.__new__(FavoritesController)
        dw = MagicMock(spec=[
            'PROJECT_LAYERS', 'current_layer', 'widgets',
            'current_exploring_groupbox', 'get_current_features',
            'mQgsDoubleSpinBox_filtering_buffer_value',
        ])
        # Simulate absent attributes — getattr returns None through spec.
        current_layer = MagicMock()
        current_layer.id.return_value = 'layer-xyz'
        dw.PROJECT_LAYERS = {
            'layer-xyz': {
                'filtering': {
                    'has_geometric_predicates': True,
                    'geometric_predicates': ['Intersect'],
                }
            }
        }
        dw.current_layer = current_layer
        dw.current_exploring_groupbox = None
        dw.get_current_features.return_value = ([], None)
        dw.widgets = {"EXPLORING": {"CUSTOM_SELECTION_EXPRESSION": {"WIDGET": None}}}
        spinbox = MagicMock()
        spinbox.value.return_value = 0.0
        dw.mQgsDoubleSpinBox_filtering_buffer_value = spinbox
        ctrl._dockwidget = dw

        config = ctrl._capture_spatial_config()
        assert config is not None
        assert config['geometric_predicates'] == ['Intersect']
        assert config['has_geometric_predicates'] is True


def _make_dockwidget_for_predicate_restore(layer_props=None):
    """Build a dockwidget wired for _restore_filtering_ui_from_favorite.

    Only the widgets the restore path actually touches are populated so the
    test's assertions stay focused on the predicate flow. We bypass the
    ``QgsProject.instance().mapLayers()`` scan by leaving remote_layers empty.
    """
    dw = MagicMock()
    dw.widgets_initialized = True

    combo = MagicMock()
    dw.comboBox_filtering_geometric_predicates = combo

    btn = MagicMock()
    dw.pushButton_checkable_filtering_geometric_predicates = btn

    layers_btn = MagicMock()
    dw.pushButton_checkable_filtering_layers_to_filter = layers_btn

    buffer_btn = MagicMock()
    dw.pushButton_checkable_filtering_buffer_value = buffer_btn

    # widgets dict keeps the LAYERS_TO_FILTER lookup harmless.
    dw.widgets = {"FILTERING": {"LAYERS_TO_FILTER": {"WIDGET": None}}}

    current_layer = MagicMock()
    current_layer.id.return_value = 'source-layer'
    dw.current_layer = current_layer

    dw.PROJECT_LAYERS = {'source-layer': layer_props if layer_props is not None else {}}

    return dw, combo, btn


class TestRestorePredicates:
    """_restore_filtering_ui_from_favorite must tick both widgets and persist
    the canonical keys in PROJECT_LAYERS so task_builder sees a consistent state."""

    def test_restores_new_format_canonical_keys(self):
        ctrl = FavoritesController.__new__(FavoritesController)
        layer_props = {}
        dw, combo, btn = _make_dockwidget_for_predicate_restore(layer_props)
        ctrl._dockwidget = dw

        fav = MagicMock()
        fav.name = "WithPred"
        fav.spatial_config = {
            'has_geometric_predicates': True,
            'geometric_predicates': ['Intersect'],
        }
        fav.remote_layers = {}

        ctrl._restore_filtering_ui_from_favorite(fav)

        combo.setCheckedItems.assert_called_once_with(['Intersect'])
        btn.setChecked.assert_called_once_with(True)
        assert layer_props['filtering']['has_geometric_predicates'] is True
        assert layer_props['filtering']['geometric_predicates'] == ['Intersect']

    def test_restores_legacy_predicates_dict(self):
        """Old favorites stored a dict under ``predicates`` — still supported."""
        ctrl = FavoritesController.__new__(FavoritesController)
        layer_props = {}
        dw, combo, btn = _make_dockwidget_for_predicate_restore(layer_props)
        ctrl._dockwidget = dw

        fav = MagicMock()
        fav.name = "Legacy"
        fav.spatial_config = {'predicates': {'Intersect': True, 'Contain': True}}
        fav.remote_layers = {}

        ctrl._restore_filtering_ui_from_favorite(fav)

        # Dict keys become the predicate list; order not guaranteed but contents are.
        args, _ = combo.setCheckedItems.call_args
        assert set(args[0]) == {'Intersect', 'Contain'}
        btn.setChecked.assert_called_once_with(True)
        assert layer_props['filtering']['has_geometric_predicates'] is True
        assert set(layer_props['filtering']['geometric_predicates']) == {'Intersect', 'Contain'}

    def test_restore_preserves_live_widgets_when_keys_absent(self):
        """FIX 2026-04-27: when the favorite carries no predicate info at all,
        restore must NOT push setCheckedItems([]) / setChecked(False) — that
        used to wipe the user's manual selection on every legacy-favorite apply.
        """
        ctrl = FavoritesController.__new__(FavoritesController)
        layer_props = {
            'filtering': {
                # User had Intersect ticked manually before applying the favorite.
                'has_geometric_predicates': True,
                'geometric_predicates': ['Intersect'],
            }
        }
        dw, combo, btn = _make_dockwidget_for_predicate_restore(layer_props)
        ctrl._dockwidget = dw

        fav = MagicMock()
        fav.name = "NoPred"
        fav.spatial_config = {}  # capture skipped predicates
        fav.remote_layers = {}

        ctrl._restore_filtering_ui_from_favorite(fav)

        combo.setCheckedItems.assert_not_called()
        btn.setChecked.assert_not_called()
        # PROJECT_LAYERS predicate state must also stay untouched.
        assert layer_props['filtering']['has_geometric_predicates'] is True
        assert layer_props['filtering']['geometric_predicates'] == ['Intersect']

    def test_restore_explicit_empty_list_clears_widgets(self):
        """When the favorite explicitly stores ``geometric_predicates: []``
        (not just missing), the widgets ARE cleared — that's a deliberate
        capture, not a legacy gap."""
        ctrl = FavoritesController.__new__(FavoritesController)
        layer_props = {
            'filtering': {
                'has_geometric_predicates': True,
                'geometric_predicates': ['Intersect'],
            }
        }
        dw, combo, btn = _make_dockwidget_for_predicate_restore(layer_props)
        ctrl._dockwidget = dw

        fav = MagicMock()
        fav.name = "ExplicitEmpty"
        fav.spatial_config = {
            'has_geometric_predicates': False,
            'geometric_predicates': [],
        }
        fav.remote_layers = {}

        ctrl._restore_filtering_ui_from_favorite(fav)

        combo.setCheckedItems.assert_called_once_with([])
        btn.setChecked.assert_called_once_with(False)
        assert layer_props['filtering']['has_geometric_predicates'] is False
        assert layer_props['filtering']['geometric_predicates'] == []


class TestBackfillLegacyPredicateDefault:
    """_backfill_legacy_predicate_default heals favorites saved before the
    predicate-capture fix: spatial_config has neither geometric_predicates
    nor has_geometric_predicates, but remote_layers is non-empty."""

    def _make_ctrl(self, manager=None):
        ctrl = FavoritesController.__new__(FavoritesController)
        ctrl._dockwidget = MagicMock()
        ctrl._favorites_manager = manager
        return ctrl

    def test_backfills_when_predicate_info_missing_and_remote_layers_present(self):
        manager = MagicMock()
        manager.update_favorite.return_value = True
        ctrl = self._make_ctrl(manager=manager)

        fav = MagicMock()
        fav.id = "fav-1"
        fav.name = "testy"
        fav.spatial_config = {
            'exploring_groupbox': 'single_selection',
            'task_feature_ids': [66],
        }
        fav.remote_layers = {
            'postgres::infra.cables': {'expression': '... ST_Intersects ...'}
        }

        assert ctrl._backfill_legacy_predicate_default(fav) is True
        assert fav.spatial_config['geometric_predicates'] == ['Intersect']
        assert fav.spatial_config['has_geometric_predicates'] is True
        manager.update_favorite.assert_called_once()
        kwargs = manager.update_favorite.call_args.kwargs
        assert kwargs['spatial_config']['geometric_predicates'] == ['Intersect']
        assert kwargs['bump_updated_at'] is False

    def test_skip_when_predicates_already_present(self):
        manager = MagicMock()
        ctrl = self._make_ctrl(manager=manager)

        fav = MagicMock()
        fav.id = "fav-2"
        fav.spatial_config = {'geometric_predicates': ['Contain']}
        fav.remote_layers = {'a': {}}

        assert ctrl._backfill_legacy_predicate_default(fav) is False
        manager.update_favorite.assert_not_called()
        # Existing predicate must be untouched.
        assert fav.spatial_config['geometric_predicates'] == ['Contain']

    def test_skip_when_only_flag_present(self):
        """Even just the ``has_geometric_predicates`` key is enough signal
        that the favorite went through the post-fix capture pipeline."""
        manager = MagicMock()
        ctrl = self._make_ctrl(manager=manager)

        fav = MagicMock()
        fav.id = "fav-3"
        fav.spatial_config = {'has_geometric_predicates': False}
        fav.remote_layers = {'a': {}}

        assert ctrl._backfill_legacy_predicate_default(fav) is False
        manager.update_favorite.assert_not_called()

    def test_skip_when_no_remote_layers(self):
        """Source-only favorites don't need predicates — no remote filtering
        means the predicate combobox is irrelevant."""
        manager = MagicMock()
        ctrl = self._make_ctrl(manager=manager)

        fav = MagicMock()
        fav.id = "fav-4"
        fav.spatial_config = {}
        fav.remote_layers = None

        assert ctrl._backfill_legacy_predicate_default(fav) is False
        manager.update_favorite.assert_not_called()
        assert 'geometric_predicates' not in fav.spatial_config

    def test_inmemory_patch_persists_when_manager_unavailable(self):
        """No favorites_manager → still patch the in-memory model so the
        current apply call works; a future load will retry the heal."""
        ctrl = self._make_ctrl(manager=None)

        fav = MagicMock()
        fav.id = "fav-5"
        fav.spatial_config = None
        fav.remote_layers = {'a': {}}

        assert ctrl._backfill_legacy_predicate_default(fav) is True
        assert fav.spatial_config['geometric_predicates'] == ['Intersect']
        assert fav.spatial_config['has_geometric_predicates'] is True


class TestDirectSubsetApply:
    """Favorites push saved subsets directly to the resolved layers.

    Validates the 2026-04-27 rewrite: ``_apply_favorite_subsets_directly``
    must (a) resolve the source layer via signature/UUID/name and apply
    ``favorite.expression`` on it, (b) resolve each ``remote_layers``
    entry and apply its ``expression``, (c) tolerate missing layers
    without aborting, (d) push everything via ``safe_set_subset_string``.
    """

    @staticmethod
    def _make_layer(name, signature, layer_id):
        layer = MagicMock()
        layer.name.return_value = name
        layer.id.return_value = layer_id
        return layer

    @staticmethod
    def _stub_qgis_project(layers_by_id):
        """Install a QgsProject.instance() stub returning ``layers_by_id``."""
        project = MagicMock()
        project.mapLayers.return_value = layers_by_id
        project.mapLayer.side_effect = lambda lid: layers_by_id.get(lid)
        sys.modules["qgis.core"].QgsProject = MagicMock()
        sys.modules["qgis.core"].QgsProject.instance.return_value = project
        return project

    def _patch_safe_set_subset_string(self, monkeypatch, sink):
        """Patch the safe_set_subset_string used by the controller so we can
        assert each (layer_name, subset) pair the apply pushed.

        The controller resolves the import relative to ``filter_mate.*``
        in the test shim (``from ...infrastructure.database.sql_utils``
        fails at the shim depth, so the fallback ``filter_mate.infrastructure.
        database.sql_utils`` path actually wins). We patch both paths so
        the test stays robust whichever one resolves first.
        """
        import importlib

        def _record(layer, subset):
            sink.append((layer.name(), subset))
            return True

        for mod_name in ("infrastructure.database.sql_utils",
                         "filter_mate.infrastructure.database.sql_utils"):
            try:
                mod = importlib.import_module(mod_name)
            except ImportError:
                continue
            monkeypatch.setattr(mod, "safe_set_subset_string", _record)
        return _record

    def test_pushes_source_and_target_subsets(self, monkeypatch):
        zone_pop = self._make_layer("Zones POP", "postgres::infra.zone_pop", "zonepop-id")
        cables = self._make_layer("Cables", "postgres::infra.cables", "cables-id")
        demand = self._make_layer("Points de demande", "postgres::infra.demand_points", "demand-id")

        layers_by_id = {
            zone_pop.id(): zone_pop,
            cables.id(): cables,
            demand.id(): demand,
        }
        self._stub_qgis_project(layers_by_id)

        # _layer_signature_for is staticmethod — patch it onto every layer for the lookup pass
        monkeypatch.setattr(
            FavoritesController, "_layer_signature_for",
            staticmethod(lambda layer: {
                zone_pop: "postgres::infra.zone_pop",
                cables: "postgres::infra.cables",
                demand: "postgres::infra.demand_points",
            }.get(layer, "unknown::?"))
        )

        applied = []
        self._patch_safe_set_subset_string(monkeypatch, applied)

        ctrl = FavoritesController.__new__(FavoritesController)
        ctrl._dockwidget = MagicMock()
        ctrl._favorites_manager = None

        fav = MagicMock()
        fav.name = "testy"
        fav.layer_id = None
        fav.layer_name = "Zones POP"
        fav.expression = "\"zone_pop\".\"id\" IN ('943b')"
        fav.spatial_config = {'source_layer_signature': 'postgres::infra.zone_pop'}
        fav.remote_layers = {
            'postgres::infra.cables': {
                'expression': 'EXISTS (SELECT 1 FROM zone_pop AS __source WHERE ST_Intersects(...))',
                'layer_signature': 'postgres::infra.cables',
                'display_name': 'Cables',
            },
            'postgres::infra.demand_points': {
                'expression': 'EXISTS (SELECT 1 FROM zone_pop AS __source WHERE ST_Intersects(demand))',
                'layer_signature': 'postgres::infra.demand_points',
                'display_name': 'Points de demande',
            },
        }

        assert ctrl._apply_favorite_subsets_directly(fav) is True

        names_to_subsets = dict(applied)
        # Source layer received the favorite expression
        assert names_to_subsets["Zones POP"] == "\"zone_pop\".\"id\" IN ('943b')"
        # Both remote layers received their EXISTS subsets
        assert "EXISTS" in names_to_subsets["Cables"]
        assert "EXISTS" in names_to_subsets["Points de demande"]

    def test_unresolvable_target_does_not_abort(self, monkeypatch):
        """A target layer that's no longer in the project is logged-skipped;
        other applies still go through and the call still reports success."""
        zone_pop = self._make_layer("Zones POP", "postgres::infra.zone_pop", "zonepop-id")
        cables = self._make_layer("Cables", "postgres::infra.cables", "cables-id")
        layers_by_id = {zone_pop.id(): zone_pop, cables.id(): cables}
        self._stub_qgis_project(layers_by_id)

        monkeypatch.setattr(
            FavoritesController, "_layer_signature_for",
            staticmethod(lambda layer: {
                zone_pop: "postgres::infra.zone_pop",
                cables: "postgres::infra.cables",
            }.get(layer, "unknown::?"))
        )

        applied = []
        self._patch_safe_set_subset_string(monkeypatch, applied)

        ctrl = FavoritesController.__new__(FavoritesController)
        ctrl._dockwidget = MagicMock()
        ctrl._favorites_manager = None

        fav = MagicMock()
        fav.name = "partial"
        fav.layer_id = "zonepop-id"
        fav.layer_name = "Zones POP"
        fav.expression = "\"id\" = 1"
        fav.spatial_config = {'source_layer_signature': 'postgres::infra.zone_pop'}
        fav.remote_layers = {
            'postgres::infra.cables': {
                'expression': 'EXISTS (SELECT 1 FROM ... AS __source ...)',
                'layer_signature': 'postgres::infra.cables',
            },
            'postgres::infra.removed_table': {
                'expression': 'EXISTS (...)',
                'layer_signature': 'postgres::infra.removed_table',
                'display_name': 'Removed',
            },
        }

        assert ctrl._apply_favorite_subsets_directly(fav) is True
        names_to_subsets = dict(applied)
        # Resolved layers got their subsets…
        assert names_to_subsets["Zones POP"] == "\"id\" = 1"
        assert "EXISTS" in names_to_subsets["Cables"]
        # …unresolvable entry never reached the sink.
        assert "Removed" not in names_to_subsets

    def test_returns_false_when_nothing_resolves(self, monkeypatch):
        """If neither source nor any target can be resolved, the apply
        is a no-op and reports failure (so the caller can warn)."""
        self._stub_qgis_project({})
        monkeypatch.setattr(
            FavoritesController, "_layer_signature_for",
            staticmethod(lambda layer: "ghost::?")
        )
        applied = []
        self._patch_safe_set_subset_string(monkeypatch, applied)

        ctrl = FavoritesController.__new__(FavoritesController)
        ctrl._dockwidget = MagicMock()
        ctrl._favorites_manager = None

        # Stub _show_warning so the no-resolve path doesn't hit feedback module
        ctrl._show_warning = MagicMock()
        ctrl.tr = lambda s: s

        fav = MagicMock()
        fav.name = "ghost"
        fav.layer_id = "missing-id"
        fav.layer_name = "Missing"
        fav.expression = ""
        fav.spatial_config = {}
        fav.remote_layers = {}

        assert ctrl._apply_favorite_subsets_directly(fav) is False
        assert applied == []
        ctrl._show_warning.assert_called_once()


class TestExactFilteredFeatureCount:
    """``_exact_filtered_feature_count`` must iterate the filtered cursor
    instead of trusting ``layer.featureCount()`` (PG returns ``pg_class.
    reltuples`` estimates that collapse to 1 for complex EXISTS subsets).
    """

    def test_returns_zero_for_none_layer(self):
        assert FavoritesController._exact_filtered_feature_count(None) == 0

    def test_returns_zero_for_invalid_layer(self):
        layer = MagicMock()
        layer.isValid.return_value = False
        assert FavoritesController._exact_filtered_feature_count(layer) == 0

    def test_counts_via_iteration(self, monkeypatch):
        """Iterating the filtered cursor must drive the count, not the
        featureCount() estimate."""
        sys.modules["qgis.core"].QgsFeatureRequest = MagicMock(return_value=MagicMock())

        layer = MagicMock()
        layer.isValid.return_value = True
        layer.getFeatures.return_value = iter([MagicMock() for _ in range(7)])
        # Stale estimate the helper must NOT trust.
        layer.featureCount.return_value = 1

        assert FavoritesController._exact_filtered_feature_count(layer) == 7

    def test_falls_back_to_featurecount_on_iteration_failure(self):
        """If the iteration path raises (provider quirk, headless test
        context, …), the helper must return ``layer.featureCount()``
        instead of crashing the favorite save."""
        sys.modules["qgis.core"].QgsFeatureRequest = MagicMock(return_value=MagicMock())

        layer = MagicMock()
        layer.isValid.return_value = True
        layer.getFeatures.side_effect = RuntimeError("provider lost connection")
        layer.featureCount.return_value = 42

        assert FavoritesController._exact_filtered_feature_count(layer) == 42


class TestCaptureRestoreRoundTrip:
    """End-to-end: capture → spatial_config → restore must keep the state."""

    def test_round_trip_single_predicate(self):
        # Capture
        ctrl_cap = FavoritesController.__new__(FavoritesController)
        dw_cap, _, _ = _make_dockwidget_for_predicate_capture(
            combobox_items=['Intersect'], button_checked=True
        )
        ctrl_cap._dockwidget = dw_cap
        captured = ctrl_cap._capture_spatial_config()
        assert captured is not None

        # Restore from the captured config
        ctrl_res = FavoritesController.__new__(FavoritesController)
        layer_props = {}
        dw_res, combo, btn = _make_dockwidget_for_predicate_restore(layer_props)
        ctrl_res._dockwidget = dw_res

        fav = MagicMock()
        fav.name = "RT"
        fav.spatial_config = captured
        fav.remote_layers = {}

        ctrl_res._restore_filtering_ui_from_favorite(fav)

        combo.setCheckedItems.assert_called_once_with(['Intersect'])
        btn.setChecked.assert_called_once_with(True)
        assert layer_props['filtering']['has_geometric_predicates'] is True
        assert layer_props['filtering']['geometric_predicates'] == ['Intersect']
