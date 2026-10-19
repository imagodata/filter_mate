# -*- coding: utf-8 -*-
"""Real QGIS bounded worker export, source selection and local target masking.

Run in qgis/qgis:ltr and qgis/qgis:stable with /src mounted read-only:
    QT_QPA_PLATFORM=offscreen python3 /src/tests/qgis_headless/check_stream_d_materialization.py
No user profile is used. Set FM_STREAM_PUBLIC_WCS=1 to additionally attempt
the public MapServer WCS in a subprocess with a 50-second wall-clock limit.
Unreachable public services print a specific SKIP; local checks always run.
"""
import concurrent.futures
import importlib
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import time
import types

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('FILTERMATE_LOG_DIR', tempfile.mkdtemp(prefix='fm_materialization_logs_'))

from osgeo import gdal, osr  # noqa: E402
from qgis.core import QgsApplication, QgsRasterLayer, QgsRectangle, Qgis  # noqa: E402

repo = Path(__file__).resolve().parents[2]
# Import submodules without the plugin's GUI initialization.
package = types.ModuleType('fm_capture_smoke')
package.__path__ = [str(repo)]
sys.modules[package.__name__] = package
module = importlib.import_module('fm_capture_smoke.adapters.qgis.coverage_layers.raster_materialization')
cache = importlib.import_module('fm_capture_smoke.adapters.qgis.coverage_layers.cache')

app = QgsApplication([], False)
app.initQgis()


def run():
    with tempfile.TemporaryDirectory(prefix='fm_capture_smoke_') as folder:
        cache.set_cache_root(str(Path(folder) / 'cache'))
        original = str(Path(folder) / 'values.tif')
        ds = gdal.GetDriverByName('GTiff').Create(original, 200, 100, 2, gdal.GDT_Float32)
        crs = osr.SpatialReference()
        crs.ImportFromEPSG(2154)
        ds.SetProjection(crs.ExportToWkt())
        ds.SetGeoTransform((0, 1, 0, 100, 0, -1))
        for band in (1, 2):
            ds.GetRasterBand(band).Fill(42 * band)
            ds.GetRasterBand(band).SetNoDataValue(-9999)
        ds = None

        def capture():
            layer = QgsRasterLayer(original, 'values', 'gdal')
            assert layer.isValid()
            return module.materialize_raster(layer, extent=QgsRectangle(50, 25, 100, 75), max_pixels=100)

        started = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(capture).result()
        elapsed = time.perf_counter() - started
        ds = gdal.Open(result)
        assert (ds.RasterXSize, ds.RasterYSize, ds.RasterCount) == (10, 10, 2)
        assert ds.GetGeoTransform() == (50, 5, 0, 75, 0, -5)
        assert ds.GetRasterBand(1).ReadAsArray()[5, 5] == 42
        assert ds.GetRasterBand(2).ReadAsArray()[5, 5] == 84
        assert ds.GetRasterBand(1).GetNoDataValue() == -9999
        ds = None
        print('PASS bounded GeoTIFF: bands, values, extent, budget, NoData; {:.3f}s'.format(elapsed), flush=True)

        def select_capture():
            jobs = importlib.import_module('fm_capture_smoke.adapters.qgis.coverage_layers.source_jobs')
            domain = importlib.import_module('fm_capture_smoke.core.domain.raster_filter_criteria')
            from qgis.core import QgsCoordinateTransformContext, QgsGeometry
            targets = importlib.import_module('fm_capture_smoke.adapters.qgis.coverage_layers.target_appliers')
            cross = importlib.import_module('fm_capture_smoke.core.domain.cross_filter')
            kinds = importlib.import_module('fm_capture_smoke.core.domain.layer_kind')
            layer = QgsRasterLayer(result, 'capture', 'gdal')
            selection = domain.RasterSelection(minimum=40, maximum=44)
            source = jobs.RasterSourceJob(layer, selection, filter_source=False)
            geometry = source._raw_geometry(lambda: False)
            assert not geometry.isEmpty()
            assert abs(geometry.area() - 2500) < 1
            target = targets.RasterTargetJob(layer, None)
            request = cross.CrossFilterRequest(layer.id(), kinds.LayerKind.RASTER)
            target.compute(QgsGeometry.fromRect(QgsRectangle(50, 25, 75, 75)), layer.crs(),
                           QgsCoordinateTransformContext(), request, lambda: False)
            assert target.outcome.success, target.outcome.message
            clipped = gdal.Open(target._derived_path)
            assert clipped.GetRasterBand(1).ReadAsArray()[5, 1] == 42
            assert clipped.GetRasterBand(1).ReadAsArray()[5, 8] == -9999
            clipped = None
            source.release()
            target.release()
            cache.settle(target.outputs)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(select_capture).result()
        print('PASS captured source geometry and local cutline target', flush=True)
        layer = QgsRasterLayer(original, 'main thread guard', 'gdal')
        try:
            module.materialize_raster(layer)
        except RuntimeError as error:
            assert 'worker thread' in str(error)
        else:
            raise AssertionError('main thread export was allowed')
        layer = None
        print('PASS main thread read guard', flush=True)
        cache.settle([result])
        cache.set_cache_root(None)
        if os.environ.get('FM_STREAM_PUBLIC_WCS') == '1':
            try:
                completed = subprocess.run(
                    [sys.executable, str(Path(__file__).resolve()), '--public-wcs-worker'],
                    timeout=50, check=False,
                )
                if completed.returncode:
                    raise RuntimeError('public WCS worker failed with exit {}'.format(completed.returncode))
            except subprocess.TimeoutExpired:
                print('SKIP public WCS: exceeded 50-second wall-clock limit (worker terminated)', flush=True)
        else:
            print('SKIP public WCS: set FM_STREAM_PUBLIC_WCS=1 to attempt MapServer demo', flush=True)


