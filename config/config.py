from qgis.core import QgsApplication, QgsProject, QgsMessageLog, Qgis
import copy
import os
import sys
import json

# Re-export get_optimization_thresholds for backward compatibility
# Function was moved to core.optimization.config_provider in EPIC-1 Phase E7.5
from ..core.optimization.config_provider import get_optimization_thresholds  # noqa: F401
from ..core.domain.project_folder import project_folder

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
        "USER_IDENTITY": {
            "value": "",
            "description": "Identity string stamped on new favorites (cascade: this → qgis/userName → OS user)"
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
                    "value": "auto",
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
            },
            # On, as in config.default.json: without them the fallback turned
            # raster and point cloud layers off.
            "RASTER": {
                "enabled": {
                    "value": True,
                    "choices": [True, False],
                    "description": "Show raster layers in the layer lists"
                }
            },
            "POINT_CLOUD": {
                "enabled": {
                    "value": True,
                    "choices": [True, False],
                    "description": "Show point cloud layers in the layer lists"
                }
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
    # Extension config namespace is populated at runtime by the
    # ExtensionRegistry from each extension's config_schema(). Keeping an
    # empty container here avoids drift with per-extension defaults.
    "EXTENSIONS": {}
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


_FALSE_STRINGS = frozenset({'false', '0', 'no', 'off', ''})
_TRUE_STRINGS = frozenset({'true', '1', 'yes', 'on'})


def _get_option_bool(option, default=False):
    """Boolean value of a config option, tolerant of a hand-edited config.json.

    ``bool("false")`` is True: "false", "0", "no", "off" and "" (any case)
    read as False, "true", "1", "yes", "on" as True; another string, or no
    value, gives ``default``.
    """
    value = _get_option_value(option, default)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in _FALSE_STRINGS:
            return False
        if text in _TRUE_STRINGS:
            return True
        return bool(default)
    if value is None:
        return bool(default)
    return bool(value)


def _get_option_int(option, default=0):
    """Integer value of a config option: 4000000, "4000000" or 4e6 are read,
    anything else (text, a boolean, no value) gives ``default``."""
    value = _get_option_value(option, default)
    if isinstance(value, bool) or value is None:
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError, OverflowError):
            return int(default)


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


# Schema-owned metadata fields that must follow the reference (template /
# extension schema), not the user's frozen copy. ``value`` is intentionally
# excluded — that is the user's data and is preserved across migrations.
_METADATA_KEYS = frozenset({
    "description",
    "choices",
    "min",
    "max",
    "applies_to",
    "_hidden",
    "_display_name",
})


def _sync_metadata(user, ref):
    """Overlay schema-owned metadata fields from ``ref`` into ``user``.

    ``merge()`` only adds keys missing from ``user`` — it never refreshes
    metadata on keys the user already has. So when a developer updates a
    description / choices / _hidden flag in ``config.default.json`` (or in
    an extension's ``config_schema()``), the user's copy keeps the stale
    text and the Configuration panel displays out-of-date tooltips,
    visibilities, and dropdown options.

    This function recurses through ``ref``, copying every metadata field
    listed in ``_METADATA_KEYS`` into ``user`` while leaving ``value`` (and
    any user-only fields) untouched. Recursion stops at ``value`` because
    its content is user data, not config structure.

    Args:
        user: The dict to refresh in place.
        ref: The schema/template dict (read-only).

    Returns:
        bool: True if any metadata field was updated.
    """
    if not (isinstance(user, dict) and isinstance(ref, dict)):
        return False
    dirty = False
    for key, ref_val in ref.items():
        if key == "value":
            continue
        if key in _METADATA_KEYS:
            if user.get(key) != ref_val:
                user[key] = ref_val
                dirty = True
            continue
        if isinstance(ref_val, dict) and isinstance(user.get(key), dict):
            if _sync_metadata(user[key], ref_val):
                dirty = True
    return dirty


