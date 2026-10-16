# -*- coding: utf-8 -*-
"""
Geometry helpers shared by the coverage adapters.

* :func:`mask_to_geometry` turns a boolean grid (pixels of a raster selection,
  cells holding points of a point cloud selection) into one valid polygon.
* :func:`buffer_geometry` applies the FILTERING buffer settings.
* :func:`transform_geometry` reprojects a geometry for a target layer.
"""
import logging
from typing import Optional, Sequence, Tuple

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCoordinateTransformContext,
    QgsGeometry,
    QgsRectangle,
)

logger = logging.getLogger(__name__)


def _end_cap(buffer_type: str):
    style = getattr(Qgis, 'EndCapStyle', None)
    name = (buffer_type or 'Round').strip().lower()
    if style is not None:
        return {'flat': style.Flat, 'square': style.Square}.get(name, style.Round)
    return {'flat': 2, 'square': 3}.get(name, 1)


def _join_style(buffer_type: str):
    style = getattr(Qgis, 'JoinStyle', None)
    name = (buffer_type or 'Round').strip().lower()
    if style is not None:
        return style.Miter if name in ('flat', 'square') else style.Round
    return 2 if name in ('flat', 'square') else 1


def buffer_geometry(geometry: QgsGeometry, value: float, segments: int = 5, buffer_type: str = 'Round') -> QgsGeometry:
    """Buffer ``geometry`` like the vector engine does (negative value = erosion).

    Args:
        geometry: Source geometry.
        value: Distance in the geometry's CRS units; 0 returns a copy.
        segments: Segments per quarter circle.
        buffer_type: ``Round``, ``Flat`` or ``Square``.
    """
    if geometry is None or geometry.isEmpty() or not value:
        return QgsGeometry(geometry) if geometry is not None else QgsGeometry()
    try:
        result = geometry.buffer(float(value), int(segments or 5), _end_cap(buffer_type), _join_style(buffer_type), 2.0)
    except TypeError:
        result = geometry.buffer(float(value), int(segments or 5))
    if result is None or result.isEmpty():
        return QgsGeometry()
    return result


def transform_geometry(geometry: QgsGeometry, source_crs: QgsCoordinateReferenceSystem,
                       target_crs: QgsCoordinateReferenceSystem,
                       context: Optional[QgsCoordinateTransformContext] = None) -> QgsGeometry:
    """Return a copy of ``geometry`` in ``target_crs`` (no-op when the CRS are equal or invalid)."""
    result = QgsGeometry(geometry)
    if result.isEmpty() or not source_crs.isValid() or not target_crs.isValid() or source_crs == target_crs:
        return result
    transform = QgsCoordinateTransform(source_crs, target_crs, context or QgsCoordinateTransformContext())
    result.transform(transform)
    return result


def make_valid(geometry: QgsGeometry) -> QgsGeometry:
    """Return a valid version of ``geometry`` (unchanged when already valid)."""
    if geometry is None or geometry.isEmpty():
        return QgsGeometry()
    try:
        if geometry.isGeosValid():
            return geometry
        fixed = geometry.makeValid()
        return fixed if fixed is not None and not fixed.isEmpty() else geometry
    except Exception:
        return geometry


def union_geometries(geometries: Sequence[QgsGeometry]) -> QgsGeometry:
    """Union of a list of geometries, empty geometry for an empty list."""
    parts = [g for g in geometries if g is not None and not g.isEmpty()]
    if not parts:
        return QgsGeometry()
    if len(parts) == 1:
        return make_valid(QgsGeometry(parts[0]))
    return make_valid(QgsGeometry.unaryUnion(parts))


def extent_polygon(extent: QgsRectangle) -> QgsGeometry:
    return QgsGeometry.fromRect(extent)


