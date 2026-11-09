# -*- coding: utf-8 -*-
"""
Centroids of the target layers, chosen layer by layer (FilterMate 5).

A target layer of FILTERING may be tested by its centroids (point on surface)
instead of its full geometries: faster on large polygons or lines, and the
predicate then reads "the centre of the target ...". It only means something
for line and polygon vector layers: a point layer is its own centroid, and a
raster or point cloud target is clipped by the source geometry, never tested
by geometry.

The choice is stored per source layer in ``filtering.centroid_layers`` (ids of
the targets tested by their centroids). Projects saved before it only have the
global ``filtering.use_centroids_distant_layers`` flag, which applied to every
target: :func:`distant_centroids_for` falls back to it when the list is absent.
"""
from typing import Any, Iterable, List, Mapping, Optional

CENTROID_LAYERS_KEY = 'centroid_layers'
LEGACY_FLAG_KEY = 'use_centroids_distant_layers'
# ``layer_geometry_type`` values (PROJECT_LAYERS infos) of the targets a centroid changes.
CENTROID_GEOMETRY_TYPES = frozenset({'GeometryType.Line', 'GeometryType.Polygon'})


def centroid_eligible(geometry_type: Any) -> bool:
    """Whether a target of ``geometry_type`` can be tested by its centroids (line or polygon layer)."""
    return str(geometry_type or '') in CENTROID_GEOMETRY_TYPES


def distant_centroids_for(layer_id: Optional[str], filtering: Optional[Mapping[str, Any]],
                          default: bool = False) -> bool:
    """Whether the target ``layer_id`` is tested by its centroids.

    Args:
        layer_id: Id of the target layer.
        filtering: ``filtering`` parameters of the source layer (task or PROJECT_LAYERS).
        default: The global flag, used when ``filtering`` has no per-layer list.
    """
    chosen = (filtering or {}).get(CENTROID_LAYERS_KEY)
    if chosen is None:
        return bool(default)
    return bool(layer_id) and layer_id in set(chosen)


def initial_centroid_layers(filtering: Optional[Mapping[str, Any]], eligible_ids: Iterable[str]) -> List[str]:
    """Targets shown with their centroid toggle on when the list of targets is filled.

    The stored list when there is one; otherwise every eligible target if the old
    global flag was on (projects saved before the per-layer choice), none if not.
    """
    filtering = filtering or {}
    eligible = list(eligible_ids)
    chosen = filtering.get(CENTROID_LAYERS_KEY)
    if chosen is not None:
        wanted = set(chosen)
        return [layer_id for layer_id in eligible if layer_id in wanted]
    return eligible if filtering.get(LEGACY_FLAG_KEY) else []


def global_centroid_state(checked_eligible: Iterable[str], centroid_ids: Iterable[str]) -> Optional[bool]:
    """State of the global centroid button for the checked line / polygon targets.

    Returns:
        True when all of them use their centroids, False when none does, None when
        only some do (partial), and False when no such target is checked.
    """
    targets = list(checked_eligible)
    chosen = set(centroid_ids)
    using = [layer_id for layer_id in targets if layer_id in chosen]
    if not targets or not using:
        return False
    return True if len(using) == len(targets) else None
