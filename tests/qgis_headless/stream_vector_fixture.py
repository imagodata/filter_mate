"""Tiny deterministic WFS 1.0 fixture; records actual server BBOX requests."""

import threading
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from xml.etree import ElementTree

_COMPARISONS = {
    "PropertyIsEqualTo": lambda left, right: left == right,
    "PropertyIsNotEqualTo": lambda left, right: left != right,
    "PropertyIsLessThan": lambda left, right: left < right,
    "PropertyIsGreaterThan": lambda left, right: left > right,
    "PropertyIsLessThanOrEqualTo": lambda left, right: left <= right,
    "PropertyIsGreaterThanOrEqualTo": lambda left, right: left >= right,
}


def _matches(element, row):
    """Evaluate the OGC comparisons on ``id``; the BBOX is applied separately."""
    tag = element.tag.rsplit("}", 1)[-1]
    children = list(element)
    if tag in ("Filter", "And"):
        return all(_matches(child, row) for child in children)
    if tag == "Or":
        return any(_matches(child, row) for child in children)
    if tag == "Not":
        return not _matches(children[0], row)
    if tag == "BBOX":
        return True
    if tag in _COMPARISONS:
        name = next(child.text for child in children if child.tag.endswith(("PropertyName", "ValueReference")))
        literal = next(child.text for child in children if child.tag.endswith("Literal"))
        if name.rsplit(":", 1)[-1] != "id":
            raise ValueError(name)
        return _COMPARISONS[tag](row, float(literal))
    raise ValueError(tag)


