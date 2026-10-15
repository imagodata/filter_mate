# -*- coding: utf-8 -*-
"""
FilterMate 5 - screenshots of the real dock for the website (user guide section 13 and landing page).

Drives the dock in QGIS 4.2 with its GUI and saves PNGs into ``website/img/guide`` (override with
``FM5_SITE_OUT``). Run it with ``qgis --code``; it quits QGIS when it is done.

Images written (``fm5_<topic>.png``):

* ``fm5_raster_exploring``     dock, raster as the current layer: band, pixel value, value range with histogram
* ``fm5_pointcloud_exploring`` dock, point cloud as the current layer: classes (building), attribute ranges
* ``fm5_filtering_targets``    dock, vector source with raster and point cloud layers in the targets list
* ``fm5_vector_to_raster``     map canvas after a vector -> raster clip (clipped VRT)
* ``fm5_raster_to_vector``     map canvas after a raster value range -> vector filter
* ``fm5_pointcloud_to_vector`` map canvas after a point cloud class -> vector filter
* ``fm5_export_tab``           dock, EXPORTING tab with a raster, a point cloud and a vector layer
* ``fm5_configuration``        dock, Configuration tab at the RASTER / POINT_CLOUD options

Data. With ``FM5_DATA`` / ``FM5_GPKG`` / ``FM5_TILE`` set, the script uses the maintainer's real data (IGN
BD TOPO GeoPackage, MNT 1 m, LiDAR HD COPC tile of Cerdagne), like ``scripts/fm5_gui_check.py``. Without them it
falls back to the synthetic fixtures of ``tests/qgis_headless/make_fixtures.py`` (``FM_FIXTURES`` folder), so it
also runs in the official QGIS Docker images. Images made on synthetic data are INTERIM: regenerate them on the
real data before publishing the site.

Windows, real data (PowerShell; QGIS 4.2, plugin loaded from the repository through QGIS_PLUGINPATH)::

    $env:QGIS_PLUGINPATH = "\\\\wsl.localhost\\Ubuntu\\home\\simon\\dev"   # folder that contains filter_mate/
    $env:FM5_DATA = "\\\\wsl.localhost\\Ubuntu\\home\\simon\\fm5_testdata"  # mnt_1m.tif, classes_2m.tif
    $env:FM5_GPKG = "$env:LOCALAPPDATA\\Temp\\fm5\\cerdagne.gpkg"           # batiment / parcelle / troncon_de_route
    $env:FM5_TILE = "<...>\\LHD_FXX_0616_6153_PTS_C_LAMB93_IGN69.copc.laz"
    $env:FM5_SITE_OUT = "<repo>\\website\\img\\guide"
    qgis-bin.exe --nologo --noversioncheck --lang en --profiles-path "$env:TEMP\\fm5\\profiles" --profile fm5 `
        --code <repo>\\scripts\\fm5_site_screenshots.py

(on Windows ``REPO`` is found from this file; set ``FM_REPO`` when QGIS runs the script without ``__file__``).

Docker, synthetic data (from the repository root; the container writes into ``website/img/guide``)::

    docker run --rm -v "$PWD:/src" -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONUNBUFFERED=1 -e FM_FIXTURES=/tmp/fm \\
        qgis/qgis:stable bash -c 'python3 /src/tests/qgis_headless/make_fixtures.py /tmp/fm >/dev/null && \\
        timeout 900 xvfb-run -a -s "-screen 0 1920x1080x24" qgis --nologo --noversioncheck --lang en \\
        --profiles-path /tmp/profiles --code /src/scripts/fm5_site_screenshots.py; \\
        chown -R $(stat -c %u:%g /src) /src/website/img/guide'

The step engine and its helpers (waiting ``switched_to()`` after a current-layer change, ``targets_ready()``,
QSettings keys that avoid modal dialogs, the ``showException`` patch, ``os._exit``) come from
``tests/qgis_headless/run_gui_smoke.py``.
"""
import faulthandler
import json
import os
import shutil
import sys
import tempfile
import time
import traceback

