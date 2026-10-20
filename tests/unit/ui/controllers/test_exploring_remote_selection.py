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
            '_remote_selection_plan', '_remote_row_key', '_remote_features', '_remote_zoom_request',
            '_zoom_canvas_to', '_queue_remote_zoom', 'identify_remote_selection',
            '_invalidate_remote_selection_cache', 'remote_filter_refused', 'remote_filter_blocked')


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


_UNSET = object()


class Feature:
    def __init__(self, fid, key=_UNSET, geometry=True):
        self._fid = fid
        self._key = fid if key is _UNSET else key
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


def _fake_modules(monkeypatch, service=True, key_field=True, limit=500, in_list_max=None, row_key=None,
                  key_origin='named'):
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
    async_query.SYNTAX = 'syntax'

    def read_now(layer, compute):
        try:
            return True, compute(ImmediateRead(layer))
        except Exception:
            async_query.read_failures.append(layer)
            return False, None

    async_query.read_failures = []
    async_query.read_now = read_now
    probe = types.ModuleType('filter_mate.adapters.qgis.source_capability_probe')
    probe.capability_for_layer = lambda layer: SimpleNamespace(
        is_remote_service=service, key_list_limit=limit if service else None, in_list_max=in_list_max)
    probe.stable_key_for_layer = lambda layer, scan=True: SimpleNamespace(
        name='gml_id' if key_field else '$id', is_field=key_field, origin=key_origin if key_field else 'none')
    probe.counts_cheaply = lambda layer: False
    formatter = types.ModuleType('filter_mate.core.filter.pk_formatter')
    formatter.QGIS_EXPRESSION = 'qgis'
    formatter.format_key_literal = lambda value, numeric, dialect: str(value) if numeric else "'{}'".format(value)
    formatter.is_null_value = lambda value: value is None
    utils = types.ModuleType('filter_mate.infrastructure.utils')
    utils.should_skip_expression_for_filtering = lambda expression: (
        not expression or not any(op in expression for op in ('=', '>', '<', ' IN ')), '')
    stable_key = types.ModuleType('filter_mate.core.domain.stable_key')
    stable_key.NAMED = 'named'
    stable_key.key_candidates = lambda names, local=True: [name for name in names
                                                           if name.lower() in ('gml_id', 'id', 'cleabs')]
    for module in (async_query, probe, formatter, utils, stable_key):
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
    def __init__(self, features=(), field_names=('gml_id', 'name'), subset=''):
        self.features = list(features)
        self.field_names = list(field_names)
        self.subset = subset
        self.reads = []
        self.provider_extent = MagicMock(isNull=MagicMock(return_value=False), isEmpty=MagicMock(return_value=False))
        for name in ('dataChanged', 'geometryChanged', 'willBeDeleted'):
            setattr(self, name, MagicMock())

    def id(self):
        return 'layer'

    def source(self):
        return 'source'

    def subsetString(self):
        return self.subset

    def crs(self):
        return 'EPSG:4326'

    def fields(self):
        names = self.field_names
        fields = MagicMock(field=MagicMock(return_value=MagicMock(isNumeric=MagicMock(return_value=True))),
                           indexOf=MagicMock(side_effect=lambda name: names.index(name) if name in names else -1))
        fields.__iter__.side_effect = lambda: iter([MagicMock(**{'name.return_value': name}) for name in names])
        return fields

    def selectedFeatureIds(self):
        return []

    def dataProvider(self):
        return SimpleNamespace(extent=lambda: self.provider_extent)

    def read(self, request):
        self.reads.append(request)
        return self.features


