# -*- coding: utf-8 -*-
"""The settings tools of the agent hardened on 2026-11-13: profiles in the export folder, the set of tools of the MCP
server.

The modules are loaded for real under a synthetic package (their relative imports reach ``core``, ``adapters`` and
``filtermate_api``); QGIS stays mocked by the root conftest, with the two Qt modules it does not mock.
"""
import importlib
import os
import pathlib
import stat
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_agent_settings_hardening_test"


def _load():
    for name, path in (("", _ROOT), (".ui", _ROOT / "ui"), (".ui.controllers", _ROOT / "ui" / "controllers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    stubs = [name for name in ("qgis.PyQt.QtNetwork", "qgis.PyQt.QtXml") if name not in sys.modules]
    sys.modules.update({name: MagicMock() for name in stubs})
    try:  # bound at import; taken out again so that no other test sees them
        return (importlib.import_module(f"{_PKG}.ui.controllers.agent_chat_controller"),
                importlib.import_module(f"{_PKG}.ui.controllers.agent_mcp_bridge"),
                importlib.import_module(f"{_PKG}.adapters.agent.plugin_settings"),
                importlib.import_module(f"{_PKG}.filtermate_api.export_root"))
    finally:
        for name in stubs:
            sys.modules.pop(name, None)


chat_controller, mcp_bridge, plugin_settings, export_root = _load()
ToolFailure = plugin_settings.ToolFailure
needs_links = pytest.mark.skipif(os.name != "posix", reason="links and O_NOFOLLOW as on Linux and macOS")


@pytest.fixture
def profiles(tmp_path, monkeypatch):
    """profiles/ of an export folder in tmp_path, and the settings as config.default.json writes them."""
    folder = tmp_path / "profiles"
    monkeypatch.setattr(plugin_settings, "_profiles_folder", lambda: folder)
    rows = plugin_settings.read_settings(None, plugin_settings.load_default())
    monkeypatch.setattr(plugin_settings, "settings_rows", lambda config=None: rows)
    return folder


def _no_export_folder():
    raise export_root.ExportRootError("the export folder is a link: FilterMate does not write there")


class TestProfiles:
    def test_export_writes_a_file_of_the_user_alone_and_asks_before_replacing(self, profiles):
        answer = plugin_settings._export_profile({"name": "team"})
        target = profiles / "team.json"
        assert answer["file"] == "profiles/team.json" and target.is_file()
        if os.name == "posix":
            assert stat.S_IMODE(target.stat().st_mode) == 0o600
        with pytest.raises(ToolFailure, match="exists already"):
            plugin_settings._export_profile({"name": "team"})
        assert plugin_settings._export_profile({"name": "team", "replace": True})["name"] == "team"

    @needs_links
    def test_export_never_follows_a_link_even_a_dangling_one(self, profiles, tmp_path):
        """2026-11-13: exists() is False for a dangling link, and the profile was written wherever it pointed."""
        profiles.mkdir()
        elsewhere = tmp_path / "elsewhere.json"
        (profiles / "team.json").symlink_to(elsewhere)
        for replace in (False, True):
            with pytest.raises(ToolFailure, match="is a link"):
                plugin_settings._export_profile({"name": "team", "replace": replace})
        assert not elsewhere.exists()

    @needs_links
    def test_a_link_put_there_after_the_check_is_refused_too(self, profiles, tmp_path, monkeypatch):
        profiles.mkdir()
        elsewhere = tmp_path / "elsewhere.json"
        (profiles / "team.json").symlink_to(elsewhere)
        real_lstat = type(profiles).lstat

        def before_the_link(self):  # the check ran before the link was put there
            if self.name == "team.json":
                raise FileNotFoundError(self)
            return real_lstat(self)
        monkeypatch.setattr(type(profiles), "lstat", before_the_link)
        with pytest.raises(ToolFailure, match="could not be written"):
            plugin_settings._export_profile({"name": "team", "replace": True})
        assert not elsewhere.exists()

    @needs_links
    def test_a_profile_replaced_is_the_users_alone_too(self, profiles):
        profiles.mkdir()
        (profiles / "team.json").write_text("{}", encoding="utf-8")
        (profiles / "team.json").chmod(0o644)  # written by 5.1, readable by others
        plugin_settings._export_profile({"name": "team", "replace": True})
        assert stat.S_IMODE((profiles / "team.json").stat().st_mode) == 0o600

    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="named pipes as on Linux and macOS")
    def test_a_pipe_named_as_the_profile_is_neither_written_nor_read(self, profiles):
        """Opening a pipe to write waits for a reader: QGIS held until someone reads it."""
        profiles.mkdir()
        os.mkfifo(profiles / "team.json")
        with pytest.raises(ToolFailure, match="not a file"):
            plugin_settings._export_profile({"name": "team", "replace": True})
        with pytest.raises(ValueError, match="no profile"):
            plugin_settings.planned_profile({"name": "team"})

    def test_an_export_folder_that_cannot_be_used_is_said_as_it_is(self, profiles, monkeypatch):
        monkeypatch.setattr(plugin_settings, "_profiles_folder", _no_export_folder)
        with pytest.raises(ToolFailure, match="export folder is a link"):
            plugin_settings._export_profile({"name": "team"})
        with pytest.raises(ValueError, match="export folder is a link"):
            plugin_settings.planned_profile({"name": "team"})
        with pytest.raises(ToolFailure, match="export folder is a link"):
            plugin_settings._apply_profile({"name": "team"})

    def test_a_profile_saved_with_a_byte_order_mark_is_read(self, profiles):
        """Notepad saves UTF-8 with a mark at the start."""
        import json
        profiles.mkdir()
        text = json.dumps({"format": "filtermate-settings-profile", "version": 1, "name": "Team",
                           "settings": {"APP.OPTIONS.SERVER_FILTER.wfs_timeout_seconds": 120}})
        (profiles / "team.json").write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
        rows, left_out, name = plugin_settings.planned_profile({"name": "team"})
        assert name == "Team" and left_out == []
        assert [(row["path"], row["before"], row["after"]) for row in rows] == [
            ("APP.OPTIONS.SERVER_FILTER.wfs_timeout_seconds", 60, 120)]


class _Host:
    """What tools_and_handlers reads of the controller: a portal-less accessor, every handler a placeholder."""

    local_filtering = staticmethod(chat_controller.AgentChatController.local_filtering)

    def _accessor(self):
        return SimpleNamespace(configured_domains=lambda: "")

    def __getattr__(self, name):
        return None


class TestTheMcpServerTakesEveryTool:
    def test_the_lighter_set_of_a_local_model_is_for_the_chat_alone(self, monkeypatch):
        monkeypatch.setattr(chat_controller, "enabled", lambda sources, ticked: [])
        monkeypatch.setattr(chat_controller, "build_handlers", lambda *args, **kwargs: {})
        monkeypatch.setattr(chat_controller, "settings_handlers", lambda *args, **kwargs: {})
        monkeypatch.setattr(chat_controller, "_default_export_root", lambda: None)
        values = SimpleNamespace(custom_sources="[]", enabled_sources="", rules={}, send_values=True,
                                 expert_python=False, preset="ollama", local_filtering_only=True)
        tools_and_handlers = chat_controller.AgentChatController.tools_and_handlers
        chat = {tool.name for tool in tools_and_handlers(_Host(), values)[0]}
        other = {tool.name for tool in tools_and_handlers(_Host(), values, for_chat=False)[0]}
        assert chat < other and "change_settings" in other and "change_settings" not in chat
        values.local_filtering_only = False
        assert {tool.name for tool in tools_and_handlers(_Host(), values)[0]} == other

    def test_the_server_asks_the_tools_for_another_application(self, monkeypatch):
        """2026-11-13: "only the tools that filter", a choice for a small model in the chat, took the settings,
        the skills, the styles and Processing away from every application of the MCP server."""
        asked = []
        bridge = object.__new__(mcp_bridge.AgentMcpBridge)  # no server: sync alone
        bridge._host = SimpleNamespace(
            tools_and_handlers=lambda values, for_chat=True: asked.append(for_chat) or ([], {}, []))
        bridge._server = SimpleNamespace(serves=lambda port, token: True, close=lambda: None)
        monkeypatch.setattr(mcp_bridge, "load_settings",
                            lambda: SimpleNamespace(mcp_enabled=True, mcp_port=1, mcp_token="t"))
        monkeypatch.setattr(mcp_bridge, "image_handlers", lambda: {})
        bridge.sync()
        assert asked == [False] and bridge.error == ""
