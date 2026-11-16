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
