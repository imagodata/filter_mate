# -*- coding: utf-8 -*-
"""Defensive reading of a point cloud layer and subset application.

``adapters/qgis/point_cloud_layer_adapter.py`` is loaded by path under a
private synthetic package; the WP-A domain dataclasses it imports are
stubbed with contract-shaped frozen dataclasses so this suite does not
depend on the real domain module. Layers are plain Python fakes.
"""
import importlib.util
import logging
import math
import os
import sys
import types
from dataclasses import dataclass
from typing import Optional, Tuple

import pytest

_PKG = "filter_mate_pc_adp"
_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


@dataclass(frozen=True)
class _AttributeSummary:
    name: str
    minimum: Optional[float] = None
    maximum: Optional[float] = None


@dataclass(frozen=True)
class _LayerSummary:
    layer_id: str
    layer_name: str
    provider: str = ""
    point_count: int = -1
    attributes: Tuple[str, ...] = ()
    classes: Tuple[Tuple[int, int], ...] = ()
    ranges: Tuple[_AttributeSummary, ...] = ()
    statistics_available: bool = False
    current_subset: str = ""

    def has_attribute(self, name):
        return name in self.attributes

    @property
    def class_codes(self):
        return tuple(code for code, _ in self.classes)

    def range_of(self, name):
        for item in self.ranges:
            if item.name == name:
                return item
        return None


