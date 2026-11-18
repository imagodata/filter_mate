# -*- coding: utf-8 -*-
"""FilterMate 5 raster / point cloud exports: no partial file left, cancellation, unreadable point clouds."""
import importlib.util
import os
import pathlib
import sys
import types

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
footprint = fk.load("point_cloud_footprint")


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


class FakeCrs:
    def __init__(self, authid='EPSG:2154'):
        self._authid = authid

    def isValid(self):
        return bool(self._authid)

    def authid(self):
        return self._authid

    def toWkt(self):
        return f'WKT[{self._authid}]'

    def isGeographic(self):
        return self._authid == 'EPSG:4326'

    def __eq__(self, other):
        return isinstance(other, FakeCrs) and other._authid == self._authid


class FakeCloud:
    def __init__(self, provider='copc', indexed=True, subset='', source='/data/cloud.copc.laz'):
        self._provider, self._indexed, self._subset, self._source = provider, indexed, subset, source

    def name(self):
        return 'cloud'

    def source(self):
        return self._source

    def crs(self):
        return FakeCrs()

    def subsetString(self):
        return self._subset

    def providerType(self):
        return self._provider

    def dataProvider(self):
        return self

    def index(self):
        return FakeIndex(self._indexed)


@pytest.fixture
def cloud_export(monkeypatch):
    monkeypatch.setattr(sys.modules['qgis.core'], 'QgsProject',
                        types.SimpleNamespace(instance=lambda: types.SimpleNamespace(mapLayers=lambda: {})), raising=False)
    monkeypatch.setattr(sys.modules['qgis.core'], 'QgsPointCloudLayerExporter', FakeExporter, raising=False)
    monkeypatch.setattr(footprint, 'qgis_reads_las', lambda: True)
    FakeExporter.made, FakeExporter.error = [], ''
    return FakeExporter


class TestPointCloudExport:
    def test_missing_copc_support_keeps_the_original_laz_and_writes_no_fallback(self, cloud_export, tmp_path, monkeypatch):
        pdal = fk.load('pdal_cli')
        monkeypatch.setattr(pdal, 'copc_unavailable_reason', lambda: 'pdal not found')
        original = tmp_path / 'cloud.laz'
        original.write_bytes(b'complete original cloud')
        cloud = FakeCloud()
        cloud.source = lambda: str(original)
        result = exporters.PointCloudExportJob(cloud, str(tmp_path / 'cloud.copc.laz'), 'COPC').run()
        assert not result.success and 'choose LAZ' in result.message
        assert original.read_bytes() == b'complete original cloud'
        assert sorted(os.listdir(tmp_path)) == ['cloud.laz']

    def test_original_source_of_a_derived_cloud_is_refused_before_export(self, cloud_export, tmp_path):
        import json
        original = tmp_path / 'cloud.laz'
        original.write_bytes(b'complete original cloud')
        cloud = FakeCloud()
        cloud.source = lambda: str(tmp_path / 'clip.copc.laz')
        cloud.customProperty = lambda key: json.dumps({'original_source': str(original)})
        with pytest.raises(ValueError, match='data source'):
            exporters.PointCloudExportJob(cloud, str(original))
        assert original.read_bytes() == b'complete original cloud' and not cloud_export.made

    def test_existing_partial_name_is_never_used_as_staging(self, cloud_export, tmp_path):
        old = tmp_path / 'cloud.partial.laz'
        old.write_bytes(b'unrelated data')
        result = exporters.PointCloudExportJob(FakeCloud(), str(tmp_path / 'cloud.laz')).run()
        assert result.success and old.read_bytes() == b'unrelated data'
        assert sorted(os.listdir(tmp_path)) == ['cloud.laz', 'cloud.partial.laz']

    def test_synchronous_helper_relays_cancel_during_export(self, cloud_export, tmp_path, monkeypatch):
        feedback = fk.FakeFeedback()
        original_write = FakeExporter.doExport

        def cancel_during_export(writer):
            original_write(writer)
            writer.feedback.cancel()
        monkeypatch.setattr(FakeExporter, 'doExport', cancel_during_export)
        result = exporters.export_point_cloud(FakeCloud(), str(tmp_path / 'cloud.laz'), feedback=feedback)
        assert not result.success and result.message == 'canceled'
        assert cloud_export.made[0].feedback is feedback and not os.listdir(tmp_path)

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

    @pytest.mark.parametrize("fmt, name, refused", [('LAZ', 'cloud.laz', True), ('COPC', 'cloud.copc.laz', True),
                                                    ('GPKG', 'cloud.gpkg', False), ('CSV', 'cloud.csv', False)])
    def test_qgis_without_pdal_writes_no_las(self, cloud_export, tmp_path, monkeypatch, fmt, name, refused):
        """2026-10-18: the exporter of a QGIS built without PDAL wrote no LAS and said nothing:
        "No such file or directory: cloud.partial.laz"."""
        monkeypatch.setattr(footprint, 'qgis_reads_las', lambda: False)
        monkeypatch.setattr(fk.load('pdal_cli'), 'copc_unavailable_reason', lambda: 'pdal not found')
        result = exporters.PointCloudExportJob(FakeCloud(), str(tmp_path / name), fmt).run()
        assert result.success is not refused
        assert ('built without PDAL' in result.message) is refused


