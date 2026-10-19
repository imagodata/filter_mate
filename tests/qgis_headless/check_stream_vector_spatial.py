"""Exact bounded remote filters in real QGIS, including cancellation and CRS.

Run with python3 in qgis/qgis:ltr and qgis/qgis:stable. All automatic cases
use local data. FM_STREAM_PUBLIC=1 additionally measures the public IGN WFS;
an unavailable public service is SKIP. All service work runs in QgsTask.
"""

import os
import sys
import time
import traceback
import types

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FILTERMATE_LOG_DIR", "/tmp/filtermate_stream_b_logs")

from qgis.core import (  # noqa: E402
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCoordinateTransformContext,
    QgsFeature,
    QgsFeatureRequest,
    QgsFeedback,
    QgsGeometry,
    QgsNetworkAccessManager,
    QgsNetworkRequestParameters,
    QgsProject,
    QgsRectangle,
    QgsTask,
    QgsVectorLayer,
)

app = QgsApplication([], False)
app.initQgis()

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
package = types.ModuleType("filter_mate")
package.__path__ = [REPO]
sys.modules["filter_mate"] = package

from filter_mate.adapters.qgis.remote_materializer import (  # noqa: E402
    RemoteMaterializationTask,
    materialize,
    reply_preprocessor_is_safe,
    supports_reply_validation,
)
from filter_mate.adapters.backends.ogr.expression_builder import OGRExpressionBuilder  # noqa: E402
from filter_mate.adapters.backends.ogr.filter_executor import copy_remote_source  # noqa: E402
from filter_mate.core.domain.materialization import MaterializationLimits  # noqa: E402

network_requests = []
QgsNetworkAccessManager.instance().requestAboutToBeCreated[QgsNetworkRequestParameters].connect(
    lambda *args: network_requests.append(1)
)
results = []
fixture_layers = []
fixture_builders = []
settings = {"_processing_settings": {"transform_context": QgsCoordinateTransformContext()}}


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append(status)
    print("{} {} {}".format(status, name, detail), flush=True)


def remote_memory(size=6):
    """Real QGIS memory provider classified as a service, with a stable id.

    The feature-source snapshot stays a real QGIS memory source. This tests
    the remote policy without needing an external network or a mock QGIS.
    """
    layer = QgsVectorLayer("Point?crs=EPSG:4326&field=id:integer&field=label:string", "remote", "memory")
    provider = layer.dataProvider()
    fixture_layers.append((layer, provider))
    rows = []
    for index in range(size):
        feature = QgsFeature(layer.fields())
        feature.setAttributes([index, "L'Isle" if index == 1 else "other"])
        feature.setGeometry(QgsGeometry.fromWkt("POINT({} 1)".format(index)))
        rows.append(feature)
    provider.addFeatures(rows)
    layer.updateExtents()
    layer.providerType = lambda: "WFS"
    layer.source = lambda: "url=http://offline.test/wfs"
    return layer


def source_polygon(crs="EPSG:4326"):
    layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "source", "memory")
    fixture_layers.append((layer, layer.dataProvider()))
    feature = QgsFeature()
    # Hole excludes point 2, although it is inside the BBOX.
    feature.setGeometry(
        QgsGeometry.fromWkt("POLYGON((0.5 0,3.5 0,3.5 2,0.5 2,0.5 0),(1.5 0.5,1.5 1.5,2.5 1.5,2.5 0.5,1.5 0.5))")
    )
    if crs != "EPSG:4326":
        geometry = feature.geometry()
        geometry.transform(
            QgsCoordinateTransform(layer.crs(), QgsCoordinateReferenceSystem(crs), QgsCoordinateTransformContext())
        )
        feature.setGeometry(geometry)
        layer.setCrs(QgsCoordinateReferenceSystem(crs))
    layer.dataProvider().addFeatures([feature])
    layer.updateExtents()
    return layer


