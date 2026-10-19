"""Network thread audit of the dock; run with QGIS --code under Xvfb.

FM_STREAM_PUBLIC=1 also exercises the Geoplateforme WFS (SKIP if unavailable).
FM_STREAM_BASELINE=1 records violations without failing, for before/after evidence.
Only operation and thread are printed: request URLs and feature keys stay private.
"""
import importlib
import faulthandler
import os
import shutil
import sys
import tempfile
import time
import traceback

from qgis.core import QgsApplication, QgsNetworkAccessManager, QgsNetworkRequestParameters, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings, QThread, QTimer, Qt
from qgis.PyQt.QtNetwork import QNetworkAccessManager, QNetworkRequest
from qgis.PyQt.QtCore import QUrl
import qgis.utils

faulthandler.enable(all_threads=True)
ROOT = os.environ.get('FM_REPO', '/src')
STATE = {'phase': '', 'requests': [], 'failures': [], 'gaps': [], 'last_tick': time.monotonic()}
PLUGIN = None
MAIN_THREAD_ID = QgsNetworkRequestParameters(QNetworkAccessManager.Operation.GetOperation,
                                             QNetworkRequest(QUrl('http://127.0.0.1/')), 0).originatingThreadId()


def show_exception(type_, value, tb, *args, **kwargs):
    traceback.print_exception(type_, value, tb)
    STATE['failures'].append('QGIS Python exception')


qgis.utils.showException = show_exception

def trace_blocking_callback():
    if os.environ.get('FM_STREAM_TRACE_BLOCKS') == '1':
        faulthandler.cancel_dump_traceback_later()
        faulthandler.dump_traceback_later(1.0, repeat=False)


def heartbeat():
    now = time.monotonic()
    if STATE['phase']:
        STATE['gaps'].append(now - STATE['last_tick'])
        trace_blocking_callback()
    else:
        faulthandler.cancel_dump_traceback_later()
    STATE['last_tick'] = now


HEARTBEAT = QTimer()
HEARTBEAT.timeout.connect(heartbeat)
HEARTBEAT.start(25)

def report(ok, name):
    print(('PASS ' if ok else 'FAIL ') + name, flush=True)
    if not ok:
        STATE['failures'].append(name)


def request_created(*args):
    if STATE['phase']:
        main = args[0].originatingThreadId() == MAIN_THREAD_ID
        STATE['requests'].append((STATE['phase'], main))
        print('NETWORK operation={} thread={}'.format(STATE['phase'], 'main' if main else 'worker'), flush=True)


def drain(seconds=1):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        QgsApplication.processEvents()
        time.sleep(0.01)


def measure(name, action):
    STATE['phase'] = name
    STATE['gaps'] = []
    STATE['last_tick'] = time.monotonic()
    trace_blocking_callback()
    started = time.monotonic()
    action()
    duration = time.monotonic() - started
    print('ACTION {} duration={:.3f}s'.format(name, duration), flush=True)
    if os.environ.get('FM_STREAM_BASELINE') != '1':
        report(duration < 1.0, name + ' returns without waiting for network')
    drain(2)
    max_gap = max(STATE['gaps'] or [0])
    print('HEARTBEAT {} max_gap={:.3f}s'.format(name, max_gap), flush=True)
    if os.environ.get('FM_STREAM_BASELINE') != '1':
        report(max_gap < 1.0, name + ' keeps GUI heartbeat responsive')
    STATE['phase'] = ''
    faulthandler.cancel_dump_traceback_later()


def verify_tasks(dock, layer):
    from filter_mate.adapters.qgis.async_query import submit_query
    from qgis.core import QgsFeatureRequest
    events = []
    reads = []

    def compute(task):
        reads.append(QThread.currentThread() != QgsApplication.instance().thread())
        return list(task.features(QgsFeatureRequest()))

    old = submit_query(dock, '_stream_smoke_query', layer, 'FilterMate: old test read', compute,
                       lambda result: events.append('old'))
    current = submit_query(dock, '_stream_smoke_query', layer, 'FilterMate: current test read', compute,
                           lambda result: events.append(('new', len(result),
                                                        QThread.currentThread() == QgsApplication.instance().thread())))
    cancelled = old.isCanceled()
    until = time.monotonic() + 15
    while not events and time.monotonic() < until:
        drain(0.05)
    drain(0.1)
    report(cancelled, 'replaced task cancels with feedback')
    report(events == [('new', 25, True)], 'only current generation delivered on GUI thread')
    report(bool(reads) and all(reads), 'feature reads execute on worker threads')


