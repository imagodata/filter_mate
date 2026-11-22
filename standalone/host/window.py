# -*- coding: utf-8 -*-
"""The main window of the standalone application: a map, a layer panel, and room for the dock.

Built from the widgets of the QGIS libraries, so that what the plugin finds around its dock is
what it finds in the QGIS application: a ``QgsMapCanvas``, a ``QgsLayerTreeView`` whose current
layer is the active one, a ``QgsMessageBar``, a ``View > Panels`` menu under the name QGIS
gives it, and dock places that are remembered from one session to the next.
"""

import os

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateTransform,
    QgsLayerTreeModel,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsVectorLayer,
)
from qgis.gui import (
    QgsAttributeDialog,
    QgsAttributeEditorContext,
    QgsLayerTreeMapCanvasBridge,
    QgsLayerTreeView,
    QgsLayerTreeViewMenuProvider,
    QgsMapCanvas,
    QgsMapToolPan,
    QgsMapToolZoom,
    QgsMessageBar,
    QgsProjectionSelectionDialog,
)
from qgis.PyQt.QtCore import QSettings, Qt, QTimer
from qgis.PyQt.QtGui import QColor, QKeySequence
from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QSizePolicy,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import version as filtermate_version
from .attribute_table import AttributeTableDialog
from .compat import enum_member, message_level
from .map_tools import IdentifyTool, PolygonSelectTool, SelectTool
from .qt import QAction, _tr
from .sources import PROJECT_SUFFIXES, Sources

PANEL_MENU_NAME = "mPanelMenu"  # the name QGIS gives View > Panels: the plugin lists its panels there
TOOLBAR_MENU_NAME = "mToolbarMenu"
STATE_KEY = "FilterMateStandalone/windowState"
GEOMETRY_KEY = "FilterMateStandalone/windowGeometry"
PROJECT_FILTER = "QGIS projects (*.qgz *.qgs)"


def _icon(name: str):
    return QgsApplication.getThemeIcon(name)


class _TreeMenu(QgsLayerTreeViewMenuProvider):
    """The context menu of the layer panel."""

    def __init__(self, window):
        super().__init__()
        self._window = window

    def createContextMenu(self):
        window = self._window
        view = window.tree_view
        menu = QMenu()
        actions = view.defaultActions()
        layer = view.currentLayer()
        if layer is None:
            menu.addAction(actions.actionAddGroup(menu))
            if view.currentNode() is not None:
                menu.addAction(actions.actionRenameGroupOrLayer(menu))
                menu.addAction(actions.actionRemoveGroupOrLayer(menu))
            return menu
        try:
            menu.addAction(actions.actionZoomToLayers(window.canvas, menu))
        except (AttributeError, TypeError):  # QGIS 3.22: the singular form
            menu.addAction(actions.actionZoomToLayer(window.canvas, menu))
        if isinstance(layer, QgsVectorLayer):
            menu.addAction(actions.actionZoomToSelection(window.canvas, menu))
            menu.addAction(actions.actionShowFeatureCount(menu))
            menu.addSeparator()
            menu.addAction(window.actions["table"])
            menu.addAction(window.actions["deselect"])
        menu.addSeparator()
        menu.addAction(actions.actionRenameGroupOrLayer(menu))
        menu.addAction(actions.actionRemoveGroupOrLayer(menu))
        menu.addSeparator()
        menu.addAction(window.actions["properties"])
        return menu


