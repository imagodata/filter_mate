# -*- coding: utf-8 -*-
"""local_copy comes into a conversation when a web service layer does (2026-11-22).

Left out of a conversation that started with nothing to copy (it would weigh on every request), it is offered from
the next request on once the project holds a web service layer, unless the user turned it off or a local model has
the filtering tools alone.
"""
import sys
import types

import pytest

from .test_agent_chat_lifecycle import _PKG, controller, ctrl_module, dock  # noqa: F401 (fixtures)

pytestmark = pytest.mark.unit


@pytest.fixture
def chat(ctrl_module, controller, monkeypatch):  # noqa: F811
    module = sys.modules[f"{_PKG}.ui.controllers.agent_chat_controller"]
    state = types.SimpleNamespace(web=True, offered=[])
    monkeypatch.setattr(module, "_holds_web_service_layers", lambda: state.web)
    controller._engine = types.SimpleNamespace(offer_tools=lambda tools: state.offered.extend(t.name for t in tools))
    controller._copy_offered = False
    values = types.SimpleNamespace(rules={}, preset="anthropic", local_filtering_only=False)
    return types.SimpleNamespace(module=module, controller=controller, state=state, values=values)


def test_offered_once_when_a_web_service_layer_comes_in(chat):
    chat.controller._offer_local_copy(chat.values)
    chat.controller._offer_local_copy(chat.values)
    assert chat.state.offered == ["local_copy"]


def test_not_offered_without_a_web_service_layer(chat):
    chat.state.web = False
    chat.controller._offer_local_copy(chat.values)
    assert chat.state.offered == []


def test_not_offered_when_turned_off_by_the_user(chat):
    chat.values.rules = {"local_copy": chat.module.RULE_NEVER}
    chat.controller._offer_local_copy(chat.values)
    assert chat.state.offered == []


def test_not_offered_to_a_local_model_with_the_filtering_tools_alone(chat):
    chat.values.preset, chat.values.local_filtering_only = "ollama", True
    chat.controller._offer_local_copy(chat.values)
    assert chat.state.offered == []


def test_not_offered_again_when_the_conversation_had_it(chat):
    chat.controller._copy_offered = True
    chat.controller._offer_local_copy(chat.values)
    assert chat.state.offered == []


def test_no_conversation_no_offer(chat):
    chat.controller._engine = None
    chat.controller._offer_local_copy(chat.values)
    assert chat.state.offered == []  # and nothing raised
