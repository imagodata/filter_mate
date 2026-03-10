# -*- coding: utf-8 -*-
"""
Adapter wrapping qfieldcloud-sdk Client for FilterMate.

Responsibilities:
- Authentication (login/token)
- Project CRUD
- File upload with retry and backoff
- Job management (trigger + poll status)

Thread safety: NOT thread-safe. Use from main thread or QgsTask only.
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .exceptions import (
    QFieldCloudAuthError,
    QFieldCloudError,
    QFieldCloudProjectError,
    QFieldCloudTimeoutError,
    QFieldCloudUploadError,
)

logger = logging.getLogger('FilterMate.Extensions.QFieldCloud.Adapter')


class QFieldCloudAdapter:
    """
    Adapter for qfieldcloud-sdk Client.

    Wraps the SDK with retry logic, structured error handling,
    and FilterMate-specific exception types.
    """

    MAX_RETRIES = 3
    BACKOFF_BASE = 2  # seconds
    CONNECTION_TIMEOUT = 30  # seconds
    UPLOAD_TIMEOUT = 300  # seconds

    def __init__(self, url: str, token: Optional[str] = None):
        from qfieldcloud_sdk import sdk

        self._client = sdk.Client(url=url)
        self._url = url
        self._token = token
        self._authenticated = False
        self._username: Optional[str] = None

        # If token provided, set it directly
        if token:
            self._client.token = token
            self._authenticated = True

    @property
    def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        return self._authenticated

    @property
    def username(self) -> Optional[str]:
        """Get authenticated username."""
        return self._username

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def login(self, username: str, password: str) -> str:
        """
        Authenticate with username/password and return JWT token.

        Args:
            username: QFieldCloud username
            password: QFieldCloud password

        Returns:
            JWT token string

        Raises:
            QFieldCloudAuthError: If authentication fails
        """
        try:
            token = self._client.login(username, password)
            self._authenticated = True
            self._username = username
            self._token = token
            logger.info("Authenticated as '%s'", username)
            return token
        except Exception as e:
            self._authenticated = False
            raise QFieldCloudAuthError(
                f"Authentication failed for user '{username}'",
                details=str(e),
            ) from e

    def login_with_token(self, token: str) -> bool:
        """
        Authenticate with existing JWT token.

        Args:
            token: JWT token

        Returns:
            True if token is valid

        Raises:
            QFieldCloudAuthError: If token is invalid
        """
        try:
            self._client.token = token
            # Validate token by listing projects (lightweight call)
            self._client.list_projects()
            self._authenticated = True
            self._token = token
            logger.info("Authenticated with token")
            return True
        except Exception as e:
            self._authenticated = False
            self._client.token = None
            raise QFieldCloudAuthError(
                "Token authentication failed",
                details=str(e),
            ) from e

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    def list_projects(self) -> List[Dict[str, Any]]:
        """
        List accessible projects.

        Returns:
            List of project dictionaries

        Raises:
            QFieldCloudError: On API error
        """
        self._require_auth()
        try:
            return list(self._client.list_projects())
        except Exception as e:
            raise QFieldCloudError(
                "Failed to list projects", details=str(e)
            ) from e

    def create_project(
        self,
        name: str,
        description: str = "",
        owner: Optional[str] = None,
        is_public: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a new QFieldCloud project.

        Args:
            name: Project name
            description: Project description
            owner: Owner username (defaults to authenticated user)
            is_public: Whether project is publicly visible

        Returns:
            Project dict with 'id' key

        Raises:
            QFieldCloudProjectError: On creation failure
        """
        self._require_auth()
        try:
            result = self._client.create_project(
                name=name,
                owner=owner or self._username or "",
                description=description,
                is_public=is_public,
            )
            project_id = result.get('id', '')
            logger.info("Created project '%s' (id: %s)", name, project_id)
            return result
        except Exception as e:
            raise QFieldCloudProjectError(
                f"Failed to create project '{name}'",
                details=str(e),
            ) from e

    def find_project_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Find a project by name.

        Args:
            name: Project name to search for

        Returns:
            Project dict or None if not found
        """
        projects = self.list_projects()
        for project in projects:
            if project.get('name') == name:
                return project
        return None

    # ------------------------------------------------------------------
    # File upload (with retry)
    # ------------------------------------------------------------------

    def upload_project_files(
        self,
        project_id: str,
        local_dir: Path,
        filter_glob: str = "**/*",
        progress_callback=None,
    ) -> int:
        """
        Upload all matching files from local_dir to a project.

        Uses retry with exponential backoff on failure.

        Args:
            project_id: QFieldCloud project ID
            local_dir: Local directory containing files to upload
            filter_glob: Glob pattern to filter files
            progress_callback: Optional callable(percent, message)

        Returns:
            Number of files uploaded

        Raises:
            QFieldCloudUploadError: If upload fails after retries
        """
        self._require_auth()

        files_to_upload = list(local_dir.glob(filter_glob))
        files_to_upload = [f for f in files_to_upload if f.is_file()]

        if not files_to_upload:
            logger.warning("No files found in %s matching '%s'", local_dir, filter_glob)
            return 0

        total = len(files_to_upload)
        uploaded = 0
        last_error = None

        for i, file_path in enumerate(files_to_upload):
            relative_path = file_path.relative_to(local_dir)

            for attempt in range(self.MAX_RETRIES):
                try:
                    self._client.upload_files(
                        project_id=project_id,
                        upload_type="project",
                        project_path=str(local_dir),
                        filter_glob=str(relative_path),
                    )
                    uploaded += 1

                    if progress_callback:
                        percent = int((i + 1) / total * 100)
                        progress_callback(
                            percent,
                            f"Uploaded {relative_path} ({i + 1}/{total})",
                        )
                    break

                except Exception as e:
                    last_error = e
                    if attempt < self.MAX_RETRIES - 1:
                        wait = self.BACKOFF_BASE ** (attempt + 1)
                        logger.warning(
                            "Upload retry %d/%d for %s (wait %ds): %s",
                            attempt + 1, self.MAX_RETRIES,
                            relative_path, wait, e,
                        )
                        time.sleep(wait)
                    else:
                        raise QFieldCloudUploadError(
                            f"Failed to upload {relative_path} after "
                            f"{self.MAX_RETRIES} attempts",
                            details=str(e),
                        ) from e

        logger.info(
            "Uploaded %d/%d files to project %s", uploaded, total, project_id
        )
        return uploaded

    # ------------------------------------------------------------------
    # Jobs
    # ------------------------------------------------------------------

    def trigger_package(self, project_id: str) -> str:
        """
        Trigger QGIS packaging job on the server.

        Args:
            project_id: QFieldCloud project ID

        Returns:
            Job ID

        Raises:
            QFieldCloudError: On failure
        """
        self._require_auth()
        try:
            result = self._client.job_trigger(
                project_id=project_id,
                job_type="package",
            )
            job_id = result.get('id', '')
            logger.info(
                "Triggered packaging job %s for project %s", job_id, project_id
            )
            return job_id
        except Exception as e:
            raise QFieldCloudError(
                f"Failed to trigger packaging for project {project_id}",
                details=str(e),
            ) from e

    def poll_job_status(
        self,
        job_id: str,
        timeout: int = 300,
        interval: int = 5,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """
        Poll job status until finished or timeout.

        Args:
            job_id: Job ID to poll
            timeout: Maximum wait time in seconds
            interval: Poll interval in seconds
            progress_callback: Optional callable(percent, message)

        Returns:
            Final job status dict

        Raises:
            QFieldCloudTimeoutError: If timeout exceeded
            QFieldCloudError: On API error
        """
        self._require_auth()
        start_time = time.time()
        last_status = ""

        while time.time() - start_time < timeout:
            try:
                status = self._client.job_status(job_id)
                current_status = status.get('status', 'unknown')

                if current_status != last_status:
                    logger.info("Job %s status: %s", job_id, current_status)
                    last_status = current_status

                if progress_callback:
                    elapsed = int(time.time() - start_time)
                    percent = min(int(elapsed / timeout * 100), 99)
                    progress_callback(
                        percent, f"Packaging: {current_status}"
                    )

                if current_status in ('finished', 'stopped', 'failed'):
                    return status

            except Exception as e:
                logger.warning("Job poll error: %s", e)

            time.sleep(interval)

        raise QFieldCloudTimeoutError(
            f"Job {job_id} did not finish within {timeout}s"
        )

    # ------------------------------------------------------------------
    # Collaborators
    # ------------------------------------------------------------------

    def add_collaborator(
        self, project_id: str, username: str, role: str = "editor"
    ) -> None:
        """
        Add a collaborator to a project.

        Args:
            project_id: QFieldCloud project ID
            username: Collaborator username
            role: Role (reader, reporter, editor, manager, admin)

        Raises:
            QFieldCloudError: On failure
        """
        self._require_auth()
        try:
            self._client.add_project_collaborator(
                project_id=project_id,
                username=username,
                role=role,
            )
            logger.info(
                "Added collaborator '%s' (%s) to project %s",
                username, role, project_id,
            )
        except Exception as e:
            raise QFieldCloudError(
                f"Failed to add collaborator '{username}' to {project_id}",
                details=str(e),
            ) from e

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------

    def get_project_url(self, project_id: str) -> str:
        """Return the web URL for a project."""
        base = self._url.rstrip('/')
        # Strip /api/v1 if present to get web URL
        if base.endswith('/api/v1'):
            base = base[:-7]
        return f"{base}/a/{project_id}"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_auth(self) -> None:
        """Raise if not authenticated."""
        if not self._authenticated:
            raise QFieldCloudAuthError("Not authenticated. Call login() first.")
