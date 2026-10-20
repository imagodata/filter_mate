"""Public API with a web service SOURCE, in real QGIS, offline (local WFS fixture).

2026-10-20: ``operations._source_job`` read a WFS source with
``list(layer.getFeatures())`` on the main thread, the whole service when
nothing was selected, and a copy cut by its budget passed for the whole
source. The dock's rule (lot B) applies now: selected or filtered, copied by
lot B's bounded reader in the API worker, an incomplete copy refused.

    docker run --rm --network none -v "$PWD:/src:ro" qgis/qgis:ltr \\
      bash -c 'cd /src/tests/qgis_headless && python3 check_stream_api_sources.py'

Lines are PASS / FAIL / SKIP, then a total; exit code 1 when a FAIL.
"""

import os
import sys
import tempfile
import threading
import traceback
import types

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FILTERMATE_LOG_DIR", "/tmp/filtermate_stream_api_sources_logs")

from qgis.core import (  # noqa: E402
    Qgis,
    QgsApplication,
    QgsFeature,
    QgsGeometry,
    QgsProject,
    QgsRectangle,
    QgsVectorLayer,
)

app = QgsApplication([], False)
app.initQgis()

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
package = types.ModuleType("filter_mate")
package.__path__ = [REPO]
sys.modules["filter_mate"] = package

from filter_mate.adapters.public_api import operations  # noqa: E402
from filter_mate.adapters.qgis import remote_materializer  # noqa: E402
from filter_mate.adapters.qgis.coverage_layers import cache  # noqa: E402
from filter_mate.core.domain.materialization import MaterializationLimits  # noqa: E402
from stream_vector_fixture import VectorService  # noqa: E402

cache.set_cache_root(tempfile.mkdtemp(prefix="fm_api_sources_"))
results = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append(status)
    print("{} {} {}".format(status, name, detail).rstrip(), flush=True)


def skip(name, reason):
    results.append("SKIP")
    print("SKIP {}: {}".format(name, reason), flush=True)


def target_layer():
    """Local polygons around the WFS points (i, 1): ids 0 - 2, point 10, nothing."""
    layer = QgsVectorLayer("Polygon?crs=EPSG:4326&field=zone:string", "zones", "memory")
    rows = []
    for name, bounds in (("first", (-0.5, 0.5, 2.5, 1.5)), ("ten", (9.5, 0.5, 10.5, 1.5)),
                         ("none", (5000.5, 0.5, 5001.5, 1.5))):
        feature = QgsFeature(layer.fields())
        feature.setAttributes([name])
        feature.setGeometry(QgsGeometry.fromRect(QgsRectangle(*bounds)))
        rows.append(feature)
    layer.dataProvider().addFeatures(rows)
    layer.updateExtents()
    return layer


def kept(layer):
    return sorted(feature["zone"] for feature in layer.getFeatures())


reads = []
_bounded_read = remote_materializer.read_bounded_features


def recording_read(*args, **kwargs):
    reads.append(threading.current_thread() is threading.main_thread())
    return _bounded_read(*args, **kwargs)


remote_materializer.read_bounded_features = recording_read


def run(source, target, **kwargs):
    reads.clear()
    target.setSubsetString("")
    return operations.cross_filter(source, [target], project=QgsProject.instance(), **kwargs)


def main():
    print("INFO QGIS " + Qgis.QGIS_VERSION, flush=True)
    with VectorService(attribute_filters=True) as fixture:
        uri = "url='{}' typename='fm:points' srsname='EPSG:4326' version='1.0.0'".format(fixture.url)
        source = QgsVectorLayer(uri, "points", "WFS")
        target = target_layer()
        check("local HTTP WFS source valid", source.isValid())
        QgsProject.instance().addMapLayers([source, target])

        def feature_requests():
            return [request for request in fixture.requests if not request["hits"]]

        # Without lot B's reply validation (QGIS < 3.26, 3.26 - 3.35 under Python 3.12)
        # every service read is refused first, as in the dock.
        validated = remote_materializer.supports_reply_validation()
        refusal = "Select or filter the remote source" if validated else "cannot be proved complete"
        fixture.requests.clear()
        report = run(source, target)
        check("unselected, unfiltered service source refused before any read",
              refusal in (report.error or "") and not feature_requests()
              and not report.done and kept(target) == ["first", "none", "ten"],
              "{!r} {} rows".format(report.error, sum(request["returned"] for request in feature_requests())))
        report = run(source, target, selected_only=False)
        check("whole-layer source refused too", refusal in (report.error or "")
              and not feature_requests(), repr(report.error))

        if not validated:
            source.setSubsetString('"id" < 3')
            report = run(source, target)
            check("older network API refuses a service source before any read",
                  "cannot be proved complete" in (report.error or "") and not feature_requests(), repr(report.error))
            skip("bounded service source reads", "service materialization is unavailable on this QGIS (lot B)")
            return

        source.setSubsetString('"id" < 3')  # the raw QGIS setter sends no request
        fixture.requests.clear()
        report = run(source, target)
        rows = feature_requests()
        check("filtered source read by the bounded reader in the API worker",
              reads == [False] and not report.error and kept(target) == ["first"],
              "{!r} reads on main: {} kept {}".format(report.error, reads, kept(target)))
        check("filtered source copy is capped by the provider row limit",
              rows and all(request["maxfeatures"] for request in rows) and sum(r["returned"] for r in rows) == 3,
              str(rows))

        remote_materializer.mark_partial_result(source, True, source.subsetString())
        report = run(source, target)
        check("partial source refused before any read",
              "incomplete" in (report.error or "") and not reads and kept(target) == ["first", "none", "ten"],
              repr(report.error))
        remote_materializer.mark_partial_result(source, False, source.subsetString())

        limits = remote_materializer.materialization_limits
        remote_materializer.materialization_limits = lambda params=None: MaterializationLimits(max_features=1)
        try:
            report = run(source, target)
        finally:
            remote_materializer.materialization_limits = limits
        check("partial source copy never taken for the whole source",
              "feature limit" in (report.error or "") and "incomplete" in report.error
              and kept(target) == ["first", "none", "ten"], repr(report.error))

        fixture.delay = 1
        try:
            report = run(source, target, feedback=_cancel_soon())
        finally:
            fixture.delay = 0
        check("cancel during the service read keeps the target", (report.error or "") == "canceled"
              and kept(target) == ["first", "none", "ten"], repr(report.error))

        source.setSubsetString("")
        source.selectByExpression('"id" = 10')  # test setup: this reads the service on the main thread
        selected = list(source.selectedFeatureIds())
        report = run(source, target)
        check("selected source rows read by id in the API worker",
              len(selected) == 1 and reads == [False] and not report.error and kept(target) == ["ten"],
              "{!r} {} {}".format(report.error, reads, kept(target)))
        QgsProject.instance().removeAllMapLayers()


def _cancel_soon():
    from qgis.core import QgsFeedback
    from qgis.PyQt.QtCore import QTimer
    feedback = QgsFeedback()
    QTimer.singleShot(300, feedback.cancel)
    return feedback


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        check("uncaught exception", False)
    print("{} passed, {} failed, {} skipped".format(
        results.count("PASS"), results.count("FAIL"), results.count("SKIP")), flush=True)
    os._exit(1 if "FAIL" in results else 0)
