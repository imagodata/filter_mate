# -*- coding: utf-8 -*-
"""Undo a whole turn of the agent, whatever kind of layer it filtered.

Built on the snapshots of the cross filters: a raster or a point cloud gets its derived
source back too, a layer changed since is left alone, and the history keeps the derived
files of the turn alive.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence, Tuple

from qgis.core import QgsProject

from ...core.domain.filter_state import CrossOperation, LayerSnapshot
from ...core.domain.layer_kind import LayerKind
from ..public_api.operations import _api_service, busy_reason, layer_kind
from ..qgis.coverage_layers.snapshots import take_snapshot

logger = logging.getLogger("FilterMate.agent")

HISTORY_KEY = "filtermate_agent_turn"
MAX_LABEL = 4000
_FILTERED_KINDS = (LayerKind.VECTOR, LayerKind.RASTER, LayerKind.POINT_CLOUD, LayerKind.VECTOR_TILE)


class TurnCheckpoint:
    """The state of the project layers before a turn, and the stack of turns to undo."""

    def __init__(self) -> None:
        self._before: Dict[str, Tuple[LayerSnapshot, LayerKind]] = {}
        self._open = False
        # The request of the turn being run, kept as the description of its operation.
        self.label = ""

    @staticmethod
    def _snapshot(layer, kind):
        """State of ``layer``, None when it cannot be captured: one odd layer must not lose the turn."""
        try:
            return take_snapshot(layer, kind)
        except (RuntimeError, ValueError, AttributeError) as exc:
            logger.info("Agent undo: %s not captured: %s", layer.name(), exc)
            return None

    def begin(self) -> None:
        """Called before each change of a turn: the first state of each layer, a layer added meanwhile included."""
        self._open = True
        for layer in QgsProject.instance().mapLayers().values():
            if layer.id() in self._before:
                continue
            kind = layer_kind(layer)
            if kind in _FILTERED_KINDS and layer.isValid():
                snapshot = self._snapshot(layer, kind)
                if snapshot is not None:
                    self._before[layer.id()] = (snapshot, kind)

    def commit(self) -> Sequence[str]:
        """Record the turn when it changed something; names of the layers it changed."""
        if not self._open:
            return ()
        self._open = False
        project = QgsProject.instance()
        changes = []
        names: List[str] = []
        for layer_id, (before, kind) in self._before.items():
            layer = project.mapLayer(layer_id)
            after = self._snapshot(layer, kind) if layer is not None else None
            if after is not None and not after.same_state(before):
                changes.append((before, after))
                names.append(layer.name())
        self._before = {}
        _api_service().history.push(CrossOperation(HISTORY_KEY, tuple(changes), description=self.label[:MAX_LABEL]))
        return names

    @staticmethod
    def turns() -> List[Dict[str, Any]]:
        """Every turn still known, oldest first: time, request, layers it changed, applied or undone."""
        history = _api_service().history
        project = QgsProject.instance()

        def describe(operation: CrossOperation, applied: bool) -> Dict[str, Any]:
            layers = []
            for before, _after in operation.changes:
                layer = project.mapLayer(before.layer_id)
                layers.append(layer.name() if layer is not None else before.layer_id)
            return {"time": operation.timestamp, "request": operation.description, "layers": layers,
                    "applied": applied}

        applied = [describe(operation, True) for operation in history.undo_stack(HISTORY_KEY)]
        undone = [describe(operation, False) for operation in reversed(history.redo_stack(HISTORY_KEY))]
        return applied + undone

    @staticmethod
    def can_undo() -> bool:
        return _api_service().can_undo(HISTORY_KEY)

    @staticmethod
    def can_redo() -> bool:
        return _api_service().can_redo(HISTORY_KEY)

    @staticmethod
    def busy() -> str:
        """Why nothing can be restored now, "" when it can."""
        return busy_reason()

    def _apply(self, operation: CrossOperation, use_before: bool) -> Tuple[List[str], List[str], bool]:
        """Put the layers of a turn in one of its states: ``(changed, left as they are, a layer refused)``.

        A layer the user changed since is left alone and does not hold the history back. A layer that refused (being
        edited) is seen by comparing the states afterwards: that can be tried again.
        """
        service = _api_service()
        project = QgsProject.instance()
        pairs = reversed(operation.changes) if use_before else operation.changes
        restored = set(service._restore(pairs, use_before=use_before, project=project))
        names, left = [], list(service.last_skipped)
        refused = False
        for before, after in operation.changes:
            layer = project.mapLayer(before.layer_id)
            if layer is None or before.layer_id not in restored:
                continue
            wanted = before if use_before else after
            now = self._snapshot(layer, LayerKind(before.kind))
            if now is not None and now.same_state(wanted):
                names.append(layer.name())
            else:
                left.append(layer.name())
                refused = True
        return names, left, refused

    def undo(self) -> Tuple[List[str], List[str]]:
        """Undo the last turn: names of the layers restored, and of those left as they are.

        When a layer refused, the turn stays where it was and can be tried again.
        """
        history = _api_service().history
        operation = history.undo(HISTORY_KEY)
        if operation is None:
            return [], []
        names, left, refused = self._apply(operation, use_before=True)
        if refused:
            history.redo(HISTORY_KEY)
        return names, left

    def redo(self) -> Tuple[List[str], List[str]]:
        """Apply again the last turn undone: names of the layers changed, and of those left as they are."""
        history = _api_service().history
        operation = history.redo(HISTORY_KEY)
        if operation is None:
            return [], []
        names, left, refused = self._apply(operation, use_before=False)
        if refused:
            history.undo(HISTORY_KEY)
        return names, left
