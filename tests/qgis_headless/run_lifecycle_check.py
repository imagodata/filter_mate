# -*- coding: utf-8 -*-
"""
FilterMate task and lifecycle checks in a real QGIS with its GUI (official qgis/qgis Docker images, Xvfb).

``run_gui_smoke.py`` drives the dock through one pass of every layer kind; this script stresses what a
pass does not: tasks that overlap, layers removed under a running task, repeated layer changes, a plugin
unloaded and loaded again. QGIS runs it at startup (``--code``) and quits with its exit code:

    python3 tests/qgis_headless/make_fixtures.py /tmp/fm
    FM_FIXTURES=/tmp/fm xvfb-run -a qgis --nologo --noversioncheck --profiles-path /tmp/profiles \\
        --code tests/qgis_headless/run_lifecycle_check.py

Checks (2026-10-17):

- a second click on Filter while the first task runs: the final subsets are the second task's;
- a target layer removed while a filter task runs: no crash, no critical message;
- three changes of the current layer: the dock is connected to the current layer's selectionChanged
  once, and to the previous layers' not at all;
- unload then load the plugin again: no second toolbar, and QGIS no longer calls the unloaded instance
  (project fileNameChanged, layer tree view currentLayerChanged, selectionChanged);
- a layer picked in the combo box right before a late refresh of the panel stays the panel's layer
  (``run_gui_smoke.py`` "a late refresh keeps the layer the user picked", repeated).

Prints one ``PASS`` / ``FAIL`` line per check.
"""
import faulthandler
import json
import logging
import os
import random
import shutil
import sys
import tempfile
import time
import traceback

from qgis.core import Qgis, QgsApplication, QgsProject, QgsRasterLayer, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings, Qt, QTimer
from qgis.utils import iface
import qgis.utils

STATE = {'results': [], 'python_errors': [], 'criticals': [], 'started': time.time()}
faulthandler.enable(all_threads=True)


def _show_exception(type_, value, tb, msg=None, messagebar=False, level=None):
    text = ''.join(traceback.format_exception(type_, value, tb)).strip()
    STATE['python_errors'].append(f"{msg or ''} {text.splitlines()[-1] if text else value}".strip())
    print(f"   [Python exception] {msg or ''}\n{text}", flush=True)


qgis.utils.showException = _show_exception


def _watchdog():
    print('FAIL   watchdog: the run did not finish in 12 minutes', flush=True)
    os._exit(2)


QTimer.singleShot(12 * 60 * 1000, _watchdog)

REPO = os.environ.get('FM_REPO') or (os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                     if '__file__' in globals() else '/src')
PACKAGE = 'filter_mate'
EXCLUDED = ('.git', '.github', '.claude', '.serena', '_bmad', '_bmad-output', 'dist', 'build', 'scripts',
            'knowledge', 'website', 'tests', 'docs', 'logs', '__pycache__', '*.pyc', 'test_*.py')
FIXTURES = os.environ.get('FM_FIXTURES', '/tmp/fm')
STEP_TIMEOUT = float(os.environ.get('FM_STEP_TIMEOUT', '90'))
POINTS = int(os.environ.get('FM_LIFECYCLE_POINTS', '150000'))
REPEATS = int(os.environ.get('FM_LIFECYCLE_REPEATS', '8'))

with open(os.path.join(FIXTURES, 'manifest.json'), encoding='utf-8') as _stream:
    M = json.load(_stream)
project = QgsProject.instance()


def report(status, name, detail=''):
    STATE['results'].append((status, name))
    print(f"{status:<5}  {name}  {detail}".rstrip(), flush=True)


def check(name, condition, detail=''):
    report('PASS' if condition else 'FAIL', name, detail)
    return bool(condition)


def _on_log(message, tag, level):
    if tag == 'Python error' or (tag == 'FilterMate' and level == Qgis.MessageLevel.Critical):
        STATE['python_errors'].append(f"[{tag}] {message[:300]}")
        print(f"   [QGIS log {tag}] {message[:300]}", flush=True)


QgsApplication.messageLog().messageReceived.connect(_on_log)


_SEEN_ITEMS = set()


