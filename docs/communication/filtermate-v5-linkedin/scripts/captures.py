# -*- coding: utf-8 -*-
"""
Capture the real FilterMate dock in QGIS for the English Sarlat article.

Writes six full QGIS windows (3030 x 2070 physical pixels), raw docks,
compact settings crops and QGIS-rendered maps. Layers, Browser, menus,
toolbars and the status bar remain visible in full-window captures.
The map is rendered using QgsMapRendererSequentialJob and composited
inside its canvas rectangle to avoid incomplete canvas rendering.

Scenarios: named-street corridor; church-to-DTM/LiDAR clip; slope-to-parcels;
NDVI-to-parcels; high vegetation-to-explicit boulevard candidates.
The mixed DTM/LiDAR operation uses FilterMate's public Python API.

Set FM5_DATA_DIR to the native Windows folder holding sarlat.gpkg,
mnt_1m.tif, ortho_rvb.tif, ortho_irc.tif and lidar_hd_sarlat.copc.laz.
Set FM5_OUT to the image output folder and FM_REPO to the plugin checkout.
Launch with QGIS --lang en --code using an isolated, disposable profile.
This script exits its QGIS process when finished.
"""
import faulthandler
import os
import shutil
import sys
import tempfile
import time
import traceback

from qgis.core import Qgis, QgsApplication, QgsProject, QgsRasterLayer, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings, Qt, QTimer
from qgis.utils import iface
import qgis.utils

STATE = {'results': [], 'python_errors': [], 'started': time.time(), 'rendered': False}
DATA = os.environ.get('FM5_DATA_DIR', r'C:\Users\Simon\Documents\FilterMate_test_v5\data')
OUT = os.environ.get('FM5_OUT', r'C:\Users\Simon\Documents\FilterMate_test_v5\linkedin_out')
os.makedirs(OUT, exist_ok=True)
LOG = open(os.path.join(OUT, 'linkedin_shots.log'), 'w', encoding='utf-8')
# qgis-bin.exe started with no console (start /min): sys.stdout / sys.stderr are None, everything goes to the log
faulthandler.enable(open(os.path.join(OUT, 'linkedin_shots_fault.log'), 'w'), all_threads=True)


def print(*args, **kwargs):  # noqa: A001 - shadows the builtin on purpose
    LOG.write(' '.join(str(a) for a in args) + '\n')
    LOG.flush()


def _show_exception(type_, value, tb, msg=None, messagebar=False, level=None):
    text = ''.join(traceback.format_exception(type_, value, tb)).strip()
    STATE['python_errors'].append(f"{msg or ''} {text.splitlines()[-1] if text else value}".strip())
    print(f"   [Python exception] {msg or ''}\n{text}", flush=True)


qgis.utils.showException = _show_exception


def _watchdog():
    print('FAIL   watchdog: the run did not finish in 15 minutes', flush=True)
    os._exit(2)


QTimer.singleShot(15 * 60 * 1000, _watchdog)

REPO = os.environ.get('FM_REPO') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE = 'filter_mate'
EXCLUDED = ('.git', '.github', '.claude', '.serena', '_bmad', '_bmad-output', 'dist', 'build', 'scripts',
            'knowledge', 'website', 'tests', 'docs', 'logs', '__pycache__', '*.pyc', 'test_*.py')
STEP_TIMEOUT = float(os.environ.get('FM_STEP_TIMEOUT', '150'))
project = QgsProject.instance()


def report(status, name, detail=''):
    STATE['results'].append((status, name))
    print(f"{status:6} {name}" + (f"  ({detail})" if detail else ''))


def check(name, condition, detail=''):
    report('PASS' if condition else 'FAIL', name, detail)
    return bool(condition)


def app():
    return qgis.utils.plugins[PACKAGE].app


def dock():
    return app().dockwidget


def coverage():
    return dock()._controller_integration.coverage_controller


def layer(name):
    found = project.mapLayersByName(name)
    if found: return found[0]
    return next((item for item in project.mapLayers().values() if item.customProperty('demo_source_key') == name), None)


def set_targets(target_names):
    combo = dock().checkableComboBoxLayer_filtering_layers_to_filter
    model = combo.model()
    for row in range(model.rowCount()):
        item = model.item(row)
        wanted = any(item.text().startswith(layer(name).name() + ' [') for name in target_names)
        item.setCheckState(Qt.CheckState.Checked if wanted else Qt.CheckState.Unchecked)
    button = dock().pushButton_checkable_filtering_layers_to_filter
    if not button.isChecked():
        button.setChecked(True)


def set_predicates(labels):
    d = dock()
    if not d.pushButton_checkable_filtering_geometric_predicates.isChecked():
        d.pushButton_checkable_filtering_geometric_predicates.setChecked(True)
    d.comboBox_filtering_geometric_predicates.setCheckedItems(labels)


def set_buffer(value):
    d = dock()
    button = d.pushButton_checkable_filtering_buffer_value
    if value is None:
        if button.isChecked():
            button.setChecked(False)
        return
    if not button.isChecked():
        button.setChecked(True)
    d.mQgsDoubleSpinBox_filtering_buffer_value.setValue(value)


def run_task(name):
    dock().launchTaskEvent(False, name)


