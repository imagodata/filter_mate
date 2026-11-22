# -*- coding: utf-8 -*-
"""Where the standalone application keeps its own files (standard library only).

Nothing is ever written in a QGIS profile of the user: the application has its own.
``FILTERMATE_HOME`` moves everything at once.
"""

import os
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


def runtime_dir() -> str:
    """Where ``filtermate setup`` installs a QGIS runtime of its own."""
    return os.path.join(user_data_dir(), "runtime")


def runtime_cache_file() -> str:
    """The runtime found by the last launch, so that the next one does not search again."""
    return os.path.join(user_data_dir(), "runtime.json")
