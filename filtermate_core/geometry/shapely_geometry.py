# -*- coding: utf-8 -*-
"""``IGeometry`` implemented with shapely, and FilterMate's spatial filter on it.

``ShapelyGeometry`` behaves as ``adapters.qgis.geometry_adapter.QGISGeometryAdapter``
where the port defines the behaviour (an empty geometry is invalid, of type
``UNKNOWN``, with a null bounding box; buffer segments are per quarter circle).
Two differences: it keeps its CRS, so :meth:`ShapelyGeometry.transform`
reprojects (with pyproj) instead of returning a copy, and it accepts any
``IGeometry`` as the other operand (read through WKB).

:func:`source_union` and :func:`matches` give the semantics the SQL backends
implement (see ``PostgreSQLExpressionBuilder._predicate_against_sources``): a
target is kept when one of the enabled predicates holds between it and the
union of the selected source features, made valid and grown by the buffer; a
target without geometry is never kept.
"""
from typing import Any, Iterable, Mapping, Optional, Union

from ..domain.filter_expression import SpatialPredicate
from ..ports.qgis_port import BoundingBox, CoordinateReferenceSystem, GeometryType, IGeometry

try:
    import numpy as _np
    import shapely  # 2.0 or later: union_all, from_wkt, transform
    SHAPELY_AVAILABLE = True
except ImportError:
    _np = None
    shapely = None
    SHAPELY_AVAILABLE = False

try:
    from pyproj import Transformer as _Transformer
    PYPROJ_AVAILABLE = True
except ImportError:
    _Transformer = None
    PYPROJ_AVAILABLE = False


_GEOMETRY_TYPES = {
    'Point': GeometryType.POINT,
    'LineString': GeometryType.LINE,
    'LinearRing': GeometryType.LINE,
    'Polygon': GeometryType.POLYGON,
    'MultiPoint': GeometryType.MULTI_POINT,
    'MultiLineString': GeometryType.MULTI_LINE,
    'MultiPolygon': GeometryType.MULTI_POLYGON,
    'GeometryCollection': GeometryType.GEOMETRY_COLLECTION,
}

# Predicate name (as the task parameters spell it) -> shapely method name.
_PREDICATES = {
    'intersects': 'intersects',
    'contains': 'contains',
    'within': 'within',
    'crosses': 'crosses',
    'touches': 'touches',
    'overlaps': 'overlaps',
    'disjoint': 'disjoint',
    'equals': 'equals',
    'covers': 'covers',
    'coveredby': 'covered_by',
    'dwithin': 'dwithin',
}


def _require_shapely() -> None:
    if not SHAPELY_AVAILABLE:
        raise RuntimeError("shapely is required for filtermate_core.geometry (pip install shapely)")


def normalize_predicate(predicate: Union[str, SpatialPredicate]) -> str:
    """Predicate name as the task parameters spell it: ``ST_CoveredBy`` -> ``coveredby``.

    Raises:
        ValueError: for a name FilterMate does not know.
    """
    name = predicate.value if isinstance(predicate, SpatialPredicate) else str(predicate)
    name = name.strip().lower().replace('_', '')
    if name.startswith('st') and name[2:] in _PREDICATES:
        name = name[2:]
    if name not in _PREDICATES:
        raise ValueError(f"unknown spatial predicate: {predicate!r}")
    return name


