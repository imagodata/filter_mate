# -*- coding: utf-8 -*-
"""What is true of the project now, for the requests offered on the welcome of AGENT (core/agent/example_prompts.py).

Counts, names, cached field schema and map extent only: never ``featureCount()`` (a request to the server for a web
service), never a feature read.
Runs on the main thread; a layer destroyed meanwhile is left out, and a reading that fails altogether gives unknown
facts (the neutral requests), never an exception.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from ...core.agent.example_prompts import Facts
from ...core.agent.example_places import view_place
from ...core.domain.layer_kind import LayerKind

logger = logging.getLogger(__name__)

# Web map images: a basemap or a picture drawn by a service, not data to work on (nor an elevation model).
TILE_PROVIDERS = frozenset({"wms", "xyz", "wmts", "arcgismapserver"})
# Vector layers read from a web service: the tools do not read their features whole (statistics, a selection).
SERVICE_PROVIDERS = frozenset({"wfs", "oapif", "arcgisfeatureserver"})
# Vector layers read from a server or a database rather than from a file.
REMOTE_PROVIDERS = SERVICE_PROVIDERS | {"postgres", "mssql", "oracle", "hana"}
_ACTIVE_KINDS = {LayerKind.VECTOR: "vector", LayerKind.RASTER: "raster", LayerKind.POINT_CLOUD: "point_cloud"}


def _provider(layer: Any) -> str:
    try:
        return str(layer.providerType() or "").lower()
    except (AttributeError, RuntimeError):
        return ""


def _is_elevation(layer: Any) -> bool:
    """A raster that can be a terrain model: one band, of numbers rather than the bytes of a picture."""
    try:
        if layer.bandCount() != 1:
            return False
        from qgis.core import Qgis
        data_type = layer.dataProvider().dataType(1)
        return data_type != Qgis.DataType.Byte
    except (AttributeError, RuntimeError, TypeError):
        return False


def _is_derived(layer: Any) -> bool:
    """The source of the layer is a copy FilterMate cut to filter it (a raster or a point cloud has no filter string)."""
    try:
        from .coverage_layers.snapshots import registry
        return registry().get(layer.id()) is not None
    except Exception:  # the registry is the plugin's: nothing may come out of a reading of the facts
        return False


def _polygons(layer: Any) -> bool:
    try:
        from qgis.core import QgsWkbTypes
        return QgsWkbTypes.geometryType(layer.wkbType()) == QgsWkbTypes.GeometryType.PolygonGeometry
    except (AttributeError, RuntimeError, TypeError):
        return False


def _name(layer: Any) -> str:
    try:
        name = layer.name
        return str(name() if callable(name) else name)
    except (AttributeError, RuntimeError):
        return ""


def _fields(layer: Any) -> tuple:
    """The cached schema only: classify fields without fetching a feature, a count or unique values."""
    found = []
    try:
        for field in list(layer.fields())[:64]:
            name = field.name()
            if field.isNumeric():
                if name.lower() not in ('id', 'fid', 'ogc_fid', 'objectid') and not name.lower().endswith('_id'):
                    found.append((name, 'numeric'))
            elif any(word in field.typeName().lower() for word in ('string', 'text', 'char')):
                found.append((name, 'text'))
    except (AttributeError, RuntimeError, TypeError):
        pass
    # A label/name is a better example than an arbitrary code; ordering remains deterministic.
    preferred = ('name', 'nom', 'label', 'libelle', 'usage', 'type', 'category', 'categorie')
    return tuple(sorted(found, key=lambda item: (item[0].lower() not in preferred,)))


def _focus(project: Any, canvas: Any):
    if canvas is None:
        return None
    try:
        from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform
        transform = QgsCoordinateTransform(canvas.mapSettings().destinationCrs(),
                                           QgsCoordinateReferenceSystem('EPSG:4326'), project)
        box = transform.transformBoundingBox(canvas.extent())
        return view_place((box.xMinimum(), box.yMinimum(), box.xMaximum(), box.yMaximum()))
    except Exception:  # an invalid CRS/extent or a canvas closing must not suppress the layer facts
        return None


def read_facts(project: Any = None, active: Optional[Any] = None, canvas: Any = None) -> Facts:
    """The ``Facts`` of ``project`` (default: the open one) with ``active`` the active layer of the layer tree.

    A layer that is not valid (a file that was moved) is not counted. A basemap is a web map image, a rendered raster
    (a GDAL description of a WMS) or a vector tile layer; meshes and the like are layers, but not data to work on.

    Args:
        project: A ``QgsProject``; None for the one that is open.
        active: The layer selected in the layer tree, or None.

    Returns:
        The facts, or unknown facts when they cannot be read.
    """
    try:
        from qgis.core import QgsProject
        from .point_cloud_capability import is_non_analysis_raster, layer_kind_by_class
        project = project or QgsProject.instance()
        layers = tiles = vectors = rasters = clouds = selected = selected_local = filtered = remote = 0
        elevations = polygons = 0
        names = {"vector": [], "raster": [], "elevation": [], "cloud": [], "selected": []}
        found = {}  # layer id -> (kind of the active layer, elevation, local)
        for layer in list(project.mapLayers().values()):
            try:
                if not layer.isValid():
                    continue
                kind = layer_kind_by_class(layer)
                provider = _provider(layer)
                layers += 1
                kept, elevation, local = "other", False, provider not in SERVICE_PROVIDERS
                if kind is LayerKind.VECTOR_TILE or provider in TILE_PROVIDERS or (
                        kind is LayerKind.RASTER and is_non_analysis_raster(layer)):
                    tiles += 1
                elif kind is LayerKind.VECTOR:
                    vectors += 1
                    count = int(layer.selectedFeatureCount() or 0)
                    selected += count
                    selected_local += count if local else 0
                    remote += 1 if provider in REMOTE_PROVIDERS else 0
                    polygons += 1 if _polygons(layer) else 0
                    kept = "vector"
                    names["vector"].append(_name(layer))
                    if count:
                        names["selected"].append(_name(layer))
                elif kind is LayerKind.RASTER:
                    rasters += 1
                    elevation = _is_elevation(layer)
                    elevations += 1 if elevation else 0
                    kept = "raster"
                    names["raster"].append(_name(layer))
                    if elevation:
                        names["elevation"].append(_name(layer))
                elif kind is LayerKind.POINT_CLOUD:
                    clouds += 1
                    kept = "point_cloud"
                    names["cloud"].append(_name(layer))
                if kind in (LayerKind.VECTOR, LayerKind.POINT_CLOUD):
                    subset = getattr(layer, "subsetString", None)
                    filtered += 1 if (callable(subset) and subset()) or _is_derived(layer) else 0
                elif kind is LayerKind.RASTER and kept == "raster":
                    filtered += 1 if _is_derived(layer) else 0
                found[layer.id()] = (kept, elevation, local)
            except (AttributeError, RuntimeError):  # a layer deleted meanwhile: the others are still counted
                logger.debug("Welcome facts: a layer left out", exc_info=True)
        try:
            kept, elevation, local = found.get(active.id() if active is not None else "", ("", False, True))
        except RuntimeError:
            kept, elevation, local = "", False, True
        active_id = active.id() if kept in ("vector", "raster", "point_cloud") else ""
        active_name = _name(active) if active_id else ""
        vectors_first = [active_name] + [name for name in names["vector"] if name != active_name] if kept == "vector" else names["vector"]
        return Facts(known=True, layers=layers, tiles=tiles, vectors=vectors, rasters=rasters, point_clouds=clouds,
                     active=kept, selected=selected, filtered=filtered, remote=remote, elevations=elevations,
                     polygons=polygons, active_elevation=elevation, active_local=local,
                     selected_local=selected_local, active_id=active_id, active_name=active_name,
                     active_fields=_fields(active) if kept == "vector" else (), vector_names=tuple(vectors_first),
                     raster_name=next(iter(names["raster"]), ""), elevation_name=next(iter(names["elevation"]), ""),
                     cloud_name=next(iter(names["cloud"]), ""), selected_names=tuple(names["selected"]),
                     focus=_focus(project, canvas) if layers else None)
    except Exception:  # nothing may come out of a reading made while a project closes
        logger.debug("Welcome facts: not read", exc_info=True)
        return Facts.unknown()
