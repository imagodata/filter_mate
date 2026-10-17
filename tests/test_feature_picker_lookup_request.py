# -*- coding: utf-8 -*-
"""
PERF 2026-09-12: the multiple-selection picker checks membership of the
clicked row with ONE indexed request instead of scanning the whole layer.

Like ``test_feature_picker_mouse_compat``, the helpers are extracted from the
widget class with ``ast`` so no QWidget is constructed.
"""

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


class FakeRequest:
    Flag = SimpleNamespace(NoGeometry='NoGeometry')

    def __init__(self):
        self.flags = None
        self.expression = None
        self.fids = None
        self.limit = None

    def setFlags(self, flags):
        self.flags = flags

    def setFilterExpression(self, expression):
        self.expression = expression

    def setFilterFids(self, fids):
        self.fids = fids

    def setLimit(self, limit):
        self.limit = limit


class FakeExpression:
    @staticmethod
    def quotedValue(value):
        return repr(value) if isinstance(value, str) else str(value)

    @staticmethod
    def quotedColumnRef(name):
        return f'"{name}"'


@pytest.fixture
def helpers():
    path = Path(__file__).resolve().parents[1] / 'ui/widgets/custom_widgets.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    widget = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                  and node.name == 'QgsCheckableComboBoxFeaturesListPickerWidget')
    wanted = {'_build_identifier_lookup_request', '_is_feature_in_layer', '_to_number', '_identifier_field_of_layer'}
    nodes = [node for node in widget.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    for node in nodes:
        node.decorator_list = []  # drop @staticmethod: exec as plain functions
    iterated = []

    def fake_iterate(layer, request=None):
        iterated.append(request)
        return layer.rows

    namespace = {
        'QgsFeatureRequest': FakeRequest,
        'QgsExpression': FakeExpression,
        'safe_iterate_features': fake_iterate,
        'logger': MagicMock(),
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
    # The request builder refers to the class for the numeric cast helper.
    namespace['QgsCheckableComboBoxFeaturesListPickerWidget'] = SimpleNamespace(_to_number=namespace['_to_number'])
    namespace['_iterated'] = iterated
    return namespace


@pytest.mark.unit
def test_lookup_request_uses_identifier_field(helpers):
    request = helpers['_build_identifier_lookup_request']('code', ['A1', 7])
    assert request.expression == '"code" IN (\'A1\', 7)'
    assert request.flags == 'NoGeometry'
    assert request.fids is None


@pytest.mark.unit
def test_lookup_request_casts_text_ids_for_numeric_keys(helpers):
    request = helpers['_build_identifier_lookup_request']('gid', ['7', 8, '9.5', 'x'], True)
    assert request.expression == '"gid" IN (7, 8, 9.5, \'x\')'


@pytest.mark.unit
def test_lookup_request_falls_back_to_fids(helpers):
    request = helpers['_build_identifier_lookup_request']('', [3, '4', 'x'])
    assert request.expression is None
    assert request.fids == [3, 4]


@pytest.mark.unit
def test_membership_is_a_single_limited_lookup(helpers):
    picker = SimpleNamespace(
        layer=SimpleNamespace(rows=[object()]),
        _build_identifier_lookup_request=helpers['_build_identifier_lookup_request'],
        _identifier_is_numeric=lambda: False,
        _identifier_field_of_layer=lambda name: name,
    )
    assert helpers['_is_feature_in_layer'](picker, 'code', 'A1') is True
    request = helpers['_iterated'][-1]
    assert request.limit == 1
    assert request.expression == '"code" IN (\'A1\')'

    picker.layer.rows = []
    assert helpers['_is_feature_in_layer'](picker, 'code', 'A1') is False


@pytest.mark.unit
def test_membership_assumes_present_on_error(helpers):
    def boom(*_):
        raise RuntimeError("provider gone")

    picker = SimpleNamespace(layer=SimpleNamespace(rows=[]), _build_identifier_lookup_request=boom,
                             _identifier_is_numeric=lambda: False)
    assert helpers['_is_feature_in_layer'](picker, 'code', 'A1') is True


@pytest.mark.unit
def test_identifier_that_is_no_field_keys_rows_by_feature_id(helpers):
    """2026-10-17: a layer without a unique key field is registered with the pseudo key 'fid'.

    A Shapefile or a web layer has no field of that name: the rows are keyed by
    feature id (setFilterFids) instead of an expression on a missing field.
    """
    fields = SimpleNamespace(indexOf=lambda name: 0 if name == 'code' else -1)
    picker = SimpleNamespace(layer=SimpleNamespace(rows=[object()], fields=lambda: fields))
    assert helpers['_identifier_field_of_layer'](picker, 'fid') is None
    assert helpers['_identifier_field_of_layer'](picker, 'code') == 'code'
    assert helpers['_identifier_field_of_layer'](picker, '') is None
    picker._build_identifier_lookup_request = helpers['_build_identifier_lookup_request']
    picker._identifier_is_numeric = lambda: True
    picker._identifier_field_of_layer = lambda name: helpers['_identifier_field_of_layer'](picker, name)
    assert helpers['_is_feature_in_layer'](picker, 'fid', 7) is True
    request = helpers['_iterated'][-1]
    assert request.expression is None and request.fids == [7]


@pytest.mark.unit
def test_rows_beyond_the_list_are_fetched_by_feature_id_without_a_key_field():
    """2026-10-17: setCheckedFeatureIds fetched '"fid" IN (...)' on a Shapefile: [] (and KeyError on 'fid')."""
    path = Path(__file__).resolve().parents[1] / 'ui/widgets/custom_widgets.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    widget = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                  and node.name == 'QgsCheckableComboBoxFeaturesListPickerWidget')
    wanted = {'_fetch_rows_by_identifier', '_row_from_feature', '_identifier_field_of_layer',
              '_build_identifier_lookup_request', '_to_number'}
    nodes = [node for node in widget.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    for node in nodes:
        node.decorator_list = []
    requests = []

    class Feature:
        def __init__(self, fid, nom):
            self._fid, self._nom = fid, nom

        def id(self):
            return self._fid

        def __getitem__(self, name):
            if name != 'nom':
                raise KeyError(name)
            return self._nom

    def iterate(layer, request=None):
        requests.append(request)
        return [Feature(fid, f"commune {fid}") for fid in (request.fids or [])]

    namespace = {'QgsFeatureRequest': FakeRequest, 'QgsExpression': FakeExpression,
                 'safe_iterate_features': iterate, 'logger': MagicMock()}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
    namespace['QgsCheckableComboBoxFeaturesListPickerWidget'] = SimpleNamespace(_to_number=namespace['_to_number'])
    picker = SimpleNamespace(layer=SimpleNamespace(fields=lambda: SimpleNamespace(indexOf=lambda name: -1)))
    for name in ('_identifier_field_of_layer', '_fetch_rows_by_identifier'):
        setattr(picker, name, namespace[name].__get__(picker))
    picker._build_identifier_lookup_request = namespace['_build_identifier_lookup_request']
    picker._row_from_feature = namespace['_row_from_feature']
    picker._make_display_evaluator = lambda expression: (None, None)
    rows = picker._fetch_rows_by_identifier('$id', [4, 9], 'nom')
    assert rows == [('commune 4', 4), ('commune 9', 9)]
    assert requests[-1].expression is None and requests[-1].fids == [4, 9]
