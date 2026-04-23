# -*- coding: utf-8 -*-
"""
Resolve the "current user" identity used to stamp ``owner`` on favorites.

Cascade (first non-empty wins):

    1. ``APP.USER_IDENTITY`` in FilterMate config.json — explicit override
       set by IT or the user. Authoritative.
    2. ``QgsSettings().value("qgis/userName")`` — QGIS' built-in "name"
       field under Settings → Options → System.
    3. OS user: ``os.getlogin()`` (falls back to ``getpass.getuser()``
       in headless / detached sessions).

When every step returns empty (rare — a CI container with no login shell,
no QGIS config, and an empty config file), identity stays ``None`` and
new favorites are written with ``owner = NULL`` (= shared with every
user on this DB).

Callers should treat the return value as the *string literal* to stamp
into SQLite. Case is preserved. Whitespace is trimmed.
"""

from __future__ import annotations

import getpass
import logging
import os
from typing import Optional

logger = logging.getLogger('FilterMate.UserIdentity')


def _from_config() -> Optional[str]:
    """Read ``APP.USER_IDENTITY`` (wrapped or raw) from ENV_VARS."""
    try:
        from filter_mate.config.config import ENV_VARS, _get_option_value
    except Exception:
        return None
    data = ENV_VARS.get("CONFIG_DATA") or {}
    app = data.get("APP") if isinstance(data, dict) else None
    if not isinstance(app, dict):
        return None
    value = _get_option_value(app.get("USER_IDENTITY"), default="")
    value = str(value or "").strip()
    return value or None


def _from_qgis_settings() -> Optional[str]:
    """Read QGIS' built-in ``qgis/userName`` setting."""
    try:
        from qgis.core import QgsSettings
    except Exception:
        return None
    try:
        value = QgsSettings().value("qgis/userName", "", type=str)
    except Exception:
        return None
    value = str(value or "").strip()
    return value or None


def _from_os() -> Optional[str]:
    """Best-effort OS user — ``os.getlogin`` then ``getpass.getuser``."""
    for fn in (os.getlogin, getpass.getuser):
        try:
            value = fn()
        except Exception:
            continue
        value = str(value or "").strip()
        if value:
            return value
    return None


def resolve_current_user(*, use_cache: bool = True) -> Optional[str]:
    """Return the identity used to stamp new favorites' ``owner``.

    Args:
        use_cache: When True (default), subsequent calls reuse the first
            resolved value for the process lifetime. The cache is
            invalidated by ``invalidate_identity_cache()`` — call it
            after the user edits ``APP.USER_IDENTITY`` via the settings
            UI so the new value takes effect without a QGIS restart.

    Returns:
        User identity string, or ``None`` when all cascade steps fail.
    """
    global _CACHED
    if use_cache and _CACHED[0]:
        return _CACHED[1]

    for step in (_from_config, _from_qgis_settings, _from_os):
        value = step()
        # Defensive strip: a step may return whitespace if it has a bug
        # or a mock feeds it one. Canonical identities never carry
        # leading/trailing whitespace.
        if isinstance(value, str):
            value = value.strip() or None
        if value:
            if use_cache:
                _CACHED = (True, value)
            logger.debug("resolve_current_user: picked '%s' from %s", value, step.__name__)
            return value

    if use_cache:
        _CACHED = (True, None)
    logger.debug("resolve_current_user: cascade exhausted, identity is None")
    return None


def invalidate_identity_cache() -> None:
    """Force the next ``resolve_current_user`` call to re-read the cascade."""
    global _CACHED
    _CACHED = (False, None)


# Module-level cache: (is_populated, value_or_None)
_CACHED: "tuple[bool, Optional[str]]" = (False, None)
