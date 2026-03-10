# -*- coding: utf-8 -*-
"""
QFieldCloud Push Dialog for FilterMate.

Allows users to export current filtered layers to QFieldCloud.
Shows active filter info, project naming, layer action modes,
and upload progress.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from qgis.core import QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QThread, Qt, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from ..extension import QFieldCloudExtension

logger = logging.getLogger('FilterMate.Extensions.QFieldCloud.UI.Push')

# QFieldSync action modes for combo boxes
ACTION_MODES = ["offline", "copy", "no_action"]


class PushWorker(QThread):
    """Background thread for push operation."""

    progress = pyqtSignal(int, str)
    finished = pyqtSignal(object)  # QFieldCloudPushResult
    error = pyqtSignal(str)

    def __init__(self, service, push_kwargs: dict):
        super().__init__()
        self._service = service
        self._push_kwargs = push_kwargs

    def run(self):
        try:
            result = self._service.push_project(
                progress_callback=self._on_progress,
                **self._push_kwargs,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    def _on_progress(self, percent: int, message: str):
        self.progress.emit(percent, message)


class QFieldCloudPushDialog(QDialog):
    """
    Dialog for exporting filtered layers to QFieldCloud.

    Shows:
        - Current filter summary
        - Project naming
        - Create new / update existing project
        - Layer action mode overrides
        - Progress bar during upload
    """

    def __init__(
        self,
        parent=None,
        extension: 'QFieldCloudExtension' = None,
        iface=None,
    ):
        super().__init__(parent, Qt.WindowType.Dialog)
        self._extension = extension
        self._iface = iface
        self._worker: Optional[PushWorker] = None

        self.setWindowTitle("Export to QFieldCloud")
        self.setMinimumWidth(500)
        self.setMinimumHeight(500)
        self.setModal(True)

        self._init_ui()
        self._populate_filter_info()
        self._populate_projects()
        self._connect_signals()

    def _init_ui(self):
        """Build the dialog UI."""
        layout = QVBoxLayout()

        # --- Filter info ---
        info_group = QGroupBox("Active Filter")
        info_layout = QFormLayout()

        self._filter_label = QLabel("No active filter")
        info_layout.addRow("Filter:", self._filter_label)

        self._layers_label = QLabel("0 layers")
        info_layout.addRow("Layers:", self._layers_label)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # --- Project settings ---
        project_group = QGroupBox("QFieldCloud Project")
        project_layout = QFormLayout()

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("WYRE-POP_001")
        project_layout.addRow("Project name:", self._name_edit)

        self._desc_edit = QLineEdit()
        self._desc_edit.setPlaceholderText("WYRE FTTH - Zone POP 001")
        project_layout.addRow("Description:", self._desc_edit)

        # Create new vs update existing
        mode_layout = QHBoxLayout()
        self._radio_new = QRadioButton("Create new")
        self._radio_update = QRadioButton("Update existing:")
        self._radio_new.setChecked(True)
        mode_layout.addWidget(self._radio_new)
        mode_layout.addWidget(self._radio_update)
        project_layout.addRow("Mode:", mode_layout)

        self._existing_combo = QComboBox()
        self._existing_combo.setEnabled(False)
        project_layout.addRow("", self._existing_combo)

        project_group.setLayout(project_layout)
        layout.addWidget(project_group)

        # --- Layer actions table ---
        layers_group = QGroupBox("Layer Modes")
        layers_layout = QVBoxLayout()

        self._layers_table = QTableWidget()
        self._layers_table.setColumnCount(2)
        self._layers_table.setHorizontalHeaderLabels(["Layer", "Mode"])
        self._layers_table.horizontalHeader().setStretchLastSection(True)
        self._layers_table.setMaximumHeight(200)
        layers_layout.addWidget(self._layers_table)

        layers_group.setLayout(layers_layout)
        layout.addWidget(layers_group)

        # --- Progress ---
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        self._progress_label = QLabel("")
        self._progress_label.setVisible(False)
        layout.addWidget(self._progress_label)

        # --- Buttons ---
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
        )
        self._export_btn = self._button_box.addButton(
            "Export", QDialogButtonBox.ButtonRole.AcceptRole
        )
        layout.addWidget(self._button_box)

        self.setLayout(layout)

    def _populate_filter_info(self):
        """Show info about the current active filter and layers."""
        project = QgsProject.instance()
        layers = project.mapLayers().values()

        filtered_layers = []
        for layer in layers:
            if isinstance(layer, QgsVectorLayer) and layer.subsetString():
                filtered_layers.append(layer)

        if filtered_layers:
            # Show first filter expression as summary
            first_filter = filtered_layers[0].subsetString()
            if len(first_filter) > 60:
                first_filter = first_filter[:57] + "..."
            self._filter_label.setText(first_filter)

            total_features = sum(l.featureCount() for l in filtered_layers)
            self._layers_label.setText(
                f"{len(filtered_layers)} layers ({total_features} features)"
            )
        else:
            # Show all vector layers if no filter active
            all_vector = [
                l for l in layers if isinstance(l, QgsVectorLayer)
            ]
            self._layers_label.setText(
                f"{len(all_vector)} layers (no filter active)"
            )

        # Populate layer actions table
        vector_layers = [
            l for l in layers if isinstance(l, QgsVectorLayer) and l.isValid()
        ]
        self._layers_table.setRowCount(len(vector_layers))

        from ..project_builder import WYRE_LAYER_ACTIONS

        for i, layer in enumerate(vector_layers):
            name = layer.name()

            # Layer name cell
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._layers_table.setItem(i, 0, name_item)

            # Action mode combo
            combo = QComboBox()
            combo.addItems(ACTION_MODES)

            # Set default from WYRE mapping or "copy"
            default_action = WYRE_LAYER_ACTIONS.get(name, "copy")
            idx = ACTION_MODES.index(default_action) if default_action in ACTION_MODES else 1
            combo.setCurrentIndex(idx)

            self._layers_table.setCellWidget(i, 1, combo)

        self._layers_table.resizeColumnsToContents()

    def _populate_projects(self):
        """Load existing QFieldCloud projects into the combo box."""
        try:
            adapter = self._extension.get_sdk_adapter()
            if adapter:
                projects = adapter.list_projects()
                for project in projects:
                    name = project.get('name', 'Unknown')
                    pid = project.get('id', '')
                    self._existing_combo.addItem(name, pid)
        except Exception as e:
            logger.debug("Could not load projects: %s", e)

        # Set default project name from credentials
        default = self._extension._credentials_manager.get_default_project()
        if default:
            self._name_edit.setText(default)

    def _connect_signals(self):
        """Connect UI signals."""
        self._radio_update.toggled.connect(
            self._existing_combo.setEnabled
        )
        self._export_btn.clicked.connect(self._on_export)
        self._button_box.rejected.connect(self._on_cancel)

    def _get_layer_actions(self) -> Dict[str, str]:
        """Read layer action modes from the table."""
        actions = {}
        for row in range(self._layers_table.rowCount()):
            name_item = self._layers_table.item(row, 0)
            combo = self._layers_table.cellWidget(row, 1)
            if name_item and combo:
                actions[name_item.text()] = combo.currentText()
        return actions

    def _on_export(self):
        """Start the export + push operation."""
        project_name = self._name_edit.text().strip()
        if not project_name:
            QMessageBox.warning(
                self, "Missing Name", "Please enter a project name."
            )
            return

        service = self._extension.get_qfc_service()
        if not service:
            QMessageBox.critical(
                self, "Not Connected",
                "QFieldCloud is not connected. Please configure credentials first.",
            )
            return

        # Determine existing project ID if updating
        existing_id = None
        if self._radio_update.isChecked():
            idx = self._existing_combo.currentIndex()
            if idx >= 0:
                existing_id = self._existing_combo.itemData(idx)

        # First, export GPKG using FilterMate's existing export
        gpkg_path = self._export_gpkg(project_name)
        if not gpkg_path:
            return

        # Prepare push kwargs
        push_kwargs = {
            'project_name': project_name,
            'gpkg_path': gpkg_path,
            'description': self._desc_edit.text().strip(),
            'layer_actions': self._get_layer_actions(),
            'existing_project_id': existing_id,
            'auto_package': self._extension._credentials_manager.get_auto_package(),
        }

        # Show progress, disable export button
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)
        self._progress_label.setVisible(True)
        self._export_btn.setEnabled(False)

        # Run push in background thread
        self._worker = PushWorker(service, push_kwargs)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_push_finished)
        self._worker.error.connect(self._on_push_error)
        self._worker.start()

    def _export_gpkg(self, project_name: str) -> Optional[Path]:
        """
        Export current filtered layers to a temporary GPKG.

        Uses FilterMate's existing export infrastructure.

        Returns:
            Path to exported GPKG or None on failure
        """
        import tempfile

        from qgis.core import QgsVectorFileWriter

        project = QgsProject.instance()
        layers = [
            l for l in project.mapLayers().values()
            if isinstance(l, QgsVectorLayer) and l.isValid()
        ]

        if not layers:
            QMessageBox.warning(self, "No Layers", "No valid layers to export.")
            return None

        tmp_dir = Path(tempfile.mkdtemp(prefix="filtermate_qfc_"))
        gpkg_path = tmp_dir / f"{project_name}.gpkg"

        try:
            for i, layer in enumerate(layers):
                options = QgsVectorFileWriter.SaveVectorOptions()
                options.driverName = "GPKG"
                options.fileEncoding = "UTF-8"

                if i == 0:
                    options.actionOnExistingFile = (
                        QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteFile
                    )
                else:
                    options.actionOnExistingFile = (
                        QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteLayer
                    )
                options.layerName = layer.name()

                # Export respects the layer's subsetString (active filter)
                error_code, error_msg, _, _ = QgsVectorFileWriter.writeAsVectorFormatV3(
                    layer, str(gpkg_path), layer.transformContext(), options
                )

                if error_code != QgsVectorFileWriter.WriterError.NoError:
                    QMessageBox.critical(
                        self, "Export Error",
                        f"Failed to export layer '{layer.name()}': {error_msg}",
                    )
                    return None

            logger.info("Exported %d layers to %s", len(layers), gpkg_path)
            return gpkg_path

        except Exception as e:
            QMessageBox.critical(
                self, "Export Error", f"GPKG export failed: {e}"
            )
            return None

    def _on_progress(self, percent: int, message: str):
        """Update progress bar."""
        self._progress_bar.setValue(percent)
        self._progress_label.setText(message)

    def _on_push_finished(self, result):
        """Handle push completion."""
        self._worker = None
        self._export_btn.setEnabled(True)

        if result.success:
            self._progress_bar.setValue(100)
            self._progress_label.setText("Push complete!")

            from qgis.core import Qgis, QgsMessageLog

            QgsMessageLog.logMessage(
                f"Project pushed to QFieldCloud: {result.project_url}",
                tag="FilterMate/QFieldCloud",
                level=Qgis.MessageLevel.Info,
            )

            msg = (
                f"Project successfully pushed to QFieldCloud!\n\n"
                f"Project: {result.project_id}\n"
                f"Files: {result.files_uploaded}\n"
                f"Duration: {result.duration_seconds:.1f}s\n"
                f"URL: {result.project_url}"
            )
            if result.warnings:
                msg += "\n\nWarnings:\n" + "\n".join(result.warnings)

            QMessageBox.information(self, "Push Complete", msg)
            self.accept()
        else:
            self._on_push_error(result.error_message or "Unknown error")

    def _on_push_error(self, error: str):
        """Handle push error."""
        self._worker = None
        self._export_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._progress_label.setText(f"Error: {error}")
        self._progress_label.setStyleSheet("color: red;")

        from qgis.core import Qgis, QgsMessageLog

        QgsMessageLog.logMessage(
            f"QFieldCloud push failed: {error}",
            tag="FilterMate/QFieldCloud",
            level=Qgis.MessageLevel.Critical,
        )

        QMessageBox.critical(self, "Push Failed", f"Push failed:\n\n{error}")

    def _on_cancel(self):
        """Cancel push operation if running."""
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(3000)
            self._worker = None
        self.reject()

    def closeEvent(self, event):
        """Ensure worker is stopped on close."""
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(3000)
        super().closeEvent(event)