def check_count(dock, layer, expected, name):
    from filter_mate.adapters.qgis.async_query import submit_query
    from qgis.core import QgsFeatureRequest
    result = []
    submit_query(dock, '_stream_count_query', layer, 'FilterMate: verify filtered count',
                 lambda task: sum(1 for feature in task.features(QgsFeatureRequest())), result.append)
    until = time.monotonic() + 15
    while not result and time.monotonic() < until:
        drain(0.05)
    report(result == [expected], name)


def exercise(dock, remote, local, field, expression):
    before = len(STATE['requests'])
    measure('register service', lambda: QgsProject.instance().addMapLayer(remote))
    until = time.monotonic() + 20
    while remote.id() not in dock.PROJECT_LAYERS and time.monotonic() < until:
        drain(0.1)
    report(remote.id() in dock.PROJECT_LAYERS, 'service registered in dock')
    measure('change current layer', lambda: dock.comboBox_filtering_current_layer.setLayer(remote))
    controller = dock._exploring_ctrl
    controller.set_layer(remote)
    if os.environ.get('FM_STREAM_BASELINE') == '1':
        controller._features_cache = None  # Avoid the unrelated legacy cache API mismatch in the baseline.
    values = []
    original_update = controller._update_features_widget
    controller._update_features_widget = lambda result: values.append(result)
    measure('unique values', lambda: controller.set_field(field))
    if remote.providerType() == 'OAPIF':
        report(bool(values) and len(values[-1]) == 25, 'remote unique values delivered')
    controller._update_features_widget = original_update
    picker = dock.widgets['EXPLORING']['MULTIPLE_SELECTION_FEATURES']['WIDGET']
    measure('list values', lambda: picker.setDisplayExpression(field))
    measure('search entity', lambda: picker._populate_features_sync(field, search_text='Place'))
    measure('zoom expression', lambda: controller.zooming_to_features([], expression))
    # selectedFeatureIds itself reads only the in-memory selection.
    remote.selectByIds([1, 2])
    measure('zoom selection', controller.zoom_to_selected)
    measure('filtered extent', lambda: dock.get_filtered_layer_extent(remote))
    dock.exploring_groupbox_changed('custom_selection')
    dock.widgets['EXPLORING']['CUSTOM_SELECTION_EXPRESSION']['WIDGET'].setExpression(expression)
    drain(2)
    until = time.monotonic() + 30
    while getattr(getattr(controller, '_selection_query', None), 'task', None) is not None and time.monotonic() < until:
        drain(0.1)
    report(dock.current_exploring_groupbox == 'custom_selection', 'custom selection active before filtering')
    measure('filter', lambda: dock.launchTaskEvent(False, 'filter'))
    until = time.monotonic() + 30
    while QgsApplication.taskManager().activeTasks() and time.monotonic() < until:
        drain(0.1)
    report(bool(remote.subsetString()), 'filter applied a service subset')
    if remote.providerType() == 'OAPIF' and os.environ.get('FM_STREAM_BASELINE') != '1':
        check_count(dock, remote, 15, 'service filter returns the exact matching features')
    measure('unfilter', lambda: dock.launchTaskEvent(False, 'unfilter'))
    until = time.monotonic() + 30
    while QgsApplication.taskManager().activeTasks() and time.monotonic() < until:
        drain(0.1)
    report(not remote.subsetString(), 'unfilter cleared the service subset')
    if remote.providerType() == 'OAPIF' and os.environ.get('FM_STREAM_BASELINE') != '1':
        check_count(dock, remote, 25, 'service unfilter restores all features')
    measure('return local', lambda: dock.comboBox_filtering_current_layer.setLayer(local))
    violations = [phase for phase, main in STATE['requests'][before:] if main]
    print('MAIN_THREAD_REQUESTS {}'.format(violations), flush=True)
    report(not violations or os.environ.get('FM_STREAM_BASELINE') == '1', 'no dock network request on main thread')


