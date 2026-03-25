"""
API configuration.

Reads settings from environment variables, falling back to defaults.
Kept intentionally separate from the QGIS plugin config (config/config.py)
which depends on QgsApplication and QgsProject.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

# Resolve the project root (parent of filtermate_api/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class APIConfig:
    """Configuration for the FilterMate HTTP API."""

    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    log_level: str = "info"
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    project_root: Path = _PROJECT_ROOT

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
        )

    @classmethod
    def from_json(cls, path: str | Path | None = None) -> "APIConfig":
        """Load API config from a JSON file.

        Looks for an ``"API"`` key in the JSON. If absent, returns defaults.
        Falls back to ``config/config.json`` in the project root.
        """
        if path is None:
            path = _PROJECT_ROOT / "config" / "config.json"
        path = Path(path)
        if not path.exists():
            return cls()

        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)

        api_section = data.get("API", {})
        return cls(
            host=api_section.get("host", "127.0.0.1"),
            port=api_section.get("port", 8000),
            debug=api_section.get("debug", False),
            log_level=api_section.get("log_level", "info"),
            cors_origins=api_section.get("cors_origins", ["*"]),
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

        return config