def tasks_idle():
    try:
        own = set(app().tasks_descriptions.values())
    except Exception:
        own = set()
    return not [task for task in QgsApplication.taskManager().activeTasks()
                if task.description().startswith('FilterMate') or task.description() in own]


def settled(seconds=2.5):
    since = time.time()
    return lambda: tasks_idle() and time.time() - since > seconds


def switched_to(name, coverage_page):
    since = time.time()
    last_retry = [since]

    def done():
        active = coverage().active_layer
        if coverage_page:
            right = active is not None and active.name() == layer(name).name()
        else:
            right = (active is None and dock().mGroupBox_exploring_single_selection.isVisible()
                     and dock().current_layer is not None and dock().current_layer.name() == layer(name).name())
        if not right and time.time() - last_retry[0] > 4.0:
            last_retry[0] = time.time()
            dock().comboBox_filtering_current_layer.setLayer(layer(name))
            if not coverage_page:
                dock().current_layer_changed(layer(name), manual_change=True)
        return right and tasks_idle() and time.time() - since > 2.5
    return done


def targets_ready(target_names):
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


def show_only(*names):
    root = project.layerTreeRoot()
    for node in root.findLayers():
        node.setItemVisibilityChecked(node.layer().id() in {layer(name).id() for name in names})


def count(name):
    """Features of a filtered layer (the provider count is -1 on a filtered OGR layer)."""
    return sum(1 for _ in layer(name).getFeatures())


def set_coverage(value):
    spin = getattr(coverage(), '_coverage_spin', None)
    if spin is not None:
        spin.setValue(value)


def kept_extent(name):
    from qgis.core import QgsRectangle
    box = QgsRectangle()
    box.setMinimal()
    for feature in layer(name).getFeatures():
        if feature.hasGeometry():
            box.combineExtentWith(feature.geometry().boundingBox())
    return box if not box.isEmpty() else STATE['extent']


def framed(extent, scale, minimum=150.0):
    """``extent`` grown by ``scale`` with the aspect of the canvas, at least ``minimum`` map units wide."""
    from qgis.core import QgsRectangle
    canvas = iface.mapCanvas()
    ratio = canvas.height() / max(canvas.width(), 1)
    centre = extent.center()
    width = max(extent.width() * scale, minimum)
    height = max(extent.height() * scale, minimum * ratio)
    width = max(width, height / ratio)
    return QgsRectangle(centre.x() - width / 2, centre.y() - width * ratio / 2,
                        centre.x() + width / 2, centre.y() + width * ratio / 2)


def render_map(extent, names):
    """The canvas area rendered away from the canvas (waits for every layer, point clouds included)."""
    from qgis.core import QgsMapRendererSequentialJob, QgsMapSettings
    from qgis.PyQt.QtGui import QColor
    canvas = iface.mapCanvas()
    settings = QgsMapSettings(canvas.mapSettings())
    settings.setLayers([layer(item) for item in names if layer(item) is not None])
    settings.setBackgroundColor(QColor('#ffffff'))
    settings.setOutputSize(canvas.size())
    settings.setOutputDpi(canvas.mapSettings().outputDpi())
    settings.setExtent(extent)
    job = QgsMapRendererSequentialJob(settings)
    job.start()
    job.waitForFinished()
    canvas.setExtent(extent)
    return job.renderedImage()


def shot(name, extent, names):
    """The whole QGIS window with the map painted from an off-canvas render, and the dock alone."""
    from qgis.PyQt.QtCore import QPoint
    from qgis.PyQt.QtGui import QPainter
    mw = iface.mainWindow()
    canvas = iface.mapCanvas()
    image = render_map(extent, names)
    pixmap = mw.grab()
    origin = canvas.mapTo(mw, QPoint(0, 0))
    painter = QPainter(pixmap)
    painter.drawImage(origin, image)
    painter.end()
    path = os.path.join(OUT, f'{name}.png')
    ok = pixmap.save(path, 'PNG')
    check(f'saved {name}.png', ok and os.path.getsize(path) > 20000, f'{pixmap.width()}x{pixmap.height()}')
    panel = dock().grab()
    panel_path = os.path.join(OUT, f'{name}-panel.png')
    panel.save(panel_path, 'PNG')


def style_layers():
    from qgis.core import QgsFillSymbol, QgsLineSymbol
    styles = {
        'parcelle': QgsFillSymbol.createSimple({'color': '150,180,230,110', 'outline_color': '#16232b', 'outline_width': '0.5'}),
        'batiment': QgsFillSymbol.createSimple({'color': '#d64545', 'outline_color': '#8c2626', 'outline_width': '0.3'}),
        'troncon_de_route': QgsLineSymbol.createSimple({'color': '#e0a200', 'width': '1.1'}),
    }
    for name, symbol in styles.items():
        item = layer(name)
        if item is not None:
            item.renderer().setSymbol(symbol)
            item.triggerRepaint()
    cloud = layer('lhd')
    if cloud is not None and cloud.renderer() is not None:
        pixels = getattr(getattr(Qgis, 'RenderUnit', None), 'Pixels', None)
        cloud.renderer().setPointSize(2.0)
        if pixels is not None:
            cloud.renderer().setPointSizeUnit(pixels)
        cloud.triggerRepaint()


