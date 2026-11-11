# -*- coding: utf-8 -*-
"""The edits of the agent on a WFS-T layer served by QGIS Server, headless.

Two steps, sharing a folder (``FM_WFST_DATA``, /data by default) and a Docker network:

    python3 check_agent_edits_wfst.py setup   # a GeoPackage and a project that publishes it with WFS-T
    (QGIS Server: docker run -d --name fm_wfst --network NET -v DATA:/data qgis/qgis-server:ltr)
    python3 check_agent_edits_wfst.py check   # FM_WFST_URL=http://fm_wfst/ows/?MAP=/data/wfst.qgs

Checks that the agent edits the edit buffer of the WFS layer only (the GeoPackage behind the server is read
directly: nothing changes there until the layer is saved), that saving sends the transaction and the server writes
it, and that undoing the turn steps back over the commands while they are not saved.
Prints one PASS / FAIL line per check; exits with 1 when one failed.
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import (QgsApplication, QgsCoordinateReferenceSystem, QgsFeature, QgsGeometry, QgsPointXY,  # noqa: E402
                       QgsProject, QgsVectorFileWriter, QgsVectorLayer)

DATA = os.environ.get("FM_WFST_DATA", "/data")
URL = os.environ.get("FM_WFST_URL", "http://fm_wfst/ows/?MAP=/data/wfst.qgs")
GPKG = os.path.join(DATA, "wfst.gpkg")
RESULTS = []


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {detail}" if not condition else ""), flush=True)


def setup():
    memory = QgsVectorLayer("Point?crs=EPSG:2154&field=nom:string(50)&field=pop:integer", "communes", "memory")
    features = []
    for index in range(1, 21):
        feature = QgsFeature(memory.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(650000 + index * 10, 6860000)))
        feature.setAttributes([f"Commune {index}", index * 100])
        features.append(feature)
    memory.dataProvider().addFeatures(features)
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = "communes"
    QgsVectorFileWriter.writeAsVectorFormatV3(memory, GPKG, QgsProject.instance().transformContext(), options)
    project = QgsProject.instance()
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:2154"))
    layer = QgsVectorLayer(f"{GPKG}|layername=communes", "communes", "ogr")
    project.addMapLayer(layer)
    project.writeEntry("WFSLayers", "/", [layer.id()])
    for operation in ("Update", "Insert", "Delete"):
        project.writeEntry("WFSTLayers", operation, [layer.id()])
    project.writeEntry("WFSLayersPrecision", "/" + layer.id(), 8)
    project.writeEntry("WMSServiceCapabilities", "/", True)
    project.writeEntry("WMSServiceTitle", "/", "FilterMate WFS-T check")
    project.writeEntry("WMSCrsList", "/", ["EPSG:2154", "EPSG:4326"])
    print("project written", project.write(os.path.join(DATA, "wfst.qgs")), flush=True)
    for name in os.listdir(DATA):
        os.chmod(os.path.join(DATA, name), 0o666)
    os.chmod(DATA, 0o777)


def on_server(where=""):
    """Rows of the GeoPackage behind the server, read directly (not through WFS)."""
    from osgeo import ogr
    source = ogr.Open(GPKG)
    table = source.GetLayer("communes")
    if where:
        table.SetAttributeFilter(where)
    return [(feature.GetField("nom"), feature.GetField("pop")) for feature in table]


def run_checks():
    from filter_mate.adapters.public_api import feature_edits as edits
    from filter_mate.adapters.public_api.introspection import describe_layer
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.core.agent.messages import ToolCallPart
    from qgis.core import QgsVectorDataProvider

    uri = f"url='{URL}' typename='communes' version='1.1.0' srsname='EPSG:2154' restrictToRequestBBOX='0'"
    layer = QgsVectorLayer(uri, "communes", "WFS")
    check("the WFS layer opens", layer.isValid() and layer.featureCount() == 20, layer.featureCount())
    flags = getattr(QgsVectorDataProvider, "Capability", QgsVectorDataProvider)
    capabilities = layer.dataProvider().capabilities()
    check("the server offers transactions", bool(capabilities & flags.ChangeAttributeValues) and
          bool(capabilities & flags.AddFeatures) and bool(capabilities & flags.DeleteFeatures), int(capabilities))
    QgsProject.instance().addMapLayer(layer)

    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("w1", "update_features", {"layer": "communes"}))
    changed = edits.update_features("communes", values={"nom": "Ville"}, formulas={"pop": '"pop" * 2'},
                                    expression='"pop" <= 300')
    check("values and a formula in the buffer", changed["changed"] == 3 and layer.isEditable() and layer.isModified(),
          changed)
    check("refuses a text in an integer", refused(edits.update_features, "communes", values={"pop": "abc"},
                                                  expression="true"))
    deleted = edits.delete_features("communes", expression='"pop" = 2000')
    check("delete in the buffer", deleted["deleted"] == 1, deleted)
    added = edits.add_features("communes", [{"wkt": "POINT(1.44 43.6)", "attributes": {"nom": "Puits", "pop": "7"}}],
                               crs="EPSG:4326")
    check("add from EPSG:4326", added["added"] == 1, added)
    check("describe_layer: edited, not saved", describe_layer("communes")["unsaved"])
    check("nothing reaches the server before saving", len(on_server()) == 20 and not on_server("nom = 'Ville'"))

    effects = recorder.finish()
    done, left = apply_effects(effects, undo=True)
    check("undo steps back over the commands", done == ["communes"] and not left and not layer.isModified(), (done, left))
    apply_effects(effects, undo=False)
    check("redo applies them again", layer.isModified())

    saved = layer.commitChanges()
    check("the user saves: the transaction goes through", saved, layer.commitErrors())
    rows = on_server()
    check("the server wrote every change", len(rows) == 20 and sorted(pop for name, pop in rows if name == "Ville") ==
          [200, 400, 600] and ("Puits", 7) in rows and not on_server("pop = 2000"), rows)


def refused(function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except ValueError as exc:
        return str(exc) or "refused"
    return ""


if __name__ == "__main__":
    app = QgsApplication([], False)
    app.initQgis()
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode == "setup":
        setup()
    else:
        package_root = tempfile.mkdtemp()
        os.symlink(os.environ.get("FM_REPO", "/src"), os.path.join(package_root, "filter_mate"))
        sys.path.insert(0, package_root)
        sys.dont_write_bytecode = True
        print(f"QGIS {__import__('qgis.core').core.Qgis.QGIS_VERSION}", flush=True)
        run_checks()
        failed = RESULTS.count(False)
        print(f"{len(RESULTS) - failed}/{len(RESULTS)} passed", flush=True)
    sys.stdout.flush()
    os._exit(1 if RESULTS.count(False) else 0)
