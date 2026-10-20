# -*- coding: utf-8 -*-
"""Bounded exports: budgets, cancellation, worker ownership and cache lifetime."""
import concurrent.futures
import importlib.util
import pathlib
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

pytestmark = pytest.mark.unit

_spec = importlib.util.spec_from_file_location('fm_materialization_fakes', pathlib.Path(__file__).with_name('coverage_fakes.py'))
fk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fk)
materialization = fk.load('raster_materialization')
cache = fk.load('cache')
source_jobs = fk.load('source_jobs')
appliers = fk.load('target_appliers')
selection_domain = fk.load('core.domain.raster_filter_criteria')


class Rect(fk.FakeRectangle):
    def intersect(self, other):
        return Rect(max(self.x0, other.x0), max(self.y0, other.y0),
                    min(self.x1, other.x1), min(self.y1, other.y1))


def worker(function, *args, **kwargs):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(function, *args, **kwargs).result()


@pytest.fixture
def exports(monkeypatch, tmp_path):
    cache.set_cache_root(str(tmp_path / 'cache'))
    records = []
    state = SimpleNamespace(error=0, canceled=False)

    class Feedback:
        def __init__(self):
            self.progressChanged = Mock()
            self.canceled = False

        def cancel(self):
            self.canceled = True

        def isCanceled(self):
            return self.canceled

    class Writer:
        def __init__(self, path):
            self.path = path

        def setOutputFormat(self, value):
            assert value == 'GTiff'

        def setCreateOptions(self, options):
            assert 'TILED=YES' in options

        def writeRaster(self, pipe, width, height, area, crs, context, feedback):
            records.append((self.path, width, height, area))
            pathlib.Path(self.path).write_bytes(b'partial' if state.error else b'complete')
            state.canceled = state.cancel_during_write if hasattr(state, 'cancel_during_write') else False
            return state.error

    core = sys.modules['qgis.core']
    monkeypatch.setattr(core, 'QgsRectangle', Rect)
    monkeypatch.setattr(core, 'QgsRasterFileWriter', Writer)
    monkeypatch.setattr(core, 'QgsRasterBlockFeedback', Feedback)
    monkeypatch.setattr(core, 'QgsRasterPipe', lambda: SimpleNamespace(set=lambda provider: True))
    yield records, state
    cache.set_cache_root(None)


def layer(provider='wcs', source='url=https://example.invalid/wcs', width=1000, height=1000):
    obj = Mock()
    obj.id.return_value = 'raster-id'
    obj.name.return_value = 'raster'
    obj.providerType.return_value = provider
    obj.source.return_value = source
    obj.isValid.return_value = True
    obj.extent.return_value = Rect(0, 0, 100, 100)
    obj.width.return_value, obj.height.return_value = width, height
    obj.bandCount.return_value = 1
    obj.crs.return_value = fk.FakeCrs('EPSG:2154')
    return obj


@pytest.mark.parametrize('width,height,budget', [(10**9, 1, 13), (1, 10**9, 13), (900, 300, 200), (5, 5, 1)])
def test_grid_strict_budget_for_thin_extents(width, height, budget):
    x, y = materialization.bounded_grid(Rect(0, 0, 100, 100), width, height, budget)
    assert 1 <= x <= width and 1 <= y <= height
    assert x * y <= budget


def test_resolution_limits_grid_without_upsampling():
    assert materialization.bounded_grid(Rect(0, 0, 100, 50), 1000, 1000, 10000, 10) == (10, 5)
    assert materialization.bounded_grid(Rect(0, 0, 100, 50), 4, 3, 10000, 1) == (4, 3)


@pytest.mark.parametrize('area', [Rect(), Rect(0, 0, float('inf'), 1), Rect(0, 0, float('nan'), 1)])
def test_invalid_extent_refused(area):
    with pytest.raises(ValueError, match='finite'):
        materialization.bounded_grid(area, 100, 100, 100)


def test_main_thread_never_opens_provider():
    source = layer()
    with pytest.raises(RuntimeError, match='worker thread'):
        materialization.materialize_raster(source)
    source.dataProvider.assert_not_called()


