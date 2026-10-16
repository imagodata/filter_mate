# -*- coding: utf-8 -*-
"""
Controller lifecycle: a real ControllerIntegration and ControllerRegistry on a
minimal stand-in dock.

Until FilterMate 5 the registry stayed empty in production: ``if not
self._registry`` read the length of a new registry (``__len__``), so nothing
was registered and ``setup_all`` / ``teardown_all`` did nothing. The raster /
point cloud controller never connected to the project (stored filters not
replayed when a project is opened again) and the Configuration tab never
applied nor saved an edit (``ConfigController._initialized`` stayed False).

The integration, the registry, the coverage and the configuration controllers
are the real modules, loaded under a private package; the other controllers
are stubs recording their setup / teardown.
"""
import importlib.util
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_ctrl_lifecycle_test"


class FakeSignal:
    def __init__(self, *args):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def disconnect(self, slot=None):
        if slot is None:
            self.slots.clear()
            return
        if slot not in self.slots:
            raise TypeError("not connected")
        self.slots.remove(slot)

    def emit(self, *args):
        for slot in list(self.slots):
            slot(*args)


class FakeTimer:
    scheduled = []

    @classmethod
    def singleShot(cls, delay, callback):
        cls.scheduled.append((delay, callback))


class FakeProject:
    def __init__(self):
        self.readProject = FakeSignal()
        self.cleared = FakeSignal()
        self.layersWillBeRemoved = FakeSignal()


class BaseController:
    """Stand-in for base_controller.BaseController (a QObject with an ABC metaclass)."""

    def __init__(self, dockwidget, filter_service=None, signal_manager=None):
        self._dockwidget = dockwidget
        self._is_active = False

    @property
    def dockwidget(self):
        return self._dockwidget

    def tr(self, text):
        return text

    def on_tab_activated(self):
        self._is_active = True

    def on_tab_deactivated(self):
        self._is_active = False

    def _disconnect_all_signals(self):
        return 0

    def setup(self):
        pass

    def teardown(self):
        pass


def _stub_controller(class_name, signals=()):
    def __init__(self, dockwidget, *args, **kwargs):
        BaseController.__init__(self, dockwidget)
        self.calls = []
        for signal in signals:
            setattr(self, signal, FakeSignal())

    return type(class_name, (BaseController,), {
        '__init__': __init__,
        'setup': lambda self: self.calls.append('setup'),
        'teardown': lambda self: self.calls.append('teardown'),
    })


_STUBS = {
    'exploring_controller': ('ExploringController', ()),
    'filtering_controller': ('FilteringController', ()),
    'exporting_controller': ('ExportingController', ()),
    'backend_controller': ('BackendController', ('backend_changed', 'reload_requested')),
    'layer_sync_controller': ('LayerSyncController', ('layer_synchronized', 'sync_blocked', 'layer_changed')),
    'favorites_controller': ('FavoritesController', ('favorites_changed', 'favorite_applied')),
    'property_controller': ('PropertyController', ('property_changed', 'property_error', 'buffer_style_changed')),
    'ui_layout_controller': ('UILayoutController', ()),
}


class FakeTabs:
    def __init__(self):
        self.currentChanged = FakeSignal()


class FakeDock:
    """The attributes ControllerIntegration reads; no Qt widget."""

    def __init__(self):
        self.current_layer = None
        self._exploring_cache = None
        self.tabTools = FakeTabs()


