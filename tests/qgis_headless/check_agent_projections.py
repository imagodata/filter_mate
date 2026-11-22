"""Projections of the agent in a real (headless) QGIS: suggest_crs from the extent of layers, every suggestion a CRS
QGIS knows, a projection made for the data set with set_project_crs and undone with the turn.

    docker run --rm -v "$PWD":/src -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr \\
        python3 /src/tests/qgis_headless/check_agent_projections.py

Prints one PASS / FAIL line per check; exits with 1 when one failed.
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import (  # noqa: E402
    QgsApplication, QgsCoordinateReferenceSystem, QgsFeature, QgsGeometry, QgsProject, QgsVectorLayer,
)

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


def memory_layer(name, crs, geometries):
    layer = QgsVectorLayer(f"Polygon?crs={crs}" if "POLYGON" in geometries[0] else f"Point?crs={crs}", name, "memory")
    features = []
    for wkt in geometries:
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromWkt(wkt))
        features.append(feature)
    layer.dataProvider().addFeatures(features)
    layer.updateExtents()
    QgsProject.instance().addMapLayer(layer)
    return layer


def main():
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.adapters.public_api import project_control
    from filter_mate.core.agent.messages import ToolCallPart
    project = QgsProject.instance()
    # Around Toulouse, in Lambert-93.
    memory_layer("communes", "EPSG:2154", [
        "POLYGON((560000 6260000, 590000 6260000, 590000 6290000, 560000 6290000, 560000 6260000))"])
    world = memory_layer("pays", "EPSG:4326", ["POLYGON((-170 -55, 175 -55, 175 75, -170 75, -170 -55))"])
    lone = memory_layer("puits", "EPSG:4326", ["POINT(45.0 47.0)"])
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
    world_node = project.layerTreeRoot().findLayer(world.id())
    world_node.setItemVisibilityChecked(False)
    lone_node = project.layerTreeRoot().findLayer(lone.id())
    lone_node.setItemVisibilityChecked(False)

    local = project_control.suggest_crs()
    crs = [row["crs"] for row in local["suggestions"]]
    west, south = local["bounds_wgs84"][:2]
    check("local: from the layers shown, in degrees", local["from"] == "layers shown" and 0.5 < west < 1.5 and
          43.0 < south < 44.0, local["bounds_wgs84"])
    check("local: Lambert-93, the CC zone, the UTM zone first",
          crs[:3] == ["EPSG:2154", "EPSG:3943", "EPSG:25831"], crs)
    check("local: every suggestion is a CRS QGIS knows, with its units",
          all(QgsCoordinateReferenceSystem(row["crs"]).isValid() and row["units"] for row in local["suggestions"]))
    areas = project_control.suggest_crs(["communes"], purpose="areas")
    check("areas: an equal-area projection first", areas["suggestions"][0]["keeps"] == "equal-area",
          areas["suggestions"][0])
    planet = project_control.suggest_crs(["pays"])
    check("world: world projections, Web Mercator last", planet["scale"] == "world" and
          planet["suggestions"][0]["crs"] == "ESRI:54030" and planet["suggestions"][-1]["crs"] == "EPSG:3857",
          [row["crs"] for row in planet["suggestions"]])
    point = project_control.suggest_crs(["puits"], purpose="distances")
    made = point["suggestions"][0]["crs"]
    check("one point: a projection made for it, centred on it", made.startswith("PROJ:+proj=aeqd") and
          "+lon_0=45.0" in made and "+lat_0=47.0" in made, point["suggestions"][0])
    check("refuses an unknown layer and purpose", refused(lambda: project_control.suggest_crs(["nope"])) and
          refused(lambda: project_control.suggest_crs(purpose="beauty")))

    memory_layer("fidji", "EPSG:4326", [
        "POLYGON((177 -19, 180 -19, 180 -16, 177 -16, 177 -19))",
        "POLYGON((-180 -19, -178 -19, -178 -16, -180 -16, -180 -19))"])
    islands = project_control.suggest_crs(["fidji"], purpose="areas")
    west, _, east, _ = islands["bounds_wgs84"]
    check("antimeridian: Fiji is a region across it, not the world", west > east and west >= 176.9 and
          east <= -177.9 and islands["scale"] != "world", islands["bounds_wgs84"])
    check("antimeridian: a projection made for it is centred near 180", any(
        "+lon_0=179" in row["crs"] or "+lon_0=-179" in row["crs"] or "+lon_0=180" in row["crs"] or
        "+lon_0=-180" in row["crs"] for row in islands["suggestions"]), islands["suggestions"])

    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("p1", "set_project_crs", {"crs": made}))
    answer = project_control.set_project_crs(made)
    check("a projection made for the data is set as it is", project.crs().isValid() and
          "aeqd" in project.crs().toProj() and not answer["geographic"], answer)
    effects = recorder.finish()
    done, left = apply_effects(effects, undo=True)
    check("undo brings the CRS of before", not left and project.crs().authid() == "EPSG:4326", (done, left))
    apply_effects(effects, undo=False)
    check("redo sets the projection made for the data again", "aeqd" in project.crs().toProj())


if __name__ == "__main__":
    app = QgsApplication([b"check_agent_projections"], False)
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
