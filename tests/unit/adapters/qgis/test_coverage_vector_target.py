# -*- coding: utf-8 -*-
"""FilterMate 5 vector targets: the features a previous subset hides, memory layers, per-feature predicates."""
import importlib.util
import pathlib
import sys
import types
from unittest.mock import MagicMock

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
    monkeypatch.setattr(appliers, 'Qgis', types.SimpleNamespace(
        GeometryType=types.SimpleNamespace(Point=0, Line=1, Polygon=2)))
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

    @pytest.mark.parametrize("source_kind", [LayerKind.RASTER, LayerKind.POINT_CLOUD])
    def test_centroid_choice_is_applied_for_coverage_sources(self, engine, source_kind):
        layer = _zones()
        request = domain.CrossFilterRequest('source', source_kind,
                                            targets=(domain.TargetSpec(layer.id(), LayerKind.VECTOR, use_centroids=True),))
        job = engine.VectorTargetJob(layer, None)
        assert _run(job, _box(510, 0, 1000, 1000), request) == ['east_a', 'east_b']

    def test_centroid_choice_is_specific_to_the_target(self, engine):
        layer = _zones()
        request = domain.CrossFilterRequest('source', LayerKind.RASTER,
                                            targets=(domain.TargetSpec('another_target', LayerKind.VECTOR, use_centroids=True),))
        assert _run(engine.VectorTargetJob(layer, None), _box(510, 0, 1000, 1000), request) == ['east_a', 'east_b', 'straddle']

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


class TestEmptiedTarget:
    """2026-10-18: a target left with ``1 = 0`` was reported "filtered" like any other."""

    FAR = (5000, 5000, 5100, 5100)  # meets no zone

    @pytest.mark.parametrize("subset, operator, emptied", [
        ('', None, True), ('ids:4', None, True), ('ids:4', 'AND', True), ('', 'OR', True),
        ('ids:4', 'OR', False), ('ids:4', 'AND NOT', False)])
    def test_nothing_kept(self, engine, subset, operator, emptied):
        job = engine.VectorTargetJob(_zones(subset=subset), operator)
        assert _run(job, _box(*self.FAR), _request(operator=operator)) == []
        assert job.outcome.kept_count == 0 and job.outcome.emptied is emptied

    def test_something_kept(self, engine):
        job = engine.VectorTargetJob(_zones(), None)
        _run(job, _box(*EAST_HALF), _request())
        assert not job.outcome.emptied


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


# Buildings: one in east_a, one in west_a, one in no zone.
BUILDINGS = [(710, 410, 720, 420), (110, 410, 120, 420), (300, 300, 310, 310)]


class FakeSourceLayer(FakeVectorLayer):
    def __init__(self):
        super().__init__('/data/buildings.gpkg|layername=b', name='buildings', features={})


def _task_kept(predicates, buffer=0.0, buildings=BUILDINGS):
    """Vector source (three buildings) -> zones, through the task as the API runs it."""
    source = source_jobs.VectorSourceJob(FakeSourceLayer(), [FakeFeature(i, _box(*b)) for i, b in enumerate(buildings)])
    layer = _zones()
    job = appliers.VectorTargetJob(layer, None)
    request = _request(*predicates, buffer=buffer)
    task = task_module.CrossFilterTask('t', request, source, [job])
    task.isCanceled = lambda: False
    assert task.run(), task.error
    assert job.outcome.success, job.outcome.message
    return _kept(job)


