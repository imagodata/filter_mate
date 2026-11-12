# -*- coding: utf-8 -*-
"""SegmentationController: the model FilterMate downloads on request, and what it tells the panel meanwhile.

The controller is loaded by path under a private synthetic package where the adapters
(``segmentation``, ``sam_model``) are stubs; the tool on the map is covered by
``tests/qgis_headless/check_segmentation.py``.
"""
import importlib.util
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_seg_ctrl_test"


class ModelState:
    def __init__(self, runtime, installed, installing_runtime=False, runtime_failed=False):
        self.runtime, self.installed, self.installing_runtime, self.runtime_failed = runtime, installed, installing_runtime, runtime_failed

    @property
    def ready(self):
        return self.runtime and self.installed


class FakeDownloadTask:
    """ModelDownloadTask: records the callback, lets the tests drive progress and the end."""

    made = []

    def __init__(self, directory, callback):
        self.directory, self.callback, self.error = directory, callback, ''
        self.progress_slots = []
        self.progressChanged = types.SimpleNamespace(connect=self.progress_slots.append)
        FakeDownloadTask.made.append(self)

    def finish(self, success, error=''):
        self.error = error
        self.callback(self, success)


class Host:
    def __init__(self):
        self._raster_panel = object()
        self._torn_down = False
        self.calls = []

    def _call(self, target, method, *args):
        self.calls.append((method,) + args)

    def _iface(self):
        return None


