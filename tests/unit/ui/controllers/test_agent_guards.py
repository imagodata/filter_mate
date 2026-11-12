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
                importlib.import_module(f"{_PKG}.ui.controllers.agent_chat_controller"))
    finally:
        for name in stubs:
            sys.modules.pop(name, None)


protected_layers, chat_controller = _load()


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
