# -*- coding: utf-8 -*-
"""
Point cloud layers (QgsPointCloudLayer) can reach safe_set_subset_string through
the undo/redo and public API paths. They expose setSubsetString() and pointCount()
but no featureCount(): the diagnostic f-strings must not raise on them, and the
vector behaviour must stay unchanged.

Module tested: infrastructure.database.sql_utils
"""
import logging

import pytest

from infrastructure.database import sql_utils


class _Records(logging.Handler):
    """Collects log records straight from the module logger (propagation-independent)."""

    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


@pytest.fixture
def records():
    handler = _Records()
    previous_level = sql_utils.logger.level
    sql_utils.logger.setLevel(logging.DEBUG)
    sql_utils.logger.addHandler(handler)
    try:
        yield handler.messages
    finally:
        sql_utils.logger.removeHandler(handler)
        sql_utils.logger.setLevel(previous_level)


class _FakePointCloudLayer:
    """Mimics the QgsPointCloudLayer surface: no featureCount(), no fields()."""

    def __init__(self, result=True, raise_on_set=None):
        self._subset = ""
        self._result = result
        self._raise = raise_on_set
        self.calls = []

    def name(self):
        return "lidar_tile"

    def providerType(self):
        return "copc"

    def source(self):
        return "/data/tile.copc.laz"

    def isValid(self):
        return True

    def pointCount(self):
        return 1234567

    def subsetString(self):
        return self._subset

    def dataProvider(self):
        return None

    def setSubsetString(self, expression):
        self.calls.append(expression)
        if self._raise is not None:
            raise self._raise
        if self._result:
            self._subset = expression
        return self._result


class _FakeVectorLayer:
    """Minimal vector layer: featureCount() present, non-postgres provider."""

    def __init__(self, result=True):
        self._subset = ""
        self._result = result
        self.calls = []

    def name(self):
        return "roads"

    def providerType(self):
        return "ogr"

    def source(self):
        return "/data/roads.gpkg|layername=roads"

    def isValid(self):
        return True

    def featureCount(self):
        return 10

    def subsetString(self):
        return self._subset

    def dataProvider(self):
        return None

    def setSubsetString(self, expression):
        self.calls.append(expression)
        if self._result:
            self._subset = expression
        return self._result


class _NoCountLayer:
    """Layer-like object without any count and without setSubsetString()."""

    def name(self):
        return "no_count"


class _BrokenCountLayer:
    def featureCount(self):
        raise RuntimeError("wrapped C/C++ object has been deleted")


@pytest.mark.unit
class TestLayerCountLabel:

    def test_vector_layer_reports_features(self):
        assert sql_utils._layer_count_label(_FakeVectorLayer()) == "10 features"

    def test_point_cloud_layer_reports_points(self):
        assert sql_utils._layer_count_label(_FakePointCloudLayer()) == "1234567 points"

    def test_layer_without_any_count_reports_na(self):
        assert sql_utils._layer_count_label(_NoCountLayer()) == "n/a"

    def test_failing_count_reports_na(self):
        assert sql_utils._layer_count_label(_BrokenCountLayer()) == "n/a"

    def test_none_layer_reports_na(self):
        assert sql_utils._layer_count_label(None) == "n/a"


@pytest.mark.unit
class TestSafeSetSubsetStringPointCloud:

    def test_success_applies_expression_verbatim(self, records):
        layer = _FakePointCloudLayer()
        expression = "Classification IN (2, 6) AND Z >= 10 AND Z <= 150"

        assert sql_utils.safe_set_subset_string(layer, expression) is True

        assert layer.calls == [expression]
        assert layer.subsetString() == expression
        assert any("1234567 points after filter" in m for m in records)
        assert not any("features after filter" in m for m in records)

    def test_empty_expression_clears_the_filter(self):
        layer = _FakePointCloudLayer()
        layer._subset = "Classification = 2"

        assert sql_utils.safe_set_subset_string(layer, "") is True

        assert layer.calls == [""]
        assert layer.subsetString() == ""

    def test_failure_diagnostics_do_not_raise(self, records):
        layer = _FakePointCloudLayer(result=False)

        assert sql_utils.safe_set_subset_string(layer, "Intensity > 100") is False

        assert layer.calls == ["Intensity > 100"]
        assert any("Count before: 1234567 points" in m for m in records)
        assert not any(m.startswith("Error setting subset string") for m in records)

    def test_exception_in_set_subset_string_returns_false(self, records):
        layer = _FakePointCloudLayer(raise_on_set=RuntimeError("provider gone"))

        assert sql_utils.safe_set_subset_string(layer, "ReturnNumber = 1") is False

        assert any(m.startswith("Error setting subset string on layer lidar_tile") for m in records)

    def test_layer_without_set_subset_string_is_rejected(self):
        assert sql_utils.safe_set_subset_string(_NoCountLayer(), "Z > 1") is False


@pytest.mark.unit
class TestSafeSetSubsetStringVectorUnchanged:

    def test_vector_success_still_reports_features(self, records):
        layer = _FakeVectorLayer()

        assert sql_utils.safe_set_subset_string(layer, '"fid" IN (1, 2, 3)') is True

        assert layer.calls == ['"fid" IN (1, 2, 3)']
        assert any("10 features after filter" in m for m in records)

    def test_vector_failure_still_reports_feature_count(self, records):
        layer = _FakeVectorLayer(result=False)

        assert sql_utils.safe_set_subset_string(layer, '"fid" IN (1)') is False

        assert any("Count before: 10 features" in m for m in records)
