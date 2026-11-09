# -*- coding: utf-8 -*-
"""Driving QGIS beyond filters: the view, the selection, the layer tree, layers added or removed, open data.

Main thread only, plain dicts out. Nothing here is undone by the turn checkpoint: a zoom or a selection is
not a filter, and a layer removed is gone (the chat asks the user first).
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from ...core.agent.open_data import parse_results, resolve_platform, search_url, source_problem
from ...core.agent.sql_guard import expression_problem, quoted_identifiers
from ...core.domain.layer_kind import LayerKind
from .operations import layer_kind, resolve_layer

logger = logging.getLogger('FilterMate.ProjectControl')

MAX_COORDINATE = 1e9
MAX_PAYLOAD = 5 * 1024 * 1024


def _iface():
    try:
        from qgis.utils import iface
    except ImportError:
        return None
    return iface


def _canvas():
    iface = _iface()
    canvas = iface.mapCanvas() if iface is not None else None
    if canvas is None:
        raise ValueError("QGIS has no map canvas here (no window)")
    return canvas


def _summary(layer) -> Dict[str, Any]:
    crs = layer.crs()
    count = layer.featureCount() if hasattr(layer, 'featureCount') else -1
    return {'layer_id': layer.id(), 'name': layer.name(), 'layer_kind': layer_kind(layer).value,
            'provider_type': layer.providerType(), 'crs_authid': crs.authid() if crs is not None else '',
            'feature_count': count if isinstance(count, int) else -1}


def zoom_to(layer: Optional[str] = None, extent_wkt: Optional[str] = None, crs: Optional[str] = None,
            selected_only: bool = False) -> Dict[str, Any]:
    """Zoom the map to a layer, its selection, or an extent given as WKT; None of them = the full extent."""
    from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsCsException, QgsGeometry, QgsProject
    canvas = _canvas()
    project = QgsProject.instance()
    target = canvas.mapSettings().destinationCrs()
    if extent_wkt:
        geometry = QgsGeometry.fromWkt(extent_wkt)
        if geometry.isNull() or geometry.isEmpty():
            raise ValueError("the WKT could not be read")
        rect = geometry.boundingBox()
        if crs:
            source = QgsCoordinateReferenceSystem(crs)
            if not source.isValid():
                raise ValueError(f"unknown CRS {crs!r}")
            try:
                rect = QgsCoordinateTransform(source, target, project).transformBoundingBox(rect)
            except QgsCsException:
                raise ValueError("this area cannot be shown in the CRS of the map") from None
    elif layer:
        found = resolve_layer(layer)
        if found is None:
            raise ValueError(f"layer {layer!r} not found")
        if selected_only:
            if layer_kind(found) is not LayerKind.VECTOR or not found.selectedFeatureCount():
                raise ValueError(f"'{found.name()}' has no selected feature")
            rect = found.boundingBoxOfSelected()
        else:
            rect = found.extent()
        if rect.isNull() or rect.isEmpty() and not rect.width() and not rect.height() and not rect.xMinimum():
            raise ValueError(f"'{found.name()}' has nothing to zoom to")
        try:
            rect = QgsCoordinateTransform(found.crs(), target, project).transformBoundingBox(rect)
        except QgsCsException:
            raise ValueError(f"'{found.name()}' cannot be shown in the CRS of the map") from None
    else:
        canvas.zoomToFullExtent()
        return {'extent_wkt': canvas.extent().asWktPolygon(), 'scale': canvas.scale()}
    if max(abs(rect.xMinimum()), abs(rect.xMaximum()), abs(rect.yMinimum()), abs(rect.yMaximum())) > MAX_COORDINATE:
        raise ValueError("this area is out of range")
    if rect.isEmpty():
        rect.grow(10)
    canvas.setExtent(rect)
    canvas.refresh()
    return {'extent_wkt': canvas.extent().asWktPolygon(), 'scale': canvas.scale()}


def select_features(layer: str, expression: str = '', clear: bool = False, add: bool = False) -> Dict[str, Any]:
    """Select the features of a vector layer matching a QGIS expression (not SQL); ``clear`` empties the selection.

    Only plain conditions: ``select_features`` is reachable by a model, and QGIS expressions can read the
    environment and the disk and write to SQLite.
    """
    from qgis.core import QgsExpression, QgsVectorLayer
    found = resolve_layer(layer)
    if found is None:
        raise ValueError(f"layer {layer!r} not found")
    if layer_kind(found) is not LayerKind.VECTOR:
        raise ValueError(f"'{found.name()}' is not a vector layer")
    if clear:
        found.removeSelection()
    else:
        problem = expression_problem(expression or '')
        if problem:
            raise ValueError(f"this expression cannot be used: {problem}")
        check = QgsExpression(expression)
        if check.hasParserError():
            raise ValueError(f"invalid QGIS expression: {check.parserErrorString()}")
        known = {field.name().lower() for field in found.fields()}
        unknown = sorted({name for name in quoted_identifiers(expression) if name.lower() not in known})
        if unknown:  # QGIS evaluates them to nothing: the user's selection would just be emptied
            raise ValueError(f"unknown field(s): {', '.join(unknown)}")
        behavior = QgsVectorLayer.SelectBehavior.AddToSelection if add else QgsVectorLayer.SelectBehavior.SetSelection
        found.selectByExpression(expression, behavior)
    return {'layer_id': found.id(), 'layer_name': found.name(), 'selected_count': found.selectedFeatureCount()}


def set_layers_visibility(layers: List[str], visible: bool) -> Dict[str, Any]:
    """Check or uncheck layers in the layer tree."""
    from qgis.core import QgsProject
    root = QgsProject.instance().layerTreeRoot()
    done, failed = [], {}
    for reference in layers:
        found = resolve_layer(reference)
        node = root.findLayer(found.id()) if found is not None else None
        if node is None:
            failed[str(reference)] = 'layer not found'
            continue
        node.setItemVisibilityChecked(bool(visible))
        done.append(found.name())
    return {'done': done, 'failed': failed, 'visible': bool(visible)}


def add_layer(source: str, name: str = '', kind: str = 'vector') -> Dict[str, Any]:
    """Add a layer from a local data file or a public https URL; returns its summary.

    Raises:
        ValueError: Any other source, or one that cannot be opened.
    """
    from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer
    problem = source_problem(source, allow_remote=True)
    if problem:
        raise ValueError(problem)
    if kind not in ('vector', 'raster'):
        raise ValueError("kind is vector or raster")
    if not source.lower().startswith('https://') and not os.path.isfile(source.split('|', 1)[0]):
        raise ValueError("this file does not exist")
    title = (name or '').strip() or source.rsplit('/', 1)[-1].split('?', 1)[0][:80] or 'layer'
    layer = QgsVectorLayer(source, title, 'ogr') if kind == 'vector' else QgsRasterLayer(source, title, 'gdal')
    if not layer.isValid():
        # Nothing more is read from an invalid layer: its provider and its error crashed QGIS 3.22.
        raise ValueError(f"the source could not be opened as a {kind} layer")
    QgsProject.instance().addMapLayer(layer)
    return _summary(layer)


def remove_layers(layers: List[str]) -> Dict[str, Any]:
    """Remove layers from the project (their files stay)."""
    from qgis.core import QgsProject
    project = QgsProject.instance()
    done, failed = [], {}
    for reference in layers:
        found = resolve_layer(reference)
        if found is None:
            failed[str(reference)] = 'layer not found'
            continue
        done.append(found.name())
        project.removeMapLayer(found.id())
    return {'done': done, 'failed': failed}


def search_open_data(query: str, platform: str = 'datagouv', limit: int = 10, extra_domains: str = '') -> Dict[str, Any]:
    """Ask an allowed open data platform for datasets; the answer is reduced to titles and geo resources."""
    from qgis.core import QgsBlockingNetworkRequest
    from qgis.PyQt.QtCore import QUrl
    from qgis.PyQt.QtNetwork import QNetworkRequest
    kind, base = resolve_platform(platform, extra_domains)
    url = search_url(kind, base, query, limit)
    request = QNetworkRequest(QUrl(url))
    request.setRawHeader(b'Accept', b'application/json')
    blocking = QgsBlockingNetworkRequest()
    code = blocking.get(request, True)
    if code != QgsBlockingNetworkRequest.ErrorCode.NoError:
        raise ValueError(f"{platform} did not answer: {blocking.errorMessage() or 'network error'}")
    content = bytes(blocking.reply().content())
    if len(content) > MAX_PAYLOAD:
        raise ValueError(f"{platform} answered with too much data")
    try:
        payload = json.loads(content.decode('utf-8'))
    except (ValueError, RecursionError):
        raise ValueError(f"{platform} answered with something that is not JSON") from None
    datasets = parse_results(kind, payload, base)
    return {'platform': platform, 'query': query, 'datasets': datasets, 'count': len(datasets)}
