"""Regression checks for edits made while a remote list read is pending."""
import ast
from pathlib import Path
from types import SimpleNamespace, MethodType
from unittest.mock import MagicMock

PATH = Path(__file__).resolve().parents[4] / 'ui/widgets/custom_widgets.py'


def method(name):
    tree = ast.parse(PATH.read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == 'QgsCheckableComboBoxFeaturesListPickerWidget')
    node = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)
    namespace = {'is_layer_valid': lambda layer: True}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(PATH), 'exec'), namespace)
    return namespace[name]


def test_clearing_a_pending_search_schedules_the_unsearched_generation():
    layer, rows = MagicMock(), MagicMock()
    layer.id.return_value = 'layer'
    rows.isTruncated.return_value = True
    rows.getSearchText.return_value = ''  # Previous completed page was unsearched.
    rows.getDisplayExpression.return_value = 'name'
    rows.count.return_value = 0
    widget = SimpleNamespace(layer=layer, list_widgets={'layer': rows}, _requested_search='Paris',
                             _populate_features_sync=MagicMock(), filteringCheckedItemList=MagicMock())
    MethodType(method('filter_items'), widget)('')
    widget._populate_features_sync.assert_called_once_with('name', preserve_checked=True, search_text=None)


def test_deselect_all_invalidates_pending_select_all_and_recovery():
    layer, rows = MagicMock(), MagicMock()
    layer.id.return_value = 'layer'
    rows.count.return_value = 0
    slot = MagicMock()
    widget = SimpleNamespace(layer=layer, list_widgets={'layer': rows}, _pending_select_all='Select All',
                             _lookup_query=slot, _emit_checked_items_update=MagicMock())
    MethodType(method('deselect_all'), widget)('De-select All')
    assert widget._pending_select_all is None
    slot.cancel.assert_called_once()
    widget._emit_checked_items_update.assert_called_once_with(force_emit=True)
