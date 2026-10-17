# -*- coding: utf-8 -*-
"""
BackendController (FilterMate 5): the backend badge with raster / point cloud
layers, and the dock state read again on a click.

- ``_update_indicator_display`` called ``layer.featureCount()``, which raster /
  point cloud layers lack: "delegate_update_backend_indicator failed:
  'QgsRasterLayer' object has no attribute 'featureCount'" on every start.
- setup() now runs when the dock is built (the controller registry used to
  stay empty): the first click on the badge no longer runs it lazily, so the
  click reads the dock's optimization settings itself.

The controller is loaded by path under a private package; Qt, QGIS, the base
controller and the SQL helpers are stubs, the badge styles are the real module.
"""
import importlib.util
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_backend_badge_test"


class FakeVectorLayer:
    def __init__(self, layer_id="zones", features=3, provider="ogr", source="/data/zones.shp"):
        self._id, self._features = layer_id, features
        self._provider, self._source = provider, source
        self.counted = 0

    def id(self):
        return self._id

    def name(self):
        return self._id

    def isValid(self):
        return True

    def providerType(self):
        return self._provider

    def source(self):
        return self._source

    def featureCount(self):
        self.counted += 1
        return self._features


class FakeRasterLayer:
    """No featureCount(), like QgsRasterLayer / QgsPointCloudLayer."""

    def id(self):
        return "dem"

    def name(self):
        return "dem"

    def isValid(self):
        return True

    def providerType(self):
        return "gdal"

    def source(self):
        return "/data/dem.tif"


class BaseController:
    def __init__(self, dockwidget, filter_service=None, signal_manager=None):
        self._dockwidget = dockwidget

    @property
    def dockwidget(self):
        return self._dockwidget

    def teardown(self):
        pass


@pytest.fixture
def backend_module(monkeypatch):
    qtcore = types.ModuleType("qgis.PyQt.QtCore")
    qtcore.pyqtSignal = lambda *args: MagicMock()
    qtcore.QCoreApplication = types.SimpleNamespace(translate=lambda context, text: text)
    qgis_core = types.ModuleType("qgis.core")
    qgis_core.QgsVectorLayer = FakeVectorLayer
    monkeypatch.setitem(sys.modules, "qgis.PyQt.QtCore", qtcore)
    monkeypatch.setitem(sys.modules, "qgis.core", qgis_core)
    for name in ("", ".ui", ".ui.controllers", ".ui.styles", ".infrastructure", ".infrastructure.database"):
        package = types.ModuleType(_PKG + name)
        package.__path__ = []
        monkeypatch.setitem(sys.modules, _PKG + name, package)
    base = types.ModuleType(f"{_PKG}.ui.controllers.base_controller")
    base.BaseController = BaseController
    monkeypatch.setitem(sys.modules, base.__name__, base)
    sql_utils = types.ModuleType(f"{_PKG}.infrastructure.database.sql_utils")
    sql_utils.sanitize_sql_identifier = lambda value: value
    monkeypatch.setitem(sys.modules, sql_utils.__name__, sql_utils)
    modules = {}
    for name, path in (("ui.styles.mockup_design", "ui/styles/mockup_design.py"),
                       ("ui.controllers.backend_controller", "ui/controllers/backend_controller.py")):
        spec = importlib.util.spec_from_file_location(f"{_PKG}.{name}", _ROOT / path)
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, spec.name, module)
        spec.loader.exec_module(module)
        modules[name] = module
    return modules["ui.controllers.backend_controller"]


@pytest.fixture
def controller(backend_module):
    dock = MagicMock()
    dock.tr = lambda text: text
    controller = backend_module.BackendController(dock)
    controller._indicator_label = MagicMock()
    return controller


def test_raster_layer_badge_without_feature_count(controller):
    controller.update_for_layer(FakeRasterLayer())
    tooltip = controller._indicator_label.setToolTip.call_args[0][0]
    assert "features" not in tooltip


