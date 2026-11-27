"""A local, explicit choice of the agent export folder, separate from the QGIS profile."""
from pathlib import Path


def choose_export_folder(parent):
    from qgis.core import QgsSettings
    from qgis.PyQt.QtCore import QCoreApplication
    from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox
    from ...filtermate_api.config import EXPORT_FOLDER_KEY, _default_export_root
    from ...filtermate_api.export_root import ExportRootError, assert_export_destination
    def tr(text):
        return QCoreApplication.translate('AgentExports', text)
    folder = QFileDialog.getExistingDirectory(parent, tr('Choose the default agent export folder'), str(_default_export_root()))
    if not folder:
        return None
    try:
        path = Path(folder).expanduser().resolve()
        assert_export_destination(path)
        if not path.is_absolute() or not path.is_dir():
            raise ExportRootError(tr('Choose an existing folder outside the QGIS profiles.'))
    except (ExportRootError, OSError, ValueError, RuntimeError):
        QMessageBox.warning(parent, tr('Export folder'), tr('Choose an existing folder outside the QGIS profiles.'))
        return None
    QgsSettings().setValue(EXPORT_FOLDER_KEY, str(path))
    return path
