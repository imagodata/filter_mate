from qgis.core import QgsApplication, QgsProject, QgsMessageLog, Qgis
import os
import sys
import json

# Re-export get_optimization_thresholds for backward compatibility
# Function was moved to core.optimization.config_provider in EPIC-1 Phase E7.5
from filter_mate.core.optimization.config_provider import get_optimization_thresholds  # noqa: F401

ENV_VARS = {}

# Minimal hardcoded fallback configuration
# Used when all config files are inaccessible or corrupted
FALLBACK_CONFIG = {
    "_CONFIG_VERSION": "2.0",
    "_CONFIG_META": {
        "description": "FilterMate Fallback Configuration (in-memory)",
        "version": "2.0",
        "fallback": True
    },
    "APP": {
        "AUTO_ACTIVATE": {
            "value": False,
            "description": "Auto-activate plugin when a project with vector layers is loaded"
        },
        "DOCKWIDGET": {
            "FEEDBACK_LEVEL": {
                "value": "normal",
                "choices": ["minimal", "normal", "verbose"],
                "description": "User feedback verbosity level"
            },
            "LANGUAGE": {
                "value": "auto",
                "description": "Interface language"
            },
            "COLORS": {
                "ACTIVE_THEME": {
                    "value": "default",
                    "choices": ["auto", "default", "dark", "light"],
                    "description": "Color theme for UI"
                },
                "THEME_SOURCE": {
                    "value": "config",
                    "choices": ["config", "qgis", "system"],
                    "description": "Theme source"
                }
            }
        },
        "OPTIONS": {
            "APP_SQLITE_PATH": {
                "value": "",
                "description": "Directory for SQLite databases"
            },
            "FRESH_RELOAD_FLAG": {
                "value": False,
                "description": "Force fresh reload on next startup"
            }
        }
    },
    "POSTGRESQL": {
        "FILTER": {
            "MATERIALIZED_VIEW": {
                "value": True,
                "description": "Use materialized views for filtering"
            }
        }
    },
    "EXTENSIONS": {
        "qfieldcloud": {
            "enabled": {
                "value": False,
                "choices": [True, False],
                "description": "Enable/disable the QFieldCloud extension"
            },
            "dismiss_missing_deps_warning": {
                "value": False,
                "choices": [True, False],
                "description": "Do not show the missing dependencies warning"
            }
        },
        "favorites_sharing": {
            "enabled": {
                "value": True,
                "choices": [True, False],
                "description": "Enable/disable the Favorites Sharing extension (Resource Sharing integration)"
            },
            "dismiss_missing_deps_warning": {
                "value": False,
                "choices": [True, False],
                "description": "Do not show the missing dependencies warning"
            }
        }
    }
}


def _get_option_value(option, default=""):
    """Extract value from a config option, handling both wrapped and raw formats.

    Wrapped format: {"value": "...", "description": "..."}
    Raw format (legacy): "..." or False etc.

    Args:
        option: The config option (dict with 'value' key, or raw value)
        default: Default value if option is None

    Returns:
        The extracted value
    """
    if option is None:
        return default
    if isinstance(option, dict) and 'value' in option:
        return option['value']
    return option


def _set_option_value(options_dict, key, new_value):
    """Set value in a config option, handling both wrapped and raw formats.

    Args:
        options_dict: The parent dict containing the option
        key: The option key
        new_value: The new value to set
    """
    option = options_dict.get(key)
    if isinstance(option, dict) and 'value' in option:
        option['value'] = new_value
    else:
        options_dict[key] = new_value


