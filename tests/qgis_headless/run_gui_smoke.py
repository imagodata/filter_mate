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
import importlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import types

from qgis.core import Qgis, QgsApplication, QgsProject, QgsProviderRegistry, QgsRasterLayer, QgsSettings, QgsVectorLayer
from qgis.PyQt.QtCore import QCoreApplication, QPoint, QPointF, QSettings, Qt, QTimer
from qgis.PyQt.QtGui import QWheelEvent
from qgis.PyQt.QtWidgets import (QAbstractButton, QApplication, QComboBox, QDockWidget, QLabel, QLineEdit, QMenu,
                                 QPushButton, QScrollArea, QToolButton, QWidget)
try:
    from qgis.PyQt.QtGui import QShortcut
except ImportError:  # QGIS < 3.34.2 (Qt5): QShortcut is in QtWidgets
    from qgis.PyQt.QtWidgets import QShortcut
from qgis.utils import iface
import qgis.utils

STATE = {'results': [], 'python_errors': [], 'started': time.time(), 'perf0': time.perf_counter()}
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
PACKAGE = os.environ.get('FM_PACKAGE') or 'filter_mate'  # FM_PACKAGE=fm_main: the plugin folder is not always filter_mate
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
        self.lines = (self.lines + [f"{record.created - STATE['started']:7.2f} {record.levelname[0]} {record.name}: "
                                    f"{record.getMessage()[:200]}"])[-1500:]


_RECENT = _RecentRecords()


def dump_recent(count=40, keywords=('FM5', 'overage', 'ross', 'BLOCKED', 'DEFERRED', 'raster', 'Raster', 'target')):
    """The last FilterMate messages about raster / point cloud targets and blocked tasks."""
    lines = [line for line in _RECENT.lines if any(word in line for word in keywords)]
    for line in dict.fromkeys(lines[-count:]):  # a logger with two handlers prints twice
        print(f"   | {line}", flush=True)


def watch_plugin_loggers():
    """Hook every FilterMate logger created so far (each one has its own handlers, no propagation)."""
    for name, logger in list(logging.root.manager.loggerDict.items()):
        if isinstance(logger, logging.Logger) and name.split('.')[0] in ('FilterMate', 'filter_mate', PACKAGE) \
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
    if os.environ.get('FM_ACTION_BAR'):  # the dock opens with this position of the action bar, as saved before
        for name in ('config.default.json', 'config.json'):
            path = os.path.join(plugins, PACKAGE, 'config', name)
            with open(path, encoding='utf-8') as stream:
                config = json.load(stream)
            config['APP']['DOCKWIDGET']['ACTION_BAR_POSITION']['value'] = os.environ['FM_ACTION_BAR']
            with open(path, 'w', encoding='utf-8') as stream:
                json.dump(config, stream, indent=2)
    if os.environ.get('FM_DETACHED'):  # and with these sections in their own panel, as left the last time
        settings.setValue('FilterMate/panels/detached', os.environ['FM_DETACHED'])
    sys.path.insert(0, plugins)
    qgis.utils.plugin_paths.insert(0, plugins)
    qgis.utils.updateAvailablePlugins()
    started = qgis.utils.loadPlugin(PACKAGE) and qgis.utils.startPlugin(PACKAGE)
    check('plugin starts with iface', started and PACKAGE in qgis.utils.plugins)
    cache = importlib.import_module(f'{PACKAGE}.adapters.qgis.coverage_layers.cache')
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


def coverage_connected():
    """The raster / point cloud controller receives the project signals (CoverageModeController.setup)."""
    return getattr(coverage(), '_project_connected', set()) == {'readProject', 'cleared', 'layersWillBeRemoved'}


def s_controllers_check():
    """The controller registry stayed empty until 5.0 (an empty registry was falsy): no controller was set up,
    so stored raster / point cloud filters were never replayed and the Configuration tab never saved an edit."""
    integration = dock()._controller_integration
    registry = integration.registry
    check('dock controllers registered and set up', registry is not None and len(registry) == 10
          and integration.validate_controllers()['all_valid'], repr(registry))
    check('raster / point cloud controller connected to the project (stored filters replayed)',
          coverage_connected())
    check('configuration controller applies the edits', integration.config_controller._initialized)


def press(key):
    """A real key press on the current-layer combo box (what a user does)."""
    from qgis.PyQt.QtCore import QEvent
    from qgis.PyQt.QtGui import QKeyEvent
    from qgis.PyQt.QtWidgets import QApplication
    QApplication.sendEvent(dock().comboBox_filtering_current_layer,
                           QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier))


def s_pick_before_late_refresh():
    """The user picks a layer in the first seconds; a refresh late after loading (_refresh_ui_with_layers)
    used to switch the panel back to QGIS' active layer."""
    combo = dock().comboBox_filtering_current_layer
    before = combo.currentLayer()
    for key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
        press(key)
        if combo.currentLayer() is not None and combo.currentLayer() is not before:
            break
    STATE['early_pick'] = combo.currentLayer().name() if combo.currentLayer() else None
    print(f"   early pick at {time.time() - STATE['started']:.2f}s: {STATE['early_pick']}", flush=True)
    since = time.time()
    return lambda: time.time() - since > 0.5


def s_late_refresh_check():
    d = dock()
    before = (getattr(d, '_user_layer_pick', None), d.comboBox_filtering_current_layer.currentLayer(),
              getattr(d, 'current_layer', None))
    app()._refresh_ui_with_layers()
    shown = getattr(d, 'current_layer', None)
    if not check('a late refresh keeps the layer the user picked', shown is not None and shown.name() == STATE['early_pick'],
                 f"picked={STATE['early_pick']} shown={shown.name() if shown else None} "
                 f"active in QGIS={iface.activeLayer().name() if iface.activeLayer() else None}"):
        pick, combo_layer, current = before
        print(f"   before the refresh: recorded pick={pick} combo={combo_layer.name() if combo_layer else None} "
              f"panel={current.name() if current else None}", flush=True)
        print(f"   pick recorded at {pick[0] - STATE['perf0']:.2f}s" if pick else "   no pick recorded", flush=True)
        dump_recent(60, ('current_layer_changed ENTRY', 'UI refreshed', 'efer', 'estor', 'protect', 'setLayer',
                         'active layer', 'Active layer', 'manual'))
    return settled()


def s_layout_check():
    # The key column aligner used to grow the page at every pass: rows 4000 px apart, one row visible.
    span = filtering_rows_span()
    check('FILTERING rows laid out together (key column aligner)', 0 < span < 600, f"first to last row: {span} px")


def rail_buttons_apart():
    """The shown EXPLORING rail buttons, top to bottom, do not overlap."""
    rail = dock().widget_exploring_keys
    buttons = sorted((button for button in rail.findChildren(QPushButton) if not button.isHidden()),
                     key=lambda button: button.y())
    return len(buttons) > 3 and all(upper.geometry().bottom() < lower.geometry().top()
                                    for upper, lower in zip(buttons, buttons[1:]))


def rail_scroll_maximum():
    return dock().findChild(QScrollArea, 'scrollArea_exploring_rail').verticalScrollBar().maximum()


def s_rail_width_check():
    """The scroll area took the width of the buttons and cut a rail wider than them (from 1920 x 1080 up: 56 px)."""
    rail = dock().widget_exploring_keys
    STATE['rail_min_width'] = rail.minimumWidth()
    rail.setMinimumWidth(rail.minimumSizeHint().width() + 20)
    return waits(0.5)


def s_rail_width_after():
    d = dock()
    rail = d.widget_exploring_keys
    band = d.findChild(QScrollArea, 'scrollArea_exploring_rail').viewport()
    shown = [button for button in rail.findChildren(QPushButton) if not button.isHidden()]
    check('EXPLORING rail wider than its buttons: not cut by its scroll area',
          band.width() == rail.width() and all(button.geometry().right() < band.width() for button in shown),
          f"band={band.width()} rail={rail.width()} right={[button.geometry().right() for button in shown]}")
    rail.setMinimumWidth(STATE['rail_min_width'])
    return waits(0.5)


def s_rail_short():
    """A band shorter than the compact buttons overlapped them (720 px screen): the rail now scrolls."""
    d = dock()
    STATE['splitter_sizes'] = d.main_splitter.sizes()
    d.main_splitter.setSizes([100, sum(STATE['splitter_sizes']) - 100])
    return waits(0.5)


def s_rail_short_check():
    d = dock()
    check('EXPLORING rail in a short band: buttons apart, and it scrolls', rail_buttons_apart() and rail_scroll_maximum() > 0,
          f"band={d.main_splitter.sizes()[0]} maximum={rail_scroll_maximum()}")
    # A button ignores the wheel, so Qt hands real input on to the scroll area. It does not do that for an
    # event sent from here: the band gets it directly. (Checked once with a real X11 wheel over a button.)
    band = d.findChild(QScrollArea, 'scrollArea_exploring_rail').viewport()
    centre = band.rect().center()
    QApplication.sendEvent(band, QWheelEvent(QPointF(centre), QPointF(band.mapToGlobal(centre)), QPoint(0, 0), QPoint(0, -120),
                                             Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                                             Qt.ScrollPhase.NoScrollPhase, False))
    scrollbar = d.findChild(QScrollArea, 'scrollArea_exploring_rail').verticalScrollBar()
    check('EXPLORING rail in a short band: the wheel scrolls it', scrollbar.value() > 0, f"value={scrollbar.value()}")
    scrollbar.setValue(0)
    d.main_splitter.setSizes([sum(STATE['splitter_sizes']), 0])
    return waits(0.5)


def s_rail_tall_check():
    d = dock()
    check('EXPLORING rail in a tall band: no scrolling', rail_buttons_apart() and rail_scroll_maximum() == 0,
          f"band={d.main_splitter.sizes()[0]} maximum={rail_scroll_maximum()}")
    d.main_splitter.setSizes(STATE['splitter_sizes'])
    return waits(0.5)


def set_ui_profile(value):
    """What the Configuration tab does for UI_PROFILE: it never ran until November 2026 (import failing in QGIS)."""
    d = dock()
    item = types.SimpleNamespace(data=lambda role: {'value': value})
    config_view = d.config_view
    d.config_view = types.SimpleNamespace(model=types.SimpleNamespace(itemFromIndex=lambda index: item))
    try:
        d._controller_integration.registry.get('config')._apply_ui_profile_change(
            {'path': ['UI_PROFILE'], 'index': types.SimpleNamespace(siblingAtColumn=lambda column: None)}, [])
    finally:
        d.config_view = config_view


def s_ui_profile_check():
    d = dock()
    ui_config = importlib.import_module(f'{PACKAGE}.ui.config').UIConfig
    check('UI profile at startup: the one detected from the screen', ui_config.get_profile() is ui_config.detect_profile_from_screen(),
          f"{ui_config.get_profile().name} vs {ui_config.detect_profile_from_screen().name}")
    set_ui_profile('normal')
    normal_height = d.minimumHeight()
    set_ui_profile('compact')
    check('UI_PROFILE setting: compact applied to the dock, splitter collapsible',
          ui_config.get_profile().name == 'COMPACT' and d.minimumHeight() < normal_height and d.main_splitter.childrenCollapsible(),
          f"{ui_config.get_profile().name} minimum height {normal_height} -> {d.minimumHeight()}")
    set_ui_profile('auto')
    check('UI_PROFILE setting: auto goes back to the profile of the screen',
          ui_config.get_profile() is ui_config.detect_profile_from_screen(), ui_config.get_profile().name)


# --- the agent changes settings of FilterMate (change_settings, 2026-11-12) ---------------------------------------

def agent_settings():
    return importlib.import_module(f'{PACKAGE}.adapters.agent.plugin_settings')


def config_value(path):
    ENV_VARS = importlib.import_module(f'{PACKAGE}.config.config').ENV_VARS
    node = ENV_VARS['CONFIG_DATA']
    for key in path.split('.'):
        node = node[key]
    return node['value'] if isinstance(node, dict) else node


def saved_value(path):
    ENV_VARS = importlib.import_module(f'{PACKAGE}.config.config').ENV_VARS
    with open(ENV_VARS['CONFIG_JSON_PATH'], encoding='utf-8') as stream:
        node = json.load(stream)
    for key in path.split('.'):
        node = node[key]
    return node['value'] if isinstance(node, dict) else node


def s_agent_settings():
    """change_settings as the chat runs it once the user said yes: the panel applies it like an edit of the tree."""
    handlers = agent_settings().settings_handlers()
    STATE['settings_before'] = {path: config_value(path) for path in (
        'APP.DOCKWIDGET.COLORS.ACTIVE_THEME', 'APP.OPTIONS.QUERY_CACHE.max_size', 'APP.OPTIONS.RASTER.enabled')}
    record_layer_kind_counts()
    answer = handlers['change_settings']({'changes': [
        {'path': 'APP.DOCKWIDGET.COLORS.ACTIVE_THEME', 'value': 'dark'},
        {'path': 'APP.OPTIONS.QUERY_CACHE.max_size', 'value': 222},
        {'path': 'APP.OPTIONS.RASTER.enabled', 'value': False}], 'reason': 'smoke'})
    STATE['settings_answer'] = answer
    return lambda: not registered('dem') and tasks_idle()


def s_agent_settings_check():
    d = dock()
    answer = STATE['settings_answer']
    changed = {row['path']: row for row in answer.get('changed', [])}
    item = config_value_item(['APP', 'DOCKWIDGET', 'COLORS', 'ACTIVE_THEME'])
    shown = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
    theme = getattr(getattr(d, '_theme_manager', None), 'current_theme', None)
    theme = theme() if callable(theme) else theme
    check('change_settings: three settings changed, in memory, on disk and in the tree',
          len(changed) == 3 and not answer.get('failed') and config_value('APP.OPTIONS.QUERY_CACHE.max_size') == 222
          and saved_value('APP.OPTIONS.QUERY_CACHE.max_size') == 222
          and isinstance(shown, dict) and shown.get('value') == 'dark', f"answer={answer} tree={shown}")
    check('change_settings: the theme follows at once', theme == 'dark', f"theme={theme}")
    check('change_settings: rasters switched off as from the tree (unregistered, gone from the list)',
          not registered('dem') and 'dem' not in current_layer_list() and STATE['kind_counts'] == (0, 1),
          f"counts={STATE['kind_counts']}")
    failure = None
    try:
        agent_settings().settings_handlers()['change_settings']({'changes': [
            {'path': 'APP.OPTIONS.AGENT.open_data_domains', 'value': 'evil.example.org'}], 'reason': 'smoke'})
    except Exception as exc:  # ToolFailure
        failure = str(exc)
    check('change_settings: the settings of the agent are refused', failure is not None and 'agent itself' in failure
          and config_value('APP.OPTIONS.AGENT.open_data_domains') != 'evil.example.org', str(failure)[:120])
    effects = importlib.import_module(f'{PACKAGE}.adapters.agent.turn_effects')
    before = {path: STATE['settings_before'][path] for path in changed}
    after = {path: row['after'] for path, row in changed.items()}
    record_layer_kind_counts()
    STATE['settings_undo'] = effects.apply_effects((('settings', '', json.dumps(before), json.dumps(after)),), undo=True)
    return lambda: registered('dem') and tasks_idle()


def s_agent_settings_undo_check():
    done, left = STATE['settings_undo']
    values = {path: config_value(path) for path in STATE['settings_before']}
    check('undoing the turn puts the settings back, rasters registered again',
          done and not left and values == STATE['settings_before'] and registered('dem')
          and saved_value('APP.OPTIONS.QUERY_CACHE.max_size') == STATE['settings_before']['APP.OPTIONS.QUERY_CACHE.max_size'],
          f"done={done} left={left} values={values}")
    return settled()


def agent_chat():
    return dock()._agent_chat


def settings_call(changes, name="change_settings"):
    messages = importlib.import_module(f'{PACKAGE}.core.agent.messages')
    return messages.ToolCallPart("smoke", name, {"changes": changes, "reason": "smoke"} if name == "change_settings"
                                 else changes)


def s_agent_settings_card_check():
    """A change of the settings proposed in the thread: nothing changes until Apply, which is a step of its own
    (undone by Undo); Cancel changes nothing; a proposal whose settings changed since is refused."""
    chat, handlers, path = agent_chat(), agent_settings().settings_handlers(), 'APP.OPTIONS.QUERY_CACHE.max_size'
    start = config_value(path)

    def propose(value):
        call = settings_call([{'path': path, 'value': value}])
        asked = chat.confirm(call)
        answer = handlers['change_settings'](call.arguments)  # what the engine runs next: a proposal, no change
        return asked, answer, chat._settings_cards[-1]
    asked, answer, card = propose(333)
    proposed_only = asked is True and 'proposed' in answer and config_value(path) == start
    card.apply_button.click()
    applied = card.done and config_value(path) == 333
    chat._on_undo()
    undone = config_value(path) == start
    _asked, _answer, card = propose(444)
    card.cancel_button.click()
    cancelled = card.done and config_value(path) == start
    _asked, _answer, card = propose(555)
    handlers['change_settings']({'changes': [{'path': path, 'value': 222}], 'reason': 'smoke'})
    card.apply_button.click()
    stale = card.done and config_value(path) == 222
    handlers['change_settings']({'changes': [{'path': path, 'value': start}], 'reason': 'smoke'})
    check('settings card: proposed, applied as a step and undone, cancelled, stale refused',
          proposed_only and applied and undone and cancelled and stale and len(chat._settings_outcomes) >= 3,
          f"{proposed_only} {applied} {undone} {cancelled} {stale} {chat._settings_outcomes}")
    chat._settings_outcomes = []
    return waits(0.5)


def s_agent_settings_link_check():
    """show_settings_link: a button that selects the setting in the configuration tree."""
    d, chat = dock(), agent_chat()
    shown = chat._settings_link_tool({'target': 'setting', 'path': 'APP.OPTIONS.QUERY_CACHE.max_size'})
    chat._links[-1]()
    QApplication.processEvents()
    index = d.config_view.currentIndex()
    toolbox = d.toolBox_tabTools
    check('settings link: the configuration opens on the setting', toolbox.currentWidget() is d.CONFIGURATION
          and index.isValid() and index.data() == 'max_size', f"{shown} -> {index.data() if index.isValid() else None}")
    toolbox.setCurrentWidget(d.FILTERING)  # the checks that follow expect FILTERING open
    return waits(0.5)


def s_agent_settings_profile_check():
    """A profile saved with the settings changed, then applied again after a change."""
    handlers = agent_settings().settings_handlers()
    handlers['change_settings']({'changes': [{'path': 'APP.OPTIONS.QUERY_CACHE.max_size', 'value': 444}],
                                 'reason': 'smoke'})
    saved = handlers['export_settings_profile']({'name': 'smoke team'})
    with open(agent_settings()._profiles_folder() / 'smoke team.json', encoding='utf-8') as stream:
        content = json.load(stream)
    handlers['change_settings']({'changes': [{'path': 'APP.OPTIONS.QUERY_CACHE.max_size', 'value': 100}],
                                 'reason': 'smoke'})
    applied = handlers['apply_settings_profile']({'name': 'smoke team'})
    check('settings profile: saved without the agent settings, applied again',
          content['settings'].get('APP.OPTIONS.QUERY_CACHE.max_size') == 444
          and not any(key.startswith('APP.OPTIONS.AGENT') for key in content['settings'])
          and config_value('APP.OPTIONS.QUERY_CACHE.max_size') == 444
          and [row['path'] for row in applied['changed']] == ['APP.OPTIONS.QUERY_CACHE.max_size'],
          f"saved={saved} applied={applied}")
    handlers['change_settings']({'changes': [{'path': 'APP.OPTIONS.QUERY_CACHE.max_size', 'value': 100}],
                                 'reason': 'smoke'})
    agent_chat().new_conversation()  # the checks of the AGENT section that follow expect its welcome
    return waits(0.5)


def s_agent_skill_from_profile_check():
    """A skill in FilterMate/skills of the profile: offered by load_skill, asked once, loaded as data."""
    sources = importlib.import_module(f'{PACKAGE}.adapters.agent.skill_sources')
    load_settings = importlib.import_module(f'{PACKAGE}.adapters.agent.settings').load_settings
    folder = sources.user_folder() / 'team-naming'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'SKILL.md').write_text("---\nname: team-naming\ntitle: Our naming rules\ndescription: how this team "
                                     "names its layers\n---\n\n# Naming\n\nLayers are named after the theme.\n",
                                     encoding='utf-8')
    chat, asked = agent_chat(), []
    original = chat._ask_code
    approvals = QgsSettings().value(sources.APPROVED_KEY)  # the allowances of the profile, put back after
    chat._ask_code = lambda title, text, code: asked.append(code) or True
    try:
        tools, handlers, _active = chat.tools_and_handlers(load_settings())
        tool = next(tool for tool in tools if tool.name == 'load_skill')
        offered = tool.input_schema['properties']['name']['enum']
        first = handlers['load_skill']({'name': 'team-naming'})
        second = handlers['load_skill']({'name': 'team-naming'})
        again, _handlers, _active = chat.tools_and_handlers(load_settings())
        allowed = next(tool for tool in again if tool.name == 'load_skill').description
    finally:
        chat._ask_code = original
        shutil.rmtree(folder, ignore_errors=True)
        if approvals is None:
            QgsSettings().remove(sources.APPROVED_KEY)
        else:
            QgsSettings().setValue(sources.APPROVED_KEY, approvals)
    check('skill of the profile: offered, asked once, loaded as data with no right',
          'team-naming' in offered and len(asked) == 1 and first.get('from') == 'user'
          and first['instructions'].startswith('This skill comes from the QGIS profile') and second == first,
          f"offered={offered} asked={len(asked)} first={str(first)[:120]}")
    # 2026-11-13: its description reached the model with every request before the user had read the skill
    check('skill of the profile: its words reach the model only once the user read them, all of them shown',
          'how this team names' not in tool.description and 'team-naming: a skill from the QGIS profile' in tool.description
          and asked and 'description: how this team names its layers' in asked[0] and 'title: Our naming rules' in asked[0]
          and 'team-naming (from the QGIS profile of the user): how this team names its layers' in allowed,
          f"before={tool.description[-160:]!r} asked={asked[:1]} after={allowed[-160:]!r}")
    return waits(0.2)


