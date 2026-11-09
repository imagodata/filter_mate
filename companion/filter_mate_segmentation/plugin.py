# -*- coding: utf-8 -*-
"""QGIS plugin giving FilterMate its segmentation model.

The model is fetched only when the user asks for it. onnxruntime is never
installed by this plugin: the command is shown, the user runs it.
"""
import importlib.util
import os
from typing import Any, Optional

from qgis.core import QgsApplication, QgsTask
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QMessageBox

try:
    from qgis.PyQt.QtGui import QAction
except ImportError:  # QGIS < 3.34.2 (Qt5): QAction is in QtWidgets
    from qgis.PyQt.QtWidgets import QAction

from . import model_files

INSTALL_COMMAND = 'python -m pip install onnxruntime'


def _tr(text: str) -> str:
    return QCoreApplication.translate('FilterMateSegmentation', text)


def model_directory() -> str:
    return os.path.join(QgsApplication.qgisSettingsDirPath(), 'filter_mate_segmentation', 'sam2.1-hiera-tiny-q')


class _DownloadTask(QgsTask):
    def __init__(self, directory: str, callback: Any) -> None:
        super().__init__(_tr('FilterMate: downloading the segmentation model'), QgsTask.Flag.CanCancel)
        self.directory, self.callback, self.error = directory, callback, ''

    def run(self) -> bool:
        try:
            model_files.download(self.directory, self.isCanceled, self.setProgress)
            return True
        except model_files.Canceled:
            return False
        except Exception as exc:  # network or disk: told to the user
            self.error = str(exc)
            return False

    def finished(self, result: bool) -> None:
        self.callback(self, bool(result))


class FilterMateSegmentationPlugin:
    def __init__(self, iface: Any) -> None:
        self.iface = iface
        self._provider: Any = None
        self._action: Any = None
        self._task: Any = None

    def initGui(self) -> None:  # noqa: N802 - QGIS plugin interface
        self._action = QAction(_tr('Install the segmentation model…'), self.iface.mainWindow())
        self._action.triggered.connect(self.install)
        self.iface.addPluginToMenu('FilterMate Segmentation', self._action)

    def unload(self) -> None:
        if self._task is not None:
            try:
                self._task.cancel()
            except RuntimeError:
                pass  # already finished
        if self._action is not None:
            self.iface.removePluginMenu('FilterMate Segmentation', self._action)
        self._provider = None

    def segmentation_provider(self) -> Optional[Any]:
        """What FilterMate calls at each raster: a few stats, no model is opened here; None until both are there."""
        if self._provider is None and model_files.is_installed(model_directory()) and importlib.util.find_spec('onnxruntime'):
            from .sam_provider import SamOnnxProvider
            self._provider = SamOnnxProvider(model_directory())
        return self._provider

    def install(self) -> None:
        try:
            import onnxruntime  # noqa: F401 - only its presence matters
        except ImportError:
            QMessageBox.information(self.iface.mainWindow(), 'FilterMate Segmentation', _tr(
                'This plugin needs onnxruntime. In a terminal using the Python of your QGIS '
                '(the OSGeo4W Shell on Windows), run:\n\n{0}\n\nThen restart QGIS.').format(INSTALL_COMMAND))
            return
        directory = model_directory()
        if model_files.is_installed(directory):
            self.iface.messageBar().pushInfo('FilterMate Segmentation', _tr('The model is already installed'))
            return
        answer = QMessageBox.question(self.iface.mainWindow(), 'FilterMate Segmentation', _tr(
            'Download the model SAM 2.1 tiny ({0} MB) from huggingface.co/{1} ?').format(
                round(model_files.total_size() / 1e6), model_files.REPOSITORY))
        if answer != QMessageBox.StandardButton.Yes or self._task is not None:
            return
        self._task = _DownloadTask(directory, self._downloaded)
        QgsApplication.taskManager().addTask(self._task)

    def _downloaded(self, task: Any, success: bool) -> None:
        self._task = None
        bar = self.iface.messageBar()
        if success:
            bar.pushSuccess('FilterMate Segmentation', _tr('Model installed: select a raster again, then choose Segment in the PIPETTE group'))
        elif task.error:
            bar.pushWarning('FilterMate Segmentation', _tr('The model could not be downloaded: {0}').format(task.error))
