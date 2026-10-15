# -*- coding: utf-8 -*-
"""
FilterMate dock smoke test in a real QGIS with its GUI (CI: official qgis/qgis Docker images under Xvfb).

``run_smoke.py`` covers the engine (Processing, ``qgis_process``); this script covers the dock on
the same synthetic data: the plugin is started with ``iface``, the dock opened, then every layer
kind is used as the current layer and filtered through the dock's own widgets, the way a user
does it. QGIS runs the script at startup (``--code``) and the script quits QGIS with its exit
code (1 when a check fails):

    python3 tests/qgis_headless/make_fixtures.py /tmp/fm
    FM_FIXTURES=/tmp/fm xvfb-run -a qgis --nologo --noversioncheck --profiles-path /tmp/profiles \\
        --code tests/qgis_headless/run_gui_smoke.py

Prints one ``PASS`` / ``FAIL`` / ``SKIP`` / ``XFAIL`` line per check, like ``run_smoke.py``.
"""
import faulthandler
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

from qgis.core import Qgis, QgsApplication, QgsProject, QgsProviderRegistry, QgsRasterLayer, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings, Qt, QTimer
from qgis.utils import iface
import qgis.utils

STATE = {'results': [], 'python_errors': [], 'started': time.time()}
faulthandler.enable(all_threads=True)  # a native crash prints the Python stack of every thread


def _show_exception(type_, value, tb, msg=None, messagebar=False, level=None):
    """qgis.utils.showException opens a modal dialog that would block the run: record and print instead."""
    text = ''.join(traceback.format_exception(type_, value, tb)).strip()
    STATE['python_errors'].append(f"{msg or ''} {text.splitlines()[-1] if text else value}".strip())
    print(f"   [Python exception] {msg or ''}\n{text}", flush=True)


qgis.utils.showException = _show_exception


def _watchdog():
    print('FAIL   watchdog: the run did not finish in 12 minutes', flush=True)
    os._exit(2)


QTimer.singleShot(12 * 60 * 1000, _watchdog)  # before the outer `timeout 900` of the CI step

# QGIS < 3.28 runs --code with exec() and no __file__: FM_REPO (default /src, the CI mount) then.
REPO = os.environ.get('FM_REPO') or (os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                     if '__file__' in globals() else '/src')
PACKAGE = 'filter_mate'
EXCLUDED = ('.git', '.github', '.claude', '.serena', '_bmad', '_bmad-output', 'dist', 'build', 'scripts',
            'knowledge', 'website', 'tests', 'docs', 'logs', '__pycache__', '*.pyc', 'test_*.py')
POINT_CLOUD_MIN_VERSION = 32600  # core/domain/point_cloud_support.py
FIXTURES = os.environ.get('FM_FIXTURES', '/tmp/fm')
STEP_TIMEOUT = float(os.environ.get('FM_STEP_TIMEOUT', '60'))

try:
    with open(os.path.join(FIXTURES, 'manifest.json'), encoding='utf-8') as _stream:
        M = json.load(_stream)
except Exception as _exc:  # never leave QGIS waiting on an error dialog in CI
    print(f"FAIL   fixtures not readable in {FIXTURES}: {_exc} (run make_fixtures.py first)", flush=True)
    os._exit(3)
project = QgsProject.instance()


def report(status, name, detail=''):
    STATE['results'].append((status, name))
    print(f"{status:<5}  {name}  {detail}".rstrip(), flush=True)


def check(name, condition, detail='', expected_failure=''):
    if condition:
        report('PASS', name, detail)
    elif expected_failure:
        report('XFAIL', name, f"{detail} | known: {expected_failure}")
    else:
        report('FAIL', name, detail)
    return bool(condition)


def _on_log(message, tag, level):
    if tag == 'Python error' or (tag == 'FilterMate' and level == Qgis.MessageLevel.Critical):
        STATE['python_errors'].append(f"[{tag}] {message[:400]}")
        print(f"   [QGIS log {tag}] {message[:400]}", flush=True)