def s_agent_setup_offer_check():
    """The setup: offered once per version (a card of the thread), an entry of both menus; no model in its name."""
    import qgis.utils
    chat = agent_chat()
    before = len(chat._settings_cards)
    first = chat.offer_setup_once('smoke-9.9.9')
    second = chat.offer_setup_once('smoke-9.9.9')
    cards = len(chat._settings_cards)
    controller = importlib.import_module(f'{PACKAGE}.ui.controllers.agent_chat_controller')
    shown = cards >= 1 and controller._tr('Set up FilterMate?') in chat.panel.thread.toPlainText()
    plugin = qgis.utils.plugins[PACKAGE]
    entries = [action.text() for action in plugin.actions]
    check('setup: offered once per version, in the QGIS menu and the panel menu',
          first is True and second is False and bool(shown) and len(chat._settings_cards) == before + 1 and plugin.tr('Set up FilterMate') in entries
          and chat.panel.setup_action is not None and 'agent' not in chat.panel.setup_action.text().lower(),
          f"first={first} second={second} entries={entries}")
    chat.new_conversation()  # the checks of the AGENT section that follow expect its welcome
    return waits(0.2)


def _wizard_card():
    """The question card of the setup waiting in the AGENT thread."""
    return agent_chat()._wizard._card


def _answer_card(untick=(), tick=()):
    card = _wizard_card()
    for buttons, _other, _field in card._groups:
        for button, label in buttons:
            if label in untick:
                button.setChecked(False)
            if label in tick:
                button.setChecked(True)
    card.answer_button.click()


def s_setup_wizard():
    """The setup with no model: cards of choices; FILTERING turned off on the first one."""
    chat = agent_chat()
    STATE['wizard_started'] = chat.start_setup()
    card = _wizard_card()
    STATE['wizard_no_other'] = card is not None and not any(
        other is not None for _buttons, other, _field in card._groups)
    STATE['wizard_steps'] = 0
    while _wizard_card() is not None and STATE['wizard_steps'] < 6:
        _answer_card(untick=('FILTERING',) if STATE['wizard_steps'] == 0 else ())
        STATE['wizard_steps'] += 1
    STATE['wizard_card'] = chat._settings_cards[-1] if chat._settings_cards else None
    return waits(0.2)


def s_setup_wizard_apply():
    card = STATE['wizard_card']
    STATE['wizard_rows'] = [row.text() for row in card.rows] if card is not None else []
    if card is not None:
        card.apply_button.click()
    return waits(0.5)


def s_setup_wizard_check():
    d = dock()
    config = d.CONFIG_DATA['APP']['OPTIONS'].get('FILTERING', {}).get('enabled', {})
    value = config.get('value') if isinstance(config, dict) else config
    combo, auto = d.comboBox_filtering_current_layer, d.pushButton_checkable_filtering_auto_current_layer
    check('setup with no model: cards without Other, four steps (FILTERING skipped), the change shown then applied',
          STATE['wizard_started'] is True and STATE['wizard_no_other'] and STATE['wizard_steps'] == 4
          and len(STATE['wizard_rows']) == 1 and STATE['wizard_card'].done and value is False,
          f"started={STATE['wizard_started']} steps={STATE['wizard_steps']} rows={STATE['wizard_rows']} value={value!r}")
    check('FILTERING off: its header and buttons hidden, the source layer chooser at the top of EXPLORING',
          not d._fm_sections.section_shown('filtering') and d.pushButton_action_filter.isHidden()
          and d.pushButton_action_unfilter.isHidden() and d.frame_exploring.isAncestorOf(combo)
          and d.frame_exploring.isAncestorOf(auto) and not combo.isHidden() and not d.FILTERING.isAncestorOf(combo),
          f"shown={d._fm_sections.section_shown('filtering')} combo parent={combo.parentWidget().objectName()}")
    STATE['wizard_reverted'] = agent_chat()._wizard.revert()  # the link after Apply puts FILTERING back
    return waits(0.5)


def s_setup_wizard_back_check():
    d = dock()
    combo, auto = d.comboBox_filtering_current_layer, d.pushButton_checkable_filtering_auto_current_layer
    check('setup put back: FILTERING, its header, buttons and the source layer chooser back in place',
          STATE['wizard_reverted'] is True and d._fm_sections.section_shown('filtering') and not d.pushButton_action_filter.isHidden()
          and d.FILTERING.isAncestorOf(combo) and d.FILTERING.isAncestorOf(auto)
          and d.findChild(QWidget, 'widget_exploring_source_layer') is None,
          f"combo parent={combo.parentWidget().objectName()} auto parent={auto.parentWidget().objectName()}")
    agent_chat().new_conversation()  # the checks of the AGENT section that follow expect its welcome
    d._fm_sections.open_top('exploring')  # the setup opened AGENT, which folds EXPLORING and FILTERING
    d.toolBox_tabTools.setCurrentWidget(d.FILTERING)  # the steps that follow filter (Undo walks FILTERING only)
    return waits(0.3)


def s_qt6_enums_check():
    """Scoped-enum spellings that raised AttributeError in QGIS 4 (October 2026 audit)."""
    from qgis.PyQt.QtGui import QColor, QStandardItem, QStandardItemModel
    from qgis.PyQt.QtWidgets import QSizePolicy
    UIConfig = importlib.import_module(f'{PACKAGE}.ui.config').UIConfig
    ColorType = importlib.import_module(f'{PACKAGE}.ui.widgets.json_view.datatypes').ColorType

    # QSizePolicy.Policy.*: the splitter set-up swallowed the error and left main_splitter at None.
    d = dock()
    d._apply_splitter_frame_policies()
    expected = {}
    for frame, defaults in (('frame_exploring', ('Preferred', 'Minimum')), ('frame_toolset', ('Preferred', 'Expanding'))):
        cfg = UIConfig.get_config(frame) or {}
        expected[frame] = (getattr(QSizePolicy.Policy, cfg.get('size_policy_h', defaults[0])),
                           getattr(QSizePolicy.Policy, cfg.get('size_policy_v', defaults[1])))
    actual = {frame: (getattr(d, frame).sizePolicy().horizontalPolicy(), getattr(d, frame).sizePolicy().verticalPolicy())
              for frame in expected}
    check('dock splitter: main_splitter set up and frame size policies applied (QSizePolicy.Policy)',
          d.main_splitter is not None and actual == expected, f"main_splitter={d.main_splitter!r} {actual} vs {expected}")

    # QColor.NameFormat.*: editing a colour in the JSON view (ColorType delegate, QgsColorButton).
    model = QStandardItemModel()
    item = QStandardItem('#ff0000')
    model.appendRow(item)
    delegate = ColorType()
    editor = delegate.createEditor(None, None, item.index())
    editor.setColor(QColor(0x12, 0x34, 0x56, 0x80))  # colorChanged -> setModelData, as for a user's pick
    translucent = model.data(item.index(), Qt.ItemDataRole.EditRole)
    editor.setColor(QColor(0x12, 0x34, 0x56))
    delegate.setModelData(editor, model, item.index())
    opaque = model.data(item.index(), Qt.ItemDataRole.EditRole)
    check('JSON view colour delegate writes #AARRGGBB / #RRGGBB (QColor.NameFormat)',
          str(translucent).lower() == '#80123456' and str(opaque).lower() == '#123456', f"{translucent!r} {opaque!r}")


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


def s_compare_check():
    """Compare (action bar): the map before the last filter left of a line, its tool on the canvas, gone when off."""
    from qgis.utils import iface
    d = dock()
    button = getattr(d, 'pushButton_action_compare', None)
    redo = d.pushButton_action_redo_filter
    if not check('compare: a checkable button beside Redo', button is not None and button.isCheckable()
                 and button.parentWidget() is redo.parentWidget()):
        return None
    shown = sorted((b for b in d.frame_actions.findChildren(QPushButton) if b.isVisible()), key=lambda b: b.x())
    gaps = [after.x() - (before.x() + before.width()) for before, after in zip(shown, shown[1:])]
    check('compare: the same gap between each two buttons of the action bar', len(gaps) >= 2
          and max(gaps) - min(gaps) <= 2, str(gaps))
    check('compare: available as Undo is', button.isEnabled() == d.pushButton_action_undo_filter.isEnabled(),
          f"compare={button.isEnabled()} undo={d.pushButton_action_undo_filter.isEnabled()}")
    canvas = iface.mapCanvas()
    previous = canvas.mapTool()
    button.click()
    session = d._controller_integration._compare_controller.session
    compared = session.compared_layer_ids() if session is not None else []
    source = d.current_layer
    check('compare: on after a filter, the source and the dem drawn as they were', button.isChecked()
          and layer('dem').id() in compared and source is not None and source.id() in compared
          and canvas.mapTool() is session.tool, f"checked={button.isChecked()} compared={compared}")
    if os.environ.get('FM_BOARDS'):  # the action bar of the guide: after a filter, Compare on
        QApplication.processEvents()
        d.frame_actions.grab().save(os.path.join(os.environ['FM_BOARDS'], 'ActionBar.png'))
    STATE['compare_session'] = session
    STATE['compare_previous_tool'] = previous
    return lambda: session is None or session.renders >= 1


def s_compare_off_check():
    from qgis.utils import iface
    d = dock()
    session = STATE.get('compare_session')
    check('compare: the before image was rendered', session is not None and session.renders >= 1,
          session.renders if session is not None else None)
    d.pushButton_action_compare.click()
    check('compare: off, the tool there before and no clone left',
          not d.pushButton_action_compare.isChecked() and iface.mapCanvas().mapTool() is STATE.get('compare_previous_tool')
          and (session is None or not session.clones))
    # On again, then another map tool chosen: the comparison ends and leaves that tool, the button goes up.
    from qgis.gui import QgsMapToolPan
    d.pushButton_action_compare.click()
    pan = QgsMapToolPan(iface.mapCanvas())
    iface.mapCanvas().setMapTool(pan)
    check('compare: another map tool ends it', not d.pushButton_action_compare.isChecked()
          and session is not None and not session.active and iface.mapCanvas().mapTool() is pan)
    previous = STATE.get('compare_previous_tool')
    if previous is not None:
        iface.mapCanvas().setMapTool(previous)
    else:
        iface.mapCanvas().unsetMapTool(pan)


def s_compare_pin():
    """Compare pinned from the menu of its button (right-click), then a layer hidden: the comparison follows the map."""
    from qgis.PyQt.QtCore import QPoint
    from qgis.utils import iface
    d = dock()
    button = d.pushButton_action_compare
    controller = d._controller_integration._compare_controller
    STATE['compare_pin_tool'] = iface.mapCanvas().mapTool()
    button.customContextMenuRequested.emit(QPoint(4, 4))  # what a right-click on the button sends
    QApplication.processEvents()
    menu = controller.menu
    texts = [action.text() for action in menu.actions()]
    check('compare: right-click opens the menu of the button', menu.isVisible()
          and texts == ['Pin the current state', 'Remove the pin', 'Pin the map before each request of the agent', '',
                        'Horizontal line', '', 'History…'], f"visible={menu.isVisible()} {texts}")
    next(action for action in menu.actions() if action.text() == 'Pin the current state').trigger()
    menu.close()
    check('compare: pinned from the menu, available, its tooltip says when', controller.pinned is not None
          and button.isEnabled() and 'pinned at' in button.toolTip(), button.toolTip())
    button.click()
    session = controller.session
    check('compare: on with the pin, nothing changed yet', button.isChecked() and session is not None
          and session.active and not session.compared_layer_ids() and not session.present
          and session.item.labels[0].startswith('Pinned '), f"labels={session.item.labels if session else None}")
    dem = layer('dem')
    node = QgsProject.instance().layerTreeRoot().findLayer(dem.id())
    STATE['compare_pin_dem_visible'] = node.itemVisibilityChecked()
    node.setItemVisibilityChecked(False)
    iface.mapCanvas().refresh()
    return lambda: dem.id() in session.present and not session.item.busy


def s_compare_pin_check():
    from qgis.utils import iface
    d = dock()
    button = d.pushButton_action_compare
    controller = d._controller_integration._compare_controller
    session = controller.session
    dem = layer('dem')
    check('compare: a layer hidden since the pin is drawn left of the line', button.isChecked() and session.active
          and dem.id() in session.present and session.renders >= 1, f"present={session.present}")
    QgsProject.instance().layerTreeRoot().findLayer(dem.id()).setItemVisibilityChecked(
        STATE.get('compare_pin_dem_visible', True))
    controller._show_menu()
    unpin = next(action for action in controller.menu.actions() if action.text() == 'Remove the pin')
    check('compare: the pin can be removed from the menu', unpin.isEnabled())
    unpin.trigger()
    controller.menu.close()
    check('compare: no pin, available as Undo is again', controller.pinned is None
          and button.isEnabled() == d.pushButton_action_undo_filter.isEnabled() and 'pinned at' not in button.toolTip())
    if button.isChecked():
        button.click()
    previous = STATE.get('compare_pin_tool')
    if previous is not None and iface.mapCanvas().mapTool() is not previous:
        iface.mapCanvas().setMapTool(previous)
    check('compare: off after the pin, the tool there before', not button.isChecked() and not session.active
          and iface.mapCanvas().mapTool() is previous)


def s_history_check():
    """The history of the project: a right-click on Undo opens it over the dock, the filter just done listed first
    among the filters of the dock, marked as what Undo would undo; its tooltip names it."""
    from qgis.PyQt.QtCore import QPoint
    from qgis.PyQt.QtGui import QContextMenuEvent
    from filter_mate.core.domain.history_timeline import KIND_VECTOR
    from filter_mate.ui.controllers.history_controller import COLUMN_MARK, COLUMN_WHAT, INDEX_ROLE
    d = dock()
    controller = d._controller_integration.history_controller
    if not check('history: set up with the dock', controller is not None):
        return None
    undo = d.pushButton_action_undo_filter
    QApplication.sendEvent(undo, QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(4, 4),
                                                   undo.mapToGlobal(QPoint(4, 4))))
    QApplication.processEvents()
    panel = controller.panel
    if not check('history: a right-click on Undo opens the panel', panel is not None and panel.isVisible()):
        return None
    vector = [(index, item) for index, item in enumerate(panel.items) if item.kind == KIND_VECTOR]
    rows = {panel.tree.topLevelItem(i).data(0, INDEX_ROLE): panel.tree.topLevelItem(i)
            for i in range(panel.tree.topLevelItemCount())}
    first = vector[0] if vector else (None, None)
    row = rows.get(first[0])
    source = d.current_layer
    check('history: the vector filter just done is listed, marked as what Undo undoes',
          first[1] is not None and first[1].applied and source is not None and source.name() in first[1].layers
          and row is not None and row.text(COLUMN_MARK) == 'Undo' and row.text(COLUMN_WHAT) == first[1].label,
          f"vector={[(item.label, item.layers, item.applied) for _i, item in vector]} "
          f"mark={row.text(COLUMN_MARK) if row is not None else None}")
    controller.close_panel()
    controller.refresh()
    check('history: the tooltip of Undo names the filter and its history', first[1] is not None
          and undo.toolTip().startswith('Undo: ' + first[1].label[:40]) and 'vector filters of the dock' in undo.toolTip(),
          undo.toolTip())


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


def s_undo_pick_race():
    """The same pick, made certain to race a check of the undo (it failed once in CI): the key press and the
    undo's first check (+200 ms, adapters/undo_redo_handler.py) fall due in one pass of the event loop. The
    press runs first and changes the combo box (signals blocked: post-filter window), then the check, before the
    call the pick detector posted for the press: the check put the source layer back, the detector saw no change."""
    combo = dock().comboBox_filtering_current_layer
    race = STATE['race'] = {'from': combo.currentLayer().name() if combo.currentLayer() else None}

    def pick():
        race['blocked'] = combo.signalsBlocked()
        race['at'] = time.perf_counter() - STATE['perf0']
        before = combo.currentLayer()
        for key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
            press(key)
            if combo.currentLayer() is not None and combo.currentLayer() is not before:
                break
        race['picked'] = combo.currentLayer().name() if combo.currentLayer() else None

    QTimer.singleShot(150, pick)  # due before the undo's first check
    run_task('undo')
    time.sleep(0.4)  # both due when the event loop runs again: one pass, the press first
    return settled()


def s_undo_pick_race_check():
    race = STATE['race']
    current = dock().comboBox_filtering_current_layer.currentLayer()
    dock_layer = getattr(dock(), 'current_layer', None)
    if not check('a layer picked as a check of the undo falls due is kept and applied',
                 race.get('picked') not in (None, race['from']) and current is not None
                 and current.name() == race['picked'] and dock_layer is not None and dock_layer.name() == race['picked'],
                 f"picked={race.get('picked')} (from {race['from']}) combo={current.name() if current else None} "
                 f"dock={dock_layer.name() if dock_layer else None} signals blocked at the pick={race.get('blocked')}"):
        pick = getattr(dock(), '_user_layer_pick', None)
        print(f"   press at {race.get('at', 0):.2f}s, recorded pick={pick}"
              + (f" at {pick[0] - STATE['perf0']:.2f}s" if pick else ''), flush=True)
        dump_recent(30, ('current_layer_changed ENTRY', 'estor', 'DELAYED', 'picked', 'protection', 'Unblocked'))


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
    RasterSelection = importlib.import_module(f'{PACKAGE}.core.domain.raster_filter_criteria').RasterSelection
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


def badge_text():
    return dock().backend_indicator_label.text()


def s_badge_raster_source():
    dock().comboBox_filtering_current_layer.setLayer(layer('dem'))
    return switched_to('dem', coverage_page=True)


def s_raster_badge_add_layer():
    """The end of add_layers / remove_layers refreshes the backend badge: a vector one was written over the
    "Raster · GDAL" badge of the current raster layer (and featureCount() failed on the raster).

    Last steps with a current-layer pick: a layer removed while a raster layer is current leaves the
    current-layer combo box empty, and the panel no longer follows it (also before 5.0's controller fixes)."""
    STATE['raster_badge'] = badge_text()
    # Out of the layer tree: a layer added to it becomes QGIS' active layer, which the panel follows.
    project.addMapLayer(QgsVectorLayer(M['zones'] + '|layername=zones', 'extra', 'ogr'), False)
    return lambda: registered('extra') and tasks_idle()


def s_raster_badge_check():
    active = coverage().active_layer
    check('raster current layer keeps its badge after a layer is added',
          STATE['raster_badge'].startswith('Raster') and badge_text() == STATE['raster_badge']
          and active is not None and active.name() == 'dem',
          f"badge before={STATE['raster_badge']!r} after={badge_text()!r} active={active.name() if active else None}")
    project.removeMapLayer(layer('extra').id())
    return lambda: layer('extra') is None and tasks_idle()


def badge_matches_current():
    """The badge names the kind of the panel's layer (a vector backend badge only for a vector layer)."""
    active, text = coverage().active_layer, badge_text()
    if active is not None:
        return text.startswith('Raster' if isinstance(active, QgsRasterLayer) else 'Point cloud')
    return text.startswith('Vector') or text == '...'


def s_raster_badge_removed_check():
    # The panel may move to another layer when one is removed: the badge then follows that layer.
    active = coverage().active_layer
    check('badge kept after a layer is removed (or follows the layer the panel moved to)',
          badge_text() == STATE['raster_badge'] if layer_name(active) == 'dem' else badge_matches_current(),
          f"badge={badge_text()!r} coverage={layer_name(active)} current={layer_name(dock().current_layer)}")


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


def pick_vector(name):
    dock().comboBox_filtering_current_layer.setLayer(layer(name))
    return switched_to(name, coverage_page=False)


def single_picker():
    return dock().mFeaturePickerWidget_exploring_single_selection


def picker_rows():
    from qgis.PyQt.QtWidgets import QComboBox
    return single_picker().findChild(QComboBox).count()


def picked_fid():
    feature = single_picker().feature()
    return feature.id() if feature.isValid() else None