def _migrate_config(config_data, default_data):
    """Migrate user config to latest structure.

    Merges new keys from default, refreshes schema-owned metadata,
    adds _hidden/_display_name metadata, and removes deprecated
    sections. Safe to call on already-migrated configs.

    Args:
        config_data: User's current config dict (modified in place)
        default_data: Default config dict (read-only reference)

    Returns:
        True if any changes were made, False otherwise
    """
    dirty = False

    # 0) FilterMate 5: raster and point cloud layers are on by default. A config
    # written before 5.0 (no RASTER section yet) still holds the off default of
    # the 4.x experimental point cloud flag: turn it on once. Afterwards the
    # RASTER section exists and the Configuration panel decides.
    def _options(data):
        app_section = data.get("APP") if isinstance(data, dict) else None
        return app_section.get("OPTIONS") if isinstance(app_section, dict) else None

    user_options, default_options = _options(config_data), _options(default_data)
    if (isinstance(user_options, dict) and isinstance(default_options, dict)
            and "RASTER" in default_options and "RASTER" not in user_options):
        point_cloud = user_options.get("POINT_CLOUD")
        if isinstance(point_cloud, dict):
            enabled = point_cloud.get("enabled")
            if isinstance(enabled, dict) and enabled.get("value") is False:
                enabled["value"] = True
                dirty = True
            elif enabled is False:
                point_cloud["enabled"] = True
                dirty = True

    # 1) Merge new keys from default into user config (recursive, non-destructive)
    if _merge_missing_keys(config_data, default_data):
        dirty = True

    # 1b) Refresh schema-owned metadata (description, choices, _hidden, …) so
    # the Configuration panel reflects the current template, not whatever
    # text the user's frozen copy still carries from an older release.
    if _sync_metadata(config_data, default_data):
        dirty = True

    def _section(parent, key):
        value = parent.get(key) if isinstance(parent, dict) else None
        return value if isinstance(value, dict) else {}

    app = _section(config_data, "APP")
    dockwidget = _section(app, "DOCKWIDGET")
    options = _section(app, "OPTIONS")
    colors = _section(dockwidget, "COLORS")

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

    # 6) EXTENSIONS root: strip legacy placeholder metadata that older
    # releases injected when the section was empty. The registry now
    # seeds real extension namespaces (qfieldcloud, favorites_sharing,
    # …) under EXTENSIONS, so the root must be visible in the
    # Configuration panel — `_hidden: true` from older defaults would
    # collapse the whole branch. The root-level `description` field
    # rendered as a confusing string child once the parent unhid; keep
    # the user-facing label only.
    extensions = config_data.get("EXTENSIONS")
    if isinstance(extensions, dict):
        if extensions.pop("_hidden", None) is not None:
            dirty = True
        if "description" in extensions and not isinstance(extensions["description"], dict):
            del extensions["description"]
            dirty = True
        if extensions.get("_display_name") != "Extensions":
            extensions["_display_name"] = "Extensions"
            dirty = True

    # 7) AUTO_OPTIMIZATION.enabled / auto_centroid_for_distant: nothing reads them since the
    # auto-optimization confirmation flow was removed (the dock keeps its own per-project switches).
    auto_optimization = _section(options, "AUTO_OPTIMIZATION")
    for dead_key in ("enabled", "auto_centroid_for_distant"):
        if dead_key in auto_optimization:
            del auto_optimization[dead_key]
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


def _merge_missing_keys(a, b):
    """Recursively add keys present in ``b`` but missing from ``a``.

    Existing keys in ``a`` are never overwritten; nested dicts are merged
    in place. Added subtrees are deep-copied so ``a`` never aliases ``b``.

    Args:
        a: Destination dict (modified in place).
        b: Reference dict (read-only).

    Returns:
        bool: True if at least one key was added to ``a``.
    """
    if not (isinstance(a, dict) and isinstance(b, dict)):
        return False
    added = False
    for key, ref_val in b.items():
        if key not in a:
            a[key] = copy.deepcopy(ref_val)
            added = True
        elif isinstance(a[key], dict) and isinstance(ref_val, dict):
            if _merge_missing_keys(a[key], ref_val):
                added = True
    return added


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


def get_config_json_path():
    """Path of the active config.json, without writing anything.

    ENV_VARS["CONFIG_JSON_PATH"] once init_env_vars() ran; before that (the
    plugin constructor reads the forced language there), the path
    init_env_vars() will settle on: config.json in the FilterMate folder of
    the QGIS profile, or in the folder its APP.OPTIONS.APP_SQLITE_PATH names
    (e.g. a QGIS 4 profile sharing the QGIS 3 FilterMate folder). The
    Configuration tab saves there; reading the profile copy instead brought
    back a stale language at every start. The copy in the plugin folder is
    only a fallback.
    """
    path = ENV_VARS.get("CONFIG_JSON_PATH")
    if path:
        return path
    settings_path = QgsApplication.qgisSettingsDirPath().rstrip(os.sep).rstrip('/')
    profile_json = os.path.join(os.path.normpath(os.path.join(settings_path, 'FilterMate')), 'config.json')
    configured = _configured_config_directory(profile_json)
    return os.path.join(configured, 'config.json') if configured else profile_json


