# -*- coding: utf-8 -*-
"""Take the screenshots used by website/guide.html inside a real QGIS session.

Usage (Windows QGIS driven from WSL or a Windows shell):

    qgis-bin.exe --nologo --lang en --code scripts/guide_screenshots.py

The script waits for QGIS and the plugins to load, then loads five layers from
a BD TOPO GeoPackage, opens FilterMate, drives the panel through the exploring
modes, runs a real spatial filter (buildings and hedges within 50 m of a named
road), opens the favorites menu and manager, the export and configuration tabs
and the Processing batch-filter dialog, saving one PNG per state in ``OUT``.
It removes the favorite it created and quits QGIS at the end.

Adjust ``OUT`` and ``GPKG`` to your machine. The layer names, the road feature
id and the field used for the custom-selection expression are specific to the
demo GeoPackage (commune 31 extract) and must be adapted for another dataset.
"""
import os, traceback
from qgis.PyQt.QtCore import QTimer, Qt
from qgis.PyQt.QtWidgets import QApplication, QDialog
from qgis.core import QgsApplication, QgsProject, QgsVectorLayer
from qgis.utils import iface, plugins

OUT = r'C:\Users\Simon\AppData\Local\Temp\fm_shots\out'
LOG = os.path.join(OUT, 'shots.log')
GPKG = r'C:\Users\Simon\Documents\31.gpkg'
STATE = {}

def log(msg):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(str(msg) + '\n')

def save(widget, name, max_width=None):
    try:
        pm = widget.grab()
        if max_width and pm.width() > max_width:
            pm = pm.scaledToWidth(max_width, Qt.TransformationMode.SmoothTransformation)
        ok = pm.save(os.path.join(OUT, name + '.png'), 'PNG')
        log(f'saved {name} {pm.width()}x{pm.height()} ok={ok}')
    except Exception:
        log('save failed ' + name + '\n' + traceback.format_exc())

def screen_save(widget, name):
    try:
        g = widget.geometry()
        p = widget.mapToGlobal(widget.rect().topLeft()) if widget.parent() else widget.pos()
        scr = QApplication.primaryScreen()
        pm = scr.grabWindow(0, p.x(), p.y(), widget.width(), widget.height())
        ok = pm.save(os.path.join(OUT, name + '.png'), 'PNG')
        log(f'screen saved {name} {pm.width()}x{pm.height()} ok={ok}')
    except Exception:
        log('screen save failed ' + name + '\n' + traceback.format_exc())

def dock():
    return plugins['filter_mate'].app.dockwidget

def layer(name):
    return QgsProject.instance().mapLayersByName(name)[0]

def check_combo_items(combo, texts):
    """Check items of a checkable combobox whose text contains one of texts."""
    model = combo.model()
    for i in range(model.rowCount()):
        item = model.item(i)
        txt = item.text()
        if any(t.lower() in txt.lower() for t in texts):
            item.setCheckState(Qt.CheckState.Checked)
            log(f'checked item {txt}')

# ---------------------------------------------------------------- steps
def s_setup():
    mw = iface.mainWindow()
    mw.showNormal()
    mw.resize(1760, 1040)
    for name in ['commune', 'cours_d_eau', 'haie', 'troncon_de_route', 'batiment']:
        vl = QgsVectorLayer(f'{GPKG}|layername={name}', name, 'ogr')
        log(f'{name} valid={vl.isValid()} count={vl.featureCount()}')
        QgsProject.instance().addMapLayer(vl)
    iface.mapCanvas().zoomToFullExtent()
    from qgis.PyQt.QtWidgets import QDockWidget
    for d in mw.findChildren(QDockWidget):
        if d.objectName() in ('MessageLog', 'Browser', 'Browser2'):
            d.hide()

def s_open_plugin():
    plugins['filter_mate'].run()

def s_after_open():
    d = dock()
    d.setMinimumWidth(640)
    save(plugins['filter_mate'].toolbar, '00-toolbar')

def s_exploring_single():
    d = dock()
    d.comboBox_filtering_current_layer.setLayer(layer('troncon_de_route'))

def s_exploring_single_pick():
    d = dock()
    roads = layer('troncon_de_route')
    STATE['road_fid'] = 247881  # 'R DE LA SOLEDRA', longest named road
    d.mGroupBox_exploring_single_selection.setChecked(True)
    d.mFeaturePickerWidget_exploring_single_selection.setFeature(STATE['road_fid'])

def s_grab_exploring_single():
    d = dock()
    save(d.frame_exploring, '02-exploring-single')
    save(d, '01-dock-overview')
    save(iface.mainWindow(), '01-qgis-window', 1600)

def s_exploring_multiple():
    d = dock()
    d.mGroupBox_exploring_multiple_selection.setChecked(True)

def s_exploring_multiple_pick():
    d = dock()
    w = d.checkableComboBoxFeaturesListPickerWidget_exploring_multiple_selection
    roads = layer('troncon_de_route')
    fids = [247881, 110289, 110293, 113421]
    try:
        w.setCheckedFeatureIds(fids)
    except Exception:
        log(traceback.format_exc())

def s_grab_exploring_multiple():
    save(dock().frame_exploring, '03-exploring-multiple')

def s_exploring_custom():
    d = dock()
    d.mGroupBox_exploring_custom_selection.setChecked(True)
    d.mFieldExpressionWidget_exploring_custom_selection.setExpression('"importance" IN (\'3\', \'4\')')

