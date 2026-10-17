# -*- coding: utf-8 -*-
"""
Extensions persist config.json atomically and never serialise what is not JSON.

``BaseExtension._persist_config`` opened config.json with ``open(path, "w")``
(truncated first) and ``json.dump`` of the live CONFIG_DATA, which can hold a
psycopg2 connection or any runtime object: a TypeError (not caught there) after
the file had been truncated. ``ExtensionRegistry._persist_config`` wrote a
neighbour ``config.json.tmp`` of its own. Both go through ``write_config_json``.
"""
import json
import os
import sys
import types
from unittest.mock import MagicMock

import pytest

from extensions import config_io
from extensions.base import BaseExtension, ExtensionMetadata, ExtensionState
from extensions.registry import ExtensionRegistry

pytestmark = pytest.mark.unit


class _Connection:
    def cursor(self):
        return object()


class _Anything:
    pass


class TestJsonSafe:
    def test_json_values_are_kept(self):
        data = {"a": 1, "b": [1, "x", None, True, 1.5], "c": {"d": "é"}}
        assert config_io.json_safe(data) == data

    def test_connections_and_unknown_objects_become_none(self):
        data = {"conn": _Connection(), "obj": _Anything(), "nested": {"conn": _Connection()}, "list": [_Anything(), 1],
                "set": {1, 2}}
        safe = config_io.json_safe(data)
        assert safe["conn"] is None and safe["obj"] is None and safe["nested"] == {"conn": None}
        assert safe["list"] == [None, 1]
        json.dumps(safe)

    def test_the_input_is_not_modified(self):
        connection = _Connection()
        data = {"conn": connection}
        config_io.json_safe(data)
        assert data["conn"] is connection

    def test_cycles_do_not_loop_forever(self):
        data = {}
        data["self"] = data
        json.dumps(config_io.json_safe(data))


class TestWriteConfigJson:
    def test_writes_utf8_atomically_without_temp_file(self, tmp_path):
        target = tmp_path / "config.json"

        assert config_io.write_config_json(str(target), {"nom": "Rhône"}) is True

        assert json.loads(target.read_bytes().decode("utf-8")) == {"nom": "Rhône"}
        assert [p.name for p in tmp_path.iterdir()] == ["config.json"]

    def test_a_connection_in_the_data_is_dropped_not_fatal(self, tmp_path):
        target = tmp_path / "config.json"

        assert config_io.write_config_json(str(target), {"ACTIVE": _Connection(), "ok": 1}) is True

        assert json.loads(target.read_text(encoding="utf-8")) == {"ACTIVE": None, "ok": 1}

    def test_failure_keeps_the_previous_file_and_warns(self, tmp_path, monkeypatch, caplog):
        target = tmp_path / "config.json"
        target.write_text('{"keep": 1}', encoding="utf-8")

        def broken(src, dst):
            raise OSError("disk full")

        monkeypatch.setattr(config_io.os, "replace", broken)
        with caplog.at_level("WARNING"):
            assert config_io.write_config_json(str(target), {"new": 1}) is False

        monkeypatch.undo()
        assert json.loads(target.read_text(encoding="utf-8")) == {"keep": 1}
        assert [p.name for p in tmp_path.iterdir()] == ["config.json"]
        assert any("config.json" in r.getMessage() for r in caplog.records)

    def test_the_plugin_writer_is_used_when_it_is_importable(self, tmp_path, monkeypatch):
        calls = []
        module = types.ModuleType("filter_mate.infrastructure.utils.atomic_io")
        module.atomic_json_write = lambda path, data, **kwargs: calls.append((path, data, kwargs))
        for name in ("filter_mate", "filter_mate.infrastructure", "filter_mate.infrastructure.utils"):
            parent = types.ModuleType(name)
            parent.__path__ = []
            monkeypatch.setitem(sys.modules, name, parent)
        monkeypatch.setitem(sys.modules, module.__name__, module)
        # config_io imports the writer relatively: re-root it under the fake filter_mate package
        from tests.unit.extensions.plugin_alias import alias_package
        alias_package(monkeypatch, "extensions.config_io")

        assert config_io.write_config_json(str(tmp_path / "config.json"), {"a": 1}) is True

        assert calls and calls[0][1] == {"a": 1}


@pytest.fixture
def live_config(tmp_path, monkeypatch):
    """filter_mate.config.config.ENV_VARS on a tmp config.json whose live data holds a connection."""
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"APP": {"keep": 1}, "EXTENSIONS": {}}), encoding="utf-8")
    connection = _Connection()
    data = {"APP": {"keep": 1},
            "CURRENT_PROJECT": {"OPTIONS": {"ACTIVE_POSTGRESQL": connection}},
            "EXTENSIONS": {"sample": {"enabled": {"value": True}}}}
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
    # the extension modules import config and the atomic writer relatively: re-root them under filter_mate
    from tests.unit.extensions.plugin_alias import alias_package
    alias_package(monkeypatch, "extensions.registry", "extensions.base", "extensions.config_io")
    return path, data, connection


class _Sample(BaseExtension):
    metadata = ExtensionMetadata(id="sample", name="Sample", version="1.0", description="x")

    def check_dependencies(self):
        return True

    def initialize(self, iface):
        self._state = ExtensionState.INITIALIZED

    def teardown(self):
        self._state = ExtensionState.TORN_DOWN


class TestExtensionPersist:
    def test_base_extension_survives_a_connection_in_the_live_config(self, live_config):
        path, data, connection = live_config

        assert _Sample()._persist_config() is True

        saved = json.loads(path.read_text(encoding="utf-8"))
        assert saved["CURRENT_PROJECT"]["OPTIONS"]["ACTIVE_POSTGRESQL"] is None
        assert saved["EXTENSIONS"]["sample"] == {"enabled": {"value": True}}
        assert data["CURRENT_PROJECT"]["OPTIONS"]["ACTIVE_POSTGRESQL"] is connection  # the live data is not touched
        assert [p.name for p in path.parent.iterdir()] == ["config.json"]

    def test_registry_survives_it_too(self, live_config):
        path, data, connection = live_config

        assert ExtensionRegistry()._persist_config() is True

        assert json.loads(path.read_text(encoding="utf-8"))["CURRENT_PROJECT"]["OPTIONS"]["ACTIVE_POSTGRESQL"] is None
        assert [p.name for p in path.parent.iterdir()] == ["config.json"]

    def test_a_failed_write_is_a_warning_and_leaves_the_file(self, live_config, monkeypatch, caplog):
        path, _data, _connection = live_config
        before = path.read_text(encoding="utf-8")
        monkeypatch.setattr("extensions.base.write_config_json", MagicMock(return_value=False))

        assert _Sample()._persist_config() is False
        assert path.read_text(encoding="utf-8") == before

    def test_neither_opens_config_json_for_writing_any_more(self):
        import ast
        from pathlib import Path
        root = Path(__file__).resolve().parents[3] / "extensions"
        for name in ("base.py", "registry.py"):
            tree = ast.parse((root / name).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "open" and len(node.args) > 1:
                    mode = getattr(node.args[1], "value", "r")
                    assert not any(flag in str(mode) for flag in "wax+"), f"{name}:{node.lineno}"
        assert os.path.exists(root / "config_io.py")
