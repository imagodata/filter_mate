# -*- coding: utf-8 -*-
"""Local copies of web services: what can be copied, where it goes, what is said before, what is kept."""
import os

import pytest

from filtermate_core.domain import stream_copy as sc

pytestmark = pytest.mark.unit

XYZ_OSM = ("crs=EPSG:3857&format&type=xyz&url=https://tile.openstreetmap.org/%7Bz%7D/%7Bx%7D/%7By%7D.png"
           "&zmax=19&zmin=0")
XYZ_CARTO = "type=xyz&url=https://basemaps.cartocdn.com/light_all/%7Bz%7D/%7Bx%7D/%7By%7D.png&zmax=20&zmin=0"
XYZ_GOOGLE = "type=xyz&url=https://mt1.google.com/vt/lyrs%3Ds%26x%3D%7Bx%7D%26y%3D%7By%7D%26z%3D%7Bz%7D&zmax=20"
XYZ_SUBDOMAINS = "type=xyz&url=https://%7Bs%7D.tile.openstreetmap.org/%7Bz%7D/%7Bx%7D/%7By%7D.png"
WMS_IGN = "contextualWMSLegend=0&crs=EPSG:2154&format=image/png&layers=ORTHOIMAGERY.ORTHOPHOTOS&styles&url=https://data.geopf.fr/wms-r"
WFS_IGN = ("pagingEnabled='true' preferCoordinatesForWfsT11='false' restrictToRequestBBOX='1' srsname='EPSG:2154' "
           "typename='ADMINEXPRESS-COG-CARTO.LATEST:commune' url='https://data.geopf.fr/wfs/ows' version='auto'")


@pytest.mark.parametrize("provider, kind", [
    ("wms", sc.KIND_IMAGE), ("WFS", sc.KIND_FEATURES), ("OAPIF", sc.KIND_FEATURES),
    ("arcgisfeatureserver", sc.KIND_FEATURES), ("gdal", ""), ("ogr", ""), ("wcs", ""), ("arcgismapserver", ""), ("", ""),
])
def test_copy_kind(provider, kind):
    assert sc.copy_kind(provider) == kind


@pytest.mark.parametrize("source, url", [
    (WFS_IGN, "https://data.geopf.fr/wfs/ows"),
    (WMS_IGN, "https://data.geopf.fr/wms-r"),
    (XYZ_OSM, "https://tile.openstreetmap.org/{z}/{x}/{y}.png"),
    ("", ""),
])
def test_service_url(source, url):
    assert sc.service_url(source) == url


@pytest.mark.parametrize("source, name", [
    (XYZ_OSM, "OpenStreetMap"), (XYZ_SUBDOMAINS, "OpenStreetMap"), (XYZ_GOOGLE, "Google"),
    ("type=xyz&url=https://tile.osm.org/%7Bz%7D/%7Bx%7D/%7By%7D.png", "OpenStreetMap"),
    ("type=xyz&url=https://tile.openstreetmap.org./%7Bz%7D/%7Bx%7D/%7By%7D.png", "OpenStreetMap"),
    ("type=xyz&url=https://khms0.google.fr/kh/v%3D1%26x%3D%7Bx%7D", "Google"),
    ("type=xyz&url=https://ecn.t0.tiles.virtualearth.net/tiles/a%7Bq%7D.jpeg", "Bing"),
    ("type=xyz&url=https://google.example.org/%7Bz%7D", ""),
    (XYZ_CARTO, ""), (WMS_IGN, ""), (WFS_IGN, ""), ("type=xyz&url=https://tile.openstreetmap.fr/osmfr/%7Bz%7D/%7Bx%7D/%7By%7D.png", ""),
    ("type=xyz&url=https://notgoogle.com.example.org/%7Bz%7D", ""),
])
def test_forbidden_by(source, name):
    assert sc.forbidden_by(source) == name


def test_project_folder_next_to_the_project():
    path = os.path.join("work", "etude", "estavar.qgz")
    assert sc.project_folder(path) == os.path.join("work", "etude", "estavar_filtermate_local")


@pytest.mark.parametrize("project", ["", "   ", "geopackage:/data/projects.gpkg?projectName=p",
                                     "postgresql:?service=gis&schema=public&project=p", "estavar.qgz"])
def test_project_folder_none_for_a_project_without_a_file(project):
    assert sc.project_folder(project) == ""


def test_project_folder_keeps_a_windows_drive():
    assert sc.project_folder(r"C:\GIS\etude.qgz").endswith("etude_filtermate_local")


def test_profile_folder_per_project_and_for_unsaved():
    first = sc.profile_folder("/profile", "/a/etude.qgz")
    second = sc.profile_folder("/profile", "/b/etude.qgz")
    assert first != second and os.path.basename(first).startswith("etude_")
    assert sc.profile_folder("/profile", "").endswith(os.path.join("filtermate", "local_copies", sc.UNSAVED))


