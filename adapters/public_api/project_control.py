# -*- coding: utf-8 -*-
"""Driving QGIS beyond filters: the view, the selection, the layer tree, layers added or removed, open data.

Main thread only, plain dicts out. Nothing here undoes itself: the chat captures the selections, the
visibility and the layers added or removed before each call (``adapters/agent/turn_effects.py``) and brings
them back with the turn; a zoom is not undone, and a memory layer removed is gone (the chat asks first).
"""
from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from ...core.agent.open_data import (
    KIND_STAC, KIND_WFS, follow_redirects, gdal_source, parse_results, parse_stac_items, resolve_platform, search_url,
    source_problem, stac_search_body, valid_day,
)
from ...core.agent.sql_guard import expression_problem, quoted_identifiers
from ...core.domain.layer_kind import LayerKind
from ..agent.bounded_http import HttpFailure, fetch
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


def _summary(layer, count_features: bool = True) -> Dict[str, Any]:
    crs = layer.crs()
    # On a web service the count is one more request, blocking and out of reach of Stop.
    count = layer.featureCount() if count_features and hasattr(layer, 'featureCount') else -1
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


def _head(url: str):
    """``(status, location)`` of a URL, without reading it."""
    try:
        reply = fetch(url, headers={'Range': 'bytes=0-0'}, headers_only=True, timeout_ms=20_000)
    except HttpFailure as exc:
        raise ValueError(f"this link did not answer: {exc}") from None
    return reply.status, reply.headers.get('location', '')


@contextmanager
def _gdal_time_limits(active: bool):
    """GDAL reads with its own HTTP client: the timeout of QGIS does not reach it, and a mute server would hang it."""
    try:
        from osgeo import gdal
    except ImportError:
        gdal = None
    if gdal is None or not active:
        yield
        return
    names = ('GDAL_HTTP_TIMEOUT', 'GDAL_HTTP_CONNECTTIMEOUT', 'GDAL_HTTP_LOW_SPEED_TIME', 'GDAL_HTTP_LOW_SPEED_LIMIT')
    previous = [gdal.GetThreadLocalConfigOption(name) for name in names]
    for name, value in zip(names, ('60', '15', '20', '100')):
        gdal.SetThreadLocalConfigOption(name, value)
    try:
        yield
    finally:
        for name, value in zip(names, previous):
            gdal.SetThreadLocalConfigOption(name, value)


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
    remote = source.lower().startswith('https://')
    opened = gdal_source(follow_redirects(source, _head), kind) if remote else source
    with _gdal_time_limits(remote):
        layer = QgsVectorLayer(opened, title, 'ogr') if kind == 'vector' else QgsRasterLayer(opened, title, 'gdal')
    if not layer.isValid():
        # Nothing more is read from an invalid layer: its provider and its error crashed QGIS 3.22.
        raise ValueError(f"the source could not be opened as a {kind} layer")
    QgsProject.instance().addMapLayer(layer)
    return _summary(layer)


def search_imagery(bbox: Optional[List[float]] = None, start: str = '', end: str = '', max_cloud: float = 20.0,
                   collections: Optional[List[str]] = None, limit: int = 5, platform: str = 'earth_search',
                   extra_domains: str = '') -> Dict[str, Any]:
    """Scenes of a STAC catalog over an area (default: the map), with the GeoTIFF of each one for ``add_layer``."""
    from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsCsException, QgsProject
    kind, base = resolve_platform(platform, extra_domains)
    if kind != KIND_STAC:
        raise ValueError(f"{platform} is not a satellite imagery catalog")
    if not bbox:
        canvas = _canvas()
        wgs84 = QgsCoordinateReferenceSystem('EPSG:4326')
        try:
            rect = QgsCoordinateTransform(canvas.mapSettings().destinationCrs(), wgs84, QgsProject.instance()) \
                .transformBoundingBox(canvas.extent())
        except QgsCsException:
            raise ValueError("the map extent cannot be expressed in longitude and latitude") from None
        bbox = [max(rect.xMinimum(), -180.0), max(rect.yMinimum(), -90.0), min(rect.xMaximum(), 180.0), min(rect.yMaximum(), 90.0)]
    if not valid_day(start) or not valid_day(end):
        raise ValueError("dates are written YYYY-MM-DD")
    if len(bbox) != 4 or not (-180 <= bbox[0] <= bbox[2] <= 180 and -90 <= bbox[1] <= bbox[3] <= 90):
        raise ValueError("bbox is [west, south, east, north] in degrees")
    default = ['sentinel-2-l2a'] if platform == 'earth_search' else []
    body = stac_search_body(collections or default, list(bbox), start, end, max_cloud, limit)
    payload = _json_answer(platform, f"{base}/search", json.dumps(body).encode('utf-8'), 'application/geo+json')
    scenes = parse_stac_items(payload)
    return {'platform': platform, 'query': f"{body.get('datetime', 'any date')} over {bbox}", 'datasets': scenes, 'count': len(scenes)}


def add_service_layer(platform: str, typename: str, name: str = '', extra_domains: str = '') -> Dict[str, Any]:
    """Add a layer of a WFS platform the user allowed: the plugin builds the source, for a name the service lists."""
    from qgis.core import QgsProject
    from . import wfs_catalog
    kind, base = resolve_platform(platform, extra_domains)
    if kind != KIND_WFS:
        raise ValueError(f"{platform} is not a WFS service: use add_layer with one of its resources")
    layer = wfs_catalog.open_layer(base, typename, name)
    if not layer.isValid():
        raise ValueError(f"{typename} could not be opened")  # nothing more is read from an invalid layer
    QgsProject.instance().addMapLayer(layer)
    return _summary(layer, count_features=False)


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


def _json_answer(platform: str, url: str, body: Optional[bytes] = None, accept: str = 'application/json') -> Any:
    headers = {'Accept': accept}
    if body is not None:
        headers['Content-Type'] = 'application/json'
    try:
        reply = fetch(url, body=body, headers=headers, max_bytes=MAX_PAYLOAD, timeout_ms=45_000)
    except HttpFailure as exc:
        raise ValueError(f"{platform} did not answer: {exc}") from None
    if reply.status != 200:
        raise ValueError(f"{platform} answered with an error ({reply.status})")
    try:
        return json.loads(reply.content.decode('utf-8'))
    except (ValueError, RecursionError):
        raise ValueError(f"{platform} answered with something that is not JSON") from None


def search_open_data(query: str, platform: str = 'datagouv', limit: int = 10, extra_domains: str = '') -> Dict[str, Any]:
    """Ask an allowed open data platform for datasets; the answer is reduced to titles and geo resources."""
    kind, base = resolve_platform(platform, extra_domains)
    if kind == KIND_WFS:
        from . import wfs_catalog
        datasets = wfs_catalog.search(base, query, max(1, min(int(limit), 20)))
        return {'platform': platform, 'query': query, 'datasets': datasets, 'count': len(datasets)}
    url = search_url(kind, base, query, limit)
    payload = _json_answer(platform, url)
    datasets = parse_results(kind, payload, base)
    return {'platform': platform, 'query': query, 'datasets': datasets, 'count': len(datasets)}
