# -*- coding: utf-8 -*-
"""Per-step screenshots of the guide tutorial (whole QGIS window at each step).

Usage: qgis-bin.exe --nologo --lang en --code scripts/guide_tutorial_screenshots.py
See scripts/guide_screenshots.py for the launch details; adjust OUT and GPKG.
"""
import os, traceback
from qgis.PyQt.QtCore import QTimer, Qt
from qgis.PyQt.QtWidgets import QDockWidget
from qgis.core import QgsApplication, QgsProject, QgsVectorLayer, QgsRectangle
from qgis.utils import iface, plugins

OUT = r'C:\Users\Simon\AppData\Local\Temp\fm_shots\tuto'
LOG = os.path.join(OUT, 'tuto.log')
GPKG = r'C:\Users\Simon\Documents\31.gpkg'
ROAD_FID = 247881
STATE = {}

def log(m):
    open(LOG, 'a', encoding='utf-8').write(str(m) + '\n')

def save_window(name):
    pm = iface.mainWindow().grab().scaledToWidth(1600, Qt.TransformationMode.SmoothTransformation)
    log(f'{name} {pm.width()}x{pm.height()} ok={pm.save(os.path.join(OUT, name + ".png"), "PNG")}')

def dock():
    return plugins['filter_mate'].app.dockwidget

def layer(name):
    return QgsProject.instance().mapLayersByName(name)[0]

def check_combo_items(combo, texts):
    model = combo.model()
    for i in range(model.rowCount()):
        item = model.item(i)
        if any(t.lower() in item.text().lower() for t in texts):
            item.setCheckState(Qt.CheckState.Checked)

def set_tutorial_extent():
    if 'extent' not in STATE:
        f = layer('troncon_de_route').getFeature(ROAD_FID)
        bb = f.geometry().boundingBox()
        bb.scale(4.5)
        STATE['extent'] = QgsRectangle(bb)
    iface.mapCanvas().setExtent(STATE['extent'])
    iface.mapCanvas().refresh()

def s_setup():
    mw = iface.mainWindow()
    mw.showNormal(); mw.resize(1760, 1040)
    for name in ['commune', 'cours_d_eau', 'haie', 'troncon_de_route', 'batiment']:
        QgsProject.instance().addMapLayer(QgsVectorLayer(f'{GPKG}|layername={name}', name, 'ogr'))
    iface.mapCanvas().zoomToFullExtent()
    for d in mw.findChildren(QDockWidget):
        if d.objectName() in ('MessageLog', 'Browser', 'Browser2'):
            d.hide()

def s_open():
    plugins['filter_mate'].run()

def s_step1():
    dock().setMinimumWidth(640)
    iface.setActiveLayer(layer('troncon_de_route'))

def s_grab1():
    save_window('tuto-01-source-layer')

def s_step2():
    d = dock()
    d.mGroupBox_exploring_single_selection.setChecked(True)
    d.mFeaturePickerWidget_exploring_single_selection.setFeature(ROAD_FID)

def s_step2_extent():
    set_tutorial_extent()

def s_grab2():
    save_window('tuto-02-pick-road')

def s_step3():
    d = dock()
    d.toolBox_tabTools.setCurrentIndex(0)
    d.pushButton_checkable_filtering_layers_to_filter.setChecked(True)
    check_combo_items(d.checkableComboBoxLayer_filtering_layers_to_filter, ['batiment', 'haie'])
    d.checkableComboBoxLayer_filtering_layers_to_filter.checkedItemsChangedEvent()

def s_grab3():
    save_window('tuto-03-target-layers')

def s_step4():
    d = dock()
    d.pushButton_checkable_filtering_geometric_predicates.setChecked(True)
    check_combo_items(d.comboBox_filtering_geometric_predicates, ['intersect'])

def s_grab4():
    save_window('tuto-04-predicate')

def s_step5():
    d = dock()
    d.pushButton_checkable_filtering_buffer_value.setChecked(True)
    d.mQgsDoubleSpinBox_filtering_buffer_value.setValue(50)

def s_grab5():
    save_window('tuto-05-buffer')

def s_step6():
    dock().pushButton_action_filter.click()

def s_step6_extent():
    set_tutorial_extent()
    for name in ['batiment', 'haie']:
        log(f'{name} subset_len={len(layer(name).subsetString())}')

def s_grab6():
    save_window('tuto-06-result')

def s_quit():
    QgsProject.instance().setDirty(False)
    QgsApplication.instance().quit()

STEPS = [
    (1000, s_setup), (3000, s_open), (8000, s_step1), (3500, s_grab1),
    (1000, s_step2), (3500, s_step2_extent), (2000, s_grab2),
    (1000, s_step3), (2500, s_grab3),
    (1000, s_step4), (2000, s_grab4),
    (1000, s_step5), (2000, s_grab5),
    (1000, s_step6), (20000, s_step6_extent), (2500, s_grab6),
    (1500, s_quit),
]

def run_steps(i=0):
    if i >= len(STEPS):
        return
    delay, fn = STEPS[i]
    def go():
        log(f'--- {fn.__name__}')
        try:
            fn()
        except Exception:
            log(traceback.format_exc())
        run_steps(i + 1)
    QTimer.singleShot(delay, go)

open(LOG, 'w').close()
QTimer.singleShot(15000, run_steps)
