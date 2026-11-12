# -*- coding: utf-8 -*-
"""Undo a whole turn of the agent, whatever kind of layer it filtered.

Built on the snapshots of the cross filters: a raster or a point cloud gets its derived
source back too, a layer changed since is left alone, and the history keeps the derived
files of the turn alive.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Sequence, Tuple

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
        # What each step did beside the filters (one per step of ``_steps``), and the recorder of the step under way.
        self._step_effects: List[Tuple[Tuple[Any, ...], ...]] = []
        self._step_recorder: Optional[EffectsRecorder] = None
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
        self._close_step()
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
        self._step_recorder = EffectsRecorder(settings=False)
        if call is not None:
            self._effects.before_call(call, len(self._steps) - 1)
            try:  # what a step did is for "undo back to here" only: it never keeps a change from being made
                self._step_recorder.before_call(call)
            except Exception:  # noqa: BLE001
                logger.debug("Agent undo: a step not recorded", exc_info=True)

    def _close_step(self) -> None:
        """The step under way ends (the next one begins, or the turn ends): what it did beside the filters."""
        if self._step_recorder is not None:
            recorder, self._step_recorder = self._step_recorder, None
            try:
                done = recorder.finish()
            except Exception:  # noqa: BLE001 - the step is still listed by its filters; the turn undoes it whole
                logger.debug("Agent undo: what a step did beside the filters not recorded", exc_info=True)
                done = ()
            self._step_effects.append(done)

    def _step_record(self, after: Dict[str, LayerSnapshot], calls: Optional[List[int]] = None,
                     settings_calls: FrozenSet[int] = frozenset()):
        """``(steps, effects)``: for each step that changed something, the state before it of the layers it filtered
        (next step's state, or the end of the turn), and what it did beside the filters.

        A step that changed settings (``settings_calls``: their calls) is kept too, its settings undone by their own
        effects. ``calls`` receives the index of the call of each step kept."""
        steps, effects = [], []
        for index, (label, states) in enumerate(self._steps):
            following = self._steps[index + 1][1] if index + 1 < len(self._steps) else after
            changed = tuple(before for layer_id, before in states.items()
                            if layer_id in following and not following[layer_id].same_state(before))
            done = self._step_effects[index] if index < len(self._step_effects) else ()
            if changed or done or index in settings_calls:
                steps.append((label, changed))
                effects.append(done)
                if calls is not None:
                    calls.append(index)
        return tuple(steps), tuple(effects)

    @staticmethod
    def _settings_at_steps(effects, calls: List[int]):
        """The call of each settings effect turned into the number of recorded steps up to it: "back to before
        recorded step k" restores the settings whose number is above k."""
        placed = []
        for effect in effects:
            if effect[0] == "settings" and len(effect) > 4:
                call = effect[4]
                effect = effect[:4] + (sum(1 for index in calls if index <= call),)
            placed.append(effect)
        return tuple(placed)

    def discard(self) -> None:
        """Forget the turn under way without recording it: its project is closing.

        Committed after, it would compare the closed project with the next one (its notes, widgets, tree, themes,
        bookmarks and CRS with empty ones, the new layers as added) and an Undo would write the old project into the
        new one.
        """
        self._open = False
        self._before = {}
        self._steps = []
        self._effects = EffectsRecorder()
        self._step_effects, self._step_recorder = [], None
        try:
            from .plugin_settings import take_applied
            take_applied()  # what the agent applied in that turn is not an effect of the next one
        except Exception:
            logger.debug("Agent undo: applied settings not forgotten", exc_info=True)

    def commit(self) -> Sequence[str]:
        """Record the turn when it changed something; names of the layers it changed."""
        if not self._open:
            return ()
        self._open = False
        self._close_step()
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
        effects = self._effects.finish()
        calls: List[int] = []
        steps, step_effects = self._step_record(final, calls, frozenset(
            effect[4] for effect in effects if effect[0] == "settings" and len(effect) > 4))
        effects = self._settings_at_steps(effects, calls)
        self._before = {}
        self._steps = []
        self._step_effects = []
        several = len(steps) > 1
        _api_service().history.push(CrossOperation(HISTORY_KEY, tuple(changes), description=self.label[:MAX_LABEL],
                                                   steps=steps if several else (),
                                                   step_effects=step_effects if several else (), effects=effects))
        for effect in effects:
            if effect[0] in ("added", "removed", "style", "edits", "layout", "join") and len(effect) > 4 \
                    and effect[4] not in names:
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
                if effect[0] in ("added", "removed", "style", "edits", "layout", "join") and len(effect) > 4 \
                        and effect[4] not in layers:
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

    def _apply(self, operation: CrossOperation, use_before: bool,
               keep: FrozenSet[str] = frozenset()) -> Tuple[List[str], List[str], bool]:
        """Put the layers of a turn in one of its states: ``(changed, left as they are, a layer refused)``.

        A layer the user changed since is left alone and does not hold the history back. A layer that refused (being
        edited) is seen by comparing the states afterwards: that can be tried again. A layer whose id is in ``keep``
        (protected from the agent) is left as it is.
        """
        service = _api_service()
        project = QgsProject.instance()
        changes = [pair for pair in operation.changes if pair[0].layer_id not in keep]
        pairs = reversed(changes) if use_before else changes
        restored = set(service._restore(pairs, use_before=use_before, project=project))
        names, left = [], list(service.last_skipped)
        for before, _after in operation.changes:
            if before.layer_id in keep:
                layer = project.mapLayer(before.layer_id)
                left.append(layer.name() if layer is not None else before.layer_id)
        refused = False
        for before, after in changes:
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

    @staticmethod
    def _effects_of(operation: CrossOperation, back: bool, keep: FrozenSet[str] = frozenset(),
                    presence: Optional[bool] = None):
        """Apply the effects of ``operation`` towards its state before (``back``) or after; ``(done, left)``."""
        reversed_ = getattr(operation, "effects_reversed", False)
        return apply_effects(getattr(operation, "effects", ()), undo=back != reversed_, keep=keep, presence=presence)

    def _move(self, operation: CrossOperation, back: bool, keep: FrozenSet[str] = frozenset()):
        """``operation`` to its state before (``back``) or after: ``(changed, left as they are, a layer refused)``.

        The layers added or removed first (a filter needs its layer), then the filters, then the rest (a filter empties
        a selection). When a layer refused, the layers go back and nothing else changes.
        """
        done, not_done = self._effects_of(operation, back, keep, presence=True)
        names, left, refused = self._apply(operation, use_before=back, keep=keep)
        if refused:
            self._effects_of(operation, not back, presence=True)
            return names, left, True
        more, not_more = self._effects_of(operation, back, keep, presence=False)
        return _merged(names, done + more), _merged(left, not_done + not_more), False

    def undo_to_step(self, step: int, description: str = "") -> Tuple[List[str], List[str]]:
        """The last turn as it was before its step ``step``: a new step of the history, undoable.

        The filters of the layers, and what the steps did beside them (a style, a layer added, a name...), what the user
        changed since left as it is. Names of what changed, and of what was left as it is (changed since, or refused).
        """
        history = _api_service().history
        stack = history.undo_stack(HISTORY_KEY)
        steps = getattr(stack[-1], "steps", ()) if stack else ()
        if not 0 <= step < len(steps):
            return [], []
        step_effects = getattr(stack[-1], "step_effects", ())
        # The settings go back by their own effects (one per step that changed them), turned the way of these:
        # undone, they go to what the settings held before the step.
        settings = tuple((kind, layer_id, after, before) + tuple(rest) for kind, layer_id, before, after, *rest
                         in self._settings_back_to(getattr(stack[-1], "effects", ()), step))
        effects = tuple(effect for done in step_effects[step:] for effect in done) + settings
        targets: Dict[str, LayerSnapshot] = {}
        for _label, befores in steps[step:]:
            for before in befores:
                targets.setdefault(before.layer_id, before)  # the state before the first change at or after it
        project = QgsProject.instance()

        def pairs_of(skip) -> List[Tuple[LayerSnapshot, LayerSnapshot]]:
            pairs = []
            for layer_id, target in targets.items():
                layer = project.mapLayer(layer_id) if layer_id not in skip else None
                now = self._snapshot(layer, LayerKind(target.kind)) if layer is not None else None
                if now is not None and not now.same_state(target):
                    pairs.append((now, target))
            return pairs

        # The filters of the layers there now (a layer a later step added is removed by the effects: undoing this
        # operation brings it back first, then its filter), then of those the effects bring back (removed by a later
        # step: back as it was then, filtered by the earlier steps).
        pairs = pairs_of(())
        if not pairs and not effects:
            return [], []
        done, not_done = apply_effects(effects, undo=True, presence=True)
        pairs += pairs_of({now.layer_id for now, _target in pairs})
        # Its effects are those of the steps, undone: undoing this operation applies them again.
        operation = CrossOperation(HISTORY_KEY, tuple(pairs), description=(description or steps[step][0])[:MAX_LABEL],
                                   effects=effects, effects_reversed=True)
        names, left, refused = self._apply(operation, use_before=False) if pairs else ([], [], False)
        if refused:  # a layer refused (being edited): the layers go back, it can be tried again
            apply_effects(effects, undo=False, presence=True)
            return names, left
        more, not_more = apply_effects(effects, undo=True, presence=False)
        if names or done or more:
            history.push(operation)
        return _merged(names, done + more), _merged(left, not_done + not_more)

    @staticmethod
    def _settings_back_to(effects, step: int):
        """The settings of the last turn changed at or after its recorded step ``step``, as effects going from what
        they hold now to what they held before that step (a step of the history of its own, undoable)."""
        import json
        from .plugin_settings import current_values
        wanted: Dict[str, Any] = {}
        last: Dict[str, Any] = {}  # what the turn left each setting at
        for effect in effects:
            if effect[0] != "settings" or len(effect) <= 4:
                continue
            last.update(json.loads(effect[3]))
            if effect[4] > step:
                for path, value in json.loads(effect[2]).items():
                    wanted.setdefault(path, value)
        if not wanted:
            return ()
        now = current_values(wanted)
        # A setting the user changed since the turn is theirs: left as it is.
        moved = {path: value for path, value in wanted.items()
                 if now.get(path) != value and now.get(path) == last.get(path)}
        if not moved:
            return ()
        return (("settings", "", json.dumps({path: now.get(path) for path in moved}), json.dumps(moved), 0),)

    def undo(self, keep: FrozenSet[str] = frozenset()) -> Tuple[List[str], List[str]]:
        """Undo the last turn: names of the layers restored, and of those left as they are.

        When a layer refused, the turn stays where it was and can be tried again. The layers whose ids are in
        ``keep`` (protected from the agent, when the agent undoes its turn) are left as they are.
        """
        history = _api_service().history
        operation = history.undo(HISTORY_KEY)
        if operation is None:
            return [], []
        names, left, refused = self._move(operation, back=True, keep=keep)
        if refused:
            history.redo(HISTORY_KEY)
        return names, left

    def redo(self) -> Tuple[List[str], List[str]]:
        """Apply again the last turn undone: names of the layers changed, and of those left as they are."""
        history = _api_service().history
        operation = history.redo(HISTORY_KEY)
        if operation is None:
            return [], []
        names, left, refused = self._move(operation, back=False)
        if refused:
            history.undo(HISTORY_KEY)
        return names, left