def _migrate_config(config_data, default_data):
    """Migrate user config to latest structure.

    Merges new keys from default, adds _hidden/_display_name metadata,
    and removes deprecated sections. Safe to call on already-migrated configs.

    Args:
        config_data: User's current config dict (modified in place)
        default_data: Default config dict (read-only reference)

    Returns:
        True if any changes were made, False otherwise
    """
    dirty = False

    # 1) Merge new keys from default into user config (recursive, non-destructive)
    merge(config_data, default_data)

    app = config_data.get("APP", {})
    dockwidget = app.get("DOCKWIDGET", {})
    options = app.get("OPTIONS", {})
    colors = dockwidget.get("COLORS", {})

    # 2) Add _hidden metadata where missing
    hidden_targets = {
        # (parent_dict, key) → must have _hidden: True in value dict
        "CONFIG_META": (config_data, "_CONFIG_META"),
        "PushButton": (dockwidget, "PushButton"),
        "CURRENT_PROJECT": (config_data, "CURRENT_PROJECT"),
    }
    # OPTIONS entries that should be hidden
    for key in ("DISCORD_INVITE", "GITHUB_PAGE", "GITHUB_REPOSITORY",
                "QGIS_PLUGIN_REPOSITORY", "APP_SQLITE_PATH", "FRESH_RELOAD_FLAG"):
        hidden_targets[f"OPTIONS.{key}"] = (options, key)

    for label, (parent, key) in hidden_targets.items():
        val = parent.get(key)
        if isinstance(val, dict):
            if val.get("_hidden") is not True:
                val["_hidden"] = True
                dirty = True
        elif key in parent:
            # Convert raw value (str, bool, etc.) to wrapped dict with _hidden
            parent[key] = {"_hidden": True, "value": val}
            dirty = True

    # 3) Add _display_name where missing
    display_names = {
        # (dict_ref, expected_display_name)
        "APP": (app, "Settings"),
        "DOCKWIDGET": (dockwidget, "Interface"),
        "COLORS": (colors, "Appearance"),
        "OPTIONS": (options, "Performance"),
    }
    for label, (d, name) in display_names.items():
        if isinstance(d, dict) and d.get("_display_name") != name:
            d["_display_name"] = name
            dirty = True

    # 4) Remove deprecated PERFORMANCE section (unused, duplicates OPTIMIZATION_THRESHOLDS)
    if "PERFORMANCE" in options:
        del options["PERFORMANCE"]
        dirty = True

    # 5) Remove orphan COLORS entries (BACKGROUND/FONT/ACCENT outside THEMES)
    for orphan_key in ("BACKGROUND", "FONT", "ACCENT"):
        if orphan_key in colors:
            del colors[orphan_key]
            dirty = True

    return dirty


def get_fallback_config():
    """
    Return a deep copy of the fallback configuration.

    This is used when all configuration files fail to load.
    The plugin will continue to work with minimal/default settings.

    Returns:
        dict: A copy of FALLBACK_CONFIG
    """
    import copy
    return copy.deepcopy(FALLBACK_CONFIG)


def merge(a, b, path=None):
    "merges b into a"
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value

        else:
            a[key] = b[key]
    return a


