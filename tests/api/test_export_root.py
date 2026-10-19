# -*- coding: utf-8 -*-
"""Audit 2026-10 (FilterMate 5) — the REST export root is private to the user.

The default root was ``/tmp/filtermate_exports_<user>``: a predictable name in
a shared folder, which another account could create first (or as a link to
``/etc``) to read or redirect the exports. It now lives in the user's own
folders, is created 0700, and a root that is a link, a file or someone
else's folder is refused. The API also reads the config.json the plugin uses.
"""
from __future__ import annotations

import os
import sys
import tempfile
import types
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from filtermate_api import config as config_module  # noqa: E402
from filtermate_api.accessor import InMemoryAccessor, LayerSummary  # noqa: E402
from filtermate_api.config import APIConfig  # noqa: E402
from filtermate_api.server import create_app  # noqa: E402

posix_only = pytest.mark.skipif(os.name == "nt", reason="POSIX modes, links and owners")


@pytest.fixture
def plugin_env(monkeypatch):
    """The FilterMate plugin loaded in this process, with its ENV_VARS."""
    def _install(**env_vars):
        # Discovery requires the loaded plugin API, not only its config module.
        monkeypatch.setitem(sys.modules, "filter_mate.filtermate_api", types.ModuleType("filter_mate.filtermate_api"))
        module = types.SimpleNamespace(ENV_VARS=dict(env_vars))
        # This fixture models an actually loaded plugin independently of the
        # checkout folder name and of collection order in other test files.
        monkeypatch.setitem(sys.modules, 'filter_mate.filtermate_api', types.ModuleType('filter_mate.filtermate_api'))
        monkeypatch.setitem(sys.modules, "filter_mate.config.config", module)
    monkeypatch.delitem(sys.modules, "filter_mate.config.config", raising=False)
    return _install


class TestDefaultRoot:
    def test_never_in_the_shared_temp_folder(self, plugin_env):
        root = APIConfig().export_root
        assert Path(tempfile.gettempdir()) not in root.parents
        assert root == Path.home() / ".filtermate" / "exports"

    def test_in_the_qgis_profile_when_the_plugin_runs(self, plugin_env, tmp_path):
        # Review 2026-10: the profile folder, not the plugin data folder (it can be a team share).
        plugin_env(QGIS_SETTINGS_PATH=str(tmp_path / "profile"),
                   PLUGIN_CONFIG_DIRECTORY=str(tmp_path / "team_share" / "FilterMate"))
        assert APIConfig().export_root == tmp_path / "profile" / "FilterMate" / "exports"

    def test_configured_root_still_wins(self, plugin_env, tmp_path, monkeypatch):
        plugin_env(PLUGIN_CONFIG_DIRECTORY=str(tmp_path / "profile"))
        monkeypatch.setenv("FILTERMATE_API_EXPORT_ROOT", str(tmp_path / "mine"))
        assert APIConfig.load().export_root == tmp_path / "mine"


class TestConfigJsonOfThePlugin:
    def test_reads_the_profile_config_json(self, plugin_env, tmp_path):
        path = tmp_path / "config.json"
        path.write_text('{"API": {"port": 8123, "cors_origins": ["https://app.example"]}}', encoding="utf-8")
        plugin_env(CONFIG_JSON_PATH=str(path))
        config = APIConfig.from_json()
        assert config.port == 8123 and config.cors_origins == ["https://app.example"]

    def test_old_place_read_while_the_profile_has_no_api_section(self, plugin_env, monkeypatch, tmp_path, caplog):
        # Review 2026-10: an API key configured in 4.x must not silently vanish.
        import logging
        monkeypatch.setattr(config_module, "_PROJECT_ROOT", tmp_path / "plugin")
        (tmp_path / "plugin" / "config").mkdir(parents=True)
        legacy = tmp_path / "plugin" / "config" / "config.json"
        legacy.write_text('{"API": {"api_key_sha256": "%s"}}' % ("ab" * 32), encoding="utf-8")
        profile = tmp_path / "profile.json"
        profile.write_text('{"APP": {}}', encoding="utf-8")
        plugin_env(CONFIG_JSON_PATH=str(profile))
        with caplog.at_level(logging.WARNING, logger="filtermate_api"):
            config = APIConfig.from_json()
        assert config.api_key_hash == "ab" * 32
        assert "old place" in caplog.text and str(profile) in caplog.text

    def test_profile_api_section_wins(self, plugin_env, monkeypatch, tmp_path):
        monkeypatch.setattr(config_module, "_PROJECT_ROOT", tmp_path / "plugin")
        (tmp_path / "plugin" / "config").mkdir(parents=True)
        (tmp_path / "plugin" / "config" / "config.json").write_text('{"API": {"port": 1}}', encoding="utf-8")
        profile = tmp_path / "profile.json"
        profile.write_text('{"API": {"port": 2}}', encoding="utf-8")
        plugin_env(CONFIG_JSON_PATH=str(profile))
        assert APIConfig.from_json().port == 2

    def test_standalone_reads_the_project_config(self, plugin_env, monkeypatch, tmp_path):
        monkeypatch.setattr(config_module, "_PROJECT_ROOT", tmp_path)
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "config.json").write_text('{"API": {"port": 8999}}', encoding="utf-8")
        assert APIConfig.from_json().port == 8999


