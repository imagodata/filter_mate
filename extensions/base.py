# -*- coding: utf-8 -*-
"""
Base Extension Class for FilterMate Extension System.

All FilterMate extensions must inherit from BaseExtension and implement
the required lifecycle methods. Extensions are optional modules that
add functionality without modifying the core plugin.

Lifecycle:
    1. __init__()          - Extension instantiated (no QGIS deps yet)
    2. check_dependencies() - Verify required packages are available
    3. initialize(iface)   - Set up services, adapters, register actions
    4. create_ui(toolbar)  - Add toolbar buttons and menu entries
    5. teardown()          - Cleanup on plugin unload

Thread safety: Extensions run on the main thread unless they use QgsTask.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger('FilterMate.Extensions')

# Base config keys every extension gets for free (merged with extension schema).
# Keeping them here means the config UI can show them consistently without each
# extension re-declaring enabled/dismiss_missing_deps_warning.
_COMMON_CONFIG_SCHEMA: Dict[str, Dict[str, Any]] = {
    "enabled": {
        "value": True,
        "choices": [True, False],
        "description": "Enable/disable this extension. When disabled, it is not initialized at plugin startup.",
    },
    "dismiss_missing_deps_warning": {
        "value": False,
        "choices": [True, False],
        "description": "Do not show the missing-dependencies warning dialog for this extension.",
    },
}


class ExtensionState(Enum):
    """Extension lifecycle state."""
    UNLOADED = "unloaded"
    DEPENDENCIES_CHECKED = "dependencies_checked"
    INITIALIZED = "initialized"
    UI_CREATED = "ui_created"
    ERROR = "error"
    TORN_DOWN = "torn_down"


@dataclass(frozen=True)
class ExtensionMetadata:
    """Metadata describing an extension."""
    id: str
    name: str
    version: str
    description: str
    author: str = ""
    min_qgis_version: str = "3.28"
    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: List[str] = field(default_factory=list)
    icon_name: str = ""


class BaseExtension(ABC):
    """
    Abstract base class for FilterMate extensions.

    Extensions add optional functionality to FilterMate without
    modifying core code. They follow the hexagonal architecture:
    - Services go in the extension's own namespace
    - Ports/adapters follow the same pattern as core FilterMate
    - UI integrates via toolbar actions and dialogs

    Subclasses must implement:
        - metadata (property)
        - check_dependencies()
        - initialize(iface)
        - teardown()

    Optional overrides:
        - create_ui(toolbar, menu)
        - get_service(name)
        - on_project_loaded()
        - on_project_closed()
    """

    def __init__(self):
        self._state = ExtensionState.UNLOADED
        self._error_message: Optional[str] = None
        self._services: Dict[str, Any] = {}
        self._actions: list = []

    @property
    @abstractmethod
    def metadata(self) -> ExtensionMetadata:
        """Return extension metadata."""
        ...

    @property
    def state(self) -> ExtensionState:
        """Current extension state."""
        return self._state

    @property
    def error_message(self) -> Optional[str]:
        """Error message if state is ERROR."""
        return self._error_message

    def is_available(self) -> bool:
        """Check if extension dependencies are met and it can be used."""
        if self._state == ExtensionState.UNLOADED:
            try:
                available = self.check_dependencies()
                if available:
                    self._state = ExtensionState.DEPENDENCIES_CHECKED
                return available
            except Exception as e:
                self._state = ExtensionState.ERROR
                self._error_message = str(e)
                return False
        return self._state not in (ExtensionState.ERROR, ExtensionState.TORN_DOWN)

    @abstractmethod
    def check_dependencies(self) -> bool:
        """
        Check if required dependencies are available.

        Returns True if all required packages can be imported.
        Should NOT raise exceptions — return False instead.
        """
        ...

    @abstractmethod
    def initialize(self, iface: Any) -> None:
        """
        Initialize extension services and adapters.

        Called after check_dependencies() returns True.
        Set up services, create adapters, register with DI container.

        Args:
            iface: QGIS interface instance
        """
        ...

    def missing_deps_hint(self) -> Dict[str, str]:
        """
        Actionable install hint surfaced when ``check_dependencies()`` fails.

        Override when the dependency is something other than a PyPI
        package — e.g. a QGIS plugin (installed via the Plugin Manager,
        not pip) or a system library. The registry's missing-deps dialog
        reads these fields instead of hard-coding "pip install …", so
        users get correct instructions.

        Returns:
            dict with keys:
              - ``method``: one of ``'pip'`` (default), ``'qgis_plugin'``,
                ``'manual'`` — drives the icon/wording in the dialog.
              - ``install_command``: exact string to display (e.g.
                ``'pip install qfieldcloud-sdk'`` or
                ``'Extensions → Installer/Gérer les extensions → Resource Sharing'``).
              - ``details``: optional extra context (URL, caveats…).
        """
        deps = ", ".join(self.metadata.dependencies) if self.metadata.dependencies else "?"
        return {
            "method": "pip",
            "install_command": f"pip install {deps}",
            "details": "",
        }

    def create_ui(self, toolbar: Any, menu_name: str) -> List[Any]:
        """
        Create UI elements (toolbar buttons, menu entries).

        Override to add toolbar actions. Return list of QActions created.

        Args:
            toolbar: QGIS toolbar to add actions to
            menu_name: Menu name for menu entries

        Returns:
            List of QAction instances created
        """
        return []

    def create_dockwidget_ui(self, dockwidget: Any) -> List[Any]:
        """
        Create UI elements inside the FilterMate dockwidget.

        Override to inject buttons/widgets into the dockwidget (e.g.,
        next to the export button in the action bar). Called after the
        dockwidget is created and shown.

        Args:
            dockwidget: FilterMate dockwidget instance

        Returns:
            List of QWidget instances created
        """
        return []

    @abstractmethod
    def teardown(self) -> None:
        """
        Cleanup extension resources.

        Called when FilterMate plugin is unloaded.
        Must release all resources, disconnect signals, remove UI elements.
        """
        ...

    def get_service(self, name: str) -> Optional[Any]:
        """
        Get a named service from this extension.

        Args:
            name: Service name (e.g., 'push', 'credentials', 'adapter')

        Returns:
            Service instance or None if not found
        """
        return self._services.get(name)

    def register_service(self, name: str, service: Any) -> None:
        """Register a service by name."""
        self._services[name] = service

    # ------------------------------------------------------------------
    # Configuration API
    # ------------------------------------------------------------------
    # All extensions share the same config namespace:
    #   ENV_VARS.CONFIG_DATA["EXTENSIONS"][<ext_id>][<key>] = {"value": ..., ...}
    # Extensions declare their own keys via config_schema(); the registry
    # seeds missing keys on discovery so config.default.json never needs to
    # be edited when an extension adds an option.

    def config_schema(self) -> Dict[str, Dict[str, Any]]:
        """
        Return the extension-specific config schema.

        Override to declare the keys this extension reads/writes under
        ``EXTENSIONS.<ext_id>`` in FilterMate's config.json. Every entry
        must be a dict with at least a ``value`` key (the default) plus an
        optional ``description``, ``choices``, ``min``, ``max`` etc. —
        same wrapped format as the rest of FilterMate's config.

        The ``enabled`` and ``dismiss_missing_deps_warning`` keys are
        injected automatically (see ``full_config_schema``) — do not
        re-declare them here unless you need to override the defaults.

        Returns:
            dict: ``{key: option_dict}`` — empty by default.
        """
        return {}

    def full_config_schema(self) -> Dict[str, Dict[str, Any]]:
        """
        Return the complete schema (common keys + extension-specific keys).

        The registry uses this to auto-seed missing keys in config.json.
        Subclasses should override ``config_schema()`` (not this method)
        to add their own options.
        """
        merged: Dict[str, Dict[str, Any]] = {}
        for key, opt in _COMMON_CONFIG_SCHEMA.items():
            merged[key] = dict(opt)  # shallow copy so overrides don't mutate global
        for key, opt in self.config_schema().items():
            merged[key] = dict(opt)
        return merged

    def _get_extension_config_dict(self) -> Dict[str, Any]:
        """
        Return the raw config dict for this extension (``EXTENSIONS.<id>``).

        Creates the nested structure on demand if absent — callers can
        safely mutate the returned dict and persist via ``_persist_config()``.
        """
        try:
            from filter_mate.config.config import ENV_VARS
        except Exception:
            return {}
        config_data = ENV_VARS.get("CONFIG_DATA")
        if not isinstance(config_data, dict):
            return {}
        extensions = config_data.setdefault("EXTENSIONS", {})
        if not isinstance(extensions, dict):
            return {}
        ext_cfg = extensions.setdefault(self.metadata.id, {})
        return ext_cfg if isinstance(ext_cfg, dict) else {}

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Read a value from the extension's config namespace.

        Handles both wrapped (``{"value": X}``) and raw formats, mirroring
        ``config._get_option_value``. Missing keys return ``default``.

        Args:
            key: Config key under ``EXTENSIONS.<ext_id>``.
            default: Fallback when the key is absent or unreadable.
                    If omitted, falls back to the schema's default ``value``.
        """
        cfg = self._get_extension_config_dict()
        if key in cfg:
            try:
                from filter_mate.config.config import _get_option_value
            except Exception:
                raw = cfg[key]
                if isinstance(raw, dict) and "value" in raw:
                    return raw["value"]
                return raw
            return _get_option_value(cfg.get(key), default=default)

        # Fallback to schema-declared default when caller didn't force one.
        if default is None:
            schema = self.full_config_schema()
            if key in schema:
                return schema[key].get("value")
        return default

    def set_config(self, key: str, value: Any, *, persist: bool = True) -> bool:
        """
        Write a value into the extension's config namespace and persist.

        Preserves the wrapped ``{"value": ..., "description": ...}`` shape
        when the key already exists; otherwise writes a wrapped dict using
        the schema's metadata (description/choices) when available.

        Args:
            key: Config key under ``EXTENSIONS.<ext_id>``.
            value: New value to store.
            persist: If True (default), write config.json to disk.

        Returns:
            True if the write (and optional persist) succeeded.
        """
        cfg = self._get_extension_config_dict()
        if not isinstance(cfg, dict):
            return False

        existing = cfg.get(key)
        if isinstance(existing, dict) and "value" in existing:
            existing["value"] = value
        else:
            schema_entry = self.full_config_schema().get(key, {})
            wrapped: Dict[str, Any] = {"value": value}
            for meta_key in ("description", "choices", "min", "max", "applies_to"):
                if meta_key in schema_entry:
                    wrapped[meta_key] = schema_entry[meta_key]
            cfg[key] = wrapped

        if persist:
            return self._persist_config()
        return True

    def _persist_config(self) -> bool:
        """Write the extension's config back to config.json defensively.

        Uses a read-modify-write pattern: we re-load the on-disk config
        just before writing, overlay *only* this extension's namespace
        (``EXTENSIONS.<ext_id>``) from in-memory state, then write back.

        Rationale: other parts of FilterMate (dockwidget, config
        controller, database manager) may have written a stale snapshot
        of ``CONFIG_DATA`` to disk in between our in-memory mutations
        and this persist. A naive ``json.dump(ENV_VARS['CONFIG_DATA'])``
        would clobber those sibling writes — or, worse, resurrect a
        stale EXTENSIONS section that no longer has our schema.
        """
        try:
            from filter_mate.config.config import ENV_VARS
        except Exception:
            return False
        config_path = ENV_VARS.get("CONFIG_JSON_PATH")
        live_data = ENV_VARS.get("CONFIG_DATA")
        if not config_path or not isinstance(live_data, dict):
            return False

        # In-memory snapshot of just this extension's namespace
        live_extensions = live_data.get("EXTENSIONS", {})
        if not isinstance(live_extensions, dict):
            live_extensions = {}
        our_slice = live_extensions.get(self.metadata.id)
        if not isinstance(our_slice, dict):
            return False  # Nothing to persist

        # Re-read disk just for *sibling* sections we might clobber on
        # write (FIX 2026-04-23: we no longer reassign ENV_VARS['CONFIG_DATA']
        # — see ExtensionRegistry._persist_config for the rationale. Keeping
        # the live dict as the single source of truth means app.CONFIG_DATA
        # and dockwidget.CONFIG_DATA don't desync).
        try:
            with open(config_path, "r", encoding="utf-8") as fh:
                disk_data = json.load(fh)
            if not isinstance(disk_data, dict):
                disk_data = {}
        except (OSError, ValueError):
            disk_data = {}

        # Pull in disk-only sibling sections we haven't touched in memory,
        # so the upcoming write doesn't drop them.
        for key, value in disk_data.items():
            if key == "EXTENSIONS":
                continue
            if key not in live_data:
                live_data[key] = value

        # Ensure EXTENSIONS exists and has our slice written in place.
        existing_ext = live_data.get("EXTENSIONS")
        if not isinstance(existing_ext, dict):
            live_data["EXTENSIONS"] = {}
            existing_ext = live_data["EXTENSIONS"]
        # Also overlay sibling extensions that only exist on disk (e.g.
        # another session seeded them while this session was offline).
        disk_ext = disk_data.get("EXTENSIONS")
        if isinstance(disk_ext, dict):
            for ext_id, slice_data in disk_ext.items():
                if ext_id not in existing_ext and isinstance(slice_data, (dict, str, bool, int, float, list)):
                    existing_ext[ext_id] = slice_data
        existing_ext[self.metadata.id] = our_slice

        try:
            with open(config_path, "w", encoding="utf-8") as fh:
                json.dump(live_data, fh, indent=2, ensure_ascii=False)
            return True
        except OSError as exc:
            logger.warning(
                "Failed to persist config for extension '%s': %s",
                self.metadata.id, exc,
            )
            return False

    # --- Convenience shortcuts for the common keys ---------------------

    def is_enabled(self) -> bool:
        """Return True when the extension is enabled in config."""
        return bool(self.get_config("enabled", default=True))

    def set_enabled(self, enabled: bool) -> bool:
        """Persist enabled/disabled state for this extension."""
        return self.set_config("enabled", bool(enabled))

    def is_warning_dismissed(self) -> bool:
        """Return True when the missing-deps warning was dismissed."""
        return bool(self.get_config("dismiss_missing_deps_warning", default=False))

    def dismiss_warning(self) -> bool:
        """Persist the 'don't show again' flag for the missing-deps warning."""
        return self.set_config("dismiss_missing_deps_warning", True)

    def seed_default_config(self) -> bool:
        """
        Insert any missing schema keys into config.json (idempotent).

        Called by the registry on discovery. Returns True if any key was
        added (caller persists once for all extensions).
        """
        cfg = self._get_extension_config_dict()
        if not isinstance(cfg, dict):
            return False

        dirty = False
        for key, schema_entry in self.full_config_schema().items():
            if key not in cfg:
                cfg[key] = dict(schema_entry)
                dirty = True
        return dirty

    def on_project_loaded(self) -> None:
        """Called when a QGIS project is loaded. Override if needed."""

    def on_project_closed(self) -> None:
        """Called when a QGIS project is closed. Override if needed."""

    def _set_state(self, state: ExtensionState) -> None:
        """Update extension state."""
        self._state = state
        logger.debug(
            "Extension '%s' state: %s", self.metadata.id, state.value
        )

    def _set_error(self, message: str) -> None:
        """Set extension to error state."""
        self._state = ExtensionState.ERROR
        self._error_message = message
        logger.error(
            "Extension '%s' error: %s", self.metadata.id, message
        )