def test_folder_candidates_project_first_then_profile():
    candidates = sc.folder_candidates(os.path.join("w", "p.qgz"), "/profile")
    assert candidates[0] == os.path.join("w", "p_filtermate_local") and candidates[1].startswith("/profile")
    assert len(sc.folder_candidates("", "/profile")) == 1


@pytest.mark.parametrize("name, kind, expected", [
    ("Communes IGN", sc.KIND_FEATURES, "Communes_IGN_20261122-1500.gpkg"),
    ("Ortho 2023 / IGN", sc.KIND_IMAGE, "Ortho_2023_IGN_20261122-1500.tif"),
    ("", sc.KIND_IMAGE, "layer_20261122-1500.tif"),
    ("CON", sc.KIND_IMAGE, "layer_CON_20261122-1500.tif"),
    ("../../etc", sc.KIND_FEATURES, "etc_20261122-1500.gpkg"),
])
def test_file_name(name, kind, expected):
    assert sc.file_name(name, kind, "20261122-1500") == expected


def test_image_estimate_tiles_and_wms_blocks():
    tiled = sc.image_estimate(1024, 512, 2.4, tiled=True)
    assert tiled.requests == 4 * 2
    wms = sc.image_estimate(4100, 2000, 1.0, tiled=False)
    assert wms.requests == 3 * 1
    assert tiled.megabytes_at_most == pytest.approx(1024 * 512 * 4 * 4 / 3 / 1048576)


def test_finest_resolutions():
    assert sc.finest_resolutions([1.2, 0.6, float("nan"), -1, True], 5.0) == (1.2, 0.6)
    assert sc.finest_resolutions([], 5.0) == (2.5,)
    assert sc.finest_resolutions([], 0) == ()


@pytest.mark.parametrize("value, expected", [
    (None, 10.0), ("", 10.0), ("abc", 10.0), (0, 10.0), (-5, 10.0), (True, 10.0), ({"value": 50}, 50.0),
    ("1 000", 100.0), (5, 8.0), (10 ** 9, 100.0), (float("inf"), 10.0),
])
def test_bounded_number(value, expected):
    assert sc.bounded_number(value, 10.0, 8.0, 100.0) == expected


def _record(**changes):
    values = dict(kind=sc.KIND_FEATURES, stream_source=WFS_IGN, stream_provider="WFS", path="/w/p_filtermate_local/c.gpkg",
                  extent=(1.0, 2.0, 3.0, 4.0), crs="EPSG:2154", captured="2026-11-22T15:00:00", complete=False,
                  features=200000, subset='"insee_dep" = \'31\'', notes=("feature_limit",))
    values.update(changes)
    return sc.LocalCopy(**values)


def test_record_round_trip():
    record = _record()
    assert sc.LocalCopy.from_json(record.to_json()) == record
    assert sc.LocalCopy.from_json(record.with_path("/other.gpkg").to_json()).path == "/other.gpkg"


@pytest.mark.parametrize("raw", [None, "", "{", "[]", '{"kind": "image"}', 42,
                                 _record(kind="other").to_json(), _record(extent=(1, 2, 3)).to_json(),
                                 _record(stream_source="").to_json()])
def test_record_unreadable_is_none(raw):
    assert sc.LocalCopy.from_json(raw) is None


def test_record_with_a_nan_extent_is_none():
    raw = _record().to_json().replace("[1.0, 2.0, 3.0, 4.0]", "[NaN, 2.0, 3.0, 4.0]")
    assert sc.LocalCopy.from_json(raw) is None


def test_record_keeps_its_opacity_and_refuses_a_wrong_one():
    assert sc.LocalCopy.from_json(_record(opacity=0.4).to_json()).opacity == 0.4
    assert sc.LocalCopy.from_json(_record(opacity=7.0).to_json()).opacity == -1.0
    assert _record().replaced(subset="").subset == ""


def test_free_path():
    taken = {"/w/a.tif", "/w/a_2.tif"}
    assert sc.free_path("/w/a.tif", taken.__contains__) == "/w/a_3.tif"
    assert sc.free_path("/w/b.tif", taken.__contains__) == "/w/b.tif"


def test_is_copy_of():
    record = _record(path="/w/p_filtermate_local/c.gpkg")
    assert sc.is_copy_of("/w/p_filtermate_local/c.gpkg|layername=c", record)
    assert sc.is_copy_of("/w/./p_filtermate_local/c.gpkg", record)
    assert not sc.is_copy_of(WFS_IGN, record)
    assert not sc.same_path("", "")
