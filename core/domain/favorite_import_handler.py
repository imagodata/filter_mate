# -*- coding: utf-8 -*-
"""Domain transforms applied to favorite dicts on import / export.

Splits the import/export pipeline cleanly:

* :class:`FavoriteImportHandler` owns the **pure transforms**
  (``strip_project_bindings``, ``rebind_to_project``) — no IO, no DB.
* :class:`FavoritesService.import_favorites` keeps the **orchestration**
  (file read, dedup, ``add_favorite`` calls, signal emission).
* :class:`LayerSignatureIndex` provides the **project state** the rebind
  needs.

Before this split, the rebind logic re-walked ``QgsProject`` once per
imported favorite and the strip / rebind / backfill / normalize quartet
each kept its own copy of the provider parsing rules. Now the index is
built once by the orchestrator and handed to the handler, which stays
trivially testable (you mock the index, not ``QgsProject``).
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from .layer_signature import LayerSignatureIndex
from .remote_layers_normalizer import RemoteLayersNormalizer

logger = logging.getLogger(__name__)


class FavoriteImportHandler:
    """Stateless transforms over favorite dicts at the import/export seam.

    Public methods are static — the handler holds no state, callers pass
    in the :class:`LayerSignatureIndex` they want to rebind against.
    Keeping them on a class (rather than module-level functions) gives
    the related transforms a shared docstring location and makes the
    intent visible at call sites: ``FavoriteImportHandler.rebind_*``
    reads as "the import-time transform", not as "some helper".
    """

    @staticmethod
    def strip_project_bindings(fav_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Strip project-specific identifiers from a favorite dict for export.

        Removes the local DB id, project_uuid and source ``layer_id`` so
        the favorite can be re-resolved against any project where a
        layer with the same signature exists. ``remote_layers`` is
        delegated to :class:`RemoteLayersNormalizer` so the strip path
        cannot drift from the other three (CRIT-3 history).
        Resets ``use_count`` and ``last_used_at`` so the importer starts
        fresh stats — the author's runtime metrics aren't meaningful in
        a different project.
        """
        out = dict(fav_dict)  # shallow copy — nested dicts we rewrite are owned
        out.pop('id', None)
        out.pop('project_uuid', None)
        # Drop the source layer_id UUID — the source layer is identified by
        # spatial_config.source_layer_signature (populated at favorite creation).
        out['layer_id'] = None
        remote_layers = out.get('remote_layers')
        if isinstance(remote_layers, dict):
            out['remote_layers'] = RemoteLayersNormalizer.strip(remote_layers)
        out['use_count'] = 0
        out['last_used_at'] = None
        return out

    @staticmethod
    def rebind_to_project(
        fav_data: Dict[str, Any],
        index: LayerSignatureIndex,
        file_version: str = '1.0',
    ) -> Dict[str, Any]:
        """Re-bind an imported favorite to ``index``'s project layer ids.

        For v2 exports (and v1 favorites that happen to carry
        ``layer_signature``), looks up each signature in ``index`` and
        repopulates the local ``layer_id``. When no match is found,
        ``layer_id`` stays ``None`` — the favorite is still usable, but
        the target layers must be resolved at apply-time (see
        ``FavoritesController._restore_filtering_ui_from_favorite``).
        """
        out = dict(fav_data)

        spatial_config = out.get('spatial_config') or {}
        if isinstance(spatial_config, dict):
            source_sig = spatial_config.get('source_layer_signature')
            if source_sig:
                resolved = index.resolve(source_sig)
                if resolved:
                    out['layer_id'] = resolved
                    logger.debug(f"Import rebind: source '{source_sig}' -> {resolved}")

        remote_layers = out.get('remote_layers')
        if isinstance(remote_layers, dict):
            out['remote_layers'] = RemoteLayersNormalizer.rebind(
                remote_layers,
                signature_resolver=index.resolve,
            )

        logger.debug(f"Imported favorite '{out.get('name')}' from v{file_version}")
        return out
