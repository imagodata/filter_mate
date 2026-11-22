# -*- coding: utf-8 -*-
"""make_cartogram: a new layer whose areas show a field of a layer, as it is filtered now.

Main thread only, plain dicts out. The features are read in a projected CRS: the layer's own, or for a layer in
degrees an equal-area projection made for its extent (``core/agent/projections.custom``), since a cartogram compares
areas. The algorithms are ``core/agent/cartograms.py``. The result is a GeoPackage of the temporary folder of QGIS,
added at the top of the layer tree with the fields of the layer and ``cartogram_value``; undoing the turn removes it.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from ...core.agent.cartograms import (
    DEFAULT_ITERATIONS, KINDS, CartogramError, contiguous, errors, noncontiguous, symbol_ring, symbols,
)
from .operations import resolve_layer

logger = logging.getLogger("FilterMate.agent")

MAX_FEATURES = 5000
VALUE_FIELD = "cartogram_value"


def _rings(geometry) -> List[List[Any]]:
    """The polygons of a geometry as lists of rings (numpy arrays), curves made straight."""
    import numpy as np
    if geometry.isMultipart():
        polygons = geometry.asMultiPolygon()
    else:
        polygons = [geometry.asPolygon()]
    return [[np.array([(point.x(), point.y()) for point in ring], dtype=float) for ring in polygon if len(ring) >= 4]
            for polygon in polygons if polygon]


def _working_crs(layer):
    """A projected CRS to compare areas in: the layer's, or an equal-area projection made for its extent."""
    from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject
    from ...core.agent.projections import custom
    crs = layer.crs()
    if crs.isValid() and not crs.isGeographic():
        return crs, ""
    wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
    box = QgsCoordinateTransform(crs, wgs84, QgsProject.instance()).transformBoundingBox(layer.extent())
    bounds = (max(-180.0, box.xMinimum()), max(-89.0, box.yMinimum()), min(180.0, box.xMaximum()),
              min(89.0, box.yMaximum()))
    text, name, _ = custom(bounds, "equal-area")
    made = QgsCoordinateReferenceSystem(text)
    if not made.isValid():
        raise CartogramError("no projected CRS could be made for this layer: set_project_crs, then try again")
    return made, name


def _read(layer, field: str, polygons: bool) -> Tuple[List[Dict[str, Any]], List[Any], Any, str]:
    from qgis.core import QgsCoordinateTransform, QgsFeatureRequest, QgsGeometry, QgsProject, QgsWkbTypes
    index = layer.fields().lookupField(field)
    if index < 0:
        raise CartogramError(f"no field {field!r} in '{layer.name()}': see describe_layer")
    if not layer.fields().at(index).isNumeric():
        raise CartogramError(f"'{field}' of '{layer.name()}' is not numeric: a cartogram shows quantities")
    count = layer.featureCount()
    if count > MAX_FEATURES:
        raise CartogramError(f"'{layer.name()}' shows {count} features: {MAX_FEATURES} at most, filter it first")
    crs, made_for = _working_crs(layer)
    transform = QgsCoordinateTransform(layer.crs(), crs, QgsProject.instance())
    features, sources = [], []
    for feature in layer.getFeatures(QgsFeatureRequest().setLimit(MAX_FEATURES + 1)):
        geometry = QgsGeometry(feature.geometry())
        if geometry.isNull() or geometry.isEmpty():
            continue
        if QgsWkbTypes.isCurvedType(geometry.wkbType()):
            geometry = QgsGeometry(geometry.constGet().segmentize())
        geometry.transform(transform)
        value = feature.attribute(index)
        value = None if value is None or (hasattr(value, "isNull") and value.isNull()) else value
        kind = QgsWkbTypes.geometryType(geometry.wkbType())
        polygon_type = getattr(QgsWkbTypes, "PolygonGeometry", None) or QgsWkbTypes.GeometryType.PolygonGeometry
        if kind == polygon_type:
            parts = _rings(geometry)
        elif polygons:
            raise CartogramError(f"'{layer.name()}' is not a polygon layer: dorling or demers for points")
        else:  # a point: a tiny square, only its centroid counts for circles and squares
            import numpy as np
            point = geometry.centroid().asPoint()
            parts = [[np.array([(point.x(), point.y()), (point.x() + 1e-3, point.y()),
                                (point.x() + 1e-3, point.y() + 1e-3), (point.x(), point.y())])]]
        if not parts:
            continue
        features.append({"parts": parts, "value": float(value) if isinstance(value, (int, float)) else None})
        sources.append(feature)
    if not features:
        raise CartogramError(f"'{layer.name()}' as filtered now has no feature to draw")
    return features, sources, crs, made_for


