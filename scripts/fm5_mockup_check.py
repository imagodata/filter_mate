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
OUT = os.environ.get('FM_CHECK_OUT') or os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', 'fm5gaps', 'out')
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
    check('vector: no source geometry line under the source layer', hint is None or not hint.isVisible())
    check('vector: tracking button visible', d.pushButton_checkable_exploring_tracking.isVisible())
    STATE['vec_identify'] = d.pushButton_exploring_identify.icon().pixmap(32, 32).toImage()
    from qgis.PyQt.QtWidgets import QLabel as _QLabel
    card = d.findChild(_QLabel, 'label_exploring_coverage_layer')
    check('vector: layer card at the top of EXPLORING', card is not None and card.isVisible() and 'Vector' in card.text()
          and card.mapTo(d, card.rect().topLeft()).y() < d.mGroupBox_exploring_single_selection.mapTo(d, d.mGroupBox_exploring_single_selection.rect().topLeft()).y(),
          card.text() if card else 'missing')
    save('vector')


def s_raster():
    dock().comboBox_filtering_current_layer.setLayer(layer('mnt'))


def s_raster_check():
    d = dock()
    from qgis.PyQt.QtWidgets import QLabel
    card = d.findChild(QLabel, 'label_exploring_coverage_layer')
    check('raster: layer card', card is not None and card.isVisible() and 'band' in card.text(), card.text() if card else 'missing')
    hint = d.findChild(QLabel, 'label_filtering_source_geometry')
    check('raster: no source geometry line', hint is None or not hint.isVisible())
    check('raster: tracking hidden', not d.pushButton_checkable_exploring_tracking.isVisible())
    check('raster: pixel picker icon on the identify button', d.pushButton_exploring_identify.icon().pixmap(32, 32).toImage() != STATE.get('vec_identify'))
    groups = [d.mGroupBox_exploring_single_selection, d.mGroupBox_exploring_multiple_selection, d.mGroupBox_exploring_custom_selection]
    check('raster: only raster groups (no vector group)', not any(g.isVisible() for g in groups) and ctrl()._raster_panel.isVisible()
          and not ctrl()._pc_panel.isVisible())
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


def s_picker():
    d, c = dock(), ctrl()
    iface.actionPan().trigger()
    d.pushButton_exploring_identify.click()
    tool = c._pixel_tool
    centre = iface.mapCanvas().extent().center()
    tool.show_marker(centre)
    c._on_pixel_picked(centre, False)
    c._on_pixel_picked(QgsPointXY(centre.x() + 5, centre.y() + 5), False)


