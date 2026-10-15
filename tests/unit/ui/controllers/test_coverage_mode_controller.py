# -*- coding: utf-8 -*-
"""
CoverageModeController (FilterMate 5): raster / point cloud source mode and
coverage targets of vector sources.

The controller is loaded by path under a private synthetic package where
BaseController, the capability module, the cross filter service and the
feedback helpers are stubs; the pure domain modules are the real ones.
"""
import importlib.util
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_cov_ctrl_test"


class FakeBaseController:
    def __init__(self, dockwidget, filter_service=None, signal_manager=None):
        self._dockwidget = dockwidget

    @property
    def dockwidget(self):
        return self._dockwidget

    def tr(self, text):
        return text

    def _disconnect_all_signals(self):
        pass


class FakeLayer:
    def __init__(self, layer_id, kind="vector", subset=""):
        self._id = layer_id
        self.kind = kind
        self._subset = subset

    def id(self):
        return self._id

    def name(self):
        return self._id

    def subsetString(self):
        return self._subset

    def setSubsetString(self, value):
        self._subset = value
        return True


class FakeService:
    def __init__(self):
        self.calls = []
        self.undo_ok = {}
        self.redo_ok = {}

    def unfilter(self, source_id, ids, kinds, record=True):
        self.calls.append(("unfilter", source_id, tuple(ids)))
        return list(ids)

    def undo(self, source_id):
        self.calls.append(("undo", source_id))
        return [source_id]

    def redo(self, source_id):
        self.calls.append(("redo", source_id))
        return [source_id]

    def can_undo(self, source_id):
        return self.undo_ok.get(source_id, False)

    def can_redo(self, source_id):
        return self.redo_ok.get(source_id, False)

    def run(self, request, job, on_done=None):
        self.calls.append(("run", request, job))


