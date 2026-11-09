# -*- coding: utf-8 -*-
"""The transcript of each project, in the QGIS settings (never in the project file, which it would mark modified)."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from qgis.core import QgsProject, QgsSettings

from ...core.agent.transcript import from_json, to_json

_PREFIX = "filter_mate/agent/transcripts/"
_INDEX = "filter_mate/agent/transcripts_index"
MAX_PROJECTS = 20


def project_key() -> str:
    """A key for the open project; "" for a project never saved (nothing is kept for it)."""
    name = QgsProject.instance().fileName() or ""
    return hashlib.blake2b(name.encode("utf-8"), digest_size=10).hexdigest() if name else ""


def load(key: str) -> List[Dict[str, Any]]:
    if not key:
        return []
    return from_json(str(QgsSettings().value(_PREFIX + key, "") or ""))


def save(key: str, entries: List[Dict[str, Any]]) -> None:
    """Keep ``entries`` for this project, and only the latest projects."""
    if not key:
        return
    settings = QgsSettings()
    order = [item for item in _index(settings) if item != key]
    if entries:
        settings.setValue(_PREFIX + key, to_json(entries))
        order.append(key)
    else:
        settings.remove(_PREFIX + key)
    for stale in order[:-MAX_PROJECTS]:
        settings.remove(_PREFIX + stale)
    settings.setValue(_INDEX, json.dumps(order[-MAX_PROJECTS:]))


def _index(settings) -> List[str]:
    try:
        value = json.loads(str(settings.value(_INDEX, "[]") or "[]"))
    except ValueError:
        return []
    return [str(item) for item in value] if isinstance(value, list) else []
