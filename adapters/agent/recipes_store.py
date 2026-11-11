# -*- coding: utf-8 -*-
"""The recipes of the agent in the project file (an entry of ``QgsProject``), read and written here."""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

import hashlib
import json

from qgis.core import QgsProject, QgsSettings

from ...core.agent.recipes import dumps, fingerprint, parse

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


# The live recipes the user turned on here, on this computer: a project made by someone else may say a recipe is live,
# but it runs at every save only once the user ticked it for these very steps (``fingerprint``).
APPROVALS_KEY = "filter_mate/agent/live_recipes"
MAX_APPROVALS = 200


def _approval(project_key: str, recipe) -> str:
    return hashlib.sha256(f"{project_key}\n{recipe['id']}\n{fingerprint(recipe)}".encode("utf-8")).hexdigest()[:32]


def _approvals():
    try:
        value = json.loads(QgsSettings().value(APPROVALS_KEY, "[]") or "[]")
    except (TypeError, ValueError):
        return []
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def live_approved(project_key: str, recipe) -> bool:
    return _approval(project_key, recipe) in _approvals()


def approve_live(project_key: str, recipe, on: bool) -> None:
    key = _approval(project_key, recipe)
    kept = [item for item in _approvals() if item != key] + ([key] if on else [])
    QgsSettings().setValue(APPROVALS_KEY, json.dumps(kept[-MAX_APPROVALS:]))
