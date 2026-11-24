# -*- coding: utf-8 -*-
"""
The FilterMate settings a project carries for its layers, read and written on the main thread (2026-11-24).

Once a project is saved, its file is the truth for the ``exploring`` and ``filtering`` settings of its layers
(``core.domain.project_layer_settings``). They are custom properties of the layers: the task that registers the layers
must not read a layer from its worker (QGIS 4.3 reports it, see ``layer_facts``), so they are read here when the task
is created, and the worker puts them over the copy of this computer's SQLite, or under it (:func:`project_is_truth`).
"""

import logging
import os
import re
from typing import Any, Collection, Dict, Iterable, Optional, Set

try:
    from ...core.domain.project_layer_settings import (
        GROUPS, LEGACY_GROUPS, PREFIX, VALUES, VERSION, VERSION_PROPERTY, is_settings_property, legacy_moves,
        project_settings, repaired_variable_names, same_setting)
except ImportError:  # loaded outside the plugin package (unit tests)
    from core.domain.project_layer_settings import (
        GROUPS, LEGACY_GROUPS, PREFIX, VALUES, VERSION, VERSION_PROPERTY, is_settings_property, legacy_moves,
        project_settings, repaired_variable_names, same_setting)
from .type_utils import return_typed_value

logger = logging.getLogger('FilterMate.Infrastructure.LayerSettings')


def load(text: str) -> Any:
    """A stored text typed as the SQLite's values are."""
    return return_typed_value(text, 'load')[0]


def _key(name: Any) -> str:
    """The key of a variable ``filterMate_<group>_<key>`` ("" for another name)."""
    for group in GROUPS:
        head = f"{PREFIX}{group}_"
        if isinstance(name, str) and name.startswith(head):
            return name[len(head):]
    return ""


def same(one: Any, other: Any, name: str = "") -> bool:
    """Two stored forms of the same setting (``'["a"]'`` and ``["a"]``) of the variable ``name``."""
    return same_setting(one, other, load, _key(name))


def is_setting_variable(name: Any) -> bool:
    """``filterMate_exploring_*`` or ``filterMate_filtering_*``: a setting the project carries."""
    return bool(_key(name))


def _project(project: Any = None) -> Any:
    if project is not None:
        return project
    from qgis.core import QgsProject
    return QgsProject.instance()


_URI = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]+:")  # postgresql:, geopackage:... (not a drive letter)


def project_file_writable(project: Any = None) -> bool:
    """The project has a file this computer can write, or is stored in a database (whose writing QGIS checks)."""
    project = _project(project)
    try:
        path = project.fileName()
        storage = project.projectStorage() if hasattr(project, "projectStorage") else None
    except (RuntimeError, AttributeError):
        return False
    if not path:
        return False
    if storage is not None or _URI.match(path):
        return True
    return os.access(path, os.W_OK)


def layer_is_truth(layer: Any, project: Any = None) -> bool:
    """The settings the project carries for ``layer`` win over this computer's SQLite.

    Only for values this version wrote for the layer (its :data:`VERSION_PROPERTY`), and only in a project that can be
    saved: otherwise the SQLite wins where it has a setting, and the project gives the others.
    """
    try:
        marked = layer.customProperty(VERSION_PROPERTY, 0)
        return int(marked or 0) >= VERSION and project_file_writable(project)
    except (RuntimeError, AttributeError, TypeError, ValueError):
        return False


def settings_written(project: Any = None, layer_id: Optional[str] = None, changed: bool = True) -> bool:
    """This version wrote the settings of a layer: the layer says so (:data:`VERSION_PROPERTY`), and when a setting
    changed the project is modified (a layer variable alone is no change for QGIS, which would not ask to save it).
    Nothing is marked modified in a project that cannot be saved.

    Returns:
        True when the project was marked modified.
    """
    project = _project(project)
    try:
        layer = project.mapLayer(layer_id) if layer_id else None
        if layer is not None and layer.customProperty(VERSION_PROPERTY) != VERSION:
            layer.setCustomProperty(VERSION_PROPERTY, VERSION)
        if not changed or not project_file_writable(project):
            return False
        project.setDirty(True)
    except (RuntimeError, AttributeError, TypeError) as exc:
        logger.debug(f"Project not marked modified: {exc}")
        return False
    return True


# The variables the panel wrote, by (layer id, name), and when: a registration queued before must not overwrite them
_DIRECT_WRITES: Dict[Any, int] = {}
_EPOCH = [0]


def note_direct_write(layer_id: str, name: str) -> None:
    """The panel wrote (or is about to write) the variable ``name`` of a layer."""
    _EPOCH[0] += 1
    _DIRECT_WRITES[(layer_id, name)] = _EPOCH[0]


def write_epoch() -> int:
    """Now, for :func:`written_since`."""
    return _EPOCH[0]


def written_since(layer_id: str, name: str, epoch: int) -> bool:
    """The panel wrote the variable since ``epoch``."""
    return _DIRECT_WRITES.get((layer_id, name), 0) > epoch


