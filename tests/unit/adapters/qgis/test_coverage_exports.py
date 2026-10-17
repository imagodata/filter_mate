# -*- coding: utf-8 -*-
"""FilterMate 5 raster / point cloud exports: no partial file left, cancellation, unreadable point clouds."""
import importlib.util
import os
import pathlib
import sys

import pytest

pytestmark = pytest.mark.unit


def _fakes():
    if "fm_coverage_fakes" not in sys.modules:
        spec = importlib.util.spec_from_file_location("fm_coverage_fakes", pathlib.Path(__file__).with_name("coverage_fakes.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules["fm_coverage_fakes"] = module
        spec.loader.exec_module(module)
    return sys.modules["fm_coverage_fakes"]


fk = _fakes()
exporters = fk.load("exporters")
task_module = fk.load("cross_filter_task")


def _write_tif(path, size=4):
    from osgeo import gdal
    dataset = gdal.GetDriverByName('GTiff').Create(path, size, size, 1, gdal.GDT_Float32)
    dataset.SetGeoTransform((0, 1, 0, size, 0, -1))
    dataset.GetRasterBand(1).Fill(1.0)
    dataset = None


class Writer:
    """QgsRasterFileWriter writing a real GeoTIFF; ``mode`` = ok, error (partial file), cancel."""

    mode = 'ok'

    def __init__(self, path):
        self.path = path

    def setOutputFormat(self, name):
        pass

    def setCreateOptions(self, options):
        pass

    def writeRaster(self, pipe, columns, rows, extent, crs, context, feedback=None):
        _write_tif(self.path)
        if Writer.mode == 'cancel':
            feedback.cancel()
        return 3 if Writer.mode == 'error' else 0


@pytest.fixture
def raster_job(monkeypatch, tmp_path):
    pytest.importorskip("osgeo.gdal")  # the raster exports finish with GDAL (COG, reprojection)
    fk.install(monkeypatch, exporters)
    monkeypatch.setattr(sys.modules['qgis.core'], 'QgsRasterFileWriter', Writer, raising=False)
    Writer.mode = 'ok'

    def make(name, fmt='GTiff'):
        job = exporters.RasterExportJob.__new__(exporters.RasterExportJob)
        job.layer_name, job.path, job.fmt, job.compress = 'dem', str(tmp_path / name), fmt, 'DEFLATE'
        job.layer_crs, job.target_crs, job.pipe_ok, job.pipe = None, None, True, None
        job.columns = job.rows = 4
        job.extent, job.context = None, None
        return job

    return make


class TestRasterExport:
    @pytest.mark.parametrize("fmt", ['GTiff', 'COG'])
    def test_complete_file_under_its_name_only(self, raster_job, tmp_path, fmt):
        result = raster_job('dem.tif', fmt).run(fk.FakeFeedback())
        assert result.success, result.message
        assert sorted(os.listdir(tmp_path)) == ['dem.tif']

    @pytest.mark.parametrize("fmt", ['GTiff', 'COG'])
    def test_side_files_of_a_previous_export_go(self, raster_job, tmp_path, fmt):
        """GDAL's Create removed them: statistics / overviews of the old file must not describe the new one."""
        for name in ('dem.tif', 'dem.tif.aux.xml', 'dem.tif.ovr', 'dem.tif.msk'):
            (tmp_path / name).write_bytes(b"previous export")
        result = raster_job('dem.tif', fmt).run(fk.FakeFeedback())
        assert result.success, result.message
        assert sorted(os.listdir(tmp_path)) == ['dem.tif']
        assert (tmp_path / 'dem.tif').read_bytes() != b"previous export"

    @pytest.mark.parametrize("mode, message", [('error', 'raster writer error 3'), ('cancel', 'canceled')])
    def test_failed_write_leaves_nothing(self, raster_job, tmp_path, mode, message):
        Writer.mode = mode
        result = raster_job('dem.tif').run(fk.FakeFeedback())
        assert not result.success and result.message == message
        assert os.listdir(tmp_path) == []

    def test_failed_conversion_leaves_nothing(self, raster_job, tmp_path, monkeypatch):
        from osgeo import gdal

        def translate(*args, **kwargs):
            raise RuntimeError('COG driver failed')

        monkeypatch.setattr(gdal, 'Translate', translate)
        result = raster_job('dem.tif', 'COG').run()
        assert not result.success and 'COG driver failed' in result.message
        assert os.listdir(tmp_path) == []


class FakeExporter:
    """QgsPointCloudLayerExporter writing its file on doExport."""

    made = []
    error = ''

    class ExportFormat:
        Las, Gpkg, Csv = 'las', 'gpkg', 'csv'

    def __init__(self, layer):
        FakeExporter.made.append(self)
        self.feedback = None

    def setAllAttributes(self):
        pass

    def setCrs(self, crs):
        pass

    def setFormat(self, value):
        pass

    def setLayerName(self, name):
        pass

    def setFileName(self, name):
        self.name = name

    def prepareExport(self):
        pass

    def setFeedback(self, feedback):
        self.feedback = feedback

    def doExport(self):
        with open(self.name, 'wb') as stream:
            stream.write(b'LASF')

    def lastError(self):
        return FakeExporter.error


class FakeIndex:
    def __init__(self, valid):
        self._valid = valid

    def isValid(self):
        return self._valid


class FakeCloud:
    def __init__(self, provider='copc', indexed=True):
        self._provider, self._indexed = provider, indexed

    def name(self):
        return 'cloud'

    def providerType(self):
        return self._provider

    def dataProvider(self):
        return self

    def index(self):
        return FakeIndex(self._indexed)


@pytest.fixture
def cloud_export(monkeypatch):
    monkeypatch.setattr(sys.modules['qgis.core'], 'QgsPointCloudLayerExporter', FakeExporter, raising=False)
    FakeExporter.made, FakeExporter.error = [], ''
    return FakeExporter


class TestPointCloudExport:
    @pytest.mark.parametrize("fmt, name", [('LAZ', 'cloud.laz'), ('GPKG', 'cloud.gpkg'), ('CSV', 'cloud.csv')])
    def test_complete_file_under_its_name_only(self, cloud_export, tmp_path, fmt, name):
        result = exporters.PointCloudExportJob(FakeCloud(), str(tmp_path / name), fmt).run()
        assert result.success, result.message
        assert os.listdir(tmp_path) == [name]

    def test_failed_export_leaves_nothing(self, cloud_export, tmp_path):
        cloud_export.error = 'disk full'
        result = exporters.PointCloudExportJob(FakeCloud(), str(tmp_path / 'cloud.laz')).run()
        assert not result.success and result.message == 'disk full'
        assert os.listdir(tmp_path) == []

    def test_locked_destination_leaves_nothing(self, cloud_export, tmp_path, monkeypatch):
        """Windows: the previous export is open in QGIS, the rename fails."""
        def locked(source, target):
            raise PermissionError(13, 'The process cannot access the file', target)

        monkeypatch.setattr(exporters.os, 'replace', locked)
        result = exporters.PointCloudExportJob(FakeCloud(), str(tmp_path / 'cloud.laz')).run()
        assert not result.success and 'cannot access' in result.message
        assert os.listdir(tmp_path) == []

    def test_canceled_export_leaves_nothing(self, cloud_export, tmp_path):
        feedback = fk.FakeFeedback()
        job = exporters.PointCloudExportJob(FakeCloud(), str(tmp_path / 'cloud.laz'))
        feedback.cancel()
        result = job.run(feedback)
        assert not result.success and result.message == 'canceled'
        assert cloud_export.made[0].feedback is feedback
        assert os.listdir(tmp_path) == []

    @pytest.mark.parametrize("cloud, message", [(FakeCloud('vpc'), 'virtual point cloud'),
                                                (FakeCloud('pdal', indexed=False), 'no index')])
    def test_unreadable_cloud_is_refused_before_the_exporter(self, cloud_export, tmp_path, cloud, message):
        """The exporter dereferences the layer index unchecked: QGIS crashed on a VPC."""
        result = exporters.PointCloudExportJob(cloud, str(tmp_path / 'cloud.laz')).run()
        assert not result.success and message in result.message
        assert cloud_export.made == []


class TestPointCloudExporterMissing:
    """QGIS 3.26 / 3.27 filter point clouds but have no QgsPointCloudLayerExporter (3.28)."""

    @pytest.fixture
    def no_exporter(self, monkeypatch):
        monkeypatch.delattr(sys.modules['qgis.core'], 'QgsPointCloudLayerExporter', raising=False)
        monkeypatch.setattr(type(sys.modules['qgis.core']), '__getattr__', _missing_exporter, raising=False)

    def test_export_reports_the_version_instead_of_raising(self, no_exporter, tmp_path):
        result = exporters.PointCloudExportJob(FakeCloud(), str(tmp_path / 'cloud.laz')).run()
        assert not result.success and 'QGIS 3.28' in result.message
        assert os.listdir(tmp_path) == []

    def test_exact_clip_reports_the_version(self, no_exporter):
        footprint = fk.load("point_cloud_footprint")
        assert footprint.point_cloud_exporter_class() is None
        assert 'QGIS 3.28' in footprint.exporter_unavailable_message()


def _missing_exporter(self, name):
    raise ImportError(f"cannot import name {name}")


class TestTasksCancel:
    def test_export_task_passes_its_feedback(self, monkeypatch):
        fk.install(monkeypatch, exporters)
        seen = []

        class Job:
            path = 'x'

            def run(self, feedback=None):
                seen.append(feedback)
                return exporters.ExportResult(True, 'x')

        task = exporters.make_export_task([Job()])
        assert task.run()
        assert seen == [task.feedback] and seen[0] is not None
        task.cancel()
        assert task.feedback.isCanceled() and task.isCanceled()

    def test_cross_filter_task_cancel_reaches_the_jobs(self, monkeypatch):
        fk.install(monkeypatch, task_module)
        task = task_module.CrossFilterTask('t', None, object(), [])
        task.cancel()
        assert task.feedback.isCanceled() and task.isCanceled()
