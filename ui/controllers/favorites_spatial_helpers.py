# -*- coding: utf-8 -*-
"""Pure helper functions for the favorites spatial-config code path.

F4 step 3 phase 1 (2026-04-28): the controller used to host these as
``@staticmethod`` decorators on ``FavoritesController``. The full god-
class découpage (Phase 3) will introduce ``FavoritesSpatialHandler``
that mutates dockwidget state via a ``DockwidgetSurface`` Protocol.
These two functions are stateless, depend only on a
``QgsVectorLayer``, and read more naturally as module-level functions
— they migrate now so phase 3 lands smaller.

See ``project_f4_step3_spatial_handler_design_2026_04_28.md`` for the
full design.
"""

from __future__ import annotations

import logging
from typing import Any

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
