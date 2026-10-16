# -*- coding: utf-8 -*-
"""FilterMate 5 Processing algorithms — audit 2026-10.

* the ``feedback`` (progress bar, Cancel button) reaches the operations;
* ``MAX_PIXELS`` / ``RESOLUTION`` left empty use the FilterMate settings
  instead of overriding them with fixed values;
* ``LAYERS_FILTERED`` / ``LAYERS_FAILED`` are declared outputs (QGIS 3.28+).

The root conftest mocks ``qgis.core`` with MagicMock instances, and a class
deriving from one is a mock too: the algorithms are loaded here against a
small ``qgis.core`` made of real classes, under a synthetic package (their
relative imports reach ``core``); ``operations`` is a recording stand-in.
"""
import importlib
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_PKG = "fm_processing_test"


class _Parameter:
    def __init__(self, name, description="", *args, **kwargs):
        self._name, self.description, self.args, self.kwargs = name, description, args, kwargs
        self._flags = 0

    def name(self):
        return self._name

    def flags(self):
        return self._flags

    def setFlags(self, flags):
        self._flags = flags


class _Number(_Parameter):
    Type = types.SimpleNamespace(Integer=0, Double=1)


class _Algorithm:
    Flag = types.SimpleNamespace(FlagNoThreading=4)

    def __init__(self):
        self.parameters_declared, self.outputs_declared = {}, {}

    def flags(self):
        return 0

    def addParameter(self, parameter):
        self.parameters_declared[parameter.name()] = parameter

    def addOutput(self, output):
        self.outputs_declared[output.name()] = output

    # parameterAs*: the parameters dict holds ready values.
    def _value(self, parameters, name, default=None):
        value = parameters.get(name)
        if value is None:
            value = self.parameters_declared[name].kwargs.get("defaultValue", default)
        return value

    def parameterAsVectorLayer(self, parameters, name, context):
        return parameters.get(name)

    parameterAsRasterLayer = parameterAsLayer = parameterAsVectorLayer

    def parameterAsLayerList(self, parameters, name, context):
        return list(parameters.get(name) or [])

    def parameterAsBoolean(self, parameters, name, context):
        return bool(self._value(parameters, name, False))

    def parameterAsInt(self, parameters, name, context):
        return int(self._value(parameters, name, 0) or 0)

    def parameterAsDouble(self, parameters, name, context):
        return float(self._value(parameters, name, 0.0) or 0.0)

    def parameterAsEnum(self, parameters, name, context):
        return int(self._value(parameters, name, 0) or 0)

    def parameterAsEnums(self, parameters, name, context):
        return list(self._value(parameters, name, []) or [])

    def parameterAsString(self, parameters, name, context):
        return str(self._value(parameters, name, "") or "")

    def parameterAsGeometry(self, parameters, name, context):
        return parameters.get(name)

    def parameterAsGeometryCrs(self, parameters, name, context):
        return types.SimpleNamespace(isValid=lambda: True)


class _Geometry:
    def isEmpty(self):
        return False


def _qgis_core(with_variant_output=True):
    core = types.ModuleType("qgis.core")
    core.QgsProcessing = types.SimpleNamespace(
        SourceType=types.SimpleNamespace(TypeMapLayer=0, TypeVectorAnyGeometry=1, TypePointCloud=8))
    core.Qgis = types.SimpleNamespace(ProcessingParameterFlag=types.SimpleNamespace(Advanced=2))
    core.QgsProcessingAlgorithm = _Algorithm
    core.QgsGeometry = _Geometry
    core.QgsProcessingException = type("QgsProcessingException", (Exception,), {})
    core.QgsProcessingParameterNumber = _Number
    core.QgsProcessingParameterDefinition = types.SimpleNamespace(FlagAdvanced=2)
    for name in ("Boolean", "Enum", "MultipleLayers", "String", "Band", "Distance", "Extent", "Geometry",
                 "RasterLayer", "VectorLayer", "PointCloudLayer", "Crs", "FolderDestination", "Expression"):
        setattr(core, f"QgsProcessingParameter{name}", type(name, (_Parameter,), {}))
    core.QgsProcessingOutputMultipleLayers = type("OutputMultipleLayers", (_Parameter,), {})
    core.QgsProcessingProvider = type("QgsProcessingProvider", (), {})
    core.QgsProcessingModelAlgorithm = type("QgsProcessingModelAlgorithm", (), {})
    core.QgsApplication = types.SimpleNamespace()
    if with_variant_output:
        core.QgsProcessingOutputVariant = type("OutputVariant", (_Parameter,), {})
    return core


