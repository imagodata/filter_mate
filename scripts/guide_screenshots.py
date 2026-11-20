# -*- coding: utf-8 -*-
"""Take the screenshots used by website/guide.html inside a real QGIS session.

Usage, without a screen (QGIS in Docker under Xvfb, see the script for the mounts and the profile)::

    scripts/guide_screenshots_headless.sh guide      # PNGs in ~/dev/fm-guide/out/guide
    scripts/guide_screenshots_headless.sh publish    # copied into website/img/guide

or in a desktop QGIS, with a throwaway profile (``--profiles-path``)::

    qgis --nologo --lang en --code scripts/guide_screenshots.py

The script waits for QGIS and the plugins to load, then loads five layers from
a BD TOPO GeoPackage, opens FilterMate in the dock of a new install (the rail of
sections, every section in the dock), drives the panel through the exploring
modes, runs a real spatial filter (buildings and hedges within 50 m of a named
road), opens the favorites menu and manager, the EXPORTING and CONFIGURATION
sections and the Processing batch-filter dialog, then shows the panels of 5.1.1:
the menu of a chip, FILTERING and EXPORTING grouped in a panel beside the map,
EXPLORING in its own panel with its list of layers, the buttons under each
section and the headers one above the other. One PNG per state in ``OUT``; the
dock is grabbed widget by widget (``QWidget.grab``), never from the screen.
The headless runner sets a 1.5 scale (``QT_SCALE_FACTOR``), the scale of the
guide's images. It removes the favorite it created and quits QGIS at the end.

Set ``FM_GUIDE_OUT`` (default: a temp folder) and ``FM_GUIDE_GPKG`` for your
machine; the PNGs carry the names used by the guide (a name that starts with
``_`` is a working image, not published). ``FM_GUIDE_UNTIL`` (a step name such
as ``s_favorites_menu``) stops the run after that step, to refresh one image
without retaking them all. The modal first-run dialogs are switched off through
QSettings. The layer names, the road feature id and the field used for the
custom-selection expression are specific to the demo GeoPackage (commune 31
extract, Toutens) and must be adapted for another dataset.
"""
import os
import time
import traceback

from qgis.PyQt.QtCore import QPoint, QRect, QSettings, QTimer, Qt
from qgis.PyQt.QtGui import QPainter
from qgis.PyQt.QtWidgets import QApplication, QDockWidget, QFrame
from qgis.core import QgsApplication, QgsProject, QgsVectorLayer
from qgis.utils import iface, plugins

OUT = os.environ.get('FM_GUIDE_OUT') or os.path.join(os.environ.get('TEMP', '/tmp'), 'fm_shots')
os.makedirs(OUT, exist_ok=True)
LOG = os.path.join(OUT, 'shots.log')
GPKG = os.environ.get('FM_GUIDE_GPKG') or r'C:\Users\Simon\Documents\31.gpkg'
EXPORT_DIR = os.environ.get('FM_GUIDE_EXPORT_DIR') or '/home/me/Documents/export'  # only typed in the field
DOCK_WIDTH = 413  # logical pixels: 620 px wide images at the 1.5 scale
# A window no taller than the panel needs, and a lower stack no taller than the rows of FILTERING and EXPORTING
# (fit_stacks): the pictures of the panel hold no empty band, neither under the rows (SECTION_HEIGHT = fit) nor between
# them (fill, the default).
WINDOW_HEIGHT = int(os.environ.get('FM_GUIDE_HEIGHT', '880'))
STEP_TIMEOUT = 60.0
STATE = {}


def log(msg):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(str(msg) + '\n')


def save_pixmap(pm, name, max_width=None):
    if max_width and pm.width() > max_width:
        pm = pm.scaledToWidth(max_width, Qt.TransformationMode.SmoothTransformation)
    ok = pm.save(os.path.join(OUT, name + '.png'), 'PNG')
    log(f'saved {name} {pm.width()}x{pm.height()} ok={ok}')


