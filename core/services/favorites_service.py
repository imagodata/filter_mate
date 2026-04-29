"""
FavoritesService - Favorites Business Logic Service.

Bridge between UI controllers and the FavoritesManager data layer.
Provides higher-level operations and event notifications.

Story: MIG-076
Phase: 6 - God Class DockWidget Migration
Pattern: Strangler Fig - Gradual extraction
"""

import logging
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass

try:
    from qgis.PyQt.QtCore import pyqtSignal, QObject
except ImportError:
    from PyQt6.QtCore import pyqtSignal, QObject

if TYPE_CHECKING:
    from qgis.core import QgsVectorLayer

# Export FilterFavorite from domain
from ..domain.exceptions import (
    FavoritePersistenceError,
    FavoritesError,
    FavoritesNotInitialized,
)
from ..domain.favorite_import_handler import FavoriteImportHandler
from ..domain.favorites_manager import FilterFavorite
from ..domain.layer_signature import LayerSignatureIndex

logger = logging.getLogger(__name__)


@dataclass
class FavoriteApplyResult:
    """Result of applying a favorite."""
    success: bool
    favorite_id: str
    favorite_name: str
    layers_affected: int = 0
    error_message: str = ""


@dataclass
class FavoriteExportResult:
    """Result of exporting favorites."""
    success: bool
    file_path: str
    favorites_count: int = 0
    error_message: str = ""


@dataclass
class FavoriteImportResult:
    """Result of importing favorites."""
    success: bool
    file_path: str
    imported_count: int = 0
    skipped_count: int = 0
    error_message: str = ""


