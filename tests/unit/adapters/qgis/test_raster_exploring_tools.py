# -*- coding: utf-8 -*-
"""FilterMate 5 raster EXPLORING tools: range extent bounds and style link rescaling (pure parts)."""
import importlib
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_raster_tools_test"


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.domain", _ROOT / "core" / "domain"),
                       (".adapters", _ROOT / "adapters"), (".adapters.qgis", _ROOT / "adapters" / "qgis"),
                       (".adapters.qgis.coverage_layers", _ROOT / "adapters" / "qgis" / "coverage_layers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.adapters.qgis.coverage_layers.raster_adapter")


adapter = _load()


class TestRescale:
    def test_stops_follow_the_new_range(self):
        assert adapter.rescale_values([0.0, 50.0, 100.0], 0.0, 100.0, 200.0, 260.0) == [200.0, 230.0, 260.0]

    def test_flat_ramp_is_spread(self):
        assert adapter.rescale_values([5.0, 5.0, 5.0], 5.0, 5.0, 0.0, 10.0) == [0.0, 5.0, 10.0]


class TestMaskBounds:
    def test_bounds_of_true_cells(self):
        np = pytest.importorskip("numpy")
        mask = np.zeros((5, 6), dtype=bool)
        mask[1, 2] = mask[3, 4] = True
        assert adapter.mask_bounds(mask) == (1, 3, 2, 4)

    def test_empty_mask(self):
        np = pytest.importorskip("numpy")
        assert adapter.mask_bounds(np.zeros((3, 3), dtype=bool)) is None
