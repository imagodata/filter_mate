# -*- coding: utf-8 -*-
"""The real conversation of each project (core/agent/session_io.py), in the QGIS settings.

Like the transcript (``transcript_store``): never in the project file, which it would mark modified, keyed by the
same project key, and only the latest projects kept. The transcript shows what the panel said; this remembers what
the model was told, so the discussion can be taken up again after the project reopens or QGIS restarts.
"""
from __future__ import annotations

import hashlib
import json

from qgis.core import QgsProject, QgsSettings

_PREFIX = "filter_mate/agent/sessions/"
_INDEX = "filter_mate/agent/sessions_index"
MAX_PROJECTS = 20


def project_key() -> str:
    """A key for the open project; "" for a project never saved (nothing is kept for it)."""
    name = QgsProject.instance().fileName() or ""
    return hashlib.blake2b(name.encode("utf-8"), digest_size=10).hexdigest() if name else ""


def load(key: str) -> str:
    """The stored conversation as JSON; "" when none."""
    if not key:
        return ""
    return str(QgsSettings().value(_PREFIX + key, "") or "")


def save(key: str, text: str) -> None:
    """Keep the conversation ``text`` for this project, and only the latest projects. Empty forgets it."""
    if not key:
        return
    settings = QgsSettings()
    order = [item for item in _index(settings) if item != key]
    if text:
        settings.setValue(_PREFIX + key, text)
        order.append(key)
    else:
        settings.remove(_PREFIX + key)
    for stale in order[:-MAX_PROJECTS]:
        settings.remove(_PREFIX + stale)
    settings.setValue(_INDEX, json.dumps(order[-MAX_PROJECTS:]))


def _index(settings) -> list:
    try:
        value = json.loads(str(settings.value(_INDEX, "[]") or "[]"))
    except ValueError:
        return []
    return [str(item) for item in value] if isinstance(value, list) else []
