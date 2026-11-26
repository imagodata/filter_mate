# -*- coding: utf-8 -*-
"""Effort changes affect the next request without clearing the user's conversation."""
import types
from unittest.mock import MagicMock

import pytest

from .test_agent_chat_lifecycle import controller, ctrl_module, dock  # noqa: F401

pytestmark = pytest.mark.unit


@pytest.fixture
def effort_controller(ctrl_module, controller, monkeypatch):  # noqa: F811
    values = types.SimpleNamespace(preset='anthropic', model='claude-haiku-5-5')
    monkeypatch.setattr(ctrl_module, 'load_settings', lambda: values)
    monkeypatch.setattr(ctrl_module, 'read_effort', lambda _values: '')
    monkeypatch.setattr(ctrl_module, 'write_effort', MagicMock())
    monkeypatch.setattr(controller, 'chat_busy', lambda: False)
    monkeypatch.setattr(controller, '_restart_engine', MagicMock())
    monkeypatch.setattr(controller, '_refresh_ready', MagicMock())
    controller.panel.clear_thread.reset_mock()
    return controller, ctrl_module, values


def test_effort_is_saved_and_the_conversation_is_not_cleared(effort_controller):
    ctrl, module, values = effort_controller
    ctrl._on_effort_changed('high')
    module.write_effort.assert_called_once_with(values, 'high')
    ctrl._restart_engine.assert_called_once_with()
    ctrl.panel.clear_thread.assert_not_called()


def test_a_running_turn_keeps_its_effort(effort_controller, monkeypatch):
    ctrl, module, _values = effort_controller
    monkeypatch.setattr(ctrl, 'chat_busy', lambda: True)
    ctrl._on_effort_changed('high')
    module.write_effort.assert_not_called()
    ctrl._restart_engine.assert_not_called()
    ctrl._refresh_ready.assert_called_once_with()


def test_an_invalid_effort_is_not_saved(effort_controller):
    ctrl, module, values = effort_controller
    values.model = 'claude-haiku-4-5'
    ctrl._on_effort_changed('high')
    module.write_effort.assert_not_called()
    ctrl._restart_engine.assert_not_called()
