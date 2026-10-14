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
    """State of every filtered raster / point cloud layer of the project."""
    from .snapshots import take_snapshot
    project = project or QgsProject.instance()
    entries = []
    for layer in project.mapLayers().values():
        kind = _kind(layer)
        if not getattr(kind, 'is_coverage', False):
            continue
        snapshot = take_snapshot(layer, kind)
        if not snapshot.derived and not snapshot.subset:
            continue
        entry = snapshot.to_dict()
        entry['layer_name'] = layer.name()
        entries.append(entry)
    return entries


def _resolve(project: QgsProject, entry: Dict):
    layer = project.mapLayer(entry.get('layer_id', ''))
    if layer is not None:
        return layer
    for candidate in project.mapLayersByName(entry.get('layer_name', '')):
        if is_coverage_layer(candidate):
            return candidate
    return None


def apply(entries: List[Dict], service=None, project: Optional[QgsProject] = None, synchronous: bool = False) -> int:
    """Re-apply captured raster / point cloud states; returns the number of layers handled."""
    from ....core.domain.cross_filter import CrossFilterRequest, TargetSpec
    from ....core.services.cross_filter_service import get_cross_filter_service
    from .snapshots import registry, restore_snapshot, take_snapshot
    from .source_jobs import FixedGeometrySourceJob
    project = project or QgsProject.instance()
    service = service or get_cross_filter_service()
    registry().install(project)
    handled = 0
    for entry in entries or []:
        layer = _resolve(project, entry)
        if layer is None:
            logger.warning(f"[FM5] favorite: layer '{entry.get('layer_name')}' not found")
            continue
        kind = _kind(layer)
        try:
            stored = LayerSnapshot.from_dict(entry)
        except TypeError:
            continue
        current = take_snapshot(layer, kind)
        original = LayerSnapshot(layer.id(), kind.value, source=current.base_source, provider=current.base_provider,
                                 subset=stored.subset if kind is LayerKind.POINT_CLOUD else '')
        restore_snapshot(layer, original)
        if stored.derived and stored.geometry_wkt:
            request = CrossFilterRequest(source_layer_id=f"favorite:{layer.id()}", source_kind=LayerKind.OTHER,
                                         targets=(TargetSpec(layer.id(), kind),), predicates=('Intersect',))
            service.run(request, FixedGeometrySourceJob(layer, stored.geometry_wkt), synchronous=synchronous)
        handled += 1
    return handled
