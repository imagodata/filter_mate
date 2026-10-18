# -*- coding: utf-8 -*-
"""FilterMate 5 raster targets: own pixel selection, CRS-less rasters, GEOS errors, the source clip's VRT."""
import importlib.util
import json
import pathlib
import struct
import sys

import pytest

gdal = pytest.importorskip("osgeo.gdal")

pytestmark = pytest.mark.unit


def _fakes():
    if "fm_coverage_fakes" not in sys.modules:
        spec = importlib.util.spec_from_file_location("fm_coverage_fakes", pathlib.Path(__file__).with_name("coverage_fakes.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules["fm_coverage_fakes"] = module
        spec.loader.exec_module(module)
    return sys.modules["fm_coverage_fakes"]


fk = _fakes()
appliers = fk.load("target_appliers")
geometry_tools = fk.load("geometry_tools")
source_jobs = fk.load("source_jobs")
snapshots = fk.load("snapshots")
cache = fk.load("cache")
domain = fk.load("core.domain.cross_filter")
LayerKind = fk.load("core.domain.layer_kind").LayerKind
LayerSnapshot = fk.load("core.domain.filter_state").LayerSnapshot
RasterSelection = fk.load("core.domain.raster_filter_criteria").RasterSelection


class FakeRasterLayer:
    def __init__(self, source, crs):
        self._source, self._crs = source, crs

    def id(self):
        return 'dem_id'

    def name(self):
        return 'dem'

    def crs(self):
        return self._crs

    def source(self):
        return self._source

    def providerType(self):
        return 'gdal'

    def isValid(self):
        return True

    def extent(self):
        return fk.FakeRectangle(0, 0, 10, 10)

    def width(self):
        return 10

    def height(self):
        return 10

    def bandCount(self):
        return 1

    def dataProvider(self):
        return None  # metadata read in a try: float raster, no NoData


@pytest.fixture
def engine(monkeypatch, tmp_path):
    fk.install(monkeypatch, appliers, geometry_tools, source_jobs)
    # The original raster of a derived target, opened by _base_raster_layer.
    monkeypatch.setattr(sys.modules['qgis.core'], 'QgsRasterLayer',
                        lambda source, name, provider: FakeRasterLayer(source, fk.FakeCrs('EPSG:2154')), raising=False)
    cache.set_cache_root(str(tmp_path / "cache"))
    snapshots.registry()._derived.clear()
    yield appliers
    snapshots.registry()._derived.clear()
    cache.set_cache_root(None)


@pytest.fixture
def raster_without_crs(tmp_path):
    path = str(tmp_path / "nocrs.tif")
    dataset = gdal.GetDriverByName('GTiff').Create(path, 10, 10, 1, gdal.GDT_Float32)
    dataset.SetGeoTransform((0, 1, 0, 10, 0, -1))
    dataset.GetRasterBand(1).Fill(1.0)
    dataset = None
    return path


def _request(*predicates):
    return domain.CrossFilterRequest('source', LayerKind.VECTOR, predicates=predicates or ('Intersect',))


def _east_half():
    return fk.FakeGeometry.fromRect(fk.FakeRectangle(5, 0, 10, 10))


def _warp_recorder(monkeypatch):
    calls = []
    monkeypatch.setattr(appliers, 'gdal_warp', lambda path, source, **options: calls.append(options))
    return calls


class TestOwnPixelSelection:
    """A raster filtered as a source keeps a pixel selection, not an area: it cannot be combined."""

    def _selected_layer(self):
        layer = FakeRasterLayer('dem_selection_uri', fk.FakeCrs('EPSG:2154'))
        snapshots.registry()._derived[layer.id()] = LayerSnapshot(
            layer.id(), 'raster', source=layer.source(), provider='virtualraster', derived=True,
            original_source='/data/dem.tif', original_provider='gdal',
            selection=json.dumps({'mode': 'range', 'band': 1, 'minimum': 150.0, 'maximum': 199.0}))
        return layer

    @pytest.mark.parametrize("operator", ['AND', 'OR', 'AND NOT'])
    def test_combination_is_refused(self, engine, monkeypatch, operator):
        calls = _warp_recorder(monkeypatch)
        job = engine.RasterTargetJob(self._selected_layer(), operator)
        job.compute(_east_half(), fk.FakeCrs('EPSG:2154'), None, _request(), lambda: False)
        assert not job.outcome.success and 'pixel selection' in job.outcome.message
        assert calls == []

    def test_replace_clips_the_original_raster(self, engine, monkeypatch):
        calls = _warp_recorder(monkeypatch)
        job = engine.RasterTargetJob(self._selected_layer(), None)
        job.compute(_east_half(), fk.FakeCrs('EPSG:2154'), None, _request(), lambda: False)
        assert job.outcome.success and len(calls) == 1


class TestCutlineCrs:
    def test_raster_without_crs_is_clipped(self, engine, raster_without_crs):
        """GDAL >= 3.9 rejects an empty cutlineSRS ("Invalid SRS for -cutline_srs")."""
        layer = FakeRasterLayer(raster_without_crs, fk.FakeCrs(valid=False))
        job = engine.RasterTargetJob(layer, None)
        job.compute(_east_half(), fk.FakeCrs(valid=False), None, _request(), lambda: False)
        assert job.outcome.success, job.outcome.message
        dataset = gdal.Open(job.outcome.details['vrt'])  # kept alive while its band is read
        row = struct.unpack('10f', dataset.GetRasterBand(1).ReadRaster(0, 5, 10, 1, buf_type=gdal.GDT_Float32))
        assert row == (-9999.0,) * 5 + (1.0,) * 5

    def test_cutline_crs_passed_when_known(self, engine, monkeypatch):
        calls = _warp_recorder(monkeypatch)
        crs = fk.FakeCrs('EPSG:2154')
        job = engine.RasterTargetJob(FakeRasterLayer('/data/dem.tif', crs), None)
        job.compute(_east_half(), crs, None, _request(), lambda: False)
        assert calls[0]['cutlineSRS'] == crs.toWkt()

    def test_no_cutline_crs_without_crs(self, engine, monkeypatch):
        calls = _warp_recorder(monkeypatch)
        job = engine.RasterTargetJob(FakeRasterLayer('/data/dem.tif', fk.FakeCrs(valid=False)), None)
        job.compute(_east_half(), fk.FakeCrs(valid=False), None, _request(), lambda: False)
        assert 'cutlineSRS' not in calls[0]


class FailingGeometry(fk.FakeGeometry):
    """GEOS failing (invalid input): a null geometry with an error, like QgsGeometry."""

    def difference(self, other):
        return fk.FakeGeometry(None, error='TopologyException: side location conflict')

    intersection = difference


class TestGeosErrors:
    """A failed GEOS operation is an error, not "nothing kept" (which masked the whole raster)."""

    def test_outside_with_a_failing_difference(self, engine, monkeypatch):
        calls = _warp_recorder(monkeypatch)
        monkeypatch.setattr(engine, 'QgsGeometry', FailingGeometry)
        job = engine.RasterTargetJob(FakeRasterLayer('/data/dem.tif', fk.FakeCrs('EPSG:2154')), None)
        with pytest.raises(RuntimeError, match='difference of the source geometry failed: TopologyException'):
            job.compute(_east_half(), fk.FakeCrs('EPSG:2154'), None, _request('Disjoint'), lambda: False)
        assert calls == [] and not job.outcome.success

    def test_combination_with_a_failing_intersection(self, engine, monkeypatch):
        monkeypatch.setattr(engine, 'QgsGeometry', FailingGeometry)
        with pytest.raises(RuntimeError, match='intersection'):
            engine._combine_geometry('POLYGON((0 0,1 0,1 1,0 1,0 0))', 'inside', _east_half(), None, 'AND')

    def test_empty_result_is_nothing_kept(self, engine, monkeypatch):
        """Areas that do not meet: a valid empty result, the raster keeps no pixel."""
        calls = _warp_recorder(monkeypatch)
        layer = FakeRasterLayer('/data/dem.tif', fk.FakeCrs('EPSG:2154'))
        snapshots.registry()._derived[layer.id()] = LayerSnapshot(
            layer.id(), 'raster', source=layer.source(), provider='gdal', derived=True, original_source='/data/o.tif',
            original_provider='gdal', geometry_wkt='POLYGON((0 0,1 0,1 1,0 1,0 0))', side='inside')
        job = engine.RasterTargetJob(layer, 'AND')
        job.compute(_east_half(), fk.FakeCrs('EPSG:2154'), None, _request(), lambda: False)
        assert job.outcome.success and calls
        kept = fk.FakeGeometry.fromWkt(job._geometry_wkt).boundingBox()
        assert kept.xMaximum() < 0  # the degenerate polygon outside the extent
        assert job.outcome.emptied

    def test_source_outside_the_raster_empties_it(self, engine, monkeypatch):
        _warp_recorder(monkeypatch)
        job = engine.RasterTargetJob(FakeRasterLayer('/data/dem.tif', fk.FakeCrs('EPSG:2154')), None)
        far = fk.FakeGeometry.fromRect(fk.FakeRectangle(50, 50, 60, 60))
        job.compute(far, fk.FakeCrs('EPSG:2154'), None, _request(), lambda: False)
        assert job.outcome.success and job.outcome.emptied

    def test_source_on_the_raster_does_not_empty_it(self, engine, monkeypatch):
        _warp_recorder(monkeypatch)
        job = engine.RasterTargetJob(FakeRasterLayer('/data/dem.tif', fk.FakeCrs('EPSG:2154')), None)
        job.compute(_east_half(), fk.FakeCrs('EPSG:2154'), None, _request(), lambda: False)
        assert job.outcome.success and not job.outcome.emptied


class TestCombinedAreas:
    """The kept area of an already clipped raster combined with a new one."""

    WEST = "POLYGON((0 0,5 0,5 10,0 10,0 0))"

    def _derived(self, wkt):
        layer = FakeRasterLayer('/data/dem.tif', fk.FakeCrs('EPSG:2154'))
        snapshots.registry()._derived[layer.id()] = LayerSnapshot(
            layer.id(), 'raster', source=layer.source(), provider='gdal', derived=True, original_source='/data/o.tif',
            original_provider='gdal', geometry_wkt=wkt, side='inside')
        return layer

    @pytest.mark.parametrize("operator, keeps_previous", [('AND', False), ('OR', True), ('AND NOT', True)])
    def test_outside_a_source_covering_everything(self, engine, monkeypatch, operator, keeps_previous):
        """Outside of the whole extent is nothing: AND keeps nothing, OR / AND NOT the previous area."""
        calls = _warp_recorder(monkeypatch)
        job = engine.RasterTargetJob(self._derived(self.WEST), operator)
        everything = fk.FakeGeometry.fromRect(fk.FakeRectangle(-5, -5, 15, 15))
        job.compute(everything, fk.FakeCrs('EPSG:2154'), None, _request('Disjoint'), lambda: False)
        assert job.outcome.success and calls
        kept = fk.FakeGeometry.fromWkt(job._geometry_wkt)
        if keeps_previous:
            assert kept.area() == pytest.approx(50.0)
        else:
            assert kept.boundingBox().xMaximum() < 0

    def test_touching_areas_keep_nothing(self, engine, monkeypatch):
        """AND of two areas sharing an edge is a line: nothing kept, not "the source has no area"."""
        calls = _warp_recorder(monkeypatch)
        job = engine.RasterTargetJob(self._derived(self.WEST), 'AND')
        job.compute(_east_half(), fk.FakeCrs('EPSG:2154'), None, _request(), lambda: False)
        assert job.outcome.success and calls
        assert fk.FakeGeometry.fromWkt(job._geometry_wkt).boundingBox().xMaximum() < 0

    def test_only_polygons_are_stored(self, engine, monkeypatch):
        _warp_recorder(monkeypatch)
        # previous: west half + a strip touching the new area along x = 5 (intersection: polygon + line)
        job = engine.RasterTargetJob(self._derived("MULTIPOLYGON(((0 0,5 0,5 10,0 10,0 0)),((6 0,8 0,8 2,6 2,6 0)))"), 'AND')
        job.compute(fk.FakeGeometry.fromRect(fk.FakeRectangle(5, 0, 10, 10)), fk.FakeCrs('EPSG:2154'), None,
                    _request(), lambda: False)
        assert job.outcome.success
        assert job._geometry_wkt.split(' ')[0].upper() in ('POLYGON', 'MULTIPOLYGON')
        assert fk.FakeGeometry.fromWkt(job._geometry_wkt).area() == pytest.approx(4.0)

    def test_line_source_fails_by_name(self, engine, monkeypatch):
        calls = _warp_recorder(monkeypatch)
        job = engine.RasterTargetJob(FakeRasterLayer('/data/dem.tif', fk.FakeCrs('EPSG:2154')), 'OR')
        job.compute(fk.FakeGeometry.fromWkt("LINESTRING(1 1,9 9)"), fk.FakeCrs('EPSG:2154'), None, _request(), lambda: False)
        assert not job.outcome.success and job.outcome.message == engine.NO_AREA and calls == []


class OldGeosGeometry(fk.FakeGeometry):
    """GEOS of QGIS 3.22 - 3.28: an overlay with a collection holding lines fails (null result)."""

    def _op(self, name, other):
        for geometry in (self, other):
            if geometry._g is not None and geometry.asWkt().upper().startswith('GEOMETRYCOLLECTION'):
                return fk.FakeGeometry(None, error='IllegalArgumentException: Overlay input is mixed-dimension')
        return super()._op(name, other)


class TestOldGeos:
    def test_combination_uses_the_polygons_only(self, engine, monkeypatch):
        monkeypatch.setattr(engine, 'QgsGeometry', OldGeosGeometry)
        previous = "GEOMETRYCOLLECTION(POLYGON((0 0,5 0,5 10,0 10,0 0)),LINESTRING(5 0,9 9))"
        new = OldGeosGeometry.fromWkt("GEOMETRYCOLLECTION(POLYGON((2 0,8 0,8 10,2 10,2 0)),POINT(9 9))")
        kept = engine._combine_geometry(previous, 'inside', new, None, 'AND')
        assert kept.area() == pytest.approx(30.0)


class TestSourceParts:
    def test_parts_kept_alive_with_their_engines(self, engine):
        """A QgsGeos engine points to its geometry: SourceParts keeps the geometries it was given."""
        import gc
        import weakref
        part = fk.FakeGeometry.fromRect(fk.FakeRectangle(0, 0, 5, 5))
        alive = weakref.ref(part)
        parts = geometry_tools.SourceParts([part])
        del part
        gc.collect()
        assert alive() is not None and parts.matches(fk.FakeGeometry.fromRect(fk.FakeRectangle(-1, -1, 6, 6)), ['contains'])


class TestSourceClipVrt:
    class Job:
        """RasterTargetJob stand-in for the clip of the source itself."""

        def __init__(self, success=True, message=''):
            self.outputs = ['/cache/dem_1234.vrt']
            self.outcome = domain.CrossFilterOutcome('dem_id', LayerKind.RASTER, False)
            self._success, self._message, self.computed = success, message, []

        def compute(self, geometry, crs, context, request, is_canceled):
            self.computed.append(is_canceled())
            self.outcome.success, self.outcome.message = self._success, self._message

        def apply(self, layer):
            return 'after'

    def _job(self, clip, provider='gdal'):
        job = source_jobs.RasterSourceJob.__new__(source_jobs.RasterSourceJob)
        job._computed, job._provider, job.message = True, object(), ''
        job._filter_source, job._band_count = True, 3
        job.selection = RasterSelection(band=1, minimum=1.0)
        job.raw_geometry = _east_half()
        job.before = LayerSnapshot('dem_id', 'raster', source='/data/dem.tif', provider=provider)
        job.layer_id, job.crs = 'dem_id', fk.FakeCrs('EPSG:2154')
        job._clip_job, job._clip_prepared = clip, False
        return job

    def test_clip_prepared_in_the_task_then_applied_and_settled(self, engine, monkeypatch):
        """The clip of a multiband / expression source is not a task target: its VRT is settled here."""
        settled = []
        monkeypatch.setattr(cache, 'settle', lambda paths: settled.append(list(paths)))
        clip = self.Job()
        job = self._job(clip)
        job.prepare_apply(lambda: False)  # the task, off the main thread
        assert clip.computed == [False] and job.outputs == ['/cache/dem_1234.vrt']
        assert job._apply_clip(object()) == 'after'
        assert clip.computed == [False]  # not computed again on the main thread
        assert settled == [['/cache/dem_1234.vrt']]

    def test_failed_clip_tells_why(self, engine, monkeypatch):
        monkeypatch.setattr(cache, 'settle', lambda paths: None)
        job = self._job(self.Job(success=False, message='derived VRT could not be written'))
        job.prepare_apply(lambda: False)
        assert job._apply_clip(object()) is None and job.message == 'derived VRT could not be written'

    def test_source_not_gdal_refused_before_reading(self, engine, monkeypatch):
        job = self._job(None, provider='wms')
        job._computed = False
        monkeypatch.setattr(job, '_raw_geometry', lambda is_canceled: pytest.fail("read for nothing"))
        assert job.clip_refusal and job._apply_clip(object()) is None and job.message == job.clip_refusal

    def test_canceled_selection_is_not_read(self, engine):
        job = source_jobs.RasterSourceJob.__new__(source_jobs.RasterSourceJob)
        job._provider, job.message = object(), ''
        assert job._raw_geometry(lambda: True).isEmpty() and job.message == 'canceled'
