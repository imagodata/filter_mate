# -*- coding: utf-8 -*-
"""A cross filter that keeps tens of thousands of features of a GeoPackage, in a real (headless) QGIS:

    docker run --rm -v "$PWD":/repo:ro -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr bash -c \\
        "cp -r /repo /src && python3 /src/tests/qgis_headless/check_cross_filter_key_lists.py"

(copied: the plugin writes its log in its own folder, a read-only mount makes each line a trace)

2026-11-23: the cross filter (agent, Processing, Python API) wrote the kept keys as one literal IN list. With 54,473
OpenStreetMap buildings kept, setSubsetString took 15 s in QGIS 3.44 and 4.3 (1 ms in 3.22), then every read of the
layer 5 s. The dock already wrote a long list of a GeoPackage as one JSON literal (json_each); so does the cross
filter now. Prints PASS / FAIL lines and the times; FM_REPO points at another checkout to compare.
"""
import os
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import (  # noqa: E402
    Qgis, QgsApplication, QgsFeature, QgsGeometry, QgsProject, QgsRectangle, QgsVectorFileWriter, QgsVectorLayer,
)

ROWS = int(os.environ.get("FM_ROWS", "120000"))
RESULTS = []


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" ({detail})" if detail else ""), flush=True)


def written(memory, path, name):
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = name
    QgsVectorFileWriter.writeAsVectorFormatV3(memory, path, QgsProject.instance().transformContext(), options)
    layer = QgsVectorLayer(f"{path}|layername={name}", name, "ogr")
    QgsProject.instance().addMapLayer(layer)
    return layer


def squares(count, size, step, per_row):
    memory = QgsVectorLayer("Polygon?crs=EPSG:2154&field=name:string", "m", "memory")
    features = []
    for index in range(count):
        x, y = 500000 + (index % per_row) * step, 6200000 + (index // per_row) * step
        feature = QgsFeature(memory.fields())
        feature.setGeometry(QgsGeometry.fromRect(QgsRectangle(x, y, x + size, y + size)))
        feature.setAttributes([f"b{index}"])
        features.append(feature)
    memory.dataProvider().addFeatures(features)
    return memory


def area(xmin, ymin, xmax, ymax):
    memory = QgsVectorLayer("Polygon?crs=EPSG:2154&field=name:string", "m", "memory")
    feature = QgsFeature(memory.fields())
    feature.setGeometry(QgsGeometry.fromRect(QgsRectangle(xmin, ymin, xmax, ymax)))
    feature.setAttributes(["zone"])
    memory.dataProvider().addFeatures([feature])
    return memory


def main():
    from filter_mate.adapters.public_api import operations
    from filter_mate.adapters.qgis.feature_count import exact_feature_count
    print(f"QGIS {Qgis.QGIS_VERSION}", flush=True)
    work = tempfile.mkdtemp()
    per_row = int(ROWS ** 0.5) + 1
    batiments = written(squares(ROWS, 10.0, 20.0, per_row), os.path.join(work, "osm.gpkg"), "batiments")
    span = per_row * 20.0
    # the west 45 % of the buildings, and a corner of 300
    west = written(area(499990, 6199990, 500000 + span * 0.45, 6200000 + span), os.path.join(work, "west.gpkg"), "west")
    corner = written(area(499990, 6199990, 500000 + 20 * 15 - 5, 6200000 + 20 * 20 - 5),
                     os.path.join(work, "corner.gpkg"), "corner")
    expected = sum(1 for feature in batiments.getFeatures()
                   if feature.geometry().boundingBox().xMinimum() <= 500000 + span * 0.45)

    started = time.perf_counter()
    report = operations.cross_filter(west, [batiments], selected_only=False)
    spent = time.perf_counter() - started
    subset = batiments.subsetString()
    check("the cross filter of 45 % of the buildings is applied", report.done and not report.error,
          f"{report.done} {report.error or ''}")
    check("its key list is one JSON literal", "json_each" in subset, subset[:90])
    started = time.perf_counter()
    read = sum(1 for _ in batiments.getFeatures())
    read_time = time.perf_counter() - started
    check("the layer keeps the buildings of the area", read == expected, f"{read} read, {expected} expected")
    check("FilterMate counts them", exact_feature_count(batiments, 10.0) == expected)
    check("the filter took less than 3 s", spent < 3.0, f"{spent:.2f} s for {expected:,} keys")
    check("a read of the layer takes less than 1.5 s", read_time < 1.5, f"{read_time:.2f} s")

    report = operations.cross_filter(corner, [batiments], selected_only=False, operator="AND")
    check("AND with a short list is applied", report.done and not report.error, report.error or "")
    kept = sum(1 for _ in batiments.getFeatures())
    check("AND keeps the buildings of the corner, within the area", 0 < kept < 1000, f"{kept} kept")

    operations.clear_filters([batiments])
    report = operations.cross_filter(corner, [batiments], selected_only=False)
    check("a short list stays a plain IN list", "json_each" not in batiments.subsetString()
          and " IN (" in batiments.subsetString(), batiments.subsetString()[:80])
    print(f"\n{sum(RESULTS)}/{len(RESULTS)} passed", flush=True)


if __name__ == "__main__":
    app = QgsApplication([], True)
    app.initQgis()
    root = tempfile.mkdtemp()
    os.symlink(os.environ.get("FM_REPO", "/src"), os.path.join(root, "filter_mate"))
    sys.path.insert(0, root)
    sys.dont_write_bytecode = True
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        RESULTS.append(False)
    os._exit(0 if RESULTS and all(RESULTS) else 1)