def mask_to_geometry(mask, geotransform: Tuple[float, float, float, float, float, float], crs_wkt: str,
                     sieve_pixels: int = 0, simplify_tolerance: float = 0.0) -> QgsGeometry:
    """Polygonize the true cells of a 2D grid.

    Args:
        mask: 2D numpy array, non-zero where the cell is selected.
        geotransform: GDAL geotransform of the grid.
        crs_wkt: CRS of the grid (WKT).
        sieve_pixels: Remove selected patches smaller than this number of cells (0 = keep all).
        simplify_tolerance: Douglas-Peucker tolerance of the result (0 = none).

    Returns:
        A valid (multi)polygon, empty when nothing is selected.
    """
    import numpy as np
    from osgeo import gdal, ogr, osr

    grid = np.ascontiguousarray((mask != 0).astype('uint8'))
    if not grid.any():
        return QgsGeometry()
    rows, cols = grid.shape
    mem = gdal.GetDriverByName('MEM').Create('', int(cols), int(rows), 1, gdal.GDT_Byte)
    mem.SetGeoTransform(tuple(float(v) for v in geotransform))
    if crs_wkt:
        mem.SetProjection(crs_wkt)
    band = mem.GetRasterBand(1)
    band.WriteArray(grid)
    band.SetNoDataValue(0)
    if sieve_pixels and sieve_pixels > 1:
        gdal.SieveFilter(band, None, band, int(sieve_pixels), 8)
    driver = ogr.GetDriverByName('Memory') or ogr.GetDriverByName('MEM')
    vector = driver.CreateDataSource('fm5_mask')
    srs = osr.SpatialReference()
    if crs_wkt:
        srs.ImportFromWkt(crs_wkt)
    layer = vector.CreateLayer('mask', srs, ogr.wkbPolygon)
    layer.CreateField(ogr.FieldDefn('v', ogr.OFTInteger))
    gdal.Polygonize(band, band, layer, 0, [], callback=None)
    geometries = []
    for feature in layer:
        if feature.GetField(0) == 0:
            continue
        ogr_geom = feature.GetGeometryRef()
        if ogr_geom is not None:
            geometry = QgsGeometry()
            geometry.fromWkb(bytes(ogr_geom.ExportToWkb()))
            geometries.append(geometry)
    result = union_geometries(geometries)
    if simplify_tolerance and simplify_tolerance > 0 and not result.isEmpty():
        simplified = result.simplify(float(simplify_tolerance))
        if simplified is not None and not simplified.isEmpty():
            result = make_valid(simplified)
    return result


# Predicates a target can test against the union of the source features:
# intersecting the union is intersecting one of them, being disjoint from it
# is being disjoint from all of them. The others hold when ONE source feature
# satisfies them (see SourceParts).
WHOLE_SOURCE_METHODS = ('intersects', 'disjoint')

# QgsGeometryEngine methods to call on the *source* engine for a predicate
# expressed on the *target* (target.contains(source) == source.within(target)).
_ENGINE_METHOD_FOR_TARGET_METHOD = {
    'intersects': 'intersects',
    'disjoint': 'disjoint',
    'equals': 'isEqual',
    'touches': 'touches',
    'overlaps': 'overlaps',
    'crosses': 'crosses',
    'contains': 'within',
    'within': 'contains',
}


def prepared_engine(geometry: QgsGeometry):
    """Prepared GEOS engine of the source geometry."""
    engine = QgsGeometry.createGeometryEngine(geometry.constGet())
    engine.prepareGeometry()
    return engine


def target_matches(engine, target_geometry: QgsGeometry, methods: Sequence[str]) -> bool:
    """True when ``target.<method>(source)`` holds for at least one method (ORed)."""
    abstract = target_geometry.constGet()
    for method in methods:
        name = _ENGINE_METHOD_FOR_TARGET_METHOD.get(method, 'intersects')
        try:
            if getattr(engine, name)(abstract):
                return True
        except Exception as exc:  # invalid target geometry
            logger.debug(f"[FM5] predicate {method} failed on a target geometry: {exc}")
    return False


class SourceParts:
    """Source features tested one by one: ``target.<method>(feature)`` for at least one of them."""

    def __init__(self, parts: Sequence[QgsGeometry]) -> None:
        from qgis.core import QgsSpatialIndex
        self._engines = []
        self._index = QgsSpatialIndex()
        for part in parts:
            if part is None or part.isEmpty():
                continue
            self._index.addFeature(len(self._engines), part.boundingBox())
            self._engines.append(prepared_engine(part))

    def matches(self, target_geometry: QgsGeometry, methods: Sequence[str]) -> bool:
        """True when one source feature whose box meets the target's satisfies one of ``methods``."""
        for number in self._index.intersects(target_geometry.boundingBox()):
            if target_matches(self._engines[number], target_geometry, methods):
                return True
        return False