def rich_target(remote=False, lines=False):
    kind = "LineString" if lines else "MultiPolygon"
    layer = QgsVectorLayer(kind + "?crs=EPSG:4326&field=id:integer", "relations", "memory")
    provider = layer.dataProvider()
    fixture_layers.append((layer, provider))
    if lines:
        geometries = [QgsGeometry.fromWkt("LINESTRING(-1 1,5 1)"), QgsGeometry.fromWkt("LINESTRING(10 10,11 11)")]
    else:
        geometries = [next(source_polygon().getFeatures()).geometry()]
        geometries += [
            QgsGeometry.fromRect(QgsRectangle(*bounds))
            for bounds in ((-1, -1, 5, 3), (0.7, 0.2, 1.2, 0.7), (3.5, 0, 4.5, 2), (0, -1, 1.3, 1), (10, 10, 11, 11))
        ]
    for index, geometry in enumerate(geometries, 1):
        if not lines:
            geometry.convertToMultiType()
        feature = QgsFeature(layer.fields())
        feature.setAttributes([index])
        feature.setGeometry(geometry)
        provider.addFeatures([feature])
    layer.updateExtents()
    if remote:
        layer.providerType = lambda: "WFS"
        layer.source = lambda: "url=http://offline.test/relations"
    return layer


def filter_keys(target, source, predicate="ST_Intersects", limits=None, **kwargs):
    queued = []
    params = dict(settings, _subset_queue_callback=lambda layer, subset: queued.append(subset))
    if limits:
        params["config_data"] = {"APP": {"OPTIONS": {"REMOTE_MATERIALIZATION": limits}}}
    builder = OGRExpressionBuilder(task_params=params)
    original_log_error = builder.log_error

    def diagnostic_error(message):
        if "has been deleted" in str(message):
            traceback.print_exc()
        original_log_error(message)

    builder.log_error = diagnostic_error
    # Processing output layers belong to each builder's task cache. Keep their
    # owners alive until this worker's comparisons finish, including on Qt6.
    fixture_builders.append(builder)
    expression = builder.build_expression(layer_props={}, predicates={predicate: True}, source_geom=source, **kwargs)
    success = builder.apply_filter(target, expression)
    return success, queued, builder


