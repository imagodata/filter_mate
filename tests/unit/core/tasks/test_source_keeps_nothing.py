# -*- coding: utf-8 -*-
"""
2026-11-12: a source filter expression that keeps no feature never filters the
targets by the whole source layer.

The source filter is queued for the main thread, so in the worker the source
layer still shows everything: the SpatiaLite FALLBACK mode and its "final
fallback", and the OGR EXPRESSION_FALLBACK (empty result or parse error), used
every feature of the layer. They now raise ``SourceSelectionError``, which the
geometry preparation lets through its backend fallbacks and the filtering
orchestrator shows to the user.

The modules are loaded inside a private package whose sub-packages point at
the repository folders, so their relative imports find the real files.
"""
import importlib.util
import logging
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[4]
_PKG = "fmtest_srcnothing_pkg"


def _module(name, path=None, **attrs):
    mod = types.ModuleType(name)
    if path is not None:
        mod.__path__ = [str(path)]
    mod.__package__ = name
    for key, value in attrs.items():
        setattr(mod, key, value)
    sys.modules[name] = mod
    return mod


def _load(dotted, relpath):
    full = f"{_PKG}.{dotted}"
    if full in sys.modules:
        return sys.modules[full]
    spec = importlib.util.spec_from_file_location(full, _ROOT / relpath)
    module = importlib.util.module_from_spec(spec)
    module.__package__ = full.rpartition('.')[0]
    sys.modules[full] = module
    spec.loader.exec_module(module)
    return module


def _packages():
    if _PKG in sys.modules:
        return
    sys.modules.setdefault("qgis", MagicMock())
    sys.modules.setdefault("qgis.core", MagicMock())
    sys.modules.setdefault("qgis.PyQt", MagicMock())
    sys.modules.setdefault("qgis.PyQt.QtCore", MagicMock())
    _module(_PKG, _ROOT)
    _module(f"{_PKG}.adapters", _ROOT / "adapters")
    _module(f"{_PKG}.adapters.backends", _ROOT / "adapters" / "backends")
    _module(f"{_PKG}.adapters.backends.spatialite", _ROOT / "adapters" / "backends" / "spatialite")
    _module(f"{_PKG}.adapters.backends.ogr", _ROOT / "adapters" / "backends" / "ogr")
    _module(f"{_PKG}.adapters.repositories", _ROOT / "adapters" / "repositories")
    _module(f"{_PKG}.adapters.repositories.history_repository", HistoryRepository=MagicMock())
    _module(f"{_PKG}.adapters.qgis", _ROOT / "adapters" / "qgis")
    _module(f"{_PKG}.adapters.qgis.source_capability_probe", capability_for_layer=lambda layer: None)
    _module(f"{_PKG}.core", _ROOT / "core")
    _module(f"{_PKG}.core.tasks", _ROOT / "core" / "tasks")
    _module(f"{_PKG}.core.services", _ROOT / "core" / "services")
    _module(f"{_PKG}.infrastructure", _ROOT / "infrastructure")
    _module(f"{_PKG}.infrastructure.logging",
            setup_logger=lambda name, *args, **kwargs: logging.getLogger(name))
    _module(f"{_PKG}.infrastructure.constants", PROVIDER_POSTGRES="postgresql")
    _module(f"{_PKG}.infrastructure.utils", is_layer_valid=lambda layer: True)
    _module(f"{_PKG}.infrastructure.parallel", ParallelFilterExecutor=MagicMock(), ParallelConfig=MagicMock())
    _module(f"{_PKG}.config", _ROOT / "config")
    _module(f"{_PKG}.config.config", ENV_VARS={})


