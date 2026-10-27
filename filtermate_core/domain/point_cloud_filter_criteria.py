"""
Point Cloud Filter Criteria - Domain Objects for Point Cloud Filtering.

Pure Python value objects describing a point cloud filter (classification,
attribute ranges, return number) and its rendering as a
``QgsPointCloudExpression`` subset string.

This is a PURE PYTHON module with NO QGIS dependencies,
enabling true unit testing and clear separation of concerns.
"""
import math
import re
from dataclasses import dataclass
from typing import FrozenSet, List, Optional, Tuple

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MAX_CLASS_CODE = 255
_MAX_RETURN_NUMBER = 15


def format_number(value: float) -> str:
    """Format a number for a point cloud expression.

    Args:
        value: Number to format (int or float).

    Returns:
        Decimal text with at most 6 decimals and no trailing zeros
        (``2`` -> ``"2"``, ``10.5`` -> ``"10.5"``, ``0.123456789`` -> ``"0.123457"``).

    Raises:
        ValueError: If ``value`` is NaN or infinite.
    """
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Cannot format non-finite number: {value!r}")
    text = f"{number:.6f}".rstrip("0").rstrip(".")
    if text in ("", "-", "-0"):
        return "0"
    return text


def _validate_bound(label: str, value: Optional[float]) -> None:
    """Raise ValueError unless ``value`` is None or a finite number."""
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number or None, got {value!r}")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{label} must be finite, got {value!r}")


