# -*- coding: utf-8 -*-
"""FilterMate 5 operations (``adapters.public_api.operations``) — audit 2026-10.

The module is loaded for real under a synthetic package (its relative
imports reach ``core`` and ``adapters``); QGIS stays mocked by the root
conftest, layers are small stand-ins.
"""
import importlib
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_operations_test"


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.domain", _ROOT / "core" / "domain"),
                       (".core.services", _ROOT / "core" / "services"), (".adapters", _ROOT / "adapters"),
                       (".adapters.public_api", _ROOT / "adapters" / "public_api"),
                       (".adapters.qgis", _ROOT / "adapters" / "qgis"),
                       (".adapters.qgis.coverage_layers", _ROOT / "adapters" / "qgis" / "coverage_layers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    return (importlib.import_module(f"{_PKG}.adapters.public_api.operations"),
            importlib.import_module(f"{_PKG}.core.services.cross_filter_service"))


operations, service_mod = _load()


@pytest.fixture
def idle(monkeypatch):
    """No FilterMate task of the dock runs."""
    monkeypatch.setattr(operations, "_background_tasks_running", lambda: False)
    yield
    operations._RUNNING.clear()


class TestOneAtATime:

    def test_idle_means_not_busy(self, idle):
        assert operations.busy_reason() == ""

    def test_an_operation_refuses_another_one_while_it_runs(self, idle):
        # e.g. a REST call re-entering through processEvents during an export.
        seen = {}

        @operations._exclusive(tidy=False)
        def outer():
            seen["reason"] = operations.busy_reason()
            seen["inner"] = operations.clear_filters(["parcelle"], project=MagicMock())
            return operations.OperationReport()

        outer()
        assert "already running outer" in seen["reason"]
        assert seen["inner"].details["busy"] is True
        assert "already running" in seen["inner"].error
        assert operations.busy_reason() == ""  # released once over

    def test_lock_released_when_the_operation_raises(self, idle):
        @operations._exclusive(tidy=False)
        def broken():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            broken()
        assert operations.busy_reason() == ""

    def test_export_is_exclusive_too(self, idle):
        operations._RUNNING.append("cross_filter")
        report = operations.export_layers(["parcelle"], "/tmp/x", project=MagicMock())
        assert report.details.get("busy") is True

    @pytest.mark.parametrize("call", [
        lambda: operations.cross_filter("src", ["t"], project=MagicMock()),
        lambda: operations.cross_filter_by_geometry(MagicMock(), None, ["t"], project=MagicMock()),
        lambda: operations.filter_point_clouds(["t"], "Classification = 2", project=MagicMock()),
        lambda: operations.clear_filters(["t"], project=MagicMock()),
        lambda: operations.apply_favorite("fav", service=MagicMock(), project=MagicMock()),
    ])
    def test_every_operation_refused_while_busy(self, monkeypatch, call):
        monkeypatch.setattr(operations, "_background_tasks_running", lambda: True)
        report = call()
        assert report.error == operations.BACKGROUND_BUSY
        assert report.details["busy"] is True


class _Task:
    def __init__(self, description):
        self._description = description

    def description(self):
        return self._description


