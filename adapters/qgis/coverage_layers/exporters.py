# -*- coding: utf-8 -*-
"""
Export raster and point cloud layers as they are currently filtered.

* Raster: the layer's current provider (original, clipped VRT or virtual
  raster) is written through ``QgsRasterFileWriter`` as GeoTIFF; ``COG`` is
  produced from it with ``gdal.Translate``. Pixels outside the filter stay
  NoData. Optional reprojection with ``gdal.Warp``.
* Point cloud: ``QgsPointCloudLayerExporter`` honors the subset string; the
  derived file of a clipped layer already holds the clipped points. LAZ, LAS,
  GPKG (points) and CSV; COPC through ``pdal translate`` when available.
"""
import logging
import os
import shutil
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

RASTER_FORMATS = {'GTiff': '.tif', 'COG': '.tif'}
POINT_CLOUD_FORMATS = {'LAZ': '.laz', 'LAS': '.las', 'COPC': '.copc.laz', 'GPKG': '.gpkg', 'CSV': '.csv'}


@dataclass
class ExportResult:
    success: bool
    path: str = ''
    message: str = ''


def output_path(folder: str, layer_name: str, extension: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_ ." else "_" for c in layer_name).strip() or "layer"
    return os.path.join(folder, safe + extension)


def export_raster(layer, path: str, fmt: str = 'GTiff', crs=None, compress: str = 'DEFLATE', feedback=None) -> ExportResult:
    """Write a raster layer as it is currently displayed (filtered pixels = NoData).

    Args:
        layer: QgsRasterLayer.
        path: Output file.
        fmt: ``GTiff`` or ``COG``.
        crs: Optional QgsCoordinateReferenceSystem to reproject to.
        compress: GDAL compression.
        feedback: Optional QgsRasterBlockFeedback.
    """
    from osgeo import gdal
    from qgis.core import QgsRasterFileWriter, QgsRasterPipe
    gdal.UseExceptions()
    fmt = fmt if fmt in RASTER_FORMATS else 'GTiff'
    os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
    reproject = crs is not None and crs.isValid() and crs != layer.crs()
    staging = path if (fmt == 'GTiff' and not reproject) else path + '.staging.tif'
    provider = layer.dataProvider()
    pipe = QgsRasterPipe()
    if not pipe.set(provider.clone()):
        return ExportResult(False, path, 'raster pipe rejected the provider')
    writer = QgsRasterFileWriter(staging)
    writer.setOutputFormat('GTiff')
    writer.setCreateOptions([f'COMPRESS={compress}', 'TILED=YES', 'BIGTIFF=IF_SAFER'])
    from qgis.core import QgsProject
    error = writer.writeRaster(pipe, provider.xSize(), provider.ySize(), provider.extent(), layer.crs(),
                               QgsProject.instance().transformContext(), feedback)
    if int(error) != 0:
        return ExportResult(False, path, f'raster writer error {int(error)}')
    try:
        current = staging
        if reproject:
            warped = path + '.warped.tif'
            gdal.Warp(warped, current, dstSRS=crs.toWkt(), creationOptions=[f'COMPRESS={compress}', 'TILED=YES'])
            _remove(current)
            current = warped
        if fmt == 'COG':
            gdal.Translate(path, current, format='COG', creationOptions=[f'COMPRESS={compress}'])
            _remove(current)
        elif current != path:
            shutil.move(current, path)
    except Exception as exc:
        return ExportResult(False, path, str(exc))
    return ExportResult(True, path)


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def export_point_cloud(layer, path: str, fmt: str = 'LAZ', crs=None) -> ExportResult:
    """Write the points of a point cloud layer that pass its current filter.

    Args:
        layer: QgsPointCloudLayer.
        path: Output file.
        fmt: ``LAZ``, ``LAS``, ``COPC``, ``GPKG`` or ``CSV``.
        crs: Optional output CRS.
    """
    from qgis.core import QgsPointCloudLayerExporter
    fmt = fmt.upper() if fmt else 'LAZ'
    if fmt not in POINT_CLOUD_FORMATS:
        return ExportResult(False, path, f'unsupported point cloud format {fmt}')
    os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
    exporter = QgsPointCloudLayerExporter(layer)
    exporter.setAllAttributes()
    if crs is not None and crs.isValid():
        exporter.setCrs(crs)
    formats = QgsPointCloudLayerExporter.ExportFormat
    target = path
    if fmt in ('LAZ', 'LAS', 'COPC'):
        exporter.setFormat(formats.Las)
        if fmt == 'COPC':
            target = path[:-len('.copc.laz')] + '.staging.laz' if path.lower().endswith('.copc.laz') else path + '.staging.laz'
    elif fmt == 'GPKG':
        exporter.setFormat(formats.Gpkg)
        exporter.setLayerName(layer.name())
    else:
        exporter.setFormat(formats.Csv)
    exporter.setFileName(target)
    exporter.prepareExport()
    exporter.doExport()
    error = exporter.lastError()
    if error:
        return ExportResult(False, path, error)
    if fmt == 'COPC':
        from . import pdal_cli
        if not pdal_cli.is_available():
            fallback = target.replace('.staging.laz', '.laz')
            shutil.move(target, fallback)
            return ExportResult(True, fallback, 'pdal not found: LAZ written instead of COPC')
        ok, message = pdal_cli.run_pipeline([
            {"type": "readers.las", "filename": target},
            {"type": "writers.copc", "filename": path, "forward": "all", "extra_dims": "all"},
        ])
        _remove(target)
        if not ok:
            return ExportResult(False, path, message)
    return ExportResult(True, path)
