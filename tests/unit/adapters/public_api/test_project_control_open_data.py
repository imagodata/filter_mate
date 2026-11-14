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


# --- a platform that stalls is asked twice (2026-11-14, data.gouv.fr) -------------------------------------------------

def _answers(monkeypatch, *answers):
    """``fetch`` giving ``answers`` one after the other (an exception is raised); the timeouts asked are returned."""
    left, timeouts = list(answers), []

    def fetch(url, **options):
        timeouts.append(options["timeout_ms"])
        answer = left.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer
    monkeypatch.setattr(project_control, "fetch", fetch)
    return timeouts


_FOUND = SimpleNamespace(status=200, headers={}, content=b'{"data": [{"id": "a", "title": "Communes"}]}')


@pytest.mark.parametrize("first", [
    project_control.HttpFailure(project_control.TOO_LONG),
    SimpleNamespace(status=200, headers={}, content=b"<html>Service unavailable</html>"),
    SimpleNamespace(status=503, headers={}, content=b""),
], ids=["too long", "not JSON", "503"])
def test_a_search_that_stalled_is_asked_once_more(monkeypatch, first):
    timeouts = _answers(monkeypatch, first, _FOUND)
    assert project_control.search_open_data("communes")["count"] == 1
    assert timeouts == list(project_control.SEARCH_TIMEOUTS_MS) and timeouts[0] < timeouts[1]


def test_a_search_that_stalled_twice_sends_the_model_elsewhere(monkeypatch):
    late = project_control.HttpFailure(project_control.TOO_LONG)
    timeouts = _answers(monkeypatch, late, late)
    with pytest.raises(ValueError, match="datagouv did not answer.*another platform"):
        project_control.search_open_data("communes")
    assert len(timeouts) == 2


@pytest.mark.parametrize("answer, message", [
    (project_control.HttpFailure(project_control.STOPPED), "did not answer: stopped"),  # the user pressed Stop
    (project_control.HttpFailure("Connection refused"), "Connection refused"),
    (SimpleNamespace(status=404, headers={}, content=b""), r"error \(404\)"),
], ids=["stopped", "refused", "404"])
def test_a_search_that_failed_for_good_is_asked_once(monkeypatch, answer, message):
    timeouts = _answers(monkeypatch, answer)
    with pytest.raises(ValueError, match=message) as failure:
        project_control.search_open_data("communes")
    assert len(timeouts) == 1 and "asked twice" not in str(failure.value)


# --- a web basemap: one of the list, checked by one tile, added under the layers ------------------------------------

_PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20


class _Tiles:
    def __init__(self, source, name, provider):
        self.source, self.title, self.provider, self.rights = source, name, provider, None

    def isValid(self):
        return True

    def metadata(self):
        return SimpleNamespace(setRights=lambda rights: setattr(self, "rights", rights))

    def setMetadata(self, metadata):
        pass


@pytest.fixture
def basemap_project(monkeypatch):
    """What add_basemap needs of QGIS: a raster layer that opens, a project and its layer tree."""
    core = sys.modules["qgis.core"]
    registered, tree = [], []
    project = SimpleNamespace(addMapLayer=lambda layer, in_tree: registered.append((layer, in_tree)),
                              layerTreeRoot=lambda: SimpleNamespace(addLayer=tree.append))
    monkeypatch.setattr(core, "QgsRasterLayer", _Tiles, raising=False)
    monkeypatch.setattr(core, "QgsProject", SimpleNamespace(instance=lambda: project), raising=False)
    monkeypatch.setattr(project_control, "_summary", lambda layer, count_features=True: {"name": layer.title})
    monkeypatch.setattr(project_control, "_map_place", lambda: None)
    return SimpleNamespace(registered=registered, tree=tree)


def _tiles(monkeypatch, status=200, content=_PNG):
    asked = []

    def fetch(url, **options):
        asked.append(url)
        return SimpleNamespace(status=status, headers={}, content=content)
    monkeypatch.setattr(project_control, "fetch", fetch)
    return asked


def test_a_basemap_of_the_list_goes_under_the_layers_with_its_attribution(basemap_project, monkeypatch):
    asked = _tiles(monkeypatch)
    assert project_control.add_basemap("carto_light_nolabels") == {"name": "Carto Light (neutral, no names)"}
    assert asked == ["https://basemaps.cartocdn.com/light_nolabels/1/0/0.png"]
    (layer, in_tree), = basemap_project.registered
    assert in_tree is False and basemap_project.tree == [layer]  # appended to the tree: below every other layer
    assert layer.provider == "wms" and layer.source == (
        "type=xyz&url=https://basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png&zmax=20&zmin=0")
    assert layer.rights == ["© OpenStreetMap contributors © CARTO"]


def test_a_basemap_the_user_added_is_named_after_its_server(basemap_project, monkeypatch):
    _tiles(monkeypatch)
    address = "https://Tiles.example.org/{z}/{x}/{y}.png"
    summary = project_control.add_basemap(address.lower(), extra_domains=f"{address}:xyz")
    assert summary == {"name": "tiles.example.org"}
    assert basemap_project.registered[0][0].source == f"type=xyz&url={address}&zmax=19&zmin=0"
    assert project_control.add_basemap(address.lower(), name="Fond", extra_domains=f"{address}:xyz") == {"name": "Fond"}


