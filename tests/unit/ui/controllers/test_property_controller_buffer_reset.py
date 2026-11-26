# -*- coding: utf-8 -*-
"""
Reset of a spinbox to its default (audit 24/11, lot 1 #9).

``QgsDoubleSpinBox.clearValue()`` reads the clear value, it resets nothing: the widget kept the buffer of the
previous layer, which the reset then stored (and persisted) for the next layer; shown again after the undo of an
agent turn that had set a buffer, the widget kept the turn's buffer the same way.

Loaded by path under a private synthetic package, like the coverage widget tests: the real controller module is
used, Qt / QGIS resolve to the root mocks. ``BaseController`` needs Qt widgets, which the reset helpers do not
use, so it is stubbed.
"""
import importlib
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_prop_reset_test"


def _load_modules():
    for name, path in (
        (_PKG, _ROOT),
        (_PKG + ".infrastructure", _ROOT / "infrastructure"),
        (_PKG + ".ui", _ROOT / "ui"),
        (_PKG + ".ui.controllers", _ROOT / "ui" / "controllers"),
    ):
        if name not in sys.modules:
            package = types.ModuleType(name)
            package.__path__ = [str(path)]
            package.__package__ = name
            sys.modules[name] = package
    stub = types.ModuleType(_PKG + ".ui.controllers.base_controller")

    class BaseController:
        def __init__(self, dockwidget=None):
            self.dockwidget = dockwidget

    stub.BaseController = BaseController
    sys.modules[stub.__name__] = stub
    return importlib.import_module(f"{_PKG}.ui.controllers.property_controller")


prop = _load_modules()


class SpinBox:
    """A ``QgsDoubleSpinBox``: ``clearValue()`` is the getter of the clear value, without side effect."""

    def __init__(self, value, clear=0.0):
        self._value = float(value)
        self._clear = float(clear)

    def clearValue(self):
        return self._clear

    def value(self):
        return self._value

    def setValue(self, value):
        self._value = float(value)


class TestSpinBoxReset:
    def test_reset_of_a_layer_puts_the_buffer_back_to_zero(self):
        """Changing layer with the buffer group off no longer copies the previous buffer onto the next layer."""
        spin = SpinBox(50.0)
        project_layers = {"L1": {"filtering": {"has_buffer_value": False, "buffer_value": 50.0}}}
        prop.PropertyController._reset_layer_property_widget(
            None, spin, "QgsDoubleSpinBox", ("filtering", "buffer_value"), "L1", project_layers,
            types.SimpleNamespace(id=lambda: "L1"), False, types.SimpleNamespace())
        assert spin.value() == 0.0
        assert project_layers["L1"]["filtering"]["buffer_value"] == 0.0

    def test_reset_of_an_export_puts_the_spinbox_back_to_zero(self):
        spin = SpinBox(25.0)
        project_props = {"EXPORTING": {"MIN_COVERAGE": 25.0}}
        prop.PropertyController._reset_export_property_widget(
            None, spin, "QgsDoubleSpinBox", ("EXPORTING", "MIN_COVERAGE"), project_props, False,
            types.SimpleNamespace())
        assert spin.value() == 0.0
        assert project_props["EXPORTING"]["MIN_COVERAGE"] == 0.0

    def test_showing_a_layer_without_a_buffer_drops_the_buffer_of_the_undone_turn(self):
        """Undo of an agent turn that had set a buffer restores the options; shown again, the panel (whose buffer
        group is off) goes through this reset, which must not keep the turn's buffer on screen."""
        spin = SpinBox(25.0)
        project_layers = {"L1": {"filtering": {"has_buffer_value": False}}}
        prop.PropertyController._reset_layer_property_widget(
            None, spin, "QgsDoubleSpinBox", ("filtering", "buffer_value"), "L1", project_layers,
            types.SimpleNamespace(id=lambda: "L1"), False, types.SimpleNamespace())
        assert spin.value() == 0.0
