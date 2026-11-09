# -*- coding: utf-8 -*-
"""Open data platforms: the allow list, the requests, what is kept of the answers."""
import pytest

from core.agent.open_data import (
    base_url, display_source, parse_extra_domains, parse_results, platforms_available, resolve_platform, search_url,
    source_problem,
)

pytestmark = pytest.mark.unit


class TestAllowList:
    def test_built_in(self):
        assert resolve_platform("datagouv") == ("datagouv", "https://www.data.gouv.fr")
        assert resolve_platform("OpenDataSoft") == ("opendatasoft", "https://data.opendatasoft.com")

    def test_unknown_is_refused_with_the_way_out(self):
        with pytest.raises(ValueError, match="open_data_domains"):
            resolve_platform("evil.example")

    def test_user_platforms(self):
        extra = "data.toulouse-metropole.fr, data.example.org:ckan ,"
        assert parse_extra_domains(extra) == {"data.toulouse-metropole.fr": ("opendatasoft", "data.toulouse-metropole.fr"),
                                              "data.example.org": ("ckan", "data.example.org")}
        assert resolve_platform("data.example.org", extra) == ("ckan", "https://data.example.org")
        assert resolve_platform("https://data.toulouse-metropole.fr/", extra)[1] == "https://data.toulouse-metropole.fr"
        assert set(platforms_available(extra)) >= {"datagouv", "opendatasoft", "data.example.org"}

    def test_http_only_for_this_machine(self):
        assert base_url("http://127.0.0.1:8000") == "http://127.0.0.1:8000"
        with pytest.raises(ValueError):
            base_url("http://data.example.org")
        with pytest.raises(ValueError):
            resolve_platform("data.example.org", "http://data.example.org:ckan")


class TestRequests:
    def test_urls(self):
        assert search_url("datagouv", "https://www.data.gouv.fr", "communes 31", 5) == \
            "https://www.data.gouv.fr/api/1/datasets/?q=communes%2031&page_size=5"
        assert search_url("ckan", "https://d.org", "a&b", 3) == "https://d.org/api/3/action/package_search?q=a%26b&rows=3"
        ods = search_url("opendatasoft", "https://d.org", 'x" or 1=1', 99)
        assert ods == "https://d.org/api/explore/v2.1/catalog/datasets?where=%22x%20or%201%3D1%22&limit=20"

    def test_unknown_kind(self):
        with pytest.raises(ValueError):
            search_url("nope", "https://d.org", "x", 1)


class TestAnswers:
    def test_datagouv(self):
        payload = {"data": [{"id": "1", "title": "Communes", "description": "x" * 400, "organization": {"name": "IGN"},
                             "page": "https://www.data.gouv.fr/datasets/1", "resources": [
                                 {"title": "GeoJSON", "format": "geojson", "url": "https://static.data.gouv.fr/c.geojson"},
                                 {"title": "PDF", "format": "pdf", "url": "https://static.data.gouv.fr/n.pdf"},
                                 {"title": "insecure", "format": "gpkg", "url": "http://static.data.gouv.fr/c.gpkg"},
                                 "junk"]}, "junk"]}
        found = parse_results("datagouv", payload, "https://www.data.gouv.fr")
        assert len(found) == 1 and found[0]["publisher"] == "IGN" and len(found[0]["description"]) == 300
        assert found[0]["resources"] == [{"title": "GeoJSON", "format": "geojson", "url": "https://static.data.gouv.fr/c.geojson"}]

    def test_opendatasoft_exports(self):
        payload = {"results": [{"dataset_id": "communes-31", "features": ["analyze", "geo"],
                                "metas": {"default": {"title": "Communes", "publisher": "Toulouse"}}},
                               {"dataset_id": "budget", "features": ["analyze"], "metas": {"default": {"title": "Budget"}}},
                               {"no": "id"}]}
        found = parse_results("opendatasoft", payload, "https://data.example.org")
        assert len(found) == 2 and found[0]["has_geometry"] is True
        assert [r["format"] for r in found[1]["resources"]] == ["csv"] and found[1]["has_geometry"] is False
        assert found[0]["resources"][0]["url"] == "https://data.example.org/api/explore/v2.1/catalog/datasets/communes-31/exports/geojson"
        assert found[0]["page"] == "https://data.example.org/explore/dataset/communes-31/"

    def test_ckan(self):
        payload = {"result": {"results": [{"name": "parcs", "title": "Parcs", "notes": "n", "organization": {"title": "Ville"},
                                           "resources": [{"name": "zip", "format": "SHP", "url": "https://d.org/p.zip"}]}]}}
        found = parse_results("ckan", payload, "https://d.org")
        assert found[0]["page"] == "https://d.org/dataset/parcs" and found[0]["resources"][0]["format"] == "shp"

    @pytest.mark.parametrize("payload", [None, [], "x", {"data": "x"}, {"results": None}, {"result": []}])
    def test_odd_answers_give_nothing(self, payload):
        for kind in ("datagouv", "opendatasoft", "ckan"):
            assert parse_results(kind, payload, "https://d.org") == []


