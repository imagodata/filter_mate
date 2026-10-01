# -*- coding: utf-8 -*-
"""
PointCloudUIController (WP-F): takes over the current-layer change and the
dock's action buttons when the current layer is a point cloud, and hands the
dock back to the vector chain otherwise.

The controller is loaded by path under a private synthetic package where
BaseController, the capability and adapter modules (WP-C), the service and
the widget are stubs: nothing here depends on the real modules of the other
work packages.
"""
import importlib.util
import pathlib
import sys
import types
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

_PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_pc_controller_test"


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _Result:
    success: bool
    subset_string: str
    previous_subset: str = ""
    message: str = ""


class _Criteria:
    def __init__(self, subset):
        self.subset = subset

    @property
    def is_empty(self):
        return not self.subset

    def to_subset_string(self):
        return self.subset


class FakeBaseController:
    def __init__(self, dockwidget, filter_service=None, signal_manager=None):
        self._dockwidget = dockwidget
        self._filter_service = filter_service
        self._signal_manager = signal_manager
        self._is_active = False
        self._connection_ids = []

    @property
    def dockwidget(self):
        return self._dockwidget

    def tr(self, text):
        return text

    def _disconnect_all_signals(self):
        self._connection_ids.clear()
        return 0


class FakeWidget:
    fail_init = False
    instances = []

    def __init__(self, parent=None):
        if FakeWidget.fail_init:
            raise RuntimeError("no Qt")
        self.parent = parent
        self.visible = True
        self.populated = []
        self.current_subsets = []
        self.reset_calls = 0
        self.deleted = False
        self.next_criteria = _Criteria("Classification = 2")
        FakeWidget.instances.append(self)

    def setVisible(self, visible):
        self.visible = bool(visible)

    def isHidden(self):
        return not self.visible

    def populate(self, summary):
        self.populated.append(summary)

    def criteria(self):
        return self.next_criteria

    def reset(self):
        self.reset_calls += 1

    def set_current_subset(self, text):
        self.current_subsets.append(text)

    def deleteLater(self):
        self.deleted = True


class FakeService:
    instances = []
    accept = True

    def __init__(self, apply_subset, read_subset, history_service=None):
        self.apply_subset = apply_subset
        self.read_subset = read_subset
        self.history_service = history_service
        self.calls = []
        FakeService.instances.append(self)

    def apply(self, layer, criteria, combine_with_existing=False):
        self.calls.append(("apply", layer, criteria, combine_with_existing))
        subset = criteria.to_subset_string()
        if FakeService.accept:
            layer.subset = subset
            return _Result(True, subset, "")
        return _Result(False, subset, "", "rejected")

    def clear(self, layer):
        self.calls.append(("clear", layer))
        layer.subset = ""
        return _Result(True, "", "")

    def current_subset(self, layer):
        return self.read_subset(layer)


class _Layer:
    def __init__(self, layer_id, point_cloud=False, valid=True):
        self._id = layer_id
        self.point_cloud = point_cloud
        self.valid = valid
        self.subset = ""
        self.subsetStringChanged = MagicMock()
        self.selectionChanged = MagicMock()
        self.triggerRepaint_calls = 0

    def id(self):
        return self._id

    def name(self):
        return self._id

    def isValid(self):
        return self.valid

    def subsetString(self):
        return self.subset

    def triggerRepaint(self):
        self.triggerRepaint_calls += 1


SUMMARY = object()


def _package(name):
    module = types.ModuleType(name)
    module.__path__ = []
    module.__package__ = name
    sys.modules[name] = module
    return module


def _stub(name, **attrs):
    module = types.ModuleType(name)
    for attr, value in attrs.items():
        setattr(module, attr, value)
    sys.modules[name] = module
    return module


def _load_controller_module():
    for name in (_PKG, f"{_PKG}.ui", f"{_PKG}.ui.controllers", f"{_PKG}.ui.widgets", f"{_PKG}.adapters",
                 f"{_PKG}.adapters.qgis", f"{_PKG}.core", f"{_PKG}.core.services", f"{_PKG}.infrastructure"):
        _package(name)
    _stub(f"{_PKG}.ui.controllers.base_controller", BaseController=FakeBaseController)
    _stub(f"{_PKG}.ui.widgets.point_cloud_filter_widget", PointCloudFilterWidget=FakeWidget)
    _stub(f"{_PKG}.adapters.qgis.point_cloud_capability",
          is_point_cloud_layer=lambda layer: bool(getattr(layer, "point_cloud", False)))
    adapter = _stub(f"{_PKG}.adapters.qgis.point_cloud_layer_adapter",
                    read_point_cloud_summary=MagicMock(return_value=SUMMARY),
                    apply_point_cloud_subset=MagicMock(return_value=True),
                    get_point_cloud_subset=lambda layer: layer.subsetString())
    _stub(f"{_PKG}.core.services.point_cloud_filter_service", PointCloudFilterService=FakeService)
    feedback = _stub(f"{_PKG}.infrastructure.feedback", show_info=MagicMock(), show_warning=MagicMock())
    _stub(f"{_PKG}.infrastructure.utils", is_layer_valid=lambda layer: layer is not None and layer.isValid())

    name = f"{_PKG}.ui.controllers.point_cloud_ui_controller"
    path = _PROJECT_ROOT / "ui" / "controllers" / "point_cloud_ui_controller.py"
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    module.__package__ = f"{_PKG}.ui.controllers"
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module, adapter, feedback


