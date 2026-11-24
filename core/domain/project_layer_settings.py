# -*- coding: utf-8 -*-
"""The FilterMate settings of a layer as its project carries them, and how they meet the copy of a computer.

Decided 2026-11-24: once a project is saved, its file is the truth for the settings of its layers, the ``exploring``
and ``filtering`` groups (``infos`` is read from the layer itself); the SQLite of each computer is a working copy. Each
setting is a custom property of the layer, ``variableValues/filterMate_<group>_<key>``, written at the registration of
the layer (LayersManagementEngineTask) and at each change (VariablesPersistenceManager), so Ctrl+S carries it.

Until 5.1.2 a change made in the panel was written as ``variableValues/<group>_<key>`` (no ``filterMate_``) while the
right name kept the value of the registration. That legacy value is the latest the user chose: it wins over the right
name, and is moved under it once (:func:`legacy_moves`).

Pure: the custom properties of a layer in (a dict), plain dicts out (infrastructure.utils.layer_settings reads and
writes the layer).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

VALUES = "variableValues/"
PREFIX = "filterMate_"
GROUPS = ("exploring", "filtering")  # what travels with the project
LEGACY_GROUPS = ("infos", "exploring", "filtering")  # what the panel wrote under a legacy name

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

    Args:
        properties: Custom properties of the layer (other keys are left out), as ``customProperty`` gives them.
    """
    settings: Settings = {}
    legacy: Settings = {}
    for key, value in properties.items():
        if value is None or not is_settings_property(key):
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
            writes[variable_name(*found)] = value
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
