# -*- coding: utf-8 -*-
"""
Port interface for QFieldCloud operations.

Follows FilterMate's hexagonal architecture:
    core/ports/  = abstract interfaces
    extensions/qfieldcloud/ = concrete implementation

This port is defined in core/ so that other core services can depend
on the interface without importing the extension directly.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional


class QFieldCloudPort(ABC):
    """Abstract port for QFieldCloud operations."""

    @abstractmethod
    def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        ...

    @abstractmethod
    def authenticate(self, url: str, username: str, password: str) -> str:
        """
        Authenticate and return token.

        Args:
            url: QFieldCloud server URL
            username: Username
            password: Password

        Returns:
            JWT token string
        """
        ...

    @abstractmethod
    def list_projects(self) -> List[Dict[str, Any]]:
        """List accessible projects."""
        ...

    @abstractmethod
    def push_project(
        self,
        project_name: str,
        gpkg_path: Path,
        styles_dir: Optional[Path] = None,
        description: str = "",
        layer_actions: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Push a GPKG + generated .qgs to QFieldCloud.

        Returns dict with 'project_id', 'url', 'job_id'.
        """
        ...

    @abstractmethod
    def update_project(
        self,
        project_id: str,
        gpkg_path: Path,
        styles_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Update files in an existing project.

        Returns dict with 'project_id', 'url', 'files_uploaded'.
        """
        ...
