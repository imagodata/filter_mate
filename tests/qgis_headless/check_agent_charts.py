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
        said = failure(lambda: charts.show_chart({"kind": "bar", "rows": [{"label": "a", "value": 1}]}, False, True))
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
    bar = charts.show_chart({"kind": "bar", "layer": "batiments", "field": "usage", "title": "Usages"}, False, True)
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
        answer = charts.show_chart(arguments, False, True)
        svg = charts.pending.svg
        check(f"{arguments['kind']}: drawn", answer["points"] > 0 and "<svg" in svg and
              chart_renderer.svg_renderer(svg).isValid() and not answer.get("errors"), answer)
    check("five more charts in under 3 s", time.time() - started < 3, time.time() - started)
    line = charts.chart("c4")
    check("line: a date field is a time axis", line.meta.get("x_type") == "time", line.meta)
    check("no value of the layer for a user who does not share them",
          "data" not in charts.show_chart({"kind": "bar", "layer": "batiments", "field": "usage"}, False, False))

    # --- rows, refusals
    rows = charts.show_chart({"kind": "bar", "rows": [{"label": "A", "value": 3}, {"label": "B", "value": 7}],
                              "title": "Rows"}, False, True)
    check("rows: drawn, said to be given", rows["source"] == "rows" and rows["points"] == 2, rows)
    for arguments, label in (({"kind": "bar", "layer": "batiments", "field": "nope"}, "an unknown field"),
                             ({"kind": "histogram", "layer": "batiments", "field": "usage"}, "a text histogram"),
                             ({"kind": "bar", "layer": "nope", "field": "usage"}, "an unknown layer"),
                             ({"kind": "bar", "rows": [{"label": "A", "value": 1}], "code": "svg.append('rect')"},
                              "code without the expert mode")):
        check(f"refuses {label}", failure(lambda: charts.show_chart(arguments, False, True)))

    # --- code of the expert mode
    code = ("svg.selectAll('rect.x').data(data).join('rect').attr('x', (d, i) => 20 + i * 60).attr('y', 40)"
            ".attr('width', 50).attr('height', d => d.value * 10).attr('fill', palette.series[1]);")
    drawn = charts.show_chart({"kind": "bar", "rows": [{"label": "A", "value": 3}, {"label": "B", "value": 7}],
                               "code": code}, True, True)
    check("code: drawn, its image sent back", hasattr(drawn, "images") and drawn.answer["code"] and
          charts.pending.svg.count("<rect") >= 3, getattr(drawn, "answer", drawn))
    told = charts.show_chart({"kind": "bar", "rows": [{"label": "A", "value": 1}],
                              "code": "svg.append('rect').attr('x', nope.y);"}, True, True)
    check("code: an error of the script is told with what it drew",
          any("nope" in error for error in told.answer.get("errors", [])), told.answer)
    said = failure(lambda: charts.show_chart({"kind": "bar", "rows": [{"label": "A", "value": 1}],
                                              "code": "d3.select('svg').remove(); throw new Error('boom');"},
                                             True, True))
    check("code: no chart at all is refused with the error", "boom" in said, said)

    hits = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            hits.append(self.path)
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    address = f"http://127.0.0.1:{server.server_address[1]}"
    leak = (f"fetch('{address}/fetch').catch(() => 0); new Image().src = '{address}/img';"
            f"svg.append('image').attr('href', '{address}/svg'); svg.append('rect').attr('width', 10)"
            ".attr('height', 10);")
    try:
        charts.show_chart({"kind": "bar", "rows": [{"label": "A", "value": 1}], "code": leak}, True, True)
    except Exception:  # noqa: BLE001 - only what reached the server matters
        pass
    deadline = time.time() + 2
    while time.time() < deadline:
        QgsApplication.processEvents()
        time.sleep(0.05)
    server.shutdown()
    check("code: reaches no network", not hits, hits)

    started = time.time()
    said = failure(lambda: charts.show_chart({"kind": "bar", "rows": [{"label": "A", "value": 1}],
                                              "code": "while (true) {}"}, True, True))
    check("code: a loop that never ends is stopped", "in time" in said and time.time() - started < 25, said)
    again = charts.show_chart({"kind": "bar", "rows": [{"label": "A", "value": 2}]}, False, True)
    check("after it, a new page draws the next chart", again["points"] == 1, again)

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