def _scan_message_bar():
    """Record the critical messages of the bar (widgetAdded hands a plain QWidget: the items are read)."""
    for item in iface.messageBar().items():
        try:
            if id(item) in _SEEN_ITEMS:
                continue
            _SEEN_ITEMS.add(id(item))
            if item.level() == Qgis.MessageLevel.Critical:
                STATE['criticals'].append(f"{item.title()}: {item.text()}"[:300])
                print(f"   [message bar critical] {item.title()}: {item.text()[:200]}", flush=True)
        except RuntimeError:
            continue


iface.messageBar().widgetAdded.connect(lambda *_args: _scan_message_bar())


class _ErrorRecords(logging.Handler):
    def emit(self, record):
        STATE['python_errors'].append(f"[{record.name}] {record.getMessage()[:300]}")


_ERRORS = _ErrorRecords(level=logging.ERROR)


def watch_plugin_loggers():
    for name, logger in list(logging.root.manager.loggerDict.items()):
        if isinstance(logger, logging.Logger) and name.split('.')[0] in ('FilterMate', 'filter_mate') \
                and _ERRORS not in logger.handlers:
            logger.addHandler(_ERRORS)


# --- helpers ---------------------------------------------------------------

def plugin():
    return qgis.utils.plugins.get(PACKAGE)


def app():
    return plugin().app


def dock():
    return app().dockwidget


def layer(name):
    found = project.mapLayersByName(name)
    return found[0] if found else None


def tasks_idle():
    try:
        own = set(app().tasks_descriptions.values())
    except Exception:
        own = set()
    return not [task for task in QgsApplication.taskManager().activeTasks()
                if task.description().startswith('FilterMate') or task.description() in own]


def registered(*layer_names):
    ids = [layer(name).id() for name in layer_names if layer(name) is not None]
    return len(ids) == len(layer_names) and all(layer_id in app().PROJECT_LAYERS for layer_id in ids)


def settled(seconds=2.5):
    since = time.time()
    return lambda: tasks_idle() and time.time() - since > seconds


def settled_after(predicate, seconds=2.5):
    """Condition: ``predicate`` true and no task running, both for ``seconds`` (the post-filter window)."""
    state = {'since': None}

    def done():
        if not (predicate() and tasks_idle()):
            state['since'] = None
            return False
        if state['since'] is None:
            state['since'] = time.time()
        return time.time() - state['since'] > seconds
    return done


def current_is(name):
    since = time.time()

    def done():
        current = getattr(dock(), 'current_layer', None)
        return current is not None and current.name() == name and tasks_idle() and time.time() - since > 2.5
    return done


def toolbars():
    from qgis.PyQt.QtWidgets import QToolBar
    found = []
    for toolbar in iface.mainWindow().findChildren(QToolBar):
        try:
            if toolbar.objectName() == 'FilterMate':
                found.append(toolbar)
        except RuntimeError:
            continue
    return found