class TestPredicatesPerSourceFeature:
    """Like native:selectbylocation and the dock's OGR backend: at least one selected feature."""

    def test_contains_one_of_the_selected_features(self, engine):
        assert _task_kept(('Contain',)) == ['east_a', 'west_a']

    def test_contains_with_a_buffer(self, engine):
        assert _task_kept(('Contain',), buffer=1.0) == ['east_a', 'west_a']

    def test_disjoint_from_every_selected_feature(self, engine):
        assert _task_kept(('Disjoint',)) == ['east_b', 'straddle', 'west_b']

    def test_intersect_and_contain_together(self, engine):
        assert _task_kept(('Intersect', 'Contain')) == ['east_a', 'west_a']

    def test_one_feature_needs_no_parts(self, engine):
        source = source_jobs.VectorSourceJob(FakeSourceLayer(), [FakeFeature(0, _box(*BUILDINGS[0]))])
        source.compute(_request('Contain'), lambda: False)
        assert source.parts(_request('Contain')) is None

    def test_intersect_alone_uses_the_union(self, engine):
        source = source_jobs.VectorSourceJob(FakeSourceLayer(), [FakeFeature(i, _box(*b)) for i, b in enumerate(BUILDINGS)])
        source.compute(_request('Intersect'), lambda: False)
        assert source.parts(_request('Intersect')) is None

    def test_parts_only_for_vector_targets(self, engine, monkeypatch):
        """Vector source -> raster / point cloud targets (the dock): the features are not buffered one by one."""
        source = source_jobs.VectorSourceJob(FakeSourceLayer(), [FakeFeature(i, _box(*b)) for i, b in enumerate(BUILDINGS)])
        monkeypatch.setattr(source, 'parts', lambda request: pytest.fail("parts built without a vector target"))

        class RasterJob:
            layer_name = 'dem'

            def compute(self, *args):
                pass

        task = task_module.CrossFilterTask('t', _request('Contain'), source, [RasterJob()])
        task.isCanceled = lambda: False
        assert task.run()

    def test_every_feature_erased_by_the_buffer_matches_nothing(self, engine):
        """A negative buffer erasing each building, not their union: Contain keeps nothing (no silent union test)."""
        block = [(710, 410, 720, 420), (720, 410, 730, 420), (710, 420, 720, 430), (720, 420, 730, 430)]
        assert _task_kept(('Contain',), buffer=-6.0, buildings=block) == []


class _KeyField:
    def __init__(self, name):
        self._name = name

    def name(self):
        return self._name


class _WebLayer(FakeVectorLayer):
    """A WFS target, with real field names (``cleabs``: a known unique key on a web service)."""

    def __init__(self, field_names, features):
        super().__init__("typename='communes' url='https://data.geopf.fr/wfs/ows'", name='communes', provider='WFS',
                         features=features)
        self._field_names = list(field_names)

    def primaryKeyAttributes(self):
        return []


def _web_fields(layer):
    """QgsFields-like iteration for the probe."""
    class Fields(list):
        def at(self, index):
            return self[index]

        def indexOf(self, name):
            return next((i for i, field in enumerate(self) if field.name() == name), -1)
    layer.fields = lambda: Fields(_KeyField(name) for name in layer._field_names)
    return layer


class TestWebServiceTargets:
    """2026-10-17: a web service is filtered by a real key, at most key_list_limit (500) of them."""

    def test_no_key_is_refused_instead_of_writing_dollar_id(self, engine, remote):
        layer = _web_fields(_WebLayer(['nom', 'population'], {fid: _box(*box) for fid, (_, box) in ZONES.items()}))
        job = engine.VectorTargetJob(layer, None)
        job.compute(_box(*EAST_HALF), fk.FakeCrs('EPSG:2154'), None, _request(), lambda: False)
        assert not job.outcome.success and "no unique key field" in job.outcome.message
        assert job._expression == ''

    @pytest.mark.parametrize("count, applied", [(500, True), (501, False)])
    def test_key_list_is_bounded(self, engine, remote, count, applied):
        features = {fid: _box(600, 100, 650, 150) for fid in range(1, count + 1)}
        layer = _web_fields(_WebLayer(['cleabs', 'population'], features))
        job = engine.VectorTargetJob(layer, None)
        assert (job._pk, job._raw_pk) == ('cleabs', False)
        job.compute(_box(*EAST_HALF), fk.FakeCrs('EPSG:2154'), None, _request(), lambda: False)
        assert job.outcome.success is applied
        if applied:
            assert job._expression.startswith('"cleabs" IN (1, 2')
        else:
            assert job.outcome.message == "dock refusal: key_limit"  # the dock's own message


class _Remote:
    """``remote_materializer`` stand-in: a server BBOX read, the exact predicate on the copies."""

    def __init__(self, outcome_class):
        self.Outcome = outcome_class
        self.reads, self.marked, self.forced = [], [], None
        self.limit_params = []

    def _snapshot(self, layer):
        return ('filtered', layer)

    def unfiltered_snapshot(self, layer):
        return ('unfiltered', layer)

    def materialization_limits(self, params=None):
        self.limit_params.append(params)
        return 'limits'

    def materialize(self, snapshot, rect, server_expression, matches, limits, feedback):
        mode, layer = snapshot
        self.reads.append((mode, (rect.x0, rect.y0, rect.x1, rect.y1), server_expression, limits))
        if self.forced is not None:
            return self.forced
        rows = layer.features if mode == 'unfiltered' else layer.visible()
        keys = []
        for fid, geometry in sorted(rows.items()):
            if not geometry.boundingBox().intersects(rect):
                continue  # the server answers the BBOX only
            try:
                matched = matches(FakeFeature(fid, fk.FakeGeometry(geometry)))
            except Exception:
                return self.Outcome(reason='read_error')  # as collect_materialization
            if matched:
                keys.append(fid)
                if len(keys) > 500:
                    return self.Outcome(reason='key_limit')
        return self.Outcome(tuple(keys), True, len(rows))

    def mark_partial_result(self, layer, partial, expression):
        self.marked.append((partial, expression))


