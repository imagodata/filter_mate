# -*- coding: utf-8 -*-
"""
FilterMate Favorites Manager - Standalone Implementation

Manages filter favorites with SQLite persistence.
Part of EPIC-1 v4.0 architecture cleanup.

Author: FilterMate Team
Date: January 2026
"""

import logging
import json
import uuid
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict, field

from .layer_signature import LayerSignatureIndex
from .remote_layers_normalizer import RemoteLayersNormalizer
from .schema_constants import GLOBAL_PROJECT_UUID

logger = logging.getLogger('FilterMate.FavoritesManager')


class FavoriteScope(Enum):
    """Four scopes a favorite can have (see ``FavoritesManager.list_by_scope``).

    Two independent dimensions combined:

    - **Project** : this project (``project_uuid = <current>``) vs. all
      projects (``project_uuid = GLOBAL_PROJECT_UUID``).
    - **Owner**   : mine (``owner = <current user>``) vs. shared
      (``owner IS NULL`` — visible to everyone on this DB).
    """
    ALL = "all"
    GLOBAL_SHARED = "global_shared"       # project=GLOBAL, owner=NULL
    PROJECT_SHARED = "project_shared"     # project=current, owner=NULL
    GLOBAL_MINE = "global_mine"            # project=GLOBAL, owner=me
    PROJECT_MINE = "project_mine"          # project=current, owner=me


def normalize_remote_layers_keys(remote_layers: Dict[str, Any]) -> Dict[str, Any]:
    """Rekey ``remote_layers`` by ``layer_signature`` and populate display_name.

    Thin wrapper kept for backward compatibility — the actual logic lives
    in :class:`RemoteLayersNormalizer` so the four historical normalisation
    paths (this one, ``_backfill_remote_layer_signatures``,
    ``FavoritesService._strip_project_bindings``,
    ``FavoritesService._rebind_imported_favorite``) cannot drift apart again.
    """
    return RemoteLayersNormalizer.normalize(remote_layers)


@dataclass
class FilterFavorite:
    """Filter favorite data class."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    expression: str = ""
    layer_name: Optional[str] = None
    layer_id: Optional[str] = None
    layer_provider: Optional[str] = None
    description: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    use_count: int = 0
    last_used_at: Optional[str] = None
    remote_layers: Optional[Dict] = None
    spatial_config: Optional[Dict] = None
    # Scope columns (v5.1+): owner is NULL for "shared with everyone" or
    # a user identity string (see core.domain.user_identity). project_uuid
    # is handled at the manager level (not carried on the dataclass) — it
    # maps to the current project or GLOBAL_PROJECT_UUID.
    owner: Optional[str] = None
    # FIX 2026-04-23 (v3): forward-compat escape hatch. Any unknown key
    # encountered in from_dict is stashed here and re-emitted by to_dict, so
    # a JSON file written by a newer plugin version round-trips through an
    # older one without silent data loss. Not persisted to SQLite columns
    # (schema is closed); JSON import/export and .qgz backup preserve it.
    _extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary. Merges ``_extra`` back at the top level so
        unknown fields from future plugin versions survive a round-trip.
        """
        data = asdict(self)
        extra = data.pop('_extra', None) or {}
        # `_extra` never shadows known fields
        for k, v in extra.items():
            if k not in data:
                data[k] = v
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FilterFavorite':
        """Create from dictionary.

        FIX 2026-04-23: remote_layers keys are normalized to signatures
        (``postgres::schema.table`` etc.) when the payload carries one, so
        in-memory representation is consistent regardless of the favorite's
        origin (legacy name-keyed v1/v2, signature-keyed v3, DB row loaded
        before the signature-keying migration). The original layer name is
        preserved as payload['display_name'] for UI.

        v3 forward-compat: unknown keys are retained under ``_extra`` so
        export re-emits them untouched — a newer plugin's JSON never loses
        data when passed through an older installation.
        """
        # Ensure tags is a list
        if 'tags' in data and isinstance(data['tags'], str):
            try:
                data['tags'] = json.loads(data['tags']) if data['tags'] else []
            except (ValueError, TypeError):
                data['tags'] = []

        # Normalize remote_layers keys to signatures (CRIT-3 fix)
        remote = data.get('remote_layers')
        if isinstance(remote, dict) and remote:
            data['remote_layers'] = normalize_remote_layers_keys(remote)

        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        # Everything else is stashed in _extra, minus the few keys we
        # deliberately drop (id/project_uuid during import).
        extra = {
            k: v for k, v in data.items()
            if k not in cls.__dataclass_fields__ and k not in ('project_uuid',)
        }
        if extra:
            known['_extra'] = extra
        return cls(**known)

    def get_layers_count(self) -> int:
        """Get total number of layers (1 + remote layers)."""
        count = 1  # Main layer
        if self.remote_layers:
            count += len(self.remote_layers)
        return count

    def get_display_name(self, max_length: int = 30) -> str:
        """Get truncated display name for UI."""
        if len(self.name) <= max_length:
            return self.name
        return self.name[:max_length - 3] + "..."

    def get_preview(self, max_length: int = 80) -> str:
        """Get expression preview for tooltips."""
        if not self.expression:
            return "(no expression)"
        if len(self.expression) <= max_length:
            return self.expression
        return self.expression[:max_length - 3] + "..."

    def mark_used(self) -> None:
        """Mark favorite as used (increment counter and update timestamp)."""
        self.use_count += 1
        self.last_used_at = datetime.now().isoformat()


