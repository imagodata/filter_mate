# -*- coding: utf-8 -*-
"""Selections, zooms and identify of a source read in tasks (web service, network database).

The ExploringController methods are extracted with ast and run against
recording fakes: which request is read, in a task or not, and what is
refused. Review of lot C (#193): H1, H2, M1, M4, M6, M7.
"""
import ast
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

_MODULE = Path(__file__).resolve().parents[4] / "ui" / "controllers" / "exploring_controller.py"
_METHODS = ('_read_mode', '_remote_single_fid', '_remote_ui_revision', '_empty_remote_selection',
            '_remote_selection_plan', '_remote_features', '_remote_zoom_request', '_zoom_canvas_to',
            '_queue_remote_zoom', 'identify_remote_selection', '_invalidate_remote_selection_cache')


class Request:
    """QgsFeatureRequest stand-in: setters return the request, filters are recorded."""

    class Flag:
        NoFlags = 0
        NoGeometry = 1

    def __init__(self):
        self.expression = None
        self.fids = None
        self.no_attributes = False

    def setNoAttributes(self):
        self.no_attributes = True
        return self

    def setFilterExpression(self, expression):
        self.expression = expression
        return self

    def setFilterFids(self, fids):
        self.fids = list(fids)
        return self

    def setFlags(self, flags):
        return self

    def filterExpression(self):
        return None if self.expression is None else SimpleNamespace(expression=lambda: self.expression)

    def filterFid(self):
        return -1

    def filterFids(self):
        return self.fids or []


class Feature:
    def __init__(self, fid, key=None, geometry=True):
        self._fid = fid
        self._key = fid if key is None else key
        self._geometry = MagicMock(isEmpty=MagicMock(return_value=False)) if geometry else None

    def id(self):
        return self._fid

    def isValid(self):
        return True

    def hasGeometry(self):
        return self._geometry is not None

    def geometry(self):
        return self._geometry

    def __getitem__(self, name):
        return self._key


def _fake_modules(monkeypatch, service=True, key_field=True, limit=500, in_list_max=None):
    async_query = types.ModuleType('filter_mate.adapters.qgis.async_query')
    async_query.submit_query = MagicMock()
    async_query.collect_extent = MagicMock(return_value='extent')
    async_query.read_refusal = MagicMock(return_value=None)
    async_query.refusal_message = lambda reason: 'refused: ' + reason

    class ImmediateRead:
        def __init__(self, layer):
            self.layer = layer

        def features(self, request):
            return iter(self.layer.read(request))

    async_query.ImmediateRead = ImmediateRead
    probe = types.ModuleType('filter_mate.adapters.qgis.source_capability_probe')
    probe.capability_for_layer = lambda layer: SimpleNamespace(
        is_remote_service=service, key_list_limit=limit if service else None, in_list_max=in_list_max)
    probe.stable_key_for_layer = lambda layer, scan=True: SimpleNamespace(
        name='gml_id' if key_field else '$id', is_field=key_field)
    probe.counts_cheaply = lambda layer: False
    formatter = types.ModuleType('filter_mate.core.filter.pk_formatter')
    formatter.QGIS_EXPRESSION = 'qgis'
    formatter.format_key_literal = lambda value, numeric, dialect: str(value) if numeric else "'{}'".format(value)
    utils = types.ModuleType('filter_mate.infrastructure.utils')
    utils.should_skip_expression_for_filtering = lambda expression: (
        not expression or not any(op in expression for op in ('=', '>', '<', ' IN ')), '')
    for module in (async_query, probe, formatter, utils):
        monkeypatch.setitem(sys.modules, module.__name__, module)
    return SimpleNamespace(async_query=async_query, probe=probe)


def _controller_class(warning):
    tree = ast.parse(_MODULE.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'ExploringController')
    nodes = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in _METHODS]
    assert len(nodes) == len(_METHODS)
    namespace = {
        '__name__': 'filter_mate.ui.controllers.exploring_controller', '__package__': 'filter_mate.ui.controllers',
        'QgsFeatureRequest': Request, 'QgsFeature': Feature, 'QgsGeometry': lambda geometry: geometry,
        'QgsExpression': SimpleNamespace(quotedColumnRef=lambda name: '"{}"'.format(name)),
        'QgsRectangle': lambda extent: extent, 'QColor': lambda *args: args, 'QTimer': MagicMock(),
        'QgsCoordinateTransform': MagicMock(), 'QgsProject': MagicMock(), 'show_warning': warning,
        'logger': MagicMock(), 'WHOLE_LAYER': object(),
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(_MODULE), 'exec'), namespace)
    methods = {name: namespace[name] for name in _METHODS}
    return type('Controller', (), methods), namespace


class Layer:
    def __init__(self, features=()):
        self.features = list(features)
        self.reads = []
        self.provider_extent = MagicMock(isNull=MagicMock(return_value=False), isEmpty=MagicMock(return_value=False))
        for name in ('dataChanged', 'geometryChanged', 'willBeDeleted'):
            setattr(self, name, MagicMock())

    def id(self):
        return 'layer'

    def source(self):
        return 'source'

    def subsetString(self):
        return ''

    def crs(self):
        return 'EPSG:4326'

    def fields(self):
        return MagicMock(field=MagicMock(return_value=MagicMock(isNumeric=MagicMock(return_value=True))))

    def selectedFeatureIds(self):
        return []

    def dataProvider(self):
        return SimpleNamespace(extent=lambda: self.provider_extent)

    def read(self, request):
        self.reads.append(request)
        return self.features


