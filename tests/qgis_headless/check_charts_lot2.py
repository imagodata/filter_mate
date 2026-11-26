"""Lot 2 integration checks on real QGIS/Qt. Mount the checkout at /src and an output folder at /artifacts.

QT_QPA_PLATFORM=offscreen QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox python3 /src/tests/qgis_headless/check_charts_lot2.py
"""
import json
import os
import sys
import time
import types
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")
sys.dont_write_bytecode = True

from qgis.core import Qgis, QgsApplication, QgsFeature, QgsField, QgsLayoutItemPicture, QgsPrintLayout, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QT_VERSION_STR, QVariant
from qgis.PyQt.QtGui import QImage

RESULTS = []


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f": {detail}" if not condition else ""), flush=True)


def failure(call):
    try:
        call()
    except Exception as exc:
        return str(exc)
    return ""


def main():
    from filter_mate.adapters.agent import chart_renderer
    from filter_mate.adapters.public_api import charts as layout_charts
    from filter_mate.core.agent.charts import chart_spec, page_html, parse_request, rows_data
    from filter_mate.ui.controllers.agent_charts import AgentCharts

    parent = Path(os.environ.get("FM_CHART_OUTPUT", "/artifacts"))
    import tempfile
    output = Path(tempfile.mkdtemp(prefix="run-", dir=parent))
    print(f"ARTIFACTS {output}", flush=True)
    charts = AgentCharts(lambda: True)
    engine_available = chart_renderer.available()
    project = QgsProject.instance()
    layer = QgsVectorLayer("Point?crs=EPSG:2154", "Private layer", "memory")
    layer.dataProvider().addAttributes([QgsField("category", QVariant.String), QgsField("value", QVariant.Double),
                                       QgsField("x", QVariant.Double)])
    layer.updateFields()
    for index in range(12):
        feature = QgsFeature(layer.fields())
        feature.setAttributes([f"secret-category-{index}", index + 1, index])
        layer.dataProvider().addFeatures([feature])
    project.addMapLayer(layer)
    check("real vector fixture", layer.isValid() and layer.featureCount() == 12)
    ids = {}
    started = time.monotonic()
    for kind in ("bar", "histogram", "pie", "line", "scatter", "kpi", "treemap", "area"):
        arguments = {"kind": kind, "layer": layer.id(), "field": "category", "title": f"Chart {kind}"}
        if kind == "histogram":
            arguments["field"] = "value"
        elif kind in ("line", "area", "scatter"):
            arguments.update(field="x", value_field="value", aggregate="sum")
        answer = charts.show_chart(arguments, False)
        chart = charts.pending
        ids[kind] = chart.chart_id
        check(f"{kind}: valid QtSvg without WebEngine", chart_renderer.svg_renderer(chart.svg).isValid())
        check(f"{kind}: no model values or image", "data" not in answer and not hasattr(answer, "images")
              and "secret-category" not in json.dumps(answer))
        check(f"{kind}: local drawing and marks", bool(chart.svg) and bool(charts.card_drawing(chart)(280, 200)[1]))
        if kind == "kpi":
            check("KPI: remainder fits the card limit", len(chart.data) == 4 and chart.data[-1]["others"])
    check("standards create no WebEngine page", chart_renderer._page is None)
    check("eight standards under 3 seconds", time.monotonic() - started < 3)
    shared = charts.show_chart({"kind": "treemap", "layer": layer.id(), "field": "category"}, True)
    check("sharing enabled returns aggregate data", bool(shared.get("data")))

    rows = [{"label": "A & <B>", "value": 45200}, {"label": "B", "value": 21000}]
    base = charts.show_chart({"kind": "kpi", "rows": rows, "title": "Big numbers"}, False)["chart_id"]
    for file_format, magic in (("png", b"\x89PNG"), ("jpg", b"\xff\xd8\xff"), ("svg", b"<?xml"), ("pdf", b"%PDF")):
        result = charts.export_chart({"chart_id": base, "format": file_format, "dpi": 150}, str(output))
        path = output / "charts" / result["path"]
        check(f"export chart {file_format}", path.read_bytes().startswith(magic) and result["bytes"] > 300)
    picture = QImage(str(output / "charts" / "Big_numbers.png"))
    check("PNG resolution", (picture.width(), picture.height()) == (1000, 625))
    check("JPEG is opaque", not QImage(str(output / "charts" / "Big_numbers.jpg")).hasAlphaChannel())
    duplicate = charts.export_chart({"chart_id": base, "format": "svg"}, str(output))
    check("export preserves existing files", duplicate["path"] == "Big_numbers_2.svg")
    check("export refuses path traversal", bool(failure(lambda: charts.export_chart(
        {"chart_id": base, "subfolder": "../outside"}, str(output)))))
    check("export refuses an excessive raster", "too large" in failure(lambda: chart_renderer.image(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1200"><rect width="10" height="10"/></svg>',
        6.25)))
    check("export refuses invalid dpi", bool(failure(lambda: chart_renderer.write(
        charts.chart(base).svg, str(output / "invalid.png"), "png", 601))))

    info = charts.show_infographic({"title": "Offline overview", "charts": [base, ids["treemap"], ids["area"], ids["bar"]],
                                    "caption": "Local values", "source": "A & B"}, False)
    check("infographic: four charts, no model values", len(info["charts"]) == 4 and "secret-category" not in json.dumps(info))
    check("infographic: fifth chart refused", bool(failure(lambda: charts.show_infographic(
        {"title": "Too much", "charts": [base] + list(ids.values())[:4]}, True))))
    for file_format, magic in (("html", b"<!doctype html>"), ("png", b"\x89PNG"), ("jpg", b"\xff\xd8\xff"),
                               ("svg", b"<?xml"), ("pdf", b"%PDF")):
        result = charts.export_infographic({"infographic_id": info["infographic_id"], "format": file_format, "dpi": 96},
                                           str(output))
        path = output / "infographics" / result["path"]
        check(f"export infographic {file_format}", path.read_bytes().startswith(magic) and result["bytes"] > 300)
    html_path = output / "infographics" / "Offline_overview.html"
    html = html_path.read_text()
    check("offline HTML embeds safe SVG and CSP", "<svg" in html and "Content-Security-Policy" in html
          and "<script" not in html and "src=" not in html and "href=" not in html)
    check("infographic QtSvg keeps all values", chart_renderer.svg_renderer(charts.pending_infographic.svg).isValid()
          and "secret-category" in charts.pending_infographic.svg)
    renderer = chart_renderer.svg_renderer(charts.pending_infographic.svg)
    check("QtSvg draws all four embedded parts", all(not renderer.boundsOnElement(f"fm_part{position}").isEmpty()
          for position in range(4)))

    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName("Charts")
    project.layoutManager().addLayout(layout)
    placed = charts.add_to_layout({"chart_id": ids["area"], "layout": "Charts"})
    items = [item for item in layout.items() if isinstance(item, QgsLayoutItemPicture) and item.customProperty(layout_charts.PROPERTY)]
    check("layout chart follows its layer", placed["follows_filter"] and len(items) == 1)
    before = items[0].picturePath()
    layer.setSubsetString('"x" < 4')
    charts.redraw_layer(layer.id())
    check("layout redraws without WebEngine", items[0].picturePath() != before)
    planted = json.loads(items[0].customProperty(layout_charts.PROPERTY))
    planted["code"] = "throw new Error('must never run')"
    items[0].setCustomProperty(layout_charts.PROPERTY, json.dumps(planted))
    before = items[0].picturePath()
    layer.setSubsetString("")
    charts.redraw_layer(layer.id())
    check("layout never runs persisted code", items[0].picturePath() == before)
    snapshot = charts.pending_infographic.svg
    check("infographic keeps its snapshot after filter changes", charts.infographic(info["infographic_id"]).svg == snapshot)

    chart_renderer._engine = ""
    check("standard export without engine", charts.export_chart({"chart_id": base, "format": "pdf"}, str(output))["bytes"] > 300)
    check("expert mode missing engine is explicit", "QtWebEngine" in failure(lambda: charts.run_chart_code(
        {"chart_id": base, "code": "svg.append('rect')"}, False)))
    chart_renderer._engine = "ok" if engine_available else ""
    if engine_available:
        code = "svg.append('rect').attr('width', 80).attr('height', 40).attr('fill', palette.series[0]);"
        hidden = charts.run_chart_code({"chart_id": base, "code": code}, False)
        check("expert code still draws, no unshared image", hidden.get("code") and not hasattr(hidden, "images"))
        shown = charts.run_chart_code({"chart_id": base, "code": code}, True)
        check("expert shared image", bool(getattr(shown, "images", ())))
        quiet = charts.run_chart_code({"chart_id": base, "code": code + " console.error('secret-category-9 45200');"}, False)
        check("expert errors hide unshared values", quiet.get("errors") and "secret-category" not in str(quiet)
              and "45200" not in str(quiet))
        message = failure(lambda: charts.run_chart_code({"chart_id": base, "code":
            "d3.select('svg').remove(); throw new Error(JSON.stringify(data));"}, False))
        check("expert thrown values are hidden", bool(message) and "45200" not in message and "A &" not in message)
        drawn = charts.run_chart_code({"chart_id": base, "code": code +
            " svg.append('image').attr('href','file:///etc/passwd');"}, False)
        check("expert file references removed", "<image" not in charts.pending.svg and "/etc/passwd" not in charts.pending.svg)
        expert = charts.pending
        original = chart_renderer.render
        chart_renderer.render = lambda *args: (_ for _ in ()).throw(AssertionError("expert reran"))
        try:
            check("expert export uses its saved SVG", charts.export_chart({"chart_id": expert.chart_id, "format": "pdf"}, str(output))["bytes"] > 300)
            check("expert infographic uses saved SVG", bool(charts.show_infographic(
                {"title": "Expert snapshot", "charts": [expert.chart_id]}, False)))
        finally:
            chart_renderer.render = original
        for kind in ("kpi", "treemap", "area"):
            request = parse_request({"kind": kind, "rows": rows if kind != "area" else
                                     [{"x": 1, "y": -4}, {"x": 2, "y": -2}]})
            data, meta = rows_data(request, "Others", "(empty)")
            spec = chart_spec(request, data, "light", x_type=meta.get("x_type", ""))
            result = chart_renderer.render(page_html(spec))
            check(f"d3 fallback {kind}", bool(result.svg) and not result.errors, result.errors)
            chart_renderer.drop_page()
        started = time.monotonic()
        message = failure(lambda: charts.run_chart_code({"chart_id": base, "code": "while (true) {}"}, False))
        check("expert loop times out and drops page", bool(message) and time.monotonic() - started < 25
              and chart_renderer._page is None)
        check("standard still draws after timeout", charts.show_chart({"kind": "kpi", "rows": rows}, False)["points"] == 2)
        from qgis.PyQt.QtCore import QEventLoop, QTimer, QUrl
        from qgis.PyQt.QtWebEngineCore import QWebEnginePage
        page = QWebEnginePage()
        event_loop = QEventLoop()
        loaded = []
        page.loadFinished.connect(lambda okay: (loaded.append(okay), event_loop.quit()))
        QTimer.singleShot(5000, event_loop.quit)
        page.load(QUrl.fromLocalFile(str(html_path)))
        event_loop.exec()
        check("standalone HTML loads in offline browser", loaded == [True])
        found = []
        page.runJavaScript("document.querySelectorAll('svg > g[id^=fm_part]').length", lambda value: (found.append(value), event_loop.quit()))
        QTimer.singleShot(5000, event_loop.quit)
        event_loop.exec()
        check("offline browser sees four embedded charts", found == [4], found)
        page.deleteLater()
    else:
        print("SKIP expert/browser execution: QtWebEngine unavailable", flush=True)
    charts.unwatch_all()
    chart_renderer.drop_page()
    project.clear()


if __name__ == "__main__":
    package = types.ModuleType("filter_mate")
    package.__path__ = [os.environ.get("FM_REPO", "/src")]
    sys.modules["filter_mate"] = package
    app = QgsApplication([b"lot2_charts"], False)
    app.initQgis()
    print(f"QGIS {Qgis.QGIS_VERSION}; Qt {QT_VERSION_STR}", flush=True)
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        RESULTS.append(False)
    failed = RESULTS.count(False)
    print(f"RESULT {len(RESULTS) - failed}/{len(RESULTS)} passed", flush=True)
    os._exit(1 if failed else 0)