from qgis.core import Qgis, QgsApplication, QgsProject, QgsProviderRegistry, QgsRasterLayer, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings, Qt, QTimer
from qgis.utils import iface
import qgis.utils

STATE = {'results': [], 'python_errors': [], 'started': time.time(), 'rendered': False}
faulthandler.enable(all_threads=True)


def _show_exception(type_, value, tb, msg=None, messagebar=False, level=None):
    """qgis.utils.showException opens a modal dialog that would block the run: record and print instead."""
    text = ''.join(traceback.format_exception(type_, value, tb)).strip()
    STATE['python_errors'].append(f"{msg or ''} {text.splitlines()[-1] if text else value}".strip())
    print(f"   [Python exception] {msg or ''}\n{text}", flush=True)


qgis.utils.showException = _show_exception


def _watchdog():
    print('FAIL   watchdog: the run did not finish in 12 minutes', flush=True)
    os._exit(2)


QTimer.singleShot(12 * 60 * 1000, _watchdog)

REPO = os.environ.get('FM_REPO') or (os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                                     if '__file__' in globals() else '/src')
PACKAGE = 'filter_mate'
EXCLUDED = ('.git', '.github', '.claude', '.serena', '_bmad', '_bmad-output', 'dist', 'build', 'scripts',
            'knowledge', 'website', 'tests', 'docs', 'logs', '__pycache__', '*.pyc', 'test_*.py')
POINT_CLOUD_MIN_VERSION = 32600
OUT = os.environ.get('FM5_SITE_OUT') or os.path.join(REPO, 'website', 'img', 'guide')
STEP_TIMEOUT = float(os.environ.get('FM_STEP_TIMEOUT', '90'))
REAL = bool(os.environ.get('FM5_DATA') and os.environ.get('FM5_GPKG') and os.environ.get('FM5_TILE'))
os.makedirs(OUT, exist_ok=True)
project = QgsProject.instance()

if REAL:
    # name of the layers in the project, as in fm5_gui_check.py
    DS = {'vector': 'batiment', 'other_vector': 'parcelle', 'raster': 'mnt', 'cloud': 'lhd',
          'raster_range': (1240.0, 1270.0), 'cloud_class': 6}
else:
    FIXTURES = os.environ.get('FM_FIXTURES', '/tmp/fm')
    try:
        with open(os.path.join(FIXTURES, 'manifest.json'), encoding='utf-8') as _stream:
            M = json.load(_stream)
    except Exception as _exc:
        print(f"FAIL   fixtures not readable in {FIXTURES}: {_exc} (run make_fixtures.py first)", flush=True)
        os._exit(3)
    DS = {'vector': 'zones', 'other_vector': None, 'raster': 'dem', 'cloud': 'cloud',
          'raster_range': tuple(M['east_range']), 'cloud_class': 6}


def report(status, name, detail=''):
    STATE['results'].append((status, name))
    print(f"{status:<5}  {name}  {detail}".rstrip(), flush=True)


def check(name, condition, detail=''):
    report('PASS' if condition else 'FAIL', name, detail)
    return bool(condition)


def _on_log(message, tag, level):
    if tag == 'Python error':
        STATE['python_errors'].append(f"[{tag}] {message[:400]}")
        print(f"   [QGIS log {tag}] {message[:400]}", flush=True)


QgsApplication.messageLog().messageReceived.connect(_on_log)


# --- helpers -------------------------------------------------------------

def app():
    return qgis.utils.plugins[PACKAGE].app


def dock():
    return app().dockwidget


def coverage():
    return dock()._controller_integration.coverage_controller


def layer(name):
    found = project.mapLayersByName(name)
    return found[0] if found else None


def has_point_clouds():
    return Qgis.QGIS_VERSION_INT >= POINT_CLOUD_MIN_VERSION


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
    try:
        own = set(app().tasks_descriptions.values())
    except Exception:
        own = set()
    return not [task for task in QgsApplication.taskManager().activeTasks()
                if task.description().startswith('FilterMate') or task.description() in own]


