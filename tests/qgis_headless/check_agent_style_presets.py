"""Official styles of the agent in a real (headless) QGIS: presets listed for tables of the BD TOPO and an OSM layer,
applied (rule-based renderer, scale ranges, labels), drawn without error, the variants gris and sombre, refusals in
words, all_scales, and the turn undone and applied again.

    docker run --rm -v "$PWD":/src -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr \\
        sh -c 'cd /tmp && xvfb-run -a python3 /src/tests/qgis_headless/check_agent_style_presets.py'

Run on qgis/qgis:latest, ltr and release-3_22: the QML files are written by the newest QGIS and must load in 3.22.
Prints one PASS / FAIL line per check; exits with 1 when one failed.
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import (  # noqa: E402
    QgsApplication, QgsFeature, QgsField, QgsFields, QgsGeometry, QgsMapRendererParallelJob, QgsMapSettings,
    QgsProject, QgsRectangle, QgsRuleBasedLabeling, QgsRuleBasedRenderer,
    QgsVectorFileWriter, QgsVectorLayer, QgsCoordinateReferenceSystem, QgsCoordinateTransformContext, QgsWkbTypes,
)
from qgis.PyQt.QtCore import QSize, QVariant  # noqa: E402
from qgis.PyQt.QtGui import QColor  # noqa: E402

RESULTS = []


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {str(detail)[:400]}" if not condition else ""))


def refusal(call):
    try:
        call()
    except ValueError as exc:
        return str(exc)
    return ""


# Around Toulouse, in Lambert-93: a few metres apart.
TABLES = {
    "batiment": ("MultiPolygon", {"nature": "Indifférenciée", "usage_1": "Résidentiel", "hauteur": 9.5},
                 "POLYGON((574000 6279000, 574020 6279000, 574020 6279015, 574000 6279015, 574000 6279000))"),
    "troncon_de_route": ("LineString", {"nature": "Route à 1 chaussée", "importance": "3"},
                         "LINESTRING(573950 6278990, 574100 6279030)"),
    "commune": ("MultiPolygon", {"nom_officiel": "Toulouse", "code_insee": "31555"},
                "POLYGON((573900 6278900, 574200 6278900, 574200 6279200, 573900 6279200, 573900 6278900))"),
    "mes_lignes": ("LineString", {"osm_id": "1", "name": "Allées Jean Jaurès", "highway": "primary"},
                   "LINESTRING(573960 6279000, 574090 6279020)"),
    "autre_batiment": ("MultiPolygon", {"nature": "x"},
                       "POLYGON((574030 6279000, 574040 6279000, 574040 6279010, 574030 6279000))"),
}


def make_gpkg(folder):
    path = os.path.join(folder, "bdtopo.gpkg")
    for index, (table, (geometry, values, wkt)) in enumerate(TABLES.items()):
        fields = QgsFields()
        for name, value in values.items():
            fields.append(QgsField(name, QVariant.Double if isinstance(value, float) else QVariant.String))
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.layerName = table
        if index:
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        writer = QgsVectorFileWriter.create(path, fields, getattr(QgsWkbTypes, geometry),
                                            QgsCoordinateReferenceSystem("EPSG:2154"),
                                            QgsCoordinateTransformContext(), options)
        feature = QgsFeature(fields)
        for name, value in values.items():
            feature[name] = value
        feature.setGeometry(QgsGeometry.fromWkt(wkt))
        writer.addFeature(feature)
        del writer
    layers = {}
    for table in TABLES:
        layer = QgsVectorLayer(f"{path}|layername={table}", table if table != "mes_lignes" else "OSM highway", "ogr")
        assert layer.isValid(), table
        QgsProject.instance().addMapLayer(layer)
        layers[table] = layer
    return layers


def render(layers, scale):
    settings = QgsMapSettings()
    settings.setLayers(layers)
    settings.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:2154"))
    settings.setOutputSize(QSize(400, 400))
    settings.setBackgroundColor(QColor(0, 0, 0, 0))  # a pixel painted is one a layer drew
    settings.setExtent(QgsRectangle(573900, 6278900, 574200, 6279200))
    if scale:
        center = settings.extent().center()
        half = scale * 400 * 0.0254 / 96 / 2  # the extent of 400 px at 96 dpi at this scale
        settings.setExtent(QgsRectangle(center.x() - half, center.y() - half, center.x() + half, center.y() + half))
    job = QgsMapRendererParallelJob(settings)
    job.start()
    job.waitForFinished()
    image = job.renderedImage()
    painted = sum(1 for x in range(0, 400, 8) for y in range(0, 400, 8) if image.pixelColor(x, y).alpha() > 0)
    return painted, [error.message for error in job.errors()], settings.scale()


def first_fill(layer):
    for rule in layer.renderer().rootRule().children():
        symbol = rule.symbol()
        if symbol is not None and symbol.type() == 2:  # a fill
            return symbol.symbolLayer(0).color()
    return QColor()


def main():
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.adapters.public_api import style_presets
    from filter_mate.core.agent.messages import ToolCallPart
    from filter_mate.core.agent.style_presets import to_oklab
    layers = make_gpkg(tempfile.mkdtemp())
    buildings, roads, communes, osm, other = (layers[name] for name in TABLES)

    every = style_presets.list_style_presets()
    ids = [row["preset"] for row in every["presets"]]
    check("all presets: the four BD TOPO styles and one of OpenStreetMap",
          all(f"ign/bdtopo/{name}" in ids for name in ("classique", "routier", "bati", "hydrographie"))
          and any(preset.startswith("osm/") for preset in ids), ids)
    listed = style_presets.list_style_presets("batiment")
    rows = [(row["preset"], row["table"]) for row in listed["presets"]]
    check("batiment: classique and bati listed for the table batiment",
          ("ign/bdtopo/classique", "batiment") in rows and ("ign/bdtopo/bati", "batiment") in rows, rows)
    rows = [(row["preset"], row["table"]) for row in style_presets.list_style_presets("troncon_de_route")["presets"]]
    check("troncon_de_route: classique and routier", ("ign/bdtopo/routier", "troncon_de_route") in rows, rows)
    rows = [(row["preset"], row["table"]) for row in style_presets.list_style_presets("OSM highway")["presets"]]
    check("an OSM layer of highway lines: the roads of OpenStreetMap first",
          rows and rows[0][1] == "roads" and rows[0][0].startswith("osm/"), rows)
    check("a layer that fits no table says so", not style_presets.list_style_presets("autre_batiment")["presets"])

    answer = style_presets.apply_style_preset("batiment", "ign/bdtopo/classique")
    renderer = buildings.renderer()
    check("applied: a rule-based renderer with the rules of the style",
          isinstance(renderer, QgsRuleBasedRenderer) and len(renderer.rootRule().children()) == answer["rules"] >= 8,
          answer)
    scales = {round(rule.minimumScale()) for rule in renderer.rootRule().children()}
    check("its zoom range as a scale range: shown from 1:48,258 (zoom 13.5) and closer", scales == {48258} and
          answer.get("drawn_from") == "1:48,258", (scales, answer))
    pink = first_fill(buildings)
    check("the colours of IGN kept (residential #ff6dee), read by this QGIS",
          (pink.red(), pink.green(), pink.blue()) == (255, 109, 238), pink.name())
    painted, errors, scale = render([buildings, roads], 5000)
    check("drawn at 1:5,000 without error", painted > 0 and not errors, (painted, errors, scale))
    painted_far, errors, scale = render([buildings], 200000)
    check("nothing drawn at 1:200,000 (further out than the style draws buildings)", painted_far == 0 and not errors,
          (painted_far, errors, scale))

    answer = style_presets.apply_style_preset("troncon_de_route", "routier")
    check("a preset named by its end, the table found from the layer",
          answer["preset"] == "ign/bdtopo/routier" and answer["table"] == "troncon_de_route", answer)
    answer = style_presets.apply_style_preset("commune", "ign/bdtopo/classique")
    check("labels: a rule-based labeling, on", isinstance(communes.labeling(), QgsRuleBasedLabeling)
          and communes.labelsEnabled() and answer["labels"] >= 1, answer)
    painted, errors, _ = render([communes], 10000)
    check("the outlines and labels of a commune drawn without error", painted > 0 and not errors, (painted, errors))

    style_presets.apply_style_preset("batiment", "ign/bdtopo/classique", variant="sombre")
    dark = first_fill(buildings)
    check("sombre: the pale pink becomes dark, its hue kept", to_oklab(dark.red(), dark.green(), dark.blue())[0] < 0.4
          and dark.red() > dark.green(), dark.name())
    style_presets.apply_style_preset("batiment", "ign/bdtopo/classique", variant="gris")
    grey = first_fill(buildings)
    check("gris: nearly grey", max(grey.red(), grey.green(), grey.blue()) - min(grey.red(), grey.green(),
                                                                                grey.blue()) < 25, grey.name())
    painted, errors, _ = render([buildings], 5000)
    check("a variant draws without error", painted > 0 and not errors, (painted, errors))

    answer = style_presets.apply_style_preset("batiment", "ign/bdtopo/classique", all_scales=True)
    check("all_scales: no scale range left", all(rule.minimumScale() == 0 and rule.maximumScale() == 0
                                                 for rule in buildings.renderer().rootRule().children())
          and "drawn_from" not in answer, answer)
    check("a layer drawn at every scale stays so", not buildings.hasScaleBasedVisibility())

    # 2026-11-23: a BD TOPO layer of the Géoplateforme opened by the agent is drawn only from 1:25,000 (each move
    # downloads what the view holds); the style, whose QML says hasScaleBasedVisibilityFlag="0", must not undo it.
    buildings.setScaleBasedVisibility(True)
    buildings.setMinimumScale(25000)
    answer = style_presets.apply_style_preset("batiment", "ign/bdtopo/classique")
    check("a style keeps the scale the layer is drawn from", buildings.hasScaleBasedVisibility()
          and buildings.minimumScale() == 25000 and "1:25,000" in answer.get("note", ""), answer)
    check("the answer gives the scale drawn from, the closer of the producer's (1:48,258) and the layer's",
          answer.get("drawn_from") == "1:25,000" and "all_scales" not in answer["note"], answer)
    answer = style_presets.apply_style_preset("batiment", "ign/bdtopo/classique", all_scales=True)
    check("all_scales drops the ranges of the producer, not the scale of the layer",
          buildings.hasScaleBasedVisibility() and buildings.minimumScale() == 25000
          and all(rule.minimumScale() == 0 for rule in buildings.renderer().rootRule().children())
          and "1:25,000" in answer.get("note", ""), answer)
    buildings.setMinimumScale(1e8)  # QGIS's default: only a limit when zooming in
    buildings.setMaximumScale(500)
    answer = style_presets.apply_style_preset("batiment", "ign/bdtopo/classique")
    check("a layer limited only when zooming in: the producer's scale, all_scales at every scale",
          answer.get("drawn_from") == "1:48,258" and "100,000,000" not in answer["note"]
          and "at every scale" in answer["note"], answer)
    buildings.setMaximumScale(0)
    buildings.setScaleBasedVisibility(False)

    answer = style_presets.apply_style_preset("OSM highway", "osm/colorful")
    check("OSM roads: rules on highway, the name labelled", answer["table"] == "roads" and
          "highway" in osm.renderer().dump() and osm.labelsEnabled(), answer)
    painted, errors, _ = render([osm], 5000)
    check("OSM roads drawn at 1:5,000 without error (widths computed from the scale)", painted > 0 and not errors,
          (painted, errors))

    said = refusal(lambda: style_presets.apply_style_preset("autre_batiment", "ign/bdtopo/classique/batiment"))
    check("refused in words: a table whose fields the layer lacks", "usage_1" in said, said)
    said = refusal(lambda: style_presets.apply_style_preset("batiment", "ign/bdtopo/classique/troncon_de_route"))
    check("refused: a table of another geometry", "geometry" in said, said)
    said = refusal(lambda: style_presets.apply_style_preset("autre_batiment", "classique"))
    check("refused: a layer named as a table, without its fields", "usage_1" in said, said)
    said = refusal(lambda: style_presets.apply_style_preset("OSM highway", "classique"))
    check("refused: a layer that fits no table of the preset", "no table" in said, said)
    check("refused: an unknown preset and variant",
          refusal(lambda: style_presets.apply_style_preset("batiment", "plan_ign"))
          and refusal(lambda: style_presets.apply_style_preset("batiment", "classique", variant="sepia")))

    before = other.renderer().type()
    other.dataProvider().addAttributes([QgsField("usage_1", QVariant.String)])
    other.updateFields()
    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("p1", "apply_style_preset", {"layer": other.id(), "preset": "classique"}))
    style_presets.apply_style_preset(other.id(), "ign/bdtopo/classique/batiment")
    effects = recorder.finish()
    done, left = apply_effects(effects, undo=True)
    check("undo brings the style of before", not left and other.renderer().type() == before, (done, left))
    apply_effects(effects, undo=False)
    check("redo applies the official style again", other.renderer().type() == "RuleRenderer")


if __name__ == "__main__":
    app = QgsApplication([b"check_agent_style_presets"], False)
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
