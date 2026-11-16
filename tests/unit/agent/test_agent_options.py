# -*- coding: utf-8 -*-
"""The options of the agent the user or the agent turns on or off: sources, MCP server, provider set up."""
import pytest

from core.agent.agent_options import (
    Change, ProviderEntry, apply_change, options_view, plan_off, plan_on, remember)
from core.agent.open_data import (
    KIND_DATABASE, KIND_DATAGOUV, KIND_ELEVATION, KIND_GEOCODER, KIND_POPULATION, KIND_STAC, KIND_WFS, KIND_XYZ)
from core.agent.sources import KIND_MCP, Source, source_group

pytestmark = pytest.mark.unit

SOURCES = [Source("datagouv", "data.gouv.fr", KIND_DATAGOUV, "x"), Source("osm_tiles", "OSM", KIND_XYZ, "x"),
           Source("mcp_osm", "OSM (MCP)", KIND_MCP, "x"), Source("nominatim", "Nominatim", KIND_GEOCODER, "x")]
CLAUDE = ProviderEntry("anthropic", "claude-haiku-5-5", "https://api.anthropic.com")
QWEN = ProviderEntry("ollama", "qwen3:8b", "http://localhost:11434")


@pytest.mark.parametrize("kind, group", [
    (KIND_DATAGOUV, "open_data"), (KIND_WFS, "open_data"), (KIND_STAC, "imagery"), (KIND_ELEVATION, "imagery"),
    (KIND_POPULATION, "imagery"), (KIND_XYZ, "basemaps"), (KIND_GEOCODER, "places"), (KIND_DATABASE, "databases"),
    (KIND_MCP, "connectors")])
def test_groups_follow_the_sources_tab(kind, group):
    assert source_group(Source("s", "S", kind, "x")) == group


def test_remember_puts_the_latest_first_and_keeps_eight():
    entries = tuple(ProviderEntry("openai", f"m{i}", "u") for i in range(8))
    kept = remember(entries, entries[3])
    assert kept[0] == entries[3] and len(kept) == 8 and kept.count(entries[3]) == 1
    assert remember(entries, CLAUDE)[0] == CLAUDE and len(remember(entries, CLAUDE)) == 8
    assert CLAUDE.label == "anthropic · claude-haiku-5-5"


def test_options_view():
    view = options_view(SOURCES, ("datagouv",), (CLAUDE, QWEN), CLAUDE, False)
    assert view["provider"] == CLAUDE.label and view["providers"] == [CLAUDE.label, QWEN.label]
    assert view["sources"][0] == {"id": "datagouv", "title": "data.gouv.fr", "group": "open_data", "on": True}
    assert view["mcp_server"] is False


def test_off_lists_what_was_on():
    change, answer = plan_off(SOURCES, ("datagouv", "osm_tiles"), ["datagouv", "mcp_osm"], None)
    assert change.sources_off == ("datagouv",) and answer == {"turned_off": ["datagouv"], "already": ["mcp_osm"]}


def test_already_on_is_not_asked():
    change, answer = plan_on(SOURCES, ("datagouv",), ["datagouv", "mcp_osm"], None, "", (CLAUDE,), CLAUDE)
    assert change.sources_on == ("mcp_osm",) and answer["already"] == ["datagouv"]
    nothing, _ = plan_on(SOURCES, ("datagouv",), ["datagouv"], None, "", (CLAUDE,), CLAUDE)
    assert nothing == Change()


def test_unknown_source_is_refused():
    with pytest.raises(ValueError, match="gone"):
        plan_off(SOURCES, (), ["gone"], None)
    with pytest.raises(ValueError, match="gone"):
        plan_on(SOURCES, (), ["gone"], None, "", (CLAUDE,), CLAUDE)


def test_only_a_configured_provider():
    with pytest.raises(ValueError, match="openai · gpt-x"):
        plan_on(SOURCES, (), [], None, "openai · gpt-x", (CLAUDE, QWEN), CLAUDE)
    change, answer = plan_on(SOURCES, (), [], None, QWEN.label, (CLAUDE, QWEN), CLAUDE)
    assert change.provider == QWEN and answer["provider"] == QWEN.label


def test_the_mcp_server_way_is_checked():
    with pytest.raises(ValueError):
        plan_off(SOURCES, (), [], True)
    change, _ = plan_on(SOURCES, (), [], True, "", (CLAUDE,), CLAUDE)
    assert change.mcp_server is True