class VectorService:
    """WFS 1.0 points 0..999 at (i, 1).

    ``attribute_filters`` also evaluates OGC comparisons on ``id`` (lot A
    filters), with the ArcGIS fixture's conventions: a literal 999 is
    rejected by an HTTP-200 OWS ExceptionReport (WFS 1.1 / 2.0 servers), a
    literal 998 by a WFS 1.0 ServiceExceptionReport, a literal 777 answers
    after ``slow`` seconds and while ``release`` is set.
    """

    def __init__(self, attribute_filters=False, slow=0.5):
        self.requests = []
        self.fail = False
        self.exception_200 = False
        self.delay = 0
        self.release = threading.Event()
        self.release.set()
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                query = {key.lower(): values[0] for key, values in parse_qs(urlsplit(self.path).query).items()}
                operation = query.get("request", "").lower()
                url = fixture.url.replace("&", "&amp;")
                status = 200
                if operation == "getcapabilities":
                    body = """<WFS_Capabilities version="1.0.0" xmlns="http://www.opengis.net/wfs"
                      xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc"
                      xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:fm="urn:filtermate">
                      <Service><Name>WFS</Name><Title>FilterMate fixture</Title><OnlineResource>{url}</OnlineResource></Service>
                      <Capability><Request>{operations}</Request></Capability>
                      <FeatureTypeList><Operations><Query/></Operations><FeatureType><Name>fm:points</Name>
                      <Title>points</Title><SRS>EPSG:4326</SRS><LatLongBoundingBox minx="-1" miny="0" maxx="1999" maxy="2"/>
                      </FeatureType></FeatureTypeList><ogc:Filter_Capabilities><ogc:Spatial_Capabilities>
                      <ogc:Spatial_Operators><ogc:BBOX/><ogc:Intersects/></ogc:Spatial_Operators>
                      </ogc:Spatial_Capabilities><ogc:Scalar_Capabilities><ogc:Logical_Operators/>
                      <ogc:Comparison_Operators><ogc:Simple_Comparisons/></ogc:Comparison_Operators>
                      </ogc:Scalar_Capabilities></ogc:Filter_Capabilities></WFS_Capabilities>""".format(
                        url=url,
                        operations="".join(
                            '<{0}><DCPType><HTTP><Get onlineResource="{1}"/></HTTP></DCPType></{0}>'.format(name, url)
                            for name in ("GetCapabilities", "DescribeFeatureType", "GetFeature")
                        ),
                    )
                elif operation == "describefeaturetype":
                    body = """<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                      xmlns:gml="http://www.opengis.net/gml" xmlns:fm="urn:filtermate"
                      targetNamespace="urn:filtermate" elementFormDefault="qualified">
                      <xsd:import namespace="http://www.opengis.net/gml" schemaLocation="http://schemas.opengis.net/gml/2.1.2/feature.xsd"/>
                      <xsd:element name="points" type="fm:pointsType" substitutionGroup="gml:_Feature"/>
                      <xsd:complexType name="pointsType"><xsd:complexContent><xsd:extension base="gml:AbstractFeatureType">
                      <xsd:sequence><xsd:element name="geometry" type="gml:PointPropertyType"/>
                      <xsd:element name="id" type="xsd:int"/><xsd:element name="label" type="xsd:string"/>
                      </xsd:sequence></xsd:extension></xsd:complexContent></xsd:complexType></xsd:schema>"""
                elif operation == "getfeature":
                    bbox = query.get("bbox")
                    root = ElementTree.fromstring(query["filter"]) if query.get("filter") else None
                    if not bbox and root is not None:
                        for element in root.iter():
                            if element.tag.endswith("coordinates"):
                                bbox = ",".join(element.text.split())
                            elif element.tag.endswith("lowerCorner"):
                                lower = element.text.split()
                            elif element.tag.endswith("upperCorner"):
                                bbox = ",".join(lower + element.text.split())
                    bounds = [float(value) for value in bbox.split(",")[:4]] if bbox else None
                    rows = [
                        i
                        for i in range(1000)
                        if bounds is None or bounds[0] <= i <= bounds[2] and bounds[1] <= 1 <= bounds[3]
                    ]
                    literals = set()
                    if attribute_filters and root is not None:
                        literals = {element.text for element in root.iter() if element.tag.endswith("Literal")}
                        rows = [row for row in rows if _matches(root, row)]
                    limit = int(query.get("maxfeatures", "1000"))
                    rows = rows[:limit]
                    fixture.requests.append(
                        {"bbox": bounds, "returned": len(rows), "hits": query.get("resulttype") == "hits",
                         "filter": query.get("filter", ""), "maxfeatures": query.get("maxfeatures")}
                    )
                    if fixture.delay:
                        time.sleep(fixture.delay)
                    if "777" in literals:
                        time.sleep(slow)
                        fixture.release.wait(10)
                    if "999" in literals:
                        body = (
                            '<?xml version="1.0" encoding="UTF-8"?><ows:ExceptionReport '
                            'xmlns:ows="http://www.opengis.net/ows" version="1.0.0"><ows:Exception '
                            'exceptionCode="InvalidParameterValue"><ows:ExceptionText>fixture rejection'
                            "</ows:ExceptionText></ows:Exception></ows:ExceptionReport>"
                        )
                    elif "998" in literals:
                        body = (
                            '<?xml version="1.0" encoding="UTF-8"?><ServiceExceptionReport version="1.2.0" '
                            'xmlns="http://www.opengis.net/ogc"><ServiceException code="InvalidParameterValue">'
                            "fixture rejection</ServiceException></ServiceExceptionReport>"
                        )
                    elif fixture.exception_200:
                        body = "<ServiceExceptionReport><ServiceException>fixture rejection</ServiceException></ServiceExceptionReport>"
                    elif fixture.fail:
                        status, body = 500, "fixture network failure"
                    else:
                        body = '<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs" '
                        body += 'xmlns:gml="http://www.opengis.net/gml" xmlns:fm="urn:filtermate" numberOfFeatures="{}">'.format(
                            len(rows)
                        )
                        if query.get("resulttype") != "hits":
                            for row in rows:
                                body += (
                                    '<gml:featureMember><fm:points fid="points.{0}"><fm:geometry>'
                                    '<gml:Point srsName="EPSG:4326"><gml:coordinates>{0},1</gml:coordinates></gml:Point>'
                                    "</fm:geometry><fm:id>{0}</fm:id><fm:label>row</fm:label>"
                                    "</fm:points></gml:featureMember>"
                                ).format(row)
                        body += "</wfs:FeatureCollection>"
                else:
                    status, body = 400, "unknown request"
                content = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/xml")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                try:
                    self.wfile.write(content)
                except (BrokenPipeError, ConnectionResetError):
                    pass  # the deadline test deliberately cancels its HTTP request

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:{}/wfs".format(self.server.server_port)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


