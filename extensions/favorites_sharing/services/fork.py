# -*- coding: utf-8 -*-
"""Fork-side of the favorites-sharing service: trust-boundary path.

EXT-2 stage 2 (audit 2026-04-29): split out from
``FavoritesSharingService`` so the trust boundary (third-party content
landing in the local DB) lives in a dedicated module. Anything that
touches the local DB on behalf of a *shared* favorite belongs here —
the read path stays in :class:`SharedFavoritesQuery`, the writer path
in :class:`BundlePublisher`.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from ..scanner import SharedFavorite

logger = logging.getLogger('FilterMate.FavoritesSharing.Fork')


class FavoritesForkService:
    """Materialize a shared favorite into the user's local favorites DB.

    The forked favorite:
    - gets a new UUID (the original is never touched);
    - preserves the author's ``created_at`` as
      ``_extra.original_created_at``;
    - resets ``use_count`` to 0;
    - has its portable ``layer_signature`` entries re-resolved to
      current-project layer UUIDs via
      :meth:`FavoriteImportHandler.rebind_to_project`;
    - has its expression run through ``sanitize_subset_string`` — a
      poisoned display expression is rejected at fork time, not at
      apply time.
    """

    def fork(
        self,
        shared: SharedFavorite,
        favorites_service: Any,
        override_name: Optional[str] = None,
    ) -> Optional[str]:
        """See class docstring.

        Args:
            shared: The SharedFavorite discovered by the scanner.
            favorites_service: The running :class:`FavoritesService`
                (obtained from ``dockwidget._favorites_service``).
            override_name: When provided, used instead of the bundled
                name (the Fork dialog lets users rename on the fly).

        Returns:
            New favorite id on success, ``None`` otherwise.
        """
        try:
            from filter_mate.core.domain.favorite_import_handler import FavoriteImportHandler
            from filter_mate.core.domain.favorites_manager import FilterFavorite
            from filter_mate.core.domain.layer_signature import LayerSignatureIndex
        except Exception:  # pragma: no cover — plugin package import guard
            logger.exception("Cannot import FilterMate core for Fork")
            return None

        rebound = self._rebind_signatures(
            shared, FavoriteImportHandler, LayerSignatureIndex,
        )

        if not self._sanitize_expression_in_place(rebound, shared.name):
            return None

        self._stamp_provenance(rebound, shared)

        if override_name:
            rebound['name'] = override_name

        # Strip identity fields that would collide with existing rows.
        # v5.1: also strip ``owner`` — a shared bundle should never pin
        # the forker to the author's identity. ``add_favorite`` will
        # re-stamp with the current user via the cascade.
        for key in ('id', 'project_uuid', 'owner'):
            rebound.pop(key, None)
        rebound['use_count'] = 0
        rebound['last_used_at'] = None

        favorite = FilterFavorite.from_dict(rebound)
        favorite.id = None  # Will generate new ID in add_favorite

        new_id = self._persist(favorite, favorites_service)
        if new_id is None:
            return None

        self._emit_favorites_changed(favorites_service)
        self._persist_qgz_backup(favorites_service)

        logger.info(
            f"Forked shared favorite '{favorite.name}' from collection "
            f"'{shared.source.collection_name}' → id={favorite.id}"
        )
        return new_id

    # ── internals -------------------------------------------------------

    def _rebind_signatures(
        self,
        shared: SharedFavorite,
        FavoriteImportHandler,
        LayerSignatureIndex,
    ) -> dict:
        """Resolve portable signatures to current-project layer UUIDs.

        A2 (audit 2026-04-29): pass the project explicitly to the index
        — the domain no longer reaches into QGIS on its own.
        """
        try:
            from qgis.core import QgsProject
            project_for_index = QgsProject.instance()
        except (ImportError, AttributeError):
            # AttributeError covers headless tests where qgis.core is a
            # MagicMock and QgsProject has no real ``instance()`` method.
            project_for_index = None
        return FavoriteImportHandler.rebind_to_project(
            dict(shared.payload),
            LayerSignatureIndex(project_for_index),
            file_version=str(shared.schema_version),
        )

    def _sanitize_expression_in_place(self, rebound: dict, fav_name: str) -> bool:
        """Run the local sanitizer on the (third-party) expression.

        Returns True when the favorite is safe to fork, False otherwise
        — caller bails out without touching the DB. ``rebound`` is
        mutated in place when sanitisation rewrote the expression.
        """
        raw_expr = str(rebound.get('expression') or '')
        if not raw_expr:
            return True
        try:
            try:
                from filter_mate.core.filter import sanitize_subset_string
            except ImportError:
                from core.filter import sanitize_subset_string  # type: ignore
            cleaned_expr = sanitize_subset_string(raw_expr)
        except Exception:
            logger.exception("Sanitizer unavailable; refusing fork to be safe")
            return False
        if not cleaned_expr:
            logger.warning(
                "Refusing fork: shared favorite '%s' carries a non-boolean "
                "expression that the sanitizer rejected.", fav_name,
            )
            return False
        if cleaned_expr != raw_expr:
            logger.info(
                "Sanitized expression on fork of '%s' (length %d → %d)",
                fav_name, len(raw_expr), len(cleaned_expr),
            )
            rebound['expression'] = cleaned_expr
        return True

    def _stamp_provenance(self, rebound: dict, shared: SharedFavorite) -> None:
        """Record where the fork came from in ``_extra`` for round-trip."""
        extra = dict(rebound.get('_extra') or {})
        extra.setdefault('original_created_at', shared.payload.get('created_at'))
        extra.setdefault('forked_from', {
            'collection': shared.source.collection_name,
            'file': shared.source.file_path,
        })
        rebound['_extra'] = extra

    def _persist(self, favorite, favorites_service) -> Optional[str]:
        """Add the favorite to the local DB via the service layer.

        Use ``preserve_timestamps=True`` so the fork keeps the author's
        original ``created_at``. Falls back to a kwarg-less call for
        the rare case where the caller passed a raw FavoritesManager
        without the kwarg.
        """
        manager = getattr(favorites_service, 'favorites_manager', favorites_service)
        add_fn = getattr(manager, 'add_favorite', None)
        if not callable(add_fn):
            logger.error("Fork failed: manager has no add_favorite()")
            return None
        try:
            success = add_fn(favorite, preserve_timestamps=True)
        except TypeError:
            success = add_fn(favorite)
        return favorite.id if success else None

    def _emit_favorites_changed(self, favorites_service) -> None:
        emit_fn = getattr(favorites_service, 'favorites_changed', None)
        if emit_fn is not None and hasattr(emit_fn, 'emit'):
            try:
                emit_fn.emit()
            except Exception:
                pass

    def _persist_qgz_backup(self, favorites_service) -> None:
        backup_fn = getattr(favorites_service, 'save_to_project_file', None)
        if callable(backup_fn):
            try:
                backup_fn()
            except Exception as e:
                logger.debug(f"Post-fork .qgz backup skipped: {e}")
