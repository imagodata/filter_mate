# -*- coding: utf-8 -*-
"""
``gdal.Warp`` for the raster targets, on every GDAL QGIS ships with.

``cutlineWKT`` and ``cutlineSRS`` came with GDAL 3.9 (Ubuntu 24.04 has 3.8,
the QGIS 3.22-3.34 images 3.4). Older versions get the same cutline through
an in-memory GeoPackage (``cutlineDSName``) that carries its CRS; a warped VRT
stores the cutline itself, so the file is removed right after the call.

A cutline must be polygonal: the polygon parts of a geometry collection
(``make_valid`` or an intersection can add lines and points) are kept, curves
are linearized and Z / M dropped, on both paths.
"""
import inspect
import logging
import uuid
from typing import Optional

logger = logging.getLogger(__name__)


def warp_option_supported(name: str) -> bool:
    """True when ``gdal.WarpOptions`` takes the keyword ``name``."""
    from osgeo import gdal
    try:
        return name in inspect.signature(gdal.WarpOptions).parameters
    except (TypeError, ValueError):
        return int(gdal.VersionInfo()) >= 3090000


def _polygonal(wkt: str):
    """OGR geometry made of the polygon parts of ``wkt`` (2D, linear); None when it has none."""
    from osgeo import ogr
    try:
        geometry = ogr.CreateGeometryFromWkt(wkt)
    except RuntimeError as exc:  # OGR exceptions on (another plugin called ogr.UseExceptions())
        raise RuntimeError(f"invalid cutline WKT: {wkt[:80]} ({exc})") from exc
    if geometry is None:
        raise RuntimeError(f"invalid cutline WKT: {wkt[:80]}")
    if geometry.HasCurveGeometry():
        geometry = geometry.GetLinearGeometry()
    geometry.FlattenTo2D()
    if ogr.GT_Flatten(geometry.GetGeometryType()) in (ogr.wkbPolygon, ogr.wkbMultiPolygon):
        return geometry
    polygons = ogr.Geometry(ogr.wkbMultiPolygon)

    def collect(part):
        kind = ogr.GT_Flatten(part.GetGeometryType())
        if kind == ogr.wkbPolygon:
            polygons.AddGeometry(part)
        elif kind in (ogr.wkbMultiPolygon, ogr.wkbGeometryCollection):
            for index in range(part.GetGeometryCount()):
                collect(part.GetGeometryRef(index))

    collect(geometry)
    return polygons if polygons.GetGeometryCount() else None


def polygonal_wkt(wkt: str) -> Optional[str]:
    """WKT of the polygon parts of ``wkt``; None when it has none (lines or points only)."""
    geometry = _polygonal(wkt)
    return geometry.ExportToWkt() if geometry is not None else None


def _cutline_folder(geometry, srs_wkt: str) -> str:
    """Write the cutline to a ``/vsimem/`` folder; return the folder (the GeoPackage is ``cutline.gpkg`` in it)."""
    from osgeo import gdal, ogr, osr
    folder = f"/vsimem/fm5_cutline_{uuid.uuid4().hex}"
    try:
        srs = None
        if srs_wkt:
            srs = osr.SpatialReference()
            if srs.ImportFromWkt(srs_wkt) != 0:
                raise RuntimeError(f"invalid cutline CRS: {srs_wkt[:80]}")
            if hasattr(srs, 'SetAxisMappingStrategy'):
                srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        dataset = ogr.GetDriverByName('GPKG').CreateDataSource(f"{folder}/cutline.gpkg")
        if dataset is None:
            raise RuntimeError(gdal.GetLastErrorMsg() or 'cutline file could not be created')
        layer = dataset.CreateLayer('cutline', srs, ogr.wkbMultiPolygon)
        if layer is None:
            raise RuntimeError(gdal.GetLastErrorMsg() or 'cutline layer could not be created')
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetGeometry(ogr.ForceToMultiPolygon(geometry))
        if layer.CreateFeature(feature) != 0:
            raise RuntimeError(gdal.GetLastErrorMsg() or 'cutline could not be written')
        feature = None
        dataset = None  # noqa: F841 - flush the file
    except Exception:
        _remove_folder(folder)
        raise
    return folder


def _remove_folder(folder: str) -> None:
    """Best effort: a failing unlink (exceptions on, no folder entry on old GDAL) must not mask the warp."""
    from osgeo import gdal
    try:
        names = gdal.ReadDir(folder) or []
    except Exception:
        names = []
    for path in [f"{folder}/{name}" for name in names] + [folder]:
        try:
            gdal.Unlink(path)
        except Exception as exc:
            logger.debug(f"[FM5] {path} not removed: {exc}")


def gdal_warp(destination: str, source: str, **options):
    """gdal.Warp with exceptions scoped to the call (no global UseExceptions in a task thread)."""
    from osgeo import gdal
    folder = ''
    if 'cutlineWKT' in options:
        geometry = _polygonal(options['cutlineWKT'])
        if geometry is None:
            raise RuntimeError("the source geometry has no area (lines or points only): add a buffer")
        if warp_option_supported('cutlineWKT'):
            options['cutlineWKT'] = geometry.ExportToWkt()
        else:
            srs_wkt = options.get('cutlineSRS') or ''
            if not warp_option_supported('cutlineSRS'):
                options.pop('cutlineSRS', None)  # the GeoPackage carries the CRS
            options.pop('cutlineWKT')
            folder = _cutline_folder(geometry, srs_wkt)
            options['cutlineDSName'] = f"{folder}/cutline.gpkg"
    try:
        gdal.ErrorReset()  # GDAL < 3.7: no stale message from an earlier call
        manager = getattr(gdal, 'ExceptionMgr', None)
        if manager is not None:
            with manager(useExceptions=True):
                return gdal.Warp(destination, source, **options)
        dataset = gdal.Warp(destination, source, **options)
        if dataset is None:
            raise RuntimeError(gdal.GetLastErrorMsg() or 'gdal.Warp failed')
        return dataset
    finally:
        if folder:
            _remove_folder(folder)
