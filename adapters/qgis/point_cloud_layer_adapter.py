# -*- coding: utf-8 -*-
"""
Point cloud layer adapter.

Reads a ``QgsPointCloudLayer`` into the pure domain summary and applies
subset strings through ``setSubsetString``. Every accessor is defensive:
a missing method, a failing statistics computation or a NaN bound never
propagates to the caller.
"""
import logging
import math
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ...core.domain import point_cloud_attributes as pc_attributes
from ...core.domain.point_cloud_filter_criteria import (
    PointCloudAttributeSummary,
    PointCloudLayerSummary,
)

logger = logging.getLogger(__name__)

# Read first, in this order; the other attributes of the layer follow in layer order.
POINT_CLOUD_RANGE_ATTRIBUTES = (
    pc_attributes.Z, pc_attributes.INTENSITY, pc_attributes.RETURN_NUMBER,
    pc_attributes.NUMBER_OF_RETURNS, pc_attributes.GPS_TIME,
)

_CLASSIFICATION_ATTRIBUTE = pc_attributes.CLASSIFICATION


def _safe_call(obj: Any, name: str, default: Any = None) -> Any:
    """Call ``obj.<name>()`` and return ``default`` when it is missing or fails."""
    method = getattr(obj, name, None)
    if not callable(method):
        return default
    try:
        return method()
    except Exception:
        return default


def _to_int(value: Any, default: int = -1) -> int:
    """Coerce ``value`` to int, ``default`` when impossible (bools rejected)."""
    if value is None or isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


