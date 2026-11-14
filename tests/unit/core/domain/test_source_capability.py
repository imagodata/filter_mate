# -*- coding: utf-8 -*-
"""
Source capability classification (2026-10-17).

Provider keys and URIs are the ones QGIS 3.44 gives (``providerType()`` of
``QgsVectorLayer(uri, 'x', 'WFS')`` is ``'WFS'``, of an OGC API Features
layer ``'OAPIF'``).

Module tested: core.domain.source_capability, adapters.qgis.source_capability_probe
"""
import importlib.util
from pathlib import Path

import pytest

from core.domain.source_capability import (
    Locality,
    NetworkCost,
    REMOTE_KEY_LIST_LIMIT,
    REMOTE_SERVICE_PROVIDERS,
    ServerFilter,
    ValueKind,
    classify,
    classify_layer,
)
from infrastructure.constants import REMOTE_PROVIDERS

pytestmark = pytest.mark.unit

WFS_URI = ("pagingEnabled='true' srsname='EPSG:2154' typename='ADMINEXPRESS-COG.LATEST:commune' "
           "url='https://data.geopf.fr/wfs/ows' version='auto'")
OAPIF_URI = "url='https://example.org/ogcapi' typename='communes'"
AFS_URI = "url='https://example.org/arcgis/rest/services/x/FeatureServer/0'"
GDAL_WMS_XML = ('<GDAL_WMS><Service name="TMS"><ServerUrl>https://tile.openstreetmap.org/${z}/${x}/${y}.png'
                '</ServerUrl></Service></GDAL_WMS>')


@pytest.mark.parametrize("key, uri, server_filter", [
    ("WFS", WFS_URI, ServerFilter.OGC_FILTER),
    ("wfs", WFS_URI, ServerFilter.OGC_FILTER),
    ("OAPIF", OAPIF_URI, ServerFilter.CQL2),
    ("oapif", OAPIF_URI, ServerFilter.CQL2),
    ("arcgisfeatureserver", AFS_URI, ServerFilter.SQL_WHERE),
    ("ogr", "WFS:https://data.geopf.fr/wfs/ows|layername=commune", ServerFilter.OGC_FILTER),
    ("ogr", "OAPIF:https://example.org/ogcapi/collections/communes", ServerFilter.CQL2),
])
def test_vector_web_services(key, uri, server_filter):
    capability = classify(key, uri)
    assert capability.locality is Locality.REMOTE_SERVICE
    assert capability.is_remote_service and capability.is_remote and not capability.is_local
    assert capability.server_filter is server_filter
    assert capability.network_cost is NetworkCost.HIGH and not capability.counts_cheaply
    assert capability.key_list_limit == REMOTE_KEY_LIST_LIMIT


@pytest.mark.parametrize("key, source", [
    ("ogr", "/vsicurl/https://example.org/communes.fgb"),
    ("ogr", "https://example.org/communes.geojson"),
    ("ogr", "/vsis3/bucket/communes.gpkg|layername=communes"),
    ("ogr", "/vsizip//vsicurl/https://example.org/communes.zip/communes.shp"),
    ("delimitedtext", "https://example.org/points.csv?delimiter=;&xField=x&yField=y"),
])
def test_remote_files(key, source):
    capability = classify(key, source)
    assert capability.locality is Locality.REMOTE_FILE
    assert capability.is_remote and not capability.is_remote_service
    assert not capability.counts_cheaply
    assert capability.key_list_limit is None


@pytest.mark.parametrize("key, source", [
    ("ogr", "/data/communes.shp"),
    ("ogr", "C:/data/bdtopo.gpkg|layername=commune"),
    ("ogr", "/vsizip//data/communes.zip/communes.shp"),
    ("spatialite", "dbname='/data/x.sqlite' table=\"t\" (geom)"),
    ("memory", "Point?crs=EPSG:2154"),
    ("delimitedtext", "file:///data/points.csv?delimiter=;"),
])
def test_local_sources(key, source):
    capability = classify(key, source)
    assert capability.is_local and capability.counts_cheaply and not capability.is_remote


