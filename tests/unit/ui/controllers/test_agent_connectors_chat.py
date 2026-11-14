# -*- coding: utf-8 -*-
"""A connector loaded in the chat: asked first, then connected, its tools offered from the next turn (lot A).

2026-11-14: every conversation connected to every connector the user ticked before its first word, 20 s for one that
stalled. Now nothing connects until the model loads the entry of a connector with load_skill.
"""
import json
import sys
import types

import pytest

from .test_agent_chat_lifecycle import _PKG, controller, ctrl_module, dock  # noqa: F401 (fixtures)

pytestmark = pytest.mark.unit


def _core(name):
    return sys.modules[f"{_PKG}.core.agent.{name}"]


class FakeConnection:
    """What McpConnection does for the loader: one tool, ``hello``, answering "Bonjour"."""

    made = []

    def __init__(self, source):
        FakeConnection.made.append(source.id)
        self.source = source

    def list_tools(self):
        listing = {"tools": [{"name": "hello", "inputSchema": {"type": "object"}}]}
        return _core("mcp_client").tools_from_listing(self.source.id, self.source.title, listing)

    def call_tool(self, remote_name, arguments):
        return "Bonjour"


class Transport:
    def __init__(self):
        self.starts = []

    def start(self, request, parser, on_event):
        self.starts.append((request, on_event))
        return types.SimpleNamespace(abort=lambda: None)

    def emit(self, event):
        self.starts[-1][1](event)


def tool_names(start):
    return [tool["name"] for tool in json.loads(start[0].body)["tools"]]


def tool_turn(name, arguments, call_id="c1"):
    messages = _core("messages")
    return messages.TurnComplete(
        messages.Message(messages.ROLE_ASSISTANT, (messages.ToolCallPart(call_id, name, arguments),)),
        messages.STOP_TOOL_USE)


def anthropic_provider():
    providers = _core("providers")
    return providers.create_provider(providers.ProviderConfig("anthropic", "m"))


def _parts():
    """A local connector the user ticked, load_skill listing it, and the handler of a skill."""
    source = _core("sources").make_source("http://127.0.0.1:3000/mcp", "mcp", "Local")
    entry = _core("connectors").connector_entries([source])[0]
    load = _core("tool_catalog").skill_tool(None, connectors=[(entry.name, entry.line)])
    return source, load, {"load_skill": lambda arguments: {"instructions": "..."}}


@pytest.fixture
def chat(ctrl_module, controller, monkeypatch):  # noqa: F811
    FakeConnection.made = []
    monkeypatch.setattr(ctrl_module, "McpConnection", FakeConnection)
    source, load, handlers = _parts()
    values = types.SimpleNamespace(tool_families=False, rules={})
    tools, handlers, held = controller._families(values, [load], handlers, [source])
    assert held == set()
    session = _core("session").AgentSession(anthropic_provider(), tools, "S")
    transport = Transport()
    executor = _core("tool_executor").ToolExecutor(tools, controller._chat_owned(handlers))
    engine = _core("chat_engine").ChatEngine(session, executor, transport, controller, controller._checkpoint,
                                             policy=controller._policy)
    controller._engine = engine
    return engine, session, transport, source


def test_loading_a_connector_asks_then_offers_its_tools_from_the_next_turn(chat, controller):  # noqa: F811
    engine, session, transport, source = chat
    asked = []
    controller._ask_user = lambda title, text: asked.append((text, list(FakeConnection.made))) or True
    engine.send("dis bonjour")
    transport.emit(tool_turn("load_skill", {"name": "connector-" + source.id}))
    question, connected_before = asked[0]
    assert connected_before == [] and "Local" in question and "127.0.0.1:3000" in question  # asked, then connected
    assert "on this computer" in question and FakeConnection.made == [source.id]
    hello = "mcp_" + source.id + "__hello"
    assert hello not in tool_names(transport.starts[0]) and tool_names(transport.starts[-1])[-1] == hello
    load_call = _core("messages").ToolCallPart("c9", "load_skill", {"name": "connector-" + source.id})
    assert controller._describe(load_call) == "Connector: Local"
    transport.emit(tool_turn("load_skill", {"name": "connector-" + source.id}, "c2"))
    assert len(asked) == 1 and FakeConnection.made == [source.id]  # loaded again: no question, no connection
    transport.emit(tool_turn(hello, {}, "c3"))
    assert "Bonjour" in session.messages[-1].parts[0].content
    assert controller._describe(_core("messages").ToolCallPart("c4", hello, {})).startswith("Local: ")


