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


def test_use_tools_knows_it_once_offered(chat):
    """2026-11-24: use_tools answered "not available ... the agent settings" for a tool offered meanwhile."""
    chat.controller._known_tools = {"use_tools"}
    chat.controller._offer_local_copy(chat.values)
    assert "local_copy" in chat.controller._known_tools


def test_offered_in_the_turn_a_tool_adds_a_web_service_layer(chat, monkeypatch):
    """2026-11-24: a WFS layer the agent added waited for the next message of the user before it could be copied."""
    chat_controller = chat.controller
    monkeypatch.setattr(chat.module, "load_settings", lambda: chat.values)
    monkeypatch.setattr(chat.module, "made_layers", lambda before, after: [{"id": "w", "name": "Pays du monde"}])
    for name in ("panel", "_log_action", "_show_chart_card", "_offer_exploring", "describe_call", "_project_layers"):
        monkeypatch.setattr(chat_controller, name, types.SimpleNamespace(finish_steps=lambda ok: None,
                                                                    set_status=lambda text: None)
                            if name == "panel" else (lambda *args, **kwargs: {}), raising=False)
    chat_controller._abandoned, chat_controller._layers_before, chat_controller._request_calls = False, (), []
    call = types.SimpleNamespace(name="add_service_layer", arguments={})
    chat_controller.on_tool_end(call, types.SimpleNamespace(is_error=False, content="{}"))
    assert chat.state.offered == ["local_copy"]


def test_a_compaction_leaves_it_to_use_tools(chat):
    """Taken out of the request by a compaction: use_tools adds it again in the same request, instead of "not here"."""
    spec = types.SimpleNamespace(name="local_copy")
    chat.controller._tools = {"local_copy": spec}
    chat.controller._later, chat.controller._by_name = {}, {}
    chat.controller._known_tools = {"use_tools", "local_copy"}
    chat.controller._copy_offered = True
    chat.controller._release_tools(["local_copy"])
    assert chat.controller._later == {"local_copy": spec} and "local_copy" not in chat.controller._known_tools
    chat.controller._known_tools = None
    chat.controller._release_tools(["local_copy"])  # no use_tools in this conversation: nothing raised
