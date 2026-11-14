# -*- coding: utf-8 -*-
"""The map before a step, for the Compare mode, from either history of FilterMate or from a pinned state.

Plain Python. The Compare mode shows the map as it was before a step, left of a swipe line, and as it is on its
right. Three histories feed Undo (agent turns, raster / point cloud operations, vector filters); two shapes come out
of them:

- a ``CrossOperation`` (agent turns, raster and point cloud filters): a pair of ``LayerSnapshot`` (before, after)
  per layer it changed; a derived raster or point cloud had another source before. A turn of the agent also keeps
  its ``effects`` (adapters/agent/turn_effects.py): a style, a layer checked or not, a layer added or removed;
- a ``HistoryEntry`` (vector filters of the dock): the subset string each layer had before.

A pin is a third way: a :class:`MapState` kept when the user pinned the map, compared with the map now.

Each becomes a :class:`BeforeMap`: :class:`BeforeState` items (what a clone of a layer needs to be drawn as it was),
the layers of the map now not drawn before, the layers hidden now drawn before, and what cannot be drawn again.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Collection, FrozenSet, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class BeforeState:
    """A layer as it was before the step. ``source`` / ``provider`` empty: the layer kept its source; ``subset``
    None: it kept its filter; ``style`` None: it kept its style."""

    layer_id: str
    subset: Optional[str] = ""
    source: str = ""
    provider: str = ""
    # The snapshot of a cross operation or of a pin (adapters/qgis/coverage_layers/snapshots.LayerSnapshot):
    # restored the way Undo restores it (vector tile style, alpha band, NoData); None for a vector filter of the dock.
    snapshot: Any = field(default=None, compare=False, repr=False)
    # The style the layer had (symbology, labels, rendering), as the XML adapters/agent/turn_effects._style writes.
    style: Optional[str] = field(default=None, repr=False)

    @property
    def other_source(self) -> bool:
        return bool(self.source)


@dataclass(frozen=True)
class BeforeMap:
    """The map before a step, as the layers of the map now are to be drawn left of the line.

    Attributes:
        states: the layers drawn as they were (another filter, source or style).
        absent: ids of layers of the map now not drawn before (added since, or hidden before).
        present: ids of layers drawn before though hidden now (unchecked since), in the order of the map before.
        missing: names of what was on the map and cannot be drawn again (a layer removed since).
        label: what the step was (the description of the operation); empty for a pin.
        pinned_at: when the state compared was pinned (a ``time.time()``), None for a step of the history.
    """

    states: Tuple[BeforeState, ...] = ()
    absent: FrozenSet[str] = frozenset()
    present: Tuple[str, ...] = ()
    missing: Tuple[str, ...] = ()
    label: str = ""
    pinned_at: Optional[float] = None

    @property
    def empty(self) -> bool:
        """Nothing to draw otherwise: the map before is the map now (a layer removed is not drawn either way)."""
        return not (self.states or self.absent or self.present)


@dataclass(frozen=True)
class LayerState:
    """One layer of the map at one moment, as a pin keeps it.

    Attributes:
        layer_id: QGIS layer id.
        name: its name then, to say it is gone.
        snapshot: its filter (``LayerSnapshot``: subset, derived source, vector tile style); None when not read.
        style: its style as XML; None when not read.
        visible: drawn then (checked in the layer tree, with its groups).
    """

    layer_id: str
    name: str = ""
    snapshot: Any = None
    style: Optional[str] = field(default=None, repr=False)
    visible: bool = False


@dataclass(frozen=True)
class MapState:
    """Every layer of the project at one moment (``taken_at``, a ``time.time()``), in the order of the layer tree."""

    layers: Tuple[LayerState, ...] = ()
    taken_at: float = 0.0


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
            before.source if source_changed else "", (before.provider or "") if source_changed else "", before))
    return _unique(states)


def map_from_history_entry(entry: Any, layer_ids: Optional[Collection[str]] = None) -> BeforeMap:
    """The map before a vector filter of the dock, for the layers of ``layer_ids`` (all of them: None)."""
    states = [state for state in from_history_entry(entry) if layer_ids is None or state.layer_id in layer_ids]
    return BeforeMap(tuple(states), label=str(getattr(entry, "description", "") or ""))


def map_from_operation(operation: Any) -> BeforeMap:
    """The map before a cross operation: its snapshots before, and what its effects changed beside the filters.

    An operation recorded by "undo back to here" holds the effects of the steps it undid (``effects_reversed``):
    undoing it applies them again, so the map before it is the map after them.
    """
    states = {state.layer_id: state for state in from_cross_operation(operation)}
    order = list(states)
    absent, present, missing = set(), [], []
    reversed_ = bool(getattr(operation, "effects_reversed", False))
    styled = set()
    for effect in getattr(operation, "effects", None) or ():
        if len(effect) < 4:
            continue
        kind, layer_id = effect[0], str(effect[1] or "")
        before = effect[3] if reversed_ else effect[2]
        if kind == "style" and layer_id and before and layer_id not in styled:
            styled.add(layer_id)  # the first one: the style before the turn touched it
            state = states.get(layer_id)
            states[layer_id] = replace(state, style=before) if state is not None else BeforeState(
                layer_id, None, style=before)
            if state is None:
                order.append(layer_id)
        elif kind == "visibility" and layer_id and bool(effect[2]) != bool(effect[3]):
            if before:
                if layer_id not in present:
                    present.append(layer_id)
                absent.discard(layer_id)
            else:
                absent.add(layer_id)
                if layer_id in present:
                    present.remove(layer_id)
        elif kind in ("added", "removed") and layer_id:
            # Added by the operation (or removed by one that undid its adding): not on the map before it.
            if (kind == "added") != reversed_:
                absent.add(layer_id)
            else:
                name = str(effect[4]) if len(effect) > 4 and effect[4] else layer_id
                if name not in missing:
                    missing.append(name)
    present = [layer_id for layer_id in present if layer_id not in absent]
    drawn = tuple(states[layer_id] for layer_id in order if layer_id not in absent)  # an absent layer needs no clone
    return BeforeMap(drawn, frozenset(absent), tuple(present), tuple(missing),
                     str(getattr(operation, "description", "") or ""))


def _filter_key(snapshot: Any) -> Tuple[str, str, str, str]:
    """What restoring a snapshot changes (``LayerSnapshot.same_state``)."""
    return tuple(str(getattr(snapshot, name, "") or "") for name in ("source", "provider", "subset", "renderer_xml"))


def map_from_pin(pinned: MapState, now: MapState) -> BeforeMap:
    """The map as it was pinned, compared with the map now: only the layers that differ are drawn otherwise.

    A layer drawn then and now is drawn as it was when its filter, source or style changed; a layer drawn then and
    hidden now is drawn too, a layer added since or hidden then is not; a layer drawn then and removed since is named
    in ``missing``. A layer hidden then and now is left alone, whatever happened to it.
    """
    current = {layer.layer_id: layer for layer in now.layers}
    states, absent, present, missing = [], set(), [], []
    for was in pinned.layers:
        layer = current.get(was.layer_id)
        if layer is None:
            if was.visible:
                missing.append(was.name or was.layer_id)
            continue
        if not was.visible:
            if layer.visible:
                absent.add(was.layer_id)
            continue
        if not layer.visible:
            present.append(was.layer_id)
        filtered = (was.snapshot is not None and layer.snapshot is not None
                    and _filter_key(was.snapshot) != _filter_key(layer.snapshot))
        styled = was.style is not None and layer.style is not None and was.style != layer.style
        if filtered or styled:
            snapshot = was.snapshot if filtered else None
            source = str(getattr(snapshot, "source", "") or "")
            moved = filtered and source != str(getattr(layer.snapshot, "source", "") or "")
            states.append(BeforeState(
                was.layer_id, str(getattr(snapshot, "subset", "") or "") if filtered else None,
                source if moved else "", str(getattr(snapshot, "provider", "") or "") if moved else "", snapshot,
                was.style if styled else None))
    pinned_ids = {layer.layer_id for layer in pinned.layers}
    absent.update(layer.layer_id for layer in now.layers if layer.visible and layer.layer_id not in pinned_ids)
    return BeforeMap(tuple(states), frozenset(absent), tuple(present), tuple(missing), pinned_at=pinned.taken_at)


def before_layer_order(drawn: Sequence[str], order: Sequence[str], absent: Collection[str],
                       present: Sequence[str]) -> List[str]:
    """The layers of the map before, top first: those drawn now (``drawn``, top first) but ``absent``, and
    ``present`` each at its place in ``order`` (the rendering order of the layer tree, top first)."""
    layers = [layer_id for layer_id in drawn if layer_id not in absent]
    rank = {layer_id: index for index, layer_id in enumerate(order)}
    for layer_id in present:
        if layer_id in layers or layer_id in absent:
            continue
        place = rank.get(layer_id)
        at = len(layers)  # unknown to the tree: at the bottom
        if place is not None:
            at = next((index for index, other in enumerate(layers) if rank.get(other, -1) > place), len(layers))
        layers.insert(at, layer_id)
    return layers