def s_picker_check():
    d, c = dock(), ctrl()
    panel = c._raster_panel
    tool = c._pixel_tool
    check('picker: pipette button held down while active', d.pushButton_exploring_identify.isDown())
    check('picker: pixel group open', not panel._pixel_group.isCollapsed())
    check('picker: picked point marked on the map', tool._marker is not None and tool._marker.isVisible())
    history = panel._pixel_history_label.text()
    check('picker: last picks as a two-column table', '<table' in history and history.count('<tr>') >= 3, history[:80])
    check('picker: value and coordinates on one line',
          abs(panel._pixel_value_label.mapTo(d, panel._pixel_value_label.rect().bottomLeft()).y()
              - panel._pixel_coordinates_label.mapTo(d, panel._pixel_coordinates_label.rect().bottomLeft()).y()) <= 4)
    iface.actionPan().trigger()
    check('picker: marker and held button cleared with another map tool', tool._marker is None and not d.pushButton_exploring_identify.isDown())


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
    check('pc: no source geometry line', hint is None or not hint.isVisible())
    profile, view3d = tool('pushButton_exploring_point_cloud_profile'), tool('pushButton_exploring_point_cloud_3d')
    check('pc: profile tool visible and enabled', profile.isVisible() and profile.isEnabled())
    check('pc: 3D tool visible', view3d.isVisible(), f'enabled={view3d.isEnabled()}')
    vgroups = [d.mGroupBox_exploring_single_selection, d.mGroupBox_exploring_multiple_selection, d.mGroupBox_exploring_custom_selection]
    check('pc: only point cloud groups (no vector, no raster group)', not any(g.isVisible() for g in vgroups)
          and ctrl()._pc_panel.isVisible() and not ctrl()._raster_panel.isVisible())
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
    check('back to vector: vector identify icon back', d.pushButton_exploring_identify.icon().pixmap(32, 32).toImage() == STATE.get('vec_identify'))
    check('back to vector: only vector groups', d.mGroupBox_exploring_single_selection.isVisible() and not ctrl()._host.isVisible())
    check('back to vector: linking visible again', d.pushButton_checkable_exploring_linking_widgets.isVisible())
    check('back to vector: kind tools hidden', not any(b.isVisible() for b in ctrl()._extras._tools.values()))
    card = d.findChild(QLabel, 'label_exploring_coverage_layer')
    check('back to vector: vector layer card', card is not None and card.isVisible() and 'Vector' in card.text(),
          card.text() if card else '')
    hint = d.findChild(QLabel, 'label_filtering_source_geometry')
    check('back to vector: no source geometry line', hint is None or not hint.isVisible())
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
        log(f'gap between FILTERING and EXPORTING: {gap}px (rows spread over the section)')

    tabs = [b for b in d.toolBox_tabTools.findChildren(QAbstractButton) if b.objectName() == 'qt_toolbox_toolboxbutton']
    last = max(tabs, key=lambda b: b.mapTo(d, b.rect().topLeft()).y())
    bar = d.frame_actions
    gap_bottom = bar.mapTo(d, bar.rect().topLeft()).y() - last.mapTo(d, last.rect().bottomLeft()).y()
    log(f'gap above the action bar: {gap_bottom}px (the lower zone is resizable)')


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
    from qgis.PyQt.QtWidgets import QLabel
    card = d.findChild(QLabel, 'label_exploring_coverage_layer')
    first_top = card.mapTo(d, card.rect().topLeft()).y() if card is not None and card.isVisible() else tops[0]
    check('harmony: layer card (or first group) top-aligned with the rail', abs(first_top - rail.mapTo(d, rail.rect().topLeft()).y()) <= 2,
          f'{first_top} vs {rail.mapTo(d, rail.rect().topLeft()).y()}')


def _rect(d, w):
    p = w.mapTo(d, w.rect().topLeft())
    return p.x(), p.y(), p.x() + w.width(), p.y() + w.height()


def _scale():
    from filter_mate.ui.styles.mockup_design import SPACING
    return SPACING['fm_edge'], SPACING['fm_block'], SPACING['fm_gap'], SPACING['fm_band']


