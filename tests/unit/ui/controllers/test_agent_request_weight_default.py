# -*- coding: utf-8 -*-
"""The measuring bench of the token diet starts a conversation as the chat does with the default settings: the same
instructions, the same tools offered, the same tools held back for their skill. QGIS stays mocked by the root
conftest; the controller is loaded for real under a synthetic package."""
import importlib
import importlib.util
import json
import pathlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_agent_request_weight_test"


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


def test_designer_guidance_is_opt_in_and_keeps_the_normal_permissions():
    values = agent_settings.AgentSettings()
    plain = Controller._prompt(values, [])
    designer = Controller._prompt(values, [], designer=True)
    assert designer.startswith(plain)
    assert 'Advanced Designer workspace:' not in plain
    assert 'Advanced Designer workspace:' in designer
    assert 'current user permissions' in designer and 'not approval' in designer


class _Host:
    """What tools_and_handlers and _families read of the controller: a portal-less accessor, placeholders."""

    local_filtering = staticmethod(Controller.local_filtering)

    def _accessor(self):
        return SimpleNamespace(configured_domains=lambda: "")

    def __getattr__(self, name):
        return None


@pytest.fixture
def plugin_tools(monkeypatch):
    monkeypatch.setattr(chat_controller, "build_handlers", lambda *args, **kwargs: {})
    monkeypatch.setattr(chat_controller, "settings_handlers", lambda *args, **kwargs: {"load_skill": lambda arguments: {}})
    monkeypatch.setattr(chat_controller, "_default_export_root", lambda: None)
    # The bench measures QGIS 4, whose Python has QtWebEngine: the chart tools are offered there.
    renderer = importlib.import_module(f"{_PKG}.adapters.agent.chart_renderer")
    monkeypatch.setattr(renderer, "_engine", "ok")


@pytest.fixture(scope="module")
def weight():
    spec = importlib.util.spec_from_file_location("agent_request_weight", _ROOT / "scripts" / "agent_request_weight.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["agent_request_weight"] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop("agent_request_weight", None)


def test_the_bench_starts_as_the_chat_does(plugin_tools, weight):
    host = _Host()
    values = agent_settings.AgentSettings(preset="anthropic", model="m")
    tools, handlers, active = Controller.tools_and_handlers(host, values)
    offered = [tool.name for tool in tools]
    kept, _handlers, held = Controller._families(host, values, tools, handlers, active)
    prompt, start, bench_held = weight.default_setup()
    assert [tool.name for tool in start] == [tool.name for tool in kept]
    assert "use_tools" in [tool.name for tool in kept] and "list_layers" not in [tool.name for tool in kept]
    assert bench_held == held  # every tool of the index, each with the skills that bring it
    assert prompt == Controller._prompt(values, active, [], offered, host._index_tools)
    assert "Tools you can add with use_tools" in prompt and "\n- list_layers: " in prompt


def test_families_off_offers_every_tool_without_index(plugin_tools):
    host = _Host()
    values = agent_settings.AgentSettings(preset="anthropic", model="m", tool_families=False)
    tools, handlers, active = Controller.tools_and_handlers(host, values)
    kept, _handlers, held = Controller._families(host, values, tools, handlers, active)
    assert [tool.name for tool in kept] == [tool.name for tool in tools] and not held and not host._index_tools
    assert "use_tools" not in [tool.name for tool in kept]
    assert "use_tools" not in Controller._prompt(values, active, [], [tool.name for tool in tools], host._index_tools)


@pytest.mark.parametrize("for_chat", [True, False])
@pytest.mark.parametrize("rules", [{}, {"open_model": "ask"}, {"open_model": "never"}])
def test_the_model_designer_cannot_be_activated_by_agent_settings(plugin_tools, for_chat, rules):
    values = agent_settings.AgentSettings(preset="anthropic", model="m", expert_python=True, tool_rules=json.dumps(rules))
    tools, handlers, _active = Controller.tools_and_handlers(_Host(), values, for_chat=for_chat)
    offered = {tool.name for tool in tools}
    assert "open_model" not in offered and "open_model" not in handlers
    assert {"find_algorithms", "describe_algorithm", "run_algorithm"} <= offered
    skills = next(tool for tool in tools if tool.name == "load_skill").input_schema["properties"]["name"]["enum"]
    assert "processing-models" not in skills
