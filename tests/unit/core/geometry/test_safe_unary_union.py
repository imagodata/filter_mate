# -*- coding: utf-8 -*-
"""
PERF 2026-09-12: ``safe_unary_union`` must use GEOS cascaded union
(``QgsGeometry.unaryUnion``) and only fall back to the quadratic
``combine()`` loop when the cascaded union fails or yields an invalid result.

The qgis package is mocked by the root conftest, so ``QgsGeometry`` is a
MagicMock class attribute we can steer per test.
"""

from unittest.mock import MagicMock, patch

import pytest

from core.geometry import geometry_safety


def _valid_geom(name="g"):
    geom = MagicMock(name=name)
    geom.isNull.return_value = False
    geom.isEmpty.return_value = False
    geom.isGeosValid.return_value = True
    return geom


@pytest.mark.unit
class TestSafeUnaryUnion:

    def test_single_geometry_returned_as_is(self):
        geom = _valid_geom()
        with patch.object(geometry_safety, "validate_geometry", return_value=True):
            assert geometry_safety.safe_unary_union([geom]) is geom

    def test_uses_cascaded_union_once(self):
        geoms = [_valid_geom(f"g{i}") for i in range(5)]
        union_result = _valid_geom("union")
        with patch.object(geometry_safety, "validate_geometry", return_value=True), \
                patch.object(geometry_safety, "QgsGeometry") as qgs_geometry:
            qgs_geometry.unaryUnion.return_value = union_result
            result = geometry_safety.safe_unary_union(geoms)

        assert result is union_result
        qgs_geometry.unaryUnion.assert_called_once_with(geoms)
        # No pairwise combine() when the cascaded union succeeds
        for geom in geoms:
            geom.combine.assert_not_called()

    def test_falls_back_to_iterative_combine_when_unary_union_raises(self):
        geoms = [_valid_geom(f"g{i}") for i in range(3)]
        combined = _valid_geom("combined")
        geoms[0].combine.return_value = combined
        combined.combine.return_value = combined

        with patch.object(geometry_safety, "validate_geometry", return_value=True), \
                patch.object(geometry_safety, "QgsGeometry") as qgs_geometry:
            qgs_geometry.unaryUnion.side_effect = RuntimeError("GEOS")
            result = geometry_safety.safe_unary_union(geoms)

        assert result is combined
        geoms[0].combine.assert_called_once_with(geoms[1])
        combined.combine.assert_called_once_with(geoms[2])

    def test_falls_back_when_unary_union_result_invalid(self):
        geoms = [_valid_geom("a"), _valid_geom("b")]
        bad_union = MagicMock(name="bad")
        combined = _valid_geom("combined")
        geoms[0].combine.return_value = combined

        def validate(geom):
            return geom is not bad_union

        with patch.object(geometry_safety, "validate_geometry", side_effect=validate), \
                patch.object(geometry_safety, "QgsGeometry") as qgs_geometry:
            qgs_geometry.unaryUnion.return_value = bad_union
            result = geometry_safety.safe_unary_union(geoms)

        assert result is combined

    def test_empty_and_all_invalid_inputs(self):
        with patch.object(geometry_safety, "validate_geometry", return_value=False):
            assert geometry_safety.safe_unary_union([]) is None
            assert geometry_safety.safe_unary_union([MagicMock(), MagicMock()]) is None
