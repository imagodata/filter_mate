# -*- coding: utf-8 -*-
"""
FilterMate 5 - full-window screenshots of five filter scenarios on the Estavar data (LinkedIn article, carousel).

Drives the real dock in QGIS 4.2 with its GUI, applies one filter per scenario and saves, for each one, the whole
QGIS window (``ln_<n>_<slug>.png``, 1760 x 1040) and the dock alone (``ln_<n>_<slug>-panel.png``). The map area
of the window is rendered away from the canvas (``QgsMapRendererSequentialJob``) so that it is never stale, point
clouds included, then painted over the canvas in the window grab.

Scenarios (source -> targets):

1. ``routes_batiments``   vector -> vector: the main roads (expression), buildings and parcels within 50 m
2. ``eglise_mnt_lidar``   vector -> raster + point cloud: the church and 50 m around it clip the DTM and the LiDAR
3. ``pente_parcelles``    raster -> vector: slope of the DTM above 20 %, parcels covered at 50 % at least
4. ``ndvi_parcelles``     raster -> vector: NDVI vegetation of the CIR orthophoto, parcels covered at 50 % at least
5. ``vegetation_routes``  point cloud -> vector: high vegetation (class 5) within 3 m of a road

Environment: ``FM5_DATA_DIR`` (folder with cerdagne.gpkg, mnt_1m.tif, ortho_irc.tif, lidar_hd_cerdagne.copc.laz),
``FM5_OUT`` (output folder), ``FM_REPO`` (checkout used as the plugin, copied into a temporary plugins folder).
Run it with ``qgis-bin.exe --code`` and a throw-away profile; it quits QGIS when it is done.
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
    return found[0] if found else None


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

    def done():
        active = coverage().active_layer
        if coverage_page:
            right = active is not None and active.name() == name
        else:
            right = active is None and dock().mGroupBox_exploring_single_selection.isVisible()
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
        node.setItemVisibilityChecked(node.layer().name() in names)


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
    mw.resize(1760, 1040)
    mw.show()
    iface.mapCanvas().renderComplete.connect(lambda painter: STATE.update(rendered=True))
    gpkg = os.path.join(DATA, 'cerdagne.gpkg')
    layers = [QgsVectorLayer(f'{gpkg}|layername={name}', name, 'ogr') for name in ('batiment', 'troncon_de_route', 'parcelle')]
    layers.append(QgsRasterLayer(os.path.join(DATA, 'ortho_irc.tif'), 'ortho_irc', 'gdal'))
    layers.append(QgsRasterLayer(os.path.join(DATA, 'mnt_1m.tif'), 'mnt', 'gdal'))
    from qgis.core import QgsPointCloudLayer
    layers.append(QgsPointCloudLayer(os.path.join(DATA, 'lidar_hd_cerdagne.copc.laz'), 'lhd', 'copc'))
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
    iface.mainWindow().resizeDocks([d], [440], Qt.Orientation.Horizontal)
    check('dock open', d.isVisible())
    return settled()


def church():
    source = layer('batiment')
    found = [f for f in source.getFeatures() if f['nature'] == 'Eglise' and f.hasGeometry()]
    return max(found, key=lambda f: f.geometry().area())


# 1. vector -> vector: the main roads (custom expression), buildings and parcels within 50 m
def s1_source():
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
    shot('ln_1_routes_batiments', framed(kept_extent('batiment'), 1.25, 300), ['troncon_de_route', 'batiment', 'parcelle', 'ortho_irc'])
    run_task('unfilter')
    return lambda: layer('batiment').subsetString() == '' and layer('parcelle').subsetString() == '' and tasks_idle()


def s1_settled():
    layer('troncon_de_route').removeSelection()
    dock().mGroupBox_exploring_custom_selection.setChecked(False)
    return settled()


# 2. vector -> raster + point cloud: the church and 50 m around it
def s2_source():
    dock().comboBox_filtering_current_layer.setLayer(layer('batiment'))
    return switched_to('batiment', coverage_page=False)


def s2_field():
    """The single-selection picker shows the building kind ("Eglise") instead of the first numeric field."""
    d = dock()
    d.mGroupBox_exploring_single_selection.setChecked(True)
    d.mFieldExpressionWidget_exploring_single_selection.setExpression('"nature"')
    picker = d.mFeaturePickerWidget_exploring_single_selection
    since = time.time()
    return lambda: picker.displayExpression() == '"nature"' and tasks_idle() and time.time() - since > 3.0


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
    shot('ln_2_eglise_mnt_lidar', framed(STATE['church_box'], 3.0, 220), ['batiment', 'lhd', 'mnt'])
    raster.setRenderer(STATE.pop('raster_renderer'))
    run_task('undo')
    return lambda: not layer('mnt').source().endswith('.vrt') and tasks_idle()


def s2_settled():
    layer('batiment').removeSelection()
    set_buffer(None)
    return settled()


# 3. raster (slope) -> vector
def s3_source():
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
    shot('ln_3_pente_parcelles', framed(kept_extent('parcelle'), 1.4, 300), ['parcelle', 'batiment', 'mnt', 'ortho_irc'])
    dock().pushButton_checkable_exploring_selecting.setChecked(False)
    run_task('unfilter')
    return lambda: layer('parcelle').subsetString() == '' and tasks_idle()


# 4. raster (NDVI expression on the CIR orthophoto) -> vector
def s4_source():
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
    check('4 NDVI selection', selection is not None and selection.mode.value == 'expression' and 'ortho_irc@' in selection.expression,
          (selection.expression if selection else '')[:80])
    return targets_ready(['parcelle'])


def s4_filter():
    run_task('filter')
    return lambda: layer('parcelle').subsetString() != '' and tasks_idle()


def s4_shot():
    n = count('parcelle')
    check('4 raster -> vector: vegetated parcels (NDVI)', n > 0, f'{n} parcels')
    shot('ln_4_ndvi_parcelles', framed(kept_extent('parcelle'), 1.15, 300), ['parcelle', 'ortho_irc'])
    run_task('unfilter')
    return lambda: layer('parcelle').subsetString() == '' and tasks_idle()


# 5. point cloud (high vegetation) -> vector
def s5_source():
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
    shot('ln_5_vegetation_routes', framed(kept_extent('troncon_de_route'), 1.15, 300), ['troncon_de_route', 'lhd', 'mnt'])
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