class TestPrepareRoot:
    @staticmethod
    def _prepare(root):
        from filtermate_api.routers.export import prepare_export_root
        return prepare_export_root(root)

    @posix_only
    def test_created_private(self, tmp_path):
        root = self._prepare(tmp_path / "a" / "exports")
        assert root.is_dir()
        assert (root.stat().st_mode & 0o777) == 0o700

    @posix_only
    def test_link_is_refused(self, tmp_path):
        from filtermate_api.routers.export import ExportRootError
        target = tmp_path / "elsewhere"
        target.mkdir()
        (tmp_path / "exports").symlink_to(target)
        with pytest.raises(ExportRootError, match="not a real folder"):
            self._prepare(tmp_path / "exports")

    @posix_only
    def test_dangling_link_is_refused(self, tmp_path):
        from filtermate_api.routers.export import ExportRootError
        (tmp_path / "exports").symlink_to(tmp_path / "missing")
        with pytest.raises(ExportRootError):
            self._prepare(tmp_path / "exports")

    def test_file_is_refused(self, tmp_path):
        from filtermate_api.routers.export import ExportRootError
        (tmp_path / "exports").write_text("x")
        with pytest.raises(ExportRootError):
            self._prepare(tmp_path / "exports")

    @posix_only
    def test_existing_root_readable_by_others_made_private(self, tmp_path):
        root = tmp_path / "exports"
        root.mkdir(mode=0o755)
        os.chmod(root, 0o755)
        self._prepare(root)
        assert (root.stat().st_mode & 0o777) == 0o700

    def test_windows_junction_is_refused(self, tmp_path, monkeypatch):
        from filtermate_api.routers import export as export_module
        from filtermate_api.routers.export import ExportRootError
        (tmp_path / "exports").mkdir()
        real_lstat = os.lstat

        def junction_lstat(path, *args, **kwargs):
            info = real_lstat(path, *args, **kwargs)
            return types.SimpleNamespace(st_mode=info.st_mode, st_uid=info.st_uid, st_file_attributes=0x400)

        monkeypatch.setattr(export_module.os, "lstat", junction_lstat)
        with pytest.raises(ExportRootError, match="not a real folder"):
            self._prepare(tmp_path / "exports")

    @posix_only
    def test_folder_of_another_user_is_refused(self, tmp_path, monkeypatch):
        from filtermate_api.routers.export import ExportRootError
        (tmp_path / "exports").mkdir()
        monkeypatch.setattr(os, "getuid", lambda: os.stat(tmp_path).st_uid + 1)
        with pytest.raises(ExportRootError, match="another user"):
            self._prepare(tmp_path / "exports")


class _RecordingAccessor(InMemoryAccessor):
    def export_layers(self, *args, **kwargs):  # type: ignore[override]
        self.exported = True
        return super().export_layers(*args, **kwargs)


@posix_only
def test_route_refuses_a_linked_root(tmp_path, caplog):
    (tmp_path / "etc").mkdir()
    (tmp_path / "exports").symlink_to(tmp_path / "etc")
    accessor = _RecordingAccessor(layers=[LayerSummary(layer_id="L1", name="communes", provider_type="ogr")])
    client = TestClient(create_app(config=APIConfig(export_root=tmp_path / "exports"), accessor=accessor),
                        base_url="http://127.0.0.1:8000")
    import logging
    with caplog.at_level(logging.ERROR, logger="filtermate_api"):
        response = client.post("/export", json={"layers": ["communes"]})
    assert response.status_code == 500
    assert response.json()["detail"] == "Export root unavailable"
    assert not getattr(accessor, "exported", False)
    assert "not a real folder" in caplog.text  # the operator reads why
