# -*- coding: utf-8 -*-
"""FilterMate 5 point clouds: target clip edge cases, the source copy and its footprint."""
import importlib.util
import pathlib
import sys

import pytest

pytest.importorskip("osgeo.ogr")
np = pytest.importorskip("numpy")

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
footprint = fk.load("point_cloud_footprint")
pdal_cli = fk.load("pdal_cli")
snapshots = fk.load("snapshots")
cache = fk.load("cache")
domain = fk.load("core.domain.cross_filter")
LayerKind = fk.load("core.domain.layer_kind").LayerKind
LayerSnapshot = fk.load("core.domain.filter_state").LayerSnapshot

EXTENT = (0, 0, 100, 100)


class FakeIndex:
    def __init__(self, valid=True):
        self._valid = valid

    def isValid(self):
        return self._valid


class OldProvider:
    """QGIS < 3.42: index() is not in Python, hasValidIndex() is."""

    def __init__(self, valid):
        self._valid = valid

    def hasValidIndex(self):
        return self._valid


class TestIndexReady:
    @pytest.mark.parametrize("valid", [True, False])
    def test_index_not_in_python(self, valid):
        layer = type('Layer', (), {'dataProvider': lambda self: OldProvider(valid)})()
        assert footprint.index_ready(layer) is valid


class FakeCloudProvider:
    def __init__(self, points=(), index_valid=True):
        self.points = list(points)  # (x, y, classification)
        self.calls = []
        self._index = FakeIndex(index_valid)

    def index(self):
        return self._index

    def identify(self, resolution, geometry, zrange, limit):
        box = geometry.boundingBox()
        inside = [{'X': x, 'Y': y, 'Z': 0.0, 'Classification': c, 'Intensity': 1} for x, y, c in self.points
                  if box.x0 < x < box.x1 and box.y0 < y < box.y1]  # strict, like QgsGeos::contains
        self.calls.append(min(len(inside), limit))
        return inside[:limit]


class FakeCloudLayer:
    def __init__(self, source='/data/cloud.copc.laz', provider='copc', crs=None, points=(), index_valid=True,
                 subset='', valid=True):
        self._source, self._provider, self._valid = source, provider, valid
        self._crs = crs or fk.FakeCrs('EPSG:2154')
        self._subset = subset
        self.provider = FakeCloudProvider(points, index_valid)

    def id(self):
        return 'cloud_id'

    def name(self):
        return 'cloud'

    def crs(self):
        return self._crs

    def source(self):
        return self._source

    def providerType(self):
        return self._provider

    def isValid(self):
        return self._valid

    def extent(self):
        return fk.FakeRectangle(*EXTENT)

    def dataProvider(self):
        return self.provider

    def subsetString(self):
        return self._subset

    def setSubsetString(self, subset):
        self._subset = subset
        return True


@pytest.fixture
def engine(monkeypatch, tmp_path):
    fk.install(monkeypatch, appliers, geometry_tools, source_jobs, footprint)
    cache.set_cache_root(str(tmp_path / "cache"))
    snapshots.registry()._derived.clear()
    yield appliers
    snapshots.registry()._derived.clear()
    cache.set_cache_root(None)


@pytest.fixture
def pdal(monkeypatch, tmp_path):
    """PDAL path: a readable COPC base, the pipelines recorded instead of run."""
    source = tmp_path / "cloud.copc.laz"
    source.write_bytes(b"")
    pipelines = []
    monkeypatch.setattr(pdal_cli, 'copc_unavailable_reason', lambda: '')
    monkeypatch.setattr(pdal_cli, 'run_pipeline', lambda stages, **kw: (pipelines.append(stages), (True, ''))[1])
    return str(source), pipelines