def init_env_vars():
    """
    Initialize environment variables and configuration paths.

    Now reads config.json from PLUGIN_CONFIG_DIRECTORY (same as SQLite database)
    instead of the plugin directory. If config.json doesn't exist there,
    copies config.default.json from the plugin directory.

    Automatically detects and migrates/resets obsolete configurations.
    """
    from qgis.core import QgsMessageLog

    PROJECT = QgsProject.instance()
    PLATFORM = sys.platform

    # Plugin directory (where config.default.json is located)
    DIR_CONFIG = os.path.normpath(os.path.dirname(__file__))
    PATH_ABSOLUTE_PROJECT = os.path.normpath(PROJECT.readPath("./"))
    if PATH_ABSOLUTE_PROJECT == './':
        if PLATFORM.startswith('win'):
            PATH_ABSOLUTE_PROJECT = os.path.normpath(os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop'))
        else:
            PATH_ABSOLUTE_PROJECT = os.path.normpath(os.environ['HOME'])

    QGIS_SETTINGS_PATH = QgsApplication.qgisSettingsDirPath()
    # Remove trailing separator if present
    QGIS_SETTINGS_PATH = QGIS_SETTINGS_PATH.rstrip(os.sep).rstrip('/')

    # Start with default PLUGIN_CONFIG_DIRECTORY
    PLUGIN_CONFIG_DIRECTORY = os.path.normpath(os.path.join(QGIS_SETTINGS_PATH, 'FilterMate'))

    # Create the plugin config directory if it doesn't exist
    if not os.path.isdir(PLUGIN_CONFIG_DIRECTORY):
        try:
            os.makedirs(PLUGIN_CONFIG_DIRECTORY, exist_ok=True)
            QgsMessageLog.logMessage(
                f"Created plugin config directory: {PLUGIN_CONFIG_DIRECTORY}",
                "FilterMate",
                Qgis.MessageLevel.Info
            )
        except OSError as error:
            QgsMessageLog.logMessage(
                f"Could not create config directory {PLUGIN_CONFIG_DIRECTORY}: {error}",
                "FilterMate",
                Qgis.MessageLevel.Critical
            )

    # Path to config.json in PLUGIN_CONFIG_DIRECTORY
    config_json_path = os.path.join(PLUGIN_CONFIG_DIRECTORY, 'config.json')
    config_default_path = os.path.join(DIR_CONFIG, 'config.default.json')

    # If config.json doesn't exist in PLUGIN_CONFIG_DIRECTORY, copy default first
    if not os.path.exists(config_json_path):
        try:
            import shutil
            shutil.copy2(config_default_path, config_json_path)
            QgsMessageLog.logMessage(
                "FilterMate: Configuration created with default values",
                "FilterMate",
                Qgis.MessageLevel.Info
            )
        except Exception as e:
            QgsMessageLog.logMessage(
                f"FilterMate: Cannot copy default configuration: {e}",
                "FilterMate",
                Qgis.MessageLevel.Warning
            )
            # Fallback: use config.json from plugin directory
            config_json_path = os.path.join(DIR_CONFIG, 'config.json')

    # Load configuration
    CONFIG_DATA = None
    using_fallback = False

    try:
        with open(config_json_path) as f:
            CONFIG_DATA = json.load(f)

        # v4.0.7: Validate configuration after loading
        try:
            from .config_validator import validate_and_log
            validate_and_log(CONFIG_DATA, DIR_CONFIG)
        except ImportError:
            pass  # Validator not available, skip validation
        except Exception as validation_error:
            QgsMessageLog.logMessage(
                f"FilterMate: Configuration validation skipped: {validation_error}",
                "FilterMate",
                Qgis.MessageLevel.Info
            )

        # v4.7: Migrate config structure (add _hidden, _display_name, remove dead sections)
        try:
            with open(config_default_path, 'r', encoding='utf-8') as f:
                default_data = json.load(f)
            if _migrate_config(CONFIG_DATA, default_data):
                with open(config_json_path, 'w', encoding='utf-8') as f:
                    json.dump(CONFIG_DATA, f, indent=4, ensure_ascii=False)
                QgsMessageLog.logMessage(
                    "FilterMate: Configuration migrated to latest structure",
                    "FilterMate",
                    Qgis.MessageLevel.Info
                )
        except Exception as mig_err:
            QgsMessageLog.logMessage(
                f"FilterMate: Config migration skipped: {mig_err}",
                "FilterMate",
                Qgis.MessageLevel.Info
            )

    except Exception as e:
        QgsMessageLog.logMessage(
            f"Failed to load config from {config_json_path}: {e}",
            "FilterMate",
            Qgis.MessageLevel.Warning
        )
        # Try to load default config as second option
        try:
            with open(config_default_path) as f:
                CONFIG_DATA = json.load(f)
            QgsMessageLog.logMessage(
                "FilterMate: Loaded default configuration file",
                "FilterMate",
                Qgis.MessageLevel.Info
            )
        except Exception as e2:
            QgsMessageLog.logMessage(
                f"Failed to load default config: {e2}. Using in-memory fallback configuration.",
                "FilterMate",
                Qgis.MessageLevel.Warning
            )
            # Ultimate fallback: use hardcoded minimal config
            CONFIG_DATA = get_fallback_config()
            using_fallback = True

    # Validate that CONFIG_DATA has the expected structure
    # Support both uppercase (config.default.json) and lowercase (migrated config.json) keys
    has_app_config = isinstance(CONFIG_DATA, dict) and ("APP" in CONFIG_DATA or "app" in CONFIG_DATA)
    if not has_app_config:
        QgsMessageLog.logMessage(
            "FilterMate: Invalid configuration detected, using fallback configuration",
            "FilterMate",
            Qgis.MessageLevel.Warning
        )
        # Use hardcoded fallback instead of raising
        CONFIG_DATA = get_fallback_config()
        using_fallback = True

        # Try to write fallback to disk for next time
        try:
            with open(config_json_path, 'w') as outfile:
                outfile.write(json.dumps(CONFIG_DATA, indent=4))
            QgsMessageLog.logMessage(
                f"FilterMate: Fallback configuration saved: {config_json_path}",
                "FilterMate",
                Qgis.MessageLevel.Info
            )
        except Exception as e:
            QgsMessageLog.logMessage(
                f"FilterMate: Cannot save fallback configuration: {e}",
                "FilterMate",
                Qgis.MessageLevel.Warning
            )

    # Log if using fallback configuration
    if using_fallback:
        QgsMessageLog.logMessage(
            "FilterMate: Plugin started with fallback configuration. "
            "Some settings may be reset to default values.",
            "FilterMate",
            Qgis.MessageLevel.Warning
        )

    # Ensure OPTIONS exists in APP (support both uppercase and lowercase keys)
    app_key = "APP" if "APP" in CONFIG_DATA else "app"
    if app_key not in CONFIG_DATA:
        CONFIG_DATA[app_key] = {}
    if "OPTIONS" not in CONFIG_DATA.get(app_key, {}):
        CONFIG_DATA[app_key]["OPTIONS"] = {
            "APP_SQLITE_PATH": {"value": "", "description": "Directory for SQLite databases"},
            "FRESH_RELOAD_FLAG": {"value": False, "description": "Force fresh reload on next startup"}
        }

    # Validate APP_SQLITE_PATH from config
    app_sqlite_path = _get_option_value(
        CONFIG_DATA.get(app_key, {}).get("OPTIONS", {}).get("APP_SQLITE_PATH"), ""
    )
    if app_sqlite_path != '':
        configured_path = os.path.normpath(app_sqlite_path)

        # Validate that parent directories exist and are accessible
        parent_dir = os.path.dirname(configured_path)
        path_is_valid = False

        if parent_dir and os.path.exists(parent_dir):
            # Check if parent directory is accessible
            try:
                if os.access(parent_dir, os.W_OK):
                    path_is_valid = True
                else:
                    QgsMessageLog.logMessage(
                        f"Configured path parent directory is not writable: {parent_dir}. Using default profile.",
                        "FilterMate",
                        Qgis.MessageLevel.Warning
                    )
            except Exception as e:
                QgsMessageLog.logMessage(
                    f"Cannot access configured path: {configured_path}. Error: {e}. Using default profile.",
                    "FilterMate",
                    Qgis.MessageLevel.Warning
                )
        else:
            QgsMessageLog.logMessage(
                f"Configured path parent directory does not exist: {parent_dir}. Using default profile.",
                "FilterMate",
                Qgis.MessageLevel.Warning
            )

        if path_is_valid:
            PLUGIN_CONFIG_DIRECTORY = configured_path
            # Update config_json_path if directory changed
            config_json_path = os.path.join(PLUGIN_CONFIG_DIRECTORY, 'config.json')

    # Auto-migrate sducournau → imagodata URLs (v4.5.1 org migration)
    options = CONFIG_DATA.get(app_key, {}).get("OPTIONS", {})
    config_dirty = False
    for key in ("GITHUB_PAGE", "GITHUB_REPOSITORY", "DISCORD_INVITE", "QGIS_PLUGIN_REPOSITORY"):
        val = _get_option_value(options.get(key), "")
        if "sducournau" in val:
            _set_option_value(options, key, val.replace("sducournau", "imagodata"))
            config_dirty = True
    github_page_val = _get_option_value(options.get("GITHUB_PAGE"), "")
    if not github_page_val.endswith("index.html"):
        _set_option_value(options, "GITHUB_PAGE", "https://imagodata.github.io/filter_mate/index.html")
        config_dirty = True

    # Update APP_SQLITE_PATH in config if needed
    current_sqlite_path = _get_option_value(
        CONFIG_DATA.get(app_key, {}).get("OPTIONS", {}).get("APP_SQLITE_PATH"), ""
    )
    if current_sqlite_path != PLUGIN_CONFIG_DIRECTORY:
        _set_option_value(CONFIG_DATA[app_key]["OPTIONS"], "APP_SQLITE_PATH", PLUGIN_CONFIG_DIRECTORY)
        config_dirty = True

    if config_dirty:
        try:
            with open(config_json_path, 'w') as outfile:
                outfile.write(json.dumps(CONFIG_DATA, indent=4))
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Could not update config.json: {e}",
                "FilterMate",
                Qgis.MessageLevel.Warning
            )

    global ENV_VARS
    ENV_VARS["PROJECT"] = PROJECT
    ENV_VARS["PLATFORM"] = PLATFORM
    ENV_VARS["DIR_CONFIG"] = DIR_CONFIG
    ENV_VARS["PATH_ABSOLUTE_PROJECT"] = PATH_ABSOLUTE_PROJECT
    ENV_VARS["CONFIG_DATA"] = CONFIG_DATA
    ENV_VARS["QGIS_SETTINGS_PATH"] = QGIS_SETTINGS_PATH
    ENV_VARS["PLUGIN_CONFIG_DIRECTORY"] = PLUGIN_CONFIG_DIRECTORY
    ENV_VARS["CONFIG_JSON_PATH"] = config_json_path  # Store active config path


