"""Reads of the panel in tasks share one wait cursor, counted (audit of 2026-11-12).

The reads of the dock itself (filtered extent, debounced pick, service
expression) drove _set_expression_loading_state directly: one that ended
took the cursor away while another read still ran. They take the lease of
the EXPLORING controller instead, which counts every read of the panel.
"""
import ast
import builtins
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
                 'QgsFeatureRequest': MagicMock(), 'QgsRectangle': MagicMock()}
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