QgsApplication.messageLog().messageReceived.connect(_on_log)


class _ErrorRecords(logging.Handler):
    """FilterMate logs with the logging module (stderr + filtermate.log, propagate=False), not QgsMessageLog."""

    def emit(self, record):
        STATE['python_errors'].append(f"[{record.name}] {record.getMessage()[:400]}")


_ERRORS = _ErrorRecords(level=logging.ERROR)


class _RecentRecords(logging.Handler):
    """The last FilterMate messages at INFO and above, printed when a check fails."""

    def __init__(self):
        super().__init__(level=logging.INFO)
        self.lines = []

    def emit(self, record):
        self.lines = (self.lines + [f"{record.levelname[0]} {record.name}: {record.getMessage()[:220]}"])[-600:]


_RECENT = _RecentRecords()


def dump_recent(count=40, keywords=('FM5', 'overage', 'ross', 'BLOCKED', 'DEFERRED', 'raster', 'Raster', 'target')):
    """The last FilterMate messages about raster / point cloud targets and blocked tasks."""
    lines = [line for line in _RECENT.lines if any(word in line for word in keywords)]
    for line in dict.fromkeys(lines[-count:]):  # a logger with two handlers prints twice
        print(f"   | {line}", flush=True)


def watch_plugin_loggers():
    """Hook every FilterMate logger created so far (each one has its own handlers, no propagation)."""
    for name, logger in list(logging.root.manager.loggerDict.items()):
        if isinstance(logger, logging.Logger) and name.split('.')[0] in ('FilterMate', 'filter_mate') \
                and _ERRORS not in logger.handlers:
            logger.addHandler(_ERRORS)
            logger.addHandler(_RECENT)
            if logger.level > logging.INFO or logger.level == logging.NOTSET:
                logger.setLevel(logging.INFO)


# --- helpers -------------------------------------------------------------

def app():
    import qgis.utils
    return qgis.utils.plugins[PACKAGE].app


def dock():
    return app().dockwidget


def coverage():
    return dock()._controller_integration.coverage_controller


def layer(name):
    found = project.mapLayersByName(name)
    return found[0] if found else None


def names(vector_layer):
    return sorted(feature['name'] for feature in vector_layer.getFeatures())


def has_point_clouds():
    return Qgis.QGIS_VERSION_INT >= POINT_CLOUD_MIN_VERSION


def can_clip_point_clouds():
    """A clip needs pdal >= 2.4 on PATH, or a QGIS able to open the LAS written by its own exporter."""
    if 'pdal' in QgsProviderRegistry.instance().providerList():
        return True
    exe = shutil.which('pdal')
    if not exe:
        return False
    out = subprocess.run([exe, '--drivers'], capture_output=True, text=True, timeout=120).stdout
    return 'writers.copc' in out


def subset_issue():
    """QGIS >= 3.44 point cloud identify() ignores the subset string now and then (see run_smoke.py)."""
    return ('QGIS point cloud identify() ignored the subset string (statistics task / block cache issue)'
            if Qgis.QGIS_VERSION_INT >= 34400 else '')


def combo_items():
    combo = dock().checkableComboBoxLayer_filtering_layers_to_filter
    return [combo.model().item(row).text() for row in range(combo.model().rowCount())]


def set_targets(target_names):
    combo = dock().checkableComboBoxLayer_filtering_layers_to_filter
    model = combo.model()
    for row in range(model.rowCount()):
        item = model.item(row)
        wanted = any(item.text().startswith(name + ' [') for name in target_names)
        item.setCheckState(Qt.CheckState.Checked if wanted else Qt.CheckState.Unchecked)
    button = dock().pushButton_checkable_filtering_layers_to_filter
    if not button.isChecked():
        button.setChecked(True)


