# -*- coding: utf-8 -*-
"""Headless config helpers for :class:`PublishFavoritesDialog`.

EXT-1 stage 1 (audit 2026-04-29): the two pre-fill helpers
(``read_config_defaults`` + ``resolve_remote_repo_manager``) live in
their own module so they can be unit-tested without instantiating Qt.
The dialog stays in charge of its widgets but reads its initial state
from here.

Pure-Python on purpose: anything that touches a QWidget belongs in
the dialog; anything that reads ENV_VARS / extension config belongs
here. Same boundary the EXT-2 split established for the service.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ..remote_repo_manager import RemoteRepoManager
from ..service import FavoritesSharingService

logger = logging.getLogger('FilterMate.FavoritesSharing.UI.PublishModel')


def resolve_remote_repo_manager(
    sharing_service: Optional[FavoritesSharingService],
) -> Optional[RemoteRepoManager]:
    """Return the RemoteRepoManager registered on the owning extension.

    Falls back to None when no extension is wired (legacy tests) or
    when the service isn't registered — the dialog then renders its
    pre-v5 behavior (scanned collections only, no git).
    """
    extension = getattr(sharing_service, "extension", None)
    if extension is None:
        return None
    mgr = extension.get_service("remote_repos") if hasattr(extension, "get_service") else None
    if isinstance(mgr, RemoteRepoManager):
        return mgr
    return None


def read_config_defaults(
    sharing_service: Optional[FavoritesSharingService],
) -> Dict[str, Any]:
    """Load pre-fill values from FilterMate config.

    Prefers the owning extension's typed accessors (single source of
    truth); falls back to a direct ENV_VARS lookup when the dialog is
    instantiated without an extension (legacy tests).

    The returned dict always carries the same shape so callers can
    index without defensive ``.get()`` chains:

        {
            'default_publish_collection': str,
            'default_publish_metadata': {
                'author': str, 'license': str, 'homepage': str,
            },
        }
    """
    defaults: Dict[str, Any] = {
        'default_publish_collection': '',
        'default_publish_metadata': {
            'author': '', 'license': '', 'homepage': '',
        },
    }

    extension = getattr(sharing_service, "extension", None)
    if extension is not None:
        try:
            defaults['default_publish_collection'] = (
                extension.get_default_publish_collection()
            )
            defaults['default_publish_metadata'] = (
                extension.get_default_publish_metadata()
            )
            return defaults
        except Exception as exc:
            logger.debug("Extension config accessors failed: %s", exc)

    # Fallback — direct ENV_VARS lookup when no extension is available.
    try:
        from filter_mate.config.config import ENV_VARS, _get_option_value
        cfg = (ENV_VARS.get("CONFIG_DATA", {}) or {}) \
            .get("EXTENSIONS", {}) \
            .get("favorites_sharing", {})
        defaults['default_publish_collection'] = str(
            _get_option_value(cfg.get("default_publish_collection"), default="") or ""
        )
        meta = _get_option_value(
            cfg.get("default_publish_metadata"),
            default={'author': '', 'license': '', 'homepage': ''},
        ) or {}
        if isinstance(meta, dict):
            for k in ('author', 'license', 'homepage'):
                defaults['default_publish_metadata'][k] = str(meta.get(k) or '')
    except Exception:
        pass
    return defaults
