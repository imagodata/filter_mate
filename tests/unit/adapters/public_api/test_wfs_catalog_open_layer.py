# -*- coding: utf-8 -*-
"""A WFS layer opened by the agent asks QGIS to read a first feature for its geometry type (2026-11-23).

The DescribeFeatureType of the IGN Géoplateforme says ``MultiSurface`` or ``Curve`` with no word of a Z, while the
BD TOPO sends 3D geometries. Typed from the schema alone, the layer was ``MultiPolygon`` or ``LineString`` and QGIS 4
logged a CRITICAL "Received feature geometry has Z values but the layer type (...) does not" for each layer
(checked in QGIS 4.3: with ``forceInitialGetFeature`` the layers are ``MultiPolygonZ`` and ``LineStringZ``; QGIS 3.44
ignores the parameter and opens the layer as before).

The module is loaded for real under a synthetic package; QGIS stays mocked by the root conftest.
"""
import importlib
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_wfs_catalog_open_layer_test"


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".adapters", _ROOT / "adapters"),
                       (".adapters.agent", _ROOT / "adapters" / "agent"),
                       (".adapters.public_api", _ROOT / "adapters" / "public_api")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    stubbed = "qgis.PyQt.QtNetwork" not in sys.modules
    if stubbed:
        sys.modules["qgis.PyQt.QtNetwork"] = MagicMock()
    try:
        return importlib.import_module(f"{_PKG}.adapters.public_api.wfs_catalog")
    finally:
        if stubbed:
            sys.modules.pop("qgis.PyQt.QtNetwork", None)


wfs_catalog = _load()


class _Uri:
    def __init__(self):
        self.params = {}

    def setParam(self, key, value):  # noqa: N802 - the QGIS name
        self.params[key] = value

    def uri(self, _expanded):
        return self


class _Layer:
    def __init__(self, uri, name, provider):
        self.uri, self.name, self.provider = uri, name, provider


@pytest.fixture
def opened(monkeypatch):
    monkeypatch.setattr(wfs_catalog, "QgsDataSourceUri", _Uri)
    monkeypatch.setattr(wfs_catalog, "QgsVectorLayer", _Layer)
    monkeypatch.setattr(wfs_catalog, "catalog", lambda _base: [
        {"name": "BDTOPO_V3:batiment", "title": "Bâtiments", "crs": "EPSG:4326", "abstract": ""}])
    return wfs_catalog.open_layer("https://data.geopf.fr/wfs/ows", "BDTOPO_V3:batiment", "")


def test_the_geometry_type_is_read_from_a_first_feature(opened):
    assert opened.uri.params["forceInitialGetFeature"] == "true"


def test_the_rest_of_the_uri_is_unchanged(opened):
    assert opened.provider == "WFS"
    assert opened.name == "Bâtiments"
    assert opened.uri.params == {
        "url": "https://data.geopf.fr/wfs/ows", "typename": "BDTOPO_V3:batiment", "version": "auto",
        "pagingEnabled": "true", "restrictToRequestBBOX": "1", "srsname": "EPSG:4326",
        "forceInitialGetFeature": "true"}


def test_a_layer_the_service_does_not_list_is_refused(monkeypatch):
    monkeypatch.setattr(wfs_catalog, "catalog", lambda _base: [])
    with pytest.raises(ValueError):
        wfs_catalog.open_layer("https://data.geopf.fr/wfs/ows", "BDTOPO_V3:batiment", "")
