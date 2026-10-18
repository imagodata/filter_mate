# -*- coding: utf-8 -*-
"""
FilterMate 5 - the rail tool of a selection type follows the group made active, in a real QGIS (GUI).

Run like ``fm5_gui_check.py`` (throw-away profile, plugin taken from the repository):

    set QGIS_PLUGINPATH=\\\\wsl.localhost\\Ubuntu\\home\\simon\\dev
    qgis-bin.exe --nologo --lang en --profiles-path %TEMP%\\fm5\\profiles --profile fm5 --code fm5_tool_sync_check.py

Environment variables: ``FM5_ORTHO`` (an RGB GeoTIFF), ``FM5_TILE`` (a COPC tile with a
Classification), ``FM5_OUT`` (log). Every check logs PASS / FAIL in ``fm5_tool_sync.log``.

Raster: checking or expanding PIPETTE puts the pipette on the map, another group takes it
off, the pipette button off leaves the group alone; the detector button is the same tool with
the object target (R4, 2026-10-18). Point cloud: CLASSES puts the class pipette on (the
Identify button, since 2026-10-18), ATTRIBUTES / EXPRESSION take it off, the class pipette on
makes CLASSES active.
Selecting a layer never puts a tool on the map by itself.
"""
import os
import traceback

from qgis.PyQt.QtCore import QTimer
from qgis.core import QgsApplication, QgsPointCloudLayer, QgsProject, QgsRasterLayer
from qgis.utils import iface, plugins

ORTHO = os.environ.get('FM5_ORTHO', r'C:\Users\Simon\Documents\FilterMate_test_v5\data\ortho_rvb.tif')
TILE = os.environ.get('FM5_TILE', r'\\wsl.localhost\Ubuntu\home\simon\dev\ign-lidar-spheron-training\data\raw_tiles'
                                  r'\pyrenees_villages_cerdagne\LHD_FXX_0616_6153_PTS_C_LAMB93_IGN69.copc.laz')
