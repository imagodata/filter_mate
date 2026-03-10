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
_SDK_AVAILABLE: Optional[bool] = None


def _check_sdk_available() -> bool:
    """Check if qfieldcloud-sdk is importable."""
    global _SDK_AVAILABLE
    if _SDK_AVAILABLE is None:
        try:
            import qfieldcloud_sdk  # noqa: F401
            _SDK_AVAILABLE = True
        except ImportError:
            _SDK_AVAILABLE = False
    return _SDK_AVAILABLE


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

    @property
    def metadata(self) -> ExtensionMetadata:
        return ExtensionMetadata(
            id=self.EXTENSION_ID,
            name="QFieldCloud",
            version=self.EXTENSION_VERSION,
            description="Export filtered layers to QFieldCloud in one click",
            author="FilterMate Team / WYRE FTTH",
            min_qgis_version="3.28",
            dependencies=["qfieldcloud_sdk"],
            optional_dependencies=["keyring"],
            icon_name="qfieldcloud.png",
        )

    def check_dependencies(self) -> bool:
        """Check if qfieldcloud-sdk is installed."""
        available = _check_sdk_available()
        if not available:
            logger.info(
                "QFieldCloud extension disabled: qfieldcloud-sdk not installed. "
                "Install with: pip install qfieldcloud-sdk"
            )
        return available

    def initialize(self, iface: Any) -> None:
        """
        Initialize QFieldCloud services.

        Creates credentials manager, SDK adapter, project builder,
        and the orchestration service.
        """
        self._iface = iface

        # Import here to avoid import errors when SDK is absent
        from .credentials_manager import CredentialsManager
        from .signals import QFieldCloudSignals

        # Initialize credentials manager
        self._credentials_manager = CredentialsManager()
        self.register_service('credentials', self._credentials_manager)

        # Initialize signals
        self._signals = QFieldCloudSignals()
        self.register_service('signals', self._signals)

        # SDK adapter and service are created lazily (need credentials first)
        logger.info("QFieldCloud extension initialized")

    def create_ui(self, toolbar: Any, menu_name: str) -> List[Any]:
        """Create QFieldCloud toolbar button and menu entries."""
        from qgis.PyQt.QtGui import QAction, QIcon
        from qgis.PyQt.QtWidgets import QMenu

        actions = []
        plugin_dir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)
        )))
        icon_path = os.path.join(plugin_dir, 'icons', 'qfieldcloud.png')

        # Fallback icon if custom icon doesn't exist
        if not os.path.isfile(icon_path):
            icon_path = os.path.join(plugin_dir, 'icons', 'export.png')
        if not os.path.isfile(icon_path):
            icon = QIcon()
        else:
            icon = QIcon(icon_path)

        # Main push action
        parent = self._iface.mainWindow()
        push_action = QAction(icon, "Export QFieldCloud", parent)
        push_action.setToolTip(
            "Export filtered layers to QFieldCloud"
        )
        push_action.triggered.connect(self._on_push_triggered)
        push_action.setEnabled(True)
        toolbar.addAction(push_action)
        actions.append(push_action)

        # Settings action (menu only)
        settings_action = QAction("QFieldCloud Settings...", parent)
        settings_action.triggered.connect(self._on_settings_triggered)
        self._iface.addPluginToVectorMenu(menu_name, settings_action)
        actions.append(settings_action)

        self._actions = actions
        return actions

    def teardown(self) -> None:
        """Cleanup all QFieldCloud resources."""
        # Remove UI actions
        for action in self._actions:
            if action.parent():
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

        if not self._credentials_manager or not self._credentials_manager.has_credentials():
            return None

        from .sdk_adapter import QFieldCloudAdapter

        url = self._credentials_manager.get_url()
        token = self._credentials_manager.get_token()
        self._sdk_adapter = QFieldCloudAdapter(url=url, token=token)
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
        if not self._credentials_manager.has_credentials():
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