# ---------------------------------------------------------------- steps: return None or a condition to poll

def s_setup():
    mw = iface.mainWindow()
    mw.resize(1720, 1280)
    mw.show()
    mw.setWindowTitle("FilterMate 5 — Sarlat-la-Canéda — demonstration")
    from qgis.PyQt.QtWidgets import QDockWidget
    # Keep the standard QGIS docks visible in contextual captures.
    iface.mapCanvas().renderComplete.connect(lambda painter: STATE.update(rendered=True))
    gpkg = os.path.join(DATA, 'sarlat.gpkg')
    layers = [QgsVectorLayer(f'{gpkg}|layername={name}', name, 'ogr') for name in ('batiment', 'troncon_de_route', 'parcelle')]
    layers.append(QgsRasterLayer(os.path.join(DATA, 'ortho_irc.tif'), 'ortho_irc', 'gdal'))
    layers.append(QgsRasterLayer(os.path.join(DATA, 'ortho_rvb.tif'), 'ortho_rvb', 'gdal'))
    layers.append(QgsRasterLayer(os.path.join(DATA, 'mnt_1m.tif'), 'mnt', 'gdal'))
    from qgis.core import QgsPointCloudLayer
    layers.append(QgsPointCloudLayer(os.path.join(DATA, 'lidar_hd_sarlat.copc.laz'), 'lhd', 'copc'))
    labels={'batiment':'Buildings','troncon_de_route':'Road segments','parcelle':'Parcels','ortho_irc':'CIR orthophoto','ortho_rvb':'RGB orthophoto','mnt':'DTM — 1 m','lhd':'LiDAR HD'}
    for item in layers:
        key=item.name()
        item.setCustomProperty('demo_source_key',key)
        item.setName(labels.get(key,key))
    project.addMapLayers(layers)
    style_layers()
    STATE['extent'] = layer('mnt').extent()
    iface.mapCanvas().setExtent(STATE['extent'])
    show_only('batiment', 'troncon_de_route', 'parcelle', 'mnt')
    check('data layers load', all(item.isValid() for item in layers), str([(item.name(), item.isValid()) for item in layers]))


def s_open_plugin():
    settings = QSettings()
    settings.setValue('FilterMate/discord_welcome_dismissed', True)
    settings.setValue('FilterMate/whats_new_seen', 99)
    settings.setValue('qgis/digitizing/validate_geometries', 0)
    plugins = os.path.join(tempfile.mkdtemp(prefix='fm_ln_'), 'plugins')
    shutil.copytree(REPO, os.path.join(plugins, PACKAGE), ignore=shutil.ignore_patterns(*EXCLUDED))
    sys.path.insert(0, plugins)
    qgis.utils.plugin_paths.insert(0, plugins)
    qgis.utils.updateAvailablePlugins()
    started = qgis.utils.loadPlugin(PACKAGE) and qgis.utils.startPlugin(PACKAGE)
    check('plugin starts with iface', started and PACKAGE in qgis.utils.plugins)
    from filter_mate.adapters.qgis.coverage_layers import cache
    cache.set_cache_root(os.path.join(os.path.dirname(plugins), 'cache'))
    qgis.utils.plugins[PACKAGE].run()
    return lambda: dock() is not None and registered('batiment', 'parcelle', 'troncon_de_route', 'mnt', 'lhd') and tasks_idle()


def s_dock_ready():
    d = dock()
    iface.mainWindow().resizeDocks([d], [600], Qt.Orientation.Horizontal)
    d.filtering_auto_current_layer_changed(False)
    check('dock open', d.isVisible())
    shot('00_sarlat_overview', framed(STATE['extent'], 1.03, 1000), ['troncon_de_route', 'batiment', 'parcelle', 'ortho_rvb'])
    return settled(5)


def church():
    source = layer('batiment')
    found = [f for f in source.getFeatures() if f['nature'] == 'Eglise' and f.hasGeometry()]
    return max(found, key=lambda f: f.geometry().area())


# 1. vector -> vector: the main roads (custom expression), buildings and parcels within 50 m
def s1_source():
    iface.setActiveLayer(layer('troncon_de_route'))
    dock().comboBox_filtering_current_layer.setLayer(layer('troncon_de_route'))
    return switched_to('troncon_de_route', coverage_page=False)


def s1_select():
    d = dock()
    d.toolBox_tabTools.setCurrentIndex(0)
    d.mGroupBox_exploring_custom_selection.setChecked(True)
    expression = '"importance" = \'4\''
    d.mFieldExpressionWidget_exploring_custom_selection.setExpression(expression)
    layer('troncon_de_route').selectByExpression(expression)
    set_targets(['batiment', 'parcelle'])
    set_predicates(['Intersect'])
    set_buffer(50.0)
    set_coverage(0)
    show_only('troncon_de_route', 'batiment', 'parcelle', 'ortho_irc')
    ready = targets_ready(['batiment', 'parcelle'])
    return lambda: bool(dock().get_current_features()[0]) and ready()


def s1_filter():
    run_task('filter')
    return lambda: layer('batiment').subsetString() != '' and layer('parcelle').subsetString() != '' and tasks_idle()