def s_spacing_scale():
    """One spacing scale (ui/styles/mockup_design.py SPACING) across the dock, vector layer, FILTERING open."""
    from qgis.PyQt.QtWidgets import QAbstractButton, QLabel
    d = dock()
    page = d.toolBox_tabTools.currentWidget()
    scrolls = page is not None and page.layout() is not None and page.height() < page.layout().sizeHint().height()
    scale_check = (lambda name, ok, detail='': log(f'{name}: skipped, the section scrolls ({detail})')) if scrolls else check
    edge, block, gap, band = _scale()
    page = d.FILTERING
    log(f'dock {d.width()}x{d.height()} toolbox h={d.toolBox_tabTools.height()} max={d.toolBox_tabTools.maximumHeight()} '
        f'page h={page.height()} hint={page.layout().sizeHint().height()} min={page.layout().minimumSize().height()} '
        f'current={d.toolBox_tabTools.currentIndex()} dockMin={d.minimumSizeHint().width()}')
    tabs = sorted((b for b in d.toolBox_tabTools.findChildren(QAbstractButton)
                   if b.objectName() == 'qt_toolbox_toolboxbutton' and b.isVisible()), key=lambda b: _rect(d, b)[1])
    rail, keys = _rect(d, d.widget_exploring_keys), _rect(d, d.widget_filtering_keys)
    groups = [d.mGroupBox_exploring_single_selection, d.mGroupBox_exploring_multiple_selection,
              d.mGroupBox_exploring_custom_selection]
    first, combo, badge = _rect(d, groups[0]), _rect(d, d.comboBox_filtering_geometric_predicates), _rect(d, d.frame_header.findChild(QLabel, 'label_backend_indicator'))
    check('scale: both rails on the dock edge', rail[0] == keys[0] == edge, f'{rail[0]} / {keys[0]} vs {edge}')
    check('scale: rail -> widgets one gap (EXPLORING, FILTERING)', first[0] - rail[2] == gap and combo[0] - keys[2] == gap,
          f'{first[0] - rail[2]} / {combo[0] - keys[2]} vs {gap}')
    rights = {'groups': first[2], 'fields': combo[2], 'sections': _rect(d, tabs[0])[2], 'badges': badge[2]}
    # Groups and fields stop a small margin before the scroll bar; headers and badges reach the dock edge.
    scale_check('scale: one right edge', rights['groups'] == rights['fields'] and rights['sections'] == rights['badges'] == d.width() - edge
          and 4 <= rights['sections'] - rights['fields'] <= 8, str(rights))
    check('scale: section headers on the dock edge', all(_rect(d, t)[0] == edge for t in tabs))
    check('scale: header -> EXPLORING one block', rail[1] - badge[3] == block, f'{rail[1] - badge[3]}')
    check('scale: EXPLORING -> FILTERING header one block', _rect(d, tabs[0])[1] - rail[3] == block,
          f'{_rect(d, tabs[0])[1] - rail[3]}')
    buffer = _rect(d, d.mQgsDoubleSpinBox_filtering_buffer_value)
    check('scale: last FILTERING row -> next header one block', _rect(d, tabs[1])[1] - buffer[3] == block,
          f'{_rect(d, tabs[1])[1] - buffer[3]}')
    scale_check('scale: FILTERING header -> first row one block', _rect(d, d.comboBox_filtering_current_layer)[1] - _rect(d, tabs[0])[3] == block)
    check('scale: collapsed section headers one block apart', _rect(d, tabs[2])[1] - _rect(d, tabs[1])[3] == block)
    check('scale: section headers one band high', all(t.height() == band for t in tabs), str([t.height() for t in tabs]))
    gaps = [_rect(d, groups[i + 1])[1] - _rect(d, groups[i])[3] for i in range(2)]
    check('scale: EXPLORING groups one gap apart', gaps == [gap, gap], str(gaps))
    collapsed = [g.height() for g in groups if g.isCollapsed()]
    check('scale: collapsed groups one band high', collapsed and all(h == band for h in collapsed), str(collapsed))
    from qgis.PyQt.QtWidgets import QWidget
    names = ('comboBox_filtering_current_layer', 'label_filtering_source_geometry',
             'checkableComboBoxLayer_filtering_layers_to_filter', 'comboBox_filtering_source_layer_combine_operator',
             'comboBox_filtering_geometric_predicates', 'mQgsDoubleSpinBox_filtering_buffer_value')
    rows = [getattr(d, n, None) or d.findChild(QWidget, n) for n in names]
    rows = [_rect(d, w) for w in rows if w is not None and w.isVisible()]
    row_gaps = [rows[i + 1][1] - rows[i][3] for i in range(len(rows) - 1)]
    # Rows spread evenly over the section (resizable with the splitter), at least one gap apart.
    check('scale: FILTERING rows evenly spaced', min(row_gaps) >= gap and max(row_gaps) - min(row_gaps) <= 2, str(row_gaps))
    handle = d.splitter_main.handle(1)
    check('scale: splitter handle one block', handle.height() == block, str(handle.height()))


def s_spacing_pc():
    """Point cloud panel on the same scale: card and groups aligned, one gap apart, collapsed = one band."""
    from qgis.PyQt.QtWidgets import QGroupBox
    d = dock()
    edge, block, gap, band = _scale()
    panel = ctrl()._pc_panel
    groups = sorted((g for g in panel.findChildren(QGroupBox) if g.isVisible()), key=lambda g: _rect(d, g)[1])
    card = getattr(d, 'label_exploring_coverage_layer', None)
    lefts = {_rect(d, g)[0] for g in groups} | ({_rect(d, card)[0]} if card is not None and card.isVisible() else set())
    check('scale: panel card and groups share one left edge', len(lefts) == 1, str(lefts))
    gaps = [_rect(d, groups[i + 1])[1] - _rect(d, groups[i])[3] for i in range(len(groups) - 1)]
    check('scale: panel groups one gap apart', gaps and all(g == gap for g in gaps), str(gaps))
    collapsed = [g.height() for g in groups if getattr(g, 'isCollapsed', lambda: False)()]
    check('scale: panel collapsed groups one band high', all(h == band for h in collapsed), str(collapsed))