class FavoritesManager:
    """
    Manages filter favorites with SQLite persistence.

    Features:
    - CRUD operations for favorites
    - SQLite database storage
    - Usage tracking and statistics
    - Search and filtering
    - Per-project organization
    """

    def __init__(self, db_path: Optional[str] = None, project_uuid: Optional[str] = None):
        """
        Initialize FavoritesManager.

        Args:
            db_path: Path to SQLite database
            project_uuid: Project UUID for favorites isolation
        """
        self._db_path = db_path
        self._project_uuid = project_uuid
        # Current user context — resolved lazily on first use. Callers can
        # override via ``set_current_user()`` for tests or explicit
        # identity switching.
        self._current_user: Optional[str] = None
        self._current_user_resolved: bool = False
        self._favorites: Dict[str, FilterFavorite] = {}
        self._initialized = False

        if db_path and project_uuid:
            self._initialize_database()
            self._load_favorites()

    def set_database(self, db_path: str, project_uuid: str) -> None:
        """
        Set database path and project UUID.

        Args:
            db_path: Path to SQLite database
            project_uuid: Project UUID
        """
        logger.debug("FavoritesManager: Configuring database")
        logger.debug(f"  → Path: {db_path}")
        logger.debug(f"  → Project UUID: {project_uuid}")

        self._db_path = db_path
        self._project_uuid = project_uuid
        self._initialize_database()
        self._load_favorites()

    def _initialize_database(self) -> None:
        """Initialize database schema if needed."""
        if not self._db_path:
            return

        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            # Check if table exists and get its columns
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fm_favorites'")
            table_exists = cursor.fetchone() is not None

            if table_exists:
                # Check existing columns
                cursor.execute("PRAGMA table_info(fm_favorites)")
                existing_columns = {row[1] for row in cursor.fetchall()}

                # Add missing columns to existing table (migration)
                required_columns = {
                    'layer_id': 'TEXT',
                    'layer_provider': 'TEXT',
                    'description': 'TEXT',
                    'tags': 'TEXT',
                    'created_at': 'TEXT',
                    'updated_at': 'TEXT',
                    'use_count': 'INTEGER DEFAULT 0',
                    'last_used_at': 'TEXT',
                    'remote_layers': 'TEXT',
                    'spatial_config': 'TEXT',
                    # v5.1: per-user scope. NULL means "shared" (everyone
                    # who opens this DB sees it); a username string means
                    # "personal to that user". See _backfill_owner_on_migration
                    # for the one-shot migration.
                    'owner': 'TEXT',
                }

                owner_was_missing = 'owner' not in existing_columns

                for col_name, col_type in required_columns.items():
                    if col_name not in existing_columns:
                        logger.info(f"Adding missing column '{col_name}' to fm_favorites table")
                        cursor.execute(f"ALTER TABLE fm_favorites ADD COLUMN {col_name} {col_type}")  # nosec B608

                # One-shot ``owner`` backfill: when the column was just
                # introduced, all existing favorites belong to the user who
                # created them. The safest proxy is "current user" — the
                # person running the migration. Users who prefer the
                # permissive pre-v5.1 behaviour can bulk-update to NULL.
                if owner_was_missing:
                    try:
                        self._backfill_owner_on_migration(cursor)
                    except Exception as exc:
                        logger.debug(f"Owner backfill skipped: {exc}")

                # FIX 2026-04-23 (HIGH-1): one-shot backfill of
                # remote_layers.layer_signature + display_name for rows saved
                # before the v2 portable format. Without the signature, legacy
                # favorites can't be exported or shared across projects. We
                # attempt resolution against the current QgsProject; layers
                # that cannot be resolved stay untouched and will backfill on
                # the next load once they are present.
                try:
                    self._backfill_remote_layer_signatures(cursor)
                except Exception as e:
                    logger.debug(f"Signature backfill skipped: {e}")

                conn.commit()
                logger.debug("fm_favorites table migrated to new schema")
            else:
                # Create new table with full schema
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS fm_favorites (
                        id TEXT PRIMARY KEY,
                        project_uuid TEXT NOT NULL,
                        name TEXT NOT NULL,
                        expression TEXT NOT NULL,
                        layer_name TEXT,
                        layer_id TEXT,
                        layer_provider TEXT,
                        description TEXT,
                        tags TEXT,
                        created_at TEXT,
                        updated_at TEXT,
                        use_count INTEGER DEFAULT 0,
                        last_used_at TEXT,
                        remote_layers TEXT,
                        spatial_config TEXT,
                        owner TEXT
                    )
                """)

                # Create index on project_uuid
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_favorites_project
                    ON fm_favorites(project_uuid)
                """)

                conn.commit()
                logger.debug("fm_favorites table created with full schema")

            # FIX 2026-04-23 (LOW-4): composite index on (project_uuid, name)
            # speeds up get_favorite_by_name / dedup-on-import flows that now
            # run more frequently (Resource Sharing scans + .qgz restore dedup).
            # IF NOT EXISTS makes this safe on both branches (new + migrated).
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_favorites_project_name
                ON fm_favorites(project_uuid, name)
            """)
            # v5.1: owner-scoped queries (project_uuid + owner) are the
            # common hot path when the scope filter is "mine" / "mine this
            # project". Partial index skips rows with NULL owner to keep
            # the index small for the "shared" bulk.
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_favorites_owner
                ON fm_favorites(project_uuid, owner)
                WHERE owner IS NOT NULL
            """)
            conn.commit()

            conn.close()

            self._initialized = True
            logger.debug(f"FavoritesManager: Database initialized at {self._db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize favorites database: {e}")
            self._initialized = False

    def _backfill_owner_on_migration(self, cursor) -> None:
        """Stamp existing rows with the current user when ``owner`` is
        introduced for the first time.

        Rationale (locked with user 2026-04-23): before v5.1 the schema
        carried no identity, so every favorite was implicitly "the one
        who created it on this workstation". The user confirmed they
        want those to migrate to the current user rather than to NULL
        (= shared with everyone), matching the real semantics of who
        *authored* them.

        Idempotent: only touches rows where ``owner IS NULL``. Users
        who prefer a shared default can bulk-update after the fact.
        """
        try:
            from .user_identity import resolve_current_user
        except Exception:
            return
        current = resolve_current_user()
        if not current:
            logger.info(
                "Owner backfill skipped — no user identity resolved; "
                "existing favorites stay shared (owner=NULL)."
            )
            return
        try:
            cursor.execute(
                "UPDATE fm_favorites SET owner = ? WHERE owner IS NULL",
                (current,),
            )
            logger.info(
                f"Owner backfill: stamped {cursor.rowcount} favorite(s) with owner='{current}'"
            )
        except Exception as exc:
            logger.warning(f"Owner backfill update failed: {exc}")

    def _backfill_remote_layer_signatures(self, cursor) -> None:
        """Backfill missing ``layer_signature`` and ``display_name`` in
        persisted favorites' ``remote_layers`` JSON (HIGH-1).

        Only rows whose JSON is missing at least one ``layer_signature``
        are rewritten. Resolution uses the current ``QgsProject`` (via
        :class:`LayerSignatureIndex`) when available; unresolved entries
        keep the legacy name-only shape and will be backfilled on the
        next load when the layer is present.
        """
        try:
            cursor.execute("SELECT id, remote_layers FROM fm_favorites WHERE remote_layers IS NOT NULL")
            rows = cursor.fetchall()
        except Exception as e:
            logger.debug(f"Signature backfill: could not scan rows: {e}")
            return

        index = LayerSignatureIndex()
        # Outside QGIS the index is empty; nothing to backfill.
        if not index.id_to_signature and not index.name_to_signature:
            return

        updated = 0
        for row_id, remote_json in rows:
            if not remote_json:
                continue
            try:
                remote = json.loads(remote_json)
            except (ValueError, TypeError):
                continue

            new_remote, rewrite_needed = RemoteLayersNormalizer.backfill(
                remote,
                id_to_signature=index.id_to_signature,
                name_to_signature=index.name_to_signature,
            )

            if rewrite_needed:
                try:
                    cursor.execute(
                        "UPDATE fm_favorites SET remote_layers = ? WHERE id = ?",
                        (json.dumps(new_remote), row_id),
                    )
                    updated += 1
                except Exception as e:
                    logger.debug(f"Signature backfill: update failed for {row_id}: {e}")

        if updated:
            logger.info(f"✓ Backfilled layer_signature on {updated} favorite(s)")

    def _load_favorites(self) -> None:
        """Load favorites from database."""
        if not self._initialized:
            logger.warning("Cannot load favorites: database not initialized")
            return

        if not self._project_uuid:
            logger.warning("Cannot load favorites: no project UUID set")
            return

        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()

            # Get available columns dynamically
            cursor.execute("PRAGMA table_info(fm_favorites)")
            available_columns = {row[1] for row in cursor.fetchall()}

            # Build SELECT query with only available columns
            columns_to_select = []
            column_map = {
                'id': 'id',
                'name': 'name',
                'expression': 'expression',
                'layer_name': 'layer_name',
                'layer_id': 'layer_id',
                'layer_provider': 'layer_provider',
                'description': 'description',
                'tags': 'tags',
                'created_at': 'created_at',
                'updated_at': 'updated_at',
                'use_count': 'use_count',
                'last_used_at': 'last_used_at',
                'remote_layers': 'remote_layers',
                'spatial_config': 'spatial_config',
                'owner': 'owner',
            }

            for col in column_map.keys():
                if col in available_columns:
                    columns_to_select.append(col)

            select_clause = ', '.join(columns_to_select)

            cursor.execute(f"""
                SELECT {select_clause}
                FROM fm_favorites
                WHERE project_uuid = ?
            """, (self._project_uuid,))  # nosec B608 - select_clause from hardcoded column_map

            self._favorites.clear()

            for row in cursor.fetchall():
                # Build data dict with defaults for missing columns
                data = {
                    'id': row['id'] if 'id' in available_columns else None,
                    'name': row['name'] if 'name' in available_columns else 'Unnamed',
                    'expression': row['expression'] if 'expression' in available_columns else '',
                    'layer_name': row['layer_name'] if 'layer_name' in available_columns else None,
                    'layer_id': row['layer_id'] if 'layer_id' in available_columns else None,
                    'layer_provider': row['layer_provider'] if 'layer_provider' in available_columns else None,
                    'description': row['description'] if 'description' in available_columns else '',
                    'tags': json.loads(row['tags']) if 'tags' in available_columns and row['tags'] else [],
                    'created_at': row['created_at'] if 'created_at' in available_columns else datetime.now().isoformat(),
                    'updated_at': row['updated_at'] if 'updated_at' in available_columns else datetime.now().isoformat(),
                    'use_count': row['use_count'] if 'use_count' in available_columns else 0,
                    'last_used_at': row['last_used_at'] if 'last_used_at' in available_columns else None,
                    'remote_layers': json.loads(row['remote_layers']) if 'remote_layers' in available_columns and row['remote_layers'] else None,
                    'spatial_config': json.loads(row['spatial_config']) if 'spatial_config' in available_columns and row['spatial_config'] else None,
                    'owner': row['owner'] if 'owner' in available_columns else None,
                }
                favorite = FilterFavorite.from_dict(data)
                self._favorites[favorite.id] = favorite

            conn.close()
            logger.info(f"✓ Loaded {len(self._favorites)} favorites for project {self._project_uuid}")
            if len(self._favorites) > 0:
                logger.debug(f"  → Database: {self._db_path}")
                logger.debug(f"  → Favorites: {', '.join([f.name for f in list(self._favorites.values())[:5]])}{'...' if len(self._favorites) > 5 else ''}")

        except Exception as e:
            logger.error(f"Failed to load favorites: {e}")

    @property
    def count(self) -> int:
        """Get number of favorites."""
        return len(self._favorites)

    def get_all_favorites(self) -> List[FilterFavorite]:
        """Get all favorites."""
        return list(self._favorites.values())

    def get_favorite(self, favorite_id: str) -> Optional[FilterFavorite]:
        """Get favorite by ID."""
        return self._favorites.get(favorite_id)

    def get_by_id(self, favorite_id: str) -> Optional[FilterFavorite]:
        """Alias for get_favorite."""
        return self.get_favorite(favorite_id)

    def get_favorite_by_name(self, name: str) -> Optional[FilterFavorite]:
        """Get favorite by name."""
        for fav in self._favorites.values():
            if fav.name == name:
                return fav
        return None

    # ─────────────────────────────────────────────────────────────────
    # User-scope API (v5.1+)
    # ─────────────────────────────────────────────────────────────────

    def set_current_user(self, user: Optional[str]) -> None:
        """Override the current-user identity for this manager.

        When None is passed, the manager falls back to the cascade
        (``APP.USER_IDENTITY → qgis/userName → OS``) the next time an
        identity is needed.
        """
        self._current_user = user
        self._current_user_resolved = True

    def get_current_user(self) -> Optional[str]:
        """Return the identity used to stamp new favorites' ``owner``.

        First call triggers a cascade resolve via
        ``core.domain.user_identity.resolve_current_user`` and caches
        the result on the instance. Subsequent calls are free.
        """
        if self._current_user_resolved:
            return self._current_user
        try:
            from .user_identity import resolve_current_user
        except Exception:
            self._current_user = None
            self._current_user_resolved = True
            return None
        self._current_user = resolve_current_user()
        self._current_user_resolved = True
        return self._current_user

    def list_by_scope(
        self,
        scope: 'FavoriteScope',
        *,
        current_user: Optional[str] = None,
    ) -> List[FilterFavorite]:
        """Filter the in-memory cache by ``(project × owner)`` scope.

        ``current_user`` lets callers pin the identity for a single call
        (e.g. "show Alice's favorites" in an admin tool); omitted, it
        falls back to ``get_current_user()``.
        """
        if scope == FavoriteScope.ALL:
            return list(self._favorites.values())

        user = current_user if current_user is not None else self.get_current_user()
        favs = self._favorites.values()

        def _is_mine(fav: FilterFavorite) -> bool:
            return user is not None and fav.owner == user

        def _is_shared(fav: FilterFavorite) -> bool:
            return fav.owner is None

        # _load_favorites only loads the current project's rows into the
        # cache, so "project" filters boil down to "not global".
        project_uuid = self._project_uuid or GLOBAL_PROJECT_UUID

        def _is_global(fav_project_uuid: Optional[str]) -> bool:
            # Rows loaded into memory don't carry their own project_uuid
            # (manager scopes the load). A global row sitting in the
            # cache must have been fetched explicitly via
            # ``get_global_favorites`` — those rows have no project_uuid
            # attribute on the dataclass, so we approximate "global" as
            # "the manager's project is GLOBAL".
            return project_uuid == GLOBAL_PROJECT_UUID

        predicates = {
            FavoriteScope.GLOBAL_SHARED: lambda f: _is_shared(f) and _is_global(None),
            FavoriteScope.PROJECT_SHARED: lambda f: _is_shared(f) and not _is_global(None),
            FavoriteScope.GLOBAL_MINE: lambda f: _is_mine(f) and _is_global(None),
            FavoriteScope.PROJECT_MINE: lambda f: _is_mine(f) and not _is_global(None),
        }
        pred = predicates.get(scope)
        if pred is None:
            return list(favs)
        return [f for f in favs if pred(f)]

    def add_favorite(self, favorite: FilterFavorite, preserve_timestamps: bool = False) -> bool:
        """
        Add a new favorite.

        Args:
            favorite: FilterFavorite instance
            preserve_timestamps: When True, keep the favorite's existing
                ``created_at`` / ``updated_at`` instead of overwriting them
                with ``now()``. Used by import / restore paths so
                provenance survives round-trips (CRIT-1).

        Returns:
            bool: True if added successfully
        """
        if not self._initialized:
            logger.warning("Cannot add favorite: database not initialized")
            return False

        try:
            import sqlite3

            # Ensure favorite has an ID
            if not favorite.id:
                favorite.id = str(uuid.uuid4())

            # FIX 2026-04-23 (CRIT-1): don't stomp timestamps when caller
            # supplied them (restore_from_project_file, import_favorites, etc.).
            # Only set them when missing, so a legacy favorite with empty
            # created_at still gets a sensible default.
            if not preserve_timestamps or not favorite.created_at:
                favorite.created_at = datetime.now().isoformat()
            if not preserve_timestamps or not favorite.updated_at:
                favorite.updated_at = favorite.created_at

            # v5.1: auto-stamp owner from the resolved current user when
            # the caller didn't specify one. ``preserve_timestamps`` also
            # signals an import/restore path — we never stomp an
            # explicitly-set owner coming from a bundle / qgz backup.
            if favorite.owner is None and not preserve_timestamps:
                resolved = self.get_current_user()
                if resolved:
                    favorite.owner = resolved

            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO fm_favorites (
                    id, project_uuid, name, expression, layer_name, layer_id,
                    layer_provider, description, tags, created_at, updated_at,
                    use_count, last_used_at, remote_layers, spatial_config, owner
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                favorite.id,
                self._project_uuid,
                favorite.name,
                favorite.expression,
                favorite.layer_name,
                favorite.layer_id,
                favorite.layer_provider,
                favorite.description,
                json.dumps(favorite.tags) if favorite.tags else None,
                favorite.created_at,
                favorite.updated_at,
                favorite.use_count,
                favorite.last_used_at,
                json.dumps(favorite.remote_layers) if favorite.remote_layers else None,
                json.dumps(favorite.spatial_config) if favorite.spatial_config else None,
                favorite.owner,
            ))

            conn.commit()
            conn.close()

            self._favorites[favorite.id] = favorite
            logger.info(f"✓ Favorite '{favorite.name}' saved to database (ID: {favorite.id}, Project: {self._project_uuid})")
            logger.debug(f"  → Database: {self._db_path}")
            logger.debug(f"  → Expression: {favorite.expression[:80]}..." if len(favorite.expression) > 80 else f"  → Expression: {favorite.expression}")
            return True

        except Exception as e:
            logger.error(f"Failed to add favorite: {e}")
            return False

    def remove_favorite(self, favorite_id: str) -> bool:
        """Remove a favorite.

        FIX 2026-04-23 (MED-5): returns False with a log warning when the
        database was not initialised OR the row is unknown — the UI layer
        must decide whether to surface that failure. The previous silent
        False return made deleted-UI/remaining-in-DB divergence invisible.
        """
        if not self._initialized:
            logger.warning(
                f"remove_favorite({favorite_id}): DB not initialised — in-memory "
                "entry kept, UI state and SQLite will diverge. Caller should show a warning."
            )
            return False
        if favorite_id not in self._favorites:
            logger.debug(f"remove_favorite({favorite_id}): no such id in cache")
            return False

        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM fm_favorites WHERE id = ?", (favorite_id,))

            conn.commit()
            conn.close()

            del self._favorites[favorite_id]
            logger.info(f"Removed favorite: {favorite_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove favorite: {e}")
            return False

    def update_favorite(
        self,
        favorite_id: str,
        *,
        bump_updated_at: bool = True,
        **kwargs,
    ) -> bool:
        """Update a favorite.

        FIX 2026-04-23 (HIGH-3): ``updated_at`` is bumped only when
        ``bump_updated_at`` stays ``True``. Pass ``False`` to mutate
        non-content fields (use_count, last_used_at) without polluting
        the "last content modification" timestamp — usage stats and
        content edits carry distinct semantics now.
        """
        if not self._initialized or favorite_id not in self._favorites:
            return False

        try:
            import sqlite3

            favorite = self._favorites[favorite_id]

            # Update fields
            for key, value in kwargs.items():
                if hasattr(favorite, key):
                    setattr(favorite, key, value)

            if bump_updated_at:
                favorite.updated_at = datetime.now().isoformat()

            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE fm_favorites SET
                    name = ?, expression = ?, layer_name = ?, layer_id = ?,
                    layer_provider = ?, description = ?, tags = ?, updated_at = ?,
                    use_count = ?, last_used_at = ?, remote_layers = ?, spatial_config = ?,
                    owner = ?
                WHERE id = ?
            """, (
                favorite.name,
                favorite.expression,
                favorite.layer_name,
                favorite.layer_id,
                favorite.layer_provider,
                favorite.description,
                json.dumps(favorite.tags) if favorite.tags else None,
                favorite.updated_at,
                favorite.use_count,
                favorite.last_used_at,
                json.dumps(favorite.remote_layers) if favorite.remote_layers else None,
                json.dumps(favorite.spatial_config) if favorite.spatial_config else None,
                favorite.owner,
                favorite_id
            ))

            conn.commit()
            conn.close()

            logger.info(f"Updated favorite: {favorite.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to update favorite: {e}")
            return False

    def increment_use_count(self, favorite_id: str) -> bool:
        """Increment use count for a favorite.

        Usage stats update last_used_at but NOT updated_at (HIGH-3).
        """
        if favorite_id not in self._favorites:
            return False

        self._favorites[favorite_id].use_count += 1
        self._favorites[favorite_id].last_used_at = datetime.now().isoformat()

        return self.update_favorite(
            favorite_id,
            bump_updated_at=False,
            use_count=self._favorites[favorite_id].use_count,
            last_used_at=self._favorites[favorite_id].last_used_at,
        )

    def search_favorites(self, query: str) -> List[FilterFavorite]:
        """Search favorites by name, expression, or tags."""
        query_lower = query.lower()
        results = []

        for fav in self._favorites.values():
            if (query_lower in fav.name.lower() or
                query_lower in fav.expression.lower() or
                    any(query_lower in tag.lower() for tag in fav.tags)):
                results.append(fav)

        return results

    def get_recent_favorites(self, limit: int = 10) -> List[FilterFavorite]:
        """Get recently used favorites."""
        favorites = [f for f in self._favorites.values() if f.last_used_at]
        favorites.sort(key=lambda f: f.last_used_at or "", reverse=True)
        return favorites[:limit]

    def get_most_used_favorites(self, limit: int = 10) -> List[FilterFavorite]:
        """Get most frequently used favorites."""
        favorites = list(self._favorites.values())
        favorites.sort(key=lambda f: f.use_count, reverse=True)
        return favorites[:limit]

    def save_to_project(self) -> None:
        """Save favorites to project (no-op, already persisted)."""
        # Favorites are saved to database immediately in add/update/remove
        logger.debug("save_to_project called (favorites already persisted)")

    def load_from_project(self) -> None:
        """Load favorites from project."""
        self._load_favorites()

    def load_from_database(self) -> None:
        """Reload favorites from database."""
        self._load_favorites()

    # ─────────────────────────────────────────────────────────────────
    # Global Favorites Support
    # ─────────────────────────────────────────────────────────────────

    def get_global_favorites(self) -> List[FilterFavorite]:
        """
        Get all global favorites (available in all projects).

        Returns:
            List of global FilterFavorite objects
        """
        if not self._initialized or not self._db_path:
            return []

        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, name, expression, layer_name, layer_id,
                       layer_provider, description, tags, created_at,
                       updated_at, use_count, last_used_at,
                       remote_layers, spatial_config
                FROM fm_favorites
                WHERE project_uuid = ?
                ORDER BY name
            """, (GLOBAL_PROJECT_UUID,))

            global_favorites = []
            for row in cursor.fetchall():
                data = {
                    'id': row['id'],
                    'name': row['name'],
                    'expression': row['expression'],
                    'layer_name': row['layer_name'],
                    'layer_id': row['layer_id'],
                    'layer_provider': row['layer_provider'],
                    'description': row['description'],
                    'tags': json.loads(row['tags']) if row['tags'] else [],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'use_count': row['use_count'] or 0,
                    'last_used_at': row['last_used_at'],
                    'remote_layers': json.loads(row['remote_layers']) if row['remote_layers'] else None,
                    'spatial_config': json.loads(row['spatial_config']) if row['spatial_config'] else None,
                }
                global_favorites.append(FilterFavorite.from_dict(data))

            conn.close()
            logger.debug(f"Loaded {len(global_favorites)} global favorites")
            return global_favorites

        except Exception as e:
            logger.error(f"Failed to load global favorites: {e}")
            return []

    def get_all_with_global(self) -> List[FilterFavorite]:
        """
        Get all favorites including global ones.

        Returns:
            List of FilterFavorite (project-specific + global)
        """
        project_favorites = self.get_all_favorites()
        global_favorites = self.get_global_favorites()

        # Combine and sort by name
        all_favorites = project_favorites + global_favorites
        all_favorites.sort(key=lambda f: f.name.lower())

        return all_favorites

    def make_favorite_global(self, favorite_id: str) -> bool:
        """
        Make a favorite global (available in all projects).

        Args:
            favorite_id: ID of favorite to make global

        Returns:
            True if successful
        """
        if not self._initialized or favorite_id not in self._favorites:
            return False

        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            # Ensure global project exists
            cursor.execute(
                "SELECT project_id FROM fm_projects WHERE project_id = ?",
                (GLOBAL_PROJECT_UUID,)
            )
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO fm_projects VALUES(
                        ?, datetime(), datetime(),
                        '__GLOBAL__', '__GLOBAL_FAVORITES__', '{}'
                    )
                """, (GLOBAL_PROJECT_UUID,))

            # Update favorite to global project
            cursor.execute("""
                UPDATE fm_favorites
                SET project_uuid = ?, updated_at = ?
                WHERE id = ?
            """, (GLOBAL_PROJECT_UUID, datetime.now().isoformat(), favorite_id))

            conn.commit()
            conn.close()

            # Remove from local cache
            del self._favorites[favorite_id]

            logger.info(f"✓ Made favorite {favorite_id} global")
            return True

        except Exception as e:
            logger.error(f"Error making favorite global: {e}")
            return False

    def copy_to_global(self, favorite_id: str) -> Optional[str]:
        """
        Copy a favorite to global (keeps original in project).

        Args:
            favorite_id: ID of favorite to copy

        Returns:
            New favorite ID if successful, None otherwise
        """
        if favorite_id not in self._favorites:
            return None

        favorite = self._favorites[favorite_id]

        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            # Ensure global project exists
            cursor.execute(
                "SELECT project_id FROM fm_projects WHERE project_id = ?",
                (GLOBAL_PROJECT_UUID,)
            )
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO fm_projects VALUES(
                        ?, datetime(), datetime(),
                        '__GLOBAL__', '__GLOBAL_FAVORITES__', '{}'
                    )
                """, (GLOBAL_PROJECT_UUID,))

            # Create new global favorite
            new_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO fm_favorites (
                    id, project_uuid, name, expression, layer_name, layer_id,
                    layer_provider, description, tags, created_at, updated_at,
                    use_count, last_used_at, remote_layers, spatial_config
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                new_id,
                GLOBAL_PROJECT_UUID,
                f"{favorite.name} (Global)",
                favorite.expression,
                favorite.layer_name,
                favorite.layer_id,
                favorite.layer_provider,
                favorite.description,
                json.dumps(favorite.tags) if favorite.tags else None,
                now,
                now,
                0,
                None,
                json.dumps(favorite.remote_layers) if favorite.remote_layers else None,
                json.dumps(favorite.spatial_config) if favorite.spatial_config else None,
            ))

            conn.commit()
            conn.close()

            logger.info(f"✓ Copied favorite to global: {new_id}")
            return new_id

        except Exception as e:
            logger.error(f"Error copying favorite to global: {e}")
            return None

    def import_global_to_project(self, global_favorite_id: str) -> Optional[str]:
        """
        Import a global favorite to the current project.

        Args:
            global_favorite_id: ID of global favorite to import

        Returns:
            New favorite ID if successful, None otherwise
        """
        if not self._initialized or not self._project_uuid:
            return None

        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get global favorite
            cursor.execute(
                "SELECT * FROM fm_favorites WHERE id = ? AND project_uuid = ?",
                (global_favorite_id, GLOBAL_PROJECT_UUID)
            )
            row = cursor.fetchone()

            if not row:
                conn.close()
                return None

            # Create new project-specific favorite
            new_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO fm_favorites (
                    id, project_uuid, name, expression, layer_name, layer_id,
                    layer_provider, description, tags, created_at, updated_at,
                    use_count, last_used_at, remote_layers, spatial_config
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                new_id,
                self._project_uuid,
                row['name'].replace(' (Global)', ''),
                row['expression'],
                row['layer_name'],
                row['layer_id'],
                row['layer_provider'],
                row['description'],
                row['tags'],
                now,
                now,
                0,
                None,
                row['remote_layers'],
                row['spatial_config'],
            ))

            conn.commit()
            conn.close()

            # Reload favorites
            self._load_favorites()

            logger.info(f"✓ Imported global favorite to project: {new_id}")
            return new_id

        except Exception as e:
            logger.error(f"Error importing global favorite: {e}")
            return None