def write_points(path, count):
    """``count`` points on a grid over the zones extent (EPSG:2154), field ``n``."""
    from osgeo import ogr, osr
    driver = ogr.GetDriverByName('GPKG')
    if os.path.exists(path):
        driver.DeleteDataSource(path)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(int(M['crs'].split(':')[1]))
    source = driver.CreateDataSource(path)
    target = source.CreateLayer('pts', srs, ogr.wkbPoint)
    target.CreateField(ogr.FieldDefn('n', ogr.OFTInteger))
    xmin, ymin, xmax, ymax = M['dem_extent']
    side = int(count ** 0.5) + 1
    target.StartTransaction()
    for index in range(count):
        x = xmin + (index % side + 0.5) * (xmax - xmin) / side
        y = ymin + (index // side + 0.5) * (ymax - ymin) / side
        feature = ogr.Feature(target.GetLayerDefn())
        feature.SetField('n', index)
        feature.SetGeometry(ogr.CreateGeometryFromWkt(f"POINT({x} {y})"))
        target.CreateFeature(feature)
    target.CommitTransaction()
    source = None


def add_points_layer():
    pts = QgsVectorLayer(STATE['pts_path'] + '|layername=pts', 'pts', 'ogr')
    project.addMapLayer(pts)
    return pts


def set_targets(target_names):
    combo = dock().checkableComboBoxLayer_filtering_layers_to_filter
    model = combo.model()
    for row in range(model.rowCount()):
        item = model.item(row)
        wanted = any(item.text().startswith(name + ' [') for name in target_names)
        item.setCheckState(Qt.CheckState.Checked if wanted else Qt.CheckState.Unchecked)
    if not dock().pushButton_checkable_filtering_layers_to_filter.isChecked():
        dock().pushButton_checkable_filtering_layers_to_filter.setChecked(True)


def set_buffer(value):
    d = dock()
    d.pushButton_checkable_filtering_buffer_value.setChecked(bool(value))
    d.mQgsDoubleSpinBox_filtering_buffer_value.setValue(float(value))


def targets_ready(target_names):
    def done():
        d = dock()
        ids = {layer(name).id() for name in target_names if layer(name) is not None}
        return (ids and ids <= set(d.get_layers_to_filter() or [])
                and d.pushButton_checkable_filtering_layers_to_filter.isChecked()
                and d.pushButton_checkable_filtering_geometric_predicates.isChecked())
    return done


def run_task(name):
    dock().launchTaskEvent(False, name)


def subsets():
    """Subset string and number of features (counted, not the provider's cached count) of zones and pts."""
    return {name: (layer(name).subsetString(), sum(1 for _ in layer(name).getFeatures())) for name in ('zones', 'pts')}


# --- steps -------------------------------------------------------------------

def s_setup():
    iface.mainWindow().resize(1600, 1000)
    iface.mainWindow().show()
    STATE['pts_path'] = os.path.join(FIXTURES, 'lifecycle_pts.gpkg')
    write_points(STATE['pts_path'], POINTS)
    zones = QgsVectorLayer(M['zones'] + '|layername=zones', 'zones', 'ogr')
    zones_b = QgsVectorLayer(M['zones'] + '|layername=zones', 'zones_b', 'ogr')
    dem = QgsRasterLayer(M['dem'], 'dem', 'gdal')
    project.addMapLayers([zones, zones_b, dem])
    add_points_layer()
    iface.mapCanvas().setExtent(dem.extent())
    check('fixture layers load', all(layer(name).isValid() for name in ('zones', 'zones_b', 'dem', 'pts')),
          f"{POINTS} points")


def s_open_plugin():
    settings = QSettings()
    settings.setValue('FilterMate/discord_welcome_dismissed', True)
    settings.setValue('FilterMate/whats_new_seen', 99)
    settings.setValue('qgis/digitizing/validate_geometries', 0)
    plugins = os.path.join(tempfile.mkdtemp(prefix='fm_life_'), 'plugins')
    shutil.copytree(REPO, os.path.join(plugins, PACKAGE), ignore=shutil.ignore_patterns(*EXCLUDED))
    sys.path.insert(0, plugins)
    qgis.utils.plugin_paths.insert(0, plugins)
    qgis.utils.updateAvailablePlugins()
    started = qgis.utils.loadPlugin(PACKAGE) and qgis.utils.startPlugin(PACKAGE)
    check('plugin starts with iface', started and PACKAGE in qgis.utils.plugins)
    install_selection_probe()
    plugin().run()
    return lambda: dock() is not None and registered('zones', 'zones_b', 'dem', 'pts') and tasks_idle()


def install_selection_probe():
    """Count the calls of FilterMateDockWidget.on_layer_selection_changed, per dock (connections made from
    now on reach the counting method; the dock is not created yet)."""
    import importlib
    module = importlib.import_module(f'{PACKAGE}.filter_mate_dockwidget')
    cls = module.FilterMateDockWidget
    original = cls.on_layer_selection_changed
    calls = STATE.setdefault('selection_calls', {})

    def counted(self, *args):
        calls[id(self)] = calls.get(id(self), 0) + 1
        return original(self, *args)

    cls.on_layer_selection_changed = counted


def s_zones_current():
    STATE['first_dock'] = id(dock())
    dock().comboBox_filtering_current_layer.setLayer(layer('zones'))
    return current_is('zones')


def s_select_source():
    d = dock()
    d.mGroupBox_exploring_single_selection.setChecked(True)
    east_a = next(feature for feature in layer('zones').getFeatures() if feature['name'] == 'east_a')
    d.mFeaturePickerWidget_exploring_single_selection.setFeature(east_a.id())
    set_targets(['pts'])
    if not d.pushButton_checkable_filtering_geometric_predicates.isChecked():
        d.pushButton_checkable_filtering_geometric_predicates.setChecked(True)
    d.comboBox_filtering_geometric_predicates.setCheckedItems(['Intersect'])
    set_buffer(0)
    ready = targets_ready(['pts'])
    return lambda: bool(dock().get_current_features()[0]) and ready()


def filter_with_buffer(value):
    set_buffer(value)
    run_task('filter')


def s_reference_small():
    filter_with_buffer(0)
    return settled()


def s_reference_small_record():
    STATE['ref_small'] = subsets()
    print(f"   reference, buffer 0: {STATE['ref_small']['pts'][1]} points, subset "
          f"{STATE['ref_small']['pts'][0][:160]!r}", flush=True)
    run_task('reset')
    return settled()


def s_reference_large():
    filter_with_buffer(150)
    return settled()


def s_reference_large_record():
    STATE['ref_large'] = subsets()
    print(f"   reference, buffer 150: {STATE['ref_large']['pts'][1]} points", flush=True)
    check('the two reference filters differ', STATE['ref_small']['pts'] != STATE['ref_large']['pts'],
          f"{STATE['ref_small']['pts'][1]} vs {STATE['ref_large']['pts'][1]} points")
    run_task('reset')
    return settled()


def double_click(delay_ms):
    def step():
        STATE['criticals_before'] = len(STATE['criticals'])
        filter_with_buffer(0)
        first = app().appTasks.get('filter')
        STATE['double_first'] = first

        def second():
            try:
                STATE['first_status_at_second'] = first.status() if first is not None else None
            except RuntimeError:  # finished and deleted already
                STATE['first_status_at_second'] = 'finished'
            filter_with_buffer(150)

        if delay_ms:
            QTimer.singleShot(delay_ms, second)
        else:
            second()
        return settled_after(lambda: True, 3.0)
    step.__name__ = f"s_double_click_{delay_ms}ms"
    return step


def double_click_check(delay_ms):
    def step():
        now = subsets()
        first = STATE.get('double_first')
        try:
            first_canceled = first.isCanceled() if first is not None else None
        except RuntimeError:
            first_canceled = 'deleted'
        check(f"second click on Filter ({delay_ms} ms after the first): the second task's subsets",
              now == STATE['ref_large'],
              f"pts={now['pts'][1]} expected={STATE['ref_large']['pts'][1]} (first task status at the second "
              f"click={STATE.get('first_status_at_second')}, canceled={first_canceled}) "
              f"zones subset={now['zones'][0][:60]!r}")
        check(f"second click on Filter ({delay_ms} ms): no critical message",
              len(STATE['criticals']) == STATE['criticals_before'], '; '.join(STATE['criticals'][-2:]))
        run_task('reset')
        return settled()
    step.__name__ = f"s_double_click_{delay_ms}ms_check"
    return step


def s_prepare_targets():
    """pts again as the target (a removed and added again layer has a new id)."""
    set_targets(['pts'])
    return targets_ready(['pts'])


def remove_target_during_task(delay_ms):
    def step():
        STATE['criticals_before'] = len(STATE['criticals'])
        STATE['errors_before'] = len(STATE['python_errors'])
        filter_with_buffer(150)
        STATE['removed_task'] = app().appTasks.get('filter')
        pts_id = layer('pts').id()

        def remove():
            task = STATE['removed_task']
            try:
                STATE['removed_task_status'] = task.status() if task is not None else None
            except RuntimeError:  # finished and deleted already
                STATE['removed_task_status'] = 'finished'
            project.removeMapLayer(pts_id)

        if delay_ms:
            QTimer.singleShot(delay_ms, remove)
        else:
            remove()
        return settled_after(lambda: layer('pts') is None, 3.0)
    step.__name__ = f"s_remove_target_{delay_ms}ms"
    return step


def remove_target_check(delay_ms):
    def step():
        task = STATE.get('removed_task')
        try:
            canceled = task.isCanceled() if task is not None else None
        except RuntimeError:
            canceled = 'deleted'
        check(f"target removed {delay_ms} ms into a filter task: no critical message, no error",
              len(STATE['criticals']) == STATE['criticals_before']
              and len(STATE['python_errors']) == STATE['errors_before'],
              f"task status at the removal={STATE.get('removed_task_status')} canceled={canceled} "
              f"{'; '.join((STATE['criticals'] + STATE['python_errors'])[-2:])}")
        check(f"target removed {delay_ms} ms into a filter task: the panel takes layer changes again",
              not getattr(dock(), '_filtering_in_progress', False))
        run_task('reset')
        add_points_layer()
        return settled_after(lambda: registered('pts'))
    step.__name__ = f"s_remove_target_{delay_ms}ms_check"
    return step


def s_three_layer_changes():
    STATE['changes'] = ['pts', 'zones', 'zones_b']

    def change(index=0):
        if index < len(STATE['changes']):
            dock().comboBox_filtering_current_layer.setLayer(layer(STATE['changes'][index]))
            QTimer.singleShot(1500, lambda: change(index + 1))
        else:
            STATE['changes_done'] = True

    STATE['changes_done'] = False
    change()
    return settled_after(lambda: STATE['changes_done'] and getattr(dock().current_layer, 'name', lambda: None)()
                         == 'zones_b')


def _selection_calls():
    return STATE['selection_calls'].get(id(dock()), 0)


def _select_one(name):
    target = layer(name)
    fid = next(target.getFeatures()).id()
    before = _selection_calls()
    target.selectByIds([fid])
    target.removeSelection()
    return _selection_calls() - before  # two selection changes per layer


def s_selection_connections_check():
    probe = QgsVectorLayer(M['zones'] + '|layername=zones', 'probe', 'ogr')
    baseline = probe.receivers(probe.selectionChanged)
    receivers = {name: layer(name).receivers(layer(name).selectionChanged) for name in ('zones', 'pts', 'zones_b')}
    calls = {name: _select_one(name) for name in ('zones', 'pts', 'zones_b')}
    check('three layer changes: the current layer reaches the dock once per selection change',
          calls['zones_b'] == 2, f"calls={calls} receivers={receivers} (a never-current layer: {baseline})")
    check('three layer changes: the previous layers no longer reach the dock',
          calls['zones'] == 0 and calls['pts'] == 0, f"calls={calls}")
    return settled(1.0)


def s_unload_reload():
    old_app, old_dock = app(), dock()
    STATE['old_dock_id'] = id(old_dock)
    STATE['old_calls'] = {'save_project_variables': 0, 'current_layer_changed': 0}

    def counter(key, original):
        def counted(*args, **kwargs):
            STATE['old_calls'][key] += 1
            print(f"   unloaded instance called: {key}, from:\n" + ''.join(traceback.format_stack(limit=8)[:-1]),
                  flush=True)
            return original(*args, **kwargs)
        return counted

    old_app.save_project_variables = counter('save_project_variables', old_app.save_project_variables)
    old_dock.current_layer_changed = counter('current_layer_changed', old_dock.current_layer_changed)
    STATE['toolbars_before'] = len(toolbars())
    STATE['old_current'] = old_dock.current_layer
    qgis.utils.unloadPlugin(PACKAGE)
    STATE['calls_during_unload'] = dict(STATE['old_calls'])
    STATE['old_calls'] = {key: 0 for key in STATE['old_calls']}  # from now on QGIS must not call it
    since = time.time()
    return lambda: time.time() - since > 1.0


def s_unloaded_check():
    check('unload: the FilterMate toolbar leaves the main window', len(toolbars()) == 0,
          f"before={STATE['toolbars_before']} after={len(toolbars())}")
    project.setFileName(os.path.join(FIXTURES, 'lifecycle_renamed.qgz'))  # fileNameChanged
    iface.layerTreeView().setCurrentLayer(layer('pts'))  # currentLayerChanged
    old_current = STATE['old_current']
    try:
        before = STATE['selection_calls'].get(STATE['old_dock_id'], 0)
        old_current.selectByIds([next(old_current.getFeatures()).id()])
        old_current.removeSelection()
        selection_calls = STATE['selection_calls'].get(STATE['old_dock_id'], 0) - before
    except Exception as exc:
        selection_calls = f"not tested: {exc}"
    check('unload: QGIS no longer calls the unloaded instance',
          STATE['old_calls'] == {'save_project_variables': 0, 'current_layer_changed': 0} and selection_calls == 0,
          f"calls={STATE['old_calls']} selectionChanged={selection_calls} "
          f"(during the unload itself: {STATE['calls_during_unload']})")
    started = qgis.utils.loadPlugin(PACKAGE) and qgis.utils.startPlugin(PACKAGE)
    check('plugin starts again after the unload', started)
    plugin().run()
    return lambda: dock() is not None and registered('zones', 'zones_b', 'dem', 'pts') and tasks_idle()


def s_reloaded_check():
    check('reload: one FilterMate toolbar', len(toolbars()) == 1, f"toolbars={len(toolbars())}")
    return settled()


def press(key):
    from qgis.PyQt.QtCore import QEvent
    from qgis.PyQt.QtGui import QKeyEvent
    from qgis.PyQt.QtWidgets import QApplication
    QApplication.sendEvent(dock().comboBox_filtering_current_layer,
                           QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier))


