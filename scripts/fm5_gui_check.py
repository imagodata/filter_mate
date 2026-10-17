# -*- coding: utf-8 -*-
"""
FilterMate 5 - end-to-end check of the dock in a real QGIS (GUI).

Run with a throw-away profile and the plugin taken from the repository, e.g.

    set QGIS_PLUGINPATH=\\\\wsl.localhost\\Ubuntu\\home\\simon\\dev
    qgis-bin.exe --nologo --lang en --profiles-path %TEMP%\\fm5\\profiles --profile fm5 --code fm5_gui_check.py

Environment variables: ``FM5_DATA`` (folder with mnt_1m.tif, classes_2m.tif),
``FM5_GPKG`` (BD TOPO extract with batiment / parcelle / troncon_de_route),
``FM5_TILE`` (LiDAR HD COPC tile), ``FM5_OUT`` (log and screenshots).

The script drives the real dock: vector source with raster and point cloud
targets, raster source (value range) with vector targets and a minimum
coverage, point cloud source (class 6) with a vector target, undo, unfilter,
exports, then quits QGIS. Every step logs PASS / FAIL in ``fm5_gui.log``.
"""
import os
import traceback

from qgis.PyQt.QtCore import QTimer, Qt
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsFeatureRequest,
    QgsPointCloudLayer,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)
from qgis.utils import iface, plugins

