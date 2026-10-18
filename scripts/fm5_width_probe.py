# -*- coding: utf-8 -*-
"""Width probe of the raster EXPLORING panel: which widget forces the panel wider than the dock.

Run with ``qgis-bin.exe --code fm5_width_probe.py`` (plugin from QGIS_PLUGINPATH, see
``fm5_tool_sync_check.py``); writes ``%LOCALAPPDATA%\\Temp\\fm5\\width_probe.log`` and quits.
"""
import os
import traceback

from qgis.PyQt.QtCore import QTimer
from qgis.core import QgsApplication, QgsProject, QgsRasterLayer
from qgis.utils import iface, plugins

ORTHO = os.environ.get('FM5_ORTHO', r'C:\Users\Simon\Documents\FilterMate_test_v5\data\ortho_rvb.tif')
MNT = os.environ.get('FM5_MNT', r'C:\Users\Simon\Documents\FilterMate_test_v5\data\mnt_1m.tif')
LOG = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', 'fm5', 'width_probe.log')
os.makedirs(os.path.dirname(LOG), exist_ok=True)
open(LOG, 'w', encoding='utf-8').close()


def log(text):
    with open(LOG, 'a', encoding='utf-8') as handle:
        handle.write(str(text) + '\n')


def dock():
    return plugins['filter_mate'].app.dockwidget


def controller():
    return dock()._controller_integration.coverage_controller


def layer(name):
    return QgsProject.instance().mapLayersByName(name)[0]


def s_setup():
    iface.mainWindow().showMinimized()
    project = QgsProject.instance()
    for path, name in ((MNT, 'mnt'), (ORTHO, 'ortho')):
        if os.path.exists(path):
            project.addMapLayer(QgsRasterLayer(path, name, 'gdal'))
    log(f"layers: {[lyr.name() for lyr in project.mapLayers().values()]}")


def s_open():
    from qgis.PyQt.QtCore import QSettings
    QSettings().setValue('FilterMate/discord_welcome_dismissed', True)
    import qgis.utils
    if 'filter_mate' not in plugins:
        qgis.utils.loadPlugin('filter_mate') and qgis.utils.startPlugin('filter_mate')
    plugins['filter_mate'].run()


def s_layer(name):
    def step():
        dock().comboBox_filtering_current_layer.setLayer(layer(name))
    return step


def describe(widget, depth=0, limit=4):
    if depth > limit or widget is None:
        return
    try:
        hint, minimum = widget.minimumSizeHint(), widget.minimumSize()
        geo = widget.geometry()
        log(f"{'  ' * depth}{type(widget).__name__} {widget.objectName() or ''} visible={widget.isVisible()} "
            f"geo=({geo.x()},{geo.y()},{geo.width()}x{geo.height()}) minHint={hint.width()}x{hint.height()} "
            f"min={minimum.width()}x{minimum.height()} sizeHint={widget.sizeHint().width()}")
    except Exception as exc:
        log(f"{'  ' * depth}{type(widget).__name__}: {exc}")
    for child in widget.children():
        if hasattr(child, 'geometry') and hasattr(child, 'minimumSizeHint'):
            describe(child, depth + 1, limit)


def s_probe(name):
    def step():
        try:
            from qgis.PyQt.QtWidgets import QScrollArea, QStackedWidget
            d = dock()
            panel = controller()._raster_panel
            log(f"=== {name}: dock width {d.width()}")
            stack = d.findChild(QStackedWidget, 'stackedWidget_exploring_coverage')
            if stack is not None:
                log(f"stack geo {stack.geometry().width()} minHint {stack.minimumSizeHint().width()}")
            for area in d.findChildren(QScrollArea):
                if area.isVisible() and area.widget() is not None:
                    log(f"scroll area {area.objectName()} viewport {area.viewport().width()} widget {area.widget().width()} "
                        f"widget minHint {area.widget().minimumSizeHint().width()}")
            describe(panel, 0, 3)
            d.grab().save(os.path.join(os.path.dirname(LOG), f'width_probe_{name}.png'), 'PNG')
        except Exception:
            log(traceback.format_exc())
    return step


def s_finish():
    QgsApplication.instance().quit()


STEPS = [(s_setup, 1500), (s_open, 6000), (s_layer('mnt'), 3000), (s_probe('mnt'), 1500),
         (s_layer('ortho'), 3000), (s_probe('ortho'), 1500), (s_finish, 500)]


def run_step(index=0):
    if index >= len(STEPS):
        return
    step, delay = STEPS[index]
    try:
        step()
    except Exception:
        log(traceback.format_exc())
    QTimer.singleShot(delay, lambda: run_step(index + 1))


QTimer.singleShot(1000, run_step)