def s_grab_exploring_custom():
    save(dock().frame_exploring, '04-exploring-custom')

def s_back_to_single():
    d = dock()
    d.mGroupBox_exploring_single_selection.setChecked(True)
    d.mFeaturePickerWidget_exploring_single_selection.setFeature(STATE['road_fid'])

def s_filtering_tab():
    d = dock()
    d.toolBox_tabTools.setCurrentIndex(0)
    d.pushButton_checkable_filtering_layers_to_filter.setChecked(True)
    check_combo_items(d.checkableComboBoxLayer_filtering_layers_to_filter, ['batiment', 'haie'])
    d.checkableComboBoxLayer_filtering_layers_to_filter.checkedItemsChangedEvent()
    d.pushButton_checkable_filtering_geometric_predicates.setChecked(True)
    check_combo_items(d.comboBox_filtering_geometric_predicates, ['intersect'])
    d.pushButton_checkable_filtering_buffer_value.setChecked(True)
    d.mQgsDoubleSpinBox_filtering_buffer_value.setValue(50)

def s_grab_filtering():
    d = dock()
    save(d.toolBox_tabTools, '05-filtering-tab')
    save(d, '05-dock-filtering')

def s_run_filter():
    dock().pushButton_action_filter.click()

def s_grab_filtered():
    d = dock()
    save(iface.mainWindow(), '06-filter-result', 1600)
    save(d.frame_actions, '07-action-bar')
    save(d.frame_header, '08-header-badges')
    for name in ['batiment', 'haie']:
        log(f'{name} subset={layer(name).subsetString()!r} count={layer(name).featureCount()}')

def s_add_favorite():
    d = dock()
    try:
        ok = d._favorites_ctrl.add_current_to_favorites('Buildings within 50 m of the main road')
        log(f'favorite added {ok}')
    except Exception:
        log(traceback.format_exc())

def s_favorites_menu():
    def grab_popup():
        w = QApplication.activePopupWidget()
        log(f'popup {w}')
        if w:
            screen_save(w, '09-favorites-menu')
            w.close()
    QTimer.singleShot(1200, grab_popup)
    dock()._favorites_ctrl.handle_indicator_clicked()

def s_favorites_manager():
    def grab_modal():
        w = QApplication.activeModalWidget()
        log(f'modal {w}')
        if w:
            w.resize(900, 600)
            QTimer.singleShot(400, lambda: (save(w, '10-favorites-manager'), w.reject()))
    QTimer.singleShot(1500, grab_modal)
    dock()._favorites_ctrl.show_manager_dialog()

def s_unfilter():
    dock().pushButton_action_unfilter.click()

def s_export_tab():
    d = dock()
    d.toolBox_tabTools.setCurrentIndex(1)
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
    d.lineEdit_exporting_output_folder.setText(r'C:\Users\Simon\Documents\export')

def s_grab_export():
    d = dock()
    save(d.toolBox_tabTools, '11-export-tab')
    save(d, '11-dock-export')

def s_config_tab():
    from qgis.PyQt.QtWidgets import QTreeView
    d = dock()
    d.toolBox_tabTools.setCurrentIndex(2)
    page = d.toolBox_tabTools.widget(2)
    for tv in page.findChildren(QTreeView):
        tv.expandToDepth(1)
        log(f'expanded {tv.objectName()}')

def s_grab_config():
    d = dock()
    save(d.toolBox_tabTools, '12-configuration-tab')
    save(d, '12-dock-configuration')

def s_processing():
    try:
        import processing
        dlg = processing.createAlgorithmDialog('filtermate:batch_filter')
        dlg.resize(820, 620)
        dlg.show()
        STATE['proc'] = dlg
    except Exception:
        log(traceback.format_exc())

def s_grab_processing():
    dlg = STATE.get('proc')
    if dlg:
        save(dlg, '13-processing-batch-filter')
        dlg.close()

def s_cleanup_favorite():
    d = dock()
    svc = getattr(d, '_favorites_service', None)
    log(f'svc {svc} methods={[m for m in dir(svc) if "delete" in m or "remove" in m or "all" in m or "list" in m]}')
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
    (1000, s_setup),
    (3000, s_open_plugin),
    (8000, s_after_open),
    (1500, s_exploring_single),
    (3000, s_exploring_single_pick),
    (2500, s_grab_exploring_single),
    (1000, s_exploring_multiple),
    (3000, s_exploring_multiple_pick),
    (2500, s_grab_exploring_multiple),
    (1000, s_exploring_custom),
    (2500, s_grab_exploring_custom),
    (1000, s_back_to_single),
    (2500, s_filtering_tab),
    (2500, s_grab_filtering),
    (1000, s_run_filter),
    (20000, s_grab_filtered),
    (1000, s_add_favorite),
    (2500, s_favorites_menu),
    (3000, s_favorites_manager),
    (4000, s_unfilter),
    (8000, s_export_tab),
    (2500, s_grab_export),
    (1000, s_config_tab),
    (2500, s_grab_config),
    (1000, s_processing),
    (3000, s_grab_processing),
    (1000, s_cleanup_favorite),
    (1500, s_quit),
]

def run_steps(i=0):
    if i >= len(STEPS):
        return
    delay, fn = STEPS[i]
    def go():
        log(f'--- step {i} {fn.__name__}')
        try:
            fn()
        except Exception:
            log(traceback.format_exc())
        run_steps(i + 1)
    QTimer.singleShot(delay, go)

open(LOG, 'w').close()
QTimer.singleShot(15000, run_steps)
