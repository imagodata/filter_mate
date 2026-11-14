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

from dataclasses import dataclass, field, replace
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .compare_states import (UNSHOWN_EFFECTS, BeforeMap, BeforeState, Effects, from_cross_operation, from_history_entry,
                             map_with_effects)

# Effects of a turn of the agent that Compare draws (map_with_effects) or names (UNSHOWN_EFFECTS).
MAP_EFFECTS = ("style", "visibility", "added", "removed") + UNSHOWN_EFFECTS

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
        time: When it was done (a turn: when it ended), in seconds since the epoch; a step has the time of its turn,
            to be listed under it.
        label: What was done, in the words its history kept (a request, an expression).
        layers: Names of the layers it changed.
        applied: False once undone: it can be redone, and the map no longer holds it.
        count: ``"kept"`` or ``"kept / total"`` features, when its history says so.
        key: The history it comes from: the id of the source layer, the key of the agent, "" for the dock.
        position: Its rank in that history, oldest first; for a step, its rank in the turn.
        befores: The state before it of each layer it changed (empty for an item undone).
        ref: The entry or operation itself, for the host.
        started: When it began, when known and not ``time``: a turn of the agent, a step of a turn (0: ``time``).
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
    started: float = 0.0

    @property
    def begun(self) -> float:
        """When it began: an operation done after that came after it, or during it."""
        return self.started or self.time


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
            started = _seconds(getattr(operation, "started", 0)) if agent else 0.0
            items.append(TimelineItem(
                kind, when, _label(getattr(operation, "description", "")), tuple(names), applied, "", key, position,
                tuple(from_cross_operation(operation)) if applied else (), operation, started))
            steps = getattr(operation, "steps", ()) or ()
            times = _step_times(operation)
            if agent and applied and position == len(undo_stack) - 1:
                for index, (label, befores) in enumerate(steps):
                    items.append(TimelineItem(
                        KIND_STEP, when, _label(label), _names([before.layer_id for before in befores], name_of), True,
                        "", key, index, _step_befores(steps, index), operation, times[index] if times else started))
    return items


def _order(item: TimelineItem) -> Tuple[float, int, int]:
    """Newest first; a turn before its steps, and its steps in the order they ran."""
    return (-item.time, 1 if item.kind == KIND_STEP else 0, item.position if item.kind == KIND_STEP else -item.position)


def timeline(*groups: Iterable[TimelineItem]) -> List[TimelineItem]:
    """Every item of ``groups`` in one list, newest first; the steps of a turn stay under it."""
    return sorted((item for group in groups for item in group), key=_order)


def _step_times(operation: Any) -> Tuple[float, ...]:
    """When each step of a turn began, when its record says so for every step; () otherwise."""
    steps = getattr(operation, "steps", ()) or ()
    times = tuple(getattr(operation, "step_times", ()) or ())
    return times if steps and len(times) == len(steps) else ()


def _done_since(item: TimelineItem, target: TimelineItem) -> Optional[Tuple[Tuple[BeforeState, ...], List[Effects]]]:
    """What of ``item`` was done after ``target`` began: the state before it of the layers it changed then, and what it
    did beside the filters; None for nothing (``item`` came before, is undone, or is ``target`` itself).

    A turn of the agent is recorded when it ends (its ``time``) but began earlier (``started``): an operation of
    another history done meanwhile (a raster filtered through the API by the turn, a filter of the dock) finds it under
    way. Of a turn under way when ``target`` began, only the steps begun after that count, when the turn says when
    each began; when it does not (a turn of one step, a record of an earlier version), nothing of it counts: what it
    did before ``target`` was on the map then, and what it did after cannot be told apart.
    """
    if not item.applied or item.kind == KIND_STEP or item is target or _same_operation(item, target):
        return None
    if item.kind == KIND_AGENT and not (target.kind in (KIND_AGENT, KIND_STEP) and item.key == target.key):
        since = target.begun
        if item.time < since:
            return None
        if item.begun < since:  # under way when target began
            steps, times = getattr(item.ref, "steps", ()) or (), _step_times(item.ref)
            first = next((index for index, begun in enumerate(times) if begun >= since), None)
            if first is None:
                return None
            step_effects = getattr(item.ref, "step_effects", ()) or ()
            return (_step_befores(steps, first),
                    [(tuple(effect for done in step_effects[first:] for effect in done), False)])
        return item.befores, [_effects_of(item.ref)]
    if not _after(item, target):
        return None
    return item.befores, [_effects_of(item.ref)] if item.kind == KIND_AGENT else []


def _since(items: Iterable[TimelineItem], target: TimelineItem) -> List[Tuple[Tuple[BeforeState, ...], List[Effects]]]:
    """What each item did after ``target`` began, oldest first."""
    found = []
    for item in sorted(items, key=lambda other: (other.time, other.position)):
        done = _done_since(item, target)
        if done is not None:
            found.append(done)
    return found


