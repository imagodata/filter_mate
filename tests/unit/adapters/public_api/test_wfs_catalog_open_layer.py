# -*- coding: utf-8 -*-
"""A WFS layer opened by the agent does not ask QGIS for an initial GetFeature (2026-11-23).

``forceInitialGetFeature`` (#641) typed the BD TOPO layers with their Z, which the DescribeFeatureType of the IGN
Géoplateforme does not name, and silenced QGIS 4's CRITICAL "Received feature geometry has Z values but the layer
type (...) does not". But QGIS sends that first GetFeature with no BBOX, and the Géoplateforme counts the whole table
for its ``numberMatched``: 24 to 60 s for the 20.5 million road sections, past QGIS's 60 s network timeout, so the
layer took 107 s to open (QGIS 4.3 against data.geopf.fr; with a BBOX the same request takes 0.3 s). The message is
the lesser harm: the parameter stays off.

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


def test_no_initial_get_feature_is_forced(opened):
    assert "forceInitialGetFeature" not in opened.uri.params


def test_the_uri(opened):
    assert opened.provider == "WFS"
    assert opened.name == "Bâtiments"
    assert opened.uri.params == {
        "url": "https://data.geopf.fr/wfs/ows", "typename": "BDTOPO_V3:batiment", "version": "auto",
        "pagingEnabled": "true", "restrictToRequestBBOX": "1", "srsname": "EPSG:4326"}


def test_a_layer_the_service_does_not_list_is_refused(monkeypatch):
    monkeypatch.setattr(wfs_catalog, "catalog", lambda _base: [])
    with pytest.raises(ValueError):
        wfs_catalog.open_layer("https://data.geopf.fr/wfs/ows", "BDTOPO_V3:batiment", "")