def set_predicates(labels):
    d = dock()
    if not d.pushButton_checkable_filtering_geometric_predicates.isChecked():
        d.pushButton_checkable_filtering_geometric_predicates.setChecked(True)
    d.comboBox_filtering_geometric_predicates.setCheckedItems(labels)


def run_task(name):
    dock().launchTaskEvent(False, name)


def tasks_idle():
    """No FilterMate task running: cross filters ("FilterMate: ...") and the app tasks (add / remove
    layers, filter, unfilter, undo...), whose descriptions are FilterMateApp.tasks_descriptions."""
    try:
        own = set(app().tasks_descriptions.values())
    except Exception:
        own = set()
    return not [task for task in QgsApplication.taskManager().activeTasks()
                if task.description().startswith('FilterMate') or task.description() in own]


def settled():
    """Condition: the post-filter window is over. For about 2 s after a filter / undo / unfilter the dock
    puts the source layer back in the current-layer combo box (adapters/undo_redo_handler.py,
    filter_result_handler.py): a layer chosen in that window is reverted."""
    since = time.time()
    return lambda: tasks_idle() and time.time() - since > 2.5


def switched_to(name, coverage_page):
    """Condition after a current-layer change: ``name`` is current with its EXPLORING page, and the dock's
    delayed restore of that layer's FILTERING settings is over (it overwrites targets / predicates / buttons
    set in the meantime: found by this test, ``run_vector_source_task`` then got no target)."""
    since = time.time()

    def done():
        active = coverage().active_layer
        if coverage_page:
            right = active is not None and active.name() == name
        else:
            right = active is None and dock().mGroupBox_exploring_single_selection.isVisible()
        return right and tasks_idle() and time.time() - since > 2.5
    return done


def targets_ready(target_names):
    """Condition: the targets and both FILTERING buttons are set, as the vector engine and
    CoverageModeController.run_vector_source_task read them."""
    def done():
        d = dock()
        ids = {layer(name).id() for name in target_names}
        return (ids <= set(d.get_layers_to_filter() or [])
                and d.pushButton_checkable_filtering_layers_to_filter.isChecked()
                and d.pushButton_checkable_filtering_geometric_predicates.isChecked())
    return done


def registered(*layer_names):
    ids = [layer(name).id() for name in layer_names if layer(name) is not None]
    return len(ids) == len(layer_names) and all(layer_id in app().PROJECT_LAYERS for layer_id in ids)


# --- steps: each returns None, or a condition polled until true (or STEP_TIMEOUT) ---

def s_setup():
    mw = iface.mainWindow()
    mw.resize(1600, 1000)
    mw.show()
    dem = QgsRasterLayer(M['dem'], 'dem', 'gdal')
    zones = QgsVectorLayer(M['zones'] + '|layername=zones', 'zones', 'ogr')
    layers = [zones, dem]
    if has_point_clouds():
        from qgis.core import QgsPointCloudLayer
        if 'pdal' in QgsProviderRegistry.instance().providerList():
            cloud = QgsPointCloudLayer(M['las'], 'cloud', 'pdal')
        else:
            cloud = QgsPointCloudLayer(M['ept'], 'cloud', 'ept')
        layers.append(cloud)
    project.addMapLayers(layers)
    iface.mapCanvas().setExtent(dem.extent())
    check('fixture layers load', all(item.isValid() for item in layers), str([item.name() for item in layers]))


def s_open_plugin():
    import qgis.utils
    settings = QSettings()
    settings.setValue('FilterMate/discord_welcome_dismissed', True)  # modal dialogs would block the run
    settings.setValue('FilterMate/whats_new_seen', 99)
    settings.setValue('qgis/digitizing/validate_geometries', 0)  # FilterMate asks about it otherwise
    plugins = os.path.join(tempfile.mkdtemp(prefix='fm_gui_'), 'plugins')
    shutil.copytree(REPO, os.path.join(plugins, PACKAGE), ignore=shutil.ignore_patterns(*EXCLUDED))
    sys.path.insert(0, plugins)
    qgis.utils.plugin_paths.insert(0, plugins)
    qgis.utils.updateAvailablePlugins()
    started = qgis.utils.loadPlugin(PACKAGE) and qgis.utils.startPlugin(PACKAGE)
    check('plugin starts with iface', started and PACKAGE in qgis.utils.plugins)
    from filter_mate.adapters.qgis.coverage_layers import cache
    cache.set_cache_root(os.path.join(os.path.dirname(plugins), 'cache'))
    qgis.utils.plugins[PACKAGE].run()
    expected = ['zones', 'dem'] + (['cloud'] if has_point_clouds() else [])
    return lambda: dock() is not None and registered(*expected) and tasks_idle()


