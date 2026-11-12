# -*- coding: utf-8 -*-
"""Segmentation: the window around a click, the prompts, the polygons a filter replays."""
import importlib.util
import pathlib
import sys
import types

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


class TestPlanPrompts:
    RASTER = (0.0, 0.0, 10000.0, 10000.0)

    @staticmethod
    def box(x, y, side):
        return segmentation.Prompt(x, y, (x - side / 2, y - side / 2, x + side / 2, y + side / 2))

    def test_neighbours_of_one_size_share_a_window(self):
        prompts = [self.box(5000, 5000, 10), self.box(5040, 5030, 12), self.box(9000, 9000, 10)]
        planned = segmentation.plan_prompts(prompts, self.RASTER, 0.25, 1024)
        assert sorted(sorted(members) for _w, members in planned) == [[0, 1], [2]]
        assert all(w.cell == 0.25 for w, _m in planned)

    def test_a_large_object_gets_a_coarser_window_that_holds_its_box(self):
        prompts = [self.box(5000, 5000, 10), self.box(5000, 5000, 600)]
        planned = dict((tuple(m), w) for w, m in segmentation.plan_prompts(prompts, self.RASTER, 0.25, 1024))
        big = planned[(1,)]
        assert big.cell == 0.25 * 4  # 600 m / (2/3) = 900 m: 0.88 m per pixel, the native cell doubled twice
        x0, y0, x1, y1 = prompts[1].box
        assert big.contains(x0, y0) and big.contains(x1, y1)

    def test_every_prompt_lies_inside_its_window_with_its_box(self):
        prompts = [self.box(100 + 37 * i, 9900 - 53 * i, 5 + i) for i in range(60)]
        planned = segmentation.plan_prompts(prompts, self.RASTER, 0.25, 1024)
        assert sorted(i for _w, m in planned for i in m) == list(range(60))
        for w, members in planned:
            for i in members:
                x0, y0, x1, y1 = prompts[i].box
                assert w.contains(x0, y0) and w.contains(x1, y1)

    def test_a_point_sees_the_view_of_a_click(self):
        (w, members), = segmentation.plan_prompts([segmentation.Prompt(5000, 5000)], self.RASTER, 0.05, 1024)
        assert members == [0] and w.side >= segmentation.PROMPT_POINT_VIEW_METRES

    def test_a_service_without_cell_uses_the_finest_needed(self):
        (w, _m), = segmentation.plan_prompts([self.box(5000, 5000, 64)], self.RASTER, 0.0, 1024)
        assert w.cell == pytest.approx(64 / segmentation.PROMPT_BOX_FILL / 1024)

    def test_a_speck_on_a_service_does_not_make_a_window_of_centimetres(self):
        (w, _m), = segmentation.plan_prompts([self.box(5000, 5000, 0.01)], self.RASTER, 0.0, 1024)
        assert w.cell == pytest.approx(segmentation.PROMPT_POINT_VIEW_METRES * segmentation.SERVICE_FINEST_SHARE / 1024)

    def test_nothing_to_plan(self):
        assert segmentation.plan_prompts([], self.RASTER, 0.25, 1024) == []


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

    def test_a_runtime_cut_short_is_offered_again(self, monkeypatch):
        """2026-11-12: an install of onnxruntime cut short was found, taken as installed and never repaired."""
        self.ready(monkeypatch)
        dependencies = fk.load("adapters.qgis.python_dependencies")
        monkeypatch.setattr(dependencies, 'is_intact', lambda package: package != 'onnxruntime')
        assert segmentation.model_state() == segmentation.ModelState(False, True)
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


