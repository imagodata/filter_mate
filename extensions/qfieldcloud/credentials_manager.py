# -*- coding: utf-8 -*-
"""
Manage QFieldCloud credentials with multi-level storage.

Priority order:
1. keyring (OS keychain) — for tokens and passwords
2. QgsSettings — for URL, username, preferences
3. Environment variables — fallback for CI/CD

If keyring is not available, falls back to QgsAuthManager.
"""

import logging
import os
from typing import Optional, Tuple

logger = logging.getLogger('FilterMate.Extensions.QFieldCloud.Credentials')

# Default QFieldCloud URL
DEFAULT_URL = "https://app.qfield.cloud/api/v1/"


def _keyring_available() -> bool:
    """Check if keyring module is available and functional."""
    try:
        import keyring
        # Test that keyring backend is usable (not the fail backend)
        backend = keyring.get_keyring()
        backend_name = type(backend).__name__
        if 'Fail' in backend_name or 'Null' in backend_name:
            return False
        return True
    except Exception:
        return False


class CredentialsManager:
    """
    Manage QFieldCloud credentials across storage backends.

    Non-sensitive data (URL, username, preferences) goes to QgsSettings.
    Sensitive data (token, password) goes to OS keyring if available,
    otherwise falls back to environment variables.
    """

    SETTINGS_PREFIX = "filtermate/qfieldcloud/"
    KEYRING_SERVICE = "filtermate-qfieldcloud"

    # Environment variable names (fallback for CI/CD)
    ENV_URL = "QFIELDCLOUD_URL"
    ENV_TOKEN = "QFIELDCLOUD_TOKEN"
    ENV_USER = "QFIELDCLOUD_USER"
    ENV_PASSWORD = "QFIELDCLOUD_PASSWORD"

    def __init__(self):
        self._keyring_ok = _keyring_available()
        if not self._keyring_ok:
            logger.info(
                "keyring not available — tokens stored in QgsSettings only"
            )

    # ------------------------------------------------------------------
    # URL
    # ------------------------------------------------------------------

    def get_url(self) -> str:
        """Get QFieldCloud server URL."""
        from qgis.core import QgsSettings
        url = QgsSettings().value(
            self.SETTINGS_PREFIX + "url", "", type=str
        )
        if not url:
            url = os.environ.get(self.ENV_URL, DEFAULT_URL)
        return url

    def set_url(self, url: str) -> None:
        """Store QFieldCloud server URL."""
        from qgis.core import QgsSettings
        QgsSettings().setValue(self.SETTINGS_PREFIX + "url", url)

    # ------------------------------------------------------------------
    # Username
    # ------------------------------------------------------------------

    def get_username(self) -> str:
        """Get stored username."""
        from qgis.core import QgsSettings
        username = QgsSettings().value(
            self.SETTINGS_PREFIX + "username", "", type=str
        )
        if not username:
            username = os.environ.get(self.ENV_USER, "")
        return username

    def set_username(self, username: str) -> None:
        """Store username."""
        from qgis.core import QgsSettings
        QgsSettings().setValue(self.SETTINGS_PREFIX + "username", username)

    # ------------------------------------------------------------------
    # Token (sensitive — keyring preferred)
    # ------------------------------------------------------------------

    def get_token(self) -> Optional[str]:
        """Get stored JWT token from keyring or fallback."""
        # Try keyring first
        if self._keyring_ok:
            try:
                import keyring
                token = keyring.get_password(
                    self.KEYRING_SERVICE, "token"
                )
                if token:
                    return token
            except Exception as e:
                logger.debug("keyring read failed: %s", e)

        # Fallback: QgsSettings (less secure but functional)
        from qgis.core import QgsSettings
        token = QgsSettings().value(
            self.SETTINGS_PREFIX + "token", "", type=str
        )
        if token:
            return token

        # Fallback: environment variable
        return os.environ.get(self.ENV_TOKEN) or None

    def set_token(self, token: str) -> None:
        """Store JWT token in keyring or fallback."""
        if self._keyring_ok:
            try:
                import keyring
                keyring.set_password(
                    self.KEYRING_SERVICE, "token", token
                )
                return
            except Exception as e:
                logger.warning("keyring write failed, using QgsSettings: %s", e)

        # Fallback: QgsSettings
        from qgis.core import QgsSettings
        QgsSettings().setValue(self.SETTINGS_PREFIX + "token", token)

    # ------------------------------------------------------------------
    # Password (sensitive — keyring preferred, not stored long-term)
    # ------------------------------------------------------------------

    def get_password(self) -> Optional[str]:
        """Get stored password (only from keyring or env, never QgsSettings)."""
        if self._keyring_ok:
            try:
                import keyring
                pwd = keyring.get_password(
                    self.KEYRING_SERVICE, "password"
                )
                if pwd:
                    return pwd
            except Exception:
                pass

        return os.environ.get(self.ENV_PASSWORD) or None

    def set_password(self, password: str) -> None:
        """Store password in keyring only."""
        if self._keyring_ok:
            try:
                import keyring
                keyring.set_password(
                    self.KEYRING_SERVICE, "password", password
                )
            except Exception as e:
                logger.warning("Cannot store password in keyring: %s", e)
        else:
            logger.warning(
                "keyring not available — password not persisted. "
                "Use token-based authentication instead."
            )

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------

    def get_default_project(self) -> str:
        """Get default QFieldCloud project name."""
        from qgis.core import QgsSettings
        return QgsSettings().value(
            self.SETTINGS_PREFIX + "default_project", "", type=str
        )

    def set_default_project(self, project_name: str) -> None:
        """Store default project name."""
        from qgis.core import QgsSettings
        QgsSettings().setValue(
            self.SETTINGS_PREFIX + "default_project", project_name
        )

    def get_auto_package(self) -> bool:
        """Get auto-package preference."""
        from qgis.core import QgsSettings
        return QgsSettings().value(
            self.SETTINGS_PREFIX + "auto_package", True, type=bool
        )

    def set_auto_package(self, enabled: bool) -> None:
        """Store auto-package preference."""
        from qgis.core import QgsSettings
        QgsSettings().setValue(
            self.SETTINGS_PREFIX + "auto_package", enabled
        )

    # ------------------------------------------------------------------
    # Aggregate accessors
    # ------------------------------------------------------------------

    def get_credentials(self) -> Tuple[str, str, Optional[str]]:
        """
        Get all credentials as a tuple.

        Returns:
            (url, username, token) — token may be None
        """
        return self.get_url(), self.get_username(), self.get_token()

    def has_credentials(self) -> bool:
        """Check if minimal credentials are configured.

        First checks FilterMate's own storage, then falls back to
        checking QFieldSync's stored auth (if the plugin is installed).
        """
        url = self.get_url()
        username = self.get_username()
        token = self.get_token()
        if url and username and token:
            return True

        # Fallback: check if QFieldSync has stored credentials
        return self._has_qfieldsync_credentials()

    def _has_qfieldsync_credentials(self) -> bool:
        """Check if QFieldSync plugin has stored credentials."""
        try:
            from qfieldsync.core.cloud_api import CloudNetworkAccessManager
            nam = CloudNetworkAccessManager()
            return nam.is_authenticated() or nam.has_token()
        except Exception:
            return False

    def clear(self) -> None:
        """Remove all stored credentials."""
        from qgis.core import QgsSettings

        settings = QgsSettings()
        for key in ("url", "username", "token", "default_project", "auto_package"):
            settings.remove(self.SETTINGS_PREFIX + key)

        if self._keyring_ok:
            try:
                import keyring
                keyring.delete_password(self.KEYRING_SERVICE, "token")
                keyring.delete_password(self.KEYRING_SERVICE, "password")
            except Exception:
                pass

        logger.info("QFieldCloud credentials cleared")
