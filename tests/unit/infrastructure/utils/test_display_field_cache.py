# -*- coding: utf-8 -*-
"""
PERF 2026-09-12: ``get_best_display_field`` is memoised per
(layer id, field names, subset string) for a short TTL so a layer change no
longer re-samples every candidate field on the GUI thread.
"""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

_UTILS_DIR = Path(__file__).resolve().parents[4] / "infrastructure" / "utils"
_PKG = "fmtest_layer_utils_pkg"


def _load_layer_utils():
    if f"{_PKG}.layer_utils" in sys.modules:
        return sys.modules[f"{_PKG}.layer_utils"]
    pkg = types.ModuleType(_PKG)
    pkg.__path__ = [str(_UTILS_DIR)]
    pkg.__package__ = _PKG
    sys.modules[_PKG] = pkg
    spec = importlib.util.spec_from_file_location(f"{_PKG}.layer_utils", _UTILS_DIR / "layer_utils.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeField:
    def __init__(self, name):
        self._name = name

    def name(self):
        return self._name


class FakeLayer:
    def __init__(self, layer_id, field_names, subset=""):
        self._id = layer_id
        self._fields = [FakeField(n) for n in field_names]
        self._subset = subset

    def id(self):
        return self._id

    def fields(self):
        return list(self._fields)

    def subsetString(self):
        return self._subset

    def isValid(self):
        return True


@pytest.fixture
def layer_utils(monkeypatch):
    module = _load_layer_utils()
    module.clear_display_field_cache()
    calls = []

    def fake_compute(layer, sample_size=10, use_value_relations=True):
        calls.append(layer.id())
        return f"best_of_{layer.id()}"

    monkeypatch.setattr(module, "_compute_best_display_field", fake_compute)
    module._test_calls = calls
    yield module
    module.clear_display_field_cache()


@pytest.mark.unit
class TestDisplayFieldCache:

    def test_second_call_hits_cache(self, layer_utils):
        layer = FakeLayer("A", ["id", "nom"])
        assert layer_utils.get_best_display_field(layer) == "best_of_A"
        assert layer_utils.get_best_display_field(layer) == "best_of_A"
        assert layer_utils._test_calls == ["A"]

    def test_subset_change_recomputes(self, layer_utils):
        layer_utils.get_best_display_field(FakeLayer("A", ["id", "nom"], subset=""))
        layer_utils.get_best_display_field(FakeLayer("A", ["id", "nom"], subset='"id" > 5'))
        assert layer_utils._test_calls == ["A", "A"]

    def test_field_change_recomputes(self, layer_utils):
        layer_utils.get_best_display_field(FakeLayer("A", ["id", "nom"]))
        layer_utils.get_best_display_field(FakeLayer("A", ["id", "nom", "label"]))
        assert layer_utils._test_calls == ["A", "A"]

    def test_parameters_are_part_of_the_key(self, layer_utils):
        layer = FakeLayer("A", ["id"])
        layer_utils.get_best_display_field(layer, sample_size=10)
        layer_utils.get_best_display_field(layer, sample_size=3)
        layer_utils.get_best_display_field(layer, sample_size=3, use_value_relations=False)
        assert len(layer_utils._test_calls) == 3

    def test_clear_for_one_layer(self, layer_utils):
        layer_utils.get_best_display_field(FakeLayer("A", ["id"]))
        layer_utils.get_best_display_field(FakeLayer("B", ["id"]))
        assert layer_utils.clear_display_field_cache("A") == 1
        layer_utils.get_best_display_field(FakeLayer("A", ["id"]))
        layer_utils.get_best_display_field(FakeLayer("B", ["id"]))
        assert layer_utils._test_calls == ["A", "B", "A"]

    def test_ttl_expiry(self, layer_utils, monkeypatch):
        monkeypatch.setattr(layer_utils, "_DISPLAY_FIELD_CACHE_TTL_SECONDS", 0.0)
        layer = FakeLayer("A", ["id"])
        layer_utils.get_best_display_field(layer)
        layer_utils.get_best_display_field(layer)
        assert layer_utils._test_calls == ["A", "A"]

    def test_uncacheable_layer_still_computes(self, layer_utils):
        class Broken(FakeLayer):
            def fields(self):
                raise RuntimeError("wrapped C++ object deleted")

        layer = Broken("Z", ["id"])
        assert layer_utils.get_best_display_field(layer) == "best_of_Z"
        assert layer_utils.get_best_display_field(layer) == "best_of_Z"
        assert layer_utils._test_calls == ["Z", "Z"]

    def test_bounded_size(self, layer_utils, monkeypatch):
        monkeypatch.setattr(layer_utils, "_DISPLAY_FIELD_CACHE_MAX_ENTRIES", 3)
        for i in range(6):
            layer_utils.get_best_display_field(FakeLayer(f"L{i}", ["id"]))
        assert len(layer_utils._DISPLAY_FIELD_CACHE) == 3
