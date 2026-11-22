"""Cartograms of the agent in a real (headless) QGIS: the four kinds from a GeoPackage of polygons as filtered, a
layer in degrees compared in an equal-area projection made for it, the refusals, and the undo of the turn.

    docker run --rm -v "$PWD":/src -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr \\
        python3 /src/tests/qgis_headless/check_agent_cartograms.py

Prints one PASS / FAIL line per check; exits with 1 when one failed.
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import (  # noqa: E402
    QgsApplication, QgsFeature, QgsField, QgsFields, QgsGeometry, QgsProject, QgsRectangle, QgsVectorFileWriter,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant  # noqa: E402

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


def make_grid(path, crs, step, origin):
    """A 4 x 4 grid of squares sharing their sides; the population grows towards one corner."""
    fields = QgsFields()
    fields.append(QgsField("nom", QVariant.String))
    fields.append(QgsField("population", QVariant.Double))
    fields.append(QgsField("dept", QVariant.String))
    memory = QgsVectorLayer(f"Polygon?crs={crs}", "memory", "memory")
    memory.dataProvider().addAttributes(fields.toList())
    memory.updateFields()
    features = []
    for row in range(4):
        for column in range(4):
            x, y = origin[0] + column * step, origin[1] + row * step
            feature = QgsFeature(memory.fields())
            feature.setGeometry(QgsGeometry.fromRect(QgsRectangle(x, y, x + step, y + step)))
            feature.setAttributes([f"C{row}{column}", float(100 * (1 + row * column) ** 2), "31" if row < 3 else "32"])
            features.append(feature)
    memory.dataProvider().addFeatures(features)
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    QgsVectorFileWriter.writeAsVectorFormatV2(memory, path, QgsProject.instance().transformContext(), options)


def main():
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.adapters.public_api import cartograms
    from filter_mate.core.agent.messages import ToolCallPart
    project = QgsProject.instance()
    work = tempfile.mkdtemp()
    make_grid(os.path.join(work, "communes.gpkg"), "EPSG:2154", 10000.0, (500000.0, 6200000.0))
    make_grid(os.path.join(work, "pays.gpkg"), "EPSG:4326", 2.0, (10.0, 40.0))
    communes = QgsVectorLayer(os.path.join(work, "communes.gpkg"), "communes", "ogr")
    pays = QgsVectorLayer(os.path.join(work, "pays.gpkg"), "pays", "ogr")
    project.addMapLayers([communes, pays])
    check("fixtures valid", communes.isValid() and pays.isValid() and communes.featureCount() == 16)

    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("c1", "make_cartogram", {"layer": "communes", "field": "population"}))
    made = cartograms.make_cartogram("communes", "population", iterations=12)
    result = project.mapLayer(made["layer_id"])
    check("contiguous: a new layer of every feature, at the top of the tree", result is not None and
          made["features"] == 16 and project.layerTreeRoot().children()[0].layerId() == made["layer_id"], made)
    # Values from 1 to 100 on squares of 4 vertices: the error falls from 9.2 to below 2 in 12 iterations.
    check("contiguous: the areas come closer to the values", made["error_after"] < made["error_before"] / 3, made)
    check("contiguous: the fields of the layer and the value kept", result is not None and
          result.fields().lookupField("nom") >= 0 and result.fields().lookupField("cartogram_value") >= 0)
    areas = {feature["nom"]: feature.geometry().area() for feature in result.getFeatures()}
    check("contiguous: the most populated cell is the largest", max(areas, key=areas.get) == "C33", areas)
    union = QgsGeometry.unaryUnion([feature.geometry() for feature in result.getFeatures()])
    total = sum(areas.values())
    check("contiguous: borders kept (no gap, no overlap: the union has the area of the parts)",
          abs(union.area() - total) / total < 0.01, (union.area(), total))
    effects = recorder.finish()
    done, left = apply_effects(effects, undo=True)
    check("undo removes the cartogram", not left and project.mapLayer(made["layer_id"]) is None, (done, left))

    communes.setSubsetString("\"dept\" = '31'")
    olson = cartograms.make_cartogram("communes", "population", kind="noncontiguous")
    check("noncontiguous: from the layer as filtered, areas exact", olson["features"] == 12 and
          olson["error_after"] < 1.01, olson)
    communes.setSubsetString("")
    for kind in ("dorling", "demers"):
        symbols = cartograms.make_cartogram("communes", "population", kind=kind, name=f"Cercles {kind}")
        layer = project.mapLayer(symbols["layer_id"])
        check(f"{kind}: one symbol per feature, named as asked", layer is not None and layer.featureCount() == 16 and
              layer.name() == f"Cercles {kind}", symbols)
    degrees = cartograms.make_cartogram("pays", "population")
    check("degrees: compared in an equal-area projection made for the layer", "projection" in degrees and
          "+proj=aea" in project.mapLayer(degrees["layer_id"]).crs().toProj() or
          "+proj=laea" in project.mapLayer(degrees["layer_id"]).crs().toProj(), degrees)
    # --- 2026-11-22 review: points, the world, a fid of text, a cartogram of a cartogram
    points = QgsVectorLayer("Point?crs=EPSG:2154&field=fid:string&field=n:double", "puits", "memory")
    made_points = []
    for index in range(20):
        feature = QgsFeature(points.fields())
        feature.setGeometry(QgsGeometry.fromWkt(f"POINT({600000 + (index % 5) * 1000} {6300000 + index // 5 * 1000})"))
        feature.setAttributes([f"p{index}", float(index + 1)])
        made_points.append(feature)
    points.dataProvider().addFeatures(made_points)
    points.updateExtents()
    project.addMapLayer(points)
    circles = project.mapLayer(cartograms.make_cartogram("puits", "n", kind="dorling")["layer_id"])
    largest = max(feature.geometry().area() for feature in circles.getFeatures())
    check("dorling of points: circles of a size seen at the scale of the points (a fid of text dropped)",
          largest > 10000.0, largest)
    again = cartograms.make_cartogram(circles.id(), "n", kind="noncontiguous")
    check("a cartogram of a cartogram: a value field of its own", again["value_field"] == "cartogram_value_2", again)
    world = QgsVectorLayer("Polygon?crs=EPSG:4326&field=n:double", "monde", "memory")
    cells = []
    for column in range(-180, 180, 60):
        for row in range(-60, 60, 30):
            feature = QgsFeature(world.fields())
            feature.setGeometry(QgsGeometry.fromRect(QgsRectangle(column, row, column + 60, row + 30)))
            feature.setAttributes([float(abs(column) + abs(row) + 1)])
            cells.append(feature)
    world.dataProvider().addFeatures(cells)
    world.updateExtents()
    project.addMapLayer(world)
    planet = cartograms.make_cartogram("monde", "n", iterations=3)
    check("the world: in Equal Earth, every number finite", "Equal Earth" in planet.get("projection", "") and
          planet["error_after"] == planet["error_after"], planet)
    for call, label in ((lambda: cartograms.make_cartogram("nope", "population"), "an unknown layer"),
                        (lambda: cartograms.make_cartogram("communes", "nom"), "a text field"),
                        (lambda: cartograms.make_cartogram("communes", "population", kind="bubble"), "a kind"),
                        (lambda: cartograms.make_cartogram("communes", "population", iterations=99), "iterations")):
        check(f"refuses {label}", refused(call))


if __name__ == "__main__":
    app = QgsApplication([b"check_agent_cartograms"], False)
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