def pick_then_refresh(round_index):
    def step():
        combo = dock().comboBox_filtering_current_layer
        before = combo.currentLayer()
        for key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
            press(key)
            if combo.currentLayer() is not None and combo.currentLayer() is not before:
                break
        picked = combo.currentLayer().name() if combo.currentLayer() else None
        delay = random.Random(round_index).choice([0, 50, 200, 500])

        def refresh():
            shown_before = getattr(dock(), 'current_layer', None)
            app()._refresh_ui_with_layers()
            shown = getattr(dock(), 'current_layer', None)
            STATE['late_refresh'].append((picked, delay, shown_before.name() if shown_before else None,
                                          shown.name() if shown else None))

        QTimer.singleShot(delay, refresh)
        since = time.time()
        return settled_after(lambda: time.time() - since > delay / 1000.0 + 0.3, 1.5)
    step.__name__ = f"s_pick_then_refresh_{round_index}"
    return step


class _DebugLines(logging.Handler):
    """The FilterMate.App DEBUG lines of a round (why a layer change was skipped / deferred)."""

    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.lines = []

    def emit(self, record):
        message = record.getMessage()
        if any(word in message for word in ('ENTRY', 'Flags:', 'skipping', 'deferring', 'BLOCKED', 'blocked',
                                            'Deferring', 'UI refreshed')):
            self.lines.append(f"{record.created - STATE['started']:7.2f} {message[:160]}")