def s1_shot():
    n_buildings, n_parcels = count('batiment'), count('parcelle')
    check('1 vector -> vector: buildings and parcels within 50 m of the main roads', n_buildings > 0,
          f'{n_buildings} buildings, {n_parcels} parcels, {layer("troncon_de_route").selectedFeatureCount()} roads selected')
    shot('01_roads_buildings', framed(kept_extent('batiment'), 1.25, 300), ['troncon_de_route', 'batiment', 'parcelle', 'ortho_rvb'])
    run_task('unfilter')
    return lambda: layer('batiment').subsetString() == '' and layer('parcelle').subsetString() == '' and tasks_idle()


def s1_settled():
    layer('troncon_de_route').removeSelection()
    dock().mGroupBox_exploring_custom_selection.setChecked(False)
    return settled()


# 2. vector -> raster + point cloud: the church and 50 m around it
def s2_source():
    iface.setActiveLayer(layer('batiment'))
    dock().comboBox_filtering_current_layer.setLayer(layer('batiment'))
    return switched_to('batiment', coverage_page=False)


def s2_field():
    """The single-selection picker shows the building kind ("Eglise") instead of the first numeric field."""
    d = dock()
    d.mGroupBox_exploring_single_selection.setChecked(True)
    d.mFieldExpressionWidget_exploring_single_selection.setExpression("CASE WHEN \"nature\" = 'Eglise' THEN 'Church' ELSE \"nature\" END")
    picker = d.mFeaturePickerWidget_exploring_single_selection
    since = time.time()
    return lambda: 'Church' in picker.displayExpression() and tasks_idle() and time.time() - since > 3.0


def s2_select():
    d = dock()
    feature = church()
    STATE['church_box'] = feature.geometry().boundingBox()
    d.mFeaturePickerWidget_exploring_single_selection.setFeature(feature.id())
    layer('batiment').selectByIds([feature.id()])
    set_targets(['mnt', 'lhd'])
    set_predicates(['Intersect'])
    set_buffer(50.0)
    show_only('batiment', 'lhd', 'mnt')
    STATE['cloud_source'] = layer('lhd').source()
    ready = targets_ready(['mnt', 'lhd'])
    return lambda: bool(dock().get_current_features()[0]) and ready()


def s2_filter():
    run_task('filter')
    return lambda: layer('mnt').source().endswith('.vrt') and layer('lhd').source() != STATE['cloud_source'] and tasks_idle()


def s2_shot():
    check('2 vector -> raster + point cloud: clipped VRT and derived cloud',
          layer('mnt').source().endswith('.vrt') and layer('lhd').source() != STATE['cloud_source'],
          f"{layer('mnt').source()[-40:]} | {layer('lhd').source()[-40:]}")
    raster = layer('mnt')
    STATE['raster_renderer'] = raster.renderer().clone()
    enhancement = getattr(raster.renderer(), 'contrastEnhancement', lambda: None)()
    if enhancement is not None:
        stats = raster.dataProvider().bandStatistics(1)
        enhancement.setMinimumValue(stats.minimumValue)
        enhancement.setMaximumValue(stats.maximumValue)
    shot('02_church_dtm_lidar', framed(STATE['church_box'], 3.0, 220), ['batiment', 'lhd', 'mnt'])
    raster.setRenderer(STATE.pop('raster_renderer'))
    run_task('undo')
    return lambda: not layer('mnt').source().endswith('.vrt') and tasks_idle()


def s2_settled():
    layer('batiment').removeSelection()
    set_buffer(None)
    return settled()


# 3. raster (slope) -> vector
def s3_source():
    iface.setActiveLayer(layer('mnt'))
    dock().comboBox_filtering_current_layer.setLayer(layer('mnt'))
    return switched_to('mnt', coverage_page=True)


def s3_select():
    ctrl = coverage()
    panel = ctrl._raster_panel
    combo = panel._derivative_combo
    combo.setCurrentIndex(combo.findData('slope_percent'))
    panel._set_range(20.0, None)
    panel._emit_now()
    set_targets(['parcelle'])
    set_predicates(['Intersect'])
    set_coverage(50)
    show_only('parcelle', 'batiment', 'mnt', 'ortho_irc')
    dock().pushButton_checkable_exploring_selecting.setChecked(True)
    selection = panel.selection()
    check('3 slope selection', selection is not None and selection.derivative.value == 'slope_percent' and selection.minimum == 20.0, str(selection))
    return targets_ready(['parcelle'])


def s3_filter():
    run_task('filter')
    return lambda: layer('parcelle').subsetString() != '' and tasks_idle()


def s3_shot():
    n = count('parcelle')
    check('3 raster -> vector: parcels on slopes above 20 %', n > 0, f'{n} parcels')
    shot('03_slope_parcels', framed(kept_extent('parcelle'), 1.4, 300), ['parcelle', 'batiment', 'mnt', 'ortho_irc'])
    dock().pushButton_checkable_exploring_selecting.setChecked(False)
    run_task('unfilter')
    return lambda: layer('parcelle').subsetString() == '' and tasks_idle()


# 4. raster (NDVI expression on the CIR orthophoto) -> vector
def s4_source():
    iface.setActiveLayer(layer('ortho_irc'))
    dock().comboBox_filtering_current_layer.setLayer(layer('ortho_irc'))
    return switched_to('ortho_irc', coverage_page=True)