class TestDockTasksDetected:
    """``_busy`` only saw the cross filter service: a vector filter task of the dock went unnoticed."""

    @pytest.fixture
    def tasks(self, monkeypatch):
        active = []
        manager = MagicMock()
        manager.activeTasks.side_effect = lambda: list(active)
        qgis_core = sys.modules["qgis.core"]
        monkeypatch.setattr(qgis_core, "QgsApplication", MagicMock(taskManager=MagicMock(return_value=manager)),
                            raising=False)
        monkeypatch.setattr(service_mod, "_service", None)
        return active

    def test_no_task(self, tasks):
        assert operations.busy_reason() == ""

    def test_vector_filter_task_of_the_dock(self, tasks):
        task_class = type("FilterEngineTask", (_Task,), {})
        tasks.append(task_class("Filtering data"))  # translated description, no "FilterMate" prefix
        assert operations.busy_reason() == operations.BACKGROUND_BUSY

    @pytest.mark.parametrize("class_name", ["CrossFilterTask", "CoverageExportTask", "HeightAboveGroundTask"])
    def test_dock_tasks_changing_the_filters(self, tasks, class_name):
        tasks.append(type(class_name, (_Task,), {})("FilterMate: something"))
        assert operations.busy_reason() == operations.BACKGROUND_BUSY

    @pytest.mark.parametrize("class_name, description", [
        ("ExpressionEvaluationTask", "FilterMate: Evaluating on communes"),  # review 2026-10: no filter
        ("LayersManagementEngineTask", "FilterMate: adding layers"),
    ])
    def test_filtermate_tasks_that_do_not_filter_are_ignored(self, tasks, class_name, description):
        tasks.append(type(class_name, (_Task,), {})(description))
        assert operations.busy_reason() == ""

    def test_other_plugin_task_is_ignored(self, tasks):
        tasks.append(_Task("Rendering"))
        assert operations.busy_reason() == ""

    @pytest.mark.parametrize("status, busy", [(1, True), (2, True), (3, False), (4, False)])
    def test_a_finishing_task_applies_its_own_filters(self, tasks, monkeypatch, status, busy):
        # QGIS lists a task in activeTasks() while its finished() runs on the
        # main thread: the dock then applies the server subsets of that very
        # task, which a busy guard must not refuse (2026-10-20).
        monkeypatch.setattr(sys.modules["qgis.core"], "QgsTask", types.SimpleNamespace(
            TaskStatus=types.SimpleNamespace(Complete=3, Terminated=4)), raising=False)
        task = type("FilterEngineTask", (_Task,), {"status": lambda self: status})("Filtering data")
        tasks.append(task)
        assert operations._background_tasks_running() is busy
        assert (operations.busy_reason() == operations.BACKGROUND_BUSY) is busy


# ---------------------------------------------------------------------------
# Stand-ins: signals, feedback, layers, project, cross filter task
# ---------------------------------------------------------------------------

class _Signal:
    def __init__(self):
        self.slots = []

    def connect(self, slot, *connection_type):
        self.slots.append(slot)

    def disconnect(self, slot):
        self.slots.remove(slot)

    def emit(self, *args):
        for slot in list(self.slots):
            slot(*args)


@pytest.fixture(autouse=True)
def qt_wait_loop(monkeypatch):
    import threading
    import time

    timers = []

    class Loop:
        def __init__(self):
            self.stopped = False

        def quit(self):
            self.stopped = True

        def exec(self):
            self.stopped = False
            deadline = time.monotonic() + 5
            while not self.stopped:
                assert time.monotonic() < deadline, "worker did not complete"
                for timer in list(timers):
                    timer.timeout.emit()
                time.sleep(0.001)

    class Timer:
        def __init__(self):
            self.timeout = _Signal()

        def start(self, interval):
            timers.append(self)

        def stop(self):
            if self in timers:
                timers.remove(self)

    qt = sys.modules["qgis.PyQt.QtCore"]
    monkeypatch.setattr(qt, "QEventLoop", Loop, raising=False)
    monkeypatch.setattr(qt, "QTimer", Timer, raising=False)
    monkeypatch.setattr(qt, "Qt", types.SimpleNamespace(DirectConnection=1), raising=False)
    yield types.SimpleNamespace(timers=timers, main_thread=threading.get_ident())
    assert not timers, "poll timer leaked"


class _Feedback:
    """QgsProcessingFeedback stand-in: progress log, Cancel button."""

    def __init__(self):
        self.canceled = _Signal()
        self._canceled = False
        self.progress = []

    def isCanceled(self):
        return self._canceled

    def cancel(self):
        self._canceled = True
        self.canceled.emit()

    def setProgress(self, value):
        self.progress.append(value)


class _Layer:
    def __init__(self, layer_id, name):
        self._id, self._name = layer_id, name

    def id(self):
        return self._id

    def name(self):
        return self._name

    def crs(self):
        return "EPSG:2154"


class _Project:
    def __init__(self, *layers):
        self.layers = {layer.id(): layer for layer in layers}

    def mapLayer(self, layer_id):
        return self.layers.get(layer_id)

    def mapLayersByName(self, name):
        return [layer for layer in self.layers.values() if layer.name() == name]

    def transformContext(self):
        return None


