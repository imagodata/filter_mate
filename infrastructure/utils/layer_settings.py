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
from typing import Any, Collection, Dict, Iterable, Optional

try:
    from ...core.domain.project_layer_settings import (
        GROUPS, LEGACY_GROUPS, PREFIX, SCOPE, VALUES, VERSION, VERSION_KEY, drop_missing_layers, is_settings_property,
        legacy_moves, project_settings, repaired_variable_names, same_setting)
except ImportError:  # loaded outside the plugin package (unit tests)
    from core.domain.project_layer_settings import (
        GROUPS, LEGACY_GROUPS, PREFIX, SCOPE, VALUES, VERSION, VERSION_KEY, drop_missing_layers, is_settings_property,
        legacy_moves, project_settings, repaired_variable_names, same_setting)
from .type_utils import return_typed_value

logger = logging.getLogger('FilterMate.Infrastructure.LayerSettings')


def load(text: str) -> Any:
    """A stored text typed as the SQLite's values are."""
    return return_typed_value(text, 'load')[0]


def same(one: Any, other: Any) -> bool:
    """Two stored forms of the same setting (``'["a"]'`` and ``["a"]``)."""
    return same_setting(one, other, load)


def is_setting_variable(name: Any) -> bool:
    """``filterMate_exploring_*`` or ``filterMate_filtering_*``: a setting the project carries."""
    return isinstance(name, str) and any(name.startswith(f"{PREFIX}{group}_") for group in GROUPS)


def _project(project: Any = None) -> Any:
    if project is not None:
        return project
    from qgis.core import QgsProject
    return QgsProject.instance()


def project_file_writable(project: Any = None) -> bool:
    """The project has a file this computer can write: what it carries can be saved."""
    try:
        path = _project(project).fileName()
    except (RuntimeError, AttributeError):
        return False
    return bool(path) and os.access(path, os.W_OK)


def project_is_truth(project: Any = None) -> bool:
    """The settings the project carries win over this computer's SQLite.

    Only for values this version wrote (the project entry of the version), and only in a project that can be saved:
    otherwise the SQLite wins where it has a setting, and the project gives the others.
    """
    project = _project(project)
    if not project_file_writable(project):
        return False
    try:
        version, _found = project.readNumEntry(SCOPE, VERSION_KEY, 0)
    except (RuntimeError, AttributeError, TypeError):
        return False
    return version >= VERSION


def settings_written(project: Any = None) -> bool:
    """A setting of a layer changed in the project: the project is modified (a layer variable alone is no change for
    QGIS, which would not ask to save it), and says the version of its settings. Nothing in a project that cannot be
    saved (read-only, or no file yet).
    """
    project = _project(project)
    if not project_file_writable(project):
        return False
    try:
        if project.readNumEntry(SCOPE, VERSION_KEY, 0)[0] != VERSION:
            project.writeEntry(SCOPE, VERSION_KEY, VERSION)
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


def remove_filtermate_variables(layer: Any, names: Optional[Collection[str]] = None) -> int:
    """Remove variables of FilterMate from ``layer``: ``names``, or all of them. Returns how many were there."""
    removed = 0
    keys = layer.customPropertyKeys()
    for key in keys:
        if not is_settings_property(key) and not (isinstance(key, str) and key.startswith(f"{VALUES}{PREFIX}")):
            continue
        if names is not None and key[len(VALUES):] not in names:
            continue
        layer.removeCustomProperty(key)
        removed += 1
    return removed


def settings_change(layer_id: str, variables: Dict[str, Any], project: Any = None) -> bool:
    """Writing ``variables`` changes a setting the project carries (not only the form it is stored in)."""
    try:
        layer = _project(project).mapLayer(layer_id)
        if layer is None:
            return False
        return any(is_setting_variable(name) and not same(layer.customProperty(f"{VALUES}{name}"), value)
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
        settings_written(project)
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


def capture_layer_settings(layers: Iterable[Any] = (), known: Iterable[str] = (),
                           layer_ids: Optional[Collection[str]] = None) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Main thread: the settings each of ``layers`` carries in the project, for the task that registers them.

    The names of FilterMate leave the variables of QGIS, and the legacy names are moved, on the way.

    Args:
        layers: Layers the task is given (ids and other items are left out).
        known: Ids of the layers registered already: the task leaves them, and their variables are the current ones.
        layer_ids: Ids of the layers of the project (default: QgsProject.instance()): a layer to filter that is not
            one of them is left out.

    Returns:
        ``{layer_id: {group: {key: value as stored}}}``, only for layers that carry some.
    """
    known = set(known or ())
    if layer_ids is None:
        try:
            layer_ids = set(_project().mapLayers().keys())
        except Exception:  # catch-all safety net: the lists are then kept as they are
            layer_ids = None
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
        if settings and layer_ids is not None:
            settings = drop_missing_layers(settings, layer_ids, load)
        if settings:
            captured[layer_id] = settings
    return captured


__all__ = ['GROUPS', 'LEGACY_GROUPS', 'capture_layer_settings', 'clear_filtermate_variables', 'is_setting_variable',
           'note_direct_write', 'settings_change',
           'project_file_writable', 'project_is_truth', 'remove_filtermate_variables', 'same', 'settings_written',
           'write_epoch', 'written_since']
