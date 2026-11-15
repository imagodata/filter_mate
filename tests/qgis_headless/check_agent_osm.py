# -*- coding: utf-8 -*-
"""The OpenStreetMap tool of the agent in a real (headless) QGIS: features asked by tags, brought in as layers.

    docker run --rm -v "$PWD":/src -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr \\
        python3 /src/tests/qgis_headless/check_agent_osm.py

Without the network: an Overpass server of this machine answers with a small OpenStreetMap document, and can be
busy, stop short, send something else or go slow. With FM_NET=1 the real servers are asked too (the hospitals of
Lyon, from the first one that answers). Prints one PASS / FAIL line per check; exits with 1 when one failed.
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import Qgis, QgsApplication, QgsProject, QgsVectorLayer, QgsWkbTypes  # noqa: E402
from qgis.PyQt.QtCore import QTimer  # noqa: E402

RESULTS = []
LYON = "POLYGON((4.78 45.70, 4.92 45.70, 4.92 45.80, 4.78 45.80, 4.78 45.70))"
HOSPITALS = [{"key": "amenity", "value": "hospital"}]


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {str(detail)[:500]}" if not condition else ""), flush=True)


def refused(function, *args, **kwargs):
    """The message of the ValueError ``function`` raises, "" when it raises none."""
    try:
        function(*args, **kwargs)
    except ValueError as exc:
        return str(exc) or "refused"
    return ""


def square(first, west, south, size=0.001):
    """Four nodes of a square, the ids of its ring (closed)."""
    corners = [(west, south), (west + size, south), (west + size, south + size), (west, south + size)]
    nodes = "".join(f'  <node id="{first + index}" lat="{lat:.7f}" lon="{lon:.7f}"/>\n'
                    for index, (lon, lat) in enumerate(corners))
    ring = "".join(f'<nd ref="{first + index}"/>' for index in (0, 1, 2, 3, 0))
    return nodes, ring


def osm_document(remark=""):
    """A small town as OpenStreetMap writes it, in the order of its files: nodes, ways, relations.

    Two buildings (one a way, one a relation), a hospital mapped as an area and another as a node, a main road, a
    roundabout (a closed way that stays a line), a cafe with an address, and the door of a building: a node with a
    tag of its own, which carries none of the tags asked.
    """
    nodes_a, _ring_a = square(1, 4.80, 45.75)
    nodes_b, ring_b = square(11, 4.81, 45.75)
    nodes_c, ring_c = square(21, 4.82, 45.75)
    nodes_d, ring_d = square(31, 4.83, 45.75)
    door = '  <node id="5" lat="45.7500000" lon="4.8005000"><tag k="entrance" v="yes"/></node>\n'
    clinic = ('  <node id="40" lat="45.7600000" lon="4.8000000"><tag k="amenity" v="hospital"/>'
              '<tag k="name" v="Clinique du Parc"/><tag k="emergency" v="no"/></node>\n')
    cafe = ('  <node id="41" lat="45.7610000" lon="4.8010000"><tag k="amenity" v="cafe"/><tag k="name" v="Café &amp; Thé"/>'
            '<tag k="addr:street" v="Rue de la République"/></node>\n')
    road = ''.join(f'  <node id="{50 + index}" lat="45.7700000" lon="{4.80 + index * 0.01:.7f}"/>\n' for index in range(3))
    ways = (
        # The door (node 5) is on the wall of the first building, between its first two corners.
        '  <way id="100"><nd ref="1"/><nd ref="5"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/>'
        '<tag k="building" v="yes"/></way>\n'
        + f'  <way id="101">{ring_b}<tag k="amenity" v="hospital"/><tag k="name" v="Hôpital Édouard Herriot"/>'
          '<tag k="building" v="hospital"/></way>\n'
        + f'  <way id="102">{ring_c}</way>\n'
        + f'  <way id="103">{ring_d}<tag k="highway" v="primary"/><tag k="junction" v="roundabout"/></way>\n'
        + '  <way id="104"><nd ref="50"/><nd ref="51"/><nd ref="52"/><tag k="highway" v="primary"/>'
          '<tag k="name" v="Avenue Berthelot"/></way>\n')
    relation = ('  <relation id="200"><member type="way" ref="102" role="outer"/><tag k="type" v="multipolygon"/>'
                '<tag k="building" v="apartments"/></relation>\n')
    tail = f"<remark> {remark} </remark>\n" if remark else ""
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<osm version="0.6" generator="check_agent_osm">\n'
            '<note>The data included in this document is from www.openstreetmap.org.</note>\n'
            + nodes_a + door + nodes_b + nodes_c + nodes_d + clinic + cafe + road + ways + relation + tail
            + "</osm>\n").encode("utf-8")


def serve_overpass(state):
    """An Overpass server on this machine. ``state``: ``status`` (what it answers), ``body`` (its document),
    ``delay`` (seconds before it answers); what was asked is kept in ``state["asked"]``."""

    class Overpass(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            form = parse_qs(self.rfile.read(length).decode("utf-8"))
            state["asked"].append({"path": self.path, "query": (form.get("data") or [""])[0],
                                   "type": self.headers.get("Content-Type", "")})
            if state["delay"]:
                time.sleep(state["delay"])
            body = state["body"] if state["status"] == 200 else b"<html>busy</html>"
            self.send_response(state["status"])
            self.send_header("Content-Type", "application/osm3s+xml" if state["status"] == 200 else "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass  # the request was stopped

    server = ThreadingHTTPServer(("127.0.0.1", 0), Overpass)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def kinds_of(project, made):
    """``{geometry: (feature count, geometry type, fields)}`` of the layers a call made, read in the project."""
    found = {}
    for row in made["layers"]:
        layer = project.mapLayer(row["layer_id"])
        found[row["geometry"]] = (layer.featureCount(), QgsWkbTypes.displayString(layer.wkbType()),
                                  [field.name() for field in layer.fields() if field.name() != "fid"])
    return found


def check_features(project, work):
    from filter_mate.adapters.agent import bounded_http
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.adapters.public_api import operations, osm_features
    from filter_mate.core.agent import osm
    from filter_mate.core.agent.messages import ToolCallPart
    from filter_mate.core.agent.sources import make_source, platform_domains, platform_name

    state = {"status": 200, "body": osm_document(), "delay": 0.0, "asked": []}
    server = serve_overpass(state)
    mine = make_source(f"http://127.0.0.1:{server.server_address[1]}/api/interpreter", "overpass", "Banc")
    platform, domains = platform_name(mine), platform_domains([mine])
    root = os.path.join(QgsApplication.qgisSettingsDirPath(), "filtermate", "open_data")

    def kept():
        return {name for name in (os.listdir(root) if os.path.isdir(root) else []) if name.startswith("osm-")}

    def temporary():
        return {name for name in os.listdir(tempfile.gettempdir()) if name.startswith("filtermate-osm-")}

    def ask(**arguments):
        arguments.setdefault("extent_wkt", LYON)
        arguments.setdefault("crs", "EPSG:4326")
        return osm_features.add_osm_features(platform, extra_domains=domains, **arguments)

    data = QgsVectorLayer("Point?crs=EPSG:4326", "data", "memory")
    project.addMapLayer(data)
    try:
        before, drafts = kept(), temporary()
        recorder = EffectsRecorder()
        recorder.before_call(ToolCallPart("o1", "add_osm_features", {"tags": HOSPITALS}))
        made = ask(tags=HOSPITALS + [{"key": "building"}], name="Ville")
        recorder.after_call()
        found = kinds_of(project, made)
        check("features: a layer per kind of geometry, the features that carry one of the tags",
              {kind: count for kind, (count, _shape, _fields) in found.items()} == {"points": 1, "polygons": 3}
              and made["feature_count"] == 4 and made["tags"] == ["amenity=hospital", "building"], (made, found))
        check("features: areas are areas, a point is a point", found["polygons"][1] == "MultiPolygon"
              and found["points"][1] == "Point", found)
        check("features: named after what was asked, with their kind when there are several",
              [row["name"] for row in made["layers"]] == ["Ville (points)", "Ville (polygons)"], made["layers"])
        order = [node.layerId() for node in project.layerTreeRoot().findLayers()]
        check("features: on top of the project, the points over the areas",
              order == [made["layers"][0]["layer_id"], made["layers"][1]["layer_id"], data.id()], order)
        polygons = project.mapLayer(made["layers"][1]["layer_id"])
        rows = {feature["osm_id"]: (feature["osm_type"], feature["name"], feature["building"], feature["amenity"])
                for feature in polygons.getFeatures()}
        check("features: each with its id, its type, its name and a column per key asked",
              rows == {"100": ("way", None, "yes", None), "101": ("way", "Hôpital Édouard Herriot", "hospital", "hospital"),
                       "200": ("relation", None, "apartments", None)}
              or {key: tuple(value or None for value in row) for key, row in rows.items()} == {
                  "100": ("way", None, "yes", None), "101": ("way", "Hôpital Édouard Herriot", "hospital", "hospital"),
                  "200": ("relation", None, "apartments", None)}, rows)
        points = project.mapLayer(made["layers"][0]["layer_id"])
        check("features: a node that came with its way and carries no tag asked is left out (the door)",
              [feature["name"] for feature in points.getFeatures()] == ["Clinique du Parc"]
              and "other_tags" in found["points"][2], [feature.attributes() for feature in points.getFeatures()])
        check("features: a column no feature fills is not kept", "building" not in found["points"][2]
              and found["points"][2][:3] == ["osm_id", "osm_type", "name"], found["points"][2])
        check("features: in longitude and latitude, with the credit of OpenStreetMap",
              made["crs_authid"] == "EPSG:4326" and points.crs().authid() == "EPSG:4326"
              and points.metadata().rights() == [osm.ATTRIBUTION] and made["attribution"] == osm.ATTRIBUTION
              and abs(next(points.getFeatures()).geometry().asPoint().x() - 4.80) < 1e-6, made)
        sent = state["asked"][-1]
        check("features: the server is asked the query written from the tags and the area",
              sent["query"] == osm.overpass_query(osm.read_tags(HOSPITALS + [{"key": "building"}]), [4.78, 45.70, 4.92, 45.80])
              and sent["type"].startswith("application/x-www-form-urlencoded") and sent["path"] == "/api/interpreter",
              sent)
        check("features: one file kept in the QGIS profile, the answer of the server is not",
              len(kept() - before) == 1 and temporary() == drafts
              and polygons.source().split("|")[0].endswith("openstreetmap.gpkg"), (kept() - before, temporary() - drafts))
        json.dumps(made)
        check("features: FilterMate is free again", operations.busy_reason() == "", operations.busy_reason())
        effects = recorder.finish()
        apply_effects(effects, undo=True)
        check("features: undoing the turn removes the layers", all(project.mapLayer(row["layer_id"]) is None
                                                                  for row in made["layers"]))
        apply_effects(effects, undo=False)
        back = sorted(layer.name() for layer in project.mapLayers().values() if layer.name().startswith("Ville"))
        check("features: redoing opens them again", back == ["Ville (points)", "Ville (polygons)"], back)
        project.removeMapLayers([layer.id() for layer in project.mapLayers().values() if layer.id() != data.id()])

        made = ask(tags=HOSPITALS, geometry="points")
        found = kinds_of(project, made)
        layer = project.mapLayer(made["layers"][0]["layer_id"])
        inside = {feature["name"]: feature.geometry().asPoint() for feature in layer.getFeatures()}
        check("points: one layer of points, a point inside each area", list(found) == ["points"]
              and found["points"][0] == 2 and set(inside) == {"Clinique du Parc", "Hôpital Édouard Herriot"}
              and 4.81 < inside["Hôpital Édouard Herriot"].x() < 4.811 and made["layers"][0]["name"] == "OSM amenity=hospital",
              (made, inside))
        check("points: each keeps the type it has in OpenStreetMap",
              {feature["name"]: feature["osm_type"] for feature in layer.getFeatures()}
              == {"Clinique du Parc": "node", "Hôpital Édouard Herriot": "way"})
        project.removeMapLayer(layer.id())

        made = ask(tags=[{"key": "highway", "value": "primary"}])
        found = kinds_of(project, made)
        check("lines: a road is a line, and so is a roundabout, which closes", list(found) == ["lines"]
              and found["lines"][:2] == (2, "MultiLineString") and "highway" in found["lines"][2], found)
        project.removeMapLayer(made["layers"][0]["layer_id"])
        middle = ask(tags=[{"key": "highway"}], geometry="points")
        layer = project.mapLayer(middle["layers"][0]["layer_id"])
        spots = sorted(round(feature.geometry().asPoint().x(), 3) for feature in layer.getFeatures())
        check("points: the middle of a line", spots[0] == 4.81 and len(spots) == 2, spots)
        project.removeMapLayer(layer.id())
        made = ask(tags=HOSPITALS + [{"key": "building"}], geometry="polygons")
        check("polygons: that kind alone", [row["geometry"] for row in made["layers"]] == ["polygons"]
              and made["feature_count"] == 3, made)
        project.removeMapLayer(made["layers"][0]["layer_id"])
        made = ask(tags=[{"key": "addr:street"}])
        layer = project.mapLayer(made["layers"][0]["layer_id"])
        check("features: a key with a colon is a column with an underscore, a name keeps its letters",
              [(feature["addr_street"], feature["name"]) for feature in layer.getFeatures()]
              == [("Rue de la République", "Café & Thé")], [feature.attributes() for feature in layer.getFeatures()])
        project.removeMapLayer(layer.id())

        count, files = len(project.mapLayers()), kept()
        for label, arguments, needle in (
                ("tags no feature carries", {"tags": [{"key": "amenity", "value": "prison"}]}, "no feature with these tags"),
                ("a kind none of them has", {"tags": HOSPITALS, "geometry": "lines"}, "no feature with these tags in this area as lines"),
                ("a tag that is no tag", {"tags": [{"key": 'amenity"](1,2,3,4);node'}]}, "a key is written"),
                ("a value that would close the query", {"tags": [{"key": "amenity", "value": 'x"];out;'}]}, "plain text"),
                ("no tag", {"tags": []}, "tags is a list"),
                ("an unknown kind", {"tags": HOSPITALS, "geometry": "areas"}, "geometry is one of"),
                ("an area too large", {"tags": HOSPITALS, "extent_wkt": "POLYGON((4 45, 6 45, 6 47, 4 47, 4 45))"}, "10,000 at most"),
                ("a point", {"tags": HOSPITALS, "extent_wkt": "POINT(4.84 45.76)"}, "a point or a line"),
                ("a CRS written as a definition", {"tags": HOSPITALS, "crs": "+proj=longlat +nadgrids=https://x.org/g"}, "unknown CRS")):
            said = refused(ask, **arguments)
            check(f"refused: {label}, nothing added nor kept", needle in said and len(project.mapLayers()) == count
                  and kept() == files and temporary() == drafts, said)
        asked = len(state["asked"])
        said = refused(ask, tags=[{"key": 'a"]'}])
        check("refused: a tag that is none is never sent", said and len(state["asked"]) == asked, said)
        for label, kind, needle in (("a platform of another kind", "datagouv", "not an OpenStreetMap"),
                                    ("a platform that is not of the list", "overpass_nowhere", "not an OpenStreetMap server of the list")):
            said = refused(osm_features.add_osm_features, kind, HOSPITALS, extent_wkt=LYON, crs="EPSG:4326")
            check(f"refused: {label}", needle in said, said)

        address = f"127.0.0.1:{server.server_address[1]}"
        for label, change, needle in (
                ("a busy server", {"status": 504}, "is busy (504)"),
                ("a server that got too many requests", {"status": 429}, "too many requests (429)"),
                ("a query it refuses", {"status": 400}, "refused the query (400)"),
                ("an answer that is not OpenStreetMap", {"body": b"<html>Welcome</html>" * 50}, "not OpenStreetMap data"),
                ("an answer cut by the server for its time",
                 {"body": osm_document('runtime error: Query timed out in "query" at line 3 after 61 seconds.')},
                 "ran out of time"),
                ("an answer cut by the server for its size",
                 {"body": osm_document("runtime error: Query run out of memory using about 2048 MB of RAM.")},
                 "too large for the server")):
            saved = dict(state)
            state.update(change)
            said = refused(ask, tags=HOSPITALS)
            state.update(status=saved["status"], body=saved["body"])
            check(f"server: {label} is said so, nothing added nor kept", needle in said
                  and len(project.mapLayers()) == count and kept() == files and temporary() == drafts, said)
        limit = osm_features.MAX_BYTES
        osm_features.MAX_BYTES = 500
        said = refused(ask, tags=HOSPITALS)
        osm_features.MAX_BYTES = limit
        check("server: an answer too large is refused", "weighs more than" in said and kept() == files
              and temporary() == drafts, said)
        state["delay"] = 3.0
        busy = []
        stop = QTimer()
        stop.setSingleShot(True)
        stop.timeout.connect(lambda: (busy.append(operations.busy_reason()), bounded_http.abort_active()))
        stop.start(400)
        started = time.monotonic()
        said = refused(ask, tags=HOSPITALS)
        waited = time.monotonic() - started
        stop.stop()
        state["delay"] = 0.0
        check("server: Stop ends the request, nothing added nor kept", said == "stopped" and waited < 2.5
              and len(project.mapLayers()) == count and kept() == files and temporary() == drafts,
              (said, round(waited, 1)))
        check("server: FilterMate is busy during the request, and free again after the Stop",
              busy and "add_osm_features" in busy[0] and operations.busy_reason() == "", (busy, operations.busy_reason()))
        check("server: the Test of the Sources tab", osm_features.check_osm(platform, extra_domains=domains)["status"] == 200)
        state["status"] = 503
        said = refused(osm_features.check_osm, platform, extra_domains=domains)
        state["status"] = 200
        check("server: a server that is down fails its Test", "busy (503)" in said, said)
        server.shutdown()
        server.server_close()
        said = refused(ask, tags=HOSPITALS)
        check("server: one that does not answer is said so", "did not answer" in said and kept() == files, said)
        return address
    finally:
        project.removeAllMapLayers()
        for name in kept():
            shutil.rmtree(os.path.join(root, name), ignore_errors=True)


def check_tools(project, work):
    """The chat tool, on the real accessor: what a model sends, what it reads back, and what it never reads."""
    from filter_mate.core.agent.messages import ToolCallPart
    from filter_mate.core.agent.sources import make_source, model_name, platform_aliases, platform_domains
    from filter_mate.core.agent.tool_catalog import chat_tools
    from filter_mate.core.agent.tool_executor import ToolExecutor
    from filter_mate.filtermate_api.agent_tools import build_handlers
    from filter_mate.filtermate_api.qgis_accessor import QGISFilterMateAccessor

    class PublicApi:
        @staticmethod
        def get_active_filters():
            return {}

    state = {"status": 200, "body": osm_document(), "delay": 0.0, "asked": []}
    server = serve_overpass(state)
    mine = make_source(f"http://127.0.0.1:{server.server_address[1]}/api/interpreter?key=SECRET", "overpass", "Banc")
    name = model_name(mine)
    root = os.path.join(QgsApplication.qgisSettingsDirPath(), "filtermate", "open_data")
    accessor = QGISFilterMateAccessor(PublicApi(), None)

    def tools(platforms):
        executor = ToolExecutor(chat_tools(), build_handlers(
            accessor, os.path.join(work, "exports"), platforms=platforms, platform_aliases=platform_aliases([mine]),
            extra_domains=platform_domains([mine])))

        def tool(tool_name, /, **arguments):
            result = executor.execute(ToolCallPart("c", tool_name, arguments))
            return result.is_error, result.content
        return tool

    try:
        tool = tools([name])
        error, content = tool("add_osm_features", tags=HOSPITALS, extent_wkt=LYON, crs="EPSG:4326", geometry="points",
                              platform=name, name="Hôpitaux")
        answer = {} if error else json.loads(content)
        check("tool add_osm_features: a server the user added, named by its id", not error
              and answer["platform"] == name and answer["feature_count"] == 2
              and answer["layers"][0]["name"] == "Hôpitaux" and answer["layers"][0]["geometry"] == "points", content)
        check("tool add_osm_features: its address and its key are never in the answer",
              "SECRET" not in content and "127.0.0.1" not in content, content)
        error, content = tool("layer_statistics", layer="Hôpitaux")
        check("tool: the layer made is read like any other", not error and json.loads(content)["feature_count"] == 2, content)
        error, content = tool("preview_filter", layer_name="Hôpitaux", expression="\"osm_type\" = 'node'")
        check("tool: and a filter on a column of it keeps what it should", not error
              and json.loads(content)["feature_count"] == 1, content)
        state["status"] = 504
        error, content = tool("add_osm_features", tags=HOSPITALS, extent_wkt=LYON, crs="EPSG:4326", platform=name)
        state["status"] = 200
        check("tool add_osm_features: a busy server is named as the model named it, never by its address",
              error and "busy (504)" in content and name in content and "SECRET" not in content
              and "127.0.0.1" not in content and "another" in content, content)
        error, content = tool("add_osm_features", tags=HOSPITALS, extent_wkt=LYON, crs="EPSG:4326")
        check("tool add_osm_features: the server of the schema is refused when it is not ticked",
              error and "not enabled" in content and name in content and "SECRET" not in content, content)
        error, content = tools([])("add_osm_features", tags=HOSPITALS, extent_wkt=LYON, crs="EPSG:4326", platform=name)
        check("tool add_osm_features: refused when no OpenStreetMap server is ticked", error and "not enabled" in content,
              content)
        error, content = tool("add_osm_features", tags=[{"key": 'a"];node(1);out;'}], extent_wkt=LYON, crs="EPSG:4326",
                              platform=name)
        check("tool add_osm_features: a tag that is none is refused", error and len(state["asked"]) == 2, content)
    finally:
        server.shutdown()
        server.server_close()
        project.removeAllMapLayers()
        for folder in (os.listdir(root) if os.path.isdir(root) else []):
            if folder.startswith("osm-"):
                shutil.rmtree(os.path.join(root, folder), ignore_errors=True)


def check_live(project):
    """The real servers: the hospitals of Lyon, from the first of the list that answers."""
    from filter_mate.adapters.public_api import osm_features
    from filter_mate.core.agent.osm import SERVERS

    root = os.path.join(QgsApplication.qgisSettingsDirPath(), "filtermate", "open_data")
    said = []
    for server in SERVERS:
        started = time.monotonic()
        try:
            made = osm_features.add_osm_features(server.id, HOSPITALS, extent_wkt=LYON, crs="EPSG:4326", geometry="points")
        except ValueError as exc:
            said.append(f"{server.id}: {exc}")
            print(f"INFO live: {server.id} did not give them: {str(exc)[:200]}", flush=True)
            continue
        layer = project.mapLayer(made["layers"][0]["layer_id"])
        names = [feature["name"] for feature in layer.getFeatures() if feature["name"]]
        check("live: the hospitals of Lyon from OpenStreetMap, as points", made["feature_count"] >= 15
              and layer.featureCount() == made["feature_count"] and len(names) >= 10, made)
        print(f"INFO live: {made['feature_count']} hospitals from {server.id} in {time.monotonic() - started:.1f} s, "
              f"such as {', '.join(names[:3])}", flush=True)
        break
    else:
        check("live: the hospitals of Lyon from OpenStreetMap, as points", False, said)
    for server in SERVERS:
        try:
            osm_features.check_osm(server.id)
            print(f"INFO live: {server.id} passes its Test", flush=True)
        except ValueError as exc:
            print(f"INFO live: {server.id} fails its Test: {str(exc)[:160]}", flush=True)
    project.removeAllMapLayers()
    for folder in (os.listdir(root) if os.path.isdir(root) else []):
        if folder.startswith("osm-"):
            shutil.rmtree(os.path.join(root, folder), ignore_errors=True)


def main():
    from osgeo import gdal
    print(f"QGIS {Qgis.QGIS_VERSION}, GDAL {gdal.__version__}", flush=True)
    work = tempfile.mkdtemp()
    project = QgsProject.instance()
    check_features(project, work)
    check_tools(project, work)
    if os.environ.get("FM_NET") == "1":
        check_live(project)


if __name__ == "__main__":
    app = QgsApplication([], False)
    app.initQgis()
    package_root = tempfile.mkdtemp()
    os.symlink(os.environ.get("FM_REPO", "/src"), os.path.join(package_root, "filter_mate"))
    sys.path.insert(0, package_root)
    sys.dont_write_bytecode = True
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        RESULTS.append(False)
    print(f"{RESULTS.count(True)}/{len(RESULTS)} passed", flush=True)
    os._exit(1 if RESULTS.count(False) else 0)