def s_rail_minimum():
    """The rail spreading must not raise the EXPLORING minimum (it did: the splitter and the dock
    could no longer shrink): the rail minimum stays its buttons plus one gap around each."""
    from qgis.PyQt.QtWidgets import QPushButton
    d = dock()
    edge, block, gap, band = _scale()
    rail = d.widget_exploring_keys
    buttons = sorted((b for b in rail.findChildren(QPushButton) if b.isVisible()), key=lambda b: b.y())
    floor = sum(b.height() for b in buttons) + gap * (len(buttons) + 1)
    minimum = rail.minimumSizeHint().height()
    check('rail: minimum height = buttons + gaps (no ratchet)', minimum <= floor + 2,
          f'min {minimum} vs {floor}, height {rail.height()}')
    gaps = [buttons[0].y()] + [buttons[i + 1].y() - buttons[i].y() - buttons[i].height() for i in range(len(buttons) - 1)] \
        + [rail.height() - buttons[-1].y() - buttons[-1].height()]
    check('rail: tools evenly spread', max(gaps) - min(gaps) <= 2 and min(gaps) >= gap, str(gaps))


def s_badge_gap():
    d = dock()
    badge = d.backend_indicator_label
    badge_bottom = badge.mapTo(d, badge.rect().bottomLeft()).y()
    exploring_top = d.frame_exploring.mapTo(d, d.frame_exploring.rect().topLeft()).y()
    check('header: gap between the source layer badge and EXPLORING', exploring_top - badge_bottom >= 6,
          f'{exploring_top - badge_bottom}px')


def s_source_row():
    d = dock()
    combo = d.comboBox_filtering_current_layer
    button = d.pushButton_checkable_filtering_auto_current_layer
    check('source layer combo and its button: first row of FILTERING',
          d.FILTERING.isAncestorOf(combo) and d.FILTERING.isAncestorOf(button)
          and combo.mapTo(d, combo.rect().topLeft()).y()
          <= d.checkableComboBoxLayer_filtering_layers_to_filter.mapTo(d, d.checkableComboBoxLayer_filtering_layers_to_filter.rect().topLeft()).y())


def s_scrollbar_margin():
    d = dock()
    viewport = d.scrollArea_frame_exploring.viewport()
    right = viewport.mapTo(d, viewport.rect().topRight()).x()
    group = d.mGroupBox_exploring_single_selection
    gap = right - group.mapTo(d, group.rect().topRight()).x()
    check('margin: EXPLORING groups clear of the scroll bar', gap >= 4, f'{gap}px')
    page = d.FILTERING
    page_right = page.mapTo(d, page.rect().topRight()).x()
    other = d.comboBox_filtering_other_layers_combine_operator
    gap2 = page_right - other.mapTo(d, other.rect().topRight()).x()
    check('margin: FILTERING widgets clear of the right edge', gap2 >= 4, f'{gap2}px')


def s_resize_lower():
    d = dock()
    sp = d.splitter_main
    before = sp.sizes()
    total = sum(before)
    sp.setSizes([int(total * 0.3), total - int(total * 0.3)])
    STATE['resize'] = before


