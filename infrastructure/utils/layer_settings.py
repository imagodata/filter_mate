# -*- coding: utf-8 -*-
"""
The FilterMate settings a project carries for its layers, read on the main thread for a task (2026-11-24).

Once a project is saved, its file is the truth for the ``exploring`` and ``filtering`` settings of its layers
(``core.domain.project_layer_settings``). They are custom properties of the layers: the task that registers the layers
must not read a layer from its worker (QGIS 4.3 reports it, see ``layer_facts``), so they are read here when the task
is created, and the worker puts them over the copy of this computer's SQLite.
"""

import logging
from typing import Any, Dict, Iterable

try:
    from ...core.domain.project_layer_settings import (
        VALUES, is_settings_property, legacy_moves, project_settings)
except ImportError:  # loaded outside the plugin package (unit tests)
    from core.domain.project_layer_settings import VALUES, is_settings_property, legacy_moves, project_settings

logger = logging.getLogger('FilterMate.Infrastructure.LayerSettings')


def _move_legacy(layer: Any, properties: Dict[str, Any]) -> None:
    """Put the legacy values of ``layer`` under their right names, once (the next reading finds none)."""
    writes, removals = legacy_moves(properties)
    if not writes and not removals:
        return
    names = layer.customProperty('variableNames', [])
    if not isinstance(names, list):
        names = [names] if names else []
    added = [name for name in writes if name not in names]
    if added:
        layer.setCustomProperty('variableNames', names + added)
    for name, value in writes.items():
        layer.setCustomProperty(f"{VALUES}{name}", value)
    # Their names stay in variableNames: QGIS pairs it by position with its own list of values.
    for name in removals:
        layer.removeCustomProperty(f"{VALUES}{name}")
    logger.info(f"Layer {layer.id()}: {len(removals)} FilterMate setting(s) of a legacy name moved")


def capture_layer_settings(layers: Iterable[Any] = (), known: Iterable[str] = ()) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Main thread: the settings each of ``layers`` carries in the project, for the task that registers them.

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
