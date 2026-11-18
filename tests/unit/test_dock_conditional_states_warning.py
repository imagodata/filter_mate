# -*- coding: utf-8 -*-
"""
2026-11-18 audit: _setup_conditional_widget_states warned at every start-up that no widget was found for
``pushButton_checkable_filtering_auto_current_layer``, which is mapped on an empty list on purpose (it controls no
widget). A name that matches no widget still warns.
"""
import ast
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
AUTO = "pushButton_checkable_filtering_auto_current_layer"
TARGETS = "pushButton_checkable_filtering_layers_to_filter"


def _setup(dock):
    tree = ast.parse((ROOT / "filter_mate_dockwidget.py").read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterMateDockWidget")
    method = next(node for node in cls.body
                  if isinstance(node, ast.FunctionDef) and node.name == "_setup_conditional_widget_states")
    logger = MagicMock()
    namespace = {"logger": logger}
    exec(compile(ast.Module(body=[method], type_ignores=[]), "filter_mate_dockwidget.py", "exec"), namespace)
    types.MethodType(namespace["_setup_conditional_widget_states"], dock)()
    return logger


def _dock(**buttons):
    """A dock with some buttons and the methods the setup calls when it is done."""
    return types.SimpleNamespace(**buttons, _toggle_associated_widgets=MagicMock(),
                                 _setup_buffer_buttons_dependency=MagicMock(),
                                 _ensure_always_enabled_widgets=MagicMock())


def test_a_button_meant_to_control_nothing_does_not_warn():
    dock = _dock(**{AUTO: MagicMock()})
    logger = _setup(dock)
    warnings = [call.args[0] for call in logger.warning.call_args_list]
    assert not [text for text in warnings if AUTO in text]
    getattr(dock, AUTO).toggled.connect.assert_not_called()  # nothing to enable or disable
    dock._toggle_associated_widgets.assert_not_called()


def test_widget_names_that_match_nothing_still_warn():
    dock = _dock(**{TARGETS: MagicMock()})
    logger = _setup(dock)
    warnings = [call.args[0] for call in logger.warning.call_args_list]
    assert any("No widgets found for " + TARGETS in text for text in warnings)