def test_apply_change_keeps_the_order():
    assert apply_change(("a", "b", "c"), Change(sources_on=("d", "a"), sources_off=("b",))) == ("a", "c", "d")


# --- the tools of the chat ------------------------------------------------------------------------------------------

NAMES = ("agent_options", "turn_off_agent_options", "turn_on_agent_options")


def test_the_tools_are_in_the_chat_with_a_summary_and_come_with_configuration():
    from core.agent import skills
    from core.agent.families import bringing
    from core.agent.tool_catalog import chat_tools
    tools = {tool.name: tool for tool in chat_tools()}
    assert all(name in tools and tools[name].summary for name in NAMES)
    held = bringing(chat_tools(), skills.SKILLS.values())
    assert all("configuration" in held.get(name, []) for name in NAMES)


@pytest.mark.parametrize("level", ["advisor", "standard", "autonomous"])
def test_turning_on_is_asked_at_every_level_turning_off_is_not(level):
    from core.agent.permissions import ASK, READ, LOCAL, PROJECT, PermissionPolicy, risk_of
    from core.agent.tool_catalog import chat_tools
    tools = {tool.name: tool for tool in chat_tools()}
    assert (risk_of(tools["agent_options"]), risk_of(tools["turn_off_agent_options"]),
            risk_of(tools["turn_on_agent_options"])) == (READ, PROJECT, LOCAL)
    policy = PermissionPolicy(level)
    assert policy.verdict(tools["turn_on_agent_options"], {"sources": ["datagouv"]}) == ASK
    if level != "advisor":
        assert policy.verdict(tools["turn_off_agent_options"], {"sources": ["datagouv"]}) != ASK


# --- 2026-11-16, review of #505: a key never goes to another provider, a withdrawn consent never comes back ---------

def test_a_key_shared_with_another_provider_is_refused():
    """The dialog kept one place for a key: a provider remembered before another key replaced it there."""
    from core.agent.agent_options import switch_problem
    anthropic = ProviderEntry("anthropic", "claude", "https://api.anthropic.com", "X", "https://api.anthropic.com",
                              "https://api.anthropic.com")
    openai = ProviderEntry("openai", "gpt", "https://api.openai.com/v1", "X", "https://api.openai.com/v1",
                           "https://api.openai.com/v1")
    assert switch_problem(anthropic, (openai, anthropic), "https://api.anthropic.com", needs_key=True) == "shared_key"
    alone = ProviderEntry("anthropic", "claude", "https://api.anthropic.com", "Y", "https://api.anthropic.com",
                          "https://api.anthropic.com")
    assert switch_problem(alone, (openai, alone), "https://api.anthropic.com", needs_key=True) == ""


def test_a_consent_or_a_key_for_another_address_is_refused():
    from core.agent.agent_options import switch_problem
    moved = ProviderEntry("openai", "gpt", "https://other.example/v1", "Z", "https://api.openai.com/v1",
                          "https://api.openai.com/v1")
    assert switch_problem(moved, (moved,), "https://other.example/v1", needs_key=True) == "consent"
    keyless = ProviderEntry("openai", "gpt", "https://api.openai.com/v1", "Z", "https://api.openai.com/v1", "")
    assert switch_problem(keyless, (keyless,), "https://api.openai.com/v1", needs_key=True) == "key"
    local = ProviderEntry("ollama", "qwen3:8b", "http://localhost:11434", "", "http://localhost:11434", "")
    assert switch_problem(local, (local,), "http://localhost:11434", needs_key=False) == ""


def test_two_providers_of_one_model_have_different_labels():
    here = ProviderEntry("ollama", "qwen3:8b", "")
    there = ProviderEntry("ollama", "qwen3:8b", "http://gpu.example:11434")
    assert here.label != there.label and "gpu.example" in there.label


def test_allowed_always_still_asks_to_turn_on():
    """Turning on widens what the agent reaches: asked at every level, whatever the Tools tab says."""
    from core.agent.permissions import ASK, PermissionPolicy
    from core.agent.tool_catalog import chat_tools
    turn_on = next(tool for tool in chat_tools() if tool.name == "turn_on_agent_options")
    policy = PermissionPolicy("autonomous")
    policy.rules = {"turn_on_agent_options": "allow"}
    assert policy.verdict(turn_on, {"mcp_server": True}) == ASK
