# -*- coding: utf-8 -*-
"""A new condition combined with the filter a layer already has, as the dock combines its filters.

Mirrors ``filtermate_core.domain.cross_filter.combine_subset`` (the API does not import the core): each side in
parentheses, so a clause of the previous filter never binds to the new one.
"""
from __future__ import annotations

from typing import Optional, Tuple

OPERATORS = ("AND", "OR", "AND NOT")


def combined(previous: Optional[str], new: str, operator: Optional[str]) -> Tuple[str, str]:
    """The expression to apply, and the filter it replaces (empty when it keeps or extends it).

    ``operator`` None replaces the previous filter; AND narrows it, OR widens it, AND NOT takes the new
    condition out of it. Without a previous filter the new condition applies alone, and AND NOT takes it
    out of the whole layer: ``NOT (new)`` (2026-11-12: it applied the condition, the opposite). An empty
    new condition leaves the previous filter as it is under an operator (it gave ``(previous) AND ()``).
    """
    previous = (previous or "").strip()
    new = (new or "").strip()
    if not operator:
        return new, previous
    op = operator.strip().upper()
    if op not in OPERATORS:
        raise ValueError(f"operator must be one of {', '.join(OPERATORS)}")
    if not new:
        return previous, ""
    if not previous:
        return (f"NOT ({new})" if op == "AND NOT" else new), ""
    if op == "AND NOT":
        return f"({previous}) AND NOT ({new})", ""
    return f"({previous}) {op} ({new})", ""


def current_filter(accessor, layer_name: str) -> str:
    """The subset string the layer shows now: read on the layer, else what FilterMate applied."""
    from .accessor import FilterRejected
    from .main_thread import QGISBusy
    try:
        details = accessor.describe_layer(layer_name)
    except (FilterRejected, QGISBusy):
        details = None
    if details is not None:
        return details.subset or ""
    return (accessor.get_active_filters() or {}).get(layer_name, "")