def reset_config_to_default():
    """
    Reset configuration to default by copying config.default.json
    to the active config location (PLUGIN_CONFIG_DIRECTORY/config.json).

    Use this when reinitializing the config and SQLite database.

    Returns:
        bool: True if reset successful, False otherwise
    """
    try:
        import shutil

        if "DIR_CONFIG" not in ENV_VARS or "CONFIG_JSON_PATH" not in ENV_VARS:
            QgsMessageLog.logMessage(
                "Environment variables not initialized. Call init_env_vars() first.",
                "FilterMate",
                Qgis.MessageLevel.Critical
            )
            return False

        config_default_path = os.path.join(ENV_VARS["DIR_CONFIG"], 'config.default.json')
        config_json_path = ENV_VARS["CONFIG_JSON_PATH"]

        # Backup existing config if it exists
        if os.path.exists(config_json_path):
            backup_path = config_json_path + '.backup'
            shutil.copy2(config_json_path, backup_path)
            QgsMessageLog.logMessage(
                f"Backed up existing config to: {backup_path}",
                "FilterMate",
                Qgis.MessageLevel.Info
            )

        # Copy default config
        shutil.copy2(config_default_path, config_json_path)

        # Reload config
        with open(config_json_path) as f:
            ENV_VARS["CONFIG_DATA"] = json.load(f)

        QgsMessageLog.logMessage(
            f"Configuration reset to default: {config_json_path}",
            "FilterMate",
            Qgis.MessageLevel.Info
        )

        return True

    except Exception as e:
        QgsMessageLog.logMessage(
            f"Failed to reset configuration: {e}",
            "FilterMate",
            Qgis.MessageLevel.Critical
        )
        return False


