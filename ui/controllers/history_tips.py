# -*- coding: utf-8 -*-
"""The tooltips of Undo and Redo of the action bar: what they would undo or redo, in which history, how far.

Undo walks one of three histories, depending on what is open (FilterMateApp.update_undo_redo_buttons): the turns of
the agent, the raster / point cloud filters of the current source, the vector filters of the dock. One composition
for the three, so that the agent says it the way the others do (ui/controllers/history_controller.py,
ui/controllers/agent_chat_controller.py).
"""
from __future__ import annotations

from qgis.PyQt.QtCore import QCoreApplication

from ...core.domain.history_timeline import KIND_AGENT, KIND_COVERAGE, KIND_VECTOR

LABEL_LENGTH = 80  # what the step did, on one line of the tooltip


def _tr(text: str) -> str:
    return QCoreApplication.translate("FilterMateDockWidget", text)


def _short(label: str) -> str:
    text = " ".join((label or "").split())
    return text if len(text) <= LABEL_LENGTH else text[:LABEL_LENGTH - 1].rstrip() + "…"


def history_name(kind: str, source: str = "") -> str:
    """The history Undo walks, as the tooltip and the history panel name it; "" for none."""
    if kind == KIND_AGENT:
        return _tr("turns of the agent")
    if kind == KIND_COVERAGE:
        return _tr("raster / point cloud filters of {}").format(source) if source else _tr("raster / point cloud filters")
    if kind == KIND_VECTOR:
        return _tr("vector filters of the dock")
    return ""


def button_tip(undo: bool, label: str = "", kind: str = "", left: int = 0, source: str = "") -> str:
    """The tooltip of Undo (``undo``) or Redo.

    Args:
        undo: Undo, or Redo.
        label: What the click would undo or redo; "" when it can do nothing.
        kind: The history it walks (``KIND_VECTOR``, ``KIND_COVERAGE``, ``KIND_AGENT``), "" for none.
        left: How many steps it can take one after the other from here.
        source: The layer of a raster / point cloud history.
    """
    if label:
        lines = [(_tr("Undo: {}") if undo else _tr("Redo: {}")).format(_short(label))]
    else:
        lines = [_tr("Nothing to undo.") if undo else _tr("Nothing to redo.")]
    name = history_name(kind, source)
    if name:
        lines.append(_tr("History: {}").format(name))
    if label and left > 0:
        lines.append((_tr("Steps to undo: {}") if undo else _tr("Steps to redo: {}")).format(left))
    lines.append(_tr("Right-click: the history of the project"))
    return "\n".join(lines)
