"""Exercise the actual QGIS expression tree and OGC compiler, without a service.

Run with python3 in qgis/qgis:ltr and qgis/qgis:stable. Public-service
observations are opt-in in measure_stream_A.py and SKIP when unavailable.
"""
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from qgis.core import Qgis, QgsApplication, QgsNetworkAccessManager, QgsNetworkRequestParameters, QgsVectorLayer  # noqa: E402
from qgis.PyQt.QtCore import QEventLoop, QTimer  # noqa: E402
from qgis.PyQt.QtNetwork import QNetworkAccessManager, QNetworkRequest  # noqa: E402

root = Path(__file__).resolve().parents[2]
temporary = Path(tempfile.mkdtemp(prefix='fm-stream-a-'))
(temporary / 'filter_mate').symlink_to(root, target_is_directory=True)
os.environ['FILTERMATE_LOG_DIR'] = str(temporary / 'logs')
sys.path.insert(0, str(temporary))
app = QgsApplication([], False)
app.initQgis()
from filter_mate.adapters.qgis.server_filter_translation import translate  # noqa: E402

fields = QgsVectorLayer('Point?field=id:integer&field=nom:string&field=population:integer', 'fixture', 'memory').fields()
failed = []


def check(expression, dialect, expected):
    result = translate(expression, dialect, fields)
    ok = result.status == expected
    print(('PASS' if ok else 'FAIL'), dialect, expression, result.status.value, flush=True)
    if not ok:
        failed.append(expression)
    return result


for dialect in ('wfs', 'arcgis', 'mssql', 'oracle', 'hana'):
    check('"nom" = \'L\'\'Isle-Jourdain\'', dialect, 'NONE' if dialect in ('mssql', 'arcgis') else 'FULL')
    check('"population" > 1000 AND "id" IN (1, 2)', dialect, 'FULL')
    check('left("nom", 3) = \'Sai\'', dialect, 'NONE')
    check('$area > 1e6', dialect, 'NONE')
    check('"id" = 1 AND left("nom", 3) = \'Sai\'', dialect, 'PARTIAL')
    check('"id" = 1 OR left("nom", 3) = \'Sai\'', dialect, 'NONE')
    check('NOT ("id" = 1 AND left("nom", 3) = \'Sai\')', dialect, 'NONE')
    check('"missing" = 1', dialect, 'NONE')
    check('"nom" IS NULL', dialect, 'FULL')
check('"id" = 1', 'oapif', 'NONE')
check('"nom" ILIKE \'saint%\'', 'wfs', 'FULL')
check('"nom" ILIKE \'saint%\'', 'mssql', 'NONE')
check('"id" = ', 'wfs', 'NONE')
check('1 = 0', 'wfs', 'FULL')

from filter_mate.adapters.qgis.server_filter_translation import (  # noqa: E402
    ServerFilterError, apply_server_subset,
)
from filter_mate.infrastructure.database.sql_utils import safe_set_subset_string  # noqa: E402
from filter_mate.core.tasks.executors.attribute_filter_executor import AttributeFilterExecutor  # noqa: E402


class ProviderDouble:
    """A service-shaped layer that forbids data access and simulates rejections."""

    def __init__(self):
        self.subset = '"id" = 2'
        self.calls = []
        self.reject = False
        self.invalid = False

    def providerType(self): return 'arcgisfeatureserver'
    def source(self): return 'https://example.invalid/service'
    def id(self): return 'fixture-service'
    def name(self): return 'fixture service'
    def fields(self): return fields
    def subsetString(self): return self.subset
    def isValid(self): return not self.invalid
    def featureCount(self): raise AssertionError('Network count forbidden')
    def triggerRepaint(self): pass
    def getFeatures(self, *args): raise AssertionError('Network read forbidden')
    def uniqueValues(self, *args): raise AssertionError('Network unique values forbidden')

    def setSubsetString(self, subset):
        self.calls.append(subset)
        self.subset = subset
        if self.reject and len(self.calls) == 1:
            return False
        self.invalid = False
        return True


def expect_refusal(label, operation, layer):
    before = layer.subset
    try:
        operation()
    except ServerFilterError as exc:
        ok = 'fixture service' in str(exc) and layer.subset == before and not layer.calls
    else:
        ok = False
    print('PASS' if ok else 'FAIL', label, flush=True)
    if not ok: failed.append(label)


