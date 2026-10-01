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
from typing import Any, List, Optional, Tuple

from ...core.domain.point_cloud_filter_criteria import (
    PointCloudAttributeSummary,
    PointCloudLayerSummary,
)

logger = logging.getLogger(__name__)

POINT_CLOUD_RANGE_ATTRIBUTES = ("Z", "Intensity", "ReturnNumber", "NumberOfReturns", "GpsTime")

_CLASSIFICATION_ATTRIBUTE = "Classification"


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
        except Exception:
            pass
    available = getattr(stats, 'availableClasses', None)
    if callable(available):
        try:
            codes = set()
            for code in list(available(_CLASSIFICATION_ATTRIBUTE) or []):
                code_int = _to_int(code, -1)
                if code_int >= 0:
                    codes.add(code_int)
            return tuple((code, -1) for code in sorted(codes))
        except Exception:
            pass
    return ()


def _read_ranges(stats: Any, attributes: Tuple[str, ...]) -> Tuple[PointCloudAttributeSummary, ...]:
    """Min/max of the standard numeric attributes present on the layer."""
    if stats is None:
        return ()
    ranges: List[PointCloudAttributeSummary] = []
    for name in POINT_CLOUD_RANGE_ATTRIBUTES:
        if name not in attributes:
            continue
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