OUT = os.environ.get('FM5_OUT', os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', 'fm5', 'tool_sync'))
os.makedirs(OUT, exist_ok=True)
LOG = os.path.join(OUT, 'fm5_tool_sync.log')
open(LOG, 'w', encoding='utf-8').close()
STATE = {'results': []}


def log(message):
    with open(LOG, 'a', encoding='utf-8') as handle:
        handle.write(str(message) + '\n')


def check(name, condition, detail=''):
    STATE['results'].append((name, bool(condition)))
    log(f"{'PASS' if condition else 'FAIL'}  {name}  {detail}")


def dock():
    return plugins['filter_mate'].app.dockwidget


def controller():
    return dock()._controller_integration.coverage_controller


def layer(name):
    return QgsProject.instance().mapLayersByName(name)[0]


def map_tool():
    return iface.mapCanvas().mapTool()


def tool_name():
    tool = map_tool()
    return type(tool).__name__ if tool is not None else 'None'


def button(name):
    return controller()._extras._tools[name]


PIPETTE = 'pushButton_checkable_exploring_raster_pipette'
DETECTOR = 'pushButton_checkable_exploring_raster_detector'


def class_pipette_button():
    """The class pipette of a point cloud is the Identify button of the dock (held down while on the map)."""
    return dock().pushButton_exploring_identify


def pipette_on():
    ctrl = controller()
    return button(PIPETTE).isChecked() and ctrl._pixel_tool is not None and map_tool() is ctrl._pixel_tool


def pipette_off():
    ctrl = controller()
    return not button(PIPETTE).isChecked() and (ctrl._pixel_tool is None or map_tool() is not ctrl._pixel_tool)


def class_pipette_on():
    ctrl = controller()
    return class_pipette_button().isDown() and ctrl._class_tool is not None and map_tool() is ctrl._class_tool


def class_pipette_off():
    ctrl = controller()
    return not class_pipette_button().isDown() and (ctrl._class_tool is None or map_tool() is not ctrl._class_tool)


def detector_on():
    ctrl = controller()
    panel = ctrl._raster_panel
    return (button(DETECTOR).isChecked() and not button(PIPETTE).isChecked() and panel.pick_target() == 'object'
            and ctrl._pixel_tool is not None and map_tool() is ctrl._pixel_tool)


# --- steps ----------------------------------------------------------------

def s_setup():
    mw = iface.mainWindow()
    mw.showNormal()
    mw.resize(1700, 1000)
    project = QgsProject.instance()
    project.addMapLayer(QgsRasterLayer(ORTHO, 'ortho', 'gdal'))
    project.addMapLayer(QgsPointCloudLayer(TILE, 'lhd', 'copc'))
    iface.mapCanvas().setExtent(layer('ortho').extent())
    iface.actionPan().trigger()
    check('layers loaded', all(lyr.isValid() for lyr in project.mapLayers().values()), str(len(project.mapLayers())))


def s_open_plugin():
    from qgis.PyQt.QtCore import QSettings
    QSettings().setValue('FilterMate/discord_welcome_dismissed', True)  # modal welcome would block the run
    import qgis.utils
    if 'filter_mate' not in plugins:
        ok = qgis.utils.loadPlugin('filter_mate') and qgis.utils.startPlugin('filter_mate')
        log(f'plugin loaded: {ok}')
    plugins['filter_mate'].run()


def s_raster():
    dock().comboBox_filtering_current_layer.setLayer(layer('ortho'))


def s_raster_check():
    panel = controller()._raster_panel
    check('raster: selecting the layer puts no tool on the map', pipette_off(), tool_name())
    panel._pipette_group.setChecked(True)  # what a click on the group switch does
    check('raster: PIPETTE checked puts the pipette on', pipette_on() and panel.active_mode().value == 'pipette', tool_name())
    panel._range_group.setChecked(True)
    check('raster: VALUE RANGE checked takes the pipette off', pipette_off() and panel.active_mode().value == 'range',
          tool_name())
    check('raster: the previous map tool comes back', tool_name() != 'PixelPickerTool', tool_name())
    button(DETECTOR).setChecked(True)
    check('raster: the detector button puts the picker on with the object target and PIPETTE active',
          detector_on() and panel.active_mode().value == 'pipette', tool_name())
    button(PIPETTE).setChecked(True)
    check('raster: the pipette button takes the similar target, the detector goes up',
          pipette_on() and not button(DETECTOR).isChecked() and panel.pick_target() == 'similar', tool_name())
    panel._target_buttons['object'].setChecked(True)  # the segmented control of the group
    check('raster: the group target moves the rail (R4)', detector_on(), tool_name())
    panel._range_group.setChecked(True)
    check('raster: VALUE RANGE takes the detector off too', pipette_off() and not button(DETECTOR).isChecked(), tool_name())
    panel._target_buttons['similar'].setChecked(True)
    panel._pipette_group.setCollapsed(False)  # expanding a group makes it the active one
    check('raster: PIPETTE expanded puts the pipette on', pipette_on() and panel.active_mode().value == 'pipette', tool_name())
    panel._expression_group.setChecked(True)
    check('raster: EXPRESSION checked takes the pipette off', pipette_off() and panel.active_mode().value == 'expression',
          tool_name())
    button(PIPETTE).setChecked(True)
    check('raster: the pipette button makes PIPETTE active', pipette_on() and panel.active_mode().value == 'pipette',
          tool_name())
    button(PIPETTE).setChecked(False)
    check('raster: the pipette button off leaves PIPETTE active', pipette_off() and panel.active_mode().value == 'pipette',
          tool_name())
    panel._pipette_group.setChecked(False)  # unchecking the active group keeps it (exclusive groups)
    check('raster: unchecking PIPETTE keeps it, no tool', pipette_off() and panel._pipette_group.isChecked(), tool_name())
    panel._range_group.setChecked(True)
    panel._pipette_group.setChecked(True)
    iface.actionPan().trigger()
    check('raster: another QGIS tool takes the pipette off, PIPETTE stays',
          pipette_off() and panel.active_mode().value == 'pipette', tool_name())


def s_point_cloud():
    dock().comboBox_filtering_current_layer.setLayer(layer('lhd'))


def s_point_cloud_check():
    panel = controller()._pc_panel
    check('point cloud: the pipette left with the raster', pipette_off(), tool_name())
    check('point cloud: selecting the layer puts no tool on the map', class_pipette_off(), tool_name())
    check('point cloud: the class pipette (Identify) is usable', class_pipette_button().isEnabled()
          and not panel._classes_group.isHidden())
    panel._ranges_group.setChecked(True)
    check('point cloud: ATTRIBUTES checked, no class pipette', class_pipette_off() and panel._ranges_group.isChecked(),
          tool_name())
    panel._classes_group.setChecked(True)
    check('point cloud: CLASSES checked puts the class pipette on', class_pipette_on() and panel._classes_group.isChecked(),
          tool_name())
    panel._expression_group.setChecked(True)
    check('point cloud: EXPRESSION checked takes the class pipette off',
          class_pipette_off() and panel._expression_group.isChecked(), tool_name())
    panel._classes_group.setCollapsed(False)
    check('point cloud: CLASSES expanded puts the class pipette on', class_pipette_on() and panel._classes_group.isChecked(),
          tool_name())
    panel._ranges_group.setChecked(True)
    check('point cloud: ATTRIBUTES checked takes the class pipette off', class_pipette_off(), tool_name())
    controller().handle_exploring_action('identify')
    check('point cloud: the Identify button makes CLASSES active',
          class_pipette_on() and panel._classes_group.isChecked() and not panel._ranges_group.isChecked(), tool_name())
    controller().handle_exploring_action('identify')
    check('point cloud: Identify again takes the class pipette off and leaves CLASSES active',
          class_pipette_off() and panel._classes_group.isChecked(), tool_name())
    controller().handle_exploring_action('identify')
    check('point cloud: the class pipette is on before leaving the layer', class_pipette_on(), tool_name())


def s_back_to_raster():
    dock().comboBox_filtering_current_layer.setLayer(layer('ortho'))


def s_back_to_raster_check():
    check('raster again: no tool put on the map by the layer change', pipette_off() and class_pipette_off(), tool_name())
    button(PIPETTE).setChecked(True)
    check('raster again: the pipette is on before leaving the layer', pipette_on(), tool_name())


def s_point_cloud_again():
    dock().comboBox_filtering_current_layer.setLayer(layer('lhd'))


def s_point_cloud_again_check():
    check('point cloud again: the class pipette comes back with the layer (R3)', class_pipette_on(), tool_name())
    controller().handle_exploring_action('identify')


def s_raster_last():
    dock().comboBox_filtering_current_layer.setLayer(layer('ortho'))


def s_raster_last_check():
    check('raster last: the pipette comes back with the layer (R3)', pipette_on(), tool_name())
    button(PIPETTE).setChecked(False)


def s_finish():
    failed = [name for name, ok in STATE['results'] if not ok]
    log(f"\n{len(STATE['results']) - len(failed)}/{len(STATE['results'])} checks passed")
    if failed:
        log('FAILED: ' + '; '.join(failed))
    QgsApplication.instance().quit()


STEPS = [
    (s_setup, 1500), (s_open_plugin, 6000), (s_raster, 3000), (s_raster_check, 1500),
    (s_point_cloud, 4000), (s_point_cloud_check, 1500), (s_back_to_raster, 3000), (s_back_to_raster_check, 500),
    (s_point_cloud_again, 3000), (s_point_cloud_again_check, 500), (s_raster_last, 3000), (s_raster_last_check, 500),
    (s_finish, 500),
]


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
