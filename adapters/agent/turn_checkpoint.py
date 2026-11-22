# -*- coding: utf-8 -*-
"""Undo a whole turn of the agent, whatever kind of layer it filtered.

Built on the snapshots of the cross filters: a raster or a point cloud gets its derived
source back too, a layer changed since is left alone, and the history keeps the derived
files of the turn alive.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Sequence, Tuple

from qgis.core import QgsProject

from ...core.domain.filter_state import CrossOperation, LayerSnapshot
from ...core.domain.layer_kind import LayerKind
from ..public_api.operations import _api_service, busy_reason, layer_kind
from ..qgis.coverage_layers.snapshots import take_snapshot
from .turn_effects import EffectsRecorder, apply_effects, takes_away

logger = logging.getLogger("FilterMate.agent")

HISTORY_KEY = "filtermate_agent_turn"
MAX_LABEL = 4000
_FILTERED_KINDS = (LayerKind.VECTOR, LayerKind.RASTER, LayerKind.POINT_CLOUD, LayerKind.VECTOR_TILE)
# The effects whose fifth item names what a turn changed (a layer, a layout), as the list of turns shows it.
_NAMED_EFFECTS = ("added", "removed", "style", "edits", "layout", "layout_item", "layout_state", "join", "form")


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
        # When the turn and each of its steps began: an operation done meanwhile (a raster filtered through the API,
        # a filter of the dock) is placed among them in the history of the project (core/domain/history_timeline.py).
        self._started = 0.0
        self._step_times: List[float] = []
        # The call of each step of ``_steps``: which step a card of the thread shows (``step_of``).
        self._calls: List[Any] = []
        self._open = False
        # The request of the turn being run, kept as the description of its operation.
        self.label = ""
        # Names a step from its tool call (the words the thread shows); None: the tool name.
        self.describe: Optional[Callable[[Any], str]] = None
        # Called when a turn opens, before its first change is made (the map is pinned then, for Compare).
        self.on_open: Optional[Callable[[], None]] = None
        # What the last commit recorded, None when it recorded nothing: the ``op_id`` of its operation, and for each
        # step of the turn kept (by ``step_of``) its rank in ``steps``, or None for a turn of a single step kept
        # (``steps`` is empty then: the turn is that step).
        self.recorded: Optional[Tuple[int, Dict[int, Optional[int]]]] = None

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
        if not self._open and self.on_open is not None:
            try:  # what is done when a turn opens never keeps its change from being made
                self.on_open()
            except Exception:  # noqa: BLE001
                logger.debug("Agent undo: the opening of a turn not followed", exc_info=True)
        now = time.time()
        if not self._open or not self._started:
            self._started = now
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
        self._step_times.append(now)
        self._calls.append(call)
        self._step_recorder = EffectsRecorder(settings=False)
        if call is not None:
            self._effects.before_call(call, len(self._steps) - 1)
            try:  # what a step did is for "undo back to here" only: it never keeps a change from being made
                self._step_recorder.before_call(call)
            except Exception:  # noqa: BLE001
                logger.debug("Agent undo: a step not recorded", exc_info=True)

    def end(self) -> None:
        """Called once the change ``begin`` announced was made: what comes to the project from now until the next
        change (a layer the user loads while the model thinks) is not the turn's."""
        for recorder in (self._effects, self._step_recorder):
            if recorder is not None:
                try:
                    recorder.after_call()
                except Exception:  # noqa: BLE001 - the turn is then compared whole, as before
                    logger.debug("Agent undo: the end of a step not recorded", exc_info=True)

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

    def step_of(self, call: Any) -> Optional[int]:
        """The step of the turn under way begun for ``call`` (that very object: two calls may share an id), in the
        order of ``begin``; None when no step was begun for it (a call that reads, or one of another turn)."""
        if not self._open or call is None:
            return None
        return next((index for index, begun in enumerate(self._calls) if begun is call), None)

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
        self._started, self._step_times, self._calls = 0.0, [], []
        self.recorded = None
        try:
            from .plugin_settings import take_applied
            take_applied()  # what the agent applied in that turn is not an effect of the next one
        except Exception:
            logger.debug("Agent undo: applied settings not forgotten", exc_info=True)

    def commit(self) -> Sequence[str]:
        """Record the turn when it changed something; names of the layers it changed."""
        self.recorded = None
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
        step_times = tuple(self._step_times[index] for index in calls if index < len(self._step_times))
        started = self._started
        self._before = {}
        self._steps = []
        self._step_effects = []
        self._started, self._step_times, self._calls = 0.0, [], []
        several = len(steps) > 1
        history = _api_service().history
        operation = CrossOperation(HISTORY_KEY, tuple(changes), description=self.label[:MAX_LABEL],
                                   steps=steps if several else (), step_effects=step_effects if several else (),
                                   effects=effects, started=started,
                                   step_times=step_times if several and len(step_times) == len(steps) else ())
        history.push(operation)
        if history.peek_undo(HISTORY_KEY) is operation:  # a turn that changed nothing is not kept
            self.recorded = (operation.op_id, {index: rank if several else None for rank, index in enumerate(calls)})
        for effect in effects:
            if effect[0] in _NAMED_EFFECTS and len(effect) > 4 \
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
                if effect[0] in _NAMED_EFFECTS and len(effect) > 4 \
                        and effect[4] not in layers:
                    layers.append(effect[4])
            return {"time": operation.timestamp, "request": operation.description, "layers": layers,
                    "applied": applied, "steps": [label for label, _states in getattr(operation, "steps", ())]}

        applied = [describe(operation, True) for operation in history.undo_stack(HISTORY_KEY)]
        undone = [describe(operation, False) for operation in reversed(history.redo_stack(HISTORY_KEY))]
        return applied + undone

    @staticmethod
    def applied() -> Tuple[CrossOperation, ...]:
        """The operations of the turns still applied, oldest first (their rank is the one ``turns`` gives)."""
        return _api_service().history.undo_stack(HISTORY_KEY)

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

    def _apply(self, operation: CrossOperation, use_before: bool, keep: FrozenSet[str] = frozenset(),
               going: FrozenSet[str] = frozenset()) -> Tuple[List[str], List[str], bool]:
        """Put the layers of a turn in one of its states: ``(changed, left as they are, a layer refused)``.

        A layer the user changed since is left alone and does not hold the history back. A layer that refused (being
        edited) is seen by comparing the states afterwards: that can be tried again. A layer whose id is in ``keep``
        (protected from the agent) is left as it is. A layer whose id is in ``going`` leaves the project next: its
        filter is not touched, and cannot refuse.
        """
        service = _api_service()
        project = QgsProject.instance()
        changes = [pair for pair in operation.changes if pair[0].layer_id not in keep and pair[0].layer_id not in going]
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
                    presence: Optional[bool] = None, edits: Optional[bool] = None, coming: Optional[bool] = None,
                    going: FrozenSet[str] = frozenset()):
        """Apply the effects of ``operation`` towards its state before (``back``) or after; ``(done, left)``."""
        reversed_ = getattr(operation, "effects_reversed", False)
        # A layer whose filter the operation restores must leave the editing mode the turn put it in; one that goes
        # away next (``going``) keeps it, and its edits come back if a layer refuses its filter.
        filtered = frozenset(before.layer_id for before, _after in operation.changes) - going
        return apply_effects(getattr(operation, "effects", ()), undo=back != reversed_, keep=keep, presence=presence,
                             edits=edits, close=filtered, coming=coming)

    @staticmethod
    def _going(operation: CrossOperation, back: bool, keep: FrozenSet[str] = frozenset()) -> FrozenSet[str]:
        """The layers that leave the project when ``operation`` goes to its state before (``back``) or after."""
        undo = back != getattr(operation, "effects_reversed", False)
        return frozenset(effect[1] for effect in getattr(operation, "effects", ())
                         if takes_away(effect, undo) and effect[1] not in keep)

    @staticmethod
    def _brought(before: set) -> set:
        """The ids of the layers in the project now that were not in ``before``: what the pass that brings layers
        back just added, read right after it (a layer added later, by the user or a task, is not counted)."""
        return set(QgsProject.instance().mapLayers()) - before

    @staticmethod
    def _take_back(brought: set) -> None:
        """Remove ``brought``: the layers a move that a layer then refused had just brought back (``_brought``). Only
        those: a layer that came in meanwhile (a Processing output finished while QGIS waited) stays."""
        project = QgsProject.instance()
        for layer_id in brought:
            if project.mapLayer(layer_id) is not None:
                project.removeMapLayer(layer_id)

    def _move(self, operation: CrossOperation, back: bool, keep: FrozenSet[str] = frozenset()):
        """``operation`` to its state before (``back``) or after: ``(changed, left as they are, a layer refused)``.

        The layers that come back first (a filter needs its layer), then the filters, then the layers that go away
        and the rest (a filter empties a selection). The edits of the turn go with the rest, except when they are
        undone: QGIS filters no layer being edited, so they are taken back before the filters, and a layer the turn put
        in editing mode leaves it. When a layer refused its filter (being edited), the edits go back as far as they
        can, what came back goes away again and nothing else changes.

        2026-11-13 (review of 5.1.0): the layers that go away were removed before the filters, and a refusal brought
        them back from their definition: a memory layer the turn had added did not come back, a file layer came back
        without its style nor its edits. They now leave once the filters are restored, so a refusal finds them as they
        were.
        """
        undoing = back != getattr(operation, "effects_reversed", False)
        going = self._going(operation, back, keep)
        present = set(QgsProject.instance().mapLayers())
        done, not_done = self._effects_of(operation, back, keep, presence=True, coming=True)
        brought = self._brought(present)
        if undoing:
            edited, not_edited = self._effects_of(operation, back, keep, presence=False, edits=True, going=going)
            done, not_done = done + edited, not_done + not_edited
        names, left, refused = self._apply(operation, use_before=back, keep=keep, going=going)
        if refused:
            if undoing:
                self._effects_of(operation, not back, keep, presence=False, edits=True)
            self._take_back(brought)
            return names, left, True
        gone, not_gone = self._effects_of(operation, back, keep, presence=True, coming=False)
        more, not_more = self._effects_of(operation, back, keep, presence=False, edits=False if undoing else None)
        return _merged(names, done + gone + more), _merged(left, not_done + not_gone + not_more), False

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
        return self.back_to(targets, effects, description or steps[step][0])

    def back_to(self, targets: Dict[str, LayerSnapshot], effects: Tuple[Tuple[Any, ...], ...],
                description: str = "") -> Tuple[List[str], List[str]]:
        """The layers of ``targets`` as their snapshots say, and ``effects`` undone: a new step of the history,
        undoable as a turn is.

        What "undo back to here" does for the steps of the last turn, and the history panel of the dock for the map
        before any step of the three histories (2026-11-14, "go back to before this step"). ``effects``: what was
        done beside the filters since, as the turns recorded it, oldest first; what the user changed since is left as
        it is. Names of what changed, and of what was left as it is (changed since, or refused).
        """
        history = _api_service().history
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
        present = set(project.mapLayers())
        done, not_done = apply_effects(effects, undo=True, presence=True, coming=True)
        brought = self._brought(present)
        pairs += pairs_of({now.layer_id for now, _target in pairs})
        # Its effects are those of the steps, undone: undoing this operation applies them again.
        operation = CrossOperation(HISTORY_KEY, tuple(pairs), description=description[:MAX_LABEL],
                                   effects=effects, effects_reversed=True)
        # A layer a later step added leaves below, once the filters are back: its own filter is left as it is (the
        # operation keeps it, for the day it is undone), and a layer that refuses finds it still in the project.
        going = self._going(operation, back=False)
        # The edits before the filters: a layer being edited refuses a filter (see _move).
        edited, not_edited = apply_effects(effects, undo=True, presence=False, edits=True,
                                           close=frozenset(now.layer_id for now, _target in pairs) - going)
        done, not_done = done + edited, not_done + not_edited
        names, left, refused = self._apply(operation, use_before=False, going=going) if pairs else ([], [], False)
        if refused:  # a layer refused (being edited by the user): what moved goes back, it can be tried again
            apply_effects(effects, undo=False, presence=False, edits=True)
            self._take_back(brought)
            return names, left
        gone, not_gone = apply_effects(effects, undo=True, presence=True, coming=False)
        more, not_more = apply_effects(effects, undo=True, presence=False, edits=False)
        if names or done or gone or more:
            history.push(operation)
        return _merged(names, done + gone + more), _merged(left, not_done + not_gone + not_more)

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
