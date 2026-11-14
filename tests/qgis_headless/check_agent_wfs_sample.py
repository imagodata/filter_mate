# -*- coding: utf-8 -*-
"""What a WFS server is really asked when the agent samples a layer: a few features, or everything the map shows?

``sample_features`` reads a web service layer in the extent of the map, with a limit. The limit bounds what the agent
is given; this check measures what the server is asked to send, with a WFS 2.0 server written here that holds 5000
points, counts the features of each answer and honours COUNT and STARTINDEX as a real one does. No network.

    docker run --rm --network none -v "$PWD:/src:ro" -e FM_REPO=/tmp/copy qgis/qgis:ltr bash -c \\
        'mkdir /tmp/copy; cp -r /src/. /tmp/copy; python3 /tmp/copy/tests/qgis_headless/check_agent_wfs_sample.py'

Prints one PASS / FAIL line per check; exits with 1 when one failed.
"""
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from qgis.core import (  # noqa: E402
    Qgis, QgsApplication, QgsCoordinateReferenceSystem, QgsDataSourceUri, QgsProject, QgsRectangle, QgsVectorLayer,
)

TOTAL = 5000
RESULTS = []
ASKED = []  # one entry per GetFeature: what was asked, how many features were sent


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {str(detail)[:500]}" if not condition else ""), flush=True)


def capabilities(base):
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
 <wfs:FeatureTypeList><wfs:FeatureType><wfs:Name>fm:points</wfs:Name><wfs:Title>points</wfs:Title>
  <wfs:DefaultCRS>urn:ogc:def:crs:EPSG::3857</wfs:DefaultCRS>
  <ows:WGS84BoundingBox><ows:LowerCorner>-1 -1</ows:LowerCorner><ows:UpperCorner>1 1</ows:UpperCorner></ows:WGS84BoundingBox>
 </wfs:FeatureType></wfs:FeatureTypeList>
 <fes:Filter_Capabilities><fes:Conformance>
  <fes:Constraint name="ImplementsMinSpatialFilter"><ows:NoValues/><ows:DefaultValue>TRUE</ows:DefaultValue></fes:Constraint>
 </fes:Conformance><fes:Spatial_Capabilities><fes:SpatialOperators><fes:SpatialOperator name="BBOX"/></fes:SpatialOperators>
 </fes:Spatial_Capabilities></fes:Filter_Capabilities>
</wfs:WFS_Capabilities>"""


SCHEMA = """<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:fm="http://fm.example/ns"
  targetNamespace="http://fm.example/ns" elementFormDefault="qualified">
 <xsd:import namespace="http://www.opengis.net/gml/3.2" schemaLocation="http://schemas.opengis.net/gml/3.2.1/gml.xsd"/>
 <xsd:complexType name="pointsType"><xsd:complexContent><xsd:extension base="gml:AbstractFeatureType"><xsd:sequence>
  <xsd:element name="num" type="xsd:int" minOccurs="0"/><xsd:element name="nom" type="xsd:string" minOccurs="0"/>
  <xsd:element name="geom" type="gml:PointPropertyType" minOccurs="0"/>
 </xsd:sequence></xsd:extension></xsd:complexContent></xsd:complexType>
 <xsd:element name="points" type="fm:pointsType" substitutionGroup="gml:AbstractFeature"/>