def _setup(monkeypatch, mode='custom_selection', custom='', checked=(), picker_fid=None, saved_fid=None,
           **capability):
    fakes = _fake_modules(monkeypatch, **capability)
    warning = MagicMock()
    cls, namespace = _controller_class(warning)
    layer = Layer([Feature(1), Feature(2)])
    picker_feature = Feature(picker_fid) if picker_fid is not None else MagicMock(isValid=MagicMock(return_value=False))
    widgets = {'EXPLORING': {
        'CUSTOM_SELECTION_EXPRESSION': {'WIDGET': MagicMock(expression=MagicMock(return_value=custom))},
        'MULTIPLE_SELECTION_FEATURES': {'WIDGET': MagicMock(checkedItems=MagicMock(return_value=list(checked)))},
        'SINGLE_SELECTION_FEATURES': {'WIDGET': MagicMock(feature=MagicMock(return_value=picker_feature))},
    }}
    canvas = MagicMock()
    canvas.mapSettings.return_value.destinationCrs.return_value = 'EPSG:4326'
    dock = SimpleNamespace(current_layer=layer, current_exploring_groupbox=mode, widgets=widgets,
                           PROJECT_LAYERS={'layer': {'exploring': {}, 'filtering': {}}}, tr=lambda text: text,
                           _last_single_selection_fid=saved_fid, _last_single_selection_layer_id='layer',
                           pushButton_checkable_exploring_selecting=MagicMock(isChecked=MagicMock(return_value=False)),
                           iface=MagicMock(mapCanvas=MagicMock(return_value=canvas)))
    controller = cls()
    controller._dockwidget = dock
    controller._current_layer = layer
    controller._remote_cache_layer = layer
    controller.set_layer = MagicMock()
    controller.handle_exploring_features_result = MagicMock()
    controller._remote_loading = MagicMock()
    return SimpleNamespace(controller=controller, dock=dock, layer=layer, warning=warning, canvas=canvas,
                           submit=fakes.async_query.submit_query, async_query=fakes.async_query,
                           whole=namespace['WHOLE_LAYER'])


def _submitted_request(env):
    compute = env.submit.call_args.args[4]
    task = SimpleNamespace(features=lambda request: env.layer.read(request))
    return compute(task)


# --- H1: an empty custom selection is no selection, on a service as on a local layer ---------------

@pytest.mark.parametrize('custom', ['', '   ', '"name"'])
def test_custom_selection_without_filter_reads_nothing(monkeypatch, custom):
    env = _setup(monkeypatch, custom=custom)
    assert env.controller._remote_features() == ([], custom.strip())
    env.submit.assert_not_called()
    assert env.layer.reads == []
    assert env.controller._remote_selection_refused is False
    assert env.controller._remote_selection_waiting is False


@pytest.mark.parametrize('custom', ['', '"name"'])
def test_zoom_without_filter_uses_the_provider_extent(monkeypatch, custom):
    env = _setup(monkeypatch, custom=custom)
    request = env.controller._remote_zoom_request()
    assert request is env.whole
    assert env.controller._queue_remote_zoom(request) is True
    env.submit.assert_not_called()
    env.canvas.zoomToFeatureExtent.assert_called_once_with(env.layer.provider_extent)


def test_custom_filter_expression_is_read_in_a_task(monkeypatch):
    env = _setup(monkeypatch, custom='"id" > 10')
    assert env.controller._remote_features() == ([], '"id" > 10')
    assert env.controller._remote_selection_waiting is True
    features, expression = _submitted_request(env)
    assert env.layer.reads[0].expression == '"id" > 10' and expression == '"id" > 10'


# --- H2: a refused multiple selection launches nothing and changes nothing ---------------------------

def test_too_many_service_keys_are_refused_without_reading(monkeypatch):
    env = _setup(monkeypatch, mode='multiple_selection', checked=[('n', i) for i in range(3)], limit=2)
    assert env.controller._remote_features() == ([], '')
    assert env.controller._remote_selection_refused is True
    env.submit.assert_not_called()
    env.controller.handle_exploring_features_result.assert_not_called()
    assert 'key limit' in env.warning.call_args.args[0]


def test_a_service_without_stable_key_refuses_a_multiple_selection_filter(monkeypatch):
    env = _setup(monkeypatch, mode='multiple_selection', checked=[('n', 4), ('m', 7)], key_field=False)
    assert env.controller._remote_features() == ([], '')
    assert env.controller._remote_selection_refused is True
    env.submit.assert_not_called()
    assert 'stable key' in env.warning.call_args.args[0]


def test_a_refused_zoom_reads_nothing(monkeypatch):
    env = _setup(monkeypatch, mode='multiple_selection', checked=[('n', i) for i in range(3)], limit=2)
    request = env.controller._remote_zoom_request()
    assert request is None
    assert env.controller._queue_remote_zoom(request) is False
    env.submit.assert_not_called()