@pytest.mark.parametrize('provider,source', [('wcs', 'url=service'), ('gdal', '/vsicurl/https://example.invalid/a.tif'),
                                           ('postgresraster', 'PG:dbname=sample')])
def test_raw_providers_export_bounded_intersection(exports, provider, source):
    records, _ = exports
    result = worker(materialization.materialize_raster, layer(provider, source),
                    extent=Rect(50, 50, 150, 150), max_pixels=100)
    assert records[0][1:3] == (10, 10)
    assert records[0][3].xMaximum() == 100
    assert cache.in_session(result)
    assert pathlib.Path(result).read_bytes() == b'complete'
    assert pathlib.Path(result).name not in cache.unused_entries([])
    cache.settle([result])
    assert pathlib.Path(result).name in cache.unused_entries([])


@pytest.mark.parametrize('cancel', [False, True])
def test_failure_or_cancellation_removes_partial_and_releases_cache(exports, cancel):
    records, state = exports
    state.error = 0 if cancel else 1
    state.cancel_during_write = cancel
    with pytest.raises(RuntimeError, match='canceled' if cancel else 'failed'):
        worker(materialization.materialize_raster, layer(), max_pixels=100,
               is_canceled=lambda: state.canceled)
    assert not pathlib.Path(records[0][0]).exists()
    assert not cache._in_flight


def test_empty_intersection_does_not_call_writer(exports):
    records, _ = exports
    with pytest.raises(ValueError, match='non-empty'):
        worker(materialization.materialize_raster, layer(), extent=Rect(200, 200, 210, 210), max_pixels=100)
    assert not records


def test_rendered_values_are_not_exported(exports):
    records, _ = exports
    with pytest.raises(RuntimeError, match='rendered color capture'):
        worker(materialization.materialize_raster, layer('wms', 'url=tiles'), max_pixels=100)
    assert not records


def test_capture_and_clip_share_cache_lifetime(exports):
    capture = worker(materialization.materialize_raster, layer(), max_pixels=100)
    clip = capture + '.clip.vrt'
    pathlib.Path(clip).write_text('local capture reference')
    cache.settle([capture, clip])
    assert cache.collect_garbage([clip]) == 0
    assert pathlib.Path(capture).exists()
    assert cache.collect_garbage([]) == 2


def test_rendered_source_uses_capture_and_never_swaps_layer(monkeypatch):
    fk.install(monkeypatch, source_jobs)
    source = layer('wms', 'url=wmts')
    selection = selection_domain.RasterSelection()
    job = source_jobs.RasterSourceJob(source, selection, analysis_source=('/cache/render.tif', 'gdal'))
    assert job._deferred_provider
    source.dataProvider.assert_not_called()
    capture = layer('gdal', '/cache/render.tif', 30, 20)
    capture.extent.return_value = Rect(10, 20, 40, 40)
    monkeypatch.setattr(sys.modules['qgis.core'], 'QgsRasterLayer', lambda *args: capture)
    monkeypatch.setattr(job, '_prepare_provider', Mock())
    worker(job._prepare_remote, lambda: False)
    assert job._read_source == '/cache/render.tif'
    assert (job._width, job._height) == (30, 20)
    assert job._extent.xMinimum() == 10
    assert job.before.base_provider == 'wms'
    assert job.before.base_source == 'url=wmts'
    assert not job.clips_source
    assert job.apply(source) is None
    source.setDataSource.assert_not_called()


@pytest.mark.parametrize('provider', ['wcs', 'postgresraster'])
def test_service_source_capture_keeps_original_snapshot(monkeypatch, provider):
    fk.install(monkeypatch, source_jobs, appliers)
    source = layer(provider)
    job = source_jobs.RasterSourceJob(source, selection_domain.RasterSelection())
    assert job.clips_source and not job.clip_refusal
    source.dataProvider.assert_not_called()
    captured = layer('gdal', '/cache/wcs.tif', 20, 10)
    monkeypatch.setattr(sys.modules['qgis.core'], 'QgsRasterLayer', lambda *args: captured)
    monkeypatch.setattr(materialization, 'materialize_raster', lambda *args, **kwargs: '/cache/wcs.tif')
    monkeypatch.setattr(job, '_prepare_provider', Mock())
    worker(job._prepare_remote, lambda: False)
    assert job.outputs == ['/cache/wcs.tif']
    assert job._read_provider == 'gdal'
    assert job.before.base_provider == provider
    assert job.before.base_source == source.source()


