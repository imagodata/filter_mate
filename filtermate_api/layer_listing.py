# -*- coding: utf-8 -*-
"""The layer list a model reads: only the layers it asks for, and long filters cut to what it needs.

Shared by the chat tools and the MCP server; plain Python, no QGIS.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

MAX_FILTER_CHARS = 200  # a filter shown in a list; describe_layer gives it whole, for one layer
DEFAULT_LIMIT = 200
MAX_LIMIT = 500


def short_filter(row: Dict[str, Any], key: str) -> Dict[str, Any]:
    """``row`` with ``key`` cut to MAX_FILTER_CHARS, and its full length beside it when it was cut."""
    text = row.get(key)
    if not isinstance(text, str) or len(text) <= MAX_FILTER_CHARS:
        return row
    return {**row, key: text[:MAX_FILTER_CHARS] + "…", f"{key}_length": len(text)}


def select_layers(rows: Iterable[Dict[str, Any]], kind: Optional[str] = None, name_contains: Optional[str] = None,
                  limit: Optional[int] = None) -> Dict[str, Any]:
    """``{"layers": [...]}`` of the rows that match, at most ``limit``, with how many matched in all."""
    wanted = (name_contains or "").casefold().strip()
    matched: List[Dict[str, Any]] = [
        short_filter(row, "active_filter_expression") for row in rows
        if (not kind or row.get("layer_kind") == kind) and (not wanted or wanted in str(row.get("name", "")).casefold())]
    count = min(max(int(limit or DEFAULT_LIMIT), 1), MAX_LIMIT)
    answer: Dict[str, Any] = {"layers": matched[:count]}
    if len(matched) > count:
        answer["more"] = len(matched) - count
        answer["note"] = "More layers match: narrow with kind or name_contains, or raise limit."
    return answer
