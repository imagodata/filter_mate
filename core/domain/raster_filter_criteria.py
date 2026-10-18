"""
Raster Filter Criteria - Domain Objects for Raster Sampling and Filtering.

Pure Python value objects for raster value sampling operations.
These define the contract between UI, services, and infrastructure layers.

This is a PURE PYTHON module with NO QGIS dependencies,
enabling true unit testing and clear separation of concerns.

Phase 1: Value Sampling criteria and results.
Future phases: Zonal Stats criteria, Histogram ranges, Band compositions.
"""
from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Dict, Optional, Tuple


class SamplingMethod(Enum):
    """Method for extracting raster values at vector feature locations.

    CENTROID: Fastest but inaccurate for concave polygons (point may fall outside).
    POINT_ON_SURFACE: Guaranteed inside polygon. Preferred default.
    MEAN_UNDER_POLYGON: Average of all raster cells under the polygon. Slowest but most accurate.
    """
    CENTROID = "centroid"
    POINT_ON_SURFACE = "point_on_surface"
    MEAN_UNDER_POLYGON = "mean_under_polygon"


class ComparisonOperator(Enum):
    """Comparison operators for filtering sampled raster values.

    Standard numeric comparisons plus BETWEEN for range filtering.
    """
    EQUAL = "="
    NOT_EQUAL = "!="
    GREATER_THAN = ">"
    GREATER_EQUAL = ">="
    LESS_THAN = "<"
    LESS_EQUAL = "<="
    BETWEEN = "BETWEEN"

    @property
    def symbol(self) -> str:
        """Return the operator symbol for display."""
        return self.value

    def evaluate(self, value: float, threshold: float, threshold_max: Optional[float] = None) -> bool:
        """Evaluate the comparison against a value.

        Args:
            value: The sampled raster value to test.
            threshold: The primary threshold value.
            threshold_max: Upper bound for BETWEEN operator.

        Returns:
            True if the comparison holds, False otherwise.

        Raises:
            ValueError: If BETWEEN is used without threshold_max.
        """
        if self == ComparisonOperator.EQUAL:
            return value == threshold
        elif self == ComparisonOperator.NOT_EQUAL:
            return value != threshold
        elif self == ComparisonOperator.GREATER_THAN:
            return value > threshold
        elif self == ComparisonOperator.GREATER_EQUAL:
            return value >= threshold
        elif self == ComparisonOperator.LESS_THAN:
            return value < threshold
        elif self == ComparisonOperator.LESS_EQUAL:
            return value <= threshold
        elif self == ComparisonOperator.BETWEEN:
            if threshold_max is None:
                raise ValueError("BETWEEN operator requires threshold_max")
            return threshold <= value <= threshold_max
        return False


@dataclass(frozen=True)
class RasterSamplingCriteria:
    """Immutable criteria for a raster value sampling operation.

    Defines what to sample, how, and how to filter the results.
    Frozen dataclass ensures thread safety when passed to tasks.

    Attributes:
        raster_uri: URI/path of the raster layer to sample from.
        vector_uri: URI/path of the vector layer providing feature geometries.
        band: 1-based band number to sample.
        method: Sampling method (how to extract point from geometry).
        operator: Comparison operator for filtering.
        threshold: Primary threshold value.
        threshold_max: Upper bound for BETWEEN operator (None otherwise).
    """
    raster_uri: str
    vector_uri: str
    band: int = 1
    method: SamplingMethod = SamplingMethod.POINT_ON_SURFACE
    operator: ComparisonOperator = ComparisonOperator.GREATER_EQUAL
    threshold: float = 0.0
    threshold_max: Optional[float] = None

    def __post_init__(self):
        """Validate criteria after initialization."""
        if self.band < 1:
            raise ValueError(f"Band number must be >= 1, got {self.band}")
        if self.operator == ComparisonOperator.BETWEEN and self.threshold_max is None:
            raise ValueError("BETWEEN operator requires threshold_max")
        if (self.threshold_max is not None
                and self.operator == ComparisonOperator.BETWEEN
                and self.threshold_max < self.threshold):
            raise ValueError(
                f"threshold_max ({self.threshold_max}) must be >= threshold ({self.threshold})"
            )