def s4_select():
    ctrl = coverage()
    panel = ctrl._raster_panel
    panel._on_layout_shortcut('irc')
    panel._insert_spectral('ndvi_vegetation')
    panel._emit_now()
    set_targets(['parcelle'])
    set_predicates(['Intersect'])
    set_coverage(50)
    show_only('parcelle', 'ortho_irc')
    selection = panel.selection()
    check('4 NDVI selection', selection is not None and selection.mode.value == 'expression' and all(ref in selection.expression for ref in ('@1', '@2', '> 0.3')),
          (selection.expression if selection else '')[:80])
    return targets_ready(['parcelle'])


def s4_filter():
    run_task('filter')
    return lambda: layer('parcelle').subsetString() != '' and tasks_idle()


def s4_shot():
    n = count('parcelle')
    check('4 raster -> vector: vegetated parcels (NDVI)', n > 0, f'{n} parcels')
    shot('04_ndvi_parcels', framed(kept_extent('parcelle'), 1.15, 300), ['parcelle', 'ortho_irc'])
    run_task('unfilter')
    return lambda: layer('parcelle').subsetString() == '' and tasks_idle()


# 5. point cloud (high vegetation) -> vector
def s5_source():
    iface.setActiveLayer(layer('lhd'))
    dock().comboBox_filtering_current_layer.setLayer(layer('lhd'))
    return switched_to('lhd', coverage_page=True)


def s5_select():
    ctrl = coverage()
    panel = ctrl._pc_panel
    state = dict(panel.state())
    state.update({'classes_enabled': True, 'classes': [5], 'checked_classes': [5]})
    panel.restore_state(state)
    set_targets(['troncon_de_route'])
    set_predicates(['Intersect'])
    set_buffer(3.0)
    set_coverage(0)
    show_only('troncon_de_route', 'lhd', 'mnt')
    return targets_ready(['troncon_de_route'])


def s5_filter():
    run_task('filter')
    return lambda: layer('troncon_de_route').subsetString() != '' and tasks_idle()


def s5_shot():
    n = count('troncon_de_route')
    check('5 point cloud -> vector: roads within 3 m of high vegetation', n > 0, f'{n} road segments')
    shot('05_high_vegetation_roads', framed(kept_extent('troncon_de_route'), 1.15, 300), ['troncon_de_route', 'lhd', 'mnt'])
    run_task('undo')
    return lambda: layer('troncon_de_route').subsetString() == '' and tasks_idle()


def s_finish():
    check('no Python error in the log', not STATE['python_errors'], '; '.join(STATE['python_errors'][:3]))
    failed = [name for status, name in STATE['results'] if status == 'FAIL']
    print(f"\n{len(STATE['results'])} checks, {len(failed)} failed in {time.time() - STATE['started']:.1f}s "
          f"(QGIS {Qgis.QGIS_VERSION}, images in {OUT})", flush=True)
    if failed:
        print('FAILED: ' + '; '.join(failed), flush=True)
    LOG.close()
    os._exit(1 if failed else 0)


# The mixed extraction is driven by the public Python API, with the real dock configured above.
def s2_filter():
    api = qgis.utils.plugins[PACKAGE].get_public_api()
    result = api.cross_filter(layer('batiment').id(), [layer('mnt').id(), layer('lhd').id()], buffer=50.0, selected_only=True)
    print('2 public Python API report:', result)
    check('2 public Python API mixed extraction succeeds', result.get('ok', False), str(result))
    return settled()

def s2_shot():
    check('2 vector -> raster + point cloud: clipped VRT and derived cloud',
          layer('mnt').source().endswith('.vrt') and layer('lhd').source() != STATE['cloud_source'])
    shot('02_church_dtm_lidar', framed(STATE['church_box'], 3.0, 220), ['batiment', 'lhd', 'mnt'])
    result = qgis.utils.plugins[PACKAGE].get_public_api().clear_filters([layer('mnt').id(), layer('lhd').id()])
    check('2 restore original sources via public Python API', result.get('ok', False), str(result))
    return settled()

# Publication capture settings: actual widget state, expanded sections and clear map context.
import json
from qgis.PyQt.QtCore import QPoint, QRect
from qgis.PyQt.QtWidgets import QToolBar, QDockWidget, QWidget, QScrollArea, QPlainTextEdit
from qgis.core import QgsGeometry, QgsRectangle, QgsFeature, QgsWkbTypes, QgsFillSymbol, QgsLineSymbol
STATE['scenario_results'] = {}
STATE['widget_checks'] = []


def visible_fraction(widget):
    if widget is None or not widget.isVisible(): return 0.0
    rect = QRect(widget.mapTo(dock(), QPoint(0, 0)), widget.size())
    visible = QRect(rect)
    parent = widget.parentWidget()
    while parent is not None and parent is not dock():
        visible = visible.intersected(QRect(parent.mapTo(dock(), QPoint(0, 0)), parent.size()))
        parent = parent.parentWidget()
    return round(visible.width() * visible.height() / max(1, rect.width() * rect.height()), 4)


