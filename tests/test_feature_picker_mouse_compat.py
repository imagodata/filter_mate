"""Exercise the feature picker mouse handler with strict Qt5/Qt6 event APIs."""

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mouse_handler():
    # Isolate the actual handler from QWidget construction and QGIS imports.
    path = Path(__file__).resolve().parents[1] / 'ui/widgets/custom_widgets.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    widget = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                  and node.name == 'QgsCheckableComboBoxFeaturesListPickerWidget')
    handler = next(node for node in widget.body if isinstance(node, ast.FunctionDef)
                   and node.name == 'eventFilter')
    namespace = {
        'is_layer_valid': lambda layer: True,
        'safe_iterate_features': lambda layer: [{'id': 42}],
        'QEvent': SimpleNamespace(Type=SimpleNamespace(MouseButtonPress=2)),
        'Qt': SimpleNamespace(
            MouseButton=SimpleNamespace(LeftButton=1, RightButton=2),
            CheckState=SimpleNamespace(Checked=2, Unchecked=0)),
        'QBrush': lambda color: color,
    }
    exec(compile(ast.Module(body=[handler], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace['eventFilter']


@pytest.mark.unit
@pytest.mark.parametrize('qt_version', [5, 6])
@pytest.mark.parametrize('initial_state', [None, 0, 2])
def test_left_click_with_qt5_and_qt6(mouse_handler, qt_version, initial_state):
    point = (12, 24)
    # SimpleNamespace deliberately exposes only the API of the chosen Qt version.
    event = SimpleNamespace(type=lambda: 2, button=lambda: 1)
    if qt_version == 5:
        event.pos = lambda: point
    else:
        event.position = lambda: SimpleNamespace(toPoint=lambda: point)

    item = None if initial_state is None else MagicMock()
    if item is not None:
        item.data.return_value = 42
        item.checkState.return_value = initial_state
    viewport = object()
    list_widget = MagicMock()
    list_widget.viewport.return_value = viewport
    list_widget.getIdentifierFieldName.return_value = 'id'
    list_widget.itemAt.return_value = item
    picker = SimpleNamespace(
        layer=SimpleNamespace(id=lambda: 'layer'),
        list_widgets={'layer': list_widget},
        font_by_state={'checked': ('font', 'color'), 'unChecked': ('font', 'color')},
        _emit_checked_items_update=MagicMock(),
    )

    assert mouse_handler(picker, viewport, event) is True
    list_widget.itemAt.assert_called_once_with(point)
    if item is None:
        picker._emit_checked_items_update.assert_not_called()
    else:
        item.setCheckState.assert_called_once_with(0 if initial_state == 2 else 2)
        picker._emit_checked_items_update.assert_called_once_with()
