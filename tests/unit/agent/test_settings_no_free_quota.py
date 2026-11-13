# -*- coding: utf-8 -*-
"""The free quota is gone from the plugin: no preset, no relay address, and a profile that was on it reads as no
provider at all, so that the settings open at the first request.

The modules are loaded for real under a synthetic package (their relative imports reach ``core``, ``adapters`` and
``filtermate_api``); QGIS stays mocked by the root conftest, with the two Qt modules it does not mock.
"""
import importlib
import pathlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_PKG = "fm_no_free_quota_test"
RELAY = "https://filtermate-free-quota.filtermate-free-quota-proxy.workers.dev"


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
                importlib.import_module(f"{_PKG}.core.agent.providers"))
    finally:
        for name in stubs:
            sys.modules.pop(name, None)


chat_controller, agent_settings, providers = _load()


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


class _Host:
    """What tools_and_handlers reads of the controller: a portal-less accessor, every handler a placeholder."""

    local_filtering = staticmethod(chat_controller.AgentChatController.local_filtering)

    def _accessor(self):
        return SimpleNamespace(configured_domains=lambda: "")

    def __getattr__(self, name):
        return None


def test_presets_have_no_free_quota():
    assert "free" not in providers.PRESETS
    assert not hasattr(providers, "FREE_PRESET") and not hasattr(providers, "FREE_QUOTA_URL")
    assert not hasattr(providers, "FREE_MODEL") and not hasattr(agent_settings, "free_quota_url")


def test_free_profile_reads_as_no_provider(fake_qgs_settings):
    fake_qgs_settings.update({"filter_mate/agent/preset": "free", "filter_mate/agent/model": "claude-haiku-5-5",
                              "filter_mate/agent/consent": True, "filter_mate/agent/consent_target": RELAY})
    values = agent_settings.load_settings()
    assert values.preset == "anthropic"
    assert not values.has_consent and not values.ready


def test_the_address_of_the_relay_does_not_follow_a_free_profile_to_anthropic(fake_qgs_settings):
    """The old dialog saved the hidden relay address under "free": Test would have sent the new key there."""
    fake_qgs_settings.update({"filter_mate/agent/preset": "free", "filter_mate/agent/base_url": RELAY,
                              "filter_mate/agent/authcfg": "cfg", "filter_mate/agent/key_target": RELAY})
    values = agent_settings.load_settings()
    assert values.preset == "anthropic" and values.base_url == ""
    assert values.target == "https://api.anthropic.com" and not values.has_key


def test_the_address_of_a_known_provider_is_kept(fake_qgs_settings):
    fake_qgs_settings.update({"filter_mate/agent/preset": "openai", "filter_mate/agent/base_url": "https://relay.example.com/v1"})
    assert agent_settings.load_settings().base_url == "https://relay.example.com/v1"


def test_the_relay_token_is_removed_from_the_profile(fake_qgs_settings):
    fake_qgs_settings.update({"filter_mate/agent/free_token": "relay-token", "filter_mate/agent/free_token_target": RELAY,
                              "filter_mate/agent/preset": "ollama"})
    agent_settings.load_settings()
    assert not [key for key in fake_qgs_settings if "free_token" in key]
    assert fake_qgs_settings["filter_mate/agent/preset"] == "ollama"
    agent_settings.load_settings()  # nothing left: loading again is harmless


def test_view_map_offered_with_values(monkeypatch):
    monkeypatch.setattr(chat_controller, "enabled", lambda sources, ticked: [])
    monkeypatch.setattr(chat_controller, "build_handlers", lambda *args, **kwargs: {})
    monkeypatch.setattr(chat_controller, "settings_handlers", lambda *args, **kwargs: {})
    monkeypatch.setattr(chat_controller, "_default_export_root", lambda: None)
    values = agent_settings.AgentSettings(preset="anthropic", send_values=True)
    tools_and_handlers = chat_controller.AgentChatController.tools_and_handlers
    offered = {tool.name for tool in tools_and_handlers(_Host(), values)[0]}
    assert "view_map" in offered
    assert "view_map" not in {tool.name for tool in tools_and_handlers(
        _Host(), agent_settings.AgentSettings(preset="anthropic", send_values=False))[0]}
