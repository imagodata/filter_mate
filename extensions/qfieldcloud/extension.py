# -*- coding: utf-8 -*-
"""
QFieldCloud Extension — Main entry point.

Implements BaseExtension lifecycle for the QFieldCloud integration module.
Manages SDK adapter, credentials, project builder, and UI components.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from ..base import BaseExtension, ExtensionMetadata, ExtensionState

logger = logging.getLogger('FilterMate.Extensions.QFieldCloud')

# Lazy availability flag — set on first check_dependencies() call
_QFIELDSYNC_AVAILABLE: Optional[bool] = None


def _check_qfieldsync_available() -> bool:
    """Check if qfieldsync plugin is installed and importable."""
    global _QFIELDSYNC_AVAILABLE
    if _QFIELDSYNC_AVAILABLE is None:
        try:
            from qfieldsync.core.cloud_api import CloudNetworkAccessManager  # noqa: F401
            _QFIELDSYNC_AVAILABLE = True
        except ImportError:
            _QFIELDSYNC_AVAILABLE = False
    return _QFIELDSYNC_AVAILABLE


class QFieldCloudExtension(BaseExtension):
    """
    QFieldCloud integration extension for FilterMate.

    Provides:
    - One-click export of filtered layers to QFieldCloud
    - Credential management (keyring + QgsSettings)
    - .qgs project generation with QFieldSync properties
    - Batch push for multiple zones

    Requires: qfieldcloud-sdk >= 0.8.0 (optional dependency)
    """

    EXTENSION_ID = "qfieldcloud"
    EXTENSION_VERSION = "1.0.0"

    def __init__(self):
        super().__init__()
        self._iface = None
        self._credentials_manager = None
        self._sdk_adapter = None
        self._qfc_service = None
        self._signals = None
        self._qfc_button = None
        self._dockwidget = None

    @property
    def metadata(self) -> ExtensionMetadata:
        return ExtensionMetadata(
            id=self.EXTENSION_ID,
            name="QFieldCloud",
            version=self.EXTENSION_VERSION,
            description="Export filtered layers to QFieldCloud in one click",
            author="FilterMate Team / WYRE FTTH",
            min_qgis_version="3.28",
            dependencies=["qfieldsync"],
            optional_dependencies=["keyring"],
            icon_name="qfieldcloud.png",
        )

    def check_dependencies(self) -> bool:
        """Check if QFieldSync plugin is installed."""
        return _check_qfieldsync_available()

    def initialize(self, iface: Any) -> None:
        """
        Initialize QFieldCloud services.

        Creates credentials manager and signals. SDK adapter and push
        service are created lazily when needed (and only if SDK is available).
        """
        self._iface = iface

        # These modules have no SDK dependency
        from .credentials_manager import CredentialsManager
        from .signals import QFieldCloudSignals

        self._credentials_manager = CredentialsManager()
        self.register_service('credentials', self._credentials_manager)

        self._signals = QFieldCloudSignals()
        self.register_service('signals', self._signals)

        logger.info("QFieldCloud extension initialized")

    def create_ui(self, toolbar: Any, menu_name: str) -> List[Any]:
        """Create QFieldCloud menu entries (button is in dockwidget)."""
        from qgis.PyQt.QtGui import QAction

        actions = []
        parent = self._iface.mainWindow()

        # Settings action (menu only)
        settings_action = QAction("QFieldCloud Settings...", parent)
        settings_action.triggered.connect(self._on_settings_triggered)
        self._iface.addPluginToVectorMenu(menu_name, settings_action)
        actions.append(settings_action)

        self._actions = actions
        return actions

    def create_dockwidget_ui(self, dockwidget: Any) -> List[Any]:
        """Inject QFieldCloud export button into the dockwidget action bar."""
        from qgis.PyQt.QtCore import QSize, Qt
        from qgis.PyQt.QtGui import QCursor, QIcon
        from qgis.PyQt.QtWidgets import QPushButton

        plugin_dir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)
        )))
        icon_path = os.path.join(plugin_dir, 'icons', 'qfield.png')
        if not os.path.isfile(icon_path):
            icon_path = os.path.join(plugin_dir, 'icons', 'export.png')

        # Copy size from existing export button for consistency
        export_btn = getattr(dockwidget, 'pushButton_action_export', None)
        icon_size = QSize(35, 35)
        if export_btn:
            icon_size = export_btn.iconSize()

        # Create the push button matching the style of existing action buttons
        btn = QPushButton(dockwidget)
        btn.setObjectName("pushButton_action_qfieldcloud")
        btn.setToolTip("Export filtered layers to QFieldCloud")
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        if os.path.isfile(icon_path):
            btn.setIcon(QIcon(icon_path))
        btn.setIconSize(icon_size)
        btn.setFlat(True)
        btn.setText("")
        btn.clicked.connect(self._on_push_triggered)

        # Copy size policy and constraints from export button
        if export_btn:
            btn.setMinimumSize(export_btn.minimumSize())
            btn.setMaximumSize(export_btn.maximumSize())
            btn.setSizePolicy(export_btn.sizePolicy())

        # Start disabled — enabled only when EXPORTING panel is active
        btn.setEnabled(False)

        # Register as dockwidget attribute so ActionBarManager can find it
        dockwidget.pushButton_action_qfieldcloud = btn

        # Find the action bar layout and insert after the export button
        layout = getattr(dockwidget, 'horizontalLayout_actions_bottom', None)

        if layout and export_btn:
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget() == export_btn:
                    layout.insertWidget(i + 1, btn)
                    break
            else:
                layout.addWidget(btn)
        elif layout:
            layout.addWidget(btn)
        else:
            logger.warning("QFieldCloud: Could not find action bar layout in dockwidget")
            return []

        # Store reference for teardown
        self._qfc_button = btn
        self._dockwidget = dockwidget

        logger.info("QFieldCloud: Export button added to dockwidget action bar")
        return [btn]

    def teardown(self) -> None:
        """Cleanup all QFieldCloud resources."""
        # Remove dockwidget button and attribute
        if self._qfc_button is not None:
            if hasattr(self, '_dockwidget') and self._dockwidget is not None:
                try:
                    delattr(self._dockwidget, 'pushButton_action_qfieldcloud')
                except AttributeError:
                    pass
                self._dockwidget = None
            self._qfc_button.setParent(None)
            self._qfc_button.deleteLater()
            self._qfc_button = None

        # Remove UI actions (menu entries)
        for action in self._actions:
            if hasattr(action, 'removeAction'):
                continue
            if hasattr(action, 'parent') and callable(action.parent) and action.parent():
                action.parent().removeAction(action)
        self._actions.clear()

        # Cleanup services
        if self._sdk_adapter:
            self._sdk_adapter = None
        if self._qfc_service:
            self._qfc_service = None
        if self._credentials_manager:
            self._credentials_manager = None
        if self._signals:
            self._signals = None

        self._services.clear()
        self._iface = None
        logger.info("QFieldCloud extension torn down")

    # ------------------------------------------------------------------
    # Lazy service initialization
    # ------------------------------------------------------------------

    def get_sdk_adapter(self):
        """
        Get or create the SDK adapter.

        Creates the adapter lazily using stored credentials.
        Returns None if credentials are not configured.
        """
        if self._sdk_adapter is not None:
            return self._sdk_adapter

        from .sdk_adapter import QFieldCloudAdapter

        # Create adapter using QFieldSync's CloudNetworkAccessManager
        self._sdk_adapter = QFieldCloudAdapter()

        # Try auto-login with QFieldSync's stored credentials
        if not self._sdk_adapter.is_authenticated:
            self._sdk_adapter.auto_login()

        self.register_service('adapter', self._sdk_adapter)
        return self._sdk_adapter

    def get_qfc_service(self):
        """
        Get or create the QFieldCloud service.

        Creates the service lazily with adapter and credentials.
        Returns None if SDK adapter is not available.
        """
        if self._qfc_service is not None:
            return self._qfc_service

        adapter = self.get_sdk_adapter()
        if adapter is None:
            return None

        from .service import QFieldCloudService

        self._qfc_service = QFieldCloudService(
            adapter=adapter,
            credentials_manager=self._credentials_manager,
            signals=self._signals,
        )
        self.register_service('push', self._qfc_service)
        return self._qfc_service

    def reset_adapter(self) -> None:
        """Reset SDK adapter (e.g., after credential change)."""
        self._sdk_adapter = None
        self._qfc_service = None
        if 'adapter' in self._services:
            del self._services['adapter']
        if 'push' in self._services:
            del self._services['push']

    # ------------------------------------------------------------------
    # UI action handlers
    # ------------------------------------------------------------------

    def _on_push_triggered(self) -> None:
        """Handle 'Export QFieldCloud' button click."""
        # Try to get adapter and auto-login
        adapter = self.get_sdk_adapter()
        if adapter is None or not adapter.is_authenticated:
            # No QFieldSync credentials either — open settings
            self._on_settings_triggered()
            return

        from .ui.push_dialog import QFieldCloudPushDialog

        dialog = QFieldCloudPushDialog(
            parent=self._iface.mainWindow(),
            extension=self,
            iface=self._iface,
        )
        dialog.exec()

    def _on_settings_triggered(self) -> None:
        """Handle 'QFieldCloud Settings' menu click."""
        from .ui.settings_dialog import QFieldCloudSettingsDialog

        dialog = QFieldCloudSettingsDialog(
            parent=self._iface.mainWindow(),
            extension=self,
        )
        if dialog.exec():
            # Credentials may have changed — reset adapter
            self.reset_adapter()
