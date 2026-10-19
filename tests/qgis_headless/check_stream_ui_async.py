"""Network thread audit of the dock; run with QGIS --code under Xvfb.

FM_STREAM_PUBLIC=1 also exercises the Geoplateforme WFS (SKIP if unavailable).
FM_STREAM_BASELINE=1 records violations without failing, for before/after evidence.
Only operation and thread are printed: request URLs and feature keys stay private.
Initiating calls must return within one second. The GUI-event budget defaults to
2 seconds for native Qt rendering on virtualized runners; override with
FM_STREAM_HEARTBEAT_BUDGET. Network-origin and result checks are unconditional.
"""
import importlib
import faulthandler
import os
import shutil
import sys
import tempfile
import time
import traceback

from qgis.core import (QgsApplication, QgsFeature, QgsGeometry, QgsNetworkAccessManager,
                       QgsNetworkRequestParameters, QgsPointXY, QgsProject, QgsVectorLayer)
from qgis.PyQt.QtCore import QSettings, QThread, QTimer, Qt
from qgis.PyQt.QtNetwork import QNetworkAccessManager, QNetworkRequest
from qgis.PyQt.QtCore import QUrl
import qgis.utils

faulthandler.enable(all_threads=True)
ROOT = os.environ.get('FM_REPO', '/src')
STATE = {'phase': '', 'requests': [], 'failures': [], 'gaps': [], 'last_tick': time.monotonic()}
PLUGIN = None
GUI_EVENT_BUDGET = float(os.environ.get('FM_STREAM_HEARTBEAT_BUDGET', '2.0'))
MAIN_THREAD_ID = QgsNetworkRequestParameters(QNetworkAccessManager.Operation.GetOperation,
                                             QNetworkRequest(QUrl('http://127.0.0.1/')), 0).originatingThreadId()


def show_exception(type_, value, tb, *args, **kwargs):
    traceback.print_exception(type_, value, tb)
    STATE['failures'].append('QGIS Python exception')


qgis.utils.showException = show_exception


def heartbeat():
    now = time.monotonic()
    if STATE['phase']:
        STATE['gaps'].append(now - STATE['last_tick'])
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
        report(max_gap < GUI_EVENT_BUDGET, name + ' keeps GUI heartbeat within {:.1f}s'.format(GUI_EVENT_BUDGET))
    # Keep auditing delayed callbacks until the next action starts.


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
    if remote.providerType() == 'OAPIF':
        rows = picker.list_widgets[remote.id()].getFeaturesList()
        report(len(rows) == 25 and {row[1] for row in rows} == set(range(1, 26)),
               'service list contains the expected values and stable keys')
    text = 'Place' if remote.providerType() == 'OAPIF' else 'Paris'
    measure('search entity', lambda: picker._populate_features_sync(field, search_text=text))
    if remote.providerType() == 'OAPIF':
        report(picker.list_widgets[remote.id()].count() == 25, 'service search returns the expected rows')
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
    from filter_mate.adapters.qgis.server_filter_translation import last_server_filter_error, remember_server_filter_error
    remember_server_filter_error(remote, '')
    PLUGIN.iface.messageBar().clearWidgets()

    def filter_error():
        error = last_server_filter_error(remote)
        if remote.providerType() != 'OAPIF':
            return error
        item = PLUGIN.iface.messageBar().currentItem()
        visible = item.text() if item is not None else ''
        return error or (visible if 'complete CQL2 translation verdict' in visible else '')

    measure('filter', lambda: dock.launchTaskEvent(False, 'filter'))
    until = time.monotonic() + (180 if remote.providerType() == 'WFS' else 30)
    while not remote.subsetString() and not filter_error() and time.monotonic() < until:
        drain(0.1)
    refused = filter_error()
    if remote.providerType() == 'OAPIF' and refused:
        # Lot A deliberately refuses unproven CQL2 translation. The UI must
        # report that refusal and preserve the complete source, not fake a filter.
        report('complete CQL2 translation verdict' in refused and not remote.subsetString(),
               'unsupported OGC API filter is explicitly refused without mutation')
        check_count(dock, remote, 25, 'refused service filter preserves all features')
    else:
        report(bool(remote.subsetString()), 'filter applied a service subset')
        if remote.providerType() == 'OAPIF' and os.environ.get('FM_STREAM_BASELINE') != '1':
            check_count(dock, remote, 15, 'service filter returns the exact matching features')
    measure('unfilter', lambda: dock.launchTaskEvent(False, 'unfilter'))
    until = time.monotonic() + (180 if remote.providerType() == 'WFS' else 30)
    while remote.subsetString() and time.monotonic() < until:
        drain(0.1)
    report(not remote.subsetString(), 'unfilter cleared the service subset')
    if remote.providerType() == 'OAPIF' and os.environ.get('FM_STREAM_BASELINE') != '1':
        check_count(dock, remote, 25, 'service unfilter restores all features')
    measure('return local', lambda: dock.comboBox_filtering_current_layer.setLayer(local))
    violations = [phase for phase, main in STATE['requests'][before:] if main]
    print('MAIN_THREAD_REQUESTS {}'.format(violations), flush=True)
    report(not violations or os.environ.get('FM_STREAM_BASELINE') == '1', 'no dock network request on main thread')
    STATE['phase'] = ''


