# -*- coding: utf-8 -*-
"""
Favorites of raster and point cloud layers.

Vector favorites are subset snapshots. Raster and point cloud filters also
change the data source (clipped VRT / COPC), so their state is captured as
:class:`LayerSnapshot` dicts in ``spatial_config['coverage_layers']`` (an
extra key, ignored by older versions) and re-applied by clipping the original
source again with the stored kept area.
"""
import logging
from typing import Dict, List, Optional

from qgis.core import QgsProject

from ....core.domain.filter_state import LayerSnapshot
from ....core.domain.layer_kind import LayerKind

logger = logging.getLogger(__name__)

COVERAGE_KEY = 'coverage_layers'


def _kind(layer):
    try:
        from ..point_cloud_capability import get_layer_kind
        return get_layer_kind(layer)
    except Exception:
        return LayerKind.OTHER


def is_coverage_layer(layer) -> bool:
    return getattr(_kind(layer), 'is_coverage', False)


def capture(project: Optional[QgsProject] = None) -> List[Dict]:
    """State of every filtered raster / point cloud layer of the project.

    A derived layer is stored with its original source, never with a file of
    the session cache (removed when QGIS closes).
    """
    from .snapshots import portable_snapshot, take_snapshot
    project = project or QgsProject.instance()
    entries = []
    for layer in project.mapLayers().values():
        kind = _kind(layer)
        if not getattr(kind, 'is_filter_target', False):
            continue
        try:
            snapshot = take_snapshot(layer, kind)
        except ValueError:
            continue  # an unrelated unsupported tile renderer must not suppress other favorites
        if not snapshot.derived and not snapshot.subset:
            continue
        entry = portable_snapshot(snapshot).to_dict()
        entry['layer_name'] = layer.name()
        entries.append(entry)
    return entries


def _resolve(project: QgsProject, entry: Dict, kind_of=None):
    kind_of = kind_of or _kind
    layer = project.mapLayer(entry.get('layer_id', ''))
    if layer is not None:
        return layer
    for candidate in project.mapLayersByName(entry.get('layer_name', '')):
        if getattr(kind_of(candidate), 'is_filter_target', False):
            return candidate
    return None


def apply(entries: List[Dict], service=None, project: Optional[QgsProject] = None, synchronous: bool = False,
          kind_of=None, applied: Optional[List[str]] = None, run=None,
          failed: Optional[Dict[str, str]] = None) -> int:
    """Re-apply captured raster / point cloud states; returns the number of layers handled.

    Args:
        kind_of: Layer kind function; the default follows the dock options,
            automation passes the class-based kind (no dock, options off).
        applied: When given, receives the ids of the layers handled.
        run: ``run(service, request, source_job) -> str`` clipping a layer
            again and waiting for it, the reason of a failure or ""
            (automation: a remote source is read in a worker, never on main).
            Without it the clip is queued (``service.run``).
        failed: When given, receives ``{layer_id: reason}`` for the layers
            that could not be filtered again (an exception included); they are
            put back as they were and not counted as handled.
    """
    kind_of = kind_of or _kind
    from ....core.domain.cross_filter import CrossFilterRequest, TargetSpec
    from ....core.services.cross_filter_service import get_cross_filter_service
    from .snapshots import base_snapshot, registry, restore_snapshot, take_snapshot
    from .source_jobs import FixedGeometrySourceJob
    project = project or QgsProject.instance()
    service = service or get_cross_filter_service()
    registry().install(project)
    handled = 0
    for entry in entries or []:
        layer = _resolve(project, entry, kind_of)
        if layer is None:
            logger.warning(f"[FM5] favorite: layer '{entry.get('layer_name')}' not found")
            continue
        kind = kind_of(layer)
        if not getattr(kind, 'is_filter_target', False):
            logger.warning(f"[FM5] favorite: '{layer.name()}' is not a raster / point cloud layer here")
            continue
        try:
            stored = LayerSnapshot.from_dict(entry)
        except TypeError:
            continue
        if stored.kind != kind.value:
            logger.warning(f"[FM5] favorite: '{layer.name()}' has a different layer kind")
            continue
        if kind is LayerKind.VECTOR_TILE:
            from .vector_tile_filters import apply_filter, tr
            from ....core.domain.filter_state import CrossOperation
            try:
                before = take_snapshot(layer, kind)
                after = apply_filter(layer, stored.tile_filter)
            except ValueError as exc:  # a style the tile filter cannot handle
                if failed is None:
                    raise
                failed[layer.id()] = str(exc)
                continue
            service.history.push(CrossOperation(layer.id(), ((before, after),), tr('Vector tile favorite')))
            handled += 1
            if applied is not None:
                applied.append(layer.id())
            continue
        current = take_snapshot(layer, kind)
        reason = ''
        try:
            restore_snapshot(layer, base_snapshot(current, stored.subset if kind is LayerKind.POINT_CLOUD else ''))
            if stored.derived and stored.selection and not stored.geometry_wkt:
                from .source_jobs import apply_stored_selection
                if apply_stored_selection(layer, stored) is None:
                    reason = 'the stored raster selection could not be rebuilt'
            elif stored.derived and stored.geometry_wkt:
                request = CrossFilterRequest(source_layer_id=layer.id(), source_kind=LayerKind.OTHER,
                                             targets=(TargetSpec(layer.id(), kind),), predicates=('Intersect',))
                job = FixedGeometrySourceJob(layer, stored.geometry_wkt)
                if run is None:
                    service.run(request, job, synchronous=synchronous)
                else:
                    reason = run(service, request, job)
        except Exception as exc:  # a stored source that no longer opens
            if failed is None:
                raise
            logger.warning(f"[FM5] favorite: '{layer.name()}' not filtered again: {exc}", exc_info=True)
            reason = str(exc) or type(exc).__name__
        if reason and failed is not None:
            # A failure leaves the layer as it was, never on its unfiltered source.
            try:
                restore_snapshot(layer, current)
            except Exception as exc:
                logger.warning(f"[FM5] favorite: '{layer.name()}' not put back: {exc}", exc_info=True)
            failed[layer.id()] = reason
            continue
        handled += 1
        if applied is not None:
            applied.append(layer.id())
    return handled
