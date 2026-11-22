# -*- coding: utf-8 -*-
"""Getting data into the standalone window: files, the source screens of QGIS, the browser, drops.

The QGIS application owns the "Data Source Manager" dialog; the libraries only give its
screens, one per provider (``QgsGui.sourceSelectProviderRegistry()``). ``AddLayerDialog`` puts
them back together, so PostGIS, WFS, delimited text and the others open as they do in QGIS.
"""

import os
import time

from qgis.core import (
    QgsDataSourceUri,
    QgsMimeDataUtils,
    QgsPointCloudLayer,
    QgsProject,
    QgsProviderRegistry,
    QgsRasterLayer,
    QgsVectorLayer,
)
from qgis.gui import QgsGui
from qgis.PyQt.QtCore import QObject, QSize, Qt
from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QVBoxLayout,
)

from .compat import enum_member, layer_type
from .qt import _tr

PROJECT_SUFFIXES = (".qgs", ".qgz")
OSM_URI = "type=xyz&url=https://tile.openstreetmap.org/%7Bz%7D/%7Bx%7D/%7By%7D.png&zmax=19&zmin=0"
DATABASE_PROVIDERS = ("postgres", "spatialite", "mssql", "oracle", "hana", "postgresraster")
# Above this many tables in one file, the user chooses instead of getting them all.
ASK_ABOVE = 8


def _layer_from_kind(kind: str, uri: str, name: str, provider: str):
    """A layer of ``kind`` (``vector``, ``raster``, ``pointcloud``, ``mesh``, ``vectortile``, ``tiledscene``)."""
    if kind == "vector":
        return QgsVectorLayer(uri, name, provider or "ogr")
    if kind == "raster":
        return QgsRasterLayer(uri, name, provider or "gdal")
    if kind == "pointcloud":
        return QgsPointCloudLayer(uri, name, provider)
    if kind == "mesh":
        from qgis.core import QgsMeshLayer
        return QgsMeshLayer(uri, name, provider or "mdal")
    if kind == "vectortile":
        from qgis.core import QgsVectorTileLayer
        return QgsVectorTileLayer(uri, name)
    if kind == "tiledscene":
        from qgis.core import QgsTiledSceneLayer
        return QgsTiledSceneLayer(uri, name, provider)
    return None


def _kind_of_type(value) -> str:
    """The ``kind`` of a ``Qgis.LayerType`` value (the ``addLayer`` signal of QGIS 3.34 and later)."""
    for kind, name in (("vector", "Vector"), ("raster", "Raster"), ("pointcloud", "PointCloud"), ("mesh", "Mesh"),
                       ("vectortile", "VectorTile"), ("tiledscene", "TiledScene")):
        if layer_type(name) is not None and value == layer_type(name):
            return kind
    return ""