def _validate_int_in_range(label: str, value: object, low: int, high: int) -> int:
    """Return ``value`` when it is an int within ``[low, high]``, else raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an integer, got {value!r}")
    if value < low or value > high:
        raise ValueError(f"{label} must be between {low} and {high}, got {value}")
    return value


@dataclass(frozen=True)
class AttributeRange:
    """Inclusive range constraint on a point cloud attribute.

    Attributes:
        attribute: Attribute name (``Z``, ``Intensity``...), a valid identifier.
        minimum: Lower bound (inclusive) or None.
        maximum: Upper bound (inclusive) or None.
    """
    attribute: str
    minimum: Optional[float] = None
    maximum: Optional[float] = None

    def __post_init__(self) -> None:
        """Validate the attribute name and the bounds."""
        if not isinstance(self.attribute, str) or not _IDENTIFIER_RE.match(self.attribute):
            raise ValueError(
                f"attribute must be a non-empty identifier, got {self.attribute!r}"
            )
        _validate_bound("minimum", self.minimum)
        _validate_bound("maximum", self.maximum)
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError(
                f"minimum ({self.minimum}) must be <= maximum ({self.maximum})"
            )

    @property
    def is_empty(self) -> bool:
        """Whether no bound is set."""
        return self.minimum is None and self.maximum is None

    def to_clauses(self) -> Tuple[str, ...]:
        """Render the range as comparison clauses.

        Returns:
            ``("Z >= 10", "Z <= 150")``; an empty tuple when no bound is set.
        """
        clauses: List[str] = []
        if self.minimum is not None:
            clauses.append(f"{self.attribute} >= {format_number(self.minimum)}")
        if self.maximum is not None:
            clauses.append(f"{self.attribute} <= {format_number(self.maximum)}")
        return tuple(clauses)

    def to_dict(self) -> dict:
        """Return a JSON-compatible representation."""
        return {
            "attribute": self.attribute,
            "minimum": self.minimum,
            "maximum": self.maximum,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AttributeRange":
        """Build a range from :meth:`to_dict` output.

        Raises:
            ValueError: If ``data`` is not a dict or holds invalid values.
        """
        if not isinstance(data, dict):
            raise ValueError(f"AttributeRange data must be a dict, got {type(data).__name__}")
        return cls(
            attribute=data.get("attribute", ""),
            minimum=data.get("minimum"),
            maximum=data.get("maximum"),
        )


@dataclass(frozen=True)
class PointCloudFilterCriteria:
    """Immutable description of a point cloud filter.

    Attributes:
        classification_codes: ASPRS codes to keep (0-255).
        ranges: Attribute range constraints, rendered in order.
        return_number: Return number to keep (1-15) or None.
        extra_clauses: Free-form expression clauses, each wrapped in parentheses.
    """
    classification_codes: FrozenSet[int] = frozenset()
    ranges: Tuple[AttributeRange, ...] = ()
    return_number: Optional[int] = None
    extra_clauses: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Normalise containers to immutable types and validate every member."""
        codes = frozenset(
            _validate_int_in_range("classification code", code, 0, _MAX_CLASS_CODE)
            for code in self.classification_codes
        )
        object.__setattr__(self, "classification_codes", codes)

        ranges = tuple(self.ranges)
        for item in ranges:
            if not isinstance(item, AttributeRange):
                raise ValueError(f"ranges must contain AttributeRange instances, got {item!r}")
        object.__setattr__(self, "ranges", ranges)

        if self.return_number is not None:
            _validate_int_in_range("return_number", self.return_number, 1, _MAX_RETURN_NUMBER)

        clauses: List[str] = []
        for clause in self.extra_clauses:
            if not isinstance(clause, str) or not clause.strip():
                raise ValueError(f"extra clauses must be non-empty strings, got {clause!r}")
            clauses.append(clause.strip())
        object.__setattr__(self, "extra_clauses", tuple(clauses))

    @property
    def is_empty(self) -> bool:
        """Whether the criteria produce no clause at all."""
        return (
            not self.classification_codes
            and all(item.is_empty for item in self.ranges)
            and self.return_number is None
            and not self.extra_clauses
        )

    def to_subset_string(self) -> str:
        """Render the criteria as a ``QgsPointCloudExpression`` subset string.

        Returns:
            Clauses joined by ``" AND "`` in the order classification, ranges,
            return number, extra clauses; ``""`` when empty.
        """
        clauses: List[str] = []
        codes = sorted(self.classification_codes)
        if len(codes) == 1:
            clauses.append(f"Classification = {codes[0]}")
        elif codes:
            joined = ", ".join(str(code) for code in codes)
            clauses.append(f"Classification IN ({joined})")
        for item in self.ranges:
            clauses.extend(item.to_clauses())
        if self.return_number is not None:
            clauses.append(f"ReturnNumber = {self.return_number}")
        clauses.extend(f"({clause})" for clause in self.extra_clauses)
        return " AND ".join(clauses)

    def to_dict(self) -> dict:
        """Return a JSON-compatible representation (lists, not tuples/sets)."""
        return {
            "classification_codes": sorted(self.classification_codes),
            "ranges": [item.to_dict() for item in self.ranges],
            "return_number": self.return_number,
            "extra_clauses": list(self.extra_clauses),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PointCloudFilterCriteria":
        """Build criteria from :meth:`to_dict` output (missing keys use defaults).

        Raises:
            ValueError: If ``data`` is not a dict or holds invalid values.
        """
        if not isinstance(data, dict):
            raise ValueError(f"criteria data must be a dict, got {type(data).__name__}")
        ranges = tuple(
            AttributeRange.from_dict(item) if isinstance(item, dict) else item
            for item in (data.get("ranges") or ())
        )
        return cls(
            classification_codes=frozenset(data.get("classification_codes") or ()),
            ranges=ranges,
            return_number=data.get("return_number"),
            extra_clauses=tuple(data.get("extra_clauses") or ()),
        )


@dataclass(frozen=True)
class PointCloudAttributeSummary:
    """Observed value range of one point cloud attribute.

    Attributes:
        name: Attribute name.
        minimum: Observed minimum or None when unknown.
        maximum: Observed maximum or None when unknown.
    """
    name: str
    minimum: Optional[float] = None
    maximum: Optional[float] = None


@dataclass(frozen=True)
class PointCloudLayerSummary:
    """Snapshot of a point cloud layer used to populate the filter panel.

    Attributes:
        layer_id: QGIS layer id.
        layer_name: Layer display name.
        provider: QGIS provider key (``copc``, ``ept``, ``vpc``, ``pdal``).
        point_count: Total point count, -1 when unknown.
        attributes: Names of the attributes present in the layer.
        classes: ``((code, count), ...)`` sorted by code; count -1 when unknown.
        ranges: Observed ranges of the numeric attributes.
        statistics_available: Whether layer statistics were readable.
        current_subset: Subset string currently applied to the layer.
    """
    layer_id: str
    layer_name: str
    provider: str = ""
    point_count: int = -1
    attributes: Tuple[str, ...] = ()
    classes: Tuple[Tuple[int, int], ...] = ()
    ranges: Tuple[PointCloudAttributeSummary, ...] = ()
    statistics_available: bool = False
    current_subset: str = ""

    def __post_init__(self) -> None:
        """Normalise containers to tuples and sort classes by code."""
        object.__setattr__(self, "attributes", tuple(str(name) for name in self.attributes))
        classes = tuple(sorted(
            (int(code), -1 if count is None else int(count))
            for code, count in self.classes
        ))
        object.__setattr__(self, "classes", classes)
        object.__setattr__(self, "ranges", tuple(self.ranges))

    def has_attribute(self, name: str) -> bool:
        """Whether ``name`` is one of the layer attributes."""
        return name in self.attributes

    @property
    def class_codes(self) -> Tuple[int, ...]:
        """Classification codes present in the layer, sorted."""
        return tuple(code for code, _count in self.classes)

    def range_of(self, name: str) -> Optional[PointCloudAttributeSummary]:
        """Return the observed range of ``name`` or None when unknown."""
        for item in self.ranges:
            if item.name == name:
                return item
        return None


@dataclass(frozen=True)
class PointCloudFilterResult:
    """Outcome of applying or clearing a point cloud subset.

    Attributes:
        success: Whether the subset was accepted by the layer.
        subset_string: Subset string that was applied (``""`` when cleared).
        previous_subset: Subset string in place before the operation.
        message: Human-readable feedback for the UI.
    """
    success: bool
    subset_string: str
    previous_subset: str = ""
    message: str = ""
