# -*- coding: utf-8 -*-
"""Segmentation: the window around a click, the prompts, the polygons a filter replays."""
import importlib.util
import pathlib
import sys

import pytest

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
fk.load("adapters.qgis.python_dependencies")  # model_state() asks it; loaded here for its real QgsTask base
segmentation = fk.load("segmentation")
geometry_tools = fk.load("geometry_tools")
raster_adapter = fk.load("raster_adapter")
criteria = fk.load("core.domain.raster_filter_criteria")
RasterSelection = criteria.RasterSelection


class FakeModel:
    input_size = 8

    def __init__(self):
        self.calls = []

    def predict(self, embedding, points, labels, box):
        self.calls.append((embedding, list(points), list(labels), box))
        return np.ones((8, 8), dtype=bool), 0.9


def window():
    return segmentation.SegmentationWindow(100.0, 180.0, 10.0, 8)


class TestPlanWindow:
    RASTER = (0.0, 0.0, 10000.0, 10000.0)

    def test_native_cell_around_the_click(self):
        w = segmentation.plan_window(5000.0, 5000.0, self.RASTER, 0.25, 100.0, 1024)
        assert w.cell == 0.25
        assert w.x_min == pytest.approx(5000.0 - 128.0)
        assert w.y_max == pytest.approx(5000.0 + 128.0)

    def test_coarser_when_the_map_shows_more_than_the_native_pixels_cover(self):
        w = segmentation.plan_window(5000.0, 5000.0, self.RASTER, 0.25, 2048.0, 1024)
        assert w.cell == 2.0

    def test_a_service_has_no_native_cell(self):
        assert segmentation.plan_window(5000.0, 5000.0, self.RASTER, 0.0, 1024.0, 1024).cell == 1.0

    def test_stays_inside_the_raster_at_a_corner(self):
        w = segmentation.plan_window(1.0, 9999.0, self.RASTER, 1.0, 10.0, 1024)
        assert (w.x_min, w.y_max) == (0.0, 10000.0)

    def test_a_small_raster_sits_in_the_middle(self):
        w = segmentation.plan_window(50.0, 50.0, (0.0, 0.0, 100.0, 100.0), 1.0, 10.0, 1024)
        assert w.x_min == pytest.approx(-462.0)
        assert w.contains(50.0, 50.0)

    @pytest.mark.parametrize('visible', [0.0, float('inf'), float('nan')])
    def test_no_usable_cell_size_is_refused(self, visible):
        with pytest.raises(ValueError):
            segmentation.plan_window(1.0, 1.0, self.RASTER, 0.0, visible, 1024)


class TestSession:
    def session(self, model=None):
        return segmentation.SegmentationSession(model or FakeModel(), window(), 'embedding')

    def test_points_are_pixels_of_the_window(self):
        model = FakeModel()
        session = self.session(model)
        assert session.add_point(125.0, 150.0, True)
        assert session.add_point(145.0, 170.0, False)
        session.predict()
        assert model.calls == [('embedding', [(2.5, 3.0), (4.5, 1.0)], [1, 0], None)]

    def test_a_point_off_the_window_is_refused(self):
        session = self.session()
        assert not session.add_point(1000.0, 150.0, True)
        assert not session.has_prompts

    def test_the_box_is_ordered_and_clipped(self):
        session = self.session()
        session.set_box(150.0, 130.0, 90.0, 400.0)
        assert session.box == (0.0, 0.0, 5.0, 5.0)

    @pytest.mark.parametrize('corners', [(1000.0, 130.0, 1100.0, 150.0), (120.0, 150.0, 120.0, 170.0)])
    def test_a_box_off_the_window_or_flat_is_refused(self, corners):
        session = self.session()
        assert not session.set_box(*corners)
        assert session.box is None

    def test_clear_keeps_the_encoded_window(self):
        session = self.session()
        session.add_point(125.0, 150.0, True)
        session.predict()
        session.clear()
        assert session.embedding == 'embedding'
        assert not session.has_prompts and session.mask is None and session.geometry() is None

    def test_the_mask_is_polygonized_on_the_window(self, monkeypatch):
        seen = {}

        def fake_mask_to_geometry(mask, geotransform, crs_wkt, sieve_pixels=0, simplify_tolerance=0.0):
            seen.update(transform=geotransform, sieve=sieve_pixels, simplify=simplify_tolerance)
            return 'polygons'

        monkeypatch.setattr(geometry_tools, 'mask_to_geometry', fake_mask_to_geometry)
        session = self.session()
        session.add_point(125.0, 150.0, True)
        session.predict()
        assert session.geometry() == 'polygons'
        assert seen == {'transform': (100.0, 10.0, 0.0, 180.0, 0.0, -10.0), 'sieve': segmentation.SIEVE_PIXELS, 'simplify': 5.0}


