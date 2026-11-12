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

from qgis.core import Qgis, QgsApplication, QgsProject, QgsProviderRegistry, QgsRasterLayer, QgsVectorLayer
from qgis.PyQt.QtCore import QCoreApplication, QPoint, QPointF, QSettings, Qt, QTimer
from qgis.PyQt.QtGui import QWheelEvent
from qgis.PyQt.QtWidgets import QAbstractButton, QApplication, QComboBox, QLabel, QLineEdit, QPushButton, QScrollArea, QToolButton
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
    chat._ask_code = lambda title, text, code: asked.append(code) or True
    try:
        tools, handlers, _active = chat.tools_and_handlers(load_settings())
        offered = next(tool for tool in tools if tool.name == 'load_skill').input_schema['properties']['name']['enum']
        first = handlers['load_skill']({'name': 'team-naming'})
        second = handlers['load_skill']({'name': 'team-naming'})
    finally:
        chat._ask_code = original
        shutil.rmtree(folder, ignore_errors=True)
    check('skill of the profile: offered, asked once, loaded as data with no right',
          'team-naming' in offered and len(asked) == 1 and first.get('from') == 'user'
          and first['instructions'].startswith('This skill comes from the QGIS profile') and second == first,
          f"offered={offered} asked={len(asked)} first={str(first)[:120]}")
    return waits(0.2)


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
    settings = importlib.import_module(f'{PACKAGE}.adapters.agent.settings')
    load_settings, target_of = settings.load_settings, settings.target_of
    AgentSettingsDialog = importlib.import_module(f'{PACKAGE}.ui.widgets.agent_panel').AgentSettingsDialog
    dialog = AgentSettingsDialog(load_settings(), target_of, d, free_available=True)
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
    check('stacks: a click on the open EXPLORING folds it', not sections.is_open('exploring') and
          not sections.is_open('agent') and sections.top.maximumHeight() < 200, str(sections.top.maximumHeight()))
    exploring_header.click()
    QApplication.processEvents()
    check('stacks: and opens it again', sections.is_open('exploring'))

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


STEPS = [s_setup, s_open_plugin, s_dock_ready, s_controllers_check, s_layout_check, s_rail_width_check, s_rail_width_after, s_rail_short, s_rail_short_check, s_rail_tall_check,
         s_ui_profile_check, s_agent_settings, s_agent_settings_check, s_agent_settings_undo_check,
         s_agent_settings_card_check, s_agent_settings_link_check, s_agent_settings_profile_check,
         s_agent_skill_from_profile_check,
         s_qt6_enums_check, s_pick_before_late_refresh,
         s_late_refresh_check,
         s_vector_source, s_vector_select, s_vector_filter, s_vector_check, s_vector_undo_check,
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
         s_switch_same_layer_check, s_switch_late_check, s_plugin_imports_check,
         s_custom_matching_nothing, s_custom_matching_nothing_single, s_custom_matching_nothing_check, s_config_search, s_wheel_needs_focus, s_wheel_needs_focus_check, s_agent_panel, s_finish]


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