# --- M6: the zoom of rows keyed by feature id ----------------------------------------------------

def test_zoom_on_rows_keyed_by_feature_id_reads_the_checked_ids(monkeypatch):
    env = _setup(monkeypatch, mode='multiple_selection', checked=[('n', 4), ('m', 7)], key_field=False)
    request = env.controller._remote_zoom_request()
    assert request.fids == [4, 7] and request.no_attributes
    assert not env.warning.called


# --- M7: a network database / remote file keeps the key lists of 5.0 ---------------------------------

def test_a_network_database_has_no_service_key_limit(monkeypatch):
    env = _setup(monkeypatch, mode='multiple_selection', checked=[('n', i) for i in range(5)],
                 service=False, in_list_max=2)
    assert env.controller._remote_features() == ([], '("gml_id" IN (0, 1) OR "gml_id" IN (2, 3) OR "gml_id" IN (4))')
    assert env.controller._remote_selection_refused is False
    env.submit.assert_called_once()


def test_a_network_database_without_key_field_filters_by_feature_id(monkeypatch):
    env = _setup(monkeypatch, mode='multiple_selection', checked=[('n', 4), ('m', 7)], key_field=False,
                 service=False)
    assert env.controller._remote_features() == ([], '$id IN (4, 7)')
    assert env.controller._remote_selection_refused is False
    _submitted_request(env)
    assert env.layer.reads[0].fids == [4, 7]


def test_an_expression_a_worker_cannot_run_is_read_as_before_on_a_network_database(monkeypatch):
    env = _setup(monkeypatch, custom='aggregate(\'x\', \'sum\', "v") > 1', service=False)
    env.async_query.read_refusal.return_value = 'unsafe'
    features, expression = env.controller._remote_features()
    env.submit.assert_not_called()
    assert [feature.id() for feature in features] == [1, 2]
    assert env.controller._remote_selection_refused is False
    assert not env.warning.called


def test_an_expression_a_worker_cannot_run_is_refused_on_a_service(monkeypatch):
    env = _setup(monkeypatch, custom='aggregate(\'x\', \'sum\', "v") > 1')
    env.async_query.read_refusal.return_value = 'virtual_field'
    assert env.controller._remote_features() == ([], '')
    assert env.controller._remote_selection_refused is True
    env.submit.assert_not_called()
    assert env.layer.reads == []
    assert env.warning.call_args.args[0] == 'refused: virtual_field'


# --- M1: a pick and a Filter click of the same feature are one read ----------------------------------

def test_a_debounced_pick_does_not_replace_the_filter_read_of_the_same_feature(monkeypatch):
    env = _setup(monkeypatch, mode='single_selection', saved_fid=5)
    env.controller._remote_features()   # Filter click: the UI designates feature 5
    env.controller._selection_query = SimpleNamespace(task=object(), cancel=MagicMock())
    env.dock._last_single_selection_fid = 5   # the debounced pick saves the same feature
    assert env.controller._remote_features(Feature(5)) == ([], '')
    env.submit.assert_called_once()
    env.controller._selection_query.cancel.assert_not_called()
    assert env.controller._remote_selection_waiting is True


def test_the_single_selection_revision_is_the_designated_feature(monkeypatch):
    env = _setup(monkeypatch, mode='single_selection', picker_fid=5, saved_fid=None)
    before = env.controller._remote_ui_revision()
    env.dock._last_single_selection_fid = 5
    assert env.controller._remote_ui_revision() == before == ('single_selection', 5)
    env.dock.widgets['EXPLORING']['SINGLE_SELECTION_FEATURES']['WIDGET'].feature.return_value = Feature(6)
    assert env.controller._remote_ui_revision() == ('single_selection', 6)


# --- M4: identify flashes the geometries already read ------------------------------------------------

def test_identify_flashes_read_geometries_without_reading_the_service(monkeypatch):
    env = _setup(monkeypatch, custom='"id" > 0')
    env.controller._remote_features()
    env.submit.call_args.args[5](_submitted_request(env))   # the read delivers
    env.submit.reset_mock()
    assert env.controller.identify_remote_selection() is True
    env.submit.assert_not_called()
    env.canvas.flashGeometries.assert_called_once()
    env.canvas.flashFeatureIds.assert_not_called()
    assert len(env.canvas.flashGeometries.call_args.args[0]) == 2


def test_identify_waits_for_a_pending_read_without_a_false_warning(monkeypatch):
    env = _setup(monkeypatch, custom='"id" > 0')
    task = SimpleNamespace(taskCompleted=MagicMock())
    original = env.submit.side_effect

    def submit(owner, attribute, *args):
        setattr(owner, attribute, SimpleNamespace(task=task, cancel=MagicMock()))
    env.submit.side_effect = submit
    assert env.controller.identify_remote_selection() is True
    env.submit.side_effect = original
    assert not env.warning.called
    env.canvas.flashGeometries.assert_not_called()
    task.taskCompleted.connect.assert_called_once()
