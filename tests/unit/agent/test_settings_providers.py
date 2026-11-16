# -*- coding: utf-8 -*-
"""The providers the user set up, remembered so that the menu of the AGENT panel and the agent switch between them
(2026-11-16). Their keys stay in the authentication database of QGIS.

The settings module is loaded for real under a synthetic package (its relative imports reach ``core`` and
``filtermate_api``); QGIS stays mocked by the root conftest.
"""
import importlib
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_PKG = "fm_settings_providers_test"


def _load():
    for name, path in (("", _ROOT),):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.adapters.agent.settings")


agent_settings = _load()


@pytest.fixture
def fake_qgs_settings(monkeypatch):
    """QgsSettings of the settings module backed by a dict, which is yielded."""
    store = {}

    class FakeQgsSettings:
        def value(self, key, default=None, type=None):
            return store.get(key, default)

        def setValue(self, key, value):
            store[key] = value

        def contains(self, key):
            return key in store

        def remove(self, key):
            store.pop(key, None)

    monkeypatch.setattr(agent_settings, "QgsSettings", FakeQgsSettings)
    return store


def test_providers_round_trip(fake_qgs_settings):
    from core.agent.agent_options import ProviderEntry
    entries = (ProviderEntry("anthropic", "claude-haiku-5-5", "https://api.anthropic.com", "abc1234", "t", "t"),
               ProviderEntry("ollama", "qwen3:8b", "http://localhost:11434"))
    agent_settings.write_providers(entries)
    assert [entry.label for entry in agent_settings.read_providers()] == [entry.label for entry in entries]
    assert agent_settings.read_providers()[0].authcfg == "abc1234"


def test_a_bad_json_reads_as_none(fake_qgs_settings):
    fake_qgs_settings["filter_mate/agent/providers"] = "{not json"
    assert agent_settings.read_providers() == ()
    fake_qgs_settings["filter_mate/agent/providers"] = '[{"preset": "x"}]'  # a model missing
    assert agent_settings.read_providers() == ()


def test_the_current_provider_of_the_settings():
    values = agent_settings.AgentSettings(preset="ollama", model="qwen3:8b", base_url="http://localhost:11434")
    entry = agent_settings.current_provider(values)
    assert (entry.preset, entry.model, entry.base_url) == ("ollama", "qwen3:8b", "http://localhost:11434")