class FavoritesService(QObject):
    """
    Service for managing filter favorites.

    Provides:
    - Favorite CRUD operations with notifications
    - Apply/unapply favorites to layers
    - Import/export favorites
    - Search and organization
    - Usage tracking and statistics

    Emits:
    - favorites_changed: When the favorites list changes (the only
      signal anyone subscribes to — the per-event signals were never
      observed and were dropped 2026-04-29 per CORE-3 audit).
    """

    # Signals
    favorites_changed = pyqtSignal()  # general notification

    def __init__(
        self,
        favorites_manager: Optional[Any] = None,
        parent: Optional[QObject] = None
    ):
        """
        Initialize FavoritesService.

        Args:
            favorites_manager: FavoritesManager instance (or will be created)
            parent: Optional parent QObject
        """
        super().__init__(parent)

        # If no manager provided, create internal one
        if favorites_manager is None:
            try:
                from ..domain.favorites_manager import FavoritesManager
                self._favorites_manager = FavoritesManager()
                logger.debug("FavoritesService: Created internal FavoritesManager")
            except Exception as e:
                logger.warning(f"Could not create internal FavoritesManager: {e}")
                self._favorites_manager = None
        else:
            self._favorites_manager = favorites_manager

        self._is_initialized = False

    # ─────────────────────────────────────────────────────────────────
    # Initialization
    # ─────────────────────────────────────────────────────────────────

    @property
    def favorites_manager(self) -> Any:
        """Get the underlying FavoritesManager."""
        return self._favorites_manager

    @favorites_manager.setter
    def favorites_manager(self, manager: Any) -> None:
        """Set the FavoritesManager."""
        self._favorites_manager = manager
        self._is_initialized = manager is not None

    def initialize(
        self,
        db_path: Optional[str] = None,
        project_uuid: Optional[str] = None
    ) -> bool:
        """
        Initialize the service with database.

        Args:
            db_path: Path to FilterMate database
            project_uuid: Current project UUID

        Returns:
            bool: True if initialization succeeded
        """
        # FavoritesService is a wrapper - it requires an external manager
        # The manager should be injected via constructor or favorites_manager setter
        if self._favorites_manager is None:
            logger.warning("FavoritesService: No favorites manager provided. Use favorites_manager setter.")
            return False

        # Configure existing manager with database
        if db_path and project_uuid:
            self.set_database(db_path, project_uuid)

        self._is_initialized = True
        return True

    def set_database(self, db_path: str, project_uuid: str) -> None:
        """
        Set database path and project UUID.
        Delegates to underlying FavoritesManager.

        Args:
            db_path: Path to SQLite database
            project_uuid: Project UUID for favorites isolation
        """
        if self._favorites_manager and hasattr(self._favorites_manager, 'set_database'):
            self._favorites_manager.set_database(db_path, project_uuid)

            # FIX 2026-04-22: if the SQLite DB is empty but the .qgz project file
            # carries a favorites backup (e.g. the plugin was re-installed, the
            # user moved the project to another machine, or the sqlite was wiped),
            # silently re-import the backup so favorites persist across transfer.
            if self.count == 0:
                try:
                    restored = self.restore_from_project_file()
                    if restored > 0:
                        logger.info(
                            f"✓ Auto-restored {restored} favorites from project file (.qgz) backup"
                        )
                except Exception as e:
                    logger.debug(f"Auto-restore from project file skipped: {e}")

            # CRITICAL: Emit favorites_changed to update UI after loading
            self.favorites_changed.emit()
            logger.info(f"✓ Favorites loaded from database and UI notified (count: {self.count})")
        else:
            # FIX 2026-04-23 (LOW-1): the previous "internal storage" fallback
            # created a divergent `favorites` table schema (vs the canonical
            # `fm_favorites`) that no downstream code could read. It was only
            # reachable when the __init__ failed to create an internal
            # FavoritesManager — which in practice never happens. We now
            # fail loudly so the bug surfaces instead of silently creating a
            # half-broken SQLite file.
            logger.error(
                "FavoritesService.set_database called without a working "
                "FavoritesManager. This indicates a plugin bootstrap failure — "
                "check earlier logs for FavoritesManager import errors."
            )

    def load_from_project(self) -> None:
        """
        Load favorites from project.
        Delegates to underlying FavoritesManager.
        """
        if self._favorites_manager and hasattr(self._favorites_manager, 'load_from_project'):
            self._favorites_manager.load_from_project()
            # CRITICAL: Emit favorites_changed to update UI after loading
            self.favorites_changed.emit()
            logger.info(f"✓ Favorites reloaded from database and UI notified (count: {self.count})")
        else:
            # Note: Internal project loading without manager is not implemented.
            # FavoritesManager is required for full functionality.
            logger.debug("FavoritesService: Loading from project (stub - no manager)")

    @property
    def count(self) -> int:
        """Get the number of favorites."""
        if self._favorites_manager and hasattr(self._favorites_manager, '__len__'):
            return len(self._favorites_manager)
        elif self._favorites_manager and hasattr(self._favorites_manager, 'count'):
            return self._favorites_manager.count
        return 0

    

    # ─────────────────────────────────────────────────────────────────
    # CRUD Operations
    # ─────────────────────────────────────────────────────────────────

    def add_favorite(
        self,
        name: str,
        expression: str,
        layer_name: Optional[str] = None,
        layer_provider: Optional[str] = None,
        spatial_config: Optional[Dict] = None,
        remote_layers: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
        description: str = ""
    ) -> Optional[str]:
        """
        Add a new favorite.

        Args:
            name: Favorite name
            expression: Filter expression
            layer_name: Optional layer name
            layer_provider: Optional provider type
            spatial_config: Optional spatial filter config
            remote_layers: Optional remote layers config
            tags: Optional tags list
            description: Optional description

        Returns:
            str: Favorite ID if created, None on error
        """
        if not self._favorites_manager:
            logger.error("FavoritesManager not initialized")
            return None

        try:
            # FilterFavorite is imported at top of file
            favorite = FilterFavorite(
                name=name,
                expression=expression,
                layer_name=layer_name,
                layer_provider=layer_provider,
                spatial_config=spatial_config,
                remote_layers=remote_layers,
                tags=tags or [],
                description=description
            )

            success = self._favorites_manager.add_favorite(favorite)

            if success:
                self.favorites_changed.emit()
                logger.info(f"✓ Favorite added via FavoritesService: {name} (ID: {favorite.id})")
                return favorite.id
            else:
                logger.error(f"✗ Failed to add favorite '{name}' - FavoritesManager.add_favorite() returned False")

            return None

        except Exception as e:
            logger.error(f"Error adding favorite: {e}")
            return None

    def remove_favorite(self, favorite_id: str) -> bool:
        """
        Remove a favorite.

        Args:
            favorite_id: ID of favorite to remove

        Returns:
            bool: True if removed successfully

        Raises:
            FavoritesNotInitialized: if the service has no manager attached
                (programmer error / startup race — see F16 phase 2).
        """
        if not self._favorites_manager:
            raise FavoritesNotInitialized(
                "FavoritesService.remove_favorite called before manager was attached"
            )

        try:
            success = self._favorites_manager.remove_favorite(favorite_id)

            if success:
                self.favorites_changed.emit()
                logger.info(f"Removed favorite: {favorite_id}")

            return success

        except FavoritesError:
            # Domain errors (NotInitialized / NotFound / PersistenceError)
            # propagate intact — caller decides how to surface.
            raise
        except Exception as e:
            logger.error(f"Error removing favorite: {e}")
            raise FavoritePersistenceError("remove_favorite", e) from e

    def update_favorite(
        self,
        favorite_id: str,
        **kwargs
    ) -> bool:
        """
        Update a favorite.

        Args:
            favorite_id: ID of favorite to update
            **kwargs: Fields to update

        Returns:
            bool: True if updated successfully

        Raises:
            FavoritesNotInitialized: if the service has no manager attached.
        """
        if not self._favorites_manager:
            raise FavoritesNotInitialized(
                "FavoritesService.update_favorite called before manager was attached"
            )

        try:
            success = self._favorites_manager.update_favorite(favorite_id, **kwargs)

            if success:
                self.favorites_changed.emit()
                logger.info(f"Updated favorite: {favorite_id}")

            return success

        except FavoritesError:
            raise
        except Exception as e:
            logger.error(f"Error updating favorite: {e}")
            raise FavoritePersistenceError("update_favorite", e) from e

    def get_favorite(self, favorite_id: str) -> Optional[Any]:
        """
        Get a favorite by ID.

        Args:
            favorite_id: Favorite ID

        Returns:
            FilterFavorite or None
        """
        if not self._favorites_manager:
            return None

        return self._favorites_manager.get_favorite(favorite_id)

    def get_favorite_by_name(self, name: str) -> Optional[Any]:
        """
        Get a favorite by name.

        Args:
            name: Favorite name

        Returns:
            FilterFavorite or None
        """
        if not self._favorites_manager:
            return None

        return self._favorites_manager.get_favorite_by_name(name)

    # ─────────────────────────────────────────────────────────────────
    # List Operations
    # ─────────────────────────────────────────────────────────────────

    def get_all_favorites(self) -> List[Any]:
        """
        Get all favorites.

        Returns:
            List of FilterFavorite objects
        """
        if not self._favorites_manager:
            return []

        return self._favorites_manager.get_all_favorites()

    def get_recent_favorites(self, limit: int = 5) -> List[Any]:
        """
        Get recently used favorites.

        Args:
            limit: Maximum number to return

        Returns:
            List of FilterFavorite objects
        """
        if not self._favorites_manager:
            return []

        return self._favorites_manager.get_recent_favorites(limit)

    def get_most_used_favorites(self, limit: int = 5) -> List[Any]:
        """
        Get most frequently used favorites.

        Args:
            limit: Maximum number to return

        Returns:
            List of FilterFavorite objects
        """
        if not self._favorites_manager:
            return []

        return self._favorites_manager.get_most_used_favorites(limit)

    def search_favorites(self, query: str) -> List[Any]:
        """
        Search favorites by name, expression, or tags.

        Args:
            query: Search query

        Returns:
            List of matching FilterFavorite objects
        """
        if not self._favorites_manager:
            return []

        return self._favorites_manager.search_favorites(query)

    def get_favorites_count(self) -> int:
        """
        Get total number of favorites.

        Returns:
            int: Number of favorites
        """
        if not self._favorites_manager:
            return 0

        return len(self.get_all_favorites())

    # ─────────────────────────────────────────────────────────────────
    # Apply Operations
    # ─────────────────────────────────────────────────────────────────

    

    def mark_favorite_used(self, favorite_id: str) -> bool:
        """
        Mark a favorite as used (update usage stats).

        Args:
            favorite_id: Favorite ID

        Returns:
            bool: True if marked successfully

        Raises:
            FavoritesNotInitialized: if the service has no manager attached.
        """
        if not self._favorites_manager:
            raise FavoritesNotInitialized(
                "FavoritesService.mark_favorite_used called before manager was attached"
            )

        return self._favorites_manager.increment_use_count(favorite_id)

    # ─────────────────────────────────────────────────────────────────
    # Create from Current State
    # ─────────────────────────────────────────────────────────────────

    

    # ─────────────────────────────────────────────────────────────────
    # Import/Export
    # ─────────────────────────────────────────────────────────────────

    # FIX 2026-04-23 (v3): plugin version embedded in each export so the
    # receiving side can render "min plugin version" warnings and downgrade
    # paths gracefully. Kept module-level for discoverability.
    EXPORT_SCHEMA = "filter_mate.favorites"
    EXPORT_SCHEMA_VERSION = 3
    EXPORT_MIN_COMPAT_PLUGIN_VERSION = "4.0.0"

    def export_favorites(
        self,
        file_path: str,
        favorite_ids: Optional[List[str]] = None,
        collection_metadata: Optional[Dict[str, Any]] = None,
        strip_owner: bool = False,
    ) -> FavoriteExportResult:
        """
        Export favorites to a JSON file.

        Writes **schema v3** — an envelope with explicit ``schema_version``,
        generator info, optional ``collection`` metadata (name, author,
        description, license, tags) and a signature-keyed ``remote_layers``
        canonical payload. Readers of v1/v2 can still ignore new fields;
        readers of v3 get provenance + upgrade hints.

        Args:
            file_path: Path to export file
            favorite_ids: Optional list of IDs to export (None = all)
            collection_metadata: Optional metadata dict to describe the
                bundle (name, author, license, description, tags). Used by
                the resource_sharing extension to ship curated collections.
            strip_owner: When True, drop ``owner`` from every favorite
                before writing. ``owner`` identifies the local author
                inside a single DB and must never leak when a bundle
                crosses organisation boundaries (publish, fork, share via
                git). Used by the resource_sharing extension; default
                False keeps owner for in-tenant exports.

        Returns:
            FavoriteExportResult with status
        """
        if not self._favorites_manager:
            return FavoriteExportResult(
                success=False,
                file_path=file_path,
                error_message="FavoritesManager not initialized"
            )

        try:
            import json

            # Get favorites to export
            if favorite_ids:
                favorites = [
                    self._favorites_manager.get_favorite(fid)
                    for fid in favorite_ids
                ]
                favorites = [f for f in favorites if f is not None]
            else:
                favorites = self.get_all_favorites()

            # v2 signature substitution + v3 canonical keying — both
            # handled by FavoriteImportHandler.strip_project_bindings
            # (updated for CRIT-3).
            serialized = [
                FavoriteImportHandler.strip_project_bindings(f.to_dict())
                for f in favorites
            ]
            # H4 fix 2026-04-27: stripping ``owner`` happens here in the
            # canonical export pass (instead of a second-rewrite post-step
            # in the sharing extension) so the on-disk file is final from
            # the first ``json.dump``.
            if strip_owner:
                for fav in serialized:
                    fav.pop('owner', None)
            # v3: stamp each favorite with its portability status so readers
            # can decide whether to accept legacy entries.
            for fav in serialized:
                fav.setdefault('portable', bool(
                    (fav.get('spatial_config') or {}).get('source_layer_signature')
                    or any(
                        isinstance(p, dict) and p.get('layer_signature')
                        for p in (fav.get('remote_layers') or {}).values()
                    )
                    or not fav.get('remote_layers')
                ))

            plugin_version = self._read_plugin_version() or "unknown"
            envelope: Dict[str, Any] = {
                "schema": self.EXPORT_SCHEMA,
                "schema_version": self.EXPORT_SCHEMA_VERSION,
                "min_compat_plugin_version": self.EXPORT_MIN_COMPAT_PLUGIN_VERSION,
                "generator": f"filter_mate/{plugin_version}",
                "exported_at": self._get_timestamp(),
                # Legacy field for v1/v2 readers — they only look at "version"
                # and "favorites". Reading v3 with a v2-era FilterMate still
                # works because the per-favorite layout is backward-compatible.
                "version": "3.0",
                "favorites": serialized,
            }
            if collection_metadata and isinstance(collection_metadata, dict):
                envelope["collection"] = {
                    k: v for k, v in collection_metadata.items()
                    if k in {'name', 'author', 'license', 'description',
                             'tags', 'homepage', 'icon'}
                }

            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(envelope, f, indent=2, ensure_ascii=False)

            count = len(favorites)

            logger.info(
                f"Exported {count} favorites to {file_path} "
                f"(schema v{self.EXPORT_SCHEMA_VERSION})"
            )

            return FavoriteExportResult(
                success=True,
                file_path=file_path,
                favorites_count=count
            )

        except Exception as e:
            logger.error(f"Error exporting favorites: {e}")
            return FavoriteExportResult(
                success=False,
                file_path=file_path,
                error_message=str(e)
            )

    @staticmethod
    def _read_plugin_version() -> Optional[str]:
        """Best-effort read of the plugin version from metadata.txt."""
        try:
            import os
            # plugin root = parent of core/services
            here = os.path.dirname(os.path.abspath(__file__))
            root = os.path.dirname(os.path.dirname(here))
            metadata_path = os.path.join(root, 'metadata.txt')
            if not os.path.isfile(metadata_path):
                return None
            with open(metadata_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('version='):
                        return line.split('=', 1)[1].strip()
        except Exception:
            pass
        return None

    def import_favorites(
        self,
        file_path: str,
        skip_duplicates: bool = True
    ) -> FavoriteImportResult:
        """
        Import favorites from a JSON file.

        Args:
            file_path: Path to import file
            skip_duplicates: Skip favorites with same name

        Returns:
            FavoriteImportResult with status
        """
        if not self._favorites_manager:
            return FavoriteImportResult(
                success=False,
                file_path=file_path,
                error_message="FavoritesManager not initialized"
            )

        try:
            import json

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            favorites_data = data.get('favorites', [])
            file_version = str(data.get('version', '1.0'))

            # Build the project signature index once for the whole
            # import — re-walking QgsProject for every entry was the
            # main perf cliff on bundles >50 favorites and the reason
            # the rebind logic kept growing module-level caches.
            index = LayerSignatureIndex()

            imported_count = 0
            skipped_count = 0

            for fav_data in favorites_data:
                name = fav_data.get('name', '')

                if skip_duplicates:
                    existing = self.get_favorite_by_name(name)
                    if existing:
                        skipped_count += 1
                        continue

                rebound = FavoriteImportHandler.rebind_to_project(
                    fav_data, index, file_version=file_version
                )

                favorite = FilterFavorite.from_dict(rebound)
                favorite.id = None  # Will generate new ID

                # CRIT-1: keep the author's original timestamps so the
                # import UI shows the real provenance; add a fresh id but
                # preserve created_at/updated_at from the JSON.
                if self._favorites_manager.add_favorite(favorite, preserve_timestamps=True):
                    imported_count += 1
                else:
                    skipped_count += 1

            self.favorites_changed.emit()

            logger.info(f"Imported {imported_count} favorites, skipped {skipped_count}")

            return FavoriteImportResult(
                success=True,
                file_path=file_path,
                imported_count=imported_count,
                skipped_count=skipped_count
            )

        except Exception as e:
            logger.error(f"Error importing favorites: {e}")
            return FavoriteImportResult(
                success=False,
                file_path=file_path,
                error_message=str(e)
            )

    # ─────────────────────────────────────────────────────────────────
    # Statistics
    # ─────────────────────────────────────────────────────────────────

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get favorites statistics.

        Returns:
            Dict with statistics
        """
        favorites = self.get_all_favorites()

        if not favorites:
            return {
                "total_count": 0,
                "total_uses": 0,
                "most_used": None,
                "recently_used": None
            }

        total_uses = sum(f.use_count for f in favorites)
        most_used = max(favorites, key=lambda f: f.use_count) if favorites else None

        recent = self.get_recent_favorites(1)
        recently_used = recent[0] if recent else None

        return {
            "total_count": len(favorites),
            "total_uses": total_uses,
            "most_used": most_used.name if most_used else None,
            "most_used_count": most_used.use_count if most_used else 0,
            "recently_used": recently_used.name if recently_used else None
        }

    # ─────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()

    def save(self) -> bool:
        """
        Save favorites to storage.

        Returns:
            bool: True if saved successfully

        Raises:
            FavoritesNotInitialized: if the service has no manager attached.
        """
        if not self._favorites_manager:
            raise FavoritesNotInitialized(
                "FavoritesService.save called before manager was attached"
            )

        try:
            self._favorites_manager.save_to_project()
            return True
        except FavoritesError:
            raise
        except Exception as e:
            logger.error(f"Error saving favorites: {e}")
            raise FavoritePersistenceError("save", e) from e

    def reload(self) -> bool:
        """
        Reload favorites from storage.

        Returns:
            bool: True if reloaded successfully

        Raises:
            FavoritesNotInitialized: if the service has no manager attached.
        """
        if not self._favorites_manager:
            raise FavoritesNotInitialized(
                "FavoritesService.reload called before manager was attached"
            )

        try:
            self._favorites_manager.load_from_database()
            self.favorites_changed.emit()
            return True
        except FavoritesError:
            raise
        except Exception as e:
            logger.error(f"Error reloading favorites: {e}")
            raise FavoritePersistenceError("reload", e) from e

    # ─────────────────────────────────────────────────────────────────
    # Project File (.qgz) Backup/Restore
    # ─────────────────────────────────────────────────────────────────

    def save_to_project_file(self, project: Optional[Any] = None) -> bool:
        """
        Save favorites to QGIS project file as custom property.

        This provides an additional backup in the .qgz file itself,
        ensuring favorites are bundled with the project.

        Args:
            project: QgsProject instance (uses current if None)

        Returns:
            bool: True if saved successfully

        Raises:
            FavoritesNotInitialized: if the service has no manager attached.
        """
        if not self._favorites_manager:
            raise FavoritesNotInitialized(
                "FavoritesService.save_to_project_file called before manager was attached"
            )

        try:
            from qgis.core import QgsProject
            import json

            if project is None:
                project = QgsProject.instance()

            favorites = self.get_all_favorites()

            if not favorites:
                # Clear any existing property
                project.removeEntry("FilterMate", "favorites_backup")
                return True

            # Serialize favorites
            data = {
                "version": "1.0",
                "backup_type": "project_file",
                "created_at": self._get_timestamp(),
                "favorites": [f.to_dict() for f in favorites]
            }

            json_data = json.dumps(data, ensure_ascii=False)

            # Store in project custom properties
            project.writeEntry("FilterMate", "favorites_backup", json_data)

            logger.info(f"✓ Saved {len(favorites)} favorites to project file")
            return True

        except FavoritesError:
            raise
        except Exception as e:
            logger.error(f"Error saving favorites to project file: {e}")
            raise FavoritePersistenceError("save_to_project_file", e) from e

    def restore_from_project_file(self, project: Optional[Any] = None) -> int:
        """
        Restore favorites from QGIS project file backup.

        This is useful when the SQLite database is lost or corrupted.

        Args:
            project: QgsProject instance (uses current if None)

        Returns:
            int: Number of favorites restored
        """
        if not self._favorites_manager:
            return 0

        try:
            from qgis.core import QgsProject
            import json

            if project is None:
                project = QgsProject.instance()

            # Read from project custom properties
            json_data, success = project.readEntry("FilterMate", "favorites_backup", "")

            if not success or not json_data:
                logger.debug("No favorites backup found in project file")
                return 0

            data = json.loads(json_data)
            favorites_data = data.get('favorites', [])

            if not favorites_data:
                return 0

            # Import favorites — dedup by id, then by (name, updated_at).
            # HIGH-4: dedup-by-name alone silently dropped newer edits from
            # the .qgz when the DB had a stale version (or vice versa).
            # Comparing updated_at now surfaces the newer version instead
            # of the first-seen one.
            from ..domain.favorites_manager import FilterFavorite
            from datetime import datetime as _dt

            def _parse_ts(value: Optional[str]) -> float:
                if not value:
                    return 0.0
                try:
                    return _dt.fromisoformat(value).timestamp()
                except (ValueError, TypeError):
                    return 0.0

            imported = 0
            updated = 0
            for fav_data in favorites_data:
                name = fav_data.get('name', '')
                fav_id_from_backup = fav_data.get('id')
                backup_updated_at = fav_data.get('updated_at')

                # Check for existing favorite (id match first, name fallback)
                existing = None
                if fav_id_from_backup:
                    existing = self._favorites_manager.get_favorite(fav_id_from_backup)
                if existing is None:
                    existing = self.get_favorite_by_name(name)

                if existing is not None:
                    # Keep the newer version — if the backup is strictly
                    # newer, refresh the in-DB row with its content; else
                    # skip silently (DB already has equal/newer data).
                    existing_ts = _parse_ts(getattr(existing, 'updated_at', None))
                    backup_ts = _parse_ts(backup_updated_at)
                    if backup_ts > existing_ts:
                        updatable_fields = {
                            k: v for k, v in fav_data.items()
                            if k in FilterFavorite.__dataclass_fields__
                            and k not in ('id', 'created_at')
                        }
                        if self._favorites_manager.update_favorite(
                            existing.id, **updatable_fields
                        ):
                            updated += 1
                    continue

                # Create and add favorite
                favorite = FilterFavorite.from_dict(fav_data)
                favorite.id = None  # Generate new ID

                # CRIT-1: restore_from_project_file is a DB rebuild, not a
                # user "add". The original created_at must survive so the
                # user doesn't see every favorite suddenly re-stamped with
                # today's date after a plugin reinstall.
                if self._favorites_manager.add_favorite(favorite, preserve_timestamps=True):
                    imported += 1

            if updated:
                logger.info(f"✓ Refreshed {updated} favorite(s) from newer .qgz backup")
            imported += updated

            if imported > 0:
                self.favorites_changed.emit()
                logger.info(f"✓ Restored {imported} favorites from project file")

            return imported

        except Exception as e:
            logger.error(f"Error restoring favorites from project file: {e}")
            return 0

    # ─────────────────────────────────────────────────────────────────
    # Global Favorites Support
    # ─────────────────────────────────────────────────────────────────

    def get_global_favorites(self) -> List[Any]:
        """
        Get all global favorites (available in all projects).

        Returns:
            List of global FilterFavorite objects
        """
        if not self._favorites_manager:
            return []

        if hasattr(self._favorites_manager, 'get_global_favorites'):
            return self._favorites_manager.get_global_favorites()

        return []

    

    def make_favorite_global(self, favorite_id: str) -> bool:
        """
        Make a favorite global (available in all projects).

        Args:
            favorite_id: ID of favorite to make global

        Returns:
            bool: True if successful

        Raises:
            FavoritesNotInitialized: if the service has no manager attached.
        """
        if not self._favorites_manager:
            raise FavoritesNotInitialized(
                "FavoritesService.make_favorite_global called before manager was attached"
            )

        if hasattr(self._favorites_manager, 'make_favorite_global'):
            success = self._favorites_manager.make_favorite_global(favorite_id)
            if success:
                self.favorites_changed.emit()
            return success

        return False

    def copy_to_global(self, favorite_id: str) -> Optional[str]:
        """
        Copy a favorite to global (keeps original in project).

        Args:
            favorite_id: ID of favorite to copy

        Returns:
            New favorite ID if successful, None otherwise
        """
        if not self._favorites_manager:
            return None

        if hasattr(self._favorites_manager, 'copy_to_global'):
            new_id = self._favorites_manager.copy_to_global(favorite_id)
            if new_id:
                self.favorites_changed.emit()
            return new_id

        return None

    def import_global_to_project(self, global_favorite_id: str) -> Optional[str]:
        """
        Import a global favorite to the current project.

        Args:
            global_favorite_id: ID of global favorite to import

        Returns:
            New favorite ID if successful, None otherwise
        """
        if not self._favorites_manager:
            return None

        if hasattr(self._favorites_manager, 'import_global_to_project'):
            new_id = self._favorites_manager.import_global_to_project(global_favorite_id)
            if new_id:
                self.favorites_changed.emit()
            return new_id

        return None