def automatic(task):
    layer = remote_memory()
    rect = QgsRectangle(0.5, 0, 3.5, 2)
    outcome = materialize(layer, rect, "", '"id" % 2 = 1', MaterializationLimits(), QgsFeedback())
    check(
        "BBOX and exact local expression",
        outcome.complete and outcome.keys == (1, 3) and outcome.fetched == 3,
        repr(outcome),
    )
    outcome = materialize(layer, rect, "", "'0'")
    check("local expression uses QGIS boolean conversion", outcome.complete and not outcome.keys, repr(outcome))
    success, queued, builder = filter_keys(layer, source_polygon())
    check(
        "polygon hole excludes BBOX false positive",
        success and len(queued) == 1 and queued[0] == '"id" IN (1, 3)',
        str(queued) + str(builder.last_error),
    )
    success, queued, builder = filter_keys(layer, source_polygon("EPSG:3857"))
    check("source reprojected to target CRS", success and queued == ['"id" IN (1, 3)'], str(queued))
    success, queued, builder = filter_keys(layer, source_polygon(), limits={"max_features": {"value": 1}})
    check(
        "partial result announced",
        success
        and any("Partial result" in warning for warning in builder.user_warnings)
        and not builder.remote_materialization_outcome.complete,
        str(builder.user_warnings),
    )
    partial_layer = remote_memory()
    success, partial_subset, _ = filter_keys(partial_layer, source_polygon(), limits={"max_features": 1})
    partial_layer.setSubsetString('({}) AND "id" > 0'.format(partial_subset[0]))
    try:
        copy_remote_source(partial_layer)
        check("partial-source provenance survives an attribute combination", False)
    except ValueError:
        check("partial-source provenance survives an attribute combination", True)
    success, queued, builder = filter_keys(layer, source_polygon(), "ST_Disjoint", {"max_features": 1})
    check("partial disjoint refused before applying", not success and not queued, str(builder.user_warnings))
    success, queued, builder = filter_keys(layer, source_polygon(), "ST_Disjoint")
    check("disjoint uses bounded complement", success and queued == ['NOT ("id" IN (1, 3))'], str(queued))
    feedback = QgsFeedback()
    feedback.cancel()
    outcome = materialize(layer, rect, "", "", feedback=feedback)
    check("cancelled read has no keys", outcome.reason == "cancelled" and not outcome.keys, repr(outcome))
    outcome = materialize(layer, rect, "", "missing_function(1)")
    check("invalid local expression refused", outcome.reason == "invalid_expression", repr(outcome))
    outcome = materialize(layer, rect, "", "eval('1')")
    check("local residual cannot escape its bounded feature context",
          outcome.reason == "invalid_expression" and not outcome.fetched, repr(outcome))
    outcome = materialize(remote_memory(502), QgsRectangle(-1, 0, 600, 2), "", "")
    check("more than 500 keys refuses entire result", outcome.reason == "key_limit" and not outcome.keys, repr(outcome))
    try:
        copy_remote_source(layer)
        check("unfiltered remote source refused", False)
    except ValueError:
        check("unfiltered remote source refused", True)
    layer.selectByIds([2])  # QGIS id 2 is stable-key value 1
    copied = copy_remote_source(layer)
    check("only selected source rows copied", [feature["id"] for feature in copied.getFeatures()] == [1])
    layer.removeSelection()
    layer.setSubsetString('"id" < 3')
    layer.selectByIds([2])  # a stale highlighted selection must not narrow the filtered source
    copied = copy_remote_source(layer)
    check("only filtered source rows copied", [feature["id"] for feature in copied.getFeatures()] == [0, 1, 2])
    check("scratch layers never added to project", not QgsProject.instance().mapLayers())
    try:
        copy_remote_source(layer, selected_fids=[99999])
        check("missing selected source rows refused", False)
    except ValueError:
        check("missing selected source rows refused", True)
    from filter_mate.adapters.backends.ogr.filter_executor import OGRSourceContext, prepare_ogr_source_geom

    snapshots = list(copied.getFeatures())
    original_read = layer.getFeatures

    def unexpected_read(*args):
        raise AssertionError("Captured task source features must not be re-read")

    layer.getFeatures = unexpected_read
    prepared = prepare_ogr_source_geom(
        OGRSourceContext(source_layer=layer, task_parameters={"task": {"features": snapshots}})
    )
    check(
        "task source snapshots used without network re-read",
        prepared is not None and len(list(prepared.getFeatures())) == 3,
    )
    try:
        prepare_ogr_source_geom(
            OGRSourceContext(source_layer=layer, task_parameters={"task": {"features": ["field-value"]}})
        )
        check("field values are refused as ambiguous remote feature snapshots", False)
    except ValueError:
        check("field values are refused as ambiguous remote feature snapshots", True)
    from filter_mate.core.services.geometry_preparer import prepare_geometries_by_provider

    order = []
    parameters = {"task": {"features": []}}

    def prepare_ogr():
        order.append("ogr")
        return copied

    def prepare_wkt():
        order.append("wkt")
        assert parameters["task"]["features"]
        return "POINT(1 1)"

    result = prepare_geometries_by_provider(
        ["spatialite"], parameters, layer, "WFS", "", {"spatialite": []}, lambda: None, prepare_wkt, prepare_ogr
    )
    check("source bounded before SpatiaLite WKT callback", result["success"] and order == ["ogr", "wkt"], str(order))
    check("original source selection parameters preserved", parameters["task"]["features"] == [])

    # Exercise both real preparers: raw degree coordinates must enter the WKT
    # path even when the OGR representation has already become metric.
    from filter_mate.adapters.backends.spatialite.filter_executor import (
        SpatialiteSourceContext,
        process_spatialite_geometries,
    )

    projection_parameters = {"task": {"features": []}}

    def project_copy(raw, authid):
        output = QgsVectorLayer("Point?crs=" + authid + "&field=id:integer&field=label:string", "metric", "memory")
        fixture_layers.append((output, output.dataProvider()))
        transform = QgsCoordinateTransform(raw.crs(), output.crs(), QgsCoordinateTransformContext())
        for source_feature in raw.getFeatures():
            feature = QgsFeature(source_feature)
            geometry = feature.geometry()
            geometry.transform(transform)
            feature.setGeometry(geometry)
            output.dataProvider().addFeatures([feature])
        output.updateExtents()
        return output

    def metric_ogr():
        return prepare_ogr_source_geom(
            OGRSourceContext(
                source_layer=layer,
                task_parameters=projection_parameters,
                has_to_reproject_source_layer=True,
                source_layer_crs_authid="EPSG:3857",
                reproject_layer=project_copy,
            )
        )

    def metric_wkt():
        return process_spatialite_geometries(
            projection_parameters["task"]["features"],
            SpatialiteSourceContext(
                source_layer=layer,
                task_parameters=projection_parameters,
                has_to_reproject_source_layer=True,
                source_crs=layer.crs(),
                source_layer_crs_authid="EPSG:3857",
                PROJECT=QgsCoordinateTransformContext(),
            ),
        )

    result = prepare_geometries_by_provider(
        ["spatialite"],
        projection_parameters,
        layer,
        "WFS",
        "",
        {"spatialite": []},
        lambda: None,
        metric_wkt,
        metric_ogr,
    )
    geometry = QgsGeometry.fromWkt(result["spatialite_source_geom"])
    check(
        "remote source WKT reprojected exactly once",
        result["success"] and not geometry.isEmpty() and 200000 < geometry.boundingBox().xMaximum() < 300000,
        result["spatialite_source_geom"][:80],
    )
    check("WKT callback restores original feature ids and scope", projection_parameters["task"]["features"] == [])
    layer.getFeatures = original_read

    # Compare the real local OGR implementation and the service policy, including
    # union semantics, predicate direction, static erosion and dynamic buffers.
    for predicate in (
        "Intersects",
        "Contains",
        "Equals",
        "Touches",
        "Overlaps",
        "Within",
        "Crosses",
        "Covers",
        "CoveredBy",
        "Disjoint",
    ):
        local = remote_memory()
        del local.providerType
        del local.source
        remote = remote_memory()
        left_ok, left, _ = filter_keys(local, source_polygon(), "ST_" + predicate)
        right_ok, right, _ = filter_keys(remote, source_polygon(), "ST_" + predicate)
        local.setSubsetString(left[0])
        left_ids = {feature["id"] for feature in local.getFeatures()}
        local.setSubsetString(right[0])
        right_ids = {feature["id"] for feature in local.getFeatures()}
        check("remote equals local " + predicate, left_ok and right_ok and left_ids == right_ids)
    for label, options in [
        ("buffer", {"buffer_value": 0.6}),
        ("erosion", {"buffer_value": -0.6}),
        ("dynamic buffer", {"buffer_expression": "0.6"}),
        ("centroids", {"use_centroids": True}),
    ]:
        local = remote_memory()
        del local.providerType
        del local.source
        left_ok, left, _ = filter_keys(local, source_polygon(), **options)
        right_ok, right, _ = filter_keys(remote_memory(), source_polygon(), **options)
        local.setSubsetString(left[0])
        left_ids = {feature["id"] for feature in local.getFeatures()}
        local.setSubsetString(right[0])
        right_ids = {feature["id"] for feature in local.getFeatures()}
        check("remote equals local " + label, left_ok and right_ok and left_ids == right_ids)

    from filter_mate.adapters.backends.ogr.filter_executor import (
        OGRSpatialSelectionContext,
        execute_ogr_spatial_selection,
    )

    layer = remote_memory()
    context = OGRSpatialSelectionContext(ogr_source_geom=source_polygon(), current_predicates={0: True})
    subset = execute_ogr_spatial_selection(layer, layer, "", context)
    check(
        "legacy executor returns keys without selecting live layer",
        subset == '"id" IN (1, 3)' and not layer.selectedFeatureIds(),
        str(subset),
    )
    for crs in ("EPSG:4326", "EPSG:3857"):
        for predicate in ("Contains", "Equals", "Touches", "Overlaps", "Within", "Covers", "CoveredBy", "Crosses"):
            local = rich_target(lines=predicate == "Crosses")
            remote = rich_target(remote=True, lines=predicate == "Crosses")
            source = source_polygon(crs)
            left_ok, left, _ = filter_keys(local, source, "ST_" + predicate)
            right_ok, right, _ = filter_keys(remote, source, "ST_" + predicate)
            if not left or not right:
                check("rich geometry " + predicate + " " + crs, False)
                continue
            local.setSubsetString(left[0])
            expected = {feature["id"] for feature in local.getFeatures()}
            local.setSubsetString(right[0])
            actual = {feature["id"] for feature in local.getFeatures()}
            check(
                "rich geometry " + predicate + " " + crs,
                left_ok and right_ok and expected == actual and (crs != "EPSG:4326" or bool(expected)),
                "local={} remote={}".format(len(expected), len(actual)),
            )

    huge = QgsVectorLayer("Polygon?crs=EPSG:4326", "large_window", "memory")
    feature = QgsFeature()
    feature.setGeometry(QgsGeometry.fromRect(QgsRectangle(-1, 0, 800, 2)))
    huge.dataProvider().addFeatures([feature])
    remote_file = remote_memory(700)
    remote_file.providerType = lambda: "ogr"
    remote_file.source = lambda: "/vsicurl/http://offline.test/points.geojson"
    success, queued, _ = filter_keys(remote_file, huge)
    check("remote file retains its existing limit above 500 keys", success and bool(queued))
    file_source = source_polygon()
    file_source.providerType = lambda: "ogr"
    file_source.source = lambda: "/vsicurl/http://offline.test/source.geojson"
    success, queued, _ = filter_keys(remote_memory(), file_source)
    check("remote file source retains its existing unfiltered semantics", success and bool(queued))
    success, queued, builder = filter_keys(remote_memory(700), huge)
    check(
        "service key overflow never applies a subset",
        not success and not queued and builder.remote_materialization_outcome.reason == "key_limit",
    )