@pytest.fixture
def exporter(monkeypatch):
    """No PDAL: QgsPointCloudLayerExporter (recorded)."""
    made = []

    class Exporter:
        class ExportFormat:
            Las = 'las'

        def __init__(self, layer):
            made.append(self)
            self.feedback, self.geometry, self.exported = None, None, False

        def setFormat(self, value):
            pass

        def setFileName(self, name):
            self.name = name

        def fileName(self):
            return self.name

        def setAllAttributes(self):
            pass

        def setFilterGeometry(self, geometry):
            self.geometry = geometry

        def setFeedback(self, feedback):
            self.feedback = feedback

        def doExport(self):
            self.exported = True

        def lastError(self):
            return ''

    monkeypatch.setattr(sys.modules['qgis.core'], 'QgsPointCloudLayerExporter', Exporter, raising=False)
    monkeypatch.setattr(pdal_cli, 'copc_unavailable_reason', lambda: 'pdal not found')
    monkeypatch.setattr(footprint, 'qgis_reads_las', lambda: True)
    monkeypatch.setattr(footprint, 'open_point_cloud', lambda source, name, provider: FakeCloudLayer(source, provider))
    return made


def _request(*predicates):
    return domain.CrossFilterRequest('source', LayerKind.VECTOR, predicates=predicates or ('Intersect',))


def _compute(job, wkt, *predicates, canceled=lambda: False):
    job.compute(fk.FakeGeometry.fromWkt(wkt), fk.FakeCrs('EPSG:2154'), None, _request(*predicates), canceled)
    return job


EAST = "POLYGON((50 0,100 0,100 100,50 100,50 0))"
LINE = "LINESTRING(10 10,90 90)"


class TestSourceWithoutArea:
    """Lines or points keep no point: an explicit failure, like the raster target, not an empty cloud."""

    def test_pdal_path(self, engine, pdal):
        source, pipelines = pdal
        job = _compute(engine.PointCloudTargetJob(FakeCloudLayer(source), None), LINE)
        assert not job.outcome.success and job.outcome.message == engine.NO_AREA
        assert pipelines == []

    def test_exporter_path(self, engine, exporter):
        job = _compute(engine.PointCloudTargetJob(FakeCloudLayer(), None), LINE)
        assert not job.outcome.success and job.outcome.message == engine.NO_AREA
        assert not exporter[0].exported

    def test_bbox_mode(self, engine):
        job = _compute(engine.PointCloudTargetJob(FakeCloudLayer(), None, 'bbox'), "LINESTRING(10 10,90 10)")
        assert not job.outcome.success and job.outcome.message == engine.NO_AREA

    def test_outside_a_line_keeps_everything(self, engine, pdal):
        source, pipelines = pdal
        job = _compute(engine.PointCloudTargetJob(FakeCloudLayer(source), None), LINE, 'Disjoint')
        assert job.outcome.success and 'polygon' in pipelines[0][0]