def test_rendered_target_refuses_before_pixels(monkeypatch):
    fk.install(monkeypatch, appliers)
    source = layer('wms', 'url=tiles')
    job = appliers.RasterTargetJob(source, None)
    job.compute(None, None, None, None, lambda: False)
    assert not job.outcome.success
    assert 'cannot be filter targets' in job.outcome.message
    source.dataProvider.assert_not_called()


@pytest.mark.parametrize('provider', ['wcs', 'postgresraster', 'gdal'])
def test_remote_target_warps_capture_and_records_pristine_service(monkeypatch, exports, provider):
    pytest.importorskip('osgeo.ogr')
    fk.install(monkeypatch, appliers, fk.load('geometry_tools'))
    source = layer(provider, '/vsicurl/https://example.invalid/raw.tif' if provider == 'gdal' else 'url=coverage')
    source.setDataSource.side_effect = lambda path, *args: source.source.configure_mock(return_value=path)
    job = appliers.RasterTargetJob(source, None)
    source.dataProvider.assert_not_called()
    captured = layer('gdal', 'local', 10, 10)
    opened = []

    def raster_layer(uri, name, provider_key):
        opened.append(provider_key)  # a layer computes renderer statistics: a whole-coverage read for a service
        return captured

    monkeypatch.setattr(sys.modules['qgis.core'], 'QgsRasterLayer', raster_layer)
    remote = Mock()
    remote.isValid.return_value = True
    remote.extent.return_value = Rect(0, 0, 100, 100)
    remote.xSize.return_value, remote.ySize.return_value = 10, 10
    registry = Mock()
    registry.createProvider.return_value = remote
    monkeypatch.setattr(sys.modules['qgis.core'], 'QgsProviderRegistry', SimpleNamespace(instance=lambda: registry))
    path = cache.new_path('coverage', '.tif')
    captures = []

    def materialize(base, **kwargs):
        assert base.dataProvider() is remote and base.providerType() == provider
        captures.append(kwargs)
        return path

    monkeypatch.setattr(materialization, 'materialize_raster', materialize)
    calls = []
    monkeypatch.setattr(appliers, 'gdal_warp', lambda dest, src, **opts: calls.append((dest, src, opts)))
    cross = fk.load('core.domain.cross_filter')
    kinds = fk.load('core.domain.layer_kind')
    geometry = fk.FakeGeometry.fromRect(Rect(0, 0, 50, 100))
    request = cross.CrossFilterRequest('source', kinds.LayerKind.RASTER)
    worker(job.compute, geometry, source.crs(), None, request, lambda: False)
    assert job.outcome.success, job.outcome.message
    # 2026-10-20: the capture covers the area kept (five cells of ten, one of margin), not the whole coverage.
    area = captures[0]['extent']
    assert (area.x0, area.y0, area.x1, area.y1) == pytest.approx((0, 0, 60, 100), abs=1e-4)
    assert registry.createProvider.call_args.args[:2] == (provider, source.source())
    assert opened == ['gdal']  # the local capture only, never a layer over the remote source
    assert calls[0][1] == path
    assert calls[0][0] == path + '.clip.vrt'
    assert calls[0][2]['callback']() == 1
    assert job.before.base_provider == provider
    # Apply without loading any remote provider: the registry still restores the service.
    snapshots = fk.load('snapshots')
    monkeypatch.setattr(snapshots, 'swap_source', lambda live, uri, provider: True)
    monkeypatch.setattr(snapshots, '_sync_alpha_band', lambda live: None)
    recorder = Mock()
    monkeypatch.setattr(appliers, 'registry', lambda: recorder)
    after = job.apply(source)
    assert after.original_source == job.before.base_source
    assert after.original_provider == provider
    recorder.record.assert_called_once_with(after, source)


