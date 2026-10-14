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
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
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
        geometry_wkt: Clip geometry of a derived layer, when known.
        side: ``inside`` / ``outside`` for a derived layer.
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

    def same_state(self, other: "LayerSnapshot") -> bool:
        """True when restoring ``other`` would not change anything."""
        return (self.source, self.provider, self.subset) == (other.source, other.provider, other.subset)


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

    def forget_layer(self, layer_id: str) -> None:
        """Drop every operation touching a removed layer (its snapshots are stale)."""
        for stacks in (self._undo, self._redo):
            stacks.pop(layer_id, None)
            for key in list(stacks):
                stacks[key] = [op for op in stacks[key] if layer_id not in op.layer_ids]

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()
