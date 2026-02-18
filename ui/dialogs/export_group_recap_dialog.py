"""
Export Group Recap Dialog.

Shown before GPKG or KML export. Displays the layer group structure
and lets the user choose whether to preserve it in the exported file.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from qgis.PyQt.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
        QPushButton, QTreeWidget, QTreeWidgetItem, QWidget,
    )
    from qgis.PyQt.QtCore import Qt, QCoreApplication
    from qgis.PyQt.QtGui import QFont, QIcon
    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False


# Format-specific UI text
_FORMAT_TEXT = {
    'GPKG': {
        'title': "Export GeoPackage",
        'header': "Export GeoPackage",
        'checkbox': "Conserver la structure des groupes dans le GPKG",
        'tooltip': (
            "Embarque un projet QGIS dans le GeoPackage qui restaure "
            "l'arborescence des groupes à l'ouverture"
        ),
    },
    'KML': {
        'title': "Export KML",
        'header': "Export KML",
        'checkbox': "Regrouper les couches dans un seul fichier KML avec dossiers",
        'tooltip': (
            "Fusionne toutes les couches dans un seul fichier KML "
            "avec des dossiers (<Folder>) correspondant aux groupes"
        ),
    },
}


class ExportGroupRecapDialog(QDialog):
    """Pre-export dialog showing group structure and preserve option."""

    def __init__(
        self,
        hierarchy: dict,
        layer_count: int,
        output_path: str,
        export_format: str = 'GPKG',
        preserve_default: bool = False,
        parent: Optional['QWidget'] = None,
    ):
        """Initialize the dialog.

        Args:
            hierarchy: Output from get_layer_group_hierarchy().
            layer_count: Total number of layers to export.
            output_path: Destination path.
            export_format: Export format key ('GPKG', 'KML').
            preserve_default: Default state of the preserve checkbox (from config).
            parent: Parent widget.
        """
        super().__init__(parent)
        self._hierarchy = hierarchy
        self._layer_count = layer_count
        self._output_path = output_path
        self._export_format = export_format.upper()
        self._preserve_default = preserve_default

        texts = _FORMAT_TEXT.get(self._export_format, _FORMAT_TEXT['GPKG'])
        self._texts = texts

        self.setWindowTitle(self.tr(texts['title']))
        self.setMinimumWidth(450)
        self.setMinimumHeight(300)
        self.setModal(True)

        self._preserve_cb = None
        self._setup_ui()

    def tr(self, message):
        return QCoreApplication.translate("ExportGroupRecapDialog", message)

    def preserve_groups(self) -> bool:
        """Return whether the user chose to preserve groups."""
        if self._preserve_cb:
            return self._preserve_cb.isChecked()
        return False

    def _setup_ui(self):
        """Build the dialog layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        header = QLabel(self.tr(self._texts['header']))
        header_font = QFont()
        header_font.setPointSize(12)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)

        # Summary
        groups = self._hierarchy.get("groups", [])
        ungrouped = self._hierarchy.get("ungrouped", [])
        group_count = self._count_groups(self._hierarchy)
        has_groups = group_count > 0

        summary_text = self.tr("{0} couche(s)").format(self._layer_count)
        if has_groups:
            summary_text += self.tr(" dans {0} groupe(s)").format(group_count)
        if ungrouped:
            summary_text += self.tr(" + {0} hors groupe").format(len(ungrouped))

        summary = QLabel(summary_text)
        summary.setStyleSheet("color: #666; margin-bottom: 4px;")
        layout.addWidget(summary)

        # Output path
        path_label = QLabel(self.tr("Destination : {0}").format(self._output_path))
        path_label.setWordWrap(True)
        path_label.setStyleSheet("color: #888; font-size: 9pt;")
        layout.addWidget(path_label)

        # Tree widget showing the hierarchy
        if has_groups or ungrouped:
            self._tree = QTreeWidget()
            self._tree.setHeaderHidden(True)
            self._tree.setIndentation(20)
            self._populate_tree()
            self._tree.expandAll()
            layout.addWidget(self._tree)

        # Preserve groups checkbox
        self._preserve_cb = QCheckBox(self.tr(self._texts['checkbox']))
        self._preserve_cb.setToolTip(self.tr(self._texts['tooltip']))
        self._preserve_cb.setChecked(self._preserve_default and has_groups)
        self._preserve_cb.setEnabled(has_groups)
        if not has_groups:
            self._preserve_cb.setToolTip(
                self.tr("Aucun groupe détecté - toutes les couches sont à la racine")
            )
        layout.addWidget(self._preserve_cb)

        # Buttons
        button_layout = QHBoxLayout()

        cancel_btn = QPushButton(self.tr("Annuler"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        button_layout.addStretch()

        export_btn = QPushButton(self.tr("Exporter"))
        export_btn.setDefault(True)
        export_btn.setStyleSheet(
            "QPushButton { background: #27ae60; color: white; padding: 8px 16px; "
            "border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #219a52; }"
        )
        export_btn.clicked.connect(self.accept)
        button_layout.addWidget(export_btn)

        layout.addLayout(button_layout)

    def _populate_tree(self):
        """Populate the QTreeWidget from the hierarchy dict."""
        try:
            from qgis.core import QgsProject
            project = QgsProject.instance()
        except ImportError:
            project = None

        # Add groups
        for group in self._hierarchy.get("groups", []):
            self._add_group_to_tree(group, self._tree, project)

        # Add ungrouped layers at root
        for lid in self._hierarchy.get("ungrouped", []):
            name = self._resolve_name(lid, project)
            item = QTreeWidgetItem(self._tree, [name])
            item.setIcon(0, self._layer_icon())

    def _add_group_to_tree(self, group: dict, parent, project):
        """Recursively add a group and its contents to the tree."""
        group_item = QTreeWidgetItem(parent, [group["name"]])
        group_item.setIcon(0, self._folder_icon())

        # Layers in this group
        for lid in group.get("layers", []):
            name = self._resolve_name(lid, project)
            layer_item = QTreeWidgetItem(group_item, [name])
            layer_item.setIcon(0, self._layer_icon())

        # Sub-groups
        for sub in group.get("groups", []):
            self._add_group_to_tree(sub, group_item, project)

    def _resolve_name(self, layer_id: str, project) -> str:
        """Resolve layer ID to display name."""
        if project:
            layer = project.mapLayer(layer_id)
            if layer:
                return layer.name()
        return layer_id

    def _folder_icon(self) -> 'QIcon':
        """Return a folder icon."""
        try:
            from qgis.PyQt.QtWidgets import QApplication
            return QApplication.style().standardIcon(
                QApplication.style().SP_DirIcon
            )
        except Exception:
            return QIcon()

    def _layer_icon(self) -> 'QIcon':
        """Return a layer/file icon."""
        try:
            from qgis.PyQt.QtWidgets import QApplication
            return QApplication.style().standardIcon(
                QApplication.style().SP_FileIcon
            )
        except Exception:
            return QIcon()

    def _count_groups(self, hierarchy: dict) -> int:
        """Count total groups recursively."""
        count = len(hierarchy.get("groups", []))
        for group in hierarchy.get("groups", []):
            if group.get("groups"):
                count += self._count_groups({"groups": group["groups"]})
        return count
