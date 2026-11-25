# -*- coding: utf-8 -*-
"""Where the standalone application keeps its own files (standard library only).

Nothing is ever written in a QGIS profile of the user: the application has its own.
``FILTERMATE_HOME`` moves everything at once.
"""

import os
import secrets
import sys


def user_data_dir() -> str:
    """The folder of the application for this user, not created."""
    override = os.environ.get("FILTERMATE_HOME")
    if override:
        return os.path.abspath(os.path.expanduser(override))
    home = os.path.expanduser("~")
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")
        return os.path.join(base, "FilterMate")
    if sys.platform == "darwin":
        return os.path.join(home, "Library", "Application Support", "FilterMate")
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    return os.path.join(base, "filtermate")


def profile_dir() -> str:
    """The QGIS profile root of the application (settings, authentication, FilterMate's config)."""
    return os.path.join(user_data_dir(), "profile")


def log_dir() -> str:
    return os.path.join(user_data_dir(), "logs")


def cache_dir() -> str:
    """The caches Qt and its libraries write (``~/.cache`` without it), not created."""
    return os.path.join(user_data_dir(), "cache")


def grassrc_file() -> str:
    """The file GRASS reads and writes instead of ``~/.grass8`` (``GISRC``), not created."""
    return os.path.join(profile_dir(), "grassrc")


def runtime_dir() -> str:
    """Where ``filtermate setup`` installs a QGIS runtime of its own."""
    return os.path.join(user_data_dir(), "runtime")


def runtime_cache_file() -> str:
    """The runtime found by the last launch, so that the next one does not search again."""
    return os.path.join(user_data_dir(), "runtime.json")


def auth_password_file() -> str:
    """The file holding this application's own QGIS master password, created (mode 0o600).

    QGIS reads the master password from the wallet of the system under a shared key: without this file the
    application would read the master password of the real QGIS there, or ask for one it cannot ask for (no
    password box is installed: the key of the agent could never be stored, audit of 2026-11-24). Pointed by
    ``QGIS_AUTH_PASSWORD_FILE``, QGIS takes this one instead: no wallet is read, none is asked for.

    Raises:
        OSError: The file cannot be read or written (the caller runs without it, degraded).
    """
    path = os.path.join(user_data_dir(), "auth-password")
    try:
        with open(path, encoding="utf-8") as handle:
            if handle.read().strip():
                return path
    except OSError:
        pass
    os.makedirs(os.path.dirname(path), exist_ok=True)
    secret = secrets.token_urlsafe(32)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(secret)
    return path
