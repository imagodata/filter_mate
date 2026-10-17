# -*- coding: utf-8 -*-
"""Extension registry — review 2026-10 (FilterMate 5).

* Secrets a past release left in an extension's config (the 4.x plaintext
  ``auth_header`` of favorites sharing) are purged when the configs load,
  whatever the state of the extension, without failing the start-up.
* config.json is written atomically: a failed write never truncates it.
"""
import json
import sys
import types

import pytest

from extensions.registry import ExtensionRegistry


class _Extension:
    def __init__(self, ext_id, purge):
        self.metadata = types.SimpleNamespace(id=ext_id, name=ext_id, version="1")
        self._purge = purge

    def seed_default_config(self):
        return False

    def purge_legacy_config(self):
        return self._purge()


@pytest.fixture
def registry(monkeypatch):
    registry = ExtensionRegistry()
    persisted = []
    monkeypatch.setattr(registry, "_persist_config", lambda: persisted.append(True) or True)
    monkeypatch.setattr(registry, "_log_discovery_summary", lambda discovered: None)
    registry.persisted = persisted
    return registry


def _discover_with(registry, monkeypatch, purge):
    monkeypatch.setattr(registry, "_load_extension_module", lambda entry: _Extension(entry, purge))
    return registry.discover_extensions()


class TestPurgeAtLoad:
    def test_purge_found_something_config_written(self, registry, monkeypatch):
        discovered = _discover_with(registry, monkeypatch, lambda: True)
        assert discovered and registry.persisted == [True]

    def test_nothing_to_purge_nothing_written(self, registry, monkeypatch):
        _discover_with(registry, monkeypatch, lambda: False)
        assert registry.persisted == []

    def test_failing_purge_does_not_stop_the_start(self, registry, monkeypatch, caplog):
        def broken():
            raise ValueError("config slice is not a dict")
        discovered = _discover_with(registry, monkeypatch, broken)
        assert discovered  # every extension still discovered
        assert "Legacy config purge failed" in caplog.text

    def test_real_favorites_sharing_hook_runs_without_dependencies(self, monkeypatch):
        # Resource Sharing is absent here (MISSING_DEPS): the hook is on the extension object all the same.
        from extensions.favorites_sharing.extension import FavoritesSharingExtension
        ext = FavoritesSharingExtension()  # never initialized: its dependencies are not checked
        writes = []
        monkeypatch.setattr(ext, "get_config", lambda key, default=None: [{"name": "A", "auth_header": "x"}])
        monkeypatch.setattr(ext, "set_config", lambda key, value, persist=True: writes.append(persist) or True)
        assert ext.purge_legacy_config() is True and writes == [False]


@pytest.fixture
def env_vars(tmp_path, monkeypatch):
    """``filter_mate.config.config.ENV_VARS`` on a tmp config.json."""
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"APP": {"keep": 1}, "EXTENSIONS": {}}), encoding="utf-8")
    data = {"APP": {"keep": 1}, "EXTENSIONS": {"favorites_sharing": {"remote_repos": {"value": []}}}}
    module = types.ModuleType("filter_mate.config.config")
    module.ENV_VARS = {"CONFIG_JSON_PATH": str(path), "CONFIG_DATA": data}
    package = types.ModuleType("filter_mate.config")
    package.__path__ = []
    package.config = module
    if "filter_mate" not in sys.modules or not hasattr(sys.modules["filter_mate"], "__path__"):
        root = types.ModuleType("filter_mate")
        root.__path__ = []
        monkeypatch.setitem(sys.modules, "filter_mate", root)
    monkeypatch.setitem(sys.modules, "filter_mate.config", package)
    monkeypatch.setitem(sys.modules, "filter_mate.config.config", module)
    from tests.unit.extensions.plugin_alias import alias_package
    alias_package(monkeypatch, "extensions.registry", "extensions.base")
    return path


class TestAtomicWrite:
    def test_written_and_no_temporary_left(self, env_vars):
        assert ExtensionRegistry()._persist_config() is True
        assert json.loads(env_vars.read_text())["EXTENSIONS"]["favorites_sharing"] == {"remote_repos": {"value": []}}
        assert not (env_vars.parent / "config.json.tmp").exists()

    def test_failed_write_keeps_the_previous_file(self, env_vars, monkeypatch):
        before = env_vars.read_text()

        def broken_dump(*args, **kwargs):  # the writer serialises with json.dumps before touching the file
            raise TypeError("Object of type MagicMock is not JSON serializable")

        monkeypatch.setattr(json, "dumps", broken_dump)
        assert ExtensionRegistry()._persist_config() is False
        assert env_vars.read_text() == before
        assert not (env_vars.parent / "config.json.tmp").exists()