class TestNothingKept:
    """Nothing kept is stored as an area (kept on reload, read by the next AND as "nothing")."""

    def _derived(self, source, wkt):
        layer = FakeCloudLayer('/cache/cloud_1.copc.laz')
        snapshots.registry()._derived[layer.id()] = LayerSnapshot(
            layer.id(), 'point_cloud', source=layer.source(), provider='copc', derived=True,
            original_source=source, original_provider='copc', geometry_wkt=wkt, side='inside')
        return layer

    def test_and_with_a_disjoint_area(self, engine, pdal, monkeypatch):
        source, pipelines = pdal
        monkeypatch.setattr(footprint, 'open_point_cloud', lambda s, n, p: FakeCloudLayer(s, p))
        layer = self._derived(source, "POLYGON((0 0,10 0,10 10,0 10,0 0))")
        job = _compute(engine.PointCloudTargetJob(layer, 'AND'), EAST)
        assert job.outcome.success and job.outcome.emptied
        assert job._geometry_wkt and not fk.FakeGeometry.fromWkt(job._geometry_wkt).boundingBox().intersects(job._extent)
        assert pipelines[0][1] == {"type": "filters.head", "count": 0}

    def test_and_after_nothing_kept_keeps_nothing(self, engine, pdal, monkeypatch):
        source, pipelines = pdal
        monkeypatch.setattr(footprint, 'open_point_cloud', lambda s, n, p: FakeCloudLayer(s, p))
        first = _compute(engine.PointCloudTargetJob(self._derived(source, "POLYGON((0 0,10 0,10 10,0 10,0 0))"), 'AND'), EAST)
        job = _compute(engine.PointCloudTargetJob(self._derived(source, first._geometry_wkt), 'AND'), EAST)
        assert job.outcome.success and pipelines[-1][1] == {"type": "filters.head", "count": 0}

    def test_and_with_a_touching_area_keeps_nothing(self, engine, pdal, monkeypatch):
        """The intersection is a line: nothing kept, not "the source geometry has no area"."""
        source, pipelines = pdal
        monkeypatch.setattr(footprint, 'open_point_cloud', lambda s, n, p: FakeCloudLayer(s, p))
        layer = self._derived(source, "POLYGON((0 0,50 0,50 100,0 100,0 0))")
        job = _compute(engine.PointCloudTargetJob(layer, 'AND'), EAST)
        assert job.outcome.success, job.outcome.message
        assert pipelines[0][1] == {"type": "filters.head", "count": 0}

    def test_outside_everything_or_keeps_the_previous_area(self, engine, pdal, monkeypatch):
        source, pipelines = pdal
        monkeypatch.setattr(footprint, 'open_point_cloud', lambda s, n, p: FakeCloudLayer(s, p))
        layer = self._derived(source, "POLYGON((0 0,50 0,50 100,0 100,0 0))")
        job = _compute(engine.PointCloudTargetJob(layer, 'OR'), "POLYGON((-10 -10,110 -10,110 110,-10 110,-10 -10))",
                       'Disjoint')
        assert job.outcome.success, job.outcome.message
        assert 'polygon' in pipelines[0][0] and not job.outcome.emptied
        assert fk.FakeGeometry.fromWkt(job._geometry_wkt).area() == pytest.approx(5000.0)

    def test_exporter_gets_the_area_outside(self, engine, exporter):
        job = _compute(engine.PointCloudTargetJob(FakeCloudLayer(), None), "POLYGON((500 500,600 500,600 600,500 600,500 500))")
        assert job.outcome.success and job._geometry_wkt and job.outcome.emptied
        assert not exporter[0].geometry.boundingBox().intersects(job._extent)


class TestPdalClipStages:
    """2026-10-18: filters.crop after readers.copc tested every point the reader had already clipped
    (vegetation footprint, 25 M points: 285 s, 148 s with the reader alone, same points)."""

    def test_copc_is_clipped_by_its_reader_alone(self, engine, pdal):
        source, pipelines = pdal
        _compute(engine.PointCloudTargetJob(FakeCloudLayer(source), None), EAST)
        reader, writer = pipelines[0]
        assert reader['type'] == 'readers.copc' and reader['polygon'].upper().startswith(('POLYGON', 'MULTIPOLYGON'))
        assert writer['type'] == 'writers.copc'

    def test_las_is_clipped_by_filters_crop(self, engine, pdal, tmp_path):
        _, pipelines = pdal
        las = tmp_path / "cloud.laz"
        las.write_bytes(b"")
        _compute(engine.PointCloudTargetJob(FakeCloudLayer(str(las), 'pdal'), None), EAST)
        reader, crop, _ = pipelines[0]
        assert reader['type'] == 'readers.las' and 'polygon' not in reader and crop['type'] == 'filters.crop'


