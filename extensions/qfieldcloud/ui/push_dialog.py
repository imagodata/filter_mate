# -*- coding: utf-8 -*-
"""
QFieldCloud Push Dialog for FilterMate.

Allows users to export current filtered layers to QFieldCloud.
Shows active filter info, project naming, layer action modes,
and upload progress.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional

from qgis.core import QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QCoreApplication, QThread, Qt, pyqtSignal
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

    @staticmethod
    def tr(message):
        return QCoreApplication.translate('QFieldCloudPushDialog', message)

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

        self.setWindowTitle(self.tr("Export to QFieldCloud"))
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
        info_group = QGroupBox(self.tr("Active Filter"))
        info_layout = QFormLayout()

        self._filter_label = QLabel(self.tr("No active filter"))
        info_layout.addRow(self.tr("Filter:"), self._filter_label)

        self._layers_label = QLabel(self.tr("0 layers"))
        info_layout.addRow(self.tr("Layers:"), self._layers_label)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # --- Project settings ---
        project_group = QGroupBox(self.tr("QFieldCloud Project"))
        project_layout = QFormLayout()

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("WYRE-POP_001")
        project_layout.addRow(self.tr("Project name:"), self._name_edit)

        self._desc_edit = QLineEdit()
        self._desc_edit.setPlaceholderText("WYRE FTTH - Zone POP 001")
        project_layout.addRow(self.tr("Description:"), self._desc_edit)

        # Create new vs update existing
        mode_layout = QHBoxLayout()
        self._radio_new = QRadioButton(self.tr("Create new"))
        self._radio_update = QRadioButton(self.tr("Update existing:"))
        self._radio_new.setChecked(True)
        mode_layout.addWidget(self._radio_new)
        mode_layout.addWidget(self._radio_update)
        project_layout.addRow(self.tr("Mode:"), mode_layout)

        self._existing_combo = QComboBox()
        self._existing_combo.setEnabled(False)
        project_layout.addRow("", self._existing_combo)

        project_group.setLayout(project_layout)
        layout.addWidget(project_group)

        # --- Layer actions table ---
        layers_group = QGroupBox(self.tr("Layer Modes"))
        layers_layout = QVBoxLayout()

        self._layers_table = QTableWidget()
        self._layers_table.setColumnCount(2)
        self._layers_table.setHorizontalHeaderLabels([self.tr("Layer"), self.tr("Mode")])
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
            self.tr("Export"), QDialogButtonBox.ButtonRole.AcceptRole
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
                self.tr("{0} layers ({1} features)").format(len(filtered_layers), total_features)
            )
        else:
            # Show all vector layers if no filter active
            all_vector = [
                l for l in layers if isinstance(l, QgsVectorLayer)
            ]
            self._layers_label.setText(
                self.tr("{0} layers (no filter active)").format(len(all_vector))
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
                self, self.tr("Missing Name"), self.tr("Please enter a project name.")
            )
            return

        service = self._extension.get_qfc_service()
        if not service:
            QMessageBox.critical(
                self, self.tr("Not Connected"),
                self.tr("QFieldCloud is not connected. Please configure credentials first."),
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

        # Run push in background thread.
        # parent=None on the QThread (PushWorker default) keeps it alive
        # via self._worker — parenting to a QDialog would let Qt destroy
        # a still-running QThread on dialog close.
        # finished/error → deleteLater() so the QThread cleans up after
        # itself once run() returns, even if the dialog has been closed.
        self._worker = PushWorker(service, push_kwargs)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_push_finished)
        self._worker.error.connect(self._on_push_error)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.error.connect(self._worker.deleteLater)
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
            QMessageBox.warning(self, self.tr("No Layers"), self.tr("No valid layers to export."))
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
                        self, self.tr("Export Error"),
                        self.tr("Failed to export layer '{0}': {1}").format(layer.name(), error_msg),
                    )
                    return None

            logger.info("Exported %d layers to %s", len(layers), gpkg_path)
            return gpkg_path

        except Exception as e:
            QMessageBox.critical(
                self, self.tr("Export Error"), self.tr("GPKG export failed: {0}").format(e)
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
            self._progress_label.setText(self.tr("Push complete!"))

            from qgis.core import Qgis, QgsMessageLog

            QgsMessageLog.logMessage(
                f"Project pushed to QFieldCloud: {result.project_url}",
                tag="FilterMate/QFieldCloud",
                level=Qgis.MessageLevel.Info,
            )

            msg = (
                self.tr("Project successfully pushed to QFieldCloud!") + "\n\n"
                + self.tr("Project: {0}").format(result.project_id) + "\n"
                + self.tr("Files: {0}").format(result.files_uploaded) + "\n"
                + self.tr("Duration: {0:.1f}s").format(result.duration_seconds) + "\n"
                + self.tr("URL: {0}").format(result.project_url)
            )
            if result.warnings:
                msg += "\n\n" + self.tr("Warnings:") + "\n" + "\n".join(result.warnings)

            QMessageBox.information(self, self.tr("Push Complete"), msg)
            self.accept()
        else:
            self._on_push_error(result.error_message or "Unknown error")

    def _on_push_error(self, error: str):
        """Handle push error."""
        self._worker = None
        self._export_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._progress_label.setText(self.tr("Error: {0}").format(error))
        self._progress_label.setStyleSheet("color: red;")

        from qgis.core import Qgis, QgsMessageLog

        QgsMessageLog.logMessage(
            f"QFieldCloud push failed: {error}",
            tag="FilterMate/QFieldCloud",
            level=Qgis.MessageLevel.Critical,
        )

        QMessageBox.critical(self, self.tr("Push Failed"), self.tr("Push failed:\n\n{0}").format(error))

    def _stop_worker(self) -> None:
        """Tear down the push worker safely.

        Drops widget-touching slot connections **before** terminate() so a
        late progress/finished/error cannot fire on a half-destroyed
        dialog. terminate() is preserved here (vs. the GitOpsWorker
        wait-only pattern): a QFC upload interrupt yields at worst a
        half-uploaded file the server will reject, while git clone
        interrupt would corrupt the local working tree. The 10s wait is
        a conservative cap — terminate() itself returns near-immediately.
        """
        worker = self._worker
        if worker is None:
            return
        try:
            worker.progress.disconnect(self._on_progress)
            worker.finished.disconnect(self._on_push_finished)
            worker.error.disconnect(self._on_push_error)
        except (TypeError, RuntimeError):
            pass
        if worker.isRunning():
            worker.terminate()
            worker.wait(10_000)
        # The deleteLater connections wired on start() will fire if the
        # worker emits finished/error before terminate; otherwise the
        # QThread is reaped when self._worker is dropped + GC'd.
        self._worker = None

    def _on_cancel(self):
        """Cancel push operation if running."""
        self._stop_worker()
        self.reject()

    def closeEvent(self, event):
        """Ensure worker is stopped on close."""
        self._stop_worker()
        super().closeEvent(event)