def wait_until(predicate, seconds):
    until = time.monotonic() + seconds
    while not predicate() and time.monotonic() < until:
        drain(0.05)
    return predicate()


def set_group(dock, name):
    """Make ``name`` the EXPLORING group (a switch is skipped while another one is in progress)."""
    seen = []
    for _ in range(20):
        if dock.current_exploring_groupbox == name:
            return True
        seen.append(dock.current_exploring_groupbox)
        dock._restore_groupbox_ui_state(name)   # also the group stored for the layer (post-filter reloads)
        dock.exploring_groupbox_changed(name)
        drain(0.3)
    print('GROUP {} not kept, seen {}'.format(name, seen), flush=True)
    return dock.current_exploring_groupbox == name


def bar_text():
    """Titles and texts of the message bar, to find a warning whatever its argument order."""
    return ' | '.join('{} {}'.format(item.title(), item.text()) for item in PLUGIN.iface.messageBar().items())


def read_feature(dock, layer, key):
    """The service feature whose "id" is ``key``, read in a task."""
    from filter_mate.adapters.qgis.async_query import submit_query
    from qgis.core import QgsFeatureRequest
    result = []
    request = QgsFeatureRequest().setFilterExpression('"id" = {}'.format(key))
    submit_query(dock, '_stream_feature_query', layer, 'FilterMate: read a test feature',
                 lambda task: list(task.features(request)), result.append)
    wait_until(lambda: bool(result), 15)
    return result[0][0] if result and result[0] else None


