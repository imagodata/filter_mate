# -*- coding: utf-8 -*-
"""The FilterMate settings of a layer as its project carries them, and how they meet the copy of a computer.

Decided 2026-11-24: once a project is saved, its file is the truth for the settings of its layers, the ``exploring``
and ``filtering`` groups (``infos`` is read from the layer itself); the SQLite of each computer is a working copy. Each
setting is a custom property of the layer, ``variableValues/filterMate_<group>_<key>``, written at the registration of
the layer (LayersManagementEngineTask) and at each change (VariablesPersistenceManager), so Ctrl+S carries it.

Until 5.1.2 a change made in the panel was written as ``variableValues/<group>_<key>`` (no ``filterMate_``) while the
right name kept the value of the registration. That legacy value is the latest the user chose: it wins over the right
name, and is moved under it once (:func:`legacy_moves`).

The project is the truth only for values this version wrote (2026-11-24, review): each layer whose settings this
version wrote carries the custom property :data:`VERSION_PROPERTY`. A layer without it (the first opening after the
update, written by an earlier version) gives the settings the SQLite of this computer does not have; so does any layer
of a project that cannot be saved (a read-only file, or no file yet).

Lists and dicts are stored as their JSON text (:func:`storable`), as the panel writes them: an empty list stored as
such comes back from a .qgz as None (QgsXmlUtils, measured in QGIS 3.44 and 4.3).

Pure: the custom properties of a layer in (a dict), plain dicts out (infrastructure.utils.layer_settings reads and
writes the layer).
"""
from __future__ import annotations

import json
from typing import Any, Callable, Collection, Dict, List, Mapping, Optional, Tuple

VERSION_PROPERTY = "filterMate/settings_version"  # a custom property of the layer
VERSION = 2
VALUES = "variableValues/"
PREFIX = "filterMate_"
GROUPS = ("exploring", "filtering")  # what travels with the project
LEGACY_GROUPS = ("infos", "exploring", "filtering")  # what the panel wrote under a legacy name
LAYER_ID_LISTS = ("layers_to_filter", "centroid_layers")  # filtering settings that list layers by id
LISTS = LAYER_ID_LISTS + ("geometric_predicates",)
# The flags of the templates of LayersManagementEngineTask (the SQLite gives 1 / 0 for those it stored as bools)
FLAGS = frozenset((
    "is_changing_all_layer_properties", "is_tracking", "is_selecting", "is_linking",
    "has_layers_to_filter", "has_combine_operator", "has_geometric_predicates", "use_centroids_source_layer",
    "use_centroids_distant_layers", "has_buffer_value", "buffer_value_property", "has_buffer_type",
    "has_simplify_tolerance"))
EMPTY_FORMS = ("", "[]", "{}")

Settings = Dict[str, Dict[str, Any]]


def variable_name(group: str, key: str) -> str:
    """The name of the layer variable of a setting: ``filterMate_<group>_<key>``."""
    return f"{PREFIX}{group}_{key}"


def _setting(name: str, prefix: str, groups) -> Optional[Tuple[str, str]]:
    """``(group, key)`` of a variable name ``<prefix><group>_<key>``, None for another name."""
    for group in groups:
        head = f"{prefix}{group}_"
        if name.startswith(head) and len(name) > len(head):
            return group, name[len(head):]
    return None


def is_settings_property(key: Any) -> bool:
    """True for a custom property that holds a setting of FilterMate, under its name or a legacy one.

    QGIS keeps its own layer variables in two lists (``variableNames``, ``variableValues``): a property
    ``variableValues/<name>`` is FilterMate's only.
    """
    if not isinstance(key, str) or not key.startswith(VALUES):
        return False
    name = key[len(VALUES):]
    return _setting(name, PREFIX, GROUPS) is not None or _setting(name, "", LEGACY_GROUPS) is not None


def project_settings(properties: Mapping[str, Any]) -> Settings:
    """``{group: {key: value as stored}}``: the settings a layer carries, a legacy name over the right one.

    A value None is kept: an empty text comes back from a .qgz as None (as an empty list stored as such), and the
    property is there (:func:`empty_value` tells which).

    Args:
        properties: Custom properties of the layer (other keys are left out), as ``customProperty`` gives them.
    """
    settings: Settings = {}
    legacy: Settings = {}
    for key, value in properties.items():
        if not is_settings_property(key):
            continue
        name = key[len(VALUES):]
        found = _setting(name, PREFIX, GROUPS)
        if found is not None:
            settings.setdefault(found[0], {})[found[1]] = value
            continue
        found = _setting(name, "", GROUPS)
        if found is not None:
            legacy.setdefault(found[0], {})[found[1]] = value
    for group, values in legacy.items():
        settings.setdefault(group, {}).update(values)
    return settings