def pick_after_safety_refresh(round_index):
    """The CI failure of run_gui_smoke (QGIS nightly, 2026-10-17): the start-up safety refresh
    (AppInitializer._ensure_ui_enabled_after_startup, 5 s after run()) deferred a layer change of the
    QGIS active layer (the panel was busy), replayed 150 ms later; the user's pick came right after and
    the panel kept the active layer. The same sequence, the pick at several delays after the refresh."""
    def step():
        delay = (0, 100, 160, 190, 220, 300)[round_index % 6]
        handler = STATE.setdefault('debug_handler', _DebugLines())
        app_logger = logging.getLogger('FilterMate.App')
        if handler not in app_logger.handlers:
            app_logger.addHandler(handler)
        STATE['saved_level'] = app_logger.level
        app_logger.setLevel(logging.DEBUG)
        handler.lines = []
        # QGIS' active layer and the panel's: pts; the layer above it in the combo box is the raster dem
        iface.setActiveLayer(layer('pts'))
        dock().comboBox_filtering_current_layer.setLayer(layer('pts'))
        initializer = getattr(app(), '_app_initializer', None)

        def pick():
            combo = dock().comboBox_filtering_current_layer
            before = combo.currentLayer()
            for key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                press(key)
                if combo.currentLayer() is not None and combo.currentLayer() is not before:
                    break
            picked = combo.currentLayer().name() if combo.currentLayer() else None

            def refresh():
                shown_before = getattr(dock(), 'current_layer', None)
                app()._refresh_ui_with_layers()
                shown = getattr(dock(), 'current_layer', None)
                entry = (picked, delay, shown_before.name() if shown_before else None, shown.name() if shown else None)
                STATE['safety_rounds'].append(entry)
                if entry[0] != entry[3] or entry[0] != entry[2]:
                    trace = '\n'.join(f"   | {line}" for line in handler.lines[-40:])
                    print(f"   round {round_index}: {entry}\n{trace}", flush=True)
                app_logger.setLevel(STATE['saved_level'])

            QTimer.singleShot(500, refresh)

        def start():
            if initializer is not None:
                initializer._ensure_ui_enabled_after_startup()
            QTimer.singleShot(delay, pick)

        QTimer.singleShot(2600, start)  # once the layer change above is over
        since = time.time()
        return settled_after(lambda: time.time() - since > 2.6 + delay / 1000.0 + 0.8, 1.0)
    step.__name__ = f"s_pick_after_safety_refresh_{round_index}"
    return step


