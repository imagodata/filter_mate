"""Thematic maps and labels of the agent in a real (headless) QGIS: the heatmap, clusters, displaced points,
proportional symbols, dot density, 2.5D blocks and diverging classes of set_layer_style, the background, callouts,
font, wrap, priority, obstacle, scales and placements of set_labels; each drawn to an image, and each brought back by
the undo of the turn (its style as XML).

    docker run --rm -v "$PWD":/src -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr \\
        sh -c 'cd /tmp && xvfb-run -a python3 /src/tests/qgis_headless/check_agent_symbology.py'

Prints one PASS / FAIL line per check; exits with 1 when one failed.
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import (  # noqa: E402
    QgsApplication, QgsFeature, QgsField, QgsFields, QgsGeometry, QgsMapRendererParallelJob, QgsMapSettings,
    QgsPointXY, QgsProject, QgsRectangle, QgsVectorFileWriter, QgsVectorLayer,
)
from qgis.PyQt.QtCore import QSize, QVariant  # noqa: E402
from qgis.PyQt.QtGui import QColor  # noqa: E402

RESULTS = []


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {str(detail)[:400]}" if not condition else ""))


def refused(call):
    """The message of the ValueError ``call`` raises; "" when it raises none."""
    try:
        call()
    except ValueError as exc:
        return str(exc) or "refused"
    return ""


def write_layer(path, geometry, rows):
    """A GeoPackage of ``rows`` ``(geometry, nom, pop, hauteur, change)``."""
    fields = QgsFields()
    for name, kind in (("nom", QVariant.String), ("pop", QVariant.Int), ("hauteur", QVariant.Double),
                       ("change", QVariant.Double)):
        fields.append(QgsField(name, kind))
    memory = QgsVectorLayer(f"{geometry}?crs=EPSG:2154", "memory", "memory")
    memory.dataProvider().addAttributes(fields.toList())
    memory.updateFields()
    features = []
    for shape, *values in rows:
        feature = QgsFeature(memory.fields())
        feature.setGeometry(shape)
        feature.setAttributes(values)
        features.append(feature)
    memory.dataProvider().addFeatures(features)
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    QgsVectorFileWriter.writeAsVectorFormatV2(memory, path, QgsProject.instance().transformContext(), options)


def fixtures(work):
    polygons, points, lines = [], [], []
    for index in range(12):
        x, y = 600000 + (index % 4) * 5000, 6280000 + (index // 4) * 5000
        polygons.append((QgsGeometry.fromRect(QgsRectangle(x, y, x + 4000, y + 4000)), f"Commune {index + 1:02d}",
                         100 * (index + 1), 3.0 * (index + 1), -50.0 + 15 * index))
        lines.append((QgsGeometry.fromPolylineXY([QgsPointXY(x, y), QgsPointXY(x + 4000, y + 3000)]),
                      f"Flux {index}", 10 * (index + 1), 1.0, 0.0))
    for index in range(300):  # a dense core, and a few points apart
        x = 610000 + (index % 20) * 40 if index < 280 else 600000 + index * 50
        y = 6285000 + (index // 20) * 40 if index < 280 else 6280500
        points.append((QgsGeometry.fromPointXY(QgsPointXY(x, y)), "abc"[index % 3], index % 7 + 1, 1.0, 0.0))
    made = {}
    for name, geometry, rows in (("communes", "Polygon", polygons), ("ecoles", "Point", points),
                                 ("flux", "LineString", lines)):
        path = os.path.join(work, f"{name}.gpkg")
        write_layer(path, geometry, rows)
        made[name] = QgsVectorLayer(path, name, "ogr")
    return made


def drawn(layer):
    """``(errors, pixels painted)`` of the layer drawn alone, labels included."""
    settings = QgsMapSettings()
    settings.setLayers([layer])
    settings.setDestinationCrs(layer.crs())
    settings.setExtent(layer.extent().buffered(2000))
    settings.setOutputSize(QSize(240, 200))
    settings.setBackgroundColor(QColor(0, 0, 0, 0))
    job = QgsMapRendererParallelJob(settings)
    job.start()
    job.waitForFinished()
    image = job.renderedImage()
    painted = sum(1 for x in range(0, image.width(), 3) for y in range(0, image.height(), 3)
                  if (image.pixel(x, y) >> 24) & 0xFF)
    return [error.message for error in job.errors()], painted


def label_look(layer):
    """``(box, callout, wrap, halo)`` of the labels of ``layer``: each object held, a format read from a temporary
    one crashed QGIS."""
    settings = layer.labeling().settings()
    text = settings.format()
    box, halo, callout = text.background(), text.buffer(), settings.callout()
    return box.enabled(), callout is not None and callout.enabled(), settings.autoWrapLength, halo.enabled()


def check_drawn(label, layer):
    errors, painted = drawn(layer)
    check(f"{label}: drawn to an image", not errors and painted > 0, (errors, painted))


def main():
    from filter_mate.adapters.agent import turn_effects
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.adapters.public_api import layer_style as style
    from filter_mate.core.agent.messages import ToolCallPart
    work = tempfile.mkdtemp()
    layers = fixtures(work)
    project = QgsProject.instance()
    for layer in layers.values():
        project.addMapLayer(layer)
    communes, ecoles, flux = layers["communes"], layers["ecoles"], layers["flux"]
    project.setCrs(communes.crs())
    check("fixtures valid", all(layer.isValid() for layer in layers.values()) and ecoles.featureCount() == 300)
    first = {name: layer.renderer().type() for name, layer in layers.items()}

    recorder = EffectsRecorder()
    for number, name in enumerate(layers):
        recorder.before_call(ToolCallPart(f"s{number}", "set_layer_style", {"layer": name}))
        recorder.before_call(ToolCallPart(f"l{number}", "set_labels", {"layer": name}))

    def round_trip(label, layer, same):
        """The style of the layer as XML, put back over another one: what undo and redo do."""
        xml = turn_effects._style(layer)
        expected = same(layer.renderer())
        from qgis.core import QgsSingleSymbolRenderer, QgsSymbol
        layer.setRenderer(QgsSingleSymbolRenderer(QgsSymbol.defaultSymbol(layer.geometryType())))
        loaded = xml is not None and turn_effects._set_style(layer, xml)
        check(f"{label}: kept by its style XML", loaded and same(layer.renderer()) == expected,
              (expected, same(layer.renderer())))

    # -- heatmap
    heat = style.set_layer_style("ecoles", "heatmap", field="pop", width=8)
    renderer = ecoles.renderer()
    check("heatmap: weighed by a field, radius in mm, a ramp that starts transparent",
          renderer.type() == "heatmapRenderer" and renderer.weightExpression() == '"pop"' and renderer.radius() == 8
          and renderer.colorRamp().color(0.0).alpha() == 0 and renderer.colorRamp().color(1.0).alpha() == 255
          and heat["ramp"] == "YlOrRd" and heat["field"] == "pop", heat)
    check_drawn("heatmap", ecoles)
    round_trip("heatmap", ecoles, lambda made: (made.type(), made.radius(), made.weightExpression()))
    check("heatmap: refused on polygons", "layer of points" in refused(
        lambda: style.set_layer_style("communes", "heatmap")))
    check("heatmap: refused on a text weight", "numbers" in refused(
        lambda: style.set_layer_style("ecoles", "heatmap", field="nom")))

    # -- clusters and displaced points keep the categories
    style.set_layer_style("ecoles", "categorized", field="nom")
    cluster = style.set_layer_style("ecoles", "point_cluster", width=5, color="#123456")
    renderer = ecoles.renderer()
    check("point_cluster: the categories kept inside, a distance in mm, the disc colored",
          renderer.type() == "pointCluster" and renderer.embeddedRenderer().type() == "categorizedSymbol"
          and renderer.tolerance() == 5 and renderer.clusterSymbol().symbolLayer(0).color().name() == "#123456"
          and "categorized" in cluster["note"], cluster)
    check_drawn("point_cluster", ecoles)
    round_trip("point_cluster", ecoles, lambda made: (made.type(), made.tolerance(), made.embeddedRenderer().type()))
    shown = style.set_layer_style("ecoles", "point_displacement")
    renderer = ecoles.renderer()
    check("point_displacement: after a cluster, the categories still inside, the usual distance",
          renderer.type() == "pointDisplacement" and renderer.embeddedRenderer().type() == "categorizedSymbol"
          and renderer.tolerance() == style.POINT_DISTANCE, shown)
    check_drawn("point_displacement", ecoles)
    round_trip("point_displacement", ecoles, lambda made: (made.type(), made.embeddedRenderer().type()))
    style.set_layer_style("ecoles", "heatmap")
    again = style.set_layer_style("ecoles", "point_cluster")
    check("point_cluster: after a heatmap, one symbol", ecoles.renderer().embeddedRenderer().type() == "singleSymbol"
          and "single" in again["note"], again)
    check("point_cluster: refused on lines", "layer of points" in refused(
        lambda: style.set_layer_style("flux", "point_cluster")))

    # -- proportional symbols
    sized = style.set_layer_style("ecoles", "proportional", field="pop", width=12)
    renderer = ecoles.renderer()
    size = renderer.symbol().dataDefinedSize()
    check("proportional points: a size from the field, 12 mm at the largest, big ones first, a legend of sizes",
          renderer.type() == "singleSymbol" and size.isActive() and size.transformer() is not None
          and abs(size.transformer().maxSize() - 12) < 1e-9 and size.transformer().minValue() == 0
          and renderer.orderByEnabled() and not renderer.orderBy().list()[0].ascending()
          and renderer.dataDefinedSizeLegend() is not None and sized["field"] == "pop", sized)
    check_drawn("proportional points", ecoles)
    round_trip("proportional points", ecoles, lambda made: (
        made.type(), made.symbol().dataDefinedSize().isActive(), made.orderByEnabled()))
    circles = style.set_layer_style("communes", "proportional", field="pop", color="steelblue")
    renderer = communes.renderer()
    centre = renderer.symbol().symbolLayer(1)
    check("proportional polygons: a circle inside each, sized by the field, drawn above every outline",
          centre.layerType() == "CentroidFill" and centre.subSymbol().dataDefinedSize().isActive()
          and centre.pointOnSurface() and renderer.usingSymbolLevels() and centre.renderingPass() == 1, circles)
    check_drawn("proportional polygons", communes)
    round_trip("proportional polygons", communes, lambda made: (
        made.symbol().symbolLayer(1).layerType(), made.usingSymbolLevels(),
        made.symbol().symbolLayer(1).subSymbol().dataDefinedSize().isActive()))
    widths = style.set_layer_style("flux", "proportional", field="pop")
    renderer = flux.renderer()
    check("proportional lines: a width from the field", renderer.symbol().dataDefinedWidth().isActive()
          and abs(renderer.symbol().dataDefinedWidth().transformer().maxSize() - style.WIDEST_LINE) < 1e-9, widths)
    check_drawn("proportional lines", flux)
    check("proportional: refused on values below zero", "below zero" in refused(
        lambda: style.set_layer_style("communes", "proportional", field="change")))
    check("proportional: refused on a text field", "numbers" in refused(
        lambda: style.set_layer_style("communes", "proportional", field="nom")))

    # -- dot density
    dotted = style.set_layer_style("communes", "dot_density", field="pop", color="black")
    renderer = communes.renderer()
    dots = renderer.symbol().symbolLayer(1)
    from qgis.core import QgsSymbolLayer
    point_count = style._enum(QgsSymbolLayer, "Property", "PointCount", "PropertyPointCount")
    count = dots.dataDefinedProperties().property(point_count)
    check("dot_density: one dot per 20 people (1,200 at most: a round share of it), a count from the field, "
          "dots that stay put", dotted["per_dot"] == 20 and dots.layerType() == "RandomMarkerFill"
          and count.isActive() and '"pop"' in count.expressionString() and dots.seed() == 1,
          (dotted, count.expressionString()))
    check_drawn("dot_density", communes)
    round_trip("dot_density", communes, lambda made: (
        made.symbol().symbolLayer(1).layerType(), made.symbol().symbolLayer(1).seed(),
        made.symbol().symbolLayer(1).dataDefinedProperties().property(
            point_count).expressionString()))
    given = style.set_layer_style("communes", "dot_density", field="pop", per_dot=50, share_values=False)
    check("dot_density: per_dot given is told, even to a user who shares no values", given["per_dot"] == 50, given)
    hidden = style.set_layer_style("communes", "dot_density", field="pop", share_values=False)
    check("dot_density: the share read from the field is not told without the values", "per_dot" not in hidden
          and "not told" in hidden["note"], hidden)
    check("dot_density: too many dots refused", "larger per_dot" in refused(
        lambda: style.set_layer_style("communes", "dot_density", field="pop", per_dot=0.1)))
    check("dot_density: refused on points", "layer of polygons" in refused(
        lambda: style.set_layer_style("ecoles", "dot_density", field="pop")))

    # -- 2.5D
    blocks = style.set_layer_style("communes", "2.5d", field="hauteur", z_factor=20, color="#cccccc")
    renderer = communes.renderer()
    xml = turn_effects._style(communes)
    check("2.5d: blocks raised by the field, the height and the angle in the style, no layer variable",
          renderer.type() == "25dRenderer" and "@qgis_25d" not in xml and "hauteur" in xml
          and blocks["field"] == "hauteur" and renderer.roofColor().name() == "#cccccc",
          (blocks, renderer.type(), [line for line in xml.splitlines() if "25d" in line][:6]))
    check_drawn("2.5d", communes)
    round_trip("2.5d", communes, lambda made: (made.type(), "@qgis_25d" in turn_effects._style(communes)))
    check("2.5d: refused on points", "layer of polygons" in refused(lambda: style.set_layer_style("ecoles", "2.5d")))

    # -- diverging classes
    diverging = style.set_layer_style("communes", "graduated", field="change", method="equal_interval", classes=6,
                                      center=0, ramp="RdBu")
    ranges = communes.renderer().ranges()
    ramp = communes.renderer().sourceColorRamp()
    limits = [item.upperValue() for item in ranges]
    below = [item for item in ranges if item.upperValue() <= 0]
    above = [item for item in ranges if item.lowerValue() >= 0]
    steps = max(len(below), len(above))
    check("graduated center: a limit at the center, the classes next to it the colors one step from the middle",
          any(abs(limit) < 1e-9 for limit in limits) and below and above
          and below[-1].symbol().color().name() == ramp.color(0.5 - 0.5 / steps).name()
          and above[0].symbol().color().name() == ramp.color(0.5 + 0.5 / steps).name(), (diverging, limits))
    check_drawn("graduated center", communes)
    quantiles = style.set_layer_style("communes", "graduated", field="change", method="quantile", center=0)
    check("graduated center: quantiles too, colored from the center", quantiles["classes"] >= 2, quantiles)
    plain = style.set_layer_style("communes", "graduated", field="pop", classes=7, method="jenks")
    check("graduated: jenks in 7 classes as before", plain["classes"] == 7, plain)

    # -- labels
    from qgis.PyQt.QtGui import QFontDatabase
    try:
        families = list(QFontDatabase.families())
    except TypeError:
        families = list(QFontDatabase().families())
    family = families[0] if families else ""
    labels = style.set_labels("communes", "nom", background="white", background_opacity=0.8, callouts=True,
                              font=family.upper(), bold=True, italic=True, wrap=12, priority=9, obstacle=False,
                              visible_from_scale=100000, visible_to_scale=1000, placement="free")
    pal = communes.labeling().settings()
    text = pal.format()
    box = text.background()
    check("labels: a box behind the text, callouts, a font in bold italic, wrapped, first placed, no obstacle",
          box.enabled() and box.fillColor().name() == "#ffffff" and abs(box.opacity() - 0.8) < 1e-9
          and pal.callout() is not None and pal.callout().enabled() and text.font().bold() and text.font().italic()
          and (not family or text.font().family() == family) and pal.autoWrapLength == 12 and pal.priority == 9
          and not pal.obstacleSettings().isObstacle() and labels["placement"] == "free", labels)
    check("labels: shown from 1:100 000 down to 1:1 000", pal.scaleVisibility and pal.minimumScale == 100000
          and pal.maximumScale == 1000)
    check_drawn("labels with a box", communes)
    round_trip("labels with a box", communes, lambda made: label_look(communes))
    for layer, placement, member in (("communes", "centroid", "OverPoint"),
                                     ("communes", "perimeter", "PerimeterCurved"),
                                     ("communes", "horizontal", "Horizontal"), ("communes", "around", "AroundPoint"),
                                     ("flux", "parallel", "Line"), ("flux", "curved", "Curved"),
                                     ("flux", "horizontal", "Horizontal"), ("ecoles", "around", "AroundPoint")):
        from qgis.core import QgsPalLayerSettings
        style.set_labels(layer, "nom", placement=placement)
        check(f"labels: {placement} on {layer}", layers[layer].labeling().settings().placement
              == getattr(QgsPalLayerSettings.Placement, member))
    check_drawn("labels curved on lines", flux)
    for call, label in ((lambda: style.set_labels("communes", "nom", placement="curved"), "curved on polygons"),
                        (lambda: style.set_labels("flux", "nom", placement="centroid"), "centroid on lines"),
                        (lambda: style.set_labels("ecoles", "nom", placement="free"), "free on points"),
                        (lambda: style.set_labels("communes", "nom", font="No Such Font 123"), "an unknown font"),
                        (lambda: style.set_labels("communes", "nom", wrap=2), "a wrap of 2"),
                        (lambda: style.set_labels("communes", "nom", priority=11), "a priority of 11"),
                        (lambda: style.set_labels("communes", "nom", background="nope"), "a background no color"),
                        (lambda: style.set_labels("communes", "nom", visible_from_scale=1000, visible_to_scale=5000),
                         "a closest scale above the farthest")):
        check(f"labels refuse {label}", bool(refused(call)), label)
    plain = style.set_labels("communes", "nom")
    pal = communes.labeling().settings()
    check("labels: the defaults as before (a halo, no box, no callout, every scale)", plain == {
        "layer_name": "communes", "labels": True, "field": "nom", "expression": "", "visible_from_scale": None,
        "placement": "auto"} and label_look(communes)[3] and not label_look(communes)[0]
        and not pal.scaleVisibility and (pal.callout() is None or not pal.callout().enabled()), plain)

    # -- the turn: undo puts every layer back, redo the last style of each
    style.set_layer_style("communes", "2.5d", field="hauteur")
    style.set_layer_style("ecoles", "point_cluster")
    style.set_layer_style("flux", "proportional", field="pop")
    style.set_labels("communes", "nom", background="yellow", callouts=True)
    effects = recorder.finish()
    check("turn: one style kept per layer", sorted(effect[0] for effect in effects) == ["style"] * 3, effects)
    done, left = apply_effects(effects, undo=True)
    check("undo: every layer drawn as before the turn, no labels", not left and {
        name: layer.renderer().type() for name, layer in layers.items()} == first
        and not communes.labelsEnabled(), (done, left))
    done, left = apply_effects(effects, undo=False)
    check("redo: the blocks, the clusters, the widths and the box come back", not left
          and communes.renderer().type() == "25dRenderer" and ecoles.renderer().type() == "pointCluster"
          and flux.renderer().symbol().dataDefinedWidth().isActive() and communes.labelsEnabled()
          and label_look(communes)[0], (done, left))
    for name, layer in layers.items():
        check_drawn(f"redo {name}", layer)
    apply_effects(effects, undo=True)


if __name__ == "__main__":
    app = QgsApplication([b"check_agent_symbology"], False)
    app.initQgis()
    package_root = tempfile.mkdtemp()
    os.symlink(os.environ.get("FM_REPO", "/src"), os.path.join(package_root, "filter_mate"))
    sys.path.insert(0, package_root)
    sys.dont_write_bytecode = True
    print(f"QGIS {__import__('qgis.core').core.Qgis.QGIS_VERSION}, Python {sys.version.split()[0]}")
    main()
    print(f"{sum(RESULTS)}/{len(RESULTS)} passed")
    sys.exit(0 if all(RESULTS) else 1)
