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
import sys
from pathlib import Path

import pytest


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
