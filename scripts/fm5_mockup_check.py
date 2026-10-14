# -*- coding: utf-8 -*-
r"""FilterMate 5 mockup check in a real QGIS (GUI): layer card, kind tools, source geometry line,
map tool handover, FILTERING alignment. Same launch as scripts/fm5_gui_check.py; log in
%LOCALAPPDATA%\Temp\fm5gaps\out\gaps.log."""
import os
import traceback

from qgis.PyQt.QtCore import QTimer, Qt
from qgis.core import QgsApplication, QgsPointCloudLayer, QgsPointXY, QgsProject, QgsRasterLayer, QgsRectangle, QgsVectorLayer, Qgis
from qgis.utils import iface, plugins

DATA = r'\\wsl.localhost\Ubuntu\home\simon\fm5_testdata'
GPKG = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', 'fm5', 'cerdagne.gpkg')
TILE = (r'\\wsl.localhost\Ubuntu\home\simon\dev\ign-lidar-spheron-training\data\raw_tiles'
        r'\pyrenees_villages_cerdagne\LHD_FXX_0616_6153_PTS_C_LAMB93_IGN69.copc.laz')
OUT = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', 'fm5gaps', 'out')
os.makedirs(OUT, exist_ok=True)
LOG = os.path.join(OUT, 'gaps.log')
open(LOG, 'w', encoding='utf-8').close()
STATE = {'results': []}


def log(message):
    with open(LOG, 'a', encoding='utf-8') as handle:
        handle.write(str(message) + '\n')


def check(name, condition, detail=''):
    STATE['results'].append((name, bool(condition)))
    log(f"{'PASS' if condition else 'FAIL'}  {name}  {detail}")


def on_message(message, tag, level):
    if ('FilterMate' in tag or 'Python' in tag) and level >= Qgis.MessageLevel.Warning:
        log(f"[{tag}:{int(level)}] {message[:800]}")


QgsApplication.messageLog().messageReceived.connect(on_message)


def dock():
    return plugins['filter_mate'].app.dockwidget


def ctrl():
    return dock()._controller_integration.coverage_controller


def layer(name):
    return QgsProject.instance().mapLayersByName(name)[0]


def tool(name):
    return ctrl()._extras._tools.get(name)


def save(name):
    try:
        dock().grab().save(os.path.join(OUT, name + '.png'), 'PNG')
    except Exception:
        log('save failed ' + traceback.format_exc())


def s_setup():
    mw = iface.mainWindow()
    mw.showNormal()
    mw.resize(1700, 1100)
    project = QgsProject.instance()
    for name in ('batiment', 'parcelle'):
        project.addMapLayer(QgsVectorLayer(f'{GPKG}|layername={name}', name, 'ogr'))
    project.addMapLayer(QgsRasterLayer(os.path.join(DATA, 'mnt_1m.tif'), 'mnt', 'gdal'))
    project.addMapLayer(QgsPointCloudLayer(TILE, 'lhd', 'copc'))
    iface.mapCanvas().setExtent(layer('mnt').extent())
    check('layers loaded', all(l.isValid() for l in project.mapLayers().values()), str(len(project.mapLayers())))


def s_open():
    import qgis.utils
    if 'filter_mate' not in plugins:
        ok = qgis.utils.loadPlugin('filter_mate') and qgis.utils.startPlugin('filter_mate')
        log(f'plugin loaded: {ok} from {qgis.utils.plugins["filter_mate"].__class__.__module__}')
    plugins['filter_mate'].run()


def s_vector():
    d = dock()
    iface.mainWindow().resizeDocks([d], [440], Qt.Orientation.Horizontal)
    d.comboBox_filtering_current_layer.setLayer(layer('parcelle'))
    QTimer.singleShot(1500, lambda: d.comboBox_filtering_current_layer.setLayer(layer('batiment')))


def s_vector_check():
    d = dock()
    hint = d.findChild(type(d.label_filtering_current_layer) if hasattr(d, 'label_filtering_current_layer') else object,
                       'label_filtering_source_geometry') if False else None
    from qgis.PyQt.QtWidgets import QLabel
    hint = d.findChild(QLabel, 'label_filtering_source_geometry')
    check('vector: source geometry line', hint is not None and hint.isVisible() and 'features' in hint.text(),
          hint.text() if hint else 'missing')
    check('vector: tracking button visible', d.pushButton_checkable_exploring_tracking.isVisible())
    save('vector')


def s_raster():
    dock().comboBox_filtering_current_layer.setLayer(layer('mnt'))