def waits(seconds, condition=lambda: True):
    since = time.time()
    return lambda: time.time() - since > seconds and condition()


def buffer_box():
    return dock().mQgsDoubleSpinBox_filtering_buffer_value


def s_switch_setup():
    """Vector -> vector layer changes: two more layers, each with its own key field (a link
    filter built on one is an unknown field on the other). QGIS keeps the filter and the feature
    id of QgsFeaturePickerWidget across setLayer(): the next layer showed no feature, or one the
    user never picked. Nothing covered a change between two vector layers until November 2026."""
    from osgeo import ogr, osr
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(2154)

    def write(name, pk, kind, wkt, count):
        path = os.path.join(tempfile.mkdtemp(prefix='fm_switch_'), f'{name}.gpkg')
        source = ogr.GetDriverByName('GPKG').CreateDataSource(path)
        table = source.CreateLayer(name, srs, kind, options=[f'FID={pk}'])
        table.CreateField(ogr.FieldDefn('label', ogr.OFTString))
        table.CreateField(ogr.FieldDefn('ref', ogr.OFTInteger))
        for index in range(1, count + 1):
            feature = ogr.Feature(table.GetLayerDefn())
            feature.SetField('label', f'{name}_{index}')
            feature.SetField('ref', index * 10)
            feature.SetGeometry(ogr.CreateGeometryFromWkt(wkt.format(x=index * 100, x2=index * 100 + 50)))
            table.CreateFeature(feature)
        source = None
        return QgsVectorLayer(f'{path}|layername={name}', name, 'ogr')

    polygon = 'POLYGON(({x} 0,{x2} 0,{x2} 50,{x} 50,{x} 0))'
    STATE['write_switch_layer'] = lambda name: write(name, 'pk_late', ogr.wkbPolygon, polygon, 4)
    project.addMapLayers([write('parcels', 'pk_parcel', ogr.wkbPolygon, polygon, 7),
                          write('wells', 'pk_well', ogr.wkbPoint, 'POINT({x} 0)', 5)])
    return lambda: registered('parcels', 'wells') and tasks_idle()


def s_switch_zones():
    return pick_vector('zones')  # layers added: QGIS made one current, the dock follows it (auto current layer)


def s_switch_multiple():
    dock().mGroupBox_exploring_multiple_selection.setChecked(True)
    return waits(2.5, tasks_idle)


def s_switch_link():
    fids = sorted(feature.id() for feature in layer('zones').getFeatures())[:2]
    dock().widgets['EXPLORING']['MULTIPLE_SELECTION_FEATURES']['WIDGET'].setCheckedFeatureIds(fids)
    return waits(0.5, lambda: bool(single_picker().filterExpression()))


def s_switch_to_parcels():
    check('linking: features checked in multiple selection filter the single selection picker',
          bool(single_picker().filterExpression()), repr(single_picker().filterExpression()))
    return pick_vector('parcels')


def s_switch_parcels_check():
    return waits(0, lambda: picker_rows() >= 7)


def s_switch_parcels_values():
    picker = single_picker()
    check('vector -> vector: the picker is on the new layer, without the link filter of the previous one',
          picker.layer() is not None and picker.layer().name() == 'parcels' and not picker.filterExpression(),
          f"filter={picker.filterExpression()!r}")
    check('vector -> vector: the single selection list shows the features of the new layer', picker_rows() >= 7,
          f"rows={picker_rows()}")
    check('vector -> vector: no feature selected that the user never picked', picked_fid() is None, f"fid={picked_fid()}")
    dock().mFieldExpressionWidget_exploring_single_selection.setField('ref')
    picker.setFeature(3)
    buffer_box().setValue(-5)
    return waits(1.5, tasks_idle)


def s_switch_to_wells():
    check('negative buffer accepted on a polygon layer', buffer_box().value() == -5, str(buffer_box().value()))
    return pick_vector('wells')


def s_switch_wells_check():
    check('polygon -> point: no negative buffer left, none possible', buffer_box().minimum() == 0
          and buffer_box().value() == 0, f"minimum={buffer_box().minimum()} value={buffer_box().value()}")
    check('vector -> vector: the feature picked on the previous layer is not carried over', picked_fid() is None,
          f"fid={picked_fid()}")
    return pick_vector('parcels')


def s_switch_back_check():
    check('point -> polygon: negative buffers possible again', buffer_box().minimum() < 0, str(buffer_box().minimum()))
    stored = app().PROJECT_LAYERS[layer('parcels').id()]['exploring']['single_selection_expression']
    check('vector -> vector: the display field chosen for a layer survives the round trip',
          'ref' in single_picker().displayExpression() and 'ref' in stored,
          f"display={single_picker().displayExpression()!r} stored={stored!r}")
    picker = single_picker()
    picker.setFeature(2)
    STATE['switch_fid'] = 2
    return waits(1, tasks_idle)


def s_switch_same_layer_reload():
    target = layer('parcels')
    dock()._reload_exploration_widgets(target, app().PROJECT_LAYERS[target.id()])  # what follows a filter
    return waits(1, tasks_idle)


def s_switch_same_layer_check():
    check('reload on the same layer: the picked feature stays', picked_fid() == STATE['switch_fid'], f"fid={picked_fid()}")
    late = STATE['write_switch_layer']('late_pick')
    project.addMapLayer(late)
    check('layer not registered yet when picked', late.id() not in app().PROJECT_LAYERS)
    dock().current_layer_changed(late, manual_change=True)
    return switched_to('late_pick', coverage_page=False)


def s_switch_late_check():
    current = dock().current_layer
    check('vector layer picked before its registration: shown once registered',
          current is not None and current.name() == 'late_pick', current.name() if current else 'no layer')


def s_partial_undo_setup():
    """2026-11-14: Undo without the layers to filter restores the current layer alone, and it popped the whole step
    of a filter that had filtered other layers: they kept their filter and lost their step. A filter from zones to a
    vector target, Undo on zones, then the target current and Undo: the target gets back its state before."""
    from osgeo import ogr, osr
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(2154)
    path = os.path.join(tempfile.mkdtemp(prefix='fm_partial_'), 'blocks.gpkg')
    source = ogr.GetDriverByName('GPKG').CreateDataSource(path)
    table = source.CreateLayer('blocks', srs, ogr.wkbPolygon)
    table.CreateField(ogr.FieldDefn('label', ogr.OFTString))
    for label, (xmin, ymin, xmax, ymax) in (('in_east_a', (700720, 6599420, 700780, 6599480)),
                                            ('far', (700300, 6599950, 700350, 6599990))):
        feature = ogr.Feature(table.GetLayerDefn())
        feature.SetField('label', label)
        feature.SetGeometry(ogr.CreateGeometryFromWkt(
            f"POLYGON(({xmin} {ymin},{xmax} {ymin},{xmax} {ymax},{xmin} {ymax},{xmin} {ymin}))"))
        table.CreateFeature(feature)
    source = None
    # zones is still filtered to east_a by the steps before: from no filter, its Undo is seen to change it
    layer('zones').setSubsetString('')
    project.addMapLayer(QgsVectorLayer(f'{path}|layername=blocks', 'blocks', 'ogr'))
    return lambda: registered('blocks') and tasks_idle()


def s_partial_undo_source():
    return pick_vector('zones')


def s_partial_undo_select():
    d = dock()
    d.mGroupBox_exploring_single_selection.setChecked(True)
    east_a = next(feature for feature in layer('zones').getFeatures() if feature['name'] == 'east_a')
    d.mFeaturePickerWidget_exploring_single_selection.setFeature(east_a.id())
    set_targets(['blocks'])
    set_predicates(['Intersect'])
    ready = targets_ready(['blocks'])
    return lambda: bool(dock().get_current_features()[0]) and ready()


def s_partial_undo_filter():
    before = STATE['partial_before'] = {name: layer(name).subsetString() for name in ('zones', 'blocks')}
    run_task('filter')
    return lambda: layer('blocks').subsetString() != before['blocks'] and tasks_idle()


def s_partial_undo_on_source():
    d, before = dock(), STATE['partial_before']
    zones, blocks = layer('zones'), layer('blocks')
    filtered = STATE['partial_filtered'] = {name: layer(name).subsetString() for name in ('zones', 'blocks')}
    entry = app().history_manager.peek_undo()
    check('partial undo: the filter from zones filtered the target, one step for both',
          filtered['zones'] != before['zones'] and filtered['blocks'] != before['blocks'] and entry is not None
          and set(entry.layer_ids) == {zones.id(), blocks.id()},
          f"filtered={filtered} step={entry.layer_ids if entry else None}")
    d.pushButton_checkable_filtering_layers_to_filter.setChecked(False)
    run_task('undo')
    return settled()


def s_partial_undo_on_source_check():
    d, before, filtered = dock(), STATE['partial_before'], STATE['partial_filtered']
    zones, blocks = layer('zones'), layer('blocks')
    history = app().history_manager
    rest, part = history.peek_undo(), history.peek_redo()
    check('partial undo: zones alone restored, the target keeps its filter and its step',
          zones.subsetString() == before['zones'] and blocks.subsetString() == filtered['blocks']
          and rest is not None and rest.layer_ids == (blocks.id(),) and part is not None
          and part.layer_ids == (zones.id(),),
          f"zones={zones.subsetString()!r} blocks={blocks.subsetString()!r} "
          f"rest={rest.layer_ids if rest else None} part={part.layer_ids if part else None}")
    check('partial undo: on zones, Undo waits for the rest of the step, Redo redoes its part',
          not d.pushButton_action_undo_filter.isEnabled() and d.pushButton_action_redo_filter.isEnabled(),
          f"undo={d.pushButton_action_undo_filter.isEnabled()} redo={d.pushButton_action_redo_filter.isEnabled()}")
    return pick_vector('blocks')


def s_partial_undo_on_target():
    check('partial undo: the target current, Undo available', dock().pushButton_action_undo_filter.isEnabled())
    run_task('undo')
    return settled()


def s_partial_undo_on_target_check():
    before, blocks = STATE['partial_before'], layer('blocks')
    history = app().history_manager
    redo = history.get_redo_stack()
    check('partial undo: the target current, Undo gives it back its state before the filter',
          blocks.subsetString() == before['blocks'] and layer('zones').subsetString() == before['zones']
          and [entry.layer_ids for entry in redo[-2:]] == [(layer('zones').id(),), (blocks.id(),)],
          f"blocks={blocks.subsetString()!r} redo={[entry.layer_ids for entry in redo[-2:]]}")
    STATE['removed_blocks'] = blocks.id()
    project.removeMapLayer(blocks.id())  # the steps that follow expect the layers of the switch steps
    return lambda: STATE['removed_blocks'] not in app().PROJECT_LAYERS and tasks_idle()


def s_partial_undo_done():
    return pick_vector('late_pick')


def s_close_dock():
    check('back to a vector layer: vector groups again', dock().mGroupBox_exploring_single_selection.isVisible())
    STATE['coverage_before_close'] = coverage()
    dock().close()  # the X of the dock title bar: run() shows the same dock again
    since = time.time()
    return lambda: not dock().isVisible() and time.time() - since > 1


def s_reopen_dock():
    qgis.utils.plugins[PACKAGE].run()  # the toolbar button
    return settled()


def s_reopen_pick_raster():
    """closeEvent used to tear the controllers down: a raster picked in the reopened dock left the vector
    layer current, without its EXPLORING page."""
    integration = dock()._controller_integration
    check('closing the dock keeps its controllers', dock().isVisible() and integration.registry is not None
          and coverage() is STATE['coverage_before_close'] and coverage_connected(),
          f"registry={integration.registry!r} coverage={coverage()!r}")
    dock().comboBox_filtering_current_layer.setLayer(layer('dem'))
    return switched_to('dem', coverage_page=True)


def layer_name(map_layer):
    try:
        return map_layer.name() if map_layer is not None else None
    except RuntimeError:
        return '<deleted>'


def s_reopen_raster_check():
    d, active = dock(), coverage().active_layer
    check('dock closed and reopened: a raster picked gets its EXPLORING page',
          layer_name(active) == 'dem' and layer_name(d.current_layer) == 'dem' and coverage()._raster_panel.isVisible(),
          f"coverage={layer_name(active)} current={layer_name(d.current_layer)}")
    d.retranslate_all_ui()  # as when the dock is shown again or the language changes: it refreshes the badge
    check('raster current layer keeps its badge when the dock is retranslated', badge_text().startswith('Raster'),
          f"badge={badge_text()!r}")
    # A handler connected twice runs twice: the layer change must run once for one pick.
    STATE['layer_changes'] = 0
    original = d.current_layer_changed

    def counted(*args, **kwargs):
        STATE['layer_changes'] += 1
        return original(*args, **kwargs)
    d.current_layer_changed = counted  # the combo calls it through a lambda: the instance attribute is used
    d.comboBox_filtering_current_layer.setLayer(layer('zones'))
    return switched_to('zones', coverage_page=False)


def s_reopen_vector_check():
    vars(dock()).pop('current_layer_changed', None)  # the class method again
    check('one layer pick runs the dock layer change once', STATE.get('layer_changes') == 1
          and dock().mGroupBox_exploring_single_selection.isVisible(),
          f"current_layer_changed ran {STATE.get('layer_changes')} time(s)")


def config_value_item(path):
    """Value item of a key path (APP, OPTIONS, ...) in the Configuration tab model."""
    parent, item = dock().config_model.invisibleRootItem(), None
    for key in path:
        # A key shown under its _display_name keeps the JSON key in UserRole.
        rows = [row for row in range(parent.rowCount())
                if key in (parent.child(row, 0).data(Qt.ItemDataRole.UserRole), parent.child(row, 0).text())]
        if not rows:
            return None
        item, parent = parent.child(rows[0], 1), parent.child(rows[0], 0)
    return item


def edit_config_choice(path, value):
    """The user picks ``value`` in the combo box of a Configuration tab choice (its delegate's setModelData)."""
    ChoicesType = importlib.import_module(f'{PACKAGE}.ui.widgets.json_view.datatypes').ChoicesType
    item = config_value_item(path)
    choices = item.data(Qt.ItemDataRole.UserRole)['choices']

    class Editor:
        def currentIndex(self):
            return choices.index(value)
    ChoicesType().setModelData(Editor(), item.model(), item.index())


def record_layer_kind_counts():
    """apply_layer_kind_options returns the (point clouds, rasters) counts it (un)registered: record them."""
    a = app()
    if not getattr(a, '_smoke_kind_counts', False):
        original = a.apply_layer_kind_options

        def recorded():
            STATE['kind_counts'] = original()
            return STATE['kind_counts']
        a.apply_layer_kind_options = recorded
        a._smoke_kind_counts = True
    STATE['kind_counts'] = None


def raster_option():
    ENV_VARS = importlib.import_module(f'{PACKAGE}.config.config').ENV_VARS
    return ENV_VARS['CONFIG_DATA']['APP']['OPTIONS']['RASTER']['enabled']['value']


def s_rasters_off():
    """The raster switch of the Configuration tab, edited as a user does (it never reached the app until 5.0)."""
    record_layer_kind_counts()
    edit_config_choice(['APP', 'OPTIONS', 'RASTER', 'enabled'], False)
    return lambda: not registered('dem') and tasks_idle()


def current_layer_list():
    """Layer names of the current-layer combo box (its items read "name [EPSG:xxxx]")."""
    combo = dock().comboBox_filtering_current_layer
    return [str(combo.model().data(combo.model().index(row, 0))).split(' [')[0] for row in range(combo.model().rowCount())]


def s_rasters_off_check():
    in_combo = current_layer_list()
    check('rasters switched off: saved, unregistered and gone from the current-layer list',
          raster_option() is False and not registered('dem') and 'dem' not in in_combo and 'zones' in in_combo
          and STATE['kind_counts'] == (0, 1), f"option={raster_option()} counts={STATE['kind_counts']} combo={in_combo}")
    record_layer_kind_counts()
    edit_config_choice(['APP', 'OPTIONS', 'RASTER', 'enabled'], True)
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


def s_replay_select():
    """A clipped raster target, saved with the project, is clipped again when the project is opened again
    (CoverageModeController.setup connects readProject: it never ran until 5.0)."""
    d = dock()
    d.mGroupBox_exploring_single_selection.setChecked(True)
    east_a = next(feature for feature in layer('zones').getFeatures() if feature['name'] == 'east_a')
    d.mFeaturePickerWidget_exploring_single_selection.setFeature(east_a.id())
    set_targets(['dem'])
    set_predicates(['Intersect'])
    ready = targets_ready(['dem'])
    return lambda: bool(dock().get_current_features()[0]) and ready()


def s_replay_filter():
    run_task('filter')
    return lambda: layer('dem').source().endswith('.vrt') and tasks_idle()


def s_replay_save_and_clear():
    dem = layer('dem')
    check('raster target clipped before the project is saved', dem.source().endswith('.vrt'), f"source=...{dem.source()[-40:]}")
    STATE['project_path'] = os.path.join(tempfile.mkdtemp(prefix='fm_project_'), 'smoke.qgs')
    check('project saved', project.write(STATE['project_path']))
    project.clear()
    since = time.time()
    return lambda: tasks_idle() and time.time() - since > 1


def s_replay_read():
    check('project opened again', project.read(STATE['project_path']))
    return lambda: layer('dem') is not None and layer('dem').source().endswith('.vrt') and registered('zones', 'dem') \
        and tasks_idle()


def s_replay_check():
    dem = layer('dem')
    check('stored raster clip replayed when the project is opened again',
          dem is not None and dem.source().endswith('.vrt') and dem.isValid(),
          f"source=...{dem.source()[-40:] if dem else None}")
    return settled()


def s_remove_layer():
    """Removing a layer from the project unregisters it (the task ignored the ids QGIS sends until 5.0)."""
    STATE['removed_id'] = layer('dem').id()
    project.removeMapLayer(STATE['removed_id'])
    return lambda: STATE['removed_id'] not in app().PROJECT_LAYERS and tasks_idle()


def s_remove_layer_check():
    check('layer removed from the project: unregistered', STATE['removed_id'] not in app().PROJECT_LAYERS
          and 'dem' not in current_layer_list(), f"registered={STATE['removed_id'] in app().PROJECT_LAYERS}")
    # The results of a short remove task used to land during its begun slot, which disconnected everything after them.
    check('layer removed from the project: the current-layer combo still answers',
          dock()._signal_connection_states.get('FILTERING.CURRENT_LAYER.layerChanged') is True)


def s_plugin_imports_check():
    """Absolute project imports fail here, not in the unit tests (tests/test_no_bare_project_imports.py)."""
    from unittest import mock
    from qgis.PyQt.QtWidgets import QFileDialog
    d = dock()
    features, expression = d._exploring_ctrl.get_exploring_features(None, custom_expression='"label" IS NOT NULL')
    check('a custom expression gives its features', len(features) == 4, f"{len(features)} feature(s), {expression!r}")
    exploring = app().PROJECT_LAYERS[d.current_layer.id()]['exploring']
    exploring.pop('is_linking', None)
    d._exploring_ctrl.exploring_link_widgets()
    check('a layer saved without is_linking gets the default', 'is_linking' in exploring, str(exploring.get('is_linking')))
    responsiveness = d.CONFIG_DATA.setdefault('APP', {}).setdefault('OPTIONS', {}).setdefault('UI_RESPONSIVENESS', {})
    saved = responsiveness.get('expression_debounce_ms')
    responsiveness['expression_debounce_ms'] = 777
    d.refresh_ui_responsiveness_params()
    check('the expression debounce setting applies', d._expression_debounce_timer.interval() == 777,
          str(d._expression_debounce_timer.interval()))
    responsiveness['expression_debounce_ms'] = saved if saved is not None else 450
    d.refresh_ui_responsiveness_params()
    exporting = d.widgets['EXPORTING']
    for key in ('HAS_LAYERS_TO_EXPORT', 'HAS_DATATYPE_TO_EXPORT', 'HAS_OUTPUT_FOLDER_TO_EXPORT'):
        exporting[key]['WIDGET'].setChecked(True)
    with mock.patch.object(exporting['LAYERS_TO_EXPORT']['WIDGET'], 'checkedItems', return_value=['zones [EPSG:2154]'], create=True), \
            mock.patch.object(QFileDialog, 'getSaveFileName', return_value=('', '')) as save_dialog:
        d._export_dialog_manager.dialog_export_output_path()
    check('one layer and a format: the export asks where to save the file', save_dialog.called)
    for key in ('HAS_LAYERS_TO_EXPORT', 'HAS_DATATYPE_TO_EXPORT', 'HAS_OUTPUT_FOLDER_TO_EXPORT'):
        exporting[key]['WIDGET'].setChecked(False)


def s_custom_matching_nothing():
    d = dock()
    d.mGroupBox_exploring_custom_selection.setChecked(True)
    d.mFieldExpressionWidget_exploring_custom_selection.setExpression('"label" = \'nothing matches\'')
    return waits(1.5, tasks_idle)


def s_custom_matching_nothing_single():
    dock().mGroupBox_exploring_single_selection.setChecked(True)
    return waits(1.5, tasks_idle)