_controller_module, _adapter, _feedback = _load_controller_module()
PointCloudUIController = _controller_module.PointCloudUIController


# ---------------------------------------------------------------------------
# Fake dock widget
# ---------------------------------------------------------------------------

class _Widget:
    def __init__(self, name, visible=True):
        self.name = name
        self.visible = visible
        self.enabled = True
        self.checked = True
        self.calls = []

    def setVisible(self, visible):
        self.calls.append(("setVisible", bool(visible)))
        self.visible = bool(visible)

    def isHidden(self):
        return not self.visible

    def setEnabled(self, enabled):
        self.calls.append(("setEnabled", bool(enabled)))
        self.enabled = bool(enabled)

    def setChecked(self, checked):
        self.calls.append(("setChecked", bool(checked)))
        self.checked = bool(checked)

    def isChecked(self):
        return self.checked

    def blockSignals(self, blocked):
        self.calls.append(("blockSignals", bool(blocked)))

    def __repr__(self):
        return f"<{self.name}>"


class _Item:
    def __init__(self, widget=None, layout=None):
        self._widget = widget
        self._layout = layout

    def widget(self):
        return self._widget

    def layout(self):
        return self._layout


class _Layout:
    def __init__(self, name, items=()):
        self.name = name
        self.items = list(items)
        self.inserted = []
        self.removed = []

    def objectName(self):
        return self.name

    def count(self):
        return len(self.items)

    def itemAt(self, index):
        return self.items[index]

    def insertWidget(self, index, widget):
        self.inserted.append((index, widget))
        self.items.insert(index, _Item(widget=widget))

    def removeWidget(self, widget):
        self.removed.append(widget)
        self.items = [item for item in self.items if item.widget() is not widget]


class _Dock:
    def __init__(self):
        self.current_layer = None
        self.PROJECT_LAYERS = {}
        self.widget_filtering_keys = _Widget("keys")
        self.checkBox_filtering_use_centroids_source_layer = _Widget("centroids")
        self.comboBox_filtering_current_layer = MagicMock()
        self.comboBox_filtering_current_layer.currentLayer.return_value = None
        self.source_row_combo = _Widget("source_combo")
        self.horizontalLayout_filtering_source_layer = _Layout(
            "horizontalLayout_filtering_source_layer",
            [_Item(widget=self.source_row_combo), _Item(widget=self.checkBox_filtering_use_centroids_source_layer)])
        self.predicates = _Widget("predicates")
        self.buffer_a = _Widget("buffer_a")
        self.buffer_b = _Widget("buffer_b", visible=False)
        self.verticalLayout_filtering_values = _Layout("verticalLayout_filtering_values", [
            _Item(layout=self.horizontalLayout_filtering_source_layer),
            _Item(),
            _Item(widget=self.predicates),
            _Item(layout=_Layout("horizontalLayout_filtering_buffer", [_Item(widget=self.buffer_a), _Item(widget=self.buffer_b)])),
        ])
        self.frame_exploring = _Widget("frame_exploring")
        self.pushButton_checkable_filtering_layers_to_filter = _Widget("layers_to_filter")
        self.currentLayerChanged = MagicMock()
        self.app = MagicMock()
        self.app.history_manager = object()
        self.current_layer_selection_connection = None
        self.on_layer_selection_changed = MagicMock()

    def vector_widgets(self):
        return (self.widget_filtering_keys, self.checkBox_filtering_use_centroids_source_layer,
                self.predicates, self.buffer_a, self.buffer_b)


@pytest.fixture(autouse=True)
def _reset_stubs():
    FakeWidget.fail_init = False
    FakeWidget.instances = []
    FakeService.instances = []
    FakeService.accept = True
    _adapter.read_point_cloud_summary.reset_mock()
    _adapter.read_point_cloud_summary.return_value = SUMMARY
    _feedback.show_info.reset_mock()
    _feedback.show_warning.reset_mock()
    yield


