# -*- coding: utf-8 -*-
"""
API requests - parameters shared by the public Python API, the Processing
algorithms and the REST API of FilterMate 5.

The three entry points accept the same plain values (numbers, strings, lists)
and turn them into domain objects here, so a model, a script and an HTTP call
build exactly the same selection:

* :func:`parse_class_codes` - ``"3, 4,5"`` or ``[3, 4, 5]`` -> ``frozenset``;
* :func:`raster_selection_from_values` - band, mode and bounds -> :class:`RasterSelection`;
* :func:`point_cloud_criteria_from_values` - classes, Z / intensity ranges,
  return number and expression -> :class:`PointCloudFilterCriteria`;
* :class:`OperationReport` - outcome of an operation on several layers.

This is a PURE PYTHON module with NO QGIS dependencies.
"""
import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

from .cross_filter import COMBINE_OPERATORS, PREDICATE_METHODS
from .point_cloud_filter_criteria import AttributeRange, PointCloudFilterCriteria
from .raster_filter_criteria import RasterSelection, RasterSelectionMode

# Predicate labels of the FILTERING tab, in the order of the Processing enum.
PREDICATES: Tuple[str, ...] = ("Intersect", "Contain", "Disjoint", "Equal", "Touch", "Overlap", "Are within", "Cross")

# Combine operators in the order of the Processing enum (None = replace).
OPERATORS: Tuple[Optional[str], ...] = (None, "AND", "OR", "AND NOT")

RASTER_SELECTION_MODES: Tuple[str, ...] = tuple(mode.value for mode in RasterSelectionMode)

# Export formats per layer kind: label -> (driver / writer format, file extension).
VECTOR_EXPORT_FORMATS: Dict[str, Tuple[str, str]] = {
    "GPKG": ("GPKG", ".gpkg"),
    "GeoJSON": ("GeoJSON", ".geojson"),
    "ESRI Shapefile": ("ESRI Shapefile", ".shp"),
    "FlatGeobuf": ("FlatGeobuf", ".fgb"),
    "CSV": ("CSV", ".csv"),
}
RASTER_EXPORT_FORMATS: Tuple[str, ...] = ("COG", "GTiff")
POINT_CLOUD_EXPORT_FORMATS: Tuple[str, ...] = ("LAZ", "COPC", "LAS", "GPKG", "CSV")


def parse_class_codes(value: Union[None, str, int, Iterable]) -> frozenset:
    """Class codes from a comma / space separated string or an iterable.

    Args:
        value: ``"3, 4 5"``, ``"6"``, ``6``, ``[3, 4]`` or None.

    Returns:
        A frozenset of ints (empty when ``value`` is empty).

    Raises:
        ValueError: When an item is not an integer.
    """
    if value is None:
        return frozenset()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        items: Sequence = [value]
    elif isinstance(value, str):
        items = [item for item in value.replace(";", ",").replace(" ", ",").split(",") if item.strip()]
    else:
        items = list(value)
    codes = set()
    for item in items:
        try:
            number = float(item)
        except (TypeError, ValueError):
            raise ValueError(f"class code must be an integer, got {item!r}") from None
        if not math.isfinite(number) or number != int(number):
            raise ValueError(f"class code must be an integer, got {item!r}")
        codes.add(int(number))
    return frozenset(codes)


def normalize_operator(value: Union[None, str, int]) -> Optional[str]:
    """Combine operator from a label (``"AND NOT"``), a Processing enum index or None.

    ``"replace"``, ``""`` and None mean: replace the previous filter.

    Raises:
        ValueError: On an unknown label or index.
    """
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        if 0 <= value < len(OPERATORS):
            return OPERATORS[value]
        raise ValueError(f"operator index out of range: {value}")
    text = " ".join(str(value).strip().upper().split())
    if text in ("", "REPLACE", "NONE"):
        return None
    if text in COMBINE_OPERATORS:
        return text
    raise ValueError(f"unknown operator {value!r}, expected one of {', '.join(COMBINE_OPERATORS)} or replace")