class ShapelyGeometry(IGeometry):
    """A shapely geometry and the CRS its coordinates are in (``None`` if unknown)."""

    def __init__(self, geometry: Any = None, crs: Optional[CoordinateReferenceSystem] = None):
        _require_shapely()
        self._geometry = geometry if geometry is not None else shapely.Point()
        self._crs = crs

    @classmethod
    def from_wkt(cls, wkt: str, crs: Optional[CoordinateReferenceSystem] = None) -> 'ShapelyGeometry':
        _require_shapely()
        return cls(shapely.from_wkt(wkt), crs)

    @classmethod
    def from_wkb(cls, wkb: bytes, crs: Optional[CoordinateReferenceSystem] = None) -> 'ShapelyGeometry':
        _require_shapely()
        return cls(shapely.from_wkb(wkb), crs)

    @classmethod
    def of(cls, geometry: Any, crs: Optional[CoordinateReferenceSystem] = None) -> 'ShapelyGeometry':
        """Wrap a shapely geometry, or read any other ``IGeometry`` through its WKB."""
        _require_shapely()
        if isinstance(geometry, ShapelyGeometry):
            return geometry
        if isinstance(geometry, IGeometry):
            wkb = geometry.as_wkb()
            return cls(shapely.from_wkb(wkb) if wkb else None, crs)
        return cls(geometry, crs)

    @property
    def shape(self) -> Any:
        """The wrapped shapely geometry."""
        return self._geometry

    @property
    def crs(self) -> Optional[CoordinateReferenceSystem]:
        return self._crs

    def is_valid(self) -> bool:
        return not self._geometry.is_empty and bool(self._geometry.is_valid)

    def is_empty(self) -> bool:
        return bool(self._geometry.is_empty)

    def geometry_type(self) -> GeometryType:
        if self._geometry.is_empty:
            return GeometryType.UNKNOWN
        return _GEOMETRY_TYPES.get(self._geometry.geom_type, GeometryType.UNKNOWN)

    def as_wkt(self) -> str:
        if self._geometry.is_empty:
            return ""
        return self._geometry.wkt

    def as_wkb(self) -> bytes:
        if self._geometry.is_empty:
            return b""
        return self._geometry.wkb

    def buffer(self, distance: float, segments: int = 5) -> 'ShapelyGeometry':
        """Buffer in the units of the CRS; ``segments`` per quarter circle, as QGIS counts them."""
        if self._geometry.is_empty:
            return ShapelyGeometry(None, self._crs)
        return ShapelyGeometry(self._geometry.buffer(distance, quad_segs=segments), self._crs)

    def intersects(self, other: IGeometry) -> bool:
        return self.satisfies(other, 'intersects')

    def contains(self, other: IGeometry) -> bool:
        return self.satisfies(other, 'contains')

    def satisfies(self, other: Any, predicate: Union[str, SpatialPredicate],
                  distance: Optional[float] = None) -> bool:
        """``predicate(self, other)``; ``dwithin`` needs ``distance``.

        As the SQL backends: a missing or empty geometry on either side
        satisfies nothing but ``disjoint`` (an empty other operand) and is
        never kept by :func:`matches`.
        """
        name = normalize_predicate(predicate)
        other_shape = ShapelyGeometry.of(other).shape
        method = getattr(self._geometry, _PREDICATES[name])
        if name == 'dwithin':
            if distance is None:
                raise ValueError("dwithin needs a distance")
            return bool(method(other_shape, distance))
        return bool(method(other_shape))

    def bounding_box(self) -> BoundingBox:
        if self._geometry.is_empty:
            return BoundingBox(0.0, 0.0, 0.0, 0.0)
        xmin, ymin, xmax, ymax = self._geometry.bounds
        return BoundingBox(xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax)

    def transform(self, target_crs: CoordinateReferenceSystem) -> 'ShapelyGeometry':
        """Reproject to ``target_crs`` (lon/lat axis order, as QGIS).

        Raises:
            ValueError: when this geometry's CRS is unknown.
            RuntimeError: when pyproj is missing and the CRS differ.
        """
        if self._crs is None:
            raise ValueError("cannot transform a geometry whose CRS is unknown")
        if self._crs.auth_id == target_crs.auth_id or self._geometry.is_empty:
            return ShapelyGeometry(self._geometry, target_crs)
        if not PYPROJ_AVAILABLE:
            raise RuntimeError("pyproj is required to reproject (pip install pyproj)")
        transformer = _Transformer.from_crs(self._crs.auth_id, target_crs.auth_id, always_xy=True)

        def project(coords):
            return _np.column_stack(transformer.transform(*coords.T))

        has_z = bool(self._geometry.has_z)
        return ShapelyGeometry(shapely.transform(self._geometry, project, include_z=has_z), target_crs)

    def __eq__(self, other) -> bool:
        if not isinstance(other, ShapelyGeometry):
            return NotImplemented
        return self._crs == other._crs and bool(self._geometry.equals_exact(other._geometry, 0.0))

    def __hash__(self):
        return hash((self._geometry.wkb, self._crs))

    def __repr__(self) -> str:
        crs = self._crs.auth_id if self._crs else 'unknown CRS'
        return f"ShapelyGeometry({self.as_wkt()[:60] or 'EMPTY'!s}, {crs})"


def source_union(geometries: Iterable[Any], buffer_distance: Optional[float] = None,
                 segments: int = 5, crs: Optional[CoordinateReferenceSystem] = None) -> ShapelyGeometry:
    """The one geometry targets are tested against: the valid union of the sources, buffered.

    Each source is made valid first (GEOS raises on an invalid polygon, which
    would reject the whole filter); the buffer, in the units of the CRS,
    applies to the union, so a negative one erodes the union and not each
    feature. Missing and empty geometries are skipped.
    """
    _require_shapely()
    shapes = []
    for geometry in geometries:
        if geometry is None:
            continue
        shape = ShapelyGeometry.of(geometry).shape
        if shape is not None and not shape.is_empty:
            shapes.append(shapely.make_valid(shape))
    union = shapely.union_all(shapes) if shapes else shapely.GeometryCollection()
    if buffer_distance:
        union = union.buffer(buffer_distance, quad_segs=segments)
    return ShapelyGeometry(union, crs)


def matches(target: Any, source: Any,
            predicates: Union[Mapping[Any, bool], Iterable[Any]],
            distance: Optional[float] = None) -> bool:
    """Whether FilterMate keeps ``target`` for ``source`` (usually a :func:`source_union`).

    Args:
        target: The target feature's geometry (shapely, ``IGeometry`` or None).
        source: The source geometry.
        predicates: ``{'intersects': True, 'touches': False}`` as in the task
            parameters, or the enabled names; ``ST_`` names and
            ``SpatialPredicate`` members are accepted. Combined with OR.
        distance: For ``dwithin``.

    Raises:
        ValueError: when no predicate is enabled or one is unknown.
    """
    if isinstance(predicates, Mapping):
        enabled = [name for name, on in predicates.items() if on]
    else:
        enabled = list(predicates)
    names = [normalize_predicate(name) for name in enabled]
    if not names:
        raise ValueError("no spatial predicate enabled")
    if target is None:
        return False
    target_geometry = ShapelyGeometry.of(target)
    if target_geometry.is_empty():
        return False
    return any(target_geometry.satisfies(source, name, distance) for name in names)


__all__ = [
    'PYPROJ_AVAILABLE',
    'SHAPELY_AVAILABLE',
    'ShapelyGeometry',
    'matches',
    'normalize_predicate',
    'source_union',
]
