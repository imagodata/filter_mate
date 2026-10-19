"""The feature list of a source read in tasks: web service rules only for web services (review of #193, M7 / M8)."""
import ast
import sys
import time
import types
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

PATH = Path(__file__).resolve().parents[4] / 'ui/widgets/custom_widgets.py'


class Request:
    class Flag:
        NoFlags = 0
        NoGeometry = 1

    def __init__(self):
        self.limit = None
        self.attributes = None
        self.expression = None

    def setFlags(self, flags):
        return self

    def setLimit(self, limit):
        self.limit = limit
        return self

    def setSubsetOfAttributes(self, attributes, fields=None):
        self.attributes = list(attributes)
        return self

    def setFilterExpression(self, expression):
        self.expression = expression
        return self


class Expression:
    def __init__(self, text):
        self.text = text

    def needsGeometry(self):
        return False

    def isField(self):
        return True

    def referencedColumns(self):
        return {self.text}

    def hasParserError(self):
        return False


def _method(name):
    tree = ast.parse(PATH.read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == 'QgsCheckableComboBoxFeaturesListPickerWidget')
    node = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)
    namespace = {'__name__': 'filter_mate.ui.widgets.custom_widgets', '__package__': 'filter_mate.ui.widgets',
                 'is_layer_valid': lambda layer: True, 'QgsFeatureRequest': Request, 'QgsExpression': Expression,
                 'feature_picker_limit': lambda: 1000, 'time': time}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(PATH), 'exec'), namespace)
    return namespace[name]


@pytest.fixture
def widget(monkeypatch):
    def make(service, refusal=None, rows=1500):
        async_query = types.ModuleType('filter_mate.adapters.qgis.async_query')
        async_query.submit_query = MagicMock()
        async_query.expression_refusal = lambda expression, fields: None
        async_query.read_refusal = MagicMock(return_value=refusal)
        async_query.refusal_message = lambda reason: 'refused: ' + reason
        async_query.ImmediateRead = lambda layer: SimpleNamespace(
            features=lambda request: iter(range(rows if request.limit is None else min(rows, request.limit))),
            isCanceled=lambda: False)
        probe = types.ModuleType('filter_mate.adapters.qgis.source_capability_probe')
        probe.capability_for_layer = lambda layer: SimpleNamespace(
            is_remote_service=service, key_list_limit=500 if service else None)
        feedback = types.ModuleType('filter_mate.infrastructure.feedback')
        feedback.show_warning = MagicMock()
        for module in (async_query, probe, feedback):
            monkeypatch.setitem(sys.modules, module.__name__, module)
        layer = MagicMock()
        layer.id.return_value = 'layer'
        layer.subsetString.return_value = ''
        rows_widget = MagicMock()
        rows_widget.getLimit.return_value = 1000
        rows_widget.getIdentifierFieldName.return_value = 'id'
        rows_widget.getDisplayExpression.return_value = 'name'
        widget_class = type('Widget', (), {
            '_row_from_feature': staticmethod(lambda feature, identifier, expression, expr, context: ('row', feature)),
            '_build_identifier_lookup_request': staticmethod(lambda *args: Request())})
        state = widget_class()
        state.__dict__.update(
            layer=layer, list_widgets={'layer': rows_widget}, _sort_order='ASC', tr=lambda text: text,
            getCheckedFeatureIds=lambda: [], _identifier_field_of_layer=lambda name: name,
            _identifier_is_numeric=lambda: True, _make_display_evaluator=MagicMock(return_value=(None, None)),
            _row_attributes=lambda expression, identifier: ['id', 'name'], _population_loading=MagicMock(),
            _search_expression=MagicMock(), _display_expression_sql=MagicMock(),
            _apply_population=MagicMock(), _recover_remote_rows=MagicMock(), select_all=MagicMock())
        state._populate = MethodType(_method('_populate_features_async'), state)
        return SimpleNamespace(state=state, submit=async_query.submit_query, warning=feedback.show_warning,
                               rows=rows_widget)
    return make


def test_select_all_on_a_network_database_loads_every_row(widget):
    env = widget(service=False)
    env.state._populate('name', force_full=True)
    compute, deliver = env.submit.call_args.args[4], env.submit.call_args.args[5]
    task = SimpleNamespace(features=lambda request: iter(range(1500)), isCanceled=lambda: False)
    rows, truncated, scanned = compute(task)
    assert len(rows) == 1500 and truncated is False
    deliver((rows, truncated, scanned))
    env.warning.assert_not_called()
    env.state._apply_population.assert_called_once()


def test_select_all_on_a_service_is_bounded_by_its_key_limit(widget):
    env = widget(service=True)
    env.state._populate('name', force_full=True)
    compute, deliver = env.submit.call_args.args[4], env.submit.call_args.args[5]
    task = SimpleNamespace(features=lambda request: iter(range(1500)), isCanceled=lambda: False)
    rows, truncated, scanned = compute(task)
    assert len(rows) == 500 and truncated is True
    deliver((rows, truncated, scanned))
    assert 'safe selection limit' in env.warning.call_args.args[0]
    env.state._apply_population.assert_not_called()


def test_a_list_a_worker_cannot_read_is_refused_with_its_reason_on_a_service(widget):
    env = widget(service=True, refusal='virtual_field')
    env.state._populate('name')
    env.submit.assert_not_called()
    assert env.warning.call_args.args[0] == 'refused: virtual_field'


def test_a_list_a_worker_cannot_read_is_read_as_before_on_a_network_database(widget):
    env = widget(service=False, refusal='virtual_field', rows=3)
    env.state._populate('name')
    env.submit.assert_not_called()
    env.warning.assert_not_called()
    env.state._make_display_evaluator.assert_called_once_with('name', worker=False)
    env.state._apply_population.assert_called_once()
    assert env.state._apply_population.call_args.args[1] == [('row', 0), ('row', 1), ('row', 2)]


def test_list_reads_only_the_row_fields():
    """A virtual field nobody displays is not evaluated, so it cannot refuse the list (M8)."""
    method = _method('_row_attributes')
    fields = MagicMock()
    fields.indexOf.side_effect = lambda name: 0 if name == 'name' else -1
    state = SimpleNamespace(layer=MagicMock(fields=MagicMock(return_value=fields)))
    assert method(state, 'name', 'id') == ['id', 'name']
    assert method(state, '', None) == []
