# -*- coding: utf-8 -*-
"""
Qt signals emitted during QFieldCloud operations.

Allows other plugins or scripts to react to QFieldCloud events.

Usage:
    from filter_mate.extensions.qfieldcloud.signals import QFieldCloudSignals

    signals = QFieldCloudSignals()
    signals.project_pushed.connect(on_project_pushed)
"""

from qgis.PyQt.QtCore import pyqtSignal, QObject


class QFieldCloudSignals(QObject):
    """Signals emitted during QFieldCloud operations."""

    # Emitted when a project is successfully pushed
    # Args: project_id (str), project_name (str), url (str)
    project_pushed = pyqtSignal(str, str, str)

    # Emitted when batch push completes
    # Args: total (int), succeeded (int), failed (int)
    batch_completed = pyqtSignal(int, int, int)

    # Emitted on push failure
    # Args: project_name (str), error_message (str)
    push_failed = pyqtSignal(str, str)

    # Emitted when packaging job finishes on server
    # Args: project_id (str), job_status (str)
    packaging_finished = pyqtSignal(str, str)

    # Emitted on progress updates
    # Args: percent (int), message (str)
    progress_updated = pyqtSignal(int, str)

    # Emitted when authentication succeeds
    # Args: username (str)
    authenticated = pyqtSignal(str)

    # Emitted when authentication fails
    # Args: error_message (str)
    authentication_failed = pyqtSignal(str)
