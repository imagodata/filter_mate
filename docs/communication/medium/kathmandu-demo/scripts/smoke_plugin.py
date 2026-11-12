import os
import sys
import traceback

from qgis.PyQt.QtCore import QSettings, QTimer
from qgis.PyQt.QtGui import QGuiApplication
from qgis.PyQt.QtWidgets import QWidget
from qgis.core import QgsProject
from qgis.utils import iface

LOG_PATH = "/demo/plugin-startup.log"
PLUGIN_ROOT = os.environ.get("FILTERMATE_PLUGIN_ROOT", "/tmp/qgisplugins")


def log(message):
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(message + "\n")


try:
    import qgis.utils

    QSettings().setValue("locale/userLocale", "en")
    qgis.utils.plugin_paths.insert(0, PLUGIN_ROOT)
    sys.path.insert(0, PLUGIN_ROOT)
    qgis.utils.updateAvailablePlugins()
    log("available=" + repr(sorted(qgis.utils.available_plugins)))

    if not qgis.utils.loadPlugin("filter_mate"):
        raise RuntimeError("QGIS could not load filter_mate")
    if not qgis.utils.startPlugin("filter_mate"):
        raise RuntimeError("QGIS could not start filter_mate")

    plugin = qgis.utils.plugins["filter_mate"]
    plugin._show_whats_new = lambda: True
    plugin._show_discord_welcome = lambda: None
    iface.mainWindow().setGeometry(0, 0, 1920, 1080)
    plugin.run()
    iface.messageBar().clearWidgets()
    log("plugin_started=" + str(plugin.pluginIsActive))
    log("dock_visible=" + str(plugin.app.dockwidget.isVisible()))
    slope_layers = QgsProject.instance().mapLayersByName("SRTM slope (%)")
    if slope_layers:
        iface.setActiveLayer(slope_layers[0])

    def dump_widgets():
        dock = plugin.app.dockwidget
        current = dock.comboBox_filtering_current_layer.currentLayer()
        log("current_layer=" + (current.name() if current else "None"))
        with open("/demo/captures/widgets.txt", "w", encoding="utf-8") as widget_file:
            for widget in dock.findChildren(QWidget):
                text = widget.text() if callable(getattr(widget, "text", None)) else ""
                widget_file.write(
                    f"{type(widget).__name__}\t{widget.objectName()}\t{text}\t"
                    f"visible={widget.isVisible()}\t{widget.toolTip()}\n"
                )

    QTimer.singleShot(2500, dump_widgets)
except Exception:
    log(traceback.format_exc())


def close_qgis():
    if iface is not None:
        QGuiApplication.primaryScreen().grabWindow(0).save(
            "/demo/captures/qgis-plugin-start.png"
        )
    if iface is not None:
        iface.mainWindow().close()


QTimer.singleShot(12000, close_qgis)