def run():
    global PLUGIN
    try:
        settings = QSettings()
        settings.setValue('FilterMate/discord_welcome_dismissed', True)
        settings.setValue('FilterMate/whats_new_seen', 99)
        settings.setValue('qgis/digitizing/validate_geometries', 0)
        plugins = tempfile.mkdtemp(prefix='fm_stream_')
        shutil.copytree(ROOT, os.path.join(plugins, 'filter_mate'), ignore=shutil.ignore_patterns(
            '.git', '.claude', '.agents', '.codex', '.aws', 'dist', 'tests', 'docs', 'website',
            '_bmad', '_bmad-output', 'logs', '__pycache__'))
        sys.path.insert(0, plugins)
        qgis.utils.plugin_paths.insert(0, plugins)
        qgis.utils.updateAvailablePlugins()
        report(qgis.utils.loadPlugin('filter_mate') and qgis.utils.startPlugin('filter_mate'), 'plugin starts')
        PLUGIN = qgis.utils.plugins['filter_mate']
        PLUGIN.run()
        until = time.monotonic() + 60
        while (PLUGIN.app is None or PLUGIN.app.dockwidget is None
               or not PLUGIN.app.dockwidget.widgets_initialized) and time.monotonic() < until:
            drain(0.1)
        dock = PLUGIN.app.dockwidget
        if dock is None:
            raise RuntimeError('Plugin dock did not initialize')
        QgsNetworkAccessManager.instance().requestAboutToBeCreated[QgsNetworkRequestParameters].connect(
            request_created, Qt.ConnectionType.DirectConnection)
        local = QgsVectorLayer('Point?crs=EPSG:4326&field=id:integer&field=name:string', 'local', 'memory')
        QgsProject.instance().addMapLayer(local)
        drain(2)
        report(dock is not None, 'dock opens')
        sys.path.insert(0, '/src/tests/qgis_headless')
        from stream_fixture import FeatureService
        service = FeatureService()
        remote = QgsVectorLayer("url='{}' typename='places'".format(service.url), 'offline service', 'OAPIF')
        report(remote.isValid(), 'offline OGC API fixture loads')
        STATE['phase'] = 'observer calibration'
        QgsNetworkAccessManager.instance().get(QNetworkRequest(QUrl(service.url + '/conformance')))
        drain(0.2)
        STATE['phase'] = ''
        report(any(phase == 'observer calibration' and main for phase, main in STATE['requests']),
               'network observer detects an actual main-thread request')

        if remote.isValid():
            if os.environ.get('FM_STREAM_BASELINE') != '1':
                verify_tasks(dock, remote)
            exercise(dock, remote, local, 'name', '"id" > 10')
            report(service.reads > 0, 'offline HTTP fixture received feature reads')
        if os.environ.get('FM_STREAM_PUBLIC') == '1':
            uri = ("url='https://data.geopf.fr/wfs/ows' version='2.0.0' "
                   "typename='ADMINEXPRESS-COG.LATEST:commune' srsname='EPSG:4326' "
                   "pagingEnabled='true' pageSize='100'")
            remote = QgsVectorLayer(uri, 'communes', 'WFS')
            if not remote.isValid():
                print('SKIP Geoplateforme WFS unavailable', flush=True)
            else:
                field = 'nom_officiel' if remote.fields().indexOf('nom_officiel') >= 0 else remote.fields()[0].name()
                exercise(dock, remote, local, field, '"code_insee" = \'75056\'')
        else:
            print('SKIP public services (set FM_STREAM_PUBLIC=1)', flush=True)
    except Exception:
        traceback.print_exc()
        STATE['failures'].append('exception')
    finally:
        print('STREAM_RESULT failures={}'.format(len(STATE['failures'])), flush=True)
        os._exit(1 if STATE['failures'] else 0)


QTimer.singleShot(1000, run)
QTimer.singleShot(180000, lambda: os._exit(2))
