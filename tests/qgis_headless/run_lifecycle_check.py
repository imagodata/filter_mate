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
  (``run_gui_smoke.py`` "a late refresh keeps the layer the user picked", repeated);
- the plugin unloaded with AGENT, FILTERING and EXPLORING in their own panels: the sections come back while the
  controllers are up, no panel and no "FilterMate: " action of the menu of the panels left, the saved panels
  kept, nothing critical or raised; loaded again, one panel per group, one F5 per panel, one ``launchingTask``
  per click on Filter; the dock closed with them apart: they are hidden and their entries of View > Panels are off
  until it is shown again (``FM_LIFECYCLE_ONLY=panels`` runs this group alone);
- a project opened while the plugin runs: the whole layer change runs at most twice for the layer shown
  (``FM_LIFECYCLE_ONLY=open``, which prints each caller and the log of the chain);
- the plugin unloaded with EXPLORING apart and a GeoPackage layer in its feature picker: no gather starts while it
  unloads (no PostgreSQL case: no server in the headless images).

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


def raster_picked_before_registration(round_index):
    """A raster added to the project and picked in the combo box at once, before add_layers registered it:
    once registered it must be the panel's layer, with the raster page (2026-10-17 review: it never was)."""
    def step():
        dock().comboBox_filtering_current_layer.setLayer(layer('zones'))
        name = f"dem_new_{round_index}"
        STATE['await_name'] = name

        def add_and_pick():
            raster = QgsRasterLayer(M['dem'], name, 'gdal')
            project.addMapLayer(raster)
            combo = dock().comboBox_filtering_current_layer
            combo.setLayer(raster)  # the user's pick, right away
            STATE['await_registered_at_pick'] = registered(name)
            controller = dock()._controller_integration.coverage_controller
            STATE['await_after_pick'] = (combo.currentLayer().name() if combo.currentLayer() else None,
                                         getattr(controller, '_awaiting_registration', None))

        QTimer.singleShot(2600, add_and_pick)  # once the change to zones is over
        since = time.time()
        return settled_after(lambda: time.time() - since > 2.8 and registered(name), 2.5)
    step.__name__ = f"s_raster_picked_before_registration_{round_index}"
    return step


def raster_picked_before_registration_check(round_index):
    def step():
        name = STATE['await_name']
        controller = dock()._controller_integration.coverage_controller
        active = controller.active_layer
        current = getattr(dock(), 'current_layer', None)
        check(f"a raster picked before its registration is shown once registered ({round_index})",
              active is not None and active.name() == name and current is not None and current.name() == name,
              f"registered at the pick={STATE['await_registered_at_pick']} (combo, awaited) after the pick="
              f"{STATE['await_after_pick']} awaited now={getattr(controller, '_awaiting_registration', None)} "
              f"coverage page="
              f"{active.name() if active else None} panel={current.name() if current else None}")
        return settled(1.0)
    step.__name__ = f"s_raster_picked_before_registration_{round_index}_check"
    return step


PANEL_PREFIX = 'FilterMatePanel_'
APART = ('agent', 'filtering', 'exploring')


def section_panels():
    """The ``QDockWidget`` panels of FilterMate in the main window of QGIS."""
    from qgis.PyQt.QtWidgets import QDockWidget
    found = []
    for widget in iface.mainWindow().findChildren(QDockWidget):
        try:
            if widget.objectName().startswith(PANEL_PREFIX):
                found.append(widget)
        except RuntimeError:
            continue
    return found


def panel_menu_actions():
    """The actions "FilterMate: ..." of View > Panels of QGIS: [(text, enabled)]."""
    from qgis.PyQt.QtWidgets import QMenu
    menu = iface.mainWindow().findChild(QMenu, 'mPanelMenu')
    if menu is None:
        return None
    return [(action.text(), action.isEnabled()) for action in menu.actions() if action.text().startswith('FilterMate: ')]