def _load_real(name, rel):
    spec = importlib.util.spec_from_file_location(f"{_PKG}.{name}", _ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"{_PKG}.{name}"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def ctrl_module(monkeypatch):
    for name in ("", ".ui", ".ui.controllers", ".core", ".core.domain", ".core.services",
                 ".adapters", ".adapters.qgis", ".infrastructure", ".infrastructure.feedback", ".config"):
        module = types.ModuleType(_PKG + name)
        module.__path__ = []
        monkeypatch.setitem(sys.modules, _PKG + name, module)
    base = types.ModuleType(f"{_PKG}.ui.controllers.base_controller")
    base.BaseController = FakeBaseController
    monkeypatch.setitem(sys.modules, base.__name__, base)
    layer_kind = _load_real("core.domain.layer_kind", "core/domain/layer_kind.py")
    _load_real("core.domain.cross_filter", "core/domain/cross_filter.py")
    _load_real("core.domain.filter_state", "core/domain/filter_state.py")
    capability = types.ModuleType(f"{_PKG}.adapters.qgis.point_cloud_capability")
    kinds = {"vector": layer_kind.LayerKind.VECTOR, "raster": layer_kind.LayerKind.RASTER,
             "pc": layer_kind.LayerKind.POINT_CLOUD}
    capability.get_layer_kind = lambda layer: kinds.get(getattr(layer, "kind", None), layer_kind.LayerKind.OTHER)
    monkeypatch.setitem(sys.modules, capability.__name__, capability)
    service = FakeService()
    service_module = types.ModuleType(f"{_PKG}.core.services.cross_filter_service")
    service_module.get_cross_filter_service = lambda: service
    service_module.calls = []
    service_module.clear_histories = lambda: service_module.calls.append(("clear_histories",))
    service_module.forget_layer_everywhere = lambda layer_id: service_module.calls.append(("forget", layer_id))
    service_module.tidy_report = None
    service_module.tidy_cache = lambda: service_module.tidy_report
    monkeypatch.setitem(sys.modules, service_module.__name__, service_module)
    feedback = sys.modules[f"{_PKG}.infrastructure.feedback"]
    feedback.messages = []
    feedback.show_info = lambda msg, *a, **k: feedback.messages.append(("info", msg))
    feedback.show_warning = lambda msg, *a, **k: feedback.messages.append(("warning", msg))
    spec = importlib.util.spec_from_file_location(f"{_PKG}.ui.controllers.coverage_mode_controller",
                                                  _ROOT / "ui/controllers/coverage_mode_controller.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    module._test_service = service
    module._test_service_module = service_module
    module._test_feedback = feedback
    module._test_kinds = kinds
    return module


@pytest.fixture
def layers(monkeypatch, ctrl_module):
    registry = {lid: FakeLayer(lid, kind) for lid, kind in
                (("v1", "vector"), ("v2", "vector"), ("r1", "raster"), ("p1", "pc"), ("o1", "other"))}
    monkeypatch.setattr(ctrl_module.CoverageModeController, "_map_layer", staticmethod(lambda i: registry.get(i)))
    return registry


def _dock(**widgets):
    dock = MagicMock()
    for name, widget in widgets.items():
        setattr(dock, name, widget)
    return dock


def _checked(value):
    widget = MagicMock()
    widget.isChecked.return_value = value
    return widget


@pytest.mark.unit
class TestDispatch:

    def test_vector_layer_change_is_not_handled(self, ctrl_module, layers):
        controller = ctrl_module.CoverageModeController(_dock())
        assert controller.on_current_layer_changed(layers["v1"]) is False

    def test_coverage_layer_change_activates(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        activated = []
        monkeypatch.setattr(controller, "_ensure_host", lambda: True)
        monkeypatch.setattr(controller, "activate", lambda layer, kind: activated.append((layer.id(), kind.value)))
        assert controller.on_current_layer_changed(layers["r1"]) is True
        assert controller.on_current_layer_changed(layers["p1"]) is True
        assert activated == [("r1", "raster"), ("p1", "point_cloud")]

    def test_missing_panels_fall_back_to_vector_chain(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        monkeypatch.setattr(controller, "_ensure_host", lambda: False)
        assert controller.on_current_layer_changed(layers["r1"]) is False

    def test_leaving_coverage_layer_deactivates(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        controller._active_layer = layers["r1"]
        calls = []
        monkeypatch.setattr(controller, "deactivate", lambda: calls.append("deactivate"))
        assert controller.on_current_layer_changed(layers["v1"]) is False
        assert calls == ["deactivate"]

    def test_tasks_are_ignored_without_active_layer(self, ctrl_module):
        controller = ctrl_module.CoverageModeController(_dock())
        assert controller.handle_task("filter") is False
        assert controller.handle_exploring_action("zoom") is False

    def test_tasks_route_to_the_service(self, ctrl_module, layers, monkeypatch):
        dock = _dock(current_layer=layers["r1"])
        controller = ctrl_module.CoverageModeController(dock)
        controller._active_layer = layers["r1"]
        restored = []
        monkeypatch.setattr(controller, "_finish_restore", lambda ids: restored.append(ids))
        monkeypatch.setattr(controller, "_run_filter", lambda layer: restored.append(("filter", layer.id())))
        monkeypatch.setattr(controller, "_run_export", lambda ids: restored.append(("export", ids)))
        monkeypatch.setattr(controller, "_layers_checked_for_export", lambda: [])
        assert controller.handle_task("undo") and controller.handle_task("redo")
        assert controller.handle_task("filter") and controller.handle_task("export")
        assert controller.handle_task("whatever") is True
        service = ctrl_module._test_service
        assert ("undo", "r1") in service.calls and ("redo", "r1") in service.calls
        assert ("filter", "r1") in restored and ("export", ["r1"]) in restored

    def test_export_defers_to_exporting_tab_when_layers_are_checked(self, ctrl_module, layers, monkeypatch):
        dock = _dock(current_layer=layers["r1"])
        controller = ctrl_module.CoverageModeController(dock)
        controller._active_layer = layers["r1"]
        monkeypatch.setattr(controller, "_layers_checked_for_export", lambda: ["v2", "r1"])
        assert controller.handle_task("export") is False

    def test_actions_blocked_while_a_task_runs(self, ctrl_module, layers, monkeypatch):
        dock = _dock(current_layer=layers["r1"])
        controller = ctrl_module.CoverageModeController(dock)
        controller._active_layer = layers["r1"]
        monkeypatch.setattr(controller, "is_running", lambda: True)
        assert controller.handle_task("undo") is True
        assert ("undo", "r1") not in ctrl_module._test_service.calls
        assert ctrl_module._test_feedback.messages[-1][0] == "warning"

    def test_task_releases_panel_when_current_layer_changed(self, ctrl_module, layers, monkeypatch):
        dock = _dock(current_layer=layers["v1"])
        controller = ctrl_module.CoverageModeController(dock)
        controller._active_layer = layers["r1"]
        calls = []
        monkeypatch.setattr(controller, "deactivate", lambda: calls.append("deactivate"))
        assert controller.handle_task("filter") is False
        assert calls == ["deactivate"]


@pytest.mark.unit
class TestVectorSourceTargets:

    def test_split(self, ctrl_module, layers):
        controller = ctrl_module.CoverageModeController(_dock())
        assert controller.split_coverage_targets(["v2", "r1", "p1", "o1"]) == (["v2", "o1"], ["r1", "p1"])
        assert controller.split_coverage_targets([]) == ([], [])

    @staticmethod
    def _linking(controller, changed=True):
        """Stand-in for _run_vector_source_filter: the cross task changed layers (or not)."""
        def fake(source, ids, run_index=None):
            if changed:
                controller._linked_runs[source.id()][run_index] = True
            return True
        return fake

    def test_undo_redo_follow_linked_runs(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        monkeypatch.setattr(controller, "_vector_engine_filters_targets", lambda: True)
        monkeypatch.setattr(controller, "_run_vector_source_filter", self._linking(controller))
        monkeypatch.setattr(controller, "_finish_restore", lambda ids: None)
        source = layers["v1"]
        controller.run_vector_source_task("filter", source, ["r1"])   # linked run
        controller.run_vector_source_task("filter", source, [])       # vector only run
        service = ctrl_module._test_service
        controller.run_vector_source_task("undo", source, [])
        assert ("undo", "v1") not in service.calls  # the vector-only run is undone first
        controller.run_vector_source_task("undo", source, [])
        assert service.calls.count(("undo", "v1")) == 1
        controller.run_vector_source_task("redo", source, [])
        assert ("redo", "v1") in service.calls
        controller.run_vector_source_task("redo", source, [])
        assert service.calls.count(("redo", "v1")) == 1

    def test_cross_task_without_change_is_not_linked(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        monkeypatch.setattr(controller, "_vector_engine_filters_targets", lambda: True)
        monkeypatch.setattr(controller, "_run_vector_source_filter", self._linking(controller, changed=False))
        controller.run_vector_source_task("filter", layers["v1"], ["r1"])
        controller.run_vector_source_task("undo", layers["v1"], [])
        assert ("undo", "v1") not in ctrl_module._test_service.calls

    def test_disabled_targets_or_predicates_skip_coverage_targets(self, ctrl_module, layers, monkeypatch):
        dock = _dock(pushButton_checkable_filtering_layers_to_filter=_checked(True),
                     pushButton_checkable_filtering_geometric_predicates=_checked(False))
        controller = ctrl_module.CoverageModeController(dock)
        ran = []
        monkeypatch.setattr(controller, "_run_vector_source_filter", lambda *a, **k: ran.append(a) or True)
        controller.run_vector_source_task("filter", layers["v1"], ["r1"])
        assert ran == [] and controller._linked_runs["v1"] == [False]

    def test_unfilter_keeps_links_like_the_vector_history(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        monkeypatch.setattr(controller, "_vector_engine_filters_targets", lambda: True)
        monkeypatch.setattr(controller, "_run_vector_source_filter", self._linking(controller))
        monkeypatch.setattr(controller, "_finish_restore", lambda ids: None)
        controller.run_vector_source_task("filter", layers["v1"], ["r1", "p1"])
        controller.run_vector_source_task("unfilter", layers["v1"], ["r1", "p1"])
        assert ("unfilter", "v1", ("r1", "p1")) in ctrl_module._test_service.calls
        # Undo after Unfilter goes back to before the last filter (vector engine rule).
        controller.run_vector_source_task("undo", layers["v1"], [])
        assert ("undo", "v1") in ctrl_module._test_service.calls

    def test_reset_clears_links_and_history(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        monkeypatch.setattr(controller, "_vector_engine_filters_targets", lambda: True)
        monkeypatch.setattr(controller, "_run_vector_source_filter", self._linking(controller))
        monkeypatch.setattr(controller, "_finish_restore", lambda ids: None)
        cleared = []
        ctrl_module._test_service.history = types.SimpleNamespace(clear_source=lambda sid: cleared.append(sid))
        controller.run_vector_source_task("filter", layers["v1"], ["r1"])
        controller.run_vector_source_task("reset", layers["v1"], ["r1"])
        assert cleared == ["v1"]
        controller.run_vector_source_task("undo", layers["v1"], [])
        assert ("undo", "v1") not in ctrl_module._test_service.calls

    def test_filter_without_coverage_targets_records_unlinked_run(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        ran = []
        monkeypatch.setattr(controller, "_run_vector_source_filter", lambda source, ids, run_index=None: ran.append(ids) or True)
        controller.run_vector_source_task("filter", layers["v1"], [])
        assert ran == [] and controller._linked_runs["v1"] == [False]

    def test_source_features_without_selection_warns(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        monkeypatch.setattr(controller, "_vector_source_features", lambda source: [])
        assert controller._run_vector_source_filter(layers["v1"], ["r1"]) is False
        assert ctrl_module._test_feedback.messages[-1][0] == "warning"


@pytest.mark.unit
class TestFilteringSettings:

    def test_reads_widgets_like_the_vector_engine(self, ctrl_module):
        predicates = MagicMock()
        predicates.checkedItems.return_value = ["Intersect", "Are within"]
        buffer_spin = MagicMock()
        buffer_spin.value.return_value = 2.5
        segments = MagicMock()
        segments.value.return_value = 8
        buffer_type = MagicMock()
        buffer_type.currentText.return_value = "Flat"
        source_op, other_op = MagicMock(), MagicMock()
        source_op.currentIndex.return_value = 0
        other_op.currentIndex.return_value = 2
        dock = _dock(
            pushButton_checkable_filtering_geometric_predicates=_checked(True),
            comboBox_filtering_geometric_predicates=predicates,
            pushButton_checkable_filtering_buffer_value=_checked(True),
            mQgsDoubleSpinBox_filtering_buffer_value=buffer_spin,
            pushButton_checkable_filtering_buffer_type=_checked(True),
            mQgsSpinBox_filtering_buffer_segments=segments,
            comboBox_filtering_buffer_type=buffer_type,
            pushButton_checkable_filtering_current_layer_combine_operator=_checked(True),
            comboBox_filtering_source_layer_combine_operator=source_op,
            comboBox_filtering_other_layers_combine_operator=other_op,
            pushButton_checkable_filtering_layers_to_filter=_checked(True),
        )
        dock._index_to_combine_operator = lambda index: ["AND", "AND NOT", "OR"][index]
        dock.get_layers_to_filter.return_value = ["v2", "r1"]
        controller = ctrl_module.CoverageModeController(dock)
        coverage = MagicMock()
        coverage.value.return_value = 50
        controller._coverage_spin = coverage
        settings = controller._filtering_settings()
        assert settings["predicates"] == ("Intersect", "Are within")
        assert settings["buffer_value"] == 2.5 and settings["buffer_segments"] == 8 and settings["buffer_type"] == "Flat"
        assert settings["source_operator"] == "AND" and settings["other_operator"] == "OR"
        assert settings["targets"] == ["v2", "r1"] and settings["coverage_min"] == 50.0

    def test_unchecked_groups_use_defaults(self, ctrl_module):
        dock = _dock(
            pushButton_checkable_filtering_geometric_predicates=_checked(False),
            pushButton_checkable_filtering_buffer_value=_checked(False),
            pushButton_checkable_filtering_buffer_type=_checked(False),
            pushButton_checkable_filtering_current_layer_combine_operator=_checked(False),
            pushButton_checkable_filtering_layers_to_filter=_checked(False),
        )
        controller = ctrl_module.CoverageModeController(dock)
        settings = controller._filtering_settings()
        assert settings["predicates"] == () and settings["buffer_value"] == 0.0
        assert settings["buffer_type"] == "Round" and settings["buffer_segments"] == 5
        assert settings["source_operator"] is None and settings["other_operator"] is None
        assert settings["targets"] == [] and settings["coverage_min"] == 0.0

    def test_target_specs_skip_source_and_unknown_layers(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        project = MagicMock()
        project.mapLayer.side_effect = lambda layer_id: layers.get(layer_id)
        qgis_core = sys.modules["qgis.core"]
        monkeypatch.setattr(qgis_core, "QgsProject", MagicMock(instance=MagicMock(return_value=project)), raising=False)
        specs = controller._target_specs(["r1", "v2", "o1", "missing", "p1"], exclude_id="p1")
        assert [(s.layer_id, s.kind.value) for s in specs] == [("r1", "raster"), ("v2", "vector")]


@pytest.mark.unit
class TestUndoRedoButtons:

    def test_buttons_follow_the_coverage_history(self, ctrl_module, layers):
        undo, redo = MagicMock(), MagicMock()
        dock = _dock(pushButton_action_undo_filter=undo, pushButton_action_redo_filter=redo)
        controller = ctrl_module.CoverageModeController(dock)
        controller._active_layer = layers["r1"]
        ctrl_module._test_service.undo_ok["r1"] = True
        controller.update_undo_redo_buttons()
        undo.setEnabled.assert_called_with(True)
        redo.setEnabled.assert_called_with(False)

    def test_inactive_controller_defers_to_the_app(self, ctrl_module):
        app = MagicMock()
        dock = _dock(filter_mate_app=app)
        controller = ctrl_module.CoverageModeController(dock)
        controller.update_undo_redo_buttons()
        app.update_undo_redo_buttons.assert_called_once()


@pytest.mark.unit
class TestFailuresCacheAndTeardown:

    def _outcome(self, ctrl_module, layer_id, message=""):
        from types import SimpleNamespace
        return SimpleNamespace(layer_id=layer_id, message=message, success=False)

    def test_failures_name_their_layer(self, ctrl_module, layers):
        controller = ctrl_module.CoverageModeController(_dock())
        text = controller._failure_text([self._outcome(ctrl_module, "r1", "pdal: no space left"),
                                         self._outcome(ctrl_module, "gone")])
        assert text == "r1: pdal: no space left; gone: failed"

    def test_failed_run_is_a_warning(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        for name in ("_refresh_canvas", "_refresh_counts", "update_undo_redo_buttons", "_schedule_cache_tidy"):
            monkeypatch.setattr(controller, name, lambda *a, **k: None)
        controller._after_run(layers["r1"], [], "1 target(s) filtered — 1 failed: p1: boom", warning=True)
        controller._after_run(layers["r1"], [], "2 target(s) filtered")
        assert [kind for kind, _ in ctrl_module._test_feedback.messages] == ["warning", "info"]

    def test_removed_layers_leave_every_history(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        tidies = []
        monkeypatch.setattr(controller, "_schedule_cache_tidy", lambda *a: tidies.append(a))
        controller._linked_runs["r1"] = [True]
        controller._on_layers_removed(["r1", "p1"])
        assert ctrl_module._test_service_module.calls == [("forget", "r1"), ("forget", "p1")]
        assert "r1" not in controller._linked_runs and tidies == [()]

    def test_project_cleared_clears_every_history(self, ctrl_module, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        monkeypatch.setattr(controller, "_schedule_cache_tidy", lambda *a: None)
        controller._on_project_cleared()
        assert ctrl_module._test_service_module.calls == [("clear_histories",)]

    def test_tidy_waits_for_running_tasks(self, ctrl_module, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        scheduled = []
        monkeypatch.setattr(controller, "_schedule_cache_tidy", lambda delay_ms=0: scheduled.append(delay_ms))
        ctrl_module._test_service_module.tidy_report = None  # a FilterMate task runs
        controller._tidy_cache()
        assert scheduled == [3000]

    def test_cache_over_limit_warns_once(self, ctrl_module, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        refreshed = []
        monkeypatch.setattr(controller, "update_undo_redo_buttons", lambda: refreshed.append(1))
        gb = 1024 ** 3
        over = {"size": 6 * gb, "limit": 5 * gb, "removed": 0, "dropped": []}
        ctrl_module._test_service_module.tidy_report = over
        controller._tidy_cache()
        controller._tidy_cache()
        warnings = [msg for kind, msg in ctrl_module._test_feedback.messages if kind == "warning"]
        assert len(warnings) == 1 and "6.0" in warnings[0] and "5.0" in warnings[0]
        ctrl_module._test_service_module.tidy_report = dict(over, size=gb)
        controller._tidy_cache()
        ctrl_module._test_service_module.tidy_report = over
        controller._tidy_cache()  # back over the limit later: warned again
        assert len([1 for kind, _ in ctrl_module._test_feedback.messages if kind == "warning"]) == 2
        assert refreshed == []

    def test_dropped_vector_step_unlinks_its_run(self, ctrl_module, monkeypatch):
        from types import SimpleNamespace
        controller = ctrl_module.CoverageModeController(_dock())
        refreshed = []
        monkeypatch.setattr(controller, "update_undo_redo_buttons", lambda: refreshed.append(1))
        controller._linked_runs["v1"] = [True, False, True]
        controller._linked_runs["v2"] = [True]
        step = SimpleNamespace(from_undo=True, operation=SimpleNamespace(source_layer_id="v1"))
        other_service = object()  # the automation history: its steps are not linked to the dock
        ctrl_module._test_service_module.tidy_report = {
            "size": 0, "limit": 0, "removed": 0,
            "dropped": [(ctrl_module._test_service, step), (other_service, step)]}
        controller._tidy_cache()
        assert controller._linked_runs == {"v1": [False, False, True], "v2": [True]}
        assert refreshed == [1]

    def test_teardown_cancels_export_and_height_tasks(self, ctrl_module, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        monkeypatch.setattr(controller, "deactivate", lambda: None)
        export, hag = MagicMock(), MagicMock()
        controller._export_task, controller._hag_task = export, hag
        controller.teardown()
        export.cancel.assert_called_once()
        hag.cancel.assert_called_once()
        assert controller._export_task is None and controller._hag_task is None


class FakeSignal:
    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def emit(self, *args):
        for slot in list(self.slots):
            slot(*args)


class StatsLayer(FakeLayer):
    class PointCloudStatisticsCalculationState:
        NotStarted, Calculating, Calculated = 0, 1, 2

    def __init__(self, layer_id):
        super().__init__(layer_id, "pc")
        self.statisticsCalculationStateChanged = FakeSignal()
        self.state = self.PointCloudStatisticsCalculationState.Calculating

    def statisticsCalculationState(self):
        return self.state


@pytest.mark.unit
class TestPointCloudStatisticsRefresh:
    def _controller(self, ctrl_module, layer, monkeypatch):
        ctrl = ctrl_module.CoverageModeController(_dock())
        ctrl._pc_panel = MagicMock()
        ctrl._active_layer = layer
        ctrl._kind = sys.modules[f"{_PKG}.core.domain.layer_kind"].LayerKind.POINT_CLOUD
        refreshed = []
        monkeypatch.setattr(ctrl, "_populate_point_cloud", lambda lyr, keep_kept=False: refreshed.append((lyr.id(), keep_kept)))
        return ctrl, refreshed

    def test_active_layer_refreshed_once_statistics_are_calculated(self, ctrl_module, monkeypatch):
        layer = StatsLayer("p1")
        ctrl, refreshed = self._controller(ctrl_module, layer, monkeypatch)
        ctrl._watch_point_cloud_statistics(layer)
        layer.statisticsCalculationStateChanged.emit(layer.state)
        assert refreshed == []  # still calculating
        layer.state = layer.PointCloudStatisticsCalculationState.Calculated
        layer.statisticsCalculationStateChanged.emit(layer.state)
        assert refreshed == [("p1", True)]  # the kept point count is kept

    def test_other_layer_ignored(self, ctrl_module, monkeypatch):
        active, other = StatsLayer("p1"), StatsLayer("p2")
        ctrl, refreshed = self._controller(ctrl_module, active, monkeypatch)
        ctrl._watch_point_cloud_statistics(other)
        other.state = other.PointCloudStatisticsCalculationState.Calculated
        other.statisticsCalculationStateChanged.emit(other.state)
        assert refreshed == []

    def test_connected_once_per_layer(self, ctrl_module, monkeypatch):
        layer = StatsLayer("p1")
        ctrl, _ = self._controller(ctrl_module, layer, monkeypatch)
        ctrl._watch_point_cloud_statistics(layer)
        ctrl._watch_point_cloud_statistics(layer)
        assert len(layer.statisticsCalculationStateChanged.slots) == 1