def s_custom_matching_nothing_check():
    check('a custom expression matching nothing does not empty the single selection list once left',
          not single_picker().filterExpression() and picker_rows() >= 4,
          f"filter={single_picker().filterExpression()!r} rows={picker_rows()}")
    dock().mFieldExpressionWidget_exploring_custom_selection.setField('label')


def s_config_search():
    """The search bar of the Configuration tab never ran until November 2026 (import failing in QGIS)."""
    d = dock()
    container = d.config_view_container
    check('Configuration tab: search bar in place', container is not None and d.config_view is container.json_view)
    d.reload_configuration_model()  # the search must read the new model
    container.set_search_text('UI_PROFILE')
    current = d.config_view.currentIndex()
    check('Configuration tab: the search finds a setting, after a reload too',
          current.isValid() and current.data() == 'UI_PROFILE' and container.model is d.config_model and current.model() is d.config_model,
          f"current={current.data() if current.isValid() else None!r}")
    # The dock stylesheet of the section headers (`QToolBox QToolButton`) drew these buttons off their frame.
    d.toolBox_tabTools.setCurrentWidget(d.CONFIGURATION)  # nothing is visible in a closed section
    QApplication.processEvents()
    field = container.findChild(QLineEdit)
    field_buttons = [button for button in field.findChildren(QToolButton) if button.isVisible()]
    check('Configuration tab: search icon and clear button drawn inside the field',
          len(field_buttons) == 2 and all(button.height() <= field.height() for button in field_buttons),
          str([(button.geometry().x(), button.height()) for button in field_buttons]) + f" field height {field.height()}")
    container.set_search_text('')
    shortcuts = {shortcut.key().toString(): shortcut.context() for shortcut in container.findChildren(QShortcut)}
    check('Configuration tab: Ctrl+F and Escape stay inside the search bar, not the whole QGIS window',
          shortcuts == {'Ctrl+F': Qt.ShortcutContext.WidgetWithChildrenShortcut, 'Esc': Qt.ShortcutContext.WidgetShortcut},
          str(shortcuts))


def s_wheel_needs_focus():
    """A wheel turned while a list passed under the pointer changed the feature, without a click."""
    picker = single_picker()
    combo = picker.findChild(QComboBox)
    dock().mGroupBox_exploring_single_selection.setChecked(True)
    picker.setFeature(2)
    focused = QApplication.focusWidget()
    if focused is not None:
        focused.clearFocus()
    STATE['wheel_combo'] = combo
    return waits(1, lambda: picked_fid() == 2)