def s_raster_check():
    d = dock()
    from qgis.PyQt.QtWidgets import QLabel
    card = d.findChild(QLabel, 'label_exploring_coverage_layer')
    check('raster: layer card', card is not None and card.isVisible() and 'band' in card.text(), card.text() if card else 'missing')
    hint = d.findChild(QLabel, 'label_filtering_source_geometry')
    check('raster: source geometry line', hint is not None and 'pixels' in hint.text(), hint.text() if hint else '')
    check('raster: tracking hidden', not d.pushButton_checkable_exploring_tracking.isVisible())
    check('raster: linking hidden', not d.pushButton_checkable_exploring_linking_widgets.isVisible())
    hover, zone = tool('pushButton_checkable_exploring_raster_hover'), tool('pushButton_checkable_exploring_raster_zone')
    check('raster: hover tool visible', hover is not None and hover.isVisible())
    check('raster: zone tool visible', zone is not None and zone.isVisible())
    check('raster: hover icon drawn', hover is not None and not hover.icon().isNull())
    check('raster: pc tools hidden', not tool('pushButton_exploring_point_cloud_profile').isVisible())
    rail = [w.objectName() for w in d.pushButton_exploring_identify.parentWidget().findChildren(type(hover))
            if w.isVisible() and w.geometry().x() < 80]
    log('visible rail buttons: ' + ', '.join(rail))
    save('raster')


def s_hover():
    hover = tool('pushButton_checkable_exploring_raster_hover')
    hover.setChecked(True)
    centre = iface.mapCanvas().extent().center()
    iface.mapCanvas().xyCoordinates.emit(QgsPointXY(centre))


def s_hover_check():
    panel = ctrl()._raster_panel
    label = panel._hover_label
    check('raster: value under the cursor shown', not label.isHidden() and 'Under the cursor' in label.text(),
          f'{label.text()!r} hidden={label.isHidden()} collapsed={getattr(panel._pixel_group, "isCollapsed", lambda: None)()} '
          f'connected={ctrl()._extras._hover_connected}')
    tool('pushButton_checkable_exploring_raster_hover').setChecked(False)
    check('raster: hover line hidden when off', not label.isVisible())


def s_zone():
    zone = tool('pushButton_checkable_exploring_raster_zone')
    zone.setChecked(True)
    extras = ctrl()._extras
    check('raster: rectangle map tool active', iface.mapCanvas().mapTool() is extras._zone_tool)
    extent = iface.mapCanvas().extent()
    small = QgsRectangle(extent.center().x() - 100, extent.center().y() - 100, extent.center().x() + 100, extent.center().y() + 100)
    extras._on_zone_drawn(small)


def s_zone_check():
    panel = ctrl()._raster_panel
    check('raster: zone statistics shown', panel._zone_label.isVisible() and 'min' in panel._zone_label.text(), panel._zone_label.text())
    save('raster_tools')
    iface.actionPan().trigger()
    check('raster: zone button follows another map tool', not tool('pushButton_checkable_exploring_raster_zone').isChecked())


def s_handover():
    canvas = iface.mapCanvas()
    iface.actionPan().trigger()
    pan = canvas.mapTool()
    d, c = dock(), ctrl()
    zone = tool('pushButton_checkable_exploring_raster_zone')
    d.pushButton_exploring_identify.click()
    check('handover: pixel picker on', canvas.mapTool() is c._pixel_tool)
    zone.setChecked(True)
    check('handover: zone on over picker', canvas.mapTool() is c._extras._zone_tool)
    zone.setChecked(False)
    check('handover: zone off restores pan, not the picker', canvas.mapTool() is pan, type(canvas.mapTool()).__name__)
    zone.setChecked(True)
    d.pushButton_exploring_identify.click()
    check('handover: picker over zone, button follows', canvas.mapTool() is c._pixel_tool and not zone.isChecked())
    d.pushButton_exploring_identify.click()
    check('handover: picker off restores pan, not the zone tool', canvas.mapTool() is pan, type(canvas.mapTool()).__name__)


def s_alignment():
    d = dock()
    pairs = [('pushButton_checkable_filtering_layers_to_filter', 'checkableComboBoxLayer_filtering_layers_to_filter'),
             ('pushButton_checkable_filtering_geometric_predicates', 'comboBox_filtering_geometric_predicates'),
             ('pushButton_checkable_filtering_buffer_value', 'mQgsDoubleSpinBox_filtering_buffer_value')]
    for key, value in pairs:
        kw, vw = getattr(d, key, None), getattr(d, value, None)
        if kw is None or vw is None:
            log(f'alignment: {key}/{value} missing')
            continue
        ky = kw.mapTo(d, kw.rect().center()).y()
        vy = vw.mapTo(d, vw.rect().center()).y()
        check(f'alignment {key}', abs(ky - vy) <= 2, f'{ky} vs {vy}')