class _Recorder(types.ModuleType):
    """``adapters.public_api.operations`` stand-in: records each call, returns an empty report."""

    def __init__(self, name):
        super().__init__(name)
        self.calls = []

    def __getattr__(self, operation):
        if operation.startswith("__"):
            raise AttributeError(operation)
        from fm_processing_test.core.domain.api_requests import OperationReport

        def record(*args, **kwargs):
            self.calls.append((operation, args, kwargs))
            report = OperationReport()
            report.done["L1"] = "parcelle"
            return report
        return record


@pytest.fixture
def load(monkeypatch):
    """``load(with_variant_output)`` -> (common, cross_filter_algorithm, layer_operations, operations recorder)."""
    def _load(with_variant_output=True):
        monkeypatch.setitem(sys.modules, "qgis.core", _qgis_core(with_variant_output))
        for name in [module for module in sys.modules if module.startswith(_PKG)]:
            monkeypatch.delitem(sys.modules, name)
        for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.domain", _ROOT / "core" / "domain"),
                           (".adapters", _ROOT / "adapters"), (".adapters.public_api", _ROOT / "adapters" / "public_api"),
                           (".infrastructure", _ROOT / "infrastructure"), (".processing", _ROOT / "processing"),
                           (".processing.algorithms", _ROOT / "processing" / "algorithms")):
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]
            monkeypatch.setitem(sys.modules, _PKG + name, package)
        recorder = _Recorder(f"{_PKG}.adapters.public_api.operations")
        monkeypatch.setitem(sys.modules, recorder.__name__, recorder)
        sys.modules[f"{_PKG}.adapters.public_api"].operations = recorder
        modules = [importlib.import_module(f"{_PKG}.processing.algorithms.{name}")
                   for name in ("common", "cross_filter_algorithm", "layer_operations_algorithms")]
        return (*modules, recorder)
    return _load


class _Feedback:
    def pushInfo(self, *args):
        pass

    pushWarning = reportError = pushInfo


class _Context:
    def project(self):
        return "project"


def _run(algorithm_class, parameters):
    algorithm = algorithm_class()
    algorithm.initAlgorithm()
    feedback = _Feedback()
    result = algorithm.processAlgorithm(parameters, _Context(), feedback)
    return algorithm, feedback, result


class _VectorSource:
    def selectedFeatureCount(self):
        return 0

    def featureCount(self):
        return 3


class TestFeedbackReachesTheOperations:
    def test_cross_filter_family(self, load):
        _, cross, _, recorder = load()
        for algorithm_class, parameters in (
                (cross.CrossFilterAlgorithm, {"SOURCE": _VectorSource(), "TARGETS": ["t"]}),
                (cross.CrossFilterFromRasterAlgorithm, {"SOURCE": "mnt", "MINIMUM": 1.0}),
                (cross.CrossFilterFromPointCloudAlgorithm, {"SOURCE": "lhd", "CLASSES": "6"}),
                (cross.CrossFilterFromGeometryAlgorithm, {"GEOMETRY": _Geometry(), "TARGETS": ["t"]})):
            _, feedback, _ = _run(algorithm_class, parameters)
            assert recorder.calls[-1][2]["feedback"] is feedback, algorithm_class.__name__

    def test_point_cloud_filter_and_favorite(self, load):
        _, _, layer_operations, recorder = load()
        _, feedback, _ = _run(layer_operations.FilterPointCloudAlgorithm, {"LAYERS": ["lhd"], "CLASSES": "2"})
        assert recorder.calls[-1][0] == "filter_point_clouds" and recorder.calls[-1][2]["feedback"] is feedback
        _, feedback, _ = _run(layer_operations.ApplyFavoriteAlgorithm, {"FAVORITE": "Zone humide"})
        assert recorder.calls[-1][0] == "apply_favorite" and recorder.calls[-1][2]["feedback"] is feedback