def _install_package() -> None:
    if _PKG in sys.modules:
        return

    root = types.ModuleType(_PKG)
    root.__path__ = [_PROJECT_ROOT]
    sys.modules[_PKG] = root
    for sub in ("adapters", "adapters.qgis", "core", "core.domain"):
        full = f"{_PKG}.{sub}"
        mod = types.ModuleType(full)
        mod.__path__ = [os.path.join(_PROJECT_ROOT, *sub.split("."))]
        sys.modules[full] = mod

    criteria_mod = types.ModuleType(f"{_PKG}.core.domain.point_cloud_filter_criteria")
    criteria_mod.PointCloudAttributeSummary = _AttributeSummary
    criteria_mod.PointCloudLayerSummary = _LayerSummary
    sys.modules[f"{_PKG}.core.domain.point_cloud_filter_criteria"] = criteria_mod

    full = f"{_PKG}.adapters.qgis.point_cloud_layer_adapter"
    path = os.path.join(_PROJECT_ROOT, "adapters", "qgis", "point_cloud_layer_adapter.py")
    spec = importlib.util.spec_from_file_location(full, path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = f"{_PKG}.adapters.qgis"
    sys.modules[full] = mod
    spec.loader.exec_module(mod)


_install_package()
adapter = sys.modules[f"{_PKG}.adapters.qgis.point_cloud_layer_adapter"]


class _Attribute:
    def __init__(self, name):
        self._name = name

    def name(self):
        return self._name


class _AttributeCollection:
    def __init__(self, names):
        self._names = names

    def attributes(self):
        return [_Attribute(n) for n in self._names]


class _Stats:
    def __init__(self, classes=None, available=None, minimums=None, maximums=None, sampled=0,
                 classes_raises=False, available_raises=False, range_raises=False):
        self._classes = classes
        self._available = available
        self._min = minimums or {}
        self._max = maximums or {}
        self._sampled = sampled
        self._classes_raises = classes_raises
        self._available_raises = available_raises
        self._range_raises = range_raises

    def classesOf(self, attribute):
        if self._classes_raises:
            raise RuntimeError("stats not ready")
        return dict(self._classes or {})

    def availableClasses(self, attribute):
        if self._available_raises:
            raise RuntimeError("stats not ready")
        return list(self._available or [])

    def minimum(self, attribute):
        if self._range_raises:
            raise RuntimeError("no stats")
        return self._min.get(attribute, float("nan"))

    def maximum(self, attribute):
        if self._range_raises:
            raise RuntimeError("no stats")
        return self._max.get(attribute, float("nan"))

    def sampledPointsCount(self):
        return self._sampled


class _Layer:
    """Duck-typed ``QgsPointCloudLayer`` fake; ``None`` stats means no ``statistics`` attribute."""

    def __init__(self, layer_id="pc1", name="tile.copc.laz", provider="copc", point_count=1_000_000,
                 attributes=("X", "Y", "Z", "Classification", "Intensity"), stats=None,
                 subset="", set_result=True, set_raises=False, repaint_raises=False,
                 stats_raises=False, attributes_raise=False, count_raises=False, subset_raises=False):
        self._id = layer_id
        self._name = name
        self._provider = provider
        self._point_count = point_count
        self._attributes = attributes
        self._stats = stats
        self._subset = subset
        self._set_result = set_result
        self._set_raises = set_raises
        self._repaint_raises = repaint_raises
        self._attributes_raise = attributes_raise
        self._count_raises = count_raises
        self._subset_raises = subset_raises
        self.applied = []
        self.repaints = 0
        if stats is not None or stats_raises:
            self._stats_raises = stats_raises
            self.statistics = self._statistics

    def id(self):
        return self._id

    def name(self):
        return self._name

    def providerType(self):
        return self._provider

    def pointCount(self):
        if self._count_raises:
            raise RuntimeError("index not loaded")
        return self._point_count

    def attributes(self):
        if self._attributes_raise:
            raise RuntimeError("no index")
        return _AttributeCollection(self._attributes)

    def _statistics(self):
        if self._stats_raises:
            raise RuntimeError("statistics failed")
        return self._stats

    def subsetString(self):
        if self._subset_raises:
            raise RuntimeError("gone")
        return self._subset

    def setSubsetString(self, subset):
        if self._set_raises:
            raise RuntimeError("provider rejected")
        self.applied.append(subset)
        if self._set_result:
            self._subset = subset
        return self._set_result

    def triggerRepaint(self):
        if self._repaint_raises:
            raise RuntimeError("canvas gone")
        self.repaints += 1


class TestReadSummaryBasics:
    def test_identity_and_counts(self):
        summary = adapter.read_point_cloud_summary(_Layer(subset="Classification = 2"))
        assert summary.layer_id == "pc1"
        assert summary.layer_name == "tile.copc.laz"
        assert summary.provider == "copc"
        assert summary.point_count == 1_000_000
        assert summary.current_subset == "Classification = 2"
        assert summary.attributes == ("X", "Y", "Z", "Classification", "Intensity")
        assert summary.has_attribute("Z") and not summary.has_attribute("GpsTime")

    def test_no_statistics_method(self):
        summary = adapter.read_point_cloud_summary(_Layer())
        assert summary.classes == ()
        assert summary.ranges == ()
        assert summary.statistics_available is False

    def test_range_attributes_constant(self):
        assert adapter.POINT_CLOUD_RANGE_ATTRIBUTES == ("Z", "Intensity", "ReturnNumber", "NumberOfReturns", "GpsTime")


class TestReadSummaryClasses:
    def test_classes_of_sorted_by_code_with_counts(self):
        stats = _Stats(classes={6: 50, 2: 100, 1: 3})
        summary = adapter.read_point_cloud_summary(_Layer(stats=stats))
        assert summary.classes == ((1, 3), (2, 100), (6, 50))
        assert summary.class_codes == (1, 2, 6)
        assert summary.statistics_available is True

    def test_available_classes_fallback_with_unknown_counts(self):
        stats = _Stats(classes={}, available=[6, 2, 2])
        summary = adapter.read_point_cloud_summary(_Layer(stats=stats))
        assert summary.classes == ((2, -1), (6, -1))
        assert summary.statistics_available is True

    def test_classes_of_raising_falls_back(self):
        stats = _Stats(classes_raises=True, available=[2])
        summary = adapter.read_point_cloud_summary(_Layer(stats=stats))
        assert summary.classes == ((2, -1),)

    def test_both_class_accessors_raising_gives_empty(self):
        stats = _Stats(classes_raises=True, available_raises=True)
        summary = adapter.read_point_cloud_summary(_Layer(stats=stats))
        assert summary.classes == ()
        assert summary.statistics_available is False

    def test_float_codes_and_garbage_entries(self):
        stats = _Stats(classes={2.0: 10.0, "x": 5, -1: 7, 6: None})
        summary = adapter.read_point_cloud_summary(_Layer(stats=stats))
        assert summary.classes == ((2, 10), (6, -1))

    def test_stats_without_class_accessors(self):
        summary = adapter.read_point_cloud_summary(_Layer(stats=types.SimpleNamespace(sampledPointsCount=lambda: 10)))
        assert summary.classes == ()
        assert summary.statistics_available is True

    def test_sampled_points_only_marks_statistics_available(self):
        summary = adapter.read_point_cloud_summary(_Layer(stats=_Stats(sampled=500)))
        assert summary.classes == ()
        assert summary.statistics_available is True

    def test_sampled_points_zero_without_classes(self):
        summary = adapter.read_point_cloud_summary(_Layer(stats=_Stats(sampled=0)))
        assert summary.statistics_available is False


class TestReadSummaryRanges:
    def test_ranges_only_for_present_standard_attributes(self):
        stats = _Stats(minimums={"Z": 1.5, "Intensity": 0, "ReturnNumber": 1},
                       maximums={"Z": 250.0, "Intensity": 65535, "ReturnNumber": 5})
        summary = adapter.read_point_cloud_summary(_Layer(stats=stats))
        assert [r.name for r in summary.ranges] == ["Z", "Intensity"]
        assert summary.range_of("Z") == _AttributeSummary("Z", 1.5, 250.0)
        assert summary.range_of("Intensity") == _AttributeSummary("Intensity", 0.0, 65535.0)
        assert summary.range_of("ReturnNumber") is None

    def test_ranges_follow_constant_order(self):
        stats = _Stats(minimums={"GpsTime": 1.0, "Z": 2.0}, maximums={"GpsTime": 9.0, "Z": 8.0})
        layer = _Layer(attributes=("GpsTime", "NumberOfReturns", "Z"), stats=stats)
        summary = adapter.read_point_cloud_summary(layer)
        assert [r.name for r in summary.ranges] == ["Z", "NumberOfReturns", "GpsTime"]

    def test_nan_none_and_infinite_bounds_become_none(self):
        stats = _Stats(minimums={"Z": float("nan"), "Intensity": None},
                       maximums={"Z": float("inf"), "Intensity": "not a number"})
        summary = adapter.read_point_cloud_summary(_Layer(stats=stats))
        assert summary.range_of("Z") == _AttributeSummary("Z", None, None)
        assert summary.range_of("Intensity") == _AttributeSummary("Intensity", None, None)

    def test_range_accessors_raising(self):
        summary = adapter.read_point_cloud_summary(_Layer(stats=_Stats(range_raises=True)))
        assert summary.range_of("Z") == _AttributeSummary("Z", None, None)

    def test_stats_without_range_accessors(self):
        stats = types.SimpleNamespace(classesOf=lambda a: {2: 1})
        summary = adapter.read_point_cloud_summary(_Layer(stats=stats))
        assert summary.range_of("Z") == _AttributeSummary("Z", None, None)
        assert summary.classes == ((2, 1),)

    def test_no_ranges_without_stats_object(self):
        summary = adapter.read_point_cloud_summary(_Layer(stats_raises=True))
        assert summary.ranges == ()


class TestReadSummaryDefensive:
    def test_statistics_raising(self):
        summary = adapter.read_point_cloud_summary(_Layer(stats_raises=True))
        assert summary.layer_id == "pc1"
        assert summary.classes == ()
        assert summary.statistics_available is False

    def test_attributes_raising(self):
        summary = adapter.read_point_cloud_summary(_Layer(attributes_raise=True, stats=_Stats(minimums={"Z": 1})))
        assert summary.attributes == ()
        assert summary.ranges == ()

    def test_attribute_collection_without_attributes_method(self):
        layer = _Layer()
        layer.attributes = lambda: [_Attribute("Z"), _Attribute("")]
        assert adapter.read_point_cloud_summary(layer).attributes == ("Z",)

    def test_point_count_raising_or_invalid(self):
        assert adapter.read_point_cloud_summary(_Layer(count_raises=True)).point_count == -1
        assert adapter.read_point_cloud_summary(_Layer(point_count="lots")).point_count == -1
        assert adapter.read_point_cloud_summary(_Layer(point_count=True)).point_count == -1
        assert adapter.read_point_cloud_summary(_Layer(point_count=12.0)).point_count == 12

    def test_subset_string_raising_or_none(self):
        assert adapter.read_point_cloud_summary(_Layer(subset_raises=True)).current_subset == ""
        assert adapter.read_point_cloud_summary(_Layer(subset=None)).current_subset == ""

    def test_plain_object_and_none(self):
        for layer in (object(), None, 42):
            summary = adapter.read_point_cloud_summary(layer)
            assert summary.layer_id == ""
            assert summary.layer_name == ""
            assert summary.point_count == -1
            assert summary.attributes == ()
            assert summary.statistics_available is False

    def test_layer_whose_every_method_raises(self):
        class _Broken:
            def __getattr__(self, name):
                def boom(*args, **kwargs):
                    raise RuntimeError(name)
                return boom

        summary = adapter.read_point_cloud_summary(_Broken())
        assert summary.layer_id == ""
        assert summary.classes == ()
        assert summary.ranges == ()


class TestApplySubset:
    def test_success_applies_and_repaints(self, caplog):
        layer = _Layer()
        with caplog.at_level(logging.INFO, logger=adapter.__name__):
            assert adapter.apply_point_cloud_subset(layer, "Classification = 2") is True
        assert layer.applied == ["Classification = 2"]
        assert layer.repaints == 1
        assert any("[PC] subset applied" in record.message for record in caplog.records)

    def test_empty_and_none_clear_the_filter(self):
        layer = _Layer(subset="Z > 1")
        assert adapter.apply_point_cloud_subset(layer, "") is True
        assert adapter.apply_point_cloud_subset(layer, None) is True
        assert layer.applied == ["", ""]
        assert layer.subsetString() == ""

    def test_provider_rejection_returns_false(self, caplog):
        layer = _Layer(set_result=False)
        with caplog.at_level(logging.WARNING, logger=adapter.__name__):
            assert adapter.apply_point_cloud_subset(layer, "Bogus = 1") is False
        assert layer.repaints == 0
        assert any("rejected" in record.message for record in caplog.records)

    def test_exception_returns_false(self, caplog):
        layer = _Layer(set_raises=True)
        with caplog.at_level(logging.WARNING, logger=adapter.__name__):
            assert adapter.apply_point_cloud_subset(layer, "Z > 1") is False
        assert any("setSubsetString failed" in record.message for record in caplog.records)

    def test_repaint_failure_does_not_fail_apply(self):
        layer = _Layer(repaint_raises=True)
        assert adapter.apply_point_cloud_subset(layer, "Z > 1") is True
        assert layer.applied == ["Z > 1"]

    def test_none_return_from_provider_is_failure(self):
        layer = _Layer(set_result=None)
        assert adapter.apply_point_cloud_subset(layer, "Z > 1") is False

    def test_layer_without_set_subset_string(self):
        assert adapter.apply_point_cloud_subset(object(), "Z > 1") is False
        assert adapter.apply_point_cloud_subset(None, "Z > 1") is False


class TestGetSubset:
    def test_returns_current_subset(self):
        assert adapter.get_point_cloud_subset(_Layer(subset="Z >= 10 AND Z <= 150")) == "Z >= 10 AND Z <= 150"

    def test_empty_when_unavailable(self):
        assert adapter.get_point_cloud_subset(_Layer(subset_raises=True)) == ""
        assert adapter.get_point_cloud_subset(_Layer(subset=None)) == ""
        assert adapter.get_point_cloud_subset(object()) == ""
        assert adapter.get_point_cloud_subset(None) == ""


class TestHelpers:
    @pytest.mark.parametrize("value, expected", [
        (None, None), (True, None), (float("nan"), None), (float("-inf"), None),
        ("abc", None), (3, 3.0), ("2.5", 2.5), (0, 0.0),
    ])
    def test_to_float(self, value, expected):
        result = adapter._to_float(value)
        assert result == expected
        assert result is None or not math.isnan(result)

    @pytest.mark.parametrize("value, expected", [
        (None, -1), (True, -1), ("x", -1), (7, 7), (7.9, 7), ("12", 12),
    ])
    def test_to_int(self, value, expected):
        assert adapter._to_int(value) == expected
