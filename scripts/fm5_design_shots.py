# -*- coding: utf-8 -*-
"""Screenshots of the dock for the mockup comparison: dark (Night Mapping) then light."""
import os
import traceback
from qgis.PyQt.QtCore import QTimer, Qt
from qgis.core import QgsApplication, QgsPointCloudLayer, QgsProject, QgsRasterLayer, QgsVectorLayer
from qgis.utils import iface, plugins

DATA = r'\\wsl.localhost\Ubuntu\home\simon\fm5_testdata'
GPKG = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', 'fm5', 'cerdagne.gpkg')
TILE = (r'\\wsl.localhost\Ubuntu\home\simon\dev\ign-lidar-spheron-training\data\raw_tiles'
        r'\pyrenees_villages_cerdagne\LHD_FXX_0616_6153_PTS_C_LAMB93_IGN69.copc.laz')
OUT = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', 'fm5gaps', 'design')
os.makedirs(OUT, exist_ok=True)
LOG = os.path.join(OUT, 'design.log')
open(LOG, 'w').close()


def log(m):
    with open(LOG, 'a', encoding='utf-8') as h:
        h.write(str(m) + '\n')


def dock():
    return plugins['filter_mate'].app.dockwidget


def layer(n):
    return QgsProject.instance().mapLayersByName(n)[0]


def shot(name):
    d = dock()
    d.grab().save(os.path.join(OUT, name + '.png'), 'PNG')
    log('saved ' + name)


def s_theme_dark():
    QgsApplication.instance().setUITheme('Night Mapping')
    mw = iface.mainWindow(); mw.showNormal(); mw.resize(1600, 1350)
    p = QgsProject.instance()
    for n in ('batiment', 'parcelle', 'troncon_de_route'):
        p.addMapLayer(QgsVectorLayer(f'{GPKG}|layername={n}', n, 'ogr'))
    p.addMapLayer(QgsRasterLayer(os.path.join(DATA, 'mnt_1m.tif'), 'mnt', 'gdal'))
    p.addMapLayer(QgsPointCloudLayer(TILE, 'lhd', 'copc'))
    iface.mapCanvas().setExtent(layer('mnt').extent())


def s_open():
    import qgis.utils
    if 'filter_mate' not in plugins:
        qgis.utils.loadPlugin('filter_mate') and qgis.utils.startPlugin('filter_mate')
    plugins['filter_mate'].run()


def s_vector():
    d = dock()
    iface.mainWindow().resizeDocks([d], [440], Qt.Orientation.Horizontal)
    d.comboBox_filtering_current_layer.setLayer(layer('parcelle'))
    QTimer.singleShot(1500, lambda: d.comboBox_filtering_current_layer.setLayer(layer('troncon_de_route')))


def s_vector_shot():
    d = dock()
    try:
        d.mGroupBox_exploring_single_selection.setChecked(True)
    except Exception:
        pass
    QTimer.singleShot(800, lambda: shot('dark_vector'))


def s_raster():
    dock().comboBox_filtering_current_layer.setLayer(layer('mnt'))


def s_pc():
    dock().comboBox_filtering_current_layer.setLayer(layer('lhd'))


def s_light():
    QgsApplication.instance().setUITheme('default')


def s_light_vector():
    dock().comboBox_filtering_current_layer.setLayer(layer('troncon_de_route'))


def s_tabprobe():
    from qgis.PyQt.QtWidgets import QAbstractButton
    d = dock()
    tb = d.toolBox_tabTools
    buttons = [b for b in tb.findChildren(QAbstractButton) if b.objectName() == 'qt_toolbox_toolboxbutton']
    for b in buttons:
        log(f'tab {b.text()!r} geo={b.geometry().getRect()} iconSize={b.iconSize().width()}x{b.iconSize().height()} hint={b.sizeHint().height()}')
    from qgis.PyQt.QtGui import QFontDatabase, QFontInfo
    log('plex families: ' + repr([f for f in QFontDatabase.families() if 'Plex' in f]))
    log('label font: ' + QFontInfo(d.mGroupBox_exploring_single_selection.font()).family() + ' / spin: ' + QFontInfo(d.mQgsDoubleSpinBox_filtering_buffer_value.font()).family())
    for n in ('pushButton_exploring_identify', 'pushButton_checkable_filtering_layers_to_filter', 'widget_exploring_keys', 'widget_filtering_keys'):
        w = getattr(d, n)
        log(f"{n}: x={w.mapTo(d, w.rect().topLeft()).x()} size={w.width()}x{w.height()} icon={getattr(w, 'iconSize', lambda: None)() and w.iconSize().width()}")
    base = d.styleSheet()
    variants = {
        'A_current': '',
        'B_noheights': '#dockWidgetContents QToolBox#toolBox_tabTools QToolButton{min-height:0px;max-height:16777215px;height:auto;padding:6px 10px;} #dockWidgetContents QToolBox#toolBox_tabTools::tab{min-height:0px;max-height:16777215px;}',
        'C_icon16': '#dockWidgetContents QToolBox#toolBox_tabTools QToolButton{qproperty-iconSize: 16px 16px; icon-size: 16px;}',
    }
    for name, extra in variants.items():
        d.setStyleSheet(base + extra)
        d.repaint()
        if buttons:
            b = buttons[0]
            log(f'{name}: geo={b.geometry().getRect()} iconSize={b.iconSize().width()}')
            tb.grab().save(os.path.join(OUT, 'tab_' + name + '.png'), 'PNG')
    d.setStyleSheet(base)


def s_quit():
    QgsApplication.instance().quit()


STEPS = [(s_theme_dark, 2000), (s_open, 7000), (s_vector, 4000), (s_vector_shot, 2000),
         (s_raster, 4000), (lambda: shot('dark_raster'), 500), (s_pc, 5000), (lambda: shot('dark_pc'), 500), (s_tabprobe, 1500),
         (s_light, 4000), (lambda: shot('light_pc'), 500), (s_light_vector, 4000), (lambda: shot('light_vector'), 500),
         (s_quit, 500)]


def run(i=0):
    if i >= len(STEPS):
        return
    step, delay = STEPS[i]
    try:
        step()
    except Exception:
        log('ERROR step %d\n%s' % (i, traceback.format_exc()))
    QTimer.singleShot(delay, lambda: run(i + 1))


QTimer.singleShot(4000, run)
