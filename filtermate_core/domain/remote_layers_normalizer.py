# -*- coding: utf-8 -*-
"""Single source of truth for ``remote_layers`` dict transformations.

Replaces four near-duplicate implementations that previously lived in
``favorites_manager.py`` and ``favorites_service.py`` (CRIT-3 fix had to
be propagated to each one independently — exactly the kind of drift this
module exists to prevent).

Each public method covers one mode:

* :py:meth:`normalize`  — rekey by signature, populate display_name.
* :py:meth:`strip`      — drop project bindings (layer_id) for export.
* :py:meth:`rebind`     — re-bind to the current project's layer UUIDs.
* :py:meth:`backfill`   — fill missing signatures from id/name maps and
  report whether the source dict was rewritten (for SQL UPDATE gating).

All modes share the same dedup convention: when two payloads collapse to
the same canonical key, the first one wins (deterministic across reloads
and stable for round-trips).
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def _canonical_key(payload: Dict[str, Any], fallback_key: str) -> str:
    """Return ``layer_signature`` from the payload, falling back to the
    original dict key when the signature is absent (legacy v1/v2)."""
    signature = payload.get("layer_signature")
    return signature if signature else fallback_key


def _ensure_display_name(payload: Dict[str, Any], original_key: str) -> bool:
    """Populate ``display_name`` from the original key when missing.

    Returns True when the payload was mutated (used by :py:meth:`backfill`
    to decide whether the persisted JSON needs an SQL rewrite).
    """
    if "display_name" not in payload:
        payload["display_name"] = original_key
        return True
    return False


class RemoteLayersNormalizer:
    """Pure-domain transforms over the ``remote_layers`` dict shape.

    None of these methods touch QGIS or SQLite directly — callers inject
    the bits that need runtime context (signature resolvers, id/name
    maps). Keeps the class headless-testable and reusable across both
    the manager (DB-side) and the service (JSON-side) layers.
    """

    @staticmethod
    def normalize(remote_layers: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Rekey by ``layer_signature`` and ensure ``display_name``.

        Used at every ``FilterFavorite.from_dict`` so the in-memory
        representation is consistent regardless of the favorite's origin
        (legacy name-keyed v1/v2, signature-keyed v3, DB row loaded
        before the signature-keying migration).
        """
        if not isinstance(remote_layers, dict) or not remote_layers:
            return remote_layers or {}

        out: Dict[str, Any] = {}
        for key, payload in remote_layers.items():
            if not isinstance(payload, dict):
                out[key] = payload
                continue

            new_payload = dict(payload)
            _ensure_display_name(new_payload, key)
            canonical = _canonical_key(new_payload, key)

            if canonical in out:
                logger.debug(
                    "RemoteLayersNormalizer.normalize: collision on '%s' — "
                    "skipping duplicate entry (original key '%s')",
                    canonical, key,
                )
                continue
            out[canonical] = new_payload
        return out

    @staticmethod
    def strip(remote_layers: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Strip project-specific identifiers for v2/v3 export.

        Drops ``layer_id`` from each payload (resets to None), preserves
        ``layer_signature``, populates ``display_name``, normalises keys
        to signatures so the JSON is deterministic across users.
        """
        if not isinstance(remote_layers, dict) or not remote_layers:
            return remote_layers or {}

        out: Dict[str, Any] = {}
        for key, payload in remote_layers.items():
            if not isinstance(payload, dict):
                out[key] = payload
                continue

            cleaned = {k: v for k, v in payload.items() if k != "layer_id"}
            cleaned["layer_id"] = None
            _ensure_display_name(cleaned, key)
            canonical = _canonical_key(cleaned, key)

            if canonical not in out:
                out[canonical] = cleaned
        return out

    @staticmethod
    def rebind(
        remote_layers: Optional[Dict[str, Any]],
        signature_resolver: Callable[[str], Optional[str]],
    ) -> Dict[str, Any]:
        """Re-bind a portable favorite to the current project's layer UUIDs.

        ``signature_resolver(signature) -> layer_id | None`` is injected so
        this method stays QGIS-free; callers pass the actual project
        lookup (e.g. ``FavoritesService._resolve_signature_to_layer_id``).
        """
        if not isinstance(remote_layers, dict) or not remote_layers:
            return remote_layers or {}

        out: Dict[str, Any] = {}
        for key, payload in remote_layers.items():
            if not isinstance(payload, dict):
                out[key] = payload
                continue

            new_payload = dict(payload)
            _ensure_display_name(new_payload, key)

            sig = new_payload.get("layer_signature")
            if sig:
                resolved = signature_resolver(sig) if signature_resolver else None
                if resolved:
                    new_payload["layer_id"] = resolved
                    logger.debug(
                        "RemoteLayersNormalizer.rebind: '%s' -> %s", sig, resolved
                    )

            canonical = _canonical_key(new_payload, key)
            if canonical not in out:
                out[canonical] = new_payload
        return out

    @staticmethod
    def backfill(
        remote_layers: Optional[Dict[str, Any]],
        id_to_signature: Optional[Dict[str, str]] = None,
        name_to_signature: Optional[Dict[str, str]] = None,
    ) -> Tuple[Dict[str, Any], bool]:
        """Fill missing signatures from the supplied id/name maps.

        Returns ``(new_dict, was_rewritten)``. ``was_rewritten`` is True
        when at least one payload changed (display_name added, signature
        backfilled, key canonicalised, or collision collapsed) — the
        manager uses it to gate the SQL UPDATE so untouched rows never
        get rewritten.
        """
        if not isinstance(remote_layers, dict) or not remote_layers:
            return (remote_layers or {}), False

        id_map = id_to_signature or {}
        name_map = name_to_signature or {}
        rewrite_needed = False
        out: Dict[str, Any] = {}

        for key, payload in remote_layers.items():
            if not isinstance(payload, dict):
                out[key] = payload
                continue

            cleaned = dict(payload)
            if _ensure_display_name(cleaned, key):
                rewrite_needed = True

            if not cleaned.get("layer_signature"):
                legacy_id = cleaned.get("layer_id")
                sig = id_map.get(legacy_id) if legacy_id else None
                if not sig:
                    sig = name_map.get(key)
                if sig:
                    cleaned["layer_signature"] = sig
                    rewrite_needed = True

            canonical = cleaned.get("layer_signature") or key
            if canonical in out:
                rewrite_needed = True  # collision collapse
                continue
            if canonical != key:
                rewrite_needed = True
            out[canonical] = cleaned

        return out, rewrite_needed
