# -*- coding: utf-8 -*-
"""2026-11-12: the stretch of a raster style takes finite bounds, the minimum below the maximum.

NaN, Infinity and an inverted range were applied as given (the REST model now refuses them with a 422; the agent
tool reaches ``set_layer_style`` directly, so the function refuses them too).
"""
import importlib
import math
import pathlib
import sys
import types
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_layer_style_test"


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


class _Layer:
    def name(self):
        return "dem"

    def extent(self):
        return None

    def dataProvider(self):
        return SimpleNamespace(bandStatistics=lambda *args: SimpleNamespace(minimumValue=100.0, maximumValue=900.0))


@pytest.fixture(autouse=True)
def stats_flags(monkeypatch):
    core = sys.modules["qgis.core"]
    monkeypatch.setattr(core, "Qgis", SimpleNamespace(RasterBandStatistic=SimpleNamespace(All=255)), raising=False)


@pytest.mark.parametrize("minimum, maximum, message", [
    (math.nan, 10.0, "minimum must be a finite number"),
    (0.0, math.inf, "maximum must be a finite number"),
    (-math.inf, None, "minimum must be a finite number"),
    (10.0, 2.0, r"minimum \(10.0\) must be below maximum \(2.0\)"),
    (5.0, 5.0, "must be below"),
    (950.0, None, r"minimum \(950\) must be below maximum \(900\)"),   # the other bound read from the band
])
def test_bad_bounds_are_refused(minimum, maximum, message):
    with pytest.raises(ValueError, match=message):
        style._band_range(_Layer(), 1, minimum, maximum)


@pytest.mark.parametrize("minimum, maximum, expected", [
    (2.0, 10.0, (2.0, 10.0)),
    (None, None, (100.0, 900.0)),
    (300.0, None, (300.0, 900.0)),
])
def test_good_bounds(minimum, maximum, expected):
    assert style._band_range(_Layer(), 1, minimum, maximum) == expected
