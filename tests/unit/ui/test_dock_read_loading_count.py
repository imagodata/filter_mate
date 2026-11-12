"""Reads of the panel in tasks share one wait cursor, counted (audit of 2026-11-12).

The reads of the dock itself (filtered extent, debounced pick, service
expression) drove _set_expression_loading_state directly: one that ended
took the cursor away while another read still ran. They take the lease of
the EXPLORING controller instead, which counts every read of the panel.
"""
import ast
import builtins
import importlib.util
import sys
import types
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[3]


def _method(path, name, submit=None):
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
    node = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)
    original_import = builtins.__import__
    fakes = {
        'source_capability_probe': SimpleNamespace(counts_cheaply=lambda layer: False),
        'async_query': SimpleNamespace(submit_query=submit, collect_extent=MagicMock(), read_now=MagicMock(),
                                       read_refusal=lambda layer, request: None, refusal_message=str),
    }

    def import_fake(module, globals=None, locals=None, fromlist=(), level=0):
        for suffix, fake in fakes.items():
            if module.endswith(suffix):
                return fake
        return original_import(module, globals, locals, fromlist, level)

    namespace = {'__builtins__': dict(vars(builtins), __import__=import_fake), 'logger': MagicMock(),
                 'QgsFeatureRequest': MagicMock(), 'QgsRectangle': MagicMock(), 'Qt': MagicMock()}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(ROOT / path), 'exec'), namespace)
    return namespace[name]


def _dock(controller):
    layer = MagicMock(**{'id.return_value': 'layer', 'source.return_value': 'source',
                         'subsetString.return_value': ''})
    return SimpleNamespace(current_layer=layer, tr=lambda text: text, _exploring_ctrl=controller,
                           _set_expression_loading_state=MagicMock(), _pending_feature_change_fid=7,
                           _is_layer_valid=lambda: True)


READS = [('_remote_filtered_extent', lambda dock: (dock.current_layer,)),
         ('_execute_debounced_feature_change', lambda dock: ()),
         ('get_exploring_features_async', lambda dock: ('"id" > 0',))]


@pytest.mark.parametrize('name, arguments', READS)
def test_a_read_of_the_dock_takes_the_counted_lease_of_the_panel(name, arguments):
    submit = MagicMock()
    controller = SimpleNamespace(_remote_loading=MagicMock(), _read_mode=lambda *args: 'task')
    dock = _dock(controller)
    MethodType(_method('filter_mate_dockwidget.py', name, submit), dock)(*arguments(dock))
    assert submit.call_args.args[6] is controller._remote_loading


@pytest.mark.parametrize('name, arguments', [read for read in READS if read[0] != '_execute_debounced_feature_change'])
def test_without_a_controller_the_dock_drives_the_cursor_itself(name, arguments):
    submit = MagicMock()
    dock = _dock(None)
    MethodType(_method('filter_mate_dockwidget.py', name, submit), dock)(*arguments(dock))
    assert submit.call_args.args[6] == dock._set_expression_loading_state


def test_a_read_that_ends_leaves_the_cursor_to_a_read_still_running():
    dock = SimpleNamespace(_set_expression_loading_state=MagicMock())
    lease = MethodType(_method('ui/controllers/exploring_controller.py', '_remote_loading'),
                       SimpleNamespace(_dockwidget=dock))
    lease(True)   # the filtered extent of the dock
    lease(True)   # the values of the controller
    lease(False)  # the extent is read
    assert [call.args for call in dock._set_expression_loading_state.call_args_list] == [(True,)]
    lease(False)
    assert [call.args for call in dock._set_expression_loading_state.call_args_list] == [(True,), (False,)]


@pytest.fixture
def async_query(monkeypatch):
    """adapters/qgis/async_query.py over a QgsTask without Qt (as in tests/unit/adapters/qgis/test_async_query.py)."""
    core = types.ModuleType('qgis.core')

    class Task:
        class Flag:
            CanCancel = 1

        def __init__(self, *args):
            self.cancelled = False

        def setDependentLayers(self, layers):
            pass

        def cancel(self):  # still queued: QGIS calls finished(false) before cancel() returns
            if not self.cancelled:
                self.cancelled = True
                self.finished(False)

        def isCanceled(self):
            return self.cancelled

    core.QgsTask = Task
    core.QgsFeedback = MagicMock(side_effect=lambda: MagicMock())
    core.QgsVectorLayerFeatureSource = MagicMock(side_effect=lambda layer: MagicMock())
    core.QgsExpression = MagicMock()
    core.QgsApplication = MagicMock()
    monkeypatch.setitem(sys.modules, 'qgis.core', core)
    spec = importlib.util.spec_from_file_location('async_query_cursor_test', ROOT / 'adapters/qgis/async_query.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, '_watcher', lambda callback: SimpleNamespace(changed=callback, deleteLater=MagicMock()))
    monkeypatch.setattr(module, 'unsafe_virtual_fields', lambda layer: set())
    return module


def _layer(name):
    return MagicMock(**{'id.return_value': name, 'source.return_value': 'source', 'subsetString.return_value': '',
                        'providerType.return_value': 'wfs'})


def test_a_layer_change_takes_the_reads_of_the_dock_off_the_wait_cursor(async_query):
    """A filtered extent of the layer left (30 to 120 s on a slow service) kept the cursor of the next layer."""
    dock = SimpleNamespace(_set_expression_loading_state=MagicMock())
    controller = SimpleNamespace(_dockwidget=dock)
    for name in ('_remote_loading', '_cancel_remote_reads'):
        setattr(controller, name, MethodType(_method('ui/controllers/exploring_controller.py', name), controller))
    lease = controller._remote_loading
    left, current = _layer('left'), _layer('current')
    for owner, attribute in ((dock, '_extent_query_left'), (dock, '_debounced_feature_query'),
                             (dock, '_remote_expression_query'), (controller, '_selection_query')):
        async_query.submit_query(owner, attribute, left, 'read', lambda task: None, MagicMock(), lease)
    controller._cancel_remote_reads()  # set_layer(current)
    read = async_query.submit_query(controller, '_selection_query', current, 'read', lambda task: [], MagicMock(), lease)
    read.finished(read.run())
    assert [call.args for call in dock._set_expression_loading_state.call_args_list] == [
        (True,), (False,), (True,), (False,)]
    assert controller._remote_loading_count == 0


@pytest.mark.parametrize('count, removed', [(1, False), (0, True)])
def test_a_direct_removal_leaves_the_cursor_to_a_read_still_running(count, removed):
    """The expression debounce, the local evaluator... took the cursor away while a read of the panel ran."""
    widgets = {name: MagicMock() for name in (
        'mFieldExpressionWidget_exploring_single_selection', 'mFeaturePickerWidget_exploring_single_selection',
        'mFieldExpressionWidget_exploring_multiple_selection',
        'checkableComboBoxFeaturesListPickerWidget_exploring_multiple_selection',
        'mFieldExpressionWidget_exploring_custom_selection')}
    dock = SimpleNamespace(_exploring_ctrl=SimpleNamespace(_remote_loading_count=count), **widgets)
    MethodType(_method('filter_mate_dockwidget.py', '_set_expression_loading_state'), dock)(False, None)
    assert all(widget.setCursor.called is removed for widget in widgets.values())
    MethodType(_method('filter_mate_dockwidget.py', '_set_expression_loading_state'), dock)(True, None)
    assert all(widget.setCursor.called for widget in widgets.values())