def normalize_predicates(values: Union[None, str, Iterable]) -> Tuple[str, ...]:
    """Predicate labels from labels, lower-case method names or enum indexes.

    Returns:
        A tuple of FILTERING labels, ``("Intersect",)`` when empty.

    Raises:
        ValueError: On an unknown predicate.
    """
    if values is None or values == "":
        return ("Intersect",)
    if isinstance(values, (str, int)):
        values = [values]
    methods_to_label = {}
    for label in PREDICATES:
        methods_to_label.setdefault(PREDICATE_METHODS[label], label)
        methods_to_label.setdefault(label.lower(), label)
    labels: List[str] = []
    for value in values:
        if isinstance(value, int) and not isinstance(value, bool):
            if not 0 <= value < len(PREDICATES):
                raise ValueError(f"predicate index out of range: {value}")
            label = PREDICATES[value]
        elif value in PREDICATES:
            label = value
        elif isinstance(value, str) and value.strip().lower() in methods_to_label:
            label = methods_to_label[value.strip().lower()]
        else:
            raise ValueError(f"unknown predicate {value!r}, expected one of {', '.join(PREDICATES)}")
        if label not in labels:
            labels.append(label)
    return tuple(labels) or ("Intersect",)


def raster_selection_from_values(band: int = 1, mode: Union[str, int, RasterSelectionMode] = "range",
                                 minimum: Optional[float] = None, maximum: Optional[float] = None,
                                 classes: Union[None, str, Iterable] = None,
                                 expression: str = "") -> RasterSelection:
    """Build the pixels selection of a raster source.

    Args:
        band: 1-based band number.
        mode: ``"range"``, ``"classes"``, ``"expression"``, a :class:`RasterSelectionMode`
            or its index in :data:`RASTER_SELECTION_MODES`.
        minimum: Lower bound of a range (inclusive), None = unbounded.
        maximum: Upper bound of a range (inclusive), None = unbounded.
        classes: Pixel values kept in ``classes`` mode.
        expression: Raster calculator expression (``"mnt@1" > 1200``) in ``expression`` mode.

    Raises:
        ValueError: When the selection would keep nothing meaningful.
    """
    if isinstance(mode, RasterSelectionMode):
        selection_mode = mode
    elif isinstance(mode, int) and not isinstance(mode, bool):
        if not 0 <= mode < len(RASTER_SELECTION_MODES):
            raise ValueError(f"raster selection mode index out of range: {mode}")
        selection_mode = RasterSelectionMode(RASTER_SELECTION_MODES[mode])
    else:
        try:
            selection_mode = RasterSelectionMode(str(mode).strip().lower())
        except ValueError:
            raise ValueError(f"unknown raster selection mode {mode!r}, expected one of "
                             f"{', '.join(RASTER_SELECTION_MODES)}") from None
    if selection_mode is RasterSelectionMode.RANGE and minimum is None and maximum is None:
        raise ValueError("a raster range needs a minimum, a maximum or both")
    for bound in (minimum, maximum):
        if bound is not None and not math.isfinite(float(bound)):
            raise ValueError(f"raster bounds must be finite numbers, got {bound!r}")
    if isinstance(band, bool) or float(band) != int(float(band)):
        raise ValueError(f"band must be an integer, got {band!r}")
    codes = parse_class_codes(classes) if selection_mode is RasterSelectionMode.CLASSES else frozenset()
    if selection_mode is RasterSelectionMode.CLASSES and not codes:
        raise ValueError("a raster classes selection needs at least one class value")
    expression = (expression or "").strip()
    if selection_mode is RasterSelectionMode.EXPRESSION and not expression:
        raise ValueError("a raster expression selection needs an expression")
    return RasterSelection(band=int(band), mode=selection_mode,
                           minimum=None if minimum is None else float(minimum),
                           maximum=None if maximum is None else float(maximum),
                           classes=codes if selection_mode is RasterSelectionMode.CLASSES else frozenset(),
                           expression=expression if selection_mode is RasterSelectionMode.EXPRESSION else "")


