# -*- coding: utf-8 -*-
"""RenderUnit fallback chain (Qt6 scoped-enum fix of 2026-11-24, hardened 2026-11-26).

``Qgis.RenderUnit`` first, then the scoped ``QgsUnitTypes.RenderUnit.RenderMillimeters`` (the only
spelling Qt6 keeps), then the flat ``QgsUnitTypes.RenderMillimeters`` last: the 3.22 floor the plugin
supports must never see an AttributeError. All lookups are string-based, so the Qt6 enum scan stays green.
"""
import importlib
import pathlib
import sys
import types
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_render_unit_fallback_test"

_NEW = object()
_SCOPED = object()
_FLAT = object()


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.domain", _ROOT / "core" / "domain"),
                       (".core.agent", _ROOT / "core" / "agent"),
                       (".adapters", _ROOT / "adapters"), (".adapters.public_api", _ROOT / "adapters" / "public_api")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    operations = types.ModuleType(f"{_PKG}.adapters.public_api.operations")
    operations.layer_kind = operations.resolve_layer = lambda *args: None
    sys.modules[operations.__name__] = operations
    introspection = types.ModuleType(f"{_PKG}.adapters.public_api.introspection")
    introspection._is_web_service = lambda layer: False
    sys.modules[introspection.__name__] = introspection
    palettes = types.ModuleType(f"{_PKG}.core.agent.palettes")
    sys.modules[palettes.__name__] = palettes
    layer_style = importlib.import_module(f"{_PKG}.adapters.public_api.layer_style")
    style_design = importlib.import_module(f"{_PKG}.adapters.public_api.style_design")
    return layer_style, style_design


layer_style, style_design = _load()


@pytest.fixture(params=[layer_style._millimetres, style_design._mm], ids=["layer_style", "style_design"])
def unit_of(request):
    return request.param


def _fake_qgis(monkeypatch, qgis_names=(), unit_types_names=(), scoped_names=()):
    """A qgis.core whose Qgis / QgsUnitTypes expose exactly the given members."""
    qgis = SimpleNamespace(**{name: SimpleNamespace(Millimeters=_NEW) for name in qgis_names})
    scoped = SimpleNamespace(**{name: _SCOPED for name in scoped_names})
    members = dict(zip(unit_types_names, [scoped] * len(unit_types_names)))
    if "RenderMillimeters" in unit_types_names:
        members["RenderMillimeters"] = _FLAT
    fake_core = types.ModuleType("qgis.core")
    fake_core.Qgis = qgis
    fake_core.QgsUnitTypes = SimpleNamespace(**members)
    monkeypatch.setitem(sys.modules, "qgis.core", fake_core)


def test_new_qgis_render_unit_wins(unit_of, monkeypatch):
    _fake_qgis(monkeypatch, qgis_names=("RenderUnit",), unit_types_names=("RenderUnit", "RenderMillimeters"),
               scoped_names=("RenderMillimeters",))
    assert unit_of() is _NEW


def test_scoped_member_used_without_new_qgis(unit_of, monkeypatch):
    _fake_qgis(monkeypatch, unit_types_names=("RenderUnit", "RenderMillimeters"),
               scoped_names=("RenderMillimeters",))
    assert unit_of() is _SCOPED


def test_flat_member_is_the_last_resort(unit_of, monkeypatch):
    """The 3.22 floor: no scope anywhere, the flat spelling still resolves instead of raising."""
    _fake_qgis(monkeypatch, unit_types_names=("RenderMillimeters",))
    assert unit_of() is _FLAT