class TestBboxEmptied:
    """2026-10-18: the bbox clip of a cloud outside the source was reported "filtered" like any other."""

    FAR = "POLYGON((500 500,600 500,600 600,500 600,500 500))"

    def test_source_outside_the_cloud(self, engine):
        job = _compute(engine.PointCloudTargetJob(FakeCloudLayer(), None, 'bbox'), self.FAR)
        assert job.outcome.success and job.outcome.emptied

    def test_source_on_the_cloud(self, engine):
        job = _compute(engine.PointCloudTargetJob(FakeCloudLayer(), None, 'bbox'), EAST)
        assert job.outcome.success and not job.outcome.emptied

    def test_or_keeps_the_own_subset(self, engine):
        job = _compute(engine.PointCloudTargetJob(FakeCloudLayer(subset='Classification = 6'), 'OR', 'bbox'), self.FAR)
        assert job.outcome.success and not job.outcome.emptied

    def test_pdal_clip_on_the_cloud(self, engine, pdal):
        source, _ = pdal
        job = _compute(engine.PointCloudTargetJob(FakeCloudLayer(source), None), EAST)
        assert job.outcome.success and not job.outcome.emptied


class TestVirtualPointCloud:
    def test_target_refused_without_exporter(self, engine, exporter):
        job = _compute(engine.PointCloudTargetJob(FakeCloudLayer('/data/tiles.vpc', 'vpc'), None), EAST)
        assert not job.outcome.success and 'virtual point cloud' in job.outcome.message
        assert exporter == []

    def test_target_in_bbox_mode_uses_a_subset(self, engine):
        job = _compute(engine.PointCloudTargetJob(FakeCloudLayer('/data/tiles.vpc', 'vpc'), None, 'bbox'), EAST)
        assert job.outcome.success and job._expression.startswith('(X >= 50.000')

    def test_target_without_index(self, engine, exporter, monkeypatch):
        monkeypatch.setattr(footprint, 'open_point_cloud',
                            lambda source, name, provider: FakeCloudLayer(source, provider, index_valid=False))
        job = _compute(engine.PointCloudTargetJob(FakeCloudLayer('/data/cloud.las', 'pdal'), None), EAST)
        assert not job.outcome.success and 'no index' in job.outcome.message
        assert exporter == []

    def test_source_refused(self, engine):
        job = source_jobs.PointCloudSourceJob(FakeCloudLayer('/data/tiles.vpc', 'vpc'))
        assert job.compute(_request(), lambda: False).isEmpty()
        assert 'virtual point cloud' in job.message


class TestQgisWithoutPdal:
    """2026-10-18: QGIS built without PDAL wrote no LAS and opened none; the clip ran, then failed obscurely."""

    def test_clip_refused_before_the_export(self, engine, exporter, monkeypatch):
        monkeypatch.setattr(footprint, 'qgis_reads_las', lambda: False)
        job = _compute(engine.PointCloudTargetJob(FakeCloudLayer(), None), EAST)
        assert not job.outcome.success and 'built without PDAL' in job.outcome.message
        assert exporter == []

    def test_bbox_mode_still_works(self, engine, monkeypatch):
        monkeypatch.setattr(footprint, 'qgis_reads_las', lambda: False)
        job = _compute(engine.PointCloudTargetJob(FakeCloudLayer(), None, 'bbox'), EAST)
        assert job.outcome.success


class TestExporterCancel:
    def test_feedback_and_cancel(self, engine, exporter):
        job = engine.PointCloudTargetJob(FakeCloudLayer(), None)
        job.feedback = fk.FakeFeedback()
        _compute(job, EAST, canceled=lambda: exporter[0].exported)
        assert exporter[0].feedback is job.feedback
        assert not job.outcome.success and job.outcome.message == 'canceled'


class TestWriterCrs:
    @pytest.mark.parametrize("crs, expected", [
        (fk.FakeCrs('EPSG:2154'), 'EPSG:2154'),
        (fk.FakeCrs('IGNF:LAMB93'), 'IGNF:LAMB93'),
        (fk.FakeCrs('USER:100001', wkt='PROJCS["custom"]'), 'PROJCS["custom"]'),
        (fk.FakeCrs('', wkt='PROJCS["no id"]'), 'PROJCS["no id"]'),
    ])
    def test_a_srs(self, engine, pdal, crs, expected):
        source, pipelines = pdal
        job = engine.PointCloudTargetJob(FakeCloudLayer(source, crs=crs), None)
        job.compute(fk.FakeGeometry.fromWkt(EAST), crs, None, _request(), lambda: False)
        assert pipelines[0][-1]['a_srs'] == expected