class Sources(QObject):
    """Adds layers to the project for the window, whatever they come from."""

    def __init__(self, window):
        super().__init__(window)
        self._window = window
        self._dialog = None
        self._recent = {}
        self.interactive = True

    # --- one layer ----------------------------------------------------------------------------------------------

    def add_layer(self, kind: str, uri: str, name: str = "", provider: str = ""):
        """Add one layer and return it, None (and a warning in the message bar) when it does not open."""
        name = name or os.path.splitext(os.path.basename(uri.split("|")[0]))[0] or kind
        try:
            layer = _layer_from_kind(kind, uri, name, provider)
        except Exception as error:
            self._warn(_tr("{0} could not be opened: {1}").format(name, error))
            return None
        return self._adopt(layer, name)

    @staticmethod
    def _key(uri: str, provider: str) -> str:
        """One spelling per layer: a database URI written twice may differ in the order of its keys."""
        if provider in DATABASE_PROVIDERS:
            try:
                return provider + ":" + QgsDataSourceUri(uri).uri(False)
            except Exception:  # nosec B110 - compared as written
                pass
        return provider + ":" + uri

    def _first_announcement(self, key: str) -> bool:
        """False when a source screen announces again the layer it announced an instant ago.

        From QGIS 3.34 a screen emits ``addLayer`` and keeps emitting the older signal of its kind: both are
        connected, so that every version and every screen adds its layers, and the second one is dropped here.
        The instant counts from the end of the first add, which can take seconds (a WFS, a PostGIS table).
        """
        now = time.monotonic()
        self._recent = {known: at for known, at in self._recent.items() if now - at < 1.0}
        return key not in self._recent

    def _done(self, key: str):
        self._recent[key] = time.monotonic()

    def _announced(self, kind: str, uri: str, name: str = "", provider: str = ""):
        key = self._key(uri, provider)
        if kind and self._first_announcement(key):
            self._recent[key] = time.monotonic()
            try:
                self.add_layer(kind, uri, name, provider)
            finally:
                self._done(key)

    def _announced_sources(self, uris, provider: str, encoding: str = ""):
        for uri in uris:
            key = self._key(uri, provider)
            if self._first_announcement(key):
                self._recent[key] = time.monotonic()
                try:
                    self.open_source(uri, provider, encoding)
                finally:
                    self._done(key)

    def _adopt(self, layer, name: str):
        if layer is None or not layer.isValid():
            self._warn(_tr("{0} could not be opened.").format(name))
            return None
        QgsProject.instance().addMapLayer(layer)
        return layer

    def _warn(self, text: str):
        self._window.message_bar.pushWarning("FilterMate", text)

    # --- files --------------------------------------------------------------------------------------------------

    def open_paths(self, paths) -> int:
        """Open projects and data files; returns how many layers were added."""
        added = 0
        for path in paths:
            if not path:
                continue
            if path.lower().endswith(PROJECT_SUFFIXES):
                self._window.open_project(path)
                continue
            added += len(self.open_source(path))
        return added

    def open_source(self, uri: str, provider: str = "", encoding: str = ""):
        """Every layer a file or a URI holds (the tables of a GeoPackage, the bands file of a raster...)."""
        try:
            registry = QgsProviderRegistry.instance()
            details = registry.querySublayers(uri) if not provider else \
                [d for d in registry.querySublayers(uri) if d.providerKey() == provider] or registry.querySublayers(uri)
        except Exception:
            details = []
        if not details:
            # Not a file the providers recognise by its content: try it as a vector, then as a raster.
            name = os.path.splitext(os.path.basename(uri))[0]
            for kind in ("vector", "raster"):
                layer = _layer_from_kind(kind, uri, name, provider if kind == "vector" else "")
                if layer is not None and layer.isValid():
                    QgsProject.instance().addMapLayer(layer)
                    return [layer]
            self._warn(_tr("{0} could not be opened.").format(os.path.basename(uri) or uri))
            return []
        if len(details) > ASK_ABOVE and self.interactive:
            details = _choose_sublayers(self._window, os.path.basename(uri), details)
            if not details:  # the choice was cancelled, or nothing ticked
                return []
        from qgis.core import QgsProviderSublayerDetails
        options = QgsProviderSublayerDetails.LayerOptions(QgsProject.instance().transformContext())
        layers = []
        for detail in details:
            try:
                layer = detail.toLayer(options)
            except Exception:
                layer = None
            if layer is not None and layer.isValid():
                if encoding and isinstance(layer, QgsVectorLayer):  # the encoding chosen in the source screen
                    layer.setProviderEncoding(encoding)
                layers.append(layer)
        if layers:
            QgsProject.instance().addMapLayers(layers)
        else:
            self._warn(_tr("{0} could not be opened.").format(os.path.basename(uri) or uri))
        return layers

    def add_database_layers(self, uris, provider: str):
        for text in uris:
            uri = QgsDataSourceUri(text)
            self._announced("vector", uri.uri(False), uri.table() or provider, provider)

    def add_basemap(self):
        """OpenStreetMap under the layers, for a map that is not a blank page."""
        for layer in QgsProject.instance().mapLayers().values():
            if layer.providerType() == "wms" and "tile.openstreetmap.org" in layer.source():
                return layer
        layer = QgsRasterLayer(OSM_URI, "OpenStreetMap", "wms")
        if not layer.isValid():
            self._warn(_tr("The OpenStreetMap tiles could not be reached."))
            return None
        QgsProject.instance().addMapLayer(layer, False)
        QgsProject.instance().layerTreeRoot().addLayer(layer)  # at the bottom of the panel
        return layer

    # --- drops and the browser ----------------------------------------------------------------------------------

    def open_uris(self, uris) -> int:
        """Layers dragged from the browser panel (``QgsMimeDataUtils.Uri``)."""
        added = 0
        for uri in uris:
            kind = {"vector": "vector", "raster": "raster", "pointcloud": "pointcloud", "mesh": "mesh",
                    "vector-tile": "vectortile", "tiled-scene": "tiledscene"}.get(uri.layerType, "")
            if uri.layerType == "project":
                self._window.open_project(uri.uri)
            elif kind:
                added += 1 if self.add_layer(kind, uri.uri, uri.name, uri.providerKey) is not None else 0
            else:
                added += len(self.open_source(uri.uri))
        return added

    def open_mime(self, mime) -> bool:
        """What was dropped on the window. True when it was data."""
        if QgsMimeDataUtils.isUriList(mime):
            self.open_uris(QgsMimeDataUtils.decodeUriList(mime))
            return True
        paths = [url.toLocalFile() for url in mime.urls() if url.isLocalFile()]
        if paths:
            self.open_paths(paths)
            return True
        return False

    # --- the source screens of QGIS -----------------------------------------------------------------------------

    def show_dialog(self):
        if self._dialog is None:
            self._dialog = AddLayerDialog(self._window, self)
        self._dialog.show()
        self._dialog.raise_()
        self._dialog.activateWindow()
        return self._dialog

    def reload_connections(self):
        if self._dialog is not None:
            self._dialog.refresh()
        model = getattr(self._window, "browser_model", None)
        if model is not None:
            try:
                model.refresh()
            except Exception:  # nosec B110 - a model not initialized yet has nothing to refresh
                pass

    def connect_source_widget(self, widget):
        """Wire the "add" signals of one source screen to this object."""
        connections = (
            ("addLayer", lambda kind, uri, name, provider: self._announced(_kind_of_type(kind), uri, name, provider)),
            ("addVectorLayer", lambda uri, name, provider="ogr": self._announced("vector", uri, name, provider)),
            ("addRasterLayer", lambda uri, name, provider="gdal": self._announced("raster", uri, name, provider)),
            ("addMeshLayer", lambda uri, name, provider="mdal": self._announced("mesh", uri, name, provider)),
            ("addVectorTileLayer", lambda uri, name: self._announced("vectortile", uri, name, "")),
            ("addPointCloudLayer", lambda uri, name, provider: self._announced("pointcloud", uri, name, provider)),
            ("addVectorLayers", lambda uris, encoding="", _kind="": self._announced_sources(uris, "ogr", encoding)),
            ("addRasterLayers", lambda uris: self._announced_sources(uris, "gdal")),
            ("addDatabaseLayers", self.add_database_layers),
            ("connectionsChanged", self.reload_connections),
        )
        for name, slot in connections:
            signal = getattr(widget, name, None)
            if signal is not None and hasattr(signal, "connect"):
                try:
                    signal.connect(slot)
                except TypeError:  # an overloaded signal PyQt cannot match to the slot: the others still add layers
                    pass
        if hasattr(widget, "pushMessage"):
            try:
                widget.pushMessage.connect(lambda title, text, level: self._window.message_bar.pushMessage(title, text, level))
            except TypeError:
                pass


