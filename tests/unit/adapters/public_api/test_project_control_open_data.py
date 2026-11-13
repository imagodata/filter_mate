# -*- coding: utf-8 -*-
"""Open data in ``adapters.public_api.project_control``: which requests have the address of their server checked.

The module is loaded for real under a synthetic package (its relative imports reach ``core`` and ``adapters``); QGIS
stays mocked by the root conftest, QtNetwork is mocked here, and ``fetch`` and the resolver are stand-ins.
"""
import importlib
import pathlib
import socket
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_project_control_open_data_test"


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.agent", _ROOT / "core" / "agent"),
                       (".core.domain", _ROOT / "core" / "domain"), (".adapters", _ROOT / "adapters"),
                       (".adapters.agent", _ROOT / "adapters" / "agent"),
                       (".adapters.public_api", _ROOT / "adapters" / "public_api")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    stubbed = "qgis.PyQt.QtNetwork" not in sys.modules
    if stubbed:
        sys.modules["qgis.PyQt.QtNetwork"] = MagicMock()
    try:
        return importlib.import_module(f"{_PKG}.adapters.public_api.project_control")
    finally:
        if stubbed:
            sys.modules.pop("qgis.PyQt.QtNetwork", None)


project_control = _load()


@pytest.fixture
def resolver(monkeypatch):
    """socket.getaddrinfo answering ``resolver.address`` for any name, and recording the names asked."""
    def resolve(host, port, *args, **kwargs):
        resolve.asked.append(host)
        return [(10 if ":" in resolve.address else 2, 1, 6, "", (resolve.address, 0))]
    resolve.asked, resolve.address = [], "93.184.215.14"
    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    return resolve


@pytest.fixture
def fetched(monkeypatch):
    """``fetch`` answering an empty JSON list, and recording the URLs asked."""
    asked = []

    def fetch(url, **options):
        asked.append(url)
        return SimpleNamespace(status=200, headers={}, content=b'{"data": [], "features": []}')
    monkeypatch.setattr(project_control, "fetch", fetch)
    return asked


# --- a platform of the list is the user's choice (regression of #429) -----------------------------------------------

@pytest.mark.parametrize("platform, address, base", [
    ("http://localhost:8000", "127.0.0.1", "http://localhost:8000/"),  # a local mirror, as base_url allows it
    ("data.example.org", "10.0.0.7", "https://data.example.org/"),  # a portal seen from the network that hosts it
])
def test_a_platform_the_user_added_is_asked_whatever_its_name_resolves_to(resolver, fetched, platform, address, base):
    resolver.address = address
    found = project_control.search_open_data("communes", platform=platform, extra_domains=f"{platform}:datagouv")
    assert found["count"] == 0 and len(fetched) == 1 and fetched[0].startswith(base)
    assert resolver.asked == []  # the address of a platform of the list is never judged


def test_a_stac_catalog_the_user_added_is_asked_whatever_its_name_resolves_to(resolver, fetched):
    resolver.address = "10.0.0.7"
    found = project_control.search_imagery(bbox=[1.3, 43.5, 1.5, 43.7], platform="stac.example.org",
                                           extra_domains="stac.example.org:stac")
    assert found["count"] == 0 and fetched == ["https://stac.example.org/search"] and resolver.asked == []


# --- a link a model gives is checked, each name once per call ------------------------------------------------------

class _Layer:
    def __init__(self, source, name, provider):
        self.source = source

    def isValid(self):
        return True


@pytest.fixture
def qgis_layers(monkeypatch, tmp_path):
    """What add_layer needs of QGIS: a profile folder, layers that open, a project that takes them."""
    core = sys.modules["qgis.core"]
    added = []
    monkeypatch.setattr(core, "QgsApplication", SimpleNamespace(qgisSettingsDirPath=lambda: str(tmp_path)), raising=False)
    monkeypatch.setattr(core, "QgsVectorLayer", _Layer, raising=False)
    monkeypatch.setattr(core, "QgsProject", SimpleNamespace(instance=lambda: SimpleNamespace(addMapLayer=added.append)),
                        raising=False)
    monkeypatch.setattr(project_control, "_summary", lambda layer: {"source": layer.source})
    return added


def test_add_layer_resolves_each_name_once(resolver, qgis_layers, monkeypatch):
    """The probe, its redirects and the download used to resolve the name each, up to 3 s apiece (audit of 13/11)."""
    def fetch(url, **options):
        if options.get("headers_only"):
            if url.endswith("/moved.geojson"):
                return SimpleNamespace(status=302, headers={"location": "/a.geojson"})
            return SimpleNamespace(status=200, headers={"content-type": "application/geo+json"})
        options["sink"](b'{"type": "FeatureCollection", "features": []}')
        return SimpleNamespace(status=200, headers={"content-type": "application/geo+json"})
    monkeypatch.setattr(project_control, "fetch", fetch)
    summary = project_control.add_layer("https://data.example.org/moved.geojson")
    assert summary["source"].endswith("a.geojson") and len(qgis_layers) == 1
    assert resolver.asked == ["data.example.org"]
    project_control.add_layer("https://data.example.org/moved.geojson")
    assert resolver.asked == ["data.example.org"] * 2  # the next call resolves it again: nothing is kept between calls


def test_add_layer_still_refuses_a_name_resolving_to_a_local_address(resolver, qgis_layers, monkeypatch):
    resolver.address = "169.254.169.254"
    monkeypatch.setattr(project_control, "fetch", MagicMock(side_effect=AssertionError("nothing is asked")))
    with pytest.raises(ValueError, match="only a public address can be read"):
        project_control.add_layer("https://data.example.org/a.geojson")
    assert qgis_layers == []