def f5_shortcuts(panel):
    from qgis.PyQt.QtGui import QKeySequence
    try:
        from qgis.PyQt.QtGui import QShortcut
    except ImportError:  # QGIS < 3.34.2 (Qt5)
        from qgis.PyQt.QtWidgets import QShortcut
    return [shortcut for shortcut in panel.findChildren(QShortcut) if shortcut.key() == QKeySequence('F5')]


def s_panels_detach():
    """AGENT, FILTERING and EXPLORING in their own panels, the way run_gui_smoke does it."""
    panels = dock()._fm_panels
    took = {key: panels.detach(key) for key in APART if panels.can_detach(key)}
    STATE['panels_saved'] = QSettings().value('FilterMate/panels/detached')
    STATE['panels_groups'] = panels.groups()
    since = time.time()
    return lambda: time.time() - since > 2.0 and len(section_panels()) >= len(took)


def s_panels_detach_check():
    panels = dock()._fm_panels
    check('panels: AGENT, FILTERING and EXPLORING are in their own panels', set(panels.detached()) == set(APART)
          and len(section_panels()) == len(APART), f"apart={panels.detached()} panels={len(section_panels())}")
    return settled(1.0)


def install_unload_probe():
    """Record what the dock does while the plugin unloads, and whether its controllers were already torn down
    (FilterMate.unload tears them down before the sections come back to the dock): a change of the open page of
    the tool box, and undoRedoStateRequested (select_tabTools_index emits it). Connected to the instance: a class
    patch would not reach the slots already connected."""
    d = dock()
    STATE['dock_calls'] = []

    def note(name):
        integration = getattr(d, '_controller_integration', None)
        up = integration is not None and getattr(integration, '_is_setup', True)
        STATE['dock_calls'].append((name, 'controllers up' if up else 'controllers torn down'))

    d.toolBox_tabTools.currentChanged.connect(lambda *_args: note('toolbox currentChanged'))
    d.undoRedoStateRequested.connect(lambda *_args: note('undoRedoStateRequested'))


def s_panels_unload():
    STATE['panel_errors_before'] = len(STATE['python_errors'])
    STATE['panel_criticals_before'] = len(STATE['criticals'])
    install_unload_probe()
    qgis.utils.unloadPlugin(PACKAGE)
    since = time.time()
    return lambda: time.time() - since > 2.0  # the event loop runs: deleteLater, queued signals, singleShots


def s_panels_unloaded_check():
    left = [panel.objectName() for panel in section_panels()]
    actions = panel_menu_actions()
    check('panels unload: no panel of FilterMate is left in the main window', not left, str(left))
    check('panels unload: no "FilterMate: " action is left in the menu of the panels', actions == [], str(actions))
    check('panels unload: the saved panels are unchanged (they come back at the next load)',
          QSettings().value('FilterMate/panels/detached') == STATE['panels_saved'],
          f"before={STATE['panels_saved']!r} after={QSettings().value('FilterMate/panels/detached')!r}")
    late = [call for call in STATE['dock_calls'] if call[1] != 'controllers up']
    check('panels unload: the sections come back while the controllers are still up (nothing runs on a dock '
          'already torn down)', not late, f"calls during the unload: {STATE['dock_calls']}")
    check('panels unload: no critical message and no Python error',
          len(STATE['python_errors']) == STATE['panel_errors_before']
          and len(STATE['criticals']) == STATE['panel_criticals_before'],
          '; '.join((STATE['python_errors'][STATE['panel_errors_before']:]
                     + STATE['criticals'][STATE['panel_criticals_before']:])[:3]))
    started = qgis.utils.loadPlugin(PACKAGE) and qgis.utils.startPlugin(PACKAGE)
    check('panels unload: the plugin starts again', started)
    install_manage_task_probe()  # before run(): the dock's signal connects to the method as it is then
    plugin().run()
    return lambda: (dock() is not None and registered('zones', 'zones_b', 'dem', 'pts') and tasks_idle()
                    and len(section_panels()) >= len(STATE['panels_groups']))


