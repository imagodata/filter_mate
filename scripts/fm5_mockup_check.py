# -*- coding: utf-8 -*-
r"""FilterMate 5 mockup check in a real QGIS (GUI): layer card, kind tools, selection strip, target hints,
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
    if os.environ.get('FM_THEME', '').lower() == 'dark':  # dark dock: the QGIS Night Mapping theme
        QgsApplication.instance().setUITheme('Night Mapping')
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
    from qgis.PyQt.QtCore import QSettings
    QSettings().setValue('FilterMate/discord_welcome_dismissed', True)  # modal welcome would block the run
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


def strip():
    from qgis.PyQt.QtWidgets import QFrame
    return dock().findChild(QFrame, 'frame_selection_strip')


def strip_text():
    found = strip()
    return '' if found is None else f"{found.kind()} | {found.caption()} | {found.value()}"


def s_strip_vector():
    d, found = dock(), strip()
    check('strip: shown for a vector source', found is not None and found.isVisible() and found.kind() == 'vector',
          strip_text())
    if found is not None:
        top = found.mapTo(d, found.rect().topLeft()).y()
        bottom = found.mapTo(d, found.rect().bottomLeft()).y()
        groups = d.scrollArea_frame_exploring
        exploring = groups.mapTo(d, groups.rect().bottomLeft()).y()
        sections = d.toolBox_tabTools.mapTo(d, d.toolBox_tabTools.rect().topLeft()).y()
        check('strip: under the EXPLORING groups, above the FILTERING header', exploring <= top and bottom < sections,
              f'groups end {exploring}, strip {top}-{bottom}, sections {sections}')
    combo = d.checkableComboBoxLayer_filtering_layers_to_filter
    hints = {}
    for row in range(combo.count()):
        item = combo.model().item(row)
        hints[item.text().split(' [')[0]] = item.data(0x0101)
    check('targets: one hint per layer kind', hints.get('parcelle') == 'features' and hints.get('mnt') == 'pixels in the zone'
          and hints.get('lhd') == 'points in the zone', str(hints))
    for name, beside in (('checkBox_filtering_use_centroids_distant_layers', combo),
                         ('checkBox_filtering_use_centroids_source_layer', d.comboBox_filtering_current_layer)):
        button = getattr(d, name)
        check(f'centroid button {name[29:]}: square, as high as its combo',
              button.width() == button.height() and abs(button.height() - beside.height()) <= 1
              and abs(button.mapTo(d, button.rect().center()).y() - beside.mapTo(d, beside.rect().center()).y()) <= 1,
              f'{button.width()}x{button.height()} vs {beside.height()}')
    exporting = d.checkableComboBoxLayer_exporting_layers
    check('targets: no hint in EXPORTING',
          all(exporting.model().item(row).data(0x0101) is None for row in range(exporting.count())))
    d._force_exploring_groupbox_exclusive('multiple_selection')
    d._configure_multiple_selection_groupbox()
    picker = d.widgets['EXPLORING']['MULTIPLE_SELECTION_FEATURES']['WIDGET']
    items = picker.list_widgets.get(d.current_layer.id()) if hasattr(picker, 'list_widgets') else None
    STATE['strip_items'] = items
    if items is not None:
        for row in range(min(2, items.count())):
            items.item(row).setCheckState(Qt.CheckState.Checked)
    d.refresh_selection_strip()


def s_strip_vector_count():
    items = STATE.get('strip_items')
    expected = min(2, items.count()) if items is not None else -1
    check('strip: counts the features checked in multiple selection', strip_text().endswith(f'{expected} feature(s)'),
          strip_text())
    save('strip_vector')
    if items is not None:
        for row in range(items.count()):
            items.item(row).setCheckState(Qt.CheckState.Unchecked)
    d = dock()
    d._force_exploring_groupbox_exclusive('single_selection')  # the following checks expect the default group
    d._configure_single_selection_groupbox()


def s_targets_popup():
    d = dock()
    combo = d.checkableComboBoxLayer_filtering_layers_to_filter
    STATE['popup_centroids'] = combo.centroid_layer_ids()
    combo.set_centroid_layer_ids([layer('parcelle').id()])
    combo.showPopup()


def s_targets_popup_shot():
    d = dock()
    combo = d.checkableComboBoxLayer_filtering_layers_to_filter
    try:
        combo.view().window().grab().save(os.path.join(OUT, 'targets_popup.png'), 'PNG')
    except Exception:
        log('popup grab failed ' + traceback.format_exc())
    rows = {combo.model().item(r).text().split(' [')[0]: combo.model().item(r).data(0x0102) for r in range(combo.count())}
    check('targets: centroid toggle on the polygon target only', rows.get('parcelle') is True and rows.get('mnt') is None
          and rows.get('lhd') is None, str(rows))
    combo.hidePopup()
    combo.set_centroid_layer_ids(STATE.get('popup_centroids', []))


def s_strip_raster():
    found = strip()
    check('strip: raster range and share of pixels', found is not None and found.isVisible() and found.kind() == 'raster'
          and '–' in found.value() and '%' in found.value(), strip_text())


def s_strip_pc():
    found = strip()
    check('strip: point cloud kept points', found is not None and found.isVisible() and found.kind() == 'point_cloud'
          and found.caption() == 'Kept points', strip_text())
    panel = ctrl()._pc_panel
    panel._classes_group.setChecked(True)
    codes = panel._present_codes()
    panel._check_codes(codes[:1])
    STATE['strip_pc_code'] = codes[:1]


def s_strip_pc_count():
    panel = ctrl()._pc_panel
    kept, total = panel.class_point_counts()
    log(f'pc class summary: {panel._class_summary_label.text()} -> {kept} / {total}')
    if kept is not None:
        check('strip: checked classes counted', '/' in strip().value() and '%' in strip().value(), strip_text())
    else:  # no point count per class in the layer statistics: the criteria are shown
        check('strip: uncounted classes show the criteria', strip().value() == panel.expression().strip(), strip_text())
    save('strip_point_cloud')
    ctrl()._pc_panel.reset()


def s_strip_back():
    check('strip: back to the vector colours', strip() is not None and strip().kind() == 'vector', strip_text())


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
    pipette = tool('pushButton_checkable_exploring_raster_pipette')
    check('raster: pipette tool visible with its icon', pipette is not None and pipette.isVisible() and not pipette.icon().isNull())
    link = tool('pushButton_checkable_exploring_raster_link')
    check('raster: style link on the rail, its icon drawn', link is not None and link.isVisible() and not link.icon().isNull())
    check('raster: no other extra tool on the rail (hover, statistics) nor the point cloud ones',
          all(tool(n) is None or not tool(n).isVisible() for n in (
              'pushButton_checkable_exploring_raster_hover', 'pushButton_checkable_exploring_raster_zone',
              'pushButton_checkable_exploring_point_cloud_pipette',
              'pushButton_exploring_point_cloud_profile', 'pushButton_exploring_point_cloud_3d')))
    rail = [w.objectName() for w in d.pushButton_exploring_identify.parentWidget().findChildren(type(d.pushButton_exploring_identify))
            if w.isVisible() and w.geometry().x() < 80]
    log('visible rail buttons: ' + ', '.join(rail))
    save('raster')


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


def s_raster_tools():
    from qgis.PyQt.QtWidgets import QAbstractButton
    d, c = dock(), ctrl()
    panel = c._raster_panel
    layer = c.active_layer
    STATE['raster_extent'] = iface.mapCanvas().extent()
    low, high = panel._data_bounds()
    STATE['range'] = (low + (high - low) * 0.4, low + (high - low) * 0.6)
    panel._set_range(*STATE['range'])
    panel._emit_now()
    STATE['style_before'] = layer.renderer().type()
    link = d.findChild(QAbstractButton, 'pushButton_checkable_exploring_raster_link')
    STATE['link_visible'] = link is not None and link.isVisible()
    if link is not None:
        link.setChecked(True)
    d.pushButton_exploring_zoom.click()


def _style_range(layer):
    renderer = layer.renderer()
    kind = renderer.type()
    if kind == 'singlebandgray':
        enhancement = renderer.contrastEnhancement()
        return enhancement.minimumValue(), enhancement.maximumValue()
    if kind == 'singlebandpseudocolor':
        return renderer.classificationMin(), renderer.classificationMax()
    return None, None


def s_raster_tools_check():
    from qgis.PyQt.QtWidgets import QAbstractButton
    d, c = dock(), ctrl()
    layer = c.active_layer
    low, high = STATE['range']
    check('raster tools: link button in the raster rail', STATE['link_visible'])
    style_low, style_high = _style_range(layer)
    check('raster tools: the style stretches over the selected range',
          style_low is not None and abs(style_low - low) < 1e-6 and abs(style_high - high) < 1e-6,
          f'{style_low}..{style_high} vs {low}..{high} ({layer.renderer().type()})')
    canvas_extent = iface.mapCanvas().extent()
    before = STATE['raster_extent']
    check('raster tools: zoom frames the selected range (not the whole layer)',
          canvas_extent.width() <= layer.extent().width() * 1.06, f'{before.width():.0f} -> {canvas_extent.width():.0f}')
    import tempfile
    from xml.dom import minidom
    saved = os.path.join(tempfile.gettempdir(), 'fm5_rail_link.qgs')
    QgsProject.instance().write(saved)
    QgsProject.instance().setFileName('')
    QgsProject.instance().setDirty(False)
    written = None
    for node in minidom.parse(saved).getElementsByTagName('maplayer'):
        ids = node.getElementsByTagName('id')
        if ids and ids[0].firstChild.data == layer.id():
            enhancement = node.getElementsByTagName('contrastEnhancement')
            if enhancement:
                written = float(enhancement[0].getElementsByTagName('minValue')[0].firstChild.data)
    check('raster tools: a saved project keeps the style from before the link',
          written is not None and abs(written - low) > 1e-6, f'written min {written} vs linked {low}')
    link = d.findChild(QAbstractButton, 'pushButton_checkable_exploring_raster_link')
    if link is not None:
        link.setChecked(False)
    restored = _style_range(layer)
    check('raster tools: unlinking gives the style back', restored != (low, high) and layer.renderer().type() == STATE['style_before'],
          str(restored))


def s_handover():
    canvas = iface.mapCanvas()
    iface.actionPan().trigger()
    pan = canvas.mapTool()
    d, c = dock(), ctrl()
    d.pushButton_exploring_identify.click()
    check('handover: pixel picker on', canvas.mapTool() is c._pixel_tool)
    d.pushButton_exploring_identify.click()
    check('handover: picker off restores pan', canvas.mapTool() is pan, type(canvas.mapTool()).__name__)
    d.pushButton_exploring_identify.click()
    iface.actionPan().trigger()  # QGIS now remembers the picker as the tool to give back
    STATE['old_picker'] = c._pixel_tool


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


def s_pc_pipette():
    canvas = iface.mapCanvas()
    iface.actionPan().trigger()
    STATE['pan'] = canvas.mapTool()
    c = ctrl()
    pipette = tool('pushButton_checkable_exploring_point_cloud_pipette')
    pipette.setChecked(True)
    check('pc pipette: the class picker is on the map', canvas.mapTool() is c._class_tool and c._class_tool is not None)
    STATE['pc_extent'] = canvas.extent()
    from qgis.core import QgsCoordinateTransform
    lhd = layer('lhd')
    centre = lhd.extent().center()
    to_map = QgsCoordinateTransform(lhd.crs(), canvas.mapSettings().destinationCrs(), QgsProject.instance())
    canvas.setExtent(to_map.transformBoundingBox(QgsRectangle(centre.x() - 100, centre.y() - 100, centre.x() + 100, centre.y() + 100)))
    STATE['pc_click'] = to_map.transform(centre)
    canvas.refresh()


def s_pc_pipette_check():
    canvas, c = iface.mapCanvas(), ctrl()
    panel = c._pc_panel
    panel._check_codes(())
    c._on_class_picked(STATE['pc_click'], False)
    picked = panel._checked_codes()
    check('pc pipette: a click checks one class', len(picked) == 1 and panel._classes_group.isChecked(), str(picked))
    others = [code for code in panel._present_codes() if code not in picked]
    if others:
        panel.select_class(others[0], extend=True)
        check('pc pipette: Ctrl+click adds a class', panel._checked_codes() == sorted(picked + others[:1]), str(panel._checked_codes()))
    pipette = tool('pushButton_checkable_exploring_point_cloud_pipette')
    pipette.setChecked(False)
    check('pc pipette: off gives the map back to pan', canvas.mapTool() is STATE['pan'], type(canvas.mapTool()).__name__)
    pipette.setChecked(True)
    iface.actionPan().trigger()
    check('pc pipette: button follows another map tool', not pipette.isChecked())
    canvas.setMapTool(c._class_tool)  # what a right click after Pan does
    check('pc pipette: button down again when QGIS gives the tool back', pipette.isChecked())
    pipette.setChecked(False)
    iface.actionPan().trigger()
    panel.reset()
    canvas.setExtent(STATE['pc_extent'])


def s_pc_check():
    d = dock()
    from qgis.PyQt import sip
    old = STATE.get('old_picker')
    check('pc: the raster picker left behind Pan is deleted with its layer',
          old is not None and sip.isdeleted(old) and ctrl()._pixel_tool is None)
    from qgis.PyQt.QtWidgets import QLabel
    card = d.findChild(QLabel, 'label_exploring_coverage_layer')
    check('pc: layer card', card is not None and 'points' in card.text(), card.text() if card else '')
    hint = d.findChild(QLabel, 'label_filtering_source_geometry')
    check('pc: no source geometry line', hint is None or not hint.isVisible())
    pipette = tool('pushButton_checkable_exploring_point_cloud_pipette')
    check('pc: class pipette on the rail, its icon drawn', pipette is not None and pipette.isVisible() and not pipette.icon().isNull())
    check('pc: no other extra tool on the rail (profile and 3D are the QGIS ones, no raster tool)',
          all(tool(n) is None or not tool(n).isVisible() for n in (
              'pushButton_exploring_point_cloud_profile', 'pushButton_exploring_point_cloud_3d',
              'pushButton_checkable_exploring_raster_link', 'pushButton_checkable_exploring_raster_pipette')))
    vgroups = [d.mGroupBox_exploring_single_selection, d.mGroupBox_exploring_multiple_selection, d.mGroupBox_exploring_custom_selection]
    check('pc: only point cloud groups (no vector, no raster group)', not any(g.isVisible() for g in vgroups)
          and ctrl()._pc_panel.isVisible() and not ctrl()._raster_panel.isVisible())
    save('point_cloud')
    host = ctrl()._host
    check('pc: panel fits the dock (no sideways scroll)', host.parentWidget().width() <= host.parentWidget().parentWidget().width() + 2, f'{host.parentWidget().width()} vs {host.parentWidget().parentWidget().width()}')


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


def s_pc_conditions():
    """ATTRIBUTES: Z between and Intensity >= joined by OR give one OR chain, AND groups parenthesised."""
    import sys
    from qgis.PyQt.QtWidgets import QPushButton
    pc = ctrl()._pc_panel
    module = sys.modules[type(pc).__module__]
    names = pc.condition_attributes()
    # Classification is a condition too since the class with a height above the DTM (76d0548c).
    check('pc conditions: layer attributes offered (not X / Y)',
          'Z' in names and 'Intensity' in names and not {'X', 'Y'} & set(names), ', '.join(names))
    pc._ranges_group.setChecked(True)
    pc.restore_state(dict(pc.state(), conditions=[]))
    add = pc.findChild(QPushButton, 'pushButton_point_cloud_add_condition')
    check('pc conditions: add button visible', add is not None and add.isVisible())
    add.click()
    add.click()
    rows = pc._condition_rows
    check('pc conditions: two named rows', len(rows) == 2 and all(r.objectName() == 'widget_point_cloud_condition' for r in rows))
    z_row, i_row = rows
    z_row._attribute_combo.setCurrentIndex(z_row._attribute_combo.findData('Z'))
    i_row._attribute_combo.setCurrentIndex(i_row._attribute_combo.findData('Intensity'))
    i_row._op_combo.setCurrentIndex(i_row._op_combo.findData('>='))
    i_row._join_combo.setCurrentIndex(i_row._join_combo.findData('OR'))
    z_low, z_high = module.summary_bounds(pc._summary, 'Z')
    i_low, i_high = module.summary_bounds(pc._summary, 'Intensity')
    low, high = round(z_low + (z_high - z_low) / 4, 3), round(z_low + (z_high - z_low) * 3 / 4, 3)
    level = float(round((i_low + i_high) / 2))
    z_row._low_spin.setValue(low)
    z_row._high_spin.setValue(high)
    i_row._low_spin.setValue(level)
    fmt = module.format_number
    expected = f"(Z >= {fmt(low)} AND Z <= {fmt(high)}) OR (Intensity >= {fmt(level)})"
    check('pc conditions: OR chain expression', pc.expression() == expected, f'{pc.expression()!r} vs {expected!r}')
    check('pc conditions: generated expression shown', pc._expression_edit.toPlainText() == expected,
          pc._expression_edit.toPlainText())
    check('pc conditions: join combo hidden on the first row only',
          z_row._join_combo.isHidden() and not i_row._join_combo.isHidden())
    if pc._return_button.isVisible():
        pc._return_actions['last'].trigger()
        last = expected[:-1] + ' AND ReturnNumber = NumberOfReturns)'
        check('pc conditions: last return shortcut joins the last group', pc.expression() == last, pc.expression())
    lhd = layer('lhd')
    before = lhd.subsetString()
    for text in (pc.expression(), 'Intensity <> 0', 'ReturnNumber = NumberOfReturns'):
        check(f'pc conditions: layer accepts {text!r}', lhd.setSubsetString(text))
    lhd.setSubsetString(before)
    group = pc._ranges_group.minimumSizeHint().width()
    check('pc conditions: ATTRIBUTES group fits 300 px', group <= 300, f'{group}px')
    # New rows are shown by a queued call (QLayout::addChildWidget), the layouts run on a posted
    # LayoutRequest and _CollapsedBand gives the expanded minimum back on a 0 ms timer: measured in
    # the same pass the group was still one band high and empty (h=34, rows hidden).
    for _ in range(5):
        QgsApplication.processEvents()
    attributes = pc._ranges_group
    check('pc conditions: ATTRIBUTES grows to its rows', attributes.height() > 34 and not attributes.isCollapsed(),
          f'h={attributes.height()} min={attributes.minimumHeight()} hint={attributes.sizeHint().height()}')
    check('pc conditions: a condition row is visible',
          any(row.isVisible() and row.objectName() == 'widget_point_cloud_condition' for row in pc._condition_rows))
    host = ctrl()._host
    check('pc conditions: panel still fits the dock', host.parentWidget().width() <= host.parentWidget().parentWidget().width() + 2,
          f'{host.parentWidget().width()} vs {host.parentWidget().parentWidget().width()}')
    save('point_cloud_conditions')
    # Back to the classes, without conditions (restore_state does not emit: no preview left behind).
    pc.restore_state(dict(pc.state(), conditions=[], classes_enabled=True, ranges_enabled=False))
    check('pc conditions: back to classes', pc._classes_group.isChecked() and not pc._ranges_group.isChecked())


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
    selection = strip()
    if selection is not None and selection.isVisible():
        # The selection strip closes EXPLORING: one block above it, one block down to the header.
        box = _rect(d, selection)
        check('scale: EXPLORING -> selection strip one block', box[1] - rail[3] == block, f'{box[1] - rail[3]}')
        check('scale: selection strip -> FILTERING header one block', _rect(d, tabs[0])[1] - box[3] == block,
              f'{_rect(d, tabs[0])[1] - box[3]}')
        check('scale: selection strip one band high', box[3] - box[1] == band, f'{box[3] - box[1]} vs {band}')
        check('scale: selection strip on the section edges', box[0] == _rect(d, tabs[0])[0] and box[2] == _rect(d, tabs[0])[2],
              f'{box} vs {_rect(d, tabs[0])}')
    else:
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
    check('scale: splitter handle shows a centred grip', 'splitter_grip' in d.splitter_main.styleSheet())
    bottom = d.gridLayout_main_header.contentsMargins().bottom()
    check('scale: EXPLORING scroll content ends one gap above the edge', bottom == gap, f'{bottom} vs {gap}')


def s_pc_statistics():
    c = ctrl()
    layer = c.active_layer
    summary = getattr(c._pc_panel, '_summary', None)
    names = [r.name for r in getattr(summary, 'ranges', ())]
    state = layer.statisticsCalculationState() if hasattr(layer, 'statisticsCalculationState') else None
    check('pc statistics: ranges known beyond Z once QGIS has the statistics', len(names) > 1, f'state={state} ranges={names}')


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


STEPS = [(s_setup, 1500), (s_open, 6000), (s_vector, 3500), (s_vector_check, 500), (s_strip_vector, 1000), (s_strip_vector_count, 500), (s_targets_popup, 800), (s_targets_popup_shot, 500), (s_raster, 4000),
         (s_raster_check, 500), (s_picker, 800), (s_picker_check, 500), (s_raster_tools, 2500), (s_raster_tools_check, 500), (s_strip_raster, 300), (s_handover, 1000), (s_alignment, 500),
         (s_pc, 5000), (s_pc_check, 3000), (s_strip_pc, 1000), (s_strip_pc_count, 500), (s_pc_pipette, 1500), (s_pc_pipette_check, 1500), (s_pc_groups, 800), (s_pc_conditions, 800), (s_pc_statistics, 300), (s_spacing_pc, 300), (s_probe, 500), (s_back, 4000), (s_back_check, 500), (s_strip_back, 300), (s_alignment, 500), (s_sections_gap, 300), (s_harmony, 300), (s_spacing_scale, 300), (s_rail_minimum, 300), (s_badge_gap, 300), (s_source_row, 300),
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
