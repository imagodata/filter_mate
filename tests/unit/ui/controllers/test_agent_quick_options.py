# -*- coding: utf-8 -*-
"""Providers, sources and the MCP server turned on or off from the agent: from the menu of the AGENT panel at once,
from the chat once the request ends (2026-11-16). QGIS stays mocked by the root conftest; the controller is loaded
for real under a synthetic package."""
import importlib
import importlib.util
import pathlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_agent_quick_options_test"


def _load():
    for name, path in (("", _ROOT), (".ui", _ROOT / "ui"), (".ui.controllers", _ROOT / "ui" / "controllers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    stubs = [name for name in ("qgis.PyQt.QtNetwork", "qgis.PyQt.QtXml") if name not in sys.modules]
    sys.modules.update({name: MagicMock() for name in stubs})
    try:  # bound at import; taken out again so that no other test sees them
        return (importlib.import_module(f"{_PKG}.ui.controllers.agent_chat_controller"),
                importlib.import_module(f"{_PKG}.adapters.agent.settings"))
    finally:
        for name in stubs:
            sys.modules.pop(name, None)


chat_controller, agent_settings = _load()
Controller = chat_controller.AgentChatController


def test_saving_a_provider_with_consent_remembers_it(monkeypatch):
    from core.agent.agent_options import ProviderEntry
    saved = []
    monkeypatch.setattr(chat_controller, "read_providers", lambda: (ProviderEntry("openai", "gpt-x", "u"),))
    monkeypatch.setattr(chat_controller, "write_providers", saved.append)
    values = agent_settings.AgentSettings(preset="ollama", model="qwen3:8b", base_url="http://localhost:11434",
                                          consent=True)
    Controller._remember_provider(values)
    assert [entry.label for entry in saved[0]] == ["ollama · qwen3:8b", "openai · gpt-x"]
    saved.clear()
    Controller._remember_provider(agent_settings.AgentSettings(preset="ollama", model="qwen3:8b", consent=False))
    assert saved == []


# --- one way to apply a change, at once (a click) or once the request ends (the agent) ---------------------------


from core.agent.agent_options import Change, ProviderEntry  # noqa: E402


@pytest.fixture
def host(monkeypatch):
    store = {"values": agent_settings.AgentSettings(preset="anthropic", model="m", consent=True, authcfg="key1",
                                                    enabled_sources=("datagouv",))}
    monkeypatch.setattr(chat_controller, "load_settings", lambda: store["values"])
    monkeypatch.setattr(chat_controller, "save_settings", lambda values: store.update(values=values))
    monkeypatch.setattr(chat_controller, "read_key", lambda authcfg: "secret" if authcfg == "key1" else "")
    made = SimpleNamespace(_reset_view=MagicMock(), _restart_engine=MagicMock(), _sync_mcp=MagicMock(),
                           _refresh_ready=MagicMock(), _say=MagicMock(), _pending_options=[], store=store)
    made.apply_agent_options = lambda change: Controller.apply_agent_options(made, change)
    made._menu_providers = lambda values: Controller._menu_providers(made, values)
    return made


def test_a_click_applies_at_once(host):
    assert Controller.apply_agent_options(host, Change(sources_on=("osm_tiles",))) == ""
    assert host.store["values"].enabled_sources == ("datagouv", "osm_tiles")
    host._restart_engine.assert_called_once()
    host._reset_view.assert_not_called()


def test_another_provider_resets_the_view(host):
    qwen = ProviderEntry("ollama", "qwen3:8b", "http://localhost:11434")
    assert Controller.apply_agent_options(host, Change(provider=qwen)) == ""
    values = host.store["values"]
    assert (values.preset, values.model, values.consent) == ("ollama", "qwen3:8b", True)
    host._reset_view.assert_called_once()


def test_a_provider_without_its_key_is_not_switched_to(host):
    gone = ProviderEntry("openai", "gpt-x", "https://api.openai.com/v1", authcfg="removed")
    reason = Controller.apply_agent_options(host, Change(provider=gone))
    assert reason and host.store["values"].preset == "anthropic"  # the text goes through _tr (mocked here)
    host._reset_view.assert_not_called()


def test_the_mcp_server_follows(host):
    Controller.apply_agent_options(host, Change(mcp_server=True))
    assert host.store["values"].mcp_enabled is True
    host._sync_mcp.assert_called_once()
    host._restart_engine.assert_not_called()


def test_a_pending_change_applies_over_the_current_settings(host):
    host._pending_options.append(Change(sources_off=("datagouv",)))
    host.store["values"] = agent_settings.AgentSettings(  # the user ticked another meanwhile, from the menu
        preset="anthropic", model="m", consent=True, authcfg="key1", enabled_sources=("datagouv", "ign_wfs"))
    Controller._apply_pending_options(host)
    assert host.store["values"].enabled_sources == ("ign_wfs",) and host._pending_options == []


def test_nothing_applies_during_the_request(host):
    host._pending_options.append(Change(sources_on=("osm_tiles",)))
    assert host.store["values"].enabled_sources == ("datagouv",)  # queued only


def test_a_click_during_a_request_waits_for_its_end(host):
    host._engine = SimpleNamespace(busy=True)
    Controller._click_option(host, Change(sources_on=("osm_tiles",)))
    assert host._pending_options == [Change(sources_on=("osm_tiles",))]
    assert host.store["values"].enabled_sources == ("datagouv",)
    host._engine = None
    Controller._click_option(host, Change(sources_on=("osm_tiles",)))
    assert host.store["values"].enabled_sources == ("datagouv", "osm_tiles")


def test_the_menu_is_filled_from_the_settings(host, monkeypatch):
    from core.agent.sources import BUILT_IN
    monkeypatch.setattr(chat_controller, "read_providers", lambda: (ProviderEntry("ollama", "qwen3:8b", "u"),))
    monkeypatch.setattr(chat_controller, "qgis_databases", lambda: [])
    host.panel = SimpleNamespace(fill_options=MagicMock())
    Controller._fill_options(host)
    groups, providers, mcp_on = host.panel.fill_options.call_args.args
    ticked = [source_id for _title, rows in groups for source_id, _name, on in rows if on]
    assert ticked == ["datagouv"] and len([row for _t, rows in groups for row in rows]) == len(BUILT_IN)
    assert providers == [("anthropic · m", True), ("ollama · qwen3:8b", False)] and mcp_on is False
