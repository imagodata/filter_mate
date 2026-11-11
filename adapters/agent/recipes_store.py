# -*- coding: utf-8 -*-
"""The recipes of the agent in the project file (an entry of ``QgsProject``), read and written here."""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

from qgis.core import QgsProject

from ...core.agent.recipes import dumps, parse

SCOPE = "FilterMateAgent"
KEY = "recipes"


def read_recipes(project=None) -> List[Dict[str, Any]]:
    project = project or QgsProject.instance()
    stored, _found = project.readEntry(SCOPE, KEY, "")
    return parse(stored)


def write_recipes(recipes: Sequence[Dict[str, Any]], project=None) -> None:
    """Keep ``recipes`` in the project: saved with it, so the project shows unsaved changes until it is."""
    project = project or QgsProject.instance()
    if list(recipes) == read_recipes(project):
        return
    if recipes:
        project.writeEntry(SCOPE, KEY, dumps(recipes))
    else:
        project.removeEntry(SCOPE, KEY)
