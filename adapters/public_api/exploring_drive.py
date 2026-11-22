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

from ...core.agent.exploring_drive import (
    HIDDEN, OFF, ON, PRESS, actions_of, check_point_cloud_values, check_raster_values, check_request, toggles_of,
)
from ...core.domain.exploring_tools import KINDS, POINT_CLOUD, RASTER, VECTOR
from .panel_options import _checked, _facts, _found, _project, dock_problem

NOT_IN_VIEW = ("EXPLORING is folded behind another section of the panel: the user opens it with its chip (a button "
               "in the thread does it too), or puts it in its own panel with a right-click on that chip.")
DOCK_CLOSED = "The FilterMate panel is closed: the user opens it (a button in the thread does it too)."
BUSY = "Nothing changed, the panel is busy: {}"
NOT_LISTED = ("EXPLORING does not list {}: a table without geometry, a layer FilterMate has not read yet, or a raster "
              "or point cloud while FilterMate's option for them is off (describe_settings: raster, point cloud).")
NO_RAIL = "The rail of EXPLORING is not ready for {} yet: try again."
PROTECTED = ("Not done: the user protected {} from the agent. EXPLORING may show it, but its tools and the values of "
             "its panel may change the layer: tell the user; do not try another tool to change it.")
# What set_exploring changed, in order: {"kind": "layer", "was": id, "now": id} and
# {"kind": "tool", "layer": id, "key": name, "was": bool, "now": bool}. Never emptied by a reader: a turn and each of
# its steps keep the place they began at (``journal_mark``).
MAX_JOURNAL = 2000
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


def journal_since(mark: int, end: Optional[int] = None) -> List[Dict[str, Any]]:
    """What was noted from ``mark`` on (to ``end``, a mark too, when given)."""
    stop = None if end is None else max(0, end - _dropped)
    return [dict(entry) for entry in _journal[max(0, mark - _dropped):stop]]


def _key(entry: Dict[str, Any]) -> Tuple[Any, ...]:
    kind = entry.get("kind")
    if kind == "tool":
        return (kind, entry.get("layer"), entry.get("key"))
    if kind == "values":
        return (kind, entry.get("layer"), entry.get("type"))
    return (kind,)