def test_vector_layer_badge_shows_the_feature_count(controller):
    controller.update_for_layer(FakeVectorLayer(features=1234))
    tooltip = controller._indicator_label.setToolTip.call_args[0][0]
    assert "Layer: zones (1,234 features)" in tooltip


WFS_URI = "typename='ADMINEXPRESS-COG.LATEST:commune' url='https://data.geopf.fr/wfs/ows' version='auto'"


@pytest.mark.parametrize("provider, source", [
    ("WFS", WFS_URI),
    ("OAPIF", "url='https://example.org/ogcapi' typename='communes'"),
    ("arcgisfeatureserver", "url='https://example.org/arcgis/rest/services/x/FeatureServer/0'"),
    ("ogr", "/vsicurl/https://example.org/communes.fgb"),
])
def test_remote_source_badge_is_remote_and_not_counted(controller, provider, source):
    """2026-10-17: a web layer showed "..." and was counted (a network request) on the main thread."""
    layer = FakeVectorLayer("communes", provider=provider, source=source)
    controller.update_for_layer(layer)
    assert controller._indicator_label.setText.call_args[0][0].endswith("Remote")
    tooltip = controller._indicator_label.setToolTip.call_args[0][0]
    assert "Remote" in tooltip and "(? features)" in tooltip
    assert layer.counted == 0


def test_remote_source_after_a_filter_stays_remote(controller):
    """The result handler passes the backend used ('ogr'): the badge keeps saying remote."""
    layer = FakeVectorLayer("communes", provider="WFS", source=WFS_URI)
    controller.update_for_layer(layer, actual_backend="ogr")
    assert "Remote" in controller._indicator_label.setText.call_args[0][0]


def test_auto_selection_does_not_count_a_remote_layer(controller, backend_module, monkeypatch):
    layer = FakeVectorLayer("communes", provider="WFS", source=WFS_URI)
    backends = types.ModuleType(f"{_PKG}.adapters.backends")
    backends.POSTGRESQL_AVAILABLE = False
    utils = types.ModuleType(f"{_PKG}.infrastructure.utils")
    utils.detect_layer_provider_type = lambda _layer: "ogr"
    for name, module in ((".adapters", types.ModuleType(_PKG + ".adapters")), (".adapters.backends", backends),
                         (".infrastructure.utils", utils)):
        module.__path__ = []
        monkeypatch.setitem(sys.modules, _PKG + name, module)
    assert controller._get_optimal_backend_for_layer(layer) == "ogr"
    assert layer.counted == 0


def test_click_reads_the_optimization_settings_of_the_dock(controller):
    dock = controller.dockwidget
    dock.forced_backends = {}
    dock.current_layer = None
    controller._initialized = True  # setup() ran when the dock was built
    dock._optimization_enabled = False  # then the optimization dialog / a restored state
    dock._centroid_auto_enabled = False
    dock._optimization_ask_before = False
    controller._indicator_label.text.return_value = "Vector · OGR"
    controller.handle_indicator_clicked()
    assert (controller.optimization_enabled, controller.centroid_auto_enabled,
            controller._optimization_ask_before) == (False, False, False)


def test_remote_is_a_badge_not_a_backend(controller):
    """"Force REMOTE for All Layers" forced a backend that does not exist: the backend of a remote source is OGR."""
    layer = FakeVectorLayer("communes", provider="WFS", source=WFS_URI)
    assert controller.get_current_backend(layer) == "ogr"
    controller.dockwidget.current_layer = layer
    controller.set_forced_backend("communes", "remote")
    assert controller.forced_backends == {"communes": "ogr"}
    assert "Remote" in controller._indicator_label.setText.call_args[0][0]


def test_remote_geopackage_is_remote_not_spatialite(controller):
    layer = FakeVectorLayer("bati", source="/vsicurl/https://example.org/bdtopo.gpkg|layername=batiment")
    assert controller._detect_backend_for_layer(layer) == "remote"
    assert controller.get_current_backend(layer) == "ogr"
    local = FakeVectorLayer("bati", source="/data/bdtopo.gpkg|layername=batiment")
    assert controller._detect_backend_for_layer(local) == "spatialite"