layer = ProviderDouble()
expect_refusal('no mutation for partial AND',
               lambda: apply_server_subset(layer, '"id" = 1 AND left("nom", 3) = \'Sai\''), layer)
executor = AttributeFilterExecutor(layer, 'ogr', 'id')
expect_refusal('source refusal prevents ID-list fallback',
               lambda: executor.process_qgis_expression('left("nom", 3) = \'Sai\''), layer)
assert safe_set_subset_string(layer, 'left("nom", 3) = \'Sai\'') is False
assert not layer.calls
print('PASS shared subset gate refuses before mutation', flush=True)
layer.reject = True
before = layer.subset
try:
    apply_server_subset(layer, '"id" = 1')
except ServerFilterError:
    assert layer.subset == before and len(layer.calls) == 2
else:
    failed.append('provider rejection not reported')
print('PASS provider rejection restores previous subset', flush=True)
assert apply_server_subset(layer, '"id" = 3') is True
print('PASS FULL predicate applied', flush=True)
from filter_mate.core.tasks.task_completion_handler import apply_pending_subset_requests
assert apply_pending_subset_requests([(layer, layer.subset)], lambda *args: True) == 1
print('PASS task completion does not count a remote provider', flush=True)

from filter_mate.processing.algorithms.batch_filter_algorithm import BatchFilterAlgorithm  # noqa: E402
from qgis.core import QgsProcessingFeedback  # noqa: E402
algorithm = BatchFilterAlgorithm()
algorithm.parameterAsLayerList = lambda *args: [ProviderDouble()]
algorithm.parameterAsExpression = lambda *args: 'left("nom", 3) = \'Sai\''
batch = algorithm.processAlgorithm({}, None, QgsProcessingFeedback())
assert batch[algorithm.LAYERS_FILTERED] == 0
print('PASS Processing reports a refused server filter as failed', flush=True)

from filter_mate.adapters.qgis import server_subset_job as job_module  # noqa: E402
from filter_mate.core.filter.server_transfer_policy import ASYNC, PRELOADED_PROVIDER_MIN  # noqa: E402
if Qgis.QGIS_VERSION_INT < PRELOADED_PROVIDER_MIN:
    from filter_mate.adapters.qgis.server_subset_job import ServerSubsetJob
    local = QgsVectorLayer('Point?field=id:integer', 'old QGIS fixture', 'memory')
    try:
        ServerSubsetJob(local, '"id" = 1').start()
    except ServerFilterError as exc:
        assert '3.32' in str(exc) and not local.subsetString()
        print('PASS old QGIS reports unsupported provider transfer without mutation', flush=True)
    else:
        failed.append('Old QGIS silently accepted a provider transfer')

# A real provider and a loopback HTTP service check what is sent on the wire.
# No public service is needed by the automatic regression suite.
import json  # noqa: E402
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402
from threading import Event, Thread  # noqa: E402
from urllib.parse import parse_qs, urlsplit  # noqa: E402
queries = []
rejected_wheres = set()  # where clauses the fixture starts rejecting mid-run
release = Event()  # cleared: the 777 answers wait, so a job cannot finish before a step acts
release.set()


class ArcGISFixture(BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def do_GET(self):
        parsed = urlsplit(self.path)
        parameters = parse_qs(parsed.query)
        if parsed.path.endswith('/query'):
            queries.append(parameters)
            where = parameters.get('where', [''])[0]
            if '777' in where:
                import time
                time.sleep(0.15)
                release.wait(10)
            if '999' in where or any(clause in where for clause in rejected_wheres) or (
                    parameters.get('returnCountOnly') == ['true'] and not where):
                payload = {'error': {'code': 400, 'message': 'Fixture rejection'}}
            elif parameters.get('returnIdsOnly') == ['true']:
                payload = {'objectIdFieldName': 'id', 'objectIds': [1]}
            elif parameters.get('returnCountOnly') == ['true']:
                payload = {'count': 1}
            else:
                payload = {'geometryType': 'esriGeometryPoint', 'spatialReference': {'wkid': 4326},
                           'fields': [{'name': 'id', 'type': 'esriFieldTypeOID'},
                                      {'name': 'nom', 'type': 'esriFieldTypeString'}],
                           'features': [{'attributes': {'id': 1, 'nom': "L'Isle-Jourdain"},
                                         'geometry': {'x': 1, 'y': 43}}]}
        else:
            payload = {'currentVersion': 10.81, 'id': 0, 'name': 'fixture', 'type': 'Feature Layer',
                       'geometryType': 'esriGeometryPoint', 'objectIdField': 'id',
                       'extent': {'xmin': 0, 'ymin': 42, 'xmax': 2, 'ymax': 44,
                                  'spatialReference': {'wkid': 4326}},
                       'fields': [{'name': 'id', 'type': 'esriFieldTypeOID', 'alias': 'id'},
                                  {'name': 'nom', 'type': 'esriFieldTypeString', 'alias': 'nom', 'length': 100}],
                       'capabilities': 'Query', 'maxRecordCount': 1000}
        content = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)