@dataclass
class RasterSamplingResult:
    """Result of a raster value sampling operation.

    Contains the per-feature sampled values and aggregated statistics.
    Not frozen because it is built incrementally during task execution.

    Attributes:
        feature_values: Mapping of feature ID to sampled raster value.
            None value means the sample point fell on NoData or outside raster extent.
        matching_ids: Set of feature IDs that pass the filter criteria.
        total_features: Total number of features processed.
        sampled_count: Number of features with valid (non-None) raster values.
        nodata_count: Number of features that fell on NoData.
        error_message: Error description if operation failed, None on success.
        stats: Summary statistics of sampled values.
    """
    feature_values: Dict[int, Optional[float]] = field(default_factory=dict)
    matching_ids: list = field(default_factory=list)
    total_features: int = 0
    sampled_count: int = 0
    nodata_count: int = 0
    error_message: Optional[str] = None
    stats: Optional['SamplingStats'] = None

    @property
    def matching_count(self) -> int:
        """Number of features passing the filter criteria."""
        return len(self.matching_ids)

    @property
    def is_success(self) -> bool:
        """Whether the sampling operation completed without error."""
        return self.error_message is None

    def summary(self) -> str:
        """Human-readable summary of the sampling result.

        Returns:
            Formatted string like '342/1204 features retained'.
        """
        if not self.is_success:
            return f"Error: {self.error_message}"
        return (
            f"{self.matching_count}/{self.total_features} features retained "
            f"({self.sampled_count} sampled, {self.nodata_count} NoData)"
        )


