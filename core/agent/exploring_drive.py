# -*- coding: utf-8 -*-
"""What an agent may ask of the EXPLORING panel while the user watches: the buttons of its rail, checked.

Plain Python. EXPLORING has a rail of buttons that changes with the kind of the layer it shows
(``core/domain/exploring_tools.py``). An agent drives it as the user does, by its buttons: a toggle is turned on or off
(a mode of the layer, or a tool put on the map), an action is pressed. Never the ``more`` button (a menu needs a hand)
nor ``reset`` (it puts the options of the layer back to their defaults, which a turn could not give back).

The caller reads the rail (``adapters/public_api/exploring_drive.py``) and gives the state of each button; every
change of a call is checked here before any is made.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional, Tuple

from ..domain.exploring_tools import POINT_CLOUD, RASTER, SETTING_PATHS, VECTOR, tools_of

# The state of a button of the rail, as an agent reads it.
ON, OFF, PRESS, HIDDEN, UNAVAILABLE = "on", "off", "press", "hidden", "unavailable"

# The buttons that stay down: a mode of the layer (sync, follow, link, preview) or a tool on the map.
TOGGLES: Dict[str, Tuple[str, ...]] = {
    VECTOR: ("sync", "follow", "zone", "link"),
    RASTER: ("preview", "pipette", "detector", "similar", "link"),
    POINT_CLOUD: ("preview", "identify", "object", "value_pipette", "zone"),
}
# The buttons that run once: the map goes to what is selected, the selected features flash.
ACTIONS: Dict[str, Tuple[str, ...]] = {
    VECTOR: ("zoom", "identify"),
    RASTER: ("zoom",),
    POINT_CLOUD: ("zoom",),
}
# The toggles that put a tool under the pointer of the user: the map holds one at a time.
MAP_TOOLS = frozenset({"zone", "pipette", "detector", "similar", "identify", "object", "value_pipette"})
# On the rail, never driven: see the top of this module.
NOT_DRIVEN = ("more", "reset")
KIND_WORDS = {VECTOR: "vector", RASTER: "raster", POINT_CLOUD: "point cloud"}


def toggles_of(kind: str) -> Tuple[str, ...]:
    return TOGGLES.get(kind, ())


def actions_of(kind: str) -> Tuple[str, ...]:
    return ACTIONS.get(kind, ())


def driven(kind: str) -> Tuple[str, ...]:
    """The buttons of the rail of ``kind`` an agent drives, in the order of the rail."""
    return tuple(name for name in tools_of(kind) if name in toggles_of(kind) or name in actions_of(kind))


def _not_a_tool(kind: str, name: str) -> str:
    return (f"{name}: not a button of the rail of a {KIND_WORDS.get(kind, kind)} layer (turned on or off: "
            f"{', '.join(toggles_of(kind))}; pressed: {', '.join(actions_of(kind))})")


def _blocked(kind: str, name: str, state: str, reasons: Mapping[str, str]) -> str:
    """Why the button ``name`` cannot be used now; "" when it can."""
    if state == HIDDEN:
        return (f"{name}: the user hid this button of the rail ({SETTING_PATHS.get(kind, '')}): tell them, they show "
                "it again with a right-click on the rail")
    if state == UNAVAILABLE:
        reason = " ".join(str(reasons.get(name) or "").split())
        return f"{name}: not available now" + (f" ({reason})" if reason else "")
    return ""


def check_request(kind: str, tools: Any, press: Any, states: Mapping[str, str],
                  reasons: Optional[Mapping[str, str]] = None) -> Tuple[Dict[str, Any], List[str]]:
    """``({"tools": [(name, on)], "press": [name]}, problems)`` for the rail of a layer of ``kind``.

    ``tools``: ``{name: true | false}`` as the call gave it; ``press``: the actions named; ``states``: the state of
    each button now (``ON``, ``OFF``, ``PRESS``, ``HIDDEN``, ``UNAVAILABLE``); ``reasons``: why a button is not
    available, in the words of the panel. The plan holds only what differs from the rail as it is, the tools put down
    first: one tool is on the map at a time. Nothing is planned when one thing asked cannot be done.
    """
    problems: List[str] = []
    reasons = reasons or {}
    if tools is None:
        tools = {}
    if press is None:
        press = []
    if not isinstance(tools, dict) or not all(isinstance(name, str) for name in tools):
        return {}, ["tools: an object {name: true or false}"]
    if not isinstance(press, (list, tuple)) or not all(isinstance(name, str) for name in press):
        return {}, ["press: a list of names"]
    wanted: Dict[str, bool] = {}
    for name, value in tools.items():
        if name in actions_of(kind):
            problems.append(f"{name}: it runs once: name it in press")
        elif name in NOT_DRIVEN and name in tools_of(kind):
            problems.append(f"{name}: the user's own button: not driven")
        elif name not in toggles_of(kind):
            problems.append(_not_a_tool(kind, name))
        elif not isinstance(value, bool):
            problems.append(f"{name}: true or false")
        else:
            wanted[name] = value
    on_map = [name for name in toggles_of(kind) if wanted.get(name) and name in MAP_TOOLS]
    if len(on_map) > 1:
        problems.append(f"{', '.join(on_map)}: the map holds one tool at a time")
    pressed: List[str] = []
    for name in press:
        if name in toggles_of(kind):
            problems.append(f"{name}: it stays down: set it in tools")
        elif name in NOT_DRIVEN and name in tools_of(kind):
            problems.append(f"{name}: the user's own button: not driven")
        elif name not in actions_of(kind):
            problems.append(_not_a_tool(kind, name))
        elif name not in pressed:
            pressed.append(name)
    changes: List[Tuple[str, bool]] = []
    for name in toggles_of(kind):
        if name not in wanted:
            continue
        state = states.get(name, UNAVAILABLE)
        if not wanted[name]:
            if state == ON:
                changes.append((name, False))
            continue  # off, hidden or greyed: it is not on, which is what was asked
        if state == ON:
            continue
        blocked = _blocked(kind, name, state, reasons)
        if blocked:
            problems.append(blocked)
        else:
            changes.append((name, True))
    for name in pressed:
        blocked = _blocked(kind, name, states.get(name, UNAVAILABLE), reasons)
        if blocked:
            problems.append(blocked)
    if problems:
        return {}, problems
    changes.sort(key=lambda change: change[1])  # what goes off first; the sort keeps the order of the rail otherwise
    return {"tools": changes, "press": pressed}, []


# --- The offer after a filter on a threshold (the chat: ui/controllers/agent_chat_controller.py) -----------------------
# A filter that compares a field with a number is a value the user may want to move: the chat adds this note to the
# answer of apply_filter, once per layer and conversation, so that the model offers the panel or a widget instead of
# setting them up unasked (2026-11-22, asked by the user: "skill proposition user ce comportement").
_THRESHOLD = re.compile(r"(?:<=|>=|(?<![<>!])<(?![>=])|(?<![<>=!-])>(?!=))\s*-?\d|\bBETWEEN\s+-?\d", re.IGNORECASE)
TUNING_OFFER = ("A threshold the user may want to tune: end your answer with one line offering it, a slider over the "
                "histogram of the field (load_skill dashboards) or EXPLORING set up for them (load_skill panels). "
                "Change nothing until they say yes.")


def tuning_offer(expression: Any) -> str:
    """The note for the answer of a filter whose expression compares a field with a number; "" for any other."""
    return TUNING_OFFER if isinstance(expression, str) and _THRESHOLD.search(expression) else ""
