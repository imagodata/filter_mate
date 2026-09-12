# -*- coding: utf-8 -*-
"""
PERF 2026-09-12: FilterMate scratch layers carry a custom-property marker so
the plugin's layersAdded / layersWillBeRemoved handlers ignore them.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[4] / "infrastructure" / "utils" / "validation_utils.py"


def _load():
    name = "fmtest_validation_utils"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FakeLayer:
    def __init__(self):
        self.props = {}

    def setCustomProperty(self, key, value):
        self.props[key] = value

    def customProperty(self, key, default=None):
        return self.props.get(key, default)


class DeletedLayer:
    def customProperty(self, key, default=None):
        raise RuntimeError("wrapped C/C++ object has been deleted")

    def setCustomProperty(self, key, value):
        raise RuntimeError("wrapped C/C++ object has been deleted")


class FakeProject:
    def __init__(self, layers):
        self._layers = layers

    def mapLayer(self, layer_id):
        return self._layers.get(layer_id)


@pytest.mark.unit
class TestTempLayerMarker:

    def test_mark_then_detect(self):
        vu = _load()
        layer = FakeLayer()
        assert vu.is_filtermate_temp_layer(layer) is False
        assert vu.mark_filtermate_temp_layer(layer) is True
        assert vu.is_filtermate_temp_layer(layer) is True
        assert layer.props == {vu.FILTERMATE_TEMP_LAYER_PROPERTY: True}

    def test_string_values_from_project_files(self):
        vu = _load()
        layer = FakeLayer()
        layer.props[vu.FILTERMATE_TEMP_LAYER_PROPERTY] = "true"
        assert vu.is_filtermate_temp_layer(layer) is True
        layer.props[vu.FILTERMATE_TEMP_LAYER_PROPERTY] = "false"
        assert vu.is_filtermate_temp_layer(layer) is False

    def test_deleted_or_missing_layer(self):
        vu = _load()
        assert vu.is_filtermate_temp_layer(None) is False
        assert vu.is_filtermate_temp_layer(DeletedLayer()) is False
        assert vu.mark_filtermate_temp_layer(DeletedLayer()) is False

    def test_lookup_by_id(self):
        vu = _load()
        temp, normal = FakeLayer(), FakeLayer()
        vu.mark_filtermate_temp_layer(temp)
        project = FakeProject({"t": temp, "n": normal})
        assert vu.is_filtermate_temp_layer_id("t", project=project) is True
        assert vu.is_filtermate_temp_layer_id("n", project=project) is False
        assert vu.is_filtermate_temp_layer_id("ghost", project=project) is False
        assert vu.is_filtermate_temp_layer_id("", project=project) is False