def make_cartogram(layer: str, field: str, kind: str = "contiguous", iterations: int = DEFAULT_ITERATIONS,
                   name: str = "") -> Dict[str, Any]:
    """A new layer whose areas show ``field`` of ``layer``: contiguous (borders kept), noncontiguous (each polygon
    scaled), dorling (circles) or demers (squares).

    Raises:
        ValueError: An unknown layer, field or kind, values that cannot be drawn, too many features.
    """
    from qgis.core import (QgsFeature, QgsField, QgsFields, QgsGeometry, QgsPointXY, QgsProcessingUtils,
                           QgsProject, QgsVectorFileWriter, QgsVectorLayer, QgsWkbTypes)
    from qgis.PyQt.QtCore import QVariant
    if kind not in KINDS:
        raise ValueError(f"kind is one of {', '.join(KINDS)}")
    source = resolve_layer(layer)
    if not isinstance(source, QgsVectorLayer):
        raise ValueError(f"no vector layer {layer!r} in the project")
    try:
        features, originals, crs, made_for = _read(source, field, polygons=kind in ("contiguous", "noncontiguous"))
        before = errors(features) if kind in ("contiguous", "noncontiguous") else None
        history: List[float] = []
        if kind == "contiguous":
            shaped, history = contiguous(features, int(iterations))
        elif kind == "noncontiguous":
            shaped = noncontiguous(features)
        else:
            squares = kind == "demers"
            shaped = [dict(feature, parts=[[symbol_ring(x, y, size, squares)]])
                      for feature, (x, y, size) in zip(features, symbols(features, squares=squares))]
    except CartogramError as exc:
        raise ValueError(str(exc)) from None
    fields = QgsFields(source.fields())
    fields.append(QgsField(VALUE_FIELD, QVariant.Double))
    path = QgsProcessingUtils.generateTempFilename("cartogram.gpkg")
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = "cartogram"
    multipolygon = getattr(QgsWkbTypes, "MultiPolygon", None) or QgsWkbTypes.Type.MultiPolygon
    writer = QgsVectorFileWriter.create(path, fields, multipolygon, crs, QgsProject.instance().transformContext(),
                                        options)
    if writer is None or writer.hasError():
        raise ValueError(f"the cartogram could not be written ({writer.errorMessage() if writer else 'no writer'})")
    for original, feature in zip(originals, shaped):
        polygons = [[[QgsPointXY(float(x), float(y)) for x, y in ring] for ring in polygon]
                    for polygon in feature["parts"]]
        made = QgsFeature(fields)
        made.setGeometry(QgsGeometry.fromMultiPolygonXY(polygons))
        made.setAttributes(list(original.attributes()) + [feature["value"]])
        writer.addFeature(made)
    del writer  # closes the file
    title = (name or f"{source.name()} - cartogram ({field})").strip()[:200]
    result = QgsVectorLayer(f"{path}|layername=cartogram", title, "ogr")
    if not result.isValid():
        raise ValueError("the cartogram could not be read back")
    project = QgsProject.instance()
    project.addMapLayer(result, False)
    project.layerTreeRoot().insertLayer(0, result)
    answer: Dict[str, Any] = {"layer": result.name(), "layer_id": result.id(), "kind": kind,
                              "features": len(shaped), "field": field,
                              "crs": crs.authid() or crs.description()}
    if made_for:
        answer["projection"] = f"{made_for} (the layer is in degrees; areas are compared in it)"
    if before is not None:
        answer["error_before"] = round(before, 3)
        answer["error_after"] = round(history[-1] if history else errors(shaped), 3)
        answer["note"] = ("error: the mean ratio between the area of a feature and the area its value asks for; "
                          "1 is exact")
    return answer