def settled():
    """The post-filter window (the dock puts the source layer back in the combo for about 2 s) is over."""
    since = time.time()
    return lambda: tasks_idle() and time.time() - since > 2.5


def switched_to(name, coverage_page):
    """``name`` is current with its EXPLORING page and the delayed restore of its FILTERING settings is over."""
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
    """Visibility of the layers in the layer tree (the canvas shows what is checked)."""
    root = project.layerTreeRoot()
    for node in root.findLayers():
        node.setItemVisibilityChecked(node.layer().name() in names)


def refresh_canvas():
    """Condition: the canvas finished rendering after a refresh."""
    STATE['rendered'] = False
    for item in project.mapLayers().values():
        item.triggerRepaint()  # also invalidates the cached render of a layer whose renderer changed
    iface.mapCanvas().refresh()
    since = time.time()
    return lambda: STATE['rendered'] and time.time() - since > 1.0


def save(widget, name, crop_to=None):
    """Grab a widget to ``OUT/fm5_<name>.png`` (``crop_to`` is an optional QRect in widget coordinates)."""
    pixmap = widget.grab()
    if crop_to is not None:
        pixmap = pixmap.copy(crop_to)
    path = os.path.join(OUT, f'fm5_{name}.png')
    ok = pixmap.save(path, 'PNG')
    check(f'saved fm5_{name}.png', ok and os.path.getsize(path) > 2000, f'{pixmap.width()}x{pixmap.height()}')


def save_dock(name):
    save(dock(), name)