class OapifService:
    def __init__(self, delay=0.0, n=1000, mode=""):
        self.requests = []
        self.delay = delay
        self.n = n
        self.mode = mode
        srv = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def send(self, status, body, ctype):
                c = body.encode()
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(c)))
                self.end_headers()
                self.wfile.write(c)

            def do_GET(self):
                parts = urlsplit(self.path)
                q = {k.lower(): v[0] for k, v in parse_qs(parts.query).items()}
                srv.requests.append({"path": "RAW " + self.path[:120]})
                base = srv.url
                p = parts.path.rstrip("/")
                if p == "":
                    return self.send(
                        200,
                        json.dumps(
                            {
                                "links": [
                                    {"href": base + "/conformance", "rel": "conformance", "type": "application/json"},
                                    {"href": base + "/collections", "rel": "data", "type": "application/json"},
                                    {
                                        "href": base + "/api",
                                        "rel": "service-desc",
                                        "type": "application/vnd.oai.openapi+json;version=3.0",
                                    },
                                ]
                            }
                        ),
                        "application/json",
                    )
                if p == "/api":
                    return self.send(
                        200,
                        json.dumps({"openapi": "3.0.2", "info": {"title": "t", "version": "1"}, "paths": {}}),
                        "application/vnd.oai.openapi+json;version=3.0",
                    )
                if p == "/conformance":
                    return self.send(
                        200,
                        json.dumps(
                            {
                                "conformsTo": [
                                    "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/core",
                                    "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/geojson",
                                ]
                            }
                        ),
                        "application/json",
                    )
                coll = {
                    "id": "points",
                    "title": "points",
                    "extent": {"spatial": {"bbox": [[-1, 0, srv.n, 2]]}},
                    "links": [
                        {"href": base + "/collections/points/items", "rel": "items", "type": "application/geo+json"}
                    ],
                }
                if p == "/collections":
                    return self.send(200, json.dumps({"collections": [coll], "links": []}), "application/json")
                if p == "/collections/points":
                    return self.send(200, json.dumps(coll), "application/json")
                if p == "/collections/points/items" and srv.mode == "oapif500" and q.get("limit") != "10":
                    srv.requests.append({"path": p, "bbox": None, "returned": 0})
                    return self.send(500, '{"code":"boom"}', "application/json")
                if p == "/collections/points/items":
                    bbox = q.get("bbox")
                    limit = int(q.get("limit", "10"))
                    offset = int(q.get("offset", "0"))
                    b = [float(v) for v in bbox.split(",")[:4]] if bbox else None
                    rows = [i for i in range(srv.n) if b is None or (b[0] <= i <= b[2] and b[1] <= 1 <= b[3])]
                    page = rows[offset : offset + limit]
                    srv.requests.append({"path": p, "bbox": b, "limit": limit, "offset": offset, "returned": len(page)})
                    links = []
                    if offset + limit < len(rows):
                        nq = "limit={}&offset={}".format(limit, offset + limit) + ("&bbox=" + bbox if bbox else "")
                        links.append(
                            {
                                "href": base + "/collections/points/items?" + nq,
                                "rel": "next",
                                "type": "application/geo+json",
                            }
                        )
                    feats = [
                        {
                            "type": "Feature",
                            "id": i,
                            "properties": {"id": i, "label": "r"},
                            "geometry": {"type": "Point", "coordinates": [i, 1]},
                        }
                        for i in page
                    ]
                    return self.send(
                        200,
                        json.dumps({"type": "FeatureCollection", "features": feats, "links": links}),
                        "application/geo+json",
                    )
                return self.send(404, "{}", "application/json")

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = "http://127.0.0.1:{}".format(self.httpd.server_port)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.httpd.shutdown()
        self.httpd.server_close()