DATA = os.environ.get('FM5_DATA', r'\\wsl.localhost\Ubuntu\home\simon\fm5_testdata')
GPKG = os.environ.get('FM5_GPKG', os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', 'fm5', 'cerdagne.gpkg'))
TILE = os.environ.get('FM5_TILE', r'\\wsl.localhost\Ubuntu\home\simon\dev\ign-lidar-spheron-training\data\raw_tiles'
                                  r'\pyrenees_villages_cerdagne\LHD_FXX_0616_6153_PTS_C_LAMB93_IGN69.copc.laz')
OUT = os.environ.get('FM5_OUT', os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', 'fm5', 'gui'))
os.makedirs(OUT, exist_ok=True)
LOG = os.path.join(OUT, 'fm5_gui.log')
open(LOG, 'w', encoding='utf-8').close()
import faulthandler  # noqa: E402 - native crashes print the Python stack here
_FAULT = open(os.path.join(OUT, 'fm5_gui_fault.log'), 'w')
faulthandler.enable(_FAULT, all_threads=True)
STATE = {'results': []}


def log(message):
    with open(LOG, 'a', encoding='utf-8') as handle:
        handle.write(str(message) + '\n')


def check(name, condition, detail=''):
    STATE['results'].append((name, bool(condition)))
    log(f"{'PASS' if condition else 'FAIL'}  {name}  {detail}")


def on_message(message, tag, level):
    if tag in ('FilterMate', 'Python warning', 'Python error') or level >= Qgis.MessageLevel.Warning:
        if 'FilterMate' in tag or 'Python' in tag or 'FM5' in message:
            log(f"[{tag}:{int(level)}] {message[:600]}")


QgsApplication.messageLog().messageReceived.connect(on_message)


def save(widget, name):
    try:
        widget.grab().save(os.path.join(OUT, name + '.png'), 'PNG')
        log(f'saved {name}')
    except Exception:
        log('save failed ' + name + '\n' + traceback.format_exc())


def dock():
    return plugins['filter_mate'].app.dockwidget


def controller():
    return dock()._controller_integration.coverage_controller


def layer(name):
    return QgsProject.instance().mapLayersByName(name)[0]


def count(vector_layer):
    request = QgsFeatureRequest().setNoAttributes().setFlags(QgsFeatureRequest.Flag.NoGeometry)
    return sum(1 for _ in vector_layer.getFeatures(request))


def set_targets(names):
    combo = dock().checkableComboBoxLayer_filtering_layers_to_filter
    model = combo.model()
    for row in range(model.rowCount()):
        item = model.item(row)
        text = item.text()
        item.setCheckState(Qt.CheckState.Checked if any(text.startswith(n + ' [') for n in names) else Qt.CheckState.Unchecked)
    button = dock().pushButton_checkable_filtering_layers_to_filter
    if not button.isChecked():
        button.setChecked(True)
    log(f"targets: {dock().get_layers_to_filter()}")


def set_predicates(labels):
    d = dock()
    if not d.pushButton_checkable_filtering_geometric_predicates.isChecked():
        d.pushButton_checkable_filtering_geometric_predicates.setChecked(True)
    d.comboBox_filtering_geometric_predicates.setCheckedItems(labels)


def set_buffer(value):
    d = dock()
    if not d.pushButton_checkable_filtering_buffer_value.isChecked():
        d.pushButton_checkable_filtering_buffer_value.setChecked(True)
    d.mQgsDoubleSpinBox_filtering_buffer_value.setValue(value)


def run_task(name):
    dock().launchTaskEvent(False, name)


# --- steps ----------------------------------------------------------------

def s_setup():
    mw = iface.mainWindow()
    mw.showNormal()
    mw.resize(1700, 1000)
    project = QgsProject.instance()
    for name in ('batiment', 'parcelle', 'troncon_de_route'):
        vl = QgsVectorLayer(f'{GPKG}|layername={name}', name, 'ogr')
        project.addMapLayer(vl)
    project.addMapLayer(QgsRasterLayer(os.path.join(DATA, 'mnt_1m.tif'), 'mnt', 'gdal'))
    project.addMapLayer(QgsRasterLayer(os.path.join(DATA, 'classes_2m.tif'), 'classes', 'gdal'))
    project.addMapLayer(QgsPointCloudLayer(TILE, 'lhd', 'copc'))
    iface.mapCanvas().setExtent(layer('mnt').extent())
    check('layers loaded', all(l.isValid() for l in project.mapLayers().values()), str(len(project.mapLayers())))


def s_open_plugin():
    from qgis.PyQt.QtCore import QSettings
    QSettings().setValue('FilterMate/discord_welcome_dismissed', True)  # modal welcome would block the run
    import qgis.utils
    if 'filter_mate' not in plugins:
        ok = qgis.utils.loadPlugin('filter_mate') and qgis.utils.startPlugin('filter_mate')
        log(f'plugin loaded from {qgis.utils.plugins.get("filter_mate").__module__ if ok else "?"}: {ok}')
    plugins['filter_mate'].run()


def s_vector_source():
    d = dock()
    iface.mainWindow().resizeDocks([d], [430], Qt.Orientation.Horizontal)
    # Go through another layer so the targets list is rebuilt once every layer is registered.
    d.comboBox_filtering_current_layer.setLayer(layer('troncon_de_route'))
    QTimer.singleShot(1500, lambda: d.comboBox_filtering_current_layer.setLayer(layer('batiment')))


def s_vector_select():
    d = dock()
    check('vector mode: exploring groups visible', d.mGroupBox_exploring_single_selection.isVisible())
    d.mGroupBox_exploring_single_selection.setChecked(True)
    first = next(layer('batiment').getFeatures(QgsFeatureRequest().setLimit(1)))
    STATE['bat_fid'] = first.id()
    d.mFeaturePickerWidget_exploring_single_selection.setFeature(first.id())
    combo = d.checkableComboBoxLayer_filtering_layers_to_filter
    names = [combo.model().item(r).text() for r in range(combo.model().rowCount())]
    check('targets list includes raster and point cloud', any(n.startswith('mnt [') for n in names) and any(n.startswith('lhd [') for n in names), str(names))
    set_targets(['mnt', 'lhd'])
    set_predicates(['Intersect'])
    set_buffer(5.0)


def s_vector_filter():
    save(dock(), '01-vector-source-before')
    run_task('filter')


def s_vector_check():
    mnt, lhd = layer('mnt'), layer('lhd')
    check('V->R: raster clipped (VRT)', mnt.source().endswith('.vrt'), mnt.source()[-50:])
    check('V->P: point cloud clipped (COPC)', lhd.source().endswith('.copc.laz') and lhd.source() != TILE, f"{lhd.pointCount()} points")
    save(iface.mainWindow(), '02-vector-source-after')


def s_vector_undo():
    run_task('undo')


def s_vector_undo_check():
    check('V undo restores raster', layer('mnt').source().endswith('mnt_1m.tif'), layer('mnt').source()[-40:])
    check('V undo restores point cloud', layer('lhd').source() == TILE)


def s_centroid_setup():
    """Centroids chosen target by target: parcels by their centroids, roads by their full geometry."""
    d = dock()
    set_targets(['parcelle', 'troncon_de_route'])
    set_predicates(['Intersect'])
    if d.pushButton_checkable_filtering_buffer_value.isChecked():
        d.pushButton_checkable_filtering_buffer_value.setChecked(False)
    combo = d.checkableComboBoxLayer_filtering_layers_to_filter
    parcels, roads = layer('parcelle').id(), layer('troncon_de_route').id()
    eligible = combo.centroid_eligible_ids()
    check('centroids: line and polygon targets have a toggle, rasters and point clouds none',
          parcels in eligible and roads in eligible and layer('mnt').id() not in eligible and layer('lhd').id() not in eligible,
          str(eligible))
    combo.set_centroid_layer_ids([parcels], emit=True)
    button = d.checkBox_filtering_use_centroids_distant_layers
    check('centroids: one target of two -> partial button', button.isEnabled()
          and button.checkState() == Qt.CheckState.PartiallyChecked, str(button.checkState()))
    check('centroids: the task gets the chosen targets', d.get_centroid_target_ids() == [parcels], str(d.get_centroid_target_ids()))
    props = d.PROJECT_LAYERS[layer('batiment').id()]['filtering']
    check('centroids: stored on the source layer', props.get('centroid_layers') == [parcels], str(props.get('centroid_layers')))
    button.click()  # partial -> every checked line / polygon target
    check('centroids: the button sets every target', sorted(combo.centroid_layer_ids()) == sorted([parcels, roads])
          and button.checkState() == Qt.CheckState.Checked, str(combo.centroid_layer_ids()))
    button.click()
    check('centroids: and clears them', combo.centroid_layer_ids() == [] and button.checkState() == Qt.CheckState.Unchecked)
    combo.set_centroid_layer_ids([parcels], emit=True)
    save(d, '02b-centroid-targets')


def s_centroid_filter():
    run_task('filter')


def s_centroid_check():
    parcels, roads = layer('parcelle').subsetString(), layer('troncon_de_route').subsetString()
    log(f'parcels subset: {parcels[:400]}')
    log(f'roads subset: {roads[:400]}')
    check('centroids: parcels tested by their centroids', 'PointOnSurface' in parcels or 'Centroid' in parcels, parcels[:120])
    check('centroids: roads tested by their full geometry', roads != '' and 'PointOnSurface' not in roads and 'Centroid' not in roads,
          roads[:120])


def s_centroid_unfilter():
    run_task('unfilter')
    dock().checkableComboBoxLayer_filtering_layers_to_filter.set_centroid_layer_ids([], emit=True)


def s_centroid_unfilter_check():
    check('centroids: unfilter restores the targets', layer('parcelle').subsetString() == ''
          and layer('troncon_de_route').subsetString() == '')
    set_targets([])


def s_raster_source():
    dock().comboBox_filtering_current_layer.setLayer(layer('mnt'))


def s_raster_mode():
    d = dock()
    ctrl = controller()
    check('raster mode active', ctrl.active_layer is not None and ctrl.active_layer.name() == 'mnt')
    check('raster mode: vector groups hidden', not d.mGroupBox_exploring_single_selection.isVisible())
    check('raster mode: raster panel visible', ctrl._raster_panel.isVisible())
    from filter_mate.core.domain.raster_filter_criteria import RasterSelection
    ctrl._raster_panel.set_selection(RasterSelection(band=1, minimum=1240.0, maximum=1270.0))
    set_targets(['parcelle', 'batiment'])
    set_predicates(['Intersect'])
    set_buffer(0.0)
    ctrl._coverage_spin.setValue(50)
    save(d, '03-raster-source-panel')


def s_raster_preview():
    dock().pushButton_checkable_exploring_selecting.setChecked(True)


def s_raster_preview_check():
    from filter_mate.adapters.qgis.coverage_layers.raster_adapter import pixel_is_transparent
    renderer = layer('mnt').renderer()
    pixels = renderer.rasterTransparency().transparentSingleValuePixelList() if renderer.rasterTransparency() else []
    check('raster preview hides pixels outside the range', len(pixels) == 2 and all(pixel_is_transparent(p) for p in pixels),
          str([(p.min, p.max, getattr(p, 'opacity', None)) for p in pixels]))
    save(iface.mainWindow(), '04-raster-preview')
    dock().pushButton_checkable_exploring_selecting.setChecked(False)


def s_raster_filter():
    run_task('filter')


def s_raster_check():
    parcelles, bat, mnt = layer('parcelle'), layer('batiment'), layer('mnt')
    check('R->V: parcels filtered', parcelles.subsetString().startswith('"fid" IN') or parcelles.subsetString() == '1 = 0', f"{count(parcelles)} parcels")
    check('R->V: buildings filtered', 0 <= count(bat) < 134, f"{count(bat)} buildings")
    check('R source masked (virtual raster)', mnt.providerType() == 'virtualraster', mnt.providerType())
    check('raster undo enabled', dock().pushButton_action_undo_filter.isEnabled())
    save(iface.mainWindow(), '05-raster-source-after')


def s_raster_unfilter():
    run_task('unfilter')


def s_raster_unfilter_check():
    check('R unfilter restores all', layer('parcelle').subsetString() == '' and layer('mnt').providerType() == 'gdal'
          and layer('batiment').subsetString() == '')


# --- raster: colour pipette on every kind of raster ---------------------------------

def _cell_point(extent, col, row, size=100):
    from qgis.core import QgsPointXY
    return QgsPointXY(extent.xMinimum() + (col + 0.5) * extent.width() / size, extent.yMaximum() - (row + 0.5) * extent.height() / size)


def s_pipette_ortho():
    import numpy as np
    from osgeo import gdal
    ext = layer('mnt').extent()
    path = os.path.join(OUT, 'ortho_test.tif')
    nx = ny = 100
    pixels = np.zeros((3, ny, nx), 'uint8')
    pixels[0], pixels[1], pixels[2] = 40, 140, 50                              # green field
    pixels[:, 20:40, 20:40] = np.array([20, 120, 200])[:, None, None]          # blue "pool", 400 px
    pixels[:, 60:80, 60:80] = np.array([200, 40, 40])[:, None, None]           # red "roof", 400 px
    ds = gdal.GetDriverByName('GTiff').Create(path, nx, ny, 3, gdal.GDT_Byte)
    ds.SetGeoTransform((ext.xMinimum(), ext.width() / nx, 0, ext.yMaximum(), 0, -ext.height() / ny))
    ds.SetProjection(layer('mnt').crs().toWkt())
    for band in range(3):
        ds.GetRasterBand(band + 1).WriteArray(pixels[band])
    ds.FlushCache()
    ds = None
    QgsProject.instance().addMapLayer(QgsRasterLayer(path, 'ortho', 'gdal'))
    dock().comboBox_filtering_current_layer.setLayer(layer('ortho'))


def _kept(selection, name='ortho'):
    from filter_mate.adapters.qgis.coverage_layers.raster_adapter import read_band_array, selection_virtual_layer
    virtual = selection_virtual_layer(layer(name), selection)
    return int((read_band_array(virtual.dataProvider(), 1, virtual.extent(), 100, 100) == 1).sum())


def s_pipette_ortho_check():
    ctrl = controller()
    panel = ctrl._raster_panel
    ext = layer('mnt').extent()
    button = ctrl._extras._tools['pushButton_checkable_exploring_raster_pipette']
    check('pipette: a rail button, visible on a raster', button.isVisible() and not button.icon().isNull())
    check('pipette: one PIPETTE group holds tolerance, bands and presets', all(
          w.parent() is panel._pipette_group for w in (panel._tolerance_spin, panel._layout_combo, panel._spectral_combo)))
    check('pipette: its group is exclusive like the others', panel._pipette_group.isCheckable()
          and panel._pipette_group in panel._mode_groups.values())
    check('pipette: bands layout and presets usable on a 3-band image', panel._spectral_combo.isEnabled() and panel._layout_combo.isEnabled())
    button.setChecked(True)
    check('pipette: the tool makes its group the active one', panel.active_mode().value == 'pipette'
          and panel._pipette_group.isChecked() and not panel._range_group.isChecked() and not panel._expression_group.isChecked())
    check('pipette: puts the pixel picker on the map', iface.mapCanvas().mapTool() is ctrl._pixel_tool)
    ctrl._on_pixel_picked(_cell_point(ext, 30, 30), False)  # the pool
    selection = panel.selection()
    check('pipette: an image gives a similar-colour selection', selection is not None and selection.mode.value == 'expression'
          and 'abs("ortho@1" - 20)' in selection.expression, (selection.expression if selection else '')[:90])
    check('pipette: the expression group is left alone', panel._expression_edit.text() == '', panel._expression_edit.text()[:60])
    check('pipette: the pool is selected, nothing else', _kept(selection) == 400, str(_kept(selection)))
    ctrl._on_pixel_picked(_cell_point(ext, 70, 70), True)  # Ctrl+click: the roof is added
    check('pipette: Ctrl+click adds the roof (pool + roof)', _kept(panel.selection()) == 800, str(_kept(panel.selection())))
    panel._tolerance_spin.setValue(100.0)  # the whole observed range of each band: the green field too
    check('pipette: the tolerance widens the selection', _kept(panel.selection()) > 800, str(_kept(panel.selection())))
    panel._tolerance_spin.setValue(12.0)
    panel._layout_combo.setCurrentIndex(panel._layout_combo.findData('irc'))
    check('pipette: IRC layout offers the infrared presets', panel._spectral_combo.count() == 4, str(panel._spectral_combo.count()))
    panel._spectral_combo.activated.emit(1)
    check('pipette: a spectral preset is the pipette selection', panel.active_mode().value == 'pipette'
          and '"ortho@1" - "ortho@2"' in panel.selection().expression, panel.selection().expression)


def s_pipette_ortho_shot():
    # A separate step: grabbed in the same event loop turn as the picks, the dock is not laid out yet.
    badge = dock().backend_indicator_label.text()
    check('pipette: the badge still names the raster after a layer was added', 'Raster' in badge, badge)
    save(dock(), '07b-pipette-ortho-panel')
    ctrl = controller()
    ctrl._extras._tools['pushButton_checkable_exploring_raster_pipette'].setChecked(False)
    check('pipette: off leaves the picker', iface.mapCanvas().mapTool() is not ctrl._pixel_tool)


def s_pipette_dem():
    dock().comboBox_filtering_current_layer.setLayer(layer('mnt'))


def s_pipette_dem_check():
    from qgis.core import QgsPointXY
    ctrl = controller()
    panel = ctrl._raster_panel
    ext = layer('mnt').extent()
    check('pipette: bands layout and presets greyed out on a single band', not panel._spectral_combo.isEnabled() and not panel._layout_combo.isEnabled())
    button = ctrl._extras._tools['pushButton_checkable_exploring_raster_pipette']
    panel._tolerance_spin.setValue(5.0)
    button.setChecked(True)
    centre = QgsPointXY(ext.center().x(), ext.center().y())
    from filter_mate.adapters.qgis.coverage_layers.raster_adapter import identify_values
    value = identify_values(layer('mnt'), centre)[1]
    range_before = (panel._low, panel._high)
    ctrl._on_pixel_picked(centre, False)
    low_bound, high_bound = panel._data_bounds()

    def expected(percent):
        """Range value +/- tolerance; a side past the data is open (None), as everywhere in the panel."""
        tol = percent / 100.0 * (high_bound - low_bound)
        return (None if value - tol <= low_bound else value - tol), (None if value + tol >= high_bound else value + tol)

    def same(a, b):
        return (a is None and b is None) or (a is not None and b is not None and abs(a - b) < 0.01)

    selection = panel.selection()
    low, high = expected(5.0)
    check('pipette: a DEM gives value +/- tolerance', selection is not None and selection.mode.value == 'range'
          and same(selection.minimum, low) and same(selection.maximum, high),
          f"{selection.minimum if selection else None}..{selection.maximum if selection else None}, expected {low}..{high} around {value:.2f}")
    panel._tolerance_spin.setValue(10.0)
    selection = panel.selection()
    low, high = expected(10.0)
    check('pipette: the tolerance rewrites the range', same(selection.minimum, low) and same(selection.maximum, high),
          f"{selection.minimum}..{selection.maximum}, expected {low}..{high}")
    check('pipette: the range group is left alone', (panel._low, panel._high) == range_before, f"{range_before} -> {(panel._low, panel._high)}")
    far = QgsPointXY(ext.xMinimum() + ext.width() * 0.1, ext.yMinimum() + ext.height() * 0.1)
    before = (selection.minimum, selection.maximum)
    ctrl._on_pixel_picked(far, True)
    after = panel.selection()
    inf = float('inf')
    lo = lambda v, d: d if v is None else v  # noqa: E731
    widened = (after is None) or (lo(after.minimum, -inf) <= lo(before[0], -inf) and lo(after.maximum, inf) >= lo(before[1], inf)
                                  and (after.minimum, after.maximum) != before)
    check('pipette: Ctrl+click widens the range', widened, f"{before} -> {(after.minimum, after.maximum) if after else None}")
    button.setChecked(False)
    panel._tolerance_spin.setValue(12.0)
    panel.reset()


def s_pipette_classes():
    dock().comboBox_filtering_current_layer.setLayer(layer('classes'))


def s_pipette_classes_check():
    ctrl = controller()
    panel = ctrl._raster_panel
    ext = layer('classes').extent()
    from qgis.core import QgsPointXY
    from filter_mate.adapters.qgis.coverage_layers.raster_adapter import identify_values
    button = ctrl._extras._tools['pushButton_checkable_exploring_raster_pipette']
    button.setChecked(True)
    centre = QgsPointXY(ext.center().x(), ext.center().y())
    value = identify_values(layer('classes'), centre)[1]
    ctrl._on_pixel_picked(centre, False)
    selection = panel.selection()
    if panel._has_classes():
        check('pipette: a classified raster selects the class', selection is not None and selection.mode.value == 'classes'
              and sorted(selection.classes) == [int(round(value))], f"{selection} for {value}")
    else:
        check('pipette: a plain single-band raster gives a range', selection is not None and selection.mode.value == 'range', str(selection))
    button.setChecked(False)
    panel.reset()
    dock().comboBox_filtering_current_layer.setLayer(layer('mnt'))


# --- raster: terrain derivative (slope) --------------------------------------

def s_terrain_source():
    dock().comboBox_filtering_current_layer.setLayer(layer('mnt'))


def s_terrain_mode():
    d, ctrl = dock(), controller()
    panel = ctrl._raster_panel
    check('terrain: raster mode active', ctrl.active_layer is not None and ctrl.active_layer.name() == 'mnt')
    combo = panel._derivative_combo
    names = [combo.itemData(i) for i in range(combo.count())]
    check('terrain: "Compute on" lists every quantity', names == ['value', 'slope_degrees', 'slope_percent',
                                                                  'aspect', 'hillshade', 'roughness'], str(names))
    check('terrain: starts on the pixel value', panel.current_derivative().value == 'value')
    combo.setCurrentIndex(combo.findData('slope_degrees'))  # the user's gesture: the controller sends the histogram
    bounds = panel._data_bounds()
    check('terrain: slope histogram is in degrees (0-90)', bounds == (0.0, 90.0), str(bounds))
    check('terrain: slope presets offered', panel._presets_combo.count() == 5 and panel._presets_combo.isVisibleTo(panel),
          str([panel._presets_combo.itemText(i) for i in range(panel._presets_combo.count())]))
    panel._presets_combo.activated.emit(2)  # "Gentle (5-15 deg)"
    panel._presets_combo.activated.emit(1)  # "Flat (< 5 deg)"
    selection = panel.selection()
    check('terrain: preset becomes a slope selection',
          selection is not None and selection.derivative.value == 'slope_degrees' and selection.maximum == 5.0
          and selection.minimum is None, str(selection))
    check('terrain: preview button stays available, expression button off',
          dock().pushButton_checkable_exploring_selecting.isEnabled() and not panel._use_range_button.isEnabled())
    panel._set_range(None, 15.0)
    panel._emit_now()
    set_targets(['parcelle', 'batiment'])
    set_predicates(['Intersect'])
    set_buffer(0.0)
    ctrl._coverage_spin.setValue(50)
    check('terrain: selection is slope <= 15', panel.selection().maximum == 15.0 and panel.selection().derivative.value == 'slope_degrees')
    save(d, '08-terrain-slope-panel')


def s_terrain_preview():
    dock().pushButton_checkable_exploring_selecting.setChecked(True)


def s_terrain_preview_check():
    ctrl = controller()
    overlay = ctrl._mask_overlay
    check('terrain preview: the veil is on the canvas', overlay is not None and overlay.visible)
    item = overlay._item if overlay is not None else None
    if item is not None:
        rect = item.boundingRect()
        check('terrain preview: veil covers the raster', rect.width() > 10 and rect.height() > 10, f"{rect.width():.0f}x{rect.height():.0f}")
        image = item._image
        veiled = sum(1 for x in range(0, image.width(), 20) for y in range(0, image.height(), 20) if image.pixelColor(x, y).alpha() > 0)
        total = len(range(0, image.width(), 20)) * len(range(0, image.height(), 20))
        check('terrain preview: veils only the steeper half', 0.2 < veiled / total < 0.8, f"{veiled}/{total}")
    check('terrain preview: no value transparency left on the layer', not layer('mnt').renderer().rasterTransparency()
          or not layer('mnt').renderer().rasterTransparency().transparentSingleValuePixelList())
    save(iface.mainWindow(), '08b-terrain-preview')
    dock().pushButton_checkable_exploring_selecting.setChecked(False)


def s_terrain_pick():
    from qgis.core import QgsPointXY
    ctrl = controller()
    check('terrain preview: veil removed when the button is off', ctrl._mask_overlay is None or not ctrl._mask_overlay.visible)
    centre = layer('mnt').extent().center()
    ctrl._on_pixel_picked(QgsPointXY(centre.x(), centre.y()), False)
    panel = ctrl._raster_panel
    text, bands = panel._pixel_value_label.text(), panel._pixel_bands_label.text()
    check('pixel picker: slope in degrees under the click', text.endswith(' °') and 0 <= float(text.split()[0]) <= 90, text)
    check('pixel picker: aspect, hillshade and roughness listed', all(n in bands for n in ('Aspect', 'Hillshade', 'Roughness')), bands.replace(chr(10), ' | '))
    before = (panel._low, panel._high)
    ctrl._on_pixel_picked(QgsPointXY(centre.x() + 40, centre.y() + 40), True)  # Ctrl+click: the range grows to the slope
    check('pixel picker: Ctrl+click extends the range in degrees', (panel._low, panel._high) != before and panel._high is not None
          and panel._high <= 90, f"{before} -> {(panel._low, panel._high)}")
    link = ctrl._extras._tools['pushButton_checkable_exploring_raster_link']
    check('buttons: style link is off while the range applies to a slope', not link.isEnabled() and 'slope' in link.toolTip().lower(), link.toolTip()[:60])
    check('buttons: zoom tooltip names the selected pixels', 'selected pixels' in dock().pushButton_exploring_zoom.toolTip(), dock().pushButton_exploring_zoom.toolTip()[:60])
    panel._set_range(None, 15.0)
    panel._emit_now()


def s_terrain_filter():
    STATE['bat_before'] = count(layer('batiment'))
    run_task('filter')


def s_terrain_check():
    parcelles, bat, mnt = layer('parcelle'), layer('batiment'), layer('mnt')
    check('terrain R->V: buildings filtered by slope', 0 < count(bat) < STATE['bat_before'], f"{count(bat)} of {STATE['bat_before']} buildings")
    check('terrain R->V: parcels filtered by slope', parcelles.subsetString() != '', parcelles.subsetString()[:60])
    check('terrain R source masked through the clipped VRT', mnt.source().endswith('.vrt') or mnt.providerType() == 'virtualraster',
          f"{mnt.providerType()} {mnt.source()[-40:]}")
    check('terrain: undo enabled', dock().pushButton_action_undo_filter.isEnabled())
    save(iface.mainWindow(), '09-terrain-slope-after')


def s_terrain_unfilter():
    run_task('unfilter')


def s_terrain_unfilter_check():
    check('terrain unfilter restores all', layer('parcelle').subsetString() == '' and layer('batiment').subsetString() == ''
          and layer('mnt').source().endswith('mnt_1m.tif'), layer('mnt').source()[-40:])
    panel = controller()._raster_panel
    panel._derivative_combo.setCurrentIndex(0)  # back to the pixel value for the rest of the run
    link = controller()._extras._tools['pushButton_checkable_exploring_raster_link']
    check('buttons: style link is back on the pixel value', link.isEnabled(), link.toolTip()[:60])
    check('terrain: back on the pixel value', panel.current_derivative().value == 'value' and panel._data_bounds()[1] > 90.0,
          str(panel._data_bounds()))


def s_pc_source():
    dock().comboBox_filtering_current_layer.setLayer(layer('lhd'))


def s_pc_mode():
    ctrl = controller()
    check('point cloud mode active', ctrl.active_layer is not None and ctrl.active_layer.name() == 'lhd')
    check('point cloud panel visible', ctrl._pc_panel.isVisible())
    panel = ctrl._pc_panel
    state = panel.state()
    log(f"pc panel state keys: {sorted(state)}")
    try:
        state = dict(state)
        state.update({'classes_enabled': True, 'classes': [6], 'checked_classes': [6]})
        panel.restore_state(state)
    except Exception:
        log(traceback.format_exc())
    log(f"pc expression: {panel.expression()}")
    set_targets(['batiment'])
    set_predicates(['Intersect'])
    controller()._coverage_spin.setValue(10)
    save(dock(), '06-point-cloud-panel')


def s_pc_filter():
    run_task('filter')


def s_pc_check():
    lhd, bat = layer('lhd'), layer('batiment')
    check('P source subset applied', 'Classification' in lhd.subsetString(), lhd.subsetString())
    check('P->V: buildings filtered', 0 < count(bat) <= 134, f"{count(bat)} buildings")
    save(iface.mainWindow(), '07-point-cloud-source-after')


def s_pc_undo():
    run_task('undo')


def s_pc_undo_check():
    check('P undo restores', layer('lhd').subsetString() == '' and layer('batiment').subsetString() == '',
          f"lhd='{layer('lhd').subsetString()}' bat='{layer('batiment').subsetString()[:40]}'")


def s_pc_quick_check():
    panel = controller()._pc_panel
    combo = panel._quick_combo
    texts = [combo.itemText(i) for i in range(combo.count())]
    check('LiDAR classes: quick selection combo', texts[0].startswith('Quick') and 'Invert the selection' in texts, str(texts))
    combo.activated.emit(1)  # Ground
    check('LiDAR classes: "Ground" checks class 2', panel._checked_codes() == [2], str(panel._checked_codes()))
    check('LiDAR classes: summary line', panel._class_summary_label.text().startswith('1 / '), panel._class_summary_label.text())
    combo.activated.emit(combo.count() - 1)  # invert
    check('LiDAR classes: invert', 2 not in panel._checked_codes() and len(panel._checked_codes()) >= 1, str(panel._checked_codes()))
    combo.activated.emit(combo.count() - 2)  # none
    check('LiDAR classes: none', panel._checked_codes() == [])


def s_back_to_vector():
    dock().comboBox_filtering_current_layer.setLayer(layer('troncon_de_route'))


def s_back_to_vector_check():
    d = dock()
    check('back to vector: groups visible again', d.mGroupBox_exploring_single_selection.isVisible())
    check('back to vector: coverage panel hidden', not controller()._host.isVisible())
    save(d, '08-back-to-vector')


def s_export():
    layer('lhd').setSubsetString('Classification = 9')
    STATE['export_task'] = controller().export_coverage_layers([layer('mnt').id(), layer('lhd').id()], OUT, None,
                                                               os.path.join(OUT, 'export.zip'))
    check('export task started', STATE['export_task'] is not None)


def s_export_wait(tries=[0]):
    """Poll until the background export task is done (up to ~3 minutes)."""
    task = STATE.get('export_task')
    tries[0] += 1
    if task is not None and getattr(controller(), 'last_export_results', None) is None and tries[0] < 180:
        QTimer.singleShot(1000, s_export_wait)
        STATE['waiting'] = True
    else:
        STATE['waiting'] = False


def s_export_check():
    results = getattr(controller(), 'last_export_results', None) or []
    check('export raster + point cloud (background task)', len(results) == 2 and all(r.success for r in results),
          str([(r.path, r.message) for r in results]))
    import zipfile
    archive = os.path.join(OUT, 'export_raster_lidar.zip')
    names = zipfile.ZipFile(archive).namelist() if os.path.exists(archive) else []
    check('export zip of raster + point cloud', sorted(names) == ['lhd.laz', 'mnt.tif'], str(names))
    layer('lhd').setSubsetString('')


def s_finish():
    failed = [name for name, ok in STATE['results'] if not ok]
    log(f"\n{len(STATE['results']) - len(failed)}/{len(STATE['results'])} checks passed")
    if failed:
        log('FAILED: ' + '; '.join(failed))
    QgsApplication.instance().quit()


STEPS = [
    (s_setup, 1500), (s_open_plugin, 6000), (s_vector_source, 3000), (s_vector_select, 2000),
    (s_vector_filter, 9000), (s_vector_check, 1000), (s_vector_undo, 3000), (s_vector_undo_check, 1000),
    (s_centroid_setup, 1500), (s_centroid_filter, 9000), (s_centroid_check, 1000), (s_centroid_unfilter, 4000), (s_centroid_unfilter_check, 1000),
    (s_raster_source, 3000), (s_raster_mode, 2500), (s_raster_preview, 1500), (s_raster_preview_check, 1000),
    (s_raster_filter, 8000), (s_raster_check, 1000), (s_raster_unfilter, 3000), (s_raster_unfilter_check, 1000),
    (s_pipette_ortho, 3500), (s_pipette_ortho_check, 1500), (s_pipette_ortho_shot, 1500), (s_pipette_dem, 3000), (s_pipette_dem_check, 1000),
    (s_pipette_classes, 3000), (s_pipette_classes_check, 1000),
    (s_terrain_source, 3000), (s_terrain_mode, 2500), (s_terrain_preview, 2500), (s_terrain_preview_check, 1000), (s_terrain_pick, 1500), (s_terrain_filter, 8000), (s_terrain_check, 1000),
    (s_terrain_unfilter, 3000), (s_terrain_unfilter_check, 1000),
    (s_pc_source, 4000), (s_pc_mode, 2500), (s_pc_filter, 15000), (s_pc_check, 1000),
    (s_pc_undo, 3000), (s_pc_undo_check, 1000), (s_pc_quick_check, 500), (s_back_to_vector, 3000), (s_back_to_vector_check, 1000),
    (s_export, 2000), (s_export_wait, 1000), (s_export_check, 500), (s_finish, 500),
]


STOP_AFTER = os.environ.get('FM5_STOP_AFTER', '')


def run_step(index=0):
    if index >= len(STEPS):
        return
    if STOP_AFTER and index > 0 and STEPS[index - 1][0].__name__ == STOP_AFTER:
        log(f'stopping after {STOP_AFTER}')
        s_finish()
        return
    if STATE.get('waiting'):
        QTimer.singleShot(1000, lambda: run_step(index))
        return
    step, delay = STEPS[index]
    log(f'--- {step.__name__}')
    try:
        step()
    except Exception:
        log('ERROR in ' + step.__name__ + '\n' + traceback.format_exc())
        check(step.__name__ + ' raised', False)
    QTimer.singleShot(delay, lambda: run_step(index + 1))


QTimer.singleShot(4000, run_step)
