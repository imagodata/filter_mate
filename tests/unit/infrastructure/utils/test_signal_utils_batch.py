# -*- coding: utf-8 -*-
"""
PERF 2026-09-12: batched layer-variable writes.

``safe_set_layer_variables_batch`` must run the crash-safety gate chain once
per layer, write only values that changed, and report (written, ok). 2026-11-24:
``variableNames`` is left alone (QGIS pairs it by position with its own list of
values: a name of FilterMate there gave a value of the user to another name). ``safe_set_layer_variable`` keeps its one-shot contract.

``signal_utils`` is loaded inside a private throw-away package so its
``from .validation_utils import …`` resolves without touching the shared
``filter_mate.*`` aliases other suites install (see issue #42).
"""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

_UTILS_DIR = Path(__file__).resolve().parents[4] / "infrastructure" / "utils"
_PKG = "fmtest_signal_utils_pkg"


def _load_signal_utils():
    if f"{_PKG}.signal_utils" in sys.modules:
        return sys.modules[f"{_PKG}.signal_utils"]
    pkg = types.ModuleType(_PKG)
    pkg.__path__ = [str(_UTILS_DIR)]
    pkg.__package__ = _PKG
    sys.modules[_PKG] = pkg
    spec = importlib.util.spec_from_file_location(f"{_PKG}.signal_utils", _UTILS_DIR / "signal_utils.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeLayer:
    """Minimal stand-in for QgsVectorLayer custom-property storage."""

    def __init__(self, valid=True):
        self._props = {}
        self._valid = valid
        self.set_calls = []

    def isValid(self):
        return self._valid

    def customProperty(self, key, default=None):
        return self._props.get(key, default)

    def setCustomProperty(self, key, value):
        self.set_calls.append((key, value))
        self._props[key] = value


class FakeProject:
    def __init__(self, layers):
        self._layers = layers

    def mapLayer(self, layer_id):
        return self._layers.get(layer_id)


@pytest.fixture
def signal_utils(monkeypatch):
    module = _load_signal_utils()
    # sip.isdeleted() raises TypeError on plain Python objects; the gates treat
    # that as "deleted", so disable sip for these pure-Python fakes.
    monkeypatch.setattr(module, "sip", None)
    monkeypatch.setattr(module, "IS_WINDOWS", False)
    monkeypatch.setattr(module, "is_qgis_alive", lambda: True)
    return module


@pytest.mark.unit
class TestSafeSetLayerVariablesBatch:

    def test_writes_every_new_variable_and_no_name(self, signal_utils):
        layer = FakeLayer()
        project = FakeProject({"L1": layer})
        variables = {"filterMate_infos_a": 1, "filterMate_exploring_b": "x", "filterMate_filtering_c": True}

        written, ok = signal_utils.safe_set_layer_variables_batch("L1", variables, project=project)

        assert (written, ok) == (3, True)
        assert layer.customProperty("variableValues/filterMate_infos_a") == 1
        assert layer.customProperty("variableValues/filterMate_exploring_b") == "x"
        assert layer.customProperty("variableValues/filterMate_filtering_c") is True
        assert [c for c in layer.set_calls if c[0] == "variableNames"] == []

    def test_unchanged_values_are_skipped(self, signal_utils):
        layer = FakeLayer()
        project = FakeProject({"L1": layer})
        variables = {"k1": 10, "k2": "v"}
        signal_utils.safe_set_layer_variables_batch("L1", variables, project=project)
        layer.set_calls.clear()

        written, ok = signal_utils.safe_set_layer_variables_batch("L1", variables, project=project)

        assert (written, ok) == (0, True)
        assert layer.set_calls == []

    def test_changed_value_is_written_without_touching_names(self, signal_utils):
        layer = FakeLayer()
        project = FakeProject({"L1": layer})
        signal_utils.safe_set_layer_variables_batch("L1", {"k1": 10, "k2": "v"}, project=project)
        layer.set_calls.clear()

        written, ok = signal_utils.safe_set_layer_variables_batch("L1", {"k1": 11, "k2": "v"}, project=project)

        assert (written, ok) == (1, True)
        assert layer.set_calls == [("variableValues/k1", 11)]

    def test_skip_unchanged_can_be_disabled(self, signal_utils):
        layer = FakeLayer()
        project = FakeProject({"L1": layer})
        signal_utils.safe_set_layer_variables_batch("L1", {"k1": 10}, project=project)

        written, ok = signal_utils.safe_set_layer_variables_batch(
            "L1", {"k1": 10}, project=project, skip_unchanged=False)

        assert (written, ok) == (1, True)

    def test_missing_or_invalid_layer(self, signal_utils):
        project = FakeProject({"bad": FakeLayer(valid=False)})
        assert signal_utils.safe_set_layer_variables_batch("nope", {"k": 1}, project=project) == (0, False)
        assert signal_utils.safe_set_layer_variables_batch("bad", {"k": 1}, project=project) == (0, False)

    def test_empty_batch_is_a_noop(self, signal_utils):
        assert signal_utils.safe_set_layer_variables_batch("L1", {}, project=FakeProject({})) == (0, True)

    def test_the_variables_of_the_user_are_left_alone(self, signal_utils):
        layer = FakeLayer()
        layer._props["variableNames"] = ["my_var"]
        layer._props["variableValues"] = ["hello"]
        project = FakeProject({"L1": layer})

        written, ok = signal_utils.safe_set_layer_variables_batch("L1", {"filterMate_exploring_b": True}, project=project)

        assert (written, ok) == (1, True)
        assert layer.customProperty("variableNames") == ["my_var"]
        assert layer.customProperty("variableValues") == ["hello"]


@pytest.mark.unit
class TestVariableValuesEqual:

    def test_semantics(self, signal_utils):
        eq = signal_utils._variable_values_equal
        assert eq(1, 1)
        assert eq(1, 1.0)          # numeric types interchangeable
        assert not eq("1", 1)      # stored as text, queued as int: rewrite to fix the type
        assert not eq(1.5, "1.5")
        assert eq(True, True)
        assert not eq(True, 1)     # bool never equals a number
        assert not eq("True", True)
        assert eq("a", "a")
        assert not eq("a", "b")
        assert eq([1, 2], [1, 2])


@pytest.mark.unit
class TestSafeSetLayerVariableStillWorks:

    def test_single_write_path(self, signal_utils):
        layer = FakeLayer()
        project = FakeProject({"L1": layer})

        assert signal_utils.safe_set_layer_variable("L1", "filterMate_infos_x", "val", project=project) is True

        assert layer.customProperty("variableValues/filterMate_infos_x") == "val"
        assert layer.customProperty("variableNames") is None

    def test_single_write_rejects_missing_layer(self, signal_utils):
        assert signal_utils.safe_set_layer_variable("ghost", "k", 1, project=FakeProject({})) is False
