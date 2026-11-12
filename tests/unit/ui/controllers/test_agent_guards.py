# -*- coding: utf-8 -*-
"""What the agent checks before a call changes the project, outside the pure policy (core/agent/permissions.py).

The modules are loaded for real under a synthetic package (their relative imports reach ``core`` and ``adapters``);
QGIS stays mocked by the root conftest, with the two Qt modules it does not mock.
"""
import importlib
import pathlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from core.agent.messages import ToolCallPart
from core.agent.permissions import PROTECTION_UNREADABLE, PermissionPolicy

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_agent_guards_test"


def _load():
    for name, path in (("", _ROOT), (".ui", _ROOT / "ui"), (".ui.controllers", _ROOT / "ui" / "controllers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    stubs = [name for name in ("qgis.PyQt.QtNetwork", "qgis.PyQt.QtXml") if name not in sys.modules]
    sys.modules.update({name: MagicMock() for name in stubs})
    try:  # bound at import; taken out again so that no other test sees them
        return (importlib.import_module(f"{_PKG}.adapters.agent.protected_layers"),
                importlib.import_module(f"{_PKG}.ui.controllers.agent_chat_controller"),
                importlib.import_module(f"{_PKG}.ui.controllers.agent_mcp_bridge"))
    finally:
        for name in stubs:
            sys.modules.pop(name, None)


protected_layers, chat_controller, mcp_bridge = _load()


class TestProtectionFailsClosed:
    def test_favorites_that_cannot_be_read_are_not_taken_for_none(self, monkeypatch):
        monkeypatch.setattr(protected_layers, "read_ids", lambda project=None: ["cadastre_id"])
        offline = types.ModuleType("operations")

        def favorite_layers(_favorite_id):
            raise RuntimeError("favorites store offline")
        offline.favorite_layers = favorite_layers
        monkeypatch.setitem(sys.modules, f"{_PKG}.adapters.public_api.operations", offline)
        protection = protected_layers.ProjectProtection()
        with pytest.raises(RuntimeError):
            protection.favorite_layers("fav-1")
        policy = PermissionPolicy(protector=protection)
        assert policy.protection_refusal("apply_favorite", {"favorite_id": "fav-1"}) == PROTECTION_UNREADABLE

    def test_nothing_protected_does_not_read_the_favorites(self, monkeypatch):
        monkeypatch.setattr(protected_layers, "read_ids", lambda project=None: [])
        assert protected_layers.ProjectProtection().favorite_layers("fav-1") == []

    def test_the_controller_refuses_a_change_it_cannot_check_and_lets_a_read_run(self):
        class Broken:
            def turned_off(self, name):
                raise RuntimeError("the project is closing")

        host = SimpleNamespace(_policy=Broken())
        refusal = chat_controller.AgentChatController.protection_refusal
        assert refusal(host, ToolCallPart("c", "apply_filter", {"layer_name": "a", "expression": "1"})) \
            == PROTECTION_UNREADABLE
        assert refusal(host, ToolCallPart("c", "apply_favorite", {"favorite_id": "f"})) == PROTECTION_UNREADABLE
        assert refusal(host, ToolCallPart("c", "list_layers", {})) == ""


class _Host:
    """What the bridge asks of the chat: nothing protected, nothing turned off there, the user answers ``answer``."""

    def __init__(self, answer):
        self.answer = answer
        self.asked = []

    def chat_busy(self):
        return False

    def protection_refusal(self, call):
        return ""

    def confirm_external(self, call, client):
        self.asked.append(call.name)
        return self.answer

    def journal(self, call, result, client):
        pass


class TestMcpBridgeFollowsTheToolsTab:
    @pytest.fixture
    def bridge(self, monkeypatch):
        from core.agent.tool_catalog import chat_tools
        from core.agent.tool_executor import ToolExecutor

        def make(rules, answer=False):
            ran = []
            tools = {tool.name: tool for tool in chat_tools()}
            handlers = {name: (lambda arguments, name=name: ran.append(name) or {}) for name in tools}
            bridge = object.__new__(mcp_bridge.AgentMcpBridge)  # no server: _run alone
            bridge._host, bridge._declined, bridge.busy = _Host(answer), {}, False
            bridge._executor = ToolExecutor(tuple(tools.values()), handlers)
            bridge._server = SimpleNamespace(client_still_there=lambda: True)
            bridge._change = lambda call, client: bridge._executor.execute(call)  # no undo point here
            monkeypatch.setattr(mcp_bridge, "load_settings", lambda: SimpleNamespace(rules=dict(rules)))
            monkeypatch.setattr(mcp_bridge, "QApplication", SimpleNamespace(activeModalWidget=lambda: None))
            return bridge, tools, ran
        return make

    def test_always_ask_asks_even_for_what_the_standard_level_runs(self, bridge):
        server, tools, ran = bridge({"list_layers": "ask", "apply_filter": "ask"})
        for name, arguments in (("list_layers", {}), ("apply_filter", {"layer_name": "a", "expression": '"x" = 1'})):
            result = server._run(tools[name], arguments, "Claude")
            assert result.is_error and name in server._host.asked, name
        assert ran == []

    def test_never_refuses_without_asking(self, bridge):
        server, tools, ran = bridge({"zoom_to": "never"})
        result = server._run(tools["zoom_to"], {"layer": "a"}, "Claude")
        assert result.is_error and "turned the tool 'zoom_to' off" in result.content
        assert server._host.asked == [] and ran == []

    def test_always_allow_does_not_take_a_confirmation_away_from_another_application(self, bridge):
        server, tools, ran = bridge({"remove_layers": "allow"})
        result = server._run(tools["remove_layers"], {"layers": ["a"]}, "Claude")
        assert result.is_error and server._host.asked == ["remove_layers"] and ran == []

    def test_without_rules_the_standard_level_stays(self, bridge):
        server, tools, ran = bridge({}, answer=True)
        assert not server._run(tools["list_layers"], {}, "Claude").is_error
        assert not server._run(tools["remove_layers"], {"layers": ["a"]}, "Claude").is_error
        assert server._host.asked == ["remove_layers"] and ran == ["list_layers", "remove_layers"]
