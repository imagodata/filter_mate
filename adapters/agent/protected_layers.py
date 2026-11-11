# -*- coding: utf-8 -*-
"""The layers the user protected from the agent, kept in the project file by their ids.

The agent reads them, uses them as a source, zooms to them, but never changes them (core/agent/permissions.py):
not in the chat, not in a recipe, not from another application through the MCP server.
"""
from __future__ import annotations

import json
from typing import List, Optional, Sequence

from qgis.core import QgsProject

SCOPE = "FilterMateAgent"
KEY = "protected_layers"


def read_ids(project=None) -> List[str]:
    project = project or QgsProject.instance()
    stored, _found = project.readEntry(SCOPE, KEY, "")
    try:
        value = json.loads(stored) if stored else []
    except (ValueError, RecursionError):
        return []
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def write_ids(ids: Sequence[str], project=None) -> None:
    """Keep ``ids`` in the project, saved with it; nothing written when nothing changes."""
    project = project or QgsProject.instance()
    wanted = sorted(set(ids))
    if wanted == sorted(read_ids(project)):
        return
    if wanted:
        project.writeEntry(SCOPE, KEY, json.dumps(wanted))
    else:
        project.removeEntry(SCOPE, KEY)


class ProjectProtection:
    """The protected layers of the open project, read at each call: the user may change them at any time."""

    def name_of(self, reference: str) -> Optional[str]:
        project = QgsProject.instance()
        ids = set(read_ids(project))
        if not ids:
            return None
        layer = project.mapLayer(reference)
        candidates = [layer] if layer is not None else project.mapLayersByName(reference)
        for candidate in candidates:
            if candidate.id() in ids:
                return candidate.name()
        return None

    def names(self) -> List[str]:
        project = QgsProject.instance()
        return [layer.name() for layer in (project.mapLayer(layer_id) for layer_id in read_ids(project))
                if layer is not None]

    def favorite_layers(self, favorite_id: str) -> List[str]:
        """The ids of the layers the favorite would change, found as applying it finds them."""
        if not read_ids():
            return []  # nothing protected: the favorite is not even read
        from ..public_api.operations import favorite_layers
        try:
            return [layer.id() for layer in favorite_layers(favorite_id)]
        except Exception:  # the favorites cannot be read now: its apply says why, nothing to protect here
            return []