class TestFindProvider:
    """The model is FilterMate's own: made once its files and onnxruntime are there, never before."""

    @pytest.fixture(autouse=True)
    def forget(self):
        segmentation.forget_provider()
        yield
        segmentation.forget_provider()

    def ready(self, monkeypatch, runtime=True, installed=True, directory='/profile/filter_mate/models/sam'):
        sam_model = fk.load("sam_model")
        monkeypatch.setattr(segmentation, 'model_directory', lambda: directory)
        monkeypatch.setattr(sam_model, 'runtime_available', lambda: runtime)
        monkeypatch.setattr(sam_model, 'is_installed', lambda folder: installed and folder == directory)
        return sam_model

    def test_nothing_installed(self, monkeypatch):
        self.ready(monkeypatch, runtime=False, installed=False)
        assert segmentation.find_provider() is None
        assert segmentation.model_state() == segmentation.ModelState(False, False)
        assert not segmentation.model_state().ready

    def test_the_runtime_without_the_files(self, monkeypatch):
        self.ready(monkeypatch, installed=False)
        assert segmentation.find_provider() is None
        assert segmentation.model_state() == segmentation.ModelState(True, False)

    def test_the_files_without_the_runtime(self, monkeypatch):
        self.ready(monkeypatch, runtime=False)
        assert segmentation.find_provider() is None
        assert segmentation.model_state() == segmentation.ModelState(False, True)

    def test_ready_makes_the_model_once(self, monkeypatch):
        sam_model = self.ready(monkeypatch)
        made = []
        monkeypatch.setattr(sam_model, 'SamOnnxProvider', lambda directory: made.append(directory) or object())
        first = segmentation.find_provider()
        assert first is not None and segmentation.find_provider() is first
        assert made == ['/profile/filter_mate/models/sam']
        segmentation.forget_provider()
        assert segmentation.find_provider() is not first and len(made) == 2

    def test_files_removed_after_the_model_was_made(self, monkeypatch):
        sam_model = self.ready(monkeypatch)
        monkeypatch.setattr(sam_model, 'SamOnnxProvider', lambda directory: object())
        assert segmentation.find_provider() is not None
        monkeypatch.setattr(sam_model, 'is_installed', lambda folder: False)
        assert segmentation.find_provider() is None

    def test_a_model_that_cannot_be_made_is_none(self, monkeypatch):
        sam_model = self.ready(monkeypatch)

        def fail(directory):
            raise RuntimeError('broken')

        monkeypatch.setattr(sam_model, 'SamOnnxProvider', fail)
        assert segmentation.find_provider() is None

    def test_an_unknown_profile_is_not_installed(self, monkeypatch):
        sam_model = fk.load("sam_model")
        monkeypatch.setattr(sam_model, 'runtime_available', lambda: True)
        monkeypatch.setattr(segmentation, 'model_directory', lambda: (_ for _ in ()).throw(TypeError('no profile')))
        assert segmentation.model_state() == segmentation.ModelState(True, False)