def filtering_rows_span():
    """Pixels between the first and the last FILTERING value row (about 4 rows of 30 px + gaps)."""
    d = dock()
    rows = [getattr(d, name) for name in ('comboBox_filtering_current_layer', 'mQgsDoubleSpinBox_filtering_buffer_value')]
    tops = [w.mapTo(d, w.rect().topLeft()).y() for w in rows]
    return tops[1] - tops[0]


def s_dock_ready():
    expected = ['zones', 'dem'] + (['cloud'] if has_point_clouds() else [])
    check('dock open, every fixture layer registered', dock() is not None and dock().isVisible() and registered(*expected),
          f"registered={[name for name in expected if registered(name)]}")
    return settled()


def s_layout_check():
    # The key column aligner used to grow the page at every pass: rows 4000 px apart, one row visible.
    span = filtering_rows_span()
    check('FILTERING rows laid out together (key column aligner)', 0 < span < 600, f"first to last row: {span} px")


def s_vector_source():
    dock().comboBox_filtering_current_layer.setLayer(layer('zones'))
    return switched_to('zones', coverage_page=False)


def s_vector_select():
    d = dock()
    check('vector layer: EXPLORING shows the vector groups', d.mGroupBox_exploring_single_selection.isVisible())
    items = combo_items()
    check('layers to filter list every kind', any(t.startswith('dem [') for t in items)
          and (not has_point_clouds() or any(t.startswith('cloud [') for t in items)), str(items))
    d.mGroupBox_exploring_single_selection.setChecked(True)
    east_a = next(feature for feature in layer('zones').getFeatures() if feature['name'] == 'east_a')
    d.mFeaturePickerWidget_exploring_single_selection.setFeature(east_a.id())
    STATE['clip_cloud'] = has_point_clouds() and can_clip_point_clouds()
    targets = ['dem'] + (['cloud'] if STATE['clip_cloud'] else [])
    set_targets(targets)
    set_predicates(['Intersect'])
    # The feature picker fetches the feature in the background: filter once EXPLORING has it, as a user
    # does (otherwise "Raster / point cloud targets skipped: no source feature selected").
    ready = targets_ready(targets)
    return lambda: bool(dock().get_current_features()[0]) and ready()


def grab(name):
    """FM_GRAB_DIR set: save the dock as <name>.png there (visual checks of the panel at stable steps)."""
    folder = os.environ.get('FM_GRAB_DIR')
    if folder:
        dock().grab().save(os.path.join(folder, f"{name}.png"))


def message_bar_texts():
    texts = []
    for item in iface.messageBar().items():
        try:
            texts.append(f"{item.title()}: {item.text()}"[:200])
        except Exception:
            pass
    return texts


def s_vector_filter():
    grab('vector_source')
    STATE['cloud_source'] = layer('cloud').source() if layer('cloud') else ''
    features, expression = dock().get_current_features()
    print(f"   EXPLORING selection at filter time: {len(features or [])} feature(s), expression={expression!r}",
          flush=True)
    ctrl = coverage()
    if not getattr(ctrl, '_smoke_traced', False):
        original = ctrl.run_vector_source_task

        def traced(task_name, source, coverage_ids):
            STATE.setdefault('vector_source_calls', []).append(
                f"{task_name} source={source.name() if source else None} targets={len(coverage_ids or [])} "
                f"engine_filters_targets={ctrl._vector_engine_filters_targets()} "
                f"features_now={len(ctrl._vector_source_features(source)) if source else '-'}")
            return original(task_name, source, coverage_ids)

        ctrl.run_vector_source_task = traced
        ctrl._smoke_traced = True
    run_task('filter')
    return lambda: layer('dem').source().endswith('.vrt') and tasks_idle()


