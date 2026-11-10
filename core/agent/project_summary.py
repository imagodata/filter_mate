# -*- coding: utf-8 -*-
"""The state of the project, in a few lines, sent with each request of the user.

It goes in the user's message, after the request: the cached prefix (system prompt, tools, earlier turns)
stays the same, and the model starts from what the project holds now instead of an earlier answer.
Plain Python: the caller reads the layers and selections.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

MAX_LAYERS = 30
MAX_FILTER_CHARS = 80
MAX_SELECTIONS = 10
HEADER = ("Project when this request was sent (for reference; list_layers, describe_layer and filter_state give "
          "the details):")


def _cut(text: str, size: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= size else text[:size] + "…"


def project_summary(layers: Iterable[Dict[str, Any]], selections: Iterable[Dict[str, Any]] = ()) -> str:
    """A short text: each layer with its kind, feature count and filter; the selections. Empty without layers."""
    rows = list(layers)
    if not rows:
        return ""
    lines: List[str] = [HEADER]
    for row in rows[:MAX_LAYERS]:
        parts = [str(row.get("layer_kind") or "layer")]
        count = row.get("feature_count")
        if isinstance(count, int) and count >= 0:
            parts.append(f"{count} features")
        expression = row.get("active_filter_expression") or ""
        if expression:
            parts.append(f"filter: {_cut(expression, MAX_FILTER_CHARS)}")
        lines.append(f"- {_cut(row.get('name', ''), 100)} ({', '.join(parts)})")
    if len(rows) > MAX_LAYERS:
        lines.append(f"- and {len(rows) - MAX_LAYERS} more layers")
    chosen = [item for item in selections if isinstance(item, dict)][:MAX_SELECTIONS]
    if chosen:
        lines.append("Selected: " + ", ".join(f"{_cut(item.get('name', ''), 100)} ({item.get('selected_count', 0)})"
                                              for item in chosen))
    else:
        lines.append("Selected: nothing")
    return "\n".join(lines)
