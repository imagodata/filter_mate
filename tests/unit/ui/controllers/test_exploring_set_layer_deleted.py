# -*- coding: utf-8 -*-
"""
2026-09-14 (user report, QGIS 4.2.2): after a project switch the previous
current layer's C++ object is deleted; ExploringController.set_layer compared
it to the new layer and raised "wrapped C/C++ object of type QgsVectorLayer
has been deleted" up to the QGIS error dialog. Method extracted with ast.
"""
import ast
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_MODULE = Path(__file__).resolve().parents[4] / "ui" / "controllers" / "exploring_controller.py"


def _set_layer():
    tree = ast.parse(_MODULE.read_text(encoding="utf-8"))
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == "set_layer":
                from typing import Optional
                ns = {"logger": MagicMock(), "Optional": Optional, "QgsVectorLayer": MagicMock}
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(_MODULE), "exec"), ns)
                return ns["set_layer"]
    raise AssertionError("set_layer not found")


class _DeletedLayer:
    """A sip wrapper whose C++ object is gone: every access raises RuntimeError."""

    def __eq__(self, other):
        raise RuntimeError("wrapped C/C++ object of type QgsVectorLayer has been deleted")

    __ne__ = __eq__
    __hash__ = object.__hash__

    def id(self):
        raise RuntimeError("wrapped C/C++ object of type QgsVectorLayer has been deleted")


def _controller(old_layer, valid):
    ctrl = types.SimpleNamespace(_current_layer=old_layer, _current_field="f",
                                 _dockwidget=MagicMock(), _populate_field_combo=MagicMock(),
                                 _clear_field_combo=MagicMock(), _clear_features_list=MagicMock())
    ctrl.is_layer_valid = lambda layer: valid(layer)
    ctrl.set_layer = types.MethodType(_set_layer(), ctrl)
    return ctrl


@pytest.mark.unit
class TestSetLayerWithDeletedPreviousLayer:

    def test_deleted_previous_layer_is_ignored(self):
        dead = _DeletedLayer()
        new_layer = MagicMock()
        ctrl = _controller(dead, valid=lambda layer: layer is new_layer)

        ctrl.set_layer(new_layer)  # must not raise

        assert ctrl._current_layer is new_layer
        ctrl._dockwidget._exploring_cache.invalidate_layer.assert_not_called()
        ctrl._populate_field_combo.assert_called_once_with(new_layer)

    def test_live_previous_layer_cache_is_invalidated(self):
        old, new_layer = MagicMock(), MagicMock()
        old.id.return_value = "old-id"
        ctrl = _controller(old, valid=lambda layer: True)

        ctrl.set_layer(new_layer)

        ctrl._dockwidget._exploring_cache.invalidate_layer.assert_called_once_with("old-id")
        assert ctrl._current_layer is new_layer

    def test_invalid_new_layer_clears_the_widgets(self):
        ctrl = _controller(None, valid=lambda layer: False)
        ctrl.set_layer(MagicMock())
        assert ctrl._current_layer is None
        ctrl._clear_field_combo.assert_called_once()
        ctrl._clear_features_list.assert_called_once()