def public_wcs():
    """Check the actual WCS provider, never substituting the GDAL provider."""
    from urllib.parse import urlencode
    from urllib.request import urlopen
    import xml.etree.ElementTree as ET
    from qgis.core import QgsDataSourceUri

    endpoint = 'https://demo.mapserver.org/cgi-bin/wcs'

    def metadata(request, **parameters):
        query = dict(SERVICE='WCS', VERSION='1.0.0', REQUEST=request, **parameters)
        with urlopen(endpoint + '?' + urlencode(query), timeout=10) as response:
            return ET.fromstring(response.read(1024 * 1024))

    def work():
        started = time.perf_counter()
        try:
            capabilities = metadata('GetCapabilities')
            names = [node.text.strip() for node in capabilities.findall('.//{*}CoverageOfferingBrief/{*}name')
                     if node.text]
            if not names:
                print('SKIP public WCS: GetCapabilities returned no coverage names', flush=True)
                return
            coverage = next((name for name in names if 'ndvi' in name.lower()), names[0])
            description = metadata('DescribeCoverage', COVERAGE=coverage)
            formats = [node.text.strip() for node in description.findall('.//{*}supportedFormats/{*}formats')
                       if node.text]
            raster_format = next((name for name in formats if 'tiff' in name.lower()), None)
            print('INFO public WCS: coverage={}, formats={}'.format(coverage, formats), flush=True)
        except Exception as error:
            print('SKIP public WCS: metadata unavailable: {}: {}'.format(type(error).__name__, error), flush=True)
            return
        uri = QgsDataSourceUri()
        for key, value in [('url', endpoint), ('version', '1.0.0'), ('identifier', coverage)]:
            uri.setParam(key, value)
        if raster_format:
            uri.setParam('format', raster_format)
        # Both opening the service and every pixel read stay in this worker.
        layer = QgsRasterLayer(bytes(uri.encodedUri()).decode('utf-8'), 'MapServer public WCS', 'wcs')
        if not layer.isValid():
            print('SKIP public WCS: QGIS WCS provider could not open coverage {}: {}'.format(
                coverage, layer.error().message()), flush=True)
            return
        assert layer.providerType() == 'wcs'
        full = layer.extent()
        center = full.center()
        dx, dy = full.width() * 0.005, full.height() * 0.005
        extent = QgsRectangle(center.x() - dx, center.y() - dy, center.x() + dx, center.y() + dy)
        print('INFO public WCS: native={}x{}, CRS={}, sample={}'.format(
            layer.width(), layer.height(), layer.crs().authid(), extent.toString()), flush=True)
        try:
            captured = module.materialize_raster(layer, extent=extent, max_pixels=1000)
        except Exception as error:
            # Metadata availability does not guarantee GetCoverage availability.
            print('SKIP public WCS: GetCoverage/export failed: {}: {}'.format(type(error).__name__, error), flush=True)
            return
        dataset = gdal.Open(captured)
        assert dataset is not None, 'WCS export is not a readable GeoTIFF'
        width, height, bands = dataset.RasterXSize, dataset.RasterYSize, dataset.RasterCount
        assert 0 < width * height <= 1000, (width, height)
        assert bands == layer.bandCount(), (bands, layer.bandCount())
        valid = dataset.GetRasterBand(1).GetMaskBand().ReadAsArray() != 0
        assert valid.any(), 'public WCS sample contains only NoData'
        values = dataset.GetRasterBand(1).ReadAsArray()[valid]
        print('PASS public WCS provider -> session GeoTIFF: coverage={}, grid={}x{}, bands={}, '
              'valid={}, range=[{}, {}], file_bytes={}, elapsed={:.3f}s'.format(
                  coverage, width, height, bands, int(valid.sum()), float(values.min()), float(values.max()),
                  Path(captured).stat().st_size, time.perf_counter() - started), flush=True)
        dataset = None
        # Source geometry and target clipping use the actual captured WCS values.
        jobs = importlib.import_module('fm_capture_smoke.adapters.qgis.coverage_layers.source_jobs')
        domain = importlib.import_module('fm_capture_smoke.core.domain.raster_filter_criteria')
        targets = importlib.import_module('fm_capture_smoke.adapters.qgis.coverage_layers.target_appliers')
        cross = importlib.import_module('fm_capture_smoke.core.domain.cross_filter')
        kinds = importlib.import_module('fm_capture_smoke.core.domain.layer_kind')
        from qgis.core import QgsCoordinateTransformContext, QgsGeometry
        local = QgsRasterLayer(captured, layer.name(), 'gdal')
        source = jobs.RasterSourceJob(layer, domain.RasterSelection(
            minimum=float(values.min()), maximum=float(values.max())), filter_source=False,
            analysis_source=(captured, 'gdal'))
        geometry = source._raw_geometry(lambda: False)
        assert not geometry.isEmpty(), 'WCS captured source produced no geometry'
        target = targets.RasterTargetJob(layer, None)
        # Reuse the bounded capture: do not fetch the full public coverage.
        target._analysis_source = (captured, 'gdal')
        request = cross.CrossFilterRequest(layer.id(), kinds.LayerKind.RASTER)
        target.compute(QgsGeometry.fromRect(local.extent()), local.crs(),
                       QgsCoordinateTransformContext(), request, lambda: False)
        assert target.outcome.success, target.outcome.message
        assert target.before.base_provider == 'wcs'
        clipped = gdal.Open(target._derived_path)
        assert clipped is not None and clipped.RasterXSize * clipped.RasterYSize <= 1000
        assert clipped.GetRasterBand(1).GetMaskBand().ReadAsArray().any()
        clipped = None
        print('PASS public WCS captured source geometry and WCS target local clipping (original provider preserved)',
              flush=True)
        source.release()
        target.release()
        cache.settle([captured] + target.outputs)

    with tempfile.TemporaryDirectory(prefix='fm_public_wcs_') as folder:
        cache.set_cache_root(str(Path(folder) / 'cache'))
        from qgis.PyQt.QtCore import QThread

        class PublicWorker(QThread):
            error = None

            def run(self):
                try:
                    work()
                except Exception as error:
                    self.error = error

        # WCS uses Qt network timers: use a real Qt worker, as QgsTask does.
        pending = PublicWorker()
        pending.start()
        while pending.isRunning():
            app.processEvents()
            time.sleep(0.01)
        pending.wait()
        if pending.error is not None:
            raise pending.error
        cache.set_cache_root(None)


try:
    print('QGIS ' + Qgis.QGIS_VERSION, flush=True)
    if '--public-wcs-worker' in sys.argv:
        public_wcs()
    else:
        run()
finally:
    app.exitQgis()