def filtermate_variable_names(layer: Any) -> list:
    """The names of the variables of FilterMate ``layer`` carries: ``filterMate_*`` and the legacy ones
    (``exploring_*``, ``filtering_*``, ``infos_*``)."""
    return [key[len(VALUES):] for key in layer.customPropertyKeys()
            if is_settings_property(key) or (isinstance(key, str) and key.startswith(f"{VALUES}{PREFIX}"))]


def remove_filtermate_variables(layer: Any, names: Optional[Collection[str]] = None) -> int:
    """Remove variables of FilterMate from ``layer``: ``names``, or all of them. Returns how many were there."""
    removed = 0
    for name in filtermate_variable_names(layer):
        if names is not None and name not in names:
            continue
        layer.removeCustomProperty(f"{VALUES}{name}")
        removed += 1
    return removed


def settings_change(layer_id: str, variables: Dict[str, Any], project: Any = None) -> bool:
    """Writing ``variables`` changes a setting the project carries (not only the form it is stored in)."""
    try:
        layer = _project(project).mapLayer(layer_id)
        if layer is None:
            return False
        return any(is_setting_variable(name) and not same(layer.customProperty(f"{VALUES}{name}"), value, name)
                   for name, value in variables.items())
    except (RuntimeError, AttributeError) as exc:
        logger.debug(f"Settings of {layer_id} not compared: {exc}")
        return False


def clear_filtermate_variables(layer_id: str, project: Any = None) -> int:
    """Main thread: remove every variable of FilterMate from a layer of the project (a fresh reload)."""
    try:
        layer = _project(project).mapLayer(layer_id)
        removed = remove_filtermate_variables(layer) if layer is not None else 0
    except (RuntimeError, AttributeError) as exc:
        logger.debug(f"Variables of {layer_id} not cleared: {exc}")
        return 0
    if removed:
        settings_written(project, layer_id)
    return removed


def _repair_variable_names(layer: Any) -> None:
    """Take the names of FilterMate out of the variables of QGIS (``variableNames``), where they broke the pairing of
    the user's variables with their values."""
    ours = {key[len(VALUES):] for key in layer.customPropertyKeys() if isinstance(key, str) and key.startswith(VALUES)}
    repaired = repaired_variable_names(layer.customProperty('variableNames'), layer.customProperty('variableValues'),
                                       ours)
    if repaired is not None:
        layer.setCustomProperty('variableNames', repaired[0])
        layer.setCustomProperty('variableValues', repaired[1])


def _move_legacy(layer: Any, properties: Dict[str, Any]) -> None:
    """Put the legacy values of ``layer`` under their right names, once (the next reading finds none)."""
    writes, removals = legacy_moves(properties)
    for name, value in writes.items():
        layer.setCustomProperty(f"{VALUES}{name}", value)
    for name in removals:
        layer.removeCustomProperty(f"{VALUES}{name}")
    if removals:
        logger.info(f"Layer {layer.id()}: {len(removals)} FilterMate setting(s) of a legacy name moved")


def capture_layer_settings(layers: Iterable[Any] = (), known: Iterable[str] = ()) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Main thread: the settings each of ``layers`` carries in the project, for the task that registers them.

    The names of FilterMate leave the variables of QGIS, and the legacy names are moved, on the way.

    Args:
        layers: Layers the task is given (ids and other items are left out).
        known: Ids of the layers registered already: the task leaves them, and their variables are the current ones.

    Returns:
        ``{layer_id: {group: {key: value as stored}}}``, only for layers that carry some.
    """
    known = set(known or ())
    captured = {}
    for layer in layers or ():
        if isinstance(layer, str):
            continue
        try:
            layer_id = layer.id()
            if layer_id in known:
                continue
            properties = {key: layer.customProperty(key) for key in layer.customPropertyKeys()
                          if is_settings_property(key)}
            _repair_variable_names(layer)
            if not properties:
                continue
            settings = project_settings(properties)
            _move_legacy(layer, properties)
        except (AttributeError, RuntimeError, TypeError) as exc:  # a deleted layer, or not a map layer
            logger.debug(f"Settings of a layer not read: {exc}")
            continue
        if settings:
            captured[layer_id] = settings
    return captured


def truth_layer_ids(layers: Iterable[Any] = (), project: Any = None) -> Set[str]:
    """Main thread: the ids of ``layers`` whose settings in the project win over this computer's SQLite."""
    found = set()
    for layer in layers or ():
        if isinstance(layer, str):
            continue
        try:
            if layer_is_truth(layer, project):
                found.add(layer.id())
        except (AttributeError, RuntimeError):
            continue
    return found


def project_layer_ids(project: Any = None) -> Optional[Set[str]]:
    """Main thread: the ids of the layers of the project (None when it cannot be read)."""
    try:
        return set(_project(project).mapLayers().keys())
    except Exception:  # catch-all safety net: the lists of layers are then used as they are
        return None


__all__ = ['GROUPS', 'LEGACY_GROUPS', 'capture_layer_settings', 'clear_filtermate_variables',
           'filtermate_variable_names', 'is_setting_variable',
           'layer_is_truth', 'note_direct_write', 'project_file_writable', 'project_layer_ids',
           'remove_filtermate_variables', 'same', 'settings_change', 'settings_written', 'truth_layer_ids',
           'write_epoch', 'written_since']
