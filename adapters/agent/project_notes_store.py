# -*- coding: utf-8 -*-
"""The notes of the agent in the project file (an entry of ``QgsProject``), read and written here."""
from __future__ import annotations

import json
from typing import List, Sequence

from qgis.core import QgsProject

from ...core.agent.project_notes import parse

SCOPE = "FilterMateAgent"
KEY = "notes"


def read_notes(project=None) -> List[str]:
    project = project or QgsProject.instance()
    stored, _found = project.readEntry(SCOPE, KEY, "")
    return parse(stored)


def write_notes(notes: Sequence[str], project=None) -> None:
    """Keep ``notes`` in the project: saved with it, so the project shows unsaved changes until it is."""
    project = project or QgsProject.instance()
    if list(notes) == read_notes(project):
        return
    if notes:
        project.writeEntry(SCOPE, KEY, json.dumps(list(notes), ensure_ascii=False))
    else:
        project.removeEntry(SCOPE, KEY)
