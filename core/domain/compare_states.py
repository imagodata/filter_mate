# -*- coding: utf-8 -*-
"""The state of each layer before a filter operation, for the Compare mode, from either history of FilterMate.

Plain Python. The Compare mode shows the map as it was before the operation Undo would undo, left of a swipe line,
and as it is on its right. Three histories feed Undo (agent turns, raster / point cloud operations, vector
filters); two shapes come out of them:

- a ``CrossOperation`` (agent turns, raster and point cloud filters): a pair of ``LayerSnapshot`` (before, after)
  per layer it changed; a derived raster or point cloud had another source before;
- a ``HistoryEntry`` (vector filters of the dock): the subset string each layer had before.

Both become :class:`BeforeState` items: what a clone of the layer needs to be drawn as it was.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List


@dataclass(frozen=True)
class BeforeState:
    """A layer as it was before the operation. ``source`` / ``provider`` empty: the layer kept its source."""

    layer_id: str
    subset: str = ""
    source: str = ""
    provider: str = ""

    @property
    def other_source(self) -> bool:
        return bool(self.source)


def _unique(states: Iterable[BeforeState]) -> List[BeforeState]:
    """The first state of each layer: an operation that changed a layer twice keeps its state before both."""
    seen, kept = set(), []
    for state in states:
        if state.layer_id and state.layer_id not in seen:
            seen.add(state.layer_id)
            kept.append(state)
    return kept


def from_history_entry(entry: Any) -> List[BeforeState]:
    """States before a vector filter of the dock (``HistoryEntry.previous_filters``)."""
    pairs = getattr(entry, "previous_filters", None) or ()
    return _unique(BeforeState(str(layer_id), str(subset or "")) for layer_id, subset in pairs)


def from_cross_operation(operation: Any) -> List[BeforeState]:
    """States before a cross operation (an agent turn, a raster / point cloud filter): its snapshots before."""
    states = []
    for before, after in getattr(operation, "changes", None) or ():
        source_changed = bool(before.source) and before.source != getattr(after, "source", None)
        states.append(BeforeState(
            before.layer_id, str(before.subset or ""),
            before.source if source_changed else "", (before.provider or "") if source_changed else ""))
    return _unique(states)