def s_vector_check():
    dem = layer('dem')
    if not check('vector source -> raster target: clipped VRT', dem.source().endswith('.vrt') and dem.isValid(),
                 f"source=...{dem.source()[-40:]}"):
        a = app()
        for text in message_bar_texts():
            print(f"   message bar: {text}", flush=True)
        print(f"   coverage calls: {STATE.get('vector_source_calls')}", flush=True)
        print(f"   app flags: initializing={getattr(a, '_initializing_project', '?')} "
              f"loading={getattr(a, '_loading_new_project', '?')} "
              f"pending_filter={getattr(dock(), '_pending_filter_after_init', '?')}", flush=True)
        dump_recent()
    if STATE['clip_cloud']:
        cloud = layer('cloud')
        check('vector source -> point cloud target: clipped', cloud.source() != STATE['cloud_source'] and cloud.isValid(),
              f"source=...{cloud.source()[-40:]} points={cloud.pointCount()}")
    elif has_point_clouds():
        report('SKIP', 'vector source -> point cloud target', 'no pdal >= 2.4 and no pdal provider in this QGIS')
    run_task('undo')
    return lambda: not layer('dem').source().endswith('.vrt') and tasks_idle()


def s_vector_undo_check():
    check('undo puts the raster target back', os.path.normpath(layer('dem').source()) == os.path.normpath(M['dem']),
          layer('dem').source())
    # Right after undo, the user picks another layer: for 1.5-2 s the dock moves the combo back to the source
    # layer when an async change moved it, never against the user (the pick ends that window at once).
    # A real key press (the combo's signals are blocked in that window, `activated` would not even fire).
    from qgis.PyQt.QtCore import QEvent
    from qgis.PyQt.QtGui import QKeyEvent
    from qgis.PyQt.QtWidgets import QApplication
    combo = dock().comboBox_filtering_current_layer
    before = combo.currentLayer()
    STATE['blocked_at_pick'] = combo.signalsBlocked()  # True: the post-filter window path is exercised
    for key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
        QApplication.sendEvent(combo, QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier))
        if combo.currentLayer() is not None and combo.currentLayer() is not before:
            break
    STATE['picked'] = combo.currentLayer().name() if combo.currentLayer() else None
    STATE['picked_from'] = before.name() if before else None
    return settled()


def s_user_pick_after_undo_check():
    current = dock().comboBox_filtering_current_layer.currentLayer()
    dock_layer = getattr(dock(), 'current_layer', None)
    check('a layer picked right after undo is kept and applied',
          STATE['picked'] not in (None, STATE['picked_from']) and current is not None and current.name() == STATE['picked']
          and dock_layer is not None and dock_layer.name() == STATE['picked'],
          f"picked={STATE['picked']} (from {STATE['picked_from']}) combo={current.name() if current else None} "
          f"dock={dock_layer.name() if dock_layer else None} signals blocked at the pick={STATE['blocked_at_pick']}")


def s_raster_source():
    dock().comboBox_filtering_current_layer.setLayer(layer('dem'))
    return switched_to('dem', coverage_page=True)


