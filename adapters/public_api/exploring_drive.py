# -*- coding: utf-8 -*-
"""EXPLORING driven while the user watches, the way a hand drives it (agent mode).

The layer the panel shows is chosen in its own selector; a button of the rail is clicked, never its slot called: the
rules of the rail (one tool on the map, the tool of a group, a button the user hid) are those of the dock. Which
buttons, and the checks of a call: ``core/agent/exploring_drive.py``.

What a call changed is noted in order (``journal_since``): the chat undoes it with the turn
(``adapters/agent/turn_effects.py``), each change only while it is still as the call left it. Main thread only, plain
dicts out, ValueError for a refusal.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from ...core.agent.exploring_drive import HIDDEN, OFF, ON, PRESS, actions_of, check_request, toggles_of
from ...core.domain.exploring_tools import KINDS, POINT_CLOUD, RASTER, VECTOR
from .panel_options import _checked, _facts, _found, _project, dock_problem

NOT_IN_VIEW = ("EXPLORING is folded behind another section of the panel: the user opens it with its chip (a button "
               "in the thread does it too), or puts it in its own panel with a right-click on that chip.")
BUSY = ("The panel did not take {} (it is busy, or its selector does not list this layer): try again once it is "
        "idle.")
NO_RAIL = "The rail of EXPLORING is not ready for {} yet: try again."

# What set_exploring changed, in order: {"kind": "layer", "was": id, "now": id} and
# {"kind": "tool", "layer": id, "key": name, "was": bool, "now": bool}. Never emptied by a reader: a turn and each of
# its steps keep the place they began at (``journal_mark``).
MAX_JOURNAL = 400
_journal: List[Dict[str, Any]] = []
_dropped = 0


def _note(entry: Dict[str, Any]) -> None:
    global _dropped
    _journal.append(entry)
    if len(_journal) > MAX_JOURNAL:
        del _journal[0]
        _dropped += 1


def journal_mark() -> int:
    """Where the journal stands now: what comes after it is what the calls from now on change."""
    return _dropped + len(_journal)


def journal_since(mark: int) -> List[Dict[str, Any]]:
    return [dict(entry) for entry in _journal[max(0, mark - _dropped):]]


def kind_of(layer: Any) -> str:
    """``vector``, ``raster`` or ``point_cloud``; "" for a layer EXPLORING has no page for."""
    from qgis.core import QgsRasterLayer, QgsVectorLayer
    if isinstance(layer, QgsVectorLayer):
        return VECTOR
    if isinstance(layer, QgsRasterLayer):
        return RASTER
    try:
        from qgis.core import QgsPointCloudLayer
    except ImportError:  # a QGIS built without point clouds
        return ""
    return POINT_CLOUD if isinstance(layer, QgsPointCloudLayer) else ""


def _shown(dock) -> Any:
    """The layer the panel shows, or None (none, or deleted meanwhile)."""
    layer = getattr(dock, "current_layer", None)
    try:
        return layer if layer is not None and layer.id() else None
    except RuntimeError:
        return None


def _rail(dock) -> Any:
    """What holds the rail of EXPLORING (``ui/controllers/coverage_dock_extras.py``), or None."""
    integration = getattr(dock, "_controller_integration", None)
    coverage = getattr(integration, "coverage_controller", None) if integration is not None else None
    rail = getattr(coverage, "rail", None)
    return rail() if callable(rail) else None


def _states(dock, kind: str) -> Optional[Dict[str, Tuple[str, str]]]:
    """``{button: (state, why it is greyed)}`` of the rail shown; None while it is not the rail of ``kind``."""
    rail = _rail(dock)
    if rail is None or rail.rail_kind() != kind:
        return None
    return rail.tool_states()


def in_view(dock) -> bool:
    """Whether the user sees EXPLORING: open in the dock, or in its own panel in front. A dock without sections to
    fold hides nothing."""
    sections = getattr(dock, "_fm_sections", None)
    look = getattr(sections, "in_view", None)
    if not callable(look):
        return True
    try:
        return bool(look("exploring"))
    except RuntimeError:  # the dock went away
        return False


def bring_in_view(dock) -> bool:
    """EXPLORING open and in front, as a click on its chip; True when the user sees it then."""
    sections = getattr(dock, "_fm_sections", None)
    bring = getattr(sections, "bring_in_view", None)
    if callable(bring):
        try:
            bring("exploring")
        except RuntimeError:
            return False
    return in_view(dock)


def panel_state(dock) -> Dict[str, Any]:
    """What EXPLORING shows now: its layer, whether the user sees it, and each button of its rail an agent drives
    (``on``, ``off``, ``press`` for one that runs once, ``hidden`` by the user, ``unavailable`` when greyed)."""
    layer = _shown(dock)
    if layer is None:
        return {"layer_name": "", "layer_id": "", "kind": "", "in_view": in_view(dock), "tools": {}}
    kind = kind_of(layer)
    states = _states(dock, kind) or {}
    return {"layer_name": layer.name(), "layer_id": layer.id(), "kind": kind, "in_view": in_view(dock),
            "tools": {name: state for name, (state, _why) in states.items()}}


def _show_layer(dock, layer) -> bool:
    """``layer`` chosen in the selector of the panel, as the user picks it; True when the panel shows it then."""
    selector = getattr(dock, "comboBox_filtering_current_layer", None)
    if selector is not None:
        selector.setLayer(layer)
    shown = _shown(dock)
    if shown is None or shown.id() != layer.id():  # the selector kept its layer quiet (the same one): the panel is told
        dock.current_layer_changed(layer, manual_change=True)
        shown = _shown(dock)
    return shown is not None and shown.id() == layer.id()


def _assumed(kind: str, hidden: Sequence[str]) -> Dict[str, str]:
    """The rail of ``kind`` before its layer is shown: every button there, but those the user hid."""
    states = {name: OFF for name in toggles_of(kind)}
    states.update({name: PRESS for name in actions_of(kind)})
    states.update({name: HIDDEN for name in hidden if name in states})
    return states


def set_exploring(dock, layer: str = "", tools: Optional[Dict[str, bool]] = None,
                  press: Optional[Sequence[str]] = None, show: bool = False, project=None) -> Dict[str, Any]:
    """Drive EXPLORING: show ``layer`` in it (the one it shows by default), turn buttons of its rail on or off
    (``tools``: ``{name: bool}``), press its actions (``press``), and open it in front of the user (``show``).

    Raises:
        ValueError: What cannot be done, for the model. A name that is no button, a button the user hid and two tools
            for the map are refused before anything changes; a button greyed for the layer once it is shown is
            refused with the layer shown.
    """
    _checked(dock)
    project = _project(project)
    shown = _shown(dock)
    target = shown
    if layer:
        target = project.mapLayer(_found(layer, _facts(project)).layer_id)
    if target is None:
        raise ValueError("EXPLORING shows no layer: name one (layer).")
    kind = kind_of(target)
    if kind not in KINDS:
        raise ValueError(f"{target.name()}: EXPLORING shows vector, raster and point cloud layers only.")
    rail = _rail(dock)
    hidden = rail.hidden_tools(kind) if rail is not None else ()
    _plan, problems = check_request(kind, tools, press, _assumed(kind, hidden))
    if problems:
        raise ValueError("; ".join(problems))
    changed: List[str] = []
    if shown is None or shown.id() != target.id():
        if not _show_layer(dock, target):
            raise ValueError(BUSY.format(target.name()))
        _note({"kind": "layer", "was": shown.id() if shown is not None else "", "now": target.id()})
        changed.append("layer")
    states = _states(dock, kind)
    if states is None:
        raise ValueError(NO_RAIL.format(target.name()))
    plan, problems = check_request(kind, tools, press, {name: state for name, (state, _why) in states.items()},
                                   {name: why for name, (_state, why) in states.items()})
    if problems:
        prefix = f"{target.name()} is shown in EXPLORING; not done: " if changed else ""
        raise ValueError(prefix + "; ".join(problems))
    rail = _rail(dock)
    refused: List[str] = []
    for name, on in plan["tools"]:
        rail.click_tool(name)
        after = (_states(dock, kind) or {}).get(name, ("", ""))[0]
        if after == (ON if on else OFF):
            _note({"kind": "tool", "layer": target.id(), "key": name, "was": not on, "now": on})
            changed.append(name)
        else:
            refused.append(name)
    pressed = [name for name in plan["press"] if rail.click_tool(name)]
    if show:
        bring_in_view(dock)
    answer = dict(panel_state(dock), changed=changed, pressed=pressed)
    if refused:
        answer["not_changed"] = refused  # the panel kept them as they were (a rule of its rail): say so
    if not answer["in_view"]:
        answer["note"] = NOT_IN_VIEW
    return answer


def replay(dock, entries: Sequence[Dict[str, Any]], undo: bool, project=None) -> str:
    """Take back (``undo``) or make again what set_exploring noted: ``"done"`` when something was put back,
    ``"left"`` when the user changed it since (theirs: left as it is), "" when all is already as wanted."""
    if dock_problem(dock):
        return "left"
    project = _project(project)
    done = left = False
    for entry in (reversed(entries) if undo else entries):
        if not isinstance(entry, dict):
            continue
        wanted, as_left = (entry.get("was"), entry.get("now")) if undo else (entry.get("now"), entry.get("was"))
        shown = _shown(dock)
        shown_id = shown.id() if shown is not None else ""
        if entry.get("kind") == "layer":
            if shown_id == wanted:
                continue
            layer = project.mapLayer(wanted) if wanted else None
            if shown_id == as_left and layer is not None and _show_layer(dock, layer):
                done = True
            else:
                left = True
        elif entry.get("kind") == "tool":
            key = str(entry.get("key", ""))
            states = _states(dock, kind_of(shown)) if shown_id == entry.get("layer") else None
            state = (states or {}).get(key, ("", ""))[0]
            if not state:  # another layer is shown now: its rail is not the one the call drove
                left = True
            elif (state == ON) == bool(wanted):  # a button hidden or greyed since is not on either
                continue
            elif state in (ON, OFF) and _rail(dock).click_tool(key):
                done = True
            else:
                left = True
    return "done" if done else ("left" if left else "")