def save_canvas(name):
    """The canvas is as tall as the dock: keep a landscape crop centred on the raster extent."""
    from qgis.PyQt.QtCore import QRect
    canvas = iface.mapCanvas()
    width, height = canvas.width(), canvas.height()
    crop_h = min(height, int(width * 0.62))
    save(canvas, name, QRect(0, (height - crop_h) // 2, width, crop_h))


def style_layers():
    """Readable colours for the canvas: transparent polygons with a red outline, grey-scale raster."""
    from qgis.PyQt.QtGui import QColor
    from qgis.core import QgsFillSymbol
    for item in project.mapLayers().values():
        if isinstance(item, QgsVectorLayer):
            item.renderer().setSymbol(QgsFillSymbol.createSimple({
                'style': 'no', 'outline_color': '#d7191c', 'outline_width': '0.9'}))
            item.triggerRepaint()


# --- steps: each returns None, or a condition polled until true (or STEP_TIMEOUT) ---

def s_setup():
    mw = iface.mainWindow()
    WIN = [int(v) for v in os.environ.get('FM5_WIN', '1700x1250').split('x')]
    mw.resize(*WIN)  # tall: the dock shows EXPLORING, FILTERING and the tabs together
    mw.show()
    iface.mapCanvas().renderComplete.connect(lambda painter: STATE.update(rendered=True))
    layers = []
    if REAL:
        data, gpkg, tile = os.environ['FM5_DATA'], os.environ['FM5_GPKG'], os.environ['FM5_TILE']
        for name in ('batiment', 'parcelle', 'troncon_de_route'):
            layers.append(QgsVectorLayer(f'{gpkg}|layername={name}', name, 'ogr'))
        layers.append(QgsRasterLayer(os.path.join(data, 'mnt_1m.tif'), 'mnt', 'gdal'))
        if has_point_clouds():
            from qgis.core import QgsPointCloudLayer
            layers.append(QgsPointCloudLayer(tile, 'lhd', 'copc'))
    else:
        layers.append(QgsVectorLayer(M['zones'] + '|layername=zones', 'zones', 'ogr'))
        layers.append(QgsRasterLayer(M['dem'], 'dem', 'gdal'))
        if has_point_clouds():
            from qgis.core import QgsPointCloudLayer
            if 'pdal' in QgsProviderRegistry.instance().providerList():
                layers.append(QgsPointCloudLayer(M['las'], 'cloud', 'pdal'))
            else:
                layers.append(QgsPointCloudLayer(M['ept'], 'cloud', 'ept'))
    project.addMapLayers(layers)
    style_layers()
    STATE['extent'] = layer(DS['raster']).extent()
    iface.mapCanvas().setExtent(STATE['extent'])
    check('data layers load', all(item.isValid() for item in layers), str([item.name() for item in layers]))


def expected_layers():
    names = [DS['vector'], DS['raster']] + ([DS['cloud']] if has_point_clouds() else [])
    return names + ([DS['other_vector']] if DS['other_vector'] else [])


def s_open_plugin():
    settings = QSettings()
    settings.setValue('FilterMate/discord_welcome_dismissed', True)  # modal dialogs would block the run
    settings.setValue('FilterMate/whats_new_seen', 99)
    settings.setValue('qgis/digitizing/validate_geometries', 0)
    plugins = os.path.join(tempfile.mkdtemp(prefix='fm_site_'), 'plugins')
    shutil.copytree(REPO, os.path.join(plugins, PACKAGE), ignore=shutil.ignore_patterns(*EXCLUDED))
    sys.path.insert(0, plugins)
    qgis.utils.plugin_paths.insert(0, plugins)
    qgis.utils.updateAvailablePlugins()
    started = qgis.utils.loadPlugin(PACKAGE) and qgis.utils.startPlugin(PACKAGE)
    check('plugin starts with iface', started and PACKAGE in qgis.utils.plugins)
    from filter_mate.adapters.qgis.coverage_layers import cache
    cache.set_cache_root(os.path.join(os.path.dirname(plugins), 'cache'))
    qgis.utils.plugins[PACKAGE].run()
    return lambda: dock() is not None and registered(*expected_layers()) and tasks_idle()


def s_dock_ready():
    d = dock()
    mw = iface.mainWindow()
    mw.resizeDocks([d], [440], Qt.Orientation.Horizontal)
    check('dock open', d.isVisible())
    return settled()


# -- vector source -> raster / point cloud targets
def s_vector_source():
    dock().comboBox_filtering_current_layer.setLayer(layer(DS['vector']))
    return switched_to(DS['vector'], coverage_page=False)


def s_vector_select():
    d = dock()
    d.toolBox_tabTools.setCurrentIndex(0)
    d.mGroupBox_exploring_single_selection.setChecked(True)
    source = layer(DS['vector'])
    wanted = (lambda f: f['name'] == 'east_a') if not REAL else (lambda f: True)
    feature = next(f for f in source.getFeatures() if wanted(f))
    d.mFeaturePickerWidget_exploring_single_selection.setFeature(feature.id())
    STATE['targets'] = [DS['raster']] + ([DS['cloud']] if has_point_clouds() else [])
    set_targets(STATE['targets'])
    set_predicates(['Intersect'])
    d.pushButton_checkable_filtering_buffer_value.setChecked(True)
    # 5 m on the real data; the synthetic zones are small squares in a 1 km DEM: a wider buffer keeps more pixels
    d.mQgsDoubleSpinBox_filtering_buffer_value.setValue(5.0 if REAL else 150.0)
    ready = targets_ready(STATE['targets'])
    return lambda: bool(dock().get_current_features()[0]) and ready()


def dump_rows(tag):
    from filter_mate.ui.layout.mockup_layout import FILTERING_PAIRS, EXPORTING_PAIRS
    d = dock()
    print(f'   [{tag}] toolBox index={d.toolBox_tabTools.currentIndex()} size={d.size().width()}x{d.size().height()}', flush=True)
    for button, value in FILTERING_PAIRS + EXPORTING_PAIRS:
        for name in (button, value):
            w = getattr(d, name, None)
            print(f'   [{tag}] {name}: visible={w.isVisible() if w else None} geom={w.geometry().getRect() if w else None}', flush=True)


def s_shot_filtering():
    dump_rows('filtering')
    save_dock('filtering_targets')
    STATE['cloud_source'] = layer(DS['cloud']).source() if layer(DS['cloud']) else ''
    show_only(DS['vector'], DS['raster'])
    run_task('filter')
    return lambda: layer(DS['raster']).source().endswith('.vrt') and tasks_idle()


def s_shot_vector_to_raster():
    check('vector -> raster: clipped VRT', layer(DS['raster']).source().endswith('.vrt'))
    iface.mapCanvas().setExtent(STATE['extent'])
    return refresh_canvas()


def s_save_vector_to_raster():
    save_canvas('vector_to_raster')
    run_task('undo')
    return lambda: not layer(DS['raster']).source().endswith('.vrt') and tasks_idle()


def s_after_undo():
    return settled()


# -- raster source (value range) -> vector targets
def s_raster_source():
    dock().comboBox_filtering_current_layer.setLayer(layer(DS['raster']))
    return switched_to(DS['raster'], coverage_page=True)


def s_raster_select():
    d, ctrl = dock(), coverage()
    check('raster panel visible', ctrl._raster_panel.isVisible() and not d.mGroupBox_exploring_single_selection.isVisible())
    from filter_mate.core.domain.raster_filter_criteria import RasterSelection
    low, high = DS['raster_range']
    ctrl._raster_panel.set_selection(RasterSelection(band=1, minimum=float(low), maximum=float(high)))
    targets = [DS['vector']] + ([DS['other_vector']] if DS['other_vector'] else [])
    set_targets(targets)
    set_predicates(['Intersect'])
    ctrl._coverage_spin.setValue(50)  # minimum coverage of the vector targets
    show_only(DS['raster'], *targets)
    d.pushButton_checkable_exploring_selecting.setChecked(True)  # live preview: other pixels hidden
    return targets_ready(targets)


def s_raster_shot():
    save_dock('raster_exploring')
    return refresh_canvas()


def s_raster_filter():
    run_task('filter')
    targets = [DS['vector']] + ([DS['other_vector']] if DS['other_vector'] else [])
    return lambda: layer(DS['vector']).subsetString() != '' and tasks_idle()


def s_raster_to_vector():
    check('raster -> vector: target filtered', layer(DS['vector']).subsetString() != '')
    return refresh_canvas()


def s_raster_save():
    save_canvas('raster_to_vector')
    dock().pushButton_checkable_exploring_selecting.setChecked(False)
    run_task('unfilter')
    return lambda: layer(DS['vector']).subsetString() == '' and tasks_idle()


def s_raster_settled():
    return settled()


# -- point cloud source (class 6) -> vector targets
def s_cloud_source():
    if not has_point_clouds():
        report('SKIP', 'point cloud screenshots', f'QGIS {Qgis.QGIS_VERSION} < 3.26')
        return None
    dock().comboBox_filtering_current_layer.setLayer(layer(DS['cloud']))
    return switched_to(DS['cloud'], coverage_page=True)


def s_cloud_select():
    if not has_point_clouds():
        return None
    ctrl = coverage()
    check('point cloud panel visible', ctrl._pc_panel.isVisible())
    panel = ctrl._pc_panel
    state = dict(panel.state())
    state.update({'classes_enabled': True, 'classes': [DS['cloud_class']], 'checked_classes': [DS['cloud_class']]})
    panel.restore_state(state)
    targets = [DS['vector']]
    set_targets(targets)
    set_predicates(['Intersect'])
    show_only(DS['cloud'], DS['vector'])
    return targets_ready(targets)


def s_cloud_shot():
    if not has_point_clouds():
        return None
    save_dock('pointcloud_exploring')
    run_task('filter')
    return lambda: layer(DS['vector']).subsetString() != '' and tasks_idle()


def s_cloud_to_vector():
    if not has_point_clouds():
        return None
    iface.mapCanvas().setExtent(STATE['extent'])
    return refresh_canvas()


def s_cloud_save():
    if not has_point_clouds():
        return None
    save_canvas('pointcloud_to_vector')
    run_task('undo')
    return lambda: layer(DS['vector']).subsetString() == '' and tasks_idle()


def s_cloud_settled():
    return settled()


# -- EXPORTING and Configuration tabs
def s_back_to_vector():
    dock().comboBox_filtering_current_layer.setLayer(layer(DS['vector']))
    return switched_to(DS['vector'], coverage_page=False)


def s_export_tab():
    d = dock()
    d.toolBox_tabTools.setCurrentIndex(1)
    d.pushButton_checkable_exporting_layers.setChecked(True)
    combo = d.checkableComboBoxLayer_exporting_layers
    wanted = [DS['raster'], DS['vector']] + ([DS['cloud']] if has_point_clouds() else [])
    model = combo.model()
    for row in range(model.rowCount()):
        item = model.item(row)
        if any(item.text().startswith(name + ' [') or item.text() == name for name in wanted):
            item.setCheckState(Qt.CheckState.Checked)
    combo.checkedItemsChangedEvent()
    d.pushButton_checkable_exporting_output_folder.setChecked(True)
    d.lineEdit_exporting_output_folder.setText('export')
    return settled()


def s_export_shot():
    save_dock('export_tab')


def s_config_tab():
    from qgis.PyQt.QtCore import QModelIndex
    from qgis.PyQt.QtWidgets import QAbstractItemView, QTreeView
    d = dock()
    d.toolBox_tabTools.setCurrentIndex(2)
    page = d.toolBox_tabTools.widget(2)
    found = []

    def walk(view, model, parent):
        for row in range(model.rowCount(parent)):
            index = model.index(row, 0, parent)
            if str(model.data(index)) in ('RASTER', 'POINT_CLOUD'):
                found.append((view, index))
            walk(view, model, index)

    for view in page.findChildren(QTreeView):
        view.expandAll()
        model = view.model() if callable(view.model) else view.model
        walk(view, model, QModelIndex())
    if found:
        view, first = min(found, key=lambda pair: pair[1].row() if str((pair[0].model() if callable(pair[0].model) else pair[0].model).data(pair[1])) == 'POINT_CLOUD' else 99)
        view.scrollTo(first, QAbstractItemView.ScrollHint.PositionAtTop)
    check('Configuration tab lists RASTER / POINT_CLOUD options', len(found) >= 2, str(len(found)))
    return settled()


def s_config_shot():
    save_dock('configuration')


def s_finish():
    check('no Python error in the log', not STATE['python_errors'], '; '.join(STATE['python_errors'][:3]))
    failed = [name for status, name in STATE['results'] if status == 'FAIL']
    print(f"\n{len(STATE['results'])} checks, {len(failed)} failed in {time.time() - STATE['started']:.1f}s "
          f"(QGIS {Qgis.QGIS_VERSION}, {'real' if REAL else 'synthetic'} data, images in {OUT})", flush=True)
    if failed:
        print('FAILED: ' + '; '.join(failed), flush=True)
    os._exit(1 if failed else 0)


STEPS = [s_setup, s_open_plugin, s_dock_ready,
         s_vector_source, s_vector_select, s_shot_filtering, s_shot_vector_to_raster, s_save_vector_to_raster,
         s_after_undo,
         s_raster_source, s_raster_select, s_raster_shot, s_raster_filter, s_raster_to_vector, s_raster_save,
         s_raster_settled,
         s_cloud_source, s_cloud_select, s_cloud_shot, s_cloud_to_vector, s_cloud_save, s_cloud_settled,
         s_back_to_vector, s_export_tab, s_export_shot, s_config_tab, s_config_shot, s_finish]


def run_step(index=0):
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
            print(f"   (timeout after {STEP_TIMEOUT:.0f}s at the end of {STEPS[index].__name__})", flush=True)
    QTimer.singleShot(300, lambda: run_step(index + 1))


QTimer.singleShot(2000, run_step)