def test_databases():
    postgres = classify("postgres", "dbname='x' table=\"public\".\"t\" (geom)")
    assert postgres.locality is Locality.DATABASE and postgres.counts_cheaply
    for key in ("mssql", "oracle", "hana", "MSSQL"):
        capability = classify(key, "")
        assert capability.locality is Locality.DATABASE and not capability.counts_cheaply, key
    assert classify("oracle", "").in_list_max == 1000
    assert classify("mssql", "").in_list_max is None


@pytest.mark.parametrize("source", [GDAL_WMS_XML, "WMS:https://example.org/wms?SERVICE=WMS&LAYERS=ortho"])
def test_gdal_rendered_services(source):
    capability = classify("gdal", source, is_raster=True)
    assert capability.locality is Locality.REMOTE_SERVICE
    assert capability.values is ValueKind.RENDERED and not capability.has_raw_values


def test_raster_values():
    assert classify("gdal", "/data/dem.tif", is_raster=True).has_raw_values
    assert classify("gdal", "WCS:https://example.org/wcs", is_raster=True).has_raw_values
    assert classify("gdal", "/vsicurl/https://example.org/dem.tif", is_raster=True).locality is Locality.REMOTE_FILE
    assert not classify("wms", "crs=EPSG:3857&type=xyz&url=https://tile.example.org/{z}/{x}/{y}.png").has_raw_values
    assert classify("wcs", "url=https://example.org/wcs").has_raw_values


def test_unknown_provider_is_local_unless_its_source_is_a_url():
    assert classify("", "").is_local
    assert classify("something", "/data/x").is_local
    assert classify("something", "https://example.org/x").is_remote


def test_constants_copy_matches_the_domain_list():
    assert REMOTE_PROVIDERS == set(REMOTE_SERVICE_PROVIDERS)


class _Layer:
    def __init__(self, layer_id, provider, source):
        self._id, self._provider, self._source = layer_id, provider, source
        self.reads = 0

    def id(self):
        return self._id

    def providerType(self):
        self.reads += 1
        return self._provider

    def source(self):
        return self._source

    def featureCount(self):
        raise AssertionError("featureCount() of a remote layer")


def test_classify_layer_is_duck_typed():
    assert classify_layer(_Layer("w", "WFS", WFS_URI)).is_remote_service
    assert classify_layer(object()).is_local