class TestSimilarWithSam:
    """2026-11-10: similar objects drawn by SAM, grouped into as few encoded windows as possible."""

    RASTER = (0.0, 0.0, 10000.0, 10000.0)

    def test_close_points_share_a_window(self):
        windows = segmentation.assign_windows([(5000.0, 5000.0), (5050.0, 5020.0), (5080.0, 4950.0)], self.RASTER, 0.25, 1024)
        assert len(windows) == 1 and windows[0][1] == [0, 1, 2]

    def test_a_far_point_opens_a_window_around_it(self):
        windows = segmentation.assign_windows([(5000.0, 5000.0), (8000.0, 2000.0)], self.RASTER, 0.25, 1024)
        assert [members for _window, members in windows] == [[0], [1]]
        assert windows[1][0].contains(8000.0, 2000.0)

    def test_a_point_near_the_border_of_a_window_opens_another(self):
        first = segmentation.window_at(5000.0, 5000.0, self.RASTER, 0.25, 1024)
        near_edge = first.x_min + first.side - 10.0  # inside, but within the margin of 128 pixels (32 m)
        windows = segmentation.assign_windows([(5000.0, 5000.0), (near_edge, 5000.0)], self.RASTER, 0.25, 1024)
        assert len(windows) == 2 and windows[1][0].contains(near_edge, 5000.0)

    def test_windows_stay_in_the_raster(self):
        window = segmentation.window_at(10.0, 10.0, self.RASTER, 0.25, 1024)
        assert window.x_min == 0.0 and window.y_max - window.side == 0.0

    @staticmethod
    def polygon(area, perimeter):
        return types.SimpleNamespace(area=lambda: area, length=lambda: perimeter)

    def test_the_area_must_be_within_the_ratios(self):
        reference = (100.0, 0.785)
        assert segmentation.is_similar(self.polygon(150.0, 49.0), *reference, (0.5, 2.0), False)
        assert not segmentation.is_similar(self.polygon(250.0, 63.0), *reference, (0.5, 2.0), False)
        assert not segmentation.is_similar(self.polygon(40.0, 25.0), *reference, (0.5, 2.0), False)

    def test_the_shape_when_asked(self):
        strip = self.polygon(100.0, 104.0)  # 2 x 50: compactness 0.116
        assert segmentation.is_similar(strip, 100.0, 0.785, (0.5, 2.0), False)
        assert not segmentation.is_similar(strip, 100.0, 0.785, (0.5, 2.0), True)
        assert segmentation.is_similar(self.polygon(100.0, 40.0), 100.0, 0.785, (0.5, 2.0), True)

    def test_an_invalid_geometry_is_no_overlap(self):
        def broken(*_args):
            raise ValueError('GEOS')

        geometry = types.SimpleNamespace(combine=broken, intersection=broken)
        assert segmentation.overlap(geometry, geometry) == 0.0

    def test_the_ratio_given_to_the_colour_is_wide(self):
        low, high = segmentation.CANDIDATE_RATIO
        assert low <= 0.1 and high >= 10.0 and segmentation.SIMILAR_CANDIDATES > 0


class TestWindowMapping:
    def test_to_map_inverts_to_pixel(self):
        w = window()
        column, row = w.to_pixel(123.0, 150.0)
        assert w.to_map(column, row) == pytest.approx((123.0, 150.0))


class TestWindowPlanningCost:
    """2026-11-12: the windows of the Processing algorithm were planned in a time quadratic in the points (20 000: 148 s)."""

    RASTER = (0.0, 0.0, 100000.0, 100000.0)

    @staticmethod
    def quadratic(points, raster, cell, size, margin_pixels=128):
        """The planning before the grid index, the reference of the windows and of their order."""
        margin = margin_pixels * cell
        windows = []
        for index, (x, y) in enumerate(points):
            for window, members in windows:
                if (window.x_min + margin <= x <= window.x_min + window.side - margin
                        and window.y_max - window.side + margin <= y <= window.y_max - margin):
                    members.append(index)
                    break
            else:
                window = segmentation.window_at(x, y, raster, cell, size)
                same = [m for other, m in windows if (other.x_min, other.y_max) == (window.x_min, window.y_max)]
                if same:
                    same[0].append(index)
                else:
                    windows.append((window, [index]))
        return [(w.x_min, w.y_max, members) for w, members in windows]

    @staticmethod
    def plan(points, raster, cell, size, margin_pixels=128):
        return [(w.x_min, w.y_max, members) for w, members in
                segmentation.assign_windows(points, raster, cell, size, margin_pixels)]

    @pytest.mark.parametrize('margin', [0, 128, 500])
    def test_the_same_windows_as_before(self, margin):
        import random
        rng = random.Random(7)
        points = [(rng.uniform(0, 100000.0), rng.uniform(0, 100000.0)) for _ in range(400)]
        for _ in range(20):  # clusters, and points along the edge of the raster
            cx, cy = rng.uniform(0, 100000.0), rng.uniform(0, 100000.0)
            points += [(min(max(cx + rng.gauss(0, 150.0), 0.0), 100000.0), min(max(cy + rng.gauss(0, 150.0), 0.0), 100000.0))
                       for _ in range(30)]
        points += [(99990.0 - rng.uniform(0, 300.0), rng.uniform(0, 100000.0)) for _ in range(100)]
        points += [(float(x * 64), float(y * 64)) for x in range(12) for y in range(12)]  # on the lines of the grid
        assert self.plan(points, self.RASTER, 0.25, 1024, margin) == self.quadratic(points, self.RASTER, 0.25, 1024, margin)

    def test_scattered_points_are_planned_quickly(self):
        import random
        import time
        rng = random.Random(11)
        points = [(rng.uniform(0, 100000.0), rng.uniform(0, 100000.0)) for _ in range(20000)]
        begin = time.perf_counter()
        windows = segmentation.assign_windows(points, self.RASTER, 0.25, 1024)
        assert time.perf_counter() - begin < 15.0  # 148 s before, under 1 s after
        assert sorted(index for _w, members in windows for index in members) == list(range(20000))

    def test_a_cancel_stops_the_planning(self):
        asked = []

        def canceled():
            asked.append(True)
            return len(asked) > 3

        points = [(1000.0 * i, 1000.0 * i) for i in range(1, 50)]
        windows = segmentation.assign_windows(points, self.RASTER, 0.25, 1024, is_canceled=canceled)
        assert sum(len(members) for _w, members in windows) == 3
        prompts = [segmentation.Prompt(x, y) for x, y in points]
        assert segmentation.plan_prompts(prompts, self.RASTER, 0.25, 1024, is_canceled=lambda: True) == []