class TestPointCloudExportByPdalTool:
    """2026-11-18: QGIS without its pdal provider (the qgis/qgis Docker images) clipped the cloud with
    the pdal tool, then refused to export the clip: the survey video zipped the DTM without the LAZ."""

    @pytest.fixture
    def pdal_tool(self, cloud_export, monkeypatch):
        pdal = fk.load('pdal_cli')
        monkeypatch.setattr(footprint, 'qgis_reads_las', lambda: False)
        monkeypatch.setattr(pdal, 'copc_unavailable_reason', lambda: '')
        runs = []

        def run_pipeline(stages, timeout=3600.0, is_canceled=None):
            runs.append(stages)
            assert timeout == float('inf')  # no time limit, canceled with the task
            with open(stages[-1]['filename'], 'wb') as stream:
                stream.write(b'LASF')
            return True, ''

        monkeypatch.setattr(pdal, 'run_pipeline', run_pipeline)
        return runs

    @pytest.mark.parametrize("fmt, name, writer", [
        ('LAZ', 'cloud.laz', {'type': 'writers.las', 'compression': 'true'}),
        ('LAS', 'cloud.las', {'type': 'writers.las', 'compression': 'false'}),
        ('COPC', 'cloud.copc.laz', {'type': 'writers.copc'}),
    ])
    def test_the_pdal_tool_writes_the_las_qgis_cannot(self, pdal_tool, tmp_path, fmt, name, writer):
        result = exporters.PointCloudExportJob(FakeCloud(), str(tmp_path / name), fmt).run()
        assert result.success, result.message
        assert os.listdir(tmp_path) == [name]
        [stages] = pdal_tool
        assert stages[0] == {'type': 'readers.copc', 'filename': '/data/cloud.copc.laz'}
        assert {key: stages[-1][key] for key in writer} == writer
        assert stages[-1]['forward'] == 'all' and stages[-1]['extra_dims'] == 'all'
        assert stages[-1]['a_srs'] == 'EPSG:2154'  # the CRS of the layer, as the exporter wrote it
        assert len(stages) == 2 and not FakeExporter.made

    @pytest.mark.parametrize("fmt", ['LAZ', 'COPC'])
    @pytest.mark.parametrize("authid, xy", [('EPSG:4326', '0.0000001'), ('EPSG:3857', '0.01')])
    def test_a_reprojection_reads_the_layer_crs_and_rescales(self, pdal_tool, tmp_path, fmt, authid, xy):
        """The forwarded scale (0.01) of metres quantized EPSG:4326 coordinates to 0.01 degree (~1 km);
        PDAL's "auto" scale gave 1 in a streamed pipeline (pdal 2.10)."""
        name = 'cloud' + exporters.POINT_CLOUD_FORMATS[fmt]
        result = exporters.PointCloudExportJob(FakeCloud(), str(tmp_path / name), fmt, FakeCrs(authid)).run()
        assert result.success, result.message
        [stages] = pdal_tool
        assert stages[1] == {'type': 'filters.reprojection', 'in_srs': 'EPSG:2154', 'out_srs': authid}
        writer = stages[-1]
        assert (writer['scale_x'], writer['scale_y'], writer['scale_z']) == (xy, xy, '0.01')
        assert all(writer[f'offset_{axis}'] == 'auto' for axis in 'xyz')
        assert 'a_srs' not in writer

    def test_the_layer_crs_is_no_reprojection(self, pdal_tool, tmp_path):
        result = exporters.PointCloudExportJob(FakeCloud(), str(tmp_path / 'cloud.laz'), 'LAZ', FakeCrs('EPSG:2154')).run()
        assert result.success, result.message
        [stages] = pdal_tool
        assert [stage['type'] for stage in stages] == ['readers.copc', 'writers.las']
        assert stages[-1]['a_srs'] == 'EPSG:2154' and 'scale_x' not in stages[-1]

    def test_a_remote_cloud_is_refused_in_one_sentence(self, pdal_tool, tmp_path):
        cloud = FakeCloud(source='https://example.org/cloud.copc.laz')
        result = exporters.PointCloudExportJob(cloud, str(tmp_path / 'cloud.laz')).run()
        assert not result.success and pdal_tool == [] and os.listdir(tmp_path) == []
        assert result.message == ('QGIS is built without PDAL and the pdal tool cannot write this file '
                                  '(it does not read a whole remote point cloud): export as GeoPackage or CSV')

    @pytest.mark.parametrize("fmt, name, refused", [('LAZ', 'cloud.laz', False), ('COPC', 'cloud.copc.laz', True)])
    def test_a_pdal_older_than_2_4_writes_las_not_copc(self, pdal_tool, tmp_path, monkeypatch, fmt, name, refused):
        pdal = fk.load('pdal_cli')
        monkeypatch.setattr(pdal, 'copc_unavailable_reason', lambda: 'pdal 2.3.0 has no writers.copc (PDAL 2.4 or later needed)')
        monkeypatch.setattr(pdal, 'is_available', lambda: True)
        cloud = FakeCloud('ept', source='/data/cloud/ept.json')
        result = exporters.PointCloudExportJob(cloud, str(tmp_path / name), fmt).run()
        assert result.success is not refused
        assert ('PDAL 2.4' in result.message) is refused

    def test_qgis_3_26_without_the_exporter_still_exports_through_pdal(self, pdal_tool, tmp_path, monkeypatch):
        monkeypatch.delattr(sys.modules['qgis.core'], 'QgsPointCloudLayerExporter', raising=False)
        assert footprint.point_cloud_exporter_class() is None
        result = exporters.PointCloudExportJob(FakeCloud(), str(tmp_path / 'cloud.laz')).run()
        assert result.success, result.message

    def test_a_filter_expression_is_still_refused(self, pdal_tool, tmp_path):
        """The pdal tool cannot apply a QGIS filter expression: all the points would be written."""
        result = exporters.PointCloudExportJob(FakeCloud(subset='"Classification" = 6'), str(tmp_path / 'cloud.laz')).run()
        assert not result.success and 'built without PDAL' in result.message and 'filter expression' in result.message
        assert pdal_tool == [] and os.listdir(tmp_path) == []

    def test_a_failed_pipeline_leaves_nothing(self, pdal_tool, tmp_path, monkeypatch):
        def failed(stages, timeout=3600.0, is_canceled=None):
            with open(stages[-1]['filename'], 'wb') as stream:
                stream.write(b'LA')
            return False, 'writers.las: disk full'

        monkeypatch.setattr(fk.load('pdal_cli'), 'run_pipeline', failed)
        result = exporters.PointCloudExportJob(FakeCloud(), str(tmp_path / 'cloud.laz')).run()
        assert not result.success and result.message == 'pdal: writers.las: disk full'
        assert os.listdir(tmp_path) == []

    def test_a_canceled_export_leaves_nothing(self, pdal_tool, tmp_path):
        feedback = fk.FakeFeedback()
        feedback.cancel()
        result = exporters.export_point_cloud(FakeCloud(), str(tmp_path / 'cloud.laz'), feedback=feedback)
        assert not result.success and result.message == 'canceled'
        assert os.listdir(tmp_path) == []


