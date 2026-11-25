# -*- coding: utf-8 -*-
"""Lot 3 (audit of 2026-11-24): a cut copy is never called complete, a copy made again reads the service anew,
a filter of the copy stays off the service, and no password reaches the log.

Pure guards, loaded for real through coverage_fakes (their relative imports reach ``core``):

- ``announced_from_prefix`` / ``announces_this_read`` (remote_materializer): what a service reply says it
  holds, and which replies may announce the read in progress;
- ``_redacted_source`` (snapshots): no address, no password in the log.
"""
import importlib.util
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit


def _fakes():
    if "fm_coverage_fakes" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "fm_coverage_fakes", pathlib.Path(__file__).with_name("coverage_fakes.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules["fm_coverage_fakes"] = module
        spec.loader.exec_module(module)
    return sys.modules["fm_coverage_fakes"]


load = _fakes().load

PACKAGE = "fm_coverage_engine_test"
ROOT = pathlib.Path(__file__).resolve().parents[4]


def _register(name, path):
    full = PACKAGE + name
    if full not in sys.modules:
        package = types.ModuleType(full)
        package.__path__ = [str(path)]
        sys.modules[full] = package


for _name, _path in ((".core.filter", ROOT / "core" / "filter"),
                     (".core.optimization", ROOT / "core" / "optimization"),
                     (".infrastructure", ROOT / "infrastructure"),
                     (".infrastructure.logging", ROOT / "infrastructure" / "logging")):
    _register(_name, _path)

materializer = load("adapters.qgis.remote_materializer")
snapshots = load("adapters.qgis.coverage_layers.snapshots")


class TestAnnouncedFromPrefix:
    @pytest.mark.parametrize("prefix, expected", [
        (b'<?xml version="1.0"?><wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0" '
         b'numberMatched="5000" numberReturned="50" timeStamp="x">', 5000),
        (b'<wfs:FeatureCollection numberMatched="unknown" numberReturned="50">', None),
        (b'<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/1.1" numberOfFeatures="861">', 861),
        (b'{"type": "FeatureCollection", "features": [], "numberMatched": 25, "numberReturned": 10}', 25),
        (b'<ows:ExceptionReport><ows:Exception exceptionCode="NoApplicableCode"/></ows:ExceptionReport>', None),
        (b'{"error": "limit exceeded"}', None),
        (b"", None),
        (None, None),
    ])
    def test_totals_only(self, prefix, expected):
        assert materializer.announced_from_prefix(prefix) == expected

    def test_number_returned_is_not_a_total(self):
        assert materializer.announced_from_prefix(b'<wfs:FeatureCollection numberReturned="50">') is None

    def test_takes_the_largest_total_seen(self):
        assert materializer.announced_from_prefix(b'numberMatched="5000" numberMatched="5001"') == 5001


class TestAnnouncesThisRead:
    @pytest.mark.parametrize("url, expected", [
        ("http://127.0.0.1/wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=fm:keyed"
         "&BBOX=1,2,3,4&COUNT=20001", True),
        ("http://127.0.0.1/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAME=fm:keyed"
         "&MAXFEATURES=20001", True),
        ("http://127.0.0.1/wfs?SERVICE=WFS&REQUEST=GetFeature&TYPENAMES=fm:keyed&COUNT=1", False),
        ("http://127.0.0.1/wfs?SERVICE=WFS&REQUEST=GetFeature&TYPENAMES=fm:keyed&RESULTTYPE=hits", False),
        ("http://127.0.0.1/wfs?SERVICE=WFS&REQUEST=GetCapabilities", False),
        ("http://127.0.0.1/wfs?SERVICE=WFS&REQUEST=DescribeFeatureType&TYPENAME=fm:keyed", False),
        ("http://127.0.0.1/api/collections/places/items?limit=10000", True),
        ("http://127.0.0.1/api/collections/places/items?limit=1", False),
        ("http://127.0.0.1/api/collections/places/items/12", False),
        ("http://127.0.0.1/wfs", False),  # a POST carries no query to scope by
        ("", False),
    ])
    def test_only_the_requests_of_the_read_announce_it(self, url, expected):
        assert materializer.announces_this_read(url) == expected


def _standalone(name):
    """A pure helper off stream_copy.py (no QGIS): os and a logger only."""
    import ast as _ast
    import logging as _logging
    import os as _os
    path = pathlib.Path(__file__).resolve().parents[4] / "adapters" / "qgis" / "stream_copy.py"
    tree = _ast.parse(path.read_text())
    wanted = [n for n in tree.body if isinstance(n, _ast.FunctionDef) and n.name == name]
    wanted += [n for n in tree.body if isinstance(n, _ast.Assign) and any(
        getattr(target, "id", "") in ("_COPY_EXTENSIONS",) for target in n.targets)]
    namespace = {"os": _os, "logger": _logging.getLogger("test")}
    exec(compile(_ast.Module(body=wanted, type_ignores=[]), str(path), "exec"), namespace)
    return namespace[name]


class TestDeleteCopyFiles:
    def test_removes_the_copy_and_its_sidecars(self, tmp_path):
        delete = _standalone("_delete_copy_files")
        base = tmp_path / "couche_120000.gpkg"
        base.write_bytes(b"0")
        for suffix in (".ovr", ".aux.xml", ".qmd"):
            (tmp_path / ("couche_120000.gpkg" + suffix)).write_bytes(b"0")
        (tmp_path / "notes.txt").write_bytes(b"0")
        delete(str(base))
        assert not base.exists()
        assert not (tmp_path / "couche_120000.gpkg.ovr").exists()
        assert (tmp_path / "notes.txt").exists()

    def test_a_missing_copy_is_no_error(self, tmp_path):
        _standalone("_delete_copy_files")(str(tmp_path / "gone.gpkg"))

    def test_only_copies_are_pruned(self):
        managed = _standalone("_is_managed_copy_name")
        assert managed("couche_120000.gpkg") and managed("fond_120000.tif.ovr") and managed("x.AUX.XML")
        assert not managed("notes.txt") and not managed("") and not managed("carte.qgz")


class TestRedactedSource:
    def test_password_beside_the_url_is_masked(self):
        source = ("url='https://geo.example.net/wfs' username='reader' password='s3cr3t' "
                  "typename='fm:keyed' version='auto'")
        redacted = snapshots._redacted_source(source)
        assert "s3cr3t" not in redacted
        assert "password='***'" in redacted
        assert "[remote source]" in redacted

    def test_credentials_in_the_url_are_masked(self):
        redacted = snapshots._redacted_source("url='https://reader:s3cr3t@geo.example.net/wfs'")
        assert "s3cr3t" not in redacted and "[remote source]" in redacted

    def test_a_plain_source_stays_useful(self):
        source = "dbname='gis' host=localhost user='reader' servicename='pg:sslmode=require'"
        assert snapshots._redacted_source(source) == source