def _setup(monkeypatch, mode='custom_selection', custom='', checked=(), picker_fid=None, saved_fid=None,
           row_key=None, field_names=('gml_id', 'name'), subset='', **capability):
    fakes = _fake_modules(monkeypatch, **capability)
    warning = MagicMock()
    cls, namespace = _controller_class(warning)
    layer = Layer([Feature(1), Feature(2)], field_names=field_names, subset=subset)
    picker_feature = Feature(picker_fid) if picker_fid is not None else MagicMock(isValid=MagicMock(return_value=False))
    if row_key is None:
        row_key = 'gml_id' if capability.get('key_field', True) else '$id'
    rows = MagicMock(getIdentifierFieldName=MagicMock(return_value=row_key))
    widgets = {'EXPLORING': {
        'CUSTOM_SELECTION_EXPRESSION': {'WIDGET': MagicMock(expression=MagicMock(return_value=custom))},
        'MULTIPLE_SELECTION_FEATURES': {'WIDGET': MagicMock(checkedItems=MagicMock(return_value=list(checked)),
                                                            list_widgets={'layer': rows})},
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
    assert env.controller.remote_filter_refused() is True
    assert 'stable key' in env.warning.call_args.args[0]
    env.warning.reset_mock()
    # The selection itself stays readable (map selection, tracking zoom, identify).
    assert env.controller._remote_features() == ([], '')
    assert env.controller._remote_selection_refused is False
    _submitted_request(env)
    assert env.layer.reads[0].fids == [4, 7]
    assert not env.warning.called


def test_a_service_list_keyed_by_feature_id_filters_with_its_stable_key(monkeypatch):
    env = _setup(monkeypatch, mode='multiple_selection', checked=[('n', 1), ('m', 2)], row_key='$id')
    assert env.controller.remote_filter_refused() is False
    env.controller._remote_features()
    env.submit.call_args.args[5](_submitted_request(env))
    assert env.controller._remote_selection_result[2] == '"gml_id" IN (1, 2)'
    assert env.controller.remote_filter_refused(read=True) is False


def test_a_service_list_keyed_by_feature_id_with_a_null_key_refuses_its_filter(monkeypatch):
    env = _setup(monkeypatch, mode='multiple_selection', checked=[('n', 1), ('m', 2)], row_key='$id')
    env.layer.features = [Feature(1), Feature(2, key=None)]
    env.controller._remote_features()
    env.submit.call_args.args[5](_submitted_request(env))
    assert env.controller.remote_filter_refused(read=True) is True


@pytest.mark.parametrize('null', [None, 'NULL', 'None'])
def test_a_checked_row_with_a_null_key_refuses_the_filter_before_reading(monkeypatch, null):
    # "gml_id" IN (NULL) keeps nothing: the list shows a NULL key as text.
    env = _setup(monkeypatch, mode='multiple_selection', checked=[('n', 1), ('m', null)])
    assert env.controller.remote_filter_refused() is True
    env.submit.assert_not_called()


@pytest.mark.parametrize('flag', ['_remote_selection_refused', '_remote_selection_waiting'])
def test_a_replayed_filter_stops_on_a_refused_or_loading_service_selection(monkeypatch, flag):
    env = _setup(monkeypatch, custom='"id" > 1')
    setattr(env.controller, flag, True)
    assert env.controller.remote_filter_blocked() is True


def test_a_read_service_selection_with_a_null_key_refuses_its_filter(monkeypatch):
    """"id" IN (NULL) keeps nothing: the Filter would empty the source and filter the targets on nothing."""
    env = _setup(monkeypatch, mode='single_selection', saved_fid=1)
    env.layer.features = [Feature(1, key=None)]
    assert env.controller.remote_filter_refused() is False
    env.controller._remote_features()
    env.submit.call_args.args[5](_submitted_request(env))   # the read delivers
    assert env.controller.remote_filter_refused(read=True) is True
    assert 'stable key' in env.warning.call_args.args[0]


def test_a_single_selection_of_a_service_without_stable_key_refuses_its_filter(monkeypatch):
    env = _setup(monkeypatch, mode='single_selection', saved_fid=1, key_field=False)
    assert env.controller.remote_filter_refused() is True


def test_a_declared_key_is_the_only_one_a_multiple_selection_may_send(monkeypatch):
    # An ArcGIS layer declaring OBJECTID: a list keyed by a business "id" could keep other features.
    env = _setup(monkeypatch, mode='multiple_selection', checked=[('n', 1)], row_key='id',
                 field_names=('gml_id', 'id'), key_origin='declared')
    assert env.controller.remote_filter_refused() is True


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


# --- review of this lot: findings fixed ---------------------------------------------------------------

def test_rows_keyed_by_an_older_registered_key_filter_on_that_key(monkeypatch):
    """The checked values are values of the list's identifier, not of a recomputed key."""
    env = _setup(monkeypatch, mode='multiple_selection', checked=[('n', 'A1'), ('m', 'B2')], service=False,
                 key_field=False, row_key='code', field_names=('code', 'name'))
    assert env.controller._remote_features() == ([], '"code" IN (A1, B2)')
    assert env.controller._remote_selection_refused is False


def test_a_service_list_keyed_by_another_field_than_its_stable_key_refuses_the_filter(monkeypatch):
    env = _setup(monkeypatch, mode='multiple_selection', checked=[('n', 1), ('m', 2)], row_key='population',
                 field_names=('gml_id', 'population'))
    assert env.controller.remote_filter_refused() is True
    assert 'stable key' in env.warning.call_args.args[0]


def test_a_service_list_keyed_by_a_trusted_key_name_keeps_its_filter(monkeypatch):
    # An older project registered "id" while the stable key is now gml_id: both are trusted names.
    env = _setup(monkeypatch, mode='multiple_selection', checked=[('n', 1), ('m', 2)], row_key='id',
                 field_names=('gml_id', 'id'))
    assert env.controller.remote_filter_refused() is False
    assert env.controller._remote_features() == ([], '"id" IN (1, 2)')


def test_a_syntax_error_is_refused_without_reading_even_off_a_service(monkeypatch):
    env = _setup(monkeypatch, custom='"name" = ', service=False)
    env.async_query.read_refusal.return_value = 'syntax'
    assert env.controller._remote_features() == ([], '')
    assert env.controller._remote_selection_refused is True
    assert env.layer.reads == [] and not env.submit.called
    assert env.warning.call_args.args[0] == 'refused: syntax'


def test_a_failed_read_on_the_gui_thread_refuses_instead_of_raising(monkeypatch):
    env = _setup(monkeypatch, custom='aggregate(\'x\', \'sum\', "v") > 1', service=False)
    env.async_query.read_refusal.return_value = 'unsafe'
    env.layer.read = MagicMock(side_effect=RuntimeError('connection lost'))
    assert env.controller._remote_features() == ([], '')
    assert env.controller._remote_selection_refused is True
    assert env.async_query.read_failures == [env.layer]


@pytest.mark.parametrize('service,subset', [(True, '"id" > 3'), (False, '')])
def test_zoom_without_selection_reads_in_a_task_unless_an_unfiltered_service(monkeypatch, service, subset):
    """A filtered service's provider extent is the whole service; a database computes its extent with a query."""
    env = _setup(monkeypatch, custom='', service=service, subset=subset)
    env.layer.dataProvider = MagicMock(side_effect=AssertionError('extent read on the GUI thread'))
    assert env.controller._queue_remote_zoom(env.controller._remote_zoom_request()) is True
    env.submit.assert_called_once()
    env.canvas.zoomToFeatureExtent.assert_not_called()


def test_an_untransformable_zoom_extent_does_not_raise(monkeypatch):
    env = _setup(monkeypatch, custom='')
    env.canvas.mapSettings.return_value.destinationCrs.return_value = 'EPSG:2154'
    transform = MagicMock()
    transform.return_value.transformBoundingBox.side_effect = RuntimeError('QgsCsException')
    monkeypatch.setitem(env.controller._zoom_canvas_to.__func__.__globals__, 'QgsCoordinateTransform', transform)
    assert env.controller._queue_remote_zoom(env.controller._remote_zoom_request()) is True
    env.canvas.zoomToFeatureExtent.assert_not_called()