def s_panels_reload_check():
    panels = dock()._fm_panels
    found = section_panels()
    names = [panel.objectName() for panel in found]
    check('panels reload: one panel per group, as before', len(found) == len(set(names))
          and panels.groups() == STATE['panels_groups'],
          f"before={STATE['panels_groups']} after={panels.groups()} panels={names}")
    counts = {panel.objectName(): len(f5_shortcuts(panel)) for panel in found}
    check('panels reload: one F5 shortcut per panel', found and all(count == 1 for count in counts.values()),
          str(counts))
    actions = panel_menu_actions()
    check('panels reload: one "FilterMate: " action per panel in the menu of the panels',
          actions is not None and len(actions) == len(found) and all(on for _text, on in actions), str(actions))
    return settled(1.0)


def s_panels_filter_ready():
    return s_select_source()


def install_manage_task_probe():
    """Count the calls of FilterMateApp.manage_task (what launchingTask is connected to), per name."""
    import importlib
    cls = importlib.import_module(f'{PACKAGE}.filter_mate_app').FilterMateApp
    original = cls.manage_task
    STATE['managed'] = []

    def counted(self, task_name, *args, **kwargs):
        STATE['managed'].append(task_name)
        return original(self, task_name, *args, **kwargs)

    cls.manage_task = counted


def s_panels_click_filter():
    """A click on Filter of the reloaded panel: one emission of launchingTask, one task launched."""
    d = dock()
    STATE['launches'] = []
    STATE['managed'] = []
    d.launchingTask.connect(lambda name: STATE['launches'].append(name))
    d.pushButton_action_filter.click()
    return settled_after(lambda: True, 3.0)


def s_panels_click_filter_check():
    check('panels reload: a click on Filter emits launchingTask once and launches one task',
          STATE['launches'] == ['filter'] and STATE['managed'] == ['filter'],
          f"launchingTask={STATE['launches']} manage_task={STATE['managed']}")
    run_task('reset')
    return settled()


def s_panels_close_dock():
    """The dock closed with a section apart: what its panels offer in the menu of the panels."""
    STATE['close_before'] = panel_menu_actions()
    dock().close()
    since = time.time()
    return lambda: time.time() - since > 1.0


def s_panels_close_dock_check():
    from qgis.PyQt.QtWidgets import QMenu
    actions = panel_menu_actions()
    hidden = [panel.objectName() for panel in section_panels() if not panel.isVisible()]
    check('dock closed: its panels are hidden', len(hidden) == len(section_panels()) > 0,
          f"hidden={hidden} of {len(section_panels())}; layer chooser={dock().comboBox_filtering_current_layer.currentLayer()}")
    check('dock closed: the panel actions of the menu of the panels are off',
          bool(actions) and not any(on for _text, on in actions), f"before={STATE['close_before']} now={actions}")
    # What a user does: View > Panels > "FilterMate: ..." on a panel hidden with the dock. A menu never runs a
    # disabled entry (QAction.trigger() does, in Qt5), so only the enabled ones are triggered.
    menu = iface.mainWindow().findChild(QMenu, 'mPanelMenu')
    triggered = [action for action in menu.actions() if action.text().startswith('FilterMate: ') and action.isEnabled()]
    for action in triggered:
        action.trigger()
    shown = [panel.objectName() for panel in section_panels() if panel.isVisible()]
    check('dock closed: triggering a panel action does not bring a panel back while the dock is closed',
          not shown, f"visible now={shown} dock visible={dock().isVisible()} "
          f"combo layer={dock().comboBox_filtering_current_layer.currentLayer()}")
    return settled(0.5)


def s_panels_reopen_dock():
    plugin().run()
    since = time.time()
    return lambda: time.time() - since > 1.5


def s_panels_reopen_dock_check():
    actions = panel_menu_actions()
    shown = [panel.objectName() for panel in section_panels() if panel.isVisible()]
    check('dock reopened: the panels are shown and their actions on again',
          len(shown) == len(section_panels()) > 0 and bool(actions) and all(on for _text, on in actions),
          f"visible={shown} actions={actions}")
    return settled(1.0)


def s_project_save():
    """A project file with the fixture layers (the one open now), saved for the next step."""
    STATE['project_path'] = os.path.join(FIXTURES, 'lifecycle_open.qgz')
    project.setFileName(STATE['project_path'])
    project.write()
    return settled(1.0)