</xsd:schema>"""


def features(first, count):
    """``count`` points from the ``first``-th: a row of 100 by 50, 10 m apart, around 0, 0 in Web Mercator."""
    members = []
    for number in range(first, min(first + count, TOTAL)):
        x, y = (number % 100) * 10.0, (number // 100) * 10.0
        members.append(f'<wfs:member><fm:points gml:id="points.{number}"><fm:num>{number}</fm:num><fm:nom>p{number}</fm:nom>'
                       f'<fm:geom><gml:Point gml:id="g.{number}" srsName="urn:ogc:def:crs:EPSG::3857"><gml:pos>{x} {y}</gml:pos>'
                       f'</gml:Point></fm:geom></fm:points></wfs:member>')
    return members


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        query = {key.lower(): value[0] for key, value in parse_qs(urlsplit(self.path).query).items()}
        request = query.get("request", "").lower()
        base = f"http://127.0.0.1:{self.server.server_port}/wfs"
        if request == "getcapabilities":
            body = capabilities(base)
        elif request == "describefeaturetype":
            body = SCHEMA
        elif request == "getfeature":
            first = int(query.get("startindex", 0))
            count = int(query.get("count", query.get("maxfeatures", 1000)))
            hits = query.get("resulttype", "") == "hits"
            sent = [] if hits else features(first, count)
            ASKED.append({"count": query.get("count", query.get("maxfeatures")), "start": first, "hits": hits,
                          "bbox": "bbox" in query or "filter" in query, "sent": len(sent)})
            body = (f'<?xml version="1.0" encoding="UTF-8"?><wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0" '
                    f'xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:fm="http://fm.example/ns" numberMatched="{TOTAL}" '
                    f'numberReturned="{len(sent)}" timeStamp="2026-11-14T00:00:00Z">{"".join(sent)}</wfs:FeatureCollection>')
        else:
            self.send_error(400)
            return
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    import qgis.utils
    from qgis.gui import QgsMapCanvas
    from filter_mate.adapters.public_api import introspection

    print(f"QGIS {Qgis.QGIS_VERSION}", flush=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    uri = QgsDataSourceUri()  # as wfs_catalog.open_layer builds it
    for key, value in (("url", f"http://127.0.0.1:{server.server_port}/wfs"), ("typename", "fm:points"), ("version", "auto"),
                       ("pagingEnabled", "true"), ("restrictToRequestBBOX", "1"), ("srsname", "EPSG:3857")):
        uri.setParam(key, value)
    layer = QgsVectorLayer(uri.uri(False), "points", "WFS")
    check("the layer of the local WFS server opens", layer.isValid(), layer.error().message() if not layer.isValid() else "")
    QgsProject.instance().addMapLayer(layer)
    canvas = QgsMapCanvas()
    canvas.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
    canvas.setExtent(QgsRectangle(-10, -10, 2000, 1000))  # every one of the 5000 points is in it
    qgis.utils.iface = SimpleNamespace(mapCanvas=lambda: canvas)
    del ASKED[:]
    sample = introspection.sample_features("points", limit=3)
    reads = [entry for entry in ASKED if not entry["hits"]]
    sent = sum(entry["sent"] for entry in reads)
    print(f"INFO a sample of 3: {len(reads)} GetFeature, {sent} features sent, asked {reads}", flush=True)
    check("the sample holds what was asked, and says it is of what the map shows",
          len(sample["features"]) == 3 and sample["truncated"] and sample["scope"] == "the features the map shows", sample)
    check("the server is asked in the extent of the map", reads and all(entry["bbox"] for entry in reads), reads)
    # What decides whether a sample is light: the server must not be made to send every feature the map shows.
    # Measured on 2026-11-14 in QGIS 3.22, 3.44 and 4.3: one request, COUNT of the limit plus one.
    check(f"the server is asked the features of the sample, not the {TOTAL} of the extent",
          len(reads) == 1 and sent == 4 and reads[0]["count"] == "4", f"{sent} features in {len(reads)} requests")
    # The capabilities of a WFS, read as those of a WMS are: where the service says its requests go.
    from filter_mate.adapters.agent.bounded_http import BoundedReply
    from filter_mate.adapters.public_api import wfs_catalog
    base = f"http://127.0.0.1:{server.server_port}/wfs"
    document = capabilities(base).encode("utf-8")
    types, endpoints = wfs_catalog.parse_capabilities(document)
    check("WFS: the feature type and the addresses of the requests", [item["name"] for item in types] == ["fm:points"]
          and endpoints == [base] * 3, (types, endpoints))
    hidden = document.replace(b'xmlns:xlink="http://www.w3.org/1999/xlink"', b'xmlns:x="http://www.w3.org/1999/xlink" xmlns:xlink="urn:other"') \
        .replace(b'<ows:Operation name="GetFeature"><ows:DCP><ows:HTTP><ows:Get xlink:href="' + base.encode() + b'"/>',
                 b'<ows:Operation name="GetFeature"><ows:DCP><ows:HTTP><ows:Get x:href="' + base.encode()
                 + b'" xlink:href="http://10.0.0.1/internal"/>')

    def said(call):
        try:
            call()
        except ValueError as exc:
            return str(exc)
        return ""
    check("WFS: a document that shows one address to XML and another to QGIS is refused",
          hidden != document and "cannot be trusted" in said(lambda: wfs_catalog.parse_capabilities(hidden)))
    real_fetch = wfs_catalog.fetch
    wfs_catalog.fetch = lambda url, **options: BoundedReply(200, {}, document)
    try:
        wfs_catalog._CACHE.clear()
        check("WFS: the service is read at its own address", len(wfs_catalog.catalog(base)) == 1)
        check("WFS: the same host and port by https is the same place",
              not wfs_catalog.foreign(base.replace("http://", "https://"), base)
              and not wfs_catalog.foreign("http://maps.example.org/wfs", "https://maps.example.org:443/wfs?map=x")
              and wfs_catalog.foreign("https://maps.example.org:8443/wfs", "https://maps.example.org/wfs")
              and wfs_catalog.foreign("ftp://maps.example.org/wfs", "https://maps.example.org/wfs")
              and wfs_catalog.foreign("/wfs", "https://maps.example.org/wfs"))
        for elsewhere, label in ((base.replace("127.0.0.1", "localhost"), "another host"),
                                 (base.replace(f":{server.server_port}", ":9"), "another port")):
            wfs_catalog._CACHE.clear()
            check(f"WFS: a service that sends its requests to {label} is refused",
                  "another host" in said(lambda: wfs_catalog.catalog(elsewhere)), elsewhere)
    finally:
        wfs_catalog.fetch = real_fetch
        wfs_catalog._CACHE.clear()
    server.shutdown()


if __name__ == "__main__":
    app = QgsApplication([], True)
    app.initQgis()
    root = tempfile.mkdtemp()
    os.symlink(os.environ.get("FM_REPO", "/src"), os.path.join(root, "filter_mate"))
    sys.path.insert(0, root)
    sys.dont_write_bytecode = True
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        RESULTS.append(False)
    print(f"{RESULTS.count(True)}/{len(RESULTS)} passed", flush=True)
    os._exit(1 if RESULTS.count(False) else 0)
