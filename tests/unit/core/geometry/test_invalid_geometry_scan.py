# -*- coding: utf-8 -*-
"""PERF 2026-09-12: ``layer_has_invalid_geometries`` stops at the first invalid geometry."""

from unittest.mock import MagicMock

import pytest

from core.geometry import geometry_safety


def _feature(valid=True, empty=False):
    feature = MagicMock()
    geometry = MagicMock()
    geometry.isNull.return_value = False
    geometry.isEmpty.return_value = empty
    geometry.isGeosValid.return_value = valid
    feature.geometry.return_value = geometry
    return feature


def _layer(features):
    layer = MagicMock()
    layer.getFeatures.return_value = iter(features)
    return layer


@pytest.mark.unit
class TestLayerHasInvalidGeometries:

    def test_clean_layer(self):
        assert geometry_safety.layer_has_invalid_geometries(_layer([_feature(), _feature()])) is False

    def test_stops_at_first_invalid(self):
        features = [_feature(), _feature(valid=False), _feature()]
        layer = _layer(features)
        assert geometry_safety.layer_has_invalid_geometries(layer) is True
        features[2].geometry.assert_not_called()

    def test_empty_geometries_are_skipped(self):
        assert geometry_safety.layer_has_invalid_geometries(_layer([_feature(empty=True)])) is False

    def test_max_features_bound(self):
        features = [_feature() for _ in range(5)] + [_feature(valid=False)]
        assert geometry_safety.layer_has_invalid_geometries(_layer(features), max_features=3) is False

    def test_scan_failure_assumes_invalid(self):
        layer = MagicMock()
        layer.getFeatures.side_effect = RuntimeError("provider gone")
        assert geometry_safety.layer_has_invalid_geometries(layer) is True

    def test_none_layer(self):
        assert geometry_safety.layer_has_invalid_geometries(None) is False
