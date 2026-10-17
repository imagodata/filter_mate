# -*- coding: utf-8 -*-
"""
FilterMate plugin entry (filter_mate.py), methods extracted with ast (the module
cannot be imported outside QGIS):

- the forced language is read from the active config (QGIS profile), where the
  Configuration tab saves it, not from config/config.json of the plugin folder;
- "Reset configuration and database" resets the active config and keeps the
  favorites stored in the layer database (it deleted every .db / .sqlite file).
"""
import ast
import json
import os
import sqlite3
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_PLUGIN = Path(__file__).resolve().parents[2] / "filter_mate.py"
_PKG = "_fm_plugin_pkg"


def _tree():
    return ast.parse(_PLUGIN.read_text(encoding="utf-8"))


def _class_methods(names):
    cls = next(n for n in _tree().body if isinstance(n, ast.ClassDef) and n.name == "FilterMate")
    return [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]


def _load(names, namespace, module_level=()):
    body = [n for n in _tree().body
            if (isinstance(n, ast.FunctionDef) and n.name in module_level)
            or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in module_level for t in n.targets))]
    methods = _class_methods(names)
    assert len(methods) == len(names)
    namespace.setdefault("logger", MagicMock())
    exec(compile(ast.Module(body=body + methods, type_ignores=[]), str(_PLUGIN), "exec"), namespace)
    return namespace


class _Plugin:
    pass


def _bind(plugin, namespace, names):
    for name in names:
        setattr(plugin, name, types.MethodType(namespace[name], plugin))


@pytest.mark.unit
class TestForcedLanguage:

    def test_read_from_the_active_config(self, tmp_path):
        plugin_dir = tmp_path / "filter_mate"
        (plugin_dir / "i18n").mkdir(parents=True)
        for locale in ("de", "fr", "en"):
            (plugin_dir / "i18n" / f"FilterMate_{locale}.qm").write_bytes(b"")
        (plugin_dir / "config").mkdir()
        (plugin_dir / "config" / "config.json").write_text(
            '{"APP": {"DOCKWIDGET": {"LANGUAGE": {"value": "fr"}}}}', encoding="utf-8")
        profile_config = tmp_path / "profile" / "FilterMate" / "config.json"
        profile_config.parent.mkdir(parents=True)
        profile_config.write_text('{"APP": {"DOCKWIDGET": {"LANGUAGE": {"value": "de"}}}}', encoding="utf-8")
        loaded = []
        translator = types.SimpleNamespace(load=loaded.append)
        namespace = _load(["__init__", "tr"], {
            "__file__": str(plugin_dir / "filter_mate.py"), "os": os,
            "QSettings": lambda: types.SimpleNamespace(value=lambda key: "en_US"),
            "QTranslator": lambda: translator, "QCoreApplication": MagicMock(),
            "get_config_json_path": lambda: str(profile_config),
        })

        plugin = _Plugin()
        _bind(plugin, namespace, ["tr"])
        namespace["__init__"](plugin, None)

        assert [os.path.basename(path) for path in loaded] == ["FilterMate_de.qm"]
        assert plugin._current_locale == "de"


