# -*- coding: utf-8 -*-
"""
2026-11-24: the settings a project carries for its layers are read on the main thread when the task that registers
the layers is created (``capture_layer_settings``), and a legacy name the panel wrote until 5.1.2 is moved under the
right one there, once.

Module tested: infrastructure.utils.layer_settings
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_UTILS_DIR = Path(__file__).resolve().parents[4] / "infrastructure" / "utils"
_PKG = "fmtest_layer_settings_pkg"


def _load():
    full = f"{_PKG}.layer_settings"
    if full in sys.modules:
        return sys.modules[full]
    package = types.ModuleType(_PKG)
    package.__path__ = [str(_UTILS_DIR)]
    package.__package__ = _PKG
    sys.modules[_PKG] = package
    spec = importlib.util.spec_from_file_location(full, _UTILS_DIR / "layer_settings.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full] = module
    spec.loader.exec_module(module)
    return module


layer_settings = _load()


class Layer:
    """The custom properties of a QgsMapLayer."""

    def __init__(self, layer_id, properties=None, deleted=False):
        self._id = layer_id
        self.props = dict(properties or {})
        self.deleted = deleted
        self.writes = []

    def id(self):
        if self.deleted:
            raise RuntimeError("wrapped C/C++ object of type QgsVectorLayer has been deleted")
        return self._id

    def customPropertyKeys(self):
        return list(self.props)

    def customProperty(self, key, default=None):
        return self.props.get(key, default)

    def setCustomProperty(self, key, value):
        self.writes.append(key)
        self.props[key] = value

    def removeCustomProperty(self, key):
        self.writes.append(f"-{key}")
        self.props.pop(key, None)


def V(name):
    return f"variableValues/{name}"


def test_reads_the_settings_of_each_layer():
    parcelles = Layer("parcelles_1", {
        V("filterMate_exploring_single_selection_expression"): '"nom"',
        V("filterMate_filtering_layers_to_filter"): '["routes_1"]',
        V("filterMate_infos_layer_name"): "parcelles",
        "variableNames": ["filterMate_exploring_single_selection_expression"],
    })
    routes = Layer("routes_1", {"labeling/enabled": True})
    captured = layer_settings.capture_layer_settings([parcelles, routes, "an id"])
    assert captured == {"parcelles_1": {"exploring": {"single_selection_expression": '"nom"'},
                                        "filtering": {"layers_to_filter": '["routes_1"]'}}}
    assert parcelles.writes == [] and routes.writes == []  # nothing written: the project stays as it was


def test_a_legacy_name_is_moved_once_and_wins():
    layer = Layer("parcelles_1", {
        V("filterMate_exploring_single_selection_expression"): '"fid"',
        V("exploring_single_selection_expression"): '"nom"',
        V("exploring_is_tracking"): True,
        V("infos_layer_name"): "parcelles",
        "variableNames": ["filterMate_exploring_single_selection_expression", "exploring_single_selection_expression",
                          "exploring_is_tracking", "infos_layer_name"],
        "variableValues": ["x"],  # QGIS's own list
    })
    captured = layer_settings.capture_layer_settings([layer])
    assert captured == {"parcelles_1": {"exploring": {"single_selection_expression": '"nom"', "is_tracking": True}}}
    assert layer.props == {
        V("filterMate_exploring_single_selection_expression"): '"nom"',
        V("filterMate_exploring_is_tracking"): True,
        # QGIS pairs its names with its values by position: FilterMate's names stay
        "variableNames": ["filterMate_exploring_single_selection_expression", "exploring_single_selection_expression",
                          "exploring_is_tracking", "infos_layer_name", "filterMate_exploring_is_tracking"],
        "variableValues": ["x"],
    }
    layer.writes.clear()
    assert layer_settings.capture_layer_settings([layer]) == captured  # the next reading: the same, nothing moved
    assert layer.writes == []


def test_known_and_deleted_layers_are_left():
    known = Layer("known_1", {V("exploring_is_tracking"): True})
    deleted = Layer("gone_1", {V("filterMate_exploring_is_tracking"): True}, deleted=True)
    assert layer_settings.capture_layer_settings([known, deleted], known={"known_1": {}}) == {}
    assert known.writes == [] and V("exploring_is_tracking") in known.props


def test_no_layers():
    assert layer_settings.capture_layer_settings(None) == {}
    assert layer_settings.capture_layer_settings() == {}
