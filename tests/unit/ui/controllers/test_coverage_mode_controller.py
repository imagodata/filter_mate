# -*- coding: utf-8 -*-
"""
CoverageModeController (FilterMate 5): raster / point cloud source mode and
coverage targets of vector sources.

The controller is loaded by path under a private synthetic package where
BaseController, the capability module, the cross filter service and the
feedback helpers are stubs; the pure domain modules are the real ones.
"""
import importlib.util
import inspect
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

    def source(self):
        return f"/data/{self._id}"

    def subsetString(self):
        return self._subset

    def setSubsetString(self, value):
        self._subset = value
        return True


class FakeService:
    """CrossFilterService stand-in: real history (pure domain), recorded calls."""

    def __init__(self, history):
        self.calls = []
        self.undo_ok = {}
        self.redo_ok = {}
        self.history = history

    def unfilter(self, source_id, ids, kinds, record=True):
        self.calls.append(("unfilter", source_id, tuple(ids)))
        return list(ids)

    def undo(self, source_id):
        self.calls.append(("undo", source_id))
        self.history.undo(source_id)
        return [source_id]

    def redo(self, source_id):
        self.calls.append(("redo", source_id))
        self.history.redo(source_id)
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
    filter_state = _load_real("core.domain.filter_state", "core/domain/filter_state.py")
    capability = types.ModuleType(f"{_PKG}.adapters.qgis.point_cloud_capability")
    kinds = {"vector": layer_kind.LayerKind.VECTOR, "raster": layer_kind.LayerKind.RASTER,
             "pc": layer_kind.LayerKind.POINT_CLOUD}
    capability.get_layer_kind = lambda layer: kinds.get(getattr(layer, "kind", None), layer_kind.LayerKind.OTHER)
    monkeypatch.setitem(sys.modules, capability.__name__, capability)
    service = FakeService(filter_state.CrossOperationHistory())
    service_module = types.ModuleType(f"{_PKG}.core.services.cross_filter_service")
    service_module.get_cross_filter_service = lambda: service
    service_module.calls = []
    service_module.clear_histories = lambda: service_module.calls.append(("clear_histories",))

    def forget_layer_everywhere(layer_id):
        service_module.calls.append(("forget", layer_id))
        service.history.forget_layer(layer_id)

    service_module.forget_layer_everywhere = forget_layer_everywhere
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
    module._test_filter_state = filter_state
    module._test_layer_kind = layer_kind
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
        controller = ctrl_module.CoverageModeController(_dock(PROJECT_LAYERS={"r1": {}, "p1": {}}))
        activated = []
        monkeypatch.setattr(controller, "_ensure_host", lambda: True)
        monkeypatch.setattr(controller, "activate", lambda layer, kind: activated.append((layer.id(), kind.value)))
        assert controller.on_current_layer_changed(layers["r1"]) is True
        assert controller.on_current_layer_changed(layers["p1"]) is True
        assert activated == [("r1", "raster"), ("p1", "point_cloud")]

    def test_missing_panels_fall_back_to_vector_chain(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock(PROJECT_LAYERS={"r1": {}}))
        monkeypatch.setattr(controller, "_ensure_host", lambda: False)
        assert controller.on_current_layer_changed(layers["r1"]) is False

    def _awaiting(self, ctrl_module, layers, monkeypatch):
        """2026-10-17: a raster picked before add_layers registered it."""
        dock = _dock(PROJECT_LAYERS={})
        controller = ctrl_module.CoverageModeController(dock)
        activated = []
        monkeypatch.setattr(controller, "_ensure_host", lambda: True)
        monkeypatch.setattr(controller, "activate", lambda layer, kind: activated.append(layer.id()))
        project = MagicMock()
        project.mapLayer.side_effect = lambda layer_id: layers.get(layer_id)
        monkeypatch.setattr(sys.modules["qgis.core"], "QgsProject",
                            MagicMock(instance=MagicMock(return_value=project)), raising=False)
        return dock, controller, activated

    def test_an_unregistered_raster_waits_for_its_registration(self, ctrl_module, layers, monkeypatch):
        dock, controller, activated = self._awaiting(ctrl_module, layers, monkeypatch)
        assert controller.on_current_layer_changed(layers["r1"], manual_change=True) is True  # vector chain stops
        assert activated == []
        assert controller.activate_awaited_layer() is False  # not registered yet: still waiting
        dock.PROJECT_LAYERS["v1"] = {}
        # the dock's refresh after add_layers shows the previous (vector) layer: no user pick, the wait stays
        controller.on_current_layer_changed(layers["v1"], manual_change=False)
        dock.PROJECT_LAYERS["r1"] = {}  # add_layers registered it
        assert controller.activate_awaited_layer() is True
        assert activated == ["r1"]
        assert controller.activate_awaited_layer() is False  # once
        assert activated == ["r1"]

    def test_another_pick_cancels_the_wait(self, ctrl_module, layers, monkeypatch):
        dock, controller, activated = self._awaiting(ctrl_module, layers, monkeypatch)
        controller.on_current_layer_changed(layers["r1"], manual_change=True)
        dock.PROJECT_LAYERS["v1"] = {}
        controller.on_current_layer_changed(layers["v1"], manual_change=True)  # the user picked a vector layer
        dock.PROJECT_LAYERS["r1"] = {}
        assert controller.activate_awaited_layer() is False
        assert activated == []

    def test_the_refresh_button_action_no_longer_activates(self, ctrl_module, layers, monkeypatch):
        """The dock's delegate skipped the action without an active layer: the wait never ended there."""
        dock, controller, activated = self._awaiting(ctrl_module, layers, monkeypatch)
        controller.on_current_layer_changed(layers["r1"], manual_change=True)
        dock.PROJECT_LAYERS["r1"] = {}
        assert controller.handle_exploring_action("refresh") is False
        assert activated == []

    def test_leaving_coverage_layer_deactivates(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock(PROJECT_LAYERS={"v1": {}}))
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
    def _linking(ctrl_module, controller, changed=True):
        """Stand-in for _run_vector_source_filter: the cross task changed the targets (or not).

        Like the service, a task with changes records one operation (one change per target).
        """
        filter_state = ctrl_module._test_filter_state

        def fake(source, ids, run=None):
            if changed:
                operation = filter_state.CrossOperation(source.id(), tuple(
                    (filter_state.LayerSnapshot(i, "raster", source="/a"),
                     filter_state.LayerSnapshot(i, "raster", source="/b")) for i in ids))
                controller.service.history.push(operation)
                run.op_id = operation.op_id
            return True
        return fake

    def test_undo_redo_follow_linked_runs(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        monkeypatch.setattr(controller, "_vector_engine_filters_targets", lambda: True)
        monkeypatch.setattr(controller, "_run_vector_source_filter", self._linking(ctrl_module, controller))
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
        monkeypatch.setattr(controller, "_run_vector_source_filter", self._linking(ctrl_module, controller, changed=False))
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
        assert ran == [] and [run.op_id for run in controller._linked_runs["v1"]] == [None]

    def test_unfilter_keeps_links_like_the_vector_history(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        monkeypatch.setattr(controller, "_vector_engine_filters_targets", lambda: True)
        monkeypatch.setattr(controller, "_run_vector_source_filter", self._linking(ctrl_module, controller))
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
        monkeypatch.setattr(controller, "_run_vector_source_filter", self._linking(ctrl_module, controller))
        monkeypatch.setattr(controller, "_finish_restore", lambda ids: None)
        controller.run_vector_source_task("filter", layers["v1"], ["r1"])
        assert ctrl_module._test_service.history.can_undo("v1")
        controller.run_vector_source_task("reset", layers["v1"], ["r1"])
        assert not ctrl_module._test_service.history.can_undo("v1")
        controller.run_vector_source_task("undo", layers["v1"], [])
        assert ("undo", "v1") not in ctrl_module._test_service.calls

    def test_filter_without_coverage_targets_records_unlinked_run(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        ran = []
        monkeypatch.setattr(controller, "_run_vector_source_filter", lambda source, ids, run=None: ran.append(ids) or True)
        controller.run_vector_source_task("filter", layers["v1"], [])
        assert ran == [] and [run.op_id for run in controller._linked_runs["v1"]] == [None]

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
        dock = _dock(pushButton_action_undo_filter=undo, pushButton_action_redo_filter=redo, tabTools_current_index=0)
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
        controller._linked_runs["r1"] = [ctrl_module._LinkedRun(1)]
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
        run = ctrl_module._LinkedRun
        controller._linked_runs["v1"] = [run(11), run(None), run(12)]
        controller._linked_runs["v2"] = [run(13)]
        step = SimpleNamespace(from_undo=True, operation=SimpleNamespace(source_layer_id="v1", op_id=11))
        other_service = object()  # the automation history: its steps are not linked to the dock
        ctrl_module._test_service_module.tidy_report = {
            "size": 0, "limit": 0, "removed": 0,
            "dropped": [(ctrl_module._test_service, step), (other_service, step)]}
        controller._tidy_cache()
        assert {sid: [r.op_id for r in runs] for sid, runs in controller._linked_runs.items()} == \
            {"v1": [None, None, 12], "v2": [13]}
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

    def disconnect(self, slot):
        if slot not in self.slots:
            raise TypeError("not connected")
        self.slots.remove(slot)

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

    def test_teardown_disconnects_the_statistics_signal(self, ctrl_module, monkeypatch):
        """2026-10-17: the lambda stayed connected: the layer called the controller of an unloaded dock."""
        layer = StatsLayer("p1")
        ctrl, _ = self._controller(ctrl_module, layer, monkeypatch)
        ctrl._watch_point_cloud_statistics(layer)
        ctrl._disconnect_point_cloud_statistics()
        assert layer.statisticsCalculationStateChanged.slots == []
        ctrl._watch_point_cloud_statistics(layer)  # watched again once set up again
        assert len(layer.statisticsCalculationStateChanged.slots) == 1
        assert "_disconnect_point_cloud_statistics" in inspect.getsource(type(ctrl).teardown)


# ---------------------------------------------------------------------------
# Audit fixes (FilterMate 5): layer switches, previews, lifecycle, history links
# ---------------------------------------------------------------------------

def _kind(ctrl_module, name):
    return getattr(ctrl_module._test_layer_kind.LayerKind, name)


def _unchecked(widget):
    return [call for call in widget.setChecked.call_args_list if call.args == (False,)]


class FakeQgsTask:
    class TaskStatus:
        Queued, OnHold, Running, Complete, Terminated = range(5)


class RunningTask:
    def __init__(self, status=FakeQgsTask.TaskStatus.Running):
        self._status = status

    def status(self):
        return self._status


def _value_panel():
    """Raster panel mock whose range applies to the pixel value (no terrain derivative)."""
    panel = MagicMock()
    panel.current_derivative.return_value = types.SimpleNamespace(is_terrain=False, value="value")
    return panel


@pytest.fixture
def adapters(monkeypatch, ctrl_module):
    """Stub ``adapters.qgis.coverage_layers`` modules (raster preview, snapshots) recording their calls."""
    package = types.ModuleType(f"{_PKG}.adapters.qgis.coverage_layers")
    package.__path__ = []
    monkeypatch.setitem(sys.modules, package.__name__, package)
    calls = []
    raster = types.ModuleType(f"{package.__name__}.raster_adapter")
    raster.apply_selection_preview = lambda layer, selection, low=None, high=None: calls.append(
        ("apply", layer.id(), low, high))
    raster.clear_selection_preview = lambda layer: calls.append(("clear", layer.id()))
    raster.band_histogram = lambda layer, band, bins=64: calls.append(("histogram", band)) or ([1, 1], 0.0, 10.0)
    raster.derivative_histogram = lambda layer, band, derivative, bins=64: calls.append(
        ("derivative_histogram", band, derivative.value)) or ([2, 1], 0.0, 90.0)
    snapshots = types.ModuleType(f"{package.__name__}.snapshots")
    snapshots.derived = {}
    snapshots.registry = lambda: types.SimpleNamespace(get=snapshots.derived.get, install=lambda *a: None)
    snapshots.take_snapshot = lambda layer, kind: ctrl_module._test_filter_state.LayerSnapshot(
        layer.id(), kind.value, source=layer.source(), subset=layer.subsetString())
    for module in (raster, snapshots):
        monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsTask", FakeQgsTask, raising=False)
    return types.SimpleNamespace(calls=calls, package=package, snapshots=snapshots, raster=raster)


@pytest.mark.unit
class TestHeightAboveGroundLayerSwitch:
    """Constats 1 / 10: the HAG callback and its retry stay on the layer they were started for."""

    @pytest.fixture
    def hag(self, monkeypatch, ctrl_module, adapters):
        module = types.ModuleType(f"{adapters.package.__name__}.hag_task")
        filter_state = ctrl_module._test_filter_state

        class Task:
            def __init__(self, layer, dem):
                self.done = FakeSignal()
                self.before = filter_state.LayerSnapshot(layer.id(), "point_cloud", source="/p1.laz")
                self.after = filter_state.LayerSnapshot(layer.id(), "point_cloud", source="/p1_hag.copc.laz")
                module.created.append(self)

        module.HeightAboveGroundTask = Task
        module.created = []
        monkeypatch.setitem(sys.modules, module.__name__, module)
        return module

    def _controller(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock(tabTools_current_index=0))
        controller._active_layer, controller._kind = layers["p1"], _kind(ctrl_module, "POINT_CLOUD")
        populated = []
        monkeypatch.setattr(controller, "_populate_point_cloud", lambda layer, keep_kept=False: populated.append(layer.id()))
        monkeypatch.setattr(controller, "_schedule_cache_tidy", lambda *a: None)
        return controller, populated

    def test_layer_switched_during_the_computation_gets_neither_populate_nor_filter(
            self, ctrl_module, layers, hag, monkeypatch):
        controller, populated = self._controller(ctrl_module, layers, monkeypatch)
        layers["dem"] = FakeLayer("dem", "raster")
        ran = []
        controller._prepare_height_above_ground(layers["p1"], ("dem", 2.0), lambda: ran.append("filter"))
        controller._active_layer, controller._kind = layers["r1"], _kind(ctrl_module, "RASTER")  # user picked r1
        hag.created[0].done.emit(True, "")
        assert ran == [] and populated == []
        assert ctrl_module._test_service.history.can_undo("p1")  # the computed height stays undoable
        assert ctrl_module._test_feedback.messages[-1] == ("warning", "Filter not applied: {0}".format("p1"))

    def test_same_layer_continues_with_the_filter(self, ctrl_module, layers, hag, monkeypatch):
        controller, populated = self._controller(ctrl_module, layers, monkeypatch)
        layers["dem"] = FakeLayer("dem", "raster")
        ran = []
        controller._prepare_height_above_ground(layers["p1"], ("dem", 2.0), lambda: ran.append("filter"))
        hag.created[0].done.emit(True, "")
        assert ran == ["filter"] and populated == ["p1"]

    def test_height_computed_once_even_without_the_dimension(self, ctrl_module, layers, adapters, monkeypatch):
        controller, _ = self._controller(ctrl_module, layers, monkeypatch)
        controller._pc_panel = MagicMock()
        controller._pc_panel.hag_settings.return_value = ("dem", 2.0)
        controller._pc_panel.expression.return_value = "HeightAboveGround >= 2"
        monkeypatch.setattr(controller, "_filtering_settings", lambda: dict(targets=[], source_operator=None))
        monkeypatch.setattr(controller, "_build_request", lambda *a: object())
        monkeypatch.setattr(controller, "_point_cloud_attributes", lambda layer: ["X", "Y", "Z"])  # PDAL wrote no HAG
        prepared = []
        monkeypatch.setattr(controller, "_prepare_height_above_ground",
                            lambda layer, hag, then: prepared.append(then) or then())
        controller._run_filter(layers["p1"])
        assert len(prepared) == 1  # the retry does not start PDAL again
        assert ctrl_module._test_feedback.messages[-1][0] == "warning"

    def test_height_computation_blocks_undo_and_unfilter(self, ctrl_module, layers, adapters):
        controller = ctrl_module.CoverageModeController(_dock(current_layer=layers["p1"]))
        controller._active_layer = layers["p1"]
        controller._hag_task = RunningTask()
        assert controller.is_running()
        controller.handle_task("undo")
        controller.handle_task("unfilter")
        assert ctrl_module._test_service.calls == []
        controller._hag_task = RunningTask(FakeQgsTask.TaskStatus.Complete)
        assert not controller.is_running()


@pytest.mark.unit
class TestPreviewStopsBeforeHistory:
    """Constat 2: the live preview never makes Undo / Redo skip the point cloud."""

    def test_undo_removes_the_point_cloud_preview_first(self, ctrl_module, adapters):
        selecting = MagicMock()
        layer = FakeLayer("p1", "pc", subset="(Classification = 2) AND (Z > 300)")
        controller = ctrl_module.CoverageModeController(_dock(current_layer=layer,
                                                              pushButton_checkable_exploring_selecting=selecting))
        controller._active_layer, controller._kind = layer, _kind(ctrl_module, "POINT_CLOUD")
        controller._preview_base_subset = "Classification = 2"
        seen = []
        ctrl_module._test_service.undo = lambda source_id: seen.append(layer.subsetString()) or []
        controller.handle_task("undo")
        assert seen == ["Classification = 2"]  # the state the history recorded
        assert _unchecked(selecting)  # the preview does not come back at the next input change
        assert controller._preview_base_subset is None

    def test_stopped_raster_preview_unchecks_the_button_and_the_box(self, ctrl_module, layers, adapters):
        selecting = MagicMock()
        controller = ctrl_module.CoverageModeController(_dock(pushButton_checkable_exploring_selecting=selecting))
        controller._active_layer, controller._kind = layers["r1"], _kind(ctrl_module, "RASTER")
        controller._raster_panel = _value_panel()
        controller._preview_active = True
        controller._stop_preview(layers["r1"])
        assert ("clear", "r1") in adapters.calls
        assert _unchecked(selecting)
        controller._raster_panel.set_preview_checked.assert_called_with(False)
        assert not controller._preview_active


@pytest.mark.unit
class TestReactivation:
    """Constat 5: activating the shown layer again keeps its input and its preview."""

    def _controller(self, ctrl_module, monkeypatch):
        selecting = MagicMock()
        controller = ctrl_module.CoverageModeController(_dock(pushButton_checkable_exploring_selecting=selecting))
        for name in ("_show_kind_badge", "_extras_call", "_populate_raster", "_sync_layer_combo",
                     "_populate_filtering_targets", "_load_coverage_min", "_save_dock_state", "update_undo_redo_buttons"):
            monkeypatch.setattr(controller, name, lambda *a, **k: None)
        controller._raster_panel = _value_panel()
        return controller, selecting

    def test_same_layer_is_not_restored_from_an_older_input(self, ctrl_module, layers, adapters, monkeypatch):
        controller, selecting = self._controller(ctrl_module, monkeypatch)
        raster = _kind(ctrl_module, "RASTER")
        controller._active_layer, controller._kind = layers["r1"], raster
        controller._panel_states["r1"] = {"mode": "range", "minimum": 1.0}  # saved when r1 was left earlier
        controller.activate(layers["r1"], raster)
        controller._raster_panel.restore_state.assert_not_called()
        assert _unchecked(selecting) == []  # the preview button stays as it is

    def test_another_layer_gets_its_input_and_its_preview_back(self, ctrl_module, layers, adapters, monkeypatch):
        controller, selecting = self._controller(ctrl_module, monkeypatch)
        raster = _kind(ctrl_module, "RASTER")
        layers["r2"] = FakeLayer("r2", "raster")
        controller._active_layer, controller._kind = layers["r2"], raster
        state = {"mode": "range", "minimum": 1.0, "preview": True}
        controller._panel_states["r1"] = state
        controller._raster_panel.selection.return_value = types.SimpleNamespace(
            derivative=types.SimpleNamespace(is_terrain=False))
        controller.activate(layers["r1"], raster)
        controller._raster_panel.restore_state.assert_called_once_with(state)
        selecting.setChecked.assert_called_with(True)
        assert ("apply", "r1", None, None) in adapters.calls


@pytest.mark.unit
class TestLayerLifecycle:
    """Constats 6, 9, 11: removed layers and closed projects."""

    def test_removed_active_layer_deactivates_before_its_input_is_forgotten(self, ctrl_module, layers, adapters, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        monkeypatch.setattr(controller, "_schedule_cache_tidy", lambda *a: None)
        controller._active_layer, controller._kind = layers["r1"], _kind(ctrl_module, "RASTER")
        controller._raster_panel = _value_panel()
        controller._raster_panel.state.return_value = {"mode": "range"}
        controller._on_layers_removed(["r1"])
        assert controller.active_layer is None
        assert "r1" not in controller._panel_states  # not put back by leaving the layer

    def test_other_removed_layer_keeps_the_mode(self, ctrl_module, layers, adapters, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        monkeypatch.setattr(controller, "_schedule_cache_tidy", lambda *a: None)
        controller._active_layer = layers["r1"]
        controller._on_layers_removed(["p1"])
        assert controller.active_layer is layers["r1"]

    def test_closed_project_deactivates(self, ctrl_module, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        monkeypatch.setattr(controller, "_schedule_cache_tidy", lambda *a: None)
        calls = []
        monkeypatch.setattr(controller, "deactivate", lambda: calls.append("deactivate"))
        controller._on_project_cleared()
        assert calls == ["deactivate"]

    def test_statistics_are_watched_again_after_the_project_is_opened_again(self, ctrl_module, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        monkeypatch.setattr(controller, "_schedule_cache_tidy", lambda *a: None)
        controller._watch_point_cloud_statistics(StatsLayer("p1"))
        controller._on_project_cleared()
        reopened = StatsLayer("p1")  # same id, new layer
        controller._watch_point_cloud_statistics(reopened)
        assert len(reopened.statisticsCalculationStateChanged.slots) == 1
        controller._on_layers_removed(["p1"])
        added_again = StatsLayer("p1")
        controller._watch_point_cloud_statistics(added_again)
        assert len(added_again.statisticsCalculationStateChanged.slots) == 1

    def test_deleted_active_layer_has_no_undo(self, ctrl_module):
        class Deleted:
            def id(self):
                raise RuntimeError("wrapped C/C++ object of type QgsRasterLayer has been deleted")

        controller = ctrl_module.CoverageModeController(_dock())
        controller._active_layer = Deleted()
        assert controller.can_undo() is False and controller.can_redo() is False

    def test_pixel_picker_released_when_the_previous_tool_is_gone(self, ctrl_module):
        canvas = MagicMock()
        tool = object()
        canvas.mapTool.return_value = tool
        canvas.setMapTool.side_effect = RuntimeError("wrapped C/C++ object has been deleted")
        app = MagicMock()
        app.iface.mapCanvas.return_value = canvas
        controller = ctrl_module.CoverageModeController(_dock(filter_mate_app=app))
        controller._pixel_tool, controller._previous_map_tool = tool, object()
        controller._deactivate_pixel_tool()  # no exception
        canvas.unsetMapTool.assert_called_once_with(tool)
        assert controller._previous_map_tool is None

    def test_leaving_a_layer_deletes_its_pickers(self, ctrl_module, layers, adapters, monkeypatch):
        # QGIS gives the last tool back after Pan: the raster picker must not come back on a point cloud.
        controller = ctrl_module.CoverageModeController(_dock())
        controller._active_layer, controller._kind = layers["r1"], _kind(ctrl_module, "RASTER")
        controller._raster_panel = _value_panel()
        pixel, cls = MagicMock(), MagicMock()
        controller._pixel_tool, controller._class_tool = pixel, cls
        controller._leave_layer()
        pixel.deleteLater.assert_called_once_with()
        cls.deleteLater.assert_called_once_with()
        assert controller._pixel_tool is None and controller._class_tool is None

    def test_pixel_pick_ignored_on_a_point_cloud(self, ctrl_module, layers):
        controller = ctrl_module.CoverageModeController(_dock())
        controller._active_layer, controller._kind = layers["p1"], _kind(ctrl_module, "POINT_CLOUD")
        controller._raster_panel = _value_panel()
        controller._on_pixel_picked(object(), False)
        controller._raster_panel.set_pixel_values.assert_not_called()

    def test_setup_connects_the_project_signals_once(self, ctrl_module, monkeypatch):
        project = types.SimpleNamespace(readProject=FakeSignal(), cleared=FakeSignal(), layersWillBeRemoved=FakeSignal())
        monkeypatch.setattr(sys.modules["qgis.core"], "QgsProject",
                            types.SimpleNamespace(instance=lambda: project), raising=False)
        controller = ctrl_module.CoverageModeController(_dock())
        controller.setup()
        controller.setup()
        assert [len(s.slots) for s in (project.readProject, project.cleared, project.layersWillBeRemoved)] == [1, 1, 1]

    def test_setup_retries_a_failed_connection_without_doubling_the_others(self, ctrl_module, monkeypatch):
        class FlakySignal(FakeSignal):
            failures = 1

            def connect(self, slot):
                if self.failures:
                    self.failures -= 1
                    raise TypeError("not ready")
                super().connect(slot)

        project = types.SimpleNamespace(readProject=FakeSignal(), cleared=FlakySignal(), layersWillBeRemoved=FakeSignal())
        monkeypatch.setattr(sys.modules["qgis.core"], "QgsProject",
                            types.SimpleNamespace(instance=lambda: project), raising=False)
        controller = ctrl_module.CoverageModeController(_dock())
        controller.setup()
        assert [len(s.slots) for s in (project.readProject, project.cleared, project.layersWillBeRemoved)] == [1, 0, 1]
        controller.setup()
        assert [len(s.slots) for s in (project.readProject, project.cleared, project.layersWillBeRemoved)] == [1, 1, 1]

    def _removal(self, ctrl_module, layers, monkeypatch, current):
        dock = _dock(current_layer=current)
        controller = ctrl_module.CoverageModeController(dock)
        monkeypatch.setattr(controller, "_schedule_cache_tidy", lambda *a: None)
        controller._active_layer, controller._kind = layers["r1"], _kind(ctrl_module, "RASTER")
        controller._extras = object()  # the dock additions exist
        extras = []
        monkeypatch.setattr(controller, "_extras_call", lambda method, *a: extras.append((method,) + a))
        return controller, dock, extras

    def test_removed_active_layer_brings_the_vector_rail_back(self, ctrl_module, layers, adapters, monkeypatch):
        controller, dock, extras = self._removal(ctrl_module, layers, monkeypatch, current=layers["r1"])
        controller._on_layers_removed(["r1"])
        assert extras == [("forget_layers", ["r1"]), ("show_vector", None)]  # no raster tool, no stale card
        assert dock.current_layer is None  # Filter would read a deleted layer

    def test_other_removed_layer_leaves_the_dock_alone(self, ctrl_module, layers, adapters, monkeypatch):
        controller, dock, extras = self._removal(ctrl_module, layers, monkeypatch, current=layers["r1"])
        controller._on_layers_removed(["p1"])
        assert extras == [("forget_layers", ["p1"])]
        assert dock.current_layer is layers["r1"] and controller.active_layer is layers["r1"]

    def test_closed_project_brings_the_vector_rail_back(self, ctrl_module, layers, adapters, monkeypatch):
        controller, dock, extras = self._removal(ctrl_module, layers, monkeypatch, current=layers["r1"])
        controller._on_project_cleared()
        assert extras == [("forget_layers", None), ("show_vector", None)]
        assert dock.current_layer is None and controller.active_layer is None

    def test_histories_are_forgotten_even_when_leaving_the_layer_fails(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        monkeypatch.setattr(controller, "_schedule_cache_tidy", lambda *a: None)

        def broken():
            raise ValueError("panel already deleted")

        monkeypatch.setattr(controller, "deactivate", broken)
        controller._active_layer = layers["r1"]
        controller._on_layers_removed(["r1"])
        controller._on_project_cleared()
        assert ctrl_module._test_service_module.calls == [("forget", "r1"), ("clear_histories",)]

    def test_preview_button_signals_unblocked_when_checking_fails(self, ctrl_module):
        selecting = MagicMock()
        selecting.setChecked.side_effect = TypeError("unexpected")
        controller = ctrl_module.CoverageModeController(_dock(pushButton_checkable_exploring_selecting=selecting))
        with pytest.raises(TypeError):
            controller._set_selecting_checked(False)
        assert selecting.blockSignals.call_args_list[-1].args == (False,)


@pytest.mark.unit
class TestLinkedRunsAfterLayerRemoval:
    """Constat 11: a removed target never makes Undo of a vector source restore the wrong step."""

    def _controller(self, ctrl_module, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        monkeypatch.setattr(controller, "_vector_engine_filters_targets", lambda: True)
        monkeypatch.setattr(controller, "_run_vector_source_filter",
                            TestVectorSourceTargets._linking(ctrl_module, controller))
        monkeypatch.setattr(controller, "_finish_restore", lambda ids: None)
        monkeypatch.setattr(controller, "_schedule_cache_tidy", lambda *a: None)
        return controller

    def test_undo_restores_the_targets_left_by_the_removed_one(self, ctrl_module, layers, monkeypatch):
        controller = self._controller(ctrl_module, monkeypatch)
        history = ctrl_module._test_service.history
        controller.run_vector_source_task("filter", layers["v1"], ["r2"])        # run 1 clips r2
        first = history.peek_undo("v1")
        controller.run_vector_source_task("filter", layers["v1"], ["r1", "r2"])  # run 2 clips r1 and r2
        second = history.peek_undo("v1")
        controller._on_layers_removed(["r1"])
        controller.run_vector_source_task("undo", layers["v1"], [])
        assert ctrl_module._test_service.calls == [("undo", "v1")]
        assert history.peek_redo("v1").op_id == second.op_id
        assert history.peek_redo("v1").layer_ids == ("r2",)  # r2 goes back to run 1's clip
        assert history.peek_undo("v1") is first

    def test_operation_of_the_removed_layer_alone_is_not_replaced_by_an_older_one(self, ctrl_module, layers, monkeypatch):
        controller = self._controller(ctrl_module, monkeypatch)
        controller.run_vector_source_task("filter", layers["v1"], ["r2"])  # run 1 clips r2
        controller.run_vector_source_task("filter", layers["v1"], ["r1"])  # run 2 clips r1 only
        controller._on_layers_removed(["r1"])
        controller.run_vector_source_task("undo", layers["v1"], [])        # undoes run 2: nothing left of it
        assert ctrl_module._test_service.calls == []
        controller.run_vector_source_task("undo", layers["v1"], [])        # run 1
        assert ctrl_module._test_service.calls == [("undo", "v1")]

    def test_cross_task_records_its_operation_on_the_run(self, ctrl_module, layers, adapters, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        jobs = types.ModuleType(f"{adapters.package.__name__}.source_jobs")
        jobs.VectorSourceJob = lambda source, features: object()
        monkeypatch.setitem(sys.modules, jobs.__name__, jobs)
        monkeypatch.setattr(controller, "_vector_source_features", lambda source: ["feature"])
        monkeypatch.setattr(controller, "_target_specs", lambda ids, exclude_id="": ids)
        monkeypatch.setattr(controller, "_filtering_settings", lambda: {})
        monkeypatch.setattr(controller, "_build_request", lambda *a: object())
        monkeypatch.setattr(controller, "_after_run", lambda *a, **k: None)
        callbacks = []
        ctrl_module._test_service.run = lambda request, job, on_done=None: callbacks.append(on_done)
        run = ctrl_module._LinkedRun()
        assert controller._run_vector_source_filter(layers["v1"], ["r1"], run=run)
        filter_state = ctrl_module._test_filter_state
        changes = ((filter_state.LayerSnapshot("r1", "raster", source="/a"),
                    filter_state.LayerSnapshot("r1", "raster", source="/b")),)
        operation = filter_state.CrossOperation("v1", changes)
        ctrl_module._test_service.history.push(operation)  # what the service records before calling back
        callbacks[0](types.SimpleNamespace(changes=list(changes), outcomes=[], error=""), True)
        assert run.op_id == operation.op_id


@pytest.mark.unit
class TestVectorSourceTaskRunning:
    """While the cross task of a vector source runs, no other task of that source may start:
    its operation would land on a run already undone or thrown away."""

    def _start(self, ctrl_module, layers, adapters, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        jobs = types.ModuleType(f"{adapters.package.__name__}.source_jobs")
        jobs.VectorSourceJob = lambda source, features: object()
        monkeypatch.setitem(sys.modules, jobs.__name__, jobs)
        for name, value in (("_vector_source_features", lambda source: ["feature"]),
                            ("_target_specs", lambda ids, exclude_id="": ids), ("_filtering_settings", lambda: {}),
                            ("_build_request", lambda *a: object()), ("_after_run", lambda *a, **k: None)):
            monkeypatch.setattr(controller, name, value)
        # The CrossFilterTask: service.run returns it, and it calls on_done(itself, result).
        task = types.SimpleNamespace(taskCompleted=FakeSignal(), taskTerminated=FakeSignal(),
                                     changes=[], outcomes=[], error="")
        callbacks = []
        ctrl_module._test_service.run = lambda request, job, on_done=None: callbacks.append(on_done) or task
        run = ctrl_module._LinkedRun()
        controller._run_vector_source_filter(layers["v1"], ["r1"], run=run)
        return controller, task, callbacks[0], run

    def test_source_is_busy_until_its_task_is_done(self, ctrl_module, layers, adapters, monkeypatch):
        controller, task, done, _ = self._start(ctrl_module, layers, adapters, monkeypatch)
        assert controller.vector_source_busy(layers["v1"])
        assert ctrl_module._test_feedback.messages[-1] == (
            "warning", "A FilterMate task is still running: wait for it to finish")
        assert not controller.vector_source_busy(layers["v2"])
        done(task, True)
        assert not controller.vector_source_busy(layers["v1"])

    def test_a_failed_callback_does_not_block_the_source(self, ctrl_module, layers, adapters, monkeypatch):
        controller, task, _, _ = self._start(ctrl_module, layers, adapters, monkeypatch)
        task.taskCompleted.emit()  # QGIS signal, also emitted when done() was never reached
        assert not controller.vector_source_busy(layers["v1"])

    def test_operation_of_a_source_removed_meanwhile_is_forgotten(self, ctrl_module, layers, adapters, monkeypatch):
        controller, task, done, run = self._start(ctrl_module, layers, adapters, monkeypatch)
        filter_state = ctrl_module._test_filter_state
        task.changes = [(filter_state.LayerSnapshot("r1", "raster", source="/a"),
                         filter_state.LayerSnapshot("r1", "raster", source="/b"))]
        ctrl_module._test_service.history.push(filter_state.CrossOperation("v1", tuple(task.changes)))
        del layers["v1"]  # removed from the project while the task ran
        done(task, True)
        assert not controller.vector_source_busy(layers["v2"])
        assert not ctrl_module._test_service.history.can_undo("v1") and run.op_id is None


@pytest.mark.unit
class TestTaskResultOfAnotherLayer:
    """Constat 8: a task ending after a layer switch leaves the panel and the Filter button alone."""

    def test_counts_of_another_layer_do_not_reach_the_panel(self, ctrl_module, layers):
        controller = ctrl_module.CoverageModeController(_dock())
        layers["p2"] = FakeLayer("p2", "pc")
        controller._active_layer, controller._kind = layers["p2"], _kind(ctrl_module, "POINT_CLOUD")
        controller._pc_panel = MagicMock()
        controller._refresh_counts(layers["p1"])
        controller._pc_panel.set_current_subset.assert_not_called()
        controller._refresh_counts(layers["p2"])
        controller._pc_panel.set_current_subset.assert_called_once()

    def test_filter_button_stays_disabled_while_another_task_runs(self, ctrl_module, adapters):
        button = MagicMock()
        controller = ctrl_module.CoverageModeController(_dock(pushButton_action_filter=button))
        controller._hag_task = RunningTask()
        controller._set_busy(False)
        button.setEnabled.assert_called_with(False)
        controller._hag_task = None
        controller._set_busy(False)
        button.setEnabled.assert_called_with(True)


@pytest.mark.unit
class TestRasterPreviewFollowsTheSelection:
    """Constat 7: an empty selection shows every pixel again."""

    def test_empty_selection_removes_the_preview(self, ctrl_module, layers, adapters):
        controller = ctrl_module.CoverageModeController(_dock())
        controller._active_layer = layers["r1"]
        controller._raster_panel = _value_panel()
        controller._raster_panel.selection.return_value = None
        controller._apply_raster_preview()
        assert adapters.calls == [("clear", "r1")]


@pytest.mark.unit
class TestHistogramCache:
    """Constat 17: histograms survive a filter of the raster, and the cache is bounded."""

    def test_histogram_cached_on_the_original_source(self, ctrl_module, layers, adapters, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        controller._active_layer = layers["r1"]
        controller._raster_panel = _value_panel()
        controller._raster_panel.current_band.return_value = 1
        controller._raster_panel.selection.return_value = None
        monkeypatch.setattr(controller, "_base_raster", lambda layer: layer)
        controller._refresh_histogram(layers["r1"], 1)
        # Filtered: the layer now shows a derived source of the cache.
        layers["r1"].source = lambda: "/cache/r1_cut.vrt"
        adapters.snapshots.derived["r1"] = types.SimpleNamespace(original_source="/data/r1")
        controller._refresh_histogram(layers["r1"], 1)
        assert [call for call in adapters.calls if call[0] == "histogram"] == [("histogram", 1)]

    def test_unavailable_statistics_are_read_again(self, ctrl_module, layers, adapters, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        controller._raster_panel = _value_panel()
        monkeypatch.setattr(controller, "_base_raster", lambda layer: layer)
        adapters.raster.band_histogram = lambda layer, band, bins=64: adapters.calls.append(("histogram", band)) \
            or ([], 0.0, 0.0)
        controller._refresh_histogram(layers["r1"], 1)
        controller._refresh_histogram(layers["r1"], 1)
        assert [call for call in adapters.calls if call[0] == "histogram"] == [("histogram", 1)] * 2
        assert controller._histogram_cache == {}

    def test_histogram_cache_is_bounded(self, ctrl_module, adapters, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        controller._raster_panel = _value_panel()
        monkeypatch.setattr(controller, "_base_raster", lambda layer: layer)
        for index in range(ctrl_module.HISTOGRAM_CACHE_SIZE + 5):
            controller._refresh_histogram(FakeLayer(f"r{index}", "raster"), 1)
        assert len(controller._histogram_cache) == ctrl_module.HISTOGRAM_CACHE_SIZE
        assert ("/data/r0", 1, "value") not in controller._histogram_cache


@pytest.mark.unit
class TestVectorLayerChange:
    """Constat 12: a layer the vector chain refuses does not end the coverage mode."""

    def _controller(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock(PROJECT_LAYERS={"v1": {}, "r1": {}}))
        controller._active_layer = layers["r1"]
        calls = []
        monkeypatch.setattr(controller, "deactivate", lambda: calls.append("deactivate"))
        monkeypatch.setattr(controller, "_extras_call", lambda method, *a: calls.append(method))
        return controller, calls

    def test_web_raster_or_table_keeps_the_raster(self, ctrl_module, layers, monkeypatch):
        controller, calls = self._controller(ctrl_module, layers, monkeypatch)
        table = FakeLayer("t1", "vector")  # a table without geometry: a vector layer FilterMate does not list
        # True: the vector chain stops (it would make the layer current, then refuse it).
        assert controller.on_current_layer_changed(layers["o1"]) is True
        assert controller.on_current_layer_changed(table) is True
        assert calls == []

    def test_vector_layer_not_listed_keeps_the_raster(self, ctrl_module, layers, monkeypatch):
        controller, calls = self._controller(ctrl_module, layers, monkeypatch)
        assert controller.on_current_layer_changed(layers["v2"]) is True  # e.g. added, add_layers not over
        assert calls == []

    def test_without_a_raster_shown_the_vector_chain_decides(self, ctrl_module, layers, monkeypatch):
        controller, calls = self._controller(ctrl_module, layers, monkeypatch)
        controller._active_layer = None
        assert controller.on_current_layer_changed(layers["v2"]) is False
        assert controller.on_current_layer_changed(layers["o1"]) is False
        assert calls == []

    def test_listed_vector_layer_ends_the_mode(self, ctrl_module, layers, monkeypatch):
        controller, calls = self._controller(ctrl_module, layers, monkeypatch)
        assert controller.on_current_layer_changed(layers["v1"]) is False
        assert calls == ["deactivate", "show_vector"]


@pytest.mark.unit
def test_undo_redo_disabled_outside_the_filtering_tab(ctrl_module, layers):
    """Constat 15: same rule as FilterMateApp.update_undo_redo_buttons."""
    undo, redo = MagicMock(), MagicMock()
    controller = ctrl_module.CoverageModeController(_dock(pushButton_action_undo_filter=undo,
                                                          pushButton_action_redo_filter=redo, tabTools_current_index=1))
    controller._active_layer = layers["r1"]
    ctrl_module._test_service.undo_ok["r1"] = ctrl_module._test_service.redo_ok["r1"] = True
    controller.update_undo_redo_buttons()
    undo.setEnabled.assert_called_with(False)
    redo.setEnabled.assert_called_with(False)


@pytest.mark.unit
class TestToolFollowsTheChosenGroup:
    """The rail tool of a selection type follows the group the user makes the active one."""

    def _controller(self, ctrl_module, monkeypatch, map_tool=None):
        controller = ctrl_module.CoverageModeController(_dock())
        calls = []
        canvas = MagicMock()
        canvas.mapTool.return_value = map_tool
        iface = MagicMock()
        iface.mapCanvas.return_value = canvas
        monkeypatch.setattr(controller, "_iface", lambda: iface)
        monkeypatch.setattr(controller, "_extras_call", lambda name, *args: calls.append((name,) + args))
        monkeypatch.setattr(controller, "_on_color_pick_toggled", lambda on: calls.append(("pipette", on)))
        monkeypatch.setattr(controller, "_on_class_pick_toggled", lambda on: calls.append(("class pipette", on)))
        monkeypatch.setattr(controller, "_deactivate_class_tool", lambda: calls.append(("class pipette", False)))
        return controller, calls

    def test_pipette_group_puts_the_pipette_on(self, ctrl_module, monkeypatch):
        controller, calls = self._controller(ctrl_module, monkeypatch)
        controller._color_pick = False
        controller._on_raster_mode_chosen("pipette")
        assert calls == [("set_pipette_checked", True), ("pipette", True)]

    def test_another_group_takes_the_pipette_off(self, ctrl_module, monkeypatch):
        controller, calls = self._controller(ctrl_module, monkeypatch)
        controller._color_pick = True
        controller._on_raster_mode_chosen("range")
        assert calls == [("set_pipette_checked", False), ("pipette", False)]

    def test_nothing_changes_when_the_pipette_already_follows(self, ctrl_module, monkeypatch):
        controller, calls = self._controller(ctrl_module, monkeypatch)
        controller._color_pick = False
        controller._on_raster_mode_chosen("expression")
        controller._color_pick = True
        controller._on_raster_mode_chosen("pipette")
        assert calls == []

    def test_classes_group_puts_the_class_pipette_on(self, ctrl_module, monkeypatch):
        controller, calls = self._controller(ctrl_module, monkeypatch)
        controller._class_tool = None
        controller._on_point_cloud_group_chosen("classes")
        assert calls == [("class pipette", True)]

    def test_attributes_or_expression_take_the_class_pipette_off(self, ctrl_module, monkeypatch):
        tool = object()
        controller, calls = self._controller(ctrl_module, monkeypatch, map_tool=tool)
        controller._class_tool = tool
        controller._on_point_cloud_group_chosen("ranges")
        assert calls == [("class pipette", False)]

    def test_classes_group_with_the_class_pipette_already_on(self, ctrl_module, monkeypatch):
        tool = object()
        controller, calls = self._controller(ctrl_module, monkeypatch, map_tool=tool)
        controller._class_tool = tool
        controller._on_point_cloud_group_chosen("classes")
        controller._class_tool = None
        controller._on_point_cloud_group_chosen("expression")
        assert calls == []