@pytest.fixture
def dock():
    return _Dock()


@pytest.fixture
def controller(dock):
    ctrl = PointCloudUIController(dockwidget=dock, filter_service=None, signal_manager=None)
    ctrl.setup()
    ctrl._ensure_widget()
    return ctrl


def _pc(layer_id="pc1"):
    return _Layer(layer_id, point_cloud=True)


def _vector(layer_id="v1"):
    return _Layer(layer_id)


# ---------------------------------------------------------------------------
# Setup / teardown
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSetup:

    def test_panel_inserted_after_the_source_row_and_hidden(self, controller, dock):
        widget = controller.widget
        assert isinstance(widget, FakeWidget)
        assert widget.parent is dock
        assert dock.verticalLayout_filtering_values.inserted == [(1, widget)]
        assert widget.visible is False

    def test_setup_alone_builds_nothing(self, dock):
        ctrl = PointCloudUIController(dockwidget=dock)

        ctrl.setup()

        assert ctrl.widget is None
        assert dock.verticalLayout_filtering_values.inserted == []
        assert FakeService.instances == []

    def test_panel_built_lazily_on_first_point_cloud_selection(self, dock):
        ctrl = PointCloudUIController(dockwidget=dock)
        ctrl.setup()

        assert ctrl.on_current_layer_changed(_pc()) is True

        assert isinstance(ctrl.widget, FakeWidget)
        assert dock.verticalLayout_filtering_values.inserted == [(1, ctrl.widget)]

    def test_service_built_with_the_adapter_callables_and_the_app_history(self, controller, dock):
        service = FakeService.instances[-1]
        assert service.apply_subset is _adapter.apply_point_cloud_subset
        assert service.read_subset is _adapter.get_point_cloud_subset
        assert service.history_service is dock.app.history_manager

    def test_history_bound_lazily_when_the_app_arrives_later(self, dock):
        dock.app = None
        ctrl = PointCloudUIController(dockwidget=dock)
        ctrl.setup()
        ctrl._ensure_widget()
        assert FakeService.instances[-1].history_service is None

        dock.app = MagicMock()
        dock.app.history_manager = object()
        ctrl.on_current_layer_changed(_pc())
        ctrl.handle_task('filter')

        assert FakeService.instances[-1].history_service is dock.app.history_manager

    def test_setup_survives_a_panel_failure(self, dock):
        FakeWidget.fail_init = True
        ctrl = PointCloudUIController(dockwidget=dock)

        ctrl.setup()

        assert ctrl.widget is None
        assert dock.verticalLayout_filtering_values.inserted == []
        assert ctrl.on_current_layer_changed(_pc()) is False
        assert ctrl.handle_task('filter') is False

    def test_teardown_restores_the_dock_and_removes_the_panel(self, controller, dock):
        widget = controller.widget
        controller.on_current_layer_changed(_pc())

        controller.teardown()

        assert controller.widget is None
        assert controller.active_layer is None
        assert dock.verticalLayout_filtering_values.removed == [widget]
        assert widget.deleted is True
        assert dock.predicates.visible is True
        assert dock.frame_exploring.enabled is True


