# -*- coding: utf-8 -*-
"""The MCP connectors the user ticked, as entries of load_skill in the chat (lot A, 2026-11-14).

Nothing connects when a conversation starts: each conversation used to wait for every connector, one that stalled
among them, and their tools (about 77 kB with the built-in ones) went with every request. The modules are loaded for
real under a synthetic package; QGIS stays mocked by the root conftest.
"""
import importlib
import pathlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_agent_connectors_listing_test"


def _load():
    for name, path in (("", _ROOT), (".ui", _ROOT / "ui"), (".ui.controllers", _ROOT / "ui" / "controllers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    stubs = [name for name in ("qgis.PyQt.QtNetwork", "qgis.PyQt.QtXml") if name not in sys.modules]
    sys.modules.update({name: MagicMock() for name in stubs})
    try:  # bound at import; taken out again so that no other test sees them
        return (importlib.import_module(f"{_PKG}.ui.controllers.agent_chat_controller"),
                importlib.import_module(f"{_PKG}.adapters.agent.settings"),
                importlib.import_module(f"{_PKG}.core.agent.sources"),
                importlib.import_module(f"{_PKG}.core.agent.providers"),
                importlib.import_module(f"{_PKG}.core.agent.messages"))
    finally:
        for name in stubs:
            sys.modules.pop(name, None)


chat_controller, agent_settings, sources, providers, messages = _load()
run = chat_controller.AgentChatController.tools_and_handlers
families = chat_controller.AgentChatController._families


class _Host:
    """What tools_and_handlers and _families read of the controller: a portal-less accessor, placeholders."""

    local_filtering = staticmethod(chat_controller.AgentChatController.local_filtering)

    def _accessor(self):
        return SimpleNamespace(configured_domains=lambda: "")

    def __getattr__(self, name):
        return None


@pytest.fixture
def plugin_tools(monkeypatch):
    monkeypatch.setattr(chat_controller, "build_handlers", lambda *args, **kwargs: {})
    monkeypatch.setattr(chat_controller, "settings_handlers", lambda *args, **kwargs: {"load_skill": lambda arguments: {}})
    monkeypatch.setattr(chat_controller, "_default_export_root", lambda: None)


def values(**changes):
    made = dict(preset="anthropic", model="m", enabled_sources=("datagouv", "datagouv_mcp", "osm_mcp"))
    made.update(changes)
    return agent_settings.AgentSettings(**made)


def load_skill_of(tools):
    return next(tool for tool in tools if tool.name == "load_skill")


def names_of(tool):
    return tool.input_schema["properties"]["name"]["enum"]


def test_load_skill_lists_the_enabled_connectors_in_the_chat_only(plugin_tools):
    chat = load_skill_of(run(_Host(), values())[0])
    assert names_of(chat)[-2:] == ["connector-datagouv_mcp", "connector-osm_mcp"]
    assert "connector-datagouv_mcp: data.gouv.fr (MCP): Datasets, data services and table queries" in chat.description
    other = load_skill_of(run(_Host(), values(), for_chat=False)[0])
    assert "connector-" not in other.description
    assert not [name for name in names_of(other) if name.startswith("connector-")]


def test_no_connector_ticked_leaves_load_skill_as_it_was(plugin_tools):
    tools = run(_Host(), values(enabled_sources=("datagouv",)))[0]
    assert "connector-" not in load_skill_of(tools).description


@pytest.mark.parametrize("changes", [{"tool_rules": '{"load_skill": "never"}'},
                                     {"preset": "ollama", "local_filtering_only": True}],
                         ids=["load_skill turned off", "the filtering tools of a local model"])
def test_load_skill_stays_for_the_connectors_alone(plugin_tools, changes):
    tools, handlers, active = run(_Host(), values(**changes))
    assert names_of(load_skill_of(tools)) == ["connector-datagouv_mcp", "connector-osm_mcp"]
    kept, _handlers, held = families(_Host(), values(**changes), tools, handlers, active)
    assert held == set() and [tool.name for tool in kept] == [tool.name for tool in tools]


def test_the_starting_request_stays_under_50_kb(plugin_tools):
    every = agent_settings.AgentSettings(preset="anthropic", model="m",
                                         enabled_sources=tuple(source.id for source in sources.BUILT_IN))
    assert every.tool_families  # the default
    tools, handlers, active = run(_Host(), every)
    tools, _handlers, held = families(_Host(), every, tools, handlers, active)
    connectors = [name for name in names_of(load_skill_of(tools)) if name.startswith("connector-")]
    assert held and len(connectors) == len([source for source in sources.BUILT_IN if source.is_connector])
    assert not [tool.name for tool in tools if tool.name.startswith("mcp_")]
    request = providers.create_provider(providers.ProviderConfig("anthropic", "m")).build_request(
        chat_controller.AgentChatController._prompt(every, active),
        [messages.Message(messages.ROLE_USER, (messages.TextPart("Bonjour"),))], tools)
    assert len(request.body) < 50_000, len(request.body)


def test_the_prompt_says_the_connectors_load_with_load_skill():
    active = [source for source in sources.BUILT_IN if source.id == "datagouv_mcp"]
    prompt = chat_controller.AgentChatController._prompt(values(), active)
    assert "data.gouv.fr (MCP)" in prompt and "connector-" in prompt and "load_skill" in prompt and "mcp_" in prompt
