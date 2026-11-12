# -*- coding: utf-8 -*-
"""The bars of a chart widget read from its layer: never more features than the limit, whatever the count says."""
import importlib
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_PKG = "fm_widget_charts_test"


class _Request:
    class Flag:
        NoGeometry = 1

    def __init__(self):
        self.limit = -1

    def setFlags(self, _flags):  # noqa: N802 - QGIS name
        return self

    def setSubsetOfAttributes(self, _attributes):  # noqa: N802 - QGIS name
        return self

    def setLimit(self, limit):  # noqa: N802 - QGIS name
        self.limit = limit
        return self


class _Layer:
    def __init__(self, values, count):
        self.values, self.count, self.read = values, count, 0

    def fields(self):
        return types.SimpleNamespace(lookupField=lambda name: 0 if name == "pop" else -1)

    def featureCount(self):  # noqa: N802 - QGIS name
        return self.count

    def getFeatures(self, request):  # noqa: N802 - QGIS name
        for number, value in enumerate(self.values):
            if 0 <= request.limit <= number:
                return
            self.read += 1
            yield types.SimpleNamespace(attribute=lambda _index, value=value: value)


@pytest.fixture
def chart_bars(monkeypatch):
    # The module alone, under a private package: the __init__ of adapters loads every backend.
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.agent", _ROOT / "core" / "agent"),
                       (".adapters", _ROOT / "adapters"), (".adapters.agent", _ROOT / "adapters" / "agent"),
                       (".adapters.public_api", None)):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)] if path else []
        monkeypatch.setitem(sys.modules, _PKG + name, package)
    introspection = types.ModuleType(_PKG + ".adapters.public_api.introspection")
    introspection.MAX_STAT_FEATURES = 5
    introspection._refuse_web_service = lambda layer: None
    monkeypatch.setitem(sys.modules, introspection.__name__, introspection)
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsFeatureRequest", _Request, raising=False)
    agent_widgets = importlib.import_module(_PKG + ".adapters.agent.agent_widgets")
    layers = {}
    monkeypatch.setattr(agent_widgets, "widget_layer", lambda widget: layers.get(widget["layer_id"]))

    def read(layer, mode="histogram"):
        layers["L1"] = layer
        return agent_widgets.chart_bars({"layer_id": "L1", "field": "pop", "mode": mode})
    return read


@pytest.mark.parametrize("count", [-1, -2])
def test_a_count_the_provider_does_not_know_reads_no_more_than_the_limit(chart_bars, count):
    layer = _Layer(list(range(1000)), count)
    assert chart_bars(layer) is None
    assert layer.read == 6  # the limit, and one more to know it is passed


def test_within_the_limit_the_bars_are_read(chart_bars):
    layer = _Layer([1, 2, 2, 3], -1)
    assert sum(bar["count"] for bar in chart_bars(layer)) == 4
    assert [bar["count"] for bar in chart_bars(_Layer(["a", "b", "a"], 3), mode="categories")] == [2, 1]


def test_a_known_count_beyond_the_limit_reads_nothing(chart_bars):
    layer = _Layer(list(range(10)), 10)
    assert chart_bars(layer) is None and layer.read == 0
