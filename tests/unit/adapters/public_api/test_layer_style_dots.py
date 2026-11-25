# -*- coding: utf-8 -*-
"""2026-11-24: dot_density with too many dots per polygon.

Shared, the refusal names the per_dot the model gave; unshared, there is no refusal at all: refusing would be an
oracle on the largest value of the field (a dichotomy finds it), and the expression caps the dots at MAX_DOTS
anyway. The answer already hides a derived per_dot (set_layer_style says to give per_dot).
"""
import importlib
import pathlib
import sys
import types
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_layer_style_dots_test"


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.domain", _ROOT / "core" / "domain"),
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
    return importlib.import_module(f"{_PKG}.adapters.public_api.layer_style")


style = _load()


class _Fields:
    def lookupField(self, name):
        return 0

    def at(self, index):
        return SimpleNamespace(isNumeric=lambda: True, name=lambda: "pop")


class _Polygons:
    def name(self):
        return "communes"

    def wkbType(self):
        return 6

    def fields(self):
        return _Fields()

    def minimumValue(self, index):
        return 0.0

    def maximumValue(self, index):
        return 1000000.0


@pytest.fixture(autouse=True)
def polygon_stubs(monkeypatch):
    monkeypatch.setattr(style, "_read_values_guard", lambda *args, **kwargs: None)
    core = sys.modules["qgis.core"]
    kinds = SimpleNamespace(PointGeometry="point", LineGeometry="line", PolygonGeometry="polygon")
    monkeypatch.setattr(core, "QgsWkbTypes",
                        SimpleNamespace(geometryType=lambda wkb: "polygon", GeometryType=kinds), raising=False)


def test_shared_too_many_dots_is_refused():
    with pytest.raises(ValueError, match="puts more than 2000 dots"):
        style._dot_density(_Polygons(), "pop", None, 100.0, None)


def test_unshared_too_many_dots_renders_capped_without_a_refusal():
    _renderer, told = style._dot_density(_Polygons(), "pop", None, 100.0, None, share_values=False)
    assert told == 100.0  # the per_dot the caller gave comes back, as it knows it


def test_unshared_derived_per_dot_is_used_but_never_refused():
    _renderer, told = style._dot_density(_Polygons(), "pop", None, None, None, share_values=False)
    assert told == style._nice(1000000.0 / style.DOTS_IN_LARGEST)