def local_http(task):
    from stream_vector_fixture import VectorService, OapifService

    with VectorService() as fixture:
        uri = "url='{}' typename='fm:points' srsname='EPSG:4326' version='1.0.0'".format(fixture.url)
        layer = QgsVectorLayer(uri, "fixture", "WFS")
        check("local HTTP WFS layer valid", layer.isValid())
        fixture.requests.clear()
        if not supports_reply_validation():
            # Refused before any reply observer registration, which segfaults
            # on QGIS 3.26-3.35 under Python 3.12+.
            outcome = materialize(layer, QgsRectangle(0.5, 0, 3.5, 2), "", "")
            check("older network API refuses unverified service reads",
                  outcome.reason == "unverified_filter" and not outcome.keys and not fixture.requests, repr(outcome))
            try:
                copy_remote_source(layer)
                check("older network API refuses a service source copy", False)
            except ValueError as exc:
                check("older network API refuses a service source copy",
                      "cannot be proved complete" in str(exc) and not fixture.requests, str(exc))
            if reply_preprocessor_is_safe(Qgis.QGIS_VERSION_INT, sys.version_info):
                reason = "reply observer lifecycle is unverified before QGIS 3.26"
            else:
                reason = "registering the reply observer crashes QGIS < 3.36 under Python 3.12+"
            print("SKIP service protocol cases: " + reason, flush=True)
            return
        outcome = materialize(layer, QgsRectangle(0.5, 0, 3.5, 2), "", '"id" % 2 = 1')
        reads = [request for request in fixture.requests if not request["hits"]]
        check(
            "actual server receives BBOX",
            bool(reads) and all(request["bbox"] is not None for request in reads),
            str(reads),
        )
        check(
            "HTTP only downloads useful rows",
            outcome.complete and outcome.keys == (1, 3) and sum(request["returned"] for request in reads) == 3,
            repr(outcome),
        )
        empty = materialize(layer, QgsRectangle(2000, 0, 2001, 2), "", "")
        check("empty remote iterator refuses without erasing a filter",
              not empty.complete and not empty.keys and empty.reason == "unverified_filter", repr(empty))
        from filter_mate.adapters.qgis.server_filter_translation import prepare_server_subset, translate
        from filter_mate.adapters.qgis.remote_materializer import materialize_translation
        from filter_mate.core.filter.server_dialect import TranslationStatus

        expression = '"id" >= 1 AND abs("id") < 3'
        translation = translate(expression, 'wfs', layer.fields())
        outcome = materialize_translation(layer, QgsRectangle(0.5, 0, 3.5, 2), translation)
        check("lot A PARTIAL executes bounded residual", translation.status == TranslationStatus.PARTIAL
              and outcome.complete and outcome.keys == (1, 2), repr(outcome))
        expression = 'abs("id") < 3'
        translation = translate(expression, 'wfs', layer.fields())
        outcome = materialize_translation(layer, QgsRectangle(0.5, 0, 3.5, 2), translation)
        check("lot A NONE executes bounded local predicate", translation.status == TranslationStatus.NONE
              and outcome.complete and outcome.keys == (1, 2), repr(outcome))
        layer.setSubsetString('"id" > 4')
        subset = prepare_server_subset(layer, expression, rect=QgsRectangle(0.5, 0, 3.5, 2))
        layer.setSubsetString('')
        check("lot A fallback returns a verified server key subset", translate(subset, 'wfs', layer.fields()).status
              == TranslationStatus.FULL and '1, 2' in subset, subset)
        fixture.fail = True
        broken = QgsVectorLayer(uri + " restrictToRequestBBOX='1'", "broken", "WFS")
        outcome = materialize(broken, QgsRectangle(10, 0, 13, 2), "", "")
        check(
            "HTTP errors never become a complete empty result", not outcome.complete and not outcome.keys, repr(outcome)
        )
        success, queued, _ = filter_keys(broken, source_polygon())
        check("HTTP error never applies an empty subset", not success and not queued)
        fixture.fail = False
        fixture.exception_200 = True
        outcome = materialize(layer, QgsRectangle(0.5, 0, 3.5, 2), "", "")
        check("HTTP 200 ExceptionReport refused", outcome.reason == "read_error", repr(outcome))
        attempts = [filter_keys(layer, source_polygon()) for unused in range(10)]
        success, queued, builder = attempts[-1]
        check(
            "ExceptionReport never applies an empty subset",
            all(not accepted and not subsets for accepted, subsets, unused in attempts),
            str([(accepted, subsets) for accepted, subsets, unused in attempts]),
        )
        fixture.exception_200 = False
        success, queued, builder = filter_keys(layer, source_polygon(), limits={"max_features": 1})
        check(
            "HTTP feature cap announces partial",
            success and queued and builder.remote_materialization_outcome.reason == "feature_limit",
            str(builder.user_warnings),
        )
        fixture.delay = 1
        success, queued, builder = filter_keys(layer, source_polygon(), limits={"timeout_seconds": 0.2})
        check("slow server preserves previous filter", not success and not queued, str(builder.user_warnings))

    with OapifService() as fixture:
        layer = QgsVectorLayer("url='{}' typename='points'".format(fixture.url), "ogc_api", "OAPIF")
        check("local HTTP OGC API layer valid", layer.isValid())
        fixture.requests.clear()
        outcome = materialize(layer, QgsRectangle(40.5, 0, 43.5, 2), "", "", MaterializationLimits(max_features=5))
        reads = [request for request in fixture.requests if "returned" in request]
        check(
            "OGC API sends useful BBOX before its limit",
            outcome.complete
            and outcome.keys == (41, 42, 43)
            and reads
            and all(request.get("bbox") for request in reads),
            repr(outcome) + str(reads),
        )
        layer.setSubsetString('"id" = 49')
        outcome = materialize(layer, QgsRectangle(40.5, 0, 50.5, 2), "", "", MaterializationLimits(max_features=5))
        check(
            "client-side OGC API subset cannot hide the row cap",
            not outcome.complete and outcome.reason == "feature_limit",
            repr(outcome),
        )
        try:
            copy_remote_source(layer)
            check("unverified OGC API source scope refused", False)
        except ValueError:
            check("unverified OGC API source scope refused", True)
        layer.setSubsetString("")
        success, queued, builder = filter_keys(layer, source_polygon())
        check(
            "OGC API key application requires verified server translation",
            not success and not queued and builder.remote_materialization_outcome.complete,
            str(builder.user_warnings),
        )
        fixture.mode = "oapif500"
        outcome = materialize(layer, QgsRectangle(0.5, 0, 3.5, 2), "", "",
                              MaterializationLimits(timeout_seconds=3))
        check("OGC API descendant URL HTTP error refused", outcome.reason == "read_error", repr(outcome))
        success, queued, _ = filter_keys(layer, source_polygon(), limits={"timeout_seconds": 3})
        check("OGC API error never applies an empty subset", not success and not queued)