def s_pc():
    dock().comboBox_filtering_current_layer.setLayer(layer('lhd'))


def s_pc_check():
    d = dock()
    from qgis.PyQt.QtWidgets import QLabel
    card = d.findChild(QLabel, 'label_exploring_coverage_layer')
    check('pc: layer card', card is not None and 'points' in card.text(), card.text() if card else '')
    hint = d.findChild(QLabel, 'label_filtering_source_geometry')
    check('pc: source geometry line', hint is not None and 'footprint' in hint.text(), hint.text() if hint else '')
    profile, view3d = tool('pushButton_exploring_point_cloud_profile'), tool('pushButton_exploring_point_cloud_3d')
    check('pc: profile tool visible and enabled', profile.isVisible() and profile.isEnabled())
    check('pc: 3D tool visible', view3d.isVisible(), f'enabled={view3d.isEnabled()}')
    check('pc: raster tools hidden', not tool('pushButton_checkable_exploring_raster_hover').isVisible())
    save('point_cloud')
    host = ctrl()._host
    check('pc: panel fits the dock (no sideways scroll)', host.parentWidget().width() <= host.parentWidget().parentWidget().width() + 2, f'{host.parentWidget().width()} vs {host.parentWidget().parentWidget().width()}')
    profile.click()


def s_pc_groups():
    pc = ctrl()._pc_panel
    classes, ranges, expression = pc._classes_group, pc._ranges_group, pc._expression_group
    ranges.setChecked(True)
    check('pc groups: checking ranges unchecks classes', ranges.isChecked() and not classes.isChecked() and not expression.isChecked())
    check('pc groups: inactive groups collapsed', classes.isCollapsed() and expression.isCollapsed() and not ranges.isCollapsed())
    ranges.setChecked(False)
    check('pc groups: the active group cannot be unchecked', ranges.isChecked())
    expression.setCollapsed(False)
    check('pc groups: expanding a group activates it', expression.isChecked() and not ranges.isChecked())
    classes.setChecked(True)
    check('pc groups: back to classes', classes.isChecked() and not expression.isChecked())


def s_profile_check():
    from qgis.PyQt.QtWidgets import QDockWidget
    docks = [w.windowTitle() for w in iface.mainWindow().findChildren(QDockWidget) if w.isVisible()]
    check('pc: elevation profile opened', any('Elevation' in t or 'Profil' in t for t in docks), ', '.join(docks))


def s_back():
    dock().comboBox_filtering_current_layer.setLayer(layer('batiment'))


def s_back_check():
    d = dock()
    from qgis.PyQt.QtWidgets import QLabel
    check('back to vector: tracking visible again', d.pushButton_checkable_exploring_tracking.isVisible())
    check('back to vector: linking visible again', d.pushButton_checkable_exploring_linking_widgets.isVisible())
    check('back to vector: kind tools hidden', not any(b.isVisible() for b in ctrl()._extras._tools.values()))
    card = d.findChild(QLabel, 'label_exploring_coverage_layer')
    check('back to vector: card hidden', card is None or not card.isVisible())
    hint = d.findChild(QLabel, 'label_filtering_source_geometry')
    check('back to vector: vector source line', hint is not None and 'features' in hint.text())
    save('vector_back')


def s_probe():
    from qgis.PyQt.QtGui import QAction
    names = sorted({(a.objectName(), a.text()) for a in iface.mainWindow().findChildren(QAction)
                    if '3d' in (a.objectName() + a.text()).lower()})
    log('3D actions: ' + repr(names))
    d = dock()
    rail = d.pushButton_exploring_identify.parentWidget()
    rail.grab().save(os.path.join(OUT, 'rail.png'), 'PNG')
    layout = ctrl()._find_parent_layout(d.pushButton_exploring_identify)
    log('rail order: ' + ', '.join(layout.itemAt(i).widget().objectName() if layout.itemAt(i).widget() else '-' for i in range(layout.count())))
    for name in ('_raster_panel', '_pc_panel'):
        panel = getattr(ctrl(), name)
        log(f'{name}: minimumSizeHint={panel.minimumSizeHint().width()} width={panel.width()} host={ctrl()._host.width()}')
    w = ctrl()._host.parentWidget()
    chain = []
    while w is not None and len(chain) < 8:
        chain.append(f'{w.objectName() or type(w).__name__}:{w.width()}')
        w = w.parentWidget()
    log('host chain: ' + ' < '.join(chain))

    from qgis.PyQt.QtWidgets import QWidget
    pc = ctrl()._raster_panel
    for child in pc.findChildren(QWidget):
        hint = child.minimumSizeHint().width()
        if hint > 200:
            log(f'  wide: {type(child).__name__} {child.objectName()!r} {getattr(child, "text", lambda: "")()!r} min={hint} parent={child.parentWidget().objectName()!r}')


