"""Server attribute filters on a WFS, per QGIS version, with a local HTTP fixture.

Run with python3 in each qgis/qgis image, 3.22 to nightly. Where
core/filter/server_transfer_policy allows the asynchronous transfer, its
guarantees are checked: candidate and rollback providers prepared in a
task, HTTP-200 ExceptionReport and HTTP 500 refused, timeout and
cancellation without a late mutation, failed installation restored.
Before 3.32 the synchronous WFS fallback is checked and its main-thread
freeze is printed (FREEZE line); where the policy refuses WFS (QGIS whose
setter corrupts a running read) the refusal is checked and the freeze is
still measured. Every mode filters once while a map canvas downloads the
layer. The ArcGIS Feature Server lifecycle is in
check_stream_vector_filters.py.
"""
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time
import types

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from qgis.core import (  # noqa: E402
    Qgis, QgsApplication, QgsNetworkAccessManager, QgsNetworkRequestParameters, QgsProject, QgsRectangle, QgsTask,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QT_VERSION_STR, QEventLoop, QThread, QTimer  # noqa: E402
from qgis.PyQt.QtNetwork import QNetworkAccessManager, QNetworkRequest  # noqa: E402

root = Path(__file__).resolve().parents[2]
temporary = Path(tempfile.mkdtemp(prefix='fm-stream-versions-'))
(temporary / 'filter_mate').symlink_to(root, target_is_directory=True)
os.environ['FILTERMATE_LOG_DIR'] = str(temporary / 'logs')
sys.path.insert(0, str(temporary))
app = QgsApplication([], True)  # a real map canvas renders the layer
app.initQgis()
from qgis.gui import QgsMapCanvas  # noqa: E402

from filter_mate.adapters.qgis import server_subset_job as job_module  # noqa: E402
from filter_mate.adapters.qgis.server_filter_translation import (  # noqa: E402
    ServerFilterError, last_server_filter_error, prepare_server_subset, restore_server_subset,
)
from filter_mate.core.filter.server_transfer_policy import ASYNC, REFUSE, SYNC  # noqa: E402
from filter_mate.infrastructure.database.sql_utils import safe_set_subset_string  # noqa: E402
from stream_vector_fixture import VectorService  # noqa: E402

failed = []


def check(label, ok, detail=''):
    print(('PASS' if ok else 'FAIL'), label, '' if ok else detail, flush=True)
    if not ok:
        failed.append(label)


def wait(milliseconds):
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def ids(layer):
    return sorted(int(feature['id']) for feature in layer.getFeatures())


def refusal(operation):
    try:
        operation()
    except ServerFilterError as exc:
        return str(exc)
    return ''


origins = []
QgsNetworkAccessManager.instance().requestAboutToBeCreated[QgsNetworkRequestParameters].connect(
    lambda parameters: origins.append(parameters.originatingThreadId()))
# QGIS identifies the QThread QObject, not the OS thread ID.
main_thread = QgsNetworkRequestParameters(
    QNetworkAccessManager.Operation.GetOperation, QNetworkRequest(), -1).originatingThreadId()

with VectorService(attribute_filters=True) as fixture:
    uri = "url='{}' typename='fm:points' srsname='EPSG:4326' version='1.0.0'".format(fixture.url)
    layer = QgsVectorLayer(uri, 'loopback WFS', 'WFS')
    check('local HTTP WFS layer valid', layer.isValid())
    QgsProject.instance().addMapLayer(layer)
    mode = job_module.transfer_mode_for_layer(layer)
    arcgis = job_module.transfer_mode_for_layer(types.SimpleNamespace(providerType=lambda: 'arcgisfeatureserver'))
    print('MODE QGIS {} ({}) Qt {} wfs={} arcgis={}'.format(
        Qgis.QGIS_VERSION, Qgis.QGIS_VERSION_INT, QT_VERSION_STR, mode, arcgis), flush=True)
    check('transfer mode known', mode in (ASYNC, SYNC, REFUSE), mode)

    # 2026-10-20: 30 s was too short for the public Géoplateforme WFS; the
    # delay is configurable (APP.OPTIONS.SERVER_FILTER), 60 s for WFS.
    from filter_mate.config.config import ENV_VARS  # noqa: E402
    delays = [job_module.ServerSubsetJob(layer, '"id" = 7').timer.interval()]
    saved_config = ENV_VARS.get('CONFIG_DATA')
    try:
        for value in (45, 'x', 0):
            ENV_VARS['CONFIG_DATA'] = {'APP': {'OPTIONS': {'SERVER_FILTER': {'wfs_timeout_seconds': {'value': value}}}}}
            delays.append(job_module.ServerSubsetJob(layer, '"id" = 7').timer.interval())
    finally:
        ENV_VARS['CONFIG_DATA'] = saved_config
        if saved_config is None:
            del ENV_VARS['CONFIG_DATA']
    check('WFS server filter delay: 60 s by default, configurable, malformed value ignored',
          delays == [60000, 45000, 60000, 60000], str(delays))

    fixture.requests.clear()
    accepted = safe_set_subset_string(layer, '"id" = 1 AND abs("id") < 3')
    check('PARTIAL predicate refused before any request', not accepted and layer.subsetString() == ''
          and not fixture.requests and 'Unsupported part' in last_server_filter_error(layer),
          last_server_filter_error(layer))

    # The QGIS 3.22 WFS setter corrupts the heap when a render still reads
    # the layer: each mode must survive a filter while the canvas downloads.
    canvas = QgsMapCanvas()
    canvas.resize(400, 200)
    canvas.show()
    canvas.setDestinationCrs(layer.crs())
    canvas.setLayers([layer])
    canvas.setExtent(QgsRectangle(-1, 0, 1999, 2))
    fixture.delay = 1.5
    canvas.refresh()
    wait(400)
    drawing = canvas.isDrawing()
    from filter_mate.adapters.public_api.operations import _background_tasks_running  # noqa: E402
    _background_tasks_running()  # one-time imports, not part of the measure
    native_set = layer.setSubsetString
    setter = []

    def timed_set(subset):
        started = time.perf_counter()
        try:
            return native_set(subset)
        finally:
            setter.append((time.perf_counter() - started) * 1000)

    layer.setSubsetString = timed_set
    started = time.perf_counter()
    try:
        accepted = safe_set_subset_string(layer, '"id" = 40')
    finally:
        layer.setSubsetString = native_set
    elapsed = (time.perf_counter() - started) * 1000
    print('CANVAS QGIS {} filter while the canvas downloads the layer (server delay 1.5 s): {}'.format(
        Qgis.QGIS_VERSION, {
            SYNC: 'main thread blocked {:.0f} ms, setter {:.0f} ms'.format(elapsed, sum(setter)),
            ASYNC: 'installed after a responsive wait of {:.0f} ms'.format(elapsed),
            REFUSE: 'refused in {:.0f} ms'.format(elapsed)}[mode]), flush=True)
    wait(2500)
    fixture.delay = 0
    expected = mode != REFUSE
    check('filter while a map canvas downloads the layer: {}, no crash'.format(
        'applied' if expected else 'refused'), drawing and accepted == expected
        and ('"id" = 40' in layer.subsetString()) == expected, '{} {} {!r}'.format(drawing, accepted, layer.subsetString()))
    canvas.setLayers([])
    wait(200)
    assert safe_set_subset_string(layer, '') and layer.subsetString() == ''

    # The dock applies a filter task's subsets in its finished(), while QGIS
    # still lists the task (status Complete) among its active tasks.
    from filter_mate.core.tasks.task_completion_handler import apply_pending_subset_requests  # noqa: E402
    finished_loop = QEventLoop()

    class FilterEngineTask(QgsTask):  # the class name the busy guards look for
        def __init__(self):
            super().__init__('FilterMate fixture filter', QgsTask.Flag.CanCancel)
            self.applied = None

        def run(self):
            time.sleep(0.2)  # a real filter takes time; an instant run() hides the issue
            return True

        def finished(self, result):
            try:
                # 2026-10-20: an API call waits for the end of finished(); only the
                # server filter of this task tolerates it (allow_finishing).
                from filter_mate.adapters.public_api.operations import busy_reason
                self.busy = busy_reason()
                self.applied = apply_pending_subset_requests([(layer, '"id" = 7')], safe_set_subset_string)
                self.busy_after = busy_reason()
            finally:
                QTimer.singleShot(0, finished_loop.quit)

    dock_task = FilterEngineTask()
    QgsApplication.taskManager().addTask(dock_task)
    finished_loop.exec()
    check('filter applied from a finishing dock filter task: {}'.format('applied' if expected else 'refused'),
          dock_task.applied == (1 if expected else 0) and ('"id" = 7' in layer.subsetString()) == expected,
          '{} {!r} {}'.format(dock_task.applied, layer.subsetString(), last_server_filter_error(layer)))
    from filter_mate.adapters.public_api.operations import BACKGROUND_BUSY, busy_reason  # noqa: E402
    check('API busy during the dock task finished(), free after it',
          dock_task.busy == BACKGROUND_BUSY == dock_task.busy_after and not busy_reason(),
          '{!r} {!r} {!r}'.format(dock_task.busy, dock_task.busy_after, busy_reason()))
    assert safe_set_subset_string(layer, '') and layer.subsetString() == ''

    if mode == REFUSE:
        fixture.requests.clear()
        accepted = safe_set_subset_string(layer, '"id" = 3')
        message = last_server_filter_error(layer)
        check('WFS refused with a clear message, no request, no mutation', not accepted and layer.subsetString() == ''
              and not fixture.requests and message.startswith('loopback WFS: ') and '3.32' in message, message)
        # What the synchronous fallback would freeze here, measured with no
        # concurrent read (the case that corrupts the heap on this QGIS).
        freezes = []
        for value in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 3):
            subset = prepare_server_subset(layer, '"id" = {}'.format(value))
            started = time.perf_counter()
            job_module.apply_server_subset_sync(layer, subset)
            freezes.append((time.perf_counter() - started) * 1000)
        check('the synchronous setter itself works on the fixture', ids(layer) == [3], repr(layer.subsetString()))
        print('FREEZE QGIS {} synchronous WFS setter, not used (refused): first call {:.1f} ms, then median {:.1f} ms, '
              'max {:.1f} ms over {} filters'.format(Qgis.QGIS_VERSION, freezes[0], statistics.median(freezes[1:]),
                                                      max(freezes[1:]), len(freezes) - 1), flush=True)
        print('SKIP asynchronous and synchronous WFS transfer on QGIS {}'.format(Qgis.QGIS_VERSION), flush=True)

    if mode == ASYNC:
        prepared = []
        native_prepared = job_module.ServerSubsetJob._prepared
        native_run = job_module._PrepareTask.run

        def spy_prepared(job, task, success):
            prepared.append((success, [provider is not None and provider.isValid() for provider in task.providers],
                             task.backup_valid, getattr(task, 'worker', None)))
            return native_prepared(job, task, success)

        def spy_run(task):
            task.worker = QThread.currentThread() != app.thread()
            return native_run(task)

        job_module._PrepareTask.run = spy_run
        native_start = job_module.ServerSubsetJob.start
        blocked = []

        def timed(function):
            def wrapper(*args):
                started = time.perf_counter()
                try:
                    return function(*args)
                finally:
                    blocked.append((time.perf_counter() - started) * 1000)
            return wrapper

        job_module.ServerSubsetJob.start = timed(native_start)
        job_module.ServerSubsetJob._prepared = timed(spy_prepared)
        installed = []
        for label, value in (('first', 2), ('warm', 3)):
            origins.clear()
            del blocked[:]
            ticks = []
            heartbeat = QTimer()
            heartbeat.timeout.connect(lambda: ticks.append(time.perf_counter()))
            heartbeat.start(5)
            started = time.perf_counter()
            installed.append(safe_set_subset_string(layer, '"id" = {}'.format(value)))
            ended = time.perf_counter()
            heartbeat.stop()
            moments = [started] + ticks + [ended]
            gap = max(later - earlier for earlier, later in zip(moments, moments[1:]))
            print('ASYNC {} filter: {:.0f} ms until installed; main thread in start {:.0f} ms, in installation '
                  '{:.0f} ms, longest gap between 5 ms ticks {:.0f} ms'.format(
                      label, (ended - started) * 1000, blocked[0] if blocked else -1,
                      blocked[-1] if len(blocked) > 1 else -1, gap * 1000), flush=True)
        job_module.ServerSubsetJob.start = native_start
        sent = list(origins)
        check('FULL filter installed by the asynchronous transfer', installed == [True, True]
              and '"id" = 3' in layer.subsetString() and ids(layer) == [3], '{} {!r}'.format(installed, layer.subsetString()))
        check('candidate and rollback providers prepared in a worker task',
              len(prepared) == 2 and all(entry == (True, [True, True], True, True) for entry in prepared), repr(prepared))
        check('every service request leaves the main thread', bool(sent) and main_thread not in sent, repr(sent))
        before = layer.subsetString()

        accepted = safe_set_subset_string(layer, '"id" = 999')
        check('HTTP-200 OWS ExceptionReport (WFS 1.1 / 2.0) refused, previous filter kept', not accepted
              and layer.subsetString() == before and ids(layer) == [3] and 'rejected' in last_server_filter_error(layer),
              last_server_filter_error(layer))
        # QGIS's GML parser ends a WFS 1.0 ServiceExceptionReport as an empty
        # collection, with no provider error: a known limit, reported only.
        accepted = safe_set_subset_string(layer, '"id" = 998')
        print('LIMIT HTTP-200 WFS 1.0 ServiceExceptionReport {} by QGIS'.format(
            'accepted (empty layer)' if accepted else 'refused'), flush=True)
        if accepted:
            assert safe_set_subset_string(layer, '"id" = 3') and layer.subsetString() == before
        fixture.fail = True
        try:
            accepted = safe_set_subset_string(layer, '"id" = 4')
        finally:
            fixture.fail = False
        check('HTTP 500 refused, previous filter kept', not accepted and layer.subsetString() == before
              and ids(layer) == [3], last_server_filter_error(layer))

        # fixture.release cleared: the server holds the 777 answer, so each
        # step acts while the job is certainly still preparing.
        fixture.release.clear()
        loop = QEventLoop()
        job = job_module.ServerSubsetJob(layer, '"id" = 777', timeout_ms=20)
        job.finished.connect(loop.quit)
        job.start()
        if not job.done:
            loop.exec()
        timed_out = job.done and not job.success and 'canceled or timed out' in job.message
        fixture.release.set()
        wait(1200)
        check('timeout discards the prepared provider without a late mutation',
              timed_out and layer.subsetString() == before, job.message)
        loop = QEventLoop()
        job = job_module.ServerSubsetJob(layer, '"id" = 777', timeout_ms=10000)
        job.finished.connect(loop.quit)
        fixture.release.clear()
        job.start()
        QTimer.singleShot(0, job.cancel)
        if not job.done:
            loop.exec()
        canceled = job.done and not job.success and 'canceled or timed out' in job.message
        fixture.release.set()
        wait(1200)
        check('cancellation keeps the previous filter without a late mutation',
              canceled and layer.subsetString() == before, job.message)
        loop = QEventLoop()
        job = job_module.ServerSubsetJob(layer, '"id" = 777', timeout_ms=10000)
        job.finished.connect(loop.quit)
        fixture.release.clear()
        job.start()
        cleared = []

        def clear_then_release():
            try:
                cleared.append(safe_set_subset_string(layer, ''))
            finally:
                fixture.release.set()

        QTimer.singleShot(0, clear_then_release)
        if not job.done:
            loop.exec()
        wait(1200)
        check('clearing supersedes an in-flight filter without a late mutation',
              job.done and not job.success and cleared == [True] and layer.subsetString() == '', repr(cleared))

        assert safe_set_subset_string(layer, '"id" = 3')
        before = layer.subsetString()
        native_read = layer.readLayerXml
        installs = []

        def reject_first_install(*args):
            result = native_read(*args)
            installs.append(result)
            return False if len(installs) == 1 else result

        layer.readLayerXml = reject_first_install
        try:
            accepted = safe_set_subset_string(layer, '"id" = 5')
        finally:
            layer.readLayerXml = native_read
        check('failed installation restores the prepared original provider', not accepted and len(installs) == 2
              and layer.subsetString() == before and ids(layer) == [3], repr(installs))
        check('history replays a native snapshot', restore_server_subset(layer, '"id" = 6') and ids(layer) == [6])
        job_module.ServerSubsetJob._prepared = native_prepared
        job_module._PrepareTask.run = native_run
        print('SKIP synchronous WFS fallback: the asynchronous transfer is proven on this QGIS', flush=True)

    if mode == SYNC:
        freezes = []
        setter = []
        during = []
        native_set = layer.setSubsetString

        def timed_set(subset):
            started = time.perf_counter()
            try:
                return native_set(subset)
            finally:
                setter.append((time.perf_counter() - started) * 1000)

        layer.setSubsetString = timed_set
        try:
            for value in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 3):
                origins.clear()
                started = time.perf_counter()
                accepted = safe_set_subset_string(layer, '"id" = {}'.format(value))
                freezes.append((time.perf_counter() - started) * 1000)
                during.extend(origins)
                if not accepted:
                    break
        finally:
            layer.setSubsetString = native_set
        check('FULL filter applied synchronously, no request inside the setter',
              accepted and not during and '"id" = 3' in layer.subsetString(),
              '{} {} {!r}'.format(accepted, len(during), layer.subsetString()))
        fixture.requests.clear()
        check('server receives the OGC filter and returns the filtered row', ids(layer) == [3] and any(
            '<ogc:Literal>3</ogc:Literal>' in request['filter'] for request in fixture.requests), repr(fixture.requests))
        print('FREEZE QGIS {} synchronous WFS filter on the main thread: first call {:.1f} ms (setter {:.1f} ms), '
              'then median {:.1f} ms, max {:.1f} ms over {} filters (setter alone: median {:.1f} ms, max {:.1f} ms)'.format(
                  Qgis.QGIS_VERSION, freezes[0], setter[0], statistics.median(freezes[1:]), max(freezes[1:]),
                  len(freezes) - 1, statistics.median(setter[1:]), max(setter[1:])), flush=True)
        before = layer.subsetString()

        check('clearing applies synchronously', safe_set_subset_string(layer, '') and layer.subsetString() == '')
        assert safe_set_subset_string(layer, '"id" = 3') and layer.subsetString() == before
        message = refusal(lambda: restore_server_subset(layer, 'SELECT * FROM missing_table'))
        check('provider returning False keeps the previous filter', 'rejected the attribute filter' in message
              and layer.subsetString() == before and ids(layer) == [3], message)
        message = refusal(lambda: restore_server_subset(layer, '$area > 1'))
        check('WFS error reported by the setter keeps the previous filter', 'rejected the attribute filter' in message
              and layer.subsetString() == before and ids(layer) == [3], message)

        native_set = layer.setSubsetString
        native_valid = layer.isValid
        calls = []

        def raise_first(subset):
            calls.append(subset)
            result = native_set(subset)
            if len(calls) == 1:
                raise RuntimeError('fixture provider failure')
            return result

        layer.setSubsetString = raise_first
        try:
            accepted = safe_set_subset_string(layer, '"id" = 4')
        finally:
            layer.setSubsetString = native_set
        check('exception in the setter restores the previous filter', not accepted and len(calls) == 2
              and layer.subsetString() == before, repr(calls))
        calls.clear()
        validity = {'valid': True}

        def invalidate_first(subset):
            calls.append(subset)
            result = native_set(subset)
            validity['valid'] = len(calls) > 1
            return result

        layer.setSubsetString = invalidate_first
        layer.isValid = lambda: validity['valid'] and native_valid()
        try:
            accepted = safe_set_subset_string(layer, '"id" = 5')
        finally:
            layer.setSubsetString = native_set
            layer.isValid = native_valid
        check('invalid layer after the setter restores the previous filter', not accepted and len(calls) == 2
              and layer.subsetString() == before and 'previous filter was restored' in last_server_filter_error(layer),
              repr(calls))
        calls.clear()
        layer.setSubsetString = lambda subset: calls.append(subset) or native_set(subset)
        layer.isValid = lambda: False  # QGIS would only store the subset and return False
        try:
            accepted = safe_set_subset_string(layer, '"id" = 8')
        finally:
            layer.setSubsetString = native_set
            layer.isValid = native_valid
        check('invalid layer refused before the setter', not accepted and not calls and layer.subsetString() == before
              and 'already invalid' in last_server_filter_error(layer), last_server_filter_error(layer))
        layer.isEditable = lambda: True
        try:
            accepted = safe_set_subset_string(layer, '"id" = 6')
        finally:
            del layer.isEditable
        check('editing layer refused without mutation', not accepted and layer.subsetString() == before
              and 'Finish editing' in last_server_filter_error(layer), last_server_filter_error(layer))
        check('history replays a native snapshot', restore_server_subset(layer, '"id" = 6') and ids(layer) == [6])
        message = refusal(lambda: job_module.ServerSubsetJob(layer, '"id" = 7').start())
        check('the asynchronous job itself still refuses', '3.32' in message and '"id" = 6' in layer.subsetString(),
              message)
        print('SKIP asynchronous WFS transfer: not proven on QGIS {}'.format(Qgis.QGIS_VERSION), flush=True)
    canvas.hide()
    QgsProject.instance().removeAllMapLayers()

print('FAILURES', len(failed), flush=True)
raise SystemExit(bool(failed))