class TestBboxBounds:
    def test_projected_bounds_rounded_outwards(self, engine):
        geometry = fk.FakeGeometry.fromRect(fk.FakeRectangle(1.2345, 10.0004, 2.3451, 11.9996))
        assert engine._bbox_expression(geometry, False) == \
            "(X >= 1.234 AND X <= 2.346 AND Y >= 10.000 AND Y <= 12.000)"

    def test_geographic_bounds_keep_their_precision(self, engine):
        geometry = fk.FakeGeometry.fromRect(fk.FakeRectangle(2.30004, 48.80004, 2.30046, 48.80046))
        expression = engine._bbox_expression(geometry, False, True)
        assert "X >= 2.300040000" in expression and "X <= 2.300460000" in expression


class TestSourceCopy:
    """The task reads a copy without statistics task, filtered by its own spelling of the selection."""

    @pytest.fixture
    def opened(self, monkeypatch):
        made = []

        class Layer(FakeCloudLayer):
            class LayerOptions:
                skipStatisticsCalculation = False
                skipIndexGeneration = False

            def __init__(self, source, name, provider, options=None):
                super().__init__(source, provider)
                self.options = options
                made.append(self)

        monkeypatch.setattr(sys.modules['qgis.core'], 'QgsPointCloudLayer', Layer, raising=False)
        return made

    def test_copy_without_statistics_nor_indexing(self, engine, opened):
        source_jobs.PointCloudSourceJob(FakeCloudLayer(subset='Classification = 6'))
        options = opened[0].options
        assert options.skipStatisticsCalculation is True and options.skipIndexGeneration is True

    def test_copy_subset_spelled_apart(self, engine, opened):
        job = source_jobs.PointCloudSourceJob(FakeCloudLayer(subset='Classification = 6'))
        assert job._layer is opened[0] and opened[0].subsetString() == '(Classification = 6\n)'

    def test_final_comment_stays_out_of_the_parenthesis(self, engine, opened):
        source_jobs.PointCloudSourceJob(FakeCloudLayer(subset='Classification = 6 -- buildings'))
        assert opened[0].subsetString() == '(Classification = 6 -- buildings\n)'

    def test_invalid_copy_never_reads_the_project_layer(self, engine, monkeypatch):
        monkeypatch.setattr(footprint, 'open_point_cloud', lambda s, n, p: FakeCloudLayer(s, p, valid=False))
        live = FakeCloudLayer(subset='Classification = 6')
        job = source_jobs.PointCloudSourceJob(live)
        assert job._layer is None
        assert job.compute(_request(), lambda: False).isEmpty() and 'could not be read' in job.message

    def test_points_failing_the_check_stop_the_run(self, engine, monkeypatch):
        live = FakeCloudLayer(subset='Classification = 6', points=[(10, 10, 2)])
        monkeypatch.setattr(footprint, 'open_point_cloud', lambda s, n, p: FakeCloudLayer(s, p, points=[(10, 10, 2)]))

        def check(subset):
            def raise_on_ground(points):
                if any(p['Classification'] != 6 for p in points):
                    raise RuntimeError('QGIS returned points outside the selection')
            return raise_on_ground

        monkeypatch.setattr(footprint, 'selection_check', check)
        job = source_jobs.PointCloudSourceJob(live)
        assert job.compute(_request(), lambda: False).isEmpty() and 'outside the selection' in job.message


