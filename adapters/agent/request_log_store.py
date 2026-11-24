# -*- coding: utf-8 -*-
"""The requests of the agent in every project (core/agent/request_log.py), in the settings of QGIS: never in a project
file, which it would mark modified, and kept from one session to the next."""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Sequence

from qgis.core import QgsProject, QgsSettings

from ...core.agent.request_log import appended, entry, from_json, to_json

KEY = "filter_mate/agent/request_log"


def load() -> List[Dict[str, Any]]:
    return from_json(str(QgsSettings().value(KEY, "") or ""))


def record(request: str, layers: Sequence[str], outcome: str) -> None:
    """Add a request of the open project, now."""
    if not str(request).strip():
        return
    project = QgsProject.instance()
    path = project.fileName() or ""
    name = project.baseName() or (os.path.splitext(os.path.basename(path))[0] if path else "")
    settings = QgsSettings()
    settings.setValue(KEY, to_json(appended(load(), entry(time.time(), request, name, path, layers, outcome))))


def clear() -> None:
    QgsSettings().remove(KEY)
