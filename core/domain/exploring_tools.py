# -*- coding: utf-8 -*-
"""Which tool buttons the EXPLORING rail shows for each kind of layer: the names, and how a setting reads.

Plain Python, no Qt. The rail of EXPLORING changes with the kind of the current layer (vector, raster, point cloud),
and the user may hide some of its buttons for each kind: ``APP.DOCKWIDGET.EXPLORING_TOOLS.<kind>_hidden`` holds the
short names of the buttons hidden, as text (``"zoom, identify"``). The list of the hidden ones, not of the shown
ones, so that an empty setting (the default) shows every button: a configuration written before the setting, and a
button added later, need no migration.

What each name stands for on screen (the Qt button) is in ``ui/controllers/exploring_tool_choice.py``.

Reading a setting never fails: nothing, a number, a name no button has, a name twice, a list instead of text all give
the buttons that can be read, and a name that is wrong hides nothing. The ``more`` button is never hidden, whatever the
setting holds (``LOCKED``). What the agent and the setup may write (the names among those of the setting, ``names`` in
config.default.json) is checked by ``core/agent/settings_reference.py``.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, FrozenSet, Iterable, List, Tuple

logger = logging.getLogger(__name__)

VECTOR, RASTER, POINT_CLOUD = "vector", "raster", "point_cloud"
KINDS = (VECTOR, RASTER, POINT_CLOUD)

SECTION = "APP.DOCKWIDGET.EXPLORING_TOOLS"
SETTING_PATHS: Dict[str, str] = {kind: f"{SECTION}.{kind}_hidden" for kind in KINDS}

# The buttons of the rail of each kind, top to bottom. The same name can stand for two buttons of two kinds
# (``link``: the link of the single and multiple selections of a vector layer, the link of the range to the style
# of a raster; ``zoom``, ``preview``, ``reset``: the shared buttons of the dock).
TOOLS: Dict[str, Tuple[str, ...]] = {
    VECTOR: ("zoom", "sync", "identify", "follow", "zone", "link", "more", "reset"),
    RASTER: ("zoom", "preview", "pipette", "detector", "similar", "link", "more", "reset"),
    POINT_CLOUD: ("zoom", "preview", "identify", "object", "value_pipette", "zone", "more", "reset"),
}

# What is never hidden: the "more" button is the way to the functions that live only in its menu (the zone and the
# value under the cursor of a raster, the target of the object detector, the shape of the zone, the QGIS tools), and
# the one button that always stays on the rail: the rail is never empty, and a right-click on it brings the others
# back. The other buttons only start a tool or turn a mode on, and the group each belongs to (the pipette, the
# classes, the ranges, the single / multiple selections...) stays usable from its own widgets.
LOCKED: FrozenSet[str] = frozenset({"more"})


_SEPARATORS = ",;|\n\r\t"
_QUOTES = "\"'[](){}`"
_reported = set()


def _name(text: str) -> str:
    """One name as the rail writes it: lower case, ``Value-Pipette`` and ``value pipette`` are ``value_pipette``."""
    return "_".join(text.strip(_QUOTES + " ").lower().replace("-", " ").split())


def _words(raw: Any, known: Iterable[str] = ()) -> List[str]:
    """The names a setting holds, in the order written: ``"Zoom; identify"``, ``"zoom identify"``, ``["zoom"]``,
    ``'["zoom", "identify"]'``, ``"zoom|identify"``.

    Names are separated by a comma, a semicolon, a bar or a line break; a part that is not a name of ``known`` is read
    again as names separated by blanks (a name written with a blank, ``value pipette``, is one name)."""
    if isinstance(raw, str):
        text = raw
        for separator in _SEPARATORS[1:]:
            text = text.replace(separator, _SEPARATORS[0])
        parts: Iterable[Any] = text.split(_SEPARATORS[0])
    elif isinstance(raw, (list, tuple, set, frozenset)):
        parts = raw
    else:
        return []
    names = set(known)
    words: List[str] = []
    for part in parts:
        if not isinstance(part, str):
            continue
        word = _name(part)
        if not word:
            continue
        if word in names or not names:
            words.append(word)
            continue
        words.extend(_blank_names(part, names))
    return words


def _blank_names(part: str, names: set) -> List[str]:
    """``"value pipette zoom"``: the longest run of blank-separated words that is a name, then the next one."""
    tokens = [token for token in (_name(piece) for piece in part.replace("-", " ").split()) if token]
    found, at = [], 0
    while at < len(tokens):
        for end in range(len(tokens), at, -1):
            joined = "_".join(tokens[at:end])
            if joined in names or end == at + 1:
                found.append(joined)
                at = end
                break
    return found


def _report(kind: str, words: Iterable[str], own: Iterable[str]) -> None:
    """One line in the log, once per name, for a name of a setting that no button of the rail has."""
    for word in words:
        if (kind, word) not in _reported and word not in own:
            _reported.add((kind, word))
            logger.warning(f"EXPLORING tools: '{word}' is not a button of the {kind} rail (it has "
                           f"{', '.join(name for name in own if name not in LOCKED)}): ignored")


def tools_of(kind: str) -> Tuple[str, ...]:
    """The names of the buttons of the rail of ``kind``; none for a kind that is not one of the three."""
    return TOOLS.get(kind, ())


def hidden_for(kind: str, raw: Any) -> FrozenSet[str]:
    """The names hidden on the rail of ``kind`` by the setting ``raw``: those of its buttons, none of the locked.
    A name no button has is left out, and said once in the log."""
    own = tuple(tools_of(kind))
    words = _words(raw, own)
    if own:
        _report(kind, words, own)
    return frozenset(word for word in words if word in set(own) - LOCKED)


def shown_for(kind: str, raw: Any) -> Tuple[str, ...]:
    """The names shown on the rail of ``kind`` by the setting ``raw``, in the order of the rail."""
    hidden = hidden_for(kind, raw)
    return tuple(name for name in tools_of(kind) if name not in hidden)


def format_hidden(kind: str, hidden: Iterable[str]) -> str:
    """The text of the setting for the names ``hidden``: those of the rail of ``kind`` in its order, none locked."""
    wanted = set(hidden)
    return ", ".join(name for name in tools_of(kind) if name in wanted and name not in LOCKED)


def setting_from_shown(kind: str, shown: Iterable[str]) -> str:
    """The text of the setting when ``shown`` are the names kept on the rail of ``kind``: the others are hidden."""
    kept = set(shown)
    return format_hidden(kind, (name for name in tools_of(kind) if name not in kept))


def hidden_in_config(config_data: Any, kind: str) -> FrozenSet[str]:
    """The names hidden for ``kind`` in the configuration in use (wrapped ``{"value": ...}`` or raw leaf); nothing
    for a configuration that has no such setting, or that is not a configuration."""
    node: Any = config_data
    for key in SETTING_PATHS.get(kind, "").split("."):
        if not isinstance(node, dict) or key not in node:
            return frozenset()
        node = node[key]
    if isinstance(node, dict):
        node = node.get("value")
    return hidden_for(kind, node)