class _CrossTask:
    """CrossFilterTask stand-in: three steps, checks cancellation between them."""

    def __init__(self, source_id, target_ids, cancel_with=None, cancel_at=None):
        self.progressChanged = _Signal()
        self._canceled = False
        self.cancel_with, self.cancel_at = cancel_with, cancel_at
        self.error, self.changes = "", []
        self.source_job = types.SimpleNamespace(layer_id=source_id, kind=operations.LayerKind.VECTOR, details={})
        self.target_ids = target_ids
        self.outcomes = []
        self.steps = 0

    def cancel(self):
        self._canceled = True

    def isCanceled(self):
        return self._canceled

    def run(self):
        for step in range(3):
            if self.isCanceled():
                return False
            if step == self.cancel_at:
                self.cancel_with.cancel()  # the user clicks Cancel while the task runs
                continue
            self.steps += 1
            self.progressChanged.emit(100.0 * (step + 1) / 3)
        return True

    def apply_results(self, result):
        # Like CrossFilterTask: each job's outcome comes from its compute step;
        # with result False nothing is applied, but computed jobs still say success.
        self.outcomes = [types.SimpleNamespace(layer_id=layer_id, success=index < self.steps, kept_count=1,
                                               elapsed=0.0, message="", details={})
                         for index, layer_id in enumerate(self.target_ids)]


class _Service:
    def __init__(self, task):
        self.task = task
        self.ran_synchronously = False
        self._running = []

    def build_task(self, request, source_job):
        self.request = request
        return self.task

    def run(self, request, source_job, synchronous=False):
        self.request, self.ran_synchronously = request, synchronous
        self.task.apply_results(self.task.run())
        return self.task


@pytest.fixture
def vector_world(idle, monkeypatch):
    """A vector source and target; the source job and the registry hook stubbed."""
    source, target = _Layer("S", "communes"), _Layer("T", "batiment")
    monkeypatch.setattr(operations, "layer_kind", lambda layer: operations.LayerKind.VECTOR)
    monkeypatch.setattr(operations, "_install_registry", lambda project: None)
    monkeypatch.setattr(operations, "_source_job", lambda layer, kind, report, **kwargs: types.SimpleNamespace(
        before=None, layer_id=layer.id(), kind=kind, details={}))
    tidied = []
    monkeypatch.setattr(service_mod, "tidy_cache", lambda project=None: tidied.append(project))
    return types.SimpleNamespace(source=source, target=target, project=_Project(source, target), tidied=tidied)


class TestFeedbackRelayed:
    """Processing's progress bar and Cancel button reach the cross filter task."""

    def test_progress_reaches_the_feedback(self, vector_world):
        feedback = _Feedback()
        task = _CrossTask("S", ["T"])
        report = operations.cross_filter(vector_world.source, ["batiment"], project=vector_world.project,
                                         service=_Service(task), feedback=feedback)
        assert report.ok and report.done == {"T": "batiment"}
        assert feedback.progress[-1] == pytest.approx(100.0)
        assert task.progressChanged.slots == [] and feedback.canceled.slots == []  # disconnected

    def test_cancel_stops_the_task_and_reports_it(self, vector_world):
        feedback = _Feedback()
        task = _CrossTask("S", ["T"], cancel_with=feedback, cancel_at=1)
        report = operations.cross_filter(vector_world.source, ["batiment"], project=vector_world.project,
                                         service=_Service(task), feedback=feedback)
        assert task.steps == 1  # stopped at the next check
        assert report.error == "canceled"
        # Review 2026-10: a target computed before the cancel was not applied: not "done".
        assert report.done == {} and report.failed == {}

    def test_source_only_canceled_before_it_is_applied(self, vector_world, monkeypatch):
        calls = []
        job = types.SimpleNamespace(before=None, layer_id="S", kind=operations.LayerKind.RASTER, details={},
                                    apply=lambda layer: calls.append("apply"), release=lambda: calls.append("release"))
        monkeypatch.setattr(operations, "_source_job", lambda layer, kind, report, **kwargs: job)
        feedback = _Feedback()
        feedback.cancel()
        service = _Service(_CrossTask("S", []))
        service.history = MagicMock()
        report = operations.cross_filter(vector_world.source, [], project=vector_world.project, service=service,
                                         feedback=feedback)
        assert report.error == "canceled"
        assert calls == ["release"]
        service.history.push.assert_not_called()

    def test_canceled_before_the_start(self, vector_world):
        feedback = _Feedback()
        feedback.cancel()
        task = _CrossTask("S", ["T"])
        report = operations.cross_filter(vector_world.source, ["batiment"], project=vector_world.project,
                                         service=_Service(task), feedback=feedback)
        assert task.steps == 0 and report.error == "canceled"

    def test_without_feedback_builds_task_instead_of_inline_service_run(self, vector_world):
        service = _Service(_CrossTask("S", ["T"]))
        report = operations.cross_filter(vector_world.source, ["batiment"], project=vector_world.project, service=service)
        assert report.ok and service.task.steps == 3
        assert service.ran_synchronously is False

    def test_point_cloud_filter_stops_before_the_next_layer(self, idle, monkeypatch):
        feedback = _Feedback()
        feedback.cancel()
        report = operations.filter_point_clouds(["dalle_1", "dalle_2"], "Classification = 2",
                                                project=_Project(), feedback=feedback)
        assert report.error == "canceled" and not report.skipped