def save(widget, name, max_width=None, rect=None):
    """Save ``widget`` (or the part ``rect`` of it, in its coordinates) by rendering it, not the screen."""
    try:
        iface.messageBar().clearWidgets()  # first-run notices of a throwaway profile (downloaded fonts...)
        save_pixmap(widget.grab(rect) if rect is not None else widget.grab(), name, max_width)
    except Exception:
        log('save failed ' + name + '\n' + traceback.format_exc())


def with_popup(widget, popup):
    """``widget`` rendered with ``popup`` (a menu, a top-level window of its own) painted where it shows."""
    pm = widget.grab()
    ratio = pm.devicePixelRatio()
    offset = popup.mapToGlobal(QPoint(0, 0)) - widget.mapToGlobal(QPoint(0, 0))
    painter = QPainter(pm)
    painter.drawPixmap(QPoint(int(offset.x()), int(offset.y())), popup.grab())
    painter.end()
    log(f'popup painted at {offset} (ratio {ratio})')
    return pm


def dock():
    return plugins['filter_mate'].app.dockwidget


def sections():
    return dock()._fm_sections


def panels():
    return dock()._fm_panels


def layer(name):
    return QgsProject.instance().mapLayersByName(name)[0]


def rect_in(widget, parent):
    """Geometry of ``widget`` in the coordinates of ``parent``."""
    return QRect(widget.mapTo(parent, QPoint(0, 0)), widget.size())


def strip():
    return dock().findChild(QFrame, 'frame_selection_strip')


def exploring_rect():
    """EXPLORING as the guide shows it: its rail of chips, the page, the selection strip below it."""
    d = dock()
    r = rect_in(sections().top, d)
    s = strip()
    if s is not None and s.isVisible():
        r = r.united(rect_in(s, d))
    return r.adjusted(-2, -2, 2, 2)


def lower_rect():
    """The lower stack: its rail of chips and the open section (FILTERING, EXPORTING or CONFIGURATION), down to the
    last row of the section (the room its packed rows leave under them is not in the picture)."""
    d = dock()
    box = rect_in(d.toolBox_tabTools, d)
    page = d.toolBox_tabTools.currentWidget()
    rows = rect_in(page, d).intersected(box) if page is not None else box
    if rows.height() < 60:
        rows = box
    return rect_in(sections().bottom_rail, d).united(QRect(box.x(), rows.y(), box.width(), rows.height())) \
        .adjusted(-2, -2, 2, 6)


def fit_stacks():
    """The handle between the stacks set so that the lower one is as tall as its rows: EXPLORING gets the rest."""
    d = dock()
    splitter, page = d.splitter_main, d.toolBox_tabTools.currentWidget()
    if page is None or page is d.CONFIGURATION:
        return
    need = sections().bottom_rail.height() + max(page.sizeHint().height(), page.minimumSizeHint().height()) + 22
    total = sum(splitter.sizes())
    if 0 < need < total:
        splitter.setSizes([total - need, need])
    log(f'stacks {splitter.sizes()} for rows of {need}')


def under_section_rect():
    """The lower stack with the buttons shown under its open section (ACTION_BAR_POSITION = sections)."""
    d = dock()
    r = lower_rect()
    for bar in d.findChildren(QFrame, 'frame_actions'):
        if bar.isVisible() and not bar.visibleRegion().isEmpty():
            r = r.united(rect_in(bar, d))
    return r


def check_combo_items(combo, texts):
    """Check items of a checkable combobox whose text contains one of texts."""
    model = combo.model()
    for i in range(model.rowCount()):
        item = model.item(i)
        txt = item.text()
        if any(t.lower() in txt.lower() for t in texts):
            item.setCheckState(Qt.CheckState.Checked)
            log(f'checked item {txt}')


def tasks_idle():
    return not [t for t in QgsApplication.taskManager().activeTasks() if 'FilterMate' in t.description()]


def waits(seconds):
    since = time.time()
    return lambda: time.time() - since > seconds


def settled(seconds=2.0):
    """No FilterMate task left, and ``seconds`` more for the dock to lay itself out."""
    since = time.time()
    return lambda: tasks_idle() and time.time() - since > seconds