class TestPointCloudExporterMissing:
    """QGIS 3.26 / 3.27 filter point clouds but have no QgsPointCloudLayerExporter (3.28)."""

    @pytest.fixture
    def no_exporter(self, monkeypatch):
        # A qgis.core without the class: 'from qgis.core import QgsPointCloudLayerExporter' raises ImportError.
        monkeypatch.setitem(sys.modules, 'qgis.core', types.ModuleType('qgis.core'))
        monkeypatch.setattr(footprint, 'qgis_reads_las', lambda: True)

    def test_export_reports_the_version_instead_of_raising(self, no_exporter, tmp_path):
        result = exporters.PointCloudExportJob(FakeCloud(), str(tmp_path / 'cloud.laz')).run()
        assert not result.success and 'QGIS 3.28' in result.message
        assert os.listdir(tmp_path) == []

    def test_exact_clip_reports_the_version(self, no_exporter):
        assert footprint.point_cloud_exporter_class() is None
        assert 'QGIS 3.28' in footprint.exporter_unavailable_message()


class TestRasterCreationOptions:
    def test_creation_options_setter_of_qgis_3_44(self):
        """setCreateOptions is deprecated since QGIS 3.44 (a warning at each raster export)."""
        calls = []

        class NewWriter:
            def setCreationOptions(self, options):
                calls.append(('new', options))

            def setCreateOptions(self, options):
                calls.append(('old', options))

        exporters.set_creation_options(NewWriter(), ('TILED=YES',))
        assert calls == [('new', ['TILED=YES'])]

    def test_older_qgis_keeps_set_create_options(self):
        calls = []

        class OldWriter:
            def setCreateOptions(self, options):
                calls.append(options)

        exporters.set_creation_options(OldWriter(), ['TILED=YES'])
        assert calls == [['TILED=YES']]


