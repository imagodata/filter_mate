"""The d3 charts of the agent in a real (headless) QGIS 4 with QtWebEngine: drawn from a layer and from rows, the code
of the expert mode and its limits, the exports, a chart in a print layout, drawn again when the filter of its layer
changes, and the undo of the turn. Run inside a qgis/qgis image that has PyQt6 QtWebEngine:

    docker run --rm -v "$PWD":/src -e QT_QPA_PLATFORM=offscreen -e QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox \\
        qgis/qgis:latest sh -c "apt-get update -qq && apt-get install -y -qq python3-pyqt6.qtwebengine >/dev/null \\
        && xvfb-run -a python3 /src/tests/qgis_headless/check_agent_charts.py"

Without QtWebEngine (QGIS 3, an image without it), checks that the tools say so and stops.
Prints one PASS / FAIL line per check; exits with 1 when one failed.
"""
import os
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import (  # noqa: E402
    QgsApplication, QgsFeature, QgsField, QgsFields, QgsGeometry, QgsLayoutItemPicture, QgsPointXY, QgsProject,
    QgsVectorFileWriter, QgsVectorLayer,
)
from qgis.PyQt.QtCore import QDate, QVariant  # noqa: E402

RESULTS = []


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {str(detail)[:400]}" if not condition else ""))


def make_layer(path):
    fields = QgsFields()
    for name, kind in (("usage", QVariant.String), ("hauteur", QVariant.Double), ("etages", QVariant.Int),
                       ("annee", QVariant.Date)):
        fields.append(QgsField(name, kind))
    memory = QgsVectorLayer("Point?crs=EPSG:2154", "memory", "memory")
    memory.dataProvider().addAttributes(fields.toList())
    memory.updateFields()
    usages = ["Résidentiel"] * 30 + ["Commercial"] * 12 + ["Industriel"] * 8 + ["Agricole"] * 5 + \
        ["</script><script>window.pwned=1</script>"] * 2 + [None] * 3
    features = []
    for index, usage in enumerate(usages):
        feature = QgsFeature(memory.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(650000 + index, 6860000)))
        feature.setAttributes([usage, 3.0 + (index % 17) * 1.5, index % 9, QDate(2000 + index % 20, 1, 1)])
        features.append(feature)
    memory.dataProvider().addFeatures(features)
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    QgsVectorFileWriter.writeAsVectorFormatV2(memory, path, QgsProject.instance().transformContext(), options)


def failure(call):
    from filter_mate.core.agent.tool_executor import ToolFailure
    try:
        call()
    except ToolFailure as exc:
        return str(exc)
    return ""