def _to_float(value: Any) -> Optional[float]:
    """Coerce ``value`` to a finite float, None for NaN, infinities or garbage."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _layer_label(layer: Any) -> str:
    """Layer name for log lines."""
    return str(_safe_call(layer, 'name', '?') or '?')


def _read_attribute_names(layer: Any) -> Tuple[str, ...]:
    """Names of the attributes declared by the layer (``layer.attributes().attributes()``)."""
    collection = _safe_call(layer, 'attributes', None)
    if collection is None:
        return ()
    items = _safe_call(collection, 'attributes', None)
    if items is None:
        items = collection
    names: List[str] = []
    try:
        for attribute in items:
            name = _safe_call(attribute, 'name', None)
            if name:
                names.append(str(name))
    except Exception:
        return tuple(names)
    return tuple(names)


def _read_classes(stats: Any) -> Tuple[Tuple[int, int], ...]:
    """Classification codes with counts; ``-1`` counts when only the codes are known."""
    if stats is None:
        return ()
    classes_of = getattr(stats, 'classesOf', None)
    if callable(classes_of):
        try:
            mapping = classes_of(_CLASSIFICATION_ATTRIBUTE) or {}
            pairs = {}
            for code, count in dict(mapping).items():
                code_int = _to_int(code, -1)
                if code_int >= 0:
                    pairs[code_int] = _to_int(count, -1)
            if pairs:
                return tuple(sorted(pairs.items()))
        except Exception as exc:
            logger.debug(f"[FM5] class statistics unreadable: {exc}")
    available = getattr(stats, 'availableClasses', None)
    if callable(available):
        try:
            codes = set()
            for code in list(available(_CLASSIFICATION_ATTRIBUTE) or []):
                code_int = _to_int(code, -1)
                if code_int >= 0:
                    codes.add(code_int)
            return tuple((code, -1) for code in sorted(codes))
        except Exception as exc:
            logger.debug(f"[FM5] available classes unreadable: {exc}")
    return ()


def _read_ranges(stats: Any, attributes: Tuple[str, ...]) -> Tuple[PointCloudAttributeSummary, ...]:
    """Min/max of the attributes present on the layer (the attribute conditions are built on them).

    The standard ones come first; X and Y are left out. Classification stays: the classes
    are counted by :func:`_read_classes`, but a condition on it needs its bounds.
    """
    if stats is None:
        return ()
    skipped = set(pc_attributes.NON_CONDITION_ATTRIBUTES)
    names = [name for name in POINT_CLOUD_RANGE_ATTRIBUTES if name in attributes]
    names += [name for name in attributes if name not in names and name not in skipped]
    ranges: List[PointCloudAttributeSummary] = []
    for name in names:
        minimum = maximum = None
        try:
            minimum = _to_float(stats.minimum(name))
        except Exception:
            minimum = None
        try:
            maximum = _to_float(stats.maximum(name))
        except Exception:
            maximum = None
        ranges.append(PointCloudAttributeSummary(name=name, minimum=minimum, maximum=maximum))
    return tuple(ranges)


def _sampled_points(stats: Any) -> int:
    """``stats.sampledPointsCount()`` or 0."""
    if stats is None:
        return 0
    return max(_to_int(_safe_call(stats, 'sampledPointsCount', 0), 0), 0)


def read_point_cloud_summary(layer: Any) -> PointCloudLayerSummary:
    """Build a :class:`PointCloudLayerSummary` from a ``QgsPointCloudLayer`` without ever raising."""
    layer_id = _safe_call(layer, 'id', '')
    layer_name = _safe_call(layer, 'name', '')
    provider = _safe_call(layer, 'providerType', '')
    point_count = _to_int(_safe_call(layer, 'pointCount', -1), -1)
    current_subset = _safe_call(layer, 'subsetString', '')
    attributes = _read_attribute_names(layer)
    stats = _safe_call(layer, 'statistics', None)
    classes = _read_classes(stats)
    ranges = _read_ranges(stats, attributes)
    statistics_available = bool(classes) or _sampled_points(stats) > 0
    return PointCloudLayerSummary(
        layer_id=str(layer_id or ''),
        layer_name=str(layer_name or ''),
        provider=str(provider or ''),
        point_count=point_count,
        attributes=attributes,
        classes=classes,
        ranges=ranges,
        statistics_available=statistics_available,
        current_subset=str(current_subset or ''),
    )


def apply_point_cloud_subset(layer: Any, subset_string: str) -> bool:
    """Apply ``subset_string`` (empty clears the filter) via ``setSubsetString``; False on failure."""
    subset = subset_string or ""
    label = _layer_label(layer)
    try:
        applied = bool(layer.setSubsetString(subset))
    except Exception as exc:
        logger.warning(f"[PC] setSubsetString failed on '{label}': {exc}")
        return False
    if not applied:
        logger.warning(f"[PC] subset rejected on '{label}': {subset!r}")
        return False
    try:
        layer.triggerRepaint()
    except Exception as exc:
        logger.debug(f"[PC] triggerRepaint failed on '{label}': {exc}")
    logger.info(f"[PC] subset applied on '{label}': {subset!r}")
    return True


def get_point_cloud_subset(layer: Any) -> str:
    """Current subset string of the layer, ``""`` when unavailable."""
    return str(_safe_call(layer, 'subsetString', '') or '')


def class_code(value: Any) -> int:
    """Classification code of an identified point: ``2``, ``"2"`` or ``"2 (Ground)"`` (identify tool); -1 otherwise."""
    if isinstance(value, str):
        match = re.match(r"\s*(\d+)", value)
        return int(match.group(1)) if match else -1
    return _to_int(value)


def dominant_class(points: Iterable[Any]) -> Optional[int]:
    """Most frequent classification code of identified points (lowest code on a tie), None without one."""
    counts: Dict[int, int] = {}
    for point in points or ():
        try:
            code = class_code(point.get(_CLASSIFICATION_ATTRIBUTE))
        except AttributeError:
            continue
        if code >= 0:
            counts[code] = counts.get(code, 0) + 1
    if not counts:
        return None
    return min(counts, key=lambda code: (-counts[code], code))


def attributes_at(layer: Any, canvas: Any, point: Any) -> Optional[Dict[str, Any]]:
    """Attributes of the first point drawn under ``point`` (canvas CRS), None without a point there.

    Same identify read as :func:`class_at` (the layer renderer: a filtered out point is not read).
    """
    try:
        from qgis.gui import QgsMapToolIdentify
        modes = getattr(QgsMapToolIdentify, 'IdentifyMode', QgsMapToolIdentify)
        pixel = canvas.getCoordinateTransform().transform(point)
        results = QgsMapToolIdentify(canvas).identify(round(pixel.x()), round(pixel.y()), [layer], modes.TopDownAll)
    except Exception as exc:
        logger.debug(f"[PC] points not identified on '{_layer_label(layer)}': {exc}")
        return None
    for result in results:
        attributes = getattr(result, 'mAttributes', None)
        if attributes:
            return dict(attributes)
    return None


def attribute_value(attributes: Optional[Dict[str, Any]], name: str) -> Optional[float]:
    """Numeric value of ``name`` in identified point attributes (registry spelling or alias), None when absent."""
    if not attributes:
        return None
    from ...core.domain.point_cloud_attributes import canonical_attribute_name
    wanted = canonical_attribute_name(name) or str(name)
    for key, value in attributes.items():
        if key == name or canonical_attribute_name(key) == wanted:
            try:
                number = float(value)
            except (TypeError, ValueError):
                return None
            return number if number == number else None  # NaN
    return None


def may_have_classes(layer: Any) -> bool:
    """False only for a layer that lists its attributes without Classification (no class to pick)."""
    names = _read_attribute_names(layer)
    return not names or _CLASSIFICATION_ATTRIBUTE in names


def class_at(layer: Any, canvas: Any, point: Any) -> Optional[int]:
    """Classification of the points drawn under ``point`` (canvas CRS), within the identify search radius.

    Reads the points with the QGIS identify tool (the layer renderer, so a filtered out point is not
    picked) and keeps the class most of them have; None without a classified point there.
    """
    try:
        from qgis.gui import QgsMapToolIdentify
        modes = getattr(QgsMapToolIdentify, 'IdentifyMode', QgsMapToolIdentify)
        pixel = canvas.getCoordinateTransform().transform(point)
        results = QgsMapToolIdentify(canvas).identify(round(pixel.x()), round(pixel.y()), [layer], modes.TopDownAll)
    except Exception as exc:
        logger.debug(f"[PC] points not identified on '{_layer_label(layer)}': {exc}")
        return None
    return dominant_class(getattr(result, 'mAttributes', None) for result in results)