def current_is(name):
    """Condition: ``name`` is the current layer of the dock, for 3 s on end. QGIS and the dock may still pick another
    one just after the start (the last layer added): the layer is set again until it holds."""
    state = {'since': None}

    def done():
        d = dock()
        shown = d.comboBox_filtering_current_layer.currentLayer()
        if shown is None or shown.name() != name:
            iface.setActiveLayer(layer(name))
            d.comboBox_filtering_current_layer.setLayer(layer(name))
            state['since'] = None
            return False
        if state['since'] is None:
            state['since'] = time.time()
        return tasks_idle() and time.time() - state['since'] > 3.0
    return done


# ---------------------------------------------------------------- steps
def s_setup():
    settings = QSettings()
    settings.setValue('FilterMate/discord_welcome_dismissed', True)  # modal dialogs would block the run
    settings.setValue('FilterMate/whats_new_seen', 99)
    settings.setValue('qgis/digitizing/validate_geometries', 0)
    mw = iface.mainWindow()
    mw.showNormal()
    mw.resize(1760, WINDOW_HEIGHT)
    for name in ['commune', 'cours_d_eau', 'haie', 'troncon_de_route', 'batiment']:
        vl = QgsVectorLayer(f'{GPKG}|layername={name}', name, 'ogr')
        log(f'{name} valid={vl.isValid()} count={vl.featureCount()}')
        QgsProject.instance().addMapLayer(vl)
    iface.mapCanvas().zoomToFullExtent()
    for d in mw.findChildren(QDockWidget):
        if d.objectName() in ('MessageLog', 'Browser', 'Browser2'):
            d.hide()


def s_open_plugin():
    import qgis.utils
    if 'filter_mate' not in plugins:  # throwaway profile: the plugin is found but not enabled
        qgis.utils.loadPlugin('filter_mate') and qgis.utils.startPlugin('filter_mate')
    plugins['filter_mate'].run()
    return lambda: plugins['filter_mate'].app is not None and dock() is not None and dock().isVisible() \
        and tasks_idle()


def s_after_open():
    d = dock()
    if panels().detached():  # a profile that kept sections apart: the guide shows the dock of a new install
        panels().attach_all()
    d.setMinimumWidth(0)
    iface.mainWindow().resizeDocks([d], [DOCK_WIDTH], Qt.Orientation.Horizontal)
    sections().open_top('exploring')
    d.toolBox_tabTools.setCurrentWidget(d.FILTERING)
    QTimer.singleShot(1200, fit_stacks)
    return settled(3.0)


def s_toolbar():
    tb = plugins['filter_mate'].toolbar
    pm = tb.grab()
    save_pixmap(pm.copy(0, 0, min(pm.width(), round(100 * pm.devicePixelRatio())), pm.height()), 'toolbar-button')
    return current_is('troncon_de_route')


def s_exploring_single_pick():
    d = dock()
    STATE['road_fid'] = 247881  # 'R DE LA SOLEDRA', longest named road
    d.mGroupBox_exploring_single_selection.setChecked(True)
    d.mFieldExpressionWidget_exploring_single_selection.setExpression('nom_collaboratif_gauche')
    d.mFeaturePickerWidget_exploring_single_selection.setFeature(STATE['road_fid'])
    return settled(2.5)


def s_grab_exploring_single():
    d = dock()
    log(f'single picker shows {d.mFeaturePickerWidget_exploring_single_selection.displayExpression()!r}')
    save(d, 'exploring-single', rect=exploring_rect())
    save(d, 'dock-overview')
    save(d.titleBarWidget() or d, 'header-badges')
    save(iface.mainWindow(), 'qgis-window', 1600)


def s_exploring_multiple():
    d = dock()
    d.mGroupBox_exploring_multiple_selection.setChecked(True)
    return settled(2.0)


def s_exploring_multiple_pick():
    d = dock()
    w = d.checkableComboBoxFeaturesListPickerWidget_exploring_multiple_selection
    fids = [247881, 110289, 110293, 113421]
    try:
        w.setCheckedFeatureIds(fids)
        w.filter_le.setText('DE')  # named roads only: the unnamed ones sort first as empty rows
    except Exception:
        log(traceback.format_exc())
    return settled(2.5)