def s_safety_refresh_report():
    rounds = STATE['safety_rounds']
    wrong = [entry for entry in rounds if entry[0] != entry[2] or entry[0] != entry[3]]
    check(f"a pick right after the start-up safety refresh is applied and kept ({len(rounds)} rounds)",
          rounds and not wrong, f"(picked, delay ms, panel before the refresh, panel after) wrong={wrong}")


def s_late_refresh_report():
    rounds = STATE['late_refresh']
    wrong = [entry for entry in rounds if entry[0] != entry[3]]
    check(f"a late refresh keeps the layer the user picked ({len(rounds)} rounds)", rounds and not wrong,
          f"(picked, delay ms, panel before, panel after) wrong={wrong}")


def s_finish():
    check('no Python error and no FilterMate critical message in the log', not STATE['python_errors'],
          '; '.join(STATE['python_errors'][:3]))
    counts = {status: sum(1 for s, _ in STATE['results'] if s == status) for status in ('PASS', 'FAIL')}
    print(f"\n{counts['PASS']} passed, {counts['FAIL']} failed in {time.time() - STATE['started']:.1f}s "
          f"(QGIS {Qgis.QGIS_VERSION}, lifecycle)", flush=True)
    failed = [name for status, name in STATE['results'] if status == 'FAIL']
    if failed:
        print('FAILED: ' + '; '.join(failed), flush=True)
    os._exit(1 if failed else 0)