def _load(name, path):
    spec = importlib.util.spec_from_file_location(f"{_PKG}.ui.controllers.{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project(monkeypatch):
    project = FakeProject()
    qgis_core = types.ModuleType("qgis.core")
    qgis_core.QgsProject = types.SimpleNamespace(instance=lambda: project)
    qtcore = types.ModuleType("qgis.PyQt.QtCore")
    qtcore.pyqtSignal = FakeSignal
    qtcore.QTimer = FakeTimer
    qtcore.Qt = MagicMock()
    qtcore.QCoreApplication = MagicMock()
    monkeypatch.setitem(sys.modules, "qgis.core", qgis_core)
    monkeypatch.setitem(sys.modules, "qgis.PyQt.QtCore", qtcore)
    FakeTimer.scheduled = []
    return project


@pytest.fixture
def integration_module(monkeypatch, project):
    # Empty package paths: the lazy imports of the real controllers (cross filter
    # service, pdal, dock additions) fail and are skipped, as they allow.
    for name in ("", ".ui", ".ui.controllers"):
        package = types.ModuleType(_PKG + name)
        package.__path__ = []
        monkeypatch.setitem(sys.modules, _PKG + name, package)
    base = types.ModuleType(f"{_PKG}.ui.controllers.base_controller")
    base.BaseController = BaseController
    monkeypatch.setitem(sys.modules, base.__name__, base)
    for module_name, (class_name, signals) in _STUBS.items():
        module = types.ModuleType(f"{_PKG}.ui.controllers.{module_name}")
        setattr(module, class_name, _stub_controller(class_name, signals))
        monkeypatch.setitem(sys.modules, module.__name__, module)
    controllers = _ROOT / "ui" / "controllers"
    for name in ("registry", "config_controller", "coverage_mode_controller", "integration"):
        monkeypatch.setitem(sys.modules, f"{_PKG}.ui.controllers.{name}", None)  # removed after the test
        _load(name, controllers / f"{name}.py")
    return sys.modules[f"{_PKG}.ui.controllers.integration"]


@pytest.fixture
def integration(integration_module):
    integration = integration_module.ControllerIntegration(FakeDock())
    assert integration.setup()
    return integration


def _stubs(integration):
    return [integration.exploring_controller, integration.filtering_controller, integration.exporting_controller,
            integration.backend_controller, integration.layer_sync_controller, integration.favorites_controller,
            integration.property_controller, integration.ui_layout_controller]


def test_a_new_registry_is_truthy(integration_module):
    registry_module = sys.modules[f"{_PKG}.ui.controllers.registry"]
    assert registry_module.ControllerRegistry()


def test_setup_registers_and_sets_up_every_controller(integration):
    assert len(integration.registry) == 10
    assert all(controller.calls == ['setup'] for controller in _stubs(integration))
    assert integration.validate_controllers()['all_valid']


def test_coverage_controller_connects_to_the_project_and_schedules_the_replay(integration, project):
    coverage = integration.coverage_controller
    assert project.readProject.slots == [coverage._on_project_read]
    assert project.cleared.slots == [coverage._on_project_cleared]
    assert project.layersWillBeRemoved.slots == [coverage._on_layers_removed]
    assert (1500, coverage.replay_stored_filters) in FakeTimer.scheduled


def test_config_controller_applies_edits(integration):
    assert integration.config_controller._initialized


def test_teardown_disconnects_the_coverage_controller_from_the_project(integration, project):
    stubs = _stubs(integration)
    coverage = integration.coverage_controller
    integration.teardown()
    assert coverage._torn_down
    assert not (project.readProject.slots or project.cleared.slots or project.layersWillBeRemoved.slots)
    assert all(controller.calls == ['setup', 'teardown'] for controller in stubs)
    assert integration.coverage_controller is None


def test_closing_the_dock_keeps_the_controllers(integration, project):
    coverage = integration.coverage_controller
    coverage._deactivate_pixel_tool = MagicMock()
    integration.on_dock_closed()
    coverage._deactivate_pixel_tool.assert_called_once_with()
    assert integration.coverage_controller is coverage
    assert project.readProject.slots == [coverage._on_project_read]
    assert all(controller.calls == ['setup'] for controller in _stubs(integration))


def test_tab_change_notifies_the_previous_and_the_new_tab(integration):
    tabs = integration._dockwidget.tabTools
    exporting, config = integration.exporting_controller, integration.config_controller
    tabs.currentChanged.emit(1)  # EXPORTING
    assert exporting._is_active
    tabs.currentChanged.emit(2)  # CONFIGURATION
    assert not exporting._is_active and config._is_active


def test_teardown_all_goes_on_when_a_controller_fails(integration_module):
    registry_module = sys.modules[f"{_PKG}.ui.controllers.registry"]
    registry = registry_module.ControllerRegistry()
    failing, other = _stub_controller('Failing')(None), _stub_controller('Other')(None)
    failing.teardown = MagicMock(side_effect=RuntimeError("wrapped C/C++ object has been deleted"))
    registry.register('other', other)
    registry.register('failing', failing)
    assert registry.teardown_all() == 1
    assert other.calls == ['teardown']
