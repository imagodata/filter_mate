# -*- coding: utf-8 -*-
"""
Cross filter - spatial relation between a source selection and target layers
of any kind (vector, raster, point cloud).

FilterMate 5 model: EXPLORING makes a selection on the source layer, whatever
its kind (features, pixels of a value range, points kept by criteria). That
selection becomes a *source geometry*; FILTERING keeps its usual settings
(layers to filter, combine operators, geometric predicates, buffer) and every
target kind applies the predicates in its own way:

* vector target: the usual predicates, evaluated per feature;
* raster / point cloud target: pixels or points are kept *inside* the source
  geometry, or *outside* of it for ``Disjoint``.

This is a PURE PYTHON module with NO QGIS dependencies.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, List, Optional, Sequence, Tuple

from .layer_kind import LayerKind

# UI labels of comboBox_filtering_geometric_predicates (filtering_controller.py)
# mapped to the QgsGeometry / QgsGeometryEngine method that tests
# ``target.<method>(source)``, the same orientation as native:selectbylocation
# used by the OGR backend (INPUT = target, INTERSECT = source). Like that
# algorithm, a vector target is kept when the predicate holds with at least
# one selected feature of a vector source (Disjoint: disjoint from all); a
# raster or point cloud source is a single geometry, the selected area.
PREDICATE_METHODS = {
    "Intersect": "intersects",
    "Contain": "contains",
    "Disjoint": "disjoint",
    "Equal": "equals",
    "Touch": "touches",
    "Overlap": "overlaps",
    "Are within": "within",
    "Cross": "crosses",
    # Lower-case aliases accepted by the vector engine.
    "intersects": "intersects",
    "contains": "contains",
    "disjoint": "disjoint",
    "equals": "equals",
    "touches": "touches",
    "overlaps": "overlaps",
    "within": "within",
    "crosses": "crosses",
}

DEFAULT_PREDICATE_METHOD = "intersects"
COMBINE_OPERATORS = ("AND", "AND NOT", "OR")


class CoverageSide(Enum):
    """Which part of a raster or point cloud target is kept."""

    INSIDE = "inside"
    OUTSIDE = "outside"
    ALL = "all"


def predicate_methods(predicates: Iterable[str]) -> List[str]:
    """Return the geometry method names for the checked predicate labels.

    Unknown labels are ignored; no usable predicate means ``intersects``,
    which is what the vector engine does when no predicate is checked.

    Args:
        predicates: Checked labels (``"Intersect"``, ``"Are within"``...).

    Returns:
        Distinct method names, in input order.
    """
    methods: List[str] = []
    for label in predicates or ():
        method = PREDICATE_METHODS.get(str(label).strip())
        if method and method not in methods:
            methods.append(method)
    return methods or [DEFAULT_PREDICATE_METHOD]


def coverage_side_for_predicates(predicates: Iterable[str]) -> CoverageSide:
    """Reduce the checked predicates to the side kept on a raster or point cloud.

    Pixels and points have no extent of their own, so every predicate other
    than ``Disjoint`` means "inside the source geometry". Several predicates
    are ORed like in the vector engine: inside OR outside keeps everything.

    Args:
        predicates: Checked labels.

    Returns:
        INSIDE, OUTSIDE (only ``Disjoint``) or ALL (``Disjoint`` and another one).
    """
    methods = predicate_methods(predicates)
    has_outside = "disjoint" in methods
    has_inside = any(method != "disjoint" for method in methods)
    if has_outside and has_inside:
        return CoverageSide.ALL
    if has_outside:
        return CoverageSide.OUTSIDE
    return CoverageSide.INSIDE


def coverage_ratio_ok(target_area: float, intersection_area: float, minimum_percent: float) -> bool:
    """Tell whether a polygon target is covered enough by the source geometry.

    Args:
        target_area: Area of the target feature.
        intersection_area: Area of target ∩ source.
        minimum_percent: Required share in percent; 0 or less disables the test.

    Returns:
        True when the test is disabled, the target has no area, or the share is reached.
    """
    if minimum_percent is None or minimum_percent <= 0:
        return True
    if not target_area or target_area <= 0:
        return True
    return (intersection_area / target_area) * 100.0 >= float(minimum_percent) - 1e-9


def combine_subset(previous: Optional[str], new: str, operator: Optional[str]) -> str:
    """Combine a new subset expression with the layer's previous one.

    Args:
        previous: Current subset string of the layer (may be empty).
        new: Expression produced by the cross filter.
        operator: ``"AND"``, ``"AND NOT"``, ``"OR"`` or None (replace).

    Returns:
        The subset string to apply.
    """
    previous = (previous or "").strip()
    new = (new or "").strip()
    if not previous or not operator:
        return new
    op = operator.strip().upper()
    if op not in COMBINE_OPERATORS:
        return new
    if not new:
        return previous
    if op == "AND NOT":
        return f"({previous}) AND NOT ({new})"
    return f"({previous}) {op} ({new})"


def quote_identifier(name: str) -> str:
    """Double-quote an SQL identifier."""
    return '"' + str(name).replace('"', '""') + '"'


def _sql_literal(value, qgis_expression: bool = False) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return repr(value) if isinstance(value, float) else str(value)
    text = str(value).replace("'", "''")
    if qgis_expression:  # a QGIS expression reads a backslash as an escape (QgsExpression.quotedString)
        text = text.replace('\\', '\\\\').replace('\n', '\\n').replace('\t', '\\t')
    return "'" + text + "'"


def build_in_expression(field_name: Optional[str], values: Sequence, raw_field: bool = False,
                        qgis_expression: bool = False) -> str:
    """Build ``"field" IN (v1, v2, ...)``, or a false predicate for no value.

    Args:
        field_name: Primary key field; ``raw_field`` keeps it unquoted
            (``FID`` for OGR special fields, ``$id`` for QGIS expressions).
        values: Key values of the kept features.
        raw_field: Do not quote the field name.
        qgis_expression: The subset is a QGIS expression (memory, delimited text,
            WFS, OGC API Features): backslashes escaped in text literals.

    Returns:
        A subset expression valid for PostgreSQL, Spatialite, OGR SQL and QGIS expressions.
    """
    if not values:
        return "1 = 0"
    field = str(field_name) if raw_field else quote_identifier(field_name)
    unique = list(dict.fromkeys(values))
    return f"{field} IN ({', '.join(_sql_literal(v, qgis_expression) for v in unique)})"


@dataclass(frozen=True)
class TargetSpec:
    """A layer to filter and its kind."""

    layer_id: str
    kind: LayerKind


@dataclass(frozen=True)
class CrossFilterRequest:
    """Everything FILTERING contributes to a cross filter.

    Attributes:
        source_layer_id: Current layer, holding the EXPLORING selection.
        source_kind: Kind of the source layer.
        targets: Layers to filter.
        predicates: Checked predicate labels.
        buffer_value: Buffer distance applied to the source geometry (map units).
        buffer_segments: Segments per quarter circle.
        buffer_type: ``Round``, ``Flat`` or ``Square``.
        coverage_min: Minimum share (%) of a polygon target inside the source geometry.
        other_layers_combine_operator: Operator combining with each target's
            previous subset, None to replace it.
    """

    source_layer_id: str
    source_kind: LayerKind
    targets: Tuple[TargetSpec, ...] = ()
    predicates: Tuple[str, ...] = ()
    buffer_value: float = 0.0
    buffer_segments: int = 5
    buffer_type: str = "Round"
    coverage_min: float = 0.0
    other_layers_combine_operator: Optional[str] = None

    @property
    def side(self) -> CoverageSide:
        """Side kept on raster and point cloud targets."""
        return coverage_side_for_predicates(self.predicates)

    @property
    def methods(self) -> List[str]:
        """Geometry methods tested on vector targets."""
        return predicate_methods(self.predicates)

    def targets_of(self, kind: LayerKind) -> Tuple[TargetSpec, ...]:
        """Targets of one kind, in request order."""
        return tuple(t for t in self.targets if t.kind is kind)


@dataclass
class CrossFilterOutcome:
    """Result of a cross filter on one target."""

    layer_id: str
    kind: LayerKind
    success: bool
    message: str = ""
    kept_count: Optional[int] = None
    elapsed: float = 0.0
    details: dict = field(default_factory=dict)
