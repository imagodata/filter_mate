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

    controller._show_error("something broke")

    assert shown == [("something broke", "FilterMate")]