class TestZoneOfTheSource:
    """2026-10-18: a shape drawn with the Zone tool cuts the footprint of the source (and bounds its read)."""

    def test_footprint_is_read_in_the_zone_box_and_cut_to_the_shape(self, engine, monkeypatch):
        live = FakeCloudLayer(subset='Classification = 6', points=[(10, 10, 6)])
        monkeypatch.setattr(footprint, 'open_point_cloud', lambda s, n, p: FakeCloudLayer(s, p, points=[(10, 10, 6)]))
        seen = {}

        def fake_footprint(layer, resolution, extent=None, **kwargs):
            seen['extent'] = extent
            return footprint.FootprintResult(fk.FakeGeometry.fromWkt('POLYGON((0 0, 40 0, 40 40, 0 40, 0 0))'),
                                             points_read=1, cell_size=2.0, truncated=False, coarse=False)

        monkeypatch.setattr(footprint, 'footprint_geometry', fake_footprint)
        zone = fk.FakeGeometry.fromWkt('POLYGON((0 0, 20 0, 20 20, 0 20, 0 0))')
        job = source_jobs.PointCloudSourceJob(live, zone=zone)
        geometry = job.compute(_request(), lambda: False)
        assert seen['extent'] is not None and seen['extent'].xMaximum() == 20
        assert abs(geometry.area() - 400) < 1e-6 and job.details.get('zone') is True

    def test_without_a_zone_nothing_changes(self, engine, monkeypatch):
        live = FakeCloudLayer(subset='Classification = 6', points=[(10, 10, 6)])
        monkeypatch.setattr(footprint, 'open_point_cloud', lambda s, n, p: FakeCloudLayer(s, p, points=[(10, 10, 6)]))
        seen = {}

        def fake_footprint(layer, resolution, extent=None, **kwargs):
            seen['extent'] = extent
            return footprint.FootprintResult(fk.FakeGeometry.fromWkt('POLYGON((0 0, 40 0, 40 40, 0 40, 0 0))'),
                                             points_read=1, cell_size=2.0, truncated=False, coarse=False)

        monkeypatch.setattr(footprint, 'footprint_geometry', fake_footprint)
        job = source_jobs.PointCloudSourceJob(live)
        geometry = job.compute(_request(), lambda: False)
        assert seen['extent'] is None and abs(geometry.area() - 1600) < 1e-6 and 'zone' not in job.details


def _points(n, x0, y0, x1, y1, seed=1):
    rng = np.random.default_rng(seed)
    return [(float(x), float(y), 6) for x, y in zip(rng.uniform(x0, x1, n), rng.uniform(y0, y1, n))]


