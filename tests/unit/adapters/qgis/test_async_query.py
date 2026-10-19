"""Cancellation and generation guards independent of a running QGIS application."""
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PATH = Path(__file__).resolve().parents[4] / 'adapters/qgis/async_query.py'


@pytest.fixture
def module(monkeypatch):
    import sys
    import types
    core = types.ModuleType('qgis.core')
    core.QgsTask = None
    core.QgsFeedback = None
    core.QgsVectorLayerFeatureSource = None
    core.QgsExpression = MagicMock()
    core.QgsApplication = MagicMock()
    monkeypatch.setitem(sys.modules, 'qgis.core', core)

    class Task:
        class Flag:
            CanCancel = 1

        def __init__(self, *args):
            self.cancelled = False
            self.taskCompleted = MagicMock()
            self.taskTerminated = MagicMock()

        def setDependentLayers(self, layers):
            pass

        def cancel(self):
            self.cancelled = True

        def isCanceled(self):
            return self.cancelled

        def description(self):
            return 'read'

    monkeypatch.setattr(core, 'QgsTask', Task)
    monkeypatch.setattr(core, 'QgsFeedback', MagicMock(side_effect=lambda: MagicMock()))
    monkeypatch.setattr(core, 'QgsVectorLayerFeatureSource', MagicMock(side_effect=lambda layer: MagicMock()))
    spec = importlib.util.spec_from_file_location('async_query_test', PATH)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_no_read_during_construction(module):
    compute, deliver = MagicMock(), MagicMock()
    task = module.SnapshotQueryTask('read', MagicMock(), compute, deliver)
    compute.assert_not_called()
    deliver.assert_not_called()
    assert task.run()
    deliver.assert_not_called()
    task.finished(True)
    deliver.assert_called_once_with(compute.return_value)


def test_cancel_uses_feedback_and_drops_completed_result(module):
    callback = MagicMock()
    task = module.SnapshotQueryTask('read', MagicMock(), lambda _: [1], callback)
    assert task.run()
    task.cancel()
    task.feedback.cancel.assert_called_once()
    task.finished(True)
    callback.assert_not_called()


def test_generation_drops_result_from_previous_expression(module):
    slot = module.QuerySlot()
    first = MagicMock()
    generation = slot.replace(first)
    assert slot.accepts(generation)
    second_generation = slot.replace(MagicMock())
    first.cancel.assert_called_once()
    assert not slot.accepts(generation)
    assert slot.accepts(second_generation)
    slot.cancel()
    assert not slot.accepts(second_generation)


def test_cancel_before_start_never_reads(module):
    compute = MagicMock()
    task = module.SnapshotQueryTask('read', MagicMock(), compute, MagicMock())
    task.cancel()
    assert not task.run()
    compute.assert_not_called()


def test_error_never_delivers_partial_result(module):
    callback = MagicMock()

    def fail(task):
        raise ValueError('read failed')

    task = module.SnapshotQueryTask('read', MagicMock(), fail, callback)
    assert not task.run()
    task.finished(False)
    callback.assert_not_called()
    assert isinstance(task.error, ValueError)


def test_iterator_is_closed_on_cancellation(module):
    task = module.SnapshotQueryTask('read', MagicMock(), MagicMock(), MagicMock())
    iterator = MagicMock()
    iterator.__iter__.return_value = iter([1, 2])
    task.source.getFeatures.return_value = iterator
    request = MagicMock()
    features = task.features(request)
    assert next(features) == 1
    task.cancel()
    assert list(features) == []
    iterator.close.assert_called_once()
    request.setFeedback.assert_called_once_with(task.feedback)


def _owner_layer():
    from types import SimpleNamespace
    layer = MagicMock()
    layer.id.return_value = 'layer'
    layer.source.return_value = 'source'
    layer.subsetString.return_value = ''
    return SimpleNamespace(), layer


def test_submit_drops_changed_subset_at_delivery(module):
    owner, layer = _owner_layer()
    callback = MagicMock()
    task = module.submit_query(owner, 'query', layer, 'read', lambda _: [1], callback)
    assert task.run()
    layer.subsetString.return_value = 'changed'
    task.finished(True)
    callback.assert_not_called()


