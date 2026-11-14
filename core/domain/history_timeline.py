# -*- coding: utf-8 -*-
"""One list of what was done to the project, from the three histories of FilterMate, newest first.

Plain Python. Undo reads a different history depending on what is open (the turns of the agent while AGENT is open,
the raster / point cloud operations of the current source, the vector filters of the dock otherwise), and nothing
showed which one, nor what it held. The three do not have the same shape:

- the vector filters of the dock: one stack of ``HistoryEntry`` for the whole dock (core/services/history_service.py),
  each with the subset every layer had before;
- the raster / point cloud / vector tile operations: one stack of ``CrossOperation`` per source layer
  (filtermate_core/domain/filter_state.CrossOperationHistory), each with a pair of snapshots per layer it changed;
- the turns of the agent: ``CrossOperation`` too, in a history of its own, under one key, with the steps of a turn.

Here each becomes a :class:`TimelineItem`, with the state before it of the layers it changed, so that the map can
be drawn as it was before any of them, whatever history it comes from (:func:`states_before`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .compare_states import BeforeState, from_cross_operation, from_history_entry

KIND_VECTOR = "vector"
KIND_COVERAGE = "coverage"
KIND_AGENT = "agent"
KIND_STEP = "step"
KINDS = (KIND_VECTOR, KIND_COVERAGE, KIND_AGENT, KIND_STEP)
MAX_LABEL = 200

NameOf = Callable[[str], str]


@dataclass(frozen=True)
class TimelineItem:
    """One thing done: a filter of the dock, a raster / point cloud operation, a turn of the agent or one of its steps.

    Attributes:
        kind: One of ``KINDS``.
        time: When, in seconds since the epoch (a step has the time of its turn).
        label: What was done, in the words its history kept (a request, an expression).
        layers: Names of the layers it changed.
        applied: False once undone: it can be redone, and the map no longer holds it.
        count: ``"kept"`` or ``"kept / total"`` features, when its history says so.
        key: The history it comes from: the id of the source layer, the key of the agent, "" for the dock.
        position: Its rank in that history, oldest first; for a step, its rank in the turn.
        befores: The state before it of each layer it changed (empty for an item undone).
        ref: The entry or operation itself, for the host.
    """

    kind: str
    time: float
    label: str
    layers: Tuple[str, ...] = ()
    applied: bool = True
    count: str = ""
    key: str = ""
    position: int = 0
    befores: Tuple[BeforeState, ...] = field(default=(), compare=False, repr=False)
    ref: Any = field(default=None, compare=False, repr=False)


def _label(text: Any) -> str:
    return " ".join(str(text or "").split())[:MAX_LABEL]


def _names(layer_ids: Iterable[str], name_of: NameOf) -> Tuple[str, ...]:
    names: List[str] = []
    for layer_id in layer_ids:
        name = name_of(layer_id) or layer_id
        if name not in names:
            names.append(name)
    return tuple(names)


def _seconds(moment: Any) -> float:
    """A ``datetime`` or a number of seconds, as seconds; 0 when neither."""
    stamp = getattr(moment, "timestamp", None)
    try:
        return float(stamp() if callable(stamp) else moment)
    except (TypeError, ValueError, OverflowError, OSError):
        return 0.0


def _entry_count(entry: Any) -> str:
    """The features a vector filter kept on its source, as its entry recorded them."""
    get = getattr(entry, "get_metadata_value", None)
    if not callable(get):
        return ""
    for key in ("source_feature_count", "feature_count"):
        value = get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return str(value)
    return ""


def vector_items(undo_stack: Sequence[Any], redo_stack: Sequence[Any], name_of: NameOf) -> List[TimelineItem]:
    """The vector filters of the dock: ``undo_stack`` oldest first, ``redo_stack`` with the next to redo last."""
    items = []
    for applied, stack in ((True, undo_stack), (False, redo_stack)):
        for position, entry in enumerate(stack):
            layer_ids = tuple(str(layer_id) for layer_id in getattr(entry, "layer_ids", ()) or ())
            label = _label(getattr(entry, "description", "")) or _label(getattr(entry, "expression", ""))
            items.append(TimelineItem(
                KIND_VECTOR, _seconds(getattr(entry, "timestamp", 0)), label, _names(layer_ids, name_of), applied,
                _entry_count(entry), "", position, tuple(from_history_entry(entry)) if applied else (), entry))
    return items


def _step_befores(steps: Sequence[Tuple[str, Sequence[Any]]], step: int) -> Tuple[BeforeState, ...]:
    """The layers as they were before the step ``step`` of a turn: for each, its state before the first step at or
    after it that changed it (what "undo back to here" restores)."""
    states: Dict[str, BeforeState] = {}
    for _label_of_step, befores in steps[step:]:
        for before in befores:
            states.setdefault(before.layer_id, BeforeState(
                before.layer_id, str(getattr(before, "subset", "") or ""), snapshot=before))
    return tuple(states.values())


def cross_items(key: str, undo_stack: Sequence[Any], redo_stack: Sequence[Any], name_of: NameOf,
                agent: bool = False) -> List[TimelineItem]:
    """The operations of one cross history (a source layer, or the agent): ``undo_stack`` oldest first, ``redo_stack``
    with the next to redo last. The steps of the last turn of the agent applied follow it, as "undo back to here"
    only reaches those."""
    kind = KIND_AGENT if agent else KIND_COVERAGE
    items = []
    for applied, stack in ((True, undo_stack), (False, redo_stack)):
        for position, operation in enumerate(stack):
            layer_ids = [before.layer_id for before, _after in getattr(operation, "changes", ()) or ()]
            names = list(_names(layer_ids, name_of))
            for effect in getattr(operation, "effects", ()) or ():  # a layer the turn added, restyled, removed...
                if len(effect) > 4 and isinstance(effect[4], str) and effect[4] and effect[4] not in names:
                    names.append(effect[4])
            when = _seconds(getattr(operation, "timestamp", 0))
            items.append(TimelineItem(
                kind, when, _label(getattr(operation, "description", "")), tuple(names), applied, "", key, position,
                tuple(from_cross_operation(operation)) if applied else (), operation))
            steps = getattr(operation, "steps", ()) or ()
            if agent and applied and position == len(undo_stack) - 1:
                for index, (label, befores) in enumerate(steps):
                    items.append(TimelineItem(
                        KIND_STEP, when, _label(label), _names([before.layer_id for before in befores], name_of), True,
                        "", key, index, _step_befores(steps, index), operation))
    return items


def _order(item: TimelineItem) -> Tuple[float, int, int]:
    """Newest first; a turn before its steps, and its steps in the order they ran."""
    return (-item.time, 1 if item.kind == KIND_STEP else 0, item.position if item.kind == KIND_STEP else -item.position)


def timeline(*groups: Iterable[TimelineItem]) -> List[TimelineItem]:
    """Every item of ``groups`` in one list, newest first; the steps of a turn stay under it."""
    return sorted((item for group in groups for item in group), key=_order)


def states_before(items: Iterable[TimelineItem], target: TimelineItem) -> List[BeforeState]:
    """The layers as they were before ``target``, among those changed since: for each, its state before the first
    item applied, at or after ``target``, that changed it, whatever history that item comes from.

    A step counts for its turn: what follows the turn is looked at, never its other steps twice. Nothing for an item
    undone: the map no longer holds it.
    """
    if not target.applied:
        return []
    states: Dict[str, BeforeState] = {}
    for state in target.befores:
        states.setdefault(state.layer_id, state)
    later = [item for item in items if item.applied and item.kind != KIND_STEP and item is not target
             and not _same_operation(item, target) and _after(item, target)]
    for item in sorted(later, key=lambda other: (other.time, other.position)):
        for state in item.befores:
            states.setdefault(state.layer_id, state)
    return list(states.values())


def _same_operation(item: TimelineItem, target: TimelineItem) -> bool:
    """A step and its turn are one operation: the turn adds nothing to what follows its step."""
    return target.kind == KIND_STEP and item.ref is not None and item.ref is target.ref


def _after(item: TimelineItem, target: TimelineItem) -> bool:
    """Was ``item`` done after ``target``? In one history its rank says so; across two, the clock."""
    if item.key == target.key and item.kind == target.kind:
        return item.position > target.position
    if target.kind == KIND_STEP and item.key == target.key and item.kind == KIND_AGENT:
        return item.time > target.time
    return item.time >= target.time


def counts(items: Iterable[TimelineItem]) -> Tuple[int, int]:
    """``(to undo, to redo)`` among ``items``, the steps of a turn left out."""
    done = undone = 0
    for item in items:
        if item.kind == KIND_STEP:
            continue
        if item.applied:
            done += 1
        else:
            undone += 1
    return done, undone


def latest(items: Iterable[TimelineItem], applied: bool = True) -> Optional[TimelineItem]:
    """The newest item applied (or undone), steps left out; None when there is none."""
    found = [item for item in items if item.kind != KIND_STEP and item.applied == applied]
    return min(found, key=_order) if found else None
