# -*- coding: utf-8 -*-
"""
Filter state of a layer of any kind, and the history of cross filters.

A vector layer is filtered by its subset string. A raster target is filtered
by swapping its data source for a derived one (clipped VRT); a point cloud
target by a derived file and/or a subset string. ``LayerSnapshot`` captures
what is needed to put a layer back as it was; ``CrossOperationHistory``
groups the snapshots of one FILTERING run so undo / redo restore every layer
touched together.

This is a PURE PYTHON module with NO QGIS dependencies.
"""
from dataclasses import dataclass, field, asdict, replace
from typing import Callable, Dict, List, NamedTuple, Optional, Tuple
import itertools
import time


@dataclass(frozen=True)
class LayerSnapshot:
    """What a layer looked like at one point in time.

    Attributes:
        layer_id: QGIS layer id.
        kind: ``vector``, ``raster`` or ``point_cloud``.
        source: Data source URI.
        provider: Provider key.
        subset: Subset string ("" when none or unsupported).
        derived: True when ``source`` is a FilterMate derived file.
        original_source: Source before FilterMate derived anything (for derived layers).
        original_provider: Provider before FilterMate derived anything.
        geometry_wkt: Area kept by a clipped layer, when known.
        side: ``inside`` / ``outside`` for a derived layer.
        nodata: User NoData value of a derived raster (virtual raster selection).
        enriched_source: Source a layer was enriched from (point cloud with a
            HeightAboveGround dimension): ``original_source`` is then the
            enriched file, which Unfilter keeps, and this is what unloading
            the plugin or saving the project goes back to.
        enriched_provider: Provider of ``enriched_source``.
        renderer_xml: Complete portable tile style, including labeling.
        original_renderer_xml: Tile style before the first FilterMate filter.
        tile_filter: Display expression, kept apart from original style rules.
        bounded_enrichment: HAG covers only its useful area; Unfilter must
            restore the pristine cloud instead of keeping the enriched crop.
        selection: JSON of the :class:`RasterSelection` a raster source keeps
            (virtual raster), to rebuild it when the project is opened again.
    """

    layer_id: str
    kind: str
    source: str = ""
    provider: str = ""
    subset: str = ""
    derived: bool = False
    original_source: str = ""
    original_provider: str = ""
    geometry_wkt: str = ""
    side: str = ""
    nodata: Optional[float] = None
    enriched_source: str = ""
    enriched_provider: str = ""
    selection: str = ""
    renderer_xml: str = ""
    original_renderer_xml: str = ""
    tile_filter: str = ""
    bounded_enrichment: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "LayerSnapshot":
        known = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
        return cls(**known)

    @property
    def base_source(self) -> str:
        """Source to derive from: the original one for a derived layer."""
        return self.original_source if self.derived and self.original_source else self.source

    @property
    def base_provider(self) -> str:
        """Provider of :attr:`base_source`."""
        return self.original_provider if self.derived and self.original_provider else self.provider

    @property
    def pristine_source(self) -> str:
        """Source before any FilterMate change (enrichment included)."""
        return self.enriched_source or self.base_source

    @property
    def pristine_provider(self) -> str:
        return self.enriched_provider or self.base_provider

    def same_state(self, other: "LayerSnapshot") -> bool:
        """True when restoring ``other`` would not change anything."""
        return (self.source, self.provider, self.subset, self.renderer_xml) == (
            other.source, other.provider, other.subset, other.renderer_xml)


_op_counter = itertools.count(1)


@dataclass(frozen=True)
class CrossOperation:
    """One FILTERING run: the before/after snapshots of every layer it changed."""

    source_layer_id: str
    changes: Tuple[Tuple[LayerSnapshot, LayerSnapshot], ...]
    description: str = ""
    op_id: int = field(default_factory=lambda: next(_op_counter))
    timestamp: float = field(default_factory=time.time)

    @property
    def layer_ids(self) -> Tuple[str, ...]:
        return tuple(before.layer_id for before, _ in self.changes)


class DroppedStep(NamedTuple):
    """An operation forgotten by :meth:`CrossOperationHistory.drop_oldest`."""

    operation: CrossOperation
    from_undo: bool  # False: the furthest step of a redo stack


