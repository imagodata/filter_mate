# -*- coding: utf-8 -*-
"""What a filter can be built from: fields, values, a trial run, the state of the map.

Read-only, for the agent and for automation. Everything runs on the main thread of
QGIS, and answers plain dicts. A web service is never read to answer.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Set

from ...core.agent.sql_guard import expression_problem, filter_problem, quoted_identifiers
from ...core.domain.layer_kind import LayerKind
from .operations import layer_kind, resolve_layer

logger = logging.getLogger('FilterMate.Introspection')

MAX_FIELDS = 500
MAX_CLASSES = 100
MAX_VALUE_CHARS = 200
MAX_VALUES = 200
MAX_SELECTIONS = 50
MAX_STAT_FEATURES = 500_000  # one pass on the main thread: beyond, QGIS would freeze for too long
MAX_GROUPS = 100
MAX_GROUPS_READ = 10_000
MAX_DISTINCT = 10_000
MAX_SAMPLE = 20
MAX_SAMPLE_FIELDS = 50
MAX_IDENTIFY_LAYERS = 20
MAX_IDENTIFY_BANDS = 20
IDENTIFY_PIXELS = 5
MAX_COORDINATE = 1e9
MAX_JOINS = 20
MAX_RELATIONS = 20
MAX_GROUP_CHARS = 200
# SQLite reads an unknown "name" as the text 'name': no error, and a filter that keeps the wrong features.
_UNKNOWN_NAME_IS_TEXT = ('ogr', 'spatialite')
_IMPLICIT_COLUMNS = frozenset({'fid', 'ogc_fid', 'rowid', 'geom', 'geometry', 'the_geom', 'wkb_geometry'})
# Their source says nothing of their features.
_NOT_REOPENABLE = ('memory',)


def _safe(getter, default=None):
    try:
        return getter()
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return default


def _json_value(value: Any) -> Any:
    """A QGIS attribute as JSON: NULL is None, dates are ISO, long text is cut."""
    if value is None:
        return None
    is_null = getattr(value, 'isNull', None)
    if callable(is_null) and is_null():
        return None
    if isinstance(value, bool) or isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, str):
        return value[:MAX_VALUE_CHARS]
    to_string = getattr(value, 'toString', None)
    if callable(to_string):
        from qgis.PyQt.QtCore import Qt
        try:
            return to_string(Qt.DateFormat.ISODate)[:MAX_VALUE_CHARS]
        except TypeError:  # not a date (QByteArray...)
            pass
    return str(value)[:MAX_VALUE_CHARS]


def _refuse_web_service(layer) -> None:
    from ..qgis.source_capability_probe import capability_for_layer
    capability = capability_for_layer(layer)
    if capability is not None and capability.is_remote_service:
        raise ValueError(f"'{layer.name()}' is a web service: it is not read to answer this")


def _resolve(reference: str):
    """Layer for an id or a name; among layers of the same name a vector one, as ``apply_filter`` picks.

    Raises:
        ValueError: The layer is broken. Reading a broken point cloud crashes QGIS.
    """
    layer = resolve_layer(reference)
    if layer is None:
        return None
    if layer.id() != reference:
        from qgis.core import QgsProject
        vectors = [item for item in QgsProject.instance().mapLayersByName(reference)
                   if layer_kind(item) is LayerKind.VECTOR]
        layer = vectors[0] if vectors else layer
    if not layer.isValid():
        raise ValueError(f"'{layer.name()}' is not available: its data source could not be opened")
    return layer


def _vector_layer(reference: str):
    """Project vector layer for ``reference``; None when absent, ValueError when of another kind."""
    layer = _resolve(reference)
    if layer is None:
        return None
    if layer_kind(layer) is not LayerKind.VECTOR:
        raise ValueError(f"'{layer.name()}' is not a vector layer")
    return layer


def describe_layer(reference: str) -> Optional[Dict[str, Any]]:
    """Fields, bands or attributes of a layer of any kind; None when it does not resolve."""
    layer = _resolve(reference)
    if layer is None:
        return None
    kind = layer_kind(layer)
    crs = _safe(layer.crs)
    _, group, visible = tree_places().get(layer.id(), (0, '', True))
    details: Dict[str, Any] = {
        'layer_id': layer.id(), 'name': layer.name(), 'layer_kind': kind.value,
        'provider_type': _safe(layer.providerType, '') or '',
        'crs_authid': (_safe(crs.authid, '') if crs is not None else '') or '',
        'visible': visible, 'group': group, 'extent': _layer_extent(layer), 'style': _style(layer, kind),
    }
    if kind is LayerKind.VECTOR:
        details.update(_vector_details(layer))
        details.update({'joins': _joins(layer), 'relations': _relations(layer)})
    elif kind is LayerKind.RASTER:
        details.update(_raster_details(layer))
    elif kind is LayerKind.POINT_CLOUD:
        details.update(_point_cloud_details(layer))
    return details


def tree_places() -> Dict[str, Any]:
    """``{layer id: (rank, groups, visible)}`` of the layer tree, top first.

    ``groups`` are the groups above the layer, outermost first, joined by " / "; ``visible`` is the layer checked
    with every group above it.
    """
    from qgis.core import QgsProject
    root = QgsProject.instance().layerTreeRoot()
    places: Dict[str, Any] = {}
    for rank, node in enumerate(_safe(root.findLayers, []) or []):
        names: List[str] = []
        parent = _safe(node.parent)
        while parent is not None and parent is not root and _safe(parent.parent) is not None:
            names.append(_safe(parent.name, '') or '')
            parent = _safe(parent.parent)
        places[node.layerId()] = (rank, ' / '.join(reversed(names))[:MAX_GROUP_CHARS],
                                  bool(_safe(node.isVisible, True)))
    return places


def _rectangle(rectangle) -> List[float]:
    """``[xmin, ymin, xmax, ymax]``; empty for a rectangle that is null or not finite.

    A rectangle without width or height is kept: it is the extent of a single point, or of points in a row.
    """
    if rectangle is None or _safe(rectangle.isNull, True):
        return []
    numbers = [rectangle.xMinimum(), rectangle.yMinimum(), rectangle.xMaximum(), rectangle.yMaximum()]
    return numbers if all(math.isfinite(item) for item in numbers) else []


def _is_web_service(layer) -> bool:
    from ..qgis.source_capability_probe import capability_for_layer
    capability = _safe(lambda: capability_for_layer(layer))
    return capability is not None and bool(capability.is_remote_service)


def _layer_extent(layer) -> List[float]:
    """Extent in the layer CRS; a web service is not asked, it could read its features to answer."""
    return [] if _is_web_service(layer) else _rectangle(_safe(layer.extent))


def _style(layer, kind: LayerKind) -> Dict[str, Any]:
    """How the layer is drawn, without any attribute value: renderer, its field, how many classes, labels, scales."""
    style: Dict[str, Any] = {}
    renderer = _safe(layer.renderer)
    renderer_type = _safe(renderer.type) if renderer is not None else None
    if renderer_type:
        style['renderer'] = str(renderer_type)
    if kind is LayerKind.VECTOR and renderer is not None:
        attribute = _safe(renderer.classAttribute) if hasattr(renderer, 'classAttribute') else None
        if attribute:
            style['field'] = str(attribute)[:MAX_VALUE_CHARS]
        for classes in ('categories', 'ranges'):
            if hasattr(renderer, classes):
                style['classes'] = len(_safe(getattr(renderer, classes), []) or [])
        if _safe(layer.labelsEnabled, False):
            labeling = _safe(layer.labeling)
            settings = _safe(labeling.settings) if labeling is not None and _safe(labeling.type) == 'simple' else None
            style['labels'] = (str(_safe(lambda: settings.fieldName, '') or '')[:MAX_VALUE_CHARS]
                               if settings is not None else 'rules')
    opacity = _safe(layer.opacity)
    if isinstance(opacity, (int, float)) and opacity < 1:
        style['opacity'] = round(float(opacity), 2)
    if _safe(layer.hasScaleBasedVisibility, False):
        # QGIS names them the other way round: minimumScale is the most zoomed out the layer still shows at.
        style.update({'min_scale': _safe(layer.minimumScale), 'max_scale': _safe(layer.maximumScale)})
    return style


def _joins(layer) -> List[Dict[str, Any]]:
    from qgis.core import QgsProject
    joins: List[Dict[str, Any]] = []
    for join in (_safe(layer.vectorJoins, []) or [])[:MAX_JOINS]:
        other = QgsProject.instance().mapLayer(_safe(join.joinLayerId, '') or '')
        joins.append({'layer': other.name() if other is not None else '',
                      'field': _safe(join.joinFieldName, '') or '',
                      'target_field': _safe(join.targetFieldName, '') or '',
                      'prefix': _safe(join.prefix, '') or ''})
    return joins


def _relations(layer) -> List[Dict[str, Any]]:
    """The relations of the project this layer takes part in, as the child (it holds the key) or the parent."""
    from qgis.core import QgsProject
    manager = _safe(QgsProject.instance().relationManager)
    if manager is None:
        return []
    relations: List[Dict[str, Any]] = []
    for role, getter, other_layer in (('child', manager.referencingRelations, 'referencedLayer'),
                                      ('parent', manager.referencedRelations, 'referencingLayer')):
        for relation in _safe(lambda: getter(layer), []) or []:
            pairs = _safe(relation.fieldPairs, {}) or {}  # {field of the child: field of the parent}
            other = _safe(getattr(relation, other_layer))
            relations.append({
                'name': _safe(relation.name, '') or '', 'role': role, 'layer': other.name() if other is not None else '',
                'fields': [{'field': child if role == 'child' else parent,
                            'other_field': parent if role == 'child' else child} for child, parent in pairs.items()]})
    return relations[:MAX_RELATIONS]


# OGR files whose filter is run by SQLite rather than by the OGR SQL engine.
_SQLITE_STORAGE = ('gpkg', 'sqlite', 'geopackage')


def sql_dialect(layer) -> str:
    """The language a subset string of this vector layer is read in, so a filter can be written for it."""
    provider = (_safe(layer.providerType, '') or '').lower()
    if provider == 'postgres':
        return 'postgresql'
    if provider == 'spatialite':
        return 'sqlite'
    if provider == 'ogr':
        storage = (_safe(lambda: layer.dataProvider().storageType(), '') or '').lower()
        return 'sqlite' if any(name in storage for name in _SQLITE_STORAGE) else 'ogr_sql'
    return 'qgis_expression'  # memory, delimited text, web services...: QGIS evaluates it


def _vector_details(layer) -> Dict[str, Any]:
    from qgis.core import QgsWkbTypes
    stored = _provider_field_names(layer)
    fields = [{'name': item.name(), 'type': item.typeName(), 'alias': item.alias() or '',
               'filterable': item.name().lower() in stored}
              for item in list(layer.fields())[:MAX_FIELDS]]
    count = _safe(layer.featureCount, -1)
    return {'fields': fields, 'feature_count': max(count if isinstance(count, int) else -1, -1),
            'subset': _safe(layer.subsetString, '') or '', 'sql_dialect': sql_dialect(layer),
            'geometry_type': _safe(lambda: QgsWkbTypes.displayString(layer.wkbType()), '') or ''}


def _provider_field_names(layer) -> Set[str]:
    """Lower-case names the data source knows: not the virtual and joined fields, which its SQL cannot test."""
    provider = _safe(layer.dataProvider)
    return {item.name().lower() for item in provider.fields()} if provider is not None else set()


def _raster_details(layer) -> Dict[str, Any]:
    palette: List[Dict[str, Any]] = []
    palette_band = None
    renderer = _safe(layer.renderer)
    if renderer is not None and _safe(renderer.type) == 'paletted':
        palette_band = _safe(renderer.band)
        for item in (_safe(renderer.classes, []) or [])[:MAX_CLASSES]:
            value = item.value
            palette.append({'value': int(value) if float(value).is_integer() else value, 'label': item.label})
    bands = []
    for number in range(1, (_safe(layer.bandCount, 0) or 0) + 1):
        band: Dict[str, Any] = {'band': number, 'name': _safe(lambda n=number: layer.bandName(n), '') or ''}
        if number == palette_band:
            band['classes'] = palette
        bands.append(band)
    return {'bands': bands, 'geometry_type': 'Raster', 'pixel_size': _safe(layer.rasterUnitsPerPixelX)}


def _point_cloud_details(layer) -> Dict[str, Any]:
    collection = _safe(layer.attributes)
    names = [item.name() for item in (_safe(collection.attributes, []) if collection is not None else [])]
    count = _safe(layer.pointCount, -1)
    return {'attributes': names, 'feature_count': count if isinstance(count, int) else -1,
            'geometry_type': 'PointCloud', 'subset': _safe(layer.subsetString, '') or ''}


def field_values(reference: str, field_name: str, search: str = '', limit: int = 50) -> Optional[Dict[str, Any]]:
    """Distinct values of a field; None when the layer or the field does not resolve.

    Raises:
        ValueError: Not a vector layer, or a web service.
    """
    layer = _vector_layer(reference)
    if layer is None:
        return None
    index = layer.fields().lookupField(field_name)
    if index < 0:
        return None
    _refuse_web_service(layer)
    limit = max(1, min(int(limit), MAX_VALUES))
    field = layer.fields().at(index)
    # One more than asked tells whether there are others, and one more for the NULL left out below.
    found = (layer.uniqueStringsMatching(index, search, limit + 2) if search
             else layer.uniqueValues(index, limit + 2))
    converted = [_json_value(item) for item in found]
    # A value cut to fit would give a filter that matches nothing.
    values = [value for value in converted
              if value is not None and not (isinstance(value, str) and len(value) >= MAX_VALUE_CHARS)]
    values.sort(key=lambda item: (isinstance(item, str), item))
    result: Dict[str, Any] = {'layer_name': layer.name(), 'field': field.name(),
                              'values': values[:limit], 'truncated': len(values) > limit}
    if not search and (field.isNumeric() or field.isDateOrTime()):
        result['minimum'] = _json_value(_safe(lambda: layer.minimumValue(index)))
        result['maximum'] = _json_value(_safe(lambda: layer.maximumValue(index)))
    return result


def preview_filter(reference: str, expression: str) -> Optional[Dict[str, Any]]:
    """What ``expression`` would keep, on a private layer of the same source; None when it does not resolve.

    Raises:
        ValueError: Not a vector layer, a source that cannot be reopened, a web service,
            or an expression that is more than a plain filter (this is announced as read-only).
    """
    from qgis.core import QgsFeatureRequest, QgsVectorLayer
    from ...infrastructure.database.sql_utils import safe_set_subset_string

    problem = filter_problem(expression)
    if problem:
        raise ValueError(f"This expression cannot be tried: {problem}")
    layer = _vector_layer(reference)
    if layer is None:
        return None
    if layer.providerType() in _NOT_REOPENABLE:
        raise ValueError(f"'{layer.name()}' is held in memory and cannot be tried on a copy: apply the filter directly")
    _refuse_web_service(layer)
    answer: Dict[str, Any] = {'layer_name': layer.name(), 'expression': expression}
    unknown = _unknown_names(layer, expression)
    if unknown:
        return {**answer, 'valid': False, 'error': (
            f"unknown field(s): {', '.join(unknown)}. Field names take double quotes, text values single quotes.")}
    trial = QgsVectorLayer(layer.source(), 'filtermate_preview', layer.providerType(),
                           QgsVectorLayer.LayerOptions(False, False))
    if not trial.isValid():
        return {**answer, 'valid': False, 'error': 'the data source could not be opened to try this filter'}
    if not safe_set_subset_string(trial, expression):
        return {**answer, 'valid': False, 'error': _provider_error(trial) or 'the provider refused this expression'}
    count = trial.featureCount()
    # OGR accepts invalid SQL in setSubsetString: it only shows when reading, as no count and no feature.
    error = _provider_error(trial)
    if error or (count < 0 and not any(True for _ in trial.getFeatures(QgsFeatureRequest().setLimit(1)))):
        return {**answer, 'valid': False, 'error': error or 'the provider could not run this expression'}
    return {**answer, 'valid': True, 'feature_count': count if count >= 0 else -1}


def _unknown_names(layer, expression: str) -> List[str]:
    """Quoted names that are no field, on the providers where such a name silently becomes text."""
    if layer.providerType() not in _UNKNOWN_NAME_IS_TEXT:
        return []
    known = _provider_field_names(layer) | _IMPLICIT_COLUMNS
    return sorted({name for name in quoted_identifiers(expression) if name.lower() not in known})


def _provider_error(layer) -> str:
    provider = _safe(layer.dataProvider)
    if provider is None or not _safe(provider.hasErrors, False):
        return ''
    errors = _safe(provider.errors, []) or []
    return str(errors[-1])[:MAX_VALUE_CHARS] if errors else ''


def map_context() -> Dict[str, Any]:
    """CRS, extent, scale, active layer and selections; ``available`` False without a canvas."""
    from qgis.core import QgsProject, QgsVectorLayer
    try:
        from qgis.utils import iface
    except ImportError:
        iface = None
    project = QgsProject.instance()
    context: Dict[str, Any] = {'project_crs': _safe(lambda: project.crs().authid(), '') or ''}
    selections: List[Dict[str, Any]] = []
    for layer in project.mapLayers().values():
        if isinstance(layer, QgsVectorLayer):
            count = _safe(layer.selectedFeatureCount, 0) or 0
            if count:
                selections.append({'layer_id': layer.id(), 'name': layer.name(), 'selected_count': count})
    context['selections'] = selections[:MAX_SELECTIONS]
    canvas = _safe(iface.mapCanvas) if iface is not None else None
    if canvas is None:
        return {**context, 'available': False}
    context.update({
        'available': True,
        'canvas_crs': _safe(lambda: canvas.mapSettings().destinationCrs().authid(), '') or '',
        'extent_wkt': _safe(lambda: canvas.extent().asWktPolygon(), '') or '',
        'extent': _rectangle(_safe(canvas.extent)),
        'scale': _safe(canvas.scale),
    })
    active = _safe(iface.activeLayer)
    if active is not None:
        context.update({'active_layer_id': active.id(), 'active_layer_name': active.name()})
    return context


# --- reading the features: statistics, a sample, what lies at a point -------------------------------------------

def _checked_expression(layer, expression: str) -> str:
    """A QGIS expression written by a model, as ``select_features`` accepts it.

    Raises:
        ValueError: More than a plain condition, a syntax error, or a field the layer does not have.
    """
    from qgis.core import QgsExpression
    problem = expression_problem(expression)
    if problem:
        raise ValueError(f"this expression cannot be used: {problem}")
    check = QgsExpression(expression)
    if check.hasParserError():
        raise ValueError(f"invalid QGIS expression: {check.parserErrorString()}")
    known = {item.name().lower() for item in layer.fields()}
    unknown = sorted({name for name in quoted_identifiers(expression) if name.lower() not in known})
    if unknown:
        raise ValueError(f"unknown field(s): {', '.join(unknown)}")
    return expression


def _request(layer, attributes: List[int], geometry: bool, selected_only: bool, expression: str = ''):
    """A request for these attributes only, of the selected features or of those matching ``expression``."""
    from qgis.core import QgsFeatureRequest
    request = QgsFeatureRequest()
    request.setSubsetOfAttributes(attributes)
    if not geometry:
        request.setFlags(QgsFeatureRequest.Flag.NoGeometry)
    if selected_only:
        if not layer.selectedFeatureCount():
            raise ValueError(f"no feature is selected on '{layer.name()}'")
        request.setFilterFids(layer.selectedFeatureIds())
    if expression:
        request.setFilterExpression(_checked_expression(layer, expression))
    return request


def _measurer(layer, measure: str):
    """``(function of a geometry, unit, ellipsoid)`` measuring lengths in metres or areas in square metres.

    On the ellipsoid of the project, or of the layer CRS when the project has none and the layer is in degrees;
    without an ellipsoid the measure is planar, in the units of the layer CRS.
    """
    from qgis.core import QgsDistanceArea, QgsProject, QgsUnitTypes, QgsWkbTypes
    project = QgsProject.instance()
    crs = layer.crs()
    ellipsoid = _safe(project.ellipsoid, '') or ''
    if ellipsoid.upper() in ('', 'NONE') and _safe(crs.isGeographic, False):
        ellipsoid = _safe(crs.ellipsoidAcronym, '') or ''
    calculator = QgsDistanceArea()
    calculator.setSourceCrs(crs, project.transformContext())
    planar = ellipsoid.upper() in ('', 'NONE')
    if not planar:
        calculator.setEllipsoid(ellipsoid)
    polygons = QgsWkbTypes.geometryType(layer.wkbType()) == QgsWkbTypes.GeometryType.PolygonGeometry
    lines = QgsWkbTypes.geometryType(layer.wkbType()) == QgsWkbTypes.GeometryType.LineGeometry
    if measure == 'area':
        if not polygons:
            raise ValueError(f"'{layer.name()}' has no polygons: it has no area to measure")
        target = QgsUnitTypes.AreaUnit.AreaSquareMeters

        def run(geometry):
            return calculator.convertAreaMeasurement(calculator.measureArea(geometry), target)
        unit = 'm2'
    else:
        if not (polygons or lines):
            raise ValueError(f"'{layer.name()}' has neither lines nor polygons: it has no length to measure")
        target = QgsUnitTypes.DistanceUnit.DistanceMeters
        length = calculator.measurePerimeter if polygons else calculator.measureLength

        def run(geometry):
            return calculator.convertLengthMeasurement(length(geometry), target)
        unit = 'm'
    if planar and _safe(crs.isGeographic, False):
        unit = 'degrees' if measure == 'length' else 'square degrees'
    return run, unit, '' if planar else ellipsoid


class _Series:
    """Count, sum, extremes and spread of the values of one pass."""

    def __init__(self, numeric: bool) -> None:
        self.numeric = numeric
        self.count = 0
        self.nulls = 0
        self.total = 0.0
        self.squares = 0.0
        self.minimum: Any = None
        self.maximum: Any = None
        self.distinct: Set[Any] = set()

    def add(self, value: Any) -> None:
        if value is None or (isinstance(value, float) and not math.isfinite(value)):
            self.nulls += 1
            return
        self.count += 1
        if self.numeric and isinstance(value, (int, float)) and not isinstance(value, bool):
            self.total += value
            self.squares += value * value
        elif len(self.distinct) <= MAX_DISTINCT:
            self.distinct.add(value)
        try:
            self.minimum = value if self.minimum is None or value < self.minimum else self.minimum
            self.maximum = value if self.maximum is None or value > self.maximum else self.maximum
        except TypeError:  # values of several types in one field: no order
            pass

    def summary(self) -> Dict[str, Any]:
        answer: Dict[str, Any] = {'count': self.count, 'nulls': self.nulls, 'minimum': self.minimum,
                                  'maximum': self.maximum}
        if self.numeric:
            mean = self.total / self.count if self.count else None
            answer.update({'sum': _rounded(self.total), 'mean': _rounded(mean)})
            if self.count > 1:
                variance = max(self.squares / self.count - mean * mean, 0.0)
                answer['stdev'] = _rounded(math.sqrt(variance * self.count / (self.count - 1)))
        else:
            answer['distinct'] = min(len(self.distinct), MAX_DISTINCT)
            answer['distinct_truncated'] = len(self.distinct) > MAX_DISTINCT
        return answer


def _rounded(value: Any) -> Any:
    """Six significant digits: a sum of floats does not need its noise."""
    if not isinstance(value, float) or not math.isfinite(value) or value == 0:
        return value
    return round(value, max(0, 6 - int(math.floor(math.log10(abs(value)))) - 1)) if abs(value) < 1e6 else round(value, 1)


def layer_statistics(reference: str, field_name: str = '', group_by: str = '', measure: str = '',
                     selected_only: bool = False, limit: int = 20) -> Optional[Dict[str, Any]]:
    """Statistics of a field or of the geometries of a vector layer, in all or by the values of another field.

    Counts the features when neither ``field_name`` nor ``measure`` is given. One pass over the features the layer
    shows now (its filter applies), or over its selection. None when the layer or a field does not resolve.

    Raises:
        ValueError: Not a vector layer, a web service, more features than ``MAX_STAT_FEATURES``, too many groups,
            a measure the geometries do not have, or nothing selected with ``selected_only``.
    """
    layer = _vector_layer(reference)
    if layer is None:
        return None
    fields = layer.fields()
    index = fields.lookupField(field_name) if field_name else -1
    group_index = fields.lookupField(group_by) if group_by else -1
    if (field_name and index < 0) or (group_by and group_index < 0):
        return None
    if measure not in ('', 'length', 'area'):
        raise ValueError("measure is 'length', 'area' or nothing")
    if field_name and measure:
        raise ValueError('give a field or a measure, not both')
    _refuse_web_service(layer)
    known = layer.selectedFeatureCount() if selected_only else (_safe(layer.featureCount, -1) or 0)
    too_many = (f"'{layer.name()}' has more than {MAX_STAT_FEATURES} features to read: filter it or select "
                "features first")
    if known > MAX_STAT_FEATURES:
        raise ValueError(too_many)
    run, unit, ellipsoid = _measurer(layer, measure) if measure else (None, '', '')
    numeric = bool(measure) or (index >= 0 and fields.at(index).isNumeric())
    request = _request(layer, [item for item in (index, group_index) if item >= 0], bool(measure), selected_only)
    overall = _Series(numeric)
    groups: Dict[Any, _Series] = {}
    read = 0
    for feature in layer.getFeatures(request):
        read += 1
        if read > MAX_STAT_FEATURES:
            raise ValueError(too_many)
        if measure:
            geometry = feature.geometry()
            value = None if geometry is None or geometry.isNull() else run(geometry)
        elif index >= 0:
            value = _json_value(feature.attribute(index))
        else:
            value = 1  # counting features
        overall.add(value)
        if group_index >= 0:
            key = _json_value(feature.attribute(group_index))
            series = groups.get(key)
            if series is None:
                if len(groups) >= MAX_GROUPS_READ:
                    raise ValueError(f"'{group_by}' takes more than {MAX_GROUPS_READ} values: group by another field")
                series = groups[key] = _Series(numeric)
            series.add(value)
    answer: Dict[str, Any] = {'layer_name': layer.name(), 'field': fields.at(index).name() if index >= 0 else '',
                              'measure': measure, 'unit': unit, 'ellipsoid': ellipsoid, 'selected_only': selected_only,
                              'feature_count': read}
    counting = index < 0 and not measure
    if not counting:
        answer['statistics'] = overall.summary()
    if group_index >= 0:
        limit = max(1, min(int(limit), MAX_GROUPS))
        ranked = sorted(groups.items(), key=lambda item: (-(item[1].count + item[1].nulls), str(item[0])))
        answer.update({
            'group_by': fields.at(group_index).name(), 'groups_total': len(ranked), 'truncated': len(ranked) > limit,
            'groups': [{'value': key, 'feature_count': series.count + series.nulls,
                        **({} if counting else series.summary())} for key, series in ranked[:limit]]})
    return answer


def _shape(geometry) -> Optional[Dict[str, Any]]:
    """Where a geometry is, without its vertices: its type, its centroid and its bounding box."""
    from qgis.core import QgsWkbTypes
    if geometry is None or geometry.isNull():
        return None
    centroid = _safe(lambda: geometry.centroid().asPoint())
    return {'type': _safe(lambda: QgsWkbTypes.displayString(geometry.wkbType()), '') or '',
            'centroid': [centroid.x(), centroid.y()] if centroid is not None else [],
            'bbox': _rectangle(_safe(geometry.boundingBox))}


def _attributes(feature, indexes: List[int], fields) -> Dict[str, Any]:
    return {fields.at(index).name(): _json_value(feature.attribute(index)) for index in indexes}


def _field_indexes(layer, names: Optional[List[str]]) -> List[int]:
    """Indexes of ``names``, or of the first ``MAX_SAMPLE_FIELDS`` fields.

    Raises:
        ValueError: A name is no field of the layer.
    """
    fields = layer.fields()
    if not names:
        return list(range(min(fields.count(), MAX_SAMPLE_FIELDS)))
    indexes = [fields.lookupField(name) for name in names[:MAX_SAMPLE_FIELDS]]
    unknown = [name for name, index in zip(names, indexes) if index < 0]
    if unknown:
        raise ValueError(f"unknown field(s): {', '.join(unknown)}")
    return indexes


def sample_features(reference: str, limit: int = 5, fields: Optional[List[str]] = None, expression: str = '',
                    selected_only: bool = False, geometry: bool = False) -> Optional[Dict[str, Any]]:
    """A few features of a vector layer, with their attributes; None when the layer does not resolve.

    Raises:
        ValueError: Not a vector layer, a web service, an unknown field, an expression that is more than a plain
            condition, or nothing selected with ``selected_only``.
    """
    layer = _vector_layer(reference)
    if layer is None:
        return None
    _refuse_web_service(layer)
    limit = max(1, min(int(limit), MAX_SAMPLE))
    indexes = _field_indexes(layer, fields)
    request = _request(layer, indexes, geometry, selected_only, expression)
    request.setLimit(limit + 1)  # one more tells whether there are others
    rows: List[Dict[str, Any]] = []
    for feature in layer.getFeatures(request):
        row: Dict[str, Any] = {'fid': feature.id(), 'attributes': _attributes(feature, indexes, layer.fields())}
        if geometry:
            row['geometry'] = _shape(feature.geometry())
        rows.append(row)
    crs = _safe(layer.crs)
    return {'layer_name': layer.name(), 'crs_authid': (_safe(crs.authid, '') if crs is not None else '') or '',
            'features': rows[:limit], 'truncated': len(rows) > limit,
            'fields_truncated': not fields and layer.fields().count() > MAX_SAMPLE_FIELDS}


def _identify_layers(references: Optional[List[str]]) -> List[Any]:
    """The layers named, or the visible vector and raster layers of the tree, top first."""
    from qgis.core import QgsProject
    if references:
        layers = []
        for reference in references[:MAX_IDENTIFY_LAYERS]:
            layer = _resolve(reference)
            if layer is None:
                raise ValueError(f"layer {reference!r} not found")
            layers.append(layer)
        return layers
    project = QgsProject.instance()
    places = tree_places()
    ranked = sorted((rank, layer_id) for layer_id, (rank, _, visible) in places.items() if visible)
    layers = [project.mapLayer(layer_id) for _, layer_id in ranked]
    return [layer for layer in layers if layer is not None and _safe(layer.isValid, False)
            and layer_kind(layer) in (LayerKind.VECTOR, LayerKind.RASTER)][:MAX_IDENTIFY_LAYERS]


def identify_at(x: float, y: float, crs: str = '', layers: Optional[List[str]] = None,
                tolerance: Optional[float] = None, limit: int = 5) -> Dict[str, Any]:
    """The features and the raster values at a point, as the Identify tool of QGIS reads them.

    ``crs`` is the CRS of the map by default, ``tolerance`` (in its units) five pixels of the map, or nothing
    without a map. Web services are left out and named in ``skipped``.

    Raises:
        ValueError: Coordinates out of range, an unknown CRS, a layer that does not resolve.
    """
    from qgis.core import (
        QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsFeatureRequest, QgsGeometry, QgsPointXY, QgsProject,
        QgsRectangle,
    )
    try:
        from qgis.utils import iface
    except ImportError:
        iface = None
    if not all(isinstance(item, (int, float)) and math.isfinite(item) and abs(item) < MAX_COORDINATE for item in (x, y)):
        raise ValueError('these coordinates are out of range')
    project = QgsProject.instance()
    canvas = _safe(iface.mapCanvas) if iface is not None else None
    map_crs = _safe(lambda: canvas.mapSettings().destinationCrs()) if canvas is not None else None
    point_crs = QgsCoordinateReferenceSystem(crs) if crs else (map_crs or project.crs())
    if crs and not point_crs.isValid():
        raise ValueError(f"unknown CRS {crs!r}")
    if tolerance is None:
        tolerance = 0.0
        if canvas is not None and map_crs is not None and map_crs == point_crs:
            tolerance = IDENTIFY_PIXELS * (_safe(canvas.mapUnitsPerPixel, 0.0) or 0.0)
    tolerance = max(0.0, min(float(tolerance), MAX_COORDINATE))
    limit = max(1, min(int(limit), MAX_SAMPLE))
    area = QgsRectangle(x - tolerance, y - tolerance, x + tolerance, y + tolerance)
    found: List[Dict[str, Any]] = []
    skipped: List[str] = []
    for layer in _identify_layers(layers):
        if _is_web_service(layer):
            skipped.append(layer.name())
            continue
        kind = layer_kind(layer)
        try:
            transform = QgsCoordinateTransform(point_crs, layer.crs(), project)
            if kind is LayerKind.VECTOR:
                box = transform.transformBoundingBox(area)
                if not tolerance:  # a rectangle without size can be read as no rectangle at all
                    box.grow(max(abs(box.xMinimum()), abs(box.yMinimum()), 1.0) * 1e-9)
                shape = QgsGeometry.fromRect(box) if tolerance else QgsGeometry.fromPointXY(QgsPointXY(box.center()))
                indexes = _field_indexes(layer, None)
                request = QgsFeatureRequest().setFilterRect(box).setSubsetOfAttributes(indexes)
                rows = []
                for feature in layer.getFeatures(request):
                    geometry = feature.geometry()
                    if geometry is None or geometry.isNull() or not geometry.intersects(shape):
                        continue  # the rectangle filter of a provider is on bounding boxes
                    rows.append({'fid': feature.id(), 'attributes': _attributes(feature, indexes, layer.fields())})
                    if len(rows) > limit:
                        break
                if rows:
                    found.append({'layer_name': layer.name(), 'layer_kind': kind.value, 'features': rows[:limit],
                                  'truncated': len(rows) > limit})
            elif kind is LayerKind.RASTER:
                where = transform.transform(QgsPointXY(x, y))
                provider = layer.dataProvider()
                values = []
                for band in range(1, min(_safe(layer.bandCount, 0) or 0, MAX_IDENTIFY_BANDS) + 1):
                    value, ok = provider.sample(where, band)
                    if ok and isinstance(value, float) and math.isfinite(value):
                        values.append({'band': band, 'value': value})
                if values:
                    found.append({'layer_name': layer.name(), 'layer_kind': kind.value, 'values': values})
        except Exception as exc:  # a point outside the domain of a CRS, a provider that cannot answer
            logger.debug("identify_at: %s left out (%s)", layer.name(), exc)
            skipped.append(layer.name())
    return {'x': x, 'y': y, 'crs': _safe(point_crs.authid, '') or '', 'tolerance': tolerance, 'layers': found,
            'skipped': skipped}