class PrivateCloud(FakeCloud):
    """A ``QgsPointCloudLayer`` opened by the export job."""
    made = []
    valid = True
    accepts_subset = True

    class LayerOptions:
        def __init__(self):
            self.loadDefaultStyle = True

    def __init__(self, source, name, provider, options=None):
        super().__init__(provider)
        self.source_uri, self.options, self.subset = source, options, ''
        PrivateCloud.made.append(self)

    def isValid(self):
        return PrivateCloud.valid

    def setSubsetString(self, subset):
        if not PrivateCloud.accepts_subset:
            return False
        self.subset = subset
        return True


class DisplayedCloud(FakeCloud):
    def source(self):
        return '/data/tile.copc.laz'

    def subsetString(self):
        return 'Classification = 9'


@pytest.fixture
def private_cloud(monkeypatch, cloud_export):
    monkeypatch.setattr(sys.modules['qgis.core'], 'QgsPointCloudLayer', PrivateCloud, raising=False)
    PrivateCloud.made, PrivateCloud.valid, PrivateCloud.accepts_subset = [], True, True
    return PrivateCloud


class TestPointCloudPrivateLayer:
    """Since QGIS 3.42 the exporter reads the index of the layer it is given, shared with the
    canvas: a filter changed on the displayed cloud during the export reached the file (34 MB
    instead of 0 point in QGIS 4.2) and QGIS crashed in doExport."""

    def test_exporter_reads_its_own_layer_with_the_same_filter(self, private_cloud, tmp_path):
        displayed = DisplayedCloud()
        job = exporters.PointCloudExportJob(displayed, str(tmp_path / 'cloud.laz'))
        own = private_cloud.made[0]
        assert job.source is own and job.source is not displayed
        assert (own.source_uri, own.providerType(), own.subset) == ('/data/tile.copc.laz', 'copc', 'Classification = 9')
        assert own.options.loadDefaultStyle is False
        assert job.run().success

    @pytest.mark.parametrize("valid, accepts_subset", [(False, True), (True, False)])
    def test_displayed_layer_when_the_copy_is_unusable(self, private_cloud, tmp_path, valid, accepts_subset):
        private_cloud.valid, private_cloud.accepts_subset = valid, accepts_subset
        displayed = DisplayedCloud()
        job = exporters.PointCloudExportJob(displayed, str(tmp_path / 'cloud.laz'))
        assert job.source is displayed
        assert job.run().success

    def test_task_releases_the_private_layer(self, private_cloud, tmp_path, monkeypatch):
        fk.install(monkeypatch, exporters)
        job = exporters.PointCloudExportJob(DisplayedCloud(), str(tmp_path / 'cloud.laz'))
        task = exporters.make_export_task([job])
        assert task.run()
        task.finished(True)
        assert job.source is None and job.exporter is None


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
