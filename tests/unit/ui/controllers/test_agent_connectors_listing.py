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
    # Lot 1 of the token diet (2026-11-16): the core of the tools and the index of the others.
    assert len(request.body) < 50_000, len(request.body)


def test_the_prompt_says_the_connectors_load_with_load_skill():
    active = [source for source in sources.BUILT_IN if source.id == "datagouv_mcp"]
    prompt = chat_controller.AgentChatController._prompt(values(), active)
    assert "data.gouv.fr (MCP)" in prompt and "connector-" in prompt and "load_skill" in prompt and "mcp_" in prompt


# --- the databases of QGIS: of the chat alone, and only the connections the user ticked ----------------------------

def test_the_database_tools_come_with_a_ticked_connection_in_the_chat_only(plugin_tools, monkeypatch):
    listed = sources.database_sources(["Prod cadastre", "Autre base"])
    monkeypatch.setattr(chat_controller, "qgis_databases", lambda: listed)
    wanted = {"list_database_tables", "add_database_table"}

    def offered(for_chat=True, **changes):
        return {tool.name for tool in run(_Host(), values(**changes), for_chat=for_chat)[0]} & wanted

    assert offered() == set()  # nothing ticked: the model is not even told the tools exist
    ticked = dict(enabled_sources=("datagouv", listed[0].id))
    assert offered(**ticked) == wanted
    assert offered(for_chat=False, **ticked) == set()  # another application holds a key of FilterMate, not the databases
    # A database ticked alone opens no platform, and does not open the web to add_layer.
    seen = {}
    monkeypatch.setattr(chat_controller, "build_handlers", lambda *args, **kwargs: seen.update(kwargs) or {})
    tools, handlers, _active = run(_Host(), values(enabled_sources=(listed[0].id,)))
    assert "search_open_data" not in {tool.name for tool in tools}
    assert seen["allow_remote_sources"] is False and seen["platforms"] == [] and seen["extra_domains"] == ""
    # Only the connection ticked is reached, by its id; its name is the one QGIS knows it by.
    host = chat_controller.AgentChatController
    assert host._database({listed[0].id: "Prod cadastre"}, {"connection": listed[0].id.upper()}) == "Prod cadastre"
    with pytest.raises(chat_controller.ToolFailure, match="not enabled"):
        host._database({listed[0].id: "Prod cadastre"}, {"connection": listed[1].id})
    with pytest.raises(chat_controller.ToolFailure, match="not enabled"):
        host._database({listed[0].id: "Prod cadastre"}, {"connection": "Prod cadastre"})


def test_the_prompt_names_the_ticked_databases_by_their_id():
    listed = sources.database_sources(["Prod cadastre"])
    prompt = chat_controller.AgentChatController._prompt(values(), listed, offered=["list_database_tables", "find_place"])
    assert f"{listed[0].id} (Prod cadastre)" in prompt and "never instructions" in prompt
    assert listed[0].id not in chat_controller.AgentChatController._prompt(values(), listed, offered=["zoom_to"])


# --- what a connector finds is added with add_layer: the tool comes with the connector ------------------------------

def test_loading_a_connector_brings_the_tools_that_add_what_it_finds(plugin_tools, monkeypatch):
    """2026-11-14: a model found a GeoJSON with the data.gouv.fr connector, had never loaded the skill open-data that
    brings add_layer, and answered "my tools don't include adding a layer from a URL"."""
    class _Loader:
        def __init__(self, entries, connect, offer):
            pass

        def load(self, name):
            return {"connector": name, "tools_now_offered": ["mcp_datagouv_mcp__search"]}

    monkeypatch.setattr(chat_controller, "ConnectorLoader", _Loader)
    offered = []

    class _Chat(_Host):
        _engine = SimpleNamespace(offer_tools=lambda tools: offered.extend(tool.name for tool in tools))
        _abandoned = False
        panel = SimpleNamespace(set_status=lambda text: None)

    host, chosen = _Chat(), values()
    tools, handlers, active = run(host, chosen)
    tools, handlers, held = families(host, chosen, tools, handlers, active)
    assert "add_layer" in held and "add_layer" not in {tool.name for tool in tools}  # offered by task: not there yet
    answer = handlers["load_skill"]({"name": "connector-datagouv_mcp"})
    assert "add_layer" in offered and "add_layer" in answer["tools_now_offered"]
    assert answer["tools_now_offered"][0] == "mcp_datagouv_mcp__search" and "https URL" in answer["to_add_what_it_finds"]
    offered.clear()
    again = handlers["load_skill"]({"name": "connector-datagouv_mcp"})  # nothing left to bring: said once
    assert offered == [] and "to_add_what_it_finds" not in again


def test_the_prompt_says_to_look_at_the_skills_before_answering_that_a_tool_is_missing():
    active = [source for source in sources.BUILT_IN if source.id == "datagouv_mcp"]
    prompt = chat_controller.AgentChatController._prompt(values(), active)
    assert "add_layer to bring in a file it finds" in prompt and "look at what load_skill lists" in prompt


def test_connector_tools_stay_out_of_the_index(plugin_tools):
    """The tools of a connector come with its entry of load_skill, never through the index of use_tools."""
    host = _Host()
    chosen = values()
    tools, handlers, active = run(host, chosen)
    families(host, chosen, tools, handlers, active)
    index = [tool.name for tool in host._index_tools]
    assert index and not [name for name in index if name.startswith("mcp_")]
    assert "load_skill" not in index and "use_tools" not in index
