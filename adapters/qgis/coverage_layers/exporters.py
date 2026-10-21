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
import tempfile
from dataclasses import dataclass


logger = logging.getLogger(__name__)

RASTER_FORMATS = {'GTiff': '.tif', 'COG': '.tif'}
# Side files GDAL keeps next to a raster (statistics, overviews, masks).
RASTER_SIDE_FILES = ('.aux.xml', '.ovr', '.ovr.aux.xml', '.msk', '.msk.aux.xml')
POINT_CLOUD_FORMATS = {'LAZ': '.laz', 'LAS': '.las', 'COPC': '.copc.laz', 'GPKG': '.gpkg', 'CSV': '.csv'}


@dataclass
class ExportResult:
    success: bool
    path: str = ''
    message: str = ''


def output_path(folder: str, layer_name: str, extension: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_ ." else "_" for c in layer_name).strip() or "layer"
    return os.path.join(folder, safe + extension)


def set_creation_options(writer, options) -> None:
    """GDAL creation options of a ``QgsRasterFileWriter``: ``setCreateOptions`` is deprecated since QGIS 3.44."""
    setter = getattr(writer, 'setCreationOptions', None) or writer.setCreateOptions
    setter(list(options))


def export_sources(layers=(), project=None):
    """Files needed by current layers and undo steps, captured on the main thread."""
    from qgis.core import QgsProject
    from ....core.export.target_guard import ProjectSources
    from ....core.services.cross_filter_service import protected_sources
    return ProjectSources(project if project is not None else QgsProject.instance(), layers=layers,
                          additional_sources=(('FilterMate state', source) for source in protected_sources()))


def _check_destination(path, sources) -> None:
    if os.path.islink(path):
        raise ValueError(f"not written: {path} is a symbolic link")
    name = sources.layer_using(path)
    if name is not None:
        raise ValueError(f"not written: {path} is the data source of the layer '{name}'")


class RasterExportJob:
    """Write a raster layer as it is currently displayed (filtered pixels = NoData).

    Built on the main thread (clones the provider), :meth:`run` may be called
    from a task thread.
    """

    def __init__(self, layer, path: str, fmt: str = 'GTiff', crs=None, compress: str = 'DEFLATE') -> None:
        from qgis.core import QgsProject, QgsRasterPipe
        self.layer_name = layer.name()
        self.path = path
        _check_destination(path, export_sources((layer,)))
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
        with tempfile.TemporaryDirectory(prefix='.filtermate-export-', dir=os.path.dirname(os.path.abspath(path))) as folder:
            return self._write(gdal, QgsRasterFileWriter, os.path.join(folder, 'staging.tif'), feedback)

    def _write(self, gdal, writer_class, staging, feedback) -> ExportResult:
        path = self.path
        writer = writer_class(staging)
        writer.setOutputFormat('GTiff')
        set_creation_options(writer, [f'COMPRESS={self.compress}', 'TILED=YES', 'BIGTIFF=IF_SAFER'])
        error = writer.writeRaster(self.pipe, self.columns, self.rows, self.extent, self.layer_crs, self.context, feedback)
        canceled = feedback is not None and feedback.isCanceled()
        if int(error) != 0 or canceled:  # canceled after the last block: still canceled
            _remove(staging)
            return ExportResult(False, path, 'canceled' if canceled else f'raster writer error {int(error)}')
        manager = getattr(gdal, 'ExceptionMgr', None)
        scope = manager(useExceptions=True) if manager is not None else _NoScope()
        try:
            with scope:
                return self._finish(gdal, staging, path)
        except Exception as exc:
            _remove(staging)
            return ExportResult(False, path, str(exc))

    def _finish(self, gdal, staging: str, path: str) -> ExportResult:
        """Reproject / convert the staging file, then rename it ``path`` (temporaries removed on failure)."""
        written = [staging]
        try:
            current = staging
            if self.target_crs is not None:
                warped = os.path.join(os.path.dirname(staging), 'warped.tif')
                written.append(warped)
                if gdal.Warp(warped, current, dstSRS=self.target_crs.toWkt(), creationOptions=[f'COMPRESS={self.compress}', 'TILED=YES']) is None:
                    raise RuntimeError(gdal.GetLastErrorMsg() or 'gdal.Warp failed')
                _remove(current)
                current = warped
            if self.fmt == 'COG':
                cog = os.path.join(os.path.dirname(staging), 'output.tif')
                written.append(cog)
                if gdal.Translate(cog, current, format='COG', creationOptions=[f'COMPRESS={self.compress}']) is None:
                    raise RuntimeError(gdal.GetLastErrorMsg() or 'gdal.Translate failed')
                _remove(current)
                current = cog
            _replace_raster(current, path)
        except Exception as exc:
            for name in written:
                _remove(name)
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


def _replace_raster(written: str, path: str) -> None:
    """Rename a complete raster ``path``, with its side files.

    GDAL's Create used to remove the side files of the file it replaced: the
    statistics and overviews of a previous export must not describe the new one.
    """
    for suffix in RASTER_SIDE_FILES:
        _remove(path + suffix)
    os.replace(written, path)
    for suffix in RASTER_SIDE_FILES:
        if os.path.exists(written + suffix):
            os.replace(written + suffix, path + suffix)


def private_point_cloud(layer):
    """A point cloud layer of its own on ``layer``'s source and filter, or ``layer`` itself.

    The exporter reads the index of the layer it is given, shared (QGIS >= 3.42)
    with the canvas and with any subset string set on the main thread meanwhile:
    in QGIS 4.2 a filter changed on the displayed cloud during a background
    export reached the file (34 MB written instead of 0 point), and QGIS crashed
    in ``doExport``. A layer nothing else touches keeps the task on its own
    index. Built on the main thread, released in ``finished``.
    """
    from qgis.core import QgsPointCloudLayer
    from .point_cloud_footprint import index_ready
    try:
        options = QgsPointCloudLayer.LayerOptions()
        options.loadDefaultStyle = False
        if hasattr(options, 'skipIndexGeneration'):
            options.skipIndexGeneration = True  # an unindexed LAS is refused, never indexed twice
        own = QgsPointCloudLayer(layer.source(), layer.name(), layer.providerType(), options)
        if not own.isValid() or not index_ready(own):
            return layer
        subset = layer.subsetString()
        if subset and not own.setSubsetString(subset):
            return layer
        return own
    except Exception as exc:  # pragma: no cover - depends on the QGIS build
        logger.debug(f"[FM5] point cloud export reads the displayed layer: {exc}")
        return layer


class PointCloudExportJob:
    """Write the points of a point cloud layer that pass its current filter.

    ``QgsPointCloudLayerExporter.prepareExport`` must run on the main thread
    (constructor); :meth:`run` may be called from a task thread. The exporter
    reads a private copy of the layer (:func:`private_point_cloud`).
    """

    def __init__(self, layer, path: str, fmt: str = 'LAZ', crs=None) -> None:
        from .point_cloud_footprint import (
            exporter_unavailable_message, index_ready, point_cloud_exporter_class, qgis_reads_las,
        )
        self.layer_name = layer.name()
        self.path = path
        self.fmt = fmt.upper() if fmt else 'LAZ'
        self.exporter = None
        self.source = None
        self.error = ''
        self._temporary = None
        exporter_class = point_cloud_exporter_class()
        if exporter_class is None:
            self.error = exporter_unavailable_message()
            return
        if self.fmt not in POINT_CLOUD_FORMATS:
            self.error = f'unsupported point cloud format {self.fmt}'
            return
        if self.fmt in ('LAZ', 'LAS', 'COPC') and not qgis_reads_las():
            self.error = 'QGIS is built without PDAL: it cannot write LAS / LAZ files, export as GeoPackage or CSV'
            return
        # The exporter reads the layer index without checking it (crash on a null one).
        if layer.providerType() == 'vpc':
            self.error = 'a virtual point cloud (VPC) cannot be exported: export its tiles'
            return
        if not index_ready(layer):
            self.error = 'the point cloud has no index yet (LAS file being indexed): try again later'
            return
        _check_destination(path, export_sources((layer,)))
        os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
        self.source = private_point_cloud(layer)
        exporter = exporter_class(self.source)
        exporter.setAllAttributes()
        if crs is not None and crs.isValid():
            exporter.setCrs(crs)
        formats = exporter_class.ExportFormat
        # Written under a partial name, renamed once complete.
        self._temporary = tempfile.TemporaryDirectory(prefix='.filtermate-export-', dir=os.path.dirname(os.path.abspath(path)))
        self.target = os.path.join(self._temporary.name, 'points' + POINT_CLOUD_FORMATS[self.fmt])
        if self.fmt in ('LAZ', 'LAS', 'COPC'):
            exporter.setFormat(formats.Las)
            if self.fmt == 'COPC':
                self.target = os.path.join(self._temporary.name, 'staging.laz')
        elif self.fmt == 'GPKG':
            exporter.setFormat(formats.Gpkg)
            exporter.setLayerName(layer.name())
        else:
            exporter.setFormat(formats.Csv)
        exporter.setFileName(self.target)
        self.exporter = exporter
        try:
            exporter.prepareExport()
        except Exception:
            self.release()
            raise

    def run(self, feedback=None) -> ExportResult:
        try:
            return self._run(feedback)
        finally:
            self._cleanup_temporary()

    def _cleanup_temporary(self) -> None:
        temporary = getattr(self, '_temporary', None)
        if temporary is not None:
            try:
                temporary.cleanup()
            except OSError as exc:
                # Windows can retain a writer handle until finished() closes
                # the exporter on the main thread; release() retries there.
                logger.debug("[FM5] export temporary files still open: %s", exc)
            else:
                self._temporary = None

    def release(self) -> None:
        """Close the writer before deleting only this job's temporary files."""
        self.exporter = None
        self.source = None
        self._cleanup_temporary()

    def _run(self, feedback=None) -> ExportResult:
        path = self.path
        if self.exporter is None:
            return ExportResult(False, path, self.error or 'exporter unavailable')
        if self.fmt == 'COPC':
            from . import pdal_cli
            reason = pdal_cli.copc_unavailable_reason()
            if reason:
                return ExportResult(False, path, f'{reason}: choose LAZ to export without COPC support')
        if feedback is not None:
            try:
                self.exporter.setFeedback(feedback)
            except Exception as exc:
                logger.debug(f"[FM5] export feedback not attached: {exc}")
        self.exporter.doExport()
        if feedback is not None and feedback.isCanceled():
            _remove(self.target)
            return ExportResult(False, path, 'canceled')
        error = self.exporter.lastError()
        if error:
            _remove(self.target)
            return ExportResult(False, path, error)
        if self.fmt == 'COPC':
            from . import pdal_cli
            copc = os.path.join(os.path.dirname(self.target), 'output.copc.laz')
            ok, message = pdal_cli.run_pipeline([
                {"type": "readers.las", "filename": self.target},
                {"type": "writers.copc", "filename": copc, "forward": "all", "extra_dims": "all"},
            ], is_canceled=feedback.isCanceled if feedback is not None else None)
            _remove(self.target)
            if not ok or (feedback is not None and feedback.isCanceled()):
                _remove(copc)
                return ExportResult(False, path, 'canceled' if feedback is not None and feedback.isCanceled() else message)
            return _rename(copc, path)
        return _rename(self.target, path)


def _rename(written: str, path: str) -> ExportResult:
    """Give the complete file its name (the previous export there may be open, on Windows)."""
    try:
        os.replace(written, path)
    except OSError as exc:
        _remove(written)
        return ExportResult(False, path, str(exc))
    return ExportResult(True, path)


def export_point_cloud(layer, path: str, fmt: str = 'LAZ', crs=None, feedback=None) -> ExportResult:
    """Synchronous point cloud export (scripts); the dock uses :class:`CoverageExportTask`."""
    job = PointCloudExportJob(layer, path, fmt, crs)
    try:
        return job.run(feedback)
    finally:
        job.release()


def make_export_task(jobs, on_done=None):
    """QgsTask running export jobs in the background; ``on_done(results)`` on the main thread."""
    from qgis.core import QgsRasterBlockFeedback, QgsTask

    class CoverageExportTask(QgsTask):
        def __init__(self):
            super().__init__('FilterMate: export', QgsTask.Flag.CanCancel)
            self.jobs = list(jobs)
            self.results = []
            # Canceled with the task; QgsRasterFileWriter takes no other feedback type.
            self.feedback = QgsRasterBlockFeedback()

        def cancel(self):
            self.feedback.cancel()
            super().cancel()

        def run(self):
            for index, job in enumerate(self.jobs):
                if self.isCanceled():
                    return False
                try:
                    self.results.append(job.run(self.feedback))
                except Exception as exc:
                    self.results.append(ExportResult(False, getattr(job, 'path', ''), str(exc)))
                self.setProgress(100.0 * (index + 1) / max(1, len(self.jobs)))
            return True

        def finished(self, result):
            for job in self.jobs:
                release = getattr(job, 'release', None)
                if release is not None:
                    release()
                for name in ('exporter', 'pipe', 'source'):
                    if hasattr(job, name):
                        setattr(job, name, None)
            self.jobs = []
            if on_done is not None:
                try:
                    on_done(self.results)
                except Exception as exc:
                    logger.error(f"[FM5] export callback failed: {exc}", exc_info=True)

    return CoverageExportTask()