def public(task):
    requests = network_requests
    manager = QgsNetworkAccessManager.instance()

    def requested(*args):
        requests.append(1)

    # The main NAM observes requests from provider downloader threads.
    try:
        base = "url='https://data.geopf.fr/wfs/ows' srsname='EPSG:4326' version='2.0.0'"
        department = QgsVectorLayer(base + " typename='ADMINEXPRESS-COG.LATEST:departement'", "department", "WFS")
        department.setSubsetString("\"code_insee\" = '31'")
        rows = list(department.getFeatures(QgsFeatureRequest().setLimit(2)))
        if not department.isValid() or len(rows) != 1:
            print("SKIP public IGN WFS: department unavailable", flush=True)
            return
        local = QgsVectorLayer("MultiPolygon?crs=EPSG:4326", "Haute-Garonne", "memory")
        local.dataProvider().addFeatures(rows)
        local.updateExtents()
        target = QgsVectorLayer(base + " typename='ADMINEXPRESS-COG.LATEST:commune'", "communes", "WFS")
        for label, source, dest in [("target_service", local, target), ("source_service", department, local)]:
            started = time.monotonic()
            before = len(requests)
            success, queued, builder = filter_keys(dest, source)
            outcome = getattr(builder, "remote_materialization_outcome", None)
            print(
                "MEASURE {} requests={} seconds={:.3f} success={} outcome={} warnings={}".format(
                    label,
                    len(requests) - before,
                    time.monotonic() - started,
                    success,
                    (
                        "complete={} fetched={} keys={} reason={}".format(
                            outcome.complete, outcome.fetched, len(outcome.keys), outcome.reason
                        )
                        if outcome
                        else None
                    ),
                    builder.user_warnings,
                ),
                flush=True,
            )

        from filter_mate.adapters.qgis.remote_materializer import _bbox_source, _snapshot, read_bounded_features

        limits = MaterializationLimits()
        reader = _bbox_source(_snapshot(target), limits)
        copies = []

        def copy(feature):
            copies.append(feature)
            return False

        started = time.monotonic()
        before = len(requests)
        outcome = read_bounded_features(
            reader,
            QgsFeatureRequest().setFilterRect(rows[0].geometry().boundingBox()),
            limits,
            None,
            copy,
            lambda feature: feature.id(),
        )
        print(
            "MEASURE complete_bbox_copy requests={} fetched={} complete={} seconds={:.3f}".format(
                len(requests) - before, outcome.fetched, outcome.complete, time.monotonic() - started
            ),
            flush=True,
        )
        if not outcome.complete:
            print("SKIP public reference comparison: candidate copy incomplete", flush=True)
            return
        reference = QgsVectorLayer("MultiPolygon?crs=EPSG:4326", "complete_local_candidates", "memory")
        reference.dataProvider().addAttributes(list(target.fields()))
        reference.updateFields()
        reference.dataProvider().addFeatures(copies)
        reference.updateExtents()
        comparison = OGRExpressionBuilder(task_params=settings)
        comparison._feedback = QgsFeedback()
        selected = comparison._select_against_union(reference, rows[0].geometry(), local.crs(), ["intersects"])
        check(
            "public Haute-Garonne local reference exceeds 500 keys",
            len(selected) > 500,
            "local_exact_keys={}".format(len(selected)),
        )
        geometry = rows[0].geometry().intersection(QgsGeometry.fromRect(QgsRectangle(1.3, 43.5, 1.5, 43.7)))
        small = QgsVectorLayer("MultiPolygon?crs=EPSG:4326", "Toulouse", "memory")
        feature = QgsFeature()
        feature.setGeometry(geometry)
        small.dataProvider().addFeatures([feature])
        selected = comparison._select_against_union(reference, geometry, small.crs(), ["intersects"])
        expected = {feature["cleabs"] for feature in reference.getFeatures(QgsFeatureRequest().setFilterFids(selected))}
        success, queued, builder = filter_keys(target, small)
        if success:
            reference.setSubsetString(queued[0])
        actual = {feature["cleabs"] for feature in reference.getFeatures()} if success else set()
        check(
            "public exact result equals complete local copy",
            success and expected == actual,
            "local={} remote={}".format(len(expected), len(actual)),
        )
    finally:
        pass


