# -*- coding: utf-8 -*-
"""FilterMate 5 vector targets: the features a previous subset hides, memory layers."""
import importlib.util
import pathlib
import sys

import pytest

pytest.importorskip("osgeo.ogr")

pytestmark = pytest.mark.unit


def _fakes():
    if "fm_coverage_fakes" not in sys.modules:
        spec = importlib.util.spec_from_file_location("fm_coverage_fakes", pathlib.Path(__file__).with_name("coverage_fakes.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules["fm_coverage_fakes"] = module
        spec.loader.exec_module(module)
    return sys.modules["fm_coverage_fakes"]


fk = _fakes()
appliers = fk.load("target_appliers")
geometry_tools = fk.load("geometry_tools")
source_jobs = fk.load("source_jobs")
task_module = fk.load("cross_filter_task")
domain = fk.load("core.domain.cross_filter")
LayerKind = fk.load("core.domain.layer_kind").LayerKind

ZONES = {
    1: ('east_a', (700, 400, 800, 500)),
    2: ('east_b', (600, 100, 650, 150)),
    3: ('straddle', (450, 600, 550, 700)),
    4: ('west_a', (100, 400, 200, 500)),
    5: ('west_b', (50, 800, 100, 900)),
}
EAST_HALF = (500, 0, 1000, 1000)


def _box(xmin, ymin, xmax, ymax):
    return fk.FakeGeometry.fromRect(fk.FakeRectangle(xmin, ymin, xmax, ymax))


class FakeFeature:
    def __init__(self, fid, geometry):
        self._fid, self._geometry = fid, geometry

    def id(self):
        return self._fid

    def geometry(self):
        return self._geometry

    def attribute(self, name):
        return self._fid


class FakeProvider:
    """Holds the subset string, like QGIS providers do."""

    def __init__(self, subset=''):
        self.subset = subset
        self.calls = []

    def subsetString(self):
        return self.subset

    def setSubsetString(self, subset, *args):
        self.calls.append(('setSubsetString', subset))
        self.subset = subset
        return True

    def blockSignals(self, block):
        self.calls.append(('blockSignals', block))
        return not block


class FakeVectorLayer:
    """Features visible through the provider subset ``ids:1,2`` (empty: all)."""

    DATA = {}  # source -> {fid: geometry}, what a layer opened again reads

    class LayerOptions:
        def __init__(self, *args):
            self.loadDefaultStyle, self.skipCrsValidation = True, False

    def __init__(self, source, name='zones', provider='ogr', options=None, features=None, subset=''):
        self.options = options
        self._source, self._name, self._provider_type = source, name, provider
        if features is not None:
            FakeVectorLayer.DATA[source] = features
        # A memory layer opened again is a new, empty layer.
        self.features = dict(features if features is not None else
                             ({} if provider == 'memory' else FakeVectorLayer.DATA.get(source, {})))
        self.provider = FakeProvider(subset)

    def id(self):
        return f"{self._name}_id"

    def name(self):
        return self._name

    def crs(self):
        return fk.FakeCrs('EPSG:2154')

    def source(self):
        return self._source

    def providerType(self):
        return self._provider_type

    def isValid(self):
        return True

    def geometryType(self):
        return 2

    def dataProvider(self):
        return self.provider

    def subsetString(self):
        return self.provider.subset

    def setSubsetString(self, subset):
        return self.provider.setSubsetString(subset)

    def triggerRepaint(self):
        pass

    def visible(self):
        subset = self.provider.subset
        if not subset:
            return dict(self.features)
        if subset.startswith('ids:'):
            ids = {int(v) for v in subset[4:].split(',') if v}
            return {fid: g for fid, g in self.features.items() if fid in ids}
        raise AssertionError(f"the fake cannot read {subset!r}")


class FakeFeatureSource:
    """QgsVectorLayerFeatureSource: the features visible when it is created."""

    def __init__(self, layer):
        self._features = layer.visible()

    def getFeatures(self, request=None):
        return [FakeFeature(fid, fk.FakeGeometry(g)) for fid, g in sorted(self._features.items())]


@pytest.fixture
def engine(monkeypatch):
    fk.install(monkeypatch, appliers, geometry_tools, source_jobs, task_module)
    monkeypatch.setattr(appliers, 'QgsVectorLayer', FakeVectorLayer)
    monkeypatch.setattr(appliers, 'QgsVectorLayerFeatureSource', FakeFeatureSource)
    FakeVectorLayer.DATA.clear()
    return appliers


def _zones(provider='ogr', subset=''):
    features = {fid: _box(*box) for fid, (_, box) in ZONES.items()}
    return FakeVectorLayer('/data/zones.gpkg|layername=zones', provider=provider, features=features, subset=subset)


def _request(*predicates, operator=None, buffer=0.0):
    return domain.CrossFilterRequest('source', LayerKind.RASTER, predicates=predicates or ('Intersect',),
                                     buffer_value=buffer, other_layers_combine_operator=operator)


def _kept(job):
    expression = job._expression
    if expression == '1 = 0':
        return []
    inside = expression[expression.index('(') + 1:expression.rindex(')')]
    return sorted(ZONES[int(v)][0] for v in inside.split(','))


def _run(job, source_geometry, request):
    job.compute(source_geometry, fk.FakeCrs('EPSG:2154'), None, request, lambda: False)
    assert job.outcome.success, job.outcome.message
    return _kept(job)


class TestPreviousSubset:
    """Replace mode (no operator) must not depend on what the previous subset hid."""

    def test_replace_tests_the_hidden_features(self, engine):
        layer = _zones(subset='ids:4')  # west_a only, from a previous filter
        job = engine.VectorTargetJob(layer, None)
        assert _run(job, _box(*EAST_HALF), _request()) == ['east_a', 'east_b', 'straddle']

    def test_replace_result_is_applied_alone(self, engine):
        layer = _zones(subset='ids:4')
        job = engine.VectorTargetJob(layer, None)
        _run(job, _box(*EAST_HALF), _request())
        job.apply(layer)
        assert layer.subsetString() == 'FID IN (1, 2, 3)'

    @pytest.mark.parametrize("operator, expected", [('AND', []), ('AND NOT', [])])
    def test_and_reads_the_filtered_layer(self, engine, operator, expected):
        """(previous) AND (...) only keeps previous features: no need to read the others."""
        layer = _zones(subset='ids:4')
        job = engine.VectorTargetJob(layer, operator)
        assert _run(job, _box(*EAST_HALF), _request(operator=operator)) == expected
        assert getattr(job, '_unfiltered', None) is None

    def test_or_tests_the_hidden_features(self, engine):
        layer = _zones(subset='ids:4')
        job = engine.VectorTargetJob(layer, 'OR')
        assert _run(job, _box(*EAST_HALF), _request(operator='OR')) == ['east_a', 'east_b', 'straddle']

    def test_copy_without_crs_prompt_nor_style(self, engine, monkeypatch):
        made = []

        class Recorded(FakeVectorLayer):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                made.append(self)

        monkeypatch.setattr(engine, 'QgsVectorLayer', Recorded)
        engine.VectorTargetJob(_zones(subset='ids:4'), None)
        assert made[0].options.skipCrsValidation is True and made[0].options.loadDefaultStyle is False

    def test_layer_that_cannot_be_reopened_fails_by_name(self, engine, monkeypatch):
        class Invalid(FakeVectorLayer):
            def isValid(self):
                return False

        layer = _zones(subset='ids:4')
        monkeypatch.setattr(engine, 'QgsVectorLayer', Invalid)
        job = engine.VectorTargetJob(layer, None)
        job.compute(_box(*EAST_HALF), fk.FakeCrs('EPSG:2154'), None, _request(), lambda: False)
        assert not job.outcome.success and 'without its current filter' in job.outcome.message


class TestMemoryLayer:
    """A memory layer opened again is empty: its own features are read, its subset left out."""

    @pytest.mark.parametrize("operator", [None, 'OR'])
    def test_hidden_features_are_tested(self, engine, operator):
        layer = _zones(provider='memory', subset='ids:4')
        job = engine.VectorTargetJob(layer, operator)
        assert _run(job, _box(*EAST_HALF), _request(operator=operator)) == ['east_a', 'east_b', 'straddle']

    def test_subset_back_and_signals_blocked(self, engine):
        layer = _zones(provider='memory', subset='ids:4')
        engine.VectorTargetJob(layer, None)
        assert layer.subsetString() == 'ids:4'
        assert layer.provider.calls == [('blockSignals', True), ('setSubsetString', ''),
                                        ('setSubsetString', 'ids:4'), ('blockSignals', False)]

