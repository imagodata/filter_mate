# -*- coding: utf-8 -*-
"""Several features selected on the map with sync on stay selected, and listed once each (2026-11-22).

The sync from the map moves the single group to the multiple one, then shows the first feature in the
single picker (setFeature). The picker announces it through its debounced featureChanged, 300 ms later,
out of the sync: the dock took it as a pick and replaced the selection of the map with that one feature,
the layer signals blocked (5 selected fell to 1, no selectionChanged). And the multiple list stored the
ids it checked in both forms (1 and '1'): 10 selected features for 5.

The methods are extracted with ast, the plugin modules are never imported.
"""
import ast
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[4]


def _method(path, name, **namespace):
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
    node = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)
    namespace = {'logger': MagicMock(), **namespace}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(ROOT / path), 'exec'), namespace)
    return namespace[name]


# --- the debounced pick of the single picker ------------------------------------------------------------------------

def _dock(group):
    layer = MagicMock(**{'getFeature.return_value': MagicMock(**{'isValid.return_value': True})})
    dock = SimpleNamespace(current_layer=layer, current_exploring_groupbox=group, _pending_feature_change_fid=1,
                           _is_layer_valid=lambda: True, exploring_features_changed=MagicMock(), _exploring_ctrl=None)
    dock._execute_debounced_feature_change = MethodType(
        _method('filter_mate_dockwidget.py', '_execute_debounced_feature_change'), dock)
    return dock


@pytest.fixture
def local_layer(monkeypatch):
    """counts_cheaply: a local layer, the feature is read at once."""
    import builtins
    original_import = builtins.__import__

    def fake_import(module, globals=None, locals=None, fromlist=(), level=0):
        if module.endswith('source_capability_probe'):
            return SimpleNamespace(counts_cheaply=lambda layer: True)
        return original_import(module, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, '__import__', fake_import)


@pytest.mark.parametrize('group', ['multiple_selection', 'custom_selection'])
def test_the_single_picker_set_by_the_sync_leaves_the_selection_of_another_group(local_layer, group):
    dock = _dock(group)
    dock._execute_debounced_feature_change()
    dock.exploring_features_changed.assert_not_called()
    assert dock._pending_feature_change_fid is None


def test_a_pick_in_the_single_group_still_drives_the_selection(local_layer):
    dock = _dock('single_selection')
    dock._execute_debounced_feature_change()
    dock.exploring_features_changed.assert_called_once_with(dock.current_layer.getFeature.return_value)


# --- the features checked in the multiple list from the map ---------------------------------------------------------

Qt = SimpleNamespace(CheckState=SimpleNamespace(Checked=2, Unchecked=0))


class _Item:
    def __init__(self, fid):
        self.values = {0: f'zone {fid}', 3: fid, 4: 'True'}
        self.state = Qt.CheckState.Unchecked

    def data(self, role):
        return self.values.get(role)

    def setData(self, role, value):
        self.values[role] = value

    def checkState(self):
        return self.state

    def setCheckState(self, state):
        self.state = state


class _List:
    def __init__(self, fids):
        self.items = [_Item(fid) for fid in fids]
        self.selected_features_list = []
        self.setCheckedByFeatureIds = MethodType(
            _method('ui/widgets/custom_widgets.py', 'setCheckedByFeatureIds', Qt=Qt, QBrush=lambda color: color), self)

    def count(self):
        return len(self.items)

    def item(self, row):
        return self.items[row]

    def isTruncated(self):
        return False

    def getSearchText(self):
        return ''

    def setSelectedFeaturesList(self, selected):
        self.selected_features_list = selected

    def getSelectedFeaturesList(self):
        return self.selected_features_list


def test_features_checked_from_the_map_are_listed_once_each():
    layer = MagicMock(**{'id.return_value': 'zones'})
    widget = SimpleNamespace(layer=layer, list_widgets={'zones': _List([1, 2, 3, 4, 5])}, items_le=MagicMock(),
                             checkedItems=lambda: [], font_by_state={state: ('font', 'color') for state in (
                                 'checked', 'checkedFiltered', 'unChecked', 'unCheckedFiltered')})
    set_checked = _method('ui/widgets/custom_widgets.py', 'setCheckedFeatureIds', Qt=Qt,
                          is_layer_valid=lambda layer: layer is not None)

    checked = set_checked(widget, [1, 2, 3, 4, 5], emit_signal=False)

    listed = widget.list_widgets['zones'].getSelectedFeaturesList()
    assert checked == 5
    assert [entry[1] for entry in listed] == [1, 2, 3, 4, 5]
    assert all(item.checkState() == Qt.CheckState.Checked for item in widget.list_widgets['zones'].items)
