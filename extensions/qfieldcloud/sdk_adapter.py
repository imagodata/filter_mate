# -*- coding: utf-8 -*-
"""
Adapter wrapping QFieldSync's CloudNetworkAccessManager for FilterMate.

Uses the already-installed QFieldSync QGIS plugin instead of requiring
a separate pip install of qfieldcloud-sdk. This means zero additional
dependencies — if QFieldSync is installed in QGIS, this works.

Responsibilities:
- Authentication (reuses QFieldSync credentials or login)
- Project CRUD
- File upload with retry and backoff
- Job management (trigger + poll status)

Note: QFieldSync's API is async (QNetworkReply-based). This adapter
provides synchronous wrappers using QEventLoop for FilterMate's use.
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from qgis.PyQt.QtCore import QEventLoop, QTimer

from .exceptions import (
    QFieldCloudAuthError,
    QFieldCloudError,
    QFieldCloudProjectError,
    QFieldCloudTimeoutError,
    QFieldCloudUploadError,
)

logger = logging.getLogger('FilterMate.Extensions.QFieldCloud.Adapter')


def _wait_for_reply(reply, timeout_ms=30000):
    """Wait synchronously for a QNetworkReply to finish."""
    if reply is None:
        return None
    if reply.isFinished():
        return reply

    loop = QEventLoop()
    reply.finished.connect(loop.quit)
    # Safety timeout
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(timeout_ms)
    loop.exec()
    timer.stop()
    return reply


class QFieldCloudAdapter:
    """
    Adapter wrapping QFieldSync's CloudNetworkAccessManager.

    Reuses QFieldSync's existing auth system (QgsAuthManager) and
    network infrastructure. No additional pip packages needed.
    """

    MAX_RETRIES = 3
    BACKOFF_BASE = 2  # seconds

    def __init__(self, network_manager=None):
        """
        Initialize adapter.

        Args:
            network_manager: Optional CloudNetworkAccessManager instance.
                If None, creates one from QFieldSync.
        """
        if network_manager is not None:
            self._nam = network_manager
        else:
            from qfieldsync.core.cloud_api import CloudNetworkAccessManager
            self._nam = CloudNetworkAccessManager()

        self._username: Optional[str] = None

    @property
    def is_authenticated(self) -> bool:
        """Check if currently authenticated via QFieldSync."""
        return self._nam.is_authenticated()

    @property
    def username(self) -> Optional[str]:
        """Get authenticated username."""
        if self._username:
            return self._username
        return self._nam.get_username()

    @property
    def server_url(self) -> str:
        """Get current server URL."""
        return self._nam.server_url

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def login(self, username: str, password: str) -> bool:
        """
        Authenticate with username/password via QFieldSync.

        Args:
            username: QFieldCloud username
            password: QFieldCloud password

        Returns:
            True if login succeeded

        Raises:
            QFieldCloudAuthError: If authentication fails
        """
        try:
            reply = self._nam.login_with_credentials(username, password)
            if reply is not None:
                _wait_for_reply(reply, timeout_ms=30000)

            if self._nam.is_authenticated():
                self._username = username
                logger.info("Authenticated as '%s' via QFieldSync", username)
                return True
            else:
                error = self._nam.get_last_login_error()
                raise QFieldCloudAuthError(
                    f"Authentication failed for user '{username}'",
                    details=error or "Unknown error",
                )
        except QFieldCloudAuthError:
            raise
        except Exception as e:
            raise QFieldCloudAuthError(
                f"Authentication failed for user '{username}'",
                details=str(e),
            ) from e

    def login_with_token(self, token: str) -> bool:
        """
        Authenticate with existing token.

        Args:
            token: QFieldCloud API token

        Returns:
            True if token is valid

        Raises:
            QFieldCloudAuthError: If token is invalid
        """
        try:
            self._nam.set_token(token)
            # Validate by fetching projects (call is for its side effect on auth state)
            self._nam.get_projects_not_async()
            if self._nam.is_authenticated():
                logger.info("Authenticated with token via QFieldSync")
                return True
            raise QFieldCloudAuthError(
                "Token authentication failed",
                details="Token rejected by server",
            )
        except QFieldCloudAuthError:
            raise
        except Exception as e:
            raise QFieldCloudAuthError(
                "Token authentication failed",
                details=str(e),
            ) from e

    def auto_login(self) -> bool:
        """
        Try to auto-login using QFieldSync's stored credentials.

        Returns:
            True if already authenticated or auto-login succeeded
        """
        if self._nam.is_authenticated():
            return True

        try:
            self._nam.auto_login_attempt()
            # Wait briefly for async login to complete
            from qgis.PyQt.QtCore import QCoreApplication
            for _ in range(50):  # 5 seconds max
                QCoreApplication.processEvents()
                if self._nam.is_authenticated():
                    logger.info("Auto-login succeeded via QFieldSync")
                    return True
                time.sleep(0.1)
        except Exception as e:
            logger.debug("Auto-login failed: %s", e)

        return self._nam.is_authenticated()

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    def list_projects(self) -> List[Dict[str, Any]]:
        """
        List accessible projects (synchronous).

        Returns:
            List of project dictionaries

        Raises:
            QFieldCloudError: On API error
        """
        self._require_auth()
        try:
            return self._nam.get_projects_not_async()
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

        Returns:
            Project dict with 'id' key

        Raises:
            QFieldCloudProjectError: On creation failure
        """
        self._require_auth()
        try:
            project_owner = owner or self.username or ""
            reply = self._nam.create_project(
                name=name,
                owner=project_owner,
                description=description,
                private=not is_public,
            )
            _wait_for_reply(reply, timeout_ms=30000)
            result = self._nam.json_object(reply)
            project_id = result.get('id', '')
            logger.info("Created project '%s' (id: %s)", name, project_id)
            return result
        except Exception as e:
            raise QFieldCloudProjectError(
                f"Failed to create project '{name}'",
                details=str(e),
            ) from e

    def find_project_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a project by name."""
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

        files_to_upload = [f for f in local_dir.glob(filter_glob) if f.is_file()]

        if not files_to_upload:
            logger.warning("No files found in %s matching '%s'", local_dir, filter_glob)
            return 0

        total = len(files_to_upload)
        uploaded = 0

        for i, file_path in enumerate(files_to_upload):
            relative_path = file_path.relative_to(local_dir)

            for attempt in range(self.MAX_RETRIES):
                try:
                    # Upload single file via QFieldSync
                    uri = ["files", project_id, str(relative_path)]
                    reply = self._nam.cloud_upload_files(
                        uri=uri,
                        filenames=[str(file_path)],
                    )
                    _wait_for_reply(reply, timeout_ms=300000)

                    # Check for errors
                    self._nam.handle_response(reply, should_parse_json=False)

                    uploaded += 1
                    if progress_callback:
                        percent = int((i + 1) / total * 100)
                        progress_callback(
                            percent,
                            f"Uploaded {relative_path} ({i + 1}/{total})",
                        )
                    break

                except Exception as e:
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

        Returns:
            Job ID

        Raises:
            QFieldCloudError: On failure
        """
        self._require_auth()
        try:
            reply = self._nam.cloud_post(
                ["jobs", project_id, "package"]
            )
            _wait_for_reply(reply, timeout_ms=30000)
            result = self._nam.json_object(reply)
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

        Returns:
            Final job status dict

        Raises:
            QFieldCloudTimeoutError: If timeout exceeded
        """
        self._require_auth()
        start_time = time.time()
        last_status = ""

        while time.time() - start_time < timeout:
            try:
                reply = self._nam.cloud_get(["jobs", job_id])
                _wait_for_reply(reply, timeout_ms=30000)
                status = self._nam.json_object(reply)
                current_status = status.get('status', 'unknown')

                if current_status != last_status:
                    logger.info("Job %s status: %s", job_id, current_status)
                    last_status = current_status

                if progress_callback:
                    elapsed = int(time.time() - start_time)
                    percent = min(int(elapsed / timeout * 100), 99)
                    progress_callback(percent, f"Packaging: {current_status}")

                if current_status in ('finished', 'stopped', 'failed'):
                    return status

            except Exception as e:
                logger.warning("Job poll error: %s", e)

            time.sleep(interval)

        raise QFieldCloudTimeoutError(
            f"Job {job_id} did not finish within {timeout}s"
        )

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------

    def get_project_url(self, project_id: str) -> str:
        """Return the web URL for a project."""
        base = self._nam.server_url.rstrip('/')
        # Strip /api/v1 if present to get web URL
        if base.endswith('/api/v1'):
            base = base[:-7]
        return f"{base}/a/{project_id}"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_auth(self) -> None:
        """Raise if not authenticated."""
        if not self.is_authenticated:
            raise QFieldCloudAuthError(
                "Not authenticated. Login via QFieldSync or call login() first."
            )