@pytest.fixture
def ctrl_module(monkeypatch):
    for name in ("", ".ui", ".ui.controllers", ".adapters", ".adapters.qgis", ".adapters.qgis.coverage_layers"):
        module = types.ModuleType(_PKG + name)
        module.__path__ = []
        monkeypatch.setitem(sys.modules, _PKG + name, module)
    segmentation = types.ModuleType(f"{_PKG}.adapters.qgis.coverage_layers.segmentation")
    segmentation.state = ModelState(True, True)
    segmentation.model_state = lambda: segmentation.state
    segmentation.model_directory = lambda: "/profile/filtermate/models/sam"
    segmentation.ModelDownloadTask = FakeDownloadTask
    monkeypatch.setitem(sys.modules, segmentation.__name__, segmentation)
    dependencies = types.ModuleType(f"{_PKG}.adapters.qgis.python_dependencies")
    dependencies.manual_command = lambda: "python -m pip install --upgrade --target /profile/py312 onnxruntime"
    monkeypatch.setitem(sys.modules, dependencies.__name__, dependencies)
    added = []
    core = sys.modules["qgis.core"]
    monkeypatch.setattr(core, "QgsApplication", types.SimpleNamespace(
        taskManager=lambda: types.SimpleNamespace(addTask=added.append)), raising=False)
    FakeDownloadTask.made = []
    spec = importlib.util.spec_from_file_location(f"{_PKG}.ui.controllers.segmentation_controller",
                                                  _ROOT / "ui/controllers/segmentation_controller.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    module._segmentation_stub, module._added_tasks = segmentation, added
    return module


@pytest.fixture
def controller(ctrl_module):
    controller = ctrl_module.SegmentationController(Host())
    controller.tr = lambda text: text
    return controller


class TestMissingModel:
    def test_after_a_failed_install_the_command_is_told(self, ctrl_module, controller):
        ctrl_module._segmentation_stub.state = ModelState(False, False, False, True)
        assert "pip install --upgrade --target /profile/py312 onnxruntime" in controller._missing_model_text()

    def test_before_any_install_the_button_is_told(self, ctrl_module, controller):
        ctrl_module._segmentation_stub.state = ModelState(False, False)
        assert "Install onnxruntime first" in controller._missing_model_text()

    def test_while_pip_runs_no_command_is_told(self, ctrl_module, controller):
        ctrl_module._segmentation_stub.state = ModelState(False, False, True)
        assert "being installed" in controller._missing_model_text()

    def test_without_the_files_the_download_is_told(self, ctrl_module, controller):
        ctrl_module._segmentation_stub.state = ModelState(True, False)
        assert "Install the segmentation model first" in controller._missing_model_text()

    def test_ready_but_unloadable(self, ctrl_module, controller):
        assert "could not be loaded" in controller._missing_model_text()

    def test_during_the_download_no_install_is_asked(self, ctrl_module, controller):
        ctrl_module._segmentation_stub.state = ModelState(True, False)
        controller.install_model()
        assert "being downloaded" in controller._missing_model_text()


class TestInstallModel:
    def test_a_download_task_goes_to_the_task_manager(self, ctrl_module, controller):
        controller.install_model()
        assert len(ctrl_module._added_tasks) == 1 and controller.downloading()
        task = FakeDownloadTask.made[0]
        assert task.directory == "/profile/filtermate/models/sam"
        assert ("set_segmentation_status", "Downloading the segmentation model… 0 %") in controller._host.calls
        assert controller._host.calls[-1][0] == "set_segmentation_readiness"  # the button waits for the download

    def test_one_download_at_a_time(self, ctrl_module, controller):
        controller.install_model()
        controller.install_model()
        assert len(ctrl_module._added_tasks) == 1

    def test_progress_reaches_the_panel(self, ctrl_module, controller):
        controller.install_model()
        FakeDownloadTask.made[0].progress_slots[0](42.7)
        assert controller._host.calls[-1] == ("set_segmentation_status", "Downloading the segmentation model… 42 %")

    def test_success_refreshes_the_readiness_and_invites_to_click(self, ctrl_module, controller):
        controller.install_model()
        ctrl_module._segmentation_stub.state = ModelState(True, True)
        FakeDownloadTask.made[0].finish(True)
        assert not controller.downloading()
        assert ("set_segmentation_readiness", True, True, False, False, False) in controller._host.calls
        assert controller._host.calls[-1] == ("set_segmentation_status", "Model installed: left click on an object, or draw a box")

    def test_a_failure_is_told_and_the_button_comes_back(self, ctrl_module, controller):
        controller.install_model()
        ctrl_module._segmentation_stub.state = ModelState(True, False)
        FakeDownloadTask.made[0].finish(False, "disk full")
        assert ("set_segmentation_readiness", True, False, False, False, False) in controller._host.calls
        assert controller._host.calls[-1] == ("set_segmentation_status", "The model could not be downloaded: disk full")
        controller.install_model()
        assert len(ctrl_module._added_tasks) == 2

    def test_success_without_the_runtime_says_what_is_left(self, ctrl_module, controller):
        controller.install_model()
        ctrl_module._segmentation_stub.state = ModelState(False, True)
        FakeDownloadTask.made[0].finish(True)
        assert "Install onnxruntime first" in controller._host.calls[-1][1]

    def test_the_dock_going_away_cancels_it(self, ctrl_module, controller):
        controller.install_model()
        task = FakeDownloadTask.made[0]
        canceled = []
        task.cancel = lambda: canceled.append(True)
        controller.cancel_download()
        assert canceled == [True] and not controller.downloading()
        controller.cancel_download()
        assert canceled == [True]

    def test_a_cancel_is_no_error(self, ctrl_module, controller):
        controller.install_model()
        FakeDownloadTask.made[0].finish(False)
        assert controller._host.calls[-1] == ("set_segmentation_status", "Download canceled")

    def test_a_torn_down_host_hears_nothing(self, ctrl_module, controller):
        controller.install_model()
        controller._host._torn_down = True
        before = list(controller._host.calls)
        FakeDownloadTask.made[0].progress_slots[0](50.0)
        FakeDownloadTask.made[0].finish(True)
        assert controller._host.calls == before and not controller.downloading()


class FakeRenderer:
    def __init__(self, alpha):
        self.alpha = alpha

    def alphaBand(self):
        return self.alpha


class FakeRaster:
    def __init__(self, layer_id, source, alpha=-1):
        self._id, self._source, self._renderer = layer_id, source, FakeRenderer(alpha)

    def id(self):
        return self._id

    def source(self):
        return self._source

    def providerType(self):
        return 'gdal'

    def extent(self):
        return types.SimpleNamespace(width=lambda: 100.0, height=lambda: 50.0)

    def width(self):
        return 400

    def height(self):
        return 200

    def renderer(self):
        return self._renderer


class TestOriginalSource:
    """2026-11-12: a raster filtered by FilterMate was drawn from its original source with the renderer of the derived
    one, whose alpha band (added by FilterMate) the original source has not: an invalid block, a black window."""

    @pytest.fixture
    def alphas(self, ctrl_module, monkeypatch):
        alphas = {}
        snapshots = types.ModuleType(f"{_PKG}.adapters.qgis.coverage_layers.snapshots")
        snapshots.registry = lambda: types.SimpleNamespace(original_alpha_band=alphas.get)
        monkeypatch.setitem(sys.modules, snapshots.__name__, snapshots)
        materialization = types.ModuleType(f"{_PKG}.adapters.qgis.coverage_layers.raster_materialization")
        materialization.raster_reads_remotely = lambda provider, source: False
        monkeypatch.setitem(sys.modules, materialization.__name__, materialization)
        return alphas

    def source_of(self, controller, layer, base):
        controller._host._raster_capability = lambda _layer: types.SimpleNamespace(has_raw_values=True)
        controller._host._base_raster = lambda _layer: base
        return controller._window_source(layer)

    def test_an_unfiltered_raster_keeps_its_renderer(self, controller, alphas):
        layer = FakeRaster('ortho', '/data/ortho.tif', alpha=4)
        assert self.source_of(controller, layer, layer) == ('/data/ortho.tif', 'gdal', 0.25, None)

    def test_the_band_the_layer_had_on_its_original_source(self, controller, alphas):
        layer, base = FakeRaster('ortho', '/cache/ortho.clip.vrt', alpha=4), FakeRaster('ortho', '/data/ortho.tif')
        alphas['ortho'] = -1  # an RGB orthophoto: no alpha band before FilterMate added one to the derived VRT
        assert self.source_of(controller, layer, base) == ('/data/ortho.tif', 'gdal', 0.25, -1)

    def test_unknown_the_band_qgis_gave_the_original(self, controller, alphas):
        layer, base = FakeRaster('ortho', '/cache/ortho.clip.vrt', alpha=5), FakeRaster('ortho', '/data/rgba.tif', alpha=4)
        assert self.source_of(controller, layer, base)[3] == 4


def _real_segmentation():
    """The adapter itself (pure parts: windows, well_inside), loaded by the coverage fakes."""
    if "fm_coverage_fakes" not in sys.modules:
        spec = importlib.util.spec_from_file_location("fm_coverage_fakes", _ROOT / "tests/unit/adapters/qgis/coverage_fakes.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules["fm_coverage_fakes"] = module
        spec.loader.exec_module(module)
    fakes = sys.modules["fm_coverage_fakes"]
    fakes.load("adapters.qgis.python_dependencies")
    return fakes, fakes.load("segmentation")


class Point:
    def __init__(self, x, y):
        self._x, self._y = float(x), float(y)

    def x(self):
        return self._x

    def y(self):
        return self._y


class TestReuseOfTheEncodedWindow:
    """2026-11-12: a click 2 pixels inside the encoded window reused it, and the object around the click was cut at its
    edge; the similar objects ask 32 pixels (well_inside). A box running past it was cut by set_box."""

    @pytest.fixture
    def flow(self, ctrl_module, controller, monkeypatch):
        fakes, real = _real_segmentation()
        model = types.SimpleNamespace(input_size=1024, predict=lambda *args: (None, 0.0))
        monkeypatch.setattr(ctrl_module._segmentation_stub, 'find_provider', lambda: model, raising=False)
        monkeypatch.setattr(ctrl_module._segmentation_stub, 'well_inside', real.well_inside, raising=False)
        extent = fakes.FakeRectangle(0.0, 0.0, 10000.0, 10000.0)
        extent.contains = lambda point: True
        layer = types.SimpleNamespace(id=lambda: 'ortho', extent=lambda: extent)
        controller._host._active_layer = layer
        encoded = real.SegmentationWindow(1000.0, 2024.0, 1.0, 1024)  # x 1000..2024, y 1000..2024
        controller._session = real.SegmentationSession(model, encoded, 'embedding')
        controller._session_layer = 'ortho'
        controller._window_source = lambda _layer: ('/data/ortho.tif', 'gdal', 1.0, None)
        controller._plan = lambda _layer, center, native, _model: real.window_at(center.x(), center.y(),
                                                                                  (0.0, 0.0, 10000.0, 10000.0), 1.0, 1024)
        done = []
        controller._encode = lambda *args: done.append('encoded')
        controller._predict = lambda session: done.append('reused')
        return controller, done, fakes

    def test_a_click_well_inside_reuses_it(self, flow):
        controller, done, _fakes = flow
        assert controller._prompt('point', Point(1500.0, 1500.0), True, False) and done == ['reused']

    def test_a_click_near_its_edge_encodes_a_window_around_it(self, flow):
        controller, done, _fakes = flow
        assert controller._prompt('point', Point(2022.0, 1500.0), True, False) and done == ['encoded']

    def test_a_box_running_past_it_encodes_another(self, flow):
        controller, done, fakes = flow
        controller._prompt('box', fakes.FakeRectangle(1900.0, 1400.0, 2100.0, 1600.0), True, False)
        controller._prompt('box', fakes.FakeRectangle(1400.0, 1400.0, 1600.0, 1600.0), True, False)
        assert done == ['encoded', 'reused']


class TestVisibleExtent:
    def test_a_map_past_the_domain_of_the_crs_gives_the_layer_extent(self, controller):
        """2026-11-12: QgsCsException raised out of the callback of the encoding (a virtual method of C++)."""
        settings = types.SimpleNamespace(visibleExtent=lambda: 'the world')
        controller._host._iface = lambda: types.SimpleNamespace(mapCanvas=lambda: types.SimpleNamespace(mapSettings=lambda: settings))
        controller._host._active_layer = types.SimpleNamespace(extent=lambda: 'the raster')

        def fail(_extent):
            raise Exception('forward transform of the world failed')  # QgsCsException is no RuntimeError

        controller._transform = lambda: types.SimpleNamespace(transformBoundingBox=fail)
        assert controller._visible_extent() == 'the raster'
        controller._transform = lambda: types.SimpleNamespace(transformBoundingBox=lambda extent: f'{extent} reprojected')
        assert controller._visible_extent() == 'the world reprojected'


class FakeOutline:
    def __init__(self):
        self.removed = False

    def hide(self):
        pass

    def remove(self):
        self.removed = True


class TestLeftovers:
    """2026-11-12: proposals left on the map once the tool left it; outlines and markers left in the scene of the map."""

    def test_the_proposals_go_with_the_tool(self, controller):
        controller._host._show_picker_state = lambda shown: None
        controller._proposals = [('POLYGON((0 0,1 0,1 1,0 0))', 'POLYGON((5 5,6 5,6 6,5 5))')]
        controller._on_tool_left()
        assert controller.proposal_count() == 0 and ('set_proposal_count', 0) in controller._host.calls

    def test_drop_takes_the_outlines_and_the_markers_out_of_the_scene(self, controller):
        outlines = [FakeOutline(), FakeOutline()]
        controller._outline, controller._proposal_outline = outlines
        removed = []
        controller.tool = types.SimpleNamespace(remove_items=lambda: removed.append('items'), clear_markers=lambda: None,
                                                deleteLater=lambda: removed.append('deleted'))
        controller._host._tool_on_map = lambda tool: False
        controller._host._release_map_tool = lambda tool, previous: None
        controller.drop()
        assert all(outline.removed for outline in outlines) and removed == ['items', 'deleted']
        assert controller._outline is None and controller._proposal_outline is None and controller.tool is None

    def test_the_tool_takes_its_items_out(self, monkeypatch):
        removed = []

        class MapTool:
            def __init__(self, canvas):
                self._canvas = canvas

            def canvas(self):
                return self._canvas

            def setCursor(self, cursor):
                pass

        gui = types.ModuleType("qgis.gui")
        gui.QgsMapTool, gui.QgsRubberBand, gui.QgsVertexMarker = MapTool, object, object
        monkeypatch.setitem(sys.modules, "qgis.gui", gui)
        spec = importlib.util.spec_from_file_location(f"{_PKG}_tool", _ROOT / "ui/tools/segmentation_tool.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        canvas = types.SimpleNamespace(scene=lambda: types.SimpleNamespace(removeItem=removed.append))
        tool = module.SegmentationTool(canvas)
        tool._markers, tool._band, tool._shown = ['cross', 'x'], 'box', 1
        tool.remove_items()
        assert removed == ['cross', 'x', 'box'] and tool._markers == [] and tool._band is None


class FakeTask:
    def __init__(self, status):
        self._status, self.canceled, self.stopped = status, False, False

    def status(self):
        return self._status

    def cancel(self):
        self.canceled = True


class TestQueuedTasks:
    """2026-11-12: a search stopped while queued was never canceled (QGIS 3.22) and ran to its end, some 20 s of CPU."""

    @pytest.fixture(autouse=True)
    def statuses(self, monkeypatch):
        monkeypatch.setattr(sys.modules["qgis.core"], "QgsTask",
                            types.SimpleNamespace(TaskStatus=types.SimpleNamespace(Running='running')), raising=False)

    def test_a_queued_task_is_flagged_not_canceled(self, ctrl_module):
        queued, running = FakeTask('queued'), FakeTask('running')
        ctrl_module.SegmentationController._stop(queued)
        ctrl_module.SegmentationController._stop(running)
        assert (queued.stopped, queued.canceled) == (True, False) and running.canceled

    def test_escape_stops_the_encoding_and_the_search(self, controller):
        encoding, search = FakeTask('queued'), FakeTask('running')
        controller._task, controller._search = encoding, search
        controller.cancel()
        assert encoding.stopped and not encoding.canceled and search.canceled
        assert controller._task is None and controller._search is None

    def test_a_task_flagged_gives_up_as_it_starts(self, monkeypatch):
        _fakes, real = _real_segmentation()
        opened = []
        monkeypatch.setattr(real, 'open_drawing', lambda *args: opened.append(args))
        window = real.SegmentationWindow(0.0, 8.0, 1.0, 8)
        embed = real.SegmentationEmbedTask('/data/ortho.tif', 'gdal', 'renderer', 'crs', window, object(), None)
        search = real.SimilarObjectsTask('/data/ortho.tif', 'gdal', 'renderer', types.SimpleNamespace(toWkt=lambda: ''),
                                         object(), (0.0, 0.0, 8.0, 8.0), 1.0, [(1.0, 1.0)], 'POLYGON EMPTY', (0.5, 2.0),
                                         False, None)
        for task in (embed, search):
            task.stopped = True
            assert task.run() is False
        assert opened == []