class TestWindowsAtTheEdge:
    """A window kept inside the raster near its edge must serve every point there, not be encoded once per point."""

    def test_points_along_the_edge_share_the_window(self):
        windows = segmentation.assign_windows([(1450.0 + i, 700.0) for i in range(10)], (0.0, 0.0, 1500.0, 1500.0), 1.0, 1024)
        assert len(windows) == 1 and len(windows[0][1]) == 10

    def test_a_raster_smaller_than_the_window_needs_one(self):
        windows = segmentation.assign_windows([(5.0 + i, 5.0) for i in range(10)], (0.0, 0.0, 900.0, 900.0), 1.0, 1024)
        assert len(windows) == 1


class TestAppearance:
    """2026-11-10: the encoder features of SAM under an object, compared with the clicked one's (cosine)."""

    @staticmethod
    def embedding(fine=None, coarse=None):
        coarse = np.zeros((1, 4, 2, 2), dtype=np.float32) if coarse is None else coarse
        fine = np.zeros((1, 2, 4, 4), dtype=np.float32) if fine is None else fine
        return {'image_embeddings.0': fine, 'image_embeddings.1': coarse}

    def test_the_coarsest_map_under_the_mask(self):
        coarse = np.zeros((1, 4, 2, 2), dtype=np.float32)
        coarse[0, 0, 0, 0] = 3.0  # top left cell points along channel 0
        coarse[0, 1, 1, 1] = 5.0  # bottom right cell along channel 1
        mask = np.zeros((8, 8), dtype=bool)
        mask[:4, :4] = True
        vector = segmentation.pooled_features(self.embedding(coarse=coarse), mask)
        assert vector == pytest.approx([1.0, 0.0, 0.0, 0.0])

    def test_nothing_for_a_stub_or_an_empty_mask(self):
        assert segmentation.pooled_features(np.zeros((8, 8, 3)), np.ones((8, 8), dtype=bool)) is None
        assert segmentation.pooled_features(self.embedding(), np.zeros((8, 8), dtype=bool)) is None
        assert segmentation.pooled_features(self.embedding(), None) is None

    def test_a_mask_that_does_not_tile_the_map_is_none(self):
        assert segmentation.pooled_features(self.embedding(), np.ones((7, 7), dtype=bool)) is None

    def test_the_threshold_is_the_measured_one(self):
        assert segmentation.SIMILAR_APPEARANCE_MIN == 0.68

    def test_looks_alike(self):
        task = object.__new__(segmentation.SimilarObjectsTask)
        coarse = np.zeros((1, 4, 2, 2), dtype=np.float32)
        coarse[0, 0] = 1.0
        mask = np.ones((8, 8), dtype=bool)
        task.reference_features = None
        assert task._looks_alike(self.embedding(coarse=coarse), mask)
        task.reference_features = np.array([1.0, 0.0, 0.0, 0.0])
        assert task._looks_alike(self.embedding(coarse=coarse), mask)
        task.reference_features = np.array([0.0, 1.0, 0.0, 0.0])
        assert not task._looks_alike(self.embedding(coarse=coarse), mask)
        assert task._looks_alike(np.zeros((8, 8, 3)), mask)  # unknown features: kept
        # features already pooled are used as given
        assert task._looks_alike(None, None, np.array([0.0, 1.0, 0.0, 0.0]))

    def test_the_coarsest_map(self):
        coarse = np.ones((1, 4, 2, 2), dtype=np.float32)
        assert segmentation.coarse_features(self.embedding(coarse=coarse)).shape == (4, 2, 2)
        assert segmentation.coarse_features(np.zeros((8, 8, 3))) is None
        assert segmentation.coarse_features({'scores': np.zeros(3)}) is None


