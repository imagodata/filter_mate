"""Exercise the real panel handlers with lightweight widget stand-ins, without Qt."""
import importlib
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit
_ROOT = pathlib.Path(__file__).resolve().parents[5]
_PKG = "fm_raster_handlers_test"


@pytest.fixture(scope="module")
def raster():
    # The root conftest's QWidget MagicMock replaces subclasses with mocks. A
    # plain base keeps the actual methods available; no QWidget is instantiated.
    widgets = sys.modules["qgis.PyQt.QtWidgets"]
    previous = widgets.QWidget
    widgets.QWidget = object
    try:
        for suffix, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.domain", _ROOT / "core/domain"),
                             (".ui", _ROOT / "ui"), (".ui.widgets", _ROOT / "ui/widgets"),
                             (".ui.widgets.coverage_panels", _ROOT / "ui/widgets/coverage_panels")):
            package = types.ModuleType(_PKG + suffix)
            package.__path__ = [str(path)]
            sys.modules[_PKG + suffix] = package
        yield importlib.import_module(_PKG + ".ui.widgets.coverage_panels.raster_exploring_panel")
    finally:
        widgets.QWidget = previous


class Text:
    def __init__(self, text=""):
        self.text, self.blocked = text, False

    def toPlainText(self):
        return self.text

    def setPlainText(self, text):
        self.text = text

    def blockSignals(self, blocked):
        previous, self.blocked = self.blocked, blocked
        return previous


@pytest.fixture
def panel(raster):
    panel = object.__new__(raster.RasterExploringPanel)
    panel.tr = lambda text: text
    panel._mode = raster.RasterSelectionMode.RANGE
    panel._derivative = raster.RasterDerivative.VALUE
    panel._custom_quantity = True
    panel._all_bands = False
    panel._active_band = 1
    panel._pipette_bands = [1]
    panel._quantity_edit = Text('"img@2" - "img@1"')
    panel._expression_edit = Text()
    panel._reference = "img"
    panel._histograms = {(1, panel._quantity_edit.text): ([10, 10], -1.0, 1.0)}
    panel._low = panel._high = None
    panel._picks, panel._seeds, panel._pick_kind = [], [], ""
    panel._pick_target = raster.PICK_SIMILAR
    panel._summary = types.SimpleNamespace(classes=[])
    panel._min_spin, panel._max_spin = MagicMock(), MagicMock()
    panel._min_spin.decimals.return_value = 6
    panel._min_spin.minimum.return_value = -1
    panel._max_spin.maximum.return_value = 1
    panel._histogram = MagicMock()
    panel._sample_label = MagicMock()
    panel._opening_combo = MagicMock()
    panel._opening_combo.currentData.return_value = 2
    panel._fill_holes_check = MagicMock()
    panel._fill_holes_check.isChecked.return_value = False
    panel._tolerance_spin = MagicMock()
    panel._tolerance_spin.value.return_value = 5
    panel._set_pipette_selection = MagicMock()
    panel._quantity_debounce = MagicMock()
    return panel


def test_range_updates_formula_without_replacing_numeric_quantity(panel, raster):
    panel._set_range(-0.25, 0.75)
    assert panel._quantity_edit.text == '"img@2" - "img@1"'
    assert panel._expression_edit.text == '(("img@2" - "img@1") >= -0.25 AND ("img@2" - "img@1") <= 0.75)'
    panel._histogram.set_range.assert_called_with(-0.25, 0.75)


def test_pipette_uses_custom_value_and_preserves_disjoint_samples(panel, raster):
    panel.set_color_sample({1: 100, 2: 200}, terrain={"custom": -0.5}, point=(1, 2))
    panel.set_color_sample({1: 200, 2: 100}, extend=True, terrain={"custom": 0.5}, point=(3, 4))
    selection = panel._set_pipette_selection.call_args.args[0]
    assert 'abs(("img@2" - "img@1") - -0.5) <= 0.1' in selection.expression
    assert " OR " in selection.expression
    assert panel._picks == [-0.5, 0.5]
    assert selection.object_opening == 2 and not selection.fill_holes


@pytest.mark.parametrize("value", [None, float("nan"), float("inf")])
def test_invalid_categorical_pick_preserves_existing_selection(panel, raster, value):
    panel._custom_quantity = False
    panel._summary.classes = [(1, "class", "")]
    panel._picks, panel._pick_kind = [1], "classes"
    panel.set_color_sample({1: value})
    assert panel._picks == [1]
    panel._set_pipette_selection.assert_not_called()


def test_one_checked_band_is_used_instead_of_the_active_band(panel, raster):
    panel._custom_quantity = False
    panel._pipette_bands = [2]
    panel._band_spans = {2: 100}
    panel.set_color_sample({1: 10, 2: 60})
    selection = panel._set_pipette_selection.call_args.args[0]
    assert selection.band == 2 and (selection.minimum, selection.maximum) == (55, 65)


def test_ctrl_click_keeps_separate_scalar_intervals(panel, raster):
    panel._custom_quantity = False
    panel._pipette_bands = [2]
    panel._band_spans = {2: 100}
    panel.set_color_sample({1: 10, 2: 20})
    panel.set_color_sample({1: 10, 2: 80}, extend=True)
    selection = panel._set_pipette_selection.call_args.args[0]
    assert selection.mode is raster.RasterSelectionMode.EXPRESSION
    assert selection.expression == '(abs("img@2" - 20) <= 5) OR (abs("img@2" - 80) <= 5)'


def test_histogram_drag_promotes_expression_to_custom_quantity(panel, raster):
    expression = '"img@2" / 100'
    panel._mode = raster.RasterSelectionMode.EXPRESSION
    panel._expression_edit.text = expression
    panel._expression_histogram = MagicMock()
    panel._expression_histogram.range.return_value = (0.25, 0.75)
    panel._histograms[(1, expression)] = ([10, 10], 0, 1)
    panel._set_derivative = MagicMock()
    panel._forget_picks = MagicMock()
    panel._activate_mode = lambda mode, emit=False: setattr(panel, "_mode", mode)
    panel._apply_band = MagicMock()
    panel.bandChanged = panel.modeChosen = MagicMock()
    panel._emit_now = MagicMock()
    panel._on_expression_histogram_changed(0.25, 0.75)
    assert panel._mode is raster.RasterSelectionMode.RANGE and panel._custom_quantity
    assert panel._quantity_edit.text == expression
    assert panel._expression_edit.text == '(("img@2" / 100) >= 0.25 AND ("img@2" / 100) <= 0.75)'