def test_replaced_query_cannot_deliver_after_its_run_completed(module):
    owner, layer = _owner_layer()
    old_callback = MagicMock()
    old = module.submit_query(owner, 'query', layer, 'read', lambda _: [1], old_callback)
    assert old.run()
    new_callback = MagicMock()
    new = module.submit_query(owner, 'query', layer, 'read', lambda _: [2], new_callback)
    old.finished(True)
    old_callback.assert_not_called()
    assert new.run()
    new.finished(True)
    new_callback.assert_called_once_with([2])


def test_layer_deleted_signal_cancels_feedback(module):
    owner, layer = _owner_layer()
    task = module.submit_query(owner, 'query', layer, 'read', lambda _: [1], MagicMock())
    invalidate = layer.willBeDeleted.connect.call_args.args[0]
    invalidate()
    assert task.isCanceled()
    task.feedback.cancel.assert_called_once()


def test_cancel_resets_loading_state(module):
    owner, layer = _owner_layer()
    loading = MagicMock()
    module.submit_query(owner, 'query', layer, 'read', lambda _: [1], MagicMock(), loading)
    loading.assert_called_once_with(True)
    owner.query.cancel()
    assert loading.call_args.args == (False,)


def test_previous_termination_does_not_clear_new_loading_state(module):
    owner, layer = _owner_layer()
    loading = MagicMock()
    old = module.submit_query(owner, 'query', layer, 'read', lambda _: [1], MagicMock(), loading)
    module.submit_query(owner, 'query', layer, 'read', lambda _: [2], MagicMock(), loading)
    loading.reset_mock()
    settled = old.taskTerminated.connect.call_args.args[0]
    settled()
    loading.assert_not_called()


def test_iterator_closes_when_consumer_stops_after_first_row(module):
    task = module.SnapshotQueryTask('read', MagicMock(), MagicMock(), MagicMock())
    iterator = MagicMock()
    iterator.__iter__.return_value = iter([1, 2])
    task.source.getFeatures.return_value = iterator
    features = task.features(MagicMock())
    assert next(features) == 1
    features.close()
    iterator.close.assert_called_once()


@pytest.mark.parametrize('functions,variables,safe', [
    ({'lower', 'coalesce'}, set(), True),
    ({'aggregate'}, set(), False),
    ({'get_feature'}, set(), False),
    ({'eval'}, set(), False),
    (set(), {'layer'}, False),
])
def test_remote_expression_never_dereferences_live_layers(module, monkeypatch, functions, variables, safe):
    import sys
    expression = MagicMock()
    expression.hasParserError.return_value = False
    expression.referencedFunctions.return_value = functions
    expression.referencedVariables.return_value = variables
    monkeypatch.setattr(sys.modules['qgis.core'], 'QgsExpression', MagicMock(return_value=expression))
    assert module.remote_expression_is_safe('expression') is safe


@pytest.mark.parametrize('signal_name', ['dataChanged', 'crsChanged', 'updatedFields', 'dataSourceChanged'])
def test_secondary_layer_data_change_cancels_union_query(module, signal_name):
    owner, first = _owner_layer()
    second = MagicMock()
    task = module.submit_query(owner, 'query', first, 'union', lambda _: None, MagicMock(),
                               dependencies=[first, second])
    getattr(second, signal_name).connect.call_args.args[0]()
    assert task.isCanceled()


def test_already_cancelled_read_does_not_open_an_iterator(module):
    task = module.SnapshotQueryTask('read', MagicMock(), MagicMock(), MagicMock())
    task.cancel()
    assert list(task.features(MagicMock())) == []
    task.source.getFeatures.assert_not_called()


def test_request_uses_a_bounded_provider_timeout(module):
    task = module.SnapshotQueryTask('read', MagicMock(), MagicMock(), MagicMock())
    task.source.getFeatures.return_value.__iter__.return_value = iter([])
    request = MagicMock()
    assert list(task.features(request)) == []
    request.setTimeout.assert_called_once_with(30000)