class StandaloneWindow(QMainWindow):
    """The window around the FilterMate dock."""

    _reading_project = False  # True while a project file loads: its layers must not change its CRS

    def __init__(self, interactive: bool = True):
        super().__init__()
        self.setObjectName("FilterMateStandaloneWindow")
        self.setDockNestingEnabled(True)
        self.setAcceptDrops(True)
        self.interactive = interactive
        self.actions = {}
        self._tables = []
        self._plugin_menus = {}
        self._plugins_root_menu = None
        self.browser_model = None
        self._browser_dock = None
        self._project_path = ""
        self.interface = None  # set by the application once the interface exists

        self._build_centre()
        self._build_layer_panel()
        self.sources = Sources(self)
        self.sources.interactive = interactive
        self._build_tools()
        self._build_log_panel()
        self._build_menus()
        self._build_status_bar()
        self._connect_project()
        self._update_title()
        self.resize(1440, 900)

    # --- construction -------------------------------------------------------------------------------------------

    def _build_centre(self):
        centre = QWidget(self)
        layout = QVBoxLayout(centre)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.message_bar = QgsMessageBar(centre)
        self.message_bar.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.canvas = QgsMapCanvas(centre)
        self.canvas.setObjectName("theMapCanvas")  # the name QGIS saves the extent under in a project file
        self.canvas.setCanvasColor(QColor(255, 255, 255))
        self.canvas.enableAntiAliasing(True)
        if hasattr(self.canvas, "setProject"):
            self.canvas.setProject(QgsProject.instance())
        layout.addWidget(self.message_bar)
        layout.addWidget(self.canvas, 1)
        self.setCentralWidget(centre)

    def _build_layer_panel(self):
        project = QgsProject.instance()
        root = project.layerTreeRoot()
        self.bridge = QgsLayerTreeMapCanvasBridge(root, self.canvas, self)
        if hasattr(self.bridge, "setAutoSetupOnFirstLayer"):
            self.bridge.setAutoSetupOnFirstLayer(False)  # done here, with the project's CRS (see _on_layers_added)
        self.tree_model = QgsLayerTreeModel(root, self)
        for flag in ("AllowNodeReorder", "AllowNodeRename", "AllowNodeChangeVisibility", "ShowLegendAsTree",
                     "UseEmbeddedWidgets", "UseTextFormatting"):
            try:
                self.tree_model.setFlag(enum_member(QgsLayerTreeModel, "Flag", flag))
            except AttributeError:  # a flag this version does not have
                pass
        self.tree_model.setAutoCollapseLegendNodes(10)
        self.tree_view = QgsLayerTreeView(self)
        self.tree_view.setModel(self.tree_model)
        self._tree_menu = _TreeMenu(self)
        self.tree_view.setMenuProvider(self._tree_menu)
        self.tree_view.currentLayerChanged.connect(self._on_current_layer)
        self.layers_dock = QDockWidget(_tr("Layers"), self)
        self.layers_dock.setObjectName("Layers")
        self.layers_dock.setWidget(self.tree_view)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.layers_dock)

    def _action(self, key, text, icon=None, slot=None, shortcut=None, checkable=False, tip=None):
        action = QAction(_icon(icon), text, self) if icon else QAction(text, self)
        action.setObjectName("fm_action_" + key)
        action.setCheckable(checkable)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.setToolTip(tip or text.replace("&", ""))
        if slot is not None:
            action.triggered.connect(lambda _checked=False: slot())
        self.actions[key] = action
        return action

    def _build_tools(self):
        add = self._action
        add("new", _tr("&New project"), "/mActionFileNew.svg", lambda: self.new_project(ask=True), "Ctrl+N")
        add("open", _tr("&Open project..."), "/mActionFileOpen.svg", self.choose_project, "Ctrl+O")
        add("save", _tr("&Save project"), "/mActionFileSave.svg", self.save_project, "Ctrl+S")
        add("save_as", _tr("Save project &as..."), "/mActionFileSaveAs.svg", lambda: self.save_project(ask_path=True),
            "Ctrl+Shift+S")
        add("add_layers", _tr("&Add layers..."), "/mActionDataSourceManager.svg", self.sources.show_dialog, "Ctrl+L")
        add("add_files", _tr("Add &files..."), "/mActionAddOgrLayer.svg", self.choose_files, "Ctrl+Shift+V")
        add("basemap", _tr("Add the OpenStreetMap &basemap"), "/mActionAddXyzLayer.svg", self.sources.add_basemap)
        add("quit", _tr("&Quit"), None, self.close, "Ctrl+Q")

        add("pan", _tr("Pan"), "/mActionPan.svg", checkable=True)
        add("zoom_in", _tr("Zoom in"), "/mActionZoomIn.svg", checkable=True)
        add("zoom_out", _tr("Zoom out"), "/mActionZoomOut.svg", checkable=True)
        add("zoom_full", _tr("Zoom to everything"), "/mActionZoomFullExtent.svg", self.canvas.zoomToFullExtent)
        add("zoom_layer", _tr("Zoom to the layer"), "/mActionZoomToLayer.svg", self.zoom_to_layer)
        add("zoom_selection", _tr("Zoom to the selection"), "/mActionZoomToSelected.svg", self.zoom_to_selection)
        add("refresh", _tr("Refresh"), "/mActionRefresh.svg", self.canvas.refreshAllLayers, "F5")
        add("select", _tr("Select features"), "/mActionSelectRectangle.svg", checkable=True,
            tip=_tr("Select features: click or drag (Shift adds, Ctrl removes)"))
        add("select_polygon", _tr("Select by polygon"), "/mActionSelectPolygon.svg", checkable=True,
            tip=_tr("Select by polygon: left clicks draw, a right click ends"))
        add("deselect", _tr("Deselect all"), "/mActionDeselectAll.svg", self.deselect_all)
        add("identify", _tr("Identify"), "/mActionIdentify.svg", checkable=True)
        add("table", _tr("Open the attribute table"), "/mActionOpenTable.svg", lambda: self.show_attribute_table(), "F6")
        add("properties", _tr("Layer properties..."), "/mActionOptions.svg", self.show_layer_properties)
        add("about", _tr("About FilterMate"), None, self.show_about)

        self._map_tools = {
            "pan": QgsMapToolPan(self.canvas),
            "zoom_in": QgsMapToolZoom(self.canvas, False),
            "zoom_out": QgsMapToolZoom(self.canvas, True),
            "select": SelectTool(self),
            "select_polygon": PolygonSelectTool(self),
            "identify": IdentifyTool(self),
        }
        for key, tool in self._map_tools.items():
            tool.setAction(self.actions[key])
            self.actions[key].triggered.connect(lambda _checked=False, t=tool: self.canvas.setMapTool(t))
        self.canvas.setMapTool(self._map_tools["pan"])

        self.file_toolbar = self._toolbar("mFileToolBar", _tr("Project"),
                                          ("new", "open", "save", None, "add_layers", "add_files"))
        self.map_toolbar = self._toolbar("mMapNavToolBar", _tr("Map"),
                                         ("pan", "zoom_in", "zoom_out", "zoom_full", "zoom_layer", "zoom_selection",
                                          "refresh", None, "select", "select_polygon", "deselect", "identify", "table"))
        self.plugin_toolbar = QToolBar(_tr("Plugins"), self)
        self.plugin_toolbar.setObjectName("mPluginToolBar")
        self.addToolBar(self.plugin_toolbar)

    def _toolbar(self, name, title, keys):
        bar = QToolBar(title, self)
        bar.setObjectName(name)
        for key in keys:
            if key is None:
                bar.addSeparator()
            else:
                bar.addAction(self.actions[key])
        self.addToolBar(bar)
        return bar

    def _build_log_panel(self):
        self.log_view = QPlainTextEdit(self)
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(5000)
        self.log_dock = QDockWidget(_tr("Log messages"), self)
        self.log_dock.setObjectName("MessageLog")
        self.log_dock.setWidget(self.log_view)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)
        self.log_dock.hide()
        QgsApplication.messageLog().messageReceived.connect(self._on_log_message)

    def _on_log_message(self, *arguments):
        if len(arguments) != 3:  # the other signal of the same name (a boolean)
            return
        message, tag, level = arguments
        names = {message_level("Warning"): "WARNING", message_level("Critical"): "CRITICAL",
                 message_level("Success"): "SUCCESS"}
        try:
            self.log_view.appendPlainText(f"{names.get(level, 'INFO')}  {tag}: {message}")
        except RuntimeError:  # a message of a thread that ends after the window
            pass

    def _build_menus(self):
        bar = self.menuBar()
        project = bar.addMenu(_tr("&Project"))
        project.setObjectName("mProjectMenu")
        for key in ("new", "open", "save", "save_as", None, "quit"):
            project.addSeparator() if key is None else project.addAction(self.actions[key])

        layer = bar.addMenu(_tr("&Layer"))
        layer.setObjectName("mLayerMenu")
        for key in ("add_layers", "add_files", "basemap", None, "table", "properties"):
            layer.addSeparator() if key is None else layer.addAction(self.actions[key])

        view = bar.addMenu(_tr("&View"))
        view.setObjectName("mViewMenu")
        for key in ("pan", "zoom_in", "zoom_out", "zoom_full", "zoom_layer", "zoom_selection", "refresh", None,
                    "select", "select_polygon", "deselect", "identify"):
            view.addSeparator() if key is None else view.addAction(self.actions[key])
        view.addSeparator()
        self.panel_menu = view.addMenu(_tr("Panels"))
        self.panel_menu.setObjectName(PANEL_MENU_NAME)
        self.panel_menu.addAction(self.layers_dock.toggleViewAction())
        self._browser_action = QAction(_tr("Browser"), self)
        self._browser_action.setCheckable(True)
        self._browser_action.triggered.connect(self._toggle_browser)
        self.panel_menu.addAction(self._browser_action)
        self.panel_menu.addAction(self.log_dock.toggleViewAction())
        self.toolbar_menu = view.addMenu(_tr("Toolbars"))
        self.toolbar_menu.setObjectName(TOOLBAR_MENU_NAME)
        for toolbar in (self.file_toolbar, self.map_toolbar, self.plugin_toolbar):
            self.toolbar_menu.addAction(toolbar.toggleViewAction())

        self.help_menu = bar.addMenu(_tr("&Help"))
        self.help_menu.setObjectName("mHelpMenu")
        self.help_menu.addAction(self.actions["about"])

    def _build_status_bar(self):
        status = self.statusBar()
        try:
            from qgis.gui import QgsTaskManagerStatusBarWidget
            status.addPermanentWidget(QgsTaskManagerStatusBarWidget(QgsApplication.taskManager(), status))
        except Exception:  # nosec B110 - a status bar without the task list still works
            pass
        self._coordinates = QLabel(status)
        self._coordinates.setMinimumWidth(190)
        self._scale = QLabel(status)
        self._scale.setMinimumWidth(110)
        self._crs_button = QToolButton(status)
        self._crs_button.setAutoRaise(True)
        self._crs_button.setToolTip(_tr("Coordinate reference system of the map"))
        self._crs_button.clicked.connect(self.choose_crs)
        for widget in (self._coordinates, self._scale, self._crs_button):
            status.addPermanentWidget(widget)
        self.canvas.xyCoordinates.connect(self._show_coordinates)
        self.canvas.scaleChanged.connect(self._show_scale)
        self.canvas.destinationCrsChanged.connect(self._show_crs)
        self._show_crs()

    def _connect_project(self):
        project = QgsProject.instance()
        project.layersAdded.connect(self._on_layers_added)
        project.layerTreeRegistryBridge().addedLayersToLayerTree.connect(self._select_added_layer)
        project.crsChanged.connect(self._on_project_crs)
        project.readProject.connect(self.canvas.readProject)
        project.writeProject.connect(self.canvas.writeProject)
        # Bound methods, never lambdas: the project outlives the window, and PyQt drops a connection to a method
        # of a widget once the widget is deleted. A lambda stays and runs on a deleted window while QGIS closes.
        project.isDirtyChanged.connect(self._update_title)
        project.fileNameChanged.connect(self._update_title)

    # --- the layer panel and the map ----------------------------------------------------------------------------

    def _on_current_layer(self, layer):
        self.canvas.setCurrentLayer(layer)

    def disconnect_project(self):
        """Drop every connection from the project to this window (the project lives on after it)."""
        project = QgsProject.instance()
        for signal, slot in ((project.layersAdded, self._on_layers_added), (project.crsChanged, self._on_project_crs),
                             (project.readProject, self.canvas.readProject),
                             (project.writeProject, self.canvas.writeProject),
                             (project.isDirtyChanged, self._update_title), (project.fileNameChanged, self._update_title),
                             (project.layerTreeRegistryBridge().addedLayersToLayerTree, self._select_added_layer),
                             (QgsApplication.messageLog().messageReceived, self._on_log_message)):
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):  # not connected, or already gone
                pass

    def _on_layers_added(self, layers):
        """The first layers of an empty project give it their CRS and the map its extent, as QGIS does."""
        project = QgsProject.instance()
        spatial = [layer for layer in layers if layer.isSpatial() and layer.crs().isValid()]
        if not spatial or self._reading_project:
            return
        first_ones = len(project.mapLayers()) == len(layers)
        if first_ones:
            natural = next((layer for layer in spatial if not _is_web_tiles(layer)), spatial[0])
            project.setCrs(natural.crs())
            self.canvas.setDestinationCrs(project.crs())
            # Not zoomToFullExtent: the map gets its layers from the layer panel a turn of the loop later.
            extent = None
            for layer in ([item for item in spatial if not _is_web_tiles(item)] or spatial):
                part = self._to_map(layer, layer.extent())
                if part is not None and not part.isEmpty():
                    if extent is None:
                        extent = part
                    else:
                        extent.combineExtentWith(part)
            if extent is not None:
                extent.scale(1.05)
                self.canvas.setExtent(extent)
            self.canvas.refresh()

    def _select_added_layer(self, layers):
        """The first of the layers just added becomes the current one, as in QGIS."""
        if layers and not self._reading_project:
            self.tree_view.setCurrentLayer(layers[0])

    def _on_project_crs(self):
        crs = QgsProject.instance().crs()
        if crs.isValid() and crs != self.canvas.mapSettings().destinationCrs():
            self.canvas.setDestinationCrs(crs)
            self.canvas.refresh()

    def current_vector_layer(self):
        layer = self.tree_view.currentLayer()
        return layer if isinstance(layer, QgsVectorLayer) else None

    def zoom_to_layer(self):
        layer = self.tree_view.currentLayer()
        if layer is None or not layer.isSpatial():
            return
        extent = self._to_map(layer, layer.extent())
        if extent is not None and not extent.isEmpty():
            extent.scale(1.05)
            self.canvas.setExtent(extent)
            self.canvas.refresh()

    def zoom_to_selection(self):
        layer = self.current_vector_layer()
        if layer is not None and layer.selectedFeatureCount():
            self.canvas.zoomToSelected(layer)

    def deselect_all(self):
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                layer.removeSelection()

    def _to_map(self, layer, rectangle):
        try:
            transform = QgsCoordinateTransform(layer.crs(), self.canvas.mapSettings().destinationCrs(),
                                               QgsProject.instance())
            return transform.transformBoundingBox(QgsRectangle(rectangle))
        except Exception:
            return None

    # --- projects -----------------------------------------------------------------------------------------------

    def _may_discard(self) -> bool:
        """True when the current project can be left: saved, or the user agrees to lose its changes."""
        project = QgsProject.instance()
        if not self.interactive or not project.isDirty() or not project.mapLayers():
            return True
        buttons = QMessageBox.StandardButton
        answer = QMessageBox.question(
            self, "FilterMate", _tr("Save the changes to the project?"),
            buttons.Save | buttons.Discard | buttons.Cancel, buttons.Save)
        if answer == buttons.Cancel:
            return False
        return self.save_project() if answer == buttons.Save else True

    def new_project(self, ask: bool = False) -> bool:
        if ask and not self._may_discard():
            return False
        self._close_tables()
        QgsProject.instance().clear()
        self.canvas.refresh()
        self._update_title()
        if self.interface is not None:
            self.interface.newProjectCreated.emit()
        return True

    def choose_project(self):
        if not self._may_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, _tr("Open a project"), self._last_folder(), PROJECT_FILTER)
        if path:
            self.open_project(path)

    def open_project(self, path: str) -> bool:
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isfile(path):
            self.message_bar.pushWarning("FilterMate", _tr("{0} does not exist.").format(path))
            return False
        self._close_tables()
        project = QgsProject.instance()
        self._reading_project = True
        try:
            done = project.read(path)
        finally:
            self._reading_project = False
        if not done:
            self.message_bar.pushCritical("FilterMate", _tr("The project could not be read: {0}").format(project.error()))
            return False
        self._remember_folder(path)
        if project.crs().isValid():
            self.canvas.setDestinationCrs(project.crs())
        self.canvas.refresh()
        self._update_title()
        if self.interface is not None:
            self.interface.projectRead.emit()
        return True

    def save_project(self, ask_path: bool = False) -> bool:
        project = QgsProject.instance()
        path = project.fileName()
        if ask_path or not path:
            path, _ = QFileDialog.getSaveFileName(self, _tr("Save the project"), self._last_folder(), PROJECT_FILTER)
            if not path:
                return False
            if not path.lower().endswith(PROJECT_SUFFIXES):
                path += ".qgz"
        if not project.write(path):
            self.message_bar.pushCritical("FilterMate", _tr("The project could not be saved: {0}").format(project.error()))
            return False
        self._remember_folder(path)
        self._update_title()
        return True

    def choose_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, _tr("Add files"), self._last_folder())
        if paths:
            self._remember_folder(paths[0])
            self.sources.open_paths(paths)

    def _last_folder(self) -> str:
        return str(QSettings().value("FilterMateStandalone/lastFolder", os.path.expanduser("~")) or "")

    def _remember_folder(self, path: str):
        QSettings().setValue("FilterMateStandalone/lastFolder", os.path.dirname(path))

    def _update_title(self, *_):
        project = QgsProject.instance()
        name = project.title() or os.path.basename(project.fileName() or "")
        mark = "*" if project.isDirty() and project.mapLayers() else ""
        self.setWindowTitle(f"{mark}{name} - FilterMate" if name else "FilterMate")

    def choose_crs(self):
        dialog = QgsProjectionSelectionDialog(self)
        dialog.setCrs(QgsProject.instance().crs())
        if dialog.exec():
            crs = dialog.crs()
            if crs.isValid():
                QgsProject.instance().setCrs(crs)

    # --- what the interface asks for ----------------------------------------------------------------------------

    def add_panel(self, area, dock):
        """A dock of a plugin, where QGIS would put it: in the window, and in View > Panels."""
        self.addDockWidget(area, dock)
        action = dock.toggleViewAction()
        if action not in self.panel_menu.actions():
            self.panel_menu.addAction(action)
        dock.show()

    def remove_panel(self, dock):
        self.removeDockWidget(dock)
        self.panel_menu.removeAction(dock.toggleViewAction())

    def add_toolbar(self, name_or_toolbar, area=Qt.ToolBarArea.TopToolBarArea):
        if isinstance(name_or_toolbar, QToolBar):
            toolbar = name_or_toolbar
        else:
            toolbar = QToolBar(str(name_or_toolbar), self)
            toolbar.setObjectName(str(name_or_toolbar))
        self.addToolBar(area, toolbar)
        self.toolbar_menu.addAction(toolbar.toggleViewAction())
        return toolbar

    @property
    def plugins_root_menu(self):
        if self._plugins_root_menu is None:
            self._plugins_root_menu = QMenu(_tr("P&lugins"), self)
            self._plugins_root_menu.setObjectName("mPluginMenu")
            self.menuBar().insertMenu(self.help_menu.menuAction(), self._plugins_root_menu)
        return self._plugins_root_menu

    def plugin_menu(self, name: str):
        """The menu of one plugin, at the top level of the window (QGIS nests it under Vector, Raster...)."""
        if name not in self._plugin_menus:
            menu = QMenu(name, self)
            self.menuBar().insertMenu(self.help_menu.menuAction(), menu)
            self._plugin_menus[name] = menu
        return self._plugin_menus[name]

    def remove_plugin_action(self, name: str, action):
        menu = self._plugin_menus.get(name)
        if menu is None:
            return
        menu.removeAction(action)
        if not menu.actions():
            self.menuBar().removeAction(menu.menuAction())
            self._plugin_menus.pop(name).deleteLater()

    def show_attribute_table(self, layer=None):
        layer = layer or self.current_vector_layer()
        if not isinstance(layer, QgsVectorLayer):
            self.message_bar.pushInfo("FilterMate", _tr("Choose a vector layer in the layer panel first."))
            return None
        dialog = AttributeTableDialog(layer, self.canvas, self)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._tables.append(dialog)
        dialog.destroyed.connect(lambda *_, d=dialog: self._tables.remove(d) if d in self._tables else None)
        dialog.show()
        return dialog

    def _close_tables(self):
        for dialog in list(self._tables):
            try:
                dialog.close()
            except RuntimeError:  # already deleted
                pass
        self._tables = []

    def open_feature_form(self, layer, feature, modal: bool = True) -> bool:
        try:
            dialog = QgsAttributeDialog(layer, feature, False, self, True, QgsAttributeEditorContext())
        except Exception as error:
            self.message_bar.pushWarning("FilterMate", str(error))
            return False
        if modal and self.interactive:
            return bool(dialog.exec())
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.show()
        return True

    def show_layer_properties(self):
        layer = self.tree_view.currentLayer()
        if layer is None:
            return
        try:
            if isinstance(layer, QgsVectorLayer):
                from qgis.gui import QgsVectorLayerProperties
                dialog = QgsVectorLayerProperties(self.canvas, self.message_bar, layer, self)
            elif isinstance(layer, QgsRasterLayer):
                from qgis.gui import QgsRasterLayerProperties
                dialog = QgsRasterLayerProperties(layer, self.canvas, self)
            else:
                self.message_bar.pushInfo("FilterMate", _tr("This kind of layer has no properties window here."))
                return
            dialog.exec()
        except Exception as error:
            self.message_bar.pushWarning("FilterMate", _tr("The properties could not be opened: {0}").format(error))

    def show_log(self):
        self.log_dock.show()
        self.log_dock.raise_()

    def _toggle_browser(self, shown: bool):
        if self._browser_dock is None:
            if not shown:
                return
            try:
                from qgis.gui import QgsBrowserDockWidget, QgsBrowserGuiModel
                self.browser_model = QgsBrowserGuiModel(self)
                self._browser_dock = QgsBrowserDockWidget(_tr("Browser"), self.browser_model, self)
                self._browser_dock.setObjectName("Browser")
                if hasattr(self._browser_dock, "setMapCanvas"):
                    self._browser_dock.setMapCanvas(self.canvas)
                self._browser_dock.setMessageBar(self.message_bar)
                self._browser_dock.handleDropUriList.connect(self.sources.open_uris)
                self._browser_dock.openFile.connect(lambda path, *_: self.sources.open_paths([path]))
                self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._browser_dock)
                self.tabifyDockWidget(self.layers_dock, self._browser_dock)
                self._browser_dock.visibilityChanged.connect(self._browser_action.setChecked)
            except Exception as error:
                self._browser_dock = None
                self._browser_action.setChecked(False)
                self.message_bar.pushWarning("FilterMate", _tr("The browser could not be opened: {0}").format(error))
                return
        self._browser_dock.setVisible(shown)
        if shown:
            self._browser_dock.raise_()

    def show_about(self):
        from qgis.PyQt.QtCore import QT_VERSION_STR
        QMessageBox.about(self, _tr("About FilterMate"), (
            "<b>FilterMate {0}</b><br>{1}<br><br>QGIS {2} &middot; Qt {3}<br>{4}<br><br>"
            "<a href='https://github.com/imagodata/filter_mate'>github.com/imagodata/filter_mate</a>").format(
                filtermate_version(), _tr("Standalone application: the FilterMate dock on the QGIS libraries."),
                Qgis.QGIS_VERSION, QT_VERSION_STR, QgsApplication.prefixPath()))

    # --- status bar ---------------------------------------------------------------------------------------------

    def _show_coordinates(self, point):
        geographic = self.canvas.mapSettings().destinationCrs().isGeographic()
        digits = 6 if geographic else 2
        self._coordinates.setText(f"{point.x():.{digits}f}  {point.y():.{digits}f}")

    def _show_scale(self, scale):
        self._scale.setText(f"1:{int(round(scale)):,}".replace(",", " ") if scale and scale > 0 else "")

    def _show_crs(self, *_):
        crs = self.canvas.mapSettings().destinationCrs()
        self._crs_button.setText((crs.authid() or crs.description() or "?") if crs.isValid() else _tr("No CRS"))

    # --- window state, drops, closing ---------------------------------------------------------------------------

    def restore_window(self):
        """Give the window the size and the dock places of the last session (before a plugin adds its docks)."""
        settings = QSettings()
        geometry, state = settings.value(GEOMETRY_KEY), settings.value(STATE_KEY)
        if geometry is not None:
            self.restoreGeometry(geometry)
        if state is not None:
            self.restoreState(state)

    def save_window(self):
        settings = QSettings()
        settings.setValue(GEOMETRY_KEY, self.saveGeometry())
        settings.setValue(STATE_KEY, self.saveState())

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls() or mime.hasFormat("application/x-vnd.qgis.qgis.uri"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        mime = event.mimeData()
        # After the drop returns: opening a layer may show a dialog, which must not run inside the drag.
        if mime.hasFormat("application/x-vnd.qgis.qgis.uri"):
            from qgis.core import QgsMimeDataUtils
            uris = QgsMimeDataUtils.decodeUriList(mime)
            QTimer.singleShot(0, lambda: self.sources.open_uris(uris))
        else:
            paths = [url.toLocalFile() for url in mime.urls() if url.isLocalFile()]
            QTimer.singleShot(0, lambda: self.sources.open_paths(paths))
        event.acceptProposedAction()

    closing = None  # set by the application: called once the user agreed to close, before the window goes

    def closeEvent(self, event):
        if not self._may_discard():
            event.ignore()
            return
        self.save_window()
        self._close_tables()
        if callable(self.closing):
            self.closing()
        self.disconnect_project()
        super().closeEvent(event)


def _is_web_tiles(layer) -> bool:
    """A basemap in web mercator: not the layer whose CRS a new project should take."""
    return isinstance(layer, QgsRasterLayer) and layer.providerType() in ("wms", "xyz")
