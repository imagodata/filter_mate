# -*- coding: utf-8 -*-
"""What the plugin calls ``iface``, outside the QGIS application.

The plugin was written against ``QgisInterface``; this class gives it the part it uses (and the
part a script written for the QGIS console most often uses), backed by the standalone window.
A method the QGIS application has and this class lacks raises ``AttributeError`` as any missing
attribute does: nothing is silently ignored. ``tests/unit/standalone`` checks that every
``iface.<method>(`` of the plugin exists here.
"""

from qgis.core import QgsProject
from qgis.PyQt.QtCore import QObject, Qt, pyqtSignal

from .qt import QAction


class StandaloneInterface(QObject):
    """The ``iface`` of the standalone application."""

    currentLayerChanged = pyqtSignal(object)
    projectRead = pyqtSignal()
    newProjectCreated = pyqtSignal()
    initializationCompleted = pyqtSignal()
    layerSavedAs = pyqtSignal(object, str)

    def __init__(self, window):
        super().__init__(window)
        self._window = window
        window.tree_view.currentLayerChanged.connect(self._relay_current_layer)

    def _relay_current_layer(self, layer):
        self.currentLayerChanged.emit(layer)

    # --- the window and its parts -------------------------------------------------------------------------------

    def mainWindow(self):
        return self._window

    def mapCanvas(self):
        return self._window.canvas

    def mapCanvases(self):
        return [self._window.canvas]

    def messageBar(self):
        return self._window.message_bar

    def layerTreeView(self):
        return self._window.tree_view

    # --- the menu of the layers: entries of plugins, as QGIS shows them ------------------------------------------

    def addCustomActionForLayerType(self, action, menu, layer_type, all_layers):
        """``action`` in the menu of the layers of ``layer_type``: every one, or those named by
        :meth:`addCustomActionForLayer` (``menu``, a submenu of QGIS, is not kept: the entry goes at the end)."""
        self._window.custom_layer_actions[action] = [layer_type, bool(all_layers), set()]

    def addCustomActionForLayer(self, action, layer):
        entry = self._window.custom_layer_actions.get(action)
        if entry is not None and layer is not None:
            entry[2].add(layer.id())

    def removeCustomActionForLayerType(self, action) -> bool:
        return self._window.custom_layer_actions.pop(action, None) is not None

    def layerTreeCanvasBridge(self):
        return self._window.bridge

    def statusBarIface(self):
        return self._window.statusBar()

    def messageTimeout(self) -> int:
        return 5

    # --- layers -------------------------------------------------------------------------------------------------

    def activeLayer(self):
        return self._window.tree_view.currentLayer()

    def setActiveLayer(self, layer) -> bool:
        try:
            if layer is None or QgsProject.instance().mapLayer(layer.id()) is None:
                return False
        except RuntimeError:  # a layer already deleted
            return False
        self._window.tree_view.setCurrentLayer(layer)
        return True

    def addVectorLayer(self, uri, name, provider):
        return self._window.sources.add_layer("vector", uri, name, provider)

    def addRasterLayer(self, uri, name="", provider="gdal"):
        return self._window.sources.add_layer("raster", uri, name, provider)

    def addPointCloudLayer(self, uri, name, provider):
        return self._window.sources.add_layer("pointcloud", uri, name, provider)

    def addProject(self, path) -> bool:
        return self._window.open_project(path)

    def newProject(self, promptToSaveFlag=False) -> bool:
        return self._window.new_project(ask=bool(promptToSaveFlag))

    def zoomFull(self):
        self._window.canvas.zoomToFullExtent()

    def zoomToActiveLayer(self):
        self._window.zoom_to_layer()

    def showAttributeTable(self, layer, filterExpression=""):
        return self._window.show_attribute_table(layer)

    def openFeatureForm(self, layer, feature, updateFeatureOnly=False, showModal=True) -> bool:
        return self._window.open_feature_form(layer, feature, modal=bool(showModal))

    # --- actions of the map -------------------------------------------------------------------------------------

    def actionPan(self):
        return self._window.actions["pan"]

    def actionZoomIn(self):
        return self._window.actions["zoom_in"]

    def actionZoomOut(self):
        return self._window.actions["zoom_out"]

    def actionZoomFullExtent(self):
        return self._window.actions["zoom_full"]

    def actionZoomToLayer(self):
        return self._window.actions["zoom_layer"]

    def actionZoomToSelected(self):
        return self._window.actions["zoom_selection"]

    def actionSelect(self):
        return self._window.actions["select"]

    def actionSelectRectangle(self):
        return self._window.actions["select"]

    def actionSelectPolygon(self):
        return self._window.actions["select_polygon"]

    def actionIdentify(self):
        return self._window.actions["identify"]

    def actionSaveAllEdits(self):
        return self._window.actions["save_edits"]

    def actionSaveActiveLayerEdits(self):
        return self._window.actions["save_edits"]

    def actionOpenTable(self):
        return self._window.actions["table"]

    # --- what a plugin adds to the window -----------------------------------------------------------------------

    def addDockWidget(self, area, dock):
        self._window.add_panel(area, dock)

    def removeDockWidget(self, dock):
        self._window.remove_panel(dock)

    def addTabifiedDockWidget(self, area, dock, tabifyWith=None, raiseTab=False):
        self._window.add_panel(area, dock)

    def addToolBar(self, name_or_toolbar, area=Qt.ToolBarArea.TopToolBarArea):
        return self._window.add_toolbar(name_or_toolbar, area)

    def addToolBarIcon(self, action: QAction) -> int:
        self._window.plugin_toolbar.addAction(action)
        return 0

    def removeToolBarIcon(self, action: QAction):
        self._window.plugin_toolbar.removeAction(action)

    def addPluginToMenu(self, name: str, action: QAction):
        self._window.plugin_menu(name).addAction(action)

    def removePluginMenu(self, name: str, action: QAction):
        self._window.remove_plugin_action(name, action)

    # The standalone window has one menu per plugin, whatever the QGIS menu it would sit in.
    addPluginToVectorMenu = addPluginToMenu
    removePluginVectorMenu = removePluginMenu
    addPluginToRasterMenu = addPluginToMenu
    removePluginRasterMenu = removePluginMenu
    addPluginToDatabaseMenu = addPluginToMenu
    removePluginDatabaseMenu = removePluginMenu
    addPluginToWebMenu = addPluginToMenu
    removePluginWebMenu = removePluginMenu

    def pluginMenu(self):
        return self._window.plugins_root_menu

    def vectorMenu(self):
        return self._window.plugins_root_menu

    def pluginToolBar(self):
        return self._window.plugin_toolbar

    def openMessageLog(self, tabName=""):
        self._window.show_log()

    def reloadConnections(self):
        self._window.sources.reload_connections()
