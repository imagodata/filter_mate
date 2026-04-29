"""
API configuration.

Reads settings from environment variables, falling back to defaults.
Kept intentionally separate from the QGIS plugin config (config/config.py)
which depends on QgsApplication and QgsProject.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

# Resolve the project root (parent of filtermate_api/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Loopback addresses considered safe for unauthenticated bind. Anything
# else (LAN, 0.0.0.0, public IP) is treated as a remote-exposed surface
# and requires either an API key or an explicit insecure-override.
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

# Env var that bypasses :meth:`APIConfig.validate`. Use only for dev/CI
# scenarios where the operator accepts the implications.
_INSECURE_OVERRIDE_ENV = "FILTERMATE_API_ALLOW_INSECURE"


class APIConfigError(RuntimeError):
    """Raised when :meth:`APIConfig.validate` rejects an insecure config."""


@dataclass
class APIConfig:
    """Configuration for the FilterMate HTTP API."""

    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    log_level: str = "info"
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    project_root: Path = _PROJECT_ROOT
    # Issue #28 — when set, every business request must carry an
    # ``X-API-Key`` header equal to this value. Empty/None ⇒ auth
    # disabled (dev mode + the health-check endpoint stays open in
    # both modes so liveness probes work).
    api_key: str | None = None

    @classmethod
    def from_env(cls) -> "APIConfig":
        """Build config from environment variables.

        Env vars (all optional):
            FILTERMATE_API_HOST     — bind address  (default 127.0.0.1)
            FILTERMATE_API_PORT     — bind port     (default 8000)
            FILTERMATE_API_DEBUG    — enable debug  (default false)
            FILTERMATE_API_LOG_LEVEL — uvicorn log level (default info)
            FILTERMATE_API_CORS_ORIGINS — comma-separated origins (default *)
        """
        cors_raw = os.getenv("FILTERMATE_API_CORS_ORIGINS", "*")
        cors_origins = [o.strip() for o in cors_raw.split(",") if o.strip()]

        return cls(
            host=os.getenv("FILTERMATE_API_HOST", "127.0.0.1"),
            port=int(os.getenv("FILTERMATE_API_PORT", "8000")),
            debug=os.getenv("FILTERMATE_API_DEBUG", "false").lower() in ("1", "true", "yes"),
            log_level=os.getenv("FILTERMATE_API_LOG_LEVEL", "info"),
            cors_origins=cors_origins,
            api_key=os.getenv("FILTERMATE_API_KEY") or None,
        )

    @classmethod
    def from_json(cls, path: str | Path | None = None) -> "APIConfig":
        """Load API config from a JSON file.

        Looks for an ``"API"`` key in the JSON. If absent, returns defaults.
        Falls back to ``config/config.json`` in the project root.

        S4 (audit 2026-04-29): when the JSON file ships an ``api_key`` in
        plaintext, we emit a one-time warning so operators see that the
        secret is sitting in a file that often syncs to Dropbox/OneDrive
        and is rarely encrypted at rest. Recommend rotating to the
        ``FILTERMATE_API_KEY`` env var (or :class:`QgsAuthManager` once
        wired). The warning is informational — config still loads.
        """
        if path is None:
            path = _PROJECT_ROOT / "config" / "config.json"
        path = Path(path)
        if not path.exists():
            return cls()

        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)

        api_section = data.get("API", {})
        api_key = api_section.get("api_key") or None

        if api_key:
            logger = logging.getLogger("filtermate_api")
            logger.warning(
                "filtermate_api.config: api_key loaded from %s in plaintext. "
                "QGIS profile dirs are commonly synced (Dropbox/OneDrive) and "
                "rarely encrypted at rest. Prefer setting FILTERMATE_API_KEY "
                "as an environment variable, or remove the key from JSON and "
                "rely on env-only configuration.",
                path,
            )

        return cls(
            host=api_section.get("host", "127.0.0.1"),
            port=api_section.get("port", 8000),
            debug=api_section.get("debug", False),
            log_level=api_section.get("log_level", "info"),
            cors_origins=api_section.get("cors_origins", ["*"]),
            api_key=api_key,
        )

    @classmethod
    def load(cls) -> "APIConfig":
        """Smart loader: env vars take priority, then JSON, then defaults.

        Strategy:
        1. Start from JSON config (if available).
        2. Override with any env vars that are explicitly set.
        """
        config = cls.from_json()

        # Override individual fields when the env var is present
        if "FILTERMATE_API_HOST" in os.environ:
            config.host = os.environ["FILTERMATE_API_HOST"]
        if "FILTERMATE_API_PORT" in os.environ:
            config.port = int(os.environ["FILTERMATE_API_PORT"])
        if "FILTERMATE_API_DEBUG" in os.environ:
            config.debug = os.environ["FILTERMATE_API_DEBUG"].lower() in ("1", "true", "yes")
        if "FILTERMATE_API_LOG_LEVEL" in os.environ:
            config.log_level = os.environ["FILTERMATE_API_LOG_LEVEL"]
        if "FILTERMATE_API_CORS_ORIGINS" in os.environ:
            raw = os.environ["FILTERMATE_API_CORS_ORIGINS"]
            config.cors_origins = [o.strip() for o in raw.split(",") if o.strip()]
        if "FILTERMATE_API_KEY" in os.environ:
            # Empty env var explicitly disables auth — distinct from "unset".
            config.api_key = os.environ["FILTERMATE_API_KEY"] or None

        return config

    @property
    def is_loopback_only(self) -> bool:
        """True when the bind address is restricted to the local machine."""
        return self.host in _LOOPBACK_HOSTS

    @property
    def has_wildcard_cors(self) -> bool:
        """True when CORS allows any origin."""
        return "*" in self.cors_origins

    def validate(self, allow_insecure: bool | None = None) -> None:
        """Reject insecure deployments before the app boots.

        Two combinations are remotely exploitable and refused:

        1. **Non-loopback bind without auth** — anything on the LAN can
           drive the QGIS session. CWE-306.
        2. **Non-loopback bind with wildcard CORS** — even with auth, a
           browser-driven CSRF can replay credentials when the user
           visits a hostile page. CWE-942.

        ``allow_insecure=True`` (or env ``FILTERMATE_API_ALLOW_INSECURE=1``)
        bypasses both rules — for tests/CI only.
        """
        if allow_insecure is None:
            allow_insecure = os.getenv(_INSECURE_OVERRIDE_ENV, "").lower() in (
                "1",
                "true",
                "yes",
            )
        if allow_insecure:
            return

        has_auth = bool(self.api_key)

        if not self.is_loopback_only and not has_auth:
            raise APIConfigError(
                f"Refusing to start: host={self.host!r} is non-loopback but "
                f"api_key is unset. Set FILTERMATE_API_KEY, bind to 127.0.0.1, "
                f"or set {_INSECURE_OVERRIDE_ENV}=1 to override (dev only)."
            )

        if not self.is_loopback_only and self.has_wildcard_cors:
            raise APIConfigError(
                f"Refusing to start: cors_origins={self.cors_origins!r} contains "
                f"a wildcard on non-loopback host {self.host!r}. Specify explicit "
                f"origins or set {_INSECURE_OVERRIDE_ENV}=1 to override (dev only)."
            )
