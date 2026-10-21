"""A worker must keep its project, respect newer work and classify internal errors."""
import importlib.util
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit
spec = importlib.util.spec_from_file_location('fm_task_state_fakes', pathlib.Path(__file__).with_name('coverage_fakes.py'))
fk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fk)
tasks = fk.load('cross_filter_task')
snapshots = fk.load('snapshots')
state = fk.load('core.domain.filter_state')
domain = fk.load('core.domain.cross_filter')
Kind = fk.load('core.domain.layer_kind').LayerKind


class Layer:
    def __init__(self, layer_id, subset='initial = 1'):
        self.layer_id, self.subset = layer_id, subset
        self.uri = layer_id + '.gpkg'

    def source(self):
        return self.uri

    def providerType(self):
        return 'ogr'


class Project:
    def __init__(self, *layers):
        self.layers = {layer.layer_id: layer for layer in layers}

    def mapLayer(self, layer_id):
        return self.layers.get(layer_id)

    def transformContext(self):
        return None


def snapshot(layer, kind):
    return state.LayerSnapshot(layer.layer_id, kind.value, subset=layer.subset)


class Job:
    kind = Kind.VECTOR
    outputs = ()

    def __init__(self, layer):
        self.layer_id = self.layer_name = layer.layer_id
        self.before = snapshot(layer, self.kind)
        self.outcome = domain.CrossFilterOutcome(self.layer_id, self.kind, True)
        self.applied = []
        self.release = MagicMock()

    def compute(self, *args):
        pass

    def apply(self, layer):
        self.applied.append(layer)
        layer.subset = 'computed = 1'
        return snapshot(layer, self.kind)


@pytest.fixture
def world(monkeypatch):
    source, target = Layer('source'), Layer('target')
    project = Project(source, target)
    monkeypatch.setattr(tasks, 'QgsProject', types.SimpleNamespace(instance=lambda: project))
    monkeypatch.setattr(snapshots, 'take_snapshot', snapshot)
    cache = fk.load('cache')
    monkeypatch.setattr(cache, 'is_closed', lambda: False)
    source_job = Job(source)
    source_job.kind = Kind.OTHER
    source_job.apply = lambda layer: None
    source_job.compute = lambda *args, **kwargs: types.SimpleNamespace(isEmpty=lambda: False)
    source_job.elapsed, source_job.details, source_job.message = 0, {}, ''
    return types.SimpleNamespace(project=project, source=source, target=target, source_job=source_job, job=Job(target))


def test_explicit_project_is_used_instead_of_singleton(world):
    other_target = Layer('target', 'other = 1')
    other = Project(other_target)
    job = Job(other_target)
    task = tasks.CrossFilterTask('test', None, world.source_job, [job], project=other)
    task.apply_results(True)
    assert job.applied == [other_target]
    assert other_target.subset == 'computed = 1' and world.target.subset == 'initial = 1'
    assert len(task.changes) == 1


@pytest.mark.parametrize('change', ['subset', 'uri'])
def test_newer_filter_or_source_is_kept_and_not_recorded_as_undoable(world, change):
    task = tasks.CrossFilterTask('test', None, world.source_job, [world.job])
    setattr(world.target, change, 'newer user work')
    task.apply_results(True)
    assert getattr(world.target, change) == 'newer user work'
    assert not world.job.applied and not task.changes
    assert not world.job.outcome.success and 'changed' in world.job.outcome.message
    world.job.release.assert_called_once()


def test_changed_source_invalidates_targets_before_any_application(world):
    world.source_job.kind = Kind.RASTER
    task = tasks.CrossFilterTask('test', None, world.source_job, [world.job])
    world.source.subset = 'newer source selection'
    task.apply_results(True)
    assert 'source changed' in task.error
    assert task.source_conflict
    assert not world.job.applied and not task.changes


def test_cancel_still_marks_a_changed_source_so_rollback_keeps_newer_work(world):
    world.source_job.kind = Kind.RASTER
    task = tasks.CrossFilterTask('test', None, world.source_job, [world.job])
    world.source.subset = 'newer source selection'
    task.apply_results(False)
    assert task.source_conflict and world.source.subset == 'newer source selection'
    assert not world.job.applied


def test_read_only_vector_selection_survives_the_linked_engines_source_filter(world):
    world.source_job.kind = Kind.VECTOR
    task = tasks.CrossFilterTask('test', None, world.source_job, [world.job])
    world.source.subset = 'filter applied by the linked vector engine'
    task.apply_results(True)
    assert world.job.applied == [world.target] and not task.error


def test_source_error_is_classified_as_internal(world):
    def fail(*args, **kwargs):
        raise RuntimeError('/private/capture.tif could not be read')
    world.source_job.compute = fail
    task = tasks.CrossFilterTask('test', None, world.source_job, [world.job])
    assert not task.run()
    assert task.internal_error and '/private/' in task.error


def test_target_exception_is_not_reported_as_success_or_as_a_validation_message(world):
    def fail(*args, **kwargs):
        raise RuntimeError('/private/target.gpkg failed')
    world.job.compute = fail
    task = tasks.CrossFilterTask('test', None, world.source_job, [world.job])
    assert task.run()
    task.apply_results(True)
    assert not world.job.outcome.success and world.job.outcome.details['internal_error']
    assert not world.job.applied


def test_point_cloud_source_checks_prepared_state_instead_of_history_before(world):
    world.source_job.kind = Kind.POINT_CLOUD
    world.source_job.before = state.LayerSnapshot('source', 'point_cloud', subset='old criteria')
    world.source.subset = 'prepared criteria'
    applied = []
    world.source_job.apply = lambda layer: applied.append(layer)
    task = tasks.CrossFilterTask('test', None, world.source_job, [])
    task.apply_results(True)
    assert applied == [world.source] and not task.error