def s_grab_exploring_multiple():
    save(dock(), 'exploring-multiple', rect=exploring_rect())


def s_exploring_custom():
    d = dock()
    d.mGroupBox_exploring_custom_selection.setChecked(True)
    d.mFieldExpressionWidget_exploring_custom_selection.setExpression('"importance" IN (\'3\', \'4\')')
    return settled(2.5)


def s_grab_exploring_custom():
    save(dock(), 'exploring-custom', rect=exploring_rect())


def s_back_to_single():
    d = dock()
    d.mGroupBox_exploring_single_selection.setChecked(True)
    d.mFeaturePickerWidget_exploring_single_selection.setFeature(STATE['road_fid'])
    return settled(2.0)


def s_filtering_tab():
    d = dock()
    d.toolBox_tabTools.setCurrentWidget(d.FILTERING)
    d.pushButton_checkable_filtering_layers_to_filter.setChecked(True)
    check_combo_items(d.checkableComboBoxLayer_filtering_layers_to_filter, ['batiment', 'haie'])
    d.checkableComboBoxLayer_filtering_layers_to_filter.checkedItemsChangedEvent()
    d.pushButton_checkable_filtering_geometric_predicates.setChecked(True)
    check_combo_items(d.comboBox_filtering_geometric_predicates, ['intersect'])
    d.pushButton_checkable_filtering_buffer_value.setChecked(True)
    d.mQgsDoubleSpinBox_filtering_buffer_value.setValue(50)
    return settled(2.5)


def s_grab_filtering():
    d = dock()
    save(d, 'filtering-tab', rect=lower_rect())
    save(d, '_dock-filtering')


def s_run_filter():
    dock().pushButton_action_filter.click()
    since = time.time()
    return lambda: layer('batiment').subsetString() != '' and tasks_idle() and time.time() - since > 3.0


def s_grab_filtered():
    d = dock()
    save(iface.mainWindow(), '_filter-result', 1600)
    save(d.frame_actions, '_action-bar')
    for name in ['batiment', 'haie']:
        log(f'{name} subset={layer(name).subsetString()!r} count={layer(name).featureCount()}')


def s_add_favorite():
    d = dock()
    try:
        ok = d._favorites_ctrl.add_current_to_favorites('Buildings within 50 m of the main road')
        log(f'favorite added {ok}')
    except Exception:
        log(traceback.format_exc())
    return waits(1.5)


def s_favorites_menu():
    def grab_popup():
        w = QApplication.activePopupWidget()
        log(f'popup {w}')
        if w:
            save(w, 'favorites-menu')
            w.close()
    QTimer.singleShot(1200, grab_popup)
    dock()._favorites_ctrl.handle_indicator_clicked()  # menu.exec: returns once grab_popup closed it
    return waits(1.0)


def s_favorites_manager():
    def grab_modal():
        w = QApplication.activeModalWidget()
        log(f'modal {w}')
        if w:
            w.resize(900, 600)
            QTimer.singleShot(600, lambda: (save(w, 'favorites-manager'), w.reject()))
    QTimer.singleShot(1500, grab_modal)
    dock()._favorites_ctrl.show_manager_dialog()
    return waits(1.0)


def s_unfilter():
    dock().pushButton_action_unfilter.click()
    since = time.time()
    return lambda: layer('batiment').subsetString() == '' and tasks_idle() and time.time() - since > 3.0