def s_raster_select():
    d, ctrl = dock(), coverage()
    current = d.comboBox_filtering_current_layer.currentLayer()
    print(f"   current layer={current.name() if current else None} coverage active="
          f"{ctrl.active_layer.name() if ctrl.active_layer else None} dock current="
          f"{getattr(d, 'current_layer', None) and d.current_layer.name()}", flush=True)
    check('raster layer: EXPLORING shows the raster panel, not the vector groups',
          ctrl._raster_panel.isVisible() and not d.mGroupBox_exploring_single_selection.isVisible())
    from filter_mate.core.domain.raster_filter_criteria import RasterSelection
    low, high = M['east_range']
    ctrl._raster_panel.set_selection(RasterSelection(band=1, minimum=float(low), maximum=float(high)))
    set_targets(['zones'])
    set_predicates(['Intersect'])
    return targets_ready(['zones'])


def s_raster_filter():
    grab('raster_source')
    run_task('filter')
    return lambda: layer('zones').subsetString() != '' and tasks_idle()


def s_raster_check():
    zones = layer('zones')
    check('raster source (value range) -> vector target', names(zones) == M['zones_in_east_range'],
          f"kept={names(zones)} subset={zones.subsetString()[:60]!r}")
    run_task('unfilter')
    return lambda: layer('zones').subsetString() == '' and tasks_idle()


def s_raster_settled():
    check('raster source: unfilter clears the vector target', layer('zones').subsetString() == '',
          repr(layer('zones').subsetString()[:60]))
    return settled()


def s_point_cloud_source():
    if not has_point_clouds():
        report('SKIP', 'point cloud source', f"QGIS {Qgis.QGIS_VERSION} < 3.26 (FilterMate gate)")
        return None
    dock().comboBox_filtering_current_layer.setLayer(layer('cloud'))
    return switched_to('cloud', coverage_page=True)


def s_point_cloud_select():
    if not has_point_clouds():
        return None
    ctrl = coverage()
    check('point cloud layer: EXPLORING shows the point cloud panel', ctrl._pc_panel.isVisible())
    panel = ctrl._pc_panel
    state = dict(panel.state())
    state.update({'classes_enabled': True, 'classes': [6], 'checked_classes': [6]})
    panel.restore_state(state)
    set_targets(['zones'])
    set_predicates(['Intersect'])
    return targets_ready(['zones'])


def s_point_cloud_filter():
    if not has_point_clouds():
        return None
    grab('point_cloud_source')
    run_task('filter')
    return lambda: layer('zones').subsetString() != '' and tasks_idle()


def s_point_cloud_check():
    if not has_point_clouds():
        return None
    zones, cloud = layer('zones'), layer('cloud')
    check('point cloud source (class 6) -> vector target', names(zones) == M['zones_with_buildings'],
          f"kept={names(zones)} source subset={cloud.subsetString()!r}", expected_failure=subset_issue())
    run_task('undo')
    return lambda: layer('zones').subsetString() == '' and tasks_idle()


def s_point_cloud_settled():
    if not has_point_clouds():
        return None
    check('point cloud source: undo clears the vector target and the source subset',
          layer('zones').subsetString() == '' and layer('cloud').subsetString() == '',
          f"zones={layer('zones').subsetString()[:40]!r} cloud={layer('cloud').subsetString()!r}")
    return settled()


def s_back_to_vector():
    dock().comboBox_filtering_current_layer.setLayer(layer('zones'))
    return switched_to('zones', coverage_page=False)


def s_rasters_off():
    check('back to a vector layer: vector groups again', dock().mGroupBox_exploring_single_selection.isVisible())
    from filter_mate.config.config import ENV_VARS
    ENV_VARS['CONFIG_DATA']['APP']['OPTIONS']['RASTER']['enabled']['value'] = False
    STATE['kind_counts'] = app().apply_layer_kind_options()
    return lambda: not registered('dem') and tasks_idle()


def current_layer_list():
    """Layer names of the current-layer combo box (its items read "name [EPSG:xxxx]")."""
    combo = dock().comboBox_filtering_current_layer
    return [str(combo.model().data(combo.model().index(row, 0))).split(' [')[0] for row in range(combo.model().rowCount())]