server = ThreadingHTTPServer(('127.0.0.1', 0), ArcGISFixture)
Thread(target=server.serve_forever, daemon=True).start()
try:
    service = QgsVectorLayer("url='http://127.0.0.1:{}/FeatureServer/0'".format(server.server_port),
                             'loopback ArcGIS', 'arcgisfeatureserver')
    assert service.isValid()
    if job_module.transfer_mode_for_layer(service) != ASYNC:
        # Its setter fetches object IDs on the calling thread: no synchronous
        # fallback, the layer keeps its filter and the user gets the reason.
        from filter_mate.adapters.qgis.server_filter_translation import last_server_filter_error
        before = service.subsetString()
        queries.clear()
        accepted = safe_set_subset_string(service, '"id" = 1')
        message = last_server_filter_error(service)
        ok = not accepted and service.subsetString() == before and not queries and message.startswith(
            'loopback ArcGIS: ') and '3.32' in message
        print('PASS' if ok else 'FAIL', 'ArcGIS refused clearly where its transfer is not proven', '' if ok else message,
              flush=True)
        if not ok:
            failed.append('ArcGIS refusal')
        print('SKIP ArcGIS provider transfer: not proven on QGIS {}'.format(Qgis.QGIS_VERSION), flush=True)
        print('FAILURES', len(failed), flush=True)
        raise SystemExit(bool(failed))
    identity = service.id()
    service.setCustomProperty('filtermate/test_preserve', 'keep')
    service.setOpacity(0.6)
    service.setDisplayExpression('nom')
    service.selectByIds([0])
    service.setAutoRefreshInterval(60000)
    service.setAutoRefreshEnabled(True)
    service.setRefreshOnNotifyEnabled(True)
    service.setRefreshOnNofifyMessage('fixture notification')
    from qgis.core import QgsFeature, QgsProject, QgsVectorLayerJoinInfo
    joined = QgsVectorLayer('None?field=id:integer&field=label:string', 'joined', 'memory')
    join_feature = QgsFeature(joined.fields())
    join_feature.setAttributes([1, 'kept'])
    joined.dataProvider().addFeatures([join_feature])
    QgsProject.instance().addMapLayer(joined)
    join_info = QgsVectorLayerJoinInfo()
    join_info.setTargetFieldName('id')
    join_info.setJoinFieldName('id')
    join_info.setJoinLayer(joined)
    service.addJoin(join_info)
    queries.clear()
    origins = []
    manager = QgsNetworkAccessManager.instance()
    manager.requestAboutToBeCreated[QgsNetworkRequestParameters].connect(
        lambda parameters: origins.append(parameters.originatingThreadId()))
    ticks = []
    heartbeat = QTimer()
    heartbeat.timeout.connect(lambda: ticks.append(True))
    heartbeat.start(1)
    service.selectByIds([0])
    assert service.selectedFeatureCount() == 1
    assert safe_set_subset_string(service, '"id" = 1')
    heartbeat.stop()
    assert ticks, 'The event loop did not remain responsive'
    assert origins, 'No provider request was observed'
    # QGIS identifies the QThread QObject, not the OS thread ID.
    main_thread = QgsNetworkRequestParameters(
        QNetworkAccessManager.Operation.GetOperation, QNetworkRequest(), -1).originatingThreadId()
    assert all(origin != main_thread for origin in origins), origins
    assert service.id() == identity and service.name() == 'loopback ArcGIS'
    assert service.customProperty('filtermate/test_preserve') == 'keep'
    assert service.opacity() == 0.6 and service.displayExpression() == 'nom'
    assert service.autoRefreshInterval() == 60000 and service.hasAutoRefreshEnabled()
    assert service.isRefreshOnNotifyEnabled() and service.refreshOnNotifyMessage() == 'fixture notification'
    assert service.fields().indexOf('joined_label') >= 0
    assert service.selectedFeatureCount() == 0
    print('PASS provider transfer preserves layer identity and style', flush=True)
    assert len(list(service.getFeatures())) == 1
    assert any('"id" = 1' in query.get('where', [''])[0] for query in queries), queries
    print('PASS real ArcGIS provider sends validated SQL from a worker', flush=True)
    before = service.subsetString()
    queries.clear()
    assert not safe_set_subset_string(service, 'left("nom", 3) = \'Sai\'')
    assert service.subsetString() == before and not queries
    print('PASS unsupported expression causes neither HTTP query nor mutation', flush=True)
    assert not safe_set_subset_string(service, '"id" = 999')
    assert service.subsetString() == before
    print('PASS HTTP-200 ArcGIS error is a failure with no mutation', flush=True)
    # The responses carry no cache headers, and QgsBlockingNetworkRequest
    # prefers QGIS's HTTP cache: the verdict must still come from the server.
    assert safe_set_subset_string(service, '"id" = 2') and safe_set_subset_string(service, '"id" = 1')
    before = service.subsetString()
    rejected_wheres.add('"id" = 2')
    queries.clear()
    assert not safe_set_subset_string(service, '"id" = 2')
    assert service.subsetString() == before
    assert any(query.get('returnCountOnly') == ['true'] for query in queries), queries
    rejected_wheres.clear()
    print('PASS ArcGIS verdict is fresh from the server, not a cached response', flush=True)
    rejected_wheres.add('"id" = 5')  # a transient error the first time this filter is seen
    assert not safe_set_subset_string(service, '"id" = 5')
    rejected_wheres.clear()
    assert safe_set_subset_string(service, '"id" = 5') and '"id" = 5' in service.subsetString()
    assert safe_set_subset_string(service, '"id" = 1') and service.subsetString() == before
    print('PASS a refused filter is not answered from the HTTP cache once the server recovers', flush=True)

    from filter_mate.adapters.qgis.server_subset_job import ServerSubsetJob
    loop = QEventLoop()
    job = ServerSubsetJob(service, '"id" = 777', timeout_ms=20)
    job.finished.connect(loop.quit)
    job.start()
    loop.exec()
    assert job.done and not job.success and service.subsetString() == before
    drain = QEventLoop()
    QTimer.singleShot(700, drain.quit)
    drain.exec()
    assert service.subsetString() == before
    print('PASS timeout discards the provider without a late mutation', flush=True)

    native_read = service.readLayerXml
    installs = []
    def reject_first_install(*args):
        result = native_read(*args)
        installs.append(result)
        return False if len(installs) == 1 else result
    service.readLayerXml = reject_first_install
    assert not safe_set_subset_string(service, '"id" = 2')
    assert len(installs) == 2 and service.subsetString() == before
    service.readLayerXml = native_read
    print('PASS failed installation restores the prepared original provider', flush=True)

    from filter_mate.adapters.qgis.server_filter_translation import restore_server_subset
    native = '"nom" = \'C:\\temp\''
    assert restore_server_subset(service, native)
    assert service.subsetString() == native
    assert not safe_set_subset_string(service, native)
    assert service.subsetString() == native
    print('PASS native history restoration preserves SQL backslashes', flush=True)

    from filter_mate.adapters.public_api.filter_mate_public_api import FilterMatePublicAPI
    api = FilterMatePublicAPI(None)
    api._find_vector_layer = lambda name: service
    errors, applied = [], []
    api.error_occurred.connect(lambda operation, message: errors.append(message))
    api.filter_applied.connect(lambda *args: applied.append(args))
    assert not api.apply_filter('loopback ArcGIS', '$area > 1e6')
    assert errors and 'Unsupported part' in errors[-1] and not applied
    print('PASS REST/MCP public API emits the actual refusal and no success', flush=True)

    import filter_mate.filter_mate_app as app_module
    from filter_mate.adapters.public_api.operations import busy_reason
    origins.clear()
    pending_loop = QEventLoop()
    pending_job = ServerSubsetJob(service, '"id" = 777', timeout_ms=5000)
    pending_job.finished.connect(pending_loop.quit)
    release.clear()
    pending_job.start()
    assert busy_reason()
    warnings = []
    previous_warning = app_module.show_warning
    app_module.show_warning = lambda message: warnings.append(message)
    try:
        app_module.FilterMateApp._execute_filter_task(object(), 'filter', {})
        app_module.FilterMateApp._handle_undo_redo(object(), True)
    finally:
        app_module.show_warning = previous_warning
    assert len(warnings) == 2
    print('PASS new GUI filter/undo and REST operations are guarded while preparing', flush=True)
    # The clear comes from inside the job's event loop, like a REST call in
    # the GUI, while the server holds the job's answer. A 10 ms timer used
    # to race a worker that QGIS's HTTP cache served in a few milliseconds.
    cleared = []

    def clear_then_release():
        try:
            cleared.append(api.clear_filter('loopback ArcGIS'))
        finally:
            release.set()

    QTimer.singleShot(0, clear_then_release)
    if not pending_job.done:
        pending_loop.exec()
    assert pending_job.done and not pending_job.success and cleared == [True]
    assert service.subsetString() == ''
    drain = QEventLoop()
    QTimer.singleShot(700, drain.quit)
    drain.exec()
    assert service.subsetString() == ''
    assert all(origin != main_thread for origin in origins), origins
    print('PASS clearing supersedes an in-flight filter without a late mutation', flush=True)

    from qgis.core import QgsProject
    deleted = QgsVectorLayer("url='http://127.0.0.1:{}/FeatureServer/0'".format(server.server_port),
                             'deleted fixture', 'arcgisfeatureserver')
    QgsProject.instance().addMapLayer(deleted)
    deleted_id = deleted.id()
    deleted_loop = QEventLoop()
    deleted_job = ServerSubsetJob(deleted, '"id" = 777', timeout_ms=3000)
    deleted_job.finished.connect(deleted_loop.quit)
    release.clear()
    deleted_job.start()

    def delete_then_release():  # same held answer as the clear above
        try:
            QgsProject.instance().removeMapLayer(deleted_id)
        finally:
            release.set()

    QTimer.singleShot(0, delete_then_release)
    if not deleted_job.done:
        deleted_loop.exec()
    assert deleted_job.done and not deleted_job.success, deleted_job.message
    assert QgsProject.instance().mapLayer(deleted_id) is None
    print('PASS layer deletion discards the prepared provider', flush=True)

    broken = QgsVectorLayer("url='http://127.0.0.1:{}/FeatureServer/0' sql=\"id\" = 999".format(server.server_port),
                            'broken subset', 'arcgisfeatureserver')
    api._find_vector_layer = lambda name: broken
    assert api.clear_filter('broken subset')
    assert broken.isValid() and not broken.subsetString()
    print('PASS an invalid previous subset can still be cleared', flush=True)

    from filter_mate.core.services.history_service import HistoryEntry, HistoryService
    from filter_mate.adapters.undo_redo_handler import UndoRedoHandler
    history = HistoryService()
    entry = HistoryEntry.create('"id" = 1', [service.id()], [(service.id(), '"id" = 999')])
    history.push(entry)
    tracking = {service.id(): {'infos': {'is_already_subset': False}}}
    handler = UndoRedoHandler(history, lambda: tracking, QgsProject.instance, lambda: None, lambda *args: None)
    before = service.subsetString()
    assert not handler._perform_layer_undo(service, tracking)
    assert history.undo_count == 1 and history.redo_count == 0 and service.subsetString() == before
    print('PASS failed server undo leaves the history position unchanged', flush=True)
finally:
    release.set()
    server.shutdown()
    server.server_close()
print('SKIP public services: opt-in measure_stream_A.py', flush=True)
print('FAILURES', len(failed), flush=True)
raise SystemExit(bool(failed))