class TestSettingsNotOverridden:
    def test_raster_max_pixels_empty_uses_the_setting(self, load):
        _, cross, _, recorder = load()
        algorithm, _, _ = _run(cross.CrossFilterFromRasterAlgorithm, {"SOURCE": "mnt", "MINIMUM": 1.0})
        assert recorder.calls[-1][2]["max_pixels"] is None
        assert algorithm.parameters_declared["MAX_PIXELS"].kwargs.get("optional") is True

    def test_raster_max_pixels_given_is_passed(self, load):
        _, cross, _, recorder = load()
        _run(cross.CrossFilterFromRasterAlgorithm, {"SOURCE": "mnt", "MINIMUM": 1.0, "MAX_PIXELS": 250000})
        assert recorder.calls[-1][2]["max_pixels"] == 250000

    def test_point_cloud_resolution_empty_uses_the_setting(self, load):
        _, cross, _, recorder = load()
        _run(cross.CrossFilterFromPointCloudAlgorithm, {"SOURCE": "lhd", "CLASSES": "6"})
        assert recorder.calls[-1][2]["footprint_resolution"] is None
        _run(cross.CrossFilterFromPointCloudAlgorithm, {"SOURCE": "lhd", "CLASSES": "6", "RESOLUTION": 0.5})
        assert recorder.calls[-1][2]["footprint_resolution"] == 0.5


class TestNamesOutputsDeclared:
    def test_declared_when_qgis_can_describe_a_list(self, load):
        _, cross, _, _ = load()
        algorithm, _, result = _run(cross.CrossFilterAlgorithm, {"SOURCE": _VectorSource(), "TARGETS": ["t"]})
        assert {"OUTPUT", "LAYERS_FILTERED", "LAYERS_FAILED"} <= set(algorithm.outputs_declared)
        assert result["LAYERS_FILTERED"] == ["parcelle"] and result["LAYERS_FAILED"] == []

    def test_older_qgis_keeps_returning_them(self, load):
        _, cross, _, _ = load(with_variant_output=False)
        algorithm, _, result = _run(cross.CrossFilterAlgorithm, {"SOURCE": _VectorSource(), "TARGETS": ["t"]})
        assert set(algorithm.outputs_declared) == {"OUTPUT"}
        assert result["LAYERS_FILTERED"] == ["parcelle"]


class TestQgisProcessExit:
    """qgis_process never unloads the plugin: the derived files of the run are purged at exit."""

    def _provider(self, load, monkeypatch, iface):
        load()
        monkeypatch.setattr(sys.modules["qgis.utils"], "iface", iface, raising=False)
        registered = []
        monkeypatch.setattr("atexit.register", registered.append)
        provider = importlib.import_module(f"{_PKG}.processing.provider")
        provider.FilterMateProcessingProvider()
        provider.FilterMateProcessingProvider()  # registered once
        return provider, registered

    def test_headless_registers_the_purge_once(self, load, monkeypatch):
        provider, registered = self._provider(load, monkeypatch, iface=None)
        assert registered == [provider._purge_cache_at_exit]

    def test_gui_leaves_it_to_the_plugin_unload(self, load, monkeypatch):
        _, registered = self._provider(load, monkeypatch, iface=object())
        assert registered == []

    def test_purge_calls_the_cache(self, load, monkeypatch):
        provider, _ = self._provider(load, monkeypatch, iface=None)
        purged = []
        cache = types.SimpleNamespace(purge_session=lambda: purged.append(True))
        for name in (".adapters.qgis", ".adapters.qgis.coverage_layers"):
            package = types.ModuleType(_PKG + name)
            package.__path__ = []
            monkeypatch.setitem(sys.modules, _PKG + name, package)
        sys.modules[f"{_PKG}.adapters.qgis.coverage_layers"].cache = cache
        provider._purge_cache_at_exit()
        assert purged == [True]