def _configured_config_directory(config_json_path):
    """Folder named by APP.OPTIONS.APP_SQLITE_PATH in config_json_path, if init_env_vars() would use it.

    Same test as init_env_vars(): its parent folder exists and is writable.
    None when the file is missing or unreadable, or the option is empty or unusable.
    """
    try:
        with open(config_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        app = data.get("APP") if isinstance(data.get("APP"), dict) else data.get("app")
        value = _get_option_value(app.get("OPTIONS", {}).get("APP_SQLITE_PATH"), "")
    except (OSError, ValueError, AttributeError):
        return None
    if not isinstance(value, str) or not value:
        return None
    configured = os.path.normpath(value)
    parent = os.path.dirname(configured)
    if parent and os.path.exists(parent) and os.access(parent, os.W_OK):
        return configured
    return None


def _write_config_json(path, data):
    """Write config.json atomically (temp file + replace), UTF-8.

    A crash or a full disk in the middle of ``open(path, 'w')`` left a
    truncated file that the next start replaced with the defaults.
    """
    try:
        # Imported here: infrastructure.utils imports this module at load time
        from filter_mate.infrastructure.utils.atomic_io import atomic_json_write
    except ImportError as error:
        QgsMessageLog.logMessage(
            f"FilterMate: atomic helper unavailable ({error}); config.json written with a local temp file",
            "FilterMate",
            Qgis.MessageLevel.Warning
        )
        import tempfile
        text = json.dumps(data, indent=4, ensure_ascii=False)
        fd, tmp_path = tempfile.mkstemp(prefix=".fm_", suffix=".tmp", dir=os.path.dirname(os.path.abspath(path)))
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as outfile:
                outfile.write(text)
            os.replace(tmp_path, path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        return
    atomic_json_write(path, data, indent=4)


def _keep_unreadable_config(path, reason):
    """Copy a config.json that cannot be used before the defaults replace it.

    Args:
        path: The config.json that failed to load.
        reason: Why (shown in the QGIS message log).
    """
    try:
        from filter_mate.infrastructure.utils.atomic_io import backup_corrupt_file
    except ImportError as error:
        QgsMessageLog.logMessage(
            f"FilterMate: {path} cannot be used ({reason}) and could not be kept ({error}); "
            "default settings are used.",
            "FilterMate",
            Qgis.MessageLevel.Warning
        )
        return
    backup = backup_corrupt_file(path)
    if backup:
        QgsMessageLog.logMessage(
            f"FilterMate: {path} cannot be used ({reason}). Your file was kept as {backup}; "
            "default settings are used.",
            "FilterMate",
            Qgis.MessageLevel.Warning
        )


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
    # An unsaved project has no folder: Desktop (Windows) / home (core.domain.project_folder)
    PATH_ABSOLUTE_PROJECT = project_folder(PROJECT.readPath("./"), windows=PLATFORM.startswith('win'))

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
        with open(config_json_path, 'r', encoding='utf-8') as f:
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
                _write_config_json(config_json_path, CONFIG_DATA)
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
        # The defaults below are written over this file by the next save: keep a copy
        _keep_unreadable_config(config_json_path, str(e))
        # Try to load default config as second option
        try:
            with open(config_default_path, 'r', encoding='utf-8') as f:
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
        _keep_unreadable_config(config_json_path, "no APP section")
        CONFIG_DATA = get_fallback_config()
        using_fallback = True

        # Try to write fallback to disk for next time
        try:
            _write_config_json(config_json_path, CONFIG_DATA)
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

    # Passwords an older version saved here (the URI of a PostgreSQL layer): mask them once
    try:
        from filter_mate.infrastructure.logging.redaction import scrub_secrets_in_place
        scrubbed = scrub_secrets_in_place(CONFIG_DATA)
    except ImportError:
        scrubbed = 0
    if scrubbed:
        config_dirty = True
        QgsMessageLog.logMessage(
            f"FilterMate: masked {scrubbed} saved connection password(s) in {config_json_path}",
            "FilterMate",
            Qgis.MessageLevel.Info
        )
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
            _write_config_json(config_json_path, CONFIG_DATA)
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
        with open(config_json_path, 'r', encoding='utf-8') as f:
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

    FIX 2026-04-27: previously did ``ENV_VARS["CONFIG_DATA"] = new_config``
    which orphans every reference held elsewhere (``app.CONFIG_DATA``,
    ``dockwidget.CONFIG_DATA``, the extension registry's seed mutations).
    The next persist write would then drop in-memory seeded keys
    (e.g. ``EXTENSIONS.favorites_sharing``) because they only existed on
    the orphaned dict. Same anti-pattern that the registry's
    ``_persist_config`` had to fix on 2026-04-23. We now mutate in place:
    clear + update the existing dict so live references see the new state.

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

        live = ENV_VARS.get("CONFIG_DATA")
        if isinstance(live, dict):
            # Mutate in place: clear + repopulate so every holder of the
            # live reference (app.CONFIG_DATA, dockwidget.CONFIG_DATA,
            # registry-seeded EXTENSIONS sub-dicts) sees the new state
            # without losing pre-existing in-memory mutations that the
            # registry just seeded but hasn't persisted yet.
            existing_extensions = live.get("EXTENSIONS")
            live.clear()
            live.update(new_config)
            # Preserve any extension keys the registry just seeded which
            # haven't reached disk yet — disk wins for keys both sides
            # have, but in-memory-only keys survive the reload.
            if isinstance(existing_extensions, dict):
                merged = dict(live.get("EXTENSIONS", {}) or {})
                for ext_id, slice_data in existing_extensions.items():
                    if ext_id not in merged:
                        merged[ext_id] = slice_data
                live["EXTENSIONS"] = merged
        else:
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
