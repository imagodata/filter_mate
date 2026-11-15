# -*- coding: utf-8 -*-
"""A web service target is cut by the extent of the source, in a real (headless) QGIS, with no network.

    docker run --rm --network none -v "$PWD:/src:ro" qgis/qgis:ltr \\
        python3 /src/tests/qgis_headless/check_stream_extent_clip.py

2026-11-15. A WFS target was refused as soon as more than 500 of its features matched the source (their keys go in
every request), or when it had no stable key at all; a WMS, WMTS or tile layer was refused as a target whatever the
source. Two servers written here stand for them:

* a WFS 2.0 server of 5000 points that honours BBOX, the OGC filters QGIS writes (BBOX, comparisons, key lists) and
  paging, and counts what it is asked. Past 500 keys the layer gets a filter by extent the server answers
  (``intersects_bbox`` in its subset, sent as ``<fes:BBOX>``), with a warning saying it is a cut by extent;
* a tile server (XYZ) whose tiles say their level and position by their color. The layer is captured in the area the
  source keeps, within a budget of pixels, then cut by the source as a local raster is; Unfilter gives the service
  back.

Prints one PASS / FAIL line per check; exits with 1 when one failed.
"""
import math
import os
import re
import struct
import sys
import tempfile
import threading
import time
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from qgis.core import (  # noqa: E402
    Qgis, QgsApplication, QgsCoordinateReferenceSystem, QgsDataSourceUri, QgsFeatureRequest, QgsGeometry, QgsProject,
    QgsRasterLayer, QgsRectangle, QgsVectorLayer,
)

TOTAL = 5000  # points, a row of 100 by 50, 10 m apart, from 0, 0 in Web Mercator
RESULTS = []
ASKED = []  # one entry per GetFeature of the WFS server
REFUSED = []  # the status of every request a server refused: QGIS shows an empty layer for them, and says nothing
TOO_LONG = []  # the length of every request the type ``strict`` refused on purpose
# A server stops reading an address at a length of its own: 8 KB is common (Apache, nginx, Tomcat). The type
# ``strict`` does the same: read on a real WFS (2026-11-15), a list of 25 keys is set and one of 100 is refused.
STRICT_MAX = 8000
TILES = []  # (name, z, x, y) of every tile asked of the tile server
MAPS = []  # (name, width, height, (x_min, y_min, x_max, y_max)) of every GetMap asked of the WMS server
WORLD = 20037508.342789244  # half the side of the square of Web Mercator


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {str(detail)[:600]}" if not condition else ""), flush=True)


def _link(source, target):
    try:
        os.symlink(source, target)
    except OSError:
        if os.name != "nt":
            raise
        import subprocess
        subprocess.run(["cmd", "/c", "mklink", "/J", target, source], check=True, capture_output=True)


# --- a WFS 2.0 server ---------------------------------------------------------------------------------------------------

def capabilities(base, types):
    listed = "".join(
        f"<wfs:FeatureType><wfs:Name>fm:{name}</wfs:Name><wfs:Title>{name}</wfs:Title>"
        "<wfs:DefaultCRS>urn:ogc:def:crs:EPSG::3857</wfs:DefaultCRS><ows:WGS84BoundingBox>"
        "<ows:LowerCorner>-1 -1</ows:LowerCorner><ows:UpperCorner>1 1</ows:UpperCorner></ows:WGS84BoundingBox>"
        "</wfs:FeatureType>" for name in types)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<wfs:WFS_Capabilities version="2.0.0" xmlns:wfs="http://www.opengis.net/wfs/2.0" xmlns:ows="http://www.opengis.net/ows/1.1"
  xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:fes="http://www.opengis.net/fes/2.0" xmlns:fm="http://fm.example/ns">
 <ows:OperationsMetadata>
  <ows:Operation name="GetCapabilities"><ows:DCP><ows:HTTP><ows:Get xlink:href="{base}"/></ows:HTTP></ows:DCP></ows:Operation>
  <ows:Operation name="DescribeFeatureType"><ows:DCP><ows:HTTP><ows:Get xlink:href="{base}"/></ows:HTTP></ows:DCP></ows:Operation>
  <ows:Operation name="GetFeature"><ows:DCP><ows:HTTP><ows:Get xlink:href="{base}"/></ows:HTTP></ows:DCP>
   <ows:Parameter name="resultType"><ows:AllowedValues><ows:Value>results</ows:Value><ows:Value>hits</ows:Value></ows:AllowedValues></ows:Parameter>
  </ows:Operation>
  <ows:Constraint name="ImplementsResultPaging"><ows:NoValues/><ows:DefaultValue>TRUE</ows:DefaultValue></ows:Constraint>
  <ows:Constraint name="CountDefault"><ows:NoValues/><ows:DefaultValue>1000</ows:DefaultValue></ows:Constraint>
 </ows:OperationsMetadata>
 <wfs:FeatureTypeList>{listed}</wfs:FeatureTypeList>
 <fes:Filter_Capabilities><fes:Conformance>
  <fes:Constraint name="ImplementsMinSpatialFilter"><ows:NoValues/><ows:DefaultValue>TRUE</ows:DefaultValue></fes:Constraint>
 </fes:Conformance><fes:Spatial_Capabilities><fes:SpatialOperators><fes:SpatialOperator name="BBOX"/></fes:SpatialOperators>
 </fes:Spatial_Capabilities></fes:Filter_Capabilities>
