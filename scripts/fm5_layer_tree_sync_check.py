# -*- coding: utf-8 -*-
"""
FilterMate 5 - the dock follows the layer picked in the QGIS layer tree (legend link), for every kind of
layer, in a real QGIS (GUI). Also: the vector rail has its Zone button before any raster was shown.

Run like ``fm5_tool_sync_check.py`` (throw-away profile, plugin taken from the repository):

    qgis-bin.exe --nologo --lang en --profiles-path %TEMP%\\fm5\\profiles --profile fm5 --code fm5_layer_tree_sync_check.py

Environment variables: ``FM5_DATA`` (folder of the test data), ``FM5_OUT`` (log). Every check logs PASS / FAIL in
``fm5_layer_tree_sync.log``.
"""
import os
import traceback

from qgis.PyQt.QtCore import QTimer
from qgis.core import (QgsApplication, QgsPointCloudLayer, QgsProject, QgsRasterLayer, QgsVectorLayer)
from qgis.utils import iface, plugins

DATA = os.environ.get('FM5_DATA', r'C:\Users\Simon\Documents\FilterMate_test_v5\data')
OUT = os.environ.get('FM5_OUT', os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', 'fm5', 'layer_tree_sync'))
os.makedirs(OUT, exist_ok=True)
LOG = os.path.join(OUT, 'fm5_layer_tree_sync.log')
open(LOG, 'w', encoding='utf-8').close()
STATE = {'results': []}
VECTOR_ZONE = 'pushButton_checkable_exploring_vector_zone'


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


def tree():
    return iface.layerTreeView()


def shown_name():
    """Name of the layer the dock shows: the raster / point cloud of the panels, else its current vector layer."""
    ctrl = controller()
    active = ctrl.active_layer
    if active is not None:
        return active.name()
    current = dock().current_layer
    return current.name() if current is not None else None


def combo_name():
    current = dock().comboBox_filtering_current_layer.currentLayer()
    return current.name() if current is not None else None


# --- steps ----------------------------------------------------------------

def s_setup():
    mw = iface.mainWindow()
    mw.showNormal()
    mw.resize(1700, 1000)
    project = QgsProject.instance()
    gpkg = os.path.join(DATA, 'cerdagne.gpkg')
    for lyr in (QgsVectorLayer(gpkg + '|layername=parcelle', 'parcelle', 'ogr'),
                QgsVectorLayer(os.path.join(DATA, 'routes.geojson'), 'routes', 'ogr'),
                QgsVectorLayer(os.path.join(DATA, 'parcelle.shp'), 'parcelle_shp', 'ogr'),
                QgsVectorLayer('Point?crs=epsg:2154&field=nom:string', 'memoire', 'memory'),
                QgsVectorLayer('NoGeometry?field=nom:string', 'table_sans_geometrie', 'memory'),
                QgsRasterLayer(os.path.join(DATA, 'ortho_rvb.tif'), 'ortho', 'gdal'),
                QgsRasterLayer(os.path.join(DATA, 'mnt_1m.tif'), 'mnt', 'gdal'),
                QgsPointCloudLayer(os.path.join(DATA, 'lidar_hd_cerdagne.copc.laz'), 'lidar', 'copc')):
        project.addMapLayer(lyr)
    # one layer in a group of the tree
    group = project.layerTreeRoot().addGroup('groupe')
    routes_node = project.layerTreeRoot().findLayer(layer('routes').id())
    group.addChildNode(routes_node.clone())
    project.layerTreeRoot().removeChildNode(routes_node)
    iface.mapCanvas().setExtent(layer('ortho').extent())
    check('layers loaded', all(lyr.isValid() for lyr in project.mapLayers().values()), str(len(project.mapLayers())))


def s_open_plugin():
    from qgis.PyQt.QtCore import QSettings
    QSettings().setValue('FilterMate/discord_welcome_dismissed', True)  # modal welcome would block the run
    import qgis.utils
    if 'filter_mate' not in plugins:
        ok = qgis.utils.loadPlugin('filter_mate') and qgis.utils.startPlugin('filter_mate')
        log(f'plugin loaded: {ok}')
    iface.setActiveLayer(layer(os.environ.get('FM5_FIRST', 'parcelle')))  # what the user sees when the dock opens
    plugins['filter_mate'].run()


def s_first_vector_rail():
    extras = controller()._extras
    log(f"extras={extras is not None} tools={sorted(extras._tools) if extras is not None else None} "
        f"active={controller().active_layer} current={dock().current_layer} "
        f"props={len(dock().PROJECT_LAYERS)} busy={dock()._plugin_busy}")
    button = extras._tools.get(VECTOR_ZONE) if extras is not None else None
    check('vector: the Zone button exists before any raster was shown', button is not None)
    check('vector: the Zone button is visible on the rail before any raster was shown',
          button is not None and button.isVisibleTo(dock()), str(button.isVisible() if button else None))
    dock().filtering_auto_current_layer_changed(True)  # the legend link option
    check('legend link option on', dock().project_props['OPTIONS']['LAYERS']['LINK_LEGEND_LAYERS_AND_CURRENT_LAYER_FLAG'])
    check('legend link: the tree signal is connected', dock()._layer_tree_view_signal_connected)


ORDER = ['parcelle', 'ortho', 'routes', 'lidar', 'parcelle_shp', 'mnt', 'memoire', 'parcelle', 'ortho', 'parcelle']
EXPECT = {'table_sans_geometrie': None}


def make_pick(name):
    def pick():
        tree().setCurrentLayer(layer(name))

    def verify():
        check(f'tree -> dock: {name} shown by the dock', shown_name() == name, f'shown={shown_name()} combo={combo_name()}')
        check(f'tree -> dock: {name} in the layer combo', combo_name() == name, combo_name())
        check(f'tree -> dock: {name} still the layer of the tree', tree().currentLayer() is not None
              and tree().currentLayer().name() == name, tree().currentLayer().name() if tree().currentLayer() else None)
        check(f'tree -> dock: the tree signal is still connected after {name}', dock()._layer_tree_view_signal_connected)
    pick.__name__ = 's_pick_' + name
    verify.__name__ = 's_verify_' + name
    return pick, verify


def s_unsupported():
    before = shown_name()
    tree().setCurrentLayer(layer('table_sans_geometrie'))
    STATE['unsupported_before'] = before


def s_unsupported_check():
    check('tree -> dock: a table without geometry leaves the dock on its layer',
          shown_name() == STATE['unsupported_before'], f"{STATE['unsupported_before']} -> {shown_name()}")
    check('tree -> dock: the tree signal is still connected after a table without geometry',
          dock()._layer_tree_view_signal_connected)
    tree().setCurrentLayer(layer('parcelle'))


def s_after_unsupported():
    check('tree -> dock: a vector layer is followed after a table without geometry', shown_name() == 'parcelle',
          f'shown={shown_name()}')


def s_group():
    before = shown_name()
    STATE['group_before'] = before
    node = QgsProject.instance().layerTreeRoot().findGroups()[0]
    tree().setCurrentIndex(tree().layerTreeModel().node2index(node))


def s_group_check():
    check('tree -> dock: a group of the tree leaves the dock on its layer',
          shown_name() == STATE['group_before'], f"{STATE['group_before']} -> {shown_name()}")


def s_finish():
    failed = [name for name, ok in STATE['results'] if not ok]
    log(f"\n{len(STATE['results']) - len(failed)}/{len(STATE['results'])} checks passed")
    if failed:
        log('FAILED: ' + '; '.join(failed))
    QgsApplication.instance().quit()


STEPS = [(s_setup, 1500), (s_open_plugin, 7000), (s_first_vector_rail, 1000)]
for _name in ORDER:
    _pick, _verify = make_pick(_name)
    STEPS += [(_pick, 2500), (_verify, 300)]
STEPS += [(s_unsupported, 2000), (s_unsupported_check, 2000), (s_after_unsupported, 500),
          (s_group, 1500), (s_group_check, 500), (s_finish, 300)]


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
