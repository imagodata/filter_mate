# -*- coding: utf-8 -*-
"""Pure helper functions for the favorites spatial-config code path.

F4 step 3 phase 1+2 (2026-04-28): the controller used to host these as
methods on ``FavoritesController``. The full god-class découpage
(Phase 3) will introduce ``FavoritesSpatialHandler`` that mutates
dockwidget state via a ``DockwidgetSurface`` Protocol. The functions
in this module are stateless — they take only the data they need
(``QgsVectorLayer``, ``QgsProject``, ``FilterFavorite``, dicts) and
read more naturally as module-level functions. They migrate now so
phase 3 lands smaller and the test surface stays simple.

See ``project_f4_step3_spatial_handler_design_2026_04_28.md`` for the
full design.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def exact_filtered_feature_count(layer: Any) -> int:
    """Count features matching the layer's current ``subsetString`` exactly.

    ``QgsVectorLayer.featureCount()`` is fast but returns an estimate
    on PostgreSQL (pulled from ``pg_class.reltuples``). For EXISTS
    subsets with intersect predicates the estimate often collapses to
    1 even when the real cursor returns hundreds of rows, so the
    favorites manager would display ``1`` everywhere. Iterate the
    filtered cursor with no attributes / no geometry — this is an
    indexed COUNT-like scan that respects ``subsetString`` and stays
    cheap.

    Falls back to ``layer.featureCount()`` if anything goes wrong
    (invalid layer, provider that doesn't honor NoGeometry, …).
    """
    if layer is None:
        return 0
    try:
        if not layer.isValid():
            return 0
    except (RuntimeError, AttributeError):
        return 0

    try:
        from qgis.core import QgsFeatureRequest
        request = QgsFeatureRequest()
        try:
            request.setNoAttributes()
        except (AttributeError, TypeError):
            pass
        try:
            request.setFlags(QgsFeatureRequest.NoGeometry)
        except (AttributeError, TypeError):
            pass
        count = 0
        for _ in layer.getFeatures(request):
            count += 1
        return count
    except Exception as e:
        logger.debug(
            f"exact_filtered_feature_count fallback for "
            f"'{getattr(layer, 'name', lambda: '?')()}': {e}"
        )
        try:
            fallback = layer.featureCount()
            return fallback if fallback is not None and fallback >= 0 else 0
        except Exception:
            return 0


def layer_signature_for(layer: Any) -> str:
    """Build a project-portable signature for a ``QgsMapLayer``.

    Thin wrapper kept for ergonomics — provider-parsing rules live in
    :class:`LayerSignature` (core domain). The wrapper exists because
    callsites in the controller read more naturally as a single import
    than as a long ``LayerSignature.compute(...)`` chain.
    """
    from ...core.domain.layer_signature import LayerSignature
    return LayerSignature.compute(layer)


def should_downgrade_single_selection(
    current_groupbox: Optional[str],
    has_restored_features: bool,
    picker_feature_valid: bool,
    selected_feature_count: int,
) -> bool:
    """Pure predicate: should we swap single_selection -> custom_selection?

    ``single_selection`` aborts when no source feature is available.
    ``custom_selection`` with an empty source expression runs with
    ``skip_source_filter=True`` and filters against the full source
    layer, which is what legacy favourites (no captured
    ``task_feature_ids``) expect.
    """
    if current_groupbox != 'single_selection':
        return False
    if has_restored_features:
        return False
    if picker_feature_valid:
        return False
    if selected_feature_count > 0:
        return False
    return True


def resolve_favorite_source_layer(
    favorite: Any,
    spatial_config: Optional[dict],
    project: Any,
    name_to_layer: Dict[str, Any],
    signature_to_layer: Dict[str, Any],
) -> Any:
    """Find the project layer the favorite was captured against.

    Stronger first: project-portable signature. UUID match next (same
    project as save-time). Last resort: name match.
    """
    sig = spatial_config.get('source_layer_signature') if isinstance(spatial_config, dict) else None
    if sig and sig in signature_to_layer:
        return signature_to_layer[sig]

    layer_id = getattr(favorite, 'layer_id', None)
    if layer_id:
        try:
            layer = project.mapLayer(layer_id)
            if layer is not None:
                return layer
        except (RuntimeError, AttributeError):
            pass

    layer_name = getattr(favorite, 'layer_name', None)
    if layer_name and layer_name in name_to_layer:
        return name_to_layer[layer_name]

    return None


def resolve_remote_layer_entry(
    key: Any,
    payload: Any,
    project: Any,
    name_to_layer: Dict[str, Any],
    signature_to_layer: Dict[str, Any],
) -> Any:
    """Find the QgsMapLayer matching a ``favorite.remote_layers[key]`` entry.

    Resolution order: payload signature -> dict-key signature (CRIT-3
    fix) -> legacy ``layer_id`` UUID -> ``display_name`` (or the dict
    key when it's a plain name).
    """
    if isinstance(payload, dict):
        payload_sig = payload.get('layer_signature')
        if payload_sig and payload_sig in signature_to_layer:
            return signature_to_layer[payload_sig]

    if isinstance(key, str) and '::' in key and key in signature_to_layer:
        return signature_to_layer[key]

    if isinstance(payload, dict):
        legacy_id = payload.get('layer_id')
        if legacy_id:
            try:
                layer = project.mapLayer(legacy_id)
                if layer is not None:
                    return layer
            except (RuntimeError, AttributeError):
                pass

    candidate_name = None
    if isinstance(payload, dict):
        candidate_name = payload.get('display_name')
    if not candidate_name and isinstance(key, str) and '::' not in key:
        candidate_name = key
    if candidate_name and candidate_name in name_to_layer:
        return name_to_layer[candidate_name]

    return None


def favorite_matches_current_layer(
    favorite: Any,
    current_layer: Any,
) -> bool:
    """Decide whether ``task_feature_ids`` from ``favorite`` can be safely
    pushed onto ``current_layer``.

    Matching order (strongest first):

    1. ``spatial_config.source_layer_signature`` matches the current
       layer's signature — portable across projects (v2 favorites).
    2. ``favorite.layer_id`` matches ``current_layer.id()`` — same QGIS
       project.
    3. ``favorite.layer_name`` matches ``current_layer.name()`` —
       last-chance fuzzy.

    Returns ``False`` as soon as we can prove mismatch; returns ``True``
    only with a positive match on at least one of the three.
    """
    if current_layer is None:
        return False

    try:
        current_layer_id = current_layer.id()
    except (RuntimeError, AttributeError):
        current_layer_id = None
    try:
        current_layer_name = current_layer.name()
    except (RuntimeError, AttributeError):
        current_layer_name = None

    spatial_config = getattr(favorite, 'spatial_config', None) or {}
    source_sig = spatial_config.get('source_layer_signature') if isinstance(spatial_config, dict) else None
    if source_sig:
        try:
            current_sig = layer_signature_for(current_layer)
            if current_sig == source_sig:
                return True
        except Exception as e:
            logger.debug(f"Could not compute signature for current layer: {e}")

    fav_layer_id = getattr(favorite, 'layer_id', None)
    if fav_layer_id and current_layer_id and fav_layer_id == current_layer_id:
        return True

    fav_layer_name = getattr(favorite, 'layer_name', None)
    if fav_layer_name and current_layer_name and fav_layer_name == current_layer_name:
        return True

    return False