class TestModelDownloadTask:
    @pytest.fixture(autouse=True)
    def forget(self):
        segmentation.forget_provider()
        yield
        segmentation.forget_provider()

    def test_success_forgets_the_old_model_and_calls_back(self, monkeypatch, tmp_path):
        sam_model = fk.load("sam_model")
        monkeypatch.setattr(sam_model, 'download', lambda directory, is_canceled, progress, proxy: progress(100.0))
        segmentation._provider = 'old'
        results = []
        task = segmentation.ModelDownloadTask(str(tmp_path), lambda t, ok: results.append((t, ok)))
        assert task.run() is True
        task.finished(True)
        assert results == [(task, True)] and task.error == '' and segmentation.find_provider() != 'old'

    def test_a_failure_is_told(self, monkeypatch, tmp_path):
        sam_model = fk.load("sam_model")

        def fail(directory, is_canceled, progress, proxy):
            raise OSError('disk full')

        monkeypatch.setattr(sam_model, 'download', fail)
        task = segmentation.ModelDownloadTask(str(tmp_path), lambda t, ok: None)
        assert task.run() is False and task.error == 'disk full'

    def test_an_error_without_a_message_is_no_cancel(self, monkeypatch, tmp_path):
        sam_model = fk.load("sam_model")

        def fail(directory, is_canceled, progress, proxy):
            raise ValueError()

        monkeypatch.setattr(sam_model, 'download', fail)
        task = segmentation.ModelDownloadTask(str(tmp_path), lambda t, ok: None)
        assert task.run() is False and task.error == 'ValueError'

    def test_a_cancel_is_no_error(self, monkeypatch, tmp_path):
        sam_model = fk.load("sam_model")

        def cancel(directory, is_canceled, progress, proxy):
            raise sam_model.Canceled()

        monkeypatch.setattr(sam_model, 'download', cancel)
        task = segmentation.ModelDownloadTask(str(tmp_path), lambda t, ok: None)
        assert task.run() is False and task.error == ''


class TestSegmentsCriteria:
    WKT = 'POLYGON((0 0,1 0,1 1,0 0))'

    def test_round_trip_without_any_model(self):
        selection = RasterSelection(segments=[self.WKT])
        assert RasterSelection.from_dict(selection.to_dict()) == selection
        assert selection.segments == (self.WKT,)

    def test_a_selection_of_segments_is_not_empty(self):
        assert not RasterSelection(segments=[self.WKT]).is_empty
        assert RasterSelection().is_empty

    def test_older_states_have_no_segments_key(self):
        assert 'segments' not in RasterSelection().to_dict()

    def test_duplicates_are_dropped(self):
        assert RasterSelection(segments=[self.WKT, self.WKT]).segments == (self.WKT,)

    @pytest.mark.parametrize('bad', [WKT, [''], [12], 12, {WKT: 1}])
    def test_malformed_segments_are_refused(self, bad):
        with pytest.raises(ValueError):
            RasterSelection(segments=bad)

    def test_no_formula_and_no_pixel_test_for_polygons(self):
        selection = RasterSelection(segments=[self.WKT])
        with pytest.raises(ValueError):
            selection.to_calc_formula('ortho')
        with pytest.raises(ValueError):
            selection.keeps(1.0)

    def test_describe_counts_them(self):
        assert RasterSelection(segments=[self.WKT]).describe() == '1 segmented object(s)'


@pytest.mark.skipif(fk.ogr is None, reason="the geometry fakes need GDAL")
class TestSegmentsGeometry:
    SQUARE = 'POLYGON((0 0,4 0,4 4,0 4,0 0))'
    OTHER = 'POLYGON((10 10,12 10,12 12,10 12,10 10))'

    def result(self, monkeypatch, segments, width=20, height=20):
        fk.install(monkeypatch, raster_adapter, geometry_tools)
        return raster_adapter.segments_geometry(RasterSelection(segments=segments), fk.FakeRectangle(0, 0, 20, 20), width, height)

    def test_union_area_and_count(self, monkeypatch):
        result = self.result(monkeypatch, [self.SQUARE, self.OTHER])
        assert result.geometry.area() == pytest.approx(20.0)
        assert (result.objects, result.kept_pixels, result.total_pixels) == (2, 20, 400)

    def test_an_unreadable_polygon_is_skipped(self, monkeypatch):
        result = self.result(monkeypatch, [self.SQUARE, 'not a wkt'])
        assert result.objects == 1

    def test_a_service_has_no_pixel_count(self, monkeypatch):
        result = self.result(monkeypatch, [self.SQUARE], width=0, height=0)
        assert (result.kept_pixels, result.total_pixels, result.objects) == (0, 0, 1)