def capture_layout(kind, verify=True):
    d = dock()
    mw = iface.mainWindow()
    mw.resize(2020, 1380)
    if 'toolbar_names' not in STATE:
        STATE['toolbar_names'] = [bar.objectName() for bar in mw.findChildren(QToolBar) if bar.isVisible()]
    for bar in mw.findChildren(QToolBar):
        bar.setVisible(bar.objectName() in STATE['toolbar_names'])
    for item in mw.findChildren(QDockWidget):
        if item.windowTitle() in ('Layers', 'Browser'):
            item.show()
            mw.resizeDocks([item], [230], Qt.Orientation.Horizontal)
    mw.resizeDocks([d], [600], Qt.Orientation.Horizontal)
    d.frame_exploring.setMinimumHeight(700)
    d.main_splitter.setSizes([740, 440])
    d.setStyleSheet(d.styleSheet() + '\nQComboBox, QLineEdit, QAbstractSpinBox {min-height: 27px;} QPlainTextEdit {font-size: 14px;}')
    rp = coverage()._raster_panel
    if kind in ('slope', 'ndvi'):
        rp._bands_group.setCollapsed(kind == 'slope')
        active = rp._range_group if kind == 'slope' else rp._expression_group
        active.setCollapsed(False)
        if kind == 'ndvi':
            rp._bands_holder.setMinimumHeight(110)
            rp._bands_grid.setVerticalSpacing(5)
            rp._bands_group.setMinimumHeight(160)
            rp._bands_group.setMaximumHeight(16777215)
            rp._expression_edit.setFixedHeight(112)
            rp._expression_group.setMinimumHeight(210)
            rp._expression_group.setMaximumHeight(16777215)
            for widget in (rp._bands_group, rp._expression_group, rp, coverage()._host):
                widget.updateGeometry()
                if widget.layout() is not None:
                    widget.layout().invalidate(); widget.layout().activate()
    elif kind == 'lidar':
        pc = coverage()._pc_panel
        pc._classes_group.setCollapsed(False)
        pc._classes_list.setMinimumHeight(240)
        pc._classes_list.setMaximumHeight(260)
    for scroll in d.findChildren(QScrollArea):
        scroll.verticalScrollBar().setValue(0)
    QgsApplication.processEvents()
    if d.layout() is not None: d.layout().activate()
    QgsApplication.processEvents()
    if not verify:
        return
    checks = [('targets', d.checkableComboBoxLayer_filtering_layers_to_filter),
              ('predicate', d.comboBox_filtering_geometric_predicates),
              ('buffer', d.mQgsDoubleSpinBox_filtering_buffer_value)]
    if kind == 'slope':
        checks += [('quantity', rp._derivative_combo), ('histogram', rp._histogram),
                   ('minimum', rp._min_spin), ('maximum', rp._max_spin), ('coverage', coverage()._coverage_spin)]
    if kind == 'ndvi':
        checks += [('band roles', rp._bands_group), ('NDVI expression', rp._expression_edit), ('coverage', coverage()._coverage_spin)]
    if kind == 'lidar': checks += [('classes', coverage()._pc_panel._classes_list)]
    result = {name:visible_fraction(widget) for name,widget in checks}
    STATE['widget_checks'].append({'kind':kind, 'widgets':result, 'dock_size':[d.width(),d.height()]})
    check(kind + ': critical widgets fully visible', all(v >= .99 for v in result.values()), str(result))


def set_parcel_style():
    layer('parcelle').renderer().setSymbol(QgsFillSymbol.createSimple({
        'color':'35,140,118,40','outline_color':'#126b60','outline_width':'0.6'}))


def uniform_selected_pixels(raster, colour):
    from qgis.core import QgsColorRampShader, QgsRasterShader, QgsSingleBandPseudoColorRenderer
    from qgis.PyQt.QtGui import QColor
    old = raster.renderer()
    shader = QgsColorRampShader()
    shader.setColorRampType(QgsColorRampShader.Type.Interpolated)
    shader.setColorRampItemList([QgsColorRampShader.ColorRampItem(-10000,QColor(colour)),
                                QgsColorRampShader.ColorRampItem(10000,QColor(colour))])
    fn = QgsRasterShader(); fn.setRasterShaderFunction(shader)
    renderer = QgsSingleBandPseudoColorRenderer(raster.dataProvider(),1,fn)
    alpha = old.alphaBand() if old else -1
    if alpha > 0: renderer.setAlphaBand(alpha)
    renderer.setOpacity(.62)
    raster.setRenderer(renderer)


_old_shot = shot

