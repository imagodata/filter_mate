"""
FavoritesService - Favorites Business Logic Service.

Bridge between UI controllers and the FavoritesManager data layer.
Provides higher-level operations and event notifications.

Story: MIG-076
Phase: 6 - God Class DockWidget Migration
Pattern: Strangler Fig - Gradual extraction
"""

import logging
import os
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass

try:
    from qgis.PyQt.QtCore import pyqtSignal, QObject
except ImportError:
    from PyQt6.QtCore import pyqtSignal, QObject

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


def _file_writable(path: str) -> bool:
    """Whether the project file ``path`` can be written back (a stub for the tests)."""
    return bool(path) and os.access(path, os.W_OK)


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
        # The project whose favorites the SQLite holds once read from its file (sync_with_project): only then are
        # changes written back to it, never into the project of before (2026-11-24).
        self._synced_project_uuid: Optional[str] = None
        # Ids written into the project entry but not saved yet (the mirror writes at each change): the file does
        # not hold them, so a sync must not remember them as its own (audit of 2026-11-24 #2: F5 bound the
        # project again, the sync remembered them, and the favorite made here was dropped as 'removed elsewhere'
        # at the next opening). Emptied when the file takes them (projectSaved) or another project is read.
        self._unsaved_entry_ids: Set[str] = set()
        # Binds the current project when none is (set_bind_callback): a favorite added after Project > Close
        self._bind_project = None
        # Whether the file of the project read cannot be written back (read-only): the mirror then stays out of
        # it (no dirty project on opening), and the dialog says a change lasts for the session (audit of 2026-11-24).
        self.project_read_only = False
        self.favorites_changed.connect(self._mirror_to_project)
        self._watch_project()

    def _watch_project(self) -> None:
        """A project being cleared or read stops the copy until its favorites are read (review of 2026-11-24: between
        the reading of project B and the deferred set_database, a change wrote the favorites of A into B); a project
        saved is what its file now holds."""
        try:
            from qgis.core import QgsProject
            project = QgsProject.instance()
            project.cleared.connect(self._on_project_cleared)
            project.readProject.connect(self._forget_synced_project)
            project.projectSaved.connect(self._on_project_saved)
        except Exception as e:  # no QGIS project here (the API without QGIS, some tests)
            logger.debug(f"FavoritesService: project signals not watched: {e}")

    def teardown(self) -> None:
        """The plugin is unloaded (FilterMateApp.cleanup): the project no longer calls this service, whose
        favorites_changed reached the widgets of the unloaded panel at the next project closed."""
        self._bind_project = None
        try:
            from qgis.core import QgsProject
            project = QgsProject.instance()
            for signal, slot in ((project.cleared, self._on_project_cleared),
                                 (project.readProject, self._forget_synced_project),
                                 (project.projectSaved, self._on_project_saved)):
                try:
                    signal.disconnect(slot)
                except (TypeError, RuntimeError):  # not connected (no QGIS project when created)
                    pass
        except Exception as e:  # no QGIS project here
            logger.debug(f"FavoritesService: project signals not released: {e}")

    def set_bind_callback(self, callback) -> None:
        """``callback()`` binds the current project (FilterMateApp.ensure_project_bound); called before a favorite
        is added, imported or duplicated while no project is bound."""
        self._bind_project = callback

    @property
    def is_bound(self) -> bool:
        """Whether the favorites are those of a project (set_database), not let go since a project was closed."""
        return bool(self._favorites_manager and getattr(self._favorites_manager, "_project_uuid", None))

    def _bound_for_writing(self) -> bool:
        """Bind the current project first when none is (Project > Close, a project that failed to read): a
        favorite made then goes to the project on screen. False when none could be bound: nothing is written."""
        if not self.is_bound and self._bind_project is not None:
            try:
                self._bind_project()
            except Exception as e:
                logger.warning(f"Favorites: the current project could not be bound: {e}")
        if not self.is_bound:
            logger.warning("Favorites: no project bound, nothing written")
            return False
        return True

    def _forget_synced_project(self, *_args) -> None:
        self._synced_project_uuid = None
        self._unsaved_entry_ids = set()

    def _on_project_cleared(self, *_args) -> None:
        """The project is closed (or another one is about to be read): its favorites leave the list, and nothing is
        added under its id any more until FilterMate binds the next project (set_database), or a favorite added binds
        the project on screen first (_bound_for_writing). 2026-11-24: a project closed kept its favorites listed (★ 3
        on an empty project), and a favorite added then went to the closed project, then into its .qgz at its next
        opening."""
        self._synced_project_uuid = None
        self._unsaved_entry_ids = set()
        manager = self._favorites_manager
        if not manager:
            return
        manager._favorites = {}
        manager._project_uuid = None
        self.favorites_changed.emit()

    def _on_project_saved(self, *_args) -> None:
        """The file holds the favorites now: remembered, so that one removed later on another computer goes here."""
        manager = self._favorites_manager
        if not manager or self._synced_project_uuid is None \
                or self._synced_project_uuid != getattr(manager, "_project_uuid", None):
            return
        try:
            manager.remember_file_ids([favorite.id for favorite in manager.get_all_favorites() if favorite.id])
        except Exception as e:
            logger.warning(f"Favorites of the saved project not remembered: {e}")
        self._unsaved_entry_ids = set()

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
        if self._favorites_manager:
            self._synced_project_uuid = None
            self._favorites_manager.set_database(db_path, project_uuid)

            # 2026-11-24: the .qgz of a saved project is the truth for its favorites; the SQLite of this computer
            # takes them (a project opened on another computer, a plugin reinstalled, a favorite removed elsewhere).
            try:
                self.sync_with_project()
            except Exception as e:
                logger.warning(f"Favorites of the project file not read: {e}")

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

    @property
    def count(self) -> int:
        """Get the number of favorites."""
        if not self._favorites_manager:
            return 0
        return self._favorites_manager.count

    def get_current_user(self) -> Optional[str]:
        """Identity that owns the favorites created here (None when unresolved)."""
        if not self._favorites_manager:
            return None
        return self._favorites_manager.get_current_user()

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
        description: str = "",
        layer_id: Optional[str] = None
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
            layer_id: Optional id of the layer (kept when a favorite is duplicated)

        Returns:
            str: Favorite ID if created, None on error
        """
        if not self._favorites_manager:
            logger.error("FavoritesManager not initialized")
            return None
        if not self._bound_for_writing():
            return None

        try:
            # FilterFavorite is imported at top of file
            favorite = FilterFavorite(
                name=name,
                expression=expression,
                layer_name=layer_name,
                layer_id=layer_id,
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

    def get_orphan_favorites(self) -> List["FilterFavorite"]:
        """Favorites of projects never saved, listed nowhere: relisted instead of purged (audit of 2026-11-24,
        decided with the user). Empty when no manager is attached."""
        manager = self._favorites_manager
        if not manager:
            return []
        try:
            return manager.get_orphan_favorites()
        except Exception as e:
            logger.warning(f"Orphan favorites not read: {e}")
            return []

    def adopt_orphan_favorite(self, favorite_id: str) -> Optional[str]:
        """Move the orphan ``favorite_id`` into this project (it travels with it at the next save).

        None when nothing is attached, nothing is bound, or the id is no orphan.
        """
        manager = self._favorites_manager
        if not manager or not self._bound_for_writing():
            return None
        try:
            if favorite_id not in {favorite.id for favorite in manager.get_orphan_favorites()}:
                return None
            if not manager.move_favorite_to_project(favorite_id, getattr(manager, "_project_uuid", None)):
                return None
        except Exception as e:
            logger.warning(f"Orphan favorite not adopted: {e}")
            return None
        self.favorites_changed.emit()
        self._mirror_to_project()
        return favorite_id

    def delete_orphan_favorite(self, favorite_id: str) -> bool:
        """Delete the orphan ``favorite_id`` from the SQLite of this computer."""
        manager = self._favorites_manager
        if not manager:
            return False
        try:
            deleted = manager.delete_orphan_favorite(favorite_id)
        except Exception as e:
            logger.warning(f"Orphan favorite not deleted: {e}")
            return False
        if deleted:
            self.favorites_changed.emit()
        return deleted

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
        except Exception:  # nosec B110 - best-effort version read, non-fatal
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
        if not self._bound_for_writing():
            return FavoriteImportResult(success=False, file_path=file_path, error_message="No project bound")

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
            # A2 (audit 2026-04-29): pass the project explicitly so the
            # domain doesn't reach into QGIS by itself.
            try:
                from qgis.core import QgsProject
                index = LayerSignatureIndex(QgsProject.instance())
            except (ImportError, AttributeError):
                # AttributeError covers headless tests where qgis.core is
                # a MagicMock and QgsProject has no real instance() method.
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

    # ─────────────────────────────────────────────────────────────────
    # Project File (.qgz) Backup/Restore
    # ─────────────────────────────────────────────────────────────────

    def save_to_project_file(self, project: Optional[Any] = None) -> bool:
        """Write the favorites into the project now (they are written at each change anyway, once the project is
        read: see ``sync_with_project``). The menu action and the sharing extension call it.

        Raises:
            FavoritesNotInitialized: if the service has no manager attached.
        """
        if not self._favorites_manager:
            raise FavoritesNotInitialized(
                "FavoritesService.save_to_project_file called before manager was attached"
            )
        try:
            self._mirror_to_project(project)
            return True
        except FavoritesError:
            raise
        except Exception as e:
            logger.error(f"Error saving favorites to project file: {e}")
            raise FavoritePersistenceError("save_to_project_file", e) from e

    def restore_from_project_file(self, project: Optional[Any] = None) -> int:
        """Read the favorites of the project again (``sync_with_project``); the number it carries, 0 without any."""
        if not self._favorites_manager:
            return 0
        try:
            return self.sync_with_project(project)
        except Exception as e:
            logger.error(f"Error restoring favorites from project file: {e}")
            return 0

    @staticmethod
    def _project(project: Optional[Any]) -> Any:
        if project is not None:
            return project
        from qgis.core import QgsProject
        return QgsProject.instance()

    def sync_with_project(self, project: Optional[Any] = None) -> int:
        """The favorites of the project, as its file carries them, in the SQLite of this computer.

        Once a project is saved its file is the truth (decided 2026-11-24): a favorite removed or changed on another
        computer is removed or changed here; the usage stays this computer's. A favorite made here that the file never
        had (not saved yet, or a project this computer cannot write) stays: only what the file had and lost goes. A backup of before (written one session
        late) is merged without copies; a project with none keeps the favorites of this computer. The result is
        written back to the project when it differs, so the next save carries it.

        Returns:
            int: the favorites the project carried, 0 when it carried none.
        """
        from ..domain import project_favorites
        manager = self._favorites_manager
        if not manager:
            return 0
        project = self._project(project)
        self.project_read_only = self.project_file_read_only(project)
        text, _found = project.readEntry(project_favorites.SCOPE, project_favorites.KEY, "")
        stored, authoritative = project_favorites.read_payload(text)
        local = [favorite.to_dict() for favorite in manager.get_all_favorites()]
        known = manager.known_file_ids() if hasattr(manager, "known_file_ids") else []
        wanted = project_favorites.reconcile(local, stored, authoritative, known)
        if project_favorites.project_payload(wanted) != project_favorites.project_payload(local) or \
                {row.get("id") for row in wanted} != {row.get("id") for row in local}:
            manager.replace_project_favorites([FilterFavorite.from_dict(dict(row)) for row in wanted])
            logger.info(f"✓ {len(wanted)} favorite(s) taken from the project file")
        if hasattr(manager, "remember_file_ids"):
            # Only what the file holds: the ids the mirror wrote but nobody saved yet are this computer's, not
            # the file's (audit of 2026-11-24 #2).
            manager.remember_file_ids([row_id for row_id in project_favorites.file_ids(stored)
                                       if row_id not in self._unsaved_entry_ids])
        self._synced_project_uuid = getattr(manager, "_project_uuid", None)
        self._mirror_to_project(project)
        self.favorites_changed.emit()
        return len(stored or [])

    def reload_from_database(self) -> None:
        """Read the favorites of the project from the SQLite again (rows another service wrote, the recovered orphan
        favorites) and write them into the project."""
        if self._favorites_manager and hasattr(self._favorites_manager, "_load_favorites"):
            self._favorites_manager._load_favorites()
            self.favorites_changed.emit()

    @staticmethod
    def project_file_read_only(project: Any) -> bool:
        """Whether the file of ``project`` cannot be written back (read-only): its favorites then live for the
        session, and nothing is written into it (audit of 2026-11-24). A project never saved has no file: it is
        not read-only, its entries travel with it when the user saves."""
        path = getattr(project, "fileName", lambda: "")() or ""
        if not path:
            return False
        try:
            # A project in a database or at a URI has no file to check: QGIS writes it (project_file_writable).
            from ...infrastructure.utils.layer_settings import project_file_writable
            return not project_file_writable(project)
        except Exception:  # noqa: BLE001 - without it, the file decides
            return not _file_writable(path)

    def _mirror_to_project(self, project: Optional[Any] = None) -> None:
        """Write the favorites into the project when they differ from what it holds (an unchanged project stays
        clean). Only for the project they were read from: before ``sync_with_project``, nothing is written."""
        try:
            from ..domain import project_favorites
            manager = self._favorites_manager
            if not manager or not getattr(manager, "_initialized", True):
                return
            if self._synced_project_uuid is None \
                    or self._synced_project_uuid != getattr(manager, "_project_uuid", None):
                return
            project = self._project(project)
            if self.project_file_read_only(project):
                # A read-only file is never marked dirty for favorites (audit of 2026-11-24).
                self.project_read_only = True
                logger.info("Favorites not written into the project: its file is read-only")
                return
            self.project_read_only = False
            favorites = [favorite.to_dict() for favorite in manager.get_all_favorites()]
            text, found = project.readEntry(project_favorites.SCOPE, project_favorites.KEY, "")
            if not favorites and not text:
                return  # a project that never had favorites keeps no entry
            payload = project_favorites.project_payload(favorites)
            if payload != text:
                before = project_favorites.read_payload(text)[0]
                project.writeEntry(project_favorites.SCOPE, project_favorites.KEY, payload)
                after = {str(row["id"]) for row in project_favorites.read_payload(payload)[0] or [] if row.get("id")}
                introduced = after - {str(row["id"]) for row in before or [] if row.get("id")}
                if introduced:
                    self._unsaved_entry_ids |= introduced
                logger.debug(f"Favorites written into the project ({len(favorites)})")
        except Exception as e:  # a slot of favorites_changed: never an error dialog
            logger.warning(f"Favorites not written into the project: {e}")

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
        return self._favorites_manager.get_global_favorites()

    def remove_global_favorite(self, favorite_id: str) -> bool:
        """
        Remove a global favorite.

        Returns:
            bool: True if a global favorite of this id was removed

        Raises:
            FavoritesNotInitialized: if the service has no manager attached.
            FavoritePersistenceError: if the database could not be written.
        """
        if not self._favorites_manager:
            raise FavoritesNotInitialized(
                "FavoritesService.remove_global_favorite called before manager was attached"
            )
        removed = self._favorites_manager.remove_global_favorite(favorite_id)
        if removed:
            self.favorites_changed.emit()
        return removed

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

        success = self._favorites_manager.make_favorite_global(favorite_id)
        if success:
            self.favorites_changed.emit()
        return success

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
        new_id = self._favorites_manager.copy_to_global(favorite_id)
        if new_id:
            self.favorites_changed.emit()
        return new_id

    def import_global_to_project(self, global_favorite_id: str) -> Optional[str]:
        """
        Import a global favorite to the current project.

        Args:
            global_favorite_id: ID of global favorite to import

        Returns:
            New favorite ID if successful, None otherwise
        """
        if not self._favorites_manager or not self._bound_for_writing():
            return None
        new_id = self._favorites_manager.import_global_to_project(global_favorite_id)
        if new_id:
            self.favorites_changed.emit()
        return new_id