def _wheel_on(widget):
    centre = widget.rect().center()
    event = QWheelEvent(QPointF(centre), QPointF(widget.mapToGlobal(centre)), QPoint(0, 0), QPoint(0, -120),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(widget, event)
    return event


def s_wheel_needs_focus_check():
    combo = STATE['wheel_combo']
    index = combo.currentIndex()
    event = _wheel_on(combo)
    check('wheel over a list without the focus: value kept, the panel gets the event',
          combo.currentIndex() == index and not event.isAccepted(), f"index {index} -> {combo.currentIndex()}")
    iface.mainWindow().activateWindow()
    combo.setFocus()
    QApplication.processEvents()
    if combo.hasFocus() or combo.isAncestorOf(QApplication.focusWidget()):
        _wheel_on(combo)
        check('wheel over a list with the focus: it changes as usual', combo.currentIndex() != index,
              f"index {index} -> {combo.currentIndex()}")
    else:
        report('SKIP', 'wheel over a list with the focus', 'no focus under Xvfb')


def headers_height(toolbox):
    heights = {b.height() for b in toolbox.findChildren(QAbstractButton) if b.objectName() == 'qt_toolbox_toolboxbutton'}
    return heights.pop() if len(heights) == 1 else -1


BOARD_TEXTS = {
    'fr': {
        'communes': 'Garde les communes de plus de 10 000 habitants',
        'filter_communes': 'Filtre sur communes',
        'communes_kept': '12 communes gardées sur 586. Les plus peuplées sont **Toulouse**, Colomiers et Tournefeuille.',
        'buildings': 'Et les bâtiments qui sont dedans',
        'filter_buildings': 'Filtre sur batiments par communes',
        'within': 'Are within · 12 communes',
        'buildings_kept': '38 412 bâtiments gardés dans ces 12 communes.',
        'near_roads': 'Les bâtiments à moins de 50 m des routes sélectionnées',
        'steps': ('Lecture des champs de batiments', 'Lecture de la carte · 3 routes sélectionnées',
                  'Filtre sur batiments par routes · tampon 50 m'),
        'parcels': "Les parcelles de plus d'un hectare",
        'select_roads': 'Sélection de 3 routes',
        'which_layers': 'Quelles couches contient ce projet ?',
        'style_roads': 'Mets les routes en valeur sur la carte',
        'questions': [
            {'header': 'Couche', 'question': 'Deux couches portent des routes. Laquelle mettre en valeur ?',
             'options': [{'label': 'troncon_de_route (recommandé)', 'description': 'BD TOPO, 48 210 tronçons'},
                         {'label': 'routes_departementales', 'description': '312 tronçons'},
                         {'label': 'Les deux'}]}],
    },
    'en': {
        'communes': 'Keep the communes of more than 10,000 people',
        'filter_communes': 'Filter on communes',
        'communes_kept': '12 communes kept out of 586. The largest are **Toulouse**, Colomiers and Tournefeuille.',
        'buildings': 'And the buildings inside them',
        'filter_buildings': 'Filter on batiments by communes',
        'within': 'Are within · 12 communes',
        'buildings_kept': '38,412 buildings kept in these 12 communes.',
        'near_roads': 'The buildings less than 50 m from the selected roads',
        'steps': ('Reading the fields of batiments', 'Reading the map · 3 roads selected',
                  'Filter on batiments by roads · buffer 50 m'),
        'parcels': 'The parcels larger than one hectare',
        'select_roads': 'Selection of 3 roads',
        'which_layers': 'Which layers does this project hold?',
        'style_roads': 'Make the roads stand out on the map',
        'questions': [
            {'header': 'Layer', 'question': 'Two layers hold roads. Which one should stand out?',
             'options': [{'label': 'troncon_de_route (recommended)', 'description': 'BD TOPO, 48,210 sections'},
                         {'label': 'routes_departementales', 'description': '312 sections'},
                         {'label': 'Both'}]}],
    },
}


def capture_boards(d, chat, folder):
    """The states of the mockup boards, one image each, to compare with the mockup (FM_BOARDS=folder).

    FM_BOARDS_LANG=en writes the requests and answers of the example in English (the site's English guide);
    French by default, as the mockup."""
    import time as _time
    t = BOARD_TEXTS['en' if os.environ.get('FM_BOARDS_LANG') == 'en' else 'fr']
    from qgis.PyQt.QtWidgets import QDialog as _Dialog
    panel = chat.panel
    shot = lambda name, widget=None: (QApplication.processEvents(), (widget or d).grab().save(
        os.path.join(folder, f"{name}.png")))
    destination = 'Claude · haiku-5-5'
    was_floating, size = d.isFloating(), d.size()
    d.setFloating(True)
    d.resize(int(os.environ.get('FM_BOARD_W', '360')), int(os.environ.get('FM_BOARD_H', '720')))
    panel.clear_thread()
    panel.set_status('')
    header = getattr(chat, '_header_label', None)  # the destination sits in the AGENT header, as the controller puts it
    if header is not None:
        header.setText('')
    panel.set_ready(False)
    panel.show_thread()
    shot('Welcome')
    if header is not None:
        header.setText(destination)
    panel.set_ready(True, '' if header is not None else destination)
    shot('Ready')
    panel.add_user(t['communes'])
    panel.add_action(t['filter_communes'], True, '"population" > 10000', '12 / 586', ('communes',))
    panel.add_text(t['communes_kept'])
    panel.end_answer()
    panel.add_user(t['buildings'])
    panel.add_action(t['filter_buildings'], True, t['within'], '38 412', ('batiments', 'communes'))
    panel.add_text(t['buildings_kept'])
    panel.end_answer()
    panel.set_can_undo(True)
    panel.show_thread()
    shot('Main')
    panel.clear_thread()
    panel.add_user(t['near_roads'])
    for step in t['steps']:
        panel.add_step(step)
    panel.set_working(True)
    panel.show_thread()
    shot('Working')
    panel.set_working(False)
    panel.clear_thread()
    panel.add_user(t['parcels'])
    panel.input.setText(t['parcels'])
    panel.show_error('The provider refused the API key (401).',
                     'The request is back in the line below: fix the settings, then send it again.', True)
    panel.show_thread()
    shot('Error')
    panel.input.clear()
    panel.set_status('')
    now = _time.time()
    panel.set_history([
        {'time': now - 600, 'request': t['parcels'], 'layers': ['parcelles'], 'applied': False},
        {'time': now - 420, 'request': t['communes'], 'layers': ['communes'], 'applied': True},
        {'time': now - 360, 'request': t['buildings'], 'layers': ['batiments'], 'applied': True,
         'steps': [t['filter_buildings'], t['select_roads']]},
        {'time': now - 180, 'request': t['which_layers'], 'layers': [], 'applied': False},
    ], True, False)
    panel.show_history()
    shot('History')
    panel.show_thread()
    # The cards of the thread: the questions of ask_user, then the offer to set FilterMate up.
    controller = importlib.import_module(f'{PACKAGE}.ui.controllers.agent_chat_controller')
    parse_questions = importlib.import_module(f'{PACKAGE}.core.agent.questions').parse_questions
    panel.clear_thread()
    panel.add_user(t['style_roads'])
    panel.add_question_card({'other': controller._tr('Other'), 'answer': controller._tr('Answer'),
                             'no_answer': controller._tr('No answer'),
                             'close': controller._tr('Close without answering')}, parse_questions(t['questions']))
    panel.show_thread()
    shot('Question')
    panel.clear_thread()
    chat._show_setup_offer()
    panel.show_thread()
    QApplication.processEvents()
    bar = panel.thread.verticalScrollBar() if hasattr(panel.thread, 'verticalScrollBar') else None
    if bar is not None:
        bar.setValue(bar.minimum())  # from its heading
    shot('Setup')
    chat._settings_cards.clear()
    chat._setup_card = None
    panel.clear_thread()
    settings = importlib.import_module(f'{PACKAGE}.adapters.agent.settings')
    load_settings, target_of = settings.load_settings, settings.target_of
    AgentSettingsDialog = importlib.import_module(f'{PACKAGE}.ui.widgets.agent_panel').AgentSettingsDialog
    dialog = AgentSettingsDialog(load_settings(), target_of, d)
    dialog.resize(440, 660)
    dialog.show()
    QApplication.processEvents()
    shot('Settings', dialog)
    dialog.tabs.setCurrentIndex(1)
    shot('Sources', dialog)
    dialog.done(_Dialog.DialogCode.Rejected)
    panel.clear_thread()
    d.setFloating(was_floating)
    d.resize(size)
    QApplication.processEvents()


def s_agent_panel():
    """Two stacks: AGENT / EXPLORING above, FILTERING / EXPORTING / CONFIGURATION below, and their rules."""
    d = dock()
    plugin = qgis.utils.plugins[PACKAGE]
    toolbox = d.toolBox_tabTools
    sections = getattr(d, '_fm_sections', None)
    if not check('stacks: set up', sections is not None):
        return
    check('agent: shown by default', getattr(d, '_agent_chat', None) is not None and 'agent' in sections._headers)
    toolbox.setCurrentWidget(d.FILTERING)
    QApplication.processEvents()
    d.select_tabTools_index()
    options = d.CONFIG_DATA['APP']['OPTIONS']
    previous = options.get('AGENT')
    options['AGENT'] = {'enabled': {'value': True}}
    d.install_agent_panel(plugin)
    chat = getattr(d, '_agent_chat', None)
    if not check('agent: the section is installed', chat is not None):
        return
    first = chat
    d.install_agent_panel(plugin)
    agent_header = sections._headers['agent']
    exploring_header = sections.exploring_header
    check('agent: installed once', d._agent_chat is first and
          len([h for h in sections.top.findChildren(QPushButton) if h.objectName() == 'pushButton_section_agent']) == 1)
    check('stacks: AGENT shares the top stack with EXPLORING', chat.panel.parentWidget() is sections.top and
          d.frame_exploring.parentWidget() is sections.top)
    top_layout = sections.top.layout()
    check('stacks: AGENT first, EXPLORING second', top_layout.indexOf(agent_header) < top_layout.indexOf(chat.panel)
          < top_layout.indexOf(exploring_header) < top_layout.indexOf(d.frame_exploring),
          str([top_layout.indexOf(w) for w in (agent_header, chat.panel, exploring_header, d.frame_exploring)]))
    # The handle reaches from one stack at its minimum to the other: no size hint floor above (the Minimum policy
    # of EXPLORING held it at 396 px of 905), no cap below (the tool box stopped at 650 px).
    splitter = d.splitter_main
    saved_sizes, total = splitter.sizes(), sum(splitter.sizes())
    collapsible = splitter.childrenCollapsible()
    splitter.setChildrenCollapsible(False)  # the compact profile lets a stack collapse to nothing
    splitter.setSizes([0, total])
    QApplication.processEvents()
    smallest_top = splitter.sizes()[0]
    splitter.setSizes([total, 0])
    QApplication.processEvents()
    smallest_bottom = splitter.sizes()[1]
    splitter.setChildrenCollapsible(collapsible)
    splitter.setSizes(saved_sizes)
    QApplication.processEvents()
    check('splitter: each stack goes down to its minimum', smallest_top <= sections.top.minimumSizeHint().height() + 2
          and smallest_bottom <= splitter.widget(1).minimumHeight() + 2 and d.toolBox_tabTools.maximumHeight() > 10000,
          f"top {smallest_top} (min {sections.top.minimumSizeHint().height()}), bottom {smallest_bottom} "
          f"(min {splitter.widget(1).minimumHeight()}), total {total}")
    # The titles of the lower sections come from the .ui and are translated (FILTRAGE, EXPORT in French): compare
    # with their translation, so that the smoke also passes with --lang fr.
    lower_titles = {page: QCoreApplication.translate('FilterMateDockWidgetBase', name) for page, name in
                    ((d.FILTERING, 'FILTERING'), (d.EXPORTING, 'EXPORTING'), (d.CONFIGURATION, 'CONFIGURATION'))}
    check('stacks: the lower one keeps its three sections in order',
          [toolbox.indexOf(page) for page in lower_titles] == sorted(toolbox.indexOf(page) for page in lower_titles)
          and -1 not in [toolbox.indexOf(page) for page in lower_titles]
          and all(toolbox.itemText(toolbox.indexOf(page)) == title for page, title in lower_titles.items()),
          str([toolbox.itemText(i) for i in range(toolbox.count())]))
    bottom_headers = [b for b in toolbox.findChildren(QAbstractButton)
                      if b.objectName() == 'qt_toolbox_toolboxbutton' and b.isVisibleTo(toolbox)]
    heights = {b.height() for b in bottom_headers} | {exploring_header.height(), agent_header.height()}
    check('stacks: one header height everywhere', len(heights) == 1, str(heights))
    check('stacks: FILTERING open, EXPLORING open, AGENT folded', toolbox.currentWidget() is d.FILTERING and
          sections.is_open('exploring') and not sections.is_open('agent') and exploring_header.isChecked())
    check('agent: FILTERING is still section 0', d.tabTools_current_index == 0, str(d.tabTools_current_index))
    filter_button = d.widgets['ACTION']['FILTER']['WIDGET']
    check('agent: filter button on FILTERING', filter_button.isEnabled())
    shots = os.environ.get('FM_SHOTS')
    if shots:
        d.grab().save(os.path.join(shots, 'agent_folded.png'))
    bar_widget = d.titleBarWidget()
    check('dock: favorites in the title bar', bar_widget is not None and d.favorites_indicator_label.parentWidget() is bar_widget)
    title_items = [w for w in (getattr(bar_widget, 'title', None), d.favorites_indicator_label,
                               getattr(bar_widget, 'float_button', None), getattr(bar_widget, 'close_button', None))
                   if w is not None and w.isVisibleTo(bar_widget)]
    title_centers = [w.geometry().center().y() for w in title_items]
    badge_heights = {w.height() for w in title_items[1:]}
    # The style pixmaps of float and close sat lower than the star badge on Windows.
    check('dock: title, favorites, float and close on one line', len(title_items) >= 3 and
          max(title_centers) - min(title_centers) <= 1 and len(badge_heights) == 1,
          f'centers {title_centers}, badge heights {badge_heights}')
    check('dock: no header row above EXPLORING', d.frame_header is None or d.frame_header.isHidden())
    tag = d.backend_indicator_label
    check('dock: the source tag is in the layer card', tag.parentWidget() is not None and
          tag.parentWidget().objectName() == 'label_exploring_coverage_layer', str(tag.parentWidget()))
    # A large screen: the dimension managers give the lower zone a minimum taller than its headers.
    lower = d.splitter_main.widget(1)
    lower_min = lower.minimumHeight()
    lower.setMinimumHeight(420)
    agent_header.click()
    QApplication.processEvents()
    check('stacks: AGENT opens, EXPLORING and FILTERING fold', sections.is_open('agent') and
          not sections.is_open('exploring') and toolbox.currentWidget() not in (d.FILTERING, d.EXPORTING, d.CONFIGURATION))
    check('agent: its own state', d.tabTools_current_index == -1, str(d.tabTools_current_index))
    check('agent: filter button off here', not filter_button.isEnabled())
    agent_header.click()
    QApplication.processEvents()
    check('stacks: a click on the open AGENT leaves it open', sections.is_open('agent') and agent_header.isChecked()
          and not sections.is_open('exploring') and not exploring_header.isChecked())
    check('stacks: the lower headers stay', all(b.isVisible() for b in bottom_headers))
    QApplication.processEvents()
    span = max(b.geometry().bottom() for b in bottom_headers) - min(b.geometry().top() for b in bottom_headers)
    check('stacks: the open AGENT takes the room, the folded stack keeps its headers only',
          lower.height() <= len(bottom_headers) * 34 + 60 and span <= len(bottom_headers) * 34 + 30,
          f"lower={lower.height()} span={span} min={lower.minimumHeight()}")
    panel = chat.panel
    panel = chat.panel
    check('agent: the welcome is shown', panel.welcome_title.isVisible())
    check('agent: the input is below it', panel.input.geometry().top() > panel.stack.geometry().bottom())
    check('agent: the input takes the width', panel.input.width() > panel.width() * 0.7,
          f"{panel.input.width()} of {panel.width()}")
    headers = [b for b in toolbox.findChildren(QAbstractButton)
               if b.objectName() == 'qt_toolbox_toolboxbutton' and not b.isHidden()]
    headers += [sections.exploring_header, agent_header]
    check('agent: same header height, the lower stack folded too', len({b.height() for b in headers}) == 1,
          str([b.height() for b in headers]))
    if shots:
        d.grab().save(os.path.join(shots, 'agent_welcome.png'))
    panel.set_ready(True, 'Claude (Anthropic) · claude-haiku-5-5')
    QApplication.processEvents()
    if shots:
        d.grab().save(os.path.join(shots, 'agent_ready.png'))
    panel.add_user('Keep the municipalities above 10000 inhabitants')
    panel.add_action('Filter on communes', True, '"population" > 10000', '12 / 586')
    panel.add_text('12 municipalities are kept in the layer.')
    panel.set_can_undo(True)
    panel.set_status('Changed: communes. Changed since, left as is: a very long list of layers that wraps on two lines.')
    QApplication.processEvents()
    page_scroll = panel.parentWidget().parentWidget() if panel.parentWidget() is not None else None
    bar = page_scroll.verticalScrollBar() if isinstance(page_scroll, QScrollArea) else None
    check('agent: the input stays in view with a conversation', panel.input.isVisible() and
          (bar is None or not bar.isVisible()), f"input {panel.input.geometry()} panel h={panel.height()}")
    from qgis.PyQt.QtWidgets import QPushButton as _Button
    card_undo = [b for b in panel.thread.findChildren(_Button, 'pushButton_agent_card_undo') if b.isVisibleTo(panel)]
    check('agent: undo is on the change card', panel.undo_offered() and len(card_undo) == 1, str(card_undo))
    if shots:
        d.grab().save(os.path.join(shots, 'agent_open.png'))
    check('agent: the thread is on the edges of the headers (mockup)', abs(panel.thread.mapTo(d, QPoint(0, 0)).x()
          - agent_header.mapTo(d, QPoint(0, 0)).x()) <= 1 and abs(panel.thread.width() - agent_header.width()) <= 2,
          f"thread x={panel.thread.mapTo(d, QPoint(0, 0)).x()} w={panel.thread.width()} header w={agent_header.width()}")
    if os.environ.get('FM_GEOMETRY'):
        def where(widget):
            top_left = widget.mapTo(d, QPoint(0, 0))
            return f"x={top_left.x()} y={top_left.y()} w={widget.width()} h={widget.height()}"
        for label, widget in (('agent header', agent_header), ('panel', panel), ('stack', panel.stack),
                              ('thread', panel.thread), ('input', panel.input), ('status', panel.status)):
            print(f"GEOMETRY {label}: {where(widget)} margins={widget.contentsMargins().left()},"
                  f"{widget.contentsMargins().top()},{widget.contentsMargins().right()}", flush=True)
        print(f"GEOMETRY panel layout margins={panel.layout().contentsMargins().left()},"
              f"{panel.layout().contentsMargins().top()} sheet={panel.styleSheet()[:0]}", flush=True)
    if os.environ.get('FM_BOARDS'):
        capture_boards(d, chat, os.environ['FM_BOARDS'])
    panel.clear_thread()
    toolbox.setCurrentWidget(d.EXPORTING)
    QApplication.processEvents()
    check('stacks: EXPORTING opens beside AGENT', sections.is_open('agent') and toolbox.currentWidget() is d.EXPORTING
          and d.tabTools_current_index == 1, str(d.tabTools_current_index))
    check('stacks: an open section gets its minimum back', lower.minimumHeight() == 420, str(lower.minimumHeight()))
    lower.setMinimumHeight(lower_min)
    export_header = next(b for b in bottom_headers if b.text() == lower_titles[d.EXPORTING])
    export_header.click()
    QApplication.processEvents()
    check('stacks: a click on the open header folds it', toolbox.currentWidget() not in (d.EXPORTING, d.FILTERING)
          and sections.is_open('agent'))
    filtering_header = next(b for b in bottom_headers if b.text() == lower_titles[d.FILTERING])
    filtering_header.click()
    QApplication.processEvents()
    check('stacks: FILTERING brings EXPLORING back and folds AGENT', toolbox.currentWidget() is d.FILTERING and
          sections.is_open('exploring') and not sections.is_open('agent'))
    exploring_header.click()
    QApplication.processEvents()
    check('stacks: a click on the open EXPLORING leaves it open (one section always open above)',
          sections.is_open('exploring') and exploring_header.isChecked() and not sections.is_open('agent')
          and toolbox.currentWidget() is d.FILTERING)
    sections.open_top(None)
    QApplication.processEvents()
    check('stacks: open_top(None) folds nothing above', sections.is_open('exploring') and exploring_header.isChecked()
          and not agent_header.isChecked())

    # Lot 1 of the undo plan: AGENT open, the action bar walks the steps of the agent.
    target = d.current_layer
    undo_button = d.widgets['ACTION']['UNDO_FILTER']['WIDGET']
    redo_button = d.widgets['ACTION']['REDO_FILTER']['WIDGET']
    if target is not None and hasattr(target, 'subsetString'):
        before = target.subsetString()
        chat._checkpoint.label = 'keep the first feature'
        chat._checkpoint.begin()
        target.setSubsetString('"fid" = 1' if target.fields().indexOf('fid') >= 0 else '1 = 1')
        chat._checkpoint.commit()
        chat._refresh_history()
        changed = target.subsetString()
        agent_header.click()
        QApplication.processEvents()
        check('undo: AGENT open, Undo of the action bar is the step of the agent', undo_button.isEnabled()
              and 'keep the first feature' in undo_button.toolTip(), undo_button.toolTip())
        undo_button.click()
        QApplication.processEvents()
        check('undo: the step is undone from the action bar', target.subsetString() == before
              and redo_button.isEnabled(), target.subsetString())
        d._on_redo_shortcut()
        QApplication.processEvents()
        check('undo: Ctrl+Y applies it again', target.subsetString() == changed, target.subsetString())
        chat._on_undo()
        filtering_header.click()
        QApplication.processEvents()
        check('undo: AGENT folded, the buttons are the dock ones again', 'keep the first feature' not in undo_button.toolTip(),
              undo_button.toolTip())
        target.setSubsetString(before)
    else:
        report('SKIP', 'undo: the action bar on the steps of the agent', 'no vector layer current')
    toolbox.setCurrentWidget(d.FILTERING)
    QApplication.processEvents()
    if previous is None:
        options.pop('AGENT', None)
    else:
        options['AGENT'] = previous


def s_finish():
    failed_extensions = [line for line in _RECENT.lines if 'Failed to load extension' in line]
    check(f"extensions discovered under the plugin folder name '{PACKAGE}'", not failed_extensions,
          '; '.join(failed_extensions[:3]))
    check('no Python error and no FilterMate critical message in the log', not STATE['python_errors'],
          '; '.join(STATE['python_errors'][:3]))
    counts = {status: sum(1 for s, _ in STATE['results'] if s == status) for status in ('PASS', 'FAIL', 'SKIP', 'XFAIL')}
    print(f"\n{counts['PASS']} passed, {counts['FAIL']} failed, {counts['SKIP']} skipped, {counts['XFAIL']} known "
          f"failures in {time.time() - STATE['started']:.1f}s (QGIS {Qgis.QGIS_VERSION}, dock)", flush=True)
    failed = [name for status, name in STATE['results'] if status == 'FAIL']
    if failed:
        print('FAILED: ' + '; '.join(failed), flush=True)
    os._exit(1 if failed else 0)  # QGIS exit code = test result; skips the slow GUI teardown


# --- the agent sets the options of the panels (adapters/public_api/panel_options.py) on the real dock ---------------
# 2026-11-16, review: on a stand-in dock everything passed while the real one emptied the predicates and the buffer
# of the current layer, put the defaults of an unticked export group back, and reset a non-field expression.

PANELS = {}


def panels_module():
    return importlib.import_module(f'{PACKAGE}.adapters.public_api.panel_options')


def s_panels_setup():
    places = QgsVectorLayer('Point?crs=EPSG:2154&field=nom:string&field=code:string', 'lieux', 'memory')
    project.addMapLayer(places)
    return lambda: registered('zones', 'lieux') and tasks_idle()


def current_is(name):
    """Condition: the panel shows ``name`` (a layer added becomes the active layer of QGIS, which the panel follows)."""
    done = switched_to(name, False)
    return lambda: done() and dock().current_layer is not None and dock().current_layer.name() == name


def s_panels_zones():
    iface.setActiveLayer(layer('zones'))
    dock().comboBox_filtering_current_layer.setLayer(layer('zones'))
    return current_is('zones')


def s_panels_set():
    turn_effects = importlib.import_module(f'{PACKAGE}.adapters.agent.turn_effects')
    messages = importlib.import_module(f'{PACKAGE}.core.agent.messages')
    panels, d = panels_module(), dock()
    recorder = turn_effects.EffectsRecorder()
    # What the panel holds before the turn: in the whole smoke, earlier steps left predicates on zones (2026-11-16:
    # the undo put back ['Intersect'] they had set, and a check that wanted [] failed on every image).
    before = app().PROJECT_LAYERS[layer('zones').id()]['filtering']
    PANELS['before'] = (list(before.get('geometric_predicates') or []),
                        list(d.widgets['FILTERING']['GEOMETRIC_PREDICATES']['WIDGET'].checkedItems()),
                        d.project_props['EXPORTING'].get('DATATYPE_TO_EXPORT'), before.get('buffer_value', 0.0))
    layers = [{'layer': 'zones', 'filtering': {'layers_to_filter': ['lieux'], 'geometric_predicates': ['Intersect'],
                                               'buffer_value': 25.0}},
              {'layer': 'lieux', 'exploring': {'single_selection_expression': '"code"'}}]
    recorder.before_call(messages.ToolCallPart('p1', 'set_layer_options', {'layers': layers}))
    recorder.before_call(messages.ToolCallPart('p2', 'set_export_options', {'changes': {}}))
    PANELS['answer'] = panels.set_layer_options(d, layers)
    PANELS['export'] = panels.set_export_options(d, {'datatype_to_export': 'GeoJSON', 'layers_to_export': ['zones']})
    PANELS['recorder'] = recorder
    return settled()


def s_panels_check():
    d = dock()
    w = d.widgets['FILTERING']
    kept = app().PROJECT_LAYERS[layer('zones').id()]['filtering']
    check('panels: the filtering options show on the current layer',
          w['GEOMETRIC_PREDICATES']['WIDGET'].checkedItems() == ['Intersect']
          and abs(w['BUFFER_VALUE']['WIDGET'].value() - 25.0) < 1e-6
          and layer('lieux').id() in (d.get_layers_to_filter() or [])
          and w['HAS_GEOMETRIC_PREDICATES']['WIDGET'].isChecked(),
          f"{w['GEOMETRIC_PREDICATES']['WIDGET'].checkedItems()} {w['BUFFER_VALUE']['WIDGET'].value()} {kept}")
    check('panels: the panel keeps them', kept.get('geometric_predicates') == ['Intersect']
          and kept.get('buffer_value') == 25.0 and PANELS['answer']['shown_in_panel'], str(PANELS['answer']))
    e = d.widgets['EXPORTING']
    d.set_exporting_properties()  # as a switch of tab does
    exporting = d.project_props['EXPORTING']
    check('panels: the export options stay after the panel is refreshed',
          exporting.get('DATATYPE_TO_EXPORT') == 'GeoJSON' and e['HAS_DATATYPE_TO_EXPORT']['WIDGET'].isChecked()
          and e['DATATYPE_TO_EXPORT']['WIDGET'].currentText() == 'GeoJSON'
          and exporting.get('LAYERS_TO_EXPORT') == [layer('zones').id()],
          f"{exporting} {e['DATATYPE_TO_EXPORT']['WIDGET'].currentText()} {PANELS['export']}")
    iface.setActiveLayer(layer('lieux'))
    d.comboBox_filtering_current_layer.setLayer(layer('lieux'))
    return current_is('lieux')


def s_panels_other_layer_check():
    kept = app().PROJECT_LAYERS[layer('lieux').id()]['exploring']
    check('panels: a field set on another layer stays when it is chosen', kept.get('single_selection_expression')
          in ('"code"', 'code'), str(kept))
    effects = PANELS['recorder'].finish()
    PANELS['effects'] = effects
    check('panels: the turn keeps the options before it', sorted(effect[0] for effect in effects)
          == ['export_options', 'layer_options', 'layer_options'], str([effect[:2] for effect in effects]))
    iface.setActiveLayer(layer('zones'))
    dock().comboBox_filtering_current_layer.setLayer(layer('zones'))
    return current_is('zones')


def s_panels_undo():
    turn_effects = importlib.import_module(f'{PACKAGE}.adapters.agent.turn_effects')
    PANELS['undo'] = turn_effects.apply_effects(PANELS['effects'], undo=True)
    return settled()


def s_panels_undo_check():
    d = dock()
    kept = app().PROJECT_LAYERS[layer('zones').id()]['filtering']
    done, left = PANELS['undo']
    predicates, shown, datatype, buffer = PANELS['before']
    check('panels: undo puts the options and the panel back', not left
          and list(kept.get('geometric_predicates') or []) == predicates and abs(kept.get('buffer_value', 0.0) - buffer) < 1e-6
          and d.widgets['FILTERING']['GEOMETRIC_PREDICATES']['WIDGET'].checkedItems() == shown
          and d.project_props['EXPORTING'].get('DATATYPE_TO_EXPORT') == datatype,
          f"done={done} left={left} before={PANELS['before']} {kept} "
          f"{d.project_props['EXPORTING'].get('DATATYPE_TO_EXPORT')}")


PANEL_STEPS = [s_panels_setup, s_panels_zones, s_panels_set, s_panels_check, s_panels_other_layer_check,
               s_panels_undo, s_panels_undo_check]


# --- sources, model and MCP server from the menu "⋯" of the AGENT panel (2026-11-16), on the real panel ----------

OPTIONS = {}


def agent_settings_module():
    return importlib.import_module(f'{PACKAGE}.adapters.agent.settings')


def s_options_menu():
    chat, settings = agent_chat(), agent_settings_module()
    OPTIONS['before'] = settings.load_settings()
    OPTIONS['thread'] = len(chat._transcript)
    chat._fill_options()  # as when the menu opens
    panel = chat.panel
    groups = [action.menu() for action in panel.sources_menu.actions() if action.menu() is not None]
    OPTIONS['groups'] = [menu.title() for menu in groups]
    entry = next(action for menu in groups for action in menu.actions()
                 if action.isCheckable() and not action.isChecked())
    OPTIONS['ticked_name'] = entry.text()
    entry.trigger()  # the user ticks a source in the menu
    return settled()


def s_options_menu_check():
    chat, settings = agent_chat(), agent_settings_module()
    after = settings.load_settings()
    added = [source_id for source_id in after.enabled_sources if source_id not in OPTIONS['before'].enabled_sources]
    check('options: the menu lists the groups of the sources', len(OPTIONS['groups']) >= 3, str(OPTIONS['groups']))
    check('options: a tick in the menu saves the source and keeps the thread',
          len(added) == 1 and len(chat._transcript) == OPTIONS['thread'], f"{added} {OPTIONS['ticked_name']}")
    chat._on_source_toggled(added[0] if added else '', False)  # and untick it again
    check('options: an untick puts it back', settings.load_settings().enabled_sources ==
          OPTIONS['before'].enabled_sources, str(settings.load_settings().enabled_sources))
    has_mcp = chat.panel.mcp_action.isCheckable()
    check('options: the MCP server and the model are in the menu', has_mcp and chat.panel.models_menu.actions(),
          str([action.text() for action in chat.panel.models_menu.actions()]))


OPTION_STEPS = [s_options_menu, s_options_menu_check]


# --- The buttons under their section; a section in its own QGIS panel (ui/layout/section_bars.py, section_panels.py)

SECTION = {}
ACTION_NAMES = ('filter', 'undo_filter', 'redo_filter', 'compare', 'unfilter', 'export', 'qfieldcloud', 'about')
FILTERING_ACTIONS = ACTION_NAMES[:5]
DETACHED_KEY = 'FilterMate/panels/detached'


def action_button(name):
    return getattr(dock(), 'pushButton_action_' + name, None)


def actions_shown():
    """The action buttons on screen, in the order of the bar."""
    return [name for name in ACTION_NAMES if action_button(name) is not None and action_button(name).isVisible()]


def open_section(page):
    """``page`` open in the lower stack; None folds it."""
    d = dock()
    d.toolBox_tabTools.setCurrentWidget(page if page is not None else d._fm_sections._nothing)
    QApplication.processEvents()


def spread(bar):
    """The gaps left of, between and right of the buttons shown in ``bar``."""
    shown = sorted((b for b in bar.findChildren(QPushButton) if b.isVisible()), key=lambda b: b.x())
    if not shown:
        return []
    return ([shown[0].x()] + [after.x() - (before.x() + before.width()) for before, after in zip(shown, shown[1:])]
            + [bar.width() - shown[-1].x() - shown[-1].width()])


def grab_widget(widget, name):
    folder = os.environ.get('FM_GRAB_DIR')
    if folder:
        widget.grab().save(os.path.join(folder, f"{name}.png"))


def bottom_header(page):
    toolbox = dock().toolBox_tabTools
    text = toolbox.itemText(toolbox.indexOf(page))
    return next((button for button in toolbox.findChildren(QAbstractButton)
                 if button.objectName() == 'qt_toolbox_toolboxbutton' and button.text() == text), None)


def panel_place(panel):
    """Where ``panel`` is, seen from the dock: ``tab`` with it, ``below`` it, ``above`` it; None without a panel."""
    if panel is None:
        return None
    d = dock()
    window = iface.mainWindow()
    if panel in window.tabifiedDockWidgets(d):
        return 'tab'
    return 'below' if panel.mapTo(window, QPoint(0, 0)).y() > d.mapTo(window, QPoint(0, 0)).y() else 'above'


def s_section_startup_check():
    """The dock opened with ``sections`` saved and sections left apart (FM_ACTION_BAR, FM_DETACHED): everything is in
    place without a click. Compare is made beside Redo after the bars: it must be in the row of FILTERING."""
    d = dock()
    panels = d._fm_panels
    manager = d._action_bar_manager
    window = iface.mainWindow()
    position, wanted = os.environ.get('FM_ACTION_BAR'), os.environ.get('FM_DETACHED', '')
    QApplication.processEvents()
    grab('startup')
    if position == 'sections':
        bars = manager.section_bars()
        if not check('startup: the buttons are under their section', bars is not None
                     and manager.get_position() == 'sections' and not d.frame_actions.isVisible()):
            return None
        row = bars.frame('filtering')
        held = [name for name in FILTERING_ACTIONS if action_button(name) is not None
                and action_button(name).parentWidget() is row]
        check('startup: FILTERING holds Filter, Undo, Redo, Compare and Unfilter', held == list(FILTERING_ACTIONS),
              str(held))
        if 'filtering' not in wanted:
            open_section(d.FILTERING)
            gaps = spread(row)
            check('startup: they are spread evenly, Compare among them', len(gaps) == 6
                  and max(gaps[1:-1]) - min(gaps[1:-1]) <= 3 and abs(gaps[0] - gaps[-1]) <= 3, str(gaps))
    if wanted:
        expected = tuple(key for key in ('agent', 'filtering', 'exporting', 'configuration') if key in wanted
                         and (key != 'agent' or 'agent' in d._fm_sections._headers))
        check('startup: the sections left apart are in their panels', panels.detached() == expected
              and all(panels.panel(key).isVisible() or panel_place(panels.panel(key)) == 'tab' for key in expected),
              f"{panels.detached()} expected {expected}")
        if 'filtering' in expected:
            panel = panels.panel('filtering')
            panels.raise_panel('filtering')
            QApplication.processEvents()
            gaps = spread(manager.section_bars().frame('filtering'))
            check('startup: the panel of FILTERING has its buttons, evenly spread, and they act',
                  all(panel.isAncestorOf(action_button(name)) for name in FILTERING_ACTIONS)
                  and len(gaps) == 6 and max(gaps[1:-1]) - min(gaps[1:-1]) <= 3 and action_button('filter').isEnabled(),
                  str(gaps))
            grab_widget(panel, 'startup_panel_filtering')
        check('startup: what is apart stays saved', QSettings().value(DETACHED_KEY) == wanted,
              str(QSettings().value(DETACHED_KEY)))
        menu = window.findChild(QMenu, 'mPanelMenu')
        check('startup: the panels are listed in the menu of the panels of QGIS', menu is not None
              and all(panels.panel(key).toggleViewAction() in menu.actions() for key in expected), f"menu={menu}")
    return None


def s_section_setup():
    """The layers the steps below filter: the raster target an earlier step removed comes back."""
    if layer('dem') is None:
        project.addMapLayer(QgsRasterLayer(M['dem'], 'dem', 'gdal'))
    return lambda: registered('zones', 'dem') and tasks_idle()


def s_section_bars():
    """ACTION_BAR_POSITION = sections: each section shows its own buttons while it is open, no bar for all."""
    d = dock()
    manager = d._action_bar_manager
    QSettings().remove(DETACHED_KEY)
    open_section(d.FILTERING)
    SECTION['all'] = actions_shown()
    SECTION['position'] = manager.get_position()
    grab('sections_before')
    manager.set_position('sections')  # what the configuration does when the setting changes
    QApplication.processEvents()
    grab('sections_filtering')
    bars = manager.section_bars()
    if not check('sections: the position is taken', bars is not None and manager.get_position() == 'sections'):
        return None
    expected = [name for name in FILTERING_ACTIONS if name in SECTION['all']]
    check('sections: FILTERING shows Filter, Undo, Redo, Compare and Unfilter', actions_shown() == expected,
          str(actions_shown()))
    check('sections: no bar for all', not d.frame_actions.isVisible())
    bar = bars.frame('filtering')
    gaps = spread(bar)
    check('sections: the buttons of FILTERING are spread evenly', len(gaps) == len(expected) + 1
          and max(gaps[1:-1]) - min(gaps[1:-1]) <= 3 and abs(gaps[0] - gaps[-1]) <= 3, str(gaps))
    below = d.height() - (bar.mapTo(d, QPoint(0, 0)).y() + bar.height())
    check('sections: the bar is at the bottom of the dock, where the bar for all was', 0 <= below <= 12, str(below))
    check('sections: the buttons of FILTERING act', all(action_button(name).isEnabled() for name in ('filter', 'unfilter')))
    open_section(d.EXPORTING)
    grab('sections_exporting')
    expected = [name for name in ('export', 'qfieldcloud') if name in SECTION['all']]
    check('sections: EXPORTING shows Export (and QFieldCloud with its extension)', actions_shown() == expected,
          str(actions_shown()))
    gaps = spread(bars.frame('exporting'))
    check('sections: Export is centred in its bar', len(gaps) >= 2 and abs(gaps[0] - gaps[-1]) <= 3, str(gaps))
    check('sections: Export acts', action_button('export').isEnabled())
    open_section(d.CONFIGURATION)
    check('sections: CONFIGURATION shows About', actions_shown() == ['about'], str(actions_shown()))
    open_section(None)
    grab('sections_nothing_open')
    check('sections: nothing open below, no button and no bar', actions_shown() == [] and not d.frame_actions.isVisible()
          and not any(bars.frame(key).isVisible() for key in ('filtering', 'exporting', 'configuration')),
          str(actions_shown()))
    if action_button('qfieldcloud') is None:
        # A button that comes late, as QFieldCloud does: its extension puts it in the bar for all, after the dock.
        late = QPushButton(d.frame_actions)
        late.setObjectName('pushButton_action_qfieldcloud')
        late.setFixedSize(action_button('export').size())
        d.frame_actions.layout().addWidget(late)
        d.pushButton_action_qfieldcloud = late
        open_section(d.EXPORTING)  # select_tabTools_index, which the extension calls too
        row = bars.frame('exporting')
        check('sections: a button that comes late joins its section, after Export', late.parentWidget() is row
              and late.isVisible() and late.x() > action_button('export').x(), str(actions_shown()))
        late.hide()  # the extension turned off
        d.select_tabTools_index()
        QApplication.processEvents()
        gaps = spread(row)
        check('sections: hidden, it stays hidden and Export is centred again', not late.isVisible()
              and actions_shown() == ['export'] and len(gaps) == 2 and abs(gaps[0] - gaps[-1]) <= 3, str(gaps))
        late.show()
        manager.set_position('bottom')
        QApplication.processEvents()
        check('sections: back in the bar for all, it is after Export and before About',
              late.parentWidget() is d.frame_actions and action_button('export').x() < late.x() < action_button('about').x(),
              f"{action_button('export').x()} {late.x()} {action_button('about').x()}")
        d.frame_actions.layout().removeWidget(late)
        d.pushButton_action_qfieldcloud = None
        late.setParent(None)
        late.deleteLater()
        manager.set_position('sections')
        QApplication.processEvents()
    open_section(d.FILTERING)
    manager.set_position(SECTION['position'])
    QApplication.processEvents()
    held = [name for name in ACTION_NAMES if action_button(name) is not None
            and action_button(name).parentWidget() is d.frame_actions]
    order = sorted(actions_shown(), key=lambda name: action_button(name).x())
    check('sections: back to the bar for all, every button in it and in order', d.frame_actions.isVisible()
          and actions_shown() == SECTION['all'] and order == SECTION['all']
          and held == [name for name in ACTION_NAMES if action_button(name) is not None],
          f"shown={actions_shown()} order={order} held={held}")
    check('sections: Export is off again while FILTERING is open', not action_button('export').isEnabled()
          and action_button('filter').isEnabled())
    grab('sections_after')
    return None


def s_section_detach():
    """FILTERING in its own QGIS panel: its widgets and its buttons go there, and act whatever the dock shows."""
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    toolbox = d.toolBox_tabTools
    open_section(d.FILTERING)
    index = toolbox.indexOf(d.FILTERING)
    check('panels: FILTERING can leave the dock, EXPLORING cannot', panels.can_detach('filtering')
          and not panels.can_detach('exploring'))
    icons = d._icon_manager.refresh_all_icons() if getattr(d, '_icon_manager', None) is not None else -1
    set_ui_profile('normal')  # the profile that asks the dock for the most height
    QApplication.processEvents()
    minimum = d.minimumHeight()
    detached = panels.detach('filtering')
    QApplication.processEvents()
    in_panel = panels.panel('filtering')
    if in_panel is not None:
        again = d._icon_manager.refresh_all_icons() if icons >= 0 else -1
        check('panels: a change of theme still redraws the icons of the section apart', again == icons
              and action_button('filter') in d.findChildren(QPushButton), f"{icons} icons before, {again} after")
        check('panels: F5, Ctrl+Z and Ctrl+Y work with the focus in the panel',
              len(getattr(in_panel, 'shortcuts', None) or []) == 3)
        check('panels: the dock gives up the minimum height of its profile, for what its contents need',
              minimum > 0 and d.minimumHeight() < minimum and panels._dock_minimum == minimum,
              f"normal profile {minimum} -> {d.minimumHeight()}, kept={panels._dock_minimum}")
        set_ui_profile('auto')
        QApplication.processEvents()
        sections = d._fm_sections
        if 'agent' in sections._headers:
            sections.open_top('agent')
            QApplication.processEvents()
            check('panels: with AGENT open in the dock, Undo and Redo of the panel stay with FILTERING',
                  sections.is_open('agent') and not d.agent_has_focus())
            sections.open_top('exploring')
            QApplication.processEvents()
    panel = panels.panel('filtering')
    if not check('panels: FILTERING is in a panel of QGIS', detached and panel is not None and panel.parent() is window
                 and panel.objectName() == 'FilterMatePanel_filtering' and panel.isVisible(),
                 f"detached={detached} panel={panel}"):
        return None
    check('panels: its widgets are those of the dock, moved', panel.isAncestorOf(d.FILTERING)
          and not d.isAncestorOf(d.FILTERING) and d.FILTERING.isVisible()
          and d.comboBox_filtering_current_layer.isVisible())
    header = bottom_header(d.FILTERING)
    check('panels: its place in the tool box is kept, its header hidden', toolbox.indexOf(d.FILTERING) == index
          and toolbox.currentWidget() is d._fm_sections._nothing and header is not None and not header.isVisible(),
          f"index={toolbox.indexOf(d.FILTERING)} current={toolbox.currentWidget().objectName()}")
    filtering = [name for name in FILTERING_ACTIONS if action_button(name) is not None]
    check('panels: its buttons went with it', all(panel.isAncestorOf(action_button(name)) for name in filtering)
          and all(action_button(name).isVisible() for name in filtering))
    check('panels: they act with nothing open in the dock', action_button('filter').isEnabled()
          and action_button('unfilter').isEnabled() and d.filtering_detached)
    check('panels: the other buttons stay in the bar of the dock', d.frame_actions.isVisible()
          and action_button('export').parentWidget() is d.frame_actions
          and action_button('about').parentWidget() is d.frame_actions and not action_button('export').isEnabled(),
          str(actions_shown()))
    check('panels: below the dock the first time, in its dock area', window.dockWidgetArea(panel) == window.dockWidgetArea(d)
          and panel_place(panel) == 'below' and not panel.isFloating(),
          f"place={panel_place(panel)} dock={d.height()} minimum={d.minimumSizeHint().height()}/{d.minimumHeight()} "
          f"docks={[(w.objectName(), w.height()) for w in window.findChildren(QDockWidget) if w.isVisible()]}")
    sheet = panel.widget().styleSheet()
    check('panels: the panel has the style sheet of the dock', len(sheet) > 100 and sheet == d.dockWidgetContents.styleSheet()
          and panel.widget().objectName() == 'dockWidgetContents', str(len(sheet)))
    check('panels: what is apart is remembered', QSettings().value(DETACHED_KEY) == 'filtering',
          str(QSettings().value(DETACHED_KEY)))
    toolbox.setCurrentWidget(d.FILTERING)  # a script, or the agent, opens FILTERING
    QApplication.processEvents()
    check('panels: FILTERING asked to open shows its panel, the dock stays folded',
          toolbox.currentWidget() is d._fm_sections._nothing and panel.isVisible())
    open_section(d.EXPORTING)
    check('panels: EXPORTING open in the dock, Export and Filter both act', action_button('export').isEnabled()
          and action_button('filter').isEnabled())
    open_section(None)
    grab_widget(panel, 'panel_filtering')
    grab('dock_filtering_apart')
    headers = sorted((bottom_header(page) for page in (d.EXPORTING, d.CONFIGURATION)), key=lambda button: button.y())
    stack = d.splitter_main.widget(1)
    last = headers[-1].mapTo(stack, QPoint(0, headers[-1].height())).y()
    gap = headers[1].y() - (headers[0].y() + headers[0].height())
    check('panels: the headers left in the dock keep their gap, the last one is whole',
          gap == toolbox.layout().spacing() and last <= stack.height(), f"gap={gap} last={last} stack={stack.height()}")
    check('panels: the panel has room for its section', panel.height() >= 180,
          f"panel={panel.height()} dock={d.height()} dock minimum={d.minimumSizeHint().height()} "
          f"window={window.height()} floating={d.isFloating()}")
    return None


def s_section_filter():
    """The Filter button of the panel filters (the selection of s_vector_select)."""
    action_button('filter').click()
    return lambda: layer('dem').source().endswith('.vrt') and tasks_idle()


def s_section_filter_check():
    dem = layer('dem')
    check('panels: Filter in the panel of FILTERING clips the raster target', dem.source().endswith('.vrt')
          and dem.isValid(), f"source=...{dem.source()[-40:]}")
    return settled()


def s_section_undo():
    undo = action_button('undo_filter')
    check('panels: Undo acts in the panel, with nothing open in the dock', undo.isEnabled()
          and dock().tabTools_current_index != 0, f"enabled={undo.isEnabled()} index={dock().tabTools_current_index}")
    undo.click()
    return lambda: not layer('dem').source().endswith('.vrt') and tasks_idle()


def s_section_undo_check():
    check('panels: Undo in the panel puts the raster target back',
          os.path.normpath(layer('dem').source()) == os.path.normpath(M['dem']), layer('dem').source())
    return settled()


def s_section_stack():
    """EXPORTING and CONFIGURATION join FILTERING as tabs, AGENT leaves too: the dock keeps EXPLORING."""
    d = dock()
    panels = d._fm_panels
    sections = d._fm_sections
    window = iface.mainWindow()
    filtering = panels.panel('filtering')
    if not check('panels: FILTERING is still apart', filtering is not None):
        return None
    check('panels: EXPORTING leaves the dock', panels.detach('exporting'))
    QApplication.processEvents()
    exporting = panels.panel('exporting')
    check('panels: EXPORTING is tabbed with FILTERING', exporting is not None
          and exporting in window.tabifiedDockWidgets(filtering),
          str([p.objectName() for p in window.tabifiedDockWidgets(filtering)]))
    export = action_button('export')
    in_panel = [name for name in ACTION_NAMES if action_button(name) is not None
                and exporting is not None and exporting.isAncestorOf(action_button(name))]
    check('panels: the panel of EXPORTING has Export (and QFieldCloud with its extension), and it acts',
          in_panel == [name for name in ('export', 'qfieldcloud') if action_button(name) is not None]
          and export.isEnabled(), str(in_panel))
    check('panels: the bar of the dock keeps About alone', d.frame_actions.isVisible()
          and action_button('about').parentWidget() is d.frame_actions, str(actions_shown()))
    check('panels: CONFIGURATION leaves the dock', panels.detach('configuration'))
    QApplication.processEvents()
    configuration = panels.panel('configuration')
    check('panels: CONFIGURATION is tabbed with them, About in it', configuration is not None
          and configuration in window.tabifiedDockWidgets(filtering)
          and configuration.isAncestorOf(action_button('about')))
    check('panels: no bar and no lower stack left in the dock', not d.frame_actions.isVisible()
          and not d.splitter_main.widget(1).isVisible() and sections.is_open('exploring'))
    has_agent = 'agent' in sections._headers
    if has_agent:
        check('panels: AGENT leaves the dock', panels.detach('agent'))
        QApplication.processEvents()
        agent = panels.panel('agent')
        page = sections._pages['agent']
        check('panels: AGENT is in its panel, EXPLORING open in the dock', agent is not None
              and agent.isAncestorOf(page) and not sections._headers['agent'].isVisible()
              and sections.is_open('exploring') and 'agent' in sections.detached)
        sections.open_top('agent')  # the agent asks for an answer of the user
        QApplication.processEvents()
        check('panels: AGENT asked to open shows its panel, EXPLORING stays open',
              sections.is_open('exploring') and agent is not None and agent.isVisible() and page.isVisible()
              and sections.is_open('agent'))
        check('panels: Undo and Redo stay with FILTERING while AGENT is apart', not d.agent_has_focus())
    else:
        report('SKIP', 'panels: AGENT leaves the dock', 'no AGENT section in this dock')
    check('panels: what is apart is remembered, in the order of the dock', QSettings().value(DETACHED_KEY)
          == ','.join((['agent'] if has_agent else []) + ['filtering', 'exporting', 'configuration']),
          str(QSettings().value(DETACHED_KEY)))
    sheet = d.dockWidgetContents.styleSheet()
    d.dockWidgetContents.setStyleSheet(sheet + '\n/* another theme */')
    QApplication.processEvents()
    check('panels: a change of theme reaches the panels',
          all(panels.panel(key).widget().styleSheet().endswith('/* another theme */') for key in panels.detached()))
    d.dockWidgetContents.setStyleSheet(sheet)
    QApplication.processEvents()
    for key in panels.detached():
        panels.raise_panel(key)
        QApplication.processEvents()
        grab_widget(panels.panel(key), f'panel_{key}')
    grab('dock_exploring_alone')
    return None


def s_section_close_dock():
    dock().close()  # the X of the dock: its panels go with it
    since = time.time()
    return lambda: not dock().isVisible() and time.time() - since > 1


def s_section_reopen_dock():
    panels = dock()._fm_panels
    check('panels: the dock closed, its panels are hidden and stay apart',
          not any(panels.panel(key).isVisible() for key in panels.detached()) and len(panels.detached()) >= 3,
          str(panels.detached()))
    qgis.utils.plugins[PACKAGE].run()  # the toolbar button
    return settled()


def s_section_close_panel():
    d = dock()
    panels = d._fm_panels
    check('panels: the dock shown again, its panels too',
          d.isVisible() and all(not panels.panel(key).isHidden() for key in panels.detached()),
          str([key for key in panels.detached() if panels.panel(key).isHidden()]))
    panels.panel('filtering').close()  # the X of the panel
    return lambda: 'filtering' not in panels.detached()


def s_section_back_check():
    """A panel closed: its section is back in the dock, folded; then every section back, and restored."""
    d = dock()
    panels = d._fm_panels
    sections = d._fm_sections
    toolbox = d.toolBox_tabTools
    window = iface.mainWindow()
    header = bottom_header(d.FILTERING)
    check('panels: closing the panel brings FILTERING back to the dock, folded', d.isAncestorOf(d.FILTERING)
          and header is not None and header.isVisible() and toolbox.isItemEnabled(toolbox.indexOf(d.FILTERING))
          and toolbox.currentWidget() is sections._nothing and d.splitter_main.widget(1).isVisible()
          and not [panel for panel in window.findChildren(QDockWidget, 'FilterMatePanel_filtering')
                   if not panel.isHidden()],
          f"current={toolbox.currentWidget().objectName()}")
    check('panels: its buttons are back in the bar of the dock', d.frame_actions.isVisible()
          and all(action_button(name).parentWidget() is d.frame_actions for name in FILTERING_ACTIONS
                  if action_button(name) is not None) and not d.filtering_detached)
    open_section(d.FILTERING)
    check('panels: FILTERING opens in the dock again, with its widgets', toolbox.currentWidget() is d.FILTERING
          and d.comboBox_filtering_current_layer.isVisible() and action_button('filter').isEnabled()
          and action_button('filter').isVisible())
    panels.attach_all()
    QApplication.processEvents()
    check('panels: with every section back the dock has the minimum height of its profile again',
          d.minimumHeight() > 0, str(d.minimumHeight()))
    if 'agent' in sections._headers:
        minimum = d.minimumHeight()
        panels.detach('agent')
        QApplication.processEvents()
        check('panels: AGENT alone apart, the dock keeps its minimum height', d.minimumHeight() == minimum,
              f"{minimum} -> {d.minimumHeight()}")
        panels.attach('agent')
        QApplication.processEvents()
    pages = [toolbox.indexOf(page) for page in (d.FILTERING, d.EXPORTING, d.CONFIGURATION)]
    held = [name for name in ACTION_NAMES if action_button(name) is not None
            and action_button(name).parentWidget() is d.frame_actions]
    order = sorted(actions_shown(), key=lambda name: action_button(name).x())
    check('panels: every section back, the dock as it was', panels.detached() == () and pages == [0, 1, 2]
          and all(d.isAncestorOf(page) for page in (d.FILTERING, d.EXPORTING, d.CONFIGURATION))
          and ('agent' not in sections._headers or (sections._headers['agent'].isVisible()
                                                    and d.isAncestorOf(sections._pages['agent'])))
          and held == [name for name in ACTION_NAMES if action_button(name) is not None]
          and order == SECTION['all'] and not QSettings().value(DETACHED_KEY),
          f"pages={pages} held={held} order={order} saved={QSettings().value(DETACHED_KEY)!r}")
    leftovers = [panel.objectName() for panel in window.findChildren(QDockWidget)
                 if panel.objectName().startswith('FilterMatePanel_') and not panel.isHidden()]
    check('panels: no panel left in QGIS', not leftovers, str(leftovers))
    QSettings().setValue(DETACHED_KEY, 'exporting, nothing, FILTERING')  # as saved by another session, and noise
    restored = panels.restore()
    QApplication.processEvents()
    check('panels: the sections that were apart are apart again when the dock is built',
          restored == ['filtering', 'exporting'] and panels.detached() == ('filtering', 'exporting')
          and panels.panel('exporting') in window.tabifiedDockWidgets(panels.panel('filtering')), str(restored))
    panels.attach_all()
    QApplication.processEvents()
    open_section(d.FILTERING)
    check('panels: left as found', panels.detached() == () and toolbox.currentWidget() is d.FILTERING
          and actions_shown() == SECTION['all'] and not QSettings().value(DETACHED_KEY), str(actions_shown()))
    grab('sections_end')
    return settled()


def s_section_restart():
    """As after a restart of QGIS: the dock and its panel come back where they were, the panel still below it."""
    from qgis.PyQt.QtWidgets import QMenu
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    module = importlib.import_module(f'{PACKAGE}.ui.layout.section_panels')
    area = window.dockWidgetArea(d)
    open_section(d.FILTERING)
    panels.detach('filtering')
    QApplication.processEvents()
    panel = panels.panel('filtering')
    place = panel_place(panel)
    if not check('restart: FILTERING is apart, below the dock or tabbed with it', place in ('below', 'tab'),
                 f"place={place} dock={d.height()} floating={d.isFloating()}/{panel.isFloating() if panel else None} "
                 f"visible={d.isVisible()}/{panel.isVisible() if panel else None} "
                 f"tops={d.mapTo(window, QPoint(0, 0)).y()}/{panel.mapTo(window, QPoint(0, 0)).y() if panel else None} "
                 f"docks={[(w.objectName(), w.height()) for w in window.findChildren(QDockWidget) if w.isVisible()]}"):
        return None
    menu = window.findChild(QMenu, module.PANEL_MENU_NAME)
    check('restart: the panel is listed in the menu of the panels of QGIS', menu is not None
          and panel.toggleViewAction() in menu.actions(), f"menu={menu}")
    state = window.saveState()  # QGIS saves its window when it closes
    panels.attach_all(remember=False)  # the plugin unloads: its panels go, what was apart stays saved
    iface.removeDockWidget(d)
    QApplication.processEvents()
    window.restoreState(state)  # QGIS starts: it knows neither the dock nor its panel yet
    QSettings().setValue(module.DOCK_AREA_KEY, module._area_number(area))
    restored = module.place_dock(d, iface, area)  # the plugin opens its dock
    d.show()
    again = panels.restore()  # and the sections that were apart
    QApplication.processEvents()
    panel = panels.panel('filtering')
    check('restart: the dock is back where QGIS kept it', restored and window.dockWidgetArea(d) == area
          and d.isVisible() and (menu is None or d.toggleViewAction() in menu.actions()), f"restored={restored}")
    check('restart: FILTERING is apart again, where it was (below the dock, or tabbed with it)',
          again == ['filtering'] and panel is not None and not panel.isHidden() and panel_place(panel) == place,
          f"again={again} place before={place} after={panel_place(panel)}")
    panels.raise_panel('filtering')
    QApplication.processEvents()
    check('restart: its buttons act', action_button('filter').isEnabled()
          and panel is not None and panel.isAncestorOf(action_button('filter')))
    QSettings().setValue(module.DOCK_AREA_KEY, -1)
    check('restart: a change of DOCK_POSITION since wins over the place QGIS kept',
          not module.restore_dock_first(panels.detached(), QSettings().value(module.DOCK_AREA_KEY),
                                        module._area_number(area)))
    QSettings().setValue(module.DOCK_AREA_KEY, module._area_number(area))
    panels.attach_all()
    QApplication.processEvents()
    open_section(d.FILTERING)
    check('restart: left as found', panels.detached() == () and not QSettings().value(DETACHED_KEY) and d.isVisible()
          and d.toolBox_tabTools.currentWidget() is d.FILTERING and actions_shown() == SECTION['all'],
          str(actions_shown()))
    return settled()


def menu_action(menu, name):
    return next((action for action in menu.actions() if action.objectName() == name), None) if menu is not None else None


def s_section_group():
    """Separate, group and merge from the menus: every section apart in one go, a panel as a tab of another, one
    section merged back, then all of them."""
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    has_agent = 'agent' in d._fm_sections._headers
    every = tuple(key for key in ('agent', 'filtering', 'exporting', 'configuration') if has_agent or key != 'agent')
    header = bottom_header(d.FILTERING)
    menu = panels.build_menu('filtering', header)
    names = [action.objectName() for action in menu.actions() if not action.isSeparator()] if menu is not None else []
    check('group: in the dock, a section is offered its own panel, alone or with the others',
          names == ['action_section_detach', 'action_section_detach_all'], str(names))
    menu_action(menu, 'action_section_detach_all').trigger()
    QApplication.processEvents()
    if not check('group: every section in its own panel in one go', panels.detached() == every, str(panels.detached())):
        panels.attach_all()
        return None
    filtering, exporting = panels.panel('filtering'), panels.panel('exporting')
    menu = panels.build_menu('filtering', filtering)
    names = [action.objectName() for action in menu.actions() if not action.isSeparator()]
    check('group: a panel is offered the panels it is not tabbed with, and to merge',
          'action_section_group_dock' in names and 'action_section_group_exporting' not in names
          and 'action_section_attach' in names and 'action_section_attach_all' in names
          and 'action_section_detach_all' not in names, str(names))
    menu_action(menu, 'action_section_group_dock').trigger()
    QApplication.processEvents()
    check('group: FILTERING becomes a tab beside the FilterMate dock', filtering in window.tabifiedDockWidgets(d)
          and filtering not in window.tabifiedDockWidgets(exporting) and filtering.isVisible(),
          str([panel.objectName() for panel in window.tabifiedDockWidgets(d)]))
    menu = panels.build_menu('exporting', exporting)
    check('group: EXPORTING is offered FILTERING again, now that they are apart',
          menu_action(menu, 'action_section_group_filtering') is not None)
    menu_action(menu, 'action_section_group_filtering').trigger()
    QApplication.processEvents()
    check('group: EXPORTING joins FILTERING and the dock as a tab', exporting in window.tabifiedDockWidgets(filtering)
          and exporting in window.tabifiedDockWidgets(d) and action_button('export').isEnabled())
    panels._show_panel_menu('exporting', exporting, QPoint(8, 4))  # a right click on the title of the panel
    QApplication.processEvents()
    shown = [popup for popup in exporting.findChildren(QMenu) if popup.isVisible()]
    check('group: a right click on the title of a panel opens its menu', len(shown) == 1)
    for popup in shown:
        popup.hide()
    inside = exporting.widget().geometry().center()
    panels._show_panel_menu('exporting', exporting, inside)
    QApplication.processEvents()
    check('group: not a right click in the contents of the panel',
          not [popup for popup in exporting.findChildren(QMenu) if popup.isVisible()])
    menu = panels.build_menu('exporting', exporting)
    menu_action(menu, 'action_section_attach').trigger()
    QApplication.processEvents()
    check('group: merged back, EXPORTING is in the dock again, the others stay apart',
          'exporting' not in panels.detached() and d.isAncestorOf(d.EXPORTING) and 'filtering' in panels.detached()
          and bottom_header(d.EXPORTING).isVisible(), str(panels.detached()))
    menu = panels.build_menu('exporting', bottom_header(d.EXPORTING))
    menu_action(menu, 'action_section_attach_all').trigger()
    QApplication.processEvents()
    open_section(d.FILTERING)
    check('group: every section merged back into FilterMate', panels.detached() == ()
          and not QSettings().value(DETACHED_KEY) and actions_shown() == SECTION['all']
          and d.toolBox_tabTools.currentWidget() is d.FILTERING, f"{panels.detached()} {actions_shown()}")
    return settled()


def s_section_off():
    """A section turned off (APP.OPTIONS.FILTERING.enabled) while it is in its own panel: the panel goes with it, and
    comes back when the section is turned on again. Undo, Redo and Compare stay within reach."""
    d = dock()
    panels = d._fm_panels
    manager = d._action_bar_manager
    options = d.CONFIG_DATA['APP']['OPTIONS']
    before = options.get('FILTERING')
    open_section(d.FILTERING)
    if not check('off: FILTERING is in its own panel', panels.detach('filtering')):
        return None
    QApplication.processEvents()
    options['FILTERING'] = {'enabled': {'value': False}}
    changed = d.apply_section_options()
    QApplication.processEvents()
    check('off: turned off, FILTERING leaves its panel and the dock, and is kept as apart',
          changed == ['filtering'] and panels.detached() == () and not bottom_header(d.FILTERING).isVisible()
          and QSettings().value(DETACHED_KEY) == 'filtering' and not panels.can_detach('filtering')
          and d.isAncestorOf(d.FILTERING), f"changed={changed} apart={panels.detached()}")
    check('off: Filter and Unfilter go, Undo and Redo stay in the bar of the dock',
          not action_button('filter').isVisible() and not action_button('unfilter').isVisible()
          and action_button('undo_filter').isVisible() and action_button('undo_filter').parentWidget() is d.frame_actions,
          str(actions_shown()))
    manager.set_position('sections')
    QApplication.processEvents()
    kept = [name for name in ('undo_filter', 'redo_filter', 'compare') if name in SECTION['all']]
    check('off: with the buttons under their section, Undo, Redo and Compare stay in a bar', d.frame_actions.isVisible()
          and actions_shown() == kept, str(actions_shown()))
    manager.set_position(SECTION['position'])
    QApplication.processEvents()
    options['FILTERING'] = {'enabled': {'value': True}}
    changed = d.apply_section_options()
    QApplication.processEvents()
    panel = panels.panel('filtering')
    check('off: turned on again, FILTERING is back in its own panel with its buttons', changed == ['filtering']
          and panels.detached() == ('filtering',) and panel is not None
          and panel.isAncestorOf(action_button('filter')) and not action_button('filter').isHidden()
          and panel.isAncestorOf(d.comboBox_filtering_current_layer), f"changed={changed} apart={panels.detached()}")
    panels.attach_all()
    if before is None:
        options.pop('FILTERING', None)
    else:
        options['FILTERING'] = before
    d.apply_section_options()
    QApplication.processEvents()
    open_section(d.FILTERING)
    check('off: left as found', panels.detached() == () and d.toolBox_tabTools.currentWidget() is d.FILTERING
          and actions_shown() == SECTION['all'] and not QSettings().value(DETACHED_KEY)
          and d.FILTERING.isAncestorOf(d.comboBox_filtering_current_layer), str(actions_shown()))
    return settled()


SECTION_STEPS = [s_section_setup, s_section_bars, s_vector_source, s_vector_select, s_section_detach, s_section_filter,
                 s_section_filter_check, s_section_undo, s_section_undo_check, s_section_stack,
                 s_section_close_dock, s_section_reopen_dock, s_section_close_panel, s_section_back_check,
                 s_section_restart, s_section_group, s_section_off]

# --- the welcome: how FilterMate works told in the AGENT thread, the layout asked by the setup (2026-11-16) --------

WELCOME = {}
EVERY_SECTION = ('agent', 'filtering', 'exporting', 'configuration')


def grab_window(name):
    """FM_GRAB_DIR set: the whole window of QGIS as <name>.png (where the panels are, beside the dock)."""
    folder = os.environ.get('FM_GRAB_DIR')
    if folder:
        QApplication.processEvents()
        iface.mainWindow().grab().save(os.path.join(folder, f"{name}.png"))


def thread_links():
    """The link buttons of the AGENT thread by their whole text, in the order they were said."""
    return {button._full: button for button in agent_chat().panel.thread.findChildren(QPushButton)
            if button.objectName() == 'pushButton_agent_link'}


def present_sections():
    return tuple(key for key in EVERY_SECTION if key != 'agent' or 'agent' in dock()._fm_sections._headers)


def leave_welcome():
    """As the other steps expect the dock: an empty thread, EXPLORING and FILTERING open, nothing apart."""
    d = dock()
    agent_chat().new_conversation()
    d._fm_panels.attach_all()
    QSettings().remove(DETACHED_KEY)
    d._fm_sections.open_top('exploring')
    d.toolBox_tabTools.setCurrentWidget(d.FILTERING)
    QApplication.processEvents()


def s_tour():
    """How FilterMate works: a button of the welcome and an entry of both menus; told in the thread, no model."""
    import qgis.utils
    d, chat = dock(), agent_chat()
    panel, plugin = chat.panel, qgis.utils.plugins[PACKAGE]
    tour = importlib.import_module(f'{PACKAGE}.ui.controllers.welcome_tour')
    chat.new_conversation()
    d._fm_sections.open_top('agent')
    QApplication.processEvents()
    entries = [action.text() for action in plugin.actions]
    check('tour: a button of the welcome, an entry of the panel menu and of the QGIS menu',
          panel.tour_button.isVisible() and panel.tour_action.text() == tour.title() and tour.title() in entries
          and plugin.tr('Set up FilterMate') in entries and not any('agent' in entry.lower() for entry in entries),
          str(entries))
    check('tour: the button fits the welcome, under what it offers', panel.tour_button.width() <= panel.stack.width()
          and panel.tour_button.geometry().top() > panel.welcome_text.geometry().bottom(),
          f"{panel.tour_button.geometry()} in {panel.stack.width()}")
    grab('welcome')
    d._fm_sections.open_top('exploring')  # told from a folded AGENT: the section opens
    QApplication.processEvents()
    panel.tour_action.trigger()
    QApplication.processEvents()
    text = panel.thread.toPlainText()
    told = [words for words in ('EXPLORING holds', 'FILTERING filters', 'EXPORTING writes', 'AGENT does',
                                'CONFIGURATION lists', 'A section can leave', 'group it with another one',
                                'The buttons act') if words in text]
    links = list(thread_links())
    check('tour: told in the AGENT thread, which opens: each section, the panels, the buttons, then the links',
          d._fm_sections.is_open('agent') and len(told) == 8 and links[:1] == ['Open every section in its own panel']
          and 'Set up FilterMate' in links, f"told={len(told)} links={links}")
    check('tour: nothing is kept in the conversation, no model is asked', not chat._transcript
          and chat._engine is None)
    labels = [label for label in panel.thread.findChildren(QLabel) if label.isVisible()]
    check('tour: no paragraph wider than the thread', all(label.width() <= panel.thread.width() for label in labels),
          str(max((label.width() for label in labels), default=0)))
    grab('tour')
    thread_links()['Open every section in its own panel'].click()
    return waits(0.6)


def s_tour_links_check():
    """The links of the tour do what was just said: every section in its own panel, then all of them back."""
    d, chat = dock(), agent_chat()
    panels = d._fm_panels
    check('tour: its link opens every section in its own panel, AGENT and its thread still in view',
          panels.detached() == present_sections() and d._fm_sections.is_open('agent') and on_screen(chat.panel),
          f"apart={panels.detached()} agent in view={d._fm_sections.is_open('agent')}")
    grab_window('tour_every_section_apart')
    chat.show_tour()  # told again: what can be done now is to bring them back
    QApplication.processEvents()
    links = list(thread_links())
    back = 'Merge every section back into FilterMate'
    offered = back in links and links.count('Open every section in its own panel') == 1  # the first telling's
    if back in links:
        thread_links()[back].click()
        QApplication.processEvents()
    check('tour: told again with the sections apart, its link merges them back', offered and panels.detached() == ()
          and d._fm_sections.is_open('agent'), f"links={links} apart={panels.detached()}")
    leave_welcome()
    return settled()


def s_setup_layout():
    """The setup asks where the sections go, with the buttons: each in its own panel, the buttons under it."""
    d, chat = dock(), agent_chat()
    chat.new_conversation()
    WELCOME['position'] = d._action_bar_manager.get_position()
    WELCOME['started'] = chat.start_setup()
    asked = []
    while _wizard_card() is not None and len(asked) < 8:
        card = _wizard_card()
        asked.append([chip.text() for chip in card._chips])
        if asked[-1] == ['Layout', 'Buttons']:
            QApplication.processEvents()
            agent_chat().panel.thread.ensureWidgetVisible(card)
            QApplication.processEvents()
            grab('setup_layout_step')
        _answer_card(tick=('Each in its own panel of QGIS', 'Under each section'))
    WELCOME['asked'] = asked
    card = chat._settings_cards[-1] if chat._settings_cards else None
    WELCOME['card'] = card
    WELCOME['rows'] = [row.text() for row in card.rows] if card is not None else []
    WELCOME['apart_before_apply'] = d._fm_panels.detached()
    QApplication.processEvents()
    grab('setup_layout_card')
    if card is not None:
        card.apply_button.click()
    return waits(0.8)


def s_setup_layout_check():
    d = dock()
    panels, manager = d._fm_panels, d._action_bar_manager
    check('setup: the layout is a step of its own, the sections asked with the buttons',
          WELCOME['started'] is True and ['Layout', 'Buttons'] in WELCOME['asked'] and len(WELCOME['asked']) == 5,
          str(WELCOME['asked']))
    check('setup: the sections and the buttons on the card of the changes, nothing moved before Apply',
          len(WELCOME['rows']) == 2 and any('own panel' in row for row in WELCOME['rows'])
          and WELCOME['apart_before_apply'] == (), f"rows={WELCOME['rows']} apart={WELCOME['apart_before_apply']}")
    check('setup: Apply moves every section to its own panel and the buttons under their section',
          WELCOME['card'] is not None and WELCOME['card'].done and panels.detached() == present_sections()
          and manager.get_position() == 'sections', f"apart={panels.detached()} position={manager.get_position()}")
    check('setup: AGENT moved with the others, its thread is still in view', d._fm_sections.is_open('agent')
          and on_screen(agent_chat().panel))
    text = agent_chat().panel.thread.toPlainText()
    check('setup: it says how to group and merge, and offers how FilterMate works',
          'group it with another one' in text and 'How FilterMate works' in thread_links(), text[-300:])
    grab_window('setup_layout_applied')
    WELCOME['reverted'] = agent_chat()._wizard.revert()  # the link after Apply
    return waits(0.8)


def s_setup_layout_back():
    d = dock()
    check('setup put back: every section in FilterMate again, the buttons where they were',
          WELCOME['reverted'] is True and d._fm_panels.detached() == ()
          and d._action_bar_manager.get_position() == WELCOME['position'],
          f"apart={d._fm_panels.detached()} position={d._action_bar_manager.get_position()}")
    leave_welcome()
    check('setup put back: the dock as it was, FILTERING open with its buttons',
          d.toolBox_tabTools.currentWidget() is d.FILTERING and d.frame_actions.isVisible()
          and action_button('filter').isVisible(), str(actions_shown()))
    return settled()


WELCOME_STEPS = [s_tour, s_tour_links_check, s_setup_layout, s_setup_layout_check, s_setup_layout_back]


# --- what a section in its own panel still shares with the others (FM_ONLY=sync) -------------------------------------

SYNC = {}


def apply_settings(values):
    """As the setup and the agent set a setting: through the panel, applied at once."""
    return importlib.import_module(f'{PACKAGE}.adapters.agent.plugin_settings').apply_values(values)


def s_sync_apart():
    d = dock()
    SYNC['theme'] = config_value('APP.DOCKWIDGET.COLORS.ACTIVE_THEME')
    SYNC['position'] = d._action_bar_manager.get_position()
    SYNC['docked'] = bool(os.environ.get('FM_SYNC_DOCKED'))  # the control: the same probes with nothing apart
    if not SYNC['docked']:
        d._fm_panels.detach_all()
    return waits(0.6)


def sync_sections():
    return () if SYNC.get('docked') else present_sections()


def s_sync_layer():
    """The current layer is chosen in FILTERING, now in its own panel: EXPLORING, left in the dock, follows."""
    d = dock()
    check('sync: every section is apart, EXPLORING alone in the dock', d._fm_panels.detached() == sync_sections()
          and d._fm_sections.is_open('exploring'), str(d._fm_panels.detached()))
    d.comboBox_filtering_current_layer.setLayer(layer('dem'))
    return switched_to('dem', coverage_page=True)


def s_sync_layer_check():
    d, ctrl = dock(), coverage()
    panel = d._fm_panels.panel('filtering') or d
    check('sync: a raster chosen in the panel of FILTERING shows its page in EXPLORING, in the dock',
          ctrl.active_layer is not None and ctrl.active_layer.name() == 'dem' and ctrl._raster_panel.isVisible()
          and d.isAncestorOf(ctrl._raster_panel) and panel.isAncestorOf(d.comboBox_filtering_current_layer))
    grab_window('sync_raster_current')
    auto = d.pushButton_checkable_filtering_auto_current_layer
    SYNC['auto'] = auto.isChecked()
    if not auto.isChecked():
        auto.click()
    iface.setActiveLayer(layer('zones'))  # the layer panel of QGIS: the chooser follows it, then EXPLORING
    return switched_to('zones', coverage_page=False)


def s_sync_active_layer_check():
    d = dock()
    current = d.comboBox_filtering_current_layer.currentLayer()
    check('sync: the layer made current in QGIS reaches the chooser in the panel, then EXPLORING in the dock',
          current is not None and current.name() == 'zones' and d.mGroupBox_exploring_single_selection.isVisible(),
          f"chooser={current.name() if current else None}")
    auto = d.pushButton_checkable_filtering_auto_current_layer
    if auto.isChecked():  # off: the layer added below would become the source, which is never among its targets
        auto.click()
    extra = QgsVectorLayer('Point?crs=EPSG:2154&field=nom:string', 'sync_extra', 'memory')
    project.addMapLayer(extra)
    return waits(3.0, lambda: registered('sync_extra') and tasks_idle())  # the lists follow in a batch, a moment later


def exporting_items():
    combo = dock().checkableComboBoxLayer_exporting_layers
    return [combo.model().item(row).text() for row in range(combo.model().rowCount())]


def s_sync_layers_check():
    """A layer added to the project reaches the lists of the panels; removed, it leaves them."""
    SYNC['added'] = (any(text.startswith('sync_extra') for text in combo_items()),
                     any(text.startswith('sync_extra') for text in exporting_items()))
    project.removeMapLayer(layer('sync_extra').id())
    return waits(2.0, tasks_idle)


def s_sync_layers_removed_check():
    gone = (not any(text.startswith('sync_extra') for text in combo_items()),
            not any(text.startswith('sync_extra') for text in exporting_items()))
    check('sync: a layer added to the project is listed in the panels of FILTERING and EXPORTING',
          SYNC['added'] == (True, True), f"filtering, exporting = {SYNC['added']}")
    check('sync: removed from the project, it leaves both lists', gone == (True, True), f"filtering, exporting = {gone}")
    apply_settings({'APP.DOCKWIDGET.COLORS.ACTIVE_THEME': 'dark' if SYNC['theme'] != 'dark' else 'light'})
    return waits(1.0)


def s_sync_theme_check():
    d = dock()
    panels = d._fm_panels
    sheet = d.dockWidgetContents.styleSheet()
    same = {key: panels.panel(key).widget().styleSheet() == sheet for key in panels.detached()}
    print(f"   lists after the theme: filtering={combo_items()} exporting={exporting_items()}", flush=True)
    agent = agent_chat().panel
    theme = getattr(getattr(d, '_theme_manager', None), 'current_theme', None)
    theme = theme() if callable(theme) else theme
    check('sync: a change of theme reaches every panel, the AGENT thread with it', all(same.values()) and len(same) == len(sync_sections())
          and agent._dark() == (theme == 'dark'), f"theme={theme} same sheet={same} agent dark={agent._dark()}")
    grab_window('sync_other_theme')
    apply_settings({'APP.DOCKWIDGET.COLORS.ACTIVE_THEME': SYNC['theme']})
    QApplication.processEvents()
    apply_settings({'APP.DOCKWIDGET.ACTION_BAR_POSITION': 'top' if SYNC['position'] != 'top' else 'bottom'})
    return waits(1.0)


def s_sync_position_check():
    """Another place for the bar for all: the buttons of a section apart stay in its panel."""
    d = dock()
    panels = d._fm_panels
    filtering, exporting = panels.panel('filtering') or d, panels.panel('exporting') or d
    check('sync: the bar moved, the buttons of FILTERING and EXPORTING stay in their panels, shown and enabled',
          filtering.isAncestorOf(action_button('filter')) and exporting.isAncestorOf(action_button('export'))
          and action_button('filter').isVisible() and action_button('export').isVisible()
          and (SYNC['docked'] or (action_button('filter').isEnabled() and action_button('export').isEnabled())),
          str(actions_shown()))
    grab_window('sync_bar_moved')
    apply_settings({'APP.DOCKWIDGET.ACTION_BAR_POSITION': SYNC['position']})
    QApplication.processEvents()
    d.raise_()  # AGENT is a tab of the dock: the dock in front hides its thread
    QApplication.processEvents()
    SYNC['agent_behind'] = SYNC['docked'] or (on_screen(agent_chat().panel) is False
                                              and not d._fm_sections.is_open('agent'))
    agent_chat()._show_agent()  # what a question of the agent, the setup and the tour do
    return waits(0.6)


def on_screen(widget):
    """Qt calls a panel behind a tab visible: only its visible region tells it is not in view."""
    return widget.isVisible() and not widget.visibleRegion().isEmpty()


def s_sync_agent_check():
    d = dock()
    check('sync: AGENT behind the tab of the dock is not counted as in view, and comes forward when its thread '
          'has something to say', SYNC['agent_behind'] and d._fm_sections.is_open('agent')
          and on_screen(agent_chat().panel),
          f"behind before={SYNC['agent_behind']} in view now={d._fm_sections.is_open('agent')} "
          f"on screen={on_screen(agent_chat().panel)}")
    d.comboBox_filtering_current_layer.setLayer(layer('zones'))
    return switched_to('zones', coverage_page=False)


def s_sync_undo():
    """A filter from the panel: Undo of the panel and the count of EXPLORING in the dock follow."""
    d = dock()
    d.mGroupBox_exploring_single_selection.setChecked(True)
    east_a = next(feature for feature in layer('zones').getFeatures() if feature['name'] == 'east_a')
    d.mFeaturePickerWidget_exploring_single_selection.setFeature(east_a.id())
    set_targets(['dem'])
    set_predicates(['Intersect'])
    ready = targets_ready(['dem'])
    return lambda: bool(dock().get_current_features()[0]) and ready()


def s_sync_filter():
    SYNC['undo_before'] = action_button('undo_filter').isEnabled()
    action_button('filter').click()
    return lambda: layer('dem').source().endswith('.vrt') and tasks_idle()


def s_sync_filter_check():
    check('sync: a filter from the panel enables Undo there, and Export stays enabled in the panel of EXPORTING',
          action_button('undo_filter').isEnabled() and action_button('export').isEnabled(),
          f"undo before={SYNC['undo_before']} after={action_button('undo_filter').isEnabled()}")
    grab_window('sync_filtered')
    action_button('undo_filter').click()
    return lambda: not layer('dem').source().endswith('.vrt') and tasks_idle()


def s_sync_new_project():
    """Another project with the sections apart: the panels stay, their lists empty, nothing raises."""
    check('sync: Undo of the panel takes the filter back', not layer('dem').source().endswith('.vrt'))
    SYNC['errors'] = len(STATE['python_errors'])
    project.setDirty(False)
    iface.newProject(False)  # File > New, without the question about unsaved changes
    return waits(3.0, tasks_idle)


def s_sync_new_project_check():
    d = dock()
    panels = d._fm_panels
    check('sync: a project emptied leaves the panels in place, their lists empty, without an error',
          panels.detached() == sync_sections() and combo_items() == [] and exporting_items() == []
          and len(STATE['python_errors']) == SYNC['errors'],
          f"apart={panels.detached()} filtering={combo_items()} exporting={exporting_items()} "
          f"errors={STATE['python_errors'][SYNC['errors']:]}")
    grab_window('sync_empty_project')
    zones = QgsVectorLayer(M['zones'] + '|layername=zones', 'zones', 'ogr')
    project.addMapLayers([zones, QgsRasterLayer(M['dem'], 'dem', 'gdal')])
    return lambda: registered('zones', 'dem') and tasks_idle()


def s_sync_layers_back_check():
    check('sync: layers loaded again are listed in the panels', any(text.startswith('dem') for text in combo_items())
          and any(text.startswith('zones') for text in exporting_items()),
          f"filtering={combo_items()} exporting={exporting_items()}")
    auto = dock().pushButton_checkable_filtering_auto_current_layer
    if auto.isChecked() != SYNC['auto']:
        auto.click()
    leave_welcome()
    return settled()


SYNC_STEPS = [s_section_setup, s_sync_apart, s_sync_layer, s_sync_layer_check, s_sync_active_layer_check,
              s_sync_layers_check, s_sync_layers_removed_check, s_sync_theme_check, s_sync_position_check,
              s_sync_agent_check, s_sync_undo, s_sync_filter, s_sync_filter_check, s_sync_new_project,
              s_sync_new_project_check, s_sync_layers_back_check]


# --- what the audit of 16 November found in the panels and the sections turned off (FM_ONLY=audit) ---------------

AUDIT = {}
FILTERING_ON = 'APP.OPTIONS.FILTERING.enabled'


def s_audit_tab_behind():
    """AGENT in its own panel, behind the tab of the dock: Qt calls its page visible, nobody sees it."""
    leave_welcome()
    dock()._fm_panels.detach('agent')
    return waits(0.6)


def s_audit_tab_behind_check():
    d, chat = dock(), agent_chat()
    d.raise_()
    QApplication.processEvents()
    page = chat.panel
    check('audit: AGENT behind the tab of the dock is not counted as open, though Qt calls its page visible',
          page.isVisible() and not on_screen(page) and not d._fm_sections.is_open('agent'),
          f"visible={page.isVisible()} on screen={on_screen(page)} open={d._fm_sections.is_open('agent')}")
    QSettings().remove(chat.SETUP_OFFERED_KEY)
    AUDIT['offered'] = chat.offer_setup_once('audit-1.0')
    AUDIT['kept_behind'] = QSettings().value(chat.SETUP_OFFERED_KEY)
    d._fm_panels.raise_panel('agent')  # the user clicks its tab
    return waits(0.6)


def s_audit_offer_check():
    d, chat = dock(), agent_chat()
    kept = QSettings().value(chat.SETUP_OFFERED_KEY)
    check('audit: an offer of the setup behind a tab is kept as made only once its tab comes forward',
          AUDIT['offered'] is True and not AUDIT['kept_behind'] and kept == 'audit-1.0',
          f"offered={AUDIT['offered']} kept behind={AUDIT['kept_behind']!r} kept in front={kept!r}")
    d.raise_()
    QApplication.processEvents()
    chat._show_agent()  # what a question of the agent does
    return waits(0.6)


def s_audit_show_agent_check():
    check('audit: a question of the agent brings its panel forward from behind a tab', on_screen(agent_chat().panel))
    leave_welcome()
    d = dock()
    d._fm_panels.detach('agent')
    QApplication.processEvents()
    open_section(d.FILTERING)
    apply_settings({FILTERING_ON: False})
    QApplication.processEvents()
    apply_settings({FILTERING_ON: True})
    return waits(0.5)


def s_audit_reopen_check():
    d = dock()
    check('audit: turned on again with AGENT in its own panel, FILTERING opens as it was',
          d.toolBox_tabTools.currentWidget() is d.FILTERING, d.toolBox_tabTools.currentWidget().objectName())
    leave_welcome()
    panels = d._fm_panels
    apply_settings({FILTERING_ON: False})
    QApplication.processEvents()
    panels.detach('exporting')
    panels.detach('configuration')
    QApplication.processEvents()
    AUDIT['stack_hidden'] = not d.splitter_main.widget(1).isVisible()
    apply_settings({FILTERING_ON: True})
    return waits(0.5)


def s_audit_stack_below_check():
    d = dock()
    header = bottom_header(d.FILTERING)
    d.raise_()  # a panel with no room below the dock is one of its tabs, in front of it
    QApplication.processEvents()
    check('audit: turned on while the two other sections are in their panels, FILTERING shows in the dock',
          AUDIT['stack_hidden'] and d.splitter_main.widget(1).isVisible() and header is not None
          and on_screen(header), f"stack hidden before={AUDIT['stack_hidden']} "
          f"stack={d.splitter_main.widget(1).isVisible()} header on screen={header is not None and on_screen(header)} "
          f"sizes={d.splitter_main.sizes()} stack={d.splitter_main.widget(1).geometry()} "
          f"header={header.geometry() if header is not None else None} visible={header is not None and header.isVisible()} "
          f"toolbox={d.toolBox_tabTools.geometry()} dock={d.height()}")
    grab_window('audit_filtering_on_among_panels')
    apply_settings({FILTERING_ON: False})
    QApplication.processEvents()
    check('audit: turned off again, the stack left empty goes', not d.splitter_main.widget(1).isVisible())
    apply_settings({FILTERING_ON: True})
    QApplication.processEvents()
    leave_welcome()
    d._fm_panels.detach('filtering')
    QApplication.processEvents()
    apply_settings({FILTERING_ON: False})  # back in the dock, kept as apart for the day it returns
    QApplication.processEvents()
    AUDIT['kept_apart'] = QSettings().value(DETACHED_KEY)
    d._fm_panels.attach_all()  # "Merge every section back into FilterMate"
    apply_settings({FILTERING_ON: True})
    return waits(0.5)


def s_audit_merge_check():
    d = dock()
    check('audit: every section merged back stays merged, one that was turned off included',
          AUDIT['kept_apart'] == 'filtering' and d._fm_panels.detached() == () and not QSettings().value(DETACHED_KEY),
          f"kept apart={AUDIT['kept_apart']!r} apart now={d._fm_panels.detached()} saved={QSettings().value(DETACHED_KEY)!r}")
    leave_welcome()
    AUDIT['position'] = d._action_bar_manager.get_position()
    other = 'top' if AUDIT['position'] != 'top' else 'bottom'
    # One change of settings: the bar is rebuilt (its buttons hidden for a moment), then FILTERING is turned off.
    apply_settings({'APP.DOCKWIDGET.ACTION_BAR_POSITION': other, FILTERING_ON: False})
    QApplication.processEvents()
    apply_settings({FILTERING_ON: True})
    return waits(0.5)


def s_audit_buttons_check():
    d = dock()
    open_section(d.FILTERING)
    check('audit: the bar moved and FILTERING turned off in one change, then on: Filter and Unfilter are back',
          action_button('filter').isVisible() and action_button('unfilter').isVisible(), str(actions_shown()))
    apply_settings({'APP.DOCKWIDGET.ACTION_BAR_POSITION': AUDIT['position']})
    QApplication.processEvents()
    leave_welcome()
    d._fm_panels.detach_all()
    return waits(0.6)


def s_audit_fronts_check():
    d = dock()
    window, panels = iface.mainWindow(), d._fm_panels
    together = panels.panel('filtering') in window.tabifiedDockWidgets(d)  # one group of tabs: the dock is in front
    behind = panels.panel('configuration') in window.tabifiedDockWidgets(panels.panel('filtering'))
    check('audit: every section apart, the dock and FILTERING stay in front, as the dock opens',
          on_screen(d.frame_exploring) and (on_screen(d.FILTERING) or together)
          and not (behind and on_screen(d.CONFIGURATION)) and not on_screen(agent_chat().panel),
          f"exploring={on_screen(d.frame_exploring)} filtering={on_screen(d.FILTERING)} "
          f"configuration={on_screen(d.CONFIGURATION)} agent={on_screen(agent_chat().panel)}")
    grab_window('audit_every_section_apart')
    leave_welcome()
    return settled()


def s_probe_settings():
    """A setting applied as the setup and the agent apply it reaches the dock (FM_STEPS, to find what stops it)."""
    d = dock()
    PROBE['position'] = d._action_bar_manager.get_position()
    other = 'top' if PROBE['position'] != 'top' else 'bottom'
    PROBE['other'] = other
    apply_settings({'APP.DOCKWIDGET.ACTION_BAR_POSITION': other, FILTERING_ON: False})
    return waits(1.0)


def s_probe_settings_check():
    d = dock()
    check('probe: a setting applied through the configuration reaches the dock',
          d._action_bar_manager.get_position() == PROBE['other'] and not d._fm_sections.section_shown('filtering'),
          f"position={d._action_bar_manager.get_position()} wanted={PROBE['other']} "
          f"filtering shown={d._fm_sections.section_shown('filtering')} "
          f"config={config_value('APP.DOCKWIDGET.ACTION_BAR_POSITION')!r}")
    apply_settings({'APP.DOCKWIDGET.ACTION_BAR_POSITION': PROBE['position'], FILTERING_ON: True})
    return waits(0.5)


PROBE = {}
AUDIT_STEPS = [s_section_setup, s_audit_tab_behind, s_audit_tab_behind_check, s_audit_offer_check,
               s_audit_show_agent_check, s_audit_reopen_check, s_audit_stack_below_check, s_audit_merge_check,
               s_audit_buttons_check, s_audit_fronts_check]


# --- the window in each layout, for the eye (FM_ONLY=layout_shots with FM_GRAB_DIR) ---------------------------------


def _shot(name, act):
    """Two steps: ``act``, then the window as <name>.png once Qt has laid it out."""
    def step():
        act()
        return waits(0.6)

    def after():
        grab_window(name)
        return None
    step.__name__, after.__name__ = f's_shot_{name}', f's_shot_{name}_grab'
    return [step, after]


def _menu_shot(name, key, on_panel):
    """The menu of a section, on its header in the dock or on the title of its panel, as a picture of its own."""
    def step():
        d = dock()
        panels = d._fm_panels
        anchor = panels.panel(key) if on_panel else (bottom_header(getattr(d, key.upper())) if key != 'agent'
                                                     else d._fm_sections._headers['agent'])
        menu = panels.build_menu(key, anchor)
        if menu is not None:
            menu.popup(anchor.mapToGlobal(QPoint(30, 12)))
            QApplication.processEvents()
            grab_widget(menu, name)
            menu.hide()
            menu.deleteLater()
        return None
    step.__name__ = f's_shot_{name}'
    return [step]


def _shots():
    def d():
        return dock()

    def panels():
        return dock()._fm_panels

    def bars(position):
        return lambda: (d()._action_bar_manager.set_position(position), QApplication.processEvents())

    def off(key, on):
        def act():
            d().CONFIG_DATA['APP']['OPTIONS'][key.upper()] = {'enabled': {'value': on}}
            d().apply_section_options()
        return act

    def floating():
        panel = panels().panel('filtering')
        panel.setFloating(True)
        panel.resize(380, 520)
        panel.move(700, 200)

    def float_grab():
        grab_widget(panels().panel('filtering'), '15_filtering_floating')
        panels().panel('filtering').setFloating(False)

    def raster():
        d().comboBox_filtering_current_layer.setLayer(layer('dem'))

    steps = [s_section_setup, s_vector_source, s_vector_select]
    steps += _shot('01_dock', lambda: open_section(d().FILTERING))
    steps += _menu_shot('02_menu_header_filtering', 'filtering', on_panel=False)
    steps += _menu_shot('02_menu_header_agent', 'agent', on_panel=False)
    steps += _shot('03_filtering_apart', lambda: panels().detach('filtering'))
    steps += _menu_shot('04_menu_panel_filtering', 'filtering', on_panel=True)
    steps += _shot('05_every_section_apart', lambda: panels().detach_all())
    steps += _menu_shot('06_menu_panel_exporting', 'exporting', on_panel=True)
    steps += _shot('07_agent_in_front', lambda: panels().raise_panel('agent'))
    steps += _shot('08_dock_in_front', lambda: d().raise_())
    steps += _shot('09_exporting_in_front', lambda: panels().raise_panel('exporting'))
    steps += _shot('10_configuration_in_front', lambda: panels().raise_panel('configuration'))
    steps += _shot('11_filtering_grouped_with_dock', lambda: panels().group('filtering', 'dock'))
    steps += _shot('12_exporting_grouped_with_agent', lambda: panels().group('exporting', 'agent'))
    steps += _shot('13_raster_current', raster)
    steps += [s_vector_source]
    steps += _shot('14_filtering_floating_window', floating)
    steps += [lambda: float_grab()]
    steps += _shot('16_filtering_merged_back', lambda: panels().attach('filtering'))
    steps += _shot('17_all_merged_back', lambda: (panels().attach_all(), open_section(d().FILTERING)))
    steps += _shot('18_bars_filtering', bars('sections'))
    steps += _shot('19_bars_exporting', lambda: open_section(d().EXPORTING))
    steps += _shot('20_bars_configuration', lambda: open_section(d().CONFIGURATION))
    steps += _shot('21_bars_nothing_open', lambda: open_section(None))
    steps += _shot('22_bars_agent', lambda: d()._fm_sections.open_top('agent'))
    steps += _shot('23_bars_filtering_apart', lambda: (d()._fm_sections.open_top('exploring'),
                                                        panels().detach('filtering')))
    steps += _shot('24_bars_every_section_apart', lambda: panels().detach_all())
    steps += _shot('25_bottom_bar_again', lambda: (panels().attach_all(), bars('bottom')(),
                                                    open_section(d().FILTERING)))
    steps += _shot('26_filtering_off', off('filtering', False))
    steps += _shot('27_filtering_off_others_apart', lambda: panels().detach_all())
    steps += _shot('28_filtering_on_again', lambda: (panels().attach_all(), off('filtering', True)(),
                                                     open_section(d().FILTERING)))
    steps += _shot('29_dark_dock', lambda: apply_settings({'APP.DOCKWIDGET.COLORS.ACTIVE_THEME': 'dark'}))
    steps += _shot('30_dark_every_section_apart', lambda: panels().detach_all())
    steps += _shot('31_dark_agent_in_front', lambda: panels().raise_panel('agent'))
    steps += _shot('32_light_again', lambda: (panels().attach_all(),
                                              apply_settings({'APP.DOCKWIDGET.COLORS.ACTIVE_THEME': 'light'}),
                                              open_section(d().FILTERING)))
    for step in steps:
        if step.__name__ == '<lambda>':
            step.__name__ = 's_shot_floating_grab'
    return steps


SHOT_STEPS = _shots() + WELCOME_STEPS

STEPS = [s_setup, s_open_plugin, s_dock_ready, s_controllers_check, s_layout_check, s_rail_width_check, s_rail_width_after, s_rail_short, s_rail_short_check, s_rail_tall_check,
         s_ui_profile_check, s_agent_settings, s_agent_settings_check, s_agent_settings_undo_check,
         s_agent_settings_card_check, s_agent_settings_link_check, s_agent_settings_profile_check,
         s_agent_skill_from_profile_check,
         s_agent_setup_offer_check, s_setup_wizard, s_setup_wizard_apply, s_setup_wizard_check,
         s_setup_wizard_back_check,
         s_qt6_enums_check, s_pick_before_late_refresh,
         s_late_refresh_check,
         s_vector_source, s_vector_select, s_vector_filter, s_compare_check, s_compare_off_check, s_compare_pin,
         s_compare_pin_check, s_history_check, s_vector_check,
         s_vector_undo_check,
         s_user_pick_after_undo_check,
         s_vector_source, s_vector_select, s_vector_filter, s_undo_pick_race, s_undo_pick_race_check,
         s_raster_source, s_raster_select, s_raster_filter, s_raster_check, s_raster_settled,
         s_point_cloud_source, s_point_cloud_select, s_point_cloud_filter, s_point_cloud_check, s_point_cloud_settled,
         s_back_to_vector, s_close_dock, s_reopen_dock, s_reopen_pick_raster, s_reopen_raster_check,
         s_reopen_vector_check,
         s_rasters_off, s_rasters_off_check, s_rasters_on_check,
         s_replay_select, s_replay_filter, s_replay_save_and_clear, s_replay_read, s_replay_check,
         s_badge_raster_source, s_raster_badge_add_layer, s_raster_badge_check, s_raster_badge_removed_check,
         s_remove_layer, s_remove_layer_check,
         s_switch_setup, s_switch_zones, s_switch_multiple, s_switch_link, s_switch_to_parcels, s_switch_parcels_check,
         s_switch_parcels_values, s_switch_to_wells, s_switch_wells_check, s_switch_back_check, s_switch_same_layer_reload,
         s_switch_same_layer_check, s_switch_late_check,
         s_partial_undo_setup, s_partial_undo_source, s_partial_undo_select, s_partial_undo_filter,
         s_partial_undo_on_source, s_partial_undo_on_source_check, s_partial_undo_on_target,
         s_partial_undo_on_target_check, s_partial_undo_done, s_plugin_imports_check,
         s_custom_matching_nothing, s_custom_matching_nothing_single, s_custom_matching_nothing_check, s_config_search, s_wheel_needs_focus, s_wheel_needs_focus_check, s_agent_panel,
         *PANEL_STEPS, *OPTION_STEPS, *SECTION_STEPS, *WELCOME_STEPS, *AUDIT_STEPS, s_finish]

if os.environ.get('FM_ONLY') == 'panels':  # the steps of the panels alone, after the plugin is up
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *PANEL_STEPS, s_finish]
if os.environ.get('FM_ONLY') == 'sections':  # the buttons under their section, a section in its own QGIS panel
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *SECTION_STEPS, s_finish]
if os.environ.get('FM_ONLY') == 'sections_startup':  # the same, as the dock finds them when it opens
    STEPS = [s_setup, s_open_plugin, s_dock_ready, s_section_startup_check, s_finish]