def reload_config():
    """
    Reload configuration from config.json file.

    Use this to apply configuration changes without restarting QGIS.
    Updates ENV_VARS['CONFIG_DATA'] with latest values from disk.

    If environment variables are not initialized, calls init_env_vars() first.

    Returns:
        bool: True if reload successful, False otherwise
    """
    global ENV_VARS

    try:
        config_json_path = ENV_VARS.get("CONFIG_JSON_PATH")

        # If CONFIG_JSON_PATH not set, initialize environment first
        if not config_json_path:
            init_env_vars()
            config_json_path = ENV_VARS.get("CONFIG_JSON_PATH")

        if not config_json_path or not os.path.exists(config_json_path):
            QgsMessageLog.logMessage(
                f"Config file not found: {config_json_path}",
                "FilterMate",
                Qgis.MessageLevel.Warning
            )
            return False

        with open(config_json_path, 'r', encoding='utf-8') as f:
            new_config = json.load(f)

        ENV_VARS["CONFIG_DATA"] = new_config

        QgsMessageLog.logMessage(
            f"Configuration reloaded from: {config_json_path}",
            "FilterMate",
            Qgis.MessageLevel.Info  # DEBUG
        )

        return True

    except Exception as e:
        QgsMessageLog.logMessage(
            f"Failed to reload configuration: {e}",
            "FilterMate",
            Qgis.MessageLevel.Critical
        )
        return False
