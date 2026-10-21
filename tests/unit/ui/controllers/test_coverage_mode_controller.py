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

    def providerType(self):
        return 'gdal' if self.kind == 'raster' else 'memory'

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
    source_capability = _load_real("core.domain.source_capability", "core/domain/source_capability.py")
    probe = types.ModuleType(f"{_PKG}.adapters.qgis.source_capability_probe")
    probe.capability_for_layer = lambda layer: source_capability.classify_layer(layer, is_raster=True)
    monkeypatch.setitem(sys.modules, probe.__name__, probe)
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

    def _outcomes(self, ctrl_module, *states):
        """CrossFilterOutcome per ``(layer_id, success, emptied)``."""
        cross = sys.modules[f"{_PKG}.core.domain.cross_filter"]
        kind = ctrl_module._test_layer_kind.LayerKind.VECTOR
        return [cross.CrossFilterOutcome(layer_id, kind, success, "boom" if not success else "", emptied=emptied)
                for layer_id, success, emptied in states]

    def _quiet(self, controller, monkeypatch):
        for name in ("_refresh_canvas", "_refresh_counts", "update_undo_redo_buttons", "_schedule_cache_tidy"):
            monkeypatch.setattr(controller, name, lambda *a, **k: None)

    def test_emptied_targets_are_a_warning_naming_them(self, ctrl_module, layers, monkeypatch):
        """2026-10-18: every target left with ``1 = 0`` still read "2 target(s) filtered", as an info."""
        controller = ctrl_module.CoverageModeController(_dock())
        self._quiet(controller, monkeypatch)
        callbacks = []
        ctrl_module._test_service.run = lambda request, job, on_done=None: callbacks.append(on_done)
        controller._start_task(object(), types.SimpleNamespace(layer_name="lidar", layer_id="p1"))
        task = types.SimpleNamespace(outcomes=self._outcomes(ctrl_module, ("v1", True, True), ("v2", True, True)),
                                     error="")
        callbacks[0](task, True)
        assert ctrl_module._test_feedback.messages[-1] == (
            "warning", "2 target(s) filtered — 2 left empty, nothing matches the selection: v1, v2")

    def test_targets_keeping_something_stay_an_info(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        self._quiet(controller, monkeypatch)
        callbacks = []
        ctrl_module._test_service.run = lambda request, job, on_done=None: callbacks.append(on_done)
        controller._start_task(object(), types.SimpleNamespace(layer_name="lidar", layer_id="p1"))
        callbacks[0](types.SimpleNamespace(outcomes=self._outcomes(ctrl_module, ("v1", True, False)), error=""), True)
        assert ctrl_module._test_feedback.messages[-1] == ("info", "1 target(s) filtered")

    def test_partial_web_service_target_is_a_warning(self, ctrl_module, layers, monkeypatch):
        """2026-10-20: a WFS target read up to its budget is applied, with the bounded read's warning."""
        controller = ctrl_module.CoverageModeController(_dock())
        self._quiet(controller, monkeypatch)
        callbacks = []
        ctrl_module._test_service.run = lambda request, job, on_done=None: callbacks.append(on_done)
        controller._start_task(object(), types.SimpleNamespace(layer_name="dem", layer_id="r1"))
        outcomes = self._outcomes(ctrl_module, ("v1", True, False))
        outcomes[0].message = "Partial result: the remote feature limit was reached."
        outcomes[0].details["partial"] = True
        callbacks[0](types.SimpleNamespace(outcomes=outcomes, error=""), True)
        assert ctrl_module._test_feedback.messages[-1] == (
            "warning", "1 target(s) filtered — Partial result: the remote feature limit was reached.")

    def test_failed_target_is_never_called_emptied(self, ctrl_module, layers):
        controller = ctrl_module.CoverageModeController(_dock())
        assert controller._emptied_text(self._outcomes(ctrl_module, ("r1", False, True), ("p1", True, False))) == ""

    def test_vector_source_names_its_emptied_targets(self, ctrl_module, layers, adapters, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        self._quiet(controller, monkeypatch)
        jobs = types.ModuleType(f"{adapters.package.__name__}.source_jobs")
        jobs.VectorSourceJob = lambda source, features: object()
        monkeypatch.setitem(sys.modules, jobs.__name__, jobs)
        for name, value in (("_vector_source_features", lambda source: ["feature"]),
                            ("_target_specs", lambda ids, exclude_id="": ids), ("_filtering_settings", lambda: {}),
                            ("_build_request", lambda *a: object())):
            monkeypatch.setattr(controller, name, value)
        callbacks = []
        ctrl_module._test_service.run = lambda request, job, on_done=None: callbacks.append(on_done)
        controller._run_vector_source_filter(layers["v1"], ["r1", "p1"])
        task = types.SimpleNamespace(outcomes=self._outcomes(ctrl_module, ("r1", True, True), ("p1", True, False)),
                                     changes=[], error="")
        callbacks[0](task, True)
        assert ctrl_module._test_feedback.messages[-1] == (
            "warning", "2 raster / point cloud target(s) filtered — 1 left empty, nothing matches the selection: r1")

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
    panel.display_bands.return_value = None
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
    raster.SOURCE_MAX_PIXELS = 100000000
    snapshots = types.ModuleType(f"{package.__name__}.snapshots")
    snapshots.derived = {}
    snapshots.registry = lambda: types.SimpleNamespace(get=snapshots.derived.get, install=lambda *a: None)
    snapshots.take_snapshot = lambda layer, kind: ctrl_module._test_filter_state.LayerSnapshot(
        layer.id(), kind.value, source=layer.source(), subset=layer.subsetString())
    for module in (raster, snapshots):
        monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsTask", FakeQgsTask, raising=False)
    return types.SimpleNamespace(calls=calls, package=package, snapshots=snapshots, raster=raster)


@pytest.fixture
def statistics_tasks(adapters, monkeypatch):
    module = types.ModuleType(f"{adapters.package.__name__}.raster_statistics_task")
    created = []

    class Task:
        def __init__(self, source, provider, band, derivative, band_count, callback, **kwargs):
            self.source, self.band, self.derivative, self.callback = source, band, derivative, callback
            self.expression = kwargs.get('expression', '')
            self.materialize = kwargs.get('materialize', True)
            self.sample_source = kwargs.get('sample_source', '')
            self.histogram, self.spans, self.expression_error = ([], 0.0, 0.0), {}, ''
            self.display_bands = tuple(kwargs.get('display_bands', ()))
            self.ranges = {}
            self.cancel = MagicMock()
            created.append(self)

    module.RasterStatisticsTask = Task
    monkeypatch.setitem(sys.modules, module.__name__, module)
    adapters.raster.raster_reference = lambda layer: layer.name()
    adapters.raster.raster_expression_error = lambda *args: ''
    adapters.raster.source_max_pixels = lambda value: 100000000
    return created


@pytest.mark.unit
class TestHeightAboveGroundLayerSwitch:
    """Constats 1 / 10: the HAG callback and its retry stay on the layer they were started for."""

    @pytest.fixture
    def hag(self, monkeypatch, ctrl_module, adapters):
        module = types.ModuleType(f"{adapters.package.__name__}.hag_task")
        filter_state = ctrl_module._test_filter_state

        class Task:
            def __init__(self, layer, dem, zone=None):
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


def _color_selection(expression='(abs("ortho@1" - 98) <= 27.96 AND abs("ortho@3" - 228) <= 27.24)'):
    """What the panel hands over after a pipette click on a pool of an RGB orthophoto."""
    return types.SimpleNamespace(mode=types.SimpleNamespace(value="expression"), expression=expression, band=1,
                                 derivative=types.SimpleNamespace(is_terrain=False))


@pytest.fixture
def overlay(monkeypatch, adapters):
    """Stub ``preview_overlay``: surfaces counted, a veil drawn on a recorded overlay."""
    module = types.ModuleType(f"{adapters.package.__name__}.preview_overlay")
    module.read = []
    module.shown = []

    class ExpressionSurface:
        def __init__(self, layer, selection):
            module.read.append(selection.expression)
            self.key = (layer.source(), selection.expression)
            self.kept_ratio = 0.00012
            self.extent = "extent"
            self.crs_authid = ""
            self.crs = MagicMock()

        def veil(self, _selection=None):
            return "veil"

    class MaskOverlay:
        def __init__(self, canvas):
            pass

        def show(self, veil, extent):
            module.shown.append((veil, extent))

        def hide(self):
            module.shown.append(None)

    module.ExpressionSurface = ExpressionSurface
    module.DerivativeSurface = None
    module.MaskOverlay = MaskOverlay
    module.fits_canvas = lambda surface, crs: True
    monkeypatch.setitem(sys.modules, module.__name__, module)
    tasks = types.ModuleType(f"{adapters.package.__name__}.raster_surface_task")

    class Task:
        def __init__(self, path, name, selection, callback, provider='gdal'):
            self.path, self.selection, self.callback = path, selection, callback
            self.surface = None
            self.cancel = MagicMock()

        def complete(self):
            try:
                self.surface = module.ExpressionSurface(types.SimpleNamespace(source=lambda: self.path), self.selection)
                ok = True
            except Exception:
                ok = False
            self.callback(self, ok)

    tasks.RasterSurfaceTask = Task
    monkeypatch.setitem(sys.modules, tasks.__name__, tasks)
    return module


class FakeTimer:
    """Single-shot QTimer stand-in: counts the (re)starts, fired by hand."""

    def __init__(self):
        self.starts = 0
        self.active = False

    def start(self):
        self.starts += 1
        self.active = True

    def stop(self):
        self.active = False

    def isActive(self):
        return self.active


@pytest.mark.unit
class TestColorPipetteFeedback:
    """2026-10-18: a pipette click on a pool showed nothing, neither on the map nor as a pixel count."""

    def _controller(self, ctrl_module, layers, monkeypatch, preview=True):
        controller = ctrl_module.CoverageModeController(_dock())
        controller._active_layer = layers["r1"]
        controller._raster_panel = _value_panel()
        controller._raster_panel.selection.return_value = _color_selection()
        controller._raster_panel.preview_enabled.return_value = preview
        controller._preview_active = preview
        controller._expression_timer = FakeTimer()
        monkeypatch.setattr(controller, "_base_raster", lambda layer: layer)
        monkeypatch.setattr(controller, "_iface", lambda: MagicMock())
        return controller

    @staticmethod
    def _settle(controller):
        """The debounce timer fires."""
        controller._expression_timer.stop()
        controller._read_expression()
        if controller._raster_surface_task is not None:
            controller._raster_surface_task.complete()

    def test_nothing_is_read_while_the_preview_is_off(self, ctrl_module, layers, adapters, overlay, monkeypatch):
        controller = self._controller(ctrl_module, layers, monkeypatch, preview=False)
        controller._on_raster_selection_changed()
        controller._read_expression()  # a timer left from before: the preview went off meanwhile
        assert overlay.read == []
        assert controller._expression_timer.starts == 0
        controller._raster_panel.set_kept_ratio.assert_called_with(None)

    def test_a_new_expression_is_read_once_the_input_settles(self, ctrl_module, layers, adapters, overlay,
                                                             monkeypatch):
        controller = self._controller(ctrl_module, layers, monkeypatch)
        for tolerance in (27.96, 30.0, 33.0):  # the tolerance wheel
            controller._raster_panel.selection.return_value = _color_selection(f'(abs("r1@1" - 98) <= {tolerance})')
            controller._on_raster_selection_changed()
        assert overlay.read == [] and overlay.shown == []
        assert controller._expression_timer.active
        self._settle(controller)
        assert overlay.read == ['(abs("r1@1" - 98) <= 33.0)']  # the last one only
        controller._raster_panel.set_kept_ratio.assert_called_with(0.00012)
        assert overlay.shown[-1] == ("veil", "extent")
        assert not [call for call in adapters.calls if call[0] == "apply"]  # one band's transparency cannot show a colour

    def test_an_expression_already_read_is_shown_at_once(self, ctrl_module, layers, adapters, overlay, monkeypatch):
        controller = self._controller(ctrl_module, layers, monkeypatch)
        controller._on_raster_selection_changed()
        self._settle(controller)
        starts = controller._expression_timer.starts
        controller._raster_panel.set_kept_ratio.reset_mock()
        controller._on_raster_selection_changed()
        assert controller._expression_timer.starts == starts
        controller._raster_panel.set_kept_ratio.assert_called_with(0.00012)
        assert len(overlay.read) == 1

    def test_surface_waits_for_worker_and_superseded_results_are_ignored(self, ctrl_module, layers, adapters, overlay, monkeypatch):
        controller = self._controller(ctrl_module, layers, monkeypatch)
        first = _color_selection('"r1@1" > 10')
        controller._raster_panel.selection.return_value = first
        assert controller._selection_surface(layers["r1"], first) is None
        old = controller._raster_surface_task
        assert old is not None and overlay.read == []
        assert controller._selection_surface(layers["r1"], first) is None
        assert controller._raster_surface_task is old
        second = _color_selection('"r1@1" > 20')
        controller._raster_panel.selection.return_value = second
        controller._selection_surface(layers["r1"], second)
        current = controller._raster_surface_task
        old.cancel.assert_called_once()
        old.complete()
        assert controller._surfaces == {}
        current.complete()
        assert list(controller._surfaces) == [("/data/r1", "r1", second.expression)]

    def test_grids_survive_a_layer_switch_and_stay_few(self, ctrl_module, layers, adapters, overlay, monkeypatch):
        controller = self._controller(ctrl_module, layers, monkeypatch)
        controller._on_raster_selection_changed()
        self._settle(controller)
        controller._stop_preview(layers["r1"])  # leaving the layer, a filter
        assert len(controller._surfaces) == 1
        for index in range(ctrl_module.SURFACE_CACHE_SIZE + 2):
            selection = _color_selection(f'("r1@1" > {index})')
            controller._raster_panel.selection.return_value = selection
            controller._selection_surface(layers["r1"], selection)
            controller._raster_surface_task.complete()
        assert len(controller._surfaces) == ctrl_module.SURFACE_CACHE_SIZE
        assert ("/data/r1", "r1", _color_selection().expression) not in controller._surfaces  # the oldest went

    def test_a_renamed_layer_is_read_again(self, ctrl_module, layers, adapters, overlay, monkeypatch):
        controller = self._controller(ctrl_module, layers, monkeypatch)
        controller._selection_surface(layers["r1"], _color_selection())
        controller._raster_surface_task.complete()
        monkeypatch.setattr(layers["r1"], "name", lambda: "r1 renamed")  # its expressions read another reference
        controller._selection_surface(layers["r1"], _color_selection())
        controller._raster_surface_task.complete()
        assert len(overlay.read) == 2

    def test_an_unreadable_expression_has_no_ratio_and_is_not_read_again(self, ctrl_module, layers, adapters,
                                                                         overlay, monkeypatch):
        controller = self._controller(ctrl_module, layers, monkeypatch)
        attempts = []

        def refuse(layer, selection):
            attempts.append(selection.expression)
            raise ValueError("unsupported raster data type")

        monkeypatch.setattr(overlay, "ExpressionSurface", refuse)
        controller._on_raster_selection_changed()
        self._settle(controller)
        controller._on_raster_selection_changed()
        controller._raster_panel.set_kept_ratio.assert_called_with(None)
        assert len(attempts) == 1

    def test_the_crs_notice_is_given_once(self, ctrl_module, layers, adapters, overlay, monkeypatch):
        controller = self._controller(ctrl_module, layers, monkeypatch)
        iface = MagicMock()
        monkeypatch.setattr(controller, "_iface", lambda: iface)
        monkeypatch.setattr(overlay, "fits_canvas", lambda surface, crs: False)
        controller._on_raster_selection_changed()
        self._settle(controller)
        for _ in range(3):
            controller._apply_raster_preview()
        assert iface.messageBar.return_value.pushInfo.call_count == 1


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

    def _expression_controller(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        controller._active_layer = layers["r1"]
        layers["r1"].bandCount = lambda: 4
        controller._raster_panel = _value_panel()
        controller._raster_panel.current_band.return_value = 1
        controller._raster_panel.selection.return_value = None
        controller._raster_panel.preview_enabled.return_value = False
        controller._raster_panel.current_quantity_expression.return_value = '"r1@1" / 100'
        monkeypatch.setattr(controller, "_base_raster", lambda layer: pytest.fail("expression pixels read on GUI thread"))
        monkeypatch.setattr(controller, "_accept_raster_sample", lambda *args: pytest.fail("local source must not become a managed capture"))
        return controller

    def test_custom_quantity_histograms_follow_formula_edits_and_reuse_cache(self, ctrl_module, layers, adapters, statistics_tasks, monkeypatch):
        controller = self._expression_controller(ctrl_module, layers, monkeypatch)
        controller._refresh_histogram(layers["r1"], 1)
        controller._refresh_histogram(layers["r1"], 1)
        assert len(statistics_tasks) == 1
        first = statistics_tasks[0]
        assert not first.materialize and not first.sample_source
        first.histogram = ([2, 3], -1, 1)
        assert first.callback(first, True)
        controller._refresh_histogram(layers["r1"], 1)
        assert len(statistics_tasks) == 1
        controller._raster_panel.set_histogram.assert_called_with(1, [2, 3], -1, 1,
                                                               controller._raster_panel.current_derivative(), expression='"r1@1" / 100')
        controller._raster_panel.current_quantity_expression.return_value = '"r1@1" / 200'
        controller._on_raster_selection_changed()
        assert len(statistics_tasks) == 2
        second = statistics_tasks[1]
        second.histogram = ([2, 3], -1, 1)
        assert second.callback(second, True)
        assert ("/data/r1", 1, '"r1@1" / 200') in controller._histogram_cache

    def test_cached_formula_cancels_a_superseded_read_and_ignores_its_error(self, ctrl_module, layers, statistics_tasks, monkeypatch):
        controller = self._expression_controller(ctrl_module, layers, monkeypatch)
        controller._histogram_cache[("/data/r1", 1, '"r1@1" / 200')] = ([3], 0, 1)
        controller._refresh_histogram(layers["r1"], 1)
        old = statistics_tasks[0]
        controller._raster_panel.current_quantity_expression.return_value = '"r1@1" / 200'
        controller._refresh_histogram(layers["r1"], 1)
        old.cancel.assert_called_once()
        controller._raster_panel.set_expression_status.reset_mock()
        assert not old.callback(old, False)
        controller._raster_panel.set_expression_status.assert_not_called()

    def test_failure_for_a_formula_edited_before_debounce_is_ignored(self, ctrl_module, layers, statistics_tasks, monkeypatch):
        controller = self._expression_controller(ctrl_module, layers, monkeypatch)
        controller._refresh_histogram(layers["r1"], 1)
        old = statistics_tasks[0]
        controller._raster_panel.current_quantity_expression.return_value = '"r1@1" / 200'
        controller._raster_panel.set_expression_status.reset_mock()
        assert not old.callback(old, False)
        controller._raster_panel.set_expression_status.assert_not_called()

    def test_empty_formula_cancels_the_pending_read(self, ctrl_module, layers, statistics_tasks, monkeypatch):
        controller = self._expression_controller(ctrl_module, layers, monkeypatch)
        controller._refresh_histogram(layers["r1"], 1)
        old = statistics_tasks[0]
        controller._raster_panel.current_quantity_expression.return_value = ''
        controller._raster_panel.histogram_uses_expression.return_value = True
        controller._on_raster_selection_changed()
        old.cancel.assert_called_once()
        controller._raster_panel.clear_expression_histogram.assert_called_once()
        assert len(statistics_tasks) == 1

    def test_invalid_band_is_reported_without_starting_a_worker(self, ctrl_module, layers, adapters, statistics_tasks, monkeypatch):
        controller = self._expression_controller(ctrl_module, layers, monkeypatch)
        adapters.raster.raster_expression_error = lambda *args: 'bands'
        controller._refresh_histogram(layers["r1"], 1)
        assert statistics_tasks == []
        controller._raster_panel.set_expression_status.assert_called_with(False, "Unknown raster layer or band in expression")

    def test_valid_empty_result_is_cached(self, ctrl_module, layers, statistics_tasks, monkeypatch):
        controller = self._expression_controller(ctrl_module, layers, monkeypatch)
        controller._refresh_histogram(layers["r1"], 1)
        task = statistics_tasks[0]
        assert task.callback(task, True)
        controller._refresh_histogram(layers["r1"], 1)
        assert len(statistics_tasks) == 1

    def test_custom_histogram_estimates_kept_share_without_preview(self, ctrl_module, layers):
        controller = ctrl_module.CoverageModeController(_dock())
        controller._active_layer = layers["r1"]
        panel = controller._raster_panel = _value_panel()
        panel.current_band.return_value = 1
        panel.current_quantity_expression.return_value = '"r1@1" / 100'
        panel.histogram_range.return_value = (0, None)
        panel.selection.return_value = types.SimpleNamespace(mode=types.SimpleNamespace(value="expression"), seeds=())
        controller._histogram_cache[("/data/r1", 1, '"r1@1" / 100')] = ([3, 1], -1, 1)
        controller._update_kept_ratio()
        panel.set_kept_ratio.assert_called_with(0.25)


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
        monkeypatch.setattr(controller, "_on_color_pick_toggled",
                            lambda on, target=None: calls.append(("pipette", on) if target is None else ("pipette", on, target)))
        monkeypatch.setattr(controller, "_on_class_pick_toggled",
                            lambda on, mode="class": calls.append(("class pipette", on) if not on else ("class pipette", on, mode)))
        monkeypatch.setattr(controller, "_deactivate_class_tool", lambda: calls.append(("class pipette", False)))
        return controller, calls

    def test_pipette_group_puts_the_pipette_on(self, ctrl_module, monkeypatch):
        controller, calls = self._controller(ctrl_module, monkeypatch)
        controller._color_pick = False
        controller._on_raster_mode_chosen("pipette")
        assert calls == [("pipette", True)]  # the rail buttons follow inside _on_color_pick_toggled

    def test_another_group_takes_the_pipette_off(self, ctrl_module, monkeypatch):
        controller, calls = self._controller(ctrl_module, monkeypatch)
        controller._color_pick = True
        controller._on_raster_mode_chosen("range")
        assert calls == [("pipette", False)]

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
        assert calls == [("class pipette", True, "class"), ("stop_zone_tool",)]

    def test_attributes_group_switches_the_picker_to_the_value_pipette(self, ctrl_module, monkeypatch):
        # 2026-10-18: ATTRIBUTES has its own tools (value pipette, zone); the picker changes mode, not map tool.
        tool = object()
        controller, calls = self._controller(ctrl_module, monkeypatch, map_tool=tool)
        controller._class_tool = tool
        controller._on_point_cloud_group_chosen("ranges")
        assert calls == [("class pipette", True, "value")]

    def test_expression_takes_the_picker_off(self, ctrl_module, monkeypatch):
        tool = object()
        controller, calls = self._controller(ctrl_module, monkeypatch, map_tool=tool)
        controller._class_tool = tool
        controller._on_point_cloud_group_chosen("expression")
        assert calls == [("class pipette", False), ("stop_zone_tool",)]

    def test_classes_group_with_the_class_pipette_already_on(self, ctrl_module, monkeypatch):
        tool = object()
        controller, calls = self._controller(ctrl_module, monkeypatch, map_tool=tool)
        controller._class_tool = tool
        controller._pc_pick_mode = "class"
        controller._on_point_cloud_group_chosen("classes")
        assert calls == [("stop_zone_tool",)]
        controller._class_tool = None
        controller._on_point_cloud_group_chosen("expression")
        assert calls == [("stop_zone_tool",), ("stop_zone_tool",)]


@pytest.mark.unit
class TestPipetteAndDetectorButtons:
    """2026-10-18: one picker tool, two rail buttons (pipette / detector) that set the target of the PIPETTE group."""

    def _controller(self, ctrl_module, monkeypatch, map_tool=None):
        controller = ctrl_module.CoverageModeController(_dock())
        calls = []
        canvas = MagicMock()
        canvas.mapTool.return_value = map_tool
        iface = MagicMock()
        iface.mapCanvas.return_value = canvas
        panel = MagicMock()
        panel.pick_target.return_value = "similar"
        controller._raster_panel = panel
        monkeypatch.setattr(controller, "_iface", lambda: iface)
        monkeypatch.setattr(controller, "_extras_call", lambda name, *args: calls.append((name,) + args))
        monkeypatch.setattr(controller, "_toggle_pixel_tool", lambda: calls.append(("picker", "on")))
        monkeypatch.setattr(controller, "_deactivate_pixel_tool", lambda: calls.append(("picker", "off")))
        return controller, panel, calls

    def test_detector_button_sets_the_object_target_and_puts_the_picker_on(self, ctrl_module, monkeypatch):
        controller, panel, calls = self._controller(ctrl_module, monkeypatch)
        controller._on_color_pick_toggled(True, "object")
        panel.set_pick_target.assert_called_once_with("object")
        panel.show_pipette_active.assert_called_once_with(True)
        assert calls == [("set_pipette_checked", True, "object"), ("picker", "on")]
        assert controller._color_pick is True

    def test_pipette_button_off_takes_the_picker_off(self, ctrl_module, monkeypatch):
        tool = object()
        controller, panel, calls = self._controller(ctrl_module, monkeypatch, map_tool=tool)
        controller._pixel_tool = tool
        controller._on_color_pick_toggled(False, "similar")
        assert calls == [("set_pipette_checked", False, "similar"), ("picker", "off")]
        assert controller._color_pick is False

    def test_without_a_target_the_panel_target_is_used(self, ctrl_module, monkeypatch):
        controller, panel, calls = self._controller(ctrl_module, monkeypatch)
        panel.pick_target.return_value = "object"
        controller._on_color_pick_toggled(True)
        panel.set_pick_target.assert_not_called()
        assert calls[0] == ("set_pipette_checked", True, "object")


@pytest.mark.unit
class TestIdentifyIsTheClassPipette:
    """2026-10-18: on a point cloud the Identify button toggles the class pipette, not the QGIS identify tool."""

    def _controller(self, ctrl_module, layers, monkeypatch, map_tool=None):
        controller = ctrl_module.CoverageModeController(_dock())
        controller._active_layer, controller._kind = layers["p1"], _kind(ctrl_module, "POINT_CLOUD")
        calls = []
        canvas = MagicMock()
        canvas.mapTool.return_value = map_tool
        iface = MagicMock()
        iface.mapCanvas.return_value = canvas
        monkeypatch.setattr(controller, "_iface", lambda: iface)
        monkeypatch.setattr(controller, "_on_class_pick_toggled",
                            lambda on, mode="class": calls.append(("class pipette", on) if not on else ("class pipette", on, mode)))
        monkeypatch.setattr(controller, "_identify_point_cloud", lambda: calls.append(("qgis identify",)))
        return controller, calls

    def test_identify_puts_the_class_pipette_on(self, ctrl_module, layers, monkeypatch):
        controller, calls = self._controller(ctrl_module, layers, monkeypatch)
        assert controller.handle_exploring_action("identify") is True
        assert calls == [("class pipette", True, "class")]

    def test_identify_again_takes_it_off(self, ctrl_module, layers, monkeypatch):
        tool = object()
        controller, calls = self._controller(ctrl_module, layers, monkeypatch, map_tool=tool)
        controller._class_tool = tool
        controller.handle_exploring_action("identify")
        assert calls == [("class pipette", False)]

    def test_identify_switches_the_value_pipette_back_to_the_class_one(self, ctrl_module, layers, monkeypatch):
        tool = object()
        controller, calls = self._controller(ctrl_module, layers, monkeypatch, map_tool=tool)
        controller._class_tool, controller._pc_pick_mode = tool, "value"
        controller.handle_exploring_action("identify")
        assert calls == [("class pipette", True, "class")]


@pytest.mark.unit
class TestValuePipette:
    """2026-10-18: the value pipette of ATTRIBUTES writes a condition around the attribute of the point clicked."""

    def _controller(self, ctrl_module, layers, monkeypatch, attributes):
        controller = ctrl_module.CoverageModeController(_dock())
        controller._active_layer, controller._kind = layers["p1"], _kind(ctrl_module, "POINT_CLOUD")
        controller._pc_pick_mode = "value"
        panel = MagicMock()
        panel.pick_attribute.return_value = "Z"
        panel.add_value_condition.return_value = True
        controller._pc_panel = panel
        canvas = MagicMock()
        iface = MagicMock()
        iface.mapCanvas.return_value = canvas
        monkeypatch.setattr(controller, "_iface", lambda: iface)
        adapter = types.ModuleType(f"{_PKG}.adapters.qgis.point_cloud_layer_adapter")
        adapter.attributes_at = lambda layer, canvas, point: attributes
        adapter.attribute_value = lambda attrs, name: None if not attrs else attrs.get(name)
        monkeypatch.setitem(sys.modules, adapter.__name__, adapter)
        return controller, panel, iface

    def test_a_click_writes_a_condition_on_the_chosen_attribute(self, ctrl_module, layers, monkeypatch):
        controller, panel, iface = self._controller(ctrl_module, layers, monkeypatch, {"Z": 1245.3, "Classification": 6})
        controller._on_class_picked(object(), False)
        panel.add_value_condition.assert_called_once_with("Z", 1245.3, False)
        iface.messageBar().pushInfo.assert_not_called()

    def test_ctrl_click_adds_an_or_condition(self, ctrl_module, layers, monkeypatch):
        controller, panel, _iface = self._controller(ctrl_module, layers, monkeypatch, {"Z": 12.0})
        controller._on_class_picked(object(), True)
        panel.add_value_condition.assert_called_once_with("Z", 12.0, True)

    def test_no_point_under_the_click_is_said(self, ctrl_module, layers, monkeypatch):
        controller, panel, iface = self._controller(ctrl_module, layers, monkeypatch, None)
        controller._on_class_picked(object(), False)
        panel.add_value_condition.assert_not_called()
        assert iface.messageBar().pushInfo.called


@pytest.mark.unit
class TestNoPixelPickerOnARaster:
    """2026-10-18: the Identify button does nothing on a raster (hidden by the rail); the pipette reads the bands."""

    def test_identify_is_a_no_op_on_a_raster(self, ctrl_module, layers, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        controller._active_layer, controller._kind = layers["r1"], _kind(ctrl_module, "RASTER")
        calls = []
        monkeypatch.setattr(controller, "_toggle_pixel_tool", lambda: calls.append("picker"))
        monkeypatch.setattr(controller, "_on_color_pick_toggled", lambda *a: calls.append("pipette"))
        assert controller.handle_exploring_action("identify") is True
        assert calls == []


@pytest.mark.unit
class TestToolComesBackWithTheLayer:
    """R3 (2026-10-18): the tool on the map leaves with the layer and is put back explicitly on its return."""

    def _controller(self, ctrl_module, layers, monkeypatch, kind, map_tool=None):
        controller = ctrl_module.CoverageModeController(_dock())
        controller._active_layer, controller._kind = layers["r1" if kind == "RASTER" else "p1"], _kind(ctrl_module, kind)
        calls = []
        canvas = MagicMock()
        canvas.mapTool.return_value = map_tool
        iface = MagicMock()
        iface.mapCanvas.return_value = canvas
        monkeypatch.setattr(controller, "_iface", lambda: iface)
        monkeypatch.setattr(controller, "_on_color_pick_toggled",
                            lambda on, target=None: calls.append(("pipette", on, target)))
        monkeypatch.setattr(controller, "_on_class_pick_toggled",
                            lambda on, mode="class": calls.append(("class pipette", on) if not on else ("class pipette", on, mode)))
        monkeypatch.setattr(controller, "_deactivate_pixel_tool", lambda: None)
        monkeypatch.setattr(controller, "_deactivate_class_tool", lambda: None)
        monkeypatch.setattr(controller, "_drop_map_tools", lambda: None)
        monkeypatch.setattr(controller, "_stop_preview", lambda layer: None)
        monkeypatch.setattr(controller, "_hide_detected_objects", lambda: None)
        return controller, calls

    def test_raster_state_remembers_the_detector_on_the_map(self, ctrl_module, layers, monkeypatch):
        tool = object()
        controller, calls = self._controller(ctrl_module, layers, monkeypatch, "RASTER", map_tool=tool)
        panel = MagicMock()
        panel.state.return_value = {"mode": "pipette"}
        panel.pick_target.return_value = "object"
        controller._raster_panel, controller._pixel_tool, controller._color_pick = panel, tool, True
        controller._leave_layer()
        saved = controller._panel_states["r1"]
        assert saved["pipette_on"] is True and saved["pipette_target"] == "object" and saved["class_pipette_on"] is False

    def test_raster_state_without_a_tool(self, ctrl_module, layers, monkeypatch):
        controller, calls = self._controller(ctrl_module, layers, monkeypatch, "RASTER")
        panel = MagicMock()
        panel.state.return_value = {"mode": "range"}
        controller._raster_panel = panel
        controller._leave_layer()
        assert controller._panel_states["r1"]["pipette_on"] is False

    def test_restore_puts_the_tool_back(self, ctrl_module, layers, monkeypatch):
        controller, calls = self._controller(ctrl_module, layers, monkeypatch, "RASTER")
        controller._restore_tool({"pipette_on": True, "pipette_target": "object"})
        assert calls == [("pipette", True, "object")]
        controller._restore_tool({"pipette_on": False})
        assert calls == [("pipette", True, "object")]

    def test_point_cloud_restore_puts_the_class_pipette_back(self, ctrl_module, layers, monkeypatch):
        controller, calls = self._controller(ctrl_module, layers, monkeypatch, "POINT_CLOUD")
        controller._restore_tool({"class_pipette_on": True})
        assert calls == [("class pipette", True, "class")]
        controller._restore_tool({"class_pipette_on": True, "pc_tool": "value"})
        assert calls[-1] == ("class pipette", True, "value")


@pytest.mark.unit
class TestRasterSourceWithoutTarget:
    """2026-10-18: the polygons of a raster selection are read at the native resolution, tile by tile:
    without a target, a source masked by them is filtered in the task, never on the main thread."""

    @pytest.fixture
    def jobs(self, monkeypatch, adapters):
        module = types.ModuleType(f"{adapters.package.__name__}.source_jobs")
        module.created = []

        class Job:
            def __init__(self, layer, selection, max_pixels):
                self.layer_id, self.layer_name, self.max_pixels = layer.id(), layer.id(), max_pixels
                self.clips_source = selection.clips
                self.clip_refusal = getattr(module, "refusal", "")
                self.before = "before"
                self.applied, self.details, self.message, self.released = [], {}, "", False
                module.created.append(self)

            def release(self):
                self.released = True

            def apply(self, layer):
                self.applied.append(layer.id())
                return None

        module.RasterSourceJob = Job
        monkeypatch.setitem(sys.modules, module.__name__, module)
        return module

    def _run(self, ctrl_module, layers, monkeypatch, clips):
        controller = ctrl_module.CoverageModeController(_dock())
        controller._active_layer, controller._kind = layers["r1"], _kind(ctrl_module, "RASTER")
        controller._raster_panel = MagicMock()
        controller._raster_panel.selection.return_value = types.SimpleNamespace(clips=clips, describe=lambda: "blue")
        monkeypatch.setattr(controller, "_filtering_settings", lambda: dict(targets=[], source_operator=None))
        monkeypatch.setattr(controller, "_build_request", lambda *a: "request")
        monkeypatch.setattr(controller, "_schedule_cache_tidy", lambda *a: None)
        controller._run_filter(layers["r1"])
        return controller

    def _task(self, ctrl_module, layers, monkeypatch, refusal=""):
        service, done = ctrl_module._test_service, []
        monkeypatch.setattr(service, "run", lambda request, job, on_done=None: service.calls.append(
            ("run", request, job)) or done.append(on_done))
        monkeypatch.setattr(sys.modules[f"{ctrl_module.__name__.rsplit('.ui.', 1)[0]}.adapters.qgis.coverage_layers"
                                        ".source_jobs"], "refusal", refusal, raising=False)
        self._run(ctrl_module, layers, monkeypatch, clips=True)
        return service, done

    def test_masked_source_goes_to_the_task(self, ctrl_module, layers, jobs, monkeypatch):
        service, done = self._task(ctrl_module, layers, monkeypatch)
        job = jobs.created[0]
        assert job.applied == [] and job.max_pixels is None  # the job reads and bounds the setting
        assert service.calls == [("run", "request", job)]
        done[0](types.SimpleNamespace(outcomes=[], error="", changes=[("before", "after")]), True)
        assert ctrl_module._test_feedback.messages[-1] == ("info", "Raster filtered: {0}".format("blue"))

    def test_coarse_read_is_told_once(self, ctrl_module, layers, jobs, monkeypatch):
        service, done = self._task(ctrl_module, layers, monkeypatch)
        jobs.created[0].details = {"decimation": 2, "smoothing": 4}
        before = len(ctrl_module._test_feedback.messages)
        done[0](types.SimpleNamespace(outcomes=[], error="", changes=[("before", "after")]), True)
        new = ctrl_module._test_feedback.messages[before:]
        assert len(new) == 1 and "every 2 pixels" in new[0][1] and "smoothed" in new[0][1]

    def test_nothing_applied_is_a_warning_with_the_reason(self, ctrl_module, layers, jobs, monkeypatch):
        service, done = self._task(ctrl_module, layers, monkeypatch)
        jobs.created[0].message = "no pixel is selected: the source is left as it is"
        done[0](types.SimpleNamespace(outcomes=[], error="", changes=[]), True)
        assert ctrl_module._test_feedback.messages[-1] == (
            "warning", "Filter not applied: {0}".format("no pixel is selected: the source is left as it is"))

    def test_source_removed_during_the_task(self, ctrl_module, layers, jobs, monkeypatch):
        service, done = self._task(ctrl_module, layers, monkeypatch)
        del layers["r1"]
        done[0](types.SimpleNamespace(outcomes=[], error="", changes=[]), True)
        assert ctrl_module._test_feedback.messages[-1] == ("warning", "Filter not applied: {0}".format("layer removed"))

    def test_source_that_cannot_be_masked_is_refused_before_reading(self, ctrl_module, layers, jobs, monkeypatch):
        service, done = self._task(ctrl_module, layers, monkeypatch, refusal="not a GDAL file")
        assert service.calls == [] and jobs.created[0].released
        assert ctrl_module._test_feedback.messages[-1] == ("warning", "Filter not applied: {0}".format("not a GDAL file"))

    def test_band_range_is_still_applied_at_once(self, ctrl_module, layers, jobs, monkeypatch):
        self._run(ctrl_module, layers, monkeypatch, clips=False)
        assert jobs.created[0].applied == ["r1"] and ctrl_module._test_service.calls == []
        assert ctrl_module._test_feedback.messages[-1] == ("info", "Raster filtered: {0}".format("blue"))


class FakeShape:
    """QgsGeometry of a box, written ``BOX x0 y0 x1 y1`` (or a union ``U[...]`` of boxes)."""

    def __init__(self, wkt=""):
        self.wkt = wkt
        self.boxes = []
        for part in wkt.replace("U[", "").replace("]", "").split(";"):
            if part.startswith("BOX"):
                self.boxes.append(tuple(float(v) for v in part.split()[1:]))

    @classmethod
    def fromWkt(cls, wkt):
        return cls(wkt)

    def isEmpty(self):
        return not self.boxes

    def area(self):
        return sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in self.boxes)

    def contains(self, point):
        return any(x0 <= point.x() <= x1 and y0 <= point.y() <= y1 for x0, y0, x1, y1 in self.boxes)

    def asWkt(self, precision=17):
        return self.wkt

    def boundingBox(self):
        x0, y0, x1, y1 = (min(b[0] for b in self.boxes), min(b[1] for b in self.boxes),
                          max(b[2] for b in self.boxes), max(b[3] for b in self.boxes))
        return types.SimpleNamespace(xMinimum=lambda: x0, yMinimum=lambda: y0, xMaximum=lambda: x1, yMaximum=lambda: y1)


class FakePoint:
    def __init__(self, x, y):
        self._x, self._y = x, y

    def x(self):
        return self._x

    def y(self):
        return self._y


class FakeObjectsPanel:
    """The object detector part of the point cloud panel."""

    def __init__(self, target="object", codes=(2, 5, 6)):
        self.target, self.codes, self.items, self.detected = target, set(codes), [], None
        self.ratio = (0.5, 2.0)

    def object_target(self):
        return self.target

    def set_object_target(self, target):
        changed, self.target = target != self.target, target
        return changed

    def object_ratio(self):
        return self.ratio

    def object_items(self):
        return [dict(item) for item in self.items]

    def add_object(self, item, extend=False):
        if item["code"] not in self.codes:
            return False
        self.items = (self.items if extend else []) + [dict(item)]
        self.detected = None
        return True

    def set_detected_objects(self, wkt, boxes, count, area=None, truncated=False):
        self.detected = (wkt, [list(box) for box in boxes], count, area, truncated)

    def object_zone_wkt(self):
        return self.detected[0] if self.detected and self.items else ""


@pytest.mark.unit
class TestPointCloudObjectDetector:
    """2026-10-18: the object detector of CLASSES (point_cloud_objects), on the class picker."""

    def _controller(self, ctrl_module, layers, monkeypatch, mode="object", target="object", code=6, map_tool=None):
        controller = ctrl_module.CoverageModeController(_dock())
        controller._active_layer, controller._kind = layers["p1"], _kind(ctrl_module, "POINT_CLOUD")
        controller._pc_pick_mode = mode
        layers["p1"].providerType = lambda: "copc"
        panel = FakeObjectsPanel(target)
        controller._pc_panel = panel
        canvas = MagicMock()
        canvas.mapTool.return_value = map_tool
        iface = MagicMock()
        iface.mapCanvas.return_value = canvas
        extras = []
        monkeypatch.setattr(controller, "_iface", lambda: iface)
        monkeypatch.setattr(controller, "_extras_call", lambda name, *args: extras.append((name,) + args))
        monkeypatch.setattr(controller, "_layer_click", lambda layer, canvas, point: (point.x(), point.y(), 0.5))
        monkeypatch.setattr(controller, "_ground_area", lambda geometry, layer: geometry.area())
        core = sys.modules["qgis.core"]
        monkeypatch.setattr(core, "QgsGeometry", FakeShape, raising=False)
        monkeypatch.setattr(core, "QgsPointXY", FakePoint, raising=False)
        package = types.ModuleType(f"{_PKG}.adapters.qgis.coverage_layers")
        package.__path__ = []
        monkeypatch.setitem(sys.modules, package.__name__, package)
        reads = types.SimpleNamespace(objects=[], footprints=[], similar=[], outlines=[], on_map=[], under=[],
                                      copies=[], readers=[])
        adapter = types.ModuleType(f"{_PKG}.adapters.qgis.point_cloud_layer_adapter")
        adapter.class_at = lambda layer, canvas, point: reads.on_map.append(layer.id()) or code
        objects = types.ModuleType(f"{package.__name__}.point_cloud_objects")
        objects.found = {}  # (x, y) -> box of the object read there
        objects.similar_parts = {}  # code -> boxes of the similar objects

        def object_footprint(layer, x, y, code, seed_radius=0.0):
            reads.objects.append((x, y, code))
            reads.readers.append(layer)
            box = objects.found.get((x, y))
            wkt = "BOX " + " ".join(str(v) for v in box) if box else ""
            return types.SimpleNamespace(geometry=FakeShape(wkt), truncated=False, message="", points=12)

        def class_footprint(layer, code, base_subset=""):
            reads.footprints.append((code, base_subset))
            return f"footprint {code}"

        def similar_objects_footprint(layer, code, areas, ratio, base_subset="", footprint=None):
            reads.similar.append((code, tuple(areas), tuple(ratio), footprint))
            parts = [FakeShape("BOX " + " ".join(str(v) for v in box)) for box in objects.similar_parts.get(code, [])]
            union = FakeShape("U[" + ";".join(part.wkt for part in parts) + "]")
            return types.SimpleNamespace(parts=parts, geometry=union, truncated=False, total=10)

        def base_copy(layer, base_subset=""):
            reads.copies.append(base_subset)
            return types.SimpleNamespace(name="copy", base=base_subset)

        objects.object_footprint = object_footprint
        objects.class_footprint = class_footprint
        objects.base_copy = base_copy
        objects.class_under = lambda layer, x, y, radius=0.0: reads.under.append((layer.name, x, y)) or code
        objects.similar_objects_footprint = similar_objects_footprint
        tools = types.ModuleType(f"{package.__name__}.geometry_tools")
        tools.union_geometries = lambda shapes: FakeShape("U[" + ";".join(shape.wkt for shape in shapes) + "]")
        overlay = types.ModuleType(f"{package.__name__}.preview_overlay")

        class ObjectOutline:
            def __init__(self, canvas):
                self.visible = False

            def show(self, geometry, layer):
                reads.outlines.append(geometry.wkt)
                self.visible = True

            def hide(self):
                reads.outlines.append(None)
                self.visible = False

        overlay.ObjectOutline = ObjectOutline
        for module in (adapter, objects, tools, overlay):
            monkeypatch.setitem(sys.modules, module.__name__, module)
        return controller, panel, iface, reads, objects, extras

    def test_a_click_selects_the_object_under_it(self, ctrl_module, layers, monkeypatch):
        controller, panel, iface, reads, objects, extras = self._controller(ctrl_module, layers, monkeypatch)
        objects.found[(1.0, 1.0)] = (0, 0, 2, 3)
        controller._on_class_picked(FakePoint(1.0, 1.0), False)
        assert reads.objects == [(1.0, 1.0, 6)]
        assert [(item["code"], item["box"], item["wkt"]) for item in panel.items] == [(6, [0, 0, 2, 3], "BOX 0 0 2 3")]
        assert panel.detected == ("U[BOX 0 0 2 3]", [[6, 0, 0, 2, 3]], 1, 6.0, False)
        assert reads.outlines == ["U[BOX 0 0 2 3]"] and ("schedule_strip",) in extras
        iface.messageBar().pushInfo.assert_not_called()

    def test_ctrl_click_adds_an_object_of_another_class(self, ctrl_module, layers, monkeypatch):
        controller, panel, _iface, reads, objects, _extras = self._controller(ctrl_module, layers, monkeypatch, code=5)
        panel.items = [{"x": 1.0, "y": 1.0, "code": 6, "box": [0, 0, 2, 3], "wkt": "BOX 0 0 2 3", "truncated": True}]
        objects.found[(1.0, 1.0)] = (0, 0, 4, 4)  # a tree over the roof: another object
        controller._on_class_picked(FakePoint(1.0, 1.0), True)
        assert [item["code"] for item in panel.items] == [6, 5]
        assert panel.detected[1] == [[6, 0, 0, 2, 3], [5, 0, 0, 4, 4]] and panel.detected[2] == 2
        assert panel.detected[4] is True  # an object was cut

    def test_ctrl_click_inside_an_object_of_its_class_reads_nothing(self, ctrl_module, layers, monkeypatch):
        controller, panel, _iface, reads, _objects, _extras = self._controller(ctrl_module, layers, monkeypatch)
        panel.items = [{"x": 1.0, "y": 1.0, "code": 6, "box": [0, 0, 2, 3], "wkt": "BOX 0 0 2 3", "truncated": False}]
        controller._on_class_picked(FakePoint(1.5, 2.0), True)
        assert reads.objects == [] and len(panel.items) == 1

    def test_no_point_of_the_class_under_the_click_is_said(self, ctrl_module, layers, monkeypatch):
        controller, panel, iface, reads, _objects, _extras = self._controller(ctrl_module, layers, monkeypatch)
        controller._on_class_picked(FakePoint(9.0, 9.0), False)
        assert reads.objects == [(9.0, 9.0, 6)] and panel.items == []
        assert "No point of class" in iface.messageBar().pushInfo.call_args.args[1]

    def test_no_class_under_the_click_reads_nothing(self, ctrl_module, layers, monkeypatch):
        controller, panel, iface, reads, _objects, _extras = self._controller(ctrl_module, layers, monkeypatch, code=None)
        controller._on_class_picked(FakePoint(9.0, 9.0), False)
        assert reads.objects == [] and iface.messageBar().pushInfo.called

    def test_similar_objects_are_read_class_by_class_and_the_footprint_kept(self, ctrl_module, layers, monkeypatch):
        controller, panel, _iface, reads, objects, _extras = self._controller(
            ctrl_module, layers, monkeypatch, mode="similar", target="similar_objects")
        layers["p1"]._subset = "Classification != 7"
        objects.found[(1.0, 1.0)] = (0, 0, 2, 3)
        objects.similar_parts[6] = [(0, 0, 2, 3), (10, 10, 12, 13), (20, 20, 21, 25)]
        controller._on_class_picked(FakePoint(1.0, 1.0), False)
        assert reads.similar == [(6, (6.0,), (0.5, 2.0), "footprint 6")]
        assert reads.footprints == [(6, "Classification != 7")]  # through the filter of the layer
        _wkt, boxes, count, area, _truncated = panel.detected
        assert count == 3 and boxes[1] == [6, 10, 10, 12, 13] and area == 6.0 + 6.0 + 5.0
        panel.ratio = (0.9, 1.1)
        controller._refresh_point_cloud_objects()  # a ratio edited: the class is not read again
        assert reads.footprints == [(6, "Classification != 7")] and reads.similar[-1][2] == (0.9, 1.1)

    def test_similar_objects_read_through_the_filter_not_the_preview(self, ctrl_module, layers, monkeypatch):
        controller, _panel, _iface, reads, objects, _extras = self._controller(
            ctrl_module, layers, monkeypatch, mode="similar", target="similar_objects")
        controller._preview_base_subset = ""
        layers["p1"]._subset = "Classification = 6 AND X >= 0"  # the live preview
        objects.found[(1.0, 1.0)] = (0, 0, 2, 3)
        objects.similar_parts[6] = [(0, 0, 2, 3)]
        controller._on_class_picked(FakePoint(1.0, 1.0), False)
        assert reads.footprints == [(6, "")]

    def test_no_similar_object_keeps_the_clicked_ones(self, ctrl_module, layers, monkeypatch):
        controller, panel, iface, _reads, objects, _extras = self._controller(
            ctrl_module, layers, monkeypatch, mode="similar", target="similar_objects")
        objects.found[(1.0, 1.0)] = (0, 0, 2, 3)
        controller._on_class_picked(FakePoint(1.0, 1.0), False)
        assert panel.detected[1] == [[6, 0, 0, 2, 3]] and panel.detected[2] == 1
        assert "No similar object" in iface.messageBar().pushInfo.call_args.args[1]

    def test_the_picker_mode_sets_the_target(self, ctrl_module, layers, monkeypatch):
        controller, panel, _iface, _reads, objects, _extras = self._controller(
            ctrl_module, layers, monkeypatch, mode="similar", target="object")
        objects.found[(1.0, 1.0)] = (0, 0, 2, 3)
        controller._on_class_picked(FakePoint(1.0, 1.0), False)
        assert panel.target == "similar_objects"

    def test_dropped_objects_take_the_outline_off(self, ctrl_module, layers, monkeypatch):
        controller, panel, _iface, reads, objects, _extras = self._controller(ctrl_module, layers, monkeypatch)
        objects.found[(1.0, 1.0)] = (0, 0, 2, 3)
        controller._on_class_picked(FakePoint(1.0, 1.0), False)
        panel.items, panel.detected = [], None  # the class list edited by hand
        controller._refresh_point_cloud_objects()
        assert reads.outlines == ["U[BOX 0 0 2 3]", None] and controller._pc_outline_wkt == ""

    def test_target_from_the_menu_switches_the_detector_on_the_map(self, ctrl_module, layers, monkeypatch):
        tool = object()
        controller, panel, _iface, _reads, _objects, extras = self._controller(ctrl_module, layers, monkeypatch,
                                                                              map_tool=tool)
        controller._class_tool = tool
        controller._on_point_cloud_object_target("similar_objects")
        assert panel.target == "similar_objects" and controller._pc_pick_mode == "similar"
        assert ("set_class_pipette_checked", True, "similar") in extras

    def test_target_from_the_menu_switches_the_value_pipette_to_the_detector(self, ctrl_module, layers, monkeypatch):
        # R4: the target chosen is the detector in that target (as the three target buttons of the raster rail).
        tool = object()
        controller, panel, _iface, _reads, _objects, extras = self._controller(ctrl_module, layers, monkeypatch,
                                                                              mode="value", map_tool=tool)
        controller._class_tool = tool
        controller._on_point_cloud_object_target("similar_objects")
        assert panel.target == "similar_objects" and controller._pc_pick_mode == "similar"
        assert ("set_class_pipette_checked", True, "similar") in extras

    def test_target_from_the_menu_puts_the_detector_on(self, ctrl_module, layers, monkeypatch):
        controller, panel, _iface, _reads, _objects, _extras = self._controller(ctrl_module, layers, monkeypatch)
        calls = []
        monkeypatch.setattr(controller, "_on_class_pick_toggled", lambda on, mode="class": calls.append((on, mode)))
        controller._on_point_cloud_object_target("similar_objects")
        assert calls == [(True, "similar")]

    def test_the_same_target_reads_nothing_again(self, ctrl_module, layers, monkeypatch):
        controller, panel, _iface, reads, _objects, _extras = self._controller(
            ctrl_module, layers, monkeypatch, mode="similar", target="similar_objects")
        monkeypatch.setattr(controller, "_on_class_pick_toggled", lambda on, mode="class": None)
        panel.items = [{"x": 1.0, "y": 1.0, "code": 6, "box": [0, 0, 2, 3], "wkt": "BOX 0 0 2 3", "truncated": False}]
        controller._on_point_cloud_object_target("similar_objects")
        assert reads.similar == [] and reads.footprints == []
        controller._on_point_cloud_object_target("object")
        assert panel.detected is not None and panel.detected[2] == 1  # changed: read again (the clicked object)

    def test_a_click_with_a_new_target_reads_once(self, ctrl_module, layers, monkeypatch):
        controller, panel, _iface, reads, objects, _extras = self._controller(
            ctrl_module, layers, monkeypatch, mode="similar", target="object")
        panel.items = [{"x": 1.0, "y": 1.0, "code": 6, "box": [0, 0, 2, 3], "wkt": "BOX 0 0 2 3", "truncated": False}]
        objects.found[(20.0, 20.0)] = (19, 19, 22, 22)
        objects.similar_parts[6] = [(19, 19, 22, 22)]
        controller._on_class_picked(FakePoint(20.0, 20.0), False)
        assert len(reads.similar) == 1 and reads.similar[0][1] == (9.0,)  # the new object only, read once

    def test_preview_on_reads_the_click_on_a_copy_of_the_filter(self, ctrl_module, layers, monkeypatch):
        controller, panel, _iface, reads, objects, _extras = self._controller(ctrl_module, layers, monkeypatch)
        controller._preview_base_subset = "Z > 0"
        layers["p1"]._subset = "(Z > 0) AND (Classification = 6 AND X >= 0 AND X <= 2 AND Y >= 0 AND Y <= 3)"
        objects.found[(20.0, 20.0)] = (19, 19, 22, 22)
        controller._on_class_picked(FakePoint(20.0, 20.0), False)
        controller._on_class_picked(FakePoint(20.0, 20.0), False)
        assert reads.copies == ["Z > 0"]  # opened once for the layer and that filter
        assert reads.on_map == [] and reads.under == [("copy", 20.0, 20.0)] * 2
        assert all(getattr(reader, "name", None) == "copy" for reader in reads.readers)
        assert panel.items and panel.items[0]["box"] == [19, 19, 22, 22]

    def test_without_preview_the_click_is_read_on_the_layer(self, ctrl_module, layers, monkeypatch):
        controller, _panel, _iface, reads, objects, _extras = self._controller(ctrl_module, layers, monkeypatch)
        controller._preview_base_subset = "Z > 0"
        layers["p1"]._subset = "Z > 0"  # the preview keeps nothing more
        objects.found[(1.0, 1.0)] = (0, 0, 2, 3)
        controller._on_class_picked(FakePoint(1.0, 1.0), False)
        assert reads.copies == [] and reads.on_map == ["p1"] and reads.readers == [layers["p1"]]

    def test_reset_brings_the_detector_back_to_the_clicked_object(self, ctrl_module, layers, monkeypatch):
        tool = object()
        controller, panel, _iface, _reads, _objects, extras = self._controller(
            ctrl_module, layers, monkeypatch, mode="similar", target="similar_objects", map_tool=tool)
        controller._class_tool = tool
        monkeypatch.setattr(controller, "_stop_preview", lambda layer: None)
        monkeypatch.setattr(controller, "_current_panel", lambda: types.SimpleNamespace(
            reset=lambda: setattr(panel, "target", "object")))
        controller.handle_exploring_action("reset")
        assert controller._pc_pick_mode == "object" and ("set_class_pipette_checked", True, "object") in extras

    def test_objects_never_read_are_read_when_the_layer_comes_back(self, ctrl_module, layers, monkeypatch):
        controller, panel, _iface, reads, _objects, _extras = self._controller(ctrl_module, layers, monkeypatch)
        panel.items = [{"x": 1.0, "y": 1.0, "code": 6, "box": [0, 0, 2, 3], "wkt": "BOX 0 0 2 3", "truncated": False}]
        panel.restore_state = lambda state: None
        panel.objects_pending = lambda: panel.detected is None
        monkeypatch.setattr(controller, "_restore_tool", lambda state: None)
        controller._panel_states["p1"] = {"objects": {}}
        controller._restore_panel_state(layers["p1"])
        assert panel.detected == ("U[BOX 0 0 2 3]", [[6, 0, 0, 2, 3]], 1, 6.0, False)
        assert reads.outlines == ["U[BOX 0 0 2 3]"]

    @pytest.mark.parametrize("target, mode", [("object", "object"), ("similar_objects", "similar")])
    def test_detector_button_uses_the_target_of_the_panel(self, ctrl_module, layers, monkeypatch, target, mode):
        controller, _panel, _iface, _reads, _objects, _extras = self._controller(ctrl_module, layers, monkeypatch,
                                                                                target=target)
        calls = []
        monkeypatch.setattr(controller, "_on_class_pick_toggled", lambda on, mode="class": calls.append((on, mode)))
        controller._on_object_pick_toggled(True)
        assert calls == [(True, mode)]

    @pytest.mark.parametrize("asked, kept", [("object", "object"), ("similar", "similar"), ("value", "value"),
                                             ("pool", "class")])
    def test_picker_modes(self, ctrl_module, layers, monkeypatch, asked, kept):
        tool = object()
        controller, _panel, _iface, _reads, _objects, extras = self._controller(ctrl_module, layers, monkeypatch,
                                                                               mode="class", map_tool=tool)
        controller._class_tool = tool
        controller._on_class_pick_toggled(True, asked)
        assert controller._pc_pick_mode == kept and extras[0] == ("set_class_pipette_checked", True, kept)

    def test_classes_group_keeps_the_detector(self, ctrl_module, layers, monkeypatch):
        tool = object()
        controller, _panel, _iface, _reads, _objects, extras = self._controller(ctrl_module, layers, monkeypatch,
                                                                               map_tool=tool)
        controller._class_tool = tool
        calls = []
        monkeypatch.setattr(controller, "_on_class_pick_toggled", lambda on, mode="class": calls.append((on, mode)))
        controller._on_point_cloud_group_chosen("classes")
        assert calls == [] and extras == [("stop_zone_tool",)]

    def test_restore_puts_the_detector_back(self, ctrl_module, layers, monkeypatch):
        controller, _panel, _iface, _reads, _objects, _extras = self._controller(ctrl_module, layers, monkeypatch)
        calls = []
        monkeypatch.setattr(controller, "_on_class_pick_toggled", lambda on, mode="class": calls.append((on, mode)))
        controller._restore_tool({"class_pipette_on": True, "pc_tool": "similar"})
        assert calls == [(True, "similar")]

    def test_outline_of_the_point_cloud_never_hides_a_raster_one(self, ctrl_module, layers, monkeypatch):
        controller, _panel, _iface, reads, _objects, _extras = self._controller(ctrl_module, layers, monkeypatch)
        controller._kind = _kind(ctrl_module, "RASTER")
        controller._pc_outline_wkt = "BOX 0 0 1 1"
        controller._show_point_cloud_objects()  # a late criteriaChanged of the point cloud panel
        assert reads.outlines == [] and controller._pc_outline_wkt == "BOX 0 0 1 1"


@pytest.mark.unit
class TestStreamRasterStatistics:
    def test_band_display_reads_statistics_only_in_a_worker(self, ctrl_module, layers, adapters, statistics_tasks, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        controller._active_layer = layers["r1"]
        panel = controller._raster_panel = _value_panel()
        panel.current_band.return_value = 1
        panel.display_bands.return_value = (4, 1, 2)
        layers["r1"].bandCount = lambda: 4
        panel.current_quantity_expression.return_value = ''
        panel.histogram_uses_expression.return_value = False
        monkeypatch.setattr(controller, '_base_raster', lambda *_: pytest.fail('band display read pixels on the GUI thread'))
        controller._on_raster_display_changed()
        assert len(statistics_tasks) == 1 and statistics_tasks[0].display_bands == (4, 1, 2)
        controller._on_raster_display_changed()
        assert len(statistics_tasks) == 1, 'reuse a pending request for the same channels'
        panel.display_bands.return_value = (3,)
        controller._on_raster_display_changed()
        assert len(statistics_tasks) == 2 and statistics_tasks[1].display_bands == (3,)
        statistics_tasks[0].cancel.assert_called_once()

    def test_invalid_or_empty_band_choices_restore_the_original_style(self, ctrl_module, layers, adapters):
        controller = ctrl_module.CoverageModeController(_dock())
        controller._active_layer = layers["r1"]
        panel = controller._raster_panel = _value_panel()
        panel.display_bands.return_value = ()
        panel.preview_enabled.return_value = False
        display = controller._raster_band_display = MagicMock()
        controller._on_raster_display_changed()
        display.restore.assert_called_once_with(layers["r1"])
        assert controller._raster_stats_task is None and controller._raster_band_display is None

    @pytest.mark.parametrize("provider,source", [
        ("gdal", "/vsicurl/https://example.test/dem.tif"),
        ("wcs", "url=https://example.test/wcs"),
        ("postgresraster", "dbname=test table=dem"),
    ])
    def test_remote_statistics_never_read_on_ui_thread(self, ctrl_module, adapters, monkeypatch, provider, source):
        layer = FakeLayer("remote", "raster")
        layer.providerType = lambda: provider
        layer.source = lambda: source
        controller = ctrl_module.CoverageModeController(_dock())
        controller._raster_panel = _value_panel()
        requests = []
        monkeypatch.setattr(controller, "_request_raster_statistics", lambda *args: requests.append(args))
        monkeypatch.setattr(controller, "_base_raster", lambda *_: pytest.fail("remote pixels on UI thread"))
        controller._refresh_histogram(layer, 1)
        assert len(requests) == 1
        assert not adapters.calls

    @pytest.mark.parametrize("provider,source", [
        ("wms", "type=xyz&url=https://example.test/{z}/{x}/{y}"),
        ("arcgismapserver", "url=https://example.test/MapServer"),
        ("gdal", "<GDAL_WMS><Service name=\"TMS\"/></GDAL_WMS>"),
    ])
    def test_rendered_images_never_have_value_histograms(self, ctrl_module, adapters, provider, source):
        layer = FakeLayer("rendered", "raster")
        layer.providerType = lambda: provider
        layer.source = lambda: source
        controller = ctrl_module.CoverageModeController(_dock())
        controller._raster_panel = _value_panel()
        controller._refresh_histogram(layer, 1)
        assert not adapters.calls
        controller._raster_panel.set_histogram.assert_not_called()

    def test_superseded_result_is_ignored(self, ctrl_module):
        controller = ctrl_module.CoverageModeController(_dock())
        controller._raster_panel = _value_panel()
        old = MagicMock()
        controller._raster_stats_task = MagicMock()
        controller._raster_statistics_ready(old, True)
        assert controller._histogram_cache == {}
        controller._raster_panel.set_histogram.assert_not_called()

    def test_changed_source_result_is_ignored(self, ctrl_module, adapters):
        layer = FakeLayer("remote", "raster")
        layer.providerType = lambda: "gdal"
        controller = ctrl_module.CoverageModeController(_dock())
        controller._active_layer = layer
        controller._raster_panel = _value_panel()
        controller._raster_panel.current_band.return_value = 1
        task = MagicMock(identity=("remote", "gdal", ("/old.tif", 1, "value")))
        controller._raster_stats_task = task
        controller._raster_statistics_ready(task, True)
        assert controller._histogram_cache == {}
        controller._raster_panel.set_histogram.assert_not_called()

    def test_cancel_invalidates_before_canceling(self, ctrl_module):
        controller = ctrl_module.CoverageModeController(_dock())
        task = MagicMock()
        task.cancel.side_effect = lambda: controller._raster_statistics_ready(task, False)
        controller._raster_stats_task = task
        controller._cancel_raster_statistics()
        task.cancel.assert_called_once()
        assert controller._raster_stats_task is None


@pytest.mark.unit
class TestStreamRasterSampleLifetime:
    def test_retired_capture_stays_protected_until_worker_returns(self, ctrl_module, adapters, monkeypatch):
        controller = ctrl_module.CoverageModeController(_dock())
        module = types.ModuleType(f"{adapters.package.__name__}.cache")
        settled = []
        module.settle = lambda paths: settled.extend(paths)
        monkeypatch.setitem(sys.modules, module.__name__, module)
        adapters.package.cache = module
        controller._raster_sample = (("r1", "gdal", "/vsicurl/a.tif"), "/cache/sample.tif", object())
        task = types.SimpleNamespace()
        controller._borrow_raster_sample(task, "/cache/sample.tif")
        controller._release_raster_sample()
        assert settled == []
        controller._return_raster_sample(task)
        assert settled == ["/cache/sample.tif"]
        assert not controller._raster_sample_users
        controller._return_raster_sample(task)
        assert settled == ["/cache/sample.tif"]

    def test_filtered_remote_source_keeps_remote_capability(self, ctrl_module, adapters):
        layer = FakeLayer("r1", "raster")
        layer.source = lambda: "/cache/filtered.tif"
        adapters.snapshots.derived["r1"] = types.SimpleNamespace(
            original_source="/vsicurl/https://example.test/source.tif", original_provider="gdal")
        controller = ctrl_module.CoverageModeController(_dock())
        assert controller._raster_needs_sample(layer)
        assert controller._raster_identity(layer) == (
            "r1", "gdal", "/vsicurl/https://example.test/source.tif")
        with pytest.raises(RuntimeError, match="sample is not ready"):
            controller._base_raster(layer)

    def test_remote_derivative_surface_is_queued(self, ctrl_module, adapters, monkeypatch):
        layer = FakeLayer("remote", "raster")
        layer.source = lambda: "/vsicurl/https://example.test/source.tif"
        controller = ctrl_module.CoverageModeController(_dock())
        selection = types.SimpleNamespace(band=1, derivative="slope", mode=types.SimpleNamespace(value="range"))
        requested = []
        monkeypatch.setattr(controller, "_request_raster_surface", lambda *args: requested.append(args))
        assert controller._selection_surface(layer, selection) is None
        assert requested[0][:2] == (layer, selection)


@pytest.mark.unit
@pytest.mark.parametrize("action", ["filter", "unfilter", "reset", "undo", "redo", "export"])
def test_gui_actions_cannot_reenter_an_api_operation(ctrl_module, layers, monkeypatch, action):
    layer = layers["r1"]
    controller = ctrl_module.CoverageModeController(_dock(current_layer=layer))
    controller._active_layer = layer
    api_package = types.ModuleType(f"{_PKG}.adapters.public_api")
    api_package.__path__ = []
    operations = types.ModuleType(f"{api_package.__name__}.operations")
    operations.busy_reason = lambda: "FilterMate is already running cross_filter"
    monkeypatch.setitem(sys.modules, api_package.__name__, api_package)
    monkeypatch.setitem(sys.modules, operations.__name__, operations)
    run_filter = MagicMock()
    run_unfilter = MagicMock()
    export_layers = MagicMock(return_value=["r1"])
    monkeypatch.setattr(controller, "_run_filter", run_filter)
    monkeypatch.setattr(controller, "_run_unfilter", run_unfilter)
    monkeypatch.setattr(controller, "_layers_checked_for_export", export_layers)
    assert controller.handle_task(action) is True
    run_filter.assert_not_called()
    run_unfilter.assert_not_called()
    export_layers.assert_not_called()  # no delegation to the vector exporter
    assert not ctrl_module._test_service.calls
    assert ctrl_module._test_feedback.messages[-1][0] == "warning"


@pytest.mark.unit
@pytest.mark.parametrize("torn_down", [False, True])
def test_rendered_filter_pins_capture_until_done(ctrl_module, adapters, layers, monkeypatch, torn_down):
    controller = ctrl_module.CoverageModeController(_dock())
    task = types.SimpleNamespace(error="canceled")
    callbacks = []

    def run(request, source_job, on_done=None):
        callbacks.append(on_done)
        return task
    monkeypatch.setattr(controller.service, "run", run)
    monkeypatch.setattr(controller, "_set_busy", lambda *_: None)
    monkeypatch.setattr(controller, "_after_run", lambda *_: None)
    monkeypatch.setattr(controller, "_map_layer", lambda *_: layers["r1"])
    module = types.ModuleType(f"{adapters.package.__name__}.cache")
    settled = []
    module.settle = lambda paths: settled.extend(paths)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    adapters.package.cache = module
    path = "/cache/rendered_sample.tif"
    controller._raster_sample = (("r1", "wms", "service"), path, object())
    job = types.SimpleNamespace(layer_id="r1", layer_name="r1", kind=_kind(ctrl_module, "RASTER"),
                               _analysis_source=(path, "gdal"))
    controller._start_task(object(), job)
    controller._release_raster_sample()
    assert settled == []
    controller._torn_down = torn_down
    callbacks[0](task, False)
    assert settled == [path]
    assert not controller._raster_sample_users
