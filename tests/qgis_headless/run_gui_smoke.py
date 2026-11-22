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
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import types

from qgis.core import Qgis, QgsApplication, QgsProject, QgsProviderRegistry, QgsRasterLayer, QgsSettings, QgsVectorLayer
from qgis.PyQt.QtCore import QCoreApplication, QEvent, QMimeData, QPoint, QPointF, QSettings, Qt, QTimer
from qgis.PyQt.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent, QWheelEvent
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
    if os.environ.get('FM_HEADERS'):  # the dock opens with the sections listed this way, as saved before
        for name in ('config.default.json', 'config.json'):
            path = os.path.join(plugins, PACKAGE, 'config', name)
            with open(path, encoding='utf-8') as stream:
                config = json.load(stream)
            config['APP']['DOCKWIDGET']['SECTION_HEADERS']['value'] = os.environ['FM_HEADERS']
            with open(path, 'w', encoding='utf-8') as stream:
                json.dump(config, stream, indent=2)
    if os.environ.get('FM_TOOLS_HIDDEN'):  # the dock opens with these buttons of the vector rail hidden, as saved before
        for name in ('config.default.json', 'config.json'):
            path = os.path.join(plugins, PACKAGE, 'config', name)
            with open(path, encoding='utf-8') as stream:
                config = json.load(stream)
            config['APP']['DOCKWIDGET']['EXPLORING_TOOLS']['vector_hidden']['value'] = os.environ['FM_TOOLS_HIDDEN']
            with open(path, 'w', encoding='utf-8') as stream:
                json.dump(config, stream, indent=2)
    if os.environ.get('FM_DETACHED'):  # and with these sections in their own panel, as left the last time
        settings.setValue('FilterMate/panels/detached', os.environ['FM_DETACHED'])
    if os.environ.get('FM_SHARE'):  # and with the handle between the two stacks where a session before left it
        settings.setValue('FilterMate/splitter_top_share', float(os.environ['FM_SHARE']))
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
    STATE['wizard_steps'], STATE['wizard_asked'] = 0, []
    while _wizard_card() is not None and STATE['wizard_steps'] < 30:  # every card, however many steps the setup has
        STATE['wizard_asked'].append([chip.text() for chip in _wizard_card()._chips])
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
    check('setup with no model: cards without Other, every step answered (FILTERING skipped), the change shown then applied',
          STATE['wizard_started'] is True and STATE['wizard_no_other']
          and not any('Filtering' in chips for chips in STATE['wizard_asked']) and len(STATE['wizard_asked']) >= 4
          and any('Vector tools' in chips for chips in STATE['wizard_asked']) and _wizard_card() is None
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
    module = sys.modules[f'{PACKAGE}.filter_mate_dockwidget']
    check('closing the dock takes it off the registry of the feature picker guard',
          module._active_dockwidget is None, repr(module._active_dockwidget))
    since = time.time()
    return lambda: not dock().isVisible() and time.time() - since > 1


def s_reopen_dock():
    qgis.utils.plugins[PACKAGE].run()  # the toolbar button
    return settled()


def s_reopen_pick_raster():
    """closeEvent used to tear the controllers down: a raster picked in the reopened dock left the vector
    layer current, without its EXPLORING page."""
    integration = dock()._controller_integration
    module = sys.modules[f'{PACKAGE}.filter_mate_dockwidget']
    # 2026-11-18, audit: the guard of QgsFeaturePickerWidget (sql_utils.feature_picker_guard) finds no dock otherwise
    check('the dock shown again is the active dock again: the feature picker guard finds it',
          module._active_dockwidget is dock(), repr(module._active_dockwidget))
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
    # A rail per stack lists its sections (ui/widgets/section_rail.py): the headers stacked above each other are gone.
    top_rail, bottom_rail = sections.top_rail, sections.bottom_rail
    agent_header = top_rail.chip('agent')
    exploring_header = top_rail.chip('exploring')
    check('agent: installed once', d._agent_chat is first and
          len([c for c in top_rail.findChildren(QPushButton) if c.property('fm_section') == 'agent']) == 1)
    check('stacks: AGENT shares the top stack with EXPLORING', chat.panel.parentWidget() is sections.top and
          d.frame_exploring.parentWidget() is sections.top)
    top_layout = sections.top.layout()
    check('stacks: the rail first, AGENT and EXPLORING listed in it in this order',
          top_layout.indexOf(top_rail) == 0 and top_rail.sections() == ['agent', 'exploring']
          and agent_header.x() < exploring_header.x()
          and top_layout.indexOf(top_rail) < min(top_layout.indexOf(chat.panel), top_layout.indexOf(d.frame_exploring)),
          f"{top_rail.sections()} {[top_layout.indexOf(w) for w in (top_rail, chat.panel, d.frame_exploring)]}")
    old_headers = [b for b in toolbox.findChildren(QAbstractButton)
                   if b.objectName() == 'qt_toolbox_toolboxbutton' and b.isVisibleTo(toolbox)]
    old_headers += [h for h in sections._headers.values() if h.isVisibleTo(sections.top)]
    check('stacks: no header stacked above another is left', not old_headers, str(len(old_headers)))
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
    bottom_headers = [bottom_rail.chip(key) for key in bottom_rail.shown_sections()]
    check('stacks: the lower rail lists FILTERING, EXPORTING and CONFIGURATION',
          bottom_rail.shown_sections() == ['filtering', 'exporting', 'configuration']
          and all(chip.isVisible() for chip in bottom_headers), str(bottom_rail.shown_sections()))
    heights = {b.height() for b in bottom_headers} | {exploring_header.height(), agent_header.height()}
    check('stacks: one chip height everywhere, that of the headers before', heights == {34}, str(heights))
    check('stacks: FILTERING open, EXPLORING open, AGENT folded', toolbox.currentWidget() is d.FILTERING and
          sections.is_open('exploring') and not sections.is_open('agent') and exploring_header.isChecked()
          and bottom_rail.chip('filtering').isChecked() and not agent_header.isChecked())
    check('stacks: the open sections show their name on their chip, the others their icon only',
          exploring_header.text() == 'EXPLORING' and bottom_rail.chip('filtering').text() == 'FILTERING'
          and agent_header.text() == '' and bottom_rail.chip('exporting').text() == ''
          and not agent_header.icon().isNull() and agent_header.toolTip() == 'AGENT')
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
    check('stacks: the lower rail stays', all(b.isVisible() for b in bottom_headers)
          and not any(b.isChecked() for b in bottom_headers))
    QApplication.processEvents()
    check('stacks: the open AGENT takes the room, the folded stack keeps its rail only',
          lower.height() <= 34 + 30 and not toolbox.isVisible(),
          f"lower={lower.height()} min={lower.minimumHeight()} tool box shown={toolbox.isVisible()}")
    panel = chat.panel
    panel = chat.panel
    check('agent: the welcome is shown', panel.welcome_title.isVisible())
    check('agent: the input is below it', panel.input.geometry().top() > panel.stack.geometry().bottom())
    check('agent: the input takes the width', panel.input.width() > panel.width() * 0.7,
          f"{panel.input.width()} of {panel.width()}")
    headers = bottom_headers + [exploring_header, agent_header]
    check('agent: same chip height, the lower stack folded too', {b.height() for b in headers} == {34},
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
    check('agent: the thread is on the edges of the rail (mockup)', abs(panel.thread.mapTo(d, QPoint(0, 0)).x()
          - top_rail.mapTo(d, QPoint(0, 0)).x()) <= 1 and abs(panel.thread.width() - top_rail.width()) <= 2,
          f"thread x={panel.thread.mapTo(d, QPoint(0, 0)).x()} w={panel.thread.width()} rail w={top_rail.width()}")
    if os.environ.get('FM_GEOMETRY'):
        def where(widget):
            top_left = widget.mapTo(d, QPoint(0, 0))
            return f"x={top_left.x()} y={top_left.y()} w={widget.width()} h={widget.height()}"
        for label, widget in (('top rail', top_rail), ('panel', panel), ('stack', panel.stack),
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
    export_header = bottom_rail.chip('exporting')
    check('stacks: the chip of EXPORTING is the open one', export_header.isChecked()
          and export_header.text() == 'EXPORTING' and bottom_rail.current() == 'exporting')
    export_header.click()
    QApplication.processEvents()
    check('stacks: a click on the chip of the open section folds it', toolbox.currentWidget() not in (d.EXPORTING, d.FILTERING)
          and sections.is_open('agent') and not export_header.isChecked() and bottom_rail.current() is None)
    filtering_header = bottom_rail.chip('filtering')
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
    """The chip of the section of ``page`` in the lower rail of the dock (the headers of the tool box gave way to it)."""
    d = dock()
    key = next(name for name in ('filtering', 'exporting', 'configuration') if getattr(d, name.upper()) is page)
    return d._fm_sections.bottom_rail.chip(key)


def s_section_rail():
    """A chip dragged along its rail puts the sections in another order, kept for the next time; the pages of the
    tool box keep their indexes. (QDrag.exec is modal: ``drop`` is what the drop event of the rail calls.)"""
    d = dock()
    sections = d._fm_sections
    toolbox = d.toolBox_tabTools
    top, bottom = sections.top_rail, sections.bottom_rail
    for key in ('FilterMate/sections/top_order', 'FilterMate/sections/bottom_order'):
        QSettings().remove(key)
    if not check('rail: the usual order', bottom.sections() == ['filtering', 'exporting', 'configuration'],
                 str(bottom.sections())):
        return None
    open_section(d.FILTERING)
    took = bottom.drop('configuration', bottom.chip('filtering').geometry().left() + 2, bottom)
    QApplication.processEvents()
    places = sorted(bottom.shown_sections(), key=lambda key: bottom.chip(key).x())
    check('rail: a chip dropped before another one takes its place', took
          and bottom.sections() == ['configuration', 'filtering', 'exporting'] and places == bottom.sections(),
          f"{bottom.sections()} on screen {places}")
    check('rail: the open section stays open, the pages keep their indexes', toolbox.currentWidget() is d.FILTERING
          and bottom.current() == 'filtering' and bottom.chip('filtering').isChecked()
          and [toolbox.indexOf(page) for page in (d.FILTERING, d.EXPORTING, d.CONFIGURATION)] == [0, 1, 2]
          and d.tabTools_current_index == 0, str(d.tabTools_current_index))
    check('rail: the order is kept for the next time',
          QSettings().value('FilterMate/sections/bottom_order') == 'configuration,filtering,exporting',
          str(QSettings().value('FilterMate/sections/bottom_order')))
    check('rail: a chip of the other stack is refused', not bottom.takes('agent', top) and not top.takes('filtering', bottom)
          and not bottom.drop('exploring', 5, top) and bottom.sections() == ['configuration', 'filtering', 'exporting'])
    bottom.drop('configuration', bottom.width() - 2, bottom)
    QApplication.processEvents()
    check('rail: dropped after the last one, it goes last', bottom.sections() == ['filtering', 'exporting', 'configuration'],
          str(bottom.sections()))
    if 'agent' in top.sections():
        top.drop('exploring', 1, top)
        QApplication.processEvents()
        check('rail: EXPLORING dragged before AGENT, in the top rail', top.sections() == ['exploring', 'agent']
              and top.chip('exploring').x() < top.chip('agent').x() and sections.is_open('exploring'), str(top.sections()))
        top.drop('agent', 1, top)
        QApplication.processEvents()
        check('rail: and AGENT dragged back first', top.sections() == ['agent', 'exploring'], str(top.sections()))
    for key in ('FilterMate/sections/top_order', 'FilterMate/sections/bottom_order'):
        QSettings().remove(key)
    grab('rails')
    return None


def panel_place(panel):
    """Where ``panel`` is, seen from the dock: a ``tab`` of it, ``below`` it, ``beside`` it, ``above`` it, or
    ``floating``; None without a panel."""
    if panel is None:
        return None
    d = dock()
    window = iface.mainWindow()
    if panel.isFloating():
        return 'floating'
    if panel in window.tabifiedDockWidgets(d):
        return 'tab'
    lower = panel.mapToGlobal(QPoint(0, 0)).y() - d.mapToGlobal(QPoint(0, 0)).y()
    return 'beside' if abs(lower) <= 4 else ('below' if lower > 0 else 'above')


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
    if position in ('top', 'bottom', 'left', 'right'):
        open_section(d.FILTERING)
        # 2026-11-17, review: 'top' was applied by a live change only, and came back at the bottom after a restart.
        check(f"startup: the buttons are at the {position}, where the setting says",
              settles(lambda: bar_place() == position), f"at {bar_place()}")
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
        expected = tuple(key for key in ('agent', 'exploring', 'filtering', 'exporting', 'configuration')
                         if key in wanted and (key != 'agent' or 'agent' in d._fm_sections._headers))
        check('startup: the sections left apart are in their panels', panels.detached() == expected
              and all(not panels.panel(key).isHidden() and panel_place(panels.panel(key)) != 'tab' for key in expected),
              f"{panels.detached()} expected {expected}")
        if 'exploring' in expected:
            mirror = explo_mirror()
            check('startup: EXPLORING in its panel shows its chooser of the current layer, the dock keeps a section',
                  mirror is not None and mirror.isVisible() and panels.panel('exploring').isAncestorOf(mirror)
                  and bool(panels.in_dock()) and d.isVisible(), f"in dock={panels.in_dock()} groups={panels.groups()}")
            if panels.in_dock() == ('agent',):
                check('startup: AGENT, the only section left in the dock, is open',
                      d._fm_sections._open_in_stack('agent') and d._fm_sections.is_open('agent'))
            grab_window('startup_exploring_apart')
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
    if 'agent' in d._fm_sections._headers:
        # 2026-11-16, audit: with AGENT open there was no button at all, while Undo, Redo and Compare walk its steps.
        d._fm_sections.open_top('agent')
        QApplication.processEvents()
        check('sections: AGENT open, the buttons of FILTERING show for Undo, Redo and Compare',
              d.agent_has_focus() and bars.frame('filtering').isVisible()
              and actions_shown() == [name for name in FILTERING_ACTIONS if name in SECTION['all']]
              and not action_button('filter').isEnabled(), str(actions_shown()))
        d._fm_sections.open_top('exploring')
        QApplication.processEvents()
        check('sections: AGENT folded, no bar again', actions_shown() == [] and not bars.frame('filtering').isVisible(),
              str(actions_shown()))
        open_section(d.EXPORTING)
        d._fm_sections.open_top('agent')
        QApplication.processEvents()
        check('sections: AGENT open over EXPORTING, the row is the one of EXPORTING alone',
              bars.frame('exporting').isVisible() and not bars.frame('filtering').isVisible(), str(actions_shown()))
        d._fm_sections.open_top('exploring')
        open_section(None)
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
    check('panels: FILTERING and EXPLORING can leave the dock', panels.can_detach('filtering')
          and panels.can_detach('exploring'))
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
    # 2026-11-16, audit: the bar stayed in the dock for an Export greyed out beside About.
    check('panels: the other buttons stay in the bar of the dock, not shown while none of them acts',
          not d.frame_actions.isVisible() and action_button('export').parentWidget() is d.frame_actions
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
    check('panels: EXPORTING open in the dock, Export and Filter both act, the bar of the dock shows',
          action_button('export').isEnabled() and action_button('filter').isEnabled() and d.frame_actions.isVisible()
          and action_button('export').isVisible())
    open_section(d.CONFIGURATION)
    check('panels: CONFIGURATION open in the dock, the bar shows for About', d.frame_actions.isVisible())
    open_section(None)
    grab_widget(panel, 'panel_filtering')
    grab('dock_filtering_apart')
    rail = d._fm_sections.bottom_rail
    stack = d.splitter_main.widget(1)
    last = rail.mapTo(stack, QPoint(0, rail.height())).y()
    check('panels: the rail of the dock keeps the chips of the sections left, whole',
          rail.shown_sections() == ['exporting', 'configuration'] and last <= stack.height()
          and stack.height() <= 34 + 30, f"{rail.shown_sections()} last={last} stack={stack.height()}")
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
    """EXPORTING and CONFIGURATION join the panel of FILTERING, listed in its rail; AGENT gets its own panel: the dock
    keeps EXPLORING."""
    d = dock()
    panels = d._fm_panels
    sections = d._fm_sections
    window = iface.mainWindow()
    filtering = panels.panel('filtering')
    if not check('stack: FILTERING is still apart, alone in its panel without a rail', filtering is not None
                 and filtering.members == ['filtering'] and not filtering.rail.isVisible()):
        return None
    check('stack: EXPORTING taken out joins the panel of FILTERING', panels.open_smart('exporting'))
    QApplication.processEvents()
    export = action_button('export')
    check('stack: one panel for both, listed in its rail, the one that came is open',
          panels.panel('exporting') is filtering and filtering.members == ['filtering', 'exporting']
          and filtering.rail.isVisible() and filtering.rail.shown_sections() == ['filtering', 'exporting']
          and filtering.current() == 'exporting' and filtering.rail.chip('exporting').isChecked()
          and d.EXPORTING.isVisible() and not d.FILTERING.isVisible(),
          f"{filtering.members} current={filtering.current()}")
    check('stack: the panel is named after its sections, QGIS knows it by the first one',
          filtering.windowTitle() == 'FILTERING · EXPORTING' and filtering.objectName() == 'FilterMatePanel_filtering',
          f"{filtering.windowTitle()} {filtering.objectName()}")
    check('stack: Export is in the panel and acts; the buttons of FILTERING are folded with it', export.isVisible()
          and export.isEnabled() and filtering.isAncestorOf(export) and not action_button('filter').isVisible()
          and action_button('filter').isEnabled() and filtering.isAncestorOf(action_button('filter')))
    open_section(d.CONFIGURATION)
    in_bar = [name for name in actions_shown() if action_button(name).parentWidget() is d.frame_actions]
    shown_open = d.frame_actions.isVisible() and in_bar == ['about']
    open_section(None)
    check('stack: the bar of the dock keeps About alone, shown while CONFIGURATION is open', shown_open
          and not d.frame_actions.isVisible() and action_button('about').parentWidget() is d.frame_actions,
          f"open={shown_open} in the bar={in_bar} folded={d.frame_actions.isVisible()}")
    filtering.rail.chip('filtering').click()
    QApplication.processEvents()
    check('stack: a click on a chip of the panel opens its section, with its buttons', filtering.current() == 'filtering'
          and d.FILTERING.isVisible() and not d.EXPORTING.isVisible() and action_button('filter').isVisible()
          and not export.isVisible(), str(actions_shown()))
    check('stack: About stays in the bar of the dock, folded while CONFIGURATION is',
          not d.frame_actions.isVisible() and action_button('about').parentWidget() is d.frame_actions,
          str(actions_shown()))
    check('stack: CONFIGURATION joins them', panels.open_smart('configuration')
          and filtering.members == ['filtering', 'exporting', 'configuration']
          and filtering.isAncestorOf(action_button('about')), str(filtering.members))
    QApplication.processEvents()
    check('stack: no bar and no lower stack left in the dock', not d.frame_actions.isVisible()
          and not d.splitter_main.widget(1).isVisible() and sections.is_open('exploring'))
    took = filtering.rail.drop('configuration', 1, filtering.rail)  # dragged before the first chip
    QApplication.processEvents()
    check('stack: a chip of the panel dragged first, the panel follows', took
          and filtering.members == ['configuration', 'filtering', 'exporting']
          and filtering.objectName() == 'FilterMatePanel_configuration'
          and filtering.windowTitle() == 'CONFIGURATION · FILTERING · EXPORTING'
          and QSettings().value(DETACHED_KEY) == 'configuration+filtering+exporting',
          f"{filtering.members} {filtering.objectName()} saved={QSettings().value(DETACHED_KEY)}")
    filtering.rail.drop('configuration', filtering.rail.width() - 1, filtering.rail)
    QApplication.processEvents()
    check('stack: and dragged back last', filtering.members == ['filtering', 'exporting', 'configuration']
          and filtering.objectName() == 'FilterMatePanel_filtering', str(filtering.members))
    has_agent = 'agent' in sections._headers
    if has_agent:
        check('stack: AGENT leaves the dock', panels.detach('agent'))
        QApplication.processEvents()
        agent = panels.panel('agent')
        page = sections._pages['agent']
        check('stack: AGENT is in a panel of its own, not a tab of the dock or of the other panel',
              agent is not None and agent is not filtering and agent.isAncestorOf(page)
              and agent not in window.tabifiedDockWidgets(d) and agent not in window.tabifiedDockWidgets(filtering)
              and not sections.top_rail.chip('agent').isVisible() and sections.is_open('exploring')
              and 'agent' in sections.detached, panel_place(agent))
        sections.open_top('agent')  # the agent asks for an answer of the user
        QApplication.processEvents()
        check('stack: AGENT asked to open shows its panel, EXPLORING stays open',
              sections.is_open('exploring') and agent is not None and agent.isVisible() and page.isVisible()
              and sections.is_open('agent'))
        check('stack: Undo and Redo stay with FILTERING while AGENT is apart', not d.agent_has_focus())
    else:
        report('SKIP', 'stack: AGENT leaves the dock', 'no AGENT section in this dock')
    check('stack: the panels are kept with their sections', QSettings().value(DETACHED_KEY)
          == ('filtering+exporting+configuration' + (',agent' if has_agent else '')),
          str(QSettings().value(DETACHED_KEY)))
    everyone = {id(panels.panel(key)): panels.panel(key) for key in panels.detached()}.values()
    sheet = d.dockWidgetContents.styleSheet()
    d.dockWidgetContents.setStyleSheet(sheet + '\n/* another theme */')
    QApplication.processEvents()
    check('stack: a change of theme reaches the panels',
          all(panel.widget().styleSheet().endswith('/* another theme */') for panel in everyone))
    d.dockWidgetContents.setStyleSheet(sheet)
    QApplication.processEvents()
    filtering.open('filtering')
    QApplication.processEvents()
    grab_widget(filtering, 'panel_stack')
    if has_agent:
        grab_widget(panels.panel('agent'), 'panel_agent')
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
    panels.panel('filtering').close()  # the X of the panel that holds FILTERING, EXPORTING and CONFIGURATION
    return lambda: 'filtering' not in panels.detached()


def s_section_back_check():
    """A panel closed: its sections are back in the dock, folded; then every section back, and restored."""
    d = dock()
    panels = d._fm_panels
    sections = d._fm_sections
    toolbox = d.toolBox_tabTools
    window = iface.mainWindow()
    rail = sections.bottom_rail
    check('panels: closing the panel brings its three sections back to the dock, folded',
          all(d.isAncestorOf(page) for page in (d.FILTERING, d.EXPORTING, d.CONFIGURATION))
          and rail.shown_sections() == ['filtering', 'exporting', 'configuration']
          and all(toolbox.isItemEnabled(toolbox.indexOf(page)) for page in (d.FILTERING, d.EXPORTING, d.CONFIGURATION))
          and toolbox.currentWidget() is sections._nothing and d.splitter_main.widget(1).isVisible()
          and not [panel for panel in window.findChildren(QDockWidget, 'FilterMatePanel_filtering')
                   if not panel.isHidden()],
          f"current={toolbox.currentWidget().objectName()} apart={panels.detached()}")
    check('panels: their buttons are back in the bar of the dock',
          all(action_button(name).parentWidget() is d.frame_actions for name in ACTION_NAMES
              if action_button(name) is not None) and not d.filtering_detached)
    open_section(d.FILTERING)
    check('panels: FILTERING opens in the dock again, with its widgets and its buttons',
          toolbox.currentWidget() is d.FILTERING and d.comboBox_filtering_current_layer.isVisible()
          and action_button('filter').isEnabled() and action_button('filter').isVisible()
          and d.frame_actions.isVisible())
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
          and ('agent' not in sections._headers or (sections.top_rail.chip('agent').isVisible()
                                                    and d.isAncestorOf(sections._pages['agent'])))
          and held == [name for name in ACTION_NAMES if action_button(name) is not None]
          and order == SECTION['all'] and not QSettings().value(DETACHED_KEY),
          f"pages={pages} held={held} order={order} saved={QSettings().value(DETACHED_KEY)!r}")
    leftovers = [panel.objectName() for panel in window.findChildren(QDockWidget)
                 if panel.objectName().startswith('FilterMatePanel_') and not panel.isHidden()]
    check('panels: no panel left in QGIS', not leftovers, str(leftovers))
    QSettings().setValue(DETACHED_KEY, 'exporting+nothing+FILTERING, configuration')  # as saved before, and noise
    restored = panels.restore()
    QApplication.processEvents()
    shared = panels.panel('exporting')
    check('panels: the panels of the last time come back with their sections in their order',
          restored == ['exporting', 'filtering', 'configuration']
          and panels.groups() == (('exporting', 'filtering'), ('configuration',))
          and shared is panels.panel('filtering') and shared.objectName() == 'FilterMatePanel_exporting'
          and panels.panel('configuration') is not shared, f"{restored} {panels.groups()}")
    panels.attach_all()
    QApplication.processEvents()
    open_section(d.FILTERING)
    check('panels: left as found', panels.detached() == () and toolbox.currentWidget() is d.FILTERING
          and actions_shown() == SECTION['all'] and not QSettings().value(DETACHED_KEY), str(actions_shown()))
    grab('sections_end')
    return settled()


def s_section_restart():
    """As after a restart of QGIS: the dock and its panel come back where they were."""
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    module = importlib.import_module(f'{PACKAGE}.ui.layout.section_panels')
    area = window.dockWidgetArea(d)
    open_section(d.FILTERING)
    panels.detach('filtering')
    panels.open_smart('exporting')
    QApplication.processEvents()
    panel = panels.panel('filtering')
    place = panel_place(panel)
    if not check('restart: FILTERING and EXPORTING share a panel, below the dock or beside it',
                 place in ('below', 'beside') and panels.groups() == (('filtering', 'exporting'),),
                 f"place={place} dock={d.height()} floating={d.isFloating()}/{panel.isFloating() if panel else None} "
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
    again = panels.restore()  # and the panels of the last time
    QApplication.processEvents()
    panel = panels.panel('filtering')
    check('restart: the dock is back where QGIS kept it', restored and window.dockWidgetArea(d) == area
          and d.isVisible() and (menu is None or d.toggleViewAction() in menu.actions()), f"restored={restored}")
    check('restart: the panel is back with its two sections, where it was',
          again == ['filtering', 'exporting'] and panel is not None and panel is panels.panel('exporting')
          and not panel.isHidden() and panel_place(panel) == place,
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


def menu_names(menu):
    return [action.objectName() for action in menu.actions() if not action.isSeparator()] if menu is not None else []


def drop_as_tab(first, second):
    """``second`` put as a tab of ``first``, as a drop with the mouse does.

    It leaves the layout of the window first. Tabbed while it is still laid out, Qt 6.10 makes two tab bars for the
    one group (QMainWindowLayout::getTabBar lays the window out again, which makes the bar a second time); the spare
    one is deleted while it is being shown when another move ends its animation in between, and QGIS dies in
    QMainWindowLayout::showTabBars. A drop with the mouse goes another way in Qt (plug), and the plugin never tabs
    a dock itself."""
    window = iface.mainWindow()
    window.removeDockWidget(second)
    QApplication.processEvents()
    window.tabifyDockWidget(first, second)
    second.show()
    QApplication.processEvents()


def s_section_tabbed_dock():
    """2026-11-16, review: the dock shares its tabs with a panel of QGIS (Layers). A panel split from a tab is one
    more tab (Qt): the section taken out was a tab of the dock, and merged back at once."""
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    layers = window.findChild(QDockWidget, 'Layers')
    if not check('tabbed dock: QGIS has its Layers panel', layers is not None and layers.isVisible()):
        return None
    state = window.saveState()  # put back at the end: the places of this step are not those of the next ones
    drop_as_tab(layers, d)
    d.raise_()
    QApplication.processEvents()
    tabbed = layers in window.tabifiedDockWidgets(d)
    took = panels.detach('filtering')
    QApplication.processEvents()
    QApplication.processEvents()
    panel = panels.panel('filtering')
    check('tabbed dock: FILTERING taken out of a dock that shares its tabs stays out, in a place of its own',
          tabbed and took and panel is not None and panel.isVisible() and panels.detached() == ('filtering',)
          and d not in window.tabifiedDockWidgets(panel) and on_screen(d.FILTERING) and on_screen(d.frame_exploring),
          f"tabbed={tabbed} took={took} apart={panels.detached()} "
          f"mates={[w.objectName() for w in window.tabifiedDockWidgets(panel)] if panel else None} "
          f"floating={panel.isFloating() if panel else None}")
    panels.detach_all()
    QApplication.processEvents()
    QApplication.processEvents()
    has_agent = 'agent' in d._fm_sections._headers
    lower = ('filtering', 'exporting', 'configuration')
    ours = [d] + [panels.panel(key) for key in panels.detached()]
    check('tabbed dock: the other sections follow, none as a tab of the dock or of a panel of FilterMate',
          set(panels.groups()) == {lower} | ({('agent',)} if has_agent else set())
          and not any(mate in ours for one in ours for mate in window.tabifiedDockWidgets(one)),
          f"{panels.groups()} "
          f"{[(one.objectName(), [w.objectName() for w in window.tabifiedDockWidgets(one)]) for one in ours]}")
    panels.attach_all()
    QApplication.processEvents()
    window.restoreState(state)
    QApplication.processEvents()
    d.show()
    d.raise_()
    open_section(d.FILTERING)
    QApplication.processEvents()
    check('tabbed dock: left as found', panels.detached() == () and not QSettings().value(DETACHED_KEY)
          and d.isVisible() and layers not in window.tabifiedDockWidgets(d) and layers.isVisible()
          and d.toolBox_tabTools.currentWidget() is d.FILTERING and actions_shown() == SECTION['all'],
          f"apart={panels.detached()} mates={[w.objectName() for w in window.tabifiedDockWidgets(d)]} {actions_shown()}")
    return settled()


def s_section_restore_order():
    """2026-11-16, review: AGENT is installed after the other sections when the dock opens. A panel it shares came
    back named after the section that was there, at another place than QGIS kept, and AGENT joined it last."""
    d = dock()
    panels, sections = d._fm_panels, d._fm_sections
    if 'agent' not in sections._headers:
        check('restore: skipped without AGENT', True)
        return settled()
    module = importlib.import_module(f'{PACKAGE}.ui.layout.section_panels')
    QSettings().setValue(DETACHED_KEY, 'agent+filtering')
    page = sections._pages.pop('agent')  # as when the dock is built: AGENT is not there yet
    try:
        first = panels.restore()
        QApplication.processEvents()
        panel = panels.panel('filtering')
        early = (first, panel.objectName() if panel else None, QSettings().value(DETACHED_KEY))
    finally:
        sections._pages['agent'] = page
    second = panels.restore()  # AGENT is installed
    QApplication.processEvents()
    panel = panels.panel('filtering')
    name = module.PANEL_NAME.format('agent')
    check('restore: a panel AGENT shares waits for it under its name, and AGENT takes its place in it',
          early == (['filtering'], name, 'agent+filtering') and second == ['agent'] and panel is not None
          and panel is panels.panel('agent') and panel.members == ['agent', 'filtering'] and panel.objectName() == name
          and panel.current() == 'agent' and panel.kept_name is None,
          f"early={early} second={second} members={panel.members if panel else None} "
          f"name={panel.objectName() if panel else None} current={panel.current() if panel else None}")
    panels.attach_all()
    QApplication.processEvents()
    open_section(d.FILTERING)
    check('restore: left as found', panels.detached() == () and not QSettings().value(DETACHED_KEY)
          and d.toolBox_tabTools.currentWidget() is d.FILTERING and actions_shown() == SECTION['all'],
          str(actions_shown()))
    return settled()


def put_behind_layers(key):
    """The panel of the section ``key`` as a tab of the Layers panel of QGIS, behind it: Qt calls its page
    visible, nobody sees it. (A panel of FilterMate is never a tab of the dock: they merge.)"""
    window = iface.mainWindow()
    layers, panel = window.findChild(QDockWidget, 'Layers'), dock()._fm_panels.panel(key)
    if layers is None or panel is None:
        return False
    if panel not in window.tabifiedDockWidgets(layers):
        drop_as_tab(layers, panel)
    layers.raise_()
    QApplication.processEvents()
    return True


def s_section_group():
    """Separate, group and merge: from the menus, by putting two panels together, and by dragging a chip onto a
    panel, back onto the dock, or out of every panel."""
    d = dock()
    panels = d._fm_panels
    sections = d._fm_sections
    window = iface.mainWindow()
    bottom = sections.bottom_rail
    has_agent = 'agent' in sections._headers
    menu = panels.build_menu('filtering', d)
    check('group: in the dock, a section is offered its own panel, alone or with the others',
          menu_names(menu) == ['action_section_detach', 'action_section_detach_all'], str(menu_names(menu)))
    menu_action(menu, 'action_section_detach_all').trigger()
    QApplication.processEvents()
    lower = ('filtering', 'exporting', 'configuration')
    if not check('group: taken out, FILTERING, EXPORTING and CONFIGURATION share a panel, AGENT has its own',
                 panels.groups() == ((('agent',),) if has_agent else ()) + (lower,), str(panels.groups())):
        panels.attach_all()
        return None
    stack = panels.panel('filtering')
    check('group: the panel shows the section that was open in the dock, not the last one that came',
          stack.current() == 'filtering' and d.FILTERING.isVisible() and action_button('filter').isVisible()
          and not d.CONFIGURATION.isVisible(), f"current={stack.current()}")
    menu = panels.build_menu('exporting', stack)
    check('group: a section that shares a panel is offered its own, the other panels, and to merge back',
          menu_names(menu) == ['action_section_detach'] + (['action_section_group_agent'] if has_agent else [])
          + ['action_section_attach', 'action_section_attach_all'], str(menu_names(menu)))
    menu_action(menu, 'action_section_detach').trigger()
    QApplication.processEvents()
    exporting = panels.panel('exporting')
    check('group: EXPORTING gets a panel of its own, not a tab of the one it left', exporting is not stack
          and exporting.members == ['exporting'] and stack.members == ['filtering', 'configuration']
          and exporting not in window.tabifiedDockWidgets(stack) and action_button('export').isEnabled(),
          f"{panels.groups()} {panel_place(exporting)}")
    # Two panels of FilterMate put together merge: EXPORTING dropped as a tab of the other panel.
    drop_as_tab(stack, exporting)
    alone = panels.panel('exporting') is stack  # the signals of the drop already merged them
    panels._fuse_tabbed(exporting)
    QApplication.processEvents()
    check('group: a panel dropped as a tab of another one gives it its sections',
          panels.panel('exporting') is stack and stack.members == ['filtering', 'configuration', 'exporting']
          and stack.current() == 'exporting' and len(panels.groups()) == (2 if has_agent else 1),
          f"{panels.groups()} merged by the signals alone={alone}")
    if has_agent:
        agent = panels.panel('agent')
        drop_as_tab(d, agent)
        panels._fuse_tabbed(agent)
        QApplication.processEvents()
        check('group: a panel dropped as a tab of the dock gives its sections back to the dock',
              'agent' not in panels.detached() and sections.top_rail.chip('agent').isVisible()
              and d.isAncestorOf(sections._pages['agent']), str(panels.groups()))
        # 2026-11-16, review: the place QGIS keeps for that panel is now a tab of the dock. Taken out again, AGENT
        # went back there, and merged at once.
        panels.detach('agent')
        QApplication.processEvents()
        QApplication.processEvents()
        again = panels.panel('agent')
        check('group: taken out again after it merged as a tab of the dock, AGENT stays out, in another place',
              again is not None and again.isVisible() and d not in window.tabifiedDockWidgets(again)
              and stack not in window.tabifiedDockWidgets(again),
              f"{panels.groups()} mates={[w.objectName() for w in window.tabifiedDockWidgets(again)] if again else None}")
        panels.attach('agent')
        QApplication.processEvents()
    # A chip dragged from a rail to another (``drop`` is what the drop event of a rail calls).
    check('group: the dock takes back a chip of a panel on the rail of its stack only',
          bottom.takes('configuration', stack.rail) and not sections.top_rail.takes('configuration', stack.rail)
          and not bottom.takes('exploring', sections.top_rail))
    bottom.drop('configuration', 0, stack.rail)
    QApplication.processEvents()
    check('group: a chip of a panel dropped on the rail of the dock: its section comes back',
          'configuration' not in panels.detached() and d.isAncestorOf(d.CONFIGURATION)
          and bottom.shown_sections() == ['configuration'] and stack.members == ['filtering', 'exporting'],
          f"{panels.groups()} {bottom.shown_sections()}")
    check('group: a panel takes the chip of a section of the dock, EXPLORING as the others, not one it holds',
          stack.rail.takes('configuration', bottom) and stack.rail.takes('exploring', sections.top_rail)
          and panels.can_take('configuration', stack) and not panels.can_take('filtering', stack))
    stack.rail.drop('configuration', 0, bottom)
    QApplication.processEvents()
    check('group: a chip of the dock dropped on the rail of a panel: its section joins it, there',
          panels.panel('configuration') is stack and stack.members == ['configuration', 'filtering', 'exporting']
          and stack.current() == 'configuration' and not bottom.shown_sections(), str(panels.groups()))
    far = window.mapToGlobal(QPoint(60, 300))  # over the map, out of the dock and of every panel
    panels._on_dropped_out('filtering', stack.mapToGlobal(QPoint(40, 60)))
    QApplication.processEvents()
    check('group: a chip dropped within its own panel changes nothing', panels.panel('filtering') is stack)
    panels._on_dropped_out('filtering', far)
    QApplication.processEvents()
    torn = panels.panel('filtering')
    check('group: a chip dropped out of every panel gets a new one, floating where it was dropped',
          torn is not stack and torn.members == ['filtering'] and torn.isFloating() and torn.isVisible()
          and stack.members == ['configuration', 'exporting'] and action_button('filter').isEnabled()
          and abs(torn.frameGeometry().center().x() - far.x()) < torn.width() and torn.frameGeometry().left() >= 0,
          f"{panels.groups()} floating={torn.isFloating()} at {torn.frameGeometry().topLeft()} for {far}")
    panels._on_dropped_out('filtering', d.mapToGlobal(QPoint(40, 200)))
    QApplication.processEvents()
    check('group: a chip of a panel dropped on the dock, out of its rails, comes back all the same',
          'filtering' not in panels.detached() and d.isAncestorOf(d.FILTERING), str(panels.groups()))
    # 2026-11-16, review: QDrag.exec says the same of a drop nobody took and of a drag given up with Escape, which
    # made a panel. The rail takes the drop itself where nothing of FilterMate does: ``catcher`` watches the windows
    # of the application while the chip is dragged (a drag a widget ignores goes up to its window). Called here as
    # Qt calls it; FM_ONLY=mouse drags with a real pointer.
    rail_module = importlib.import_module(f'{PACKAGE}.ui.widgets.section_rail')
    window = iface.mainWindow()
    accepted_before = window.acceptDrops()
    mime = QMimeData()
    mime.setData(rail_module.SECTION_MIME, b'filtering')
    buttons, keys = Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
    catcher = bottom.catcher('filtering')
    catcher.watch()
    watched = [shown for shown, _accepted in catcher._windows]
    ours = [panel for panel in panels._panels if panel.isFloating()] + ([d] if d.isFloating() else [])
    on_map = QDragEnterEvent(QPoint(80, 90), Qt.DropAction.MoveAction, mime, buttons, keys)
    on_map.ignore()
    took_map = catcher.eventFilter(window, on_map)
    other = QMimeData()
    other.setData(rail_module.SECTION_MIME, b'exporting')
    not_its_chip = QDragEnterEvent(QPoint(80, 90), Qt.DropAction.MoveAction, other, buttons, keys)
    not_its_chip.ignore()
    took_other = catcher.eventFilter(window, not_its_chip)
    dropped = QDropEvent(QPointF(80, 90), Qt.DropAction.MoveAction, mime, buttons, keys)
    catcher.eventFilter(window, dropped)
    accepting = window.acceptDrops()
    catcher.unwatch()
    check('drag: the windows of QGIS take the drop of the chip dragged, not those of FilterMate, and only while '
          'it is dragged', window in watched and not any(one in watched for one in ours) and accepting
          and took_map and on_map.isAccepted() and not took_other
          and catcher.place == window.mapToGlobal(QPoint(80, 90)) and window.acceptDrops() == accepted_before,
          f"watched={[one.objectName() for one in watched]} map={took_map}/{on_map.isAccepted()} other={took_other} "
          f"place={catcher.place}")
    bottom.finish_drag('filtering', None)  # given up with Escape, or dropped out of QGIS: nothing took it
    QApplication.processEvents()
    check('drag: a drag given up with Escape changes nothing', 'filtering' not in panels.detached()
          and len(panels.groups()) == 1, str(panels.groups()))
    bottom.finish_drag('filtering', catcher.place)  # dropped on the map
    QApplication.processEvents()
    dropped_panel = panels.panel('filtering')
    check('drag: a chip of the dock dropped on the map gets a panel, floating there',
          dropped_panel is not None and dropped_panel.isFloating() and dropped_panel.members == ['filtering'],
          str(panels.groups()))
    panels._on_dropped_out('filtering', stack.mapToGlobal(QPoint(40, 120)))  # on a panel, out of its rail
    QApplication.processEvents()
    check('drag: a chip dropped on another panel, out of its rail, joins it all the same',
          panels.panel('filtering') is stack and 'filtering' in stack.members, str(panels.groups()))
    panels.attach('filtering')
    QApplication.processEvents()
    panels._show_panel_menu(stack, QPoint(8, 4))  # a right click on the title of the panel
    QApplication.processEvents()
    shown = [popup for popup in stack.findChildren(QMenu) if popup.isVisible()]
    check('group: a right click on the title of a panel opens the menu of its open section', len(shown) == 1
          and 'action_section_attach' in menu_names(shown[0]) if shown else False)
    for popup in shown:
        popup.hide()
    panels._show_panel_menu(stack, stack.widget().geometry().center())
    QApplication.processEvents()
    check('group: not a right click in the contents of the panel',
          not [popup for popup in stack.findChildren(QMenu) if popup.isVisible()])
    menu = panels.build_menu('filtering', d)
    check('group: a section of the dock is offered the panel of its stack first, then its own',
          menu_names(menu)[:2] == ['action_section_group_configuration', 'action_section_detach'], str(menu_names(menu)))
    menu_action(menu, 'action_section_attach_all').trigger()
    QApplication.processEvents()
    for key in ('FilterMate/sections/top_order', 'FilterMate/sections/bottom_order'):
        QSettings().remove(key)
    bottom.drop('configuration', bottom.width() - 1, bottom)  # the usual order of the lower rail again
    QApplication.processEvents()
    for key in ('FilterMate/sections/top_order', 'FilterMate/sections/bottom_order'):
        QSettings().remove(key)
    open_section(d.FILTERING)
    check('group: every section merged back into FilterMate', panels.detached() == () and panels.groups() == ()
          and not QSettings().value(DETACHED_KEY) and actions_shown() == SECTION['all']
          and bottom.sections() == ['filtering', 'exporting', 'configuration']
          and d.toolBox_tabTools.currentWidget() is d.FILTERING, f"{panels.groups()} {actions_shown()} {bottom.sections()}")
    return settled()


def s_section_off():
    """A section turned off (APP.OPTIONS.FILTERING.enabled) while it is in a panel: it leaves the panel, and is in it
    again when it is turned on. Undo, Redo and Compare stay within reach."""
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
    # Turned off again, then every section merged back: that last word holds the day it is turned on.
    options['FILTERING'] = {'enabled': {'value': False}}
    d.apply_section_options()
    QApplication.processEvents()
    kept_apart = QSettings().value(DETACHED_KEY)
    panels.attach_all()
    options['FILTERING'] = {'enabled': {'value': True}}
    d.apply_section_options()
    QApplication.processEvents()
    check('off: merged back while it was off, FILTERING is in the dock when it is turned on again',
          kept_apart == 'filtering' and not QSettings().value(DETACHED_KEY) and panels.detached() == ()
          and d.isAncestorOf(d.FILTERING) and bottom_header(d.FILTERING).isVisible(),
          f"kept={kept_apart} saved={QSettings().value(DETACHED_KEY)} apart={panels.detached()}")
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


SECTION_STEPS = [s_section_setup, s_section_rail, s_section_bars, s_section_tabbed_dock, s_vector_source,
                 s_vector_select, s_section_detach,
                 s_section_filter,
                 s_section_filter_check, s_section_undo, s_section_undo_check, s_section_stack,
                 s_section_close_dock, s_section_reopen_dock, s_section_close_panel, s_section_back_check,
                 s_section_restart, s_section_restore_order, s_section_group, s_section_off]

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
    told = [words for words in ('a rail that lists its sections', 'EXPLORING holds', 'FILTERING filters',
                                'EXPORTING writes', 'AGENT does', 'CONFIGURATION lists',
                                'By default every section is in this panel', 'A panel holds one section or several',
                                'The buttons act') if words in text]
    links = list(thread_links())
    check('tour: told in the AGENT thread, which opens: each section, the panels, the buttons, then the links',
          d._fm_sections.is_open('agent') and len(told) == 9 and links[:1] == ['Take every section out of FilterMate']
          and 'Set up FilterMate' in links, f"told={len(told)} links={links}")
    check('tour: nothing is kept in the conversation, no model is asked', not chat._transcript
          and chat._engine is None)
    labels = [label for label in panel.thread.findChildren(QLabel) if label.isVisible()]
    check('tour: no paragraph wider than the thread', all(label.width() <= panel.thread.width() for label in labels),
          str(max((label.width() for label in labels), default=0)))
    grab('tour')
    thread_links()['Take every section out of FilterMate'].click()
    return waits(0.6)


def s_tour_links_check():
    """The links of the tour do what was just said: every section out of FilterMate, then all of them back."""
    d, chat = dock(), agent_chat()
    panels = d._fm_panels
    lower = tuple(key for key in present_sections() if key != 'agent')
    check('tour: its link takes every section out, AGENT in its own panel and the others together, its thread '
          'still in view', panels.detached() == present_sections() and d._fm_sections.is_open('agent')
          and on_screen(chat.panel) and lower in panels.groups() and len(panels.groups()) == len(present_sections()) - 2,
          f"groups={panels.groups()} agent in view={d._fm_sections.is_open('agent')}")
    grab_window('tour_every_section_apart')
    chat.show_tour()  # told again: what can be done now is to bring them back
    QApplication.processEvents()
    links = list(thread_links())
    back = 'Merge every section back into FilterMate'
    WELCOME['links'] = links
    if back in links:
        thread_links()[back].click()
    return waits(0.6)  # AGENT comes back folded: its section opens once Qt has laid the dock out


def s_tour_merged_check():
    d = dock()
    check('tour: told again with the sections apart, its link merges them back, AGENT open in the dock',
          'Merge every section back into FilterMate' in WELCOME['links'] and d._fm_panels.detached() == ()
          and d._fm_sections.is_open('agent') and on_screen(agent_chat().panel),
          f"links={WELCOME['links']} apart={d._fm_panels.detached()} agent open={d._fm_sections.is_open('agent')}")
    leave_welcome()
    return settled()


def s_setup_layout():
    """The setup asks where the sections go, with the buttons: in panels of QGIS, the buttons under them."""
    d, chat = dock(), agent_chat()
    chat.new_conversation()
    WELCOME['position'] = d._action_bar_manager.get_position()
    WELCOME['started'] = chat.start_setup()
    asked = []
    while _wizard_card() is not None and len(asked) < 30:  # every card, however many steps the setup has
        card = _wizard_card()
        asked.append([chip.text() for chip in card._chips])
        if asked[-1] == ['Layout', 'Headers', 'Buttons']:
            QApplication.processEvents()
            agent_chat().panel.thread.ensureWidgetVisible(card)
            QApplication.processEvents()
            grab('setup_layout_step')
        _answer_card(tick=('In panels of QGIS', 'Under each section'))
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
          WELCOME['started'] is True and ['Layout', 'Headers', 'Rows', 'Buttons'] in WELCOME['asked']
          and any(chips[:1] == ['Vector tools'] for chips in WELCOME['asked']) and _wizard_card() is None,
          str(WELCOME['asked']))
    check('setup: the sections and the buttons on the card of the changes, nothing moved before Apply',
          len(WELCOME['rows']) == 2 and any('in panels of QGIS' in row for row in WELCOME['rows'])
          and WELCOME['apart_before_apply'] == (), f"rows={WELCOME['rows']} apart={WELCOME['apart_before_apply']}")
    check('setup: Apply takes every section out of FilterMate and puts the buttons under their section',
          WELCOME['card'] is not None and WELCOME['card'].done and panels.detached() == present_sections()
          and manager.get_position() == 'sections', f"apart={panels.detached()} position={manager.get_position()}")
    check('setup: AGENT moved with the others, its thread is still in view', d._fm_sections.is_open('agent')
          and on_screen(agent_chat().panel))
    text = agent_chat().panel.thread.toPlainText()
    check('setup: it says how to group and merge, and offers how FilterMate works',
          'to group them' in text and 'How FilterMate works' in thread_links(), text[-300:])
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


def s_welcome_by_state():
    """The requests of the welcome follow the project (2026-11-20), on a project of their own read as the controller reads
    the open one (the layers of the dock stay where they are): nothing open, a raster, a vector layer and a selection;
    a filter; and the link that reconfigures FilterMate with a model. The dock is left as it was found."""
    from qgis.core import QgsFeature, QgsGeometry, QgsPointXY
    from osgeo import gdal
    d, chat = dock(), agent_chat()
    panel = chat.panel
    prompts = importlib.import_module(f'{PACKAGE}.core.agent.example_prompts')
    reader = importlib.import_module(f'{PACKAGE}.adapters.qgis.project_facts')
    catalog = {example.key: example for example in prompts.CATALOG}
    scratch, kept = QgsProject(), {'provider': panel.facts_provider, 'ready': panel._ready}
    active = []

    def facts():
        return reader.read_facts(project=scratch, active=active[0] if active else None)

    def drawn():
        panel.refresh_examples()
        QApplication.processEvents()
        return panel.example_keys

    def true_now():
        tokens = facts().tokens()
        return all(set(catalog[key].needs) <= tokens for key in panel.example_keys)

    chat.new_conversation()
    d._fm_sections.open_top('agent')
    panel.facts_provider = facts
    panel.set_ready(True, 'Claude (Anthropic) · claude-haiku-5-5')  # a model is connected
    QApplication.processEvents()
    empty = drawn()
    check('welcome by state: nothing open offers only ways to bring data in',
          len(empty) == 4 and all(catalog[key].group == prompts.DATA for key in empty) and true_now()
          and all(button.isVisible() for button in panel.example_buttons), str(empty))
    grab('welcome_empty_project')
    folder = tempfile.mkdtemp()
    path = os.path.join(folder, 'dem.tif')
    dataset = gdal.GetDriverByName('GTiff').Create(path, 4, 4, 1, gdal.GDT_Float32)
    dataset.SetGeoTransform((650000, 10, 0, 6860000, 0, -10))
    dataset.GetRasterBand(1).Fill(100)
    dataset = None
    raster = QgsRasterLayer(path, 'dem')
    scratch.addMapLayer(raster)
    active[:] = [raster]
    with_raster = drawn()
    check('welcome by state: a raster active gives requests about it, none about a vector layer',
          with_raster != empty and true_now() and any({'active_raster', 'active_elevation'} & set(catalog[key].needs) for key in with_raster)
          and not any({'vector', 'active_vector', 'selection', 'local_selection'} & set(catalog[key].needs) for key in with_raster),
          str(with_raster))
    grab('welcome_raster_active')
    points = QgsVectorLayer('Point?crs=EPSG:4326&field=name:string', 'pts', 'memory')
    features = []
    for index in range(3):
        feature = QgsFeature(points.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(index, index)))
        feature.setAttributes([f'p{index}'])
        features.append(feature)
    points.dataProvider().addFeatures(features)
    scratch.addMapLayer(points)
    active[:] = [points]
    with_vector = drawn()
    check('welcome by state: a vector layer added changes the requests to those about it',
          with_vector != with_raster and true_now() and any('active_vector' in catalog[key].needs for key in with_vector),
          str(with_vector))
    points.selectByIds([next(iter(points.allFeatureIds()))])
    selected = drawn()
    check('welcome by state: a selection brings a request about it',
          selected != with_vector and true_now() and any({'selection', 'local_selection'} & set(catalog[key].needs) for key in selected),
          str(selected))
    grab('welcome_vectors_selection')
    points.removeSelection()
    points.setSubsetString("name <> 'p0'")
    filtered = drawn()
    check('welcome by state: a filter brings a request about it',
          true_now() and any('filter' in catalog[key].needs for key in filtered), str(filtered))
    still = drawn()
    check('welcome by state: nothing is drawn again while the state stays', still == filtered)
    # A set that was seen is replaced only by a state that changed, and without what was seen.
    panel._examples_seen = True
    QSettings().setValue('filter_mate/agent/last_examples', ','.join(filtered))
    points.setSubsetString('')
    after = drawn()
    check('welcome by state: the set seen changes only where the state changed: the filter request goes, the others stay',
          after != filtered and true_now() and not any('filter' in catalog[key].needs for key in after)
          and sum(1 for key in after if key in filtered) >= 2, f'{filtered} -> {after}')
    # The link that reconfigures: there with a model, and the setup cards come in the thread.
    check('welcome by state: the link to reconfigure is under the requests with a model, the button of the setup hidden',
          panel.reconfigure_button.isVisible() and not panel.setup_button.isVisible()
          and panel.reconfigure_button.geometry().top() > max(b.geometry().bottom() for b in panel.example_buttons)
          and panel.reconfigure_button.geometry().bottom() <= panel.tour_button.geometry().top()
          and panel.reconfigure_button.width() <= panel.stack.width(),
          f'{panel.reconfigure_button.geometry()} {panel.tour_button.geometry()}')
    grab('welcome_model_connected')
    panel.reconfigure_button.click()
    QApplication.processEvents()
    check('welcome by state: the link starts the cards of the setup, no model asked',
          _wizard_card() is not None and chat._engine is None, panel.thread.toPlainText()[:80])
    chat.new_conversation()  # the cards are left unanswered: nothing is changed
    chat._wizard.forget()
    panel.set_ready(False)
    QApplication.processEvents()
    # Without a model the existing button is the only one: the link is not doubled.
    check('welcome by state: without a model the button of the setup stays and the link is hidden',
          not panel.setup_button.isHidden() and panel.reconfigure_button.isHidden(),
          f'{panel.setup_button.isHidden()} {panel.reconfigure_button.isHidden()}')
    panel.facts_provider = kept['provider']
    chat._refresh_ready()
    scratch.clear()
    shutil.rmtree(folder, ignore_errors=True)
    leave_welcome()
    return settled()


def _wire():
    """The state of the real wiring between steps: the controller, the layers it added, the project as found."""
    return WELCOME.setdefault('wire', {})


def _wire_facts():
    from qgis.core import QgsProject as Project
    chat = agent_chat()
    prompts = importlib.import_module(f'{PACKAGE}.core.agent.example_prompts')
    catalog = {example.key: example for example in prompts.CATALOG}
    facts = chat._read_welcome_facts()
    keys = chat.panel.example_keys
    true = bool(keys) and all(set(catalog[key].needs) <= facts.tokens() for key in keys)
    return facts, keys, catalog, true, Project.instance()


def s_welcome_wire_raster():
    """The real wiring (2026-11-22): a real project, real layers, the signals of QGIS and of its interface, with the
    controller of the dock and no reader replaced. A terrain model is added and made the active layer."""
    from qgis.core import QgsFeature, QgsGeometry, QgsPointXY
    from osgeo import gdal
    chat, wire = agent_chat(), _wire()
    panel = chat.panel
    chat.new_conversation()
    dock()._fm_sections.open_top('agent')
    wire['before'] = set(QgsProject.instance().mapLayers())
    wire['active'] = iface.activeLayer()
    # An empty set: what is drawn next is drawn because the wiring told the panel, not because it was already there.
    panel.example_keys, panel._examples_signature, panel._examples_seen = (), (), False
    wire['folder'] = tempfile.mkdtemp()
    path = os.path.join(wire['folder'], 'wire_dem.tif')
    dataset = gdal.GetDriverByName('GTiff').Create(path, 4, 4, 1, gdal.GDT_Float32)
    dataset.SetGeoTransform((650000, 10, 0, 6860000, 0, -10))
    dataset.GetRasterBand(1).Fill(100)
    dataset = None
    raster = QgsRasterLayer(path, 'wire_dem')
    points = QgsVectorLayer('Point?crs=EPSG:4326&field=name:string', 'wire_pts', 'memory')
    features = []
    for index in range(3):
        feature = QgsFeature(points.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(index, index)))
        feature.setAttributes([f'p{index}'])
        features.append(feature)
    points.dataProvider().addFeatures(features)
    QgsProject.instance().addMapLayers([raster, points])
    wire['raster'], wire['points'] = raster.id(), points.id()
    iface.setActiveLayer(raster)
    return waits(1.0, lambda: tasks_idle())


def s_welcome_wire_raster_check():
    facts, keys, catalog, true, _project = _wire_facts()
    check('welcome wiring: layers added and the active layer changed draw the requests, none false',
          bool(keys) and true and facts.active == 'raster' and facts.active_elevation,
          f'{keys} {facts}')
    check('welcome wiring: the active terrain model brings a request about it',
          any({'active_elevation', 'active_raster'} & set(catalog[key].needs) for key in keys), str(keys))
    points = QgsProject.instance().mapLayer(_wire()['points'])
    iface.setActiveLayer(points)  # the active layer changes alone
    return waits(0.9)


def s_welcome_wire_vector_check():
    facts, keys, catalog, true, project = _wire_facts()
    check('welcome wiring: another active layer (a signal of the interface) changes the requests to those about it',
          true and facts.active == 'vector' and any('active_vector' in catalog[key].needs for key in keys)
          and not any({'active_raster', 'active_elevation'} & set(catalog[key].needs) for key in keys), f'{keys} {facts}')
    points = project.mapLayer(_wire()['points'])
    points.selectByIds([next(iter(points.allFeatureIds()))])  # the selection of a real layer
    return waits(0.9)


def s_welcome_wire_selection_check():
    facts, keys, catalog, true, project = _wire_facts()
    check('welcome wiring: a selection (a signal of the layer) brings a request about it, none false',
          true and facts.selected >= 1 and any({'selection', 'local_selection'} & set(catalog[key].needs) for key in keys),
          f'{keys} {facts}')
    points = project.mapLayer(_wire()['points'])
    points.removeSelection()
    points.setSubsetString("name <> 'p0'")  # the filter of a real layer
    return waits(0.9)


def s_welcome_wire_filter_check():
    facts, keys, catalog, true, project = _wire_facts()
    check('welcome wiring: a filter (a signal of the layer) brings a request about it, none false',
          true and facts.filtered >= 1 and any('filter' in catalog[key].needs for key in keys), f'{keys} {facts}')
    wire = _wire()
    project.mapLayer(wire['points']).setSubsetString('')
    project.removeMapLayer(wire['raster'])
    project.removeMapLayer(wire['points'])
    if wire['active'] is not None and project.mapLayer(wire['active'].id()) is not None:
        iface.setActiveLayer(wire['active'])
    return waits(1.2, lambda: tasks_idle())


def s_welcome_wire_done():
    """The project as found; the set is true of it; the dock as it was."""
    facts, keys, catalog, true, project = _wire_facts()
    wire = _wire()
    check('welcome wiring: the layers removed, the project is as found and the requests are true of it',
          set(project.mapLayers()) == wire['before'] and true, f'{keys} {facts}')
    shutil.rmtree(wire.get('folder', ''), ignore_errors=True)
    WELCOME.pop('wire', None)
    leave_welcome()
    return settled()


WELCOME_STEPS = [s_tour, s_tour_links_check, s_tour_merged_check, s_setup_layout, s_setup_layout_check, s_setup_layout_back,
                 s_welcome_by_state, s_welcome_wire_raster, s_welcome_wire_raster_check, s_welcome_wire_vector_check,
                 s_welcome_wire_selection_check, s_welcome_wire_filter_check, s_welcome_wire_done]


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

    def acts(key, name):
        """The button ``name`` shows, enabled, once its section ``key`` is the open one of its panel."""
        if not SYNC['docked']:
            panels.raise_panel(key)
            QApplication.processEvents()
        return action_button(name).isVisible() and (SYNC['docked'] or action_button(name).isEnabled())

    check('sync: the bar moved, the buttons of FILTERING and EXPORTING stay in their panel, shown and enabled',
          filtering.isAncestorOf(action_button('filter')) and exporting.isAncestorOf(action_button('export'))
          and acts('exporting', 'export') and acts('filtering', 'filter'), str(actions_shown()))
    grab_window('sync_bar_moved')
    apply_settings({'APP.DOCKWIDGET.ACTION_BAR_POSITION': SYNC['position']})
    QApplication.processEvents()
    put_behind_layers('agent')  # AGENT as a tab of Layers, behind it: the tab in front hides its thread
    SYNC['agent_behind'] = SYNC['docked'] or (on_screen(agent_chat().panel) is False
                                              and not d._fm_sections.is_open('agent'))
    agent_chat()._show_agent()  # what a question of the agent, the setup and the tour do
    return waits(0.6)


def on_screen(widget):
    """Qt calls a panel behind a tab visible: only its visible region tells it is not in view."""
    return widget.isVisible() and not widget.visibleRegion().isEmpty()


def s_sync_agent_check():
    d = dock()
    check('sync: AGENT behind the tab of another panel is not counted as in view, and comes forward when its thread '
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
    # 2026-11-16: the lists keep the layers of the project that was closed (with every section in the dock too);
    # they are greyed out with the rest of the dock, and filled again by the next layers. Known, not a defect of
    # the panels: what is checked here is that nothing can be done with them meanwhile.
    stale = [text for text in combo_items() + exporting_items()]
    usable = d.checkableComboBoxLayer_exporting_layers.isEnabled() or d.checkableComboBoxLayer_filtering_layers_to_filter.isEnabled()
    check('sync: a project emptied leaves the panels in place, without an error, their lists out of reach',
          panels.detached() == sync_sections() and len(STATE['python_errors']) == SYNC['errors']
          and (not stale or not usable),
          f"apart={panels.detached()} stale={stale} usable={usable} errors={STATE['python_errors'][SYNC['errors']:]}")
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
    """AGENT in its own panel, behind the tab of another panel: Qt calls its page visible, nobody sees it."""
    leave_welcome()
    dock()._fm_panels.detach('agent')
    QApplication.processEvents()
    AUDIT['behind'] = put_behind_layers('agent')
    return waits(0.6)


def s_audit_tab_behind_check():
    d, chat = dock(), agent_chat()
    put_behind_layers('agent')
    page = chat.panel
    check('audit: AGENT behind the tab of another panel is not counted as open, though Qt calls its page visible',
          AUDIT['behind'] and page.isVisible() and not on_screen(page) and not d._fm_sections.is_open('agent'),
          f"visible={page.isVisible()} on screen={on_screen(page)} open={d._fm_sections.is_open('agent')}")
    QSettings().remove(chat.SETUP_OFFERED_KEY)
    AUDIT['offered'] = chat.offer_setup_once('audit-1.0')
    AUDIT['kept_behind'] = QSettings().value(chat.SETUP_OFFERED_KEY)
    d._fm_panels.raise_panel('agent')  # the user clicks its tab
    return waits(0.6)


def s_audit_offer_check():
    chat = agent_chat()
    kept = QSettings().value(chat.SETUP_OFFERED_KEY)
    check('audit: an offer of the setup behind a tab is kept as made only once its tab comes forward',
          AUDIT['offered'] is True and not AUDIT['kept_behind'] and kept == 'audit-1.0',
          f"offered={AUDIT['offered']} kept behind={AUDIT['kept_behind']!r} kept in front={kept!r}")
    put_behind_layers('agent')
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
    lower = panels.panel('filtering')
    check('audit: every section taken out, what was open stays in view: EXPLORING in the dock, FILTERING in the '
          'panel of the lower sections', on_screen(d.frame_exploring) and on_screen(d.FILTERING)
          and lower is not None and lower.current() == 'filtering' and lower is panels.panel('configuration')
          and not on_screen(d.CONFIGURATION) and lower not in window.tabifiedDockWidgets(d),
          f"exploring={on_screen(d.frame_exploring)} filtering={on_screen(d.FILTERING)} "
          f"configuration={on_screen(d.CONFIGURATION)} groups={panels.groups()}")
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


def icon_lightness(button):
    """How light the icon of ``button`` is drawn, 0 (black) to 255 (white); -1 without a pixel."""
    image = button.icon().pixmap(32, 32).toImage()
    values = [image.pixelColor(x, y).lightness() for x in range(image.width()) for y in range(image.height())
              if image.pixelColor(x, y).alpha() > 128]
    return sum(values) / len(values) if values else -1


def s_audit_theme():
    """The tools the kind of the layer adds to the rail of EXPLORING draw their own icons: a theme set while the
    panel is open reaches them too (they were drawn again only when the current layer changed)."""
    AUDIT['theme'] = config_value('APP.DOCKWIDGET.COLORS.ACTIVE_THEME')
    more = dock().findChild(QAbstractButton, 'pushButton_exploring_vector_more')
    AUDIT['light_before'] = icon_lightness(more) if more is not None else None
    apply_settings({'APP.DOCKWIDGET.COLORS.ACTIVE_THEME': 'dark'})
    return waits(0.8)


def s_audit_theme_check():
    d = dock()
    names = ('pushButton_exploring_vector_more', 'pushButton_checkable_exploring_vector_zone')
    drawn = {name: icon_lightness(d.findChild(QAbstractButton, name)) for name in names
             if d.findChild(QAbstractButton, name) is not None}
    check('audit: a dark theme set while the panel is open draws the tools of the rail light',
          len(drawn) == 2 and all(value > 140 for value in drawn.values()),
          f"before={AUDIT['light_before']} dark={drawn}")
    apply_settings({'APP.DOCKWIDGET.COLORS.ACTIVE_THEME': 'light'})
    return waits(0.8)


def s_audit_theme_back_check():
    d = dock()
    more = d.findChild(QAbstractButton, 'pushButton_exploring_vector_more')
    check('audit: and a light one draws them dark again', more is not None and 0 <= icon_lightness(more) < 110,
          str(icon_lightness(more) if more is not None else None))
    apply_settings({'APP.DOCKWIDGET.COLORS.ACTIVE_THEME': AUDIT['theme']})
    return waits(0.5)


def s_audit_empty_bar():
    """The buttons under their section and EXPORTING turned off: the bar for all stayed, empty, for the buttons
    that went with the section."""
    AUDIT['position'] = dock()._action_bar_manager.get_position()
    apply_settings({'APP.DOCKWIDGET.ACTION_BAR_POSITION': 'sections', 'APP.OPTIONS.EXPORTING.enabled': False})
    return waits(0.6)


def s_audit_empty_bar_check():
    d = dock()
    open_section(None)
    folded = d.frame_actions.isVisible()
    open_section(d.FILTERING)
    check('audit: the buttons under their section and EXPORTING turned off, no empty bar for all',
          not folded and not d.frame_actions.isVisible() and action_button('filter').isVisible(),
          f"nothing open={folded} filtering open={d.frame_actions.isVisible()} {actions_shown()}")
    apply_settings({'APP.DOCKWIDGET.ACTION_BAR_POSITION': AUDIT['position'], 'APP.OPTIONS.EXPORTING.enabled': True})
    return waits(0.6)


def s_audit_empty_bar_back_check():
    d = dock()
    open_section(d.FILTERING)
    check('audit: back to the bar for all with EXPORTING on, every button in it', d.frame_actions.isVisible()
          and action_button('export').isVisible() and action_button('filter').isVisible(), str(actions_shown()))
    return waits(0.2)


AUDIT_STEPS = [s_section_setup, s_vector_source, s_audit_empty_bar, s_audit_empty_bar_check,
               s_audit_empty_bar_back_check, s_audit_theme, s_audit_theme_check, s_audit_theme_back_check,
               s_audit_tab_behind, s_audit_tab_behind_check, s_audit_offer_check,
               s_audit_show_agent_check, s_audit_reopen_check, s_audit_stack_below_check, s_audit_merge_check,
               s_audit_buttons_check, s_audit_fronts_check]


# --- the headers stacked, a choice beside the rails (APP.DOCKWIDGET.SECTION_HEADERS, FM_ONLY=headers) -------------

HEADERS = {}


def top_headers():
    """The sections of the upper stack whose header shows, from the top."""
    sections = dock()._fm_sections
    shown = [(header.y(), key) for key, header in sections._headers.items() if header.isVisible()]
    return [key for _y, key in sorted(shown)]


def toolbox_header(page):
    toolbox = dock().toolBox_tabTools
    text = toolbox.itemText(toolbox.indexOf(page))
    return next((button for button in toolbox.findChildren(QAbstractButton)
                 if button.objectName() == 'qt_toolbox_toolboxbutton' and button.text() == text), None)


def toolbox_headers():
    """The sections of the lower stack whose header shows, from the top."""
    d = dock()
    shown = [(toolbox_header(getattr(d, name)).y(), name.lower()) for name in ('FILTERING', 'EXPORTING', 'CONFIGURATION')
             if toolbox_header(getattr(d, name)) is not None and toolbox_header(getattr(d, name)).isVisible()]
    return [key for _y, key in sorted(shown)]


def expected_top():
    return ['agent', 'exploring'] if 'agent' in dock()._fm_sections._headers else ['exploring']


def s_headers_stacked():
    """APP.DOCKWIDGET.SECTION_HEADERS = stacked: the headers one above the other list the sections, no rail."""
    leave_welcome()
    sections = dock()._fm_sections
    HEADERS['rails'] = (not sections.stacked and sections.top_rail.isVisible() and sections.bottom_rail.isVisible()
                        and top_headers() == [] and toolbox_headers() == [])
    HEADERS['value'] = config_value('APP.DOCKWIDGET.SECTION_HEADERS')
    apply_settings({'APP.DOCKWIDGET.SECTION_HEADERS': 'stacked'})
    return waits(0.6)


def s_headers_stacked_check():
    d = dock()
    sections, toolbox = d._fm_sections, d.toolBox_tabTools
    check('headers: the rails are the default, with no header', HEADERS['rails'] and HEADERS['value'] == 'rail',
          f"rails={HEADERS['rails']} value={HEADERS['value']!r}")
    check('headers: stacked, a header per section and no rail', sections.stacked
          and not sections.top_rail.isVisible() and not sections.bottom_rail.isVisible()
          and top_headers() == expected_top() and toolbox_headers() == ['filtering', 'exporting', 'configuration'],
          f"top={top_headers()} bottom={toolbox_headers()}")
    check('headers: what was open stays open, its header checked', sections.is_open('exploring')
          and sections._headers['exploring'].isChecked() and toolbox.currentWidget() is d.FILTERING
          and d.comboBox_filtering_current_layer.isVisible())
    layout = sections._top_layout
    order = [layout.indexOf(sections._headers[key]) for key in expected_top()] + [layout.indexOf(d.frame_exploring)]
    heights = {sections._headers[key].height() for key in expected_top()} | {
        toolbox_header(page).height() for page in (d.FILTERING, d.EXPORTING, d.CONFIGURATION)}
    check('headers: each header above its page, all of one height, within the dock', order == sorted(order)
          and min(order) >= 0 and len(heights) == 1
          and all(sections._headers[key].width() <= d.width() for key in expected_top()),
          f"order={order} heights={heights}")
    if 'agent' in sections._headers:
        # 2026-11-17, review: the label that says where the requests go stayed in the rail, hidden with it.
        label = sections._agent_trailer
        label.setText('Ollama · qwen3 · MCP')
        QApplication.processEvents()
        check('headers: where the requests of AGENT go is said at the right of its header',
              label.parentWidget() is sections._headers['agent'] and label.isVisible()
              and label.geometry().right() <= sections._headers['agent'].width(), str(label.geometry()))
    grab('headers_stacked')
    grab_window('headers_stacked_window')
    if 'agent' in sections._headers:
        sections._headers['agent'].click()
        QApplication.processEvents()
        check('headers: a click on the header of AGENT opens it, EXPLORING and FILTERING fold',
              sections.is_open('agent') and not sections.is_open('exploring') and sections._headers['agent'].isChecked()
              and not sections._headers['exploring'].isChecked() and toolbox.currentWidget() is not d.FILTERING
              and top_headers() == expected_top(), f"top={top_headers()}")
        grab('headers_agent_open')
        sections._headers['agent'].click()
        QApplication.processEvents()
        check('headers: a click on the open one leaves it open', sections.is_open('agent')
              and sections._headers['agent'].isChecked())
        sections._headers['exploring'].click()
        QApplication.processEvents()
        check('headers: a click on the header of EXPLORING brings it back', sections.is_open('exploring')
              and not sections.is_open('agent') and sections._headers['exploring'].isChecked())
    toolbox_header(d.EXPORTING).click()
    QApplication.processEvents()
    opened = toolbox.currentWidget() is d.EXPORTING
    toolbox_header(d.EXPORTING).click()
    QApplication.processEvents()
    check('headers: a click on a header below opens its section, a second one folds the stack', opened
          and toolbox.currentWidget() is sections._nothing and toolbox_headers() == ['filtering', 'exporting', 'configuration'],
          f"opened={opened} current={toolbox.currentWidget().objectName()}")
    stack = d.splitter_main.widget(1)
    headers = sorted((toolbox_header(page) for page in (d.FILTERING, d.EXPORTING, d.CONFIGURATION)), key=lambda b: b.y())
    last = headers[-1].mapTo(stack, QPoint(0, headers[-1].height())).y()
    gaps = {after.y() - (before.y() + before.height()) for before, after in zip(headers, headers[1:])}
    check('headers: with nothing open below, the three headers are whole, evenly apart, and the stack is held to them',
          last <= stack.height() and len(gaps) == 1 and stack.height() <= last + 24,
          f"last={last} stack={stack.height()} gaps={gaps}")
    grab('headers_nothing_open')
    header = toolbox_header(d.FILTERING)
    header.customContextMenuRequested.emit(QPoint(8, 8))
    QApplication.processEvents()
    menus = [menu for menu in d.findChildren(QMenu) if menu.isVisible()]
    names = [action.objectName() for menu in menus for action in menu.actions() if not action.isSeparator()]
    check('headers: a right click on a header opens the menu of its section',
          names == ['action_section_detach', 'action_section_detach_all'], str(names))
    for menu in menus:
        menu.hide()
    toolbox.setCurrentWidget(d.FILTERING)
    QApplication.processEvents()
    apply_settings({'APP.OPTIONS.FILTERING.enabled': False})
    return waits(0.5)


def s_headers_off_check():
    d = dock()
    sections, panels = d._fm_sections, d._fm_panels
    check('headers: a section turned off loses its header', toolbox_headers() == ['exporting', 'configuration']
          and d.frame_exploring.isAncestorOf(d.comboBox_filtering_current_layer), str(toolbox_headers()))
    apply_settings({'APP.OPTIONS.FILTERING.enabled': True})
    QApplication.processEvents()
    check('headers: turned on again, its header is back and it opens as it was',
          toolbox_headers() == ['filtering', 'exporting', 'configuration']
          and d.toolBox_tabTools.currentWidget() is d.FILTERING, str(toolbox_headers()))
    apart = panels.detach('exporting') and (panels.detach('agent') if 'agent' in sections._headers else True)
    QApplication.processEvents()
    check('headers: a section in its own panel loses its header in the dock', apart
          and toolbox_headers() == ['filtering', 'configuration'] and top_headers() == ['exploring'],
          f"top={top_headers()} bottom={toolbox_headers()}")
    grab_window('headers_sections_apart')
    panels.attach_all()
    QApplication.processEvents()
    layout = sections._top_layout
    order = [layout.indexOf(widget) for key in expected_top()
             for widget in (sections._headers[key], sections._pages[key])]
    check('headers: merged back, each header is there again above its page, AGENT folded',
          toolbox_headers() == ['filtering', 'exporting', 'configuration'] and top_headers() == expected_top()
          and order == sorted(order) and min(order) >= 0 and sections.is_open('exploring'),
          f"top={top_headers()} order={order}")
    apply_settings({'APP.DOCKWIDGET.SECTION_HEADERS': 'rail'})
    return waits(0.6)


def s_headers_rail_check():
    d = dock()
    sections = d._fm_sections
    check('headers: back to the rails, no header left and the sections as they were', not sections.stacked
          and sections.top_rail.isVisible() and sections.bottom_rail.isVisible() and top_headers() == []
          and toolbox_headers() == [] and sections.is_open('exploring')
          and sections.bottom_rail.shown_sections() == ['filtering', 'exporting', 'configuration']
          and d.toolBox_tabTools.currentWidget() is d.FILTERING,
          f"top={top_headers()} bottom={toolbox_headers()} rail={sections.bottom_rail.shown_sections()}")
    if 'agent' in sections._headers:
        label = sections._agent_trailer
        check('headers: with the rails, where the requests go is said at the right of the top rail again',
              label.parentWidget() is sections.top_rail and label.isVisible())
        label.setText('')
    open_section(None)
    stack = d.splitter_main.widget(1)
    check('headers: with the rails and nothing open below, the lower stack is its rail again',
          not d.toolBox_tabTools.isVisible() and stack.height() <= sections.bottom_rail.height() + 24,
          f"stack={stack.height()} rail={sections.bottom_rail.height()}")
    apply_settings({'APP.DOCKWIDGET.SECTION_HEADERS': HEADERS['value']})
    leave_welcome()
    return settled()


def s_headers_startup_check():
    """The dock opened with the headers stacked saved (FM_HEADERS=stacked): they are there without a click, the one
    of AGENT too, which joins the dock after the others."""
    d = dock()
    sections = d._fm_sections
    check('headers at startup: the dock opens with its headers stacked, AGENT above EXPLORING', sections.stacked
          and not sections.top_rail.isVisible() and not sections.bottom_rail.isVisible()
          and top_headers() == expected_top() and toolbox_headers() == ['filtering', 'exporting', 'configuration']
          and sections.is_open('exploring'), f"top={top_headers()} bottom={toolbox_headers()}")
    grab('headers_startup')
    return None


HEADER_STEPS = [s_section_setup, s_headers_stacked, s_headers_stacked_check, s_headers_off_check, s_headers_rail_check]


# --- EXPLORING in its own panel, with a chooser of the current layer of its own (FM_ONLY=exploring) ----------------

EXPLO = {}


def explo_mirror():
    return dock().frame_exploring.findChild(QComboBox, 'comboBox_exploring_current_layer')


def s_explo_detach():
    """EXPLORING leaves the dock by its own menu entry: a panel of QGIS above the dock."""
    d = dock()
    leave_welcome()
    panels = d._fm_panels
    EXPLO['errors'] = len(STATE['python_errors'])
    EXPLO['minimum'] = d.minimumHeight()
    mirror = explo_mirror()
    check('explo: in the dock EXPLORING has no chooser of the current layer of its own',
          mirror is None or mirror.isHidden())
    names = menu_names(panels.build_menu('exploring', d))
    check('explo: the menu of EXPLORING offers its own panel, and every section out',
          names == ['action_section_detach', 'action_section_detach_all'], str(names))
    grab_window('explo_0_dock')
    window = iface.mainWindow()
    probe = QDockWidget('probe', window)  # a panel of QGIS under the dock, in its area
    probe.setObjectName('fm_bench_probe')
    probe.setWidget(QLabel('probe'))
    window.addDockWidget(window.dockWidgetArea(d), probe)
    QApplication.processEvents()
    EXPLO['probe'] = probe
    EXPLO['detached'] = panels.detach('exploring')
    return waits(0.8)


def s_explo_check():
    d = dock()
    panels, sections = d._fm_panels, d._fm_sections
    panel = panels.panel('exploring')
    combo, mirror = d.comboBox_filtering_current_layer, explo_mirror()
    if not check('explo: EXPLORING is in its own panel, its widgets with it, and kept as apart',
                 EXPLO['detached'] and panel is not None and panel.isAncestorOf(d.frame_exploring)
                 and d.frame_exploring.isVisible() and panels.groups() == (('exploring',),)
                 and QSettings().value(DETACHED_KEY) == 'exploring',
                 f"detached={EXPLO['detached']} groups={panels.groups()} saved={QSettings().value(DETACHED_KEY)}"):
        return None
    check('explo: its panel is above the dock, in its column', panel_place(panel) == 'above'
          and abs(panel.mapToGlobal(QPoint(0, 0)).x() - d.mapToGlobal(QPoint(0, 0)).x()) <= 4
          and panel.height() >= 180 and d.height() >= 180,
          f"place={panel_place(panel)} panel={panel.height()} dock={d.height()}")
    probe = EXPLO.pop('probe')
    tops = [widget.mapToGlobal(QPoint(0, 0)).y() for widget in (panel, d, probe)]
    # 2026-11-17, review: the dock went down to the end of its area with the panel, below the panels of QGIS.
    check('explo: the dock keeps its place above the panel of QGIS that was under it',
          tops == sorted(tops) and len(set(tops)) == 3 and not probe.isFloating(), f"panel, dock, probe at {tops}")
    iface.mainWindow().removeDockWidget(probe)
    probe.setParent(None)
    probe.deleteLater()
    QApplication.processEvents()
    check('explo: away from FILTERING, EXPLORING shows a chooser of the current layer that says the same',
          mirror is not None and mirror.isVisible() and panel.isAncestorOf(mirror) and d.FILTERING.isAncestorOf(combo)
          and mirror.currentIndex() == combo.currentIndex() and mirror.currentText().startswith(combo.currentText())
          and mirror.count() == combo.count() and combo.currentLayer().id() == layer('zones').id()
          and bool(mirror.property('fm_wheel_guarded')),  # the wheel changes the layer only once it has the focus
          f"mirror={mirror.currentText() if mirror is not None else None} combo={combo.currentText()}")
    check('explo: the dock keeps FILTERING open with its buttons, and asks less height than with EXPLORING in it',
          d.toolBox_tabTools.currentWidget() is d.FILTERING and action_button('filter').isVisible()
          and action_button('filter').isEnabled() and d.minimumHeight() < EXPLO['minimum'],
          f"{actions_shown()} minimum={d.minimumHeight()} (was {EXPLO['minimum']})")
    has_agent = 'agent' in sections._headers
    check('explo: the rail above lists what is left there, folded',
          sections.top_rail.shown_sections() == (['agent'] if has_agent else [])
          and sections.top.isVisible() == has_agent and not sections._open_in_stack('agent'),
          f"rail={sections.top_rail.shown_sections()} top={sections.top.isVisible()}")
    grab_window('explo_1_apart')
    index = next(row for row in range(combo.count()) if combo.layer(row).id() == layer('dem').id())
    mirror.setCurrentIndex(index)  # as a choice in its list
    mirror.activated.emit(index)
    return switched_to('dem', coverage_page=True)


def s_explo_layer_check():
    """A layer chosen in the chooser of EXPLORING is the current layer everywhere; one chosen in FILTERING shows
    in it."""
    d = dock()
    panel = d._fm_panels.panel('exploring')
    combo, mirror = d.comboBox_filtering_current_layer, explo_mirror()
    check('explo: a layer chosen in EXPLORING is the current layer of FILTERING, and its page shows in the panel',
          combo.currentLayer() is not None and combo.currentLayer().id() == layer('dem').id()
          and mirror.currentIndex() == combo.currentIndex() and coverage()._raster_panel.isVisible()
          and panel.isAncestorOf(coverage()._raster_panel), f"combo={combo.currentText()} mirror={mirror.currentText()}")
    grab_window('explo_2_raster')
    combo.setLayer(layer('zones'))
    return switched_to('zones', coverage_page=False)


def s_explo_select():
    d = dock()
    combo, mirror = d.comboBox_filtering_current_layer, explo_mirror()
    QApplication.processEvents()
    check('explo: a layer chosen in FILTERING shows in the chooser of EXPLORING',
          mirror.currentIndex() == combo.currentIndex() and mirror.currentText().startswith('zones')
          and combo.currentLayer().id() == layer('zones').id(), f"mirror={mirror.currentText()} combo={combo.currentText()}")
    d.mGroupBox_exploring_single_selection.setChecked(True)
    east_a = next(feature for feature in layer('zones').getFeatures() if feature['name'] == 'east_a')
    d.mFeaturePickerWidget_exploring_single_selection.setFeature(east_a.id())
    set_targets(['dem'])
    set_predicates(['Intersect'])
    ready = targets_ready(['dem'])
    return lambda: bool(dock().get_current_features()[0]) and ready()


def s_explo_filter():
    action_button('filter').click()
    return lambda: layer('dem').source().endswith('.vrt') and tasks_idle()


def s_explo_filter_check():
    d = dock()
    panels, sections = d._fm_panels, d._fm_sections
    toolbox = d.toolBox_tabTools
    check('explo: a feature picked in the panel of EXPLORING filters from the dock',
          layer('dem').source().endswith('.vrt'), layer('dem').source())
    grab_window('explo_3_filtered')
    if 'agent' in sections._headers:
        chip = sections.top_rail.chip('agent')
        chip.click()
        QApplication.processEvents()
        check('explo: AGENT opens in the dock beside FILTERING, EXPLORING stays in view, Undo walks the filters',
              sections.is_open('agent') and sections.is_open('exploring') and toolbox.currentWidget() is d.FILTERING
              and not d.agent_has_focus() and action_button('undo_filter').isVisible(),
              f"agent={sections.is_open('agent')} below={toolbox.currentWidget().objectName()} {actions_shown()}")
        grab_window('explo_4_agent_open')
        open_section(d.EXPORTING)
        open_section(d.FILTERING)
        check('explo: FILTERING opened again below leaves AGENT open and the panel of EXPLORING where it is',
              sections.is_open('agent') and toolbox.currentWidget() is d.FILTERING
              and panel_place(panels.panel('exploring')) == 'above', panel_place(panels.panel('exploring')))
        open_section(None)
        check('explo: with FILTERING folded under the open AGENT, Undo and Redo walk the steps of the agent',
              sections.is_open('agent') and d.agent_has_focus())
        open_section(d.FILTERING)
        # 2026-11-17, review: back in the dock, EXPLORING stayed folded under AGENT with FILTERING open.
        panels.attach('exploring')
        QApplication.processEvents()
        check('explo: back in the dock under AGENT and FILTERING open together, EXPLORING opens and folds AGENT',
              sections.is_open('exploring') and not sections.is_open('agent') and toolbox.currentWidget() is d.FILTERING
              and d.isAncestorOf(d.frame_exploring) and not d.agent_has_focus(),
              f"exploring={sections.is_open('exploring')} agent={sections.is_open('agent')}")
        panels.detach('exploring')
        QApplication.processEvents()
        chip.click()
        QApplication.processEvents()
        check('explo: taken out again, EXPLORING is back above the dock and AGENT opens beside FILTERING',
              panel_place(panels.panel('exploring')) == 'above' and sections.is_open('agent')
              and toolbox.currentWidget() is d.FILTERING, panel_place(panels.panel('exploring')))
        chip.click()
        QApplication.processEvents()
        check('explo: a click on the chip of the open AGENT folds it: nothing has to stay open above',
              not sections.is_open('agent') and chip.isVisible() and sections.top_rail.current() is None
              and sections.top.height() <= sections.top_rail.height() + 4,
              f"agent={sections.is_open('agent')} top={sections.top.height()} rail={sections.top_rail.height()}")
    action_button('undo_filter').click()
    return lambda: not layer('dem').source().endswith('.vrt') and tasks_idle()


def s_explo_all():
    """With EXPLORING apart, "every section out" leaves the last section in the dock."""
    d = dock()
    panels = d._fm_panels
    check('explo: Undo from the dock puts the raster target back',
          os.path.normpath(layer('dem').source()) == os.path.normpath(M['dem']), layer('dem').source())
    left = panels.detach_all()
    QApplication.processEvents()
    names = menu_names(panels.build_menu('configuration', d))
    check('explo: with EXPLORING apart, every section out leaves the last one in the dock',
          panels.in_dock() == ('configuration',) and 'configuration' not in left
          and not panels.can_detach('configuration') and not panels.detach('configuration') and d.isVisible()
          and d.isAncestorOf(d.CONFIGURATION) and names == ['action_section_attach_all'],
          f"left={left} in dock={panels.in_dock()} menu={names}")
    chip = d._fm_sections.bottom_rail.chip('configuration')
    chip.click()
    QApplication.processEvents()
    check('explo: the only section left in the dock is open, and a click on its chip leaves it open',
          d.toolBox_tabTools.currentWidget() is d.CONFIGURATION and d.CONFIGURATION.isVisible(),
          d.toolBox_tabTools.currentWidget().objectName())
    grab_window('explo_5_every_section_out')
    return settled()  # the 2 s after Undo, when the dock puts the source layer back


def s_explo_restart():
    """As after a restart of QGIS: EXPLORING is in its panel again, above the dock, with its chooser."""
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    module = importlib.import_module(f'{PACKAGE}.ui.layout.section_panels')
    area = window.dockWidgetArea(d)
    panels.attach_all()
    QApplication.processEvents()
    panels.detach('exploring')
    QApplication.processEvents()
    place = panel_place(panels.panel('exploring'))
    state = window.saveState()  # QGIS saves its window when it closes
    panels.attach_all(remember=False)  # the plugin unloads: its panels go, what was apart stays saved
    mirror = explo_mirror()
    merged = d.isAncestorOf(d.frame_exploring) and mirror.isHidden()
    iface.removeDockWidget(d)
    QApplication.processEvents()
    window.restoreState(state)  # QGIS starts: it knows neither the dock nor its panel yet
    QSettings().setValue(module.DOCK_AREA_KEY, module._area_number(area))
    restored = module.place_dock(d, iface, area)  # the plugin opens its dock
    d.show()
    again = panels.restore()  # and the panels of the last time
    QApplication.processEvents()
    panel = panels.panel('exploring')
    check('explo: after a restart EXPLORING is in its panel again, above the dock, with its chooser',
          merged and restored and again == ['exploring'] and panel is not None and place == 'above'
          and panel_place(panel) == place and panel.isAncestorOf(mirror) and mirror.isVisible(),
          f"merged={merged} restored={restored} again={again} place before={place} after={panel_place(panel)}")
    grab_window('explo_6_restarted')
    return waits(0.4)


def s_explo_off():
    """The last section of the dock cannot leave it; turned off, it gives the dock to EXPLORING, which comes back."""
    d = dock()
    panels, sections = d._fm_panels, d._fm_sections
    combo, mirror = d.comboBox_filtering_current_layer, explo_mirror()
    options = d.CONFIG_DATA['APP']['OPTIONS']
    before = options.get('FILTERING')
    for key in ('agent', 'exporting', 'configuration'):
        panels.detach(key)  # AGENT may not be installed
    QApplication.processEvents()
    check('explo: FILTERING, the last section of the dock, cannot leave it',
          panels.in_dock() == ('filtering',) and not panels.can_detach('filtering') and not panels.detach('filtering')
          and not sections.top.isVisible() and d.isVisible() and d.toolBox_tabTools.currentWidget() is d.FILTERING,
          f"in dock={panels.in_dock()} top={sections.top.isVisible()}")
    grab_window('explo_7_filtering_alone')
    options['FILTERING'] = {'enabled': {'value': False}}
    changed = d.apply_section_options()
    QApplication.processEvents()
    check('explo: the last section of the dock turned off, EXPLORING comes back to it with the chooser of FILTERING',
          changed == ['filtering'] and panels.in_dock() == ('exploring',) and d.isAncestorOf(d.frame_exploring)
          and sections.is_open('exploring') and d.isVisible() and mirror.isHidden()
          and d.frame_exploring.isAncestorOf(combo) and combo.isVisible(),
          f"changed={changed} in dock={panels.in_dock()} mirror hidden={mirror.isHidden()}")
    if before is None:
        options.pop('FILTERING', None)
    else:
        options['FILTERING'] = before
    d.apply_section_options()
    QApplication.processEvents()
    panels.attach_all()
    QApplication.processEvents()
    sections.open_top('exploring')
    open_section(d.FILTERING)
    check('explo: merged back, EXPLORING is in the dock without its chooser, FILTERING holds its own',
          panels.detached() == () and not QSettings().value(DETACHED_KEY) and d.isAncestorOf(d.frame_exploring)
          and sections.is_open('exploring') and d.FILTERING.isAncestorOf(combo) and mirror.isHidden()
          and d.toolBox_tabTools.currentWidget() is d.FILTERING and len(STATE['python_errors']) == EXPLO['errors'],
          f"apart={panels.detached()} saved={QSettings().value(DETACHED_KEY)!r} "
          f"errors={STATE['python_errors'][EXPLO['errors']:]}")
    # The minimum of its profile, kept since the profile was applied: not the one it had when the steps began,
    # which Qt may have raised since to what the contents needed then (399 for 357 after the steps before these).
    check('explo: merged back, the dock has the minimum height of its profile again',
          not panels._dock_relaxed and panels._dock_minimum is not None and panels._dock_minimum > 0
          and d.minimumHeight() >= panels._dock_minimum,
          f"minimum={d.minimumHeight()} profile={panels._dock_minimum} at the start={EXPLO['minimum']}")
    grab_window('explo_8_merged_back')
    return waits(0.3)


def pick_in_chooser(chooser, layer_name):
    """Choose ``layer_name`` in the list of a chooser of the current layer as a user does: open its list, click the
    row. True when the list took the click; otherwise the choice is made as the list makes it (``activated``)."""
    from qgis.PyQt.QtTest import QTest
    source = dock().comboBox_filtering_current_layer
    row = next(r for r in range(source.count()) if source.layer(r) is not None and source.layer(r).name() == layer_name)
    before = chooser.currentIndex()
    chooser.showPopup()
    QApplication.processEvents()
    view = chooser.view()
    QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                     view.visualRect(view.model().index(row, 0)).center())
    QApplication.processEvents()
    if chooser.currentIndex() == row or chooser.currentIndex() != before:
        return True
    chooser.hidePopup()
    chooser.setCurrentIndex(row)
    chooser.activated.emit(row)
    return False


def explo_pick_check(title, detail=''):
    """``zones_b`` is the current layer everywhere after it was chosen in the chooser of EXPLORING. When the click on
    its list did not take (the choice was made as the list makes it), the check is skipped, said so: it would not
    be the gesture of a user."""
    d = dock()
    combo, mirror = d.comboBox_filtering_current_layer, explo_mirror()
    shown = (f"panel={d.current_layer.name() if d.current_layer is not None else None} combo={combo.currentText()} "
             f"chooser={mirror.currentText()} {detail}").strip()
    if not EXPLO.get('pick_by_list'):
        report('SKIP', title, f"the click on the list of the chooser did not take, no real click: {shown}")
        return
    check(title, d.current_layer is not None and d.current_layer.name() == 'zones_b'
          and combo.currentLayer() is not None and combo.currentLayer().name() == 'zones_b'
          and mirror.currentText().startswith('zones_b'), shown)


def drop_task_hook():
    """The hook of ``s_explo_pick_during_filter`` on the task manager, off whether a task came or not."""
    hook = EXPLO.pop('task_hook', None)
    if hook is not None:
        try:
            QgsApplication.taskManager().taskAdded.disconnect(hook)
        except (TypeError, RuntimeError):  # it disconnected itself on the task
            pass


def s_explo_pick_setup():
    """A second vector layer to choose, and the post-undo window of the step before over."""
    if layer('zones_b') is None:
        project.addMapLayer(QgsVectorLayer(M['zones'] + '|layername=zones', 'zones_b', 'ogr'))
    since = time.time()
    return lambda: registered('zones', 'zones_b') and tasks_idle() and time.time() - since > 2.5


def s_explo_pick_ready():
    """What a filter needs, as a user leaves it (a layer added or chosen again resets the targets): a feature of
    zones picked, dem as the target."""
    d = dock()
    d.comboBox_filtering_current_layer.setLayer(layer('zones'))
    east_a = next(feature for feature in layer('zones').getFeatures() if feature['name'] == 'east_a')
    d.mFeaturePickerWidget_exploring_single_selection.setFeature(east_a.id())
    set_targets(['dem'])
    set_predicates(['Intersect'])
    ready = targets_ready(['dem'])
    since = time.time()
    return lambda: bool(dock().get_current_features()[0]) and ready() and time.time() - since > 2.0


def s_explo_pick_during_filter():
    """2026-11-18, audit: a layer chosen in the chooser of EXPLORING while the filter runs is the user's choice."""
    d = dock()
    d.comboBox_filtering_current_layer.setLayer(layer('zones'))
    QApplication.processEvents()
    EXPLO['pick_before'] = d.current_layer.name() if d.current_layer is not None else None
    EXPLO['pick_state'] = None
    EXPLO['pick_by_list'] = False
    manager = QgsApplication.taskManager()

    def on_task(_task_id):  # the task is added: the dock has blocked the chooser of FILTERING by now
        manager.taskAdded.disconnect(on_task)
        combo = d.comboBox_filtering_current_layer
        EXPLO['pick_state'] = (combo.signalsBlocked(), bool(getattr(d, '_filtering_in_progress', False)))
        EXPLO['pick_by_list'] = pick_in_chooser(explo_mirror(), 'zones_b')

    EXPLO['task_hook'] = on_task
    manager.taskAdded.connect(on_task)
    action_button('filter').click()
    return settled()


def s_explo_pick_during_filter_check():
    drop_task_hook()  # no task came: it must not choose in a later step
    d = dock()
    combo = d.comboBox_filtering_current_layer
    check('explo: the choice in the chooser of EXPLORING came while the filter ran (chooser of FILTERING blocked, '
          'filter in progress)', EXPLO['pick_state'] == (True, True),
          f"(combo blocked, filtering) at the pick={EXPLO['pick_state']}")
    explo_pick_check('explo: a layer chosen in the chooser of EXPLORING while the filter runs stays the current '
                     'layer', f"before={EXPLO['pick_before']} at the pick={EXPLO['pick_state']}")
    combo.setLayer(layer('zones'))
    return switched_to('zones', coverage_page=False)


def s_explo_pick_in_window():
    """The same, in the second and a half that follows a filter that is over."""
    d = dock()
    EXPLO['pick_before'] = d.current_layer.name() if d.current_layer is not None else None
    action_button('filter').click()
    return lambda: callable(getattr(d, '_end_post_filter_window', None)) and tasks_idle()


def s_explo_pick_in_window_pick():
    EXPLO['pick_by_list'] = pick_in_chooser(explo_mirror(), 'zones_b')
    return settled()


def s_explo_pick_in_window_check():
    explo_pick_check('explo: a layer chosen in the chooser of EXPLORING right after a filter stays the current layer',
                     f"before={EXPLO['pick_before']}")
    combo = dock().comboBox_filtering_current_layer
    combo.setLayer(layer('zones'))
    return switched_to('zones', coverage_page=False)


def s_explo_pick_after_undo():
    """The same after Undo: the window that follows it put the source layer back over the choice."""
    action_button('undo_filter').click()
    EXPLO['pick_by_list'] = pick_in_chooser(explo_mirror(), 'zones_b')  # its window of checks is open for 2 s
    return settled()


def s_explo_pick_after_undo_check():
    explo_pick_check('explo: a layer chosen in the chooser of EXPLORING right after Undo stays the current layer')
    combo = dock().comboBox_filtering_current_layer
    combo.setLayer(layer('zones'))
    project.removeMapLayer(layer('zones_b').id())
    return switched_to('zones', coverage_page=False)


def s_explo_pick_undo_rest():
    """The two filters of the steps above are undone: the next steps find the raster target as it was."""
    action_button('undo_filter').click()
    return lambda: not layer('dem').source().endswith('.vrt') and tasks_idle()


EXPLO_STEPS = [s_section_setup, s_vector_source, s_explo_detach, s_explo_check, s_explo_layer_check, s_explo_select,
               s_explo_filter, s_explo_filter_check, s_explo_pick_setup, s_explo_pick_ready, s_explo_pick_during_filter,
               s_explo_pick_during_filter_check, s_explo_pick_ready, s_explo_pick_in_window, s_explo_pick_in_window_pick,
               s_explo_pick_in_window_check, s_explo_pick_ready, s_explo_pick_after_undo,
               s_explo_pick_after_undo_check, s_explo_pick_undo_rest, s_explo_all,
               s_explo_restart, s_explo_off]


# --- the drags with a real pointer (FM_ONLY=mouse) ---------------------------------------------------------------
#
# The steps above call what Qt calls (the drop of a rail, the filter of a drag): a drag started by the mouse blocks
# the handler that started it, so no step can start one and go on. Here a pointer is moved from another process
# (tests/qgis_headless/x_mouse.py, the XTest extension of the X server): QGIS gets what a real mouse sends, and
# QDrag.exec and the drag of a dock by its title run for real. X11 only: not what Windows does with a drag.

MOUSE = {}


def mouse(*actions):
    """The pointer does ``actions`` (x_mouse.py) beside QGIS; ``mouse_over`` tells when it is done."""
    script = os.path.join(REPO, 'tests', 'qgis_headless', 'x_mouse.py')
    MOUSE['process'] = subprocess.Popen(['python3', script, *[str(action) for action in actions]])
    return mouse_over


def mouse_over():
    """The pointer is done, and no drag is left running: the next step must not start inside one."""
    process = MOUSE.get('process')
    rails = getattr(dock(), '_fm_rails', None) or []
    return ((process is None or process.poll() is not None)
            and not any(getattr(rail, '_dragging', False) for rail in rails))


def at(widget, x=None, y=None):
    """The place of the screen of a point of ``widget`` (its centre by default)."""
    centre = widget.rect().center()
    point = widget.mapToGlobal(QPoint(centre.x() if x is None else x, centre.y() if y is None else y))
    return point.x(), point.y()


def drag(start, end, hold=0.3, before_release=()):
    """Press at ``start``, go to ``end`` step by step, wait, release."""
    return ['move', start[0], start[1], 'sleep', 0.2, 'down', 1, 'sleep', 0.15, 'drag', start[0] + 16, start[1],
            'drag', end[0], end[1], 'sleep', hold, *before_release, 'up', 1, 'sleep', 0.3, 'move', 5, 5, 'sleep', 0.2]


def mouse_works():
    if not MOUSE.get('works'):
        report('SKIP', f"mouse: {sys._getframe(1).f_code.co_name}", 'no pointer could be moved on this display')
    return bool(MOUSE.get('works'))


def s_mouse_setup():
    d = dock()
    leave_welcome()
    for key in ('FilterMate/sections/top_order', 'FilterMate/sections/bottom_order'):
        QSettings().remove(key)
    MOUSE['works'] = False
    MOUSE['order'] = d._fm_sections.bottom_rail.sections()
    MOUSE['ends'] = []  # how each drag of a chip of the dock ended: (section, dropped on a widget of QGIS)
    for rail in (d._fm_sections.top_rail, d._fm_sections.bottom_rail):
        def finish(key, place, end=type(rail).finish_drag, rail=rail):
            MOUSE['ends'].append((key, place is not None))
            end(rail, key, place)
        rail.finish_drag = finish
    return mouse('move', 640, 480, 'sleep', 0.2)


def s_mouse_reorder():
    """A chip dragged along its rail with the mouse: the sections are in another order."""
    from qgis.PyQt.QtGui import QCursor
    d = dock()
    bottom = d._fm_sections.bottom_rail
    MOUSE['works'] = QCursor.pos() == QPoint(640, 480) and not d._fm_sections.stacked
    if not mouse_works():
        return None
    first, last = bottom.chip(MOUSE['order'][0]), bottom.chip(MOUSE['order'][-1])
    return mouse(*drag(at(last), at(first, x=2)))


def s_mouse_reorder_check():
    if not mouse_works():
        return None
    d = dock()
    bottom = d._fm_sections.bottom_rail
    order = MOUSE['order']
    check('mouse: a chip dragged along its rail goes where it is dropped, and the order is kept',
          bottom.sections() == [order[-1]] + order[:-1]
          and QSettings().value('FilterMate/sections/bottom_order') == ','.join(bottom.sections())
          and d._fm_panels.detached() == (), f"{bottom.sections()} kept={QSettings().value('FilterMate/sections/bottom_order')!r}")
    bottom.drop(order[-1], bottom.width() - 1, bottom)  # the usual order again
    QApplication.processEvents()
    QSettings().remove('FilterMate/sections/bottom_order')
    canvas = iface.mapCanvas()
    MOUSE['on_map'] = at(canvas, x=canvas.width() // 2, y=canvas.height() // 2)
    return mouse(*drag(at(bottom.chip('filtering')), MOUSE['on_map']))


def s_mouse_out_check():
    """Dropped on the map, where nothing knows of sections: a panel of its own, floating there."""
    if not mouse_works():
        return None
    d = dock()
    panels = d._fm_panels
    panel = panels.panel('filtering')
    place = MOUSE['on_map']
    check('mouse: a chip of the dock dropped on the map gets a panel, floating where it was dropped',
          panel is not None and panel.isFloating() and panel.isVisible() and panel.members == ['filtering']
          and panel.frameGeometry().contains(QPoint(*place)) and action_button('filter').isVisible(),
          f"{panels.groups()} at {panel.frameGeometry() if panel else None} for {place}")
    chip = d._fm_sections.bottom_rail.chip('exporting')
    canvas = iface.mapCanvas()
    away = at(canvas, x=canvas.width() // 4, y=canvas.height() // 4)
    return mouse(*drag(at(chip), away, before_release=('key', 'Escape', 'sleep', 0.4)))


def s_mouse_escape_check():
    """Escape while a chip is dragged: nothing moves (it made a floating panel under the pointer)."""
    if not mouse_works():
        return None
    d = dock()
    panels = d._fm_panels
    check('mouse: a drag given up with Escape changes nothing', panels.groups() == (('filtering',),)
          and d.isAncestorOf(d.EXPORTING), f"{panels.groups()} ends={MOUSE['ends']}")
    return mouse(*drag(at(d._fm_sections.bottom_rail.chip('exporting')), at(panels.panel('filtering'), y=200)))


def s_mouse_join_check():
    """Dropped on a panel, out of its rail: the section joins it."""
    if not mouse_works():
        return None
    d = dock()
    panels = d._fm_panels
    panel = panels.panel('filtering')
    check('mouse: a chip of the dock dropped on a panel joins it; the panel lists both in its rail',
          panel is not None and panels.panel('exporting') is panel and panel.members == ['filtering', 'exporting']
          and panel.rail.isVisible() and panel.current() == 'exporting' and action_button('export').isVisible(),
          f"{panels.groups()} current={panel.current() if panel else None}")
    if panel is None or panel.rail.chip('exporting') is None:
        return None
    return mouse(*drag(at(panel.rail.chip('exporting')), at(panel.rail.chip('filtering'), x=2)))


def s_mouse_panel_rail_check():
    if not mouse_works():
        return None
    d = dock()
    panels = d._fm_panels
    panel = panels.panel('filtering')
    check('mouse: a chip dragged along the rail of a panel reorders its sections, and renames the panel',
          panel is not None and panel.members == ['exporting', 'filtering']
          and panel.windowTitle() == 'EXPORTING · FILTERING' and QSettings().value(DETACHED_KEY) == 'exporting+filtering',
          f"{panel.members if panel else None} {panel.windowTitle() if panel else None} "
          f"kept={QSettings().value(DETACHED_KEY)!r}")
    if panel is None or panel.rail.chip('filtering') is None:
        return None
    return mouse(*drag(at(panel.rail.chip('filtering')), at(d.frame_exploring)))


def s_mouse_back_check():
    """Dropped on the dock, out of its rails: the section comes back."""
    if not mouse_works():
        return None
    d = dock()
    panels = d._fm_panels
    check('mouse: a chip of a panel dropped on the dock comes back to it', panels.groups() == (('exporting',),)
          and d.isAncestorOf(d.FILTERING) and d._fm_sections.bottom_rail.chip('filtering').isVisible(),
          str(panels.groups()))
    MOUSE['target'] = 'configuration'
    panels.detach('configuration')  # a second panel, docked: the floating one is dropped on it as a tab
    QApplication.processEvents()
    QApplication.processEvents()
    floating, docked = panels.panel('exporting'), panels.panel('configuration')
    if floating is None or docked is None:
        return None
    MOUSE['docked_floating'] = (docked.isFloating(), floating.isFloating())
    # By its title, as a hand takes a panel; held over the middle of the other one, where Qt offers a tab.
    return mouse(*drag(at(floating, y=11), at(docked), hold=1.0))


def s_mouse_tab_check():
    """A panel dragged by its title onto another one, as a tab: Qt plugs it there (its own way, not
    tabifyDockWidget), and the two merge."""
    if not mouse_works():
        return None
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    docked = panels.panel('configuration')
    together = docked is not None and panels.panel('exporting') is docked
    check('mouse: a panel dropped as a tab of another one with the mouse gives it its sections',
          together and docked.members == ['configuration', 'exporting'] and len(panels.groups()) == 1
          and not docked.isFloating() and docked.rail.isVisible(),
          f"{panels.groups()} floating before={MOUSE.get('docked_floating')} "
          f"tabs={[w.objectName() for w in window.tabifiedDockWidgets(docked)] if docked else None}")
    if docked is None:
        return None
    MOUSE['aim'] = (at(docked, y=11), at(d.frame_exploring))
    return mouse(*drag(at(docked, y=11), at(d.frame_exploring), hold=1.0))


def s_mouse_dock_tab_check():
    """The panel dragged by its title onto the dock, as a tab: its sections come back."""
    if not mouse_works():
        return None
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    left = panels.panel('configuration')
    check('mouse: a panel dropped as a tab of the dock with the mouse gives its sections back',
          panels.detached() == () and d.isAncestorOf(d.EXPORTING) and d.isAncestorOf(d.CONFIGURATION)
          and d.isVisible(),
          f"{panels.groups()} floating={left.isFloating() if left else None} "
          f"at={left.frameGeometry() if left else None} dock={d.frameGeometry()} "
          f"tabs of the dock={[w.objectName() for w in window.tabifiedDockWidgets(d)]} "
          f"aimed={MOUSE.get('aim')}")
    leave_welcome()
    QSettings().remove('FilterMate/sections/bottom_order')
    open_section(d.FILTERING)
    check('mouse: left as found', panels.detached() == () and not QSettings().value(DETACHED_KEY)
          and d._fm_sections.bottom_rail.sections() == MOUSE['order']
          and d.toolBox_tabTools.currentWidget() is d.FILTERING and d.isVisible() and not d.isFloating(),
          f"{panels.groups()} {d._fm_sections.bottom_rail.sections()}")
    return settled()


MOUSE_STEPS = [s_section_setup, s_mouse_setup, s_mouse_reorder, s_mouse_reorder_check, s_mouse_out_check,
               s_mouse_escape_check, s_mouse_join_check, s_mouse_panel_rail_check, s_mouse_back_check,
               s_mouse_tab_check, s_mouse_dock_tab_check]


# --- the freedom to switch: any layout from any other one, in any order (FM_ONLY=switch) ----------------------------
#
# A walk at random (FM_SEED, the same walk for the same seed) through what changes the layout of the dock: where each
# section is (dock, panel of its own, panel shared), how the stacks list their sections, where the buttons are,
# sections turned off, display profile, theme, the dock closed, QGIS restarted. After each move the dock must still
# be usable (``switch_problems``); every few moves, and at the end, everything is put back as the dock is by
# default and compared with what it was before the walk (``switch_print``).

SWITCH = {}
SWITCH_SETTINGS = {
    'APP.DOCKWIDGET.SECTION_HEADERS': ('rail', 'stacked'),
    'APP.DOCKWIDGET.SECTION_HEIGHT': ('fill', 'fit'),
    'APP.DOCKWIDGET.ACTION_BAR_POSITION': ('bottom', 'top', 'left', 'right', 'sections'),
    'APP.DOCKWIDGET.ACTION_BAR_VERTICAL_ALIGNMENT': ('top', 'bottom'),
    'APP.OPTIONS.FILTERING.enabled': (True, False),
    'APP.OPTIONS.EXPORTING.enabled': (True, False),
    'APP.DOCKWIDGET.UI_PROFILE': ('auto', 'compact', 'normal'),
    'APP.DOCKWIDGET.COLORS.ACTIVE_THEME': ('light', 'dark'),
}
SWITCH_OWNERS = {'filter': 'filtering', 'undo_filter': 'filtering', 'redo_filter': 'filtering', 'compare': 'filtering',
                 'unfilter': 'filtering', 'export': 'exporting', 'about': 'configuration'}


def pump(milliseconds=80):
    """Let Qt run its events, its timers and what was put off to a later turn of its loop."""
    end = time.time() + milliseconds / 1000.0
    while time.time() < end:
        QApplication.processEvents()
        time.sleep(0.004)


def settles(condition, seconds=2.0):
    """``condition`` holds, at once or within ``seconds``: a layout is applied a few turns of the loop of Qt after
    what asked for it (a change of profile or of theme, a bar that changed parent)."""
    end = time.time() + seconds
    while not condition():
        if time.time() > end:
            return False
        pump(50)
    return True


def switch_pages():
    d = dock()
    return {'agent': d._fm_sections._pages.get('agent'), 'exploring': d.frame_exploring, 'filtering': d.FILTERING,
            'exporting': d.EXPORTING, 'configuration': d.CONFIGURATION}


def switch_way_in(key):
    """What the user clicks to open the section ``key`` where it is: its chip, or its header."""
    d = dock()
    panels, sections = d._fm_panels, d._fm_sections
    panel = panels.panel(key)
    if panel is not None:
        return panel.rail.chip(key) if len(panel.members) > 1 else panel
    if sections.stacked:
        if key in sections._headers:
            return sections._headers[key]
        title = d.toolBox_tabTools.itemText(d.toolBox_tabTools.indexOf(switch_pages()[key]))
        return next((button for button in sections._bottom_headers() if button.text() == title), None)
    return (sections.top_rail if key in sections._headers else sections.bottom_rail).chip(key)


def switch_problems():
    """What is wrong with the layout as it is now: an empty list when the dock is usable."""
    d = dock()
    panels, sections = d._fm_panels, d._fm_sections
    module = importlib.import_module(f'{PACKAGE}.ui.layout.section_panels')
    found = []
    errors = STATE['python_errors'][SWITCH['errors']:]
    if errors:  # told once: the walk moves SWITCH['errors'] on after it reported them
        found.append(f"python errors: {errors[:2]}")
    present, in_dock, apart = list(panels._present()), list(panels.in_dock()), list(panels.detached())
    pages = switch_pages()
    # Where each section is, and what the two sides say of it.
    if not in_dock:
        found.append('the dock holds no section')
    if set(sections.detached) != set(apart):
        found.append(f"the stacks say {sorted(sections.detached)} are apart, the panels {apart}")
    for panel in panels._panels:
        if not panel.members:
            found.append('a panel with no section is kept')
        found += [f"{key} is listed by a panel that is not its own" for key in panel.members
                  if panels.panel(key) is not panel]
        if panel.isHidden() != bool(panels._hidden_with_dock):
            found.append(f"the panel of {panel.members} is {'hidden' if panel.isHidden() else 'shown'} "
                         f"while the dock is {'closed' if panels._hidden_with_dock else 'open'}")
    for key in present:
        panel = panels.panel(key)
        if panel is None and not d.isAncestorOf(pages[key]):
            found.append(f"{key} is neither in the dock nor in a panel")
        elif panel is not None and not panel.isAncestorOf(pages[key]):
            found.append(f"{key} is not in the panel that holds it")
    saved = tuple(group for group in (tuple(key for key in group if key in present)
                                      for group in module.parse_groups(QSettings().value(DETACHED_KEY, ''))) if group)
    if set(saved) != set(panels.groups()):  # the panels in any order: a restored one is the newest again
        found.append(f"kept for the next time {saved}, shown {panels.groups()}")
    # A way to open each section.
    host_of = {key: (panels.panel(key) or d) for key in present}
    for key in present:
        way = switch_way_in(key)
        if way is None or (way is not host_of[key] and not way.isVisibleTo(host_of[key])):
            found.append(f"no chip nor header to open {key} ({'stacked' if sections.stacked else 'rail'})")
    # What is open.
    above = [key for key in ('agent', 'exploring') if key in in_dock]
    open_above = [key for key in above if sections._open_in_stack(key)]
    if len(open_above) > 1 or ('exploring' in in_dock and len(open_above) != 1):
        found.append(f"{open_above} open above, of {above}")
    below = sections.bottom_key()
    if below is not None and (below not in in_dock or not sections.section_shown(below)):
        found.append(f"the lower stack shows {below}, which is not in the dock")
    if ('exploring' in in_dock and below == 'filtering' and sections._open_in_stack('agent')):
        found.append('AGENT and FILTERING open together in the dock, EXPLORING folded')
    if in_dock and not open_above and below is None:
        found.append(f"nothing is open in the dock, which holds {in_dock}")
    # The buttons where their section is.
    for name, owner in SWITCH_OWNERS.items():
        button = action_button(name)
        if button is None:
            continue
        panel = panels.panel(owner)
        if not (panel or d).isAncestorOf(button):
            found.append(f"the button {name} is not where {owner} is")
    for name, owner in (('filter', 'filtering'), ('export', 'exporting')):
        if owner not in present or action_button(name) is None:
            continue
        panel = panels.panel(owner)
        is_open = panel.current() == owner if panel is not None else below == owner
        if is_open and not action_button(name).isVisibleTo(panel or d):
            found.append(f"{owner} is open and shows no {name} button (bar {d._action_bar_manager.get_position()})")
    # The chooser of the current layer.
    combo, mirror = d.comboBox_filtering_current_layer, explo_mirror()
    mirror_shown = mirror is not None and not mirror.isHidden()
    if not sections.section_shown('filtering'):
        if mirror_shown or not d.frame_exploring.isAncestorOf(combo) or combo.isHidden():
            found.append('FILTERING is off and its chooser of the current layer is not at the top of EXPLORING')
    elif mirror_shown == sections.together() or not d.FILTERING.isAncestorOf(combo):
        found.append(f"the second chooser is {'shown' if mirror_shown else 'hidden'} with EXPLORING and FILTERING "
                     f"{'both in the dock' if sections.together() else 'separated'}")
    # Room: an open section is not squeezed to nothing, the dock has its minimum when its sections are in it.
    lower = d.splitter_main.widget(1)
    if below is None and d.isVisible() and not d.visibleRegion().isEmpty() and lower.isVisibleTo(d):
        rail = sections._bottom_headers_height(lower)
        if lower.height() > rail + 6:
            found.append(f"nothing is open below and the lower stack is {lower.height()} px high for {rail} px of "
                         f"{'headers' if sections.stacked else 'rail'}")
    watcher = getattr(d, '_theme_watcher', None)
    if watcher is not None and d._on_qgis_theme_changed not in watcher._callbacks:
        found.append('the dock no longer follows the theme of QGIS')
    relaxed = any(key != 'agent' for key in apart)
    if panels._dock_relaxed != relaxed:
        found.append(f"the minimum height of the dock is {'given up' if panels._dock_relaxed else 'kept'} with {apart} apart")
    if d.isVisible() and not d.visibleRegion().isEmpty():
        for key in open_above + ([below] if below else []):
            if pages[key].height() < 30:
                splitter = d.splitter_main
                found.append(f"{key} is open in the dock, {pages[key].height()} px high (dock {d.height()}, upper stack "
                             f"{sections.top.height()} max {sections.top.maximumHeight()}, splitter {splitter.sizes()} "
                             f"of {splitter.height()}, share {sections._share:.2f}, lower shown "
                             f"{splitter.widget(1).isVisibleTo(d)} min {splitter.widget(1).minimumHeight()} "
                             f"max {splitter.widget(1).maximumHeight()}, bar {d._action_bar_manager.get_position()})")
    return found


def switch_print():
    """The dock as it is by default, in what a user would notice: what shows, where, in which order."""
    d = dock()
    sections, toolbox = d._fm_sections, d.toolBox_tabTools
    bar = d.frame_actions
    buttons = sorted((b for b in bar.findChildren(QPushButton) if b.isVisible()), key=lambda b: (b.y(), b.x()))
    return {
        'apart': d._fm_panels.detached(), 'saved': QSettings().value(DETACHED_KEY) or '',
        'stacked': sections.stacked, 'position': d._action_bar_manager.get_position(),
        'top chips': [key for key in sections.top_rail.shown_sections() if sections.top_rail.chip(key).isVisibleTo(d)],
        'bottom chips': [key for key in sections.bottom_rail.shown_sections()
                         if sections.bottom_rail.chip(key).isVisibleTo(d)],
        'open': (next((key for key in sections._pages if sections._open_in_stack(key)), None), sections.bottom_key()),
        'buttons': [b.objectName().replace('pushButton_action_', '') for b in buttons],
        'bar shown': bar.isVisibleTo(d), 'bar parent': bar.parentWidget().objectName(),
        'bar under': (bar.mapTo(d, QPoint(0, 0)).y() > toolbox.mapTo(d, QPoint(0, 0)).y()) if bar.isVisibleTo(d) else None,
        'mirror': bool(explo_mirror() is not None and not explo_mirror().isHidden()),
        'chooser in FILTERING': d.FILTERING.isAncestorOf(d.comboBox_filtering_current_layer),
        'relaxed': d._fm_panels._dock_relaxed, 'top shown': sections.top.isVisibleTo(d),
        'toolbox shown': toolbox.isVisibleTo(d), 'dock shown': d.isVisible(),
    }


def switch_to_default():
    """Everything as the dock is by default, by the means a user has: every section merged back, the settings of the
    layout at their values of before the walk, EXPLORING and FILTERING open."""
    d = dock()
    if not d.isVisible():
        qgis.utils.plugins[PACKAGE].run()
        pump(300)
    d._fm_panels.attach_all()
    pump()
    values = {path: value for path, value in SWITCH['settings'].items() if config_value(path) != value}
    if values:
        apply_settings(values)
        pump(250)
    d._fm_sections.open_top('exploring')
    open_section(d.FILTERING)
    pump(120)


def switch_moves():
    """The moves of the walk, each ``(weight, name, run)``; ``run(rng)`` does one and says what, None when there is
    nothing of the kind to do in the layout as it is."""
    d = dock()
    panels, sections = d._fm_panels, d._fm_sections
    module = importlib.import_module(f'{PACKAGE}.ui.layout.section_panels')
    window = iface.mainWindow()

    def setting(path):
        def run(rng):
            value = rng.choice([choice for choice in SWITCH_SETTINGS[path] if choice != config_value(path)])
            apply_settings({path: value})
            pump(250 if 'PROFILE' in path or 'THEME' in path else 60)
            return f"{'.'.join(path.split('.')[2:])} = {value}"
        return run

    def detach(rng):
        keys = [key for key in panels._present() if panels.can_detach(key)
                or (panels.panel(key) is not None and len(panels.panel(key).members) > 1)]
        if not keys:
            return None
        key = rng.choice(keys)
        return f"{key} in a panel of its own: {panels.detach(key)}"

    def smart(rng):
        keys = [key for key in panels._present() if panels.can_detach(key)]
        if not keys:
            return None
        key = rng.choice(keys)
        return f"{key} out of the dock, wherever it goes: {panels.open_smart(key)}"

    def group(rng):
        pairs = [(key, panel) for panel in panels._panels for key in panels._present() if panels.can_take(key, panel)]
        if not pairs:
            return None
        key, panel = rng.choice(pairs)
        return f"{key} into the panel of {list(panel.members)}: {panels.move(key, panel)}"

    def attach(rng):
        keys = list(panels.detached())
        if not keys:
            return None
        key = rng.choice(keys)
        return f"{key} merged back: {panels.attach(key)}"

    def close_panel(rng):
        if not panels._panels or panels._hidden_with_dock:
            return None
        panel = rng.choice(panels._panels)
        members = list(panel.members)
        panel.close()
        pump(150)
        return f"the panel of {members} closed"

    def float_panel(rng):
        if not panels._panels or panels._hidden_with_dock:
            return None
        panel = rng.choice(panels._panels)
        panel.setFloating(not panel.isFloating())
        pump(450)  # a panel that lands as a tab of another one of FilterMate merges a moment later
        return f"the panel of {list(panel.members)} {'floating' if panel.isFloating() else 'docked'}"

    def open_above(rng):
        keys = [key for key in sections._pages if key not in sections.detached]
        if not keys:
            return None
        key = rng.choice(keys)
        switch_way_in(key).click()
        return f"click on {key} above"

    def open_below(rng):
        keys = [key for key in ('filtering', 'exporting', 'configuration')
                if key in panels.in_dock() and sections.section_shown(key)]
        if not keys:
            return None
        key = rng.choice(keys)
        way = switch_way_in(key)
        if sections.stacked:  # QToolBox opens the page of a header itself; the dock then folds the open one
            way.pressed.emit()
        way.click()
        return f"click on {key} below"

    def open_in_panel(rng):
        shared = [panel for panel in panels._panels if len(panel.members) > 1]
        if not shared:
            return None
        panel = rng.choice(shared)
        key = rng.choice(panel.members)
        panel.rail.chip(key).click()
        return f"click on {key} in the panel of {list(panel.members)}"

    def close_dock(rng):
        if d.isVisible():
            d.close()
            pump(200)
            return 'the dock closed'
        qgis.utils.plugins[PACKAGE].run()
        pump(400)
        return 'the dock opened again'

    def restart(rng):
        if not d.isVisible() or d.isFloating():
            return None
        before = panels.groups()
        area = window.dockWidgetArea(d)
        state = window.saveState()
        panels.attach_all(remember=False)
        iface.removeDockWidget(d)
        pump()
        window.restoreState(state)
        QSettings().setValue(module.DOCK_AREA_KEY, module._area_number(area))
        module.place_dock(d, iface, area)
        d.show()
        panels.restore()
        pump(200)
        same = panels.groups() == before
        if not same:
            SWITCH['found'].append((SWITCH['done'], f"after a restart {panels.groups()}, before {before}"))
        return f"restart: {'the same panels' if same else 'OTHER PANELS'}"

    return [(10, 'detach', detach), (6, 'smart', smart), (8, 'group', group), (10, 'attach', attach),
            (2, 'detach all', lambda rng: f"every section out: {panels.detach_all()}"),
            (2, 'attach all', lambda rng: (panels.attach_all(), 'every section merged back')[1]),
            (3, 'close panel', close_panel), (3, 'float', float_panel),
            (7, 'open above', open_above), (9, 'open below', open_below), (4, 'open in panel', open_in_panel),
            (5, 'headers', setting('APP.DOCKWIDGET.SECTION_HEADERS')),
            (2, 'height', setting('APP.DOCKWIDGET.SECTION_HEIGHT')),
            (8, 'position', setting('APP.DOCKWIDGET.ACTION_BAR_POSITION')),
            (2, 'alignment', setting('APP.DOCKWIDGET.ACTION_BAR_VERTICAL_ALIGNMENT')),
            (5, 'filtering', setting('APP.OPTIONS.FILTERING.enabled')),
            (4, 'exporting', setting('APP.OPTIONS.EXPORTING.enabled')),
            (2, 'profile', setting('APP.DOCKWIDGET.UI_PROFILE')),
            (1, 'theme', setting('APP.DOCKWIDGET.COLORS.ACTIVE_THEME')),
            (2, 'dock', close_dock), (2, 'restart', restart)]


def s_switch_begin():
    import random
    leave_welcome()
    SWITCH.update(seed=int(os.environ.get('FM_SEED', '1')), wanted=int(os.environ.get('FM_SWITCHES', '100')),
                  done=0, found=[], trail=[], resets=0, errors=len(STATE['python_errors']),
                  settings={path: config_value(path) for path in SWITCH_SETTINGS})
    SWITCH['rng'] = random.Random(SWITCH['seed'])
    switch_to_default()
    SWITCH['default'] = switch_print()
    problems = switch_problems()
    check('switch: the dock as it is by default is usable', not problems, '; '.join(problems))
    print(f"   switch: seed {SWITCH['seed']}, {SWITCH['wanted']} moves, default {SWITCH['default']}", flush=True)
    return waits(0.3)


def switch_compare(label):
    """Put the dock back as it is by default and tell what differs from before the walk."""
    switch_to_default()
    before = SWITCH['default']
    settles(lambda: switch_print() == before and not switch_problems())
    now = switch_print()
    differs = {key: (before[key], now[key]) for key in before if now[key] != before[key]}
    problems = switch_problems()
    SWITCH['errors'] = len(STATE['python_errors'])
    SWITCH['resets'] += 1
    if differs or problems:
        SWITCH['found'].append((SWITCH['done'], f"{label}: not as before the walk {differs} {problems}"))
        print(f"   switch {SWITCH['done']:3d}: BACK TO DEFAULT differs {differs} {problems}", flush=True)
    return not differs and not problems


def s_switch_walk():
    """A slice of the walk: 25 moves, the invariants after each, and the way back to the default at its end."""
    moves = switch_moves()
    rng = SWITCH['rng']
    weights = [weight for weight, _name, _run in moves]
    until = min(SWITCH['wanted'], SWITCH['done'] + 25)
    while SWITCH['done'] < until:
        _weight, name, run = rng.choices(moves, weights)[0]
        try:
            said = run(rng)
        except Exception:
            said = f"{name} RAISED {traceback.format_exc().strip().splitlines()[-1]}"
            SWITCH['found'].append((SWITCH['done'], said))
        if said is None:
            continue  # nothing of the kind to do here: another move
        SWITCH['done'] += 1
        pump()
        settles(lambda: not switch_problems(), 1.0)
        problems = switch_problems()
        SWITCH['errors'] = len(STATE['python_errors'])
        SWITCH['trail'].append(said)
        print(f"   switch {SWITCH['done']:3d}: {said}{'  <-- ' + '; '.join(problems) if problems else ''}", flush=True)
        if problems:
            SWITCH['found'].append((SWITCH['done'], f"after [{said}]: {'; '.join(problems)}"))
    switch_compare(f"after {SWITCH['done']} moves")
    return waits(0.2)


def s_switch_end():
    back = switch_compare('at the end')
    found = SWITCH['found']
    check(f"switch: {SWITCH['done']} moves at random (seed {SWITCH['seed']}), the dock usable after each",
          not [what for _at, what in found if 'not as before the walk' not in what],
          ' | '.join(f"#{at} {what}" for at, what in found if 'not as before the walk' not in what)[:1500])
    check(f"switch: back to the default layout {SWITCH['resets']} times, each time as before the walk",
          back and not [what for _at, what in found if 'not as before the walk' in what],
          ' | '.join(f"#{at} {what}" for at, what in found if 'not as before the walk' in what)[:1500])
    return waits(0.3)


def bar_place():
    """Where the bar that holds Filter is, seen from the stacks: ``top``, ``bottom``, ``left``, ``right``; None when
    Filter is not shown."""
    d = dock()
    button = action_button('filter')
    if button is None or not button.isVisibleTo(d):
        return None
    bar, splitter = button.parentWidget(), d.splitter_main
    at, stacks = bar.mapTo(d, QPoint(0, 0)), splitter.mapTo(d, QPoint(0, 0))
    if bar.height() > bar.width():  # a column of buttons, beside the stacks
        return 'left' if at.x() < stacks.x() else 'right'
    return 'top' if at.y() < stacks.y() else 'bottom'


def s_switch_positions():
    """Every place of the buttons from every other one: the bar is where the setting says, each time."""
    d = dock()
    leave_welcome()
    path = 'APP.DOCKWIDGET.ACTION_BAR_POSITION'
    before = config_value(path)
    open_section(d.FILTERING)
    pump(120)
    gaps = spread(d.frame_actions)  # as the bar is when the dock opens
    wrong = []
    places = SWITCH_SETTINGS[path]
    order = [(first, second) for first in places for second in places if first != second]
    for first, second in order:
        for value in (first, second):
            if config_value(path) != value:
                apply_settings({path: value})
                pump(60)
            open_section(d.FILTERING)
            pump(40)
            wanted = 'bottom' if value == 'sections' else value
            if not settles(lambda: bar_place() == wanted):
                wrong.append(f"{first} -> {second}: at {value} the buttons are at {bar_place()}")
    apply_settings({path: before})
    pump(60)
    open_section(d.FILTERING)
    check('switch: every place of the buttons from every other one, the bar where the setting says',
          not wrong and bar_place() == ('bottom' if before == 'sections' else before), ' | '.join(wrong[:8]))

    def same_look():
        now = spread(d.frame_actions)
        return len(now) == len(gaps) and all(abs(a - b) <= 3 for a, b in zip(now, gaps))
    # 2026-11-17, review: rebuilt, the bar grouped its buttons in the centre; spread again once a section left.
    check('switch: back at its place, the bar spreads its buttons as when the dock opened', settles(same_look),
          f"gaps at the start {gaps}, now {spread(d.frame_actions)}")
    return waits(0.3)


def s_switch_stack_back():
    """The upper stack comes back from hidden (AGENT and EXPLORING were both in panels) while the lower one shows
    its rail only: AGENT opened 0 px high, the room of the stacks being read from sizes that had none for it."""
    d = dock()
    panels, sections = d._fm_panels, d._fm_sections
    if 'agent' not in sections._headers:
        return None
    leave_welcome()
    panels.detach('agent')
    panels.detach('exploring')
    pump()
    open_section(None)
    hidden = not sections.top.isVisibleTo(d)
    panels.attach('agent')
    pump()
    sections.top_rail.chip('agent').click()
    page = sections._pages['agent']
    roomy = settles(lambda: sections._open_in_stack('agent') and page.height() > 80)
    check('switch: AGENT merged back to an upper stack that was hidden opens with room, nothing open below',
          hidden and roomy, f"hidden before={hidden} AGENT {page.height()} px, splitter {d.splitter_main.sizes()} "
          f"of {d.splitter_main.height()}")
    leave_welcome()
    return waits(0.3)


SWITCH_STEPS = [s_section_setup, s_vector_source, s_switch_positions, s_switch_stack_back, s_switch_begin,
                *[s_switch_walk] * max(1, (int(os.environ.get('FM_SWITCHES', '100')) + 24) // 25), s_switch_end]


# --- the rows of FILTERING / EXPORTING: packed at the top or spread (APP.DOCKWIDGET.SECTION_HEIGHT, FM_ONLY=rows) ------
#
# 18 November 2026: the rows were spread over the whole height of the section, the rail band ran down to the action
# bar, and in a short section the key buttons drifted under their rows (a layout spacing counted twice around each
# spacer) until the last one was cut. Now: each button in front of its row, a short section scrolls, the right margin
# is the gap to a scroll bar only when one shows, and the rows are one gap apart at the top with ``fit``. ``fit`` was
# the default for a day; since 19 November the rows are spread again by default (``fill``, as in 5.1.1: the steps of
# FM_ONLY=like511 compare them with it), and these steps choose ``fit`` first.

ROWS = {}


def mockup_module():
    return importlib.import_module(f'{PACKAGE}.ui.layout.mockup_layout')


def row_report(section):
    """What a section shows of its rows: ``(deltas, gaps, cut, page, area)``. ``deltas``: row centre - key button
    centre, per shown row; ``gaps``: between two shown rows; ``cut``: buttons that end below the rail band."""
    d = dock()
    module = mockup_module()
    page = getattr(d, section.upper())
    holder = getattr(d, f'widget_{section}_keys')
    pairs = module.FILTERING_PAIRS if section == 'filtering' else module.EXPORTING_PAIRS
    deltas, cut = [], []
    for button_name, value_name in pairs:
        button, value = getattr(d, button_name, None), getattr(d, value_name, None)
        if button is None or value is None or not button.isVisibleTo(page) or not value.isVisibleTo(page):
            continue
        b = button.mapTo(page, button.rect().center()).y()
        v = value.mapTo(page, value.rect().center()).y()
        deltas.append(v - b)
        if button.mapTo(holder, button.rect().bottomLeft()).y() > holder.height() - 1:
            cut.append(button_name)
    values = getattr(d, f'verticalLayout_{section}_values')
    rows = [values.itemAt(i).geometry() for i in range(values.count())
            if values.itemAt(i).spacerItem() is None and not values.itemAt(i).isEmpty()]
    gaps = [lower.top() - upper.bottom() - 1 for upper, lower in zip(rows, rows[1:])]
    viewport = page.parentWidget()
    area = viewport.parentWidget() if viewport is not None else None
    return deltas, gaps, cut, page, area if isinstance(area, QScrollArea) else None


def rows_text(section):
    deltas, gaps, cut, page, area = row_report(section)
    bar = area.verticalScrollBar() if area is not None else None
    main = getattr(dock(), f'horizontalLayout_{section}_main').contentsMargins()
    return (f"{section}: deltas={deltas} gaps={gaps} cut={cut} page={page.height()} hint={page.sizeHint().height()} "
            f"viewport={area.viewport().height() if area else None} bar max={bar.maximum() if bar else None} "
            f"shown={bar.isVisibleTo(area) if bar else None} right margin={main.right()}")


def rows_aligned(section):
    deltas, _gaps, cut, _page, _area = row_report(section)
    return len(deltas) >= 4 and all(abs(delta) <= 1 for delta in deltas) and not cut


def rows_packed(section):
    """``fit``: the rows one gap apart, the page held to them: inside a viewport as tall or taller (a panel sized to its
    rows, PANEL_SIZING), or scrolled in a shorter one."""
    _deltas, gaps, _cut, page, area = row_report(section)
    gap = mockup_module().ROW_GAP
    if len(gaps) < 3 or not all(abs(value - gap) <= 1 for value in gaps) or area is None:
        return False
    held = abs(page.height() - page.sizeHint().height()) <= 1
    return held and (page.height() <= area.viewport().height() or area.verticalScrollBar().maximum() > 0)


def right_margin_follows_bar(section):
    _deltas, _gaps, _cut, _page, area = row_report(section)
    if area is None:
        return False
    shown = area.verticalScrollBar().isVisibleTo(area)
    right = getattr(dock(), f'horizontalLayout_{section}_main').contentsMargins().right()
    return right == mockup_module().scroll_bar_margin(shown)


def s_rows_setup():
    d = dock()
    leave_welcome()
    ROWS['height'] = config_value('APP.DOCKWIDGET.SECTION_HEIGHT')
    ROWS['sizes'] = d.main_splitter.sizes()
    d._fm_sections.open_top('exploring')
    open_section(d.FILTERING)
    pump(400)
    check('rows: a configuration of now spreads the rows (the default, as in 5.1.1)', ROWS['height'] == 'fill'
          and d.property('fm_section_height') == 'fill'
          and settles(lambda: min(row_report('filtering')[1] or [0]) > mockup_module().ROW_GAP + 4
                      and rows_aligned('filtering')),
          f"setting={ROWS['height']} dock={d.property('fm_section_height')} | {rows_text('filtering')}")
    apply_settings({'APP.DOCKWIDGET.SECTION_HEIGHT': 'fit'})
    return waits(0.6)


def s_rows_fit_check():
    d = dock()
    check('rows: SECTION_HEIGHT = fit applied at once', d.property('fm_section_height') == 'fit',
          f"setting={config_value('APP.DOCKWIDGET.SECTION_HEIGHT')} dock={d.property('fm_section_height')}")
    check('rows: FILTERING, each key button in front of its row', settles(lambda: rows_aligned('filtering')),
          rows_text('filtering'))
    check('rows: FILTERING rows one gap apart at the top, the room left under them',
          settles(lambda: rows_packed('filtering')), rows_text('filtering'))
    check('rows: FILTERING right margin only beside a scroll bar', settles(lambda: right_margin_follows_bar('filtering')),
          rows_text('filtering'))
    exploring = d.findChild(QWidget, 'scrollAreaWidgetContents')
    area = d.scrollArea_frame_exploring
    check('rows: EXPLORING right margin only beside a scroll bar', settles(
        lambda: d.gridLayout_main_header.contentsMargins().right()
        == mockup_module().scroll_bar_margin(area.verticalScrollBar().isVisibleTo(area))),
        f"right={d.gridLayout_main_header.contentsMargins().right()} bar={area.verticalScrollBar().isVisibleTo(area)} "
        f"content={exploring is not None}")
    open_section(d.EXPORTING)
    return waits(0.6)


def s_rows_exporting_check():
    d = dock()
    check('rows: EXPORTING, each key button in front of its row', settles(lambda: rows_aligned('exporting')),
          rows_text('exporting'))
    check('rows: EXPORTING rows one gap apart at the top', settles(lambda: rows_packed('exporting')),
          rows_text('exporting'))
    open_section(d.FILTERING)
    total = sum(d.main_splitter.sizes())
    d.main_splitter.setSizes([total - 150, 150])  # a short lower stack: the rows no longer fit
    return waits(0.6)


def s_rows_short_check():
    d = dock()
    area = row_report('filtering')[4]
    check('rows: a short FILTERING scrolls, its rows not squeezed',
          settles(lambda: area is not None and area.verticalScrollBar().maximum() > 0
                  and all(abs(value - mockup_module().ROW_GAP) <= 1 for value in row_report('filtering')[1])),
          rows_text('filtering'))
    check('rows: a short FILTERING keeps each button in front of its row, none cut',
          settles(lambda: rows_aligned('filtering')), rows_text('filtering'))
    check('rows: a short FILTERING keeps one gap from its scroll bar', settles(lambda: right_margin_follows_bar('filtering')),
          rows_text('filtering'))
    d.main_splitter.setSizes(ROWS['sizes'])
    apply_settings({'APP.DOCKWIDGET.SECTION_HEIGHT': 'fill'})
    return waits(0.6)


def s_rows_fill_check():
    d = dock()
    gap = mockup_module().ROW_GAP
    check('rows: SECTION_HEIGHT = fill applied at once, the rows spread over the section',
          d.property('fm_section_height') == 'fill' and settles(lambda: min(row_report('filtering')[1] or [0]) > gap + 4),
          rows_text('filtering'))
    check('rows: spread, each key button still in front of its row', settles(lambda: rows_aligned('filtering')),
          rows_text('filtering'))
    # Spread, the page takes the height of its viewport: it has its size before Qt hides the scroll bar, and no
    # resize tells of the bar gone. A section given its height back in one step kept the 6 px beside the bar.
    total = sum(d.main_splitter.sizes())
    d.main_splitter.setSizes([total - 150, 150])
    area = row_report('filtering')[4]
    short = settles(lambda: area.verticalScrollBar().maximum() > 0 and right_margin_follows_bar('filtering'))
    d.main_splitter.setSizes(ROWS['sizes'])
    check('rows: spread, the right margin comes and goes with the scroll bar of a short section',
          short and settles(lambda: area.verticalScrollBar().maximum() == 0 and right_margin_follows_bar('filtering')),
          f"short: {short} | {rows_text('filtering')}")
    apply_settings({'APP.DOCKWIDGET.SECTION_HEIGHT': 'fit'})
    return waits(0.6)


def s_rows_hidden_change():
    """The setting changed while FILTERING is closed (CONFIGURATION open, as in the tree): its hidden scroll area was
    told nothing and kept the old height when FILTERING opened again (review of 18 November 2026)."""
    d = dock()
    open_section(d.CONFIGURATION)
    pump(200)
    apply_settings({'APP.DOCKWIDGET.SECTION_HEIGHT': 'fill'})
    pump(200)
    open_section(d.FILTERING)
    check('rows: fill set while FILTERING was closed, spread when it opens',
          settles(lambda: min(row_report('filtering')[1] or [0]) > mockup_module().ROW_GAP + 4
                  and rows_aligned('filtering')), rows_text('filtering'))
    open_section(d.CONFIGURATION)
    pump(200)
    apply_settings({'APP.DOCKWIDGET.SECTION_HEIGHT': 'fit'})
    pump(200)
    open_section(d.FILTERING)
    return waits(0.6)


def s_rows_fit_again_check():
    d = dock()
    check('rows: fit set while FILTERING was closed, then fit again: the rows one gap apart', d.property('fm_section_height') == 'fit'
          and settles(lambda: rows_packed('filtering') and rows_aligned('filtering')), rows_text('filtering'))
    if d._fm_panels.can_detach('filtering'):
        d._fm_panels.detach('filtering')
    return waits(0.8)


def s_rows_panel_check():
    d = dock()
    panel = d._fm_panels.panel('filtering')
    if panel is None:
        report('SKIP', 'rows: FILTERING in a panel of QGIS', 'it cannot leave the dock here')
        return None
    check('rows: FILTERING in its own panel, rows packed and buttons in front of them',
          settles(lambda: rows_packed('filtering') and rows_aligned('filtering')), rows_text('filtering'))
    check('rows: FILTERING in its own panel, right margin only beside a scroll bar',
          settles(lambda: right_margin_follows_bar('filtering')), rows_text('filtering'))
    d._fm_panels.attach('filtering')
    return waits(0.8)


def s_rows_end():
    d = dock()
    check('rows: FILTERING back in the dock, packed and aligned',
          settles(lambda: d.isAncestorOf(d.FILTERING) and rows_packed('filtering') and rows_aligned('filtering')),
          rows_text('filtering'))
    if config_value('APP.DOCKWIDGET.SECTION_HEIGHT') != ROWS['height']:
        apply_settings({'APP.DOCKWIDGET.SECTION_HEIGHT': ROWS['height']})
    d.main_splitter.setSizes(ROWS['sizes'])
    return waits(0.4)


ROWS_STEPS = [s_rows_setup, s_rows_fit_check, s_rows_exporting_check, s_rows_short_check, s_rows_fill_check,
              s_rows_hidden_change, s_rows_fit_again_check, s_rows_panel_check, s_rows_end]


# --- the heights of the dock and of the panels of its sections (APP.DOCKWIDGET.PANEL_SIZING, 19 November 2026) -----
# "No widgets laid out badly with a lot of empty space; a smart resizing when the widgets of FilterMate are separated."
# A rigid holder (FILTERING or EXPORTING open and nothing else, rows at their own height) is measured by the room left
# empty under its rows, in the scroll area that holds them: no more than a few pixels when a neighbour in its column can
# take the rest, and its rows not cut. No dock of QGIS below its minimum.

SIZING = {'rows': []}
SIZING_SLACK = 12  # px under the rows: the margins of the scroll area and rounding, never a row (34 px and more)


def sizing_holders():
    """The dock and the panels of FilterMate on screen, with a name for the report."""
    d = dock()
    holders = [('dock', d)] + [('+'.join(panel.members), panel) for panel in d._fm_panels._panels if panel.members]
    return [(name, holder) for name, holder in holders if holder.isVisible()]


def sizing_rigid_page(holder):
    """The page of FILTERING or EXPORTING when it is all ``holder`` opens (rows spread or not), else None."""
    d = dock()
    if holder is d:
        sections = d._fm_sections
        if any(sections._open_in_stack(key) for key in sections._pages):
            return None
        key = sections.bottom_key()
        if key in d._fm_panels.detached():
            return None
    else:
        key = holder.current()
    page = getattr(d, key.upper(), None) if key in ('filtering', 'exporting') else None
    return page if page is not None and page.isVisible() else None


def sizing_empty(holder):
    """What the scroll area of the rows of ``holder`` has more than they need at their own height: left empty under
    them (fit), or spread between them (fill); None when it is not rigid."""
    page = sizing_rigid_page(holder)
    if page is None:
        return None
    viewport = page.parentWidget()
    return viewport.height() - page.sizeHint().height()


def sizing_column(holder):
    """The docks of QGIS stacked with ``holder`` (its width overlapping theirs), on screen; [] when it floats."""
    window = iface.mainWindow()
    if holder.isFloating():
        return []
    area = window.dockWidgetArea(holder)
    left, width = holder.x(), holder.width()
    return [w for w in window.findChildren(QDockWidget) if w.parentWidget() is window
            if w.isVisible() and not w.isFloating() and window.dockWidgetArea(w) == area
            and 2 * (min(w.x() + w.width(), left + width) - max(w.x(), left)) > min(w.width(), width)
            and not (w is not holder and abs(w.y() - holder.y()) <= 2)]  # not a tab of the same group


def sizing_below_minimum():
    """The docks of QGIS on screen lower than their minimum."""
    window = iface.mainWindow()
    return [(w.objectName(), w.height(), max(w.minimumHeight(), w.minimumSizeHint().height()))
            for w in window.findChildren(QDockWidget) if w.parentWidget() is window
            if w.isVisible() and w.height() < max(w.minimumHeight(), w.minimumSizeHint().height()) - 1]


def sizing_state():
    """Each holder: its name, height, kind and the room under its rows; and where it is."""
    rows = []
    for name, holder in sizing_holders():
        empty = sizing_empty(holder)
        place = 'floating' if holder.isFloating() else f"column of {len(sizing_column(holder))}"
        least = max(holder.minimumHeight(), holder.minimumSizeHint().height())
        rows.append(f"{name}: {holder.height()} px {'rigid, ' + str(empty) + ' px under the rows' if empty is not None else 'elastic'}"
                    f" ({place}, minimum {least})")
    return '; '.join(rows)


def sizing_check(scenario, wanted_rigid=1):
    """Every rigid holder holds its rows with no room left under them (when a neighbour can take it), none cut; no
    dock below its minimum. ``wanted_rigid``: how many rigid holders the scenario shows (a check that measures nothing
    would pass)."""
    pump(900)  # the pass, and the late one of a drop
    rigid = [(name, holder, sizing_empty(holder)) for name, holder in sizing_holders() if sizing_empty(holder) is not None]
    for name, holder, empty in rigid:
        alone = not holder.isFloating() and len(sizing_column(holder)) < 2
        # Rigid docks side by side share one height: the one whose rows need the most sets it.
        beside = [other_empty for _other, other, other_empty in rigid if other is not holder and not other.isFloating()
                  and not holder.isFloating() and abs(other.y() - holder.y()) <= 2 and abs(other.height() - holder.height()) <= 2]
        note = 'alone' if alone else (f"beside one with {min(beside)} px" if beside else '')
        SIZING['rows'].append((scenario, name, holder.height(), empty, note))
        if alone:
            report('SKIP', f"sizing: {scenario}: {name} alone in its column", f"{empty} px under its rows: Qt gives it all")
            continue
        if not holder.isFloating() and [w for w in iface.mainWindow().tabifiedDockWidgets(holder) if w.isVisible()]:
            report('SKIP', f"sizing: {scenario}: {name} in a group of tabs", f"{empty} px under its rows: the height of the group")
            continue
        if empty > SIZING_SLACK and holder.height() <= max(holder.minimumHeight(), holder.minimumSizeHint().height()) + 2:
            report('SKIP', f"sizing: {scenario}: {name} held to its minimum", f"{empty} px under its rows | {sizing_state()}")
            continue
        if beside and min(beside) < empty:
            check(f"sizing: {scenario}: {name}, beside a taller section, not cut", empty >= -2,
                  f"{empty} px under its rows, {min(beside)} beside | {sizing_state()}")
            continue
        check(f"sizing: {scenario}: {name} at the height of its rows", -2 <= empty <= SIZING_SLACK,
              f"{empty} px under its rows | {sizing_state()}")
    check(f"sizing: {scenario}: the holders measured", len(rigid) >= wanted_rigid, sizing_state())
    low = sizing_below_minimum()
    check(f"sizing: {scenario}: no dock below its minimum", not low, str(low))
    cut = sizing_cut_in_width()
    check(f"sizing: {scenario}: no row cut on the right", not cut, str(cut))


def sizing_cut_in_width():
    """The holders whose open section of the lower stack asks for more width than its scroll area shows."""
    d = dock()
    cut = []
    for name, holder in sizing_holders():
        key = holder.current() if holder is not d else d._fm_sections.bottom_key()
        if key not in ('filtering', 'exporting', 'configuration') or (holder is d and key in d._fm_panels.detached()):
            continue
        page = getattr(d, key.upper())
        if not page.isVisible():
            continue
        viewport = page.parentWidget()
        if page.minimumSizeHint().width() > viewport.width() + 1:
            cut.append((name, key, page.minimumSizeHint().width(), viewport.width()))
    return cut


def sizing_armed():
    """The start is over for the panels (a version before that state has none: always)."""
    return getattr(dock()._fm_panels, '_armed', True)


def user_drop(holder, act):
    """``act`` (a move of ``holder``) as a drop with the mouse: the press on its title before, the release after,
    as the panels see them (a drag with the real pointer blocks the steps: FM_ONLY=mouse does that one)."""
    panels = dock()._fm_panels
    on_mouse = getattr(panels, '_on_mouse', None)
    try:
        if on_mouse is not None:
            on_mouse(True, holder)
    except TypeError:  # a version that does not say which dock was pressed
        on_mouse(True)
    act()
    pump(100)
    try:
        if on_mouse is not None:
            on_mouse(False, holder)
    except TypeError:
        on_mouse(False)


def sizing_reset():
    d = dock()
    d._fm_panels.attach_all()
    QSettings().remove(DETACHED_KEY)
    d._fm_sections.open_top('exploring')
    open_section(d.FILTERING)
    pump(300)


def s_sizing_setup():
    d = dock()
    leave_welcome()
    SIZING['state'] = iface.mainWindow().saveState()
    # The handle between the two stacks, kept for the next session: given back at the end (like511 reads it).
    SIZING['share'] = (d._fm_sections._share, QSettings().value('FilterMate/splitter_top_share'), d.main_splitter.sizes())
    try:
        SIZING['auto'] = config_value('APP.DOCKWIDGET.PANEL_SIZING') is not None
    except KeyError:  # a version before the setting (the pictures before it)
        SIZING['auto'] = False
    if SIZING['auto'] and config_value('APP.DOCKWIDGET.PANEL_SIZING') != 'auto':
        apply_settings({'APP.DOCKWIDGET.PANEL_SIZING': 'auto'})
    sizing_reset()
    settles(lambda: d.toolBox_tabTools.currentWidget() is d.FILTERING)
    SIZING['dock_width'] = d.width()
    SIZING['height'] = config_value('APP.DOCKWIDGET.SECTION_HEIGHT')
    if SIZING['auto']:  # the rows need the same height spread or not: one need in both modes
        hints = {}
        for mode in ('fit', 'fill'):
            apply_settings({'APP.DOCKWIDGET.SECTION_HEIGHT': mode})
            pump(600)
            hints[mode] = (d.FILTERING.sizeHint().height(), d.EXPORTING.sizeHint().height())
        check('sizing: the rows of FILTERING and EXPORTING need the same height spread (fill) or not (fit)',
              hints['fit'] == hints['fill'], str(hints))
    mode = os.environ.get('FM_SIZING_MODE') or SIZING['height']
    if mode != config_value('APP.DOCKWIDGET.SECTION_HEIGHT'):
        apply_settings({'APP.DOCKWIDGET.SECTION_HEIGHT': mode})
        pump(600)
    SIZING['mode'] = config_value('APP.DOCKWIDGET.SECTION_HEIGHT')
    print(f"   sizing | rows: {SIZING['mode']}", flush=True)
    check('sizing: the panels size themselves once the start is over', settles(sizing_armed, 8))
    grab_window('sizing_00_dock')
    return None


def s_sizing_filtering_below():
    panels = dock()._fm_panels
    panels.detach('filtering')
    sizing_check('FILTERING below the dock')
    grab_window('sizing_01_filtering_below')
    # The user makes it shorter: nothing is resized (a separator dragged is no change of structure), the rows scroll.
    d, window, panel = dock(), iface.mainWindow(), panels.panel('filtering')
    total = d.height() + panel.height()
    window.resizeDocks([d, panel], [total - 150, 150], Qt.Orientation.Vertical)
    pump(900)
    short = panel.height()
    check('sizing: a panel the user made shorter stays so, its rows scroll', short < 200 and sizing_empty(panel) < 0
          and right_margin_follows_bar('filtering'), f"{short} px, {sizing_empty(panel)} px under the rows")
    panels.resize_soon()  # as a change of a setting does: sized again, its scroll bar gone with its margin
    pump(900)
    check('sizing: sized again, the panel holds its rows and its right margin follows the scroll bar it lost',
          -2 <= sizing_empty(panel) <= SIZING_SLACK and right_margin_follows_bar('filtering'),
          f"{panel.height()} px, {sizing_empty(panel)} px under the rows, margin "
          f"{d.horizontalLayout_filtering_main.contentsMargins().right()}")
    return None


def s_sizing_exploring():
    d = dock()
    sizing_reset()
    d._fm_panels.detach('exploring')
    sizing_check('EXPLORING out, the dock keeps FILTERING')
    panel = d._fm_panels.panel('exploring')
    check('sizing: EXPLORING above the dock takes the rest of its column', panel is not None and panel_place(panel) == 'above'
          and panel.height() > d.height(), sizing_state())
    grab_window('sizing_02_exploring_above')
    return None


def s_sizing_every_section():
    d = dock()
    sizing_reset()
    d._fm_panels.detach_all()
    sizing_check('every section out')
    grab_window('sizing_03_every_section_out')
    return None


def s_sizing_grouped():
    d = dock()
    panels = d._fm_panels
    sizing_reset()
    panels.detach('filtering')
    panels.group('exporting', 'filtering')
    panel = panels.panel('filtering')
    if not check('sizing: FILTERING and EXPORTING grouped in one panel', panel is not None
                 and panel.members == ['filtering', 'exporting'], str(panels.groups())):
        return None
    panel.rail.chip('filtering').click()
    sizing_check('FILTERING + EXPORTING grouped, FILTERING open')
    grab_window('sizing_04_grouped_filtering')
    before = panel.height()
    panel.rail.chip('exporting').click()  # the user opens EXPORTING in the panel: six rows instead of five
    sizing_check('FILTERING + EXPORTING grouped, EXPORTING opened')
    check('sizing: the panel follows the rows of EXPORTING', panel.height() != before, f"{before} -> {panel.height()}")
    grab_window('sizing_05_grouped_exporting')
    panel.rail.chip('filtering').click()
    sizing_check('FILTERING + EXPORTING grouped, FILTERING opened again')
    return None


def s_sizing_under_layers():
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    layers = window.findChild(QDockWidget, 'Layers')
    panel = panels.panel('filtering')
    if layers is None or not layers.isVisible() or panel is None:
        report('SKIP', 'sizing: a panel moved under the Layers panel', f"layers={layers} panel={panel}")
        return None
    user_drop(panel, lambda: window.splitDockWidget(layers, panel, Qt.Orientation.Vertical))  # dropped under it
    pump(100)
    if panel in window.tabifiedDockWidgets(layers) or panel.isFloating() or window.dockWidgetArea(panel) != window.dockWidgetArea(layers):
        report('SKIP', 'sizing: a panel moved under the Layers panel', 'it became a tab or floats: not a column')
        return None
    sizing_check('FILTERING + EXPORTING moved under the Layers panel')
    grab_window('sizing_06_under_layers')
    return None


def s_sizing_back_to_dock():
    d = dock()
    panels = d._fm_panels
    sizing_reset()
    panels.detach('exploring')
    panels.detach('filtering')  # the dock opens EXPORTING: it keeps it alone
    sizing_check('EXPLORING and FILTERING out, the dock keeps EXPORTING', wanted_rigid=2)
    panels.attach('filtering')  # back, folded: the dock still shows EXPORTING
    sizing_check('FILTERING given back to the dock')
    grab_window('sizing_07_filtering_back')
    return None


def s_sizing_beside():
    """The panel of FILTERING put beside the dock that keeps EXPORTING: one row for both, at the height of the six
    rows of EXPORTING, FILTERING not cut."""
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    sizing_reset()
    panels.detach('exploring')
    panels.detach('filtering')
    panel = panels.panel('filtering')
    user_drop(panel, lambda: window.splitDockWidget(d, panel, Qt.Orientation.Horizontal))  # dropped beside it
    pump(100)
    if panel.isFloating() or panel in window.tabifiedDockWidgets(d) or abs(panel.y() - d.y()) > 2:
        report('SKIP', 'sizing: FILTERING beside the dock', f"floating={panel.isFloating()} y={panel.y()} dock={d.y()}")
        return None
    sizing_check('FILTERING beside the dock that keeps EXPORTING', wanted_rigid=2)
    grab_window('sizing_08_beside')
    return None


def sizing_heights():
    return [(name, holder.isFloating(), holder.width(), holder.height()) for name, holder in sizing_holders()]


def sizing_restart(float_dock):
    """As QGIS starting again: the dock placed, then the panels of the last time restored, at the sizes QGIS kept.
    Those sizes are the user's, chosen here: nothing may change them, now or a while later."""
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    module = importlib.import_module(f'{PACKAGE}.ui.layout.section_panels')
    sizing_reset()
    area = window.dockWidgetArea(d)
    panels.detach('filtering')
    pump(900)
    panel = panels.panel('filtering')
    if float_dock:
        d.setFloating(True)
        pump(300)
        d.resize(max(d.width(), 420), 400)  # lower than a floating panel starts: kept as QGIS kept it
        d.move(500, 120)
    else:
        total = d.height() + panel.height()
        window.resizeDocks([d, panel], [total - 420, 420], Qt.Orientation.Vertical)  # taller than its rows
    pump(900)
    before = sizing_heights()
    state = window.saveState()  # QGIS saves its window when it closes
    panels.attach_all(remember=False)  # the plugin unloads: its panels go, what was apart stays saved
    if d.isFloating():
        d.setFloating(False)
    iface.removeDockWidget(d)
    QApplication.processEvents()
    window.restoreState(state)  # QGIS starts again
    QSettings().setValue(module.DOCK_AREA_KEY, module._area_number(area))
    module.place_dock(d, iface, area)  # the plugin opens its dock: Qt says it moved
    d.show()
    pump(200)  # a dialog of the new version may hold the start here
    panels.restore()  # then the panels of the last time
    pump(1000)
    soon = sizing_heights()
    pump(2500)  # and once the start is over
    later = sizing_heights()
    close = all(abs(a[2] - b[2]) <= 2 and abs(a[3] - b[3]) <= 2 and a[:2] == b[:2]
                for a, b in zip(before, later)) and len(before) == len(later)
    kind = 'floating' if float_dock else 'docked'
    check(f"sizing: QGIS starting again, the dock {kind}: the sizes it kept stay, 1 s and 3.5 s later",
          close and [row[:2] for row in soon] == [row[:2] for row in before]
          and all(abs(a[3] - b[3]) <= 2 for a, b in zip(before, soon)), f"{before} -> {soon} -> {later}")
    grab_window(f"sizing_11_restart_{kind}")
    settles(sizing_armed, 8)
    if d.isFloating():
        d.setFloating(False)
    QSettings().remove(module.DOCK_AREA_KEY)


def s_sizing_restart_docked():
    sizing_restart(False)
    return None


def s_sizing_restart_floating():
    sizing_restart(True)
    return None


def s_sizing_open_chip_again():
    """A click on the chip already open, in a panel or in the dock, changes nothing: the size set by hand stays."""
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    sizing_reset()
    panels.detach('filtering')
    panels.group('exporting', 'filtering')
    panel = panels.panel('filtering')
    window.splitDockWidget(d, panel, Qt.Orientation.Vertical)  # below the dock, whatever place was kept for it
    panel.rail.chip('filtering').click()
    pump(900)
    if panel.isFloating() or len(sizing_column(panel)) < 2:
        report('SKIP', 'sizing: a click on the chip already open', f"the panel is not below the dock: {sizing_state()}")
        return None
    total = d.height() + panel.height()
    window.resizeDocks([d, panel], [total - panel.height() - 120, panel.height() + 120], Qt.Orientation.Vertical)
    pump(900)
    before = sizing_heights()
    check('sizing: the panel enlarged by hand is taller than its rows', sizing_empty(panel) > 60, sizing_state())
    panel.rail.chip('filtering').click()  # already open
    pump(900)
    after_panel = sizing_heights()
    d._fm_sections.top_rail.chip('exploring').click()  # already open in the dock
    pump(900)
    after_dock = sizing_heights()
    check('sizing: a click on the chip already open changes no size (panel, then dock)',
          before == after_panel == after_dock, f"{before} -> {after_panel} -> {after_dock}")
    return None


def s_sizing_elsewhere():
    """A rigid panel enlarged by hand in another column, and one floating, stay as they are when the structure
    changes elsewhere (AGENT opened in the dock)."""
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    layers = window.findChild(QDockWidget, 'Layers')
    if 'agent' not in d._fm_sections._headers or layers is None or not layers.isVisible():
        report('SKIP', 'sizing: a change elsewhere', 'no AGENT or no Layers panel')
        return None
    sizing_reset()
    # Each panel put where it goes at once: a place kept for it by an earlier step may be a tab, and the panels of
    # FilterMate tabbed together merge a turn of the loop later.
    panels.detach('filtering')
    window.splitDockWidget(layers, panels.panel('filtering'), Qt.Orientation.Vertical)
    panels.detach('exporting')
    panels.panel('exporting').setFloating(True)
    pump(900)
    filtering, exporting = panels.panel('filtering'), panels.panel('exporting')
    if filtering is None or exporting is None or filtering is exporting or filtering.isFloating() \
            or window.tabifiedDockWidgets(filtering):
        report('SKIP', 'sizing: a change elsewhere', f"the panels are not where they were put: {panels.groups()}")
        return None
    window.resizeDocks([layers, filtering], [layers.height() - 100, filtering.height() + 100], Qt.Orientation.Vertical)
    pump(900)
    exporting.resize(exporting.width(), exporting.height() + 150)
    pump(900)
    before = sizing_heights()
    d._fm_sections.top_rail.chip('agent').click()  # the user opens AGENT in the dock
    pump(900)
    after = sizing_heights()
    kept = [row for row in before if row[0] != 'dock']
    check('sizing: a change in the dock leaves a panel sized by hand in another column, and a floating one, as they are',
          kept == [row for row in after if row[0] != 'dock'], f"{before} -> {after}")
    grab_window('sizing_12_elsewhere')
    d._fm_sections.top_rail.chip('exploring').click()
    exporting.setFloating(False)
    pump(300)
    return None


def s_sizing_short_screen():
    """A short window: Layers and Browser above EXPLORING held to its minimum, FILTERING under them. The panels of
    QGIS give up height before the rows of FILTERING are cut."""
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    layers = window.findChild(QDockWidget, 'Layers')
    if layers is None or not layers.isVisible():
        report('SKIP', 'sizing: a short window', 'no Layers panel')
        return None
    sizing_reset()
    panels.detach('exploring')
    window.splitDockWidget(layers, panels.panel('exploring'), Qt.Orientation.Vertical)  # at once (see above)
    panels.detach('filtering')
    window.splitDockWidget(panels.panel('exploring'), panels.panel('filtering'), Qt.Orientation.Vertical)
    pump(900)
    exploring, filtering = panels.panel('exploring'), panels.panel('filtering')
    column = sizing_column(filtering) if filtering is not None else []
    if exploring is None or filtering is exploring or filtering.isFloating() or exploring.isFloating() \
            or len(column) < 3 or window.tabifiedDockWidgets(filtering):
        report('SKIP', 'sizing: a short window', f"column of {len(column)}")
        return None
    SIZING['window'] = (window.isMaximized(), window.geometry())
    need = filtering.height() - sizing_empty(filtering)
    floor = sum(max(w.minimumHeight(), w.minimumSizeHint().height()) for w in column if w is not filtering)
    room = sum(w.height() for w in column)
    wanted = floor + need + 30  # room enough when Layers and Browser give up theirs, not when they keep it
    window.showNormal()
    pump(300)
    window.resize(window.width(), window.height() - (room - wanted))
    pump(900)
    panels.resize_soon()  # a change of a setting: every column
    sizing_check('a short window, Layers above EXPLORING at its minimum')
    grab_window('sizing_13_short_window')
    maximized, geometry = SIZING['window']
    if maximized:
        window.showMaximized()
    else:
        window.setGeometry(geometry)
    pump(600)
    return None


def s_sizing_opened_by_code():
    """EXPORTING opened by the agent or a script in a panel that showed FILTERING: its six rows fit."""
    d = dock()
    panels = d._fm_panels
    sizing_reset()
    panels.detach('filtering')
    iface.mainWindow().splitDockWidget(d, panels.panel('filtering'), Qt.Orientation.Vertical)  # at once, below the dock
    panels.group('exporting', 'filtering')
    panels.panel('filtering').open('filtering')
    pump(900)
    panels.raise_panel('exporting')  # what the agent does
    sizing_check('EXPORTING opened by the code in the panel it shares with FILTERING')
    return None


def s_sizing_closed_by_cross():
    """EXPLORING above FILTERING under Layers, the dock elsewhere: FILTERING closed by the cross of its panel, its
    room goes to EXPLORING, Layers keeps its height."""
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    layers = window.findChild(QDockWidget, 'Layers')
    if layers is None or not layers.isVisible():
        report('SKIP', 'sizing: a panel closed by its cross', 'no Layers panel')
        return None
    sizing_reset()
    panels.detach('exploring')
    window.splitDockWidget(layers, panels.panel('exploring'), Qt.Orientation.Vertical)  # at once (see above)
    panels.detach('filtering')
    window.splitDockWidget(panels.panel('exploring'), panels.panel('filtering'), Qt.Orientation.Vertical)
    pump(1200)
    exploring, filtering = panels.panel('exploring'), panels.panel('filtering')
    if exploring is None or filtering is None or exploring is filtering or window.tabifiedDockWidgets(filtering) \
            or window.tabifiedDockWidgets(exploring) or filtering.isFloating() or exploring.isFloating():
        report('SKIP', 'sizing: a panel closed by its cross', f"not one column: {sizing_state()}")
        return None
    before = (layers.height(), exploring.height(), filtering.height())
    filtering.close()  # its cross
    pump(1200)
    after = (layers.height(), exploring.height())
    check('sizing: FILTERING closed by its cross, EXPLORING above it takes its room, Layers keeps its height',
          panels.panel('filtering') is None and abs(after[0] - before[0]) <= 4
          and after[1] >= before[1] + before[2] - 20, f"Layers, EXPLORING, FILTERING {before} -> {after}")
    grab_window('sizing_14_closed_by_cross')
    return None


def s_sizing_width_given_back():
    """FILTERING put beside the dock, both made wide enough for their rows; given back to the dock, the dock gets the
    width it had. Ten times: it never grows."""
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    sizing_reset()
    window.resizeDocks([d], [SIZING['dock_width']], Qt.Orientation.Horizontal)  # the width it had at the start
    pump(900)
    start = d.width()
    widths = []
    for _round in range(10):
        panels.detach('filtering')
        panel = panels.panel('filtering')
        user_drop(panel, lambda: window.splitDockWidget(d, panel, Qt.Orientation.Horizontal))  # dropped beside it
        pump(1200)
        beside = (d.width(), panel.width(), abs(panel.y() - d.y()) <= 2 and not panel.isFloating())
        panels.attach('filtering')
        pump(1200)
        widths.append((beside, d.width()))
        if _round == 0:
            check('sizing: FILTERING beside the dock then given back, the dock has its width again',
                  beside[2] and abs(d.width() - start) <= 6, f"start {start}, beside {beside}, after {d.width()}")
    check('sizing: ten times beside the dock and back, the dock never grows', abs(widths[-1][1] - start) <= 6
          and max(width for _beside, width in widths) <= start + 6, f"start {start}: {widths}")
    grab_window('sizing_15_width_given_back')
    return None


def s_sizing_behind_a_tab():
    """FILTERING behind the tab of Layers: Qt calls it visible and moves it out of the window. A pass measures it
    not, widens nothing for it: the group of tabs keeps its width and its height."""
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    layers = window.findChild(QDockWidget, 'Layers')
    if layers is None or not layers.isVisible():
        report('SKIP', 'sizing: a panel behind a tab', 'no Layers panel')
        return None
    sizing_reset()
    pump(600)
    before = (layers.width(), layers.height())  # before the panel joins its tabs: the pass then must not widen it
    panels.detach('filtering')
    panel = panels.panel('filtering')
    drop_as_tab(layers, panel)
    layers.raise_()
    pump(1200)
    if panel not in window.tabifiedDockWidgets(layers):
        report('SKIP', 'sizing: a panel behind a tab', 'not tabbed')
        return None
    tabbed = layers.height()
    panels.resize_soon()  # a change of a setting: every column
    pump(1200)
    after = (layers.width(), layers.height())
    check('sizing: FILTERING behind the tab of Layers is neither measured nor widened: the group keeps its width',
          after[0] == before[0], f"{before} -> {after}, the panel at {panel.geometry().getRect()} "
                                 f"needs {d.FILTERING.minimumSizeHint().width()} px")
    check('sizing: FILTERING behind the tab of Layers: the group keeps its height', abs(after[1] - tabbed) <= 2,
          f"{tabbed} -> {after[1]}")
    grab_window('sizing_16_behind_a_tab')
    return None


def s_sizing_whole_dock():
    """The dock in one piece, 300 px wide, narrower than the rows of FILTERING: a setting that sizes every panel
    again changes neither its size nor its place; floating, neither."""
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    sizing_reset()
    profile = config_value('APP.DOCKWIDGET.UI_PROFILE')
    apply_settings({'APP.DOCKWIDGET.UI_PROFILE': 'compact'})
    pump(1200)
    width = max(300, d.minimumSizeHint().width(), d.minimumWidth())
    window.resizeDocks([d], [width], Qt.Orientation.Horizontal)
    pump(900)
    before = d.geometry().getRect()
    print(f"   sizing | the dock in one piece, compact: {before}, rows cut on the right: {sizing_cut_in_width()}, "
          f"rows need {d.FILTERING.minimumSizeHint().width()} px", flush=True)
    for mode in ('fit' if SIZING['mode'] == 'fill' else 'fill', SIZING['mode']):  # there and back
        apply_settings({'APP.DOCKWIDGET.SECTION_HEIGHT': mode})
        pump(900)
    panels.resize_soon()  # what a change of UI_PROFILE asks for, once the profile has given its own sizes
    pump(1200)
    after = d.geometry().getRect()
    check('sizing: the dock in one piece keeps its size and place when the settings change', after == before,
          f"{before} -> {after} (rows need {d.FILTERING.minimumSizeHint().width()} px)")
    d.setFloating(True)  # floated, then sized again by every pass: none
    pump(600)
    d.resize(width, 520)
    d.move(1600 - width - 4, 300)
    pump(900)
    floating = d.geometry().getRect()
    panels.resize_soon()
    pump(1200)
    check('sizing: the dock in one piece, floating, keeps its size and place too', d.geometry().getRect() == floating,
          f"{floating} -> {d.geometry().getRect()}")
    grab_window('sizing_17_whole_dock')
    d.setFloating(False)
    pump(600)
    if config_value('APP.DOCKWIDGET.UI_PROFILE') != profile:
        apply_settings({'APP.DOCKWIDGET.UI_PROFILE': profile})
    window.resizeDocks([d], [SIZING['dock_width']], Qt.Orientation.Horizontal)
    pump(900)
    return None


def sizing_left_column(names):
    """EXPLORING and / or FILTERING out, under Layers in the left area, each put there at once (see above). The
    panels, or None when they are not one column under Layers."""
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    layers = window.findChild(QDockWidget, 'Layers')
    if layers is None or not layers.isVisible():
        return None
    above = layers
    for key in names:
        panels.detach(key)
        window.splitDockWidget(above, panels.panel(key), Qt.Orientation.Vertical)
        above = panels.panel(key)
    pump(1200)
    found = [panels.panel(key) for key in names]
    if any(panel is None or panel.isFloating() or window.tabifiedDockWidgets(panel) for panel in found) \
            or len(set(found)) != len(found) or window.dockWidgetArea(found[-1]) != window.dockWidgetArea(layers):
        return None
    return found


def s_sizing_separator_dragged():
    """F1: Layers beside the dock in the right area. The user drags the edge of the area (no change of structure),
    then FILTERING goes and comes back: the width the user set stays, nothing is given back over it."""
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    layers = window.findChild(QDockWidget, 'Layers')
    if layers is None or not layers.isVisible():
        report('SKIP', 'sizing: the edge of an area dragged by the user', 'no Layers panel')
        return None
    SIZING['layers_state'] = window.saveState()
    sizing_reset()
    window.splitDockWidget(d, layers, Qt.Orientation.Horizontal)  # Layers beside the dock, the same top
    pump(900)
    panels.detach('filtering')
    # Below the dock, at once: a place kept beside it by an earlier step would give its width back to the dock (Qt)
    window.splitDockWidget(d, panels.panel('filtering'), Qt.Orientation.Vertical)
    pump(1200)
    window.resizeDocks([d], [d.width() + 150], Qt.Orientation.Horizontal)  # the user drags the edge of the area
    pump(600)
    dragged = (d.width(), layers.width())
    panels.resize_soon()  # an ordinary pass (a setting changed): not a change of structure
    pump(900)
    panels.attach('filtering')
    pump(1200)
    after = (d.width(), layers.width())
    check('sizing: the edge of an area dragged by the user, then a panel back in the dock: the width the user set stays',
          abs(after[0] - dragged[0]) <= 6 and abs(after[1] - dragged[1]) <= 6, f"{dragged} -> {after}")
    window.restoreState(SIZING['layers_state'])
    pump(600)
    return None


def s_sizing_dragged_away():
    """F2: Layers above EXPLORING and FILTERING in the left area; FILTERING dragged away (floated by a double click
    on its title): EXPLORING takes its room, Layers keeps its height."""
    window = iface.mainWindow()
    layers = window.findChild(QDockWidget, 'Layers')
    sizing_reset()
    found = sizing_left_column(['exploring', 'filtering'])
    if found is None:
        report('SKIP', 'sizing: a panel dragged out of its column', sizing_state())
        return None
    exploring, filtering = found
    before = (layers.height(), exploring.height(), filtering.height())
    user_drop(filtering, lambda: filtering.setFloating(True))
    pump(1500)
    after = (layers.height(), exploring.height())
    check('sizing: FILTERING dragged out of its column, EXPLORING takes its room, Layers keeps its height',
          abs(after[0] - before[0]) <= 4 and after[1] >= before[1] + before[2] - 20,
          f"Layers, EXPLORING, FILTERING {before} -> {after}")
    filtering.setFloating(False)
    pump(600)
    grab_window('sizing_19_dragged_away')
    return None


def s_sizing_beside_then_below():
    """F3: FILTERING dropped beside the dock (the area grows), then below it in the same area: the area has its
    width back."""
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    sizing_reset()
    window.resizeDocks([d], [SIZING['dock_width']], Qt.Orientation.Horizontal)
    pump(900)
    start = d.width()
    panels.detach('filtering')
    panel = panels.panel('filtering')
    user_drop(panel, lambda: window.splitDockWidget(d, panel, Qt.Orientation.Horizontal))
    pump(1200)
    beside = (d.width(), panel.width(), abs(panel.y() - d.y()) <= 2)
    user_drop(panel, lambda: window.splitDockWidget(d, panel, Qt.Orientation.Vertical))
    pump(1500)
    below = panel.y() > d.y() + 10 and abs(panel.x() - d.x()) <= 2
    check('sizing: FILTERING beside the dock, then dropped below it: the area has its width back',
          beside[2] and below and abs(d.width() - start) <= 6, f"start {start}, beside {beside}, below {below}: "
                                                              f"{d.width()} px")
    grab_window('sizing_20_beside_then_below')
    return None


def s_sizing_manual_between():
    """F4: PANEL_SIZING manual, FILTERING closed by its cross meanwhile, then auto again: nothing noted under manual
    is applied (Layers keeps the height it has)."""
    window = iface.mainWindow()
    layers = window.findChild(QDockWidget, 'Layers')
    if not SIZING['auto']:
        report('SKIP', 'sizing: manual, a panel closed, auto again', 'no such setting in this version')
        return None
    sizing_reset()
    found = sizing_left_column(['exploring', 'filtering'])
    if found is None:
        report('SKIP', 'sizing: manual, a panel closed, auto again', sizing_state())
        return None
    exploring, filtering = found
    apply_settings({'APP.DOCKWIDGET.PANEL_SIZING': 'manual'})
    pump(600)
    filtering.close()  # its cross, under manual
    pump(1200)
    window.resizeDocks([layers, exploring], [layers.height() + 60, exploring.height() - 60], Qt.Orientation.Vertical)
    pump(600)
    kept = layers.height()
    apply_settings({'APP.DOCKWIDGET.PANEL_SIZING': 'auto'})  # sized again at once, from what is there now
    pump(1200)
    check('sizing: manual, a panel closed meanwhile, then auto: no height noted under manual comes back',
          abs(layers.height() - kept) <= 4, f"Layers {kept} -> {layers.height()}")
    return None


def s_sizing_floating():
    d = dock()
    panels = d._fm_panels
    sizing_reset()
    panels.detach('filtering')
    panel = panels.panel('filtering')
    panel.setFloating(True)
    sizing_check('FILTERING floating')
    grab_window('sizing_09_floating')
    grab_widget(panel, 'sizing_09_floating_panel')
    panel.setFloating(False)
    pump(300)
    return None


def s_sizing_manual():
    d = dock()
    panels = d._fm_panels
    if not SIZING['auto']:
        report('SKIP', 'sizing: PANEL_SIZING = manual', 'no such setting in this version')
        return None
    sizing_reset()
    apply_settings({'APP.DOCKWIDGET.PANEL_SIZING': 'manual'})
    panels.detach('filtering')
    panels.group('exporting', 'filtering')
    panel = panels.panel('filtering')
    panel.rail.chip('filtering').click()
    QApplication.processEvents()
    before = [(name, holder.height()) for name, holder in sizing_holders()]
    panel.rail.chip('exporting').click()
    pump(900)
    after = [(name, holder.height()) for name, holder in sizing_holders()]
    check('sizing: PANEL_SIZING = manual, nothing is resized when another section opens', before == after,
          f"{before} -> {after}")
    grab_window('sizing_05b_manual')
    panel.rail.chip('filtering').click()
    apply_settings({'APP.DOCKWIDGET.PANEL_SIZING': 'auto'})  # applied at once: sized again
    sizing_check('PANEL_SIZING back to auto')
    return None


def s_sizing_probe():
    """FM_STEPS=s_sizing_probe: the numbers behind the pass, printed (not a check)."""
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    sizing_reset()
    panels.detach('filtering')
    pump(900)
    every = window.findChildren(QDockWidget)
    direct = window.findChildren(QDockWidget, '', Qt.FindChildOption.FindDirectChildrenOnly)
    print(f"   probe | docks {len(every)} direct {len(direct)} | visible "
          f"{[(w.objectName(), w.geometry().getRect(), window.dockWidgetArea(w)) for w in every if w.isVisible()]}", flush=True)
    for name, holder in sizing_holders():
        page = sizing_rigid_page(holder)
        info = ''
        if page is not None:
            viewport = page.parentWidget()
            info = (f"viewport {viewport.height()} page {page.height()} hint {page.sizeHint().height()} "
                    f"minhint {page.minimumSizeHint().height()} min {page.minimumHeight()} max {page.maximumHeight()} "
                    f"policy {page.sizePolicy().verticalPolicy()}")
        try:
            measure = panels._measure(holder)
            column = [w.objectName() for w in panels._column(window, holder)]
        except Exception as exc:
            measure, column = repr(exc), []
        print(f"   probe | {name} h {holder.height()} min {holder.minimumHeight()}/{holder.minimumSizeHint().height()} "
              f"parent {holder.parent().objectName() if holder.parent() else None} measure {measure} column {column} {info}",
              flush=True)
    return None


def s_sizing_alone():
    """FILTERING alone in its column, beside the dock that keeps EXPLORING (elastic): nothing can take the rest, the
    panel keeps the whole column. Rows spread (fill): no band under the last one; one gap apart (fit): at the top."""
    d = dock()
    panels = d._fm_panels
    window = iface.mainWindow()
    sizing_reset()
    panels.detach('filtering')
    panel = panels.panel('filtering')
    window.splitDockWidget(d, panel, Qt.Orientation.Horizontal)  # at once: beside the dock, a column of its own
    pump(1200)
    if panel.isFloating() or window.tabifiedDockWidgets(panel) or abs(panel.y() - d.y()) > 2:
        report('SKIP', 'sizing: FILTERING alone in its column', sizing_state())
        return None
    page = d.FILTERING
    viewport = page.parentWidget()
    last = max(widget.mapTo(page, QPoint(0, widget.height())).y()
               for widget in (getattr(d, name) for _key, name in mockup_module().FILTERING_PAIRS) if widget.isVisible())
    band = page.height() - last
    if SIZING['mode'] == 'fill':
        check('sizing: FILTERING alone in its column (fill): the whole column, its rows spread, no band under them',
              abs(panel.height() - d.height()) <= 2 and abs(viewport.height() - page.height()) <= 2 and band <= 16,
              f"panel {panel.height()} dock {d.height()} viewport {viewport.height()} page {page.height()} band {band}")
    else:
        check('sizing: FILTERING alone in its column (fit): the whole column, its rows at the top',
              abs(panel.height() - d.height()) <= 2 and page.height() == page.sizeHint().height(),
              f"panel {panel.height()} dock {d.height()} page {page.height()}/{page.sizeHint().height()}")
    grab_window('sizing_18_alone')
    return None


def s_sizing_end():
    d = dock()
    sizing_reset()
    window = iface.mainWindow()
    window.restoreState(SIZING['state'])
    share, saved, sizes = SIZING['share']
    d._fm_sections._share = share
    if saved is None:
        QSettings().remove('FilterMate/splitter_top_share')
    else:
        QSettings().setValue('FilterMate/splitter_top_share', saved)
    if SIZING.get('height') and config_value('APP.DOCKWIDGET.SECTION_HEIGHT') != SIZING['height']:
        apply_settings({'APP.DOCKWIDGET.SECTION_HEIGHT': SIZING['height']})
    d.show()
    d.raise_()
    open_section(d.FILTERING)
    QApplication.processEvents()
    d.main_splitter.setSizes(sizes)
    for scenario, name, height, empty, note in SIZING['rows']:
        print(f"   sizing | {scenario:<55} | {name:<28} | {height:>4} px | {empty:>4} px under the rows {note}", flush=True)
    check('sizing: left as found', d._fm_panels.detached() == () and d.toolBox_tabTools.currentWidget() is d.FILTERING
          and d.isVisible(), str(d._fm_panels.detached()))
    return settled()


# The manual step before those that leave places kept for the panel of FILTERING elsewhere (under Layers, beside).
SIZING_STEPS = [s_section_setup, s_vector_source, s_sizing_setup, s_sizing_filtering_below, s_sizing_exploring,
                s_sizing_every_section, s_sizing_grouped, s_sizing_manual, s_sizing_under_layers, s_sizing_back_to_dock,
                s_sizing_beside, s_sizing_floating, s_sizing_open_chip_again, s_sizing_elsewhere, s_sizing_opened_by_code,
                s_sizing_short_screen, s_sizing_closed_by_cross, s_sizing_width_given_back, s_sizing_behind_a_tab,
                s_sizing_whole_dock, s_sizing_alone, s_sizing_separator_dragged, s_sizing_dragged_away,
                s_sizing_beside_then_below, s_sizing_manual_between, s_sizing_restart_docked, s_sizing_restart_floating,
                s_sizing_end]


# --- the two stacks and the rows as 5.1.1 laid them out (FM_ONLY=like511) ---------------------------------------------
#
# 19 November 2026, the user after trying the dock of main: "I want it as before, in 5.1.1". The rows of FILTERING
# and EXPORTING spread over the height of their section again by default (SECTION_HEIGHT = fill), and the two stacks
# share the dock as 5.1.1 shares it. These steps go through the dock as a user does (the three kinds of layer, real
# drags of the handle: a press, moves with the button held, a release; a window made shorter and taller) and compare
# what they measure with what the same steps measured on the tag v5.1.1 (LIKE511, one entry per room the two stacks
# have, which depends on the image of QGIS). FM_LIKE_MEASURE=1 prints the measures instead, to write that table.

LIKE = {}
LIKE_KEY = 'FilterMate/splitter_top_share'  # where the user left the handle (dock_chrome.py)
# Measured on v5.1.1 (d43f9064), 19 November 2026, by these steps with FM_LIKE_MEASURE=1. The key: the room the
# two stacks share when the dock opens in a 1600 x 1000 window.
LIKE511 = {
    733: {  # QGIS 3.44 (LTR), a dock 834 px high
        'start zones': [246, 487], 'filtering rows': [445, 0, 108, 216, 315, 415], 'exporting': [246, 487],
        'exporting rows': [445, 0, 85, 167, 250, 332, 415], 'start dem': [246, 487], 'start cloud': [246, 487],
        'zones again': [246, 487], 'handle up': [122, 611], 'handle down': [583, 150], 'handle middle': [366, 367],
        'filtering rows middle': [325, 0, 78, 156, 225, 295], 'next section': [358, 375],
        'window short': [166, 367], 'window tall': [458, 475], 'window back': [266, 467],
        'handle third': [219, 514], 'third short': [122, 211], 'third tall': [268, 665], 'third back': [122, 611],
        'folded profile': [583, 150], 'folded profile dragged': [116, 0]},
    735: {  # QGIS 4.3 (latest, Qt6)
        'start zones': [247, 488], 'filtering rows': [446, 0, 108, 216, 316, 416], 'exporting': [247, 488],
        'exporting rows': [446, 0, 85, 168, 250, 333, 416], 'start dem': [247, 488], 'start cloud': [247, 488],
        'zones again': [247, 488], 'handle up': [122, 613], 'handle down': [585, 150], 'handle middle': [367, 368],
        'filtering rows middle': [326, 0, 78, 156, 226, 296], 'next section': [359, 376],
        'window short': [167, 368], 'window tall': [459, 476], 'window back': [267, 468],
        'handle third': [220, 515], 'third short': [122, 213], 'third tall': [269, 666], 'third back': [122, 613],
        'folded profile': [585, 150], 'folded profile dragged': [116, 0]},
    729: {  # QGIS 3.22, which has no point cloud
        'start zones': [245, 484], 'filtering rows': [442, 0, 107, 214, 313, 412], 'exporting': [245, 484],
        'exporting rows': [442, 0, 84, 166, 248, 330, 412], 'start dem': [245, 484],
        'zones again': [245, 484], 'handle up': [122, 607], 'handle down': [579, 150], 'handle middle': [364, 365],
        'filtering rows middle': [323, 0, 77, 155, 224, 293], 'next section': [356, 373],
        'window short': [164, 365], 'window tall': [456, 473], 'window back': [264, 465],
        'handle third': [218, 511], 'third short': [122, 207], 'third tall': [267, 662], 'third back': [122, 607],
        'folded profile': [579, 150], 'folded profile dragged': [116, 0]},
}
# The same rooms, the dock opened with the handle a session before left at 0.5421 of the two stacks (FM_SHARE).
LIKE511_LEFT = {733: [390, 343], 735: [391, 344], 729: [388, 341]}
# The rows are where 5.1.1 put them within these pixels. Since 5.1.1 the values column keeps a margin above its
# first row and under its last one so their key buttons, taller than the rows, sit in front of them (#549): the
# last row ends 3 px higher, the first one of EXPORTING starts 2 px lower, the rows between follow.
LIKE_ROWS = 3


def drag_handle(by):
    """The handle between the stacks dragged ``by`` pixels down (up when negative), as a mouse does: a press, moves
    with the left button held, a release, sent to the handle (``setSizes`` does not go through ``moveSplitter``:
    the dock keeps nothing of it)."""
    handle = dock().main_splitter.handle(1)
    origin = handle.mapToGlobal(handle.rect().center())

    def send(kind, shift, button, buttons):
        at = origin + QPoint(0, shift)
        QApplication.sendEvent(handle, QMouseEvent(kind, QPointF(handle.mapFromGlobal(at)), QPointF(at), button,
                                                   buttons, Qt.KeyboardModifier.NoModifier))
        QApplication.processEvents()
    left, none = Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton
    send(QEvent.Type.MouseButtonPress, 0, left, left)
    for step in range(1, 5):
        send(QEvent.Type.MouseMove, by * step // 4, none, left)
    send(QEvent.Type.MouseButtonRelease, by, left, none)
    pump(150)


def drag_handle_to(top):
    """A real drag that leaves the upper stack ``top`` pixels high."""
    drag_handle(top - dock().main_splitter.sizes()[0])


def resize_window(height):
    """The window of QGIS ``height`` pixels high, the dock with it."""
    window = iface.mainWindow()
    window.resize(window.width(), height)
    pump(400)


def stack_least(index):
    """The height the splitter never takes a stack under, as Qt reads it: its minimum height when it has one, else
    the smallest its layout says."""
    stack = dock().main_splitter.widget(index)
    return stack.minimumHeight() or stack.minimumSizeHint().height()


def rows_place(section):
    """Where the rows of ``section`` are in their page: ``[page height, top of each row shown...]``."""
    d = dock()
    page = getattr(d, section.upper())
    values = getattr(d, f'verticalLayout_{section}_values')
    origin = values.parentWidget().mapTo(page, QPoint(0, 0)).y()
    return [page.height()] + [origin + values.itemAt(i).geometry().top() for i in range(values.count())
                              if values.itemAt(i).spacerItem() is None and not values.itemAt(i).isEmpty()]


def like_text():
    d = dock()
    lower = d.main_splitter.widget(1)
    return (f"dock={d.height()} sizes={d.main_splitter.sizes()} left at={d._fm_sections._share} least="
            f"{[stack_least(0), stack_least(1)]} lower limits={[lower.minimumHeight(), lower.maximumHeight()]}")


def like_note(key, value=None):
    """``key`` measured: the sizes of the two stacks, or ``value``."""
    LIKE['now'][key] = list(dock().main_splitter.sizes()) if value is None else value
    print(f"   like511: {key} = {LIKE['now'][key]} | {like_text()}", flush=True)


def s_like_start():
    """As the dock opens, a vector layer current: the two stacks, the rows of FILTERING."""
    d = dock()
    leave_welcome()
    pump(400)
    LIKE['now'] = {}
    LIKE['left at'] = (d._fm_sections._share, QSettings().value(LIKE_KEY))
    LIKE['window'] = iface.mainWindow().height()
    LIKE['height'] = d.property('fm_section_height')
    LIKE['room'] = sum(d.main_splitter.sizes())
    like_note('start zones')
    like_note('filtering rows', rows_place('filtering'))
    print(f"   like511: {rows_text('filtering')}", flush=True)
    grab('like_start_zones')
    open_section(d.EXPORTING)
    return waits(0.6)


def s_like_exporting():
    d = dock()
    like_note('exporting')
    like_note('exporting rows', rows_place('exporting'))
    print(f"   like511: {rows_text('exporting')}", flush=True)
    grab('like_exporting')
    open_section(d.FILTERING)
    pump(300)
    d.comboBox_filtering_current_layer.setLayer(layer('dem'))
    return switched_to('dem', coverage_page=True)


def s_like_raster():
    d = dock()
    like_note('start dem')
    grab('like_start_dem')
    if layer('cloud') is None:
        return None
    d.comboBox_filtering_current_layer.setLayer(layer('cloud'))
    return switched_to('cloud', coverage_page=True)


def s_like_cloud():
    d = dock()
    if layer('cloud') is not None:
        like_note('start cloud')
        grab('like_start_cloud')
    d.comboBox_filtering_current_layer.setLayer(layer('zones'))
    return switched_to('zones', coverage_page=False)


def s_like_handle():
    """Real drags of the handle: to each end of its course, to the middle, then another section opened."""
    d = dock()
    room = LIKE['room']
    like_note('zones again')
    drag_handle_to(stack_least(0))
    drag_handle(-10)  # further up: held (a collapsible stack folds only past half of its minimum)
    like_note('handle up')
    grab('like_handle_up')
    drag_handle_to(room - stack_least(1))
    drag_handle(10)
    like_note('handle down')
    grab('like_handle_down')
    drag_handle_to(room // 2)
    like_note('handle middle')
    like_note('filtering rows middle', rows_place('filtering'))
    grab('like_handle_middle')
    open_section(d.EXPORTING)
    pump(300)
    open_section(d.FILTERING)
    pump(300)
    like_note('next section')
    drag_handle_to(room // 2)
    return None


def s_like_window():
    """A window 200 px shorter, 200 px taller, then as before: the handle in the middle, then 30 % of the way down."""
    room, window = LIKE['room'], LIKE['window']
    for label, height in (('window short', window - 200), ('window tall', window + 200), ('window back', window)):
        resize_window(height)
        like_note(label)
        if height != window:
            grab(f"like_{label.replace(' ', '_')}")
    drag_handle_to(room * 3 // 10)
    like_note('handle third')
    for label, height in (('third short', window - 400), ('third tall', window + 200), ('third back', window)):
        resize_window(height)
        like_note(label)
    drag_handle_to(room // 2)
    return None


def s_like_folded():
    """A display profile applied while nothing is open below, then the profile of before (the 150 px defect)."""
    LIKE['profile'] = config_value('APP.DOCKWIDGET.UI_PROFILE')
    open_section(None)
    pump(200)
    ui_config = importlib.import_module(f'{PACKAGE}.ui.config').UIConfig
    apply_settings({'APP.DOCKWIDGET.UI_PROFILE': 'normal' if ui_config.get_profile().name == 'COMPACT' else 'compact'})
    return waits(0.8)


def s_like_folded_back():
    apply_settings({'APP.DOCKWIDGET.UI_PROFILE': LIKE['profile']})
    return waits(0.8)


def s_like_folded_open():
    d = dock()
    open_section(d.FILTERING)
    pump(400)
    like_note('folded profile')
    before = d.main_splitter.sizes()
    drag_handle(-40)
    like_note('folded profile dragged', [after - start for start, after in zip(before, d.main_splitter.sizes())])
    return None


def like_compare(now, then):
    """``now`` against ``then``, what 5.1.1 measured: the two stacks to the pixel, the rows within LIKE_ROWS px.
    Not ``next section`` nor ``folded profile``, two defects of 5.1.1 fixed since: there the handle is expected
    where the user left it."""
    def same(keys, tolerance=1):
        off = {key: (then[key], now.get(key)) for key in keys if key in then and (
            now.get(key) is None or len(now[key]) != len(then[key])
            or any(abs(a - b) > tolerance for a, b in zip(now[key], then[key])))}
        return not off, ', '.join(f"{key}: 5.1.1 {was}, now {is_}" for key, (was, is_) in off.items()) or str(
            {key: now.get(key) for key in keys if key in then})

    check('like511: the rows of FILTERING and EXPORTING are spread by default, as in 5.1.1', LIKE['height'] == 'fill',
          str(LIKE['height']))
    for name, keys, tolerance in (
            ('as the dock opens, the two stacks as in 5.1.1: a vector layer, a raster, a point cloud, EXPORTING',
             ('start zones', 'exporting', 'start dem', 'start cloud', 'zones again'), 1),
            ('the handle dragged to each end of its course and to the middle stops where it did in 5.1.1',
             ('handle up', 'handle down', 'handle middle'), 1),
            ('a window 200 px shorter, 200 px taller, then as before: the two stacks as in 5.1.1',
             ('window short', 'window tall', 'window back'), 1),
            ('the same with the handle 30 % of the way down, in a window too short for it',
             ('handle third', 'third short', 'third tall', 'third back'), 1),
            ('the rows of FILTERING where 5.1.1 put them, as the dock opens and with the handle in the middle',
             ('filtering rows', 'filtering rows middle'), LIKE_ROWS),
            ('the rows of EXPORTING where 5.1.1 put them', ('exporting rows',), LIKE_ROWS)):
        passed, detail = same(keys, tolerance)
        check(f"like511: {name}", passed, detail)
    check('like511: another section opened, the handle is where the user left it (5.1.1: 8 px higher)',
          now['next section'] == now['handle middle'],
          f"left at {now['handle middle']}, then {now['next section']} (5.1.1: {then['next section']})")
    check('like511: a display profile applied with nothing open below, FILTERING opens where the handle was left '
          'and the handle still enlarges it (5.1.1: a stack 150 px high, held)',
          now['folded profile'] == now['handle middle'] and now['folded profile dragged'] == [-40, 40],
          f"{now['folded profile']}, dragged 40 px up {now['folded profile dragged']} (5.1.1: "
          f"{then['folded profile']}, {then['folded profile dragged']})")


def s_like_end():
    """What was measured against 5.1.1, then the dock as it was found."""
    d = dock()
    sections = d._fm_sections
    now, room = LIKE['now'], LIKE['room']
    if os.environ.get('FM_LIKE_MEASURE'):
        print(f"LIKE511 {room}: {now!r},", flush=True)
    elif room not in LIKE511:
        report('SKIP', 'like511: the two stacks and the rows as 5.1.1 laid them out',
               f"no measure of 5.1.1 for a room of {room} px (QGIS {Qgis.QGIS_VERSION}): run these steps on the tag "
               f"v5.1.1 with FM_LIKE_MEASURE=1 and add it to LIKE511")
    else:
        like_compare(now, LIKE511[room])
    sections._share, kept = LIKE['left at']
    sections._left = None
    if kept is None:
        QSettings().remove(LIKE_KEY)
    else:
        QSettings().setValue(LIKE_KEY, kept)
    sections.dimensions_applied()
    return waits(0.4)


def s_like_startup_check():
    """The dock opened with the handle a session before left at FM_SHARE of the two stacks (QSettings)."""
    d = dock()
    share = float(os.environ.get('FM_SHARE', '0.5421'))
    leave_welcome()
    pump(400)
    sizes = d.main_splitter.sizes()
    room = sum(sizes)
    print(f"   like511: opened with the handle left at {share}, {like_text()}", flush=True)
    grab('like_startup_left')
    if os.environ.get('FM_LIKE_MEASURE'):
        print(f"LIKE511_LEFT {room}: {sizes!r},", flush=True)
    elif share != 0.5421 or room not in LIKE511_LEFT:
        report('SKIP', 'like511: the dock opened with a handle left before, as 5.1.1 opens it',
               f"no measure of 5.1.1 for a room of {room} px and a share of {share}")
    else:
        check('like511: opened with the handle a session before left at 0.5421, the two stacks as 5.1.1 opens them',
              all(abs(a - b) <= 1 for a, b in zip(sizes, LIKE511_LEFT[room])) and abs(d._fm_sections._share - share)
              < 0.0001, f"5.1.1 {LIKE511_LEFT[room]}, now {sizes}")
    check('like511: nothing was written over the share the user left',
          abs(float(QSettings().value(LIKE_KEY, -1.0)) - share) < 0.0001, str(QSettings().value(LIKE_KEY)))
    return None


LIKE_STEPS = [s_section_setup, s_vector_source, s_like_start, s_like_exporting, s_like_raster, s_like_cloud,
              s_like_handle, s_like_window, s_like_folded, s_like_folded_back, s_like_folded_open, s_like_end]


# --- the tools of the EXPLORING rail, chosen for each kind of layer (APP.DOCKWIDGET.EXPLORING_TOOLS, FM_ONLY=tools) -----

TOOLS = {}
TOOLS_HIDDEN = {'vector': 'zoom, follow', 'raster': 'pipette, preview', 'point_cloud': 'identify, value_pipette'}
TOOLS_PATH = 'APP.DOCKWIDGET.EXPLORING_TOOLS.{}_hidden'


def tools_module():
    return importlib.import_module(f'{PACKAGE}.core.domain.exploring_tools')


def tools_buttons():
    return importlib.import_module(f'{PACKAGE}.ui.controllers.exploring_tool_choice').BUTTONS


def tools_rail(kind):
    """The rail as the user sees it for ``kind``: the names of the buttons shown (top to bottom), a problem if any."""
    d = dock()
    rail = d.widget_exploring_keys
    names = {name: key for key, name in tools_buttons()[kind].items()}
    shown = sorted((button for button in rail.findChildren(QPushButton) if button.isVisibleTo(rail)
                    and button.objectName() != 'pushButton_exploring_stream_copy'),  # of a web service, any kind
                   key=lambda button: button.y())
    keys = [names.get(button.objectName(), button.objectName()) for button in shown]
    problems = []
    if any(button.objectName() not in names for button in shown):
        problems.append('a button of another kind is shown')
    if not all(upper.geometry().bottom() < lower.geometry().top() for upper, lower in zip(shown, shown[1:])):
        problems.append('buttons overlap')
    if rail_scroll_maximum() == 0 and not all(0 <= button.geometry().top() and button.geometry().bottom() < rail.height()
                                              for button in shown):
        problems.append('a button is cut')
    gaps = [lower.geometry().top() - upper.geometry().bottom() for upper, lower in zip(shown, shown[1:])]
    if gaps and max(gaps) - min(gaps) > 2:
        problems.append(f'uneven gaps {gaps}')
    return keys, problems


def tools_expected(kind, hidden=None):
    module = tools_module()
    return list(module.shown_for(kind, TOOLS_HIDDEN[kind] if hidden is None else hidden))


def tools_rail_is(kind, hidden=None):
    keys, problems = tools_rail(kind)
    return keys == tools_expected(kind, hidden) and not problems


def tools_check(kind, label, hidden=None):
    ok = settles(lambda: tools_rail_is(kind, hidden), 3.0)
    keys, problems = tools_rail(kind)
    check(f'tools: the {label} rail shows its buttons but those hidden, in place, none cut', ok,
          f"shown={keys} expected={tools_expected(kind, hidden)} {problems}")


def tools_pick(name, coverage_page):
    dock().comboBox_filtering_current_layer.setLayer(layer(name))
    return switched_to(name, coverage_page)


def s_tools_begin():
    d = dock()
    leave_welcome()
    d._fm_sections.open_top('exploring')
    current = d.comboBox_filtering_current_layer.currentLayer()
    TOOLS.update(layer=current.name() if current else 'zones', saved={kind: config_value(TOOLS_PATH.format(kind))
                                                                        for kind in TOOLS_HIDDEN})
    check('tools: nothing is hidden by default, every kind keeps all of its buttons',
          all(value == '' for value in TOOLS['saved'].values()), str(TOOLS['saved']))
    apply_settings({TOOLS_PATH.format(kind): text for kind, text in TOOLS_HIDDEN.items()})
    return tools_pick('zones', coverage_page=False)


def s_tools_vector_check():
    tools_check('vector', 'vector')
    grab('tools_vector')
    keys, _problems = tools_rail('vector')
    check('tools: a tool hidden for vector layers stays on the raster rail and the other way round',
          'zoom' not in keys and 'follow' not in keys and 'more' in keys, str(keys))
    return tools_pick('dem', coverage_page=True)


def s_tools_raster_check():
    tools_check('raster', 'raster')
    grab('tools_raster')
    zoom = dock().pushButton_exploring_zoom
    check('tools: zoom hidden for vector layers is shown on a raster (one choice per kind)',
          zoom.isVisibleTo(dock().widget_exploring_keys))
    if not has_point_clouds():
        report('SKIP', 'tools: the point cloud rail', f"QGIS {Qgis.QGIS_VERSION} < 3.26 (FilterMate gate)")
        return tools_pick('zones', coverage_page=False)
    return tools_pick('cloud', coverage_page=True)


def s_tools_cloud_check():
    if has_point_clouds():
        tools_check('point_cloud', 'point cloud')
        grab('tools_point_cloud')
    return tools_pick('zones', coverage_page=False)


def tools_on_map():
    """The map tool of QGIS is one of the pickers of FilterMate (the pixel picker of a raster, the picker of a cloud)."""
    ctrl = coverage()
    tool = iface.mapCanvas().mapTool()
    return tool is not None and tool in (ctrl._pixel_tool, ctrl._class_tool)


def s_tools_groups_begin():
    """A tool whose button is hidden is not put on the map by choosing its group (the group stays the active one)."""
    apply_settings({TOOLS_PATH.format('raster'): 'pipette, detector, similar',
                    TOOLS_PATH.format('point_cloud'): 'identify, value_pipette, object'})
    return tools_pick('dem', coverage_page=True)


def s_tools_groups_raster():
    ctrl = coverage()
    iface.mapCanvas().unsetMapTool(iface.mapCanvas().mapTool()) if iface.mapCanvas().mapTool() else None
    ctrl._on_raster_mode_chosen('pipette')  # the click on the PIPETTE group
    pump(200)
    armed = ctrl._color_pick or tools_on_map()
    check('tools: the PIPETTE group chosen puts no tool on the map when its three buttons are hidden',
          not armed and ctrl._raster_panel.isVisible(), f"color_pick={ctrl._color_pick} on map={tools_on_map()}")
    apply_settings({TOOLS_PATH.format('raster'): 'pipette, detector'})  # one button kept: the tool is armed, on a button
    ctrl._on_raster_mode_chosen('pipette')
    pump(200)
    shown = [button for button in dock().widget_exploring_keys.findChildren(QPushButton)
             if button.isVisibleTo(dock().widget_exploring_keys) and button.isChecked()]
    check('tools: with one pipette button kept the group arms the tool, shown down on that button',
          ctrl._color_pick and tools_on_map() and [b.objectName() for b in shown] ==
          ['pushButton_checkable_exploring_raster_similar'], f"checked={[b.objectName() for b in shown]}")
    ctrl._on_color_pick_toggled(False)
    pump(100)
    apply_settings({TOOLS_PATH.format('raster'): ''})
    if not has_point_clouds():
        return tools_pick('zones', coverage_page=False)
    return tools_pick('cloud', coverage_page=True)


def s_tools_groups_cloud():
    if has_point_clouds():
        ctrl = coverage()
        for group in ('classes', 'ranges'):
            ctrl._on_point_cloud_group_chosen(group)
            pump(200)
            check(f'tools: the {group} group chosen puts no picker on the map when its pipette button is hidden',
                  not tools_on_map(), f"on map={tools_on_map()}")
        apply_settings({TOOLS_PATH.format('point_cloud'): 'value_pipette, object'})
        ctrl._on_point_cloud_group_chosen('classes')
        pump(200)
        check('tools: the classes group arms the class pipette again once its button is shown', tools_on_map()
              and dock().pushButton_exploring_identify.isVisibleTo(dock().widget_exploring_keys), f"on map={tools_on_map()}")
        ctrl._on_class_pick_toggled(False)
        pump(100)
        apply_settings({TOOLS_PATH.format('point_cloud'): ''})
    return tools_pick('zones', coverage_page=False)


def s_tools_live():
    """The setting changed while a layer is shown: the rail follows at once, with no restart."""
    tools_check('vector', 'vector (back on the layer)')
    apply_settings({TOOLS_PATH.format('vector'): 'identify'})
    tools_check('vector', 'vector, setting changed live', 'identify')
    d = dock()
    check('tools: a button hidden then shown again is back in its place', d.pushButton_exploring_zoom.isVisibleTo(d.widget_exploring_keys)
          and not d.pushButton_exploring_identify.isVisibleTo(d.widget_exploring_keys), '')
    # a tool on the map is put down when its button goes
    extras = coverage()._extras
    link = d.pushButton_checkable_exploring_linking_widgets
    zone = extras._tools['pushButton_checkable_exploring_vector_zone']
    zone.setChecked(True)
    pump(100)
    on = zone.isChecked()
    apply_settings({TOOLS_PATH.format('vector'): 'zone'})
    pump(150)
    check('tools: a tool put on the map is put down before its button goes', on and not zone.isChecked()
          and not zone.isVisibleTo(d.widget_exploring_keys) and not extras.zone_tool_on(),
          f"on={on} checked={zone.isChecked()} tool on map={extras.zone_tool_on()}")
    # a mode is turned off with its button, and nothing turns it on again meanwhile
    link.setChecked(True)
    apply_settings({TOOLS_PATH.format('vector'): 'link'})
    pump(150)
    check('tools: a mode (link) is turned off when its button is hidden', not link.isChecked()
          and not link.isVisibleTo(d.widget_exploring_keys), f"checked={link.isChecked()}")
    sync = d.pushButton_checkable_exploring_selecting
    sync.setChecked(True)
    apply_settings({TOOLS_PATH.format('vector'): 'sync'})
    pump(150)
    off = not sync.isChecked() and not sync.isVisibleTo(d.widget_exploring_keys)
    from qgis.core import QgsGeometry
    extras._on_vector_zone_drawn(QgsGeometry.fromRect(d.current_layer.extent()))
    pump(100)
    check('tools: a mode (sync) is turned off with its button, and the zone does not turn it on again',
          off and not sync.isChecked(), f"off={off} after the zone={sync.isChecked()}")
    return waits(0.3)


def s_tools_layer_modes_add():
    project.addMapLayer(QgsVectorLayer(M['zones'] + '|layername=zones', 'zones_again', 'ogr'))
    return lambda: registered('zones_again') and tasks_idle()


def s_tools_layer_modes():
    """A layer that was left with a mode on, shown again while its button is hidden: the mode is not on."""
    d = dock()
    d.PROJECT_LAYERS[layer('zones_again').id()].setdefault('exploring', {})['is_selecting'] = True
    apply_settings({TOOLS_PATH.format('vector'): 'sync'})
    return tools_pick('zones_again', coverage_page=False)


def s_tools_layer_modes_check():
    d = dock()
    sync = d.pushButton_checkable_exploring_selecting
    check('tools: a layer left with the mode on comes back with it off while its button is hidden',
          settles(lambda: not sync.isChecked() and not sync.isVisibleTo(d.widget_exploring_keys), 2.0),
          f"checked={sync.isChecked()} visible={sync.isVisibleTo(d.widget_exploring_keys)}")
    apply_settings({TOOLS_PATH.format('vector'): ''})
    project.removeMapLayer(layer('zones_again').id())
    return lambda: layer('zones_again') is None and tasks_idle()


def s_tools_layer_modes_back():
    return tools_pick('zones', coverage_page=False)


def s_tools_menu():
    """The right-click menu of the rail: one check box per button, "more" always on, a box writes the setting; the menu
    is destroyed once it ran."""
    from qgis.PyQt import sip
    from qgis.PyQt.QtGui import QContextMenuEvent
    d = dock()
    seen, snapshots = [], []

    def fake_exec(menu, *args):
        seen.append(menu)
        snapshots.append([(a.text(), a.isCheckable(), a.isChecked(), a.isEnabled()) for a in menu.actions()
                          if not a.isSeparator()])
        if TOOLS.get('trigger') is not None:
            [a for a in menu.actions() if a.isCheckable()][TOOLS['trigger']].trigger()  # a box ticked or unticked

    def right_click():
        button = d.pushButton_exploring_reset_layer_properties  # no menu of its own: the click goes on to the rail
        point = QPoint(button.width() // 2, button.height() // 2)
        QApplication.sendEvent(button, QContextMenuEvent(QContextMenuEvent.Reason.Mouse, point, button.mapToGlobal(point)))
        pump(300)

    original = QMenu.exec
    QMenu.exec = fake_exec
    try:
        TOOLS['trigger'] = None
        apply_settings({TOOLS_PATH.format('vector'): 'follow'})
        pump(150)
        right_click()
        shown = snapshots[-1] if snapshots else []
        title, boxes = shown[:1], [row for row in shown if row[1]]
        module = tools_module()
        wanted = [key not in module.hidden_for('vector', 'follow') for key in module.tools_of('vector')]
        locked = [row for row in boxes if not row[3]]
        check('tools: a right-click on a button of the rail lists its tools, one check box each, "more" always on',
              len(boxes) == len(wanted) and [row[2] for row in boxes] == wanted and len(locked) == 1
              and locked[0][0].startswith('More tools') and all(row[3] for row in boxes if row not in locked),
              f"menu={bool(seen)} actions={shown}")
        check('tools: the title of the menu is a disabled entry (a section is not drawn by the native styles)',
              title and title[0][0] == 'Tools shown for this type of layer' and not title[0][1] and not title[0][3], str(title))
        check('tools: the menu is destroyed once it ran', bool(seen) and sip.isdeleted(seen[-1]), f"seen={len(seen)}")
        TOOLS['trigger'] = 0  # zoom unticked
        right_click()
        pump(300)
        check('tools: a box of the menu writes the setting and the rail follows at once',
              config_value(TOOLS_PATH.format('vector')) == 'zoom, follow' and tools_rail_is('vector', 'zoom, follow'),
              f"setting={config_value(TOOLS_PATH.format('vector'))!r} rail={tools_rail('vector')}")
    finally:
        QMenu.exec = original
        TOOLS['trigger'] = None
    return waits(0.3)


def s_tools_wizard():
    """The setup asks the tools of each kind, ticked as they are; answering as ticked changes nothing; a tool unticked
    is a change, applied at once, and the link puts it back."""
    apply_settings({TOOLS_PATH.format(kind): '' for kind in TOOLS_HIDDEN})
    chat = agent_chat()
    chat.start_setup()
    TOOLS['asked'] = []
    steps = 0
    while _wizard_card() is not None and steps < 30:
        card = _wizard_card()
        labels = [label for buttons, _other, _field in card._groups for _button, label in buttons]
        if [chip.text() for chip in card._chips][:1] == ['Vector tools']:
            TOOLS['asked'] = labels
            TOOLS['chips'] = [chip.text() for chip in card._chips]
            _answer_card(untick=('Identify the selected features', 'Value pipette'))
        else:
            _answer_card()
        steps += 1
    TOOLS['card'] = chat._settings_cards[-1] if chat._settings_cards else None
    return waits(0.2)


def s_tools_wizard_apply():
    card = TOOLS['card']
    TOOLS['rows'] = [row.text() for row in card.rows] if card is not None else []
    if card is not None:
        card.apply_button.click()
    return waits(0.6)


def s_tools_wizard_check():
    check('tools: the setup asked every button that can be hidden, none of "more", one question per kind of data',
          TOOLS.get('chips') == ['Vector tools', 'Raster tools', 'Cloud tools'] and 'Zoom to the selected features' in TOOLS['asked'] and 'Value pipette' in TOOLS['asked']
          and 'More tools (always shown)' not in TOOLS['asked'], str(TOOLS['asked']))
    check('tools: the setup changed the two settings unticked, no other',
          len(TOOLS['rows']) == 2 and config_value(TOOLS_PATH.format('vector')) == 'identify'
          and config_value(TOOLS_PATH.format('point_cloud')) == 'value_pipette'
          and config_value(TOOLS_PATH.format('raster')) == '', f"rows={TOOLS['rows']}")
    dock()._fm_sections.open_top('exploring')  # the setup opened AGENT, which folds EXPLORING (and its rail)
    pump(400)
    tools_check('vector', 'vector, after the setup', 'identify')
    TOOLS['reverted'] = agent_chat()._wizard.revert()
    return waits(0.6)


def s_tools_end():
    dock()._fm_sections.open_top('exploring')
    pump(400)
    check('tools: the link of the setup puts the tools back, the rail follows',
          TOOLS['reverted'] is True and all(config_value(TOOLS_PATH.format(kind)) == '' for kind in TOOLS_HIDDEN)
          and settles(lambda: tools_rail_is('vector', '')), str(tools_rail('vector')))
    # a setting hand-written with a name no button has hides nothing and breaks nothing
    apply_settings({TOOLS_PATH.format('vector'): ''})
    for kind, text in TOOLS['saved'].items():
        apply_settings({TOOLS_PATH.format(kind): text})
    agent_chat().new_conversation()
    d = dock()
    d._fm_sections.open_top('exploring')
    d.toolBox_tabTools.setCurrentWidget(d.FILTERING)
    return tools_pick(TOOLS['layer'], coverage_page=(TOOLS['layer'] in ('dem', 'cloud')))


def s_tools_startup_check():
    """The dock opened with buttons hidden in its configuration (FM_TOOLS_HIDDEN): the rail is as the setting says
    from the start, and its right-click menu is connected."""
    d = dock()
    wanted = os.environ.get('FM_TOOLS_HIDDEN', '')
    extras = coverage()._extras
    check('tools: a dock opened with buttons hidden shows its rail as the setting says, and its menu is connected',
          settles(lambda: tools_rail_is('vector', wanted), 3.0) and extras is not None
          and extras._rail_menu_rail is d.widget_exploring_keys, f"rail={tools_rail('vector')} wanted={wanted!r}")
    return waits(0.2)


TOOLS_STEPS = [s_tools_begin, s_tools_vector_check, s_tools_raster_check, s_tools_cloud_check, s_tools_groups_begin, s_tools_groups_raster,
               s_tools_groups_cloud, s_tools_live, s_tools_layer_modes_add, s_tools_layer_modes,
               s_tools_layer_modes_check, s_tools_layer_modes_back, s_tools_menu,
               s_tools_wizard, s_tools_wizard_apply, s_tools_wizard_check, s_tools_end]


# --- EXPLORING driven by the agent as a hand drives it (set_exploring, FM_ONLY=drive) ---------------------------------

DRIVE = {}


def drive_module():
    return importlib.import_module(f'{PACKAGE}.adapters.public_api.exploring_drive')


def drive(**arguments):
    """set_exploring on the dock, as the chat calls it; the answer, or the refusal as text."""
    try:
        return drive_module().set_exploring(dock(), **arguments)
    except ValueError as exc:
        return str(exc)


def s_drive_begin():
    leave_welcome()
    turn_effects = importlib.import_module(f'{PACKAGE}.adapters.agent.turn_effects')
    messages = importlib.import_module(f'{PACKAGE}.core.agent.messages')
    DRIVE['recorder'] = recorder = turn_effects.EffectsRecorder()
    arguments = {'layer': 'dem', 'tools': {'pipette': True}}
    recorder.before_call(messages.ToolCallPart('d1', 'set_exploring', arguments))
    DRIVE['answer'] = drive(**arguments)
    recorder.after_call()
    return switched_to('dem', True)


def s_drive_raster_check():
    answer = DRIVE['answer']
    check('drive: the layer is shown in EXPLORING and the pipette armed on the map, as by a click',
          isinstance(answer, dict) and answer['layer_name'] == 'dem' and answer['kind'] == 'raster'
          and answer['tools'].get('pipette') == 'on' and tools_on_map() and coverage()._color_pick
          and answer['changed'] == ['layer', 'pipette'], str(answer))
    check('drive: its button shows down on the rail', dock().widget_exploring_keys.findChild(
        QPushButton, 'pushButton_checkable_exploring_raster_pipette').isChecked())
    two = drive(tools={'detector': True, 'similar': True})
    check('drive: two tools for the map are refused, nothing changed', isinstance(two, str)
          and 'one tool at a time' in two and coverage()._color_pick, str(two))
    apply_settings({TOOLS_PATH.format('raster'): 'detector'})
    pump(150)
    hidden = drive(tools={'detector': True})
    check('drive: a button the user hid is refused with the way to show it, the pipette stays',
          isinstance(hidden, str) and 'right-click' in hidden and tools_on_map(), str(hidden))
    apply_settings({TOOLS_PATH.format('raster'): ''})
    pump(150)
    swap = drive(tools={'pipette': False, 'similar': True})
    check('drive: one tool put down for another, the map keeps one', isinstance(swap, dict)
          and swap['tools'].get('similar') == 'on' and swap['tools'].get('pipette') == 'off' and tools_on_map(),
          str(swap))
    effects = DRIVE['recorder'].finish()
    DRIVE['effects'] = effects
    check('drive: the turn keeps what it drove', [effect[0] for effect in effects] == ['exploring'],
          str([effect[:2] for effect in effects]))
    turn_effects = importlib.import_module(f'{PACKAGE}.adapters.agent.turn_effects')
    DRIVE['undo'] = turn_effects.apply_effects(effects, undo=True)
    return switched_to('zones', False)


def s_drive_undo_check():
    done, left = DRIVE['undo']
    check('drive: undoing the turn puts the tool down and shows the layer of before',
          dock().current_layer.name() == 'zones' and not tools_on_map() and not coverage()._color_pick and done
          and not left, f"done={done} left={left} on map={tools_on_map()}")
    d = dock()
    follow = d.pushButton_checkable_exploring_tracking
    answer = drive(tools={'follow': True}, press=['zoom'])
    check('drive: a mode of a vector layer turned on and an action pressed', isinstance(answer, dict)
          and follow.isChecked() and answer['tools'].get('follow') == 'on' and answer['pressed'] == ['zoom']
          and app().PROJECT_LAYERS[layer('zones').id()]['exploring'].get('is_tracking') is True, str(answer))
    options = panels_module().layer_options(d, 'zones')
    check('drive: layer_options says what the rail shows of the layer shown', options['panel'].get('shown')
          and options['panel']['tools'].get('follow') == 'on', str(options['panel']))
    d._fm_sections.open_top('agent')
    pump(150)
    folded = drive(tools={'follow': False})
    check('drive: EXPLORING folded behind the chat is said so', isinstance(folded, dict)
          and folded['in_view'] is False and 'note' in folded and not follow.isChecked(), str(folded))
    shown = drive(show=True)
    check('drive: show opens EXPLORING in front', isinstance(shown, dict) and shown['in_view'] is True
          and d._fm_sections.in_view('exploring'), str(shown))
    unknown = drive(tools={'pipette': True})
    check('drive: a button of another rail is refused with those of this one', isinstance(unknown, str)
          and 'sync, follow, zone, link' in unknown, unknown)
    leave_welcome()
    return settled()


def drive_turn(arguments):
    """set_exploring in a turn of its own, as the chat records it; the answer, and the effects of the turn."""
    turn_effects = importlib.import_module(f'{PACKAGE}.adapters.agent.turn_effects')
    messages = importlib.import_module(f'{PACKAGE}.core.agent.messages')
    recorder = turn_effects.EffectsRecorder()
    recorder.before_call(messages.ToolCallPart('v1', 'set_exploring', arguments))
    answer = drive(**arguments)
    recorder.after_call()
    return answer, recorder.finish()


def drive_undo(effects):
    return importlib.import_module(f'{PACKAGE}.adapters.agent.turn_effects').apply_effects(effects, undo=True)


def s_drive_values_begin():
    """The range of a raster set in its panel, with the preview; then the selection sync replaces, given back."""
    d = dock()
    zones = layer('zones')
    zones.selectByIds(sorted(zones.allFeatureIds())[:1])
    DRIVE['selected'] = sorted(zones.selectedFeatureIds())
    answer, effects = drive_turn({'tools': {'sync': True}})
    DRIVE['sync'] = (answer, effects)
    return settled()


def s_drive_sync_check():
    answer, effects = DRIVE['sync']
    undone = drive_undo(effects)
    pump(300)
    check('drive: the selection sync replaced comes back with the undo', isinstance(answer, dict)
          and sorted(layer('zones').selectedFeatureIds()) == DRIVE['selected']
          and not dock().pushButton_checkable_exploring_selecting.isChecked(),
          f"{answer} undone={undone} now={sorted(layer('zones').selectedFeatureIds())} was={DRIVE['selected']}")
    dem = layer('dem')
    stats = dem.dataProvider().bandStatistics(1)
    DRIVE['low'] = low = stats.minimumValue + (stats.maximumValue - stats.minimumValue) / 2
    DRIVE['before'] = None
    answer, effects = drive_turn({'layer': 'dem', 'raster': {'minimum': low, 'maximum': None},
                                  'tools': {'preview': True}})
    DRIVE['raster'] = (answer, effects)
    return switched_to('dem', True)


def s_drive_raster_values_check():
    answer, effects = DRIVE['raster']
    panel = coverage()._raster_panel
    state = panel.state()
    check('drive: the range of the raster is set in its panel, RANGE active, the preview on',
          isinstance(answer, dict) and state['mode'] == 'range' and state['minimum'] is not None
          and abs(state['minimum'] - DRIVE['low']) < 1e-6 and state['maximum'] is None
          and answer['tools'].get('preview') == 'on' and 'values' in answer['changed'], f"{answer} {state}")
    check('drive: the histogram shows the range', panel._histogram.range()[0] is not None
          and abs(panel._histogram.range()[0] - DRIVE['low']) < 1e-6, str(panel._histogram.range()))
    bad = drive(raster={'band': 9})
    check('drive: a band the raster has not is refused', isinstance(bad, str) and 'raster.band' in bad, str(bad))
    DRIVE['raster_undo'] = drive_undo(effects)
    return switched_to('zones', False)


def s_drive_raster_undo_check():
    done, left = DRIVE['raster_undo']
    DRIVE['undo_left'] = left
    tools_pick('dem', coverage_page=True)  # look at the panel of the raster again
    return switched_to('dem', True)


def s_drive_raster_undo_panel():
    state = coverage()._raster_panel.state()
    check('drive: the undo gives the range of before back and puts the preview down',
          state['minimum'] is None and not dock().pushButton_checkable_exploring_selecting.isChecked()
          and not DRIVE['undo_left'], f"{state['mode']} {state['minimum']} left={DRIVE['undo_left']}")
    drive(raster={'minimum': DRIVE['low']})
    slope = drive(raster={'quantity': 'slope_degrees'})
    state = coverage()._raster_panel.state()
    check('drive: another quantity without bounds forgets the bounds of the value (another unit)',
          isinstance(slope, dict) and state['derivative'] == 'slope_degrees' and state['minimum'] is None
          and state['maximum'] is None, f"{slope} {state['derivative']} {state['minimum']}")
    drive(raster={'quantity': 'value'})
    if not has_point_clouds():
        report('SKIP', 'drive: point cloud values', f"QGIS {Qgis.QGIS_VERSION} < 3.26")
        return tools_pick('zones', coverage_page=False)
    cloud = layer('cloud')
    listed = cloud.id() in app().PROJECT_LAYERS
    DRIVE['cloud_listed'] = listed
    if not listed:
        before = dock().current_layer.name()
        refused = drive(layer='cloud', point_cloud={'classes': [2]})
        check('drive: a point cloud the panel does not list is refused, the panel stays on its layer',
              isinstance(refused, str) and 'does not list' in refused and dock().current_layer.name() == before,
              f"{refused} now={dock().current_layer.name()}")
        return tools_pick('zones', coverage_page=False)
    return tools_pick('cloud', coverage_page=True)


def s_drive_cloud_check():
    if has_point_clouds() and DRIVE.get('cloud_listed'):
        panel = coverage()._pc_panel
        codes = sorted(panel._present_codes()) or sorted(
            int(item.data(Qt.ItemDataRole.UserRole)) for item in panel._class_items())
        answer = drive(point_cloud={'classes': codes[:1]}) if codes else 'no class'
        state = panel.state()
        check('drive: the classes of a point cloud are set in its panel', isinstance(answer, dict)
              and state['classes_enabled'] and state['classes'] == codes[:1], f"{answer} {state.get('classes')}")
        both = drive(point_cloud={'classes': codes[:1], 'ranges': [{'attribute': 'Z', 'minimum': 0}]})
        check('drive: classes and ranges together are refused', isinstance(both, str) and 'not both' in both, both)
    return tools_pick('zones', coverage_page=False)


DRIVE_STEPS = [s_drive_begin, s_drive_raster_check, s_drive_undo_check, s_drive_values_begin, s_drive_sync_check,
               s_drive_raster_values_check, s_drive_raster_undo_check, s_drive_raster_undo_panel, s_drive_cloud_check]


# --- a source filtered again by an expression its SQL cannot write (FM_ONLY=refilter) ---------------------------------
# 2026-11-18: the first filter of the GeoPackage by bounds_width($geometry) > 60 listed the keys QGIS kept; a second
# one replacing it read its features through that first filter, wrote no list and fell to the former conversion
# (bounds_width("geom") > 40, refused by SQLite: "previous filter kept"; $area as a planar ST_Area). Widths: east_a,
# straddle and west_a 100 m, east_b and west_b 50 m.
REFILTERS = [
    ('bounds_width($geometry) > 60', None),
    ('bounds_width($geometry) > 40', None),  # replaced: the five, not the three of the subset it replaces
    ('$area > 5000', None),  # west_b: 5,000 m2 on the plane, more on the ellipsoid; QGIS keeps it, ST_Area did not
    # ORed: east_a and west_b, kept by the old subset too, are listed with east_b (the selection of the targets)
    ('bounds_width($geometry) < 60 OR x_min($geometry) > 700650', 'OR'),
]
REFILTER_BUTTONS = ('pushButton_checkable_filtering_layers_to_filter', 'pushButton_checkable_filtering_geometric_predicates',
                    'pushButton_checkable_filtering_current_layer_combine_operator')


def refilter_reference(text):
    """The names QGIS keeps for ``text`` on every feature of zones, in the variables of the layer."""
    from qgis.core import QgsExpression, QgsExpressionContext, QgsExpressionContextUtils
    whole = QgsVectorLayer(M['zones'] + '|layername=zones', 'zones reference', 'ogr')
    expression = QgsExpression(text)
    context = QgsExpressionContext(QgsExpressionContextUtils.globalProjectLayerScopes(layer('zones')))
    expression.prepare(context)
    kept = []
    for feature in whole.getFeatures():
        context.setFeature(feature)
        if expression.evaluate(context) in (True, 1):
            kept.append(feature['name'])
    return sorted(kept)


def listed_fids(subset):
    return {int(value) for values in re.findall(r'"fid" IN \(([\d, ]+)\)', subset) for value in values.split(',')}


def s_refilter_setup():
    d = dock()
    STATE['refilter_before'] = {
        'current': d.comboBox_filtering_current_layer.currentLayer(), 'subset': layer('zones').subsetString(),
        'buttons': {name: getattr(d, name).isChecked() for name in REFILTER_BUTTONS},
        'operator': d.comboBox_filtering_source_layer_combine_operator.currentIndex(),
        'single': d.mGroupBox_exploring_single_selection.isChecked(),
        'expression': d.mFieldExpressionWidget_exploring_custom_selection.expression()}
    return pick_vector('zones')


def s_refilter_source_only():
    """After the switch: the dock has put back the FILTERING settings of zones, a filter of the source alone now."""
    d = dock()
    layer('zones').setSubsetString('')
    for name in REFILTER_BUTTONS:
        getattr(d, name).setChecked(False)


def _refilter_steps(text, operator):
    def select():
        d = dock()
        d.pushButton_checkable_filtering_current_layer_combine_operator.setChecked(operator is not None)
        if operator is not None:
            d.comboBox_filtering_source_layer_combine_operator.setCurrentIndex({'AND': 0, 'AND NOT': 1, 'OR': 2}[operator])
        d.mGroupBox_exploring_custom_selection.setChecked(True)
        d.mFieldExpressionWidget_exploring_custom_selection.setExpression(text)
        return waits(2.0, tasks_idle)

    def run():
        iface.messageBar().clearWidgets()
        zones = layer('zones')
        STATE['refilter_old'] = (zones.subsetString(), names(zones))
        run_task('filter')
        return waits(3.0, tasks_idle)

    def verify():
        zones, (old, shown) = layer('zones'), STATE['refilter_old']
        subset, expected = zones.subsetString(), refilter_reference(text)
        if operator == 'OR':
            # the new part is also the selection the targets follow: every zone the expression keeps
            fids = {feature['name']: feature.id() for feature in QgsVectorLayer(
                M['zones'] + '|layername=zones', 'zones fids', 'ogr').getFeatures()}
            new_part = subset[len(f'( {old} ) OR ( '):] if subset.startswith(f'( {old} ) OR ( ') else ''
            listed = listed_fids(new_part) == {fids[name] for name in expected}
            expected = sorted(set(expected) | set(shown))
        else:
            listed = subset.startswith('"fid" IS NOT NULL AND "fid" IN (')
        refused = [message for message in message_bar_texts() if 'previous filter kept' in message]
        check(f"refilter {operator or 'replace'}: {text} keeps what QGIS keeps, as a list of keys",
              names(zones) == expected and listed and not refused,
              f"expected={expected} got={names(zones)} subset={subset[:160]!r} refused={refused}")

    for step, kind in ((select, 'select'), (run, 'filter'), (verify, 'check')):
        step.__name__ = f"s_refilter_{kind}_{REFILTERS.index((text, operator)) + 1}"
    return [select, run, verify]


def s_refilter_done():
    d, before = dock(), STATE['refilter_before']
    layer('zones').setSubsetString(before['subset'])
    d.comboBox_filtering_source_layer_combine_operator.setCurrentIndex(before['operator'])
    for name, checked in before['buttons'].items():
        getattr(d, name).setChecked(checked)
    d.mFieldExpressionWidget_exploring_custom_selection.setExpression(before['expression'])
    if before['single']:
        d.mGroupBox_exploring_single_selection.setChecked(True)
    if before['current'] is not None:
        d.comboBox_filtering_current_layer.setLayer(before['current'])
    return settled()


REFILTER_STEPS = ([s_refilter_setup, s_refilter_source_only]
                  + [step for text, operator in REFILTERS for step in _refilter_steps(text, operator)]
                  + [s_refilter_done])


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
        sections = d._fm_sections
        anchor = panels.panel(key) if on_panel else (sections.top_rail if key == 'agent'
                                                     else sections.bottom_rail).chip(key)
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
    steps += _menu_shot('02_menu_chip_filtering', 'filtering', on_panel=False)
    steps += _menu_shot('02_menu_chip_agent', 'agent', on_panel=False)
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
         s_back_to_vector, *TOOLS_STEPS, s_close_dock, s_reopen_dock, s_reopen_pick_raster, s_reopen_raster_check,
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
         *PANEL_STEPS, *OPTION_STEPS, *SECTION_STEPS, *WELCOME_STEPS, *AUDIT_STEPS, *HEADER_STEPS, *EXPLO_STEPS,
         *SWITCH_STEPS, *ROWS_STEPS, *LIKE_STEPS, *REFILTER_STEPS, *SIZING_STEPS, s_finish]

# --- the local copy of a web service layer: its button on the rail, one click, the layer on its copy (FM_ONLY=stream_copy)

STREAM_COPY = {}


def stream_copy_button():
    return dock().findChild(QPushButton, 'pushButton_exploring_stream_copy')


def s_stream_copy_begin():
    """A tile server of the bench of the streams, and a layer of its tiles, current in the dock."""
    import threading
    from http.server import ThreadingHTTPServer
    from qgis.core import QgsCoordinateReferenceSystem, QgsRectangle
    sys.path.insert(0, os.path.join(os.environ.get('FM_REPO', '/src'), 'tests', 'qgis_headless'))
    import check_stream_extent_clip as fixture
    server = ThreadingHTTPServer(('127.0.0.1', 0), fixture.MapHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    STREAM_COPY['server'] = server
    project.setFileName(os.path.join(tempfile.mkdtemp(), 'copie.qgz'))
    uri = (f"type=xyz&url=http://127.0.0.1:{server.server_port}/tiles/{{z}}/{{x}}/{{y}}.png&zmin=0&zmax=14"
           "&crs=EPSG:3857")
    tiles = QgsRasterLayer(uri, 'Tuiles locales', 'wms')
    project.addMapLayer(tiles)
    leave_welcome()
    dock()._fm_sections.open_top('exploring')
    iface.mapCanvas().setDestinationCrs(QgsCoordinateReferenceSystem('EPSG:3857'))
    iface.mapCanvas().setExtent(QgsRectangle(100000, 100000, 300000, 250000))
    dock().comboBox_filtering_current_layer.setLayer(tiles)
    return switched_to('Tuiles locales', coverage_page=True)


def s_stream_copy_click():
    button = stream_copy_button()
    check('stream copy: the button is on the rail of a web service layer, and says what it does',
          button is not None and button.isVisible() and 'Local copy' in button.toolTip(),
          button and (button.isVisible(), button.toolTip()[:80]))
    actions = importlib.import_module(f'{PACKAGE}.ui.controllers.stream_copy_actions').get()
    check('stream copy: the plugin started the local copies, with their entry in the menu of the layers',
          actions is not None and actions._action is not None, actions)
    exporting = dock()._controller_integration.exporting_controller
    if exporting is not None:
        exporting.populate_export_combobox()
        widget = dock().widgets['EXPORTING']['LAYERS_TO_EXPORT']['WIDGET']
        listed = [widget.itemText(index) for index in range(widget.count())]
        check('stream copy: EXPORTING lists the web map (written as it draws over the visible map)',
              any(text.startswith('Tuiles locales') for text in listed), listed)
    if button is None or actions is None:
        return None
    actions._ask = lambda title, text, buttons: (STREAM_COPY.setdefault('asked', []).append(text), 0)[1]
    button.click()
    tiles = layer('Tuiles locales')
    return lambda: tiles.providerType() == 'gdal' and tasks_idle()


def s_stream_copy_check():
    tiles = layer('Tuiles locales')
    button = stream_copy_button()
    asked = STREAM_COPY.get('asked') or ['']
    check('stream copy: the cost was said before the copy (pixels, requests, folder)',
          'pixels' in asked[0] and 'requests' in asked[0] and 'copie_filtermate_local' in asked[0], asked[0][:200])
    check('stream copy: one click, and the layer reads a GeoTIFF next to the project',
          tiles.providerType() == 'gdal' and 'copie_filtermate_local' in tiles.source(), tiles.source()[-80:])
    check('stream copy: the button stays, and now offers the way back',
          button.isVisible() and 'back to the service' in button.toolTip(), button.toolTip()[:120])
    actions = importlib.import_module(f'{PACKAGE}.ui.controllers.stream_copy_actions').get()
    mark = actions.mark_of(tiles.id()) if actions is not None else None
    node = project.layerTreeRoot().findLayer(tiles.id())
    shown = iface.layerTreeView().indicators(node) if node is not None else []
    check('stream copy: the layer panel of QGIS marks the layer that reads its copy',
          mark is not None and mark in shown and 'Local copy' in mark.toolTip(),
          (mark, len(shown), mark and mark.toolTip()[:80]))
    # Grouped, the layer has a new node of the layer tree (QGIS moves a node by making another): the mark follows.
    root = project.layerTreeRoot()
    old = root.findLayer(tiles.id())
    group = root.addGroup('Copies locales')
    group.addChildNode(old.clone())
    old.parent().removeChildNode(old)
    STREAM_COPY['group'] = group

    def marked():
        node = root.findLayer(tiles.id())
        return node is not None and actions.mark_of(tiles.id()) in iface.layerTreeView().indicators(node)
    followed = settles(marked, 3.0)
    node = root.findLayer(tiles.id())
    check('stream copy: the mark follows the layer moved into a group', followed,
          node and [indicator.toolTip()[:30] for indicator in iface.layerTreeView().indicators(node)])
    dock().comboBox_filtering_current_layer.setLayer(layer('zones'))
    return switched_to('zones', coverage_page=False)


def s_stream_copy_end():
    button = stream_copy_button()
    check('stream copy: no button on the rail of a local layer', not button.isVisible())
    tiles = layer('Tuiles locales')
    actions = importlib.import_module(f'{PACKAGE}.ui.controllers.stream_copy_actions').get()
    check('stream copy: back to the service', actions.back_to_stream(tiles) and tiles.providerType() == 'wms',
          tiles.providerType())
    node = project.layerTreeRoot().findLayer(tiles.id())
    check('stream copy: back on its service, the layer has no mark in the layer panel',
          actions.mark_of(tiles.id()) is None and not iface.layerTreeView().indicators(node))
    project.removeMapLayer(tiles.id())
    if STREAM_COPY.get('group') is not None:
        project.layerTreeRoot().removeChildNode(STREAM_COPY['group'])
    STREAM_COPY['server'].shutdown()
    return None


STREAM_COPY_STEPS = [s_stream_copy_begin, s_stream_copy_click, s_stream_copy_check, s_stream_copy_end]

if os.environ.get('FM_ONLY') == 'stream_copy':  # the local copy of a web service layer from its button
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *STREAM_COPY_STEPS, s_finish]
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
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *SECTION_STEPS, *WELCOME_STEPS, *AUDIT_STEPS, *HEADER_STEPS,
             *EXPLO_STEPS, *SWITCH_STEPS, s_finish]
if os.environ.get('FM_ONLY') == 'exploring':  # EXPLORING in its own panel, with its chooser of the current layer
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *EXPLO_STEPS, s_finish]
if os.environ.get('FM_ONLY') == 'switch':  # a walk at random through the layouts (FM_SEED, FM_SWITCHES)
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *SWITCH_STEPS, s_finish]
if os.environ.get('FM_ONLY') == 'mouse':  # the drags of the sections with a real pointer (XTest)
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *MOUSE_STEPS, s_finish]
if os.environ.get('FM_ONLY') == 'headers':  # the headers stacked instead of the rails, and back
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *HEADER_STEPS, s_finish]
if os.environ.get('FM_ONLY') == 'headers_startup':  # the same as the dock finds them when it opens (FM_HEADERS)
    STEPS = [s_setup, s_open_plugin, s_dock_ready, s_headers_startup_check, s_finish]
if os.environ.get('FM_ONLY') == 'audit':  # the defects of the panels found on 16 November, each one alone
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *AUDIT_STEPS, s_finish]
if os.environ.get('FM_ONLY') == 'sync':  # what a section in its own panel still shares with the others
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *SYNC_STEPS, s_finish]
if os.environ.get('FM_ONLY') == 'layout_shots':  # the window in each layout, as pictures in FM_GRAB_DIR
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *SHOT_STEPS, s_finish]
if os.environ.get('FM_ONLY') == 'rows':  # the rows of FILTERING / EXPORTING packed or spread, and their key buttons
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *ROWS_STEPS, s_finish]
if os.environ.get('FM_ONLY') == 'sizing':  # the heights of the dock and of the panels of its sections
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *SIZING_STEPS, s_finish]
if os.environ.get('FM_ONLY') == 'like511':  # the two stacks and the rows as 5.1.1 laid them out
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *LIKE_STEPS, s_finish]
if os.environ.get('FM_ONLY') == 'like511_startup':  # the dock opened with the handle where it was left (FM_SHARE)
    STEPS = [s_setup, s_open_plugin, s_dock_ready, s_section_setup, s_vector_source, s_like_startup_check, s_finish]
if os.environ.get('FM_ONLY') == 'tools':  # the tools of the EXPLORING rail chosen per kind of layer, and the setup
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *TOOLS_STEPS, s_finish]
if os.environ.get('FM_ONLY') == 'refilter':  # a source filtered again by an expression its SQL cannot write
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *REFILTER_STEPS, s_finish]
if os.environ.get('FM_ONLY') == 'tools_startup':  # the dock opened with buttons of the vector rail hidden (FM_TOOLS_HIDDEN)
    STEPS = [s_setup, s_open_plugin, s_dock_ready, s_tools_startup_check, s_finish]
if os.environ.get('FM_ONLY') == 'drive':  # EXPLORING driven by the agent (set_exploring), undone with the turn
    STEPS = [s_setup, s_open_plugin, s_dock_ready, *DRIVE_STEPS, s_finish]
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