def s_resize_lower_check():
    d = dock()
    sp = d.splitter_main
    before = STATE['resize']
    after = sp.sizes()
    check('resize: the lower zone can be enlarged with the splitter', after[1] > before[1] + 20, f'{before} -> {after}')
    rows = [d.comboBox_filtering_current_layer, d.checkableComboBoxLayer_filtering_layers_to_filter,
            d.comboBox_filtering_source_layer_combine_operator, d.comboBox_filtering_geometric_predicates,
            d.mQgsDoubleSpinBox_filtering_buffer_value]
    tops = [w.mapTo(d, w.rect().topLeft()).y() for w in rows]
    gaps = [tops[i + 1] - tops[i] for i in range(len(tops) - 1)]
    check('resize: rows spread over the taller section', max(gaps) - min(gaps) <= 3 and max(gaps) > 48, str(gaps))
    for key, value in (('pushButton_checkable_filtering_layers_to_filter', 'checkableComboBoxLayer_filtering_layers_to_filter'),
                       ('pushButton_checkable_filtering_buffer_value', 'mQgsDoubleSpinBox_filtering_buffer_value')):
        kw, vw = getattr(d, key), getattr(d, value)
        ky, vy = kw.mapTo(d, kw.rect().center()).y(), vw.mapTo(d, vw.rect().center()).y()
        check(f'resize: {key} still in front of its row', abs(ky - vy) <= 2, f'{ky} vs {vy}')
    sp.setSizes(before)


def s_list_grow():
    d = dock()
    group = d.mGroupBox_exploring_multiple_selection
    group.setChecked(True)
    group.setCollapsed(False)
    sp = d.splitter_main
    STATE['grow'] = (sp.sizes(), group.height())
    total = sum(sp.sizes())
    sp.setSizes([int(total * 0.7), total - int(total * 0.7)])


def s_list_grow_check():
    d = dock()
    group = d.mGroupBox_exploring_multiple_selection
    sizes, before = STATE['grow']
    tl = d.verticalLayout_exploring_tabs_content
    from qgis.PyQt.QtWidgets import QSizePolicy
    free = d.scrollArea_frame_exploring.viewport().height() - d.scrollAreaWidgetContents.minimumSizeHint().height()
    check('list group: the expanded multiple selection may take the free height',
          group.sizePolicy().verticalPolicy() == QSizePolicy.Policy.MinimumExpanding and tl.stretch(tl.indexOf(group)) == 1
          and (free <= 0 or group.height() > before), f'{before} -> {group.height()} (free {free}px)')
    d.splitter_main.setSizes(sizes)
    d.mGroupBox_exploring_single_selection.setChecked(True)


def s_font_reload():
    from qgis.PyQt.QtGui import QFontDatabase
    try:
        families = QFontDatabase.families()
    except TypeError:
        families = QFontDatabase().families()
    STATE['plex'] = sum(1 for f in families if 'Plex' in f)
    import qgis.utils
    qgis.utils.reloadPlugin('filter_mate')


def s_font_reload_check():
    from qgis.PyQt.QtGui import QFontDatabase
    try:
        families = QFontDatabase.families()
    except TypeError:
        families = QFontDatabase().families()
    count = sum(1 for f in families if 'Plex' in f)
    check('fonts: a plugin reload does not add IBM Plex again', count == STATE['plex'] and count >= 2, f"{STATE['plex']} -> {count}")


def s_finish():
    failed = [name for name, ok in STATE['results'] if not ok]
    log(f"\n{len(STATE['results']) - len(failed)}/{len(STATE['results'])} checks passed")
    if failed:
        log('FAILED: ' + '; '.join(failed))
    QgsApplication.instance().quit()


STEPS = [(s_setup, 1500), (s_open, 6000), (s_vector, 3500), (s_vector_check, 500), (s_raster, 4000),
         (s_raster_check, 500), (s_hover, 1500), (s_hover_check, 500), (s_zone, 2000), (s_zone_check, 1000), (s_picker, 800), (s_picker_check, 500), (s_handover, 1000), (s_alignment, 500),
         (s_pc, 5000), (s_pc_check, 3000), (s_profile_check, 500), (s_pc_groups, 800), (s_spacing_pc, 300), (s_probe, 500), (s_back, 4000), (s_back_check, 500), (s_alignment, 500), (s_sections_gap, 300), (s_harmony, 300), (s_spacing_scale, 300), (s_rail_minimum, 300), (s_badge_gap, 300), (s_source_row, 300),
         (s_scrollbar_margin, 300), (s_resize_lower, 1500), (s_resize_lower_check, 500),
         (s_list_grow, 1500), (s_list_grow_check, 500), (s_font_reload, 6000), (s_font_reload_check, 500),
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