</wfs:WFS_Capabilities>"""


def schema(name, keyed):
    key = '<xsd:element name="id" type="xsd:int" minOccurs="0"/>' if keyed else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:fm="http://fm.example/ns"
  targetNamespace="http://fm.example/ns" elementFormDefault="qualified">
 <xsd:import namespace="http://www.opengis.net/gml/3.2" schemaLocation="http://schemas.opengis.net/gml/3.2.1/gml.xsd"/>
 <xsd:complexType name="{name}Type"><xsd:complexContent><xsd:extension base="gml:AbstractFeatureType"><xsd:sequence>
  {key}<xsd:element name="num" type="xsd:int" minOccurs="0"/><xsd:element name="nom" type="xsd:string" minOccurs="0"/>
  <xsd:element name="geom" type="gml:PointPropertyType" minOccurs="0"/>
 </xsd:sequence></xsd:extension></xsd:complexContent></xsd:complexType>
 <xsd:element name="{name}" type="fm:{name}Type" substitutionGroup="gml:AbstractFeature"/>
</xsd:schema>"""


def position(number):
    return (number % 100) * 10.0, (number // 100) * 10.0


def _numbers(text):
    return [float(value) for value in text.replace(",", " ").split()]


def matching(query):
    """The numbers of the points a GetFeature asks for: its BBOX, and the OGC filter QGIS wrote.

    Read from the filter: every envelope (the extent of the subset, and the rectangle of the request QGIS adds), the
    list of keys, and ``num < n``. All of them are joined by And in what the checks send.
    """
    kept = list(range(TOTAL))
    if "bbox" in query:
        x1, y1, x2, y2 = (float(value) for value in query["bbox"].split(",")[:4])
        kept = [n for n in kept if x1 <= position(n)[0] <= x2 and y1 <= position(n)[1] <= y2]
    # QGIS writes the elements bare in the filter of a subset, and each with its namespaces once it adds the
    # rectangle of a request to it (about 280 bytes a key then): both are read.
    text = re.sub(r"<(/?)([\w:]+)[^>]*>", r"<\1\2>", query.get("filter", ""))
    for lower, upper in re.findall(r"<gml:lowerCorner>([^<]+)</gml:lowerCorner>\s*<gml:upperCorner>([^<]+)</gml:upperCorner>",
                                   text):
        (x1, y1), (x2, y2) = _numbers(lower), _numbers(upper)
        kept = [n for n in kept if x1 <= position(n)[0] <= x2 and y1 <= position(n)[1] <= y2]
    for below in re.findall(r"<fes:PropertyIsLessThan>\s*<fes:ValueReference>(?:fm:)?num</fes:ValueReference>\s*"
                            r"<fes:Literal>(\d+)</fes:Literal>", text):
        kept = [n for n in kept if n < int(below)]
    keys = {int(value) for value in re.findall(
        r"<fes:ValueReference>(?:fm:)?id</fes:ValueReference>\s*<fes:Literal>(\d+)</fes:Literal>", text)}
    if keys:
        kept = [n for n in kept if n in keys]
    return kept


class WfsHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_error(self, code, message=None, explain=None):
        # Among them 414: http.server reads 65536 bytes of a request line, and a list of keys is about 190 bytes
        # a key in the address QGIS writes (231 keys and the rectangle of a request went past it, 2026-11-15).
        REFUSED.append(int(code))
        return super().send_error(code, message, explain)

    def do_GET(self):
        query = {key.lower(): value[0] for key, value in parse_qs(urlsplit(self.path).query).items()}
        request = query.get("request", "").lower()
        base = f"http://127.0.0.1:{self.server.server_port}/wfs"
        name = (query.get("typenames") or query.get("typename") or "fm:keyed").split(":")[-1]
        keyed = name in ("keyed", "strict")
        if name == "strict" and request == "getfeature" and len(self.path) > STRICT_MAX:
            TOO_LONG.append(len(self.path))
            self.send_response(414)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if request == "getcapabilities":
            body = capabilities(base, ("keyed", "keyless", "strict"))
        elif request == "describefeaturetype":
            body = schema(name, keyed)
        elif request == "getfeature":
            kept = matching(query)
            first = int(query.get("startindex", 0))
            count = int(query.get("count", query.get("maxfeatures", 1000)))
            hits = query.get("resulttype", "") == "hits"
            sent = [] if hits else kept[first:first + count]
            ASKED.append({"type": name, "filter": query.get("filter", ""), "bbox": query.get("bbox", ""),
                          "hits": hits, "sent": len(sent), "matched": len(kept)})
            members = []
            for number in sent:
                x, y = position(number)
                key = f"<fm:id>{number}</fm:id>" if keyed else ""
                members.append(
                    f'<wfs:member><fm:{name} gml:id="{name}.{number}">{key}<fm:num>{number}</fm:num><fm:nom>p{number}</fm:nom>'
                    f'<fm:geom><gml:Point gml:id="g.{number}" srsName="urn:ogc:def:crs:EPSG::3857"><gml:pos>{x} {y}</gml:pos>'
                    f'</gml:Point></fm:geom></fm:{name}></wfs:member>')
            body = (f'<?xml version="1.0" encoding="UTF-8"?><wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0" '
                    f'xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:fm="http://fm.example/ns" numberMatched="{len(kept)}" '
                    f'numberReturned="{len(sent)}" timeStamp="2026-11-15T00:00:00Z">{"".join(members)}</wfs:FeatureCollection>')
        else:
            self.send_error(400)
            return
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def wfs_layer(port, name):
    uri = QgsDataSourceUri()  # as wfs_catalog.open_layer builds it
    for key, value in (("url", f"http://127.0.0.1:{port}/wfs"), ("typename", f"fm:{name}"), ("version", "auto"),
                       ("pagingEnabled", "true"), ("restrictToRequestBBOX", "1"), ("srsname", "EPSG:3857")):
        uri.setParam(key, value)
    layer = QgsVectorLayer(uri.uri(False), name, "WFS")
    QgsProject.instance().addMapLayer(layer)
    return layer


def shown(layer):
    """The numbers of the points the layer gives, read where they all are."""
    request = QgsFeatureRequest().setFilterRect(QgsRectangle(-100, -100, 2000, 1000))
    return sorted(feature["num"] for feature in layer.getFeatures(request))


def inside(x1, y1, x2, y2):
    return sorted(n for n in range(TOTAL) if x1 <= position(n)[0] <= x2 and y1 <= position(n)[1] <= y2)


def check_dialect(fields):
    """The validated server dialect reads one function call, the filter by extent, and nothing near it."""
    from filter_mate.adapters.qgis.server_filter_translation import translate
    from filter_mate.core.filter.server_dialect import TranslationStatus
    box = "intersects_bbox($geometry, geom_from_wkt('POLYGON((10 20, 30 20, 30 40.5, 10 40.5, 10 20))'))"
    result = translate(box, "wfs", fields)
    check("dialect: the filter by extent is read, and proved to be an OGC filter (BBOX)",
          result.status == TranslationStatus.FULL and result.subset_expression == box and "BBOX" in result.server_expression,
          (result.status, result.subset_expression[:80], result.server_expression[:160], result.reason))
    spaced = translate("intersects_bbox( $geometry , geom_from_wkt( 'polygon((10 20,30 20,30 40.5,10 40.5,10 20))' ) )",
                       "wfs", fields)
    check("dialect: it is written again from its bounds, whatever its spelling",
          spaced.status == TranslationStatus.FULL and spaced.subset_expression == box, spaced.subset_expression[:120])
    both = translate('"num" < 100 AND ' + box, "wfs", fields)
    check("dialect: beside an attribute filter", both.status == TranslationStatus.FULL
          and both.subset_expression == '("num" < 100) AND ' + box, (both.status, both.subset_expression[:120]))
    for label, expression in (
            ("another predicate", box.replace("intersects_bbox", "intersects")),
            ("a geometry that is not the one of the feature", box.replace("$geometry", "buffer($geometry, 1)")),
            ("a rectangle that is not one", box.replace("30 20,", "30 21,")),
            ("a third argument", box[:-1] + ", 1)"),
            ("a geometry read from a field", box.replace("'POLYGON((10 20, 30 20, 30 40.5, 10 40.5, 10 20))'", '"nom"')),
            ("its negation", "NOT " + box),
            ("an unknown function", "length(\"nom\") > 2"),
    ):
        refused = translate(expression, "wfs", fields)
        check(f"dialect: {label} stays refused", refused.status == TranslationStatus.NONE,
              (refused.status, refused.subset_expression[:100]))
    for dialect in ("arcgis", "oapif", "mssql"):
        check(f"dialect: {dialect} takes no filter by extent",
              translate(box, dialect, fields).status == TranslationStatus.NONE)


def check_refused_keys(operations, port, crs, exact):
    """A service that refuses a long list of keys, as a real one does far under 500 keys: cut by extent instead."""
    strict = wfs_layer(port, "strict")
    check("the WFS layer that refuses long requests opens", strict.isValid())

    def info_of(report):
        return next(iter((report.details.get("layers") or {}).values()), {})

    # Six keys: a request the server reads.
    tiny = QgsGeometry.fromWkt("POLYGON((95 95, 125 95, 125 115, 95 115, 95 95))")  # 3 x 2 points
    del TOO_LONG[:]
    report = operations.cross_filter_by_geometry(tiny, crs, [strict.id()])
    if exact:
        check("a short list of keys: set as it is, the exact filter",
              not report.failed and '"id" IN' in strict.subsetString() and "by_extent" not in info_of(report)
              and shown(strict) == inside(95, 95, 125, 115) and not TOO_LONG,
              (report.failed, strict.subsetString()[:80], TOO_LONG))
    operations.clear_filters([strict.id()])
    # 231 keys, under 500: about 43 KB of address. It was "subset rejected by the provider", the layer left whole.
    medium = QgsGeometry.fromWkt("POLYGON((95 95, 305 95, 305 205, 95 205, 95 95))")
    del TOO_LONG[:]
    report = operations.cross_filter_by_geometry(medium, crs, [strict.id()])
    info = info_of(report)
    if exact:
        check("a list of keys the service refuses: cut by the extent of the source instead, and says why",
              not report.failed and strict.subsetString().startswith("intersects_bbox(") and TOO_LONG
              and "refused the list" in str(info.get("by_extent")) and info.get("kept") is None,
              (report.failed, strict.subsetString()[:80], TOO_LONG[:2], info))
    else:
        check("a QGIS that cannot check a service: cut by the extent of the source, nothing refused",
              not report.failed and strict.subsetString().startswith("intersects_bbox(") and not TOO_LONG,
              (report.failed, strict.subsetString()[:80], TOO_LONG[:2], info))
    check("a list of keys the service refuses: the layer gives what meets the extent",
          shown(strict) == inside(95, 95, 305, 205), len(shown(strict)))
    operations.clear_filters([strict.id()])
    check("a list of keys the service refuses: Unfilter gives the whole service back",
          strict.subsetString() == "" and len(shown(strict)) == TOTAL, strict.subsetString()[:80])
    # AND NOT has no cut by extent: refused as before, the previous filter kept.
    strict.setSubsetString('"num" < 4000')
    report = operations.cross_filter_by_geometry(medium, crs, [strict.id()], operator="AND NOT")
    check("a list of keys the service refuses, under AND NOT: refused, the previous filter kept",
          bool(report.failed) and strict.subsetString() == '"num" < 4000', (report.failed, strict.subsetString()[:80]))
    strict.setSubsetString("")
    QgsProject.instance().removeMapLayer(strict.id())


def check_wfs(operations):
    """A WFS target under a source of more than 500 features, of fewer, and a WFS with no key at all."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), WfsHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    keyed, keyless = wfs_layer(server.server_port, "keyed"), wfs_layer(server.server_port, "keyless")
    check("the two layers of the local WFS server open", keyed.isValid() and keyless.isValid())
    crs = QgsCoordinateReferenceSystem("EPSG:3857")

    def layers(report):
        return (report.details.get("layers") or {})

    check_dialect(keyed.fields())
    large = QgsGeometry.fromWkt("POLYGON((95 95, 705 95, 505 405, 95 405, 95 95))")  # a trapeze: 61 x 31 in its box
    from filter_mate.adapters.qgis.remote_materializer import supports_reply_validation
    from filter_mate.adapters.qgis.server_subset_job import transfer_mode_for_layer
    from filter_mate.core.filter.server_transfer_policy import REFUSE
    # What this QGIS can do (the versions of the CI differ): set the filter of a WFS at all (from 3.24), and check
    # what a service answers, without which no feature is read (from 3.26, and from 3.36 under Python 3.12).
    exact = supports_reply_validation()
    print(f"   this QGIS sets a WFS filter: {transfer_mode_for_layer(keyed)}; reads a service: {exact}", flush=True)
    if transfer_mode_for_layer(keyed) == REFUSE:
        # Before 3.24 the setter of a WFS filter crashes: refused, by extent as by keys, the layer left alone.
        for layer in (keyed, keyless):
            report = operations.cross_filter_by_geometry(large, crs, [layer.id()])
            check(f"QGIS that sets no WFS filter, {layer.name()}: refused with its reason, the layer left as it was",
                  bool(report.failed) and layer.subsetString() == "" and len(shown(layer)) == TOTAL,
                  (report.failed, layer.subsetString()[:80]))
        check("the server refused no request", not REFUSED, REFUSED)
        server.shutdown()
        return

    # Fewer than 500 features match: their keys are listed, as before.
    small = QgsGeometry.fromWkt("POLYGON((95 95, 155 95, 155 135, 95 135, 95 95))")  # 6 x 4 points = 24
    few = inside(95, 95, 155, 135)
    started = time.perf_counter()
    report = operations.cross_filter_by_geometry(small, crs, [keyed.id()])
    elapsed = time.perf_counter() - started
    info = next(iter(layers(report).values()), {})
    # The private copy of the service asks again the GetFeature COUNT=1 the layer sent when it opened, which QGIS
    # answers from its network cache. Read too early by the observer of replies, that reply never signalled: the
    # copy waited for the network timeout of QGIS (60 s), and the read was counted as failed.
    check("a service read right after it opened is not held by a reply of the network cache", elapsed < 20,
          round(elapsed, 1))
    if exact:
        check("under 500 features: the keys are listed, nothing is said of an extent",
              not report.error and not report.failed and '"id" IN' in keyed.subsetString() and "by_extent" not in info
              and info.get("kept") == len(few) == 24, (report.error, report.failed, keyed.subsetString()[:80], info))
    else:
        # It was refused there ("The service filter cannot be proved complete"): nothing is read, so nothing is
        # listed, whatever the number of features.
        check("a QGIS that cannot check a service: cut by the extent of the source, and says why",
              not report.error and not report.failed and keyed.subsetString().startswith("intersects_bbox(")
              and "this version of QGIS" in str(info.get("by_extent")),
              (report.error, report.failed, keyed.subsetString()[:80], info))
    check("under 500 features: the layer gives them", shown(keyed) == few, len(shown(keyed)))
    operations.clear_filters([keyed.id()])

    # More than 500: it was refused ("more than the 500 sent to a web service").
    box = inside(95, 95, 705, 405)
    del ASKED[:]
    report = operations.cross_filter_by_geometry(large, crs, [keyed.id()])
    info = next(iter(layers(report).values()), {})
    check("over 500 features: the layer is cut by the extent of the source, and says so",
          not report.error and not report.failed and keyed.subsetString().startswith("intersects_bbox($geometry, ")
          and "extent of the source" in str(info.get("by_extent")), (report.error, report.failed, keyed.subsetString()[:90], info))
    del ASKED[:]
    given = shown(keyed)
    check("over 500 features: the server answers what meets the extent, every feature of it",
          given == box and len(box) == 61 * 31, (len(given), len(box)))
    check("over 500 features: the server was asked with a BBOX filter, not a list of keys",
          ASKED and all("<fes:BBOX>" in entry["filter"] and "Literal" not in entry["filter"] for entry in ASKED),
          [entry["filter"][:200] for entry in ASKED[:2]])
    # Narrowed with an attribute filter of the user, then widened: the filter by extent combines as any other.
    report = operations.cross_filter_by_geometry(small, crs, [keyed.id()], operator="AND")
    check("AND under an extent: the keys of the smaller source, inside the extent", not report.failed
          and shown(keyed) == few, (report.failed, keyed.subsetString()[:120]))
    operations.clear_filters([keyed.id()])
    check("Unfilter gives the whole service back", keyed.subsetString() == "" and len(shown(keyed)) == TOTAL,
          keyed.subsetString())
    # AND NOT is never cut by an extent: it would take away features that do not match the source.
    keyed.setSubsetString('"num" < 4000')
    report = operations.cross_filter_by_geometry(large, crs, [keyed.id()], operator="AND NOT")
    check("AND NOT over 500 features: refused, the previous filter kept", report.failed
          and keyed.subsetString() == '"num" < 4000', (report.failed, keyed.subsetString()))
    keyed.setSubsetString("")
    # A filter of the user stays, and the extent is added to it: the server is asked both.
    keyed.setSubsetString('"num" < 2500')
    del ASKED[:]
    report = operations.cross_filter_by_geometry(large, crs, [keyed.id()], operator="AND")
    wanted = [n for n in box if n < 2500]
    given = shown(keyed)
    check("AND over 500 features on a filtered layer: the filter of the user and the extent, both asked",
          not report.failed and '"num" < 2500' in keyed.subsetString() and "intersects_bbox(" in keyed.subsetString()
          and given == wanted and ASKED and "PropertyIsLessThan" in ASKED[-1]["filter"],
          (report.failed, keyed.subsetString()[:140], len(given), len(wanted)))
    operations.clear_filters([keyed.id()])
    keyed.setSubsetString("")
    # Disjoint is never cut by an extent: what lies outside a rectangle is a negation, which the validated WFS
    # dialect does not write (what a server answers for a feature without geometry is not proven).
    report = operations.cross_filter_by_geometry(large, crs, [keyed.id()], predicates=("Disjoint",))
    check("Disjoint over 500 features: refused, the layer left as it was", report.failed
          and keyed.subsetString() == "", (report.failed, keyed.subsetString()[:80]))
    operations.clear_filters([keyed.id()])

    # No stable key: nothing can be listed, so nothing is read; the server is asked the extent.
    del ASKED[:]
    report = operations.cross_filter_by_geometry(small, crs, [keyless.id()])
    info = next(iter(layers(report).values()), {})
    # (One feature without filter is what QGIS asks when a provider opens, as the copy a subset is tried on does.)
    unfiltered = [entry for entry in ASKED if entry["type"] == "keyless" and "<fes:BBOX>" not in entry["filter"]
                  and entry["sent"] > 1]
    check("no stable key: cut by the extent of the source, without reading the service first",
          not report.failed and keyless.subsetString().startswith("intersects_bbox(") and not unfiltered
          and "extent of the source" in str(info.get("by_extent")),
          (report.failed, keyless.subsetString()[:80], unfiltered[:2], info))
    check("no stable key: the layer gives what meets the extent", shown(keyless) == few, len(shown(keyless)))
    operations.clear_filters([keyless.id()])
    from filter_mate.core.filter.server_transfer_policy import ASYNC
    if transfer_mode_for_layer(keyed) == ASYNC:
        check_refused_keys(operations, server.server_port, crs, exact)
    else:
        # From 3.24 to 3.31 QGIS sets a WFS filter without asking the service anything: a list it refuses is not
        # seen when it is set, only as an empty layer when it is read (as before 2026-11-15).
        print("SKIP a list of keys the service refuses: this QGIS sets a WFS filter without preparing it", flush=True)
    check("the server refused no request (QGIS shows an empty layer for a refused one, and says nothing)",
          not REFUSED, REFUSED)
    for layer in (keyed, keyless):
        QgsProject.instance().removeMapLayer(layer.id())
    server.shutdown()


# --- web maps: a tile server (XYZ) and a WMS ---------------------------------

def png(color, width=256, height=256):
    """A PNG of one color (red, green, blue, alpha), written here: no image library off the main thread."""
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    row = b"\x00" + bytes(color) * width
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(row * height, 1)) + chunk(b"IEND", b""))


def tile_color(z, x, y):
    """A tile says its level and its position by its color."""
    return (x * 40) % 256, (y * 40) % 256, (z * 20) % 256, 255


def tile_at(z, x_map, y_map):
    side = 2 * WORLD / 2 ** z
    return int(math.floor((x_map + WORLD) / side)), int(math.floor((WORLD - y_map) / side))


WMS_COLOR = (10, 200, 30, 255)


def wms_capabilities(base):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<WMS_Capabilities version="1.3.0" xmlns="http://www.opengis.net/wms" xmlns:xlink="http://www.w3.org/1999/xlink">
<Service><Name>WMS</Name><Title>fm</Title><OnlineResource xlink:type="simple" xlink:href="{base}"/>
 <MaxWidth>2048</MaxWidth><MaxHeight>2048</MaxHeight></Service>
<Capability>
 <Request>
  <GetCapabilities><Format>text/xml</Format><DCPType><HTTP><Get><OnlineResource xlink:type="simple" xlink:href="{base}?"/>
   </Get></HTTP></DCPType></GetCapabilities>
  <GetMap><Format>image/png</Format><DCPType><HTTP><Get><OnlineResource xlink:type="simple" xlink:href="{base}?"/>
   </Get></HTTP></DCPType></GetMap>
 </Request>
 <Exception><Format>XML</Format></Exception>
 <Layer><Title>root</Title><CRS>EPSG:3857</CRS>
  <Layer queryable="0"><Name>plan</Name><Title>plan</Title><CRS>EPSG:3857</CRS>
   <EX_GeographicBoundingBox><westBoundLongitude>-1</westBoundLongitude><eastBoundLongitude>1</eastBoundLongitude>
    <southBoundLatitude>-1</southBoundLatitude><northBoundLatitude>1</northBoundLatitude></EX_GeographicBoundingBox>
   <BoundingBox CRS="EPSG:3857" minx="-111319" miny="-111325" maxx="111319" maxy="111325"/>
  </Layer>
 </Layer>
</Capability></WMS_Capabilities>"""


class MapHandler(BaseHTTPRequestHandler):
    """``/<name>/<z>/<x>/<y>.png`` (tiles, holes: every other tile fails, dead: none answers) and ``/<name>`` (WMS)."""

    def log_message(self, *args):
        pass

    def _send(self, data, kind):
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parts = urlsplit(self.path)
        steps = parts.path.strip("/").split("/")
        name = steps[0]
        if len(steps) == 4:
            z, x, y = int(steps[1]), int(steps[2]), int(steps[3].split(".")[0])
            TILES.append((name, z, x, y))
            if name == "dead" or (name == "holes" and (x + y) % 2):
                self.send_error(404 if name == "dead" else 500)
                return
            self._send(png(tile_color(z, x, y)), "image/png")
            return
        query = {key.lower(): value[0] for key, value in parse_qs(parts.query).items()}
        request = query.get("request", "").lower()
        if request == "getcapabilities":
            self._send(wms_capabilities(f"http://127.0.0.1:{self.server.server_port}/{name}").encode("utf-8"), "text/xml")
        elif request == "getmap":
            width, height = int(query["width"]), int(query["height"])
            MAPS.append((name, width, height, tuple(float(value) for value in query["bbox"].split(","))))
            if name == "wmsdead":  # what a WMS answers when it cannot draw: HTTP 200, and a report
                self._send(b'<?xml version="1.0"?><ServiceExceptionReport><ServiceException>no</ServiceException>'
                           b'</ServiceExceptionReport>', "text/xml")
                return
            self._send(png(WMS_COLOR, width, height), "image/png")
        else:
            self.send_error(400)


def pixel(layer, x_map, y_map):
    """The (red, green, blue, alpha) the file of a cut layer holds at a point; None outside its grid."""
    from osgeo import gdal
    dataset = gdal.Open(layer.source())
    x0, dx, _, y0, _, dy = dataset.GetGeoTransform()
    column, row = int((x_map - x0) / dx), int((y_map - y0) / dy)
    if not (0 <= column < dataset.RasterXSize and 0 <= row < dataset.RasterYSize) or dataset.RasterCount != 4:
        return None
    return tuple(int(dataset.GetRasterBand(band).ReadAsArray(column, row, 1, 1)[0][0]) for band in range(1, 5))


def grid(layer):
    from osgeo import gdal
    dataset = gdal.Open(layer.source())
    return dataset.RasterXSize, dataset.RasterYSize, abs(dataset.GetGeoTransform()[1]), dataset.RasterCount


def check_web_maps(operations):
    """Tiles (XYZ) and a WMS as targets: captured in the area the source keeps, cut, and given back by Unfilter."""
    from filter_mate.adapters.qgis import point_cloud_capability as capability
    from filter_mate.adapters.qgis.coverage_layers import cache
    from filter_mate.config.config import ENV_VARS
    cache.set_cache_root(tempfile.mkdtemp())
    options = ENV_VARS.setdefault("CONFIG_DATA", {}).setdefault("APP", {}).setdefault("OPTIONS", {})
    options.setdefault("CROSS_FILTER", {})["web_map_target_max_pixels"] = {"value": 1000000}
    options.setdefault("RASTER", {})["enabled"] = {"value": True}  # the option of the dock, off when unset
    server = ThreadingHTTPServer(("127.0.0.1", 0), MapHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_port
    crs = QgsCoordinateReferenceSystem("EPSG:3857")

    def tiles(name):
        uri = f"type=xyz&url=http://127.0.0.1:{port}/{name}/{{z}}/{{x}}/{{y}}.png&zmin=0&zmax=14&crs=EPSG:3857"
        layer = QgsRasterLayer(uri, name, "wms")
        QgsProject.instance().addMapLayer(layer)
        return layer, layer.source()  # as the layer says it: QGIS 4 writes the address of a WMS its own way

    def wms(name):
        uri = f"crs=EPSG:3857&format=image/png&layers=plan&styles=&url=http://127.0.0.1:{port}/{name}"
        layer = QgsRasterLayer(uri, name, "wms")
        QgsProject.instance().addMapLayer(layer)
        return layer, layer.source()

    def info_of(report):
        return next(iter((report.details.get("layers") or {}).values()), {})

    basemap, basemap_uri = tiles("tiles")
    check("tiles: the layer opens, and is listed among the targets of a vector source, not greyed",
          basemap.isValid() and capability.is_listed_coverage_target(basemap, True)
          and not capability.is_listed_rendered_raster(basemap, True) and capability.is_non_analysis_raster(basemap),
          basemap.isValid())
    basemap.renderer().setOpacity(0.6)
    was = basemap.renderer().type()

    # A triangle of 200 km by 150 km. A million pixels: level 10 (153 m) is past the budget, level 9 (306 m) is not.
    triangle = QgsGeometry.fromWkt("POLYGON((100000 100000, 300000 100000, 200000 250000, 100000 100000))")
    del TILES[:]
    report = operations.cross_filter_by_geometry(triangle, crs, [basemap.id()])
    info = info_of(report)
    level = 2 * WORLD / 256 / 2 ** 9
    check("tiles: cut by the source, and says it is a still image at a resolution",
          not report.error and not report.failed and "still image" in str(info.get("captured"))
          and "306" in str(info.get("captured")), (report.error, report.failed, info))
    check("tiles: the layer is now a local file, with its opacity",
          basemap.isValid() and basemap.providerType() == "gdal" and basemap.source().endswith(".vrt")
          and abs(basemap.renderer().opacity() - 0.6) < 1e-6 and basemap.renderer().alphaBand() == 4,
          (basemap.providerType(), basemap.source()[-40:], basemap.renderer().opacity(), basemap.renderer().alphaBand()))
    columns, rows, cell, bands = grid(basemap)
    check("tiles: captured at the finest level the budget affords, on the pixels of that level",
          bands == 4 and abs(cell - level) < 1e-6 and columns * rows <= 1000000 and columns >= 654 and rows >= 490,
          (columns, rows, cell, level, bands))
    levels = sorted({z for _name, z, _x, _y in TILES})
    check("tiles: only the tiles of that level over the area kept were asked", levels == [9] and 0 < len(TILES) <= 25,
          (levels, len(TILES)))
    inside_tile = tile_at(9, 200000, 150000)
    check("tiles: a pixel inside the source holds the color of its tile",
          pixel(basemap, 200000, 150000) == tile_color(9, *inside_tile), (pixel(basemap, 200000, 150000), inside_tile))
    check("tiles: a pixel of the capture outside the source is transparent",
          (pixel(basemap, 110000, 240000) or (0, 0, 0, 255))[3] == 0, pixel(basemap, 110000, 240000))

    # AND with a smaller zone inside the triangle: a new capture, finer, of the area both keep.
    square = QgsGeometry.fromWkt("POLYGON((180000 120000, 220000 120000, 220000 160000, 180000 160000, 180000 120000))")
    del TILES[:]
    report = operations.cross_filter_by_geometry(square, crs, [basemap.id()], operator="AND")
    columns, rows, cell, _bands = grid(basemap)
    check("tiles, AND: the area both sources keep, captured again at a finer level",
          not report.failed and cell < level and columns * rows <= 1000000
          and (pixel(basemap, 200000, 150000) or (0, 0, 0, 0))[3] == 255 and pixel(basemap, 250000, 110000) is None,
          (report.failed, columns, rows, cell, pixel(basemap, 200000, 150000), pixel(basemap, 250000, 110000)))
    # AND with a zone that meets nothing of it: nothing is kept, and the service is asked nothing.
    away = QgsGeometry.fromWkt("POLYGON((900000 900000, 950000 900000, 950000 950000, 900000 950000, 900000 900000))")
    del TILES[:]
    report = operations.cross_filter_by_geometry(away, crs, [basemap.id()], operator="AND")
    check("tiles, AND with a zone elsewhere: nothing kept, no tile asked", not report.failed and not TILES
          and basemap.isValid() and basemap.providerType() == "gdal", (report.failed, len(TILES)))
    operations.clear_filters([basemap.id()])
    check("tiles: Unfilter gives the live service back, as it was",
          basemap.isValid() and basemap.providerType() == "wms" and basemap.source() == basemap_uri
          and basemap.renderer().type() == was and abs(basemap.renderer().opacity() - 0.6) < 1e-6,
          (basemap.providerType(), basemap.renderer().type(), basemap.renderer().opacity()))

    # Disjoint: what lies outside the source, over the whole service, as coarse as the budget makes it.
    del TILES[:]
    report = operations.cross_filter_by_geometry(triangle, crs, [basemap.id()], predicates=("Disjoint",))
    info = info_of(report)
    columns, rows, cell, _bands = grid(basemap) if basemap.providerType() == "gdal" else (0, 0, 0, 0)
    check("tiles, Disjoint: the whole service outside the source, within the budget, and it says how coarse",
          not report.failed and 0 < columns * rows <= 1000000 and "still image" in str(info.get("captured"))
          and (pixel(basemap, 200000, 150000) or (0, 0, 0, 255))[3] == 0
          and (pixel(basemap, -5000000, 3000000) or (0, 0, 0, 0))[3] == 255,
          (report.failed, columns, rows, cell, info))
    operations.clear_filters([basemap.id()])

    # A service that fails for every other tile: the cut is made, and says the image may have holes.
    holes, _uri = tiles("holes")
    report = operations.cross_filter_by_geometry(triangle, crs, [holes.id()])
    info = info_of(report)
    check("tiles with holes: cut, and says some requests were not answered",
          not report.failed and holes.providerType() == "gdal" and "not answered" in str(info.get("captured")),
          (report.failed, info))
    operations.clear_filters([holes.id()])
    # A service that answers nothing: refused, the layer stays the live service.
    dead, dead_uri = tiles("dead")
    report = operations.cross_filter_by_geometry(triangle, crs, [dead.id()])
    check("tiles that never answer: refused with its reason, the layer left as it was",
          bool(report.failed) and "answered none" in str(report.failed) and dead.providerType() == "wms"
          and dead.source() == dead_uri and dead.isValid(), (report.failed, dead.providerType()))

    # A WMS: no levels, the resolution is the one the budget gives; GetMap is asked over the area kept only.
    plan, plan_uri = wms("wms")
    check("WMS: the layer opens, and is listed among the targets", plan.isValid()
          and capability.is_listed_coverage_target(plan, True), plan.isValid())
    wedge = QgsGeometry.fromWkt("POLYGON((-50000 -50000, 50000 -50000, 0 60000, -50000 -50000))")
    del MAPS[:]
    report = operations.cross_filter_by_geometry(wedge, crs, [plan.id()])
    info = info_of(report)
    asked = [entry for entry in MAPS if entry[0] == "wms"]
    total = sum(width * height for _name, width, height, _box in asked)
    within = all(box[0] >= -52000 and box[1] >= -52000 and box[2] <= 52000 and box[3] <= 62000
                 for _name, _width, _height, box in asked)
    check("WMS: cut by the source from a capture of the area kept, within the budget",
          not report.failed and plan.providerType() == "gdal" and "still image" in str(info.get("captured"))
          and asked and total <= 1050000 and within and all(max(w, h) <= 2048 for _n, w, h, _b in asked),
          (report.failed, len(asked), total, within, info))
    check("WMS: inside the source the image of the service, outside it nothing",
          pixel(plan, 0, 0) == WMS_COLOR and (pixel(plan, -45000, 50000) or (0, 0, 0, 255))[3] == 0,
          (pixel(plan, 0, 0), pixel(plan, -45000, 50000)))
    operations.clear_filters([plan.id()])
    check("WMS: Unfilter gives the live service back", plan.providerType() == "wms" and plan.source() == plan_uri
          and plan.isValid(), plan.providerType())
    # A WMS that answers a report in place of an image (HTTP 200): refused, never a transparent image.
    broken, broken_uri = wms("wmsdead")
    report = operations.cross_filter_by_geometry(wedge, crs, [broken.id()])
    check("WMS that answers a report in place of an image: refused, the layer left as it was",
          bool(report.failed) and broken.providerType() == "wms" and broken.source() == broken_uri,
          (report.failed, broken.providerType()))
    for layer in (basemap, holes, dead, plan, broken):
        QgsProject.instance().removeMapLayer(layer.id())
    server.shutdown()


def main():
    print(f"QGIS {Qgis.QGIS_VERSION}", flush=True)
    from filter_mate.adapters.public_api import operations
    check_wfs(operations)
    check_web_maps(operations)


if __name__ == "__main__":
    import logging
    logging.raiseExceptions = False  # the log file of the plugin cannot be written under a read-only mount
    app = QgsApplication([], True)
    app.initQgis()
    package_root = tempfile.mkdtemp()
    _link(os.environ.get("FM_REPO", "/src"), os.path.join(package_root, "filter_mate"))
    sys.path.insert(0, package_root)
    sys.dont_write_bytecode = True
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        RESULTS.append(False)
    failed = RESULTS.count(False)
    print(f"{len(RESULTS) - failed}/{len(RESULTS)} passed", flush=True)
    os._exit(1 if failed else 0)
