# -*- coding: utf-8 -*-
"""
Capture and restore the filter state of a layer of any kind, and keep track of
layers whose data source was swapped for a FilterMate derived file.

Derived sources must never be written into a project file: the registry
listens to ``QgsProject.writeMapLayer`` and writes the original source back
in the saved XML (with a ``<filtermate_derived>`` element describing the
filter), while the layer itself keeps showing the filtered data. When the
plugin unloads, :meth:`DerivedSourceRegistry.restore_all` puts every layer
back on its original source.
"""
import json
import logging
from typing import Dict, Optional

from qgis.core import QgsDataProvider, QgsMapLayer, QgsProject

from ....core.domain.filter_state import LayerSnapshot
from ....core.domain.layer_kind import LayerKind

logger = logging.getLogger(__name__)


def _supports_subset(layer: QgsMapLayer) -> bool:
    return hasattr(layer, 'subsetString') and hasattr(layer, 'setSubsetString')


class DerivedSourceRegistry:
    """Layers currently showing a derived source, keyed by layer id."""

    def __init__(self) -> None:
        self._derived: Dict[str, LayerSnapshot] = {}
        self._project: Optional[QgsProject] = None

    # --- bookkeeping --------------------------------------------------------

    def get(self, layer_id: str) -> Optional[LayerSnapshot]:
        return self._derived.get(layer_id)

    def is_derived(self, layer_id: str) -> bool:
        return layer_id in self._derived

    def record(self, snapshot: LayerSnapshot) -> None:
        """Remember (or forget, for a non derived snapshot) the state of a layer."""
        if snapshot.derived:
            self._derived[snapshot.layer_id] = snapshot
        else:
            self._derived.pop(snapshot.layer_id, None)

    def forget(self, layer_id: str) -> None:
        self._derived.pop(layer_id, None)

    def layer_ids(self):
        return list(self._derived)

    # --- project file -------------------------------------------------------

    def install(self, project: Optional[QgsProject] = None) -> None:
        """Connect to ``writeMapLayer`` and ``layersWillBeRemoved`` of the project."""
        project = project or QgsProject.instance()
        if self._project is project:
            return
        self.uninstall()
        project.writeMapLayer.connect(self._on_write_map_layer)
        project.layersWillBeRemoved.connect(self._on_layers_removed)
        self._project = project

    def uninstall(self) -> None:
        if self._project is None:
            return
        for signal, slot in ((self._project.writeMapLayer, self._on_write_map_layer),
                             (self._project.layersWillBeRemoved, self._on_layers_removed)):
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        self._project = None

    def _on_layers_removed(self, layer_ids) -> None:
        for layer_id in layer_ids or []:
            self._derived.pop(layer_id, None)

    def _on_write_map_layer(self, layer, element, document) -> None:
        try:
            snapshot = self._derived.get(layer.id())
        except RuntimeError:
            return
        if snapshot is None or not snapshot.original_source:
            return
        try:
            datasource = element.firstChildElement('datasource')
            if not datasource.isNull():
                while datasource.hasChildNodes():
                    datasource.removeChild(datasource.firstChild())
                datasource.appendChild(document.createTextNode(snapshot.original_source))
            provider = element.firstChildElement('provider')
            if not provider.isNull() and snapshot.original_provider:
                while provider.hasChildNodes():
                    provider.removeChild(provider.firstChild())
                provider.appendChild(document.createTextNode(snapshot.original_provider))
            marker = document.createElement('filtermate_derived')
            marker.setAttribute('state', json.dumps(snapshot.to_dict()))
            element.appendChild(marker)
        except Exception as exc:
            logger.warning(f"[FM5] derived source of '{snapshot.layer_id}' not rewritten in the project: {exc}")

    # --- unload -------------------------------------------------------------

    def restore_all(self, project: Optional[QgsProject] = None) -> int:
        """Put every derived layer back on its original source; returns the count."""
        project = project or QgsProject.instance()
        restored = 0
        for layer_id, snapshot in list(self._derived.items()):
            layer = project.mapLayer(layer_id)
            if layer is None:
                continue
            original = LayerSnapshot(layer_id, snapshot.kind, source=snapshot.original_source,
                                     provider=snapshot.original_provider, subset='')
            try:
                restore_snapshot(layer, original, self)
                restored += 1
            except Exception as exc:
                logger.warning(f"[FM5] '{layer.name()}' not restored to its original source: {exc}")
        self._derived.clear()
        return restored


_registry: Optional[DerivedSourceRegistry] = None


def registry() -> DerivedSourceRegistry:
    """Process-wide registry (one QGIS project at a time)."""
    global _registry
    if _registry is None:
        _registry = DerivedSourceRegistry()
    return _registry


def take_snapshot(layer: QgsMapLayer, kind: LayerKind, derived_registry: Optional[DerivedSourceRegistry] = None) -> LayerSnapshot:
    """Capture the current filter state of ``layer``."""
    reg = derived_registry or registry()
    known = reg.get(layer.id())
    subset = layer.subsetString() if _supports_subset(layer) else ''
    if known is not None and known.source == layer.source():
        return LayerSnapshot(layer.id(), kind.value, source=layer.source(), provider=layer.providerType(),
                             subset=subset, derived=True, original_source=known.original_source,
                             original_provider=known.original_provider, geometry_wkt=known.geometry_wkt,
                             side=known.side)
    return LayerSnapshot(layer.id(), kind.value, source=layer.source(), provider=layer.providerType(), subset=subset)


def restore_snapshot(layer: QgsMapLayer, snapshot: LayerSnapshot,
                     derived_registry: Optional[DerivedSourceRegistry] = None) -> bool:
    """Put ``layer`` back in the state captured by ``snapshot`` (main thread).

    Returns:
        True when something changed.
    """
    reg = derived_registry or registry()
    changed = False
    if snapshot.source and (layer.source() != snapshot.source or layer.providerType() != snapshot.provider):
        layer.setDataSource(snapshot.source, layer.name(), snapshot.provider, QgsDataProvider.ProviderOptions(), False)
        changed = True
        if snapshot.kind == LayerKind.RASTER.value:
            _sync_alpha_band(layer)
    if _supports_subset(layer) and layer.subsetString() != (snapshot.subset or ''):
        try:
            from ....infrastructure.database.sql_utils import safe_set_subset_string
            safe_set_subset_string(layer, snapshot.subset or '')
        except ImportError:
            layer.setSubsetString(snapshot.subset or '')
        changed = True
    reg.record(snapshot)
    if changed:
        layer.triggerRepaint()
    return changed


def _sync_alpha_band(layer) -> None:
    """Point a raster renderer at the alpha band FilterMate may have added (or drop it)."""
    renderer = layer.renderer()
    if renderer is None or not hasattr(renderer, 'setAlphaBand'):
        return
    try:
        provider = layer.dataProvider()
        alpha = -1
        from qgis.core import Qgis
        interpretation = getattr(Qgis, 'RasterColorInterpretation', None)
        alpha_value = interpretation.AlphaBand if interpretation is not None else 6
        for band in range(1, layer.bandCount() + 1):
            if provider.colorInterpretation(band) == alpha_value:
                alpha = band
        renderer.setAlphaBand(alpha)
    except Exception as exc:
        logger.debug(f"[FM5] alpha band not synchronized: {exc}")