def main():
    from filter_mate.adapters.agent import chart_renderer
    from filter_mate.ui.controllers.agent_charts import AgentCharts
    charts = AgentCharts(lambda: False)
    if not chart_renderer.available():
        said = failure(lambda: charts.show_chart({"kind": "bar", "rows": [{"label": "a", "value": 1}]}, True))
        check("no QtWebEngine: show_chart says so", "QtWebEngine" in said, said)
        return

    work = tempfile.mkdtemp()
    path = os.path.join(work, "batiments.gpkg")
    make_layer(path)
    layer = QgsVectorLayer(path, "batiments", "ogr")
    project = QgsProject.instance()
    project.addMapLayer(layer)
    check("fixture valid", layer.isValid() and layer.featureCount() == 60)

    # --- every kind from the layer
    started = time.time()
    bar = charts.show_chart({"kind": "bar", "layer": "batiments", "field": "usage", "title": "Usages"}, True)
    first = time.time() - started
    svg = charts.pending.svg
    check("bar: drawn from the layer, the NULL and the markup as categories", bar["features"] == 60 and
          bar["points"] == 6 and svg.count("<path") >= 6 and "Résidentiel" in svg, bar)
    check("bar: a value of the layer is text, never markup", "&lt;/script&gt;" in svg and "<script" not in svg,
          svg[:300])
    check("bar: the first chart starts QtWebEngine in under 15 s", first < 15, first)
    started = time.time()
    for arguments in ({"kind": "pie", "layer": "batiments", "field": "usage", "limit": 3},
                      {"kind": "histogram", "layer": "batiments", "field": "hauteur", "bins": 8},
                      {"kind": "line", "layer": "batiments", "field": "annee", "value_field": "hauteur",
                       "aggregate": "mean"},
                      {"kind": "scatter", "layer": "batiments", "field": "hauteur", "value_field": "etages",
                       "series_field": "usage"},
                      {"kind": "bar", "layer": "batiments", "field": "usage", "value_field": "hauteur",
                       "aggregate": "sum", "horizontal": True}):
        answer = charts.show_chart(arguments, True)
        svg = charts.pending.svg
        check(f"{arguments['kind']}: drawn", answer["points"] > 0 and "<svg" in svg and
              chart_renderer.svg_renderer(svg).isValid() and not answer.get("errors"), answer)
    check("five more charts in under 3 s", time.time() - started < 3, time.time() - started)
    line = charts.chart("c4")
    check("line: a date field is a time axis", line.meta.get("x_type") == "time", line.meta)
    check("no value of the layer for a user who does not share them",
          "data" not in charts.show_chart({"kind": "bar", "layer": "batiments", "field": "usage"}, False))

    # --- rows, refusals
    rows = charts.show_chart({"kind": "bar", "rows": [{"label": "A", "value": 3}, {"label": "B", "value": 7}],
                              "title": "Rows"}, True)
    check("rows: drawn, said to be given", rows["source"] == "rows" and rows["points"] == 2, rows)
    for arguments, label in (({"kind": "bar", "layer": "batiments", "field": "nope"}, "an unknown field"),
                             ({"kind": "histogram", "layer": "batiments", "field": "usage"}, "a text histogram"),
                             ({"kind": "bar", "layer": "nope", "field": "usage"}, "an unknown layer"),
                             ({"kind": "bar", "rows": [{"label": "A", "value": 1e308}, {"label": "A", "value": 1e308}]},
                              "a sum beyond a float")):
        check(f"refuses {label}", failure(lambda: charts.show_chart(arguments, True)))
    negative = charts.show_chart({"kind": "bar", "rows": [{"label": "A", "value": -3}, {"label": "B", "value": -7}]},
                                 True)
    check("bar: values all negative are drawn", negative["points"] == 2)

    # --- code of the expert mode: run_chart_code over the data of a chart
    base = charts.show_chart({"kind": "bar", "rows": [{"label": "A", "value": 3}, {"label": "B", "value": 7}]},
                             True)["chart_id"]

    def code_run(code, share=True):
        return charts.run_chart_code({"chart_id": base, "purpose": "test", "code": code}, share)

    code = ("svg.selectAll('rect.x').data(data).join('rect').attr('x', (d, i) => 20 + i * 60).attr('y', 40)"
            ".attr('width', 50).attr('height', d => d.value * 10).attr('fill', palette.series[1]);")
    drawn = code_run(code)
    check("code: drawn, its image sent back", hasattr(drawn, "images") and drawn.answer["code"] and
          drawn.answer["drawn_from"] == base and charts.pending.svg.count("<rect") >= 3,
          getattr(drawn, "answer", drawn))
    hidden = code_run(code, share=False)
    check("code: no image for a user who does not share values", not hasattr(hidden, "images"), hidden)
    quiet = code_run("console.error(data.map(d => d.label + ' ' + d.value).join(' ')); svg.append('rect')"
                     ".attr('width', 5).attr('height', 5);", share=False)
    check("code: no word of its errors for a user who does not share values",
          "A 3" not in str(quiet) and quiet.get("errors"), quiet)
    check("code: drawn light, whatever the theme of the dock", "#1a1a19" not in charts.pending.svg)
    told = code_run("svg.append('rect').attr('x', nope.y);")
    check("code: an error of the script is told with what it drew",
          any("nope" in error for error in told.answer.get("errors", [])), told.answer)
    said = failure(lambda: code_run("d3.select('svg').remove(); throw new Error('boom');"))
    check("code: no chart at all is refused with the error", "boom" in said, said)
    secret = os.path.join(work, "secret.png")
    from qgis.PyQt.QtGui import QColor, QImage
    red = QImage(20, 20, QImage.Format.Format_ARGB32)
    red.fill(QColor("red"))
    red.save(secret)
    stolen = code_run(f"svg.append('image').attr('href', {secret!r}).attr('width', 600).attr('height', 380);"
                      f"svg.append('image').attr('xlink:href', {secret!r});")
    check("code: an image of the disk never reaches the chart", "secret" not in charts.pending.svg and
          "<image" not in charts.pending.svg, stolen.answer)
    replaced = failure(lambda: code_run("FMCharts.result = function () { return '[1]'; };"))
    check("code: a result replaced by the code is refused in words", "no chart" in replaced, replaced)

    hits = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            hits.append(self.path)
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    import socket
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    address = f"http://127.0.0.1:{server.server_address[1]}"
    stun = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    stun.bind(("127.0.0.1", 0))
    stun.settimeout(0.1)
    leak = (f"fetch('{address}/fetch').catch(() => 0); new Image().src = '{address}/img';"
            f"svg.append('image').attr('href', '{address}/svg'); svg.append('rect').attr('width', 10)"
            ".attr('height', 10); try { const pc = new RTCPeerConnection({iceServers: [{urls: "
            f"'stun:127.0.0.1:{stun.getsockname()[1]}'}}]}}); pc.createDataChannel('x');"
            " pc.createOffer().then(o => pc.setLocalDescription(o)); } catch (e) {}")
    try:
        code_run(leak)
    except Exception:  # noqa: BLE001 - only what reached the servers matters
        pass
    packets = []
    deadline = time.time() + 2
    while time.time() < deadline:
        QgsApplication.processEvents()
        try:
            packets.append(stun.recvfrom(2048)[0])
        except socket.timeout:
            pass
    server.shutdown()
    check("code: reaches no web server", not hits, hits)
    check("code: RTCPeerConnection is gone from the top frame of the page (no STUN packet)", not packets,
          len(packets))
    check("code: its page is dropped after the run (what it opened goes with it)", chart_renderer._page is None)

    started = time.time()
    said = failure(lambda: code_run("while (true) {}"))
    check("code: a loop that never ends is stopped", "in time" in said and time.time() - started < 25, said)
    again = charts.show_chart({"kind": "bar", "rows": [{"label": "A", "value": 2}]}, True)
    check("after it, a new page draws the next chart", again["points"] == 1, again)
    chart_renderer._busy = True
    try:
        busy = failure(lambda: charts.show_chart({"kind": "bar", "rows": [{"label": "A", "value": 2}]}, True))
    finally:
        chart_renderer._busy = False
    check("a chart asked while another is drawn is refused, never mixed", "another chart" in busy, busy)

    # --- exports
    root = os.path.join(work, "exports")
    for file_format, magic in (("png", b"\x89PNG"), ("jpg", b"\xff\xd8\xff"), ("svg", b"<?xml")):
        answer = charts.export_chart({"chart_id": "c1", "format": file_format, "dpi": 150}, root)
        written = os.path.join(root, "charts", answer["path"])
        check(f"export {file_format}", answer["bytes"] > 1000 and open(written, "rb").read(len(magic)) == magic,
              answer)
    from qgis.PyQt.QtGui import QImage
    picture = QImage(os.path.join(root, "charts", "Usages.png"))
    check("export png: 150 dpi is 640 x 400 px times 150 / 96", (picture.width(), picture.height()) == (1000, 625),
          (picture.width(), picture.height()))
    twice = charts.export_chart({"chart_id": "c1", "format": "png"}, root)
    check("export: an existing file is kept", twice["path"] == "Usages_2.png", twice)
    check("export: refuses a way out of the root",
          failure(lambda: charts.export_chart({"chart_id": "c1", "subfolder": "../out"}, root)))
    check("export: refuses an unknown chart", failure(lambda: charts.export_chart({"chart_id": "c99"}, root)))

    # --- a print layout: added, drawn again when the filter changes, undone with the turn
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.adapters.public_api import layouts
    from filter_mate.adapters.public_api.charts import PROPERTY
    from filter_mate.core.agent.messages import ToolCallPart
    layouts.create_layout("Rapport", title="Bâtiments", extent_layer="batiments")
    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("t1", "add_chart_to_layout", {"chart_id": "c1", "layout": "Rapport"}))
    placed = charts.add_to_layout({"chart_id": "c1", "layout": "Rapport"})
    layout = project.layoutManager().layoutByName("Rapport")
    items = [item for item in layout.items()
             if isinstance(item, QgsLayoutItemPicture) and item.customProperty(PROPERTY)]
    check("layout: the chart is a picture of the layout", len(items) == 1 and placed["follows_filter"] and
          placed["width_mm"] > 50, placed)
    before = items[0].picturePath() if items else ""
    check("layout: its SVG is embedded", before.startswith("base64:"), before[:30])
    folder = os.path.join(work, "layout_out")
    os.makedirs(folder)
    exported = layouts.export_layout("Rapport", folder, "png", dpi=96)
    check("layout: exported with the chart", exported["bytes"] > 5000, exported)
    layer.setSubsetString("\"usage\" = 'Commercial'")
    deadline = time.time() + 5
    while time.time() < deadline and items[0].picturePath() == before:
        QgsApplication.processEvents()
        time.sleep(0.05)
    check("layout: drawn again when the filter of its layer changes", items[0].picturePath() != before)
    layer.setSubsetString("")
    deadline = time.time() + 3
    while time.time() < deadline:
        QgsApplication.processEvents()
        time.sleep(0.05)
    import json as _json
    planted = _json.loads(items[0].customProperty(PROPERTY))
    planted["code"] = "svg.append('rect').attr('width', 99).attr('height', 99).attr('fill', 'red');"
    items[0].setCustomProperty(PROPERTY, _json.dumps(planted))
    kept = items[0].picturePath()
    layer.setSubsetString("\"usage\" = 'Agricole'")
    deadline = time.time() + 3
    while time.time() < deadline:
        QgsApplication.processEvents()
        time.sleep(0.05)
    check("layout: code a project holds is never run", items[0].picturePath() == kept)
    planted.pop("code")
    items[0].setCustomProperty(PROPERTY, _json.dumps(planted))
    layer.setSubsetString("")
    effects = recorder.finish()
    check("layout: the turn keeps the chart it put there", [effect[0] for effect in effects] == ["layout_item"],
          [effect[0] for effect in effects])
    done, left = apply_effects(effects, undo=True)
    remaining = [item for item in layout.items()
                 if isinstance(item, QgsLayoutItemPicture) and item.customProperty(PROPERTY)]
    check("layout: undo takes it away", not left and not remaining, (done, left))
    done, left = apply_effects(effects, undo=False)
    back = [item for item in layout.items() if isinstance(item, QgsLayoutItemPicture) and item.customProperty(PROPERTY)]
    check("layout: redo brings it back, still a chart", not left and len(back) == 1, (done, left))
    charts.unwatch_all()
    chart_renderer.drop_page()


if __name__ == "__main__":
    app = QgsApplication([b"check_agent_charts"], False)
    app.initQgis()
    package_root = tempfile.mkdtemp()
    os.symlink(os.environ.get("FM_REPO", "/src"), os.path.join(package_root, "filter_mate"))
    sys.path.insert(0, package_root)
    sys.dont_write_bytecode = True
    print(f"QGIS {__import__('qgis.core').core.Qgis.QGIS_VERSION}, Python {sys.version.split()[0]}")
    main()
    failed = RESULTS.count(False)
    print(f"{len(RESULTS) - failed}/{len(RESULTS)} passed")
    sys.stdout.flush()
    os._exit(1 if failed else 0)
