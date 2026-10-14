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


class RasterExportJob:
    """Write a raster layer as it is currently displayed (filtered pixels = NoData).

    Built on the main thread (clones the provider), :meth:`run` may be called
    from a task thread.
    """

    def __init__(self, layer, path: str, fmt: str = 'GTiff', crs=None, compress: str = 'DEFLATE') -> None:
        from qgis.core import QgsProject, QgsRasterPipe
        self.layer_name = layer.name()
        self.path = path
        self.fmt = fmt if fmt in RASTER_FORMATS else 'GTiff'
        self.compress = compress
        self.layer_crs = layer.crs()
        self.target_crs = crs if crs is not None and crs.isValid() and crs != layer.crs() else None
        provider = layer.dataProvider()
        self.columns, self.rows, self.extent = provider.xSize(), provider.ySize(), provider.extent()
        self.pipe = QgsRasterPipe()
        self.pipe_ok = self.pipe.set(provider.clone())
        self.context = QgsProject.instance().transformContext()

    def run(self, feedback=None) -> ExportResult:
        from osgeo import gdal
        from qgis.core import QgsRasterFileWriter
        path = self.path
        if not self.pipe_ok:
            return ExportResult(False, path, 'raster pipe rejected the provider')
        os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
        staging = path if (self.fmt == 'GTiff' and self.target_crs is None) else path + '.staging.tif'
        writer = QgsRasterFileWriter(staging)
        writer.setOutputFormat('GTiff')
        writer.setCreateOptions([f'COMPRESS={self.compress}', 'TILED=YES', 'BIGTIFF=IF_SAFER'])
        error = writer.writeRaster(self.pipe, self.columns, self.rows, self.extent, self.layer_crs, self.context, feedback)
        if int(error) != 0:
            return ExportResult(False, path, f'raster writer error {int(error)}')
        manager = getattr(gdal, 'ExceptionMgr', None)
        scope = manager(useExceptions=True) if manager is not None else _NoScope()
        try:
            with scope:
                return self._finish(gdal, staging, path)
        except Exception as exc:
            return ExportResult(False, path, str(exc))

    def _finish(self, gdal, staging: str, path: str) -> ExportResult:
        try:
            current = staging
            if self.target_crs is not None:
                warped = path + '.warped.tif'
                if gdal.Warp(warped, current, dstSRS=self.target_crs.toWkt(), creationOptions=[f'COMPRESS={self.compress}', 'TILED=YES']) is None:
                    raise RuntimeError(gdal.GetLastErrorMsg() or 'gdal.Warp failed')
                _remove(current)
                current = warped
            if self.fmt == 'COG':
                if gdal.Translate(path, current, format='COG', creationOptions=[f'COMPRESS={self.compress}']) is None:
                    raise RuntimeError(gdal.GetLastErrorMsg() or 'gdal.Translate failed')
                _remove(current)
            elif current != path:
                shutil.move(current, path)
        except Exception as exc:
            return ExportResult(False, path, str(exc))
        return ExportResult(True, path)


class _NoScope:
    """Stand-in for gdal.ExceptionMgr on GDAL < 3.7 (results are checked instead)."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def export_raster(layer, path: str, fmt: str = 'GTiff', crs=None, compress: str = 'DEFLATE', feedback=None) -> ExportResult:
    """Synchronous raster export (scripts); the dock uses :class:`CoverageExportTask`."""
    return RasterExportJob(layer, path, fmt, crs, compress).run(feedback)


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


class PointCloudExportJob:
    """Write the points of a point cloud layer that pass its current filter.

    ``QgsPointCloudLayerExporter.prepareExport`` must run on the main thread
    (constructor); :meth:`run` may be called from a task thread.
    """

    def __init__(self, layer, path: str, fmt: str = 'LAZ', crs=None) -> None:
        from qgis.core import QgsPointCloudLayerExporter
        self.layer_name = layer.name()
        self.path = path
        self.fmt = fmt.upper() if fmt else 'LAZ'
        self.exporter = None
        self.error = ''
        if self.fmt not in POINT_CLOUD_FORMATS:
            self.error = f'unsupported point cloud format {self.fmt}'
            return
        os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
        exporter = QgsPointCloudLayerExporter(layer)
        exporter.setAllAttributes()
        if crs is not None and crs.isValid():
            exporter.setCrs(crs)
        formats = QgsPointCloudLayerExporter.ExportFormat
        self.target = path
        if self.fmt in ('LAZ', 'LAS', 'COPC'):
            exporter.setFormat(formats.Las)
            if self.fmt == 'COPC':
                self.target = path[:-len('.copc.laz')] + '.staging.laz' if path.lower().endswith('.copc.laz') else path + '.staging.laz'
        elif self.fmt == 'GPKG':
            exporter.setFormat(formats.Gpkg)
            exporter.setLayerName(layer.name())
        else:
            exporter.setFormat(formats.Csv)
        exporter.setFileName(self.target)
        exporter.prepareExport()
        self.exporter = exporter

    def run(self, feedback=None) -> ExportResult:
        path = self.path
        if self.exporter is None:
            return ExportResult(False, path, self.error or 'exporter unavailable')
        if feedback is not None:
            try:
                self.exporter.setFeedback(feedback)
            except Exception:
                pass
        self.exporter.doExport()
        error = self.exporter.lastError()
        if error:
            return ExportResult(False, path, error)
        if self.fmt == 'COPC':
            from . import pdal_cli
            if not pdal_cli.is_available():
                fallback = self.target.replace('.staging.laz', '.laz')
                shutil.move(self.target, fallback)
                return ExportResult(True, fallback, 'pdal not found: LAZ written instead of COPC')
            ok, message = pdal_cli.run_pipeline([
                {"type": "readers.las", "filename": self.target},
                {"type": "writers.copc", "filename": path, "forward": "all", "extra_dims": "all"},
            ])
            _remove(self.target)
            if not ok:
                return ExportResult(False, path, message)
        return ExportResult(True, path)


def export_point_cloud(layer, path: str, fmt: str = 'LAZ', crs=None) -> ExportResult:
    """Synchronous point cloud export (scripts); the dock uses :class:`CoverageExportTask`."""
    return PointCloudExportJob(layer, path, fmt, crs).run()


def make_export_task(jobs, on_done=None):
    """QgsTask running export jobs in the background; ``on_done(results)`` on the main thread."""
    from qgis.core import QgsTask

    class CoverageExportTask(QgsTask):
        def __init__(self):
            super().__init__('FilterMate: export', QgsTask.CanCancel)
            self.jobs = list(jobs)
            self.results = []

        def run(self):
            for index, job in enumerate(self.jobs):
                if self.isCanceled():
                    return False
                try:
                    self.results.append(job.run())
                except Exception as exc:
                    self.results.append(ExportResult(False, getattr(job, 'path', ''), str(exc)))
                self.setProgress(100.0 * (index + 1) / max(1, len(self.jobs)))
            return True

        def finished(self, result):
            for job in self.jobs:
                for name in ('exporter', 'pipe'):
                    if hasattr(job, name):
                        setattr(job, name, None)
            self.jobs = []
            if on_done is not None:
                try:
                    on_done(self.results)
                except Exception as exc:
                    logger.error(f"[FM5] export callback failed: {exc}", exc_info=True)

    return CoverageExportTask()
