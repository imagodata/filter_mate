# -*- coding: utf-8 -*-
"""Answers of the introspection tools.

Audit 2026-11-18: ``layer_statistics`` ranked its groups by number of features whatever was asked.

"Which commune has the largest built area?", grouped by commune with ``measure=area``, answered with the ten
communes holding the most buildings: when the true largest was not among them, only ``truncated`` said so.
The module is loaded for real under a synthetic package; layers are small stand-ins (see test_operations.py).
"""
import importlib
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_statistics_test"


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.domain", _ROOT / "core" / "domain"),
                       (".core.services", _ROOT / "core" / "services"), (".adapters", _ROOT / "adapters"),
                       (".adapters.public_api", _ROOT / "adapters" / "public_api"),
                       (".adapters.qgis", _ROOT / "adapters" / "qgis"),
                       (".adapters.qgis.coverage_layers", _ROOT / "adapters" / "qgis" / "coverage_layers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.adapters.public_api.introspection")


introspection = _load()


class _Field:
    def __init__(self, name, numeric):
        self._name, self._numeric = name, numeric

    def name(self):
        return self._name

    def isNumeric(self):
        return self._numeric


class _Fields:
    def __init__(self, *fields):
        self._fields = list(fields)

    def lookupField(self, name):
        return next((index for index, field in enumerate(self._fields) if field.name() == name), -1)

    def at(self, index):
        return self._fields[index]


class _Geometry:
    def __init__(self, size):
        self.size = size

    def isNull(self):
        return False


class _Feature:
    def __init__(self, commune, pop, size):
        self._attributes, self._geometry = [commune, pop], _Geometry(size)

    def attribute(self, index):
        return self._attributes[index]

    def geometry(self):
        return self._geometry


class _Layer:
    def __init__(self, features):
        self._features = features

    def name(self):
        return "buildings"

    def fields(self):
        return _Fields(_Field("commune", False), _Field("pop", True))

    def getFeatures(self, request):
        return iter(self._features)

    def selectedFeatureCount(self):
        return 0


@pytest.fixture
def buildings(monkeypatch):
    """Twelve communes: "big" has two huge buildings, the other eleven have three small ones each."""
    features = [_Feature("big", 1000, 500), _Feature("big", 900, 400)]
    for number in range(11):
        features.extend(_Feature(f"c{number:02d}", 10, 5) for _ in range(3))
    layer = _Layer(features)
    monkeypatch.setattr(introspection, "_vector_layer", lambda reference: layer)
    monkeypatch.setattr(introspection, "_refuse_web_service", lambda layer: None)
    monkeypatch.setattr(introspection, "features_to_read", lambda layer: len(features))
    monkeypatch.setattr(introspection, "_request", lambda *args: None)
    monkeypatch.setattr(introspection, "_measurer", lambda layer, measure: (lambda geometry: geometry.size, "m2", ""))
    return layer


def test_the_groups_are_ranked_by_the_measure_asked(buildings):
    answer = introspection.layer_statistics("buildings", group_by="commune", measure="area", limit=10)
    assert answer["ranked_by"] == "sum" and answer["truncated"] and answer["groups_total"] == 12
    assert answer["groups"][0]["value"] == "big" and answer["groups"][0]["sum"] == 900
    sums = [row["sum"] for row in answer["groups"]]
    assert sums == sorted(sums, reverse=True)


def test_the_groups_are_ranked_by_the_sum_of_a_numeric_field(buildings):
    answer = introspection.layer_statistics("buildings", "pop", group_by="commune", limit=3)
    assert answer["ranked_by"] == "sum" and answer["groups"][0]["value"] == "big"


def test_without_a_field_or_a_measure_the_groups_are_ranked_by_features(buildings):
    answer = introspection.layer_statistics("buildings", group_by="commune", limit=3)
    assert answer["ranked_by"] == "feature_count" and answer["groups"][0]["value"] != "big"
    assert answer["groups"][0]["feature_count"] == 3
    text = introspection.layer_statistics("buildings", "commune", group_by="commune", limit=3)
    assert text["ranked_by"] == "feature_count"


def test_a_crs_without_identifier_is_given_by_its_description():
    """Review 2026-11-18: authid() is "" for a CRS defined in the project: map_context gave no CRS, so a change of it
    could not be told to the model."""
    class Crs:
        def __init__(self, authid, description):
            self._authid, self._description = authid, description

        def authid(self):
            return self._authid

        def description(self):
            return self._description

    assert introspection._crs_label(Crs("EPSG:2154", "RGF93 v1 / Lambert-93")) == "EPSG:2154"
    assert introspection._crs_label(Crs("", "Custom Lambert")) == "Custom Lambert"
    assert introspection._crs_label(Crs("", "")) == ""
