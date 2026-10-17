# -*- coding: utf-8 -*-
"""The buffer type applies as soon as a buffer is active (2026-10-17).

In FilterMate 5 the buffer type switch is hidden (merged into the buffer
value row); ``has_buffer_type`` stayed False after a layer change and a
Flat / Square buffer came out Round (story 2, Muret noise).
"""
import importlib.util
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[4]


def _load(name, relative):
    spec = importlib.util.spec_from_file_location(name, PLUGIN_ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


buffer_builder = _load("fm_test_source_subset_buffer_builder", "core/services/source_subset_buffer_builder.py")


def _load_mockup():
    """ui/layout/mockup_layout.py with its sibling packages (as tests/unit/ui/layout/test_mockup_layout.py)."""
    import importlib
    package_name = "fm_test_buffer_type_pkg"
    for name, path in (("", PLUGIN_ROOT), (".ui", PLUGIN_ROOT / "ui"), (".ui.layout", PLUGIN_ROOT / "ui" / "layout"),
                       (".ui.styles", PLUGIN_ROOT / "ui" / "styles")):
        package = types.ModuleType(package_name + name)
        package.__path__ = [str(path)]
        sys.modules[package_name + name] = package
    return importlib.import_module(f"{package_name}.ui.layout.mockup_layout")


mockup = _load_mockup()


def _extract(**filtering):
    return buffer_builder.SourceSubsetBufferBuilder()._extract_buffer_type(filtering)


@pytest.mark.parametrize("filtering, expected_type, expected_segments", [
    # the hidden switch left False, a buffer active: the panel's type applies
    ({"has_buffer_value": True, "has_buffer_type": False, "buffer_type": "Flat", "buffer_segments": 8}, 1, 8),
    ({"has_buffer_value": True, "has_buffer_type": False, "buffer_type": "Square"}, 2, 5),
    ({"has_buffer_value": True, "has_buffer_type": True, "buffer_type": "Flat"}, 1, 5),
    # older layers / favorites with the switch on: unchanged
    ({"has_buffer_value": False, "has_buffer_type": True, "buffer_type": "Flat"}, 1, 5),
    # no buffer at all: default Round, 5 segments
    ({"has_buffer_value": False, "has_buffer_type": False, "buffer_type": "Flat"}, 0, 5),
])
def test_buffer_type_applies_with_an_active_buffer(filtering, expected_type, expected_segments):
    result = _extract(**filtering)
    assert result == {"type": expected_type, "segments": expected_segments}


def test_the_task_hands_the_end_cap_to_the_backends():
    source = (PLUGIN_ROOT / "core" / "tasks" / "filter_task.py").read_text(encoding="utf-8")
    assert "self.task_parameters['buffer_endcap_style'] = BUFFER_ENDCAP_STYLES.get(self.param_buffer_type, 'round')" in source
    assert "self.task_parameters['buffer_segments'] = self.param_buffer_segments" in source
    assert "BUFFER_ENDCAP_STYLES = {0: 'round', 1: 'flat', 2: 'square'}" in source


class _Signal:
    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def emit(self, *args):
        for slot in self.slots:
            slot(*args)


class _Button:
    def __init__(self, checked=False):
        self.checked = checked
        self.toggled = _Signal()

    def isChecked(self):
        return self.checked

    def setChecked(self, value):
        if value != self.checked:
            self.checked = value
            self.toggled.emit(value)


class _Combo:
    def __init__(self):
        self.currentIndexChanged = _Signal()


class _Spin:
    def __init__(self):
        self.valueChanged = _Signal()


def _linked(value_checked=False, type_checked=False):
    value, kind, combo, segments = _Button(value_checked), _Button(type_checked), _Combo(), _Spin()
    mockup.link_buffer_type_to_value(value, kind, combo, segments)
    return value, kind, combo, segments


def test_type_switch_follows_the_value_switch():
    value, kind, _, _ = _linked()
    value.setChecked(True)
    assert kind.isChecked()
    value.setChecked(False)
    assert not kind.isChecked()


def test_changing_the_type_with_an_active_buffer_turns_the_type_switch_on():
    value, kind, combo, segments = _linked(value_checked=True, type_checked=False)
    combo.currentIndexChanged.emit(1)  # Flat
    assert kind.isChecked()
    kind.checked = False
    segments.valueChanged.emit(8)
    assert kind.isChecked()


def test_changing_the_type_without_a_buffer_leaves_it_off():
    _, kind, combo, _ = _linked(value_checked=False, type_checked=False)
    combo.currentIndexChanged.emit(2)
    assert not kind.isChecked()