def point_cloud_criteria_from_values(classes: Union[None, str, Iterable] = None,
                                     z_min: Optional[float] = None, z_max: Optional[float] = None,
                                     intensity_min: Optional[float] = None, intensity_max: Optional[float] = None,
                                     return_number: Optional[int] = None,
                                     expression: str = "") -> PointCloudFilterCriteria:
    """Build point cloud criteria (ASPRS classes, Z / intensity ranges, return, expression)."""
    ranges = []
    if z_min is not None or z_max is not None:
        ranges.append(AttributeRange("Z", z_min, z_max))
    if intensity_min is not None or intensity_max is not None:
        ranges.append(AttributeRange("Intensity", intensity_min, intensity_max))
    expression = (expression or "").strip()
    return PointCloudFilterCriteria(classification_codes=parse_class_codes(classes), ranges=tuple(ranges),
                                    return_number=int(return_number) if return_number else None,
                                    extra_clauses=(expression,) if expression else ())


@dataclass
class OperationReport:
    """Outcome of an operation on several layers.

    Attributes:
        done: Layers handled, as ``{layer_id: layer_name}`` in order.
        failed: ``{layer_name: message}`` for the layers that could not be handled.
        skipped: ``{layer_name: reason}`` for the layers left out on purpose
            (not filterable, not in the project, the source itself).
        error: Error that stopped the whole operation, empty otherwise.
        outputs: Files written, ``{layer_name: path}`` (exports).
        details: Free information (timings, source geometry statistics).
    """

    done: Dict[str, str] = field(default_factory=dict)
    failed: Dict[str, str] = field(default_factory=dict)
    skipped: Dict[str, str] = field(default_factory=dict)
    error: str = ""
    outputs: Dict[str, str] = field(default_factory=dict)
    details: Dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """True when nothing stopped the operation and no layer failed."""
        return not self.error and not self.failed

    @property
    def done_ids(self) -> List[str]:
        return list(self.done)

    @property
    def done_names(self) -> List[str]:
        return list(self.done.values())

    def to_dict(self) -> Dict:
        """JSON-compatible view, layers by name (public API, REST)."""
        return {
            "ok": self.ok,
            "done": self.done_names,
            "failed": dict(self.failed),
            "skipped": dict(self.skipped),
            "error": self.error,
            "outputs": dict(self.outputs),
            "details": dict(self.details),
        }


_RASTER_KEYS = ("band", "mode", "minimum", "maximum", "classes", "expression")
_POINT_CLOUD_KEYS = ("classes", "z_min", "z_max", "intensity_min", "intensity_max", "return_number", "expression")


def raster_selection_from_dict(data: Optional[Dict]) -> Optional[RasterSelection]:
    """:func:`raster_selection_from_values` from a JSON object; None when ``data`` is empty.

    Raises:
        ValueError: On unknown keys or an invalid selection.
    """
    if not data:
        return None
    if not isinstance(data, dict):
        raise ValueError(f"raster_selection must be an object, got {type(data).__name__}")
    unknown = sorted(set(data) - set(_RASTER_KEYS))
    if unknown:
        raise ValueError(f"unknown raster_selection keys: {', '.join(unknown)}")
    return raster_selection_from_values(**{key: value for key, value in data.items() if value is not None})


def point_cloud_criteria_from_dict(data: Union[None, str, Dict]) -> Optional[PointCloudFilterCriteria]:
    """:func:`point_cloud_criteria_from_values` from a JSON object or an expression string.

    Returns:
        None when ``data`` is empty.

    Raises:
        ValueError: On unknown keys or invalid values.
    """
    if not data:
        return None
    if isinstance(data, str):
        return point_cloud_criteria_from_values(expression=data)
    if not isinstance(data, dict):
        raise ValueError(f"point cloud criteria must be an object or an expression, got {type(data).__name__}")
    unknown = sorted(set(data) - set(_POINT_CLOUD_KEYS))
    if unknown:
        raise ValueError(f"unknown point cloud criteria keys: {', '.join(unknown)}")
    criteria = point_cloud_criteria_from_values(**{key: value for key, value in data.items() if value is not None})
    return None if criteria.is_empty else criteria