class TestUnexpectedErrorsFlagged:
    """Review 2026-10: kept for the local caller, flagged so REST hides them (paths, SQL)."""

    def test_operation_error(self, vector_world):
        class _Failing(_Service):
            def build_task(self, request, source_job):
                raise OSError("[Errno 13] Permission denied: '/home/u/.local/share/QGIS/cache/session_1/x.vrt'")

        report = operations.cross_filter(vector_world.source, ["batiment"], project=vector_world.project,
                                         service=_Failing(_CrossTask("S", ["T"])))
        assert "Permission denied" in report.error
        assert report.details["internal_error"] is True

    def test_validation_error_is_not_flagged(self, vector_world):
        report = operations.cross_filter(vector_world.source, ["batiment"], buffer=float("nan"),
                                         project=vector_world.project)
        assert report.error and "internal_error" not in report.details

    def test_export_layer_failure(self, vector_world, tmp_path, monkeypatch):
        def broken(*args, **kwargs):
            raise RuntimeError("sqlite3: no such table gpkg_contents in /srv/qgis/private.gpkg")

        monkeypatch.setattr(operations, "_export_vector", broken)
        layer = _Layer("A", "parcelle")
        report = operations.export_layers([layer], str(tmp_path), project=_Project(layer))
        assert "no such table" in report.failed["parcelle"]
        assert report.details["internal_failures"] == ["parcelle"]


class TestHomonymsEverywhere:
    def test_cross_filter_targets(self, vector_world):
        twin = _Layer("T2", "batiment")
        project = _Project(vector_world.source, vector_world.target, twin)
        task = _CrossTask("S", ["T", "T2"])
        task.steps = 2
        task.run = lambda: True
        report = operations.cross_filter(vector_world.source, ["T", "T2"], project=project, service=_Service(task))
        assert report.done == {"T": "batiment", "T2": "batiment (T2)"}
        assert set(report.details["layers"]) == {"batiment", "batiment (T2)"}

    def test_clear_filters(self, vector_world):
        twin = _Layer("T2", "batiment")
        service = MagicMock()
        service.unfilter.return_value = ["T"]
        report = operations.clear_filters(["T", "T2"], project=_Project(vector_world.target, twin), service=service)
        assert report.done == {"T": "batiment"}
        assert report.skipped == {"batiment (T2)": "not filtered"}


class TestCacheTidied:
    """The derived files of automation runs are removed (the dock only tidied after its own runs)."""

    def test_tidied_after_a_filter(self, vector_world):
        operations.cross_filter(vector_world.source, ["batiment"], project=vector_world.project,
                                service=_Service(_CrossTask("S", ["T"])))
        assert vector_world.tidied == [vector_world.project]

    def test_tidied_after_a_failed_filter(self, vector_world):
        operations.cross_filter(vector_world.source, ["ghost"], project=vector_world.project)
        assert vector_world.tidied == [vector_world.project]

    def test_not_tidied_when_refused_busy(self, vector_world):
        operations._RUNNING.append("export_layers")
        operations.cross_filter(vector_world.source, ["batiment"], project=vector_world.project)
        assert vector_world.tidied == []

    def test_not_tidied_after_an_export(self, vector_world, tmp_path):
        operations.export_layers([], str(tmp_path), project=vector_world.project)
        assert vector_world.tidied == []

    def test_tidy_failure_does_not_break_the_operation(self, vector_world, monkeypatch):
        def broken(project=None):
            raise OSError("cache folder gone")
        monkeypatch.setattr(service_mod, "tidy_cache", broken)
        report = operations.cross_filter(vector_world.source, ["batiment"], project=vector_world.project,
                                         service=_Service(_CrossTask("S", ["T"])))
        assert report.ok