@pytest.fixture
def qgis(monkeypatch):
    """qgis.core with a QgsExpression whose parse result the test sets, plain translations."""
    _packages()
    core = sys.modules["qgis.core"]
    state = SimpleNamespace(parse_error=False)

    class _Expression:
        def __init__(self, text):
            self.text = text

        def hasParserError(self):
            return state.parse_error

        def parserErrorString(self):
            return "syntax error"

    class _Request:
        def __init__(self, *args):
            self.args = args  # (expression,) for a filtered request

        def setNoAttributes(self):
            return self

    monkeypatch.setattr(core, "QgsExpression", _Expression, raising=False)
    monkeypatch.setattr(core, "QgsFeatureRequest", _Request, raising=False)
    monkeypatch.setattr(sys.modules["qgis.PyQt.QtCore"], "QCoreApplication",
                        SimpleNamespace(translate=lambda context, text: text), raising=False)
    return state


def _refusal_class():
    return _load("adapters.backends.source_refusal", "adapters/backends/source_refusal.py").SourceSelectionError


class _Layer:
    """A source layer with no subset, no selection and 12 features; the expression keeps ``kept``."""

    def __init__(self, kept=()):
        self.kept = list(kept)
        self.requests = []

    def name(self):
        return "routes"

    def id(self):
        return "routes_id"

    def subsetString(self):
        return ""

    def selectedFeatureCount(self):
        return 0

    def featureCount(self):
        return 12

    def crs(self):
        return "EPSG:2154"

    def getFeatures(self, request=None):
        self.requests.append(request)
        if request is not None and getattr(request, "args", None):
            return iter(self.kept)  # filtered by the expression
        return iter([MagicMock(name=f"feature{i}") for i in range(12)])  # the whole layer


# ---------------------------------------------------------------------------
# SpatiaLite
# ---------------------------------------------------------------------------

def _spatialite_context(mod, layer, expression):
    return mod.SpatialiteSourceContext(
        source_layer=layer,
        task_parameters={"task": {"features": []}},
        expression=expression,
    )


def test_spatialite_expression_keeping_nothing_is_refused(qgis):
    mod = _load("adapters.backends.spatialite.filter_executor", "adapters/backends/spatialite/filter_executor.py")
    layer = _Layer(kept=[])

    with pytest.raises(_refusal_class(), match="keeps no feature"):
        mod.prepare_spatialite_source_geom(_spatialite_context(mod, layer, '"class" = \'none\''))

    assert all(getattr(request, "args", None) for request in layer.requests), "the whole layer was read"


def test_spatialite_unreadable_expression_is_refused(qgis):
    mod = _load("adapters.backends.spatialite.filter_executor", "adapters/backends/spatialite/filter_executor.py")
    qgis.parse_error = True

    with pytest.raises(_refusal_class(), match="cannot be evaluated"):
        mod.prepare_spatialite_source_geom(_spatialite_context(mod, _Layer(kept=[]), 'CAST("x" AS TEXT) GLOB'))


def test_spatialite_fallback_reads_the_features_of_the_expression(qgis):
    mod = _load("adapters.backends.spatialite.filter_executor", "adapters/backends/spatialite/filter_executor.py")
    kept = [MagicMock(name="kept")]
    layer = _Layer(kept=kept)
    context = _spatialite_context(mod, layer, '"class" = \'major\'')

    mode, metadata = mod.determine_spatialite_source_mode(context)
    features, recovery = mod.resolve_spatialite_features(context, mode, metadata)

    assert mode == mod.SourceMode.FALLBACK
    assert features == kept


def test_spatialite_fallback_without_expression_keeps_every_feature(qgis):
    mod = _load("adapters.backends.spatialite.filter_executor", "adapters/backends/spatialite/filter_executor.py")
    context = _spatialite_context(mod, _Layer(), None)

    mode, metadata = mod.determine_spatialite_source_mode(context)
    features, _ = mod.resolve_spatialite_features(context, mode, metadata)

    assert len(features) == 12


# ---------------------------------------------------------------------------
# OGR
# ---------------------------------------------------------------------------

def _ogr_context(mod, layer, expression, memory=None):
    return mod.OGRSourceContext(
        source_layer=layer,
        task_parameters={"task": {"features": []}},
        expression=expression,
        create_memory_layer_from_features=memory,
    )