def shot(name, extent, names):
    from qgis.PyQt.QtGui import QImage, QPainter, QColor
    kind = ('slope' if name.startswith('03') else 'ndvi' if name.startswith('04') else
            'lidar' if name.startswith('05') else 'vector')
    capture_layout(kind)
    # Match the final visible map and retain native-resolution map and dock exports.
    show_only(*names)
    _old_shot(name,extent,names)
    render_map(extent,names).save(os.path.join(OUT,name+'-map.png'),'PNG')
    d = dock()
    # Keep the raw panel, and stack two native crops to remove unused layout space.
    if kind in ('slope','ndvi'):
        panel=coverage()._raster_panel
        groups=[panel._bands_group,panel._pipette_group,panel._range_group,panel._expression_group]
    elif kind=='lidar':
        panel=coverage()._pc_panel
        groups=[panel._classes_group,panel._ranges_group,panel._hag_group,panel._expression_group]
    else:
        groups=[d.mGroupBox_exploring_single_selection,d.mGroupBox_exploring_multiple_selection,d.mGroupBox_exploring_custom_selection]
    upper_bottom=max(widget.mapTo(d,QPoint(0,0)).y()+widget.height() for widget in groups if widget.isVisible())+12
    page=d.toolBox_tabTools.widget(0)
    lower_top=max(upper_bottom,page.mapTo(d,QPoint(0,0)).y()-78)
    upper=d.grab(QRect(0,0,d.width(),upper_bottom)).toImage()
    lower=d.grab(QRect(0,lower_top,d.width(),d.height()-lower_top)).toImage()
    upper.setDevicePixelRatio(1); lower.setDevicePixelRatio(1)
    stacked=QImage(upper.width(),upper.height()+lower.height()+12,QImage.Format.Format_RGB32)
    stacked.fill(QColor('#f2f4f5'))
    painter=QPainter(stacked);painter.drawImage(QPoint(0,0),upper);painter.drawImage(QPoint(0,upper.height()+12),lower);painter.end()
    stacked.save(os.path.join(OUT,name+'-settings.png'),'PNG')


def s_dock_ready():
    d = dock()
    d.filtering_auto_current_layer_changed(False)
    # Settle the initial layout; shot() validates the final visible geometry.
    capture_layout('vector', verify=False)
    check('dock open',d.isVisible())
    set_parcel_style()
    # The overview shows the full checked dataset with a natural-colour background.
    layer('troncon_de_route').renderer().setSymbol(QgsLineSymbol.createSimple({'color':'#7f878a','width':'.35'}))
    layer('batiment').renderer().setSymbol(QgsFillSymbol.createSimple({'color':'195,87,65,95','outline_color':'#954f43','outline_width':'.2'}))
    shot('00_sarlat_overview',framed(STATE['extent'],1.0,1000),['batiment','troncon_de_route','parcelle','ortho_rvb'])
    return settled(5)


def s1_select():
    d=dock();d.toolBox_tabTools.setCurrentIndex(0)
    d.mGroupBox_exploring_custom_selection.setChecked(True)
    expression = '"nom_collaboratif_gauche" = \'BD HENRI ARLET\''
    STATE['road_expression'] = expression
    d.mFieldExpressionWidget_exploring_custom_selection.setExpression(expression)
    layer('troncon_de_route').selectByExpression(expression)
    set_targets(['batiment','parcelle']);set_predicates(['Intersect']);set_buffer(50);set_coverage(0)
    ready=targets_ready(['batiment','parcelle'])
    return lambda: bool(d.get_current_features()[0]) and ready()


def s1_shot():
    b,p=count('batiment'),count('parcelle')
    STATE['scenario_results']['roads']={'selected_road_segments':layer('troncon_de_route').selectedFeatureCount(),'buildings':b,'parcels':p,'buffer_m':50,'road':'Boulevard Henri Arlet'}
    check('1 named-street corridor returns useful subset',0<b<718 and 0<p<684,str(STATE['scenario_results']['roads']))
    layer('batiment').renderer().setSymbol(QgsFillSymbol.createSimple({'color':'#db704d','outline_color':'#833f2b','outline_width':'.25'}))
    layer('troncon_de_route').renderer().setSymbol(QgsLineSymbol.createSimple({'color':'#de9b00','width':'1.4'}))
    shot('01_roads_buildings',framed(kept_extent('batiment'),1.05,260),['troncon_de_route','batiment','parcelle','ortho_rvb'])
    run_task('unfilter')
    return lambda: not layer('batiment').subsetString() and not layer('parcelle').subsetString() and tasks_idle()