class TestNumbersChecked:
    """Python API / Processing: NaN or infinite buffer refused with a message, never run."""

    @pytest.mark.parametrize("buffer, coverage", [(float("nan"), 0), (float("inf"), 0), (0, float("nan")), (0, 150)])
    def test_cross_filter(self, vector_world, buffer, coverage):
        service = _Service(_CrossTask("S", ["T"]))
        report = operations.cross_filter(vector_world.source, ["batiment"], buffer=buffer, coverage_min=coverage,
                                         project=vector_world.project, service=service)
        assert report.error and not report.done
        assert service.task.steps == 0


class _Geometry:
    """QgsGeometry stand-in whose reprojection fails (QgsCsException)."""

    def __init__(self, other=None):
        pass

    def isNull(self):
        return False

    def isEmpty(self):
        return False

    def transform(self, transform):
        raise RuntimeError("forward transform of (1e+20, 0): latitude or longitude exceeded limits")


class TestGeometryFilterErrors:
    @pytest.fixture
    def geometry(self, monkeypatch):
        qgis_core = sys.modules["qgis.core"]
        monkeypatch.setattr(qgis_core, "QgsGeometry", _Geometry, raising=False)
        monkeypatch.setattr(qgis_core, "QgsCoordinateTransform", lambda *args: "transform", raising=False)
        return _Geometry()

    def test_transform_failure_is_a_report_error(self, vector_world, geometry):
        crs = MagicMock()
        crs.isValid.return_value = True
        report = operations.cross_filter_by_geometry(geometry, crs, ["batiment"], project=vector_world.project)
        assert "latitude or longitude" in report.error

    def test_nan_buffer_is_a_report_error(self, vector_world, geometry):
        report = operations.cross_filter_by_geometry(geometry, None, ["batiment"], buffer=float("nan"),
                                                     project=vector_world.project)
        assert "finite" in report.error


class TestExportReport:
    def test_homonym_layers_both_reported(self, vector_world, tmp_path, monkeypatch):
        first, second = _Layer("A", "parcelle"), _Layer("B", "parcelle")
        monkeypatch.setattr(operations, "_export_vector",
                            lambda layer, path, driver, crs, project, feedback=None: (True, path, ""))
        report = operations.export_layers([first, second], str(tmp_path), project=_Project(first, second))
        assert report.done == {"A": "parcelle", "B": "parcelle (B)"}
        assert sorted(report.outputs) == ["parcelle", "parcelle (B)"]
        assert report.outputs["parcelle"] != report.outputs["parcelle (B)"]

    @pytest.mark.skipif(sys.platform.startswith("win"), reason="symbolic links need privileges on Windows")
    def test_symlinked_output_file_is_not_written(self, vector_world, tmp_path, monkeypatch):
        # Audit 2026-10: a link planted as the output file would make the writer write anywhere.
        written = []
        monkeypatch.setattr(operations, "_export_vector",
                            lambda layer, path, driver, crs, project, feedback=None: (written.append(path) or
                                                                                      (True, path, "")))
        victim = tmp_path / "victim.txt"
        victim.write_text("keep")
        (tmp_path / "out").mkdir()
        (tmp_path / "out" / "parcelle.gpkg").symlink_to(victim)
        layer = _Layer("A", "parcelle")
        report = operations.export_layers([layer, _Layer("B", "route")], str(tmp_path / "out"),
                                          project=_Project(layer))
        assert "symbolic link" in report.failed["parcelle"]
        assert written == [str(tmp_path / "out" / "route.gpkg")]
        assert victim.read_text() == "keep"

    def test_output_file_that_is_the_source_of_a_layer_is_not_written(self, vector_world, tmp_path, monkeypatch):
        # A layer stored in out/parcelle.gpkg: the writer would overwrite the file and lose it.
        written = []
        monkeypatch.setattr(operations, "_export_vector",
                            lambda layer, path, driver, crs, project, feedback=None: (written.append(path) or
                                                                                      (True, path, "")))
        (tmp_path / "out").mkdir()
        source = tmp_path / "out" / "parcelle.gpkg"
        source.write_bytes(b"precious")
        exported, other = _Layer("A", "parcelle"), _Layer("B", "route")
        exported.source = lambda: f"{source}|layername=parcelle"
        other.source = lambda: "/data/route.shp"
        project = _Project(exported, other)
        project.mapLayers = lambda: project.layers
        report = operations.export_layers([exported, other], str(tmp_path / "out"), project=project)
        assert "data source of the layer 'parcelle'" in report.failed["parcelle"]
        assert written == [str(tmp_path / "out" / "route.gpkg")]
        assert source.read_bytes() == b"precious"

    def test_vector_writer_gets_a_child_feedback(self, vector_world, tmp_path, monkeypatch):
        captured = {}

        class _Writer:
            class WriterError:
                NoError = 0

            class SaveVectorOptions:
                feedback = None

            @staticmethod
            def writeAsVectorFormatV3(layer, path, context, options):
                captured["feedback"] = options.feedback
                options.feedback.progressChanged.emit(50.0)
                return (0, "", path)

        class _ChildFeedback(_Feedback):
            def __init__(self):
                super().__init__()
                self.progressChanged = _Signal()

        qgis_core = sys.modules["qgis.core"]
        monkeypatch.setattr(qgis_core, "QgsVectorFileWriter", _Writer, raising=False)
        monkeypatch.setattr(qgis_core, "QgsFeedback", _ChildFeedback, raising=False)
        feedback = _Feedback()
        layer = _Layer("A", "parcelle")
        report = operations.export_layers([layer, _Layer("B", "route")], str(tmp_path), feedback=feedback,
                                          project=_Project(layer))
        assert report.ok
        assert isinstance(captured["feedback"], _ChildFeedback)
        # 50 % of the first of two layers = 25 % of the export.
        assert 25.0 in feedback.progress
        assert feedback.canceled.slots == []