def install_layer_change_probe():
    """The calls of FilterMateDockWidget.current_layer_changed from now on, with their callers (slots look the
    method up when they run: a class patch reaches them)."""
    import importlib
    cls = importlib.import_module(f'{PACKAGE}.filter_mate_dockwidget').FilterMateDockWidget
    original = cls.current_layer_changed
    STATE['layer_changes'] = []
    STATE['chain_log'] = []
    words = ('current_layer_changed ENTRY', 'current_layer_changed SUCCESS', 'New project loaded', 'Refreshing UI with',
             'UI refreshed with', 'Already updating', 'deferring', 'Deferring', 'BLOCKED', 'blocked', 'Reinitializing',
             'project_read', 'current_layer_changed:', 'unregistered', 'awaiting', 'Skipping', 'skipping',
             'same layer', 'already current', 'Safety timer')

    class Chain(logging.Handler):
        def emit(self, record):
            message = record.getMessage()
            if any(word in message for word in words):
                STATE['chain_log'].append(f"{record.created - STATE['started']:7.2f}s {message.splitlines()[0][:150]}")

    for name in ('FilterMate.App', 'FilterMate.LayerTaskCompletionHandler'):
        logging.getLogger(name).addHandler(Chain(level=logging.DEBUG))
        logging.getLogger(name).setLevel(logging.DEBUG)

    def counted(self, layer, *args, **kwargs):
        frames = [f"{os.path.basename(f.filename)}:{f.lineno} {f.name}" for f in traceback.extract_stack()[:-1]]
        useful = [f for f in frames if 'filter_mate' in f or 'dockwidget' in f or 'app' in f][-4:]
        STATE['layer_changes'].append((round(time.time() - STATE['started'], 2), layer.name() if layer else None,
                                       kwargs, useful))
        return original(self, layer, *args, **kwargs)

    cls.current_layer_changed = counted


def s_project_reopen():
    """Open the saved project in the running QGIS (File > Open): how many times the layer change runs."""
    install_layer_change_probe()
    iface.addProject(STATE['project_path'])
    return settled_after(lambda: registered('zones', 'zones_b', 'dem', 'pts'), 4.0)


def s_project_reopen_report():
    changes = STATE['layer_changes']
    print(f"   current_layer_changed calls after opening the project: {len(changes)}", flush=True)
    for when, name, kwargs, callers in changes:
        print(f"   {when:7.2f}s {name} {kwargs}\n      from: " + ' <- '.join(reversed(callers)), flush=True)
    print("   the plugin log of the chain:\n" + '\n'.join(f"      {line}" for line in STATE['chain_log']), flush=True)
    log = STATE['chain_log']
    opened = next((index for index, line in enumerate(log) if 'Disconnecting old layer store' in line), 0)
    passes = sum('current_layer_changed SUCCESS' in line for line in log[opened:])  # after the project was read
    # Two are the work: the result of add_layers shows the layer, then the refresh of the panel after the project
    # was read. The replays of the requests deferred while the panel was busy made it three to four (5.1.1 log: three
    # in a second, 131 + 47 + 49 ms).
    check('opening a project: the whole layer change runs at most twice for the layer shown',
          0 < passes <= 2, f"{passes} full change(s); {len(changes)} call(s) reached current_layer_changed")
    return settled(0.5)


def s_picker_prepare():
    """EXPLORING in its own panel with a layer and a feature in its feature picker (a GeoPackage layer)."""
    d = dock()
    d._fm_panels.attach_all()  # the sections apart of an earlier group go back
    d.mGroupBox_exploring_single_selection.setChecked(True)
    east_a = next(feature for feature in layer('zones').getFeatures() if feature['name'] == 'east_a')
    picker = d.mFeaturePickerWidget_exploring_single_selection
    picker.setFeature(east_a.id())
    took = d._fm_panels.detach('exploring')
    STATE['picker_case'] = (bool(took), picker.layer() is not None)
    since = time.time()
    return lambda: time.time() - since > 2.0 and tasks_idle()