def states_before(items: Iterable[TimelineItem], target: TimelineItem) -> List[BeforeState]:
    """The layers as they were before ``target``, among those changed since: for each, its state before the first
    item applied, at or after ``target``, that changed it, whatever history that item comes from (of a turn of the
    agent under way at ``target``, the steps begun after it: see :func:`_done_since`).

    A step counts for its turn: what follows the turn is looked at, never its other steps twice. Nothing for an item
    undone: the map no longer holds it.
    """
    if not target.applied:
        return []
    states: Dict[str, BeforeState] = {}
    for state in target.befores:
        states.setdefault(state.layer_id, state)
    for befores, _effects in _since(items, target):
        for state in befores:
            states.setdefault(state.layer_id, state)
    return list(states.values())


def _same_operation(item: TimelineItem, target: TimelineItem) -> bool:
    """A step and its turn are one operation: the turn adds nothing to what follows its step."""
    return target.kind == KIND_STEP and item.ref is not None and item.ref is target.ref


def _after(item: TimelineItem, target: TimelineItem) -> bool:
    """Was ``item`` done after ``target`` began? In one history its rank says so; across two, the clock."""
    if item.key == target.key and item.kind == target.kind:
        return item.position > target.position
    if target.kind == KIND_STEP and item.key == target.key and item.kind == KIND_AGENT:
        return item.time > target.time
    return item.time >= target.begun


def map_before(items: Sequence[TimelineItem], target: TimelineItem) -> BeforeMap:
    """The map before ``target``, for Compare: each layer changed since as it was then (:func:`states_before`), and
    what the turns of the agent did since beside the filters (a style, a layer shown, hidden, added or removed), as it
    was before the first of them.

    The turns counted are ``target`` itself (a step: the steps of its turn from that one, what "undo back to here"
    undoes) and those done after it (of a turn under way at ``target``, its steps begun after it). Empty for an item
    undone: the map no longer holds it.
    """
    if not target.applied:
        return BeforeMap(label=target.label)
    effects = []
    if target.kind == KIND_STEP:
        step_effects = getattr(target.ref, "step_effects", ()) or ()
        effects.append((tuple(effect for done in step_effects[target.position:] for effect in done), False))
    elif target.kind == KIND_AGENT:
        effects.append(_effects_of(target.ref))
    for _befores, done in _since(items, target):
        effects.extend(done)
    return map_with_effects(states_before(items, target), effects, target.label)


def agent_item(items: Iterable[TimelineItem], key: str, turn: int, step: Optional[int] = None) -> Optional[TimelineItem]:
    """The turn of the agent applied at rank ``turn`` of its history ``key`` (oldest first, as the history page of the
    agent lists it), or its step ``step``; None when ``items`` hold neither (undone since, or a step of an earlier
    turn: only those of the last turn applied are listed)."""
    found = next((item for item in items if item.kind == KIND_AGENT and item.key == key and item.applied
                  and item.position == turn), None)
    if found is None or step is None:
        return found
    return next((item for item in items if item.kind == KIND_STEP and item.key == key and item.ref is found.ref
                 and item.position == step), None)


def _draws(befores: Sequence[Any], effects: Iterable[Tuple[Any, ...]]) -> bool:
    """Whether a turn or a step changed the map as Compare draws or names it: a filter, a style, a layer shown, hidden,
    added or removed, the layer tree... (not a note, a selection, a widget or a setting)."""
    return bool(befores) or any(effect and effect[0] in MAP_EFFECTS for effect in effects)


def changes_map(operation: Any) -> bool:
    """Whether a turn of the agent (its operation) changed the map as Compare draws or names it."""
    return _draws(getattr(operation, "changes", ()) or (), getattr(operation, "effects", ()) or ())


def card_target(undo_stack: Sequence[Any], op_id: int, step: Optional[int]) -> Optional[Tuple[int, Optional[int], bool]]:
    """What the card of an action of the agent compares with (``HistoryController.compare_agent_turn``): ``(turn,
    step, exact)``, the rank of its turn in ``undo_stack`` (the turns applied, oldest first) and the rank of its step,
    or None (the whole turn); ``exact``: that is the map before the action itself.

    ``op_id``: the operation of the turn; ``step``: the rank of the action among the steps of the turn, None for a turn
    of a single step (the turn is the action). Only the steps of the last turn applied are compared one by one (as the
    history lists them): the card of a step of an earlier turn compares with the map before its whole turn, not
    exact. None when the turn is no longer applied (undone, or forgotten), or when the action changed nothing of the
    map.
    """
    rank = next((index for index, operation in enumerate(undo_stack) if getattr(operation, "op_id", None) == op_id),
                None)
    if rank is None:
        return None
    operation = undo_stack[rank]
    if step is None:
        return (rank, None, True) if changes_map(operation) else None
    steps = getattr(operation, "steps", ()) or ()
    step_effects = getattr(operation, "step_effects", ()) or ()
    if not 0 <= step < len(steps) or not _draws(steps[step][1], step_effects[step] if step < len(step_effects) else ()):
        return None
    return (rank, step, True) if rank == len(undo_stack) - 1 else (rank, None, False)


