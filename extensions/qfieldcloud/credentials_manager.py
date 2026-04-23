# -*- coding: utf-8 -*-
"""
Manage QFieldCloud credentials across storage tiers.

Storage split (harmonized v5.x):
- **Team-level settings** (server URL, default project, auto-package,
  default SRID, description, timeouts) live in FilterMate's ``config.json``
  under ``EXTENSIONS.qfieldcloud.*`` — portable across a team via a shared
  profile directory, editable from the Settings dialog.
- **Per-user identity** (username) goes to ``QgsSettings`` — it is user-
  specific and should not leak into a shared config.
- **Secrets** (token, password) go to the OS keyring when available, with
  a ``QgsSettings`` fallback for token (less secure but functional) and
  environment-variable overrides for CI/CD.
"""

import logging
import os
from typing import Optional, Tuple

logger = logging.getLogger('FilterMate.Extensions.QFieldCloud.Credentials')

# Default QFieldCloud URL — also used as the schema default
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
    Tiered credential + preference store for the QFieldCloud extension.

    Non-sensitive team-level settings delegate to the owning extension's
    ``get_config``/``set_config`` (FilterMate config.json). Per-user
    identity stays in QgsSettings; secrets stay in keyring.

    A one-shot ``migrate_legacy_qgssettings()`` transparently moves
    pre-v5 users' URL / default_project / auto_package entries out of
    QgsSettings into the harmonized config.
    """

    SETTINGS_PREFIX = "filtermate/qfieldcloud/"
    KEYRING_SERVICE = "filtermate-qfieldcloud"

    # Environment variable names (fallback for CI/CD)
    ENV_URL = "QFIELDCLOUD_URL"
    ENV_TOKEN = "QFIELDCLOUD_TOKEN"
    ENV_USER = "QFIELDCLOUD_USER"
    ENV_PASSWORD = "QFIELDCLOUD_PASSWORD"

    # Keys that moved from QgsSettings → FilterMate config during v5
    # Each entry is (qgssettings_key, config_key, parse_fn)
    _LEGACY_MIGRATIONS = (
        ("url", "server_url", str),
        ("default_project", "default_project", str),
        ("auto_package", "auto_package", lambda v: str(v).lower() in ("true", "1", "yes")),
    )

    def __init__(self, extension=None):
        """
        Args:
            extension: Owning ``QFieldCloudExtension`` — provides
                ``get_config``/``set_config`` for team-level settings.
                Optional (when None the manager falls back to QgsSettings
                only, preserving pre-v5 behavior for standalone tests).
        """
        self._extension = extension
        self._keyring_ok = _keyring_available()
        if not self._keyring_ok:
            logger.info(
                "keyring not available — tokens stored in QgsSettings only"
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    # Mapping from FilterMate config keys to legacy QgsSettings keys —
    # used when the manager runs without an extension (standalone tests)
    # so team-level settings round-trip through QgsSettings as before.
    _CONFIG_KEY_TO_QGSSETTINGS = {
        "server_url": "url",
        "default_project": "default_project",
        "auto_package": "auto_package",
        "default_srid": "default_srid",
        "default_description": "default_description",
        "upload_timeout_seconds": "upload_timeout_seconds",
    }

    def _read_ext_config(self, key: str, default):
        """Read a team-level setting.

        Prefers the owning extension's config store; falls back to
        QgsSettings under the legacy ``filtermate/qfieldcloud/*`` prefix
        when no extension is wired up (keeps the class usable in
        isolation for tests).
        """
        if self._extension is not None:
            try:
                return self._extension.get_config(key, default=default)
            except Exception as exc:
                logger.debug("Extension config read failed for %s: %s", key, exc)
                return default

        # Standalone fallback — QgsSettings
        qgs_key = self._CONFIG_KEY_TO_QGSSETTINGS.get(key)
        if qgs_key is None:
            return default
        try:
            from qgis.core import QgsSettings
        except Exception:
            return default
        settings = QgsSettings()
        full = self.SETTINGS_PREFIX + qgs_key
        if isinstance(default, bool):
            return settings.value(full, default, type=bool)
        if isinstance(default, int):
            try:
                return int(settings.value(full, default, type=int))
            except Exception:
                return default
        return settings.value(full, default, type=str) or default

    def _write_ext_config(self, key: str, value) -> bool:
        """Persist a team-level setting via the extension (or QgsSettings fallback)."""
        if self._extension is not None:
            try:
                return bool(self._extension.set_config(key, value))
            except Exception as exc:
                logger.warning("Extension config write failed for %s: %s", key, exc)
                return False

        qgs_key = self._CONFIG_KEY_TO_QGSSETTINGS.get(key)
        if qgs_key is None:
            return False
        try:
            from qgis.core import QgsSettings
        except Exception:
            return False
        QgsSettings().setValue(self.SETTINGS_PREFIX + qgs_key, value)
        return True

    # ------------------------------------------------------------------
    # One-shot migration of pre-v5 QgsSettings keys into config.json
    # ------------------------------------------------------------------

    def migrate_legacy_qgssettings(self) -> None:
        """
        Move legacy per-user QgsSettings entries to the extension config.

        Pre-v5 users had ``url``, ``default_project`` and ``auto_package``
        stored under ``filtermate/qfieldcloud/*`` in QgsSettings; harmonized
        v5 keeps those in FilterMate's config.json. This migration runs
        once at extension init, is idempotent (skips keys already present
        in the new store or absent from the legacy store), and removes the
        old QgsSettings entries on successful move.
        """
        if self._extension is None:
            return
        try:
            from qgis.core import QgsSettings
        except Exception:
            return
        settings = QgsSettings()
        migrated: list = []
        for qgs_key, cfg_key, parser in self._LEGACY_MIGRATIONS:
            full_key = self.SETTINGS_PREFIX + qgs_key
            if not settings.contains(full_key):
                continue
            # Skip if the user already edited the new location
            current = self._read_ext_config(cfg_key, default=None)
            if current not in (None, "", DEFAULT_URL if cfg_key == "server_url" else None):
                settings.remove(full_key)
                continue
            raw = settings.value(full_key, "", type=str)
            if raw in (None, ""):
                settings.remove(full_key)
                continue
            try:
                parsed = parser(raw)
            except Exception:
                continue
            if self._write_ext_config(cfg_key, parsed):
                settings.remove(full_key)
                migrated.append(cfg_key)
        if migrated:
            logger.info(
                "QFieldCloud: migrated legacy QgsSettings keys to config.json: %s",
                ", ".join(migrated),
            )

    # ------------------------------------------------------------------
    # URL (team-level — FilterMate config)
    # ------------------------------------------------------------------

    def get_url(self) -> str:
        """Get QFieldCloud server URL from FilterMate config (env override)."""
        # Env override wins so CI/CD can point at a staging instance
        env_url = os.environ.get(self.ENV_URL)
        if env_url:
            return env_url
        url = self._read_ext_config("server_url", default=DEFAULT_URL) or DEFAULT_URL
        return str(url)

    def set_url(self, url: str) -> None:
        """Store QFieldCloud server URL in FilterMate config."""
        self._write_ext_config("server_url", url)

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
    # Team-level preferences (FilterMate config)
    # ------------------------------------------------------------------

    def get_default_project(self) -> str:
        """Get default QFieldCloud project name from FilterMate config."""
        return str(self._read_ext_config("default_project", default="") or "")

    def set_default_project(self, project_name: str) -> None:
        """Store default project name in FilterMate config."""
        self._write_ext_config("default_project", project_name)

    def get_auto_package(self) -> bool:
        """Get auto-package preference from FilterMate config."""
        return bool(self._read_ext_config("auto_package", default=True))

    def set_auto_package(self, enabled: bool) -> None:
        """Store auto-package preference in FilterMate config."""
        self._write_ext_config("auto_package", bool(enabled))

    def get_default_srid(self) -> int:
        """Get default EPSG code for generated projects."""
        try:
            return int(self._read_ext_config("default_srid", default=4326) or 4326)
        except (TypeError, ValueError):
            return 4326

    def set_default_srid(self, srid: int) -> None:
        self._write_ext_config("default_srid", int(srid))

    def get_default_description(self) -> str:
        return str(self._read_ext_config("default_description", default="") or "")

    def set_default_description(self, description: str) -> None:
        self._write_ext_config("default_description", description)

    def get_upload_timeout_seconds(self) -> int:
        try:
            return int(self._read_ext_config("upload_timeout_seconds", default=300) or 300)
        except (TypeError, ValueError):
            return 300

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
        """Remove stored credentials and per-user identity.

        Team-level settings (server URL, default project, auto-package,
        SRID, description) are intentionally preserved — they are shared
        across the team and should survive an individual user signing
        out. Call ``set_url("")`` etc. via the Settings dialog if you
        really want to wipe those too.
        """
        from qgis.core import QgsSettings

        settings = QgsSettings()
        # Per-user identity + legacy leftovers from pre-v5
        for key in ("username", "token", "url", "default_project", "auto_package"):
            settings.remove(self.SETTINGS_PREFIX + key)

        if self._keyring_ok:
            try:
                import keyring
                keyring.delete_password(self.KEYRING_SERVICE, "token")
                keyring.delete_password(self.KEYRING_SERVICE, "password")
            except Exception:
                pass

        logger.info("QFieldCloud credentials cleared (team-level settings preserved)")
