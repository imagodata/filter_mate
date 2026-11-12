# -*- coding: utf-8 -*-
"""The FILTERING targets list filled again after a CROSS_FILTER option changed (PropertyController).

A click in the list is not saved: the list on screen is what the user chose. Filling it again must
keep each listed layer as it is on screen, unchecked ones included, and keep in the saved targets
a layer the option takes off the list, so that it comes back checked with the option.
"""
import importlib.util
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_refill_targets_test"
CHECKED, UNCHECKED = 2, 0
Qt = types.SimpleNamespace(CheckState=types.SimpleNamespace(Checked=CHECKED, Unchecked=UNCHECKED),
                           ItemDataRole=types.SimpleNamespace(UserRole=256))


@pytest.fixture
def controller_class(monkeypatch):
    monkeypatch.setitem(sys.modules, "qgis.PyQt.QtCore", types.SimpleNamespace(Qt=Qt, pyqtSignal=MagicMock()))
    for name, path in (("", _ROOT), (".ui", _ROOT / "ui"), (".ui.controllers", _ROOT / "ui" / "controllers"),
                       (".infrastructure", None)):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)] if path else []
        monkeypatch.setitem(sys.modules, _PKG + name, package)
    base = types.ModuleType(f"{_PKG}.ui.controllers.base_controller")
    base.BaseController = type("BaseController", (), {})
    monkeypatch.setitem(sys.modules, base.__name__, base)
    signal_utils = types.ModuleType(f"{_PKG}.infrastructure.signal_utils")
    signal_utils.SignalBlocker = MagicMock()
    monkeypatch.setitem(sys.modules, signal_utils.__name__, signal_utils)
    spec = importlib.util.spec_from_file_location(f"{_PKG}.ui.controllers.property_controller",
                                                  _ROOT / "ui" / "controllers" / "property_controller.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module.PropertyController


class _Item:
    def __init__(self, data, state=None):
        self._data, self.state = data, state

    def checkState(self):
        return self.state if self.state is not None else UNCHECKED

    def setCheckState(self, state):
        self.state = state

    def data(self, role):
        return self._data


class _Dock:
    """The dock as the refill sees it: populate checks the saved targets while the key is on (FilteringController)."""

    def __init__(self, saved, key_on=True, layers=("v1", "v2", "r1")):
        self.layers, self.listed = layers, {layer_id: True for layer_id in layers}
        self.PROJECT_LAYERS = {"src": {"filtering": {"has_layers_to_filter": key_on, "layers_to_filter": list(saved)}}}
        self.current_layer = types.SimpleNamespace(id=lambda: "src")
        self.items = []
        model = types.SimpleNamespace(rowCount=lambda: len(self.items), item=lambda row: self.items[row])
        self.checkableComboBoxLayer_filtering_layers_to_filter = types.SimpleNamespace(model=lambda: model)
        self.filtering_populate_layers_chekableCombobox(self.current_layer)

    def manageSignal(self, *args, **kwargs):
        pass

    def filtering_populate_layers_chekableCombobox(self, layer):
        filtering = self.PROJECT_LAYERS["src"]["filtering"]
        saved, key_on = filtering["layers_to_filter"], filtering["has_layers_to_filter"]
        self.items = [_Item({"layer_id": i}, CHECKED if key_on and i in saved else UNCHECKED)
                      for i in self.layers if self.listed[i]]
        self.items.append(_Item({"unfilterable_layer_id": "osm"}))  # a greyed web basemap

    def click(self, layer_id, state):
        next(item for item in self.items if item.data(None).get("layer_id") == layer_id).setCheckState(state)

    def screen(self):
        return {item.data(None)["layer_id"]: item.checkState() == CHECKED for item in self.items
                if "layer_id" in item.data(None)}

    @property
    def saved(self):
        return self.PROJECT_LAYERS["src"]["filtering"]["layers_to_filter"]


def _controller(controller_class, dock):
    controller = controller_class.__new__(controller_class)
    controller.dockwidget = dock
    return controller


def test_a_target_unchecked_on_screen_stays_unchecked(controller_class):
    """Review 2026-11-12: V2 unchecked by a click came back checked, saved, and filtered at the next launch."""
    dock = _Dock(saved=["v1", "v2", "r1"])
    controller = _controller(controller_class, dock)
    dock.click("v2", UNCHECKED)
    dock.listed["r1"] = False  # vector_source_raster_targets turned off
    controller.refill_layers_to_filter()
    assert dock.screen() == {"v1": True, "v2": False}
    assert dock.saved == ["v1", "r1"]  # r1 kept: it comes back with the option
    dock.listed["r1"] = True  # turned back on
    controller.refill_layers_to_filter()
    assert dock.screen() == {"v1": True, "v2": False, "r1": True}
    assert dock.saved == ["v1", "r1"]


def test_everything_unchecked_is_saved_too(controller_class):
    dock = _Dock(saved=["v1", "r1"])
    controller = _controller(controller_class, dock)
    dock.click("v1", UNCHECKED)
    dock.click("r1", UNCHECKED)
    controller.refill_layers_to_filter()
    assert dock.screen() == {"v1": False, "v2": False, "r1": False}
    assert dock.saved == []


def test_a_target_unchecked_then_hidden_does_not_come_back(controller_class):
    dock = _Dock(saved=["v1", "r1"])
    controller = _controller(controller_class, dock)
    dock.click("r1", UNCHECKED)
    dock.listed["r1"] = False
    controller.refill_layers_to_filter()
    assert dock.saved == ["v1"]
    dock.listed["r1"] = True
    controller.refill_layers_to_filter()
    assert dock.screen() == {"v1": True, "v2": False, "r1": False}


def test_a_click_checked_target_hidden_by_the_option_is_kept(controller_class):
    dock = _Dock(saved=["v1"])
    controller = _controller(controller_class, dock)
    dock.click("r1", CHECKED)  # not saved by the click
    dock.listed["r1"] = False
    controller.refill_layers_to_filter()
    assert dock.saved == ["v1", "r1"]


def test_key_off_saves_nothing_and_keeps_the_screen(controller_class):
    """Key off: the list was filled showing nothing checked; the saved targets are left alone."""
    dock = _Dock(saved=["v1", "r1"], key_on=False)
    controller = _controller(controller_class, dock)
    dock.click("v2", CHECKED)  # left on screen from before the key went off
    dock.listed["r1"] = False
    controller.refill_layers_to_filter()
    assert dock.saved == ["v1", "r1"]
    assert dock.screen() == {"v1": False, "v2": True}


def test_the_greyed_row_is_never_checked(controller_class):
    dock = _Dock(saved=["v1"])
    _controller(controller_class, dock).refill_layers_to_filter()
    assert dock.items[-1].state is None


def test_switching_the_key_on_still_restores_the_saved_targets(controller_class):
    """The targets key path is unchanged: filled with the key off, the list showed nothing checked."""
    dock = _Dock(saved=["v1", "r1"], key_on=False)
    controller = _controller(controller_class, dock)
    dock.PROJECT_LAYERS["src"]["filtering"]["has_layers_to_filter"] = True
    controller._refresh_layers_to_filter()
    assert dock.screen() == {"v1": True, "v2": False, "r1": True}
    assert dock.saved == ["v1", "r1"]
