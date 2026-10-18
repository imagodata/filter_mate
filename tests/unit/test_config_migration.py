# -*- coding: utf-8 -*-
"""Tests for config migration helpers (``_sync_metadata`` / ``_migrate_config``).

These helpers ensure the Configuration panel always shows the schema-owned
metadata from the current release (descriptions, choices, bounds, _hidden,
_display_name) rather than whatever stale text the user's frozen
config.json still carries from an older version. The user's ``value`` is
always preserved.

The functions are imported via a lightweight stand-alone path that does
not require pulling in ``filter_mate.core.optimization.config_provider``
(which transitively imports the QGIS PyQt wrappers).
"""
import ast
import importlib.util
import json
import os
import sys
import types
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DEFAULT_PATH = PLUGIN_ROOT / "config" / "config.default.json"


@pytest.fixture(scope="module")
def config_helpers():
    """Load just ``_sync_metadata`` / ``_migrate_config`` / ``merge`` from
    config/config.py without executing the QGIS-dependent imports.

    The module's first non-stdlib import is the optimization
    ``config_provider``, which transitively pulls QGIS PyQt wrappers that
    are not packaged on the test runner. We patch around that by
    pre-installing a stub for the offending module.
    """
    plugin_root = Path(__file__).resolve().parents[2]
    config_path = plugin_root / "config" / "config.py"

    # Stub the QGIS module surface needed by config.py top-level imports.
    from unittest.mock import MagicMock

    for name in ("qgis", "qgis.core"):
        if name not in sys.modules:
            sys.modules[name] = MagicMock()

    # config.py imports core.optimization.config_provider RELATIVELY (the plugin folder
    # name is not 'filter_mate' once installed from a zip): load it as a module of a
    # throw-away package, with a stub for that provider.
    package = "_test_fm_pkg"
    for name, path in ((package, plugin_root), (f"{package}.config", plugin_root / "config"),
                       (f"{package}.core", plugin_root / "core"),
                       (f"{package}.core.optimization", plugin_root / "core" / "optimization")):
        stub = types.ModuleType(name)
        stub.__path__ = [str(path)]
        sys.modules[name] = stub
    provider = types.ModuleType(f"{package}.core.optimization.config_provider")
    provider.get_optimization_thresholds = MagicMock()
    sys.modules[provider.__name__] = provider

    spec = importlib.util.spec_from_file_location(f"{package}.config.config", str(config_path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    yield module
    for name in [n for n in sys.modules if n == package or n.startswith(package + ".")]:
        del sys.modules[name]


class TestSyncMetadata:
    """Direct tests for ``_sync_metadata`` (the leaf helper)."""

    def test_overlays_description_choices_min_max(self, config_helpers):
        user = {
            "endpoint": {"value": "https://user.example", "description": "OLD"},
            "timeout": {"value": 99, "min": 0, "max": 100, "description": "OLD"},
            "flag": {"value": True, "choices": [True], "description": "OLD"},
        }
        ref = {
            "endpoint": {"value": "https://default", "description": "NEW api"},
            "timeout": {"value": 30, "min": 1, "max": 300, "description": "NEW timeout"},
            "flag": {"value": False, "choices": [True, False], "description": "NEW flag"},
        }
        dirty = config_helpers._sync_metadata(user, ref)
        assert dirty is True
        # Values preserved
        assert user["endpoint"]["value"] == "https://user.example"
        assert user["timeout"]["value"] == 99
        assert user["flag"]["value"] is True
        # Metadata refreshed
        assert user["endpoint"]["description"] == "NEW api"
        assert user["timeout"]["min"] == 1
        assert user["timeout"]["max"] == 300
        assert user["timeout"]["description"] == "NEW timeout"
        assert user["flag"]["choices"] == [True, False]
        assert user["flag"]["description"] == "NEW flag"

    def test_overlays_hidden_and_display_name(self, config_helpers):
        user = {"EXTENSIONS": {"_hidden": False, "_display_name": "Old"}}
        ref = {"EXTENSIONS": {"_hidden": True, "_display_name": "Extensions"}}
        config_helpers._sync_metadata(user, ref)
        assert user["EXTENSIONS"]["_hidden"] is True
        assert user["EXTENSIONS"]["_display_name"] == "Extensions"

    def test_idempotent_when_metadata_already_matches(self, config_helpers):
        user = {"a": {"value": 1, "description": "same"}}
        ref = {"a": {"value": 0, "description": "same"}}
        assert config_helpers._sync_metadata(user, ref) is False

    def test_does_not_touch_user_value_dicts(self, config_helpers):
        """``value`` is opaque user data — even when it's a nested dict, we
        must not let the recursion sneak inside and overlay anything.
        """
        user = {
            "publish_metadata": {
                "value": {"author": "Alice", "license": "MIT"},
                "description": "OLD",
            },
        }
        ref = {
            "publish_metadata": {
                "value": {"author": "", "license": "", "homepage": ""},
                "description": "NEW",
            },
        }
        config_helpers._sync_metadata(user, ref)
        # value dict left exactly as the user had it
        assert user["publish_metadata"]["value"] == {"author": "Alice", "license": "MIT"}
        # description overlaid
        assert user["publish_metadata"]["description"] == "NEW"

    def test_recurses_into_container_dicts(self, config_helpers):
        user = {
            "APP": {
                "OPTIONS": {
                    "TIMEOUT": {"value": 5, "description": "OLD"},
                },
            },
        }
        ref = {
            "APP": {
                "_display_name": "Settings",
                "OPTIONS": {
                    "_display_name": "Performance",
                    "TIMEOUT": {"value": 0, "description": "NEW"},
                },
            },
        }
        config_helpers._sync_metadata(user, ref)
        assert user["APP"]["_display_name"] == "Settings"
        assert user["APP"]["OPTIONS"]["_display_name"] == "Performance"
        assert user["APP"]["OPTIONS"]["TIMEOUT"]["description"] == "NEW"
        assert user["APP"]["OPTIONS"]["TIMEOUT"]["value"] == 5  # preserved

    def test_skips_keys_user_added_locally(self, config_helpers):
        """Reference is the source of truth — keys present only in the user
        config are left alone (they may be project-specific or runtime data).
        """
        user = {"SECTION": {"local_only": "kept", "description": "OLD"}}
        ref = {"SECTION": {"description": "NEW"}}
        config_helpers._sync_metadata(user, ref)
        assert user["SECTION"]["local_only"] == "kept"
        assert user["SECTION"]["description"] == "NEW"

    def test_returns_false_for_non_dict_inputs(self, config_helpers):
        assert config_helpers._sync_metadata(None, {}) is False
        assert config_helpers._sync_metadata({}, None) is False
        assert config_helpers._sync_metadata("a", "b") is False


class TestMigrateConfigRefreshesMetadata:
    """Top-level migration smoke test."""

    def test_migrate_overlays_template_metadata(self, config_helpers):
        user = {
            "_CONFIG_VERSION": "2.0",
            "APP": {
                "_display_name": "Old Settings",
                "DOCKWIDGET": {
                    "LANGUAGE": {
                        "value": "fr",  # user's choice — must survive
                        "choices": ["auto", "fr"],  # stale list
                        "description": "OLD",
                    },
                    "COLORS": {
                        "ACTIVE_THEME": {
                            "value": "dark",
                            "choices": ["default", "dark"],
                            "description": "OLD",
                        },
                    },
                },
                "OPTIONS": {},
            },
        }
        default = {
            "_CONFIG_VERSION": "2.0",
            "APP": {
                "_display_name": "Settings",
                "DOCKWIDGET": {
                    "_display_name": "Interface",
                    "LANGUAGE": {
                        "value": "auto",
                        "choices": ["auto", "fr", "en", "es"],
                        "description": "Interface language",
                    },
                    "COLORS": {
                        "_display_name": "Appearance",
                        "ACTIVE_THEME": {
                            "value": "default",
                            "choices": ["auto", "default", "dark", "light"],
                            "description": "Color theme for UI",
                        },
                    },
                },
                "OPTIONS": {
                    "_display_name": "Performance",
                    "APP_SQLITE_PATH": {"value": "", "description": "DB dir"},
                    "FRESH_RELOAD_FLAG": {"value": False, "description": "Force reload"},
                },
            },
        }

        config_helpers._migrate_config(user, default)

        # User's chosen values preserved
        assert user["APP"]["DOCKWIDGET"]["LANGUAGE"]["value"] == "fr"
        assert user["APP"]["DOCKWIDGET"]["COLORS"]["ACTIVE_THEME"]["value"] == "dark"

        # Schema-owned metadata refreshed
        assert user["APP"]["DOCKWIDGET"]["LANGUAGE"]["choices"] == \
            ["auto", "fr", "en", "es"]
        assert user["APP"]["DOCKWIDGET"]["LANGUAGE"]["description"] == \
            "Interface language"
        assert user["APP"]["DOCKWIDGET"]["COLORS"]["ACTIVE_THEME"]["choices"] == \
            ["auto", "default", "dark", "light"]

        # _display_name overlaid even on container dicts
        assert user["APP"]["_display_name"] == "Settings"
        assert user["APP"]["DOCKWIDGET"]["_display_name"] == "Interface"
        assert user["APP"]["DOCKWIDGET"]["COLORS"]["_display_name"] == "Appearance"

        # New keys added by the existing merge() pass
        assert "APP_SQLITE_PATH" in user["APP"]["OPTIONS"]
        assert "FRESH_RELOAD_FLAG" in user["APP"]["OPTIONS"]


def _point_cloud_section():
    return {
        "description": "Point cloud filtering",
        "enabled": {
            "value": False,
            "choices": [True, False],
            "description": "Enable the point cloud panel",
        },
    }


def _migrated_user_config():
    """A user config already carrying every migration marker except POINT_CLOUD."""
    return {
        "_CONFIG_VERSION": "2.0",
        "_CONFIG_META": {"_hidden": True, "version": "2.0"},
        "APP": {
            "_display_name": "Settings",
            "DOCKWIDGET": {"_display_name": "Interface", "COLORS": {"_display_name": "Appearance"}},
            "OPTIONS": {
                "_display_name": "Performance",
                "APP_SQLITE_PATH": {"_hidden": True, "value": "/tmp", "description": "DB dir"},
                "FRESH_RELOAD_FLAG": {"_hidden": True, "value": False, "description": "Force reload"},
                "EXPLORATION": {
                    "description": "Exploration",
                    "auto_zoom_on_filter": {"value": False, "description": "Auto zoom"},
                },
            },
        },
        "EXTENSIONS": {"_display_name": "Extensions"},
    }


def _default_config_with_point_cloud():
    default = _migrated_user_config()
    default["APP"]["OPTIONS"]["APP_SQLITE_PATH"]["value"] = ""
    default["APP"]["OPTIONS"]["EXPLORATION"]["auto_zoom_on_filter"]["value"] = True
    default["APP"]["OPTIONS"]["POINT_CLOUD"] = _point_cloud_section()
    return default


class TestMergeMissingKeys:
    """Direct tests for ``_merge_missing_keys`` (the dirty-aware merge)."""

    def test_returns_true_when_top_level_key_added(self, config_helpers):
        user = {"a": 1}
        assert config_helpers._merge_missing_keys(user, {"a": 0, "b": 2}) is True
        assert user == {"a": 1, "b": 2}

    def test_returns_true_when_nested_key_added(self, config_helpers):
        user = {"APP": {"OPTIONS": {"X": {"value": 1}}}}
        ref = {"APP": {"OPTIONS": {"X": {"value": 0}, "Y": {"value": 2}}}}
        assert config_helpers._merge_missing_keys(user, ref) is True
        assert user["APP"]["OPTIONS"]["X"]["value"] == 1
        assert user["APP"]["OPTIONS"]["Y"] == {"value": 2}

    def test_returns_false_when_nothing_missing(self, config_helpers):
        user = {"a": {"b": 1, "c": [1, 2]}, "d": "x"}
        ref = {"a": {"b": 0, "c": []}, "d": "y"}
        assert config_helpers._merge_missing_keys(user, ref) is False
        assert user == {"a": {"b": 1, "c": [1, 2]}, "d": "x"}

    def test_never_overwrites_existing_leaf(self, config_helpers):
        user = {"a": {"value": "mine"}}
        config_helpers._merge_missing_keys(user, {"a": {"value": "theirs", "description": "d"}})
        assert user["a"]["value"] == "mine"
        assert user["a"]["description"] == "d"

    def test_added_subtree_does_not_alias_reference(self, config_helpers):
        ref = {"NEW": {"enabled": {"value": False}}}
        user = {}
        config_helpers._merge_missing_keys(user, ref)
        user["NEW"]["enabled"]["value"] = True
        assert ref["NEW"]["enabled"]["value"] is False

    def test_returns_false_for_non_dict_inputs(self, config_helpers):
        assert config_helpers._merge_missing_keys(None, {"a": 1}) is False
        assert config_helpers._merge_missing_keys({}, None) is False
        assert config_helpers._merge_missing_keys("a", "b") is False

    def test_legacy_merge_still_returns_destination(self, config_helpers):
        user = {"a": 1}
        result = config_helpers.merge(user, {"a": 0, "b": 2})
        assert result is user
        assert user == {"a": 1, "b": 2}


class TestMigrateConfigPersistsNewSections:
    """A brand-new section in the template must flag the config as dirty so
    ``init_env_vars`` writes it back to disk (otherwise it only lives in
    memory and vanishes on the next ``reload_config``)."""

    def test_new_point_cloud_section_marks_config_dirty(self, config_helpers):
        user = _migrated_user_config()
        default = _default_config_with_point_cloud()
        assert "POINT_CLOUD" not in user["APP"]["OPTIONS"]

        dirty = config_helpers._migrate_config(user, default)

        assert dirty is True
        section = user["APP"]["OPTIONS"]["POINT_CLOUD"]
        assert section["enabled"]["value"] is False
        assert section["enabled"]["choices"] == [True, False]
        assert isinstance(section["enabled"]["description"], str)
        # Existing user values untouched
        assert user["APP"]["OPTIONS"]["APP_SQLITE_PATH"]["value"] == "/tmp"
        assert user["APP"]["OPTIONS"]["EXPLORATION"]["auto_zoom_on_filter"]["value"] is False

    def test_migration_is_idempotent_once_section_present(self, config_helpers):
        user = _migrated_user_config()
        default = _default_config_with_point_cloud()
        assert config_helpers._migrate_config(user, default) is True
        assert config_helpers._migrate_config(user, default) is False

    def test_user_flag_value_survives_migration(self, config_helpers):
        user = _migrated_user_config()
        user["APP"]["OPTIONS"]["POINT_CLOUD"] = _point_cloud_section()
        user["APP"]["OPTIONS"]["POINT_CLOUD"]["enabled"]["value"] = True
        default = _default_config_with_point_cloud()

        assert config_helpers._migrate_config(user, default) is False
        assert user["APP"]["OPTIONS"]["POINT_CLOUD"]["enabled"]["value"] is True


def _raster_section(value=True):
    return {
        "description": "Raster filtering",
        "enabled": {"value": value, "choices": [True, False], "description": "Show raster layers"},
    }


def _fm5_default():
    default = _default_config_with_point_cloud()
    default["APP"]["OPTIONS"]["POINT_CLOUD"]["enabled"]["value"] = True
    default["APP"]["OPTIONS"]["RASTER"] = _raster_section()
    return default


class TestFilterMate5EnablesLayerKinds:
    """Raster and point cloud layers are on by default in FilterMate 5. A 4.x
    config still carries the off default of the experimental point cloud flag:
    it is turned on once, then the Configuration panel decides."""

    def _user_4x(self, point_cloud_value=False):
        user = _migrated_user_config()
        user["APP"]["OPTIONS"]["POINT_CLOUD"] = _point_cloud_section()
        user["APP"]["OPTIONS"]["POINT_CLOUD"]["enabled"]["value"] = point_cloud_value
        return user

    def test_4x_point_cloud_off_is_turned_on(self, config_helpers):
        user = self._user_4x(False)
        assert config_helpers._migrate_config(user, _fm5_default()) is True
        assert user["APP"]["OPTIONS"]["POINT_CLOUD"]["enabled"]["value"] is True
        assert user["APP"]["OPTIONS"]["RASTER"]["enabled"]["value"] is True

    def test_turned_on_only_once(self, config_helpers):
        """Switched off again in the Configuration panel: stays off at the next start."""
        user = self._user_4x(False)
        config_helpers._migrate_config(user, _fm5_default())
        user["APP"]["OPTIONS"]["POINT_CLOUD"]["enabled"]["value"] = False
        user["APP"]["OPTIONS"]["RASTER"]["enabled"]["value"] = False
        assert config_helpers._migrate_config(user, _fm5_default()) is False
        assert user["APP"]["OPTIONS"]["POINT_CLOUD"]["enabled"]["value"] is False
        assert user["APP"]["OPTIONS"]["RASTER"]["enabled"]["value"] is False

    def test_4x_without_point_cloud_section_gets_defaults(self, config_helpers):
        user = _migrated_user_config()
        config_helpers._migrate_config(user, _fm5_default())
        assert user["APP"]["OPTIONS"]["POINT_CLOUD"]["enabled"]["value"] is True
        assert user["APP"]["OPTIONS"]["RASTER"]["enabled"]["value"] is True

    def test_template_without_raster_never_flips(self, config_helpers):
        """The marker is the RASTER section of the template: without it, nothing is forced."""
        user = self._user_4x(False)
        config_helpers._migrate_config(user, _default_config_with_point_cloud())
        assert user["APP"]["OPTIONS"]["POINT_CLOUD"]["enabled"]["value"] is False

    def test_raw_flag_value_is_turned_on_too(self, config_helpers):
        user = _migrated_user_config()
        user["APP"]["OPTIONS"]["POINT_CLOUD"] = {"enabled": False}
        config_helpers._migrate_config(user, _fm5_default())
        enabled = user["APP"]["OPTIONS"]["POINT_CLOUD"]["enabled"]
        assert (enabled["value"] if isinstance(enabled, dict) else enabled) is True


@pytest.fixture(scope="module")
def default_config():
    with open(CONFIG_DEFAULT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TestDefaultConfigPointCloudSection:
    """The shipped template must declare the point cloud feature flag."""

    def test_point_cloud_enabled_is_choices_entry(self, default_config):
        section = default_config["APP"]["OPTIONS"]["POINT_CLOUD"]
        enabled = section["enabled"]
        assert set(enabled.keys()) == {"value", "choices", "description"}
        # FilterMate 5: point clouds are a first-class layer kind, on by default.
        assert enabled["value"] is True
        assert enabled["choices"] == [True, False]
        assert enabled["value"] in enabled["choices"]
        assert isinstance(enabled["description"], str) and enabled["description"]

    def test_point_cloud_section_has_description(self, default_config):
        section = default_config["APP"]["OPTIONS"]["POINT_CLOUD"]
        assert isinstance(section["description"], str) and section["description"]
        assert "_hidden" not in section

    def test_point_cloud_follows_exploration(self, default_config):
        keys = list(default_config["APP"]["OPTIONS"].keys())
        assert keys.index("POINT_CLOUD") == keys.index("EXPLORATION") + 1


class TestDefaultConfigRasterAndCrossFilterSections:
    """FilterMate 5 sections: raster flag and cross-kind filtering options."""

    def test_raster_enabled_is_choices_entry(self, default_config):
        enabled = default_config["APP"]["OPTIONS"]["RASTER"]["enabled"]
        assert set(enabled.keys()) == {"value", "choices", "description"}
        assert enabled["value"] is True
        assert enabled["choices"] == [True, False]

    def test_cross_filter_options(self, default_config):
        section = default_config["APP"]["OPTIONS"]["CROSS_FILTER"]
        assert section["point_cloud_clip"]["value"] in section["point_cloud_clip"]["choices"]
        assert section["raster_source_max_pixels"]["value"] >= 400000000
        assert section["point_cloud_footprint_resolution"]["value"] > 0
        assert section["cache_max_gb"]["value"] > 0
        assert section["pdal_path"]["value"] == ""

    def test_sections_order(self, default_config):
        keys = list(default_config["APP"]["OPTIONS"].keys())
        assert keys[-3:] == ["POINT_CLOUD", "RASTER", "CROSS_FILTER"]

    def test_options_read_by_the_code_are_declared(self, default_config):
        """cache_dir and the export formats were read with a code default but absent from
        the template, so missing from the Configuration tab."""
        section = default_config["APP"]["OPTIONS"]["CROSS_FILTER"]
        assert section["cache_dir"]["value"] == ""  # the cache module's default: the QGIS profile
        assert section["raster_export_format"]["value"] == "COG"  # the dock's defaults
        assert section["point_cloud_export_format"]["value"] == "LAZ"
        exporters = ast.parse((PLUGIN_ROOT / "adapters" / "qgis" / "coverage_layers" / "exporters.py")
                              .read_text(encoding="utf-8"))
        formats = {node.targets[0].id: ast.literal_eval(node.value) for node in exporters.body
                   if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "").endswith("_FORMATS")}
        assert set(section["raster_export_format"]["choices"]) == set(formats["RASTER_FORMATS"])
        assert set(section["point_cloud_export_format"]["choices"]) == set(formats["POINT_CLOUD_FORMATS"])


class TestShippedConfigJson:
    """config/config.json is read as a fallback (no copy in the QGIS profile, REST API):
    it predated FilterMate 5 (no RASTER, POINT_CLOUD nor CROSS_FILTER section)."""

    def test_it_mirrors_the_template(self, default_config):
        with open(PLUGIN_ROOT / "config" / "config.json", "r", encoding="utf-8") as f:
            assert json.load(f) == default_config


class TestFallbackConfig:

    def test_layer_kinds_are_on_as_in_the_template(self, config_helpers, default_config):
        options = config_helpers.get_fallback_config()["APP"]["OPTIONS"]
        for kind in ("RASTER", "POINT_CLOUD"):
            assert options[kind]["enabled"]["value"] is True
            assert options[kind]["enabled"]["value"] == default_config["APP"]["OPTIONS"][kind]["enabled"]["value"]


class TestOptionReaders:

    @pytest.mark.parametrize("value", [False, "false", "False", " FALSE ", "0", "no", "off", "", 0])
    def test_bool_false(self, config_helpers, value):
        assert config_helpers._get_option_bool({"value": value}, True) is False

    @pytest.mark.parametrize("value", [True, "true", "True", "1", "yes", "on", 1])
    def test_bool_true(self, config_helpers, value):
        assert config_helpers._get_option_bool({"value": value}, False) is True

    @pytest.mark.parametrize("option", [None, {"value": None}, {"value": "maybe"}])
    def test_bool_default(self, config_helpers, option):
        assert config_helpers._get_option_bool(option, True) is True
        assert config_helpers._get_option_bool(option, False) is False

    def test_bool_raw_value(self, config_helpers):
        assert config_helpers._get_option_bool("false", True) is False

    @pytest.mark.parametrize("value, expected", [
        (4000000, 4000000), ("4000000", 4000000), (" 250 ", 250), (4e6, 4000000), ("4e6", 4000000),
        ("2.5", 2), ("lots", 7), ("", 7), (None, 7), (True, 7), (float("nan"), 7), ("inf", 7), ([1], 7)])
    def test_int(self, config_helpers, value, expected):
        assert config_helpers._get_option_int({"value": value}, 7) == expected


class TestActiveConfigPath:
    """The plugin constructor read the forced language in config/config.json of the plugin
    folder, while the Configuration tab saves it in the QGIS profile: lost on restart."""

    def test_after_init_env_vars(self, config_helpers, monkeypatch):
        monkeypatch.setitem(config_helpers.ENV_VARS, "CONFIG_JSON_PATH", "/custom/FilterMate/config.json")
        assert config_helpers.get_config_json_path() == "/custom/FilterMate/config.json"

    def test_before_init_env_vars(self, config_helpers, monkeypatch, tmp_path):
        monkeypatch.delitem(config_helpers.ENV_VARS, "CONFIG_JSON_PATH", raising=False)
        profile = str(tmp_path / "profiles" / "default") + "/"
        monkeypatch.setattr(config_helpers, "QgsApplication",
                            types.SimpleNamespace(qgisSettingsDirPath=lambda: profile))
        expected = str(tmp_path / "profiles" / "default" / "FilterMate" / "config.json")
        assert config_helpers.get_config_json_path() == expected

    def _profile_config(self, config_helpers, monkeypatch, tmp_path, sqlite_path):
        monkeypatch.delitem(config_helpers.ENV_VARS, "CONFIG_JSON_PATH", raising=False)
        profile = tmp_path / "QGIS4" / "profiles" / "default"
        (profile / "FilterMate").mkdir(parents=True)
        (profile / "FilterMate" / "config.json").write_text(json.dumps({
            "APP": {"DOCKWIDGET": {"LANGUAGE": {"value": "vi"}},
                    "OPTIONS": {"APP_SQLITE_PATH": {"value": sqlite_path}}}}), encoding="utf-8")
        monkeypatch.setattr(config_helpers, "QgsApplication",
                            types.SimpleNamespace(qgisSettingsDirPath=lambda: str(profile) + "/"))
        return profile / "FilterMate" / "config.json"

    def test_before_init_env_vars_follows_the_configured_folder(self, config_helpers, monkeypatch, tmp_path):
        """A QGIS 4 profile whose config points to the QGIS 3 FilterMate folder: init_env_vars()
        saves there, so the forced language is read there too (the profile copy is stale)."""
        shared = tmp_path / "QGIS3" / "profiles" / "default" / "FilterMate"
        shared.mkdir(parents=True)
        self._profile_config(config_helpers, monkeypatch, tmp_path, str(shared))
        assert config_helpers.get_config_json_path() == os.path.join(os.path.normpath(str(shared)), "config.json")

    @pytest.mark.parametrize("configured", ["", "/no/such/parent/FilterMate"])
    def test_before_init_env_vars_ignores_an_unusable_folder(self, config_helpers, monkeypatch, tmp_path,
                                                             configured):
        profile_json = self._profile_config(config_helpers, monkeypatch, tmp_path, configured)
        assert config_helpers.get_config_json_path() == str(profile_json)

    def test_before_init_env_vars_without_profile_config(self, config_helpers, monkeypatch, tmp_path):
        monkeypatch.delitem(config_helpers.ENV_VARS, "CONFIG_JSON_PATH", raising=False)
        monkeypatch.setattr(config_helpers, "QgsApplication",
                            types.SimpleNamespace(qgisSettingsDirPath=lambda: str(tmp_path) + "/"))
        assert config_helpers.get_config_json_path() == str(tmp_path / "FilterMate" / "config.json")


class TestConfigFilesAreUtf8:
    """config.default.json holds non-ASCII text (language names) and the Configuration tab
    writes UTF-8: an open() without encoding (cp1252 on Windows) failed, the in-memory
    fallback was used and then written over the user's config.json."""

    @pytest.mark.parametrize("path", sorted(
        str(p.relative_to(PLUGIN_ROOT)) for p in
        list((PLUGIN_ROOT / "config").glob("*.py")) + list((PLUGIN_ROOT / "infrastructure" / "config").glob("*.py"))))
    def test_every_open_names_its_encoding(self, path):
        tree = ast.parse((PLUGIN_ROOT / path).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "open":
                mode = node.args[1].value if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else "r"
                if "b" not in mode:
                    assert any(k.arg == "encoding" for k in node.keywords), f"{path}:{node.lineno}"

    def test_the_template_is_not_ascii(self):
        assert any(byte > 127 for byte in CONFIG_DEFAULT_PATH.read_bytes())


class TestMigrationOddShapes:
    @pytest.mark.parametrize("app", [[], "x", None])
    def test_non_dict_app_section_does_not_raise(self, config_helpers, app):
        user = {"APP": app}
        default = {"APP": {"OPTIONS": {"RASTER": {"enabled": {"value": True}}}}}
        config_helpers._migrate_config(user, default)  # no AttributeError from step 0


class TestDeadAutoOptimizationSwitches:
    """AUTO_OPTIMIZATION.enabled / auto_centroid_for_distant: nothing reads them since the confirmation flow went."""

    DEAD = ("enabled", "auto_centroid_for_distant")

    def test_the_defaults_no_longer_ship_them(self):
        defaults = json.loads(CONFIG_DEFAULT_PATH.read_text(encoding="utf-8"))
        section = defaults["APP"]["OPTIONS"]["AUTO_OPTIMIZATION"]
        assert not [key for key in self.DEAD if key in section]
        shipped = json.loads((PLUGIN_ROOT / "config" / "config.json").read_text(encoding="utf-8"))
        assert not [key for key in self.DEAD if key in shipped["APP"]["OPTIONS"]["AUTO_OPTIMIZATION"]]

    def test_an_old_config_json_loses_them_and_keeps_the_rest(self, config_helpers):
        defaults = json.loads(CONFIG_DEFAULT_PATH.read_text(encoding="utf-8"))
        user = json.loads(CONFIG_DEFAULT_PATH.read_text(encoding="utf-8"))
        section = user["APP"]["OPTIONS"]["AUTO_OPTIMIZATION"]
        section["enabled"] = {"value": False, "description": "old"}
        section["auto_centroid_for_distant"] = {"value": False, "description": "old"}
        section["centroid_threshold_distant"]["value"] = 123

        assert config_helpers._migrate_config(user, defaults) is True

        migrated = user["APP"]["OPTIONS"]["AUTO_OPTIMIZATION"]
        assert not [key for key in self.DEAD if key in migrated]
        assert migrated["centroid_threshold_distant"]["value"] == 123
        assert config_helpers._migrate_config(user, defaults) is False  # idempotent


class TestRasterSourceMaxPixelsRenamed:
    """raster_selection_max_pixels (4 million cells over the whole raster) became raster_source_max_pixels
    when the source geometry of a raster selection went tile by tile at the native resolution (2026-10-18)."""

    def _old_config(self, value):
        user = json.loads(CONFIG_DEFAULT_PATH.read_text(encoding="utf-8"))
        section = user["APP"]["OPTIONS"]["CROSS_FILTER"]
        del section["raster_source_max_pixels"]
        section["raster_selection_max_pixels"] = {"value": value, "description": "old"}
        return user

    def test_the_former_default_gives_way_to_the_new_one(self, config_helpers):
        defaults = json.loads(CONFIG_DEFAULT_PATH.read_text(encoding="utf-8"))
        user = self._old_config(4000000)
        assert config_helpers._migrate_config(user, defaults) is True
        section = user["APP"]["OPTIONS"]["CROSS_FILTER"]
        assert "raster_selection_max_pixels" not in section
        assert section["raster_source_max_pixels"]["value"] == 400000000
        assert config_helpers._migrate_config(user, defaults) is False  # idempotent

    @pytest.mark.parametrize("value", [16000000, "16000000", "lots"])
    def test_the_old_value_is_never_carried_over(self, config_helpers, value):
        """A grid of cells over the whole raster is not a count of pixels read at the native resolution."""
        defaults = json.loads(CONFIG_DEFAULT_PATH.read_text(encoding="utf-8"))
        user = self._old_config(value)
        config_helpers._migrate_config(user, defaults)
        assert user["APP"]["OPTIONS"]["CROSS_FILTER"]["raster_source_max_pixels"]["value"] == 400000000

    def test_a_new_value_already_set_is_kept(self, config_helpers):
        defaults = json.loads(CONFIG_DEFAULT_PATH.read_text(encoding="utf-8"))
        user = self._old_config(16000000)
        user["APP"]["OPTIONS"]["CROSS_FILTER"]["raster_source_max_pixels"] = {"value": 50000000, "description": "x"}
        config_helpers._migrate_config(user, defaults)
        section = user["APP"]["OPTIONS"]["CROSS_FILTER"]
        assert section["raster_source_max_pixels"]["value"] == 50000000 and "raster_selection_max_pixels" not in section