class AddLayerDialog(QDialog):
    """The source screens of QGIS, one per provider, in one window."""

    def __init__(self, window, sources: Sources):
        super().__init__(window)
        self.setObjectName("FilterMateAddLayerDialog")
        self.setWindowTitle(_tr("Add layers"))
        self.resize(980, 640)
        self._window, self._sources, self._widgets = window, sources, {}
        self._list = QListWidget(self)
        self._list.setIconSize(QSize(22, 22))
        self._list.setFixedWidth(210)
        self._stack = QStackedWidget(self)
        self._providers = sorted(QgsGui.sourceSelectProviderRegistry().providers(), key=lambda p: p.ordering())
        for provider in self._providers:
            item = QListWidgetItem(provider.icon(), provider.text().replace("&", ""))
            item.setToolTip(provider.toolTip() or provider.text())
            self._list.addItem(item)
            self._stack.addWidget(QLabel("", self))  # replaced by the real screen when first shown: some are slow
        row = QHBoxLayout()
        row.addWidget(self._list)
        row.addWidget(self._stack, 1)
        layout = QVBoxLayout(self)
        layout.addLayout(row)
        self._list.currentRowChanged.connect(self._show)
        if self._providers:
            self._list.setCurrentRow(0)

    def _show(self, row: int):
        if row < 0 or row >= len(self._providers):
            return
        if row not in self._widgets:
            self._widgets[row] = self._create(row)
            old = self._stack.widget(row)
            self._stack.removeWidget(old)
            old.deleteLater()
            self._stack.insertWidget(row, self._widgets[row])
        self._stack.setCurrentIndex(row)

    def _create(self, row: int):
        provider = self._providers[row]
        try:
            embedded = enum_member(QgsProviderRegistry, "WidgetMode", "Embedded")
            widget = provider.createDataSourceWidget(self, Qt.WindowType.Widget, embedded)
        except Exception as error:
            return QLabel(_tr("This source is not available here: {0}").format(error), self)
        if widget is None:
            return QLabel(_tr("This source is not available here."), self)
        for setter, value in (("setMapCanvas", self._window.canvas),
                              ("setBrowserModel", getattr(self._window, "browser_model", None))):
            if value is not None and hasattr(widget, setter):
                try:
                    getattr(widget, setter)(value)
                except Exception:  # nosec B110 - the screen works without the canvas or the browser model
                    pass
        self._sources.connect_source_widget(widget)
        for name, slot in (("accepted", self.accept), ("rejected", self.reject)):
            signal = getattr(widget, name, None)
            if signal is not None:
                signal.connect(slot)
        return widget

    def refresh(self):
        for widget in self._widgets.values():
            if hasattr(widget, "refresh"):
                try:
                    widget.refresh()
                except Exception:  # nosec B110 - one screen that cannot refresh does not stop the others
                    pass


def _choose_sublayers(parent, title: str, details):
    """Let the user tick the tables of a file that has many. Cancel means none."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(_tr("Layers of {0}").format(title))
    dialog.resize(420, 480)
    chooser = QListWidget(dialog)
    for detail in details:
        item = QListWidgetItem(detail.name())
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked)
        chooser.addItem(item)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, dialog)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout = QVBoxLayout(dialog)
    layout.addWidget(chooser)
    layout.addWidget(buttons)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return []
    return [detail for index, detail in enumerate(details)
            if chooser.item(index).checkState() == Qt.CheckState.Checked]


__all__ = ["Sources", "AddLayerDialog", "PROJECT_SUFFIXES"]