def test_remote_source_refuses_main_thread_before_open(monkeypatch):
    fk.install(monkeypatch, source_jobs, appliers)
    source = layer('postgresraster', 'PG:dbname=sample')
    job = source_jobs.RasterSourceJob(source, selection_domain.RasterSelection())
    opener = Mock()
    monkeypatch.setattr(sys.modules['qgis.core'], 'QgsRasterLayer', opener)
    with pytest.raises(RuntimeError, match='worker thread'):
        job._prepare_remote(lambda: False)
    opener.assert_not_called()


class TestCaptureWindow:
    """2026-10-20: a remote target was captured over its whole extent (1 240 km of WCS for a 25 km zone)."""

    FULL = Rect(0, 0, 100, 100)  # a 10 x 10 grid of 10 m cells

    @staticmethod
    def _window(kept, width=10, height=10, full=None):
        area, grid = appliers._capture_window(full or TestCaptureWindow.FULL, width, height, kept)
        return (area.x0, area.y0, area.x1, area.y1), grid

    def test_native_cells_around_the_kept_area_plus_one(self, monkeypatch):
        fk.install(monkeypatch, appliers)
        monkeypatch.setattr(appliers, 'QgsRectangle', Rect)
        box, grid = self._window(fk.FakeGeometry.fromRect(Rect(23, 41, 37, 58)))
        assert grid == (4, 4)  # columns 1-4, rows 3-6 from the top
        assert box == pytest.approx((10, 30, 50, 70), abs=1e-4)

    def test_clamped_to_the_extent(self, monkeypatch):
        fk.install(monkeypatch, appliers)
        monkeypatch.setattr(appliers, 'QgsRectangle', Rect)
        box, grid = self._window(fk.FakeGeometry.fromRect(Rect(-50, 95, 5, 150)))
        assert grid == (2, 2) and box == pytest.approx((0, 80, 20, 100), abs=1e-4)

    @pytest.mark.parametrize('kept', [None, 'outside'])
    def test_nothing_kept_reads_one_cell(self, monkeypatch, kept):
        fk.install(monkeypatch, appliers)
        monkeypatch.setattr(appliers, 'QgsRectangle', Rect)
        geometry = fk.FakeGeometry.fromRect(Rect(500, 500, 510, 510)) if kept else None
        box, grid = self._window(geometry)
        assert grid == (1, 1) and box == pytest.approx((0, 90, 10, 100), abs=1e-4)

    def test_capture_keeps_the_native_cell_count(self, exports, monkeypatch):
        """materialize_raster's ceil() must not add a resampled row or column to the window."""
        monkeypatch.setattr(appliers, 'QgsRectangle', Rect)
        records, _ = exports
        source = layer(width=1234, height=987)
        full = Rect(1_000_000.0, 6_000_000.0, 1_000_000.0 + 1234 * 0.7, 6_000_000.0 + 987 * 0.7)
        source.extent.return_value = full
        kept = fk.FakeGeometry.fromRect(Rect(1_000_123.4, 6_000_100.1, 1_000_456.7, 6_000_400.2))
        area, grid = appliers._capture_window(full, 1234, 987, kept)
        worker(materialization.materialize_raster, source, extent=area, max_pixels=10**8)
        assert records[-1][1:3] == grid

    def test_parts_outside_the_extent_do_not_stretch_the_window(self, monkeypatch):
        """Review: a stored "nothing kept" polygon (outside the extent) OR-combined with a zone."""
        fk.install(monkeypatch, appliers)
        monkeypatch.setattr(appliers, 'QgsRectangle', Rect)
        kept = fk.FakeGeometry.fromWkt('MULTIPOLYGON(((-2 -2,-1 -2,-1 -1,-2 -1,-2 -2)),((63 63,67 63,67 67,63 67,63 63)))')
        box, grid = self._window(kept)
        assert grid == (3, 3) and box == pytest.approx((50, 50, 80, 80), abs=1e-4)