def s_export_tab():
    d = dock()
    d.toolBox_tabTools.setCurrentWidget(d.EXPORTING)
    d.pushButton_checkable_exporting_layers.setChecked(True)
    check_combo_items(d.checkableComboBoxLayer_exporting_layers, ['batiment', 'troncon_de_route'])
    d.checkableComboBoxLayer_exporting_layers.checkedItemsChangedEvent()
    d.pushButton_checkable_exporting_projection.setChecked(True)
    d.pushButton_checkable_exporting_styles.setChecked(True)
    d.pushButton_checkable_exporting_datatype.setChecked(True)
    i = d.comboBox_exporting_datatype.findText('GPKG', Qt.MatchFlag.MatchContains)
    if i >= 0:
        d.comboBox_exporting_datatype.setCurrentIndex(i)
    d.pushButton_checkable_exporting_output_folder.setChecked(True)
    d.lineEdit_exporting_output_folder.setText(EXPORT_DIR)
    return settled(2.5)


def s_grab_export():
    d = dock()
    save(d, 'export-tab', rect=lower_rect())
    save(d, '_dock-export')


def s_config_tab():
    from qgis.PyQt.QtWidgets import QTreeView
    d = dock()
    d.toolBox_tabTools.setCurrentWidget(d.CONFIGURATION)
    for tv in d.CONFIGURATION.findChildren(QTreeView):
        tv.expandToDepth(0)
        log(f'expanded {tv.objectName()}')
    return settled(2.5)


def s_grab_config():
    d = dock()
    save(d, 'configuration-tab', rect=lower_rect())
    save(d, '_dock-configuration')


def s_processing():
    try:
        import processing
        dlg = processing.createAlgorithmDialog('filtermate:batch_filter')
        dlg.resize(820, 560)
        dlg.show()
        STATE['proc'] = dlg
    except Exception:
        log(traceback.format_exc())
    return waits(2.5)


def s_grab_processing():
    dlg = STATE.get('proc')
    if dlg:
        save(dlg, 'processing-batch-filter')
        dlg.close()
    d = dock()
    d.toolBox_tabTools.setCurrentWidget(d.FILTERING)
    return settled(2.0)