@dataclass(frozen=True)
class SamplingStats:
    """Summary statistics for sampled raster values.

    Computed from the valid (non-None) values in RasterSamplingResult.

    Attributes:
        min_value: Minimum sampled value.
        max_value: Maximum sampled value.
        mean_value: Mean of sampled values.
        std_value: Standard deviation of sampled values.
        median_value: Median of sampled values.
    """
    min_value: float = 0.0
    max_value: float = 0.0
    mean_value: float = 0.0
    std_value: float = 0.0
    median_value: float = 0.0

    @classmethod
    def from_values(cls, values: list) -> Optional['SamplingStats']:
        """Compute stats from a list of float values.

        Args:
            values: List of sampled raster values (no None entries).

        Returns:
            SamplingStats instance, or None if values is empty.
        """
        if not values:
            return None
        n = len(values)
        sorted_vals = sorted(values)
        min_val = sorted_vals[0]
        max_val = sorted_vals[-1]
        mean_val = sum(sorted_vals) / n

        # Standard deviation (population)
        variance = sum((v - mean_val) ** 2 for v in sorted_vals) / n
        std_val = variance ** 0.5

        # Median
        if n % 2 == 0:
            median_val = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
        else:
            median_val = sorted_vals[n // 2]

        return cls(
            min_value=min_val,
            max_value=max_val,
            mean_value=mean_val,
            std_value=std_val,
            median_value=median_val,
        )


# ---------------------------------------------------------------------------
# FilterMate 5: selection on a raster source (EXPLORING)
# ---------------------------------------------------------------------------

class RasterSelectionMode(Enum):
    """How the pixels of a raster source are selected in EXPLORING."""

    RANGE = "range"
    CLASSES = "classes"
    EXPRESSION = "expression"


class RasterDerivative(Enum):
    """Quantity the RANGE of a selection is read on: the pixel value or a terrain derivative.

    A derivative is computed from the band read as an elevation model (DTM), over the
    3 x 3 neighbourhood of each pixel; the raster calculator has none of them, so only
    a RANGE selection can use one.
    """

    VALUE = "value"
    SLOPE_DEGREES = "slope_degrees"
    SLOPE_PERCENT = "slope_percent"
    ASPECT = "aspect"
    HILLSHADE = "hillshade"
    ROUGHNESS = "roughness"

    @property
    def is_terrain(self) -> bool:
        return self is not RasterDerivative.VALUE


# Natural bounds of the derivatives that have some (None: unbounded above).
DERIVATIVE_BOUNDS = {
    RasterDerivative.SLOPE_DEGREES: (0.0, 90.0),
    RasterDerivative.ASPECT: (0.0, 360.0),
    RasterDerivative.HILLSHADE: (0.0, 255.0),
}


@dataclass(frozen=True)
class RasterSelection:
    """Pixels kept by a raster EXPLORING selection.

    Attributes:
        band: 1-based band number.
        mode: Range of values, set of class values, or raster calculator expression.
        minimum: Lower bound (inclusive) for RANGE, None = unbounded.
        maximum: Upper bound (inclusive) for RANGE, None = unbounded.
        classes: Pixel values kept for CLASSES (paletted / categorical rasters).
        expression: Raster calculator expression for EXPRESSION, using
            ``"<ref>@<band>"`` references; a pixel is kept where it is not 0.
        derivative: Quantity the RANGE bounds apply to (slope, aspect... of the
            band read as a DTM); the pixel value by default.
        seeds: Points ``(x, y)`` in the layer CRS (clicks of the pipette in object
            detection): only the patches of kept pixels that hold one of them are
            selected, a pool rather than every pixel of its colour. Empty: every
            kept pixel of the raster.
        objects: One selection per seed, each with its own criterion (the colour,
            class or value picked there): a pool and the lawn beside it, clicked
            one after the other, stay two objects instead of one patch of both
            colours. The criterion of this selection is then their union (what
            the whole raster would keep). Empty: every seed grows in this criterion.
        similar: ``(low, high)`` area ratios of the "similar objects" mode: every
            patch of kept pixels of the raster whose area is between ``low`` times
            the smallest clicked object and ``high`` times the largest one is
            selected (all the pools like this one). Needs seeds. Empty: the
            clicked objects only (object detection) or every kept pixel.
    """

    band: int = 1
    mode: RasterSelectionMode = RasterSelectionMode.RANGE
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    classes: frozenset = frozenset()
    expression: str = ""
    derivative: RasterDerivative = RasterDerivative.VALUE
    seeds: Tuple[Tuple[float, float], ...] = ()
    objects: Tuple["RasterSelection", ...] = ()
    similar: Tuple[float, float] = ()

    def __post_init__(self):
        object.__setattr__(self, "similar", _similar_from(self.similar))
        if self.similar and not (self.seeds or self.objects):
            raise ValueError("similar objects need a clicked object (a seed)")
        if not isinstance(self.derivative, RasterDerivative):
            object.__setattr__(self, "derivative", _derivative_from(self.derivative))
        object.__setattr__(self, "seeds", _seeds_from(self.seeds))
        objects = tuple(self.objects or ())
        for item in objects:
            if not isinstance(item, RasterSelection) or len(item.seeds) != 1 or item.objects:
                raise ValueError("an object is a selection of one seed, without objects of its own")
        object.__setattr__(self, "objects", objects)
        if objects and not self.seeds:
            object.__setattr__(self, "seeds", _seeds_from(item.seeds[0] for item in objects))
        if self.band < 1:
            raise ValueError(f"band must be >= 1, got {self.band}")
        if self.derivative.is_terrain and self.mode is not RasterSelectionMode.RANGE:
            raise ValueError(f"a {self.derivative.value} selection must use the range mode, not {self.mode.value}")
        if (self.mode is RasterSelectionMode.RANGE and self.minimum is not None
                and self.maximum is not None and self.minimum > self.maximum):
            raise ValueError(f"minimum ({self.minimum}) > maximum ({self.maximum})")

    @property
    def is_empty(self) -> bool:
        """True when the selection keeps no constraint at all."""
        if self.mode is RasterSelectionMode.RANGE:
            return self.minimum is None and self.maximum is None
        if self.mode is RasterSelectionMode.CLASSES:
            return not self.classes
        return not (self.expression or "").strip()

    def keeps(self, value: float) -> bool:
        """Tell whether one pixel value is selected (RANGE and CLASSES only).

        Raises:
            ValueError: For EXPRESSION, which needs the raster calculator.
        """
        if self.mode is RasterSelectionMode.RANGE:
            if self.minimum is not None and value < self.minimum:
                return False
            if self.maximum is not None and value > self.maximum:
                return False
            return True
        if self.mode is RasterSelectionMode.CLASSES:
            return int(round(value)) in self.classes
        raise ValueError("an expression selection cannot be evaluated per value")

    def to_calc_formula(self, reference: str) -> str:
        """Raster calculator formula, 1 where the pixel is selected and 0 elsewhere.

        Args:
            reference: Layer reference used in the virtual raster (``"mnt"``).

        Returns:
            Formula such as ``("mnt@1" >= 200 AND "mnt@1" <= 260)``.

        Raises:
            ValueError: For a terrain derivative, which the raster calculator cannot compute.
        """
        if self.derivative.is_terrain:
            raise ValueError("a terrain derivative cannot be written as a raster calculator formula")
        ref = f'"{reference}@{self.band}"'
        if self.mode is RasterSelectionMode.RANGE:
            parts = []
            if self.minimum is not None:
                parts.append(f"{ref} >= {_fmt(self.minimum)}")
            if self.maximum is not None:
                parts.append(f"{ref} <= {_fmt(self.maximum)}")
            return "(" + " AND ".join(parts) + ")" if parts else "1"
        if self.mode is RasterSelectionMode.CLASSES:
            if not self.classes:
                return "0"
            return "(" + " OR ".join(f"{ref} = {_fmt(c)}" for c in sorted(self.classes)) + ")"
        return f"({self.expression.strip()})" if self.expression.strip() else "1"

    def describe(self) -> str:
        """Short human readable summary (English, translated by the UI)."""
        if self.mode is RasterSelectionMode.RANGE:
            low = "-∞" if self.minimum is None else _fmt(self.minimum)
            high = "+∞" if self.maximum is None else _fmt(self.maximum)
            what = "band" if not self.derivative.is_terrain else self.derivative.value.replace("_", " ") + " of band"
            text = f"{what} {self.band} in [{low} ; {high}]"
        elif self.mode is RasterSelectionMode.CLASSES:
            text = f"band {self.band} classes " + ", ".join(_fmt(c) for c in sorted(self.classes))
        else:
            text = self.expression.strip()
        if self.seeds and self.similar:
            text += (f" · objects like the one(s) under {len(self.seeds)} click(s), "
                     f"×{_fmt(self.similar[0])} to ×{_fmt(self.similar[1])} in area")
        elif self.seeds:
            text += f" · object(s) under {len(self.seeds)} click(s)"
        return text

    def to_dict(self) -> Dict:
        data = {
            "band": self.band,
            "mode": self.mode.value,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "classes": sorted(self.classes),
            "expression": self.expression,
            "derivative": self.derivative.value,
        }
        if self.seeds:  # older readers see the same keys as before without object detection
            data["seeds"] = [list(seed) for seed in self.seeds]
        if self.objects:
            data["objects"] = [item.to_dict() for item in self.objects]
        if self.similar:
            data["similar"] = list(self.similar)
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "RasterSelection":
        return cls(
            band=int(data.get("band", 1)),
            mode=RasterSelectionMode(data.get("mode", "range")),
            minimum=data.get("minimum"),
            maximum=data.get("maximum"),
            classes=frozenset(int(c) for c in data.get("classes", ()) or ()),
            expression=data.get("expression", "") or "",
            derivative=_derivative_from(data.get("derivative")),
            seeds=data.get("seeds") or (),
            objects=tuple(cls.from_dict(item) for item in data.get("objects") or ()),
            similar=tuple(data.get("similar") or ()),
        )


def _fmt(value) -> str:
    """Format a number without a useless trailing ``.0``."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return repr(value) if isinstance(value, float) else str(value)


def _similar_from(value) -> Tuple[float, float]:
    """``(low, high)`` area ratios, ordered, both above zero; ``()`` for anything else.

    Raises:
        ValueError: For a malformed pair.
    """
    if not value:
        return ()
    try:
        low, high = (float(item) for item in value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"similar objects ratios must be a (low, high) pair, got {value!r}") from exc
    if not (low > 0 and high > 0) or low != low or high != high:
        raise ValueError(f"similar objects ratios must be above zero, got {value!r}")
    return (min(low, high), max(low, high))


def _seeds_from(value) -> Tuple[Tuple[float, float], ...]:
    """Seeds as a tuple of ``(x, y)`` floats, in order, without duplicates.

    Raises:
        ValueError: For a seed that is not two finite numbers.
    """
    seeds = []
    for seed in value or ():
        try:
            x, y = (float(v) for v in seed)
        except (TypeError, ValueError):
            raise ValueError(f"a seed is a point (x, y), got {seed!r}") from None
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError(f"a seed must be finite, got {seed!r}")
        if (x, y) not in seeds:
            seeds.append((x, y))
    return tuple(seeds)


def _derivative_from(value) -> RasterDerivative:
    """Derivative named ``value``; the pixel value when missing (older saved states)."""
    try:
        return RasterDerivative(value or RasterDerivative.VALUE.value)
    except ValueError:
        raise ValueError(f"unknown raster derivative {value!r}") from None