def test_slow_eof_is_an_error_instead_of_a_partial_success(module, monkeypatch):
    task = module.SnapshotQueryTask('read', MagicMock(), MagicMock(), MagicMock())
    task.source.getFeatures.return_value.__iter__.return_value = iter([])
    from types import SimpleNamespace
    monkeypatch.setattr(module, 'time', SimpleNamespace(monotonic=MagicMock(side_effect=[0, 30])))
    with pytest.raises(TimeoutError):
        list(task.features(MagicMock()))
    task.source.getFeatures.return_value.close.assert_called_once()


def test_repeated_values_stop_at_scan_budget_and_report_partial(module):
    task = MagicMock()
    seen = []

    def features(request):
        for i in range(100000):
            seen.append(i)
            yield {0: 'same'}

    task.features.side_effect = features
    request = MagicMock()
    values, partial = module.collect_unique_values(task, request, 0, 10, scan_limit=100)
    assert values == ['same']
    assert partial
    assert len(seen) == 101
    request.setLimit.assert_called_once_with(101)


def test_complete_unique_values_do_not_report_a_partial_result(module):
    task = MagicMock()
    task.features.return_value = iter([{0: 'b'}, {0: 'a'}, {0: 'a'}])
    assert module.collect_unique_values(task, MagicMock(), 0, 10) == (['a', 'b'], False)


def test_virtual_project_expression_is_rejected_before_worker_reads(module, monkeypatch):
    layer = MagicMock()
    layer.fields.return_value.__len__.return_value = 1
    layer.expressionField.return_value = "aggregate(@layer, 'count', id)"
    monkeypatch.setattr(module, 'remote_expression_is_safe', lambda *args: False)
    compute = MagicMock()
    task = module.SnapshotQueryTask('read', layer, compute, MagicMock())
    assert not task.run()
    assert isinstance(task.error, module.UnsafeExpressionError)
    compute.assert_not_called()


def test_delivery_error_is_recorded_without_escaping_the_qgis_callback(module):
    task = module.SnapshotQueryTask('read', MagicMock(), lambda _: [1], MagicMock(side_effect=ValueError('bad view')))
    assert task.run()
    task.finished(True)
    assert isinstance(task.error, ValueError)
    assert task.deliver is None and task.compute is None


def test_replacing_a_pending_read_keeps_the_loading_lease(module):
    owner, layer = _owner_layer()
    loading = MagicMock()
    module.submit_query(owner, 'query', layer, 'read', lambda _: [1], MagicMock(), loading)
    module.submit_query(owner, 'query', layer, 'read', lambda _: [2], MagicMock(), loading)
    loading.assert_called_once_with(True)
    owner.query.cancel()
    assert [call.args[0] for call in loading.call_args_list] == [True, False]


def test_clearing_an_expression_cancels_a_completed_but_undelivered_read(module):
    import ast
    from types import MethodType
    owner, layer = _owner_layer()
    callback = MagicMock()
    task = module.submit_query(owner, '_selection_query', layer, 'old', lambda _: [1], callback)
    assert task.run()
    controller = PATH.parents[2] / 'ui/controllers/exploring_controller.py'
    tree = ast.parse(controller.read_text(encoding='utf-8'))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'ExploringController')
    node = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == '_empty_remote_selection')
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(controller), 'exec'), namespace)
    empty = MethodType(namespace['_empty_remote_selection'], owner)
    assert empty('name') == ([], 'name')
    task.finished(True)
    callback.assert_not_called()
    task.feedback.cancel.assert_called_once()


def test_a_slow_successful_match_is_not_a_false_timeout(module, monkeypatch):
    from types import SimpleNamespace
    task = module.SnapshotQueryTask('read', MagicMock(), MagicMock(), MagicMock())
    task.source.getFeatures.return_value.__iter__.return_value = iter([1])
    monkeypatch.setattr(module, 'time', SimpleNamespace(monotonic=MagicMock(side_effect=[0, 45, 45.1])))
    assert list(task.features(MagicMock())) == [1]
    task.source.getFeatures.return_value.close.assert_called_once()