def s_sections_gap():
    from qgis.PyQt.QtWidgets import QAbstractButton
    d = dock()
    tabs = [b for b in d.toolBox_tabTools.findChildren(QAbstractButton) if b.objectName() == 'qt_toolbox_toolboxbutton']
    exporting = [b for b in tabs if 'EXPORT' in b.text().upper()]
    row = d.mQgsDoubleSpinBox_filtering_buffer_value
    if exporting:
        gap = exporting[0].mapTo(d, exporting[0].rect().topLeft()).y() - row.mapTo(d, row.rect().bottomLeft()).y()
        check('sections: no blank between FILTERING and EXPORTING', gap <= 24, f'{gap}px')

    tabs = [b for b in d.toolBox_tabTools.findChildren(QAbstractButton) if b.objectName() == 'qt_toolbox_toolboxbutton']
    last = max(tabs, key=lambda b: b.mapTo(d, b.rect().topLeft()).y())
    bar = d.frame_actions
    gap_bottom = bar.mapTo(d, bar.rect().topLeft()).y() - last.mapTo(d, last.rect().bottomLeft()).y()
    check('sections: no blank above the action bar', gap_bottom <= 24, f'{gap_bottom}px')


def s_harmony():
    d = dock()
    ref = d.comboBox_filtering_current_layer.height()
    for n in ('comboBox_filtering_geometric_predicates', 'mQgsDoubleSpinBox_filtering_buffer_value',
              'comboBox_filtering_buffer_type', 'mQgsSpinBox_filtering_buffer_segments',
              'comboBox_filtering_source_layer_combine_operator'):
        w = getattr(d, n)
        check(f'harmony: {n} height = source combo', abs(w.height() - ref) <= 1, f'{w.height()} vs {ref}')
    spin = d.mQgsDoubleSpinBox_filtering_buffer_value
    combo = d.comboBox_filtering_current_layer
    check('harmony: buffer row starts at the values edge', abs(spin.mapTo(d, spin.rect().topLeft()).x() - combo.mapTo(d, combo.rect().topLeft()).x()) <= 1)
    groups = [d.mGroupBox_exploring_single_selection, d.mGroupBox_exploring_multiple_selection, d.mGroupBox_exploring_custom_selection]
    tops = [g.mapTo(d, g.rect().topLeft()).y() for g in groups]
    gaps = [tops[i + 1] - (tops[i] + groups[i].height()) for i in range(2)]
    check('harmony: even gaps between EXPLORING groups', abs(gaps[0] - gaps[1]) <= 1, str(gaps))
    rail = d.widget_exploring_keys
    check('harmony: first group top-aligned with the rail', abs(tops[0] - rail.mapTo(d, rail.rect().topLeft()).y()) <= 2,
          f'{tops[0]} vs {rail.mapTo(d, rail.rect().topLeft()).y()}')


def s_finish():
    failed = [name for name, ok in STATE['results'] if not ok]
    log(f"\n{len(STATE['results']) - len(failed)}/{len(STATE['results'])} checks passed")
    if failed:
        log('FAILED: ' + '; '.join(failed))
    QgsApplication.instance().quit()


STEPS = [(s_setup, 1500), (s_open, 6000), (s_vector, 3500), (s_vector_check, 500), (s_raster, 4000),
         (s_raster_check, 500), (s_hover, 1500), (s_hover_check, 500), (s_zone, 2000), (s_zone_check, 1000), (s_handover, 1000), (s_alignment, 500),
         (s_pc, 5000), (s_pc_check, 3000), (s_profile_check, 500), (s_pc_groups, 800), (s_probe, 500), (s_back, 4000), (s_back_check, 500), (s_alignment, 500), (s_sections_gap, 300), (s_harmony, 300),
         (s_finish, 500)]


def run_step(index=0):
    if index >= len(STEPS):
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