@pytest.mark.parametrize("status, content, said", [
    (404, b"", "answered with an error \\(404\\)"), (200, b"<html>blocked</html>", "not with an image"),
])
def test_a_server_that_gives_no_tile_is_said_and_nothing_is_added(basemap_project, monkeypatch, status, content, said):
    _tiles(monkeypatch, status, content)
    with pytest.raises(ValueError, match=said):
        project_control.add_basemap("osm_tiles")
    assert basemap_project.registered == [] and basemap_project.tree == []


def test_only_a_basemap_is_added_as_a_basemap_and_an_address_is_never_taken(basemap_project, monkeypatch):
    monkeypatch.setattr(project_control, "fetch", MagicMock(side_effect=AssertionError("nothing is asked")))
    with pytest.raises(ValueError, match="is not a basemap"):
        project_control.add_basemap("ign_wfs")
    with pytest.raises(ValueError, match="not a basemap of the list"):
        project_control.add_basemap("https://evil.example.org/{z}/{x}/{y}.png")  # not in the user's list
    with pytest.raises(ValueError) as refused:
        project_control.search_open_data("communes", platform="nowhere")
    assert "datagouv" in str(refused.value) and "carto_light" not in str(refused.value)  # basemaps hold no data
    with pytest.raises(ValueError, match="holds"):  # a line of the configuration file that is no template
        project_control.add_basemap("tiles.example.org", extra_domains="tiles.example.org:xyz")
    with pytest.raises(ValueError, match="is a basemap"):
        project_control.search_open_data("communes", platform="osm_tiles")
    assert basemap_project.registered == []


def test_a_server_of_one_country_is_asked_where_the_map_is(basemap_project, monkeypatch):
    """2026-11-14: swisstopo, GSI and basemap.at have no tile for a quarter of the world; QGIS draws them well."""
    asked = []

    def fetch(url, **options):
        asked.append(url)
        return SimpleNamespace(status=200 if url.endswith("/10/516/373.png") else 404, headers={}, content=_PNG)
    monkeypatch.setattr(project_control, "fetch", fetch)
    monkeypatch.setattr(project_control, "_map_place", lambda: (1.444, 43.604))
    address = "https://tiles.example.org/{z}/{x}/{y}.png"
    project_control.add_basemap(address, extra_domains=f"{address}:xyz")
    assert asked == ["https://tiles.example.org/10/516/373.png"] and len(basemap_project.registered) == 1
    monkeypatch.setattr(project_control, "_map_place", lambda: (140.0, 36.0))  # the map is elsewhere
    with pytest.raises(ValueError, match="move the map over the area it covers"):
        project_control.add_basemap(address, extra_domains=f"{address}:xyz")
    assert asked[-1] == "https://tiles.example.org/1/0/0.png"


@pytest.mark.parametrize("status", [204, 302])
def test_a_server_that_sends_elsewhere_or_has_nothing_there_is_taken_as_answering(basemap_project, monkeypatch, status):
    _tiles(monkeypatch, status, b"")
    project_control.add_basemap("osm_tiles")
    assert len(basemap_project.registered) == 1


# --- a point cloud: a local LAS or LAZ file, opened by its own provider ---------------------------------------------

@pytest.fixture
def cloud_project(monkeypatch, tmp_path):
    core = sys.modules["qgis.core"]
    added, providers = [], {"copc", "pdal"}
    monkeypatch.setattr(core, "QgsPointCloudLayer", _Tiles, raising=False)
    monkeypatch.setattr(core, "QgsProviderRegistry", SimpleNamespace(instance=lambda: SimpleNamespace(
        providerMetadata=lambda name: object() if name in providers else None)), raising=False)
    monkeypatch.setattr(core, "QgsProject", SimpleNamespace(instance=lambda: SimpleNamespace(addMapLayer=added.append)),
                        raising=False)
    monkeypatch.setattr(project_control, "_summary", lambda layer: {"name": layer.title, "provider": layer.provider})
    for name in ("tile.laz", "tile.copc.laz", "communes.gpkg"):
        (tmp_path / name).write_bytes(b"x")
    return SimpleNamespace(added=added, providers=providers, folder=tmp_path)


def test_a_las_file_is_a_point_cloud_whatever_kind_is_asked(cloud_project):
    folder = cloud_project.folder
    assert project_control.add_layer(str(folder / "tile.laz")) == {"name": "tile.laz", "provider": "pdal"}
    assert project_control.add_layer(str(folder / "tile.copc.laz"), name="sol", kind="raster") == {
        "name": "sol", "provider": "copc"}
    assert len(cloud_project.added) == 2


def test_what_is_no_local_point_cloud_file_is_refused_as_one(cloud_project, monkeypatch):
    monkeypatch.setattr(project_control, "fetch", MagicMock(side_effect=AssertionError("nothing is asked")))
    with pytest.raises(ValueError, match="from a local file"):
        project_control.add_layer("https://data.example.org/tile.laz")
    with pytest.raises(ValueError, match="is a .las, .laz or .copc.laz file"):
        project_control.add_layer(str(cloud_project.folder / "communes.gpkg"), kind="point_cloud")
    cloud_project.providers.discard("pdal")
    with pytest.raises(ValueError, match="built without PDAL"):
        project_control.add_layer(str(cloud_project.folder / "tile.laz"))
    assert project_control.add_layer(str(cloud_project.folder / "tile.copc.laz"))["provider"] == "copc"
    assert len(cloud_project.added) == 1