def s2_shot():
    check('2 real mixed clip',layer('mnt').source().endswith('.vrt') and layer('lhd').source()!=STATE['cloud_source'])
    feature=church()
    selection=QgsVectorLayer('MultiPolygon?crs=EPSG:2154','Selected church','memory')
    f=QgsFeature();f.setGeometry(QgsGeometry(feature.geometry()));selection.dataProvider().addFeatures([f])
    selection.setCustomProperty('demo_source_key','church_outline')
    selection.renderer().setSymbol(QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':'#ffcc00','outline_width':'1.2'}))
    project.addMapLayer(selection)
    layer('lhd').renderer().setPointSize(.7)
    STATE['scenario_results']['mixed_clip']={'raster_clipped':True,'point_cloud_clipped':True,'buffer_m':50,'entry_point':'public Python API'}
    box=QgsRectangle(STATE['church_box']);box.grow(65)
    shot('02_church_dtm_lidar',framed(box,1.0,190),['church_outline','lhd','mnt','ortho_rvb'])
    # A second actual QGIS map shows the DTM without cloud points covering it.
    raster=layer('mnt')
    original_renderer=raster.renderer().clone()
    enhancement=getattr(raster.renderer(),'contrastEnhancement',lambda:None)()
    if enhancement is not None:
        stats=raster.dataProvider().bandStatistics(1)
        enhancement.setMinimumValue(stats.minimumValue)
        enhancement.setMaximumValue(stats.maximumValue)
    render_map(framed(box,1.0,190),['church_outline','mnt','ortho_rvb']).save(os.path.join(OUT,'02_church_dtm_lidar-terrain.png'),'PNG')
    raster.setRenderer(original_renderer)
    result=qgis.utils.plugins[PACKAGE].get_public_api().clear_filters([layer('mnt').id(),layer('lhd').id()])
    check('2 original sources restored',result.get('ok',False))
    return settled()


def s3_shot():
    n=count('parcelle');check('3 slope result',n>0,str(n))
    STATE['scenario_results']['slope']={'slope_min_percent':20,'coverage_min_percent':50,'parcels':n}
    STATE['mnt_style']=layer('mnt').renderer().clone()
    uniform_selected_pixels(layer('mnt'),'#e5a53a')
    shot('03_slope_parcels',framed(STATE['extent'],.86,850),['parcelle','mnt','ortho_rvb'])
    layer('mnt').setRenderer(STATE.pop('mnt_style'))
    dock().pushButton_checkable_exploring_selecting.setChecked(False)
    run_task('unfilter')
    return lambda: not layer('parcelle').subsetString() and tasks_idle()


def s4_shot():
    n=count('parcelle');check('4 NDVI result',n>0,str(n))
    STATE['scenario_results']['ndvi']={'ndvi_min':.3,'coverage_min_percent':50,'parcels':n}
    STATE['cir_style']=layer('ortho_irc').renderer().clone()
    uniform_selected_pixels(layer('ortho_irc'),'#30b571')
    shot('04_ndvi_parcels',framed(STATE['extent'],.86,850),['parcelle','ortho_irc','ortho_rvb'])
    layer('ortho_irc').setRenderer(STATE.pop('cir_style'))
    run_task('unfilter')
    return lambda: not layer('parcelle').subsetString() and tasks_idle()


def s5_source():
    # An explicit nine-feature copy makes the candidate network scope visible in the target name.
    src=layer('troncon_de_route')
    target=QgsVectorLayer(QgsWkbTypes.displayString(src.wkbType())+'?crs=EPSG:2154','Boulevard Henri Arlet — road segments','memory')
    target.dataProvider().addAttributes(src.fields());target.updateFields()
    features=[QgsFeature(f) for f in src.getFeatures() if f['nom_collaboratif_gauche']=='BD HENRI ARLET']
    target.dataProvider().addFeatures(features);target.updateExtents();target.setCustomProperty('demo_source_key','corridor')
    target.renderer().setSymbol(QgsLineSymbol.createSimple({'color':'#ed8f00','width':'1.5'}))
    project.addMapLayer(target)
    STATE['corridor_total']=len(features)
    iface.setActiveLayer(layer('lhd'));dock().comboBox_filtering_current_layer.setLayer(layer('lhd'))
    active=switched_to('lhd',True)
    return lambda: active() and registered('corridor')


def s5_select():
    panel=coverage()._pc_panel
    state=dict(panel.state());state.update({'classes_enabled':True,'classes':[5],'checked_classes':[5]});panel.restore_state(state)
    set_targets(['corridor']);set_predicates(['Intersect']);set_buffer(3);set_coverage(0)
    layer('lhd').renderer().setPointSize(.65)
    return targets_ready(['corridor'])


def s5_filter():
    run_task('filter')
    return lambda: bool(layer('corridor').subsetString()) and tasks_idle()


def s5_shot():
    n=count('corridor');check('5 scoped vegetation result',0<n<=STATE['corridor_total'],str(n))
    STATE['scenario_results']['high_vegetation']={'class':5,'buffer_m':3,'road_segments':n,'candidate_road_segments':STATE['corridor_total'],'road':'Boulevard Henri Arlet'}
    # Frame the same street corridor, retaining a natural-colour base for context.
    box=QgsRectangle(layer('corridor').extent());box.grow(35)
    shot('05_high_vegetation_roads',framed(box,1.0,280),['corridor','lhd','ortho_rvb'])
    return settled()


_old_finish=s_finish

def s_finish():
    with open(os.path.join(OUT,'capture-validation.json'),'w',encoding='utf-8') as file:
        json.dump({'scenario_results':STATE['scenario_results'],'widget_checks':STATE['widget_checks'],'python_errors':STATE['python_errors'],'checks':STATE['results']},file,ensure_ascii=False,indent=2)
    _old_finish()

STEPS = [s_setup, s_open_plugin, s_dock_ready,
         s1_source, s1_select, s1_filter, s1_shot, s1_settled,
         s2_source, s2_field, s2_select, s2_filter, s2_shot, s2_settled,
         s3_source, s3_select, s3_filter, s3_shot,
         s4_source, s4_select, s4_filter, s4_shot,
         s5_source, s5_select, s5_filter, s5_shot,
         s_finish]


def run_step(index=0):
    step = STEPS[index]
    print(f"--- {step.__name__}", flush=True)
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
    if until is not None:
        try:
            done = until()
        except Exception:
            done = False
        if not done and time.time() - since < STEP_TIMEOUT:
            QTimer.singleShot(250, lambda: wait(index, until, since))
            return
        if not done:
            report('FAIL', f"timeout after {STEP_TIMEOUT:.0f}s at the end of {STEPS[index].__name__}")
    QTimer.singleShot(400, lambda: run_step(index + 1))


QTimer.singleShot(2000, run_step)