def check_review_fixes(dock, remote, local, service):
    """Review of lot C (#193): H1, H2, M1 and M11 on the offline OGC API service."""
    from dataclasses import replace
    from filter_mate.adapters.qgis import source_capability_probe as probe
    from filter_mate.adapters.qgis.server_filter_translation import last_server_filter_error, remember_server_filter_error
    from qgis.core import QgsRectangle
    launches = []
    dock.launchingTask.connect(launches.append)
    bar = PLUGIN.iface.messageBar()
    STATE['phase'] = 'review fixes'
    dock.comboBox_filtering_current_layer.setLayer(remote)
    wait_until(lambda: dock.current_layer is remote, 10)
    controller = dock._exploring_ctrl
    controller.set_layer(remote)
    props = dock.PROJECT_LAYERS[remote.id()]
    drain(1)

    def idle(name, owner=None):
        slot = getattr(controller if owner is None else owner, name, None)
        return slot is None or slot.task is None

    def quiet():
        """No read of the selection, the canvas selection, the debounced pick or the lists still running."""
        picker = dock.widgets['EXPLORING']['MULTIPLE_SELECTION_FEATURES']['WIDGET']
        wait_until(lambda: all((idle('_selection_query'), idle('_canvas_selection_query'), idle('_zoom_query'),
                                idle('_debounced_feature_query', dock), idle('_population_query', picker))), 20)
        drain(0.5)

    def launched_filter():
        error = last_server_filter_error(remote) or ''
        return bool(remote.subsetString()) or 'complete CQL2 translation verdict' in error + bar_text()

    def settle_filter():
        wait_until(lambda: not getattr(dock, '_filtering_in_progress', False), 30)
        drain(1)
        if remote.subsetString():
            dock.launchTaskEvent(False, 'unfilter')
            wait_until(lambda: not remote.subsetString(), 30)
        remember_server_filter_error(remote, '')
        bar.clearWidgets()
        drain(0.5)

    # H1: an empty custom selection is no selection: nothing read, the source is not filtered by it.
    report(set_group(dock, 'custom_selection'), 'H1 custom selection active')
    dock.widgets['EXPLORING']['CUSTOM_SELECTION_EXPRESSION']['WIDGET'].setExpression('')
    drain(1.5)
    wait_until(lambda: idle('_selection_query'), 15)
    selection = dock.get_current_features()
    report(selection == ([], '') and idle('_selection_query'),
           'H1 empty custom selection is no selection and starts no read of the service')
    canvas = PLUGIN.iface.mapCanvas()
    canvas.setExtent(QgsRectangle(100, 100, 101, 101))
    controller.zooming_to_features([])
    report(idle('_zoom_query'), 'H1 zoom without filter starts no read of the service')
    drain(1)
    report(canvas.extent().contains(QgsRectangle(12, 12, 13, 13)), 'H1 zoom without filter shows the provider extent')
    del launches[:]
    bar.clearWidgets()
    dock.launchTaskEvent(False, 'filter')
    report(launches == ['filter'], 'H1 empty custom selection filters at once, as a local layer')
    settle_filter()
    expression = props['filtering'].get('current_filter_expression') or ''
    report(' IN (' not in expression and not remote.subsetString(),
           'H1 no key list of the whole service, source not filtered')

    # H2: a refused multiple selection launches nothing and changes nothing.
    key = next(key for key in probe._CACHE if key[0] == remote.id())
    original = probe._CACHE[key]
    probe._CACHE[key] = replace(original, key_list_limit=10)
    picker = dock.widgets['EXPLORING']['MULTIPLE_SELECTION_FEATURES']['WIDGET']
    try:
        report(set_group(dock, 'multiple_selection'), 'H2 multiple selection active')
        wait_until(lambda: remote.id() in picker.list_widgets and picker.list_widgets[remote.id()].count() == 25, 20)
        picker.setCheckedFeatureIds(list(range(1, 16)), emit_signal=False)
        drain(0.5)
        first = read_feature(dock, remote, 1)
        remote.selectByIds([first.id()] if first is not None else [])
        selected = list(remote.selectedFeatureIds())
        before = props['filtering'].get('current_filter_expression')
        del launches[:]
        bar.clearWidgets()
        dock.launchTaskEvent(False, 'filter')
        drain(2)
        report(not launches and 'key limit' in bar_text(), 'H2 too many service keys: the filter is refused, not launched')
        report(props['filtering'].get('current_filter_expression') == before != 'FALSE'
               and list(remote.selectedFeatureIds()) == selected and len(picker.checkedItems()) == 15
               and not remote.subsetString(), 'H2 refused selection leaves the selection and the source untouched')
    finally:
        probe._CACHE[key] = original
        picker.deselect_all('De-select All')   # as the user: no later list delivery re-checks the 15 rows
        remote.removeSelection()
        settle_filter()

    # M1: a debounced pick of the feature a Filter click is waiting for does not drop that filter.
    quiet()
    report(set_group(dock, 'single_selection'), 'M1 single selection active')
    feature = read_feature(dock, remote, 5)
    single = dock.widgets['EXPLORING']['SINGLE_SELECTION_FEATURES']['WIDGET']
    single.setFeature(feature.id())

    def picked():
        return single.feature().isValid() and single.feature().id() == feature.id()

    wait_until(picked, 15)
    drain(1)  # the picker's own debounced pick
    quiet()
    service.delay = 1.0
    try:
        report(set_group(dock, 'single_selection') and picked(),
               'M1 the single selection designates the picked feature')
        quiet()
        controller._invalidate_remote_selection_cache()
        del launches[:]
        bar.clearWidgets()
        dock.launchTaskEvent(False, 'filter')
        waiting = not launches and not idle('_selection_query')
        dock.exploring_features_changed(feature)   # the 300 ms debounce delivers the same pick
        launched = wait_until(lambda: bool(launches), 20)
        print('M1 waiting={} launched={} group={} bar={!r}'.format(
            waiting, launched, dock.current_exploring_groupbox, bar_text()[:300]), flush=True)
        report(waiting and launched and 'not launched' not in bar_text(),
               'M1 filter waiting for its pick survives the debounced pick of the same feature')
        settle_filter()

        # M11: a read cancelled under a waiting filter says the filter was not launched.
        quiet()
        report(set_group(dock, 'single_selection') and picked(),
               'M11 the single selection designates the picked feature')
        controller._invalidate_remote_selection_cache()
        del launches[:]
        dock.launchTaskEvent(False, 'filter')
        waiting = not launches and not idle('_selection_query')
        remote.reload()   # dataChanged cancels the selection read
        told = wait_until(lambda: 'not launched' in bar_text(), 10)
        print('M11 waiting={} told={} launches={} bar={!r}'.format(waiting, told, launches, bar_text()[:300]),
              flush=True)
        report(waiting and told and not launches, 'M11 a cancelled selection read tells the filter was not launched')
    finally:
        service.delay = 0.15
        settle_filter()
    dock.launchingTask.disconnect(launches.append)
    dock.comboBox_filtering_current_layer.setLayer(local)
    drain(1)
    violations = [phase for phase, main in STATE['requests'] if main and phase == 'review fixes']
    report(not violations, 'review fixes make no network request on the main thread')
    STATE['phase'] = ''


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
        if os.environ.get('FM_STREAM_BASELINE') != '1':
            from filter_mate.adapters.qgis.async_query import SnapshotQueryTask
            original_run = SnapshotQueryTask.run

            def audited_run(task):
                success = original_run(task)
                if task.error is not None:
                    print('TASK_FAILURE operation={} error={}'.format(
                        task.compute.__qualname__, type(task.error).__name__), flush=True)
                return success

            SnapshotQueryTask.run = audited_run
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
        features = []
        for index in range(1, 26):
            feature = QgsFeature(local.fields())
            feature.setAttributes([index, 'Local {}'.format(index)])
            feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(index, index)))
            features.append(feature)
        local.dataProvider().addFeatures(features)
        local.updateExtents()
        QgsProject.instance().addMapLayer(local)
        until = time.monotonic() + 20
        while (local.id() not in dock.PROJECT_LAYERS or dock.current_layer is not local) and time.monotonic() < until:
            drain(0.1)
        drain(2)
        report(dock is not None, 'dock opens')
        # Warm native row/font layout on the local path before measuring HTTP reads.
        # This also checks that the inexpensive path is still synchronous.
        local_picker = dock.widgets['EXPLORING']['MULTIPLE_SELECTION_FEATURES']['WIDGET']
        local_picker.setDisplayExpression('name')
        report(local_picker.list_widgets[local.id()].count() == 25, 'local list remains synchronous')
        drain(1)
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
            if os.environ.get('FM_STREAM_BASELINE') != '1':
                check_review_fixes(dock, remote, local, service)
        if os.environ.get('FM_STREAM_PUBLIC') == '1':
            uri = ("url='https://data.geopf.fr/wfs/ows' version='2.0.0' "
                   "typename='ADMINEXPRESS-COG.LATEST:commune' srsname='EPSG:4326' "
                   "pagingEnabled='true' pageSize='1000'")
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
QTimer.singleShot(900000 if os.environ.get('FM_STREAM_PUBLIC') == '1' else 480000,
                  lambda: os._exit(2))