class TestClickWindow:
    """2026-11-11: the candidates inside the window of the click are drawn on it, as the search was measured."""

    RASTER = (0.0, 0.0, 5000.0, 5000.0)

    def click(self):
        return segmentation.SegmentationWindow(1000.0, 2024.0, 1.0, 1024)  # x 1000..2024, y 1000..2024

    def test_inside_on_the_click_first_the_others_grouped(self):
        points = [(4000.0, 4000.0), (1500.0, 1500.0), (1010.0, 1500.0), (1600.0, 1600.0)]
        planned = segmentation.plan_similar_windows(points, self.RASTER, 1.0, 1024, self.click())
        assert planned[0][0] is not None and planned[0][1:] == ([1, 3], True)
        rest = sorted(index for _window, members, on_click in planned[1:] for index in members)
        assert rest == [0, 2] and not any(on_click for _w, _m, on_click in planned[1:])  # 1010: in the margin

    def test_every_candidate_once(self):
        points = [(1000.0 + 37 * i, 1000.0 + 23 * i) for i in range(40)]
        planned = segmentation.plan_similar_windows(points, self.RASTER, 1.0, 1024, self.click())
        assert sorted(index for _window, members, _on in planned for index in members) == list(range(40))

    def test_without_the_click_or_at_another_cell_as_before(self):
        points = [(1500.0, 1500.0)]
        for click in (None, segmentation.SegmentationWindow(1000.0, 2024.0, 2.0, 1024)):
            planned = segmentation.plan_similar_windows(points, self.RASTER, 1.0, 1024, click)
            assert [on for _w, _m, on in planned] == [False]

    def test_the_edge_of_the_raster_is_no_edge_of_an_object(self):
        window = segmentation.SegmentationWindow(0.0, 1024.0, 1.0, 1024)  # on the corner of the raster
        assert segmentation.well_inside(window, 5.0, 5.0, self.RASTER)
        assert not segmentation.well_inside(window, 1015.0, 500.0, self.RASTER)


class TestFeatureCandidates:
    """2026-11-11: the places whose features look like the clicked object's, and the proposals sorted by keep / reject."""

    @staticmethod
    def coarse(*cells):
        """A 2 x 3 x 3 map: channel 0 at the given cells, channel 1 elsewhere."""
        coarse = np.zeros((2, 3, 3), dtype=np.float32)
        coarse[1] = 1.0
        for row, column, value in cells:
            coarse[:, row, column] = (value, 1.0 - value)
        return coarse

    def test_the_peaks_best_first(self):
        peaks = segmentation.similarity_peaks(self.coarse((0, 0, 1.0), (2, 2, 0.8)), np.array([1.0, 0.0]), 0.3)
        assert [(row, column) for _cosine, row, column in peaks] == [(0, 0), (2, 2)]
        assert peaks[0][0] == pytest.approx(1.0) and peaks[1][0] == pytest.approx(0.8 / np.hypot(0.8, 0.2))

    def test_a_cell_next_to_a_better_one_is_no_peak(self):
        peaks = segmentation.similarity_peaks(self.coarse((0, 0, 1.0), (0, 1, 0.9)), np.array([1.0, 0.0]), 0.3)
        assert [(row, column) for _cosine, row, column in peaks] == [(0, 0)]

    def test_under_the_minimum_no_peak(self):
        assert segmentation.similarity_peaks(self.coarse((1, 1, 0.2)), np.array([1.0, 0.0]), 0.3) == []

    def test_an_empty_cell_does_not_divide_by_zero(self):
        coarse = np.zeros((2, 2, 2), dtype=np.float32)
        assert segmentation.similarity_peaks(coarse, np.array([1.0, 0.0]), 0.3) == []

    def test_the_settings_are_the_measured_ones(self):
        assert (segmentation.SIMILAR_FEATURE_CANDIDATES, segmentation.SIMILAR_FEATURE_MIN,
                segmentation.SORT_AFTER_DECISIONS) == (10, 0.3, 3)

    def test_closer_to_the_rejected_ones(self):
        kept, rejected = [[1.0, 0.0]], [[0.0, 1.0], [0.1, 1.0]]
        assert segmentation.closer_to_rejected([0.0, 1.0], kept, rejected)
        assert not segmentation.closer_to_rejected([1.0, 0.1], kept, rejected)

    def test_without_evidence_nothing_goes(self):
        assert not segmentation.closer_to_rejected(None, [[1.0, 0.0]], [[0.0, 1.0]])
        assert not segmentation.closer_to_rejected([0.0, 1.0], [[1.0, 0.0]], [])
        assert not segmentation.closer_to_rejected([0.0, 1.0], [], [[0.0, 1.0]])

    def test_a_tie_stays(self):
        assert not segmentation.closer_to_rejected([1.0, 1.0], [[1.0, 0.0]], [[0.0, 1.0]])