class TestFootprint:
    @pytest.fixture
    def grids(self, monkeypatch):
        shapes = []

        def mask_to_geometry(grid, geotransform, crs_wkt, sieve_pixels=0, simplify_tolerance=0.0):
            shapes.append((grid.shape, geotransform, int(grid.sum())))
            return fk.FakeGeometry.fromWkt("POINT(0 0)")

        monkeypatch.setattr(geometry_tools, 'mask_to_geometry', mask_to_geometry)
        return shapes

    def test_grid_covers_the_points_read(self, engine, grids):
        """A selection in a corner of a 10 km cloud: a small grid, not 5000 x 5000 cells."""
        layer = FakeCloudLayer(points=_points(50, 10, 10, 20, 20))
        layer.extent = lambda: fk.FakeRectangle(0, 0, 10000, 10000)
        result = footprint.footprint_geometry(layer, 2.0)
        (rows, cols), transform, occupied = grids[0]
        assert rows <= 12 and cols <= 12 and occupied > 0
        assert result.points_read == 50 and not result.truncated
        assert transform[0] <= 10 and transform[3] >= 20

    @pytest.mark.parametrize("box", [(1, 1, 99, 99), (1, 40, 99, 42)], ids=["square", "elongated"])
    def test_grid_size_is_capped(self, engine, grids, monkeypatch, box):
        monkeypatch.setattr(footprint, 'MAX_GRID_CELLS', 400)
        result = footprint.footprint_geometry(FakeCloudLayer(points=_points(200, *box)), 0.5)
        (rows, cols), _, _ = grids[0]
        assert rows * cols <= 400 and result.cell_size > 0.5 and result.coarse

    def test_coarse_footprint_is_flagged_in_the_details(self, engine, monkeypatch):
        monkeypatch.setattr(footprint, 'open_point_cloud', lambda s, n, p: FakeCloudLayer(s, p))
        monkeypatch.setattr(footprint, 'footprint_geometry',
                            lambda *a, **k: footprint.FootprintResult(fk.FakeGeometry.fromWkt(EAST), 10, 25.0, coarse=True))
        job = source_jobs.PointCloudSourceJob(FakeCloudLayer())
        job.compute(_request(), lambda: False)
        assert job.details['coarse'] is True and job.details['cell_size'] == 25.0

    @pytest.mark.parametrize("crs, expected", [(fk.FakeCrs('EPSG:2154'), 2.0),
                                               (fk.FakeCrs('EPSG:4326', geographic=True), 2.0 / 111320.0)])
    def test_resolution_in_metres_whatever_the_crs(self, engine, monkeypatch, crs, expected):
        """2026-10-18: a cloud in EPSG:4326 was read at 2 degrees (3 points, every target feature kept)."""
        monkeypatch.setattr(footprint, 'open_point_cloud', lambda s, n, p: FakeCloudLayer(s, p, crs=crs))
        asked = []
        monkeypatch.setattr(footprint, 'footprint_geometry', lambda layer, resolution, **k: asked.append(resolution)
                            or footprint.FootprintResult(fk.FakeGeometry.fromWkt(EAST), 10, resolution))
        job = source_jobs.PointCloudSourceJob(FakeCloudLayer(crs=crs), 2.0)
        job.compute(_request(), lambda: False)
        assert asked == [pytest.approx(expected)]

    def test_read_in_tiles_of_a_bounded_size(self, engine, grids, monkeypatch):
        monkeypatch.setattr(footprint, 'POINTS_PER_CALL', 50)
        monkeypatch.setattr(footprint, 'MIN_TILE_CELLS', 1)
        layer = FakeCloudLayer(points=_points(300, 1, 1, 99, 99))
        result = footprint.footprint_geometry(layer, 1.0)
        assert max(layer.provider.calls) <= 50 and result.points_read == 300 and not result.truncated

    def test_corridor_is_cut_along_its_length(self, engine, grids, monkeypatch):
        """A saturated strip narrower than two minimum tiles is split along its long side, not truncated."""
        monkeypatch.setattr(footprint, 'POINTS_PER_CALL', 50)
        layer = FakeCloudLayer(points=_points(300, 1, 1, 1999, 29))
        layer.extent = lambda: fk.FakeRectangle(0, 0, 2000, 30)
        result = footprint.footprint_geometry(layer, 1.0)
        assert result.points_read == 300 and not result.truncated
        assert max(layer.provider.calls) <= 50

    def test_points_limit_is_reported(self, engine, grids):
        result = footprint.footprint_geometry(FakeCloudLayer(points=_points(300, 1, 1, 99, 99)), 1.0, points_limit=100)
        assert result.truncated and result.points_read <= 100

    def test_cancel_stops_reading(self, engine, grids, monkeypatch):
        monkeypatch.setattr(footprint, 'POINTS_PER_CALL', 50)
        monkeypatch.setattr(footprint, 'MIN_TILE_CELLS', 1)
        layer = FakeCloudLayer(points=_points(300, 1, 1, 99, 99))
        footprint.footprint_geometry(layer, 1.0, is_canceled=lambda: len(layer.provider.calls) >= 2)
        assert len(layer.provider.calls) == 2

    def test_every_read_is_checked(self, engine, grids):
        seen = []
        footprint.footprint_geometry(FakeCloudLayer(points=_points(30, 1, 1, 99, 99)), 1.0, check=seen.append)
        assert len(seen) == 1 and len(seen[0]) == 30

    def test_points_on_the_layer_edge_are_read(self, engine, grids):
        result = footprint.footprint_geometry(FakeCloudLayer(points=[(100.0, 50.0, 6), (0.0, 0.0, 6)]), 2.0)
        assert result.points_read == 2

    def test_truncated_footprint_is_flagged_in_the_details(self, engine, monkeypatch):
        monkeypatch.setattr(footprint, 'open_point_cloud', lambda s, n, p: FakeCloudLayer(s, p))
        monkeypatch.setattr(footprint, 'footprint_geometry',
                            lambda *a, **k: footprint.FootprintResult(fk.FakeGeometry.fromWkt(EAST), 10, 2.0, True))
        job = source_jobs.PointCloudSourceJob(FakeCloudLayer())
        job.compute(_request(), lambda: False)
        assert job.details['truncated'] is True and job.details['points_read'] == 10


