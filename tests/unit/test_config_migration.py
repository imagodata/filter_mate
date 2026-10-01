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
import importlib.util
import json
import sys
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

    for name in (
        "qgis",
        "qgis.core",
        "filter_mate",
        "filter_mate.core",
        "filter_mate.core.optimization",
        "filter_mate.core.optimization.config_provider",
    ):
        if name not in sys.modules:
            sys.modules[name] = MagicMock()
    # ``from … import get_optimization_thresholds`` resolves to a callable
    # via MagicMock — fine, we never call it from these helpers.
    sys.modules["filter_mate.core.optimization.config_provider"] \
        .get_optimization_thresholds = MagicMock()

    spec = importlib.util.spec_from_file_location(
        "_test_filter_mate_config", str(config_path),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
        assert enabled["value"] is False
        assert enabled["choices"] == [True, False]
        assert enabled["value"] in enabled["choices"]
        assert isinstance(enabled["description"], str) and enabled["description"]

    def test_point_cloud_section_has_description(self, default_config):
        section = default_config["APP"]["OPTIONS"]["POINT_CLOUD"]
        assert isinstance(section["description"], str) and section["description"]
        assert "_hidden" not in section

    def test_point_cloud_is_last_option_section(self, default_config):
        keys = list(default_config["APP"]["OPTIONS"].keys())
        assert keys[-1] == "POINT_CLOUD"
        assert keys[-2] == "EXPLORATION"
