"""The saved single pick of a web service is never read on the GUI thread (review of #193, M4/M5 follow-up).

A group switch, a layer change and the picker tooltip reloaded the saved
feature id with ``layer.getFeature``: a network request on the GUI thread
for a service. The saved id alone is handed over (exploring_features_changed
reads the feature in a task); the tooltip uses the picker's feature.
"""
import sys

import pytest


class _IdOnlyFeature:
    def __init__(self, fields, fid):
        self._fid, self._valid = fid, False

    def id(self):
        return self._fid

    def setValid(self, valid):
        self._valid = valid

    def isValid(self):
        return self._valid


@pytest.fixture(autouse=True)
def _id_only_feature(monkeypatch):
    monkeypatch.setattr(sys.modules['qgis.core'], 'QgsFeature', _IdOnlyFeature, raising=False)
import ast
import builtins
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[3]


def _method(path, name, **namespace):
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
    node = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)
    original_import = builtins.__import__

    def import_capability(module, globals=None, locals=None, fromlist=(), level=0):
        if module.endswith('source_capability_probe'):
            return SimpleNamespace(counts_cheaply=lambda layer: False)
        return original_import(module, globals, locals, fromlist, level)

    namespace.update({'__builtins__': dict(vars(builtins), __import__=import_capability), 'logger': MagicMock(),
                      'QCoreApplication': MagicMock()})
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(ROOT / path), 'exec'), namespace)
    return namespace[name]


def _service_layer():
    layer = MagicMock()
    layer.id.return_value = 'layer'
    layer.getFeature.side_effect = AssertionError('service read on the GUI thread')
    return layer


def test_layer_change_hands_the_saved_pick_of_a_service_over_unread():
    method = _method('ui/controllers/layer_sync_controller.py', '_restore_feature_selection_state')
    picker = MagicMock()
    dock = SimpleNamespace(current_layer=_service_layer(), current_exploring_groupbox='single_selection',
                           widgets={'EXPLORING': {'SINGLE_SELECTION_FEATURES': {'WIDGET': picker}}},
                           _last_single_selection_fid=7, _last_single_selection_layer_id='layer',
                           exploring_link_widgets=MagicMock(), exploring_features_changed=MagicMock(),
                           _execute_debounced_feature_change=MagicMock())
    controller = SimpleNamespace(dockwidget=dock)
    MethodType(method, controller)({'exploring': {'is_selecting': True}})
    dock.current_layer.getFeature.assert_not_called()
    (feature,), _ = dock.exploring_features_changed.call_args
    assert feature.id() == 7 and feature.isValid()


def test_picker_tooltip_never_reads_a_service():
    method = _method('filter_mate_dockwidget.py', '_update_feature_picker_tooltip')
    picker = MagicMock()
    picker.displayExpression.return_value = 'name'
    picker.feature.return_value.isValid.return_value = False
    dock = SimpleNamespace(current_layer=_service_layer(), _last_single_selection_fid=7,
                           _last_single_selection_layer_id='layer')
    MethodType(method, dock)(picker)
    dock.current_layer.getFeature.assert_not_called()


def test_single_group_switch_hands_the_saved_pick_of_a_service_over_unread():
    method = _method('filter_mate_dockwidget.py', '_configure_single_selection_groupbox')
    picker = MagicMock()
    dock = SimpleNamespace(
        current_layer=_service_layer(), widgets={'EXPLORING': {'SINGLE_SELECTION_FEATURES': {'WIDGET': picker}}},
        _last_single_selection_fid=7, _last_single_selection_layer_id='layer', _syncing_from_qgis=False,
        _configure_groupbox_common=MagicMock(return_value={}), _ensure_selection_changed_connected=MagicMock(),
        manageSignal=MagicMock(), exploring_link_widgets=MagicMock(), exploring_features_changed=MagicMock(),
        _update_exploring_buttons_state=MagicMock(), _execute_debounced_feature_change=MagicMock(),
        _debounced_exploring_features_changed=MagicMock())
    MethodType(method, dock)()
    dock.current_layer.getFeature.assert_not_called()
    (feature,), _ = dock.exploring_features_changed.call_args
    assert feature.id() == 7 and feature.isValid()
