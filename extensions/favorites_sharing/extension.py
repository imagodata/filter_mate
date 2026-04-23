# -*- coding: utf-8 -*-
"""
FavoritesSharing Extension — BaseExtension entry point.

Discovers favorites JSON bundles published through the QGIS
``resource_sharing`` plugin, exposes them to FilterMate's Favorites Manager
dialog as a read-only "Shared" section, and provides a "Fork" action that
copies a shared favorite into the current project's DB.

Has **no required runtime dependency** on ``resource_sharing`` — absent
that plugin, the scanner still looks at the conventional profile path
(``{profile}/resource_sharing/collections``) and just returns an empty
list. Users can still install collections manually under that tree.
"""

import logging
from typing import Any, List, Optional

from qgis.PyQt.QtCore import QCoreApplication

from ..base import BaseExtension, ExtensionMetadata
from .scanner import ResourceSharingScanner
from .service import FavoritesSharingService

logger = logging.getLogger('FilterMate.Extensions.FavoritesSharing')


class FavoritesSharingExtension(BaseExtension):
    """Favorites collections via QGIS Resource Sharing."""

    EXTENSION_ID = "favorites_sharing"
    EXTENSION_VERSION = "1.0.0"

    @staticmethod
    def tr(message: str) -> str:
        return QCoreApplication.translate('FavoritesSharingExtension', message)

    def __init__(self):
        super().__init__()
        self._iface = None
        self._scanner: Optional[ResourceSharingScanner] = None
        self._service: Optional[FavoritesSharingService] = None

    @property
    def metadata(self) -> ExtensionMetadata:
        return ExtensionMetadata(
            id=self.EXTENSION_ID,
            name="Favorites Sharing",
            version=self.EXTENSION_VERSION,
            description=(
                "Distribute and consume FilterMate favorite collections "
                "through the QGIS Resource Sharing plugin."
            ),
            author="FilterMate Team",
            min_qgis_version="3.28",
            dependencies=[],
            optional_dependencies=["resource_sharing"],
            icon_name="favorites_shared.png",
        )

    def check_dependencies(self) -> bool:
        """No hard dependencies — always available.

        The resource_sharing plugin is optional: when absent, we still
        scan the conventional ``~/.qgis/.../resource_sharing/collections``
        tree (users can populate it manually). When present, nothing
        changes — we just read the same directory.
        """
        return True

    def initialize(self, iface: Any) -> None:
        self._iface = iface
        self._scanner = ResourceSharingScanner()
        self._service = FavoritesSharingService(self._scanner)
        self.register_service('scanner', self._scanner)
        self.register_service('service', self._service)
        logger.info("FavoritesSharing extension initialized")

    def create_ui(self, toolbar: Any, menu_name: str) -> List[Any]:
        """No toolbar button — UI is injected into the Favorites Manager
        dialog via the service when the dialog opens.
        """
        return []

    def teardown(self) -> None:
        self._scanner = None
        self._service = None
        self._iface = None

    def on_project_loaded(self) -> None:
        """Re-scan so a newly-loaded project's layers can resolve shared
        favorites' signatures.
        """
        if self._service is not None:
            try:
                self._service.invalidate_cache()
            except Exception as e:
                logger.debug(f"Scanner cache invalidation skipped: {e}")
