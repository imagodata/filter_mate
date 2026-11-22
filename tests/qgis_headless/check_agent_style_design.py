"""design_style in a real (headless) QGIS: palettes by their job, the three modes, every look of each geometry, icons
of the SVG library in the colour of their category, the variants, the check of colours, a render, the undo of the turn.

    docker run --rm -v "$PWD":/src -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr \\
        python3 /src/tests/qgis_headless/check_agent_style_design.py

Prints one PASS / FAIL line per check; exits with 1 when one failed.
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import (  # noqa: E402
    QgsApplication, QgsFeature, QgsGeometry, QgsMapRendererParallelJob, QgsMapSettings, QgsProject, QgsRectangle,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QSize  # noqa: E402

RESULTS = []


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {str(detail)[:400]}" if not condition else ""))


def refused(call):
    try:
        call()
    except ValueError:
        return True
    return False


def layer(kind, name, rows):
    made = QgsVectorLayer(f"{kind}?crs=EPSG:2154&field=nature:string&field=pop:double", name, "memory")
    features = []
    for wkt, nature, pop in rows:
        feature = QgsFeature(made.fields())
        feature.setGeometry(QgsGeometry.fromWkt(wkt))
        feature.setAttributes([nature, pop])
        features.append(feature)
    made.dataProvider().addFeatures(features)
    made.updateExtents()
    QgsProject.instance().addMapLayer(made)
    return made


def renders(target):
    settings = QgsMapSettings()
    settings.setLayers([target])
    settings.setExtent(target.extent().buffered(100))
    settings.setOutputSize(QSize(200, 200))
    job = QgsMapRendererParallelJob(settings)
    job.start()
    job.waitForFinished()
    image = job.renderedImage()
    return not image.isNull() and len(job.errors()) == 0


def main():
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.adapters.public_api import style_design
    from filter_mate.core.agent.messages import ToolCallPart
    natures = ["Bois", "Prairie", "Bati", "Eau", "Vigne", "Verger", "Lande", "Friche", "Carriere", "Parc"]
    polygons = layer("Polygon", "occupation", [
        (QgsRectangle(600000 + i * 100, 6200000, 600090 + i * 100, 6200090).asWktPolygon(), natures[i % 10],
         float(i * 13 % 97)) for i in range(40)])
    lines = layer("LineString", "routes", [(f"LINESTRING({600000 + i * 50} 6200000, {600000 + i * 50} 6201000)",
                                            ["Autoroute", "Nationale", "Departementale"][i % 3], float(i))
                                           for i in range(9)])
    points = layer("Point", "lieux", [(f"POINT({600000 + i * 40} 6200500)", ["ecole", "mairie"][i % 2], float(i))
                                      for i in range(6)])

    single = style_design.design_style("occupation")
    check("single: one symbol of the first colour of the palette", single["palette"] == "filtermate" and
          single["colors"] == ["#2a78d6"] and polygons.renderer().type() == "singleSymbol", single)
    cats = style_design.design_style("occupation", "categorized", "nature", look="outlined", limit=8)
    check("categorized: 8 categories and the grey of the others", cats["categories"] == 8 and cats["others"] and
          len(polygons.renderer().categories()) == 9 and "problems" not in cats, cats)
    labels = [category.label() for category in polygons.renderer().categories()]
    check("categorized: colours given in a stable order (sorted), the rest last", labels[:-1] == sorted(labels[:-1])
          and labels[-1] == "Others", labels)
    graded = style_design.design_style("occupation", "graduated", "pop", palette="viridis", classes=5,
                                       method="jenks")
    check("graduated: classes in a sequential palette", graded["classes"] >= 3 and graded["palette"] == "viridis" and
          polygons.renderer().type() == "graduatedSymbol", graded)
    diverging = style_design.design_style("occupation", "graduated", "pop", palette="rdbu", classes=5)
    check("graduated: a diverging palette", diverging["palette"] == "rdbu", diverging)
    hatched = style_design.design_style("occupation", "categorized", "nature", look="hatched", palette="okabe_ito",
                                        limit=7)
    check("hatched: lines in the colour of each category", "problems" not in hatched and renders(polygons), hatched)
    weak = style_design.design_style("occupation", "categorized", "nature", palette="set2")
    check("the check of colours says what a reader cannot tell apart (set2)", weak.get("problems"), weak)
    check("the credit of ColorBrewer travels with its palettes", "ColorBrewer" in weak.get("credit", ""), weak)

    roads = style_design.design_style("routes", "categorized", "nature", look="casing")
    road_categories = lines.renderer().categories()  # copies: kept alive while their symbols are read
    check("casing: two lines per road, casings under every line (symbol levels)", lines.renderer().usingSymbolLevels()
          and road_categories[0].symbol().symbolLayerCount() == 2 and renders(lines), roads)
    for look in ("halo", "dashed", "flat"):
        check(f"line look {look}", style_design.design_style("routes", look=look)["look"] == look and renders(lines))
    icons = style_design.design_style("lieux", "categorized", "nature", look="icon", icon="library")
    point_categories = points.renderer().categories()
    first = point_categories[0].symbol().symbolLayer(0)
    check("icon: an SVG of QGIS in the colour of each category", icons["icon"] and first.layerType() == "SvgMarker"
          and first.fillColor().name() == icons["colors"][0] and renders(points), icons)
    badge = style_design.design_style("lieux", look="badge", icon="library", variant="dark")
    check("badge: a dot of the colour and the icon in the background colour", badge["variant"] == "dark" and
          points.renderer().symbol().symbolLayerCount() == 2 and renders(points), badge)
    for variant in ("dark", "print", "discreet"):
        made = style_design.design_style("occupation", "categorized", "nature", variant=variant)
        check(f"variant {variant}: other colours than the light ones", made["colors"] != cats["colors"], made["colors"])
    for call, label in ((lambda: style_design.design_style("occupation", look="casing"), "a look of another geometry"),
                        (lambda: style_design.design_style("lieux", look="icon"), "an icon look without icon"),
                        (lambda: style_design.design_style("lieux", look="icon", icon="zzqx"), "an unknown icon"),
                        (lambda: style_design.design_style("occupation", "graduated", "nature"), "a text graduated"),
                        (lambda: style_design.design_style("occupation", "graduated", "pop", palette="set2"),
                         "a categorical palette for classes"),
                        (lambda: style_design.design_style("occupation", palette="rainbow"), "an unknown palette")):
        check(f"refuses {label}", refused(call))
    listed = style_design.list_palettes("categorical")
    check("list_palettes: the categorical ones and what their check says", {"filtermate", "okabe_ito", "set2"} <=
          {row["name"] for row in listed["palettes"]} and
          next(row for row in listed["palettes"] if row["name"] == "set2")["problems"], listed["defaults"])

    recorder = EffectsRecorder()
    before = polygons.renderer().type()
    recorder.before_call(ToolCallPart("s1", "design_style", {"layer": "occupation"}))
    style_design.design_style("occupation", "graduated", "pop", palette="magma")
    effects = recorder.finish()
    done, left = apply_effects(effects, undo=True)
    check("undo brings the style of before", not left and polygons.renderer().type() == before, (done, left))
    apply_effects(effects, undo=False)
    check("redo draws the classes again", polygons.renderer().type() == "graduatedSymbol")


if __name__ == "__main__":
    app = QgsApplication([b"check_agent_style_design"], False)
    app.initQgis()
    package_root = os.environ.get("FM_PACKAGE_ROOT") or tempfile.mkdtemp()
    if not os.environ.get("FM_PACKAGE_ROOT"):
        os.symlink(os.environ.get("FM_REPO", "/src"), os.path.join(package_root, "filter_mate"))
    sys.path.insert(0, package_root)
    sys.dont_write_bytecode = True
    print(f"QGIS {__import__('qgis.core').core.Qgis.QGIS_VERSION}, Python {sys.version.split()[0]}")
    main()
    failed = RESULTS.count(False)
    print(f"{len(RESULTS) - failed}/{len(RESULTS)} passed")
    sys.stdout.flush()
    os._exit(1 if failed else 0)
