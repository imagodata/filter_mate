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
import os
import re
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from qgis.core import (  # noqa: E402
    Qgis, QgsApplication, QgsCoordinateReferenceSystem, QgsDataSourceUri, QgsFeatureRequest, QgsGeometry, QgsProject,
    QgsRectangle, QgsVectorLayer,
)

TOTAL = 5000  # points, a row of 100 by 50, 10 m apart, from 0, 0 in Web Mercator
RESULTS = []
ASKED = []  # one entry per GetFeature of the WFS server
REFUSED = []  # the status of every request a server refused: QGIS shows an empty layer for them, and says nothing


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
        keyed = name == "keyed"
        if request == "getcapabilities":
            body = capabilities(base, ("keyed", "keyless"))
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
    if Qgis.QGIS_VERSION_INT < 33200:
        # A filter of a web service is installed on a copy of the provider, off the main thread, which QGIS does
        # from 3.32 (server_subset_job); before, it is refused, by extent as by keys, and the layer is left alone.
        for layer in (keyed, keyless):
            report = operations.cross_filter_by_geometry(large, crs, [layer.id()])
            check(f"QGIS before 3.32, {layer.name()}: refused with its reason, the layer left as it was",
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
    check("under 500 features: the keys are listed, nothing is said of an extent",
          not report.error and not report.failed and '"id" IN' in keyed.subsetString() and "by_extent" not in info
          and info.get("kept") == len(few) == 24, (report.error, report.failed, keyed.subsetString()[:80], info))
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
    check("the server refused no request (QGIS shows an empty layer for a refused one, and says nothing)",
          not REFUSED, REFUSED)
    for layer in (keyed, keyless):
        QgsProject.instance().removeMapLayer(layer.id())
    server.shutdown()


def main():
    print(f"QGIS {Qgis.QGIS_VERSION}", flush=True)
    from filter_mate.adapters.public_api import operations
    check_wfs(operations)


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