def _layer_database(path):
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE fm_projects (project_id TEXT);
        CREATE TABLE fm_favorites (id TEXT, project_uuid TEXT);
        CREATE TABLE fm_project_layers_properties (fk_project TEXT, layer_id TEXT);
        CREATE TABLE fm_subset_history (fk_project TEXT, layer_id TEXT);
        INSERT INTO fm_projects VALUES ('p1');
        INSERT INTO fm_favorites VALUES ('fav1', 'p1');
        INSERT INTO fm_project_layers_properties VALUES ('p1', 'L1');
        INSERT INTO fm_subset_history VALUES ('p1', 'L1');
    """)
    conn.commit()
    conn.close()


def _count(path, table):
    conn = sqlite3.connect(path)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # nosec B608
    finally:
        conn.close()


class _MessageBox:
    class StandardButton:
        Yes, No = 1, 2

    question = staticmethod(lambda *args: _MessageBox.StandardButton.Yes)
    information = staticmethod(lambda *args: None)


@pytest.fixture
def reset_env(tmp_path, monkeypatch):
    plugin_dir = tmp_path / "filter_mate"
    (plugin_dir / "config").mkdir(parents=True)
    (plugin_dir / "config" / "config.default.json").write_text('{"APP": {"default": true}}', encoding="utf-8")
    shipped = plugin_dir / "config" / "config.json"
    shipped.write_text('{"APP": {"shipped": true}}', encoding="utf-8")
    profile = tmp_path / "profile" / "FilterMate"
    profile.mkdir(parents=True)
    _layer_database(str(profile / "filterMate_db.sqlite"))
    (profile / "filtermate_cache.db").write_bytes(b"cache")
    (profile / "config.json").write_text('{"APP": {"user": true}}', encoding="utf-8")

    env_vars = {}

    def init_env_vars():
        env_vars.update(PLUGIN_CONFIG_DIRECTORY=str(profile), CONFIG_JSON_PATH=str(profile / "config.json"),
                        DIR_CONFIG=str(plugin_dir / "config"))
        env_vars["CONFIG_DATA"] = json.loads((profile / "config.json").read_text(encoding="utf-8"))

    def reset_config_to_default():
        Path(env_vars["CONFIG_JSON_PATH"]).write_text(
            (plugin_dir / "config" / "config.default.json").read_text(encoding="utf-8"), encoding="utf-8")
        return True

    for name, attrs in (
        (_PKG, {}), (f"{_PKG}.config", {}),
        (f"{_PKG}.config.config", dict(ENV_VARS=env_vars, init_env_vars=init_env_vars,
                                       reset_config_to_default=reset_config_to_default)),
        (f"{_PKG}.infrastructure", {}),
    ):
        module = types.ModuleType(name)
        module.__path__ = []
        module.__dict__.update(attrs)
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(sys.modules["qgis.PyQt.QtWidgets"], "QMessageBox", _MessageBox, raising=False)

    namespace = _load(["reset_configuration", "_adopt_reset_config", "tr"],
                      {"__package__": _PKG, "os": os, "QCoreApplication": MagicMock()},
                      module_level=("LAYER_DATABASE_NAME", "LEGACY_CACHE_DB_NAME", "_clear_layer_database"))
    plugin = _Plugin()
    connection = object()
    plugin.app = types.SimpleNamespace(dockwidget=types.SimpleNamespace(CONFIG_DATA={
        "APP": {"user": True}, "CURRENT_PROJECT": {"OPTIONS": {"ACTIVE_POSTGRESQL": connection}}}))
    plugin.plugin_dir = str(plugin_dir)
    plugin.iface = MagicMock()
    _bind(plugin, namespace, ["reset_configuration", "_adopt_reset_config", "tr"])
    return types.SimpleNamespace(plugin=plugin, profile=profile, shipped=shipped, namespace=namespace,
                                 connection=connection)


@pytest.mark.unit
class TestResetConfiguration:

    def test_the_panel_config_takes_the_reset_values(self, reset_env):
        """FilterMateApp.save_project_variables writes the panel's dict to config.json at the
        end of every layer task: the old settings came back before the restart."""
        live = reset_env.plugin.app.dockwidget.CONFIG_DATA

        reset_env.plugin.reset_configuration()

        assert live == {"APP": {"default": True},
                        "CURRENT_PROJECT": {"OPTIONS": {"ACTIVE_POSTGRESQL": reset_env.connection}}}
        assert reset_env.plugin.app.dockwidget.CONFIG_DATA is live

    def test_the_active_config_is_reset(self, reset_env):
        reset_env.plugin.reset_configuration()

        assert (reset_env.profile / "config.json").read_text(encoding="utf-8") == '{"APP": {"default": true}}'
        assert reset_env.shipped.read_text(encoding="utf-8") == '{"APP": {"shipped": true}}'
        reset_env.plugin.iface.messageBar().pushCritical.assert_not_called()

    def test_favorites_survive_and_layer_data_is_deleted(self, reset_env):
        db = str(reset_env.profile / "filterMate_db.sqlite")

        reset_env.plugin.reset_configuration()

        assert _count(db, "fm_favorites") == 1
        assert _count(db, "fm_projects") == 1
        assert _count(db, "fm_project_layers_properties") == 0
        assert _count(db, "fm_subset_history") == 0
        assert not (reset_env.profile / "filtermate_cache.db").exists()

    def test_clear_layer_database_on_a_database_without_the_tables(self, reset_env, tmp_path):
        db = str(tmp_path / "empty.sqlite")
        sqlite3.connect(db).close()

        reset_env.namespace["_clear_layer_database"](db)  # no "no such table" error