def s_picker_unload():
    """Unload with it: no gather of the feature picker may start while the plugin unloads (a gather that ends
    after the unload crashed QGIS on 2026-09-14, QgsFeaturePickerModelBase::endUpdate)."""
    from qgis.PyQt.QtWidgets import QComboBox
    d = dock()
    picker = d.mFeaturePickerWidget_exploring_single_selection
    # the model of the picker is the one of its inner combo box (it is no child of the widget)
    models = [box.model() for box in picker.findChildren(QComboBox) if hasattr(box.model(), 'isLoadingChanged')]
    STATE['gathers'] = []
    STATE['picker_models'] = len(models)
    for model in models:
        model.isLoadingChanged.connect(lambda m=model: STATE['gathers'].append(m.isLoading()))
    picker.modelUpdated.connect(lambda *_args: STATE['gathers'].append('modelUpdated'))
    STATE['picker_errors_before'] = len(STATE['python_errors'])
    qgis.utils.unloadPlugin(PACKAGE)
    since = time.time()
    return lambda: time.time() - since > 3.0


def s_picker_unload_check():
    check('unload with EXPLORING apart and a layer in its feature picker: the case is set up',
          STATE['picker_case'] == (True, True) and STATE['picker_models'] > 0,
          f"(panel made, picker has a layer)={STATE['picker_case']} models watched={STATE['picker_models']}")
    started = list(STATE['gathers'])  # a gather starting (isLoading) or ending (modelUpdated)
    check('unload with EXPLORING apart and a layer in its feature picker: no gather starts while it unloads',
          not started, f"{len(started)} gather(s) started, loading changes={STATE['gathers']}")
    check('unload with EXPLORING apart and a layer in its feature picker: no panel and no error left',
          not section_panels() and len(STATE['python_errors']) == STATE['picker_errors_before'],
          '; '.join(STATE['python_errors'][STATE['picker_errors_before']:][:2]))
    started = qgis.utils.loadPlugin(PACKAGE) and qgis.utils.startPlugin(PACKAGE)
    check('unload with EXPLORING apart: the plugin starts again', started)
    plugin().run()
    return lambda: dock() is not None and registered('zones', 'zones_b', 'dem', 'pts') and tasks_idle()


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
         + [s_safety_refresh_report]
         + [step for index in range(3)
            for step in (raster_picked_before_registration(index), raster_picked_before_registration_check(index))]
         + [s_zones_current, s_picker_prepare, s_picker_unload, s_picker_unload_check,
            s_zones_current, s_panels_detach, s_panels_detach_check, s_panels_unload, s_panels_unloaded_check,
            s_panels_reload_check, s_zones_current, s_panels_filter_ready, s_panels_click_filter,
            s_panels_click_filter_check,
            s_panels_close_dock, s_panels_close_dock_check, s_panels_reopen_dock, s_panels_reopen_dock_check]
         + [s_finish])
if os.environ.get('FM_LIFECYCLE_ONLY') == 'panels':  # the sections apart, unload and closed dock alone
    STEPS = ([s_setup, s_open_plugin, s_zones_current, s_picker_prepare, s_picker_unload, s_picker_unload_check,
              s_zones_current, s_panels_detach, s_panels_detach_check, s_panels_unload, s_panels_unloaded_check,
              s_panels_reload_check, s_zones_current, s_panels_filter_ready, s_panels_click_filter,
              s_panels_click_filter_check, s_panels_close_dock, s_panels_close_dock_check, s_panels_reopen_dock, s_panels_reopen_dock_check,
              s_finish])
if os.environ.get('FM_LIFECYCLE_ONLY') == 'open':  # a project opened while the plugin runs
    STEPS = [s_setup, s_open_plugin, s_zones_current, s_project_save, s_project_reopen, s_project_reopen_report,
             s_finish]
if os.environ.get('FM_LIFECYCLE_ONLY') == 'await':  # the raster picked before its registration alone
    STEPS = ([s_setup, s_open_plugin, s_zones_current]
             + [step for index in range(3)
                for step in (raster_picked_before_registration(index), raster_picked_before_registration_check(index))]
             + [s_finish])
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
