# -*- coding: utf-8 -*-
"""The Sources tab enforced on the REST API (audit of 2026-11-24, decided with the user).

The chat does not offer the tools of the sources the user did not tick; the REST API (and through it the MCP
server) reached Overpass, Copernicus and Meta anyway. Pure gate, no QGIS.
"""
import sys
import types
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit

from filtermate_api.source_gate import open_data_refusal, refused_for


@pytest.mark.parametrize("kinds", [{"overpass"}, {"overpass", "elevation"}])
def test_ticked_kind_allowed(kinds):
    assert refused_for(kinds, "overpass", "Overpass") is None


@pytest.mark.parametrize("kinds", [set(), {"elevation"}, {"xyz"}])
def test_unticked_kind_refused_with_the_tab(kinds):
    refused = refused_for(kinds, "overpass", "Overpass")
    assert refused is not None and "Sources tab" in refused


def _fake_settings(monkeypatch, configured, ticked=()):
    """Stand-ins for adapters.agent.settings and core.agent.sources (2026-11-26)."""
    settings = types.ModuleType("adapters.agent.settings")
    settings.sources_configured = lambda: configured
    settings.load_settings = lambda: SimpleNamespace(custom_sources="[]", enabled_sources=tuple(ticked))
    sources = types.ModuleType("core.agent.sources")
    catalog = [SimpleNamespace(kind="overpass"), SimpleNamespace(kind="elevation")]
    sources.custom_from_json = lambda text: []
    sources.all_sources = lambda custom: list(catalog)
    sources.enabled = lambda all_sources, ticked_names: [source for source in all_sources
                                                         if source.kind in set(ticked_names)]
    monkeypatch.setitem(sys.modules, "adapters.agent.settings", settings)
    monkeypatch.setitem(sys.modules, "core.agent.sources", sources)


def test_never_configured_sources_stay_reachable(monkeypatch):
    """No 403 until the user saves the Sources tab: existing REST/MCP setups keep working until they opt in."""
    _fake_settings(monkeypatch, configured=False)
    assert open_data_refusal("overpass", "Overpass") is None


def test_configured_but_unticked_source_is_refused(monkeypatch):
    _fake_settings(monkeypatch, configured=True, ticked=("elevation",))
    refused = open_data_refusal("overpass", "Overpass")
    assert refused is not None and "Sources tab" in refused


def test_configured_and_ticked_source_is_allowed(monkeypatch):
    _fake_settings(monkeypatch, configured=True, ticked=("overpass", "elevation"))
    assert open_data_refusal("overpass", "Overpass") is None


def test_unreadable_settings_do_not_brick_the_api(monkeypatch):
    settings = types.ModuleType("adapters.agent.settings")
    settings.sources_configured = lambda: True

    def _boom():
        raise RuntimeError("gone")

    settings.load_settings = _boom
    sources = types.ModuleType("core.agent.sources")
    sources.custom_from_json = lambda text: []
    sources.all_sources = lambda custom: []
    sources.enabled = lambda all_sources, ticked: []
    monkeypatch.setitem(sys.modules, "adapters.agent.settings", settings)
    monkeypatch.setitem(sys.modules, "core.agent.sources", sources)
    assert open_data_refusal("overpass", "Overpass") is None