class CrossOperationHistory:
    """Undo / redo stacks of cross filter operations, per source layer.

    Kept apart from the vector ``HistoryService`` on purpose: its entries only
    know subset strings, while a cross operation restores data sources too.
    """

    def __init__(self, max_depth: int = 50) -> None:
        self._max_depth = max(1, int(max_depth))
        self._undo: Dict[str, List[CrossOperation]] = {}
        self._redo: Dict[str, List[CrossOperation]] = {}

    def push(self, operation: CrossOperation) -> None:
        """Record a new operation; it clears the redo stack of its source."""
        if not operation.changes:
            return
        stack = self._undo.setdefault(operation.source_layer_id, [])
        stack.append(operation)
        if len(stack) > self._max_depth:
            del stack[0]
        self._redo[operation.source_layer_id] = []

    def can_undo(self, source_layer_id: str) -> bool:
        return bool(self._undo.get(source_layer_id))

    def can_redo(self, source_layer_id: str) -> bool:
        return bool(self._redo.get(source_layer_id))

    def peek_undo(self, source_layer_id: str) -> Optional[CrossOperation]:
        stack = self._undo.get(source_layer_id) or []
        return stack[-1] if stack else None

    def peek_redo(self, source_layer_id: str) -> Optional[CrossOperation]:
        stack = self._redo.get(source_layer_id) or []
        return stack[-1] if stack else None

    def undo(self, source_layer_id: str) -> Optional[CrossOperation]:
        """Pop the last operation of the source; restore its ``before`` snapshots."""
        stack = self._undo.get(source_layer_id) or []
        if not stack:
            return None
        operation = stack.pop()
        self._redo.setdefault(source_layer_id, []).append(operation)
        return operation

    def redo(self, source_layer_id: str) -> Optional[CrossOperation]:
        """Pop the last undone operation; restore its ``after`` snapshots."""
        stack = self._redo.get(source_layer_id) or []
        if not stack:
            return None
        operation = stack.pop()
        self._undo.setdefault(source_layer_id, []).append(operation)
        return operation

    def clear_source(self, source_layer_id: str) -> None:
        """Drop the history of one source (vector Reset clears its own history too)."""
        self._undo.pop(source_layer_id, None)
        self._redo.pop(source_layer_id, None)

    def operations(self) -> List[CrossOperation]:
        """Every operation still kept (undo and redo stacks)."""
        return [op for stacks in (self._undo, self._redo) for stack in stacks.values() for op in stack]

    def _oldest(self, holds: Optional[Callable[[CrossOperation], bool]] = None):
        # Bottom of each stack: the oldest undo step, or the furthest redo step.
        # Undo / redo pop from the top, so dropping a bottom never shifts them.
        # ``op_id`` is a process-wide counter: comparable across histories.
        found = None
        for stacks, from_undo in ((self._undo, True), (self._redo, False)):
            for source_id, stack in stacks.items():
                if not stack or (holds is not None and not any(holds(op) for op in stack)):
                    continue
                if found is None or stack[0].op_id < found[2].op_id:
                    found = (stacks, source_id, stack[0], from_undo)
        return found

    def oldest(self, holds: Optional[Callable[[CrossOperation], bool]] = None) -> Optional[CrossOperation]:
        """The operation :meth:`drop_oldest` would forget, None when nothing qualifies."""
        found = self._oldest(holds)
        return found[2] if found else None

    def drop_oldest(self, holds: Optional[Callable[[CrossOperation], bool]] = None) -> Optional["DroppedStep"]:
        """Forget the bottom of the stack whose bottom is the oldest.

        Args:
            holds: Only stacks with at least one operation for which it is
                True are considered (e.g. "keeps a derived file alive"), so
                dropping never wipes stacks that would free nothing.

        Returns:
            The dropped step, None when nothing qualifies.
        """
        found = self._oldest(holds)
        if found is None:
            return None
        stacks, source_id, operation, from_undo = found
        stacks[source_id].pop(0)
        return DroppedStep(operation, from_undo)

    def forget_layer(self, layer_id: str) -> None:
        """Forget a removed layer: its own history, and its changes in the operations of other sources.

        The other layers of an operation keep their (before, after) pair, so
        undoing it still restores them; the operation keeps its ``op_id`` and
        is dropped only when the removed layer was all it changed.
        """
        for stacks in (self._undo, self._redo):
            stacks.pop(layer_id, None)
            for key in list(stacks):
                kept = []
                for op in stacks[key]:
                    if layer_id in op.layer_ids:
                        changes = tuple(pair for pair in op.changes if pair[0].layer_id != layer_id)
                        if not changes:
                            continue
                        op = replace(op, changes=changes)
                    kept.append(op)
                stacks[key] = kept

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()