if os.environ.get('FM_ONLY') == 'welcome':  # the tour and the layout step of the setup alone
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *WELCOME_STEPS, s_finish]
if os.environ.get('FM_STEPS'):  # steps by name, in this order: to find which one leaves the dock in another state
    STEPS = [s_setup, s_open_plugin, s_dock_ready,
             *[step for name in os.environ['FM_STEPS'].split(',') for step in
               (globals()[name] if isinstance(globals()[name], list) else [globals()[name]])], s_finish]
if os.environ.get('FM_ONLY') == 'layout':  # everything about the sections, their panels and the welcome, in a row
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *SECTION_STEPS, *WELCOME_STEPS, *AUDIT_STEPS, s_finish]
if os.environ.get('FM_ONLY') == 'audit':  # the defects of the panels found on 16 November, each one alone
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *AUDIT_STEPS, s_finish]
if os.environ.get('FM_ONLY') == 'sync':  # what a section in its own panel still shares with the others
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *SYNC_STEPS, s_finish]
if os.environ.get('FM_ONLY') == 'layout_shots':  # the window in each layout, as pictures in FM_GRAB_DIR
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *SHOT_STEPS, s_finish]
if os.environ.get('FM_ONLY') == 'options':  # the menu of the options of the agent alone
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *OPTION_STEPS, s_finish]


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