@pytest.fixture
def remote(monkeypatch):
    """The lot B modules the web service targets call (materializer, the dock's messages)."""
    stand_in = _Remote(fk.load('core.domain.materialization').MaterializationOutcome)
    module = types.ModuleType(f'{fk.PACKAGE}.adapters.qgis.remote_materializer')
    for name in ('_snapshot', 'unfiltered_snapshot', 'materialization_limits', 'materialize', 'mark_partial_result'):
        setattr(module, name, getattr(stand_in, name))
    monkeypatch.setitem(sys.modules, module.__name__, module)
    for name in ('adapters.backends', 'adapters.backends.ogr'):
        package = types.ModuleType(f'{fk.PACKAGE}.{name}')
        package.__path__ = []
        monkeypatch.setitem(sys.modules, package.__name__, package)
    executor = types.ModuleType(f'{fk.PACKAGE}.adapters.backends.ogr.filter_executor')
    executor._remote_message = lambda reason: f"dock refusal: {reason}"
    monkeypatch.setitem(sys.modules, executor.__name__, executor)
    monkeypatch.setattr(sys.modules[f'{fk.PACKAGE}.adapters.backends.ogr'], 'filter_executor', executor, raising=False)
    # The key list reaches the provider as is (the server translation has its own tests).
    for name in ('infrastructure', 'infrastructure.database'):
        if f'{fk.PACKAGE}.{name}' not in sys.modules:
            package = types.ModuleType(f'{fk.PACKAGE}.{name}')
            package.__path__ = []
            monkeypatch.setitem(sys.modules, package.__name__, package)
    sql_utils = types.ModuleType(f'{fk.PACKAGE}.infrastructure.database.sql_utils')
    sql_utils.safe_set_subset_string = lambda layer, subset: layer.setSubsetString(subset)
    monkeypatch.setitem(sys.modules, sql_utils.__name__, sql_utils)
    return stand_in


def _web_zones(subset=''):
    layer = _web_fields(_WebLayer(['cleabs', 'nom'], {fid: _box(*box) for fid, (_, box) in ZONES.items()}))
    layer.provider.subset = subset
    return layer