def net(entries: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """What an undo or a redo walks: one change per button and per panel (from what it was before the first change to
    what the last one left), at the place of its last change; a button turned on then off again by the turn is no
    change of the turn, and an undo must not click it (the user may have turned it on since). The changes of layer stay
    as they were, in order: what was done on a layer the turn went through is undone on that layer. Only a round trip
    on which nothing was left changed (the turn showed B, then A again) is dropped: the user may show B since."""
    out: List[Dict[str, Any]] = []
    first: Dict[Tuple[Any, ...], Any] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        key = _key(entry)
        if entry.get("kind") == "layer":
            out.append(dict(entry))
            continue
        first.setdefault(key, entry.get("was"))
        out = [item for item in out if _key(item) != key]
        out.append(dict(entry, was=first[key]))
    out = [entry for entry in out if entry.get("kind") == "layer" or entry.get("was") != entry.get("now")]
    layers = [entry for entry in out if entry.get("kind") == "layer"]
    if layers and layers[0].get("was") == layers[-1].get("now") and all(
            entry.get("layer") == layers[0].get("was") for entry in out if entry.get("kind") != "layer"):
        out = [entry for entry in out if entry.get("kind") != "layer"]
    return out


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
    try:
        if rail is None or rail.rail_kind() != kind:
            return None
        return rail.tool_states()
    except RuntimeError:  # a button deleted meanwhile (the dock closing)
        return None


def _click(dock, key: str) -> bool:
    rail = _rail(dock)
    try:
        return bool(rail is not None and rail.click_tool(key))
    except RuntimeError:
        return False


def _dock_shown(dock) -> bool:
    """Whether the panel is open (it may be behind the tab of another panel of QGIS, which a raise brings forward)."""
    try:
        return not bool(dock.isHidden())
    except (AttributeError, RuntimeError):
        return True  # a stand-in of the tests: nothing to say


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
    """EXPLORING open and in front, as a click on its chip (the panel opened first when it is closed); True when the
    user sees it then."""
    try:
        if not _dock_shown(dock):
            dock.show()
        dock.raise_()  # in front of the tabs it shares with other panels
    except (AttributeError, RuntimeError):
        return False
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


def _listed(dock, layer) -> bool:
    """Whether the selector of the panel lists ``layer`` and FilterMate has read it: a layer it does not list would be
    replaced by another one when chosen (the selector falls on none, the dock on its first layer)."""
    if layer.id() not in (getattr(dock, "PROJECT_LAYERS", None) or {}):
        return False
    selector = getattr(dock, "comboBox_filtering_current_layer", None)
    if selector is None or not hasattr(selector, "count") or not hasattr(selector, "layer"):
        return True
    try:
        return any(selector.layer(index) is not None and selector.layer(index).id() == layer.id()
                   for index in range(selector.count()))
    except RuntimeError:
        return False


def _busy(dock) -> str:
    """Why the panel would not take another layer now (it would take it later, unnoted); "" when it would."""
    for flag, words in (("_filtering_in_progress", "a filter runs"), ("_updating_current_layer", "a layer is shown"),
                        ("_plugin_busy", "a task runs")):
        if getattr(dock, flag, False) is True:
            return words
    try:
        from .operations import busy_reason
        return busy_reason()
    except ImportError:
        return ""


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


# --- The values of the panel of a raster and of a point cloud -----------------------------------------------------
# The keys of the state of a panel that make what it selects (the rest is how it shows): compared before an undo puts
# the state of before back, so that a change of the user since is left as it is.
RASTER_STATE_KEYS = ("mode", "pipette_bands", "derivative", "minimum", "maximum", "custom_quantity", "all_bands")
POINT_CLOUD_STATE_KEYS = ("classes_enabled", "classes", "ranges_enabled", "conditions", "expression_enabled", "objects",
                          "zone_wkt")


def _coverage(dock) -> Any:
    integration = getattr(dock, "_controller_integration", None)
    return getattr(integration, "coverage_controller", None) if integration is not None else None


def _panel_of(dock, kind: str) -> Any:
    """The EXPLORING panel of a raster or a point cloud, or None."""
    coverage = _coverage(dock)
    if coverage is None or kind not in (RASTER, POINT_CLOUD):
        return None
    return getattr(coverage, "_raster_panel" if kind == RASTER else "_pc_panel", None)


def _plain(state: Dict[str, Any]) -> Dict[str, Any]:
    """A state of a panel as JSON keeps it (the effects of a turn are JSON)."""
    import json
    return json.loads(json.dumps(state, default=str))


def _part(state: Dict[str, Any], kind: str) -> Dict[str, Any]:
    keys = RASTER_STATE_KEYS if kind == RASTER else POINT_CLOUD_STATE_KEYS
    plain = _plain(state)
    return {key: plain.get(key) for key in keys}


def _raster_facts(panel) -> Tuple[List[int], bool]:
    """The bands the panel lets the user choose (not an alpha band), and whether the raster gives colours only."""
    return list(panel._selectable_bands()), bool(getattr(panel, "_rendered_only", False))


def _point_cloud_facts(panel) -> Tuple[List[int], List[str]]:
    """The classes the panel lets the user tick (those of the cloud, or every ASPRS code when it does not know them),
    and the attributes of its conditions."""
    from qgis.PyQt.QtCore import Qt
    # A cloud without a Classification attribute has no CLASSES group: no class to set.
    group = getattr(panel, "_classes_group", None)
    classes = [] if group is not None and group.isHidden() else sorted(
        {int(item.data(Qt.ItemDataRole.UserRole)) for item in panel._class_items()})
    attributes = [name for name, _label in (getattr(panel, "_condition_choices", None) or ())]
    return classes, attributes


def _restored(dock, kind: str, panel, wanted: Dict[str, Any]) -> None:
    """The keys of the selection of ``wanted`` (``*_STATE_KEYS``) in the panel, the rest as it is now (what the user
    set since: roles, tolerance, height...), then what the panel says when the user changes them: the bands chosen
    (the histogram and the map follow), the quantity (its histogram), the group made active (its tool follows, as a
    click does), the selection (the preview follows)."""
    before = _plain(panel.state())
    keys = RASTER_STATE_KEYS if kind == RASTER else POINT_CLOUD_STATE_KEYS
    state = dict(before, **{key: wanted[key] for key in keys if key in wanted})
    if kind == RASTER:
        if list(state.get("pipette_bands") or []) != list(before.get("pipette_bands") or []):
            low, high, derivative = state.get("minimum"), state.get("maximum"), state.get("derivative")
            panel._set_selected_bands(list(state.get("pipette_bands") or []))  # the path of a band ticked
            state = dict(_plain(panel.state()), derivative=derivative, minimum=low, maximum=high,
                         mode=state.get("mode"), custom_quantity=state.get("custom_quantity"))
        panel.restore_state(state)
        after = _plain(panel.state())
        if after.get("derivative") != before.get("derivative") or after.get("custom_quantity") != before.get(
                "custom_quantity"):
            panel.bandChanged.emit(panel.current_band())  # the histogram of the quantity now in use
        if after.get("mode") != before.get("mode"):
            panel.modeChosen.emit(after.get("mode"))
        panel.selectionChanged.emit()
    else:
        panel.restore_state(state)
        after = _plain(panel.state())
        for group, flag in (("classes", "classes_enabled"), ("ranges", "ranges_enabled")):
            if after.get(flag) and not before.get(flag):
                panel.groupChosen.emit(group)  # its tool follows, as a click on the group does
        panel.criteriaChanged.emit()


def _apply_raster(dock, panel, values: Dict[str, Any]) -> None:
    """The range of the raster set as the user sets it: RANGE active, on the band and the quantity asked; a band or a
    quantity changed without bounds forgets the old ones (they were in another unit), as the panel does."""
    state = _plain(panel.state())
    band = values.get("band", panel.current_band())
    quantity = values.get("quantity", state.get("derivative"))
    wanted = dict(mode="range", custom_quantity=False, all_bands=False, pipette_bands=[band], derivative=quantity,
                  minimum=state.get("minimum"), maximum=state.get("maximum"))
    if band != panel.current_band() or quantity != state.get("derivative") or state.get("custom_quantity"):
        wanted.update(minimum=None, maximum=None)
    wanted.update({key: values[key] for key in ("minimum", "maximum") if key in values})
    _restored(dock, RASTER, panel, wanted)


def _apply_point_cloud(dock, panel, values: Dict[str, Any]) -> None:
    from ...core.domain.point_cloud_attributes import (
        JOIN_AND, OP_BETWEEN, OP_GREATER_OR_EQUAL, OP_LESS_OR_EQUAL,
    )
    if "classes" in values:
        # The objects detected in CLASSES stand for their classes: the panel drops them when a class is ticked.
        wanted = dict(classes_enabled=True, classes=list(values["classes"]), ranges_enabled=False,
                      expression_enabled=False, objects={})
    else:
        conditions = []
        for item in values["ranges"]:
            low, high = item["minimum"], item["maximum"]
            if low is not None and high is not None:
                condition = {"op": OP_BETWEEN, "low": low, "high": high}
            elif low is not None:
                condition = {"op": OP_GREATER_OR_EQUAL, "low": low}
            else:
                condition = {"op": OP_LESS_OR_EQUAL, "low": high}
            conditions.append(dict(condition, attribute=item["attribute"], join=JOIN_AND))
        # The outline of a zone drawn went with its X / Y conditions, which these replace.
        wanted = dict(ranges_enabled=True, conditions=conditions, classes_enabled=False, expression_enabled=False,
                      zone_wkt="")
    _restored(dock, POINT_CLOUD, panel, wanted)


def _values_said(panel, kind: str) -> Dict[str, Any]:
    """What the panel holds now of the values an agent sets, in its words."""
    state = _plain(panel.state())
    if kind == RASTER:
        return {"band": state.get("band"), "quantity": state.get("derivative"), "minimum": state.get("minimum"),
                "maximum": state.get("maximum")}
    if state.get("classes_enabled"):
        return {"classes": state.get("classes") or []}
    return {"ranges": [{"attribute": item.get("attribute"), "op": item.get("op"), "low": item.get("low"),
                        "high": item.get("high")} for item in state.get("conditions") or []]}


def set_exploring(dock, layer: str = "", tools: Optional[Dict[str, bool]] = None,
                  press: Optional[Sequence[str]] = None, show: bool = False, project=None,
                  raster: Optional[Dict[str, Any]] = None,
                  point_cloud: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Drive EXPLORING: show ``layer`` in it (the one it shows by default), set the range of a raster (``raster``)
    or the classes or ranges of a point cloud (``point_cloud``) as its panel holds them, turn buttons of its rail on
    or off (``tools``: ``{name: bool}``), press its actions (``press``), and open it in front of the user (``show``).

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
    raster, point_cloud = raster or None, point_cloud or None  # {} from a client: nothing asked
    if raster is not None and kind != RASTER:
        problems.append(f"raster: {target.name()} is not a raster")
    if point_cloud is not None and kind != POINT_CLOUD:
        problems.append(f"point_cloud: {target.name()} is not a point cloud")
    switching = shown is None or shown.id() != target.id()
    if switching and not _listed(dock, target):
        problems.append(NOT_LISTED.format(target.name()))
    elif switching and _busy(dock):
        problems.append(BUSY.format(_busy(dock)))
    # On a protected layer EXPLORING only shows: a tool or a value may change its group, its preview or its style.
    if (raster or point_cloud or (isinstance(tools, dict) and tools)) and _protected(target):
        problems.append(PROTECTED.format(target.name()))
    if problems:
        raise ValueError("; ".join(problems))
    changed: List[str] = []
    if switching:
        if not _show_layer(dock, target):
            raise ValueError(BUSY.format(f"{target.name()} was not taken"))
        _note({"kind": "layer", "was": shown.id() if shown is not None else "", "now": target.id()})
        changed.append("layer")
    states = _states(dock, kind)
    if states is None:
        prefix = f"{target.name()} is shown in EXPLORING; not done: " if changed else ""
        raise ValueError(prefix + NO_RAIL.format(target.name()))
    plan, problems = check_request(kind, tools, press, {name: state for name, (state, _why) in states.items()},
                                   {name: why for name, (_state, why) in states.items()})
    values, panel = {}, None
    if raster is not None or point_cloud is not None:
        panel = _panel_of(dock, kind)
        if panel is None:
            problems.append(NO_RAIL.format(target.name()))
        elif kind == RASTER:
            values, more = check_raster_values(raster, *_raster_facts(panel))
            problems += more
        else:
            values, more = check_point_cloud_values(point_cloud, *_point_cloud_facts(panel))
            problems += more
    if problems:
        prefix = f"{target.name()} is shown in EXPLORING; not done: " if changed else ""
        raise ValueError(prefix + "; ".join(problems))
    panel = panel if panel is not None else _panel_of(dock, kind)
    part_before = _plain(panel.state()) if panel is not None and kind in (RASTER, POINT_CLOUD) else None
    if values:
        tools_before = {name: state for name, (state, _why) in states.items()}
        if kind == RASTER:
            _apply_raster(dock, panel, values)
        else:
            _apply_point_cloud(dock, panel, values)
        _note_moved(dock, kind, target, tools_before)
        changed.append("values")
        states = _states(dock, kind) or states
        plan, problems = check_request(kind, tools, press, {name: state for name, (state, _why) in states.items()},
                                       {name: why for name, (_state, why) in states.items()})
        if problems:
            _note_values(kind, target, panel, part_before)
            raise ValueError(f"The values are set in EXPLORING; not done: {'; '.join(problems)}")
    refused: List[str] = []
    for name, on in plan["tools"]:
        before = {key: state for key, (state, _why) in (_states(dock, kind) or {}).items()}
        _click(dock, name)
        moved = _note_moved(dock, kind, target, before, clicked=name)
        changed += [key for key in moved if key not in changed]
        if (_states(dock, kind) or {}).get(name, ("", ""))[0] != (ON if on else OFF):
            refused.append(name)
    pressed = [name for name in plan["press"] if _click(dock, name)]
    if part_before is not None:
        _note_values(kind, target, panel, part_before)  # what the values and the clicks left in the panel, once
    if show:
        bring_in_view(dock)
    answer = dict(panel_state(dock), changed=changed, pressed=pressed)
    if values:
        answer["values"] = _values_said(panel, kind)
    if refused:
        answer["not_changed"] = refused  # the panel kept them as they were (a rule of its rail): say so
    if not answer["in_view"]:
        answer["note"] = NOT_IN_VIEW if _dock_shown(dock) else DOCK_CLOSED
    return answer


def _note_moved(dock, kind: str, target, before: Dict[str, str], clicked: str = "") -> List[str]:
    """Note every button of the rail that went on or off since ``before`` (the one clicked, one the rail put down for
    it, one the panel greyed because its group left): an undo puts each back. The one clicked is noted last, so that
    an undo (read from the end) puts it down first, which gives the others their use back."""
    after = {key: state for key, (state, _why) in (_states(dock, kind) or {}).items()}
    moved = [key for key, state in after.items() if before.get(key) in (ON, OFF) and (state == ON) != (before[key] == ON)]
    moved.sort(key=lambda key: key == clicked)
    for key in moved:
        _note({"kind": "tool", "layer": target.id(), "key": key, "was": before[key] == ON, "now": after[key] == ON})
    return moved


def _note_values(kind: str, target, panel, before: Dict[str, Any]) -> None:
    """Note what the call left of the selection of the panel of a raster or a point cloud, when it changed (by the
    values asked, or by a tool that made another group active)."""
    after = _plain(panel.state())
    if _part(after, kind) != _part(before, kind):
        _note({"kind": "values", "layer": target.id(), "type": kind, "was": before, "now": after})


def _protected(layer) -> bool:
    """Whether the user protected ``layer`` from the agent; True when the protection cannot be read (refused)."""
    try:
        from ..agent.protected_layers import ProjectProtection
        return ProjectProtection().name_of(layer.id()) is not None
    except Exception:  # noqa: BLE001 - unreadable: never let a change through unchecked
        return True


def replay(dock, entries: Sequence[Dict[str, Any]], undo: bool, project=None) -> str:
    """Take back (``undo``) or make again what set_exploring noted: ``"done"`` when something was put back,
    ``"left"`` when the user changed it since (theirs: left as it is), "" when all is already as wanted."""
    if dock_problem(dock):
        return "left"
    project = _project(project)
    done = left = False
    entries = net(entries)
    for entry in (reversed(entries) if undo else entries):
        wanted, as_left = (entry.get("was"), entry.get("now")) if undo else (entry.get("now"), entry.get("was"))
        shown = _shown(dock)
        shown_id = shown.id() if shown is not None else ""
        if entry.get("kind") == "layer":
            if shown_id == wanted or not wanted:  # the panel showed no layer before: nothing to show back
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
            elif state in (ON, OFF) and _click(dock, key):
                done = True
            else:
                left = True
        elif entry.get("kind") == "values":
            kind = str(entry.get("type", ""))
            panel = _panel_of(dock, kind) if shown_id == entry.get("layer") else None
            if panel is None or not isinstance(wanted, dict) or not isinstance(as_left, dict):
                left = True
                continue
            now = _part(panel.state(), kind)
            if now == _part(wanted, kind):
                continue
            if now == _part(as_left, kind):
                _restored(dock, kind, panel, wanted)
                done = True
            else:
                left = True
    return "done" if done else ("left" if left else "")