def _effects_of(operation: Any) -> Effects:
    return getattr(operation, "effects", ()) or (), bool(getattr(operation, "effects_reversed", False))


def linked_pairs(entries: Sequence[Any], source_id: str, run_ids: Sequence[Optional[int]],
                 operations: Sequence[Any]) -> List[Tuple[Any, Any]]:
    """The raster / point cloud operation each vector filter of the dock of ``source_id`` ran with, as Undo (or Redo)
    takes them together (CoverageModeController.run_vector_source_task): ``(entry, operation)`` pairs.

    ``entries``: the stack of the vector filters, the next taken last; ``run_ids``: the ``op_id`` each run of the
    source recorded (None: nothing clipped), the next taken last; ``operations``: the cross stack of the source, the
    next taken last. Each entry of the source taken takes a run, and the operation on top of the cross stack with it
    when the run recorded that one. The clock cannot pair them: each is recorded when its own task ends.
    """
    mine = [entry for entry in entries if tuple(getattr(entry, "layer_ids", ()) or ())[:1] == (source_id,)]
    stack = list(operations)
    pairs = []
    for entry, op_id in zip(reversed(mine), reversed(list(run_ids))):
        if stack and op_id is not None and getattr(stack[-1], "op_id", None) == op_id:
            pairs.append((entry, stack.pop()))
    return pairs


def link(items: Sequence[TimelineItem], pairs: Iterable[Tuple[Any, Any]]) -> List[TimelineItem]:
    """``items`` with each vector filter of ``pairs`` and the raster / point cloud operation it ran with made one step:
    the filter holds the state before of the layers of the operation too, and the operation takes the time of the
    filter. The map before either is the map before both, as Undo undoes both; each keeps its line."""
    by_ref = {id(item.ref): index for index, item in enumerate(items) if item.ref is not None}
    linked = list(items)
    for entry, operation in pairs:
        at, other = by_ref.get(id(entry)), by_ref.get(id(operation))
        if at is None or other is None:
            continue
        vector, cross = linked[at], linked[other]
        known = {state.layer_id for state in vector.befores}
        linked[at] = replace(vector, befores=vector.befores + tuple(
            state for state in cross.befores if state.layer_id not in known))
        linked[other] = replace(cross, time=vector.time, started=0.0)
    return linked


@dataclass(frozen=True)
class UndoFocus:
    """The history Undo and Redo of the action bar walk now, and what they would take.

    Attributes:
        kind: ``KIND_VECTOR``, ``KIND_COVERAGE`` or ``KIND_AGENT``; "" when they walk none (another section is open).
        undo: What Undo would undo now: an entry or an operation (a vector filter and the raster / point cloud step
            it ran with), empty when nothing.
        redo: What Redo would redo now.
        undo_left: How many steps Undo can take one after the other from here.
        redo_left: How many steps Redo can take.
        source: The name of the layer whose raster / point cloud history they walk.
    """

    kind: str = ""
    undo: Tuple[Any, ...] = ()
    redo: Tuple[Any, ...] = ()
    undo_left: int = 0
    redo_left: int = 0
    source: str = ""


def walkable(stack: Sequence[Any], takes: Callable[[Any], bool]) -> int:
    """How many entries of ``stack`` (the next one last) Undo or Redo takes one after the other: it stops at the first
    one ``takes`` refuses (a vector filter out of the scope of the current layer)."""
    count = 0
    for entry in reversed(stack):
        if not takes(entry):
            break
        count += 1
    return count


def mark(item: TimelineItem, focus: UndoFocus) -> str:
    """``"undo"`` for what Undo would undo now, ``"redo"`` for what Redo would redo, "" otherwise (a step of a turn
    is never taken alone by the action bar)."""
    if item.kind == KIND_STEP or item.ref is None:
        return ""
    if item.applied and any(item.ref is ref for ref in focus.undo):
        return "undo"
    if not item.applied and any(item.ref is ref for ref in focus.redo):
        return "redo"
    return ""


def label_of(ref: Any) -> str:
    """What an entry or an operation did, in the words its history kept (as the label of its item)."""
    return _label(getattr(ref, "description", "")) or _label(getattr(ref, "expression", ""))


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