class TestSelectionCheck:
    """The guard on the points identify() returns, with a QgsExpression stand-in."""

    @pytest.fixture
    def expressions(self, monkeypatch):
        core = sys.modules['qgis.core']

        class Fields(list):
            pass

        class Feature:
            def __init__(self, fields):
                self.fields, self.values = fields, []

            def setAttributes(self, values):
                self.values = values

        class Context:
            def setFields(self, fields):
                self.fields = fields

            def setFeature(self, feature):
                self.feature = feature

        class Expression:
            """``<attribute> = <number>`` only; a text or NULL compared with a number is false (no error), like QGIS."""

            def __init__(self, text):
                self.name, self.value = (part.strip(' ()\n') for part in text.split('='))

            def hasParserError(self):
                return False

            def prepare(self, context):
                pass

            def referencedColumns(self):
                return {self.name}

            def evaluate(self, context):
                feature = context.feature
                value = feature.values[feature.fields.index(self.name)]
                return isinstance(value, (int, float)) and value == float(self.value)

            def hasEvalError(self):
                return False

        for name, value in (('QgsExpression', Expression), ('QgsExpressionContext', Context), ('QgsFeature', Feature),
                            ('QgsField', lambda name: name), ('QgsFields', Fields)):
            monkeypatch.setattr(core, name, value, raising=False)

    def test_points_outside_the_selection_raise(self, engine, expressions):
        check = footprint.selection_check('(Classification = 6)')
        with pytest.raises(RuntimeError, match='outside the selection'):
            check([{'X': 1.0, 'Y': 1.0, 'Classification': 6}, {'X': 2.0, 'Y': 2.0, 'Classification': 2}])

    def test_selected_points_pass(self, engine, expressions):
        footprint.selection_check('(Classification = 6)')([{'X': 1.0, 'Y': 1.0, 'Classification': 6}] * 500)

    def test_gps_time_text_is_read_as_its_number(self, engine, expressions):
        """QGIS >= 3.42 identify(): GpsTime is a date text for COPC, the number is under 'GpsTime (raw)'."""
        point = {'X': 1.0, 'Y': 1.0, 'GpsTime': '2021-03-04T10:00:00Z', 'GpsTime (raw)': 330000000.5}
        footprint.selection_check('(GpsTime = 330000000.5\n)')([point] * 10)
        with pytest.raises(RuntimeError, match='outside the selection'):
            footprint.selection_check('(GpsTime = 1.0\n)')([point])

    def test_a_text_or_null_the_expression_reads_turns_the_check_off(self, engine, expressions):
        check = footprint.selection_check('(Intensity = 5\n)')
        check([{'X': 1.0, 'Y': 1.0, 'Intensity': None}])
        check([{'X': 1.0, 'Y': 1.0, 'Intensity': 2}])  # off for the run: no reliable check

    def test_other_texts_do_not_matter(self, engine, expressions):
        """A text attribute the expression does not read leaves the check on."""
        check = footprint.selection_check('(Classification = 6\n)')
        with pytest.raises(RuntimeError, match='outside the selection'):
            check([{'X': 1.0, 'Classification': 2, 'GpsTime': 'Thu 12:34:56'}])

    def test_nothing_to_check_without_subset(self, engine):
        assert footprint.selection_check('') is None