def test_a_no_is_kept_for_the_conversation_and_forgotten_with_it(chat, controller):  # noqa: F811
    engine, session, transport, source = chat
    asked = []
    controller._ask_user = lambda title, text: asked.append(text) or False
    engine.send("dis bonjour")
    transport.emit(tool_turn("load_skill", {"name": "connector-" + source.id}))
    transport.emit(tool_turn("load_skill", {"name": "connector-" + source.id}, "c2"))
    assert len(asked) == 1 and FakeConnection.made == []
    assert "do not ask again in this conversation" in session.messages[-1].parts[0].content
    controller.new_conversation()
    assert controller._policy.declined == frozenset()


def test_at_the_advisor_level_nothing_is_asked_nor_connected(chat, controller):  # noqa: F811
    """The tools of a connector never run at that level: asking, then connecting, would be for nothing."""
    engine, session, transport, source = chat
    controller._policy.set_level("advisor")
    asked = []
    controller._ask_user = lambda title, text: asked.append(text) or True
    engine.send("dis bonjour")
    transport.emit(tool_turn("load_skill", {"name": "connector-" + source.id}))
    assert asked == [] and FakeConnection.made == []
    assert "advise only" in session.messages[-1].parts[0].content


def test_a_connector_loaded_is_not_asked_again_after_another_level(chat, controller):  # noqa: F811
    """A review of 2026-11-14: asked again, a no marked it declined while its tools stayed offered."""
    engine, session, transport, source = chat
    asked = []
    controller._ask_user = lambda title, text: asked.append(text) or True
    engine.send("dis bonjour")
    transport.emit(tool_turn("load_skill", {"name": "connector-" + source.id}))
    controller._policy.set_level("careful")
    controller._ask_user = lambda title, text: asked.append(text) or False
    transport.emit(tool_turn("load_skill", {"name": "connector-" + source.id}, "c2"))
    assert len(asked) == 1 and not session.messages[-1].parts[0].is_error
    assert controller._policy.declined == frozenset()


def test_the_tools_of_a_connector_go_with_the_conversation(chat, controller):  # noqa: F811
    engine, session, transport, source = chat
    engine.send("dis bonjour")
    transport.emit(tool_turn("load_skill", {"name": "connector-" + source.id}))
    hello = "mcp_" + source.id + "__hello"
    assert hello in controller._tools and hello in controller._connector_labels
    controller._engine = None  # over, as new_conversation finds it once the turn ended
    controller.new_conversation()
    assert hello not in controller._tools and controller._connector_labels == {} and controller._connectors is None


def test_a_connector_that_does_not_answer_is_said_and_the_status_is_cleared(chat, controller, ctrl_module):  # noqa: F811
    engine, session, transport, source = chat
    mcp_error = _core("mcp_client").McpError

    def refused(source):
        raise mcp_error("Local: Connection refused")
    ctrl_module.McpConnection = refused
    engine.send("dis bonjour")
    transport.emit(tool_turn("load_skill", {"name": "connector-" + source.id}))
    answer = session.messages[-1].parts[0]
    assert answer.is_error and "does not answer" in answer.content and "Connection refused" in answer.content
    statuses = [call.args[0] for call in controller.panel.set_status.call_args_list]
    connecting = statuses.index("Connecting to Local…")
    assert statuses[connecting + 1] == "" and not controller._policy.granted
    assert "Not reachable" not in str(controller.panel.add_note.call_args_list)


def test_nothing_connects_when_a_conversation_starts(ctrl_module, controller, monkeypatch):  # noqa: F811
    FakeConnection.made = []
    source, load, handlers = _parts()
    ready = types.SimpleNamespace(has_consent=True, model="m", needs_key=False, has_key=False, tool_families=True,
                                  rules={}, send_values=True, preset="anthropic", local_filtering_only=False)
    monkeypatch.setattr(ctrl_module, "McpConnection", FakeConnection)
    monkeypatch.setattr(ctrl_module, "load_settings", lambda: ready)
    monkeypatch.setattr(ctrl_module, "provider_config", lambda values, key: None, raising=False)
    monkeypatch.setattr(ctrl_module, "create_provider", lambda config: anthropic_provider())
    monkeypatch.setattr(controller, "tools_and_handlers", lambda values, for_chat=True: ([load], handlers, [source]))
    assert controller._build_engine() is not None and FakeConnection.made == []
    assert "Not reachable" not in str(controller.panel.add_note.call_args_list)