def legacy_moves(properties: Mapping[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """What puts the legacy values of a layer under their right names.

    Returns:
        ``({variable name: value} to write, [legacy variable names] to remove)``. A legacy ``infos`` value is removed
        only: ``infos`` is read from the layer.
    """
    writes: Dict[str, Any] = {}
    removals: List[str] = []
    for key, value in properties.items():
        if not is_settings_property(key):
            continue
        name = key[len(VALUES):]
        found = _setting(name, "", LEGACY_GROUPS)
        if found is None:
            continue
        removals.append(name)
        if found[0] in GROUPS and value is not None:
            writes[variable_name(*found)] = storable(value)
    return writes, sorted(removals)


def typed_value(stored: Any, load: Callable[[str], Any]) -> Any:
    """A stored setting as the panel holds it.

    A value is stored as written: a bool, a number or a text as such, a list as its JSON text (or a list, written from
    the SQLite before). A text is typed by ``load`` as one read from the SQLite (``return_typed_value(text, 'load')``),
    and kept as it is when ``load`` cannot read it (an expression that starts with ``[``).
    """
    if not isinstance(stored, str):
        return stored
    try:
        return load(stored)
    except (ValueError, TypeError):
        return stored


def storable(value: Any) -> Any:
    """A setting as it is stored: a list or a dict as its JSON text (it then survives a .qgz), the rest as it is."""
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(list(value) if isinstance(value, tuple) else value)
    return value


def empty_value(current: Any, key: str = "") -> Any:
    """What a setting read as None from a .qgz holds: an empty list where the panel holds a list (or the setting is a
    list), else an empty text."""
    return [] if isinstance(current, (list, tuple)) or key in LISTS else ""


def as_flag(key: str, value: Any) -> Any:
    """A flag the SQLite gave as 1 / 0 is the bool it was stored as."""
    if key in FLAGS and type(value) is int and value in (0, 1):
        return bool(value)
    return value


def same_setting(one: Any, other: Any, load: Callable[[str], Any], key: str = "") -> bool:
    """True when two stored forms hold the same setting: ``'["a"]'`` and ``["a"]``; None (what a .qgz gives back for
    an empty value) and ``""``, ``[]``, ``"[]"``, ``{}``; a flag and the 1 / 0 the SQLite gave for it; two lists of
    layers in another order."""
    if one is None or other is None:
        return all(value is None or value in EMPTY_FORMS or value == [] or value == {} for value in (one, other))
    one, other = as_flag(key, typed_value(one, load)), as_flag(key, typed_value(other, load))
    if key in LAYER_ID_LISTS and isinstance(one, list) and isinstance(other, list):
        return sorted(map(str, one)) == sorted(map(str, other))
    if isinstance(one, bool) or isinstance(other, bool):
        return type(one) is type(other) and one == other
    if isinstance(one, (int, float)) and isinstance(other, (int, float)):
        return one == other
    return type(one) is type(other) and one == other


def present_layers(value: Any, layer_ids: Collection[str]) -> Any:
    """A list of layers without the ids the project does not have (an item that is not an id stays)."""
    if not isinstance(value, list):
        return value
    return [item for item in value if not isinstance(item, str) or item in layer_ids]


def repaired_variable_names(names: Any, values: Any, ours: Collection[str]) -> Optional[Tuple[List[Any], Any]]:
    """``(variableNames, variableValues)`` without the names of FilterMate, None when there is nothing to change.

    QGIS keeps the variables of a layer in two lists, paired by position. FilterMate added its names to the first one
    (its values are properties of their own), so a variable the user added after them took the value of a name of
    FilterMate. Repaired when the pairing can be told:

    - both lists of the same length (QGIS wrote them together): each name of FilterMate goes with its value;
    - as many values as names of the user (only the user's variables have values): the user's names, those values;
    - otherwise only the names of FilterMate that have no value at all go.

    Args:
        names: ``customProperty('variableNames')``.
        values: ``customProperty('variableValues')``.
        ours: Names of FilterMate (the ``variableValues/<name>`` properties of the layer, and ``filterMate_*``).
    """
    if not isinstance(names, list):
        return None
    values_list = values if isinstance(values, list) else ([] if values in (None, "") else [values])
    mine = [index for index, name in enumerate(names) if isinstance(name, str)
            and (name.startswith(PREFIX) or name in ours)]
    if not mine:
        return None
    theirs = [name for index, name in enumerate(names) if index not in mine]
    if len(values_list) == len(names):
        return theirs, [value for index, value in enumerate(values_list) if index not in mine]
    if len(values_list) == len(theirs):
        return theirs, values_list
    kept = [name for index, name in enumerate(names) if index not in mine or index < len(values_list)]
    return (kept, values) if len(kept) != len(names) else None


# --- The question asked at the opening of a project (2026-11-24) ----------------------------------------------------
#
# A setting the project carries (its layer marked, the file writable) that differs from the one this computer's SQLite
# has is not applied at the registration: the user is asked once for the whole project which groups to take. A group
# kept leaves this computer's values in the panel and the SQLite, and the project's in the project (never written over
# them: the settings of the others stay in a shared project). Asks are ``{layer_id: {group: {key: (mine, project's)}}}``.

Asks = Dict[str, Dict[str, Dict[str, Tuple[Any, Any]]]]


def merged_asks(pending: Asks, new: Asks) -> Asks:
    """The asks of several registrations of one project, the latest for a setting."""
    merged = {layer_id: {group: dict(keys) for group, keys in groups.items()} for layer_id, groups in pending.items()}
    for layer_id, groups in (new or {}).items():
        for group, keys in groups.items():
            merged.setdefault(layer_id, {}).setdefault(group, {}).update(keys)
    return merged


def asked_groups(asks: Asks) -> List[str]:
    """The groups the question is about, in the order of :data:`GROUPS`."""
    present = {group for groups in asks.values() for group, keys in groups.items() if keys}
    return [group for group in GROUPS if group in present]


def settings_to_apply(asks: Asks, groups: Collection[str], held: Mapping[str, Mapping[str, Mapping[str, Any]]],
                      load: Callable[[str], Any], layer_ids: Optional[Collection[str]] = None
                      ) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """``{layer_id: {group: {key: the project's value}}}`` to put in the panel for the groups the user took.

    A setting the panel no longer holds as it was at the registration (changed meanwhile by the user, or the layer
    gone) is left: the latest change wins. A list of layers is compared without the layers the project does not have
    (as the panel holds it), and given as the project stores it: the panel leaves them out, in memory only.

    Args:
        asks: What the registrations found different.
        groups: The groups the user took.
        held: The settings the panel holds now (``PROJECT_LAYERS``).
        layer_ids: The layers of the project: a list of layers keeps only them, as the panel does.
    """
    chosen: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for layer_id, by_group in asks.items():
        props = held.get(layer_id)
        if not isinstance(props, Mapping):
            continue
        for group, keys in by_group.items():
            if group not in groups:
                continue
            now = props.get(group) or {}
            for key, (mine, theirs) in keys.items():
                seen_mine, seen_theirs = mine, theirs
                if key in LAYER_ID_LISTS and layer_ids is not None:  # compared as the panel holds them
                    seen_mine, seen_theirs = present_layers(mine, layer_ids), present_layers(theirs, layer_ids)
                if key in now and same_setting(now[key], seen_mine, load, key) \
                        and not same_setting(seen_theirs, seen_mine, load, key):
                    # The project's value as stored: its variable holds it already, nothing is written there
                    chosen.setdefault(layer_id, {}).setdefault(group, {})[key] = theirs
    return chosen


def without_groups(asks: Asks, groups: Collection[str]) -> Asks:
    """The asks left once ``groups`` are settled."""
    left: Asks = {}
    for layer_id, by_group in asks.items():
        kept = {group: keys for group, keys in by_group.items() if keys and group not in groups}
        if kept:
            left[layer_id] = kept
    return left


ANSWERS = {"apply": True, "keep": False}


def answer_text(decisions: Mapping[str, bool]) -> str:
    """Remembered answers as stored, one per group asked: ``exploring:keep,filtering:apply``."""
    return ",".join(f"{group}:{'apply' if decisions[group] else 'keep'}" for group in GROUPS if group in decisions)


def answer_decisions(text: Any) -> Dict[str, bool]:
    """``{group: apply}`` of remembered answers (a group never asked is absent: it is asked)."""
    decisions: Dict[str, bool] = {}
    if not isinstance(text, str):
        return decisions
    for part in text.split(","):
        group, _sep, answer = part.partition(":")
        if group in GROUPS and answer in ANSWERS:
            decisions[group] = ANSWERS[answer]
    return decisions