STATE['late_refresh'] = []
STATE['safety_rounds'] = []
STEPS = ([s_setup, s_open_plugin, s_zones_current, s_select_source,
          s_reference_small, s_reference_small_record, s_reference_large, s_reference_large_record]
         + [step for delay in (0, 30, 150) for step in (double_click(delay), double_click_check(delay))]
         + [step for delay in (0, 100)
            for step in (s_prepare_targets, remove_target_during_task(delay), remove_target_check(delay))]
         + [s_three_layer_changes, s_selection_connections_check, s_unload_reload, s_unloaded_check,
            s_reloaded_check]
         + [pick_then_refresh(index) for index in range(REPEATS)]
         + [s_late_refresh_report]
         + [pick_after_safety_refresh(index) for index in range(2 * 6)]
         + [s_safety_refresh_report, s_finish])
if os.environ.get('FM_LIFECYCLE_ONLY') == 'pick':  # the layer pick rounds alone (faster to iterate)
    STEPS = ([s_setup, s_open_plugin, s_zones_current] + [pick_then_refresh(index) for index in range(REPEATS)]
             + [s_late_refresh_report] + [pick_after_safety_refresh(index) for index in range(2 * 6)]
             + [s_safety_refresh_report, s_finish])


def run_step(index=0):
    watch_plugin_loggers()
    step = STEPS[index]
    print(f"-- {step.__name__} ({time.time() - STATE['started']:.1f}s)", flush=True)
    try:
        until = step()
    except Exception:
        report('FAIL', f"{step.__name__} raised", traceback.format_exc().strip().splitlines()[-1])
        print(traceback.format_exc(), flush=True)
        until = None
        if step in (s_setup, s_open_plugin):
            QTimer.singleShot(0, lambda: run_step(STEPS.index(s_finish)))
            return
    wait(index, until, time.time())


def wait(index, until, since):
    if until is not None:
        try:
            done = until()
        except Exception:
            done = False
        if not done and time.time() - since < STEP_TIMEOUT:
            QTimer.singleShot(250, lambda: wait(index, until, since))
            return
        if not done:
            print(f"   (timeout after {STEP_TIMEOUT:.0f}s waiting at the end of {STEPS[index].__name__})", flush=True)
    QTimer.singleShot(300, lambda: run_step(index + 1))


QTimer.singleShot(2000, run_step)
