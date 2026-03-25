#!/usr/bin/env python3
"""
Standalone launcher for the FilterMate API server.

Usage:
    python -m filtermate_api.run_api
    # or
    python filtermate_api/run_api.py

Environment variables (all optional):
    FILTERMATE_API_HOST       — bind address   (default 127.0.0.1)
    FILTERMATE_API_PORT       — bind port      (default 8000)
    FILTERMATE_API_DEBUG      — reload on change (default false)
    FILTERMATE_API_LOG_LEVEL  — log level       (default info)
"""

import uvicorn

from .config import APIConfig


def main() -> None:
    """Entry point: load config and start uvicorn."""
    config = APIConfig.load()

    uvicorn.run(
        "filtermate_api.server:app",
        host=config.host,
        port=config.port,
        log_level=config.log_level,
        reload=config.debug,
    )


if __name__ == "__main__":
    main()
