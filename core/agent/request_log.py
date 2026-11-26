# -*- coding: utf-8 -*-
"""The requests of the agent in every project, for the tab "All projects" of its history (2026-11-24).

The history of a project lists its turns while it is open (the undo stack of FilterMate); this log keeps, across
projects and sessions, what was asked, where, when, and what it changed. Pure Python: the adapter stores it in the
settings of QGIS (adapters/agent/request_log_store.py), never in a project file.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence

MAX_ENTRIES = 300
MAX_REQUEST = 500  # characters of a request shown in the history
MAX_STORED = 4000  # characters of a request kept: "Send again" resends what was asked, not its first lines
MAX_LAYERS = 12
OUTCOMES = ("changed", "unchanged", "stopped", "failed")


def short(request: str) -> str:
    """A request as the history shows it: the first lines, with an ellipsis when the rest stays out of sight."""
    text = str(request or "")
    return text if len(text) <= MAX_REQUEST else text[:MAX_REQUEST] + "…"


def entry(when: float, request: str, project: str, path: str, layers: Sequence[str], outcome: str) -> Dict[str, Any]:
    """One request: when (seconds since the epoch), the request, the project (its name and its file), the layers it
    changed, and how it ended (one of OUTCOMES)."""
    return {"time": float(when), "request": str(request)[:MAX_STORED], "project": str(project), "path": str(path),
            "layers": [str(name) for name in list(layers)[:MAX_LAYERS]],
            "outcome": outcome if outcome in OUTCOMES else "unchanged"}


def appended(entries: Sequence[Dict[str, Any]], new: Dict[str, Any], limit: int = MAX_ENTRIES) -> List[Dict[str, Any]]:
    """``entries`` with ``new`` at the end, the oldest dropped beyond ``limit``."""
    return [*entries, new][-limit:] if limit > 0 else []


def to_json(entries: Sequence[Dict[str, Any]]) -> str:
    return json.dumps(list(entries), ensure_ascii=False)


def from_json(text: str) -> List[Dict[str, Any]]:
    """The entries of a stored text; what is not an entry is left out (a text of another version, edited by hand)."""
    try:
        value = json.loads(text or "[]")
    except ValueError:
        return []
    if not isinstance(value, list):
        return []
    kept = []
    for item in value:
        if not isinstance(item, dict) or not str(item.get("request") or "").strip():
            continue
        try:
            kept.append(entry(float(item.get("time") or 0), item["request"], item.get("project") or "",
                              item.get("path") or "", item.get("layers") or (), str(item.get("outcome") or "")))
        except (TypeError, ValueError):
            continue
    return kept[-MAX_ENTRIES:]
