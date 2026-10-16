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
    check('terrain: preview stays available, expression button off', panel._preview_check.isEnabled() and not panel._use_range_button.isEnabled())
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
    (s_raster_source, 3000), (s_raster_mode, 2500), (s_raster_preview, 1500), (s_raster_preview_check, 1000),
    (s_raster_filter, 8000), (s_raster_check, 1000), (s_raster_unfilter, 3000), (s_raster_unfilter_check, 1000),
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