class TestWorkerExecution:
    @pytest.mark.parametrize("with_feedback", [False, True])
    def test_compute_worker_apply_and_progress_main(self, qt_wait_loop, with_feedback):
        import threading
        threads = {}
        feedback = _Feedback() if with_feedback else None
        task = _CrossTask("S", ["T"])
        original_run, original_apply = task.run, task.apply_results

        def run():
            threads["compute"] = threading.get_ident()
            return original_run()

        def apply(result):
            threads["apply"] = threading.get_ident()
            original_apply(result)

        task.run, task.apply_results = run, apply
        if feedback is not None:
            def progress(value):
                threads.setdefault("progress", []).append(threading.get_ident())
                feedback.progress.append(value)
            feedback.setProgress = progress
        assert operations._run_task(_Service(task), None, None, feedback) is task
        assert threads["compute"] != qt_wait_loop.main_thread
        assert threads["apply"] == qt_wait_loop.main_thread
        if feedback is not None:
            assert threads["progress"] and set(threads["progress"]) == {qt_wait_loop.main_thread}
            assert feedback.progress[-1] == 100.0
            assert not feedback.canceled.slots and not task.progressChanged.slots

    def test_main_event_loop_can_cancel_busy_worker(self, qt_wait_loop):
        import threading
        import time
        started = threading.Event()
        feedback = _Feedback()
        task = _CrossTask("S", ["T"])
        applied = []

        def run():
            started.set()
            deadline = time.monotonic() + 3
            while not task.isCanceled() and time.monotonic() < deadline:
                time.sleep(0.001)
            assert task.isCanceled(), "main event loop never canceled worker"
            return False

        original_progress = feedback.setProgress
        def cancel_on_main(value):
            assert threading.get_ident() == qt_wait_loop.main_thread
            original_progress(value)
            feedback.cancel()
        feedback.setProgress = cancel_on_main
        def computing():
            task.progressChanged.emit(10)
            return run()
        task.run = computing
        task.apply_results = lambda result: applied.append((result, threading.get_ident()))
        operations._run_task(_Service(task), None, None, feedback)
        assert started.is_set()
        assert applied == [(False, qt_wait_loop.main_thread)]
        assert not feedback.canceled.slots and not task.progressChanged.slots

    def test_worker_exception_releases_results_once_on_main(self, qt_wait_loop):
        import threading
        task = _CrossTask("S", ["T"])
        feedback = _Feedback()
        applied = []
        def broken():
            raise RuntimeError("worker failure")
        task.run = broken
        task.apply_results = lambda result: applied.append((result, threading.get_ident()))
        with pytest.raises(RuntimeError, match="worker failure"):
            operations._run_task(_Service(task), None, None, feedback)
        assert applied == [(False, qt_wait_loop.main_thread)]
        assert not feedback.canceled.slots and not task.progressChanged.slots


