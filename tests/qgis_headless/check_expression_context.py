# -*- coding: utf-8 -*-
"""Compare synchronous expression reads with ExpressionEvaluationTask in a real worker.

No service or database is required. Run, for example:
    docker run --rm --network none -v "$PWD:/src:ro" qgis/qgis:ltr \
        python3 /src/tests/qgis_headless/check_expression_context.py

FM_REPO can point to another checkout to reproduce the failures before a change.
"""
import concurrent.futures
import os
from pathlib import Path
import sys
import tempfile
import time
import types

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FILTERMATE_LOG_DIR", tempfile.mkdtemp(prefix="fm_expression_logs_"))

from qgis.core import (  # noqa: E402
    Qgis, QgsApplication, QgsCoordinateReferenceSystem, QgsExpressionContextUtils,
    QgsFeature, QgsFeatureRequest, QgsField, QgsGeometry, QgsProject, QgsUnitTypes, QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant  # noqa: E402

REPO = Path(os.environ.get("FM_REPO", Path(__file__).resolve().parents[2]))
# Load the production modules without starting the plugin UI or changing its configuration.
for suffix in ("", "core", "core.tasks", "adapters", "adapters.qgis", "adapters.backends", "infrastructure"):
    name = "filter_mate" + ("." + suffix if suffix else "")
    package = types.ModuleType(name)
    package.__path__ = [str(REPO.joinpath(*suffix.split("."))) if suffix else str(REPO)]
    sys.modules[name] = package

from filter_mate.adapters.backends.source_refusal import with_layer_context  # noqa: E402
from filter_mate.core.tasks.expression_evaluation_task import ExpressionEvaluationTask  # noqa: E402

RESULTS = []


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {detail}" if not condition else ""), flush=True)


def layer_of(kind, wkts):
    layer = QgsVectorLayer(f"{kind}?crs=EPSG:4326&field=num:integer", kind, "memory")
    features = []
    for num, wkt in enumerate(wkts, 1):
        feature = QgsFeature(layer.fields())
        feature.setAttributes([num])
        feature.setGeometry(QgsGeometry.fromWkt(wkt))
        features.append(feature)
    layer.dataProvider().addFeatures(features)
    QgsProject.instance().addMapLayer(layer)
    return layer


def evaluate(label, layer, expression, expected, **options):
    request = with_layer_context(QgsFeatureRequest().setFilterExpression(expression), layer)
    if options.get("limit", 0):
        request.setLimit(options["limit"])
    if options.get("request_fields"):
        request.setSubsetOfAttributes(options["request_fields"], layer.fields())
    if not options.get("include_geometry", True):
        request.setFlags(QgsFeatureRequest.Flag.NoGeometry)
    synchronous = list(layer.getFeatures(request))
    task = ExpressionEvaluationTask(label, layer, expression, **options)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(task.run)
        deadline = time.monotonic() + 30
        while not future.done():
            QgsApplication.processEvents()
            if time.monotonic() >= deadline:
                check(label + ": worker finished within 30 seconds", False)
                os._exit(1)  # a deadlocked worker must not hang the bench's teardown
            time.sleep(0.005)
        success = future.result()
    actual = sorted(feature["num"] for feature in task.result_features)
    sync_nums = sorted(feature["num"] for feature in synchronous)
    check(label, success and actual == sync_nums == expected,
          (success, str(task.exception), "sync", sync_nums, "worker", actual, "expected", expected))
    check(label + ": returned fields and geometry match",
          [(f.attributes(), f.geometry().asWkt()) for f in task.result_features]
          == [(f.attributes(), f.geometry().asWkt()) for f in synchronous])
    return task


def main():
    project = QgsProject.instance()
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
    project.setEllipsoid("WGS84")
    polygons = layer_of("Polygon", [
        "POLYGON((0 45,0.01 45,0.01 45.01,0 45.01,0 45))",
        "POLYGON((0 45,0.02 45,0.02 45.02,0 45.02,0 45))",
    ])
    lines = layer_of("LineString", ["LINESTRING(0 45,0 45.01)", "LINESTRING(0 45,0 45.02)"])
    QgsExpressionContextUtils.setGlobalVariable("fm_context_cutoff", 99)
    QgsExpressionContextUtils.setProjectVariable(project, "fm_context_cutoff", 0)
    QgsExpressionContextUtils.setLayerVariable(polygons, "fm_context_cutoff", 1)
    QgsExpressionContextUtils.setProjectVariable(project, "fm_project_cutoff", 1)
    evaluate("layer variable overrides project and global", polygons, '"num" > @fm_context_cutoff', [2])
    evaluate("project variable", polygons, '"num" > @fm_project_cutoff', [2])
    evaluate("unknown variable is NULL", polygons, "@fm_unknown_variable IS NULL", [1, 2])
    evaluate("ellipsoidal area in square metres, geographic layer CRS", polygons, "$area > 1000000", [2])
    evaluate("ellipsoidal perimeter in metres", polygons, "$perimeter > 5000", [2])
    evaluate("ellipsoidal length in metres", lines, "$length > 1500", [2])
    project.setAreaUnits(QgsUnitTypes.AreaUnit.AreaHectares)
    project.setDistanceUnits(QgsUnitTypes.DistanceUnit.DistanceKilometers)
    evaluate("project area units in hectares", polygons, "$area > 100", [2])
    evaluate("project distance units in kilometres", lines, "$length > 1.5", [2])
    evaluate("CRS transform uses project transform context", lines,
             "y(end_point(transform($geometry, @layer_crs, 'EPSG:3857'))) > 5624000", [2])
    project.setEllipsoid("NONE")
    evaluate("area after disabling the ellipsoid", polygons, "$area > 200", [2])
    polygons.selectByIds([next(polygons.getFeatures()).id()])
    evaluate("selection-dependent expression", polygons, "is_selected()", [1])
    evaluate("aggregate in the live layer context", polygons, '"num" > mean("num")', [2])
    polygons.addExpressionField('"num" * 10', QgsField("computed", QVariant.Int))
    evaluate("virtual field used in expression", polygons, '"computed" > 10', [2])
    evaluate("virtual field returned by a provider-only expression", polygons, '"num" > 0', [1, 2])
    polygons.startEditing()
    polygons.changeAttributeValue(next(polygons.getFeatures()).id(), 0, 3)
    evaluate("unsaved attribute edits", polygons, '"num" > 1', [2, 3])
    polygons.rollBack()
    evaluate("limit and omitted geometry", lines, '"num" > 0', [1], limit=1,
             request_fields=["num"], include_geometry=False)
    print(f"{sum(RESULTS)}/{len(RESULTS)} passed (QGIS {Qgis.QGIS_VERSION})", flush=True)
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    app = QgsApplication([], False)
    app.initQgis()
    print(f"QGIS {Qgis.QGIS_VERSION}, plugin {REPO}", flush=True)
    os._exit(main())
