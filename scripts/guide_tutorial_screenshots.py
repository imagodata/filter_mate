# -*- coding: utf-8 -*-
"""Per-step screenshots of the guide tutorial (whole QGIS window at each step).

Usage, without a screen: ``scripts/guide_screenshots_headless.sh tutorial`` (then ``publish``); or in a desktop
QGIS with a throwaway profile: ``qgis --nologo --lang en --code scripts/guide_tutorial_screenshots.py``.
See scripts/guide_screenshots.py for the details; set FM_GUIDE_OUT and FM_GUIDE_GPKG. The dock is the one of a
new install: the rail of sections, every section in it, EXPLORING and FILTERING open.
"""
import os
import time
import traceback

from qgis.PyQt.QtCore import QSettings, QTimer, Qt
from qgis.PyQt.QtWidgets import QDockWidget
from qgis.core import QgsApplication, QgsProject, QgsVectorLayer, QgsRectangle
from qgis.utils import iface, plugins

OUT = os.environ.get('FM_GUIDE_OUT') or os.path.join(os.environ.get('TEMP', '/tmp'), 'fm_shots')
os.makedirs(OUT, exist_ok=True)
LOG = os.path.join(OUT, 'tuto.log')
GPKG = os.environ.get('FM_GUIDE_GPKG') or r'C:\Users\Simon\Documents\31.gpkg'
ROAD_FID = 247881
DOCK_WIDTH = 413
STEP_TIMEOUT = 60.0
STATE = {}


def log(m):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(str(m) + '\n')


def save_window(name):
    iface.messageBar().clearWidgets()  # first-run notices of a throwaway profile
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


def tasks_idle():
    return not [t for t in QgsApplication.taskManager().activeTasks() if 'FilterMate' in t.description()]


def settled(seconds=2.0):
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


def set_tutorial_extent():
    if 'extent' not in STATE:
        f = layer('troncon_de_route').getFeature(ROAD_FID)
        bb = f.geometry().boundingBox()
        bb.scale(4.5)
        STATE['extent'] = QgsRectangle(bb)
    iface.mapCanvas().setExtent(STATE['extent'])
    iface.mapCanvas().refresh()


def s_setup():
    QSettings().setValue('FilterMate/discord_welcome_dismissed', True)  # modal dialogs would block the run
    QSettings().setValue('FilterMate/whats_new_seen', 99)
    QSettings().setValue('qgis/digitizing/validate_geometries', 0)
    mw = iface.mainWindow()
    mw.showNormal()
    mw.resize(1760, 1040)
    for name in ['commune', 'cours_d_eau', 'haie', 'troncon_de_route', 'batiment']:
        QgsProject.instance().addMapLayer(QgsVectorLayer(f'{GPKG}|layername={name}', name, 'ogr'))
    iface.mapCanvas().zoomToFullExtent()
    for d in mw.findChildren(QDockWidget):
        if d.objectName() in ('MessageLog', 'Browser', 'Browser2'):
            d.hide()


def s_open():
    import qgis.utils
    if 'filter_mate' not in plugins:  # throwaway profile: the plugin is found but not enabled
        qgis.utils.loadPlugin('filter_mate') and qgis.utils.startPlugin('filter_mate')
    plugins['filter_mate'].run()
    return lambda: plugins['filter_mate'].app is not None and dock() is not None and dock().isVisible() \
        and tasks_idle()


def s_step1():
    d = dock()
    if d._fm_panels.detached():  # the dock of a new install
        d._fm_panels.attach_all()
    d.setMinimumWidth(0)
    iface.mainWindow().resizeDocks([d], [DOCK_WIDTH], Qt.Orientation.Horizontal)
    d._fm_sections.open_top('exploring')
    d.toolBox_tabTools.setCurrentWidget(d.FILTERING)
    return current_is('troncon_de_route')


def s_grab1():
    save_window('tuto-01')


def s_step2():
    d = dock()
    d.mGroupBox_exploring_single_selection.setChecked(True)
    d.mFieldExpressionWidget_exploring_single_selection.setExpression('nom_collaboratif_gauche')
    d.mFeaturePickerWidget_exploring_single_selection.setFeature(ROAD_FID)
    d.pushButton_checkable_exploring_selecting.setChecked(True)  # the road selected on the map: in yellow
    return settled(3.0)


def s_step2_extent():
    set_tutorial_extent()
    return settled(2.0)


def s_grab2():
    save_window('tuto-02')


def s_step3():
    d = dock()
    d.toolBox_tabTools.setCurrentWidget(d.FILTERING)
    d.pushButton_checkable_filtering_layers_to_filter.setChecked(True)
    check_combo_items(d.checkableComboBoxLayer_filtering_layers_to_filter, ['batiment', 'haie'])
    d.checkableComboBoxLayer_filtering_layers_to_filter.checkedItemsChangedEvent()
    return settled(2.5)


def s_grab3():
    save_window('tuto-03')


def s_step4():
    d = dock()
    d.pushButton_checkable_filtering_geometric_predicates.setChecked(True)
    check_combo_items(d.comboBox_filtering_geometric_predicates, ['intersect'])
    return settled(2.0)


def s_grab4():
    save_window('tuto-04')


def s_step5():
    d = dock()
    d.pushButton_checkable_filtering_buffer_value.setChecked(True)
    d.mQgsDoubleSpinBox_filtering_buffer_value.setValue(50)
    return settled(2.0)


def s_grab5():
    save_window('tuto-05')


def s_step6():
    dock().pushButton_action_filter.click()
    since = time.time()
    return lambda: layer('batiment').subsetString() != '' and tasks_idle() and time.time() - since > 3.0


def s_step6_extent():
    set_tutorial_extent()
    for name in ['batiment', 'haie']:
        log(f'{name} subset_len={len(layer(name).subsetString())}')
    return settled(2.5)


def s_grab6():
    save_window('tuto-06')


def s_quit():
    QgsProject.instance().setDirty(False)
    QgsApplication.instance().quit()


STEPS = [s_setup, s_open, s_step1, s_grab1, s_step2, s_step2_extent, s_grab2, s_step3, s_grab3, s_step4, s_grab4,
         s_step5, s_grab5, s_step6, s_step6_extent, s_grab6, s_quit]


def run_step(i=0):
    if i >= len(STEPS):
        return
    fn = STEPS[i]
    log(f'--- {fn.__name__}')
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