class TestCaptureDetails:
    def test_resampled_target_metadata_survives_worker_and_collection(self, vector_world):
        task = _CrossTask("S", ["T"])
        original_apply = task.apply_results
        def apply(result):
            original_apply(result)
            task.outcomes[0].details.update(capture_resampled=True, capture_grid="128x128")
        task.apply_results = apply
        report = operations.cross_filter(vector_world.source, ["batiment"], project=vector_world.project,
                                         service=_Service(task))
        assert report.ok
        assert report.details["layers"]["batiment"]["resampled"] is True
        assert report.details["layers"]["batiment"]["capture_grid"] == "128x128"


class TestWorkerServiceLease:
    @pytest.fixture(params=["dock", "api"])
    def service(self, monkeypatch, request):
        # Use the real service cancellation and status checks, with a task that
        # stays Queued because the API computes it outside QgsTaskManager.
        service = service_mod.CrossFilterService()
        monkeypatch.setattr(service_mod, "_service", service if request.param == "dock"
                            else service_mod.CrossFilterService())
        monkeypatch.setattr(operations, "_API_SERVICE", service if request.param == "api" else None)
        core = sys.modules["qgis.core"]
        monkeypatch.setattr(core, "QgsTask", types.SimpleNamespace(
            TaskStatus=types.SimpleNamespace(Complete=3, Terminated=4)), raising=False)
        monkeypatch.setattr(core, "QgsApplication", types.SimpleNamespace(
            taskManager=lambda: types.SimpleNamespace(activeTasks=lambda: [])), raising=False)
        return service

    def test_unload_cancels_worker_while_main_loop_reports_background_busy(self, service, qt_wait_loop,
                                                                        monkeypatch):
        import threading
        import time
        task = _CrossTask("S", ["T"])
        task.status = lambda: 0
        callbacks = []
        task.on_done = lambda: callbacks.append("done")
        feedback = _Feedback()
        applied = []
        monkeypatch.setattr(service, "build_task", lambda *args: task)
        registered_after_unload = object()

        def computing():
            task.progressChanged.emit(10)
            deadline = time.monotonic() + 3
            while not task.isCanceled() and time.monotonic() < deadline:
                time.sleep(0.001)
            assert task.isCanceled(), "cancel_all did not reach the worker"
            return False

        def unload(value):
            assert threading.get_ident() == qt_wait_loop.main_thread
            assert service._running == [task]
            assert operations._background_tasks_running()
            assert operations.busy_reason() == operations.BACKGROUND_BUSY
            service.cancel_all()
            assert task.on_done is None
            # Final cleanup must use the current list, not its old reference.
            service._running.append(registered_after_unload)

        def apply(result):
            applied.append((result, threading.get_ident()))
            if task.on_done is not None:
                task.on_done()

        task.run, task.apply_results = computing, apply
        feedback.setProgress = unload
        operations._run_task(service, None, None, feedback)
        assert applied == [(False, qt_wait_loop.main_thread)]
        assert callbacks == []
        assert service._running == [registered_after_unload]
        service._running.clear()
        assert not operations._background_tasks_running()
        assert not feedback.canceled.slots and not task.progressChanged.slots

    @pytest.mark.parametrize("failure", [None, "compute", "apply"])
    def test_service_lease_is_removed_on_success_or_exception(self, service, qt_wait_loop,
                                                            monkeypatch, failure):
        task = _CrossTask("S", ["T"])
        task.status = lambda: 0
        unrelated = object()
        service._running.append(unrelated)
        monkeypatch.setattr(service, "build_task", lambda *args: task)
        applied = []
        feedback = _Feedback()

        def compute():
            assert service._running == [unrelated, task]
            if failure == "compute":
                raise RuntimeError("compute failed")
            return True

        def apply(result):
            assert task in service._running
            applied.append(result)
            if failure == "apply":
                raise RuntimeError("apply failed")

        task.run, task.apply_results = compute, apply
        if failure:
            with pytest.raises(RuntimeError, match=failure + " failed"):
                operations._run_task(service, None, None, feedback)
        else:
            operations._run_task(service, None, None, feedback)
        assert applied == [failure != "compute"]
        assert service._running == [unrelated]
        assert not feedback.canceled.slots and not task.progressChanged.slots
        service._running.clear()