class TestWebServiceBoundedRead:
    """2026-10-20: the API read a WFS target through a filter rectangle alone, which the QGIS WFS
    provider answers by downloading the whole service (35 000 communes). The dock's bounded read
    (lot B, remote_materializer) is used instead: server BBOX, exact predicate on bounded copies."""

    @pytest.mark.parametrize("predicate,expression", [
        ('Intersect', '"cleabs" IN (1, 2)'),
        ('Disjoint', 'NOT ("cleabs" IN (1, 2))'),
    ])
    def test_centroids_are_tested_on_bounded_remote_copies(self, engine, remote, predicate, expression):
        layer = _web_zones()
        request = domain.CrossFilterRequest('source', LayerKind.RASTER, predicates=(predicate,),
                                            targets=(domain.TargetSpec(layer.id(), LayerKind.VECTOR, use_centroids=True),))
        job = engine.VectorTargetJob(layer, None)
        job.compute(_box(510, 0, 1000, 1000), fk.FakeCrs('EPSG:2154'), None, request, lambda: False)
        assert job.outcome.success and job._expression == expression
        assert remote.reads[0][1] == (510.0, 0.0, 1000.0, 1000.0)

    def test_reads_the_useful_bbox_through_the_materializer(self, engine, remote, monkeypatch):
        monkeypatch.setattr(engine, 'QgsVectorLayer', MagicMock(side_effect=AssertionError("unbounded copy")))
        layer = _web_zones(subset='ids:4')
        job = engine.VectorTargetJob(layer, None)
        assert _run(job, _box(*EAST_HALF), _request()) == ['east_a', 'east_b', 'straddle']
        assert remote.reads == [('unfiltered', (500.0, 0.0, 1000.0, 1000.0), '', 'limits')]
        assert job._expression == '"cleabs" IN (1, 2, 3)'
        job.apply(layer)
        assert remote.marked == [(False, '"cleabs" IN (1, 2, 3)')]

    def test_budgets_are_the_users_as_in_the_dock(self, engine, remote):
        """Review 2026-10-20: the API read with the defaults whatever REMOTE_MATERIALIZATION said."""
        import importlib
        config = importlib.import_module(f'{fk.PACKAGE}.config.config')
        _run(engine.VectorTargetJob(_web_zones(), None), _box(*EAST_HALF), _request())
        assert len(remote.limit_params) == 1 and remote.limit_params[0] is config.ENV_VARS

    def test_and_reads_through_the_previous_filter(self, engine, remote):
        job = engine.VectorTargetJob(_web_zones(subset='ids:1,4'), 'AND')
        assert _run(job, _box(*EAST_HALF), _request(operator='AND')) == ['east_a']
        assert remote.reads[0][0] == 'filtered'

    def test_contain_tested_on_the_copies(self, engine, remote):
        job = engine.VectorTargetJob(_web_zones(), None)
        assert _run(job, _box(690, 390, 810, 510), _request('Are within')) == ['east_a']

    def test_partial_result_applied_with_the_dock_warning(self, engine, remote):
        remote.forced = remote.Outcome((1,), False, 20001, 'feature_limit')
        layer = _web_zones()
        job = engine.VectorTargetJob(layer, None)
        assert _run(job, _box(*EAST_HALF), _request()) == ['east_a']
        assert job.outcome.message == "dock refusal: feature_limit" and job.outcome.details['partial']
        job.apply(layer)
        assert remote.marked == [(True, '"cleabs" IN (1)')]

    @pytest.mark.parametrize("outcome, predicates, reason", [
        (((), False, 7, 'timeout'), ('Intersect',), 'partial_empty'),
        (((), False, 0, 'read_error'), ('Intersect',), 'read_error'),
        (((), False, 0, 'unverified_filter'), ('Intersect',), 'unverified_filter'),
        (((2,), False, 9, 'timeout'), ('Disjoint',), 'disjoint_partial'),
        (None, ('Disjoint', 'Intersect'), 'mixed_disjoint'),
    ])
    def test_refusals_of_the_dock(self, engine, remote, outcome, predicates, reason):
        remote.forced = remote.Outcome(*outcome) if outcome else None
        job = engine.VectorTargetJob(_web_zones(), None)
        job.compute(_box(*EAST_HALF), fk.FakeCrs('EPSG:2154'), None, _request(*predicates), lambda: False)
        assert not job.outcome.success and job.outcome.message == f"dock refusal: {reason}"

    def test_disjoint_keeps_every_feature_but_the_intersecting_ones(self, engine, remote):
        job = engine.VectorTargetJob(_web_zones(), None)
        job.compute(_box(*EAST_HALF), fk.FakeCrs('EPSG:2154'), None, _request('Disjoint'), lambda: False)
        assert job.outcome.success, job.outcome.message
        assert job._expression == 'NOT ("cleabs" IN (1, 2, 3))'
        assert remote.reads[0][1] == (500.0, 0.0, 1000.0, 1000.0)

    def test_and_not_with_a_partial_result_is_refused(self, engine, remote):
        """Review: (old) AND NOT (partial keys) would keep the matching features never read."""
        remote.forced = remote.Outcome((1,), False, 20001, 'feature_limit')
        job = engine.VectorTargetJob(_web_zones(subset='ids:1,4'), 'AND NOT')
        job.compute(_box(*EAST_HALF), fk.FakeCrs('EPSG:2154'), None, _request(operator='AND NOT'), lambda: False)
        assert not job.outcome.success
        assert job.outcome.message == ("dock refusal: feature_limit AND NOT would keep the features not read; "
                                       "the previous filter is kept.")

    def test_and_not_without_a_previous_filter_lists_the_partial_keys(self, engine, remote):
        """Without a previous filter AND NOT replaces it (combine_subset): incomplete, not wrong."""
        remote.forced = remote.Outcome((1,), False, 20001, 'feature_limit')
        job = engine.VectorTargetJob(_web_zones(), 'AND NOT')
        assert _run(job, _box(*EAST_HALF), _request(operator='AND NOT')) == ['east_a']
        assert job.outcome.details['partial']

    def test_invalid_target_geometry_is_refused_as_in_the_dock(self, engine, remote):
        layer = _web_zones()
        layer.features[6] = fk.FakeGeometry.fromWkt('POLYGON((600 100,650 150,650 100,600 150,600 100))')
        job = engine.VectorTargetJob(layer, None)
        job.compute(_box(*EAST_HALF), fk.FakeCrs('EPSG:2154'), None, _request('Disjoint'), lambda: False)
        assert not job.outcome.success and job.outcome.message == "dock refusal: read_error"