def test_ogr_expression_keeping_nothing_is_refused(qgis):
    mod = _load("adapters.backends.ogr.filter_executor", "adapters/backends/ogr/filter_executor.py")
    memory = MagicMock()

    with pytest.raises(_refusal_class(), match="keeps no feature"):
        mod.prepare_ogr_source_geom(_ogr_context(mod, _Layer(kept=[]), '"class" = \'none\'', memory))

    memory.assert_not_called()


def test_ogr_unreadable_expression_is_refused(qgis):
    mod = _load("adapters.backends.ogr.filter_executor", "adapters/backends/ogr/filter_executor.py")
    qgis.parse_error = True

    with pytest.raises(_refusal_class(), match="cannot be evaluated"):
        mod.prepare_ogr_source_geom(_ogr_context(mod, _Layer(kept=[]), '"class" =', MagicMock()))


def test_ogr_expression_features_become_the_source(qgis):
    mod = _load("adapters.backends.ogr.filter_executor", "adapters/backends/ogr/filter_executor.py")
    kept = [MagicMock(name="kept")]
    memory_layer = MagicMock()
    memory_layer.featureCount.return_value = 1
    memory = MagicMock(return_value=memory_layer)
    mod_validate = mod.validate_ogr_result_layer
    try:
        mod.validate_ogr_result_layer = lambda layer: (layer is memory_layer, None)
        result = mod.prepare_ogr_source_geom(_ogr_context(mod, _Layer(kept=kept), '"class" = \'major\'', memory))
    finally:
        mod.validate_ogr_result_layer = mod_validate

    assert result is memory_layer
    assert memory.call_args[0][0] == kept


# ---------------------------------------------------------------------------
# Geometry preparation and orchestrator
# ---------------------------------------------------------------------------

def test_geometry_preparer_lets_the_refusal_through(qgis):
    mod = _load("core.services.geometry_preparer", "core/services/geometry_preparer.py")
    refusal = _refusal_class()
    ogr_callback = MagicMock()

    def spatialite_callback():
        raise refusal("The source filter of 'routes' keeps no feature")

    with pytest.raises(refusal):
        mod.prepare_geometries_by_provider(
            provider_list=['spatialite'], task_parameters={'task': {'features': []}},
            source_layer=_Layer(), param_source_provider_type='spatialite', param_buffer_expression='',
            layers_dict={}, prepare_postgresql_geom_callback=MagicMock(),
            prepare_spatialite_geom_callback=spatialite_callback, prepare_ogr_geom_callback=ogr_callback,
            logger=logging.getLogger("test"), postgresql_available=False)

    ogr_callback.assert_not_called()  # no OGR fallback, no source layer used whole


def test_orchestrator_shows_the_refusal_and_leaves_the_targets(qgis):
    mod = _load("core.tasks.filtering_orchestrator", "core/tasks/filtering_orchestrator.py")
    refusal = _refusal_class()
    source = MagicMock()
    source.name.return_value = "routes"

    def distant():
        raise refusal("The source filter of 'routes' keeps no feature: the target layers were not filtered.")

    result = mod.FilteringOrchestrator().execute_filtering(
        task_parameters={
            "task": {"features": [], "expression": '"class" = \'none\'', "layers": [{"layer_name": "batiments"}]},
            "filtering": {"has_geometric_predicates": True, "has_layers_to_filter": True,
                          "geometric_predicates": ["Intersect"]},
        },
        source_layer=source, layers={"ogr": [(MagicMock(), {})]}, layers_count=1, current_predicates={},
        initialize_current_predicates_callback=lambda: None,
        execute_source_layer_filtering_callback=lambda: True,
        manage_distant_layers_callback=distant,
        is_canceled_callback=lambda: False, set_progress_callback=lambda percent: None,
    )

    assert result['success'] is False
    assert result['message'] == "The source filter of 'routes' keeps no feature: the target layers were not filtered."