class TestSourceOnlyProject:
    def test_clipped_source_uses_explicit_project(self, qt_wait_loop, monkeypatch):
        import threading
        layer = _Layer("S", "raster")
        project = _Project(layer)
        after = types.SimpleNamespace(layer_id="S")
        applied = []
        def apply(current):
            assert threading.get_ident() == qt_wait_loop.main_thread
            assert current is layer
            applied.append(True)
            return after
        job = types.SimpleNamespace(layer_id="S", kind=operations.LayerKind.RASTER,
                                    clips_source=True, details={}, message="", before=object(),
                                    apply=apply, release=MagicMock())
        task = _CrossTask("S", [])
        task.source_job = job
        task.apply_results = MagicMock(side_effect=AssertionError("must not resolve singleton project"))
        service = _Service(task)
        service.history = MagicMock()
        cache = types.ModuleType(f"{_PKG}.adapters.qgis.coverage_layers.cache")
        cache.is_closed = lambda: False
        cache.settle = MagicMock()
        monkeypatch.setitem(sys.modules, cache.__name__, cache)
        report = operations._source_only(layer, operations.LayerKind.RASTER, job,
                                         operations.OperationReport(), service, True, project=project)
        assert report.ok and report.done == {"S": "raster"}
        assert applied == [True]
        job.release.assert_called_once_with()
        service.history.push.assert_called_once()
        assert not service._running

    def test_detached_source_is_released_without_compute_or_apply(self, monkeypatch):
        job = types.SimpleNamespace(clips_source=True, release=MagicMock(), apply=MagicMock())
        service = _Service(_CrossTask("S", []))
        monkeypatch.setattr(service, "build_task", MagicMock())
        report = operations._source_only(_Layer("S", "detached"), operations.LayerKind.RASTER, job,
                                         operations.OperationReport(), service, False, project=_Project())
        assert report.error and not report.done
        job.release.assert_called_once_with()
        job.apply.assert_not_called()
        service.build_task.assert_not_called()


class TestDiagnosticTranslation:
    def test_new_diagnostics_use_operations_translation_context(self, monkeypatch):
        translate = MagicMock(side_effect=lambda context, text: "translated: " + text)
        monkeypatch.setattr(sys.modules["qgis.PyQt.QtCore"], "QCoreApplication",
                            types.SimpleNamespace(translate=translate), raising=False)
        message = "rendered or unsupported raster: cannot be a filter target"
        assert operations._tr(message) == "translated: " + message
        translate.assert_called_once_with("FilterMateOperations", message)


class TestGuiReentry:
    @pytest.mark.parametrize("method", ["manage_task", "_execute_filter_task"])
    @pytest.mark.parametrize("task_name", ["filter", "unfilter", "reset", "export"])
    def test_gui_launch_is_refused_during_api_nested_loop(self, qt_wait_loop, monkeypatch, method, task_name):
        import ast
        import threading
        tree = ast.parse((_ROOT / "filter_mate_app.py").read_text())
        app_class = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                         and node.name == "FilterMateApp")
        function = next(node for node in app_class.body if isinstance(node, ast.FunctionDef) and node.name == method)
        warnings = MagicMock()
        namespace = {"__package__": _PKG, "logger": MagicMock(),
                     "iface": types.SimpleNamespace(messageBar=lambda: warnings),
                     "QCoreApplication": types.SimpleNamespace(translate=lambda context, text: text)}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(_ROOT / "filter_mate_app.py"), "exec"), namespace)
        # Any attempt to prepare a layer/task after the gate hits missing app
        # attributes and fails the regression, before it can mutate a target.
        gui_app = types.SimpleNamespace()
        task = _CrossTask("S", ["T"])
        release = threading.Event()
        feedback = _Feedback()
        monkeypatch.setattr(operations, "_background_tasks_running", lambda: False)

        def compute():
            task.progressChanged.emit(10)
            assert release.wait(3), "nested main loop did not handle GUI launch"
            return True

        def gui_launch(value):
            assert operations._RUNNING
            assert not release.is_set()
            assert threading.get_ident() == qt_wait_loop.main_thread
            try:
                arguments = (task_name, {}) if method == "_execute_filter_task" else (task_name,)
                namespace[method](gui_app, *arguments)
            finally:
                release.set()
        task.run = compute
        feedback.setProgress = gui_launch

        @operations._exclusive(tidy=False)
        def api_operation():
            return operations._run_task(_Service(task), None, None, feedback)

        assert api_operation() is task
        warnings.pushWarning.assert_called_once()
        assert not operations._RUNNING
