# -*- coding: utf-8 -*-
"""
Extension Registry for FilterMate.

Discovers, loads, initializes, and manages extension lifecycle.
Extensions are discovered from the `extensions/` directory by looking
for subpackages that define an `Extension` class inheriting BaseExtension.

Usage:
    registry = get_extension_registry()
    registry.discover_extensions()
    registry.initialize_all(iface)

    # Later, on plugin unload:
    registry.teardown_all()
"""

import importlib
import logging
import os
from typing import Any, Dict, List, Optional

from .base import BaseExtension, ExtensionState

logger = logging.getLogger('FilterMate.Extensions.Registry')

_registry_instance: Optional['ExtensionRegistry'] = None


class ExtensionRegistry:
    """
    Registry for discovering and managing FilterMate extensions.

    Extensions are Python subpackages under `extensions/` that expose
    an `Extension` class inheriting from `BaseExtension`.

    The registry handles the full lifecycle:
        discover → check_dependencies → initialize → create_ui → teardown
    """

    def __init__(self):
        self._extensions: Dict[str, BaseExtension] = {}
        self._load_order: List[str] = []
        self._initialized = False

    @property
    def extensions(self) -> Dict[str, BaseExtension]:
        """All registered extensions (keyed by extension ID)."""
        return dict(self._extensions)

    def discover_extensions(self) -> List[str]:
        """
        Discover extensions in the extensions/ directory.

        Scans for subpackages containing a module with an `Extension` class
        that inherits from BaseExtension.

        Returns:
            List of discovered extension IDs
        """
        extensions_dir = os.path.dirname(os.path.abspath(__file__))
        discovered = []

        config_dirty = False
        for entry in sorted(os.listdir(extensions_dir)):
            entry_path = os.path.join(extensions_dir, entry)
            if not os.path.isdir(entry_path):
                continue
            if entry.startswith(('_', '.')):
                continue
            init_file = os.path.join(entry_path, '__init__.py')
            if not os.path.isfile(init_file):
                continue

            try:
                extension = self._load_extension_module(entry)
                if extension:
                    ext_id = extension.metadata.id
                    self._extensions[ext_id] = extension
                    self._load_order.append(ext_id)
                    discovered.append(ext_id)
                    logger.info(
                        "Discovered extension: %s v%s",
                        extension.metadata.name,
                        extension.metadata.version,
                    )
                    # Auto-seed any schema keys missing from config.json
                    # (non-destructive: existing user values are preserved).
                    try:
                        if extension.seed_default_config():
                            config_dirty = True
                            logger.info(
                                "Seeded missing config keys for extension '%s'",
                                ext_id,
                            )
                    except Exception as seed_err:
                        logger.warning(
                            "Config seeding failed for '%s': %s",
                            ext_id, seed_err,
                        )
                else:
                    # FIX 2026-04-23: surface silent load failures. Before,
                    # _load_extension_module returned None on import error /
                    # missing Extension class with only a DEBUG log — the
                    # user ended up with an empty EXTENSIONS panel and no
                    # way to diagnose why. Push a WARNING to QgsMessageLog
                    # so the QGIS log panel shows it.
                    self._log_discovery_failure(
                        entry, "module loaded without an 'Extension' class or failed to import",
                    )
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                logger.warning("Failed to load extension '%s': %s\n%s", entry, e, tb)
                self._log_discovery_failure(entry, f"{type(e).__name__}: {e}\n{tb}")

        # Persist when something changed. Also persist when discover_extensions
        # inserted *any* new extension namespace (even empty) — callers rely
        # on EXTENSIONS.<ext_id> existing on disk so the Configuration UI
        # enumerates them.
        if config_dirty:
            if self._persist_config():
                logger.info("Extension config persisted to config.json")
            else:
                logger.warning(
                    "Could not persist extension config — %d extension(s) "
                    "may show stale options in the Configuration panel",
                    len(discovered),
                )

        # Diagnostic summary (2026-04-23): push the list of discovered
        # extensions + their persisted config slice to the QGIS log panel
        # so users can see at a glance whether the Configuration panel
        # should be showing their extension. Only logged on first call
        # (initial discovery) so we don't spam when the registry is
        # re-scanned.
        self._log_discovery_summary(discovered)

        return discovered

    def _log_discovery_summary(self, discovered: List[str]) -> None:
        """Push a compact snapshot of discovery results to the QGIS log."""
        try:
            from qgis.core import Qgis, QgsMessageLog  # type: ignore
            from filter_mate.config.config import ENV_VARS

            cfg = ENV_VARS.get("CONFIG_DATA", {})
            ext_keys = list((cfg.get("EXTENSIONS") or {}).keys()) if isinstance(cfg, dict) else []

            QgsMessageLog.logMessage(
                f"Extension discovery: {len(discovered)} loaded ({', '.join(discovered) or 'none'}); "
                f"EXTENSIONS config keys: {ext_keys or 'none'}",
                "FilterMate",
                Qgis.MessageLevel.Info,
            )
        except Exception:
            pass

    def _load_extension_module(self, package_name: str) -> Optional[BaseExtension]:
        """
        Load an extension from a subpackage.

        Args:
            package_name: Name of the subpackage under extensions/

        Returns:
            Extension instance or None

        Raises:
            ImportError (and other exceptions) when the extension subpackage
            cannot be imported at all — the caller surfaces these to the
            user via the QGIS log so discovery failures are never silent.
        """
        module_path = f".extensions.{package_name}"
        # Import relative to filter_mate package. Let import errors bubble
        # up to the caller so _log_discovery_failure can attach the full
        # traceback to the QGIS log panel — historically this was a
        # silent debug log, which made "extension vanished from the
        # Configuration panel" impossible to diagnose.
        module = importlib.import_module(
            module_path, package="filter_mate"
        )

        extension_cls = getattr(module, 'Extension', None)
        if extension_cls is None:
            logger.debug("No 'Extension' class in %s", module_path)
            return None

        if not isinstance(extension_cls, type) or not issubclass(extension_cls, BaseExtension):
            logger.warning(
                "'Extension' in %s does not inherit BaseExtension", module_path
            )
            return None

        return extension_cls()

    def _log_discovery_failure(self, package_name: str, detail: str) -> None:
        """Push a discovery failure to the QGIS log panel.

        The python logger is normally invisible to end users; without this,
        a broken extension simply didn't show up anywhere and support had
        no entry point. This method is best-effort — any failure to reach
        QgsMessageLog is swallowed because discovery must never crash the
        plugin startup.
        """
        try:
            from qgis.core import Qgis, QgsMessageLog  # type: ignore
            QgsMessageLog.logMessage(
                f"Extension '{package_name}' failed to load — see details below.\n{detail}",
                "FilterMate",
                Qgis.MessageLevel.Warning,
            )
        except Exception:
            pass

    def register(self, extension: BaseExtension) -> None:
        """
        Manually register an extension instance.

        Args:
            extension: Extension to register
        """
        ext_id = extension.metadata.id
        if ext_id in self._extensions:
            logger.warning("Extension '%s' already registered, replacing", ext_id)
        self._extensions[ext_id] = extension
        if ext_id not in self._load_order:
            self._load_order.append(ext_id)

    def get_extension(self, ext_id: str) -> Optional[BaseExtension]:
        """
        Get a registered extension by ID.

        Args:
            ext_id: Extension identifier

        Returns:
            Extension instance or None
        """
        return self._extensions.get(ext_id)

    def get_available_extensions(self) -> List[BaseExtension]:
        """Get all extensions whose dependencies are met."""
        return [
            ext for ext in self._extensions.values()
            if ext.is_available()
        ]

    def initialize_all(self, iface: Any) -> Dict[str, bool]:
        """
        Initialize all available extensions.

        Args:
            iface: QGIS interface instance

        Returns:
            Dict mapping extension ID to success status
        """
        results = {}
        for ext_id in self._load_order:
            ext = self._extensions[ext_id]
            results[ext_id] = self._initialize_extension(ext, iface)
        self._initialized = True
        return results

    def _persist_config(self) -> bool:
        """Persist all extensions' seeded config namespaces defensively.

        Read-modify-write against disk (see ``BaseExtension._persist_config``
        for the rationale): other FilterMate components may have written
        a stale CONFIG_DATA between the seed mutations and this persist.
        We overlay only the ``EXTENSIONS`` dict on top of the current
        disk state, preserving sibling sections even if they diverged.

        FIX 2026-04-23: the previous implementation reassigned
        ``ENV_VARS["CONFIG_DATA"] = disk_data``, but ``app.CONFIG_DATA``
        and ``dockwidget.CONFIG_DATA`` hold a *reference* to the live
        dict captured earlier. Reassigning the module-level slot leaves
        those references pointing at the old object, so the config
        panel tree (built from ``dw.CONFIG_DATA``) silently misses the
        newly-seeded extension entries — exactly the symptom reported
        when ``favorites_sharing`` was discovered and seeded yet the
        EXTENSIONS panel kept showing only ``qfieldcloud``.
        We now **mutate in place**: merge disk-only sections back into
        the live dict, then overwrite the live EXTENSIONS with the
        merged slice. Every holder of the old reference sees the fix.
        """
        try:
            from filter_mate.config.config import ENV_VARS
            import json
        except Exception:
            return False
        config_path = ENV_VARS.get("CONFIG_JSON_PATH")
        live_data = ENV_VARS.get("CONFIG_DATA")
        if not config_path or not isinstance(live_data, dict):
            return False

        live_extensions = live_data.get("EXTENSIONS", {})
        if not isinstance(live_extensions, dict):
            live_extensions = {}

        # Re-read disk state (best-effort) to pull in any sibling sections
        # written by other components between our seed and this persist.
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                disk_data = json.load(f)
            if not isinstance(disk_data, dict):
                disk_data = {}
        except (OSError, ValueError):
            disk_data = {}

        # 1. Merge disk-only sibling sections into live_data (preserves any
        #    sibling that another component wrote directly to disk).
        for key, value in disk_data.items():
            if key == "EXTENSIONS":
                continue  # handled below
            if key not in live_data:
                live_data[key] = value

        # 2. Build the merged EXTENSIONS dict: disk version + live overrides.
        disk_extensions = disk_data.get("EXTENSIONS", {})
        if not isinstance(disk_extensions, dict):
            disk_extensions = {}
        merged_ext: Dict[str, Any] = {}
        # Start from disk (preserves user edits that only exist on disk).
        for ext_id, slice_data in disk_extensions.items():
            if isinstance(slice_data, (dict, str, bool, int, float, list)):
                merged_ext[ext_id] = slice_data
        # Overlay with live values:
        #  - extension namespaces (dicts) — fresh seed wins over stale disk
        #  - metadata keys starting with "_" (e.g. ``_display_name``) so the
        #    Configuration panel keeps a label even when the disk file was
        #    rewritten by an older release that didn't carry it.
        for ext_id, slice_data in live_extensions.items():
            if isinstance(slice_data, dict):
                merged_ext[ext_id] = slice_data
            elif isinstance(ext_id, str) and ext_id.startswith("_") and isinstance(
                slice_data, (str, bool, int, float, list)
            ):
                merged_ext[ext_id] = slice_data

        # 3. Mutate live_data["EXTENSIONS"] in place — do NOT reassign
        #    ENV_VARS["CONFIG_DATA"]. Every reader holding the live ref
        #    (app.CONFIG_DATA, dockwidget.CONFIG_DATA, config tree model)
        #    will see the merged state on the next access.
        existing = live_data.get("EXTENSIONS")
        if isinstance(existing, dict):
            existing.clear()
            existing.update(merged_ext)
        else:
            live_data["EXTENSIONS"] = merged_ext

        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(live_data, f, indent=2, ensure_ascii=False)
            return True
        except OSError as exc:
            logger.warning("Could not persist config.json: %s", exc)
            return False

    def _show_missing_deps_message(self, ext: BaseExtension, iface: Any) -> None:
        """Show a message when extension deps are missing, with dismiss option."""
        ext_id = ext.metadata.id

        if ext.is_warning_dismissed():
            return

        try:
            from qgis.PyQt.QtWidgets import QCheckBox, QMessageBox

            deps = ", ".join(ext.metadata.dependencies) if ext.metadata.dependencies else "?"

            # FIX 2026-04-23: per-extension install hint so the dialog
            # stops telling users "pip install resource_sharing" when
            # the dep is actually a QGIS plugin installed via the
            # Plugin Manager. Falls back to the legacy pip wording for
            # extensions that don't override missing_deps_hint().
            try:
                hint = ext.missing_deps_hint() or {}
            except Exception as hint_err:
                logger.debug("missing_deps_hint() failed for %s: %s", ext_id, hint_err)
                hint = {}
            method = (hint.get("method") or "pip").lower()
            install_cmd = hint.get("install_command") or f"pip install {deps}"
            details = hint.get("details") or ""

            if method == "qgis_plugin":
                step_one = f"Installez le plugin QGIS : {install_cmd}"
            elif method == "manual":
                step_one = install_cmd
            else:
                step_one = f"Installez : {install_cmd}"

            msg = QMessageBox(iface.mainWindow())
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle(f"FilterMate — Extension {ext.metadata.name}")
            msg.setText(
                f"L'extension <b>{ext.metadata.name}</b> n'a pas pu démarrer "
                f"car les dépendances requises ne sont pas disponibles.\n"
            )
            informative_lines = [
                f"Paquets manquants : {deps}",
                "",
                "Pour l'activer :",
                f"  1. {step_one}",
                "  2. Redémarrez QGIS (ou rechargez le plugin FilterMate)",
            ]
            if details:
                informative_lines.extend(["", details])
            informative_lines.extend([
                "",
                "Réglages :",
                f"  config.json → EXTENSIONS → {ext_id} → enabled",
            ])
            msg.setInformativeText("\n".join(informative_lines))

            checkbox = QCheckBox("Ne plus afficher ce message")
            msg.setCheckBox(checkbox)
            msg.exec()

            if checkbox.isChecked():
                ext.dismiss_warning()

        except Exception as e:
            logger.debug("Could not show missing deps message: %s", e)

    def _initialize_extension(self, ext: BaseExtension, iface: Any) -> bool:
        """Initialize a single extension."""
        ext_id = ext.metadata.id
        try:
            # Check config enable/disable
            if not ext.is_enabled():
                logger.info("Extension '%s' disabled in config", ext_id)
                return False

            # Check dependencies
            if not ext.is_available():
                logger.info(
                    "Extension '%s' not available (missing dependencies)",
                    ext_id,
                )
                # FIX 2026-04-23: do NOT flip enabled=False here. Previously
                # we did, which meant installing the missing dep + reloading
                # was insufficient — the user also had to re-flip enabled
                # to True by hand. Leaving the config flag alone lets the
                # extension auto-resume on the next session once the dep
                # is available. is_available() remains the single source
                # of truth per session.
                self._show_missing_deps_message(ext, iface)
                return False

            ext.initialize(iface)
            ext._set_state(ExtensionState.INITIALIZED)
            logger.info("Extension '%s' initialized", ext_id)
            return True

        except Exception as e:
            ext._set_error(f"Initialization failed: {e}")
            logger.exception("Failed to initialize extension '%s'", ext_id)
            return False

    def create_all_ui(self, toolbar: Any, menu_name: str) -> Dict[str, List[Any]]:
        """
        Create UI for all initialized extensions.

        Args:
            toolbar: QGIS toolbar
            menu_name: Menu name

        Returns:
            Dict mapping extension ID to list of QActions created
        """
        results = {}
        for ext_id in self._load_order:
            ext = self._extensions[ext_id]
            if ext.state != ExtensionState.INITIALIZED:
                continue
            try:
                actions = ext.create_ui(toolbar, menu_name)
                ext._set_state(ExtensionState.UI_CREATED)
                results[ext_id] = actions
            except Exception as e:
                ext._set_error(f"UI creation failed: {e}")
                logger.exception("Failed to create UI for extension '%s'", ext_id)
                results[ext_id] = []
        return results

    def create_all_dockwidget_ui(self, dockwidget: Any) -> Dict[str, List[Any]]:
        """
        Create dockwidget UI for all initialized extensions.

        Called after the FilterMate dockwidget is created and shown,
        allowing extensions to inject buttons/widgets into the dockwidget.

        Args:
            dockwidget: FilterMate dockwidget instance

        Returns:
            Dict mapping extension ID to list of widgets created
        """
        results = {}
        for ext_id in self._load_order:
            ext = self._extensions.get(ext_id)
            if ext is None:
                continue
            if ext.state not in (ExtensionState.INITIALIZED, ExtensionState.UI_CREATED):
                continue
            try:
                widgets = ext.create_dockwidget_ui(dockwidget)
                results[ext_id] = widgets or []
            except Exception as e:
                logger.warning(
                    "Failed to create dockwidget UI for extension '%s': %s",
                    ext_id, e,
                )
                results[ext_id] = []
        return results

    def teardown_all(self) -> None:
        """Teardown all extensions in reverse load order."""
        for ext_id in reversed(self._load_order):
            ext = self._extensions[ext_id]
            if ext.state in (ExtensionState.INITIALIZED, ExtensionState.UI_CREATED):
                try:
                    ext.teardown()
                    ext._set_state(ExtensionState.TORN_DOWN)
                    logger.debug("Extension '%s' torn down", ext_id)
                except Exception as e:
                    logger.warning(
                        "Error tearing down extension '%s': %s", ext_id, e
                    )
        self._extensions.clear()
        self._load_order.clear()
        self._initialized = False

    def notify_project_loaded(self) -> None:
        """Notify all active extensions that a project was loaded."""
        for ext in self._extensions.values():
            if ext.state in (ExtensionState.INITIALIZED, ExtensionState.UI_CREATED):
                try:
                    ext.on_project_loaded()
                except Exception as e:
                    logger.warning(
                        "Extension '%s' project_loaded error: %s",
                        ext.metadata.id, e,
                    )

    def notify_project_closed(self) -> None:
        """Notify all active extensions that a project was closed."""
        for ext in self._extensions.values():
            if ext.state in (ExtensionState.INITIALIZED, ExtensionState.UI_CREATED):
                try:
                    ext.on_project_closed()
                except Exception as e:
                    logger.warning(
                        "Extension '%s' project_closed error: %s",
                        ext.metadata.id, e,
                    )

    def get_status_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get a summary of all extensions and their states."""
        summary = {}
        for ext_id, ext in self._extensions.items():
            summary[ext_id] = {
                'name': ext.metadata.name,
                'version': ext.metadata.version,
                'state': ext.state.value,
                'available': ext.is_available(),
                'error': ext.error_message,
            }
        return summary


def get_extension_registry() -> ExtensionRegistry:
    """
    Get the global extension registry singleton.

    Returns:
        ExtensionRegistry instance
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ExtensionRegistry()
    return _registry_instance


def reset_extension_registry() -> None:
    """Reset the global registry (for testing)."""
    global _registry_instance
    if _registry_instance is not None:
        _registry_instance.teardown_all()
    _registry_instance = None