# -- the panels of 5.1.1: the menu of a chip, sections apart, grouped, EXPLORING alone, the other layouts
def s_chip_menu():
    chip = sections().bottom_rail.chip('filtering')
    menu = panels().build_menu('filtering', dock())
    STATE['menu'] = menu
    menu.popup(chip.mapToGlobal(QPoint(chip.width() // 2, chip.height() // 2)))
    log(f'menu of filtering: {[a.text() for a in menu.actions() if not a.isSeparator()]}')
    return waits(1.0)


def s_grab_chip_menu():
    d, menu = dock(), STATE.pop('menu')
    try:
        iface.messageBar().clearWidgets()
        pm = with_popup(d, menu)
        top = rect_in(sections().top, d).bottom() - 40  # from the bottom of EXPLORING to the end of the menu
        bottom = menu.mapToGlobal(QPoint(0, menu.height())).y() - d.mapToGlobal(QPoint(0, 0)).y() + 16
        ratio = pm.devicePixelRatio()
        save_pixmap(pm.copy(QRect(0, round(top * ratio), pm.width(), round((bottom - top) * ratio))),
                    'panels-chip-menu')
    except Exception:
        log(traceback.format_exc())
    menu.close()


def s_detach_filtering():
    log(f"detach filtering: {panels().detach('filtering')}")
    return waits(1.5)


def s_group_exporting():
    log(f"group exporting: {panels().group('exporting', 'filtering')}, groups {panels().groups()}")
    return waits(1.5)


def s_beside_map():
    """The panel under the Layers panel, in the column left of the map; the map on the road and its buildings."""
    window = iface.mainWindow()
    layers = window.findChild(QDockWidget, 'Layers')
    panel = panels().panel('filtering')
    window.splitDockWidget(layers, panel, Qt.Orientation.Vertical)
    window.resizeDocks([layers, panel], [340, 376], Qt.Orientation.Vertical)
    window.resizeDocks([layers], [DOCK_WIDTH], Qt.Orientation.Horizontal)
    panel.open('filtering')
    box = layer('troncon_de_route').getFeature(STATE['road_fid']).geometry().boundingBox()
    box.scale(4.5)
    iface.mapCanvas().setExtent(box)
    iface.mapCanvas().refresh()
    return settled(3.0)


def s_grab_beside_map():
    panel = panels().panel('filtering')
    log(f'panel {panel.windowTitle()!r} at {panel.geometry()}, floating={panel.isFloating()}')
    save(iface.mainWindow(), 'panels-beside-map', 1600)
    save(panel, 'panels-grouped')


def s_attach_all():
    panels().attach_all()
    return settled(2.0)


def s_detach_exploring():
    log(f"detach exploring: {panels().detach('exploring')}, groups {panels().groups()}")
    return settled(2.5)


def s_exploring_share():
    """The panel of EXPLORING and the dock share the column of the right."""
    panel, d = panels().panel('exploring'), dock()
    if panel is not None and not panel.isFloating():
        total = panel.height() + d.height()
        first, second = (panel, d) if panel.y() < d.y() else (d, panel)
        part = int(total * 0.5)
        iface.mainWindow().resizeDocks([first, second], [part, total - part], Qt.Orientation.Vertical)
    return settled(2.0)


def s_grab_exploring_panel():
    window, panel, d = iface.mainWindow(), panels().panel('exploring'), dock()
    r = rect_in(panel, window).united(rect_in(d, window))
    log(f'EXPLORING panel {panel.windowTitle()!r} {rect_in(panel, window)}, dock {rect_in(d, window)}')
    save(window, 'panels-exploring', rect=r)
    save(window, '_exploring-window', 1600)


def apply(values):
    import importlib
    applied = importlib.import_module('filter_mate.adapters.agent.plugin_settings').apply_values(values)
    log(f'applied {values}: {applied}')


def s_section_buttons():
    panels().attach_all()
    apply({'APP.DOCKWIDGET.ACTION_BAR_POSITION': 'sections'})
    d = dock()
    d.toolBox_tabTools.setCurrentWidget(d.FILTERING)
    QTimer.singleShot(1200, fit_stacks)
    return settled(2.5)


def s_grab_section_buttons_filtering():
    d = dock()
    STATE['under_filtering'] = d.grab(under_section_rect())
    d.toolBox_tabTools.setCurrentWidget(d.EXPORTING)
    return settled(2.5)


def s_grab_section_buttons():
    """FILTERING and EXPORTING, each open with its own buttons under it, side by side in one image."""
    d = dock()
    first = STATE.pop('under_filtering')
    second = d.grab(under_section_rect())
    ratio = first.devicePixelRatio()
    gap = round(16 * ratio)
    first.setDevicePixelRatio(1.0)  # painted pixel for pixel on a plain pixmap
    second.setDevicePixelRatio(1.0)
    from qgis.PyQt.QtGui import QColor, QPixmap
    both = QPixmap(first.width() + gap + second.width(), max(first.height(), second.height()))
    both.fill(QColor('#ffffff'))
    painter = QPainter(both)
    painter.drawPixmap(0, 0, first)
    painter.drawPixmap(first.width() + gap, 0, second)
    painter.end()
    save_pixmap(both, 'panels-section-buttons')
    apply({'APP.DOCKWIDGET.ACTION_BAR_POSITION': 'bottom'})
    d.toolBox_tabTools.setCurrentWidget(d.FILTERING)
    return settled(2.0)


def s_stacked():
    apply({'APP.DOCKWIDGET.SECTION_HEADERS': 'stacked'})
    QTimer.singleShot(1200, fit_stacks)
    return settled(2.5)


def s_grab_stacked():
    save(dock(), 'panels-stacked')
    apply({'APP.DOCKWIDGET.SECTION_HEADERS': 'rail'})
    return settled(1.5)


# -- only the sections that are used: EXPORTING turned off, then FILTERING too (EXPLORING alone)
def s_sections_off():
    """EXPORTING turned off: its chip and its Export button leave the panel, which stays in one piece."""
    apply({'APP.OPTIONS.EXPORTING.enabled': False})
    d = dock()
    d.toolBox_tabTools.setCurrentWidget(d.FILTERING)
    QTimer.singleShot(1200, fit_stacks)
    return settled(2.5)


def s_grab_sections_off():
    """Then FILTERING off too: EXPLORING chooses its layer itself. It is shown with the multiple selection
    (s_exploring_multiple, s_exploring_multiple_pick), whose list takes the height the panel has: a single
    selection would leave the panel half empty."""
    save(dock(), 'panels-sections-off')
    apply({'APP.OPTIONS.FILTERING.enabled': False})
    return settled(2.5)


def s_grab_exploring_alone():
    d = dock()
    log(f'sections shown: filtering {sections().section_shown("filtering")}, exporting {sections().section_shown("exporting")}')
    save(d, 'panels-exploring-alone')
    apply({'APP.OPTIONS.FILTERING.enabled': True, 'APP.OPTIONS.EXPORTING.enabled': True})
    d.mGroupBox_exploring_single_selection.setChecked(True)
    return settled(2.5)


def s_cleanup_favorite():
    d = dock()
    svc = getattr(d, '_favorites_service', None)
    try:
        favs = None
        for getter in ('get_all_favorites', 'get_all', 'list_favorites', 'favorites'):
            if hasattr(svc, getter):
                favs = getattr(svc, getter)
                favs = favs() if callable(favs) else favs
                break
        for f in favs or []:
            name = getattr(f, 'name', None) or (f.get('name') if isinstance(f, dict) else None)
            if name == 'Buildings within 50 m of the main road':
                fid = getattr(f, 'id', None) or (f.get('id') if isinstance(f, dict) else None)
                for deleter in ('delete_favorite', 'remove_favorite', 'delete'):
                    if hasattr(svc, deleter):
                        log(f'delete {fid} via {deleter}: {getattr(svc, deleter)(fid)}')
                        break
    except Exception:
        log(traceback.format_exc())


def s_quit():
    QgsProject.instance().setDirty(False)
    QgsApplication.instance().quit()


STEPS = [
    s_setup, s_open_plugin, s_after_open, s_toolbar,
    s_exploring_single_pick, s_grab_exploring_single,
    s_exploring_multiple, s_exploring_multiple_pick, s_grab_exploring_multiple,
    s_exploring_custom, s_grab_exploring_custom, s_back_to_single,
    s_filtering_tab, s_grab_filtering,
    s_run_filter, s_grab_filtered, s_add_favorite, s_favorites_menu, s_favorites_manager, s_unfilter,
    s_export_tab, s_grab_export, s_config_tab, s_grab_config, s_processing, s_grab_processing,
    s_chip_menu, s_grab_chip_menu, s_detach_filtering, s_group_exporting, s_beside_map, s_grab_beside_map,
    s_attach_all, s_detach_exploring, s_exploring_share, s_grab_exploring_panel,
    s_section_buttons, s_grab_section_buttons_filtering, s_grab_section_buttons, s_stacked, s_grab_stacked,
    s_sections_off, s_grab_sections_off, s_exploring_multiple, s_exploring_multiple_pick, s_grab_exploring_alone,
    s_cleanup_favorite, s_quit,
]

UNTIL = os.environ.get('FM_GUIDE_UNTIL')  # e.g. s_favorites_menu: stop after that step (then clean up and quit)
if UNTIL:
    STEPS[:] = STEPS[:STEPS.index(globals()[UNTIL]) + 1] + [s_cleanup_favorite, s_quit]


def run_step(i=0):
    if i >= len(STEPS):
        return
    fn = STEPS[i]
    log(f'--- step {i} {fn.__name__}')
    try:
        until = fn()
    except Exception:
        log(traceback.format_exc())
        until = None
    wait(i, until, time.time())


def wait(i, until, since):
    """Poll ``until`` every 250 ms (at most STEP_TIMEOUT), then go on with the next step."""
    if until is not None:
        try:
            done = until()
        except Exception:
            done = False
        if not done and time.time() - since < STEP_TIMEOUT:
            QTimer.singleShot(250, lambda: wait(i, until, since))
            return
        if not done:
            log(f'   (timeout at the end of {STEPS[i].__name__})')
    QTimer.singleShot(400, lambda: run_step(i + 1))


open(LOG, 'w').close()
QTimer.singleShot(12000, run_step)
