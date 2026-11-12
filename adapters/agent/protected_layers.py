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


def read_ids(project=None, strict: bool = False) -> List[str]:
    """The ids kept in the project. An entry that cannot be read (cut, not a list of texts) raises ValueError when
    ``strict`` (what the agent is refused by), and reads as what it holds of ids otherwise (what the settings show).
    """
    project = project or QgsProject.instance()
    stored, _found = project.readEntry(SCOPE, KEY, "")
    try:
        value = json.loads(stored) if stored else []
    except (ValueError, RecursionError):
        value = None
    readable = isinstance(value, list) and all(isinstance(item, str) for item in value)
    if strict and not readable:
        raise ValueError("the layers protected from the agent cannot be read in this project")
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def write_ids(ids: Sequence[str], project=None) -> None:
    """Keep ``ids`` in the project, saved with it; nothing written when nothing changes, an entry that cannot be read
    written again."""
    project = project or QgsProject.instance()
    wanted = sorted(set(ids))
    try:
        current = sorted(read_ids(project, strict=True))
    except ValueError:
        current = None
    if wanted == current:
        return
    if wanted:
        project.writeEntry(SCOPE, KEY, json.dumps(wanted))
    else:
        project.removeEntry(SCOPE, KEY)


class ProjectProtection:
    """The protected layers of the open project, read at each call: the user may change them at any time.

    An entry that cannot be read raises: the policy refuses the change (PROTECTION_UNREADABLE).
    """

    def name_of(self, reference: str) -> Optional[str]:
        project = QgsProject.instance()
        ids = set(read_ids(project, strict=True))
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
        return [layer.name() for layer in (project.mapLayer(layer_id) for layer_id in read_ids(project, strict=True))
                if layer is not None]

    def favorite_layers(self, favorite_id: str) -> List[str]:
        """The ids of the layers the favorite would change, found as applying it finds them.

        Raises whatever stops the favorites from being read: the policy then refuses the favorite, never runs it
        unchecked.
        """
        if not read_ids(strict=True):
            return []  # nothing protected: the favorite is not even read
        from ..public_api.operations import favorite_layers
        return [layer.id() for layer in favorite_layers(favorite_id)]

    def theme_layers(self, name: str) -> List[str]:
        """The ids of the layers applying the map theme ``name`` would restyle (current style, legend items)."""
        if not read_ids(strict=True):
            return []  # nothing protected: the theme is not even read
        from ..public_api.layer_tree import theme_changed_layers
        return theme_changed_layers(name)