def _probe():
    path = Path(__file__).resolve().parents[4] / "adapters" / "qgis" / "source_capability_probe.py"
    spec = importlib.util.spec_from_file_location("fm_test_source_capability_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_probe_caches_by_layer_and_source():
    probe = _probe()
    layer = _Layer("w1", "WFS", WFS_URI)
    first = probe.capability_for_layer(layer)
    assert probe.capability_for_layer(layer) is first
    layer._source = "/vsicurl/https://example.org/communes.fgb"
    layer._provider = "ogr"
    assert probe.capability_for_layer(layer).locality is Locality.REMOTE_FILE
    assert probe.capability_for_layer(None) is None


def test_probe_never_counts_a_remote_layer():
    probe = _probe()
    assert probe.feature_count_or_none(_Layer("w2", "OAPIF", OAPIF_URI)) is None
    assert probe.is_remote_layer(_Layer("w3", "arcgisfeatureserver", AFS_URI))


class TestExtentSubset:
    """A web service cut by the extent of the source, where its features cannot be listed (2026-11-15)."""

    def test_a_wfs_takes_a_filter_by_extent(self):
        from core.domain.source_capability import extent_subset
        capability = classify("WFS", WFS_URI)
        assert capability.takes_extent_subset
        subset = extent_subset(capability, 1.5, -2, 30, 40.25)
        assert subset == ("intersects_bbox($geometry, geom_from_wkt('POLYGON((1.5 -2, 30 -2, 30 40.25, 1.5 40.25, "
                          "1.5 -2))'))")

    @pytest.mark.parametrize("provider, uri", [
        ("OAPIF", OAPIF_URI), ("arcgisfeatureserver", "url='https://example.org/FeatureServer/0'"),
        ("ogr", "/data/a.gpkg|layername=a"), ("postgres", "dbname='gis' table=\"a\""), ("memory", "Point"),
    ])
    def test_no_other_source_does(self, provider, uri):
        """What an OGC API or an ArcGIS service is sent for such an expression was not read: refused as before."""
        from core.domain.source_capability import extent_subset
        capability = classify(provider, uri)
        assert not capability.takes_extent_subset and extent_subset(capability, 0, 0, 1, 1) is None

    def test_coordinates_are_plain_decimals(self):
        """WKT in a filter sent to a server: never an exponent, nine decimals at most, no negative zero."""
        from core.domain.source_capability import extent_subset
        subset = extent_subset(classify("WFS", WFS_URI), 1e-7, -0.0, 652381.123456789123, 6.862e6)
        assert "POLYGON((0.0000001 0, 652381.123456789 0, 652381.123456789 6862000, 0.0000001 6862000, " \
               "0.0000001 0))" in subset
        assert "e" not in subset.split("POLYGON")[1].lower()

    @pytest.mark.parametrize("bounds", [
        (float("nan"), 0, 1, 1), (0, 0, float("inf"), 1), (2, 0, 1, 1), (0, 2, 1, 1), ("a", 0, 1, 1), (None, 0, 1, 1),
    ])
    def test_a_rectangle_that_is_none_gives_no_filter(self, bounds):
        from core.domain.source_capability import extent_subset
        assert extent_subset(classify("WFS", WFS_URI), *bounds) is None

    def test_a_point_is_a_rectangle(self):
        """A source of one point: its extent has no size, the server is still asked what meets it."""
        from core.domain.source_capability import extent_subset
        assert "POLYGON((5 6, 5 6, 5 6, 5 6, 5 6))" in extent_subset(classify("WFS", WFS_URI), 5, 6, 5, 6)

    @pytest.mark.parametrize("bounds", [
        (1.5, -2, 30, 40.25), (0, 0, 0, 0), (-652381.123456789, 6862000, 652381.5, 6862000.25), (1e-7, 0, 1, 1),
    ])
    def test_the_rectangle_is_read_back_from_what_was_written(self, bounds):
        """The validated server dialect reads the bounds of the WKT, and writes the filter again from them."""
        from core.domain.source_capability import extent_expression, extent_of_wkt
        written = extent_expression(*bounds)
        wkt = written.split("geom_from_wkt('")[1].split("')")[0]
        assert extent_of_wkt(wkt) == tuple(float(value) for value in bounds)
        assert extent_expression(*extent_of_wkt(wkt)) == written

    @pytest.mark.parametrize("wkt", [
        "POLYGON((0 0, 10 0, 10 10, 0 10))",                       # not closed
        "POLYGON((0 0, 10 0, 10 10, 0 10, 0 1))",                  # closed elsewhere
        "POLYGON((0 0, 10 1, 10 10, 0 10, 0 0))",                  # not axis-aligned
        "POLYGON((0 0, 0 10, 10 10, 10 0, 0 0))",                  # the other way round
        "POLYGON((0 0, 10 0, 10 10, 0 10, 0 0),(1 1, 2 1, 2 2, 1 2, 1 1))",  # a hole
        "POLYGON((0 0, 1e3 0, 1e3 10, 0 10, 0 0))",                # an exponent
        "POLYGON((0 0 5, 10 0 5, 10 10 5, 0 10 5, 0 0 5))",        # a third coordinate
        "POLYGON((0 0, 10 0, 10 10, 0 10, 0 0)) ; DROP",           # something after
        "MULTIPOLYGON(((0 0, 10 0, 10 10, 0 10, 0 0)))", "POINT(0 0)", "", None, 5,
        "POLYGON((" + ", ".join(["0 0"] * 200) + "))",             # too long
    ])
    def test_nothing_else_is_read_as_an_extent(self, wkt):
        from core.domain.source_capability import extent_of_wkt
        assert extent_of_wkt(wkt) is None
