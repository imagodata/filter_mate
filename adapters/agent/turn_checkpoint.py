# -*- coding: utf-8 -*-
"""Undo a whole turn of the agent, whatever kind of layer it filtered.

Built on the snapshots of the cross filters: a raster or a point cloud gets its derived
source back too, a layer changed since is left alone, and the history keeps the derived
files of the turn alive.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from qgis.core import QgsProject

from ...core.domain.filter_state import CrossOperation, LayerSnapshot
from ...core.domain.layer_kind import LayerKind
from ..public_api.operations import _api_service, busy_reason, layer_kind
from ..qgis.coverage_layers.snapshots import take_snapshot
from .turn_effects import EffectsRecorder, apply_effects

logger = logging.getLogger("FilterMate.agent")

HISTORY_KEY = "filtermate_agent_turn"
MAX_LABEL = 4000
_FILTERED_KINDS = (LayerKind.VECTOR, LayerKind.RASTER, LayerKind.POINT_CLOUD, LayerKind.VECTOR_TILE)


def _merged(first: List[str], second: List[str]) -> List[str]:
    return first + [name for name in second if name not in first]


class TurnCheckpoint:
    """The state of the project layers before a turn, and the stack of turns to undo."""

    def __init__(self) -> None:
        self._before: Dict[str, Tuple[LayerSnapshot, LayerKind]] = {}
        self._steps: List[Tuple[str, Dict[str, LayerSnapshot]]] = []
        self._effects = EffectsRecorder()
        self._open = False
        # The request of the turn being run, kept as the description of its operation.
        self.label = ""
        # Names a step from its tool call (the words the thread shows); None: the tool name.
        self.describe: Optional[Callable[[Any], str]] = None

    @staticmethod
    def _snapshot(layer, kind):
        """State of ``layer``, None when it cannot be captured: one odd layer must not lose the turn."""
        try:
            return take_snapshot(layer, kind)
        except (RuntimeError, ValueError, AttributeError) as exc:
            logger.info("Agent undo: %s not captured: %s", layer.name(), exc)
            return None

    def _label(self, call: Any) -> str:
        if call is None:
            return ""
        try:
            return self.describe(call) if self.describe is not None else str(getattr(call, "name", ""))
        except Exception:
            return str(getattr(call, "name", ""))

    def begin(self, call: Any = None) -> None:
        """Called before each change of a turn: the state of each layer then, a layer added meanwhile included.

        The first state of a layer is what the turn restores; the state before each change is what "undo back to
        here" restores, step by step.
        """
        self._open = True
        states: Dict[str, LayerSnapshot] = {}
        for layer in QgsProject.instance().mapLayers().values():
            kind = layer_kind(layer)
            if kind not in _FILTERED_KINDS or not layer.isValid():
                continue
            snapshot = self._snapshot(layer, kind)
            if snapshot is None:
                continue
            states[layer.id()] = snapshot
            if layer.id() not in self._before:
                self._before[layer.id()] = (snapshot, kind)
        self._steps.append((self._label(call), states))
        if call is not None:
            self._effects.before_call(call)

    def _step_record(self, after: Dict[str, LayerSnapshot]) -> Tuple[Tuple[str, Tuple[LayerSnapshot, ...]], ...]:
        """For each step, the state before it of the layers it changed (next step's state, or the end of the turn)."""
        steps = []
        for index, (label, states) in enumerate(self._steps):
            following = self._steps[index + 1][1] if index + 1 < len(self._steps) else after
            changed = tuple(before for layer_id, before in states.items()
                            if layer_id in following and not following[layer_id].same_state(before))
            if changed:
                steps.append((label, changed))
        return tuple(steps)

    def commit(self) -> Sequence[str]:
        """Record the turn when it changed something; names of the layers it changed."""
        if not self._open:
            return ()
        self._open = False
        project = QgsProject.instance()
        changes = []
        names: List[str] = []
        final: Dict[str, LayerSnapshot] = {}
        for layer_id, (before, kind) in self._before.items():
            layer = project.mapLayer(layer_id)
            after = self._snapshot(layer, kind) if layer is not None else None
            if after is not None:
                final[layer_id] = after
            if after is not None and not after.same_state(before):
                changes.append((before, after))
                names.append(layer.name())
        steps = self._step_record(final)
        effects = self._effects.finish()
        self._before = {}
        self._steps = []
        _api_service().history.push(CrossOperation(HISTORY_KEY, tuple(changes), description=self.label[:MAX_LABEL],
                                                   steps=steps if len(steps) > 1 else (), effects=effects))
        for effect in effects:
            if effect[0] in ("added", "removed", "style", "edits") and len(effect) > 4 and effect[4] not in names:
                names.append(effect[4])
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
            for effect in getattr(operation, "effects", ()):
                if effect[0] in ("added", "removed", "style", "edits") and len(effect) > 4 and effect[4] not in layers:
                    layers.append(effect[4])
            return {"time": operation.timestamp, "request": operation.description, "layers": layers,
                    "applied": applied, "steps": [label for label, _states in getattr(operation, "steps", ())]}

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

    def undo_to_step(self, step: int, description: str = "") -> Tuple[List[str], List[str]]:
        """The layers of the last turn as they were before its step ``step``: a new step of the history, undoable.

        Names of the layers changed, and of those left as they are (changed since, or refused).
        """
        history = _api_service().history
        stack = history.undo_stack(HISTORY_KEY)
        steps = getattr(stack[-1], "steps", ()) if stack else ()
        if not 0 <= step < len(steps):
            return [], []
        targets: Dict[str, LayerSnapshot] = {}
        for _label, befores in steps[step:]:
            for before in befores:
                targets.setdefault(before.layer_id, before)  # the state before the first change at or after it
        project = QgsProject.instance()
        pairs = []
        for layer_id, target in targets.items():
            layer = project.mapLayer(layer_id)
            now = self._snapshot(layer, LayerKind(target.kind)) if layer is not None else None
            if now is not None and not now.same_state(target):
                pairs.append((now, target))
        if not pairs:
            return [], []
        operation = CrossOperation(HISTORY_KEY, tuple(pairs), description=(description or steps[step][0])[:MAX_LABEL])
        names, left, refused = self._apply(operation, use_before=False)
        if names and not refused:
            history.push(operation)
        return names, left

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
        done, not_done = apply_effects(getattr(operation, "effects", ()), undo=True)
        return _merged(names, done), _merged(left, not_done)

    def redo(self) -> Tuple[List[str], List[str]]:
        """Apply again the last turn undone: names of the layers changed, and of those left as they are."""
        history = _api_service().history
        operation = history.redo(HISTORY_KEY)
        if operation is None:
            return [], []
        done, not_done = apply_effects(getattr(operation, "effects", ()), undo=False)  # layers first: filters need them
        names, left, refused = self._apply(operation, use_before=False)
        if refused:
            apply_effects(getattr(operation, "effects", ()), undo=True)
            history.undo(HISTORY_KEY)
            return names, left
        return _merged(names, done), _merged(left, not_done)