# ---------------------------------------------------------------------------
# Layer change
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestLayerChange:

    def test_point_cloud_activates_the_panel(self, controller, dock):
        layer = _pc()

        assert controller.on_current_layer_changed(layer) is True

        assert controller.active_layer is layer
        assert dock.current_layer is layer
        _adapter.read_point_cloud_summary.assert_called_once_with(layer)
        assert controller.widget.populated == [SUMMARY]
        assert controller.widget.visible is True
        for widget in dock.vector_widgets():
            assert widget.visible is False, widget
        assert dock.source_row_combo.calls == []
        assert dock.frame_exploring.enabled is False
        assert dock.pushButton_checkable_filtering_layers_to_filter.checked is False
        assert dock.pushButton_checkable_filtering_layers_to_filter.enabled is False
        dock.currentLayerChanged.emit.assert_called_once_with()
        dock.app.update_undo_redo_buttons.assert_called_once_with()
        layer.subsetStringChanged.connect.assert_called_once_with(controller._on_subset_changed)

    def test_layer_combo_synchronized_with_signals_blocked(self, controller, dock):
        layer = _pc()
        combo = dock.comboBox_filtering_current_layer

        controller.on_current_layer_changed(layer)

        combo.setLayer.assert_called_once_with(layer)
        assert [call.args for call in combo.blockSignals.call_args_list] == [(True,), (False,)]

    def test_layer_combo_left_alone_when_already_on_the_layer(self, controller, dock):
        layer = _pc()
        dock.comboBox_filtering_current_layer.currentLayer.return_value = layer

        controller.on_current_layer_changed(layer)

        dock.comboBox_filtering_current_layer.setLayer.assert_not_called()

    def test_vector_layer_after_point_cloud_restores_the_dock(self, controller, dock):
        layer = _pc()
        controller.on_current_layer_changed(layer)

        assert controller.on_current_layer_changed(_vector()) is False

        assert controller.active_layer is None
        assert controller.widget.visible is False
        assert dock.predicates.visible is True
        assert dock.buffer_a.visible is True
        assert dock.buffer_b.visible is False
        assert dock.widget_filtering_keys.visible is True
        assert dock.checkBox_filtering_use_centroids_source_layer.visible is True
        assert dock.frame_exploring.enabled is True
        button = dock.pushButton_checkable_filtering_layers_to_filter
        assert button.enabled is True
        assert button.checked is True, "the pre-activation checked state must be restored"
        # setChecked() must always be wrapped in blockSignals(): unwrapped, it would
        # emit toggled() -> ... -> settingLayerVariable.emit(QgsVectorLayer, ...) with
        # a point cloud as dw.current_layer, a sip TypeError.
        assert button.calls.count(("blockSignals", True)) == 2
        assert button.calls.count(("blockSignals", False)) == 2
        layer.subsetStringChanged.disconnect.assert_called_once_with(controller._on_subset_changed)

    def test_vector_layer_alone_has_no_effect(self, controller, dock):
        assert controller.on_current_layer_changed(_vector()) is False

        assert dock.current_layer is None
        for widget in dock.vector_widgets():
            assert widget.calls == [], widget
        dock.currentLayerChanged.emit.assert_not_called()
        assert controller.widget.populated == []

    def test_vector_layer_selection_signal_disconnected_when_a_point_cloud_takes_over(self, controller, dock):
        old_vector = _vector()
        dock.current_layer = old_vector
        dock.current_layer_selection_connection = "connected"

        controller.on_current_layer_changed(_pc())

        old_vector.selectionChanged.disconnect.assert_called_once_with(dock.on_layer_selection_changed)
        assert dock.current_layer_selection_connection is None

    def test_no_disconnect_attempted_without_a_prior_selection_connection(self, controller, dock):
        old_vector = _vector()
        dock.current_layer = old_vector
        dock.current_layer_selection_connection = None

        controller.on_current_layer_changed(_pc())

        old_vector.selectionChanged.disconnect.assert_not_called()

    def test_none_layer_has_no_effect(self, controller, dock):
        assert controller.on_current_layer_changed(None) is False
        assert dock.current_layer is None

    def test_switching_between_two_point_clouds(self, controller, dock):
        first, second = _pc("pc1"), _pc("pc2")
        controller.on_current_layer_changed(first)

        assert controller.on_current_layer_changed(second) is True

        assert controller.active_layer is second
        first.subsetStringChanged.disconnect.assert_called_once_with(controller._on_subset_changed)
        second.subsetStringChanged.connect.assert_called_once_with(controller._on_subset_changed)
        assert controller.widget.populated == [SUMMARY, SUMMARY]
        assert dock.predicates.visible is False

    def test_same_point_cloud_twice_connects_once(self, controller):
        layer = _pc()
        controller.on_current_layer_changed(layer)
        controller.on_current_layer_changed(layer)
        assert layer.subsetStringChanged.connect.call_count == 1

    def test_summary_failure_still_activates(self, controller, dock):
        _adapter.read_point_cloud_summary.side_effect = RuntimeError("stats")
        layer = _pc()
        try:
            assert controller.on_current_layer_changed(layer) is True
        finally:
            _adapter.read_point_cloud_summary.side_effect = None
        assert controller.active_layer is layer
        assert controller.widget.populated == []

    def test_subset_signal_refreshes_the_label(self, controller):
        layer = _pc()
        controller.on_current_layer_changed(layer)
        layer.subset = "Z >= 10"

        controller._on_subset_changed()

        assert controller.widget.current_subsets[-1] == "Z >= 10"


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestHandleTask:

    def test_no_active_layer_is_not_handled(self, controller):
        assert controller.handle_task('filter') is False
        assert FakeService.instances[-1].calls == []

    def test_filter_applies_the_criteria_and_refreshes(self, controller, dock):
        layer = _pc()
        dock.PROJECT_LAYERS = {"pc1": {"infos": {"is_already_subset": False}}}
        controller.on_current_layer_changed(layer)
        dock.app.update_undo_redo_buttons.reset_mock()
        criteria = _Criteria("Classification IN (2, 6)")
        controller.widget.next_criteria = criteria

        assert controller.handle_task('filter') is True

        service = FakeService.instances[-1]
        assert service.calls == [("apply", layer, criteria, False)]
        assert layer.triggerRepaint_calls == 1
        dock.app.iface.mapCanvas.return_value.refresh.assert_called_once_with()
        dock.app.update_undo_redo_buttons.assert_called_once_with()
        assert controller.widget.current_subsets[-1] == "Classification IN (2, 6)"
        assert dock.PROJECT_LAYERS["pc1"]["infos"]["is_already_subset"] is True
        _feedback.show_info.assert_called_once()
        assert "Classification IN (2, 6)" in _feedback.show_info.call_args.args[0]
        _feedback.show_warning.assert_not_called()

    def test_filter_with_empty_criteria_warns_without_applying(self, controller):
        controller.on_current_layer_changed(_pc())
        controller.widget.next_criteria = _Criteria("")

        assert controller.handle_task('filter') is True

        assert FakeService.instances[-1].calls == []
        _feedback.show_warning.assert_called_once()

    def test_rejected_filter_warns(self, controller, dock):
        controller.on_current_layer_changed(_pc())
        FakeService.accept = False

        assert controller.handle_task('filter') is True

        _feedback.show_warning.assert_called_once()
        assert "rejected" in _feedback.show_warning.call_args.args[0]
        _feedback.show_info.assert_not_called()

    def test_unfilter_clears(self, controller, dock):
        layer = _pc()
        layer.subset = "Z >= 10"
        dock.PROJECT_LAYERS = {"pc1": {"infos": {"is_already_subset": True}}}
        controller.on_current_layer_changed(layer)

        assert controller.handle_task('unfilter') is True

        assert FakeService.instances[-1].calls == [("clear", layer)]
        assert controller.widget.reset_calls == 0
        assert controller.widget.current_subsets[-1] == ""
        assert dock.PROJECT_LAYERS["pc1"]["infos"]["is_already_subset"] is False
        assert layer.triggerRepaint_calls == 1
        dock.app.iface.mapCanvas.return_value.refresh.assert_called_once_with()

    def test_reset_resets_the_panel_and_clears(self, controller):
        layer = _pc()
        controller.on_current_layer_changed(layer)

        assert controller.handle_task('reset') is True

        assert controller.widget.reset_calls == 1
        assert FakeService.instances[-1].calls == [("clear", layer)]

    def test_undo_and_redo_go_through_the_app(self, controller, dock):
        controller.on_current_layer_changed(_pc())
        dock.app.update_undo_redo_buttons.reset_mock()

        assert controller.handle_task('undo') is True
        dock.app.handle_undo.assert_called_once_with()
        assert controller.handle_task('redo') is True
        dock.app.handle_redo.assert_called_once_with()
        assert dock.app.update_undo_redo_buttons.call_count == 2
        assert FakeService.instances[-1].calls == []

    def test_export_is_refused_with_a_warning(self, controller, dock):
        controller.on_current_layer_changed(_pc())

        assert controller.handle_task('export') is True

        _feedback.show_warning.assert_called_once()
        assert "Export" in _feedback.show_warning.call_args.args[0]

    def test_unknown_task_is_handled_and_swallowed(self, controller):
        controller.on_current_layer_changed(_pc())
        assert controller.handle_task('add_layers') is True
        assert FakeService.instances[-1].calls == []

    def test_deleted_layer_releases_the_panel(self, controller, dock):
        layer = _pc()
        controller.on_current_layer_changed(layer)
        layer.valid = False

        assert controller.handle_task('filter') is False

        assert controller.active_layer is None
        assert dock.current_layer is None
        assert dock.predicates.visible is True

    def test_current_layer_replaced_behind_the_panel_releases_it(self, controller, dock):
        controller.on_current_layer_changed(_pc())
        dock.current_layer = _vector()

        assert controller.handle_task('filter') is False

        assert controller.active_layer is None
        assert dock.predicates.visible is True

    def test_service_exception_is_reported_and_still_handled(self, controller):
        controller.on_current_layer_changed(_pc())
        controller.widget.next_criteria = None

        assert controller.handle_task('filter') is True

        _feedback.show_warning.assert_called_once()

    def test_undo_without_app_is_handled(self, controller, dock):
        controller.on_current_layer_changed(_pc())
        dock.app = None

        assert controller.handle_task('undo') is True