def s_rasters_off_check():
    in_combo = current_layer_list()
    check('rasters switched off: unregistered and gone from the current-layer list',
          not registered('dem') and 'dem' not in in_combo and 'zones' in in_combo and STATE['kind_counts'] == (0, 1),
          f"counts={STATE['kind_counts']} combo={in_combo}")
    from filter_mate.config.config import ENV_VARS
    ENV_VARS['CONFIG_DATA']['APP']['OPTIONS']['RASTER']['enabled']['value'] = True
    STATE['kind_counts'] = app().apply_layer_kind_options()
    return lambda: registered('dem') and tasks_idle()


def s_rasters_on_check():
    a = app()
    print(f"   add_layers: pending={getattr(a, '_pending_add_layers_tasks', '?')} "
          f"queue={len(getattr(a, '_add_layers_queue', []) or [])} initializing={getattr(a, '_initializing_project', '?')} "
          f"loading={getattr(a, '_loading_new_project', '?')}", flush=True)
    in_combo = current_layer_list()
    targets = [item.split(' [')[0] for item in combo_items()]
    check('rasters switched on again: registered and listed once', registered('dem') and in_combo.count('dem') == 1
          and STATE['kind_counts'] == (1, 0), f"counts={STATE['kind_counts']} combo={in_combo}")
    check('layers to filter list each layer once', len(targets) == len(set(targets)), str(targets))


def s_remove_layer():
    """Removing a layer from the project unregisters it (the task ignored the ids QGIS sends until 5.0)."""
    STATE['removed_id'] = layer('dem').id()
    project.removeMapLayer(STATE['removed_id'])
    return lambda: STATE['removed_id'] not in app().PROJECT_LAYERS and tasks_idle()


def s_remove_layer_check():
    check('layer removed from the project: unregistered', STATE['removed_id'] not in app().PROJECT_LAYERS
          and 'dem' not in current_layer_list(), f"registered={STATE['removed_id'] in app().PROJECT_LAYERS}")


def s_finish():
    check('no Python error and no FilterMate critical message in the log', not STATE['python_errors'],
          '; '.join(STATE['python_errors'][:3]))
    counts = {status: sum(1 for s, _ in STATE['results'] if s == status) for status in ('PASS', 'FAIL', 'SKIP', 'XFAIL')}
    print(f"\n{counts['PASS']} passed, {counts['FAIL']} failed, {counts['SKIP']} skipped, {counts['XFAIL']} known "
          f"failures in {time.time() - STATE['started']:.1f}s (QGIS {Qgis.QGIS_VERSION}, dock)", flush=True)
    failed = [name for status, name in STATE['results'] if status == 'FAIL']
    if failed:
        print('FAILED: ' + '; '.join(failed), flush=True)
    os._exit(1 if failed else 0)  # QGIS exit code = test result; skips the slow GUI teardown


STEPS = [s_setup, s_open_plugin, s_dock_ready, s_layout_check,
         s_vector_source, s_vector_select, s_vector_filter, s_vector_check, s_vector_undo_check,
         s_user_pick_after_undo_check,
         s_raster_source, s_raster_select, s_raster_filter, s_raster_check, s_raster_settled,
         s_point_cloud_source, s_point_cloud_select, s_point_cloud_filter, s_point_cloud_check, s_point_cloud_settled,
         s_back_to_vector, s_rasters_off, s_rasters_off_check, s_rasters_on_check,
         s_remove_layer, s_remove_layer_check, s_finish]


def run_step(index=0):
    watch_plugin_loggers()
    step = STEPS[index]
    try:
        until = step()
    except Exception:
        report('FAIL', f"{step.__name__} raised", traceback.format_exc().strip().splitlines()[-1])
        print(traceback.format_exc(), flush=True)
        until = None
        if step in (s_setup, s_open_plugin, s_dock_ready):
            QTimer.singleShot(0, lambda: run_step(STEPS.index(s_finish)))
            return
    wait(index, until, time.time())


def wait(index, until, since):
    """Poll ``until`` every 250 ms, then move on (a timeout is reported, the next check tells what failed)."""
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
