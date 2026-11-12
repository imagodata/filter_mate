# -*- coding: utf-8 -*-
"""Configuration tab: switching raster / point cloud layers on or off registers or unregisters them."""
import importlib.util
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_config_controller_test"


@pytest.fixture(scope="module")
def controller_class():
    saved = {name: sys.modules.get(name) for name in ("qgis", "qgis.PyQt", "qgis.PyQt.QtCore")}
    qtcore = MagicMock()
    qtcore.pyqtSignal = MagicMock(side_effect=lambda *a: MagicMock())
    for name, module in (("qgis", MagicMock()), ("qgis.PyQt", MagicMock()), ("qgis.PyQt.QtCore", qtcore)):
        sys.modules[name] = module
    for name, path in (("", _ROOT), (".ui", _ROOT / "ui"), (".ui.controllers", _ROOT / "ui" / "controllers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    base = types.ModuleType(f"{_PKG}.ui.controllers.base_controller")

    class BaseController:
        def __init__(self, dockwidget, *args, **kwargs):
            self.dockwidget = dockwidget

    base.BaseController = BaseController
    sys.modules[base.__name__] = base
    spec = importlib.util.spec_from_file_location(
        f"{_PKG}.ui.controllers.config_controller", _ROOT / "ui" / "controllers" / "config_controller.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    yield module.ConfigController
    for name, module in saved.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module
    for name in [n for n in sys.modules if n.startswith(_PKG)]:
        del sys.modules[name]


def _controller(controller_class, flags):
    """A controller whose flags read ``flags`` (a list, consumed in order)."""
    controller = controller_class.__new__(controller_class)
    controller.dockwidget = MagicMock()
    controller._layer_kind_flags = lambda: flags.pop(0)
    controller._target_option_flags = lambda: None  # the CROSS_FILTER target options: unread here
    return controller


def _timer(controller_class):
    timer = sys.modules[controller_class.__module__].QTimer
    timer.reset_mock(return_value=True, side_effect=True)
    return timer


def test_switch_updates_the_layers_after_the_commit(controller_class):
    """No F5: F5 cancels every running task (exports, height above ground, other plugins)."""
    timer = _timer(controller_class)
    controller = _controller(controller_class, [(True, False)])
    summary = []
    controller._apply_layer_kinds_change((True, True), summary)
    timer.singleShot.assert_called_once_with(0, controller.dockwidget.filter_mate_app.apply_layer_kind_options)
    controller.dockwidget._on_reload_layers_shortcut.assert_not_called()
    assert summary and 'rasters=False' in summary[0]


@pytest.mark.parametrize("before, after", [((True, True), (True, True)), (None, (True, True)), ((True, True), None)])
def test_nothing_when_unchanged_or_unknown(controller_class, before, after):
    timer = _timer(controller_class)
    controller = _controller(controller_class, [after])
    summary = []
    controller._apply_layer_kinds_change(before, summary)
    timer.singleShot.assert_not_called()
    assert summary == []


def test_edit_compares_flags_around_the_save(controller_class):
    """Read before the handlers, compared after the save (the save updates ENV_VARS)."""
    calls = []
    controller = _controller(controller_class, [(False, True), (True, True)])
    controller._initialized = True
    controller.config_changed = MagicMock()
    for name in ('_apply_theme_change', '_apply_ui_profile_change', '_apply_action_bar_position_change',
                 '_apply_export_style_change', '_apply_export_format_change'):
        setattr(controller, name, lambda *a: None)
    controller._save_configuration = lambda: calls.append('save')
    timer = _timer(controller_class)
    timer.singleShot.side_effect = lambda delay, slot: calls.append('schedule')

    item = MagicMock()
    key_item = MagicMock()
    key_item.data.return_value = 'enabled'
    key_item.parent.return_value = None
    item.index.return_value.model.return_value.itemFromIndex.return_value = key_item
    controller.data_changed_configuration_model(item)

    assert calls == ['save', 'schedule']


@pytest.mark.parametrize("attribute", ["filter_mate_app", "app"])
def test_switch_reaches_the_app_of_the_dock(controller_class, attribute):
    """FilterMateApp exposes itself as dock.filter_mate_app; dock.app exists only in its legacy mode."""
    timer = _timer(controller_class)
    controller = _controller(controller_class, [(True, False)])
    app = MagicMock()
    controller.dockwidget = types.SimpleNamespace(**{attribute: app})  # a real dock, not a MagicMock
    summary = []
    controller._apply_layer_kinds_change((True, True), summary)
    timer.singleShot.assert_called_once_with(0, app.apply_layer_kind_options)
    assert summary


def _targets_controller(controller_class, flags):
    """A controller whose CROSS_FILTER target options read ``flags`` (consumed in order)."""
    controller = controller_class.__new__(controller_class)
    controller.dockwidget = MagicMock()
    controller._target_option_flags = lambda: flags.pop(0)
    return controller


def test_target_option_switch_fills_the_targets_list_again(controller_class):
    """vector_source_raster_targets switched: the list is filled again; no layer is registered or dropped."""
    timer = _timer(controller_class)
    controller = _targets_controller(controller_class, [(False, True)])
    summary = []
    controller._apply_target_options_change((True, True), summary)
    properties = controller.dockwidget._controller_integration.property_controller
    timer.singleShot.assert_called_once_with(0, properties.refill_layers_to_filter)
    controller.dockwidget.filter_mate_app.apply_layer_kind_options.assert_not_called()
    assert summary and 'rasters=False' in summary[0]


@pytest.mark.parametrize("before, after", [((True, True), (True, True)), (None, (True, False)), ((True, True), None)])
def test_targets_list_left_alone_when_options_unchanged_or_unknown(controller_class, before, after):
    timer = _timer(controller_class)
    controller = _targets_controller(controller_class, [after])
    summary = []
    controller._apply_target_options_change(before, summary)
    timer.singleShot.assert_not_called()
    assert summary == []


def test_targets_list_needs_the_property_controller(controller_class):
    timer = _timer(controller_class)
    controller = _targets_controller(controller_class, [(True, False)])
    controller.dockwidget = types.SimpleNamespace(_controller_integration=None)
    controller._apply_target_options_change((True, True), [])
    timer.singleShot.assert_not_called()


def test_edit_compares_target_options_around_the_save(controller_class):
    calls = []
    controller = _controller(controller_class, [(True, True), (True, True)])  # layer kinds unchanged
    target_flags = [(True, True), (True, False)]
    controller._target_option_flags = lambda: target_flags.pop(0)
    controller._initialized = True
    controller.config_changed = MagicMock()
    for name in ('_apply_theme_change', '_apply_ui_profile_change', '_apply_action_bar_position_change',
                 '_apply_export_style_change', '_apply_export_format_change'):
        setattr(controller, name, lambda *a: None)
    controller._save_configuration = lambda: calls.append('save')
    timer = _timer(controller_class)
    timer.singleShot.side_effect = lambda delay, slot: calls.append(('schedule', slot))

    item = MagicMock()
    key_item = MagicMock()
    key_item.data.return_value = 'vector_source_point_cloud_targets'
    key_item.parent.return_value = None
    item.index.return_value.model.return_value.itemFromIndex.return_value = key_item
    controller.data_changed_configuration_model(item)

    properties = controller.dockwidget._controller_integration.property_controller
    assert calls == ['save', ('schedule', properties.refill_layers_to_filter)]


def test_configuration_reload_fills_the_targets_list_again(monkeypatch):
    """ConfigModelManager reads config.json again when the tab opens: a hand-edited option counts too."""
    pkg = "fm_config_model_manager_test"
    for name, path in ((pkg, _ROOT), (f"{pkg}.ui", _ROOT / "ui"), (f"{pkg}.ui.managers", _ROOT / "ui" / "managers"),
                       (f"{pkg}.infrastructure", None), (f"{pkg}.infrastructure.utils", None)):
        package = types.ModuleType(name)
        package.__path__ = [str(path)] if path else []
        monkeypatch.setitem(sys.modules, name, package)
    atomic_io = types.ModuleType(f"{pkg}.infrastructure.utils.atomic_io")
    atomic_io.atomic_json_write = MagicMock()
    monkeypatch.setitem(sys.modules, atomic_io.__name__, atomic_io)
    spec = importlib.util.spec_from_file_location(f"{pkg}.ui.managers.config_model_manager",
                                                  _ROOT / "ui" / "managers" / "config_model_manager.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    timer = MagicMock()
    monkeypatch.setitem(sys.modules, "qgis.PyQt.QtCore", types.SimpleNamespace(QTimer=timer))

    dock = MagicMock()
    manager = module.ConfigModelManager(dock)
    flags = [(True, True), (False, True)]
    manager._target_option_flags = lambda: flags.pop(0)
    manager._realign_target_options((True, True))  # unchanged: nothing
    timer.singleShot.assert_not_called()
    manager._realign_target_options((True, True))
    timer.singleShot.assert_called_once_with(0, dock._controller_integration.property_controller.refill_layers_to_filter)


def test_show_error_reaches_the_message_bar_with_the_message_first(controller_class, monkeypatch):
    """The import pointed at config.feedback_config (gone) and the arguments were swapped:
    infrastructure.feedback.show_error(message, title)."""
    pkg = controller_class.__module__.split(".ui.")[0]
    shown = []
    feedback = types.ModuleType(f"{pkg}.infrastructure.feedback")
    feedback.show_error = lambda message, title="FilterMate": shown.append((message, title))
    infrastructure = types.ModuleType(f"{pkg}.infrastructure")
    infrastructure.__path__ = []
    infrastructure.feedback = feedback
    monkeypatch.setitem(sys.modules, infrastructure.__name__, infrastructure)
    monkeypatch.setitem(sys.modules, feedback.__name__, feedback)
    controller = controller_class.__new__(controller_class)

    logged = []
    monkeypatch.setattr(sys.modules[controller_class.__module__].logger, "error", logged.append)

    controller._show_error("something broke")

    assert shown == [("something broke", "FilterMate")]
    assert logged and "something broke" in logged[0]  # also in the log, whatever the message bar shows
