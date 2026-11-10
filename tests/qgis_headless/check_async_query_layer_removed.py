# -*- coding: utf-8 -*-
"""A guarded read (adapters/qgis/async_query.py) whose layer is removed while it runs, many times over.

When the read settled, it disconnected the signals of its layers through bound signals kept from the start: once the
layer was deleted, that read freed memory and QGIS crashed (Windows: access violation in ``settled``, QGIS 4.2.2,
2026-11-11; Linux: segmentation fault on the first round). Run inside a qgis/qgis image:

    docker run --rm -v "$PWD":/src:ro qgis/qgis:stable python3 /src/tests/qgis_headless/check_async_query_layer_removed.py

Prints PASS or dies; exits with 1 when the reads did not all settle.
"""
import faulthandler
import os
import sys
import tempfile
import time

faulthandler.enable()
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import QgsApplication, QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsVectorLayer  # noqa: E402
from qgis.PyQt.QtCore import QCoreApplication, QObject  # noqa: E402

ROUNDS = int(os.environ.get("ROUNDS", "200"))


def main():
    from filter_mate.adapters.qgis.async_query import submit_query
    owner = QObject()
    settled = 0
    for number in range(ROUNDS):
        layer = QgsVectorLayer("Point?crs=EPSG:2154&field=a:integer", f"l{number}", "memory")
        features = []
        for index in range(200):
            feature = QgsFeature(layer.fields())
            feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(index, index)))
            feature.setAttributes([index])
            features.append(feature)
        layer.dataProvider().addFeatures(features)
        QgsProject.instance().addMapLayer(layer)

        def compute(task):
            time.sleep(0.02)
            return 1

        submit_query(owner, "_check_slot", layer, "check", compute, lambda result: None)
        QCoreApplication.processEvents()
        QgsProject.instance().removeMapLayer(layer.id())  # deleted while the read runs
        layer = None
        deadline = time.time() + 5
        while time.time() < deadline and QgsApplication.taskManager().count():
            QCoreApplication.processEvents()
            time.sleep(0.005)
        settled += not QgsApplication.taskManager().count()
    ok = settled == ROUNDS
    print(f"{'PASS' if ok else 'FAIL'} a read whose layer is removed while it runs settles, {settled}/{ROUNDS} rounds",
          flush=True)
    return ok


if __name__ == "__main__":
    app = QgsApplication([], False)
    app.initQgis()
    package_root = tempfile.mkdtemp()
    os.symlink(os.environ.get("FM_REPO", "/src"), os.path.join(package_root, "filter_mate"))
    sys.path.insert(0, package_root)
    sys.dont_write_bytecode = True
    passed = main()
    sys.stdout.flush()
    os._exit(0 if passed else 1)
