# -*- coding: utf-8 -*-
"""What is true of the project now, for the requests offered on the welcome of AGENT (core/agent/example_prompts.py).

Counts and flags only: never ``featureCount()`` (a request to the server for a web service), never a feature read.
Runs on the main thread; a layer destroyed meanwhile is left out, and a reading that fails altogether gives unknown
facts (the neutral requests), never an exception.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from ...core.agent.example_prompts import Facts
from ...core.domain.layer_kind import LayerKind

logger = logging.getLogger(__name__)

# Web map images: a basemap or a picture drawn by a service, not data to work on (nor an elevation model).
TILE_PROVIDERS = frozenset({"wms", "xyz", "wmts", "arcgismapserver"})
# Vector layers read from a server or a database rather than from a file.
REMOTE_PROVIDERS = frozenset({"wfs", "oapif", "arcgisfeatureserver", "postgres", "mssql", "oracle", "hana"})
_ACTIVE_KINDS = {LayerKind.VECTOR: "vector", LayerKind.RASTER: "raster", LayerKind.POINT_CLOUD: "point_cloud"}


def _provider(layer: Any) -> str:
    try:
        return str(layer.providerType() or "").lower()
    except (AttributeError, RuntimeError):
        return ""


def read_facts(project: Any = None, active: Optional[Any] = None) -> Facts:
    """The ``Facts`` of ``project`` (default: the open one) with ``active`` the active layer of the layer tree.

    Args:
        project: A ``QgsProject``; None for the one that is open.
        active: The layer selected in the layer tree, or None.

    Returns:
        The facts, or unknown facts when they cannot be read.
    """
    try:
        from qgis.core import QgsProject
        from .point_cloud_capability import layer_kind_by_class
        project = project or QgsProject.instance()
        layers = tiles = vectors = rasters = clouds = selected = filtered = remote = 0
        kinds = {}
        for layer in list(project.mapLayers().values()):
            try:
                kind = layer_kind_by_class(layer)
                provider = _provider(layer)
                layers += 1
                tile = provider in TILE_PROVIDERS
                if tile:
                    tiles += 1
                elif kind is LayerKind.VECTOR:
                    vectors += 1
                    selected += int(layer.selectedFeatureCount() or 0)
                    remote += 1 if provider in REMOTE_PROVIDERS else 0
                elif kind is LayerKind.RASTER:
                    rasters += 1
                elif kind is LayerKind.POINT_CLOUD:
                    clouds += 1
                if kind in (LayerKind.VECTOR, LayerKind.POINT_CLOUD):
                    subset = getattr(layer, "subsetString", None)
                    filtered += 1 if callable(subset) and subset() else 0
                kinds[layer.id()] = "other" if tile else _ACTIVE_KINDS.get(kind, "other")
            except (AttributeError, RuntimeError):  # a layer deleted meanwhile: the others are still counted
                logger.debug("Welcome facts: a layer left out", exc_info=True)
        try:
            active_id = active.id() if active is not None else ""
        except RuntimeError:
            active_id = ""
        return Facts(known=True, layers=layers, tiles=tiles, vectors=vectors, rasters=rasters, point_clouds=clouds,
                     active=kinds.get(active_id, ""), selected=selected, filtered=filtered, remote=remote)
    except Exception:  # nothing may come out of a reading made while a project closes
        logger.debug("Welcome facts: not read", exc_info=True)
        return Facts.unknown()
