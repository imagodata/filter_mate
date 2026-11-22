# -*- coding: utf-8 -*-
"""The attribute table of a layer, to see what a filter kept (``QgsDualView`` of the libraries)."""

from qgis.core import QgsFeatureRequest, QgsVectorLayer
from qgis.gui import QgsAttributeEditorContext, QgsDualView
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import QDialog, QLabel, QVBoxLayout

from .compat import enum_member
from .qt import _tr


class AttributeTableDialog(QDialog):
    """A table that follows the layer: its filter, its selection, its edits."""

    def __init__(self, layer: QgsVectorLayer, canvas, parent=None):
        super().__init__(parent)
        self.setObjectName("FilterMateAttributeTable")
        self._layer, self._canvas = layer, canvas
        self.resize(900, 480)
        self._view = QgsDualView(self)
        self._count = QLabel(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self._view, 1)
        layout.addWidget(self._count)
        self._reload = QTimer(self)
        self._reload.setSingleShot(True)
        self._reload.setInterval(150)
        self._reload.timeout.connect(self._load)
        layer.subsetStringChanged.connect(self._reload.start)
        layer.willBeDeleted.connect(self.close)
        layer.selectionChanged.connect(self._title)
        self._load()

    def _load(self):
        if self._layer is None:
            return
        self._view.init(self._layer, self._canvas, QgsFeatureRequest(), QgsAttributeEditorContext())
        self._view.setView(enum_member(QgsDualView, "ViewMode", "AttributeTable"))
        self._title()

    def _title(self, *_):
        layer = self._layer
        if layer is None:
            return
        self.setWindowTitle(_tr("{0}: attributes").format(layer.name()))
        total = layer.featureCount()
        text = _tr("{0} features").format(total) if total >= 0 else ""
        if layer.selectedFeatureCount():
            text += _tr(", {0} selected").format(layer.selectedFeatureCount())
        if layer.subsetString():
            text += _tr(" (filtered)")
        self._count.setText(text)

    def closeEvent(self, event):
        self._layer = None
        super().closeEvent(event)