class TestSources:
    @pytest.mark.parametrize("source", [
        "/data/communes.gpkg", "C:\\data\\a.shp", "C:/data/a.geojson", "/data/a.gpkg|layername=communes", "relative/a.tif",
    ])
    def test_plain_local_files(self, source):
        assert source_problem(source, False) == ""

    @pytest.mark.parametrize("source", [
        # Each of these opened something over the network or read what it should not, in a real QGIS.
        "\\\\evil\\share\\x.gpkg", "//evil/share/x.gpkg", "\\\\?\\UNC\\evil\\x.gpkg",
        "PG:host=evil dbname=x", "MySQL:x", "MSSQL:server=evil", "host=evil dbname=x.gpkg",
        "type=xyz&u%72l=http%3A%2F%2F127.0.0.1%2Fa.gpkg", "<GDAL_WMS><ServerUrl>http://x</ServerUrl></GDAL_WMS>",
        "/vsicurl/http://x/a.gpkg", "/vsicurl?url=http%3A%2F%2Fx%2Fa.geojson", "/vsizip//vsis3/b/a.gpkg", "/vsiaz/a.gpkg",
        "CSV:/tmp/secret.txt", "<OGRVRTDataSource><OGRVRTLayer/></OGRVRTDataSource>", "/data/a.gpkg|subset=1=1",
        "file:///etc/passwd", "file:///a.gpkg", "ftp://x/a.gpkg", "http://x.org/a.geojson", "/tmp/secret.txt", "/data/noextension",
        "ftp://evil/a.geojson?https://", "/data/a\nb.gpkg", "url='https://evil/wfs' authcfg=abc1234 typename='a.gpkg'",
    ])
    @pytest.mark.parametrize("remote", [False, True])
    def test_anything_else_is_refused(self, source, remote):
        assert source_problem(source, remote)

    @pytest.mark.parametrize("url", ["https://static.data.gouv.fr/c.geojson", "https://d.org:443/a?x=1", "https://8.8.8.8/a.gpkg"])
    def test_public_https(self, url):
        assert source_problem(url, True) == ""
        assert "open data" in source_problem(url, False)

    @pytest.mark.parametrize("url", [
        "https://localhost/a", "https://127.0.0.1/a", "https://10.0.0.5/a", "https://192.168.1.1/a", "https://169.254.169.254/a",
        "https://[::1]/a", "https://intranet/a", "https://nas.local/a", "https://user:pw@x.org/a", "https://x.org:8443/a",
        "https://x.org/a b", "https://x.org|y",
    ])
    def test_private_or_odd_urls(self, url):
        assert source_problem(url, True)

    def test_too_long(self):
        assert source_problem("https://x.org/" + "a" * 3000, True)

    def test_what_the_user_reads_starts_with_the_host(self):
        shown = display_source("https://static.example.org/" + "p" * 200 + "?secret=1")
        assert shown.startswith("static.example.org\n") and "secret" not in shown and len(shown) < 150


class TestOddAnswers:
    @pytest.mark.parametrize("payload", [{"metas": 1}, {"results": [{"dataset_id": "a", "metas": {"default": "x"}}]},
                                         {"data": 5}, {"data": [{"resources": 5}]}, {"results": 7}])
    def test_nothing_raises(self, payload):
        for kind in ("datagouv", "opendatasoft", "ckan"):
            assert isinstance(parse_results(kind, payload, "https://d.org"), list)

    def test_a_page_full_of_whitespace_is_dropped(self):
        found = parse_results("datagouv", {"data": [{"id": "1", "page": "https://x\n" + "y" * 10}]}, "https://d.org")
        assert found[0]["page"] == ""


class TestExtraDomains:
    def test_a_typo_is_not_part_of_the_address(self):
        assert parse_extra_domains("x.org:KIND, y.org:ckan") == {"y.org": ("ckan", "y.org")}