def wait(task):
    QgsApplication.taskManager().addTask(task)
    while QgsApplication.taskManager().countActiveTasks():
        app.processEvents()
        time.sleep(0.005)
    app.processEvents()
    if task.__dict__.get("exception"):
        raise task.__dict__["exception"]


def main():
    print("INFO QGIS " + Qgis.QGIS_VERSION, flush=True)
    from filter_mate.adapters.qgis.server_filter_translation import ServerFilterError, prepare_server_subset
    owner_layer = remote_memory()
    try:
        prepare_server_subset(owner_layer, 'abs("id") < 3', rect=QgsRectangle(0.5, 0, 3.5, 2))
        check("attribute fallback refuses main-thread reads", False)
    except ServerFilterError:
        check("attribute fallback refuses main-thread reads", True)

    def foreign_owner(task):
        try:
            prepare_server_subset(owner_layer, 'abs("id") < 3', rect=QgsRectangle(0.5, 0, 3.5, 2))
            check("attribute fallback refuses a foreign-thread layer", False)
        except ServerFilterError:
            check("attribute fallback refuses a foreign-thread layer", True)

    wait(QgsTask.fromFunction("attribute fallback ownership", foreign_owner))
    try:
        materialize(remote_memory(), QgsRectangle(0, 0, 2, 2), "", "")
        check("main thread refuses remote reads", False)
    except RuntimeError:
        check("main thread refuses remote reads", True)
    wait(QgsTask.fromFunction("stream B automatic", automatic))
    wait(QgsTask.fromFunction("stream B HTTP fixture", local_http))
    standalone = RemoteMaterializationTask(remote_memory(), QgsRectangle(0.5, 0, 3.5, 2), "", '"id" % 2 = 1')
    wait(standalone)
    check(
        "standalone task returns exact keys",
        standalone.outcome.complete and standalone.outcome.keys == (1, 3),
        repr(standalone.outcome),
    )
    invalid = RemoteMaterializationTask(remote_memory(), None)
    wait(invalid)
    check("standalone invalid extent is an explicit outcome", invalid.outcome.reason == "invalid_extent")
    cancelled = RemoteMaterializationTask(remote_memory(), QgsRectangle(0.5, 0, 3.5, 2))
    cancelled.cancel()
    check("cancellation before scheduling is explicit", cancelled.outcome.reason == "cancelled")
    if os.environ.get("FM_STREAM_PUBLIC") == "1":
        wait(QgsTask.fromFunction("stream B public measurement", public))
    else:
        print("SKIP public WFS: set FM_STREAM_PUBLIC=1", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        check("uncaught exception", False)
    print("{} passed, {} failed".format(results.count("PASS"), results.count("FAIL")), flush=True)
    os._exit(1 if "FAIL" in results else 0)
