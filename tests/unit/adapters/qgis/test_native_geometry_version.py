# -*- coding: utf-8 -*-
"""The geometric functions written natively, by version of QGIS (``adapters/qgis/native_filter_translation.py``).

2026-11-13: before QGIS 3.34 the bounds of an empty line, polygon or collection are 0 (the rectangle of an empty
geometry was 0,0,0,0 until ``QgsRectangle.setNull``), so ``x_min($geometry) < 100`` keeps such a feature, where
the source answers NULL and leaves it out. The functions were compared with QGIS 3.44 and 4.x only
(``tests/qgis_headless/check_native_translation.py``): an older version leaves them to QGIS.

The module is loaded alone; QGIS stays mocked by the root conftest, with the two classes read here.
"""
import importlib.util
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_PATH = pathlib.Path(__file__).resolve().parents[4] / "adapters" / "qgis" / "native_filter_translation.py"


@pytest.fixture
def translation(monkeypatch):
    spec = importlib.util.spec_from_file_location("fm_native_geometry_version_test", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsWkbTypes", types.SimpleNamespace(isCurvedType=lambda kind: False),
                        raising=False)
    return module


def _qgis(monkeypatch, version):
    monkeypatch.setattr(sys.modules["qgis.core"], "Qgis", types.SimpleNamespace(QGIS_VERSION_INT=version), raising=False)


def _points_of_a_geopackage():
    provider = types.SimpleNamespace(storageType=lambda: "GPKG", geometryColumnName=lambda: "geom")
    return types.SimpleNamespace(providerType=lambda: "ogr", dataProvider=lambda: provider, geometryType=lambda: 0,
                                 wkbType=lambda: 1)


@pytest.mark.parametrize("version", [33400, 34415, 40300])
def test_the_geometry_is_written_where_it_was_compared_with_qgis(translation, monkeypatch, version):
    _qgis(monkeypatch, version)
    geometry = translation.native_geometry(_points_of_a_geopackage())
    assert geometry is not None and (geometry.column, geometry.kind) == ("geom", "point")


@pytest.mark.parametrize("version", [32200, 32816, 33399])
def test_an_older_qgis_leaves_the_geometric_functions_to_qgis(translation, monkeypatch, version):
    _qgis(monkeypatch, version)
    assert translation.native_geometry(_points_of_a_geopackage()) is None
