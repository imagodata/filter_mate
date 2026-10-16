# -*- coding: utf-8 -*-
"""
Capture and restore the filter state of a layer of any kind, and keep track of
layers whose data source was swapped for a FilterMate derived file.

Derived sources must never be written into a project file: the registry
listens to ``QgsProject.writeMapLayer`` and writes the original source back
in the saved XML (with a ``<filtermate_derived>`` element marking the layer),
while the layer itself keeps showing the filtered data. When the plugin
unloads, :meth:`DerivedSourceRegistry.restore_all` puts every layer back on
its original source.

A layer definition file (``.qlr``, also what copy / paste of layers goes
through) is written by ``QgsLayerDefinition`` without any project signal: a
derived layer exported that way keeps its cache path. Pasted in the same
session, the copy is recognized and registered (``layersAdded``); a ``.qlr``
opened after the session ended points at a removed file.
"""
import dataclasses
import functools
import json
import logging
from typing import Dict, List, Optional, Tuple

from qgis.core import QgsDataProvider, QgsMapLayer, QgsProject, QgsProviderRegistry

from ....core.domain.filter_state import LayerSnapshot
from ....core.domain.layer_kind import LayerKind
from . import cache

logger = logging.getLogger(__name__)

DERIVED_PROPERTY = 'filtermate/derived'
# Dimension added by a height above ground run (hag_task): the original cloud has none.
HAG_DIMENSION = 'HeightAboveGround'


def _supports_subset(layer: QgsMapLayer) -> bool:
    return hasattr(layer, 'subsetString') and hasattr(layer, 'setSubsetString')


class DerivedSourceRegistry:
    """Layers currently showing a derived source, keyed by layer id."""

    def __init__(self) -> None:
        self._derived: Dict[str, LayerSnapshot] = {}
        # Alpha band of the raster renderer on the original source: a clipped
        # VRT may add one (integer raster without NoData), which the original
        # source written in the project does not have.
        self._alpha: Dict[str, int] = {}
        # Projects the hooks are connected to, with their (signal, slot) pairs.
        self._hooks: List[Tuple[QgsProject, tuple]] = []

    # --- bookkeeping --------------------------------------------------------

    def get(self, layer_id: str) -> Optional[LayerSnapshot]:
        return self._derived.get(layer_id)

    def is_derived(self, layer_id: str) -> bool:
        return layer_id in self._derived

    def record(self, snapshot: LayerSnapshot, layer: Optional[QgsMapLayer] = None) -> None:
        """Remember (or forget, for a non derived snapshot) the state of a layer.

        The state is also kept as the ``filtermate/derived`` custom property of
        the layer, saved with the project, so the filter can be rebuilt when the
        project is opened again (see :func:`replay_project_filters`).
        """
        if snapshot.derived:
            self._derived[snapshot.layer_id] = snapshot
        else:
            self.forget(snapshot.layer_id)
        if layer is None:
            try:
                layer = QgsProject.instance().mapLayer(snapshot.layer_id)
            except Exception:
                layer = None
        if layer is not None:
            try:
                if snapshot.derived and (snapshot.geometry_wkt or snapshot.selection):
                    layer.setCustomProperty(DERIVED_PROPERTY, json.dumps(snapshot.to_dict()))
                else:
                    layer.removeCustomProperty(DERIVED_PROPERTY)
            except RuntimeError:
                pass

    def forget(self, layer_id: str) -> None:
        self._derived.pop(layer_id, None)
        self._alpha.pop(layer_id, None)

    def layer_ids(self):
        return list(self._derived)

    def remember_alpha_band(self, layer) -> None:
        """Keep the alpha band of a raster still on its original source (its source is about to change)."""
        if self.is_derived(layer.id()):
            return  # the band of the original source is already known
        renderer = layer.renderer()
        if renderer is not None and hasattr(renderer, 'alphaBand'):
            self._alpha[layer.id()] = renderer.alphaBand()

    def _drop(self, layer) -> None:
        """The user changed the data source of a derived layer since: it is theirs now."""
        self.forget(layer.id())
        try:
            layer.removeCustomProperty(DERIVED_PROPERTY)
        except RuntimeError:
            pass
        logger.info(f"[FM5] '{layer.name()}': data source changed by the user, its filter is forgotten")

    def _adopt(self, layer) -> Optional[LayerSnapshot]:
        """Register a copy of a derived layer (Duplicate Layer, copy / paste); returns its state.

        The copy shows the same derived file under a new id, with the
        ``filtermate/derived`` property of its model. Unknown, it would be
        saved with the path of the session cache, broken once the cache is
        removed, and Unfilter would keep that file as its base. Its model is
        the registered layer showing the same source, else its own property
        when the file belongs to the current session.
        """
        source = layer.source()
        if not source:
            return None
        model = next((known for known in self._derived.values() if known.source == source), None)
        if model is None and cache.in_session(source):
            stored = _stored_snapshot(layer)
            if stored is not None and stored.derived and stored.source == source:
                model = stored
        if model is None:
            return None
        if model.layer_id in self._alpha:
            self._alpha[layer.id()] = self._alpha[model.layer_id]
        snapshot = dataclasses.replace(model, layer_id=layer.id(),
                                       subset=layer.subsetString() if _supports_subset(layer) else '')
        self.record(snapshot, layer)
        logger.info(f"[FM5] '{layer.name()}' is a copy of a filtered layer: its original source is kept")
        return snapshot

    # --- project file -------------------------------------------------------

    def install(self, project: Optional[QgsProject] = None) -> None:
        """Connect the hooks to ``project`` (the current project by default).

        Every project gets its own hooks: installing them on another project
        (automation with ``project=``) keeps those of the current project.
        """
        project = project or QgsProject.instance()
        if any(known is project for known, _ in self._hooks):
            return
        connections = ((project.writeMapLayer, functools.partial(self._on_write_map_layer, project)),
                       (project.layersAdded, self._on_layers_added),
                       (project.layersWillBeRemoved, self._on_layers_removed))
        for signal, slot in connections:
            signal.connect(slot)
        self._hooks.append((project, connections))

    def uninstall(self) -> None:
        for _project, connections in self._hooks:
            for signal, slot in connections:
                try:
                    signal.disconnect(slot)
                except (TypeError, RuntimeError):
                    pass
        self._hooks = []

    def _on_layers_removed(self, layer_ids) -> None:
        for layer_id in layer_ids or []:
            self.forget(layer_id)

    def _on_layers_added(self, layers) -> None:
        for layer in layers or []:
            try:
                if layer.id() not in self._derived:
                    self._adopt(layer)
            except Exception as exc:
                logger.debug(f"[FM5] added layer not checked for a derived source: {exc}")

    def _on_write_map_layer(self, project, layer, element, document) -> None:
        try:
            snapshot = self._derived.get(layer.id()) or self._adopt(layer)
            current = layer.source()
        except RuntimeError:
            return
        if snapshot is None or not snapshot.pristine_source:
            return
        if current != snapshot.source:
            self._drop(layer)  # Change Data Source…: the source written is the user's
            return
        try:
            source = _project_source(project, snapshot.pristine_source, snapshot.pristine_provider, write=True)
            _set_text(element, document, 'datasource', source)
            if snapshot.pristine_provider:
                _set_text(element, document, 'provider', snapshot.pristine_provider)
            renderer = element.firstChildElement('pipe').firstChildElement('rasterrenderer')
            alpha = self._alpha.get(snapshot.layer_id)
            if alpha is not None and not renderer.isNull():
                renderer.setAttribute('alphaBand', str(alpha))
            subset = element.firstChildElement('subset')
            if snapshot.enriched_source and not subset.isNull() and HAG_DIMENSION in subset.text():
                _set_text(element, document, 'subset', '')  # the original cloud would reject it
            # What opening the project needs to clip the layer again
            # (pending_replays): the original source as written, no cache path.
            stored = dataclasses.replace(snapshot, source='', provider='', original_source=source,
                                         original_provider=snapshot.pristine_provider,
                                         enriched_source='', enriched_provider='')
            _set_custom_property(element, DERIVED_PROPERTY, json.dumps(stored.to_dict()))
            _set_tree_layer_source(document, snapshot.layer_id, source, snapshot.pristine_provider)
            marker = document.createElement('filtermate_derived')
            marker.setAttribute('kind', snapshot.kind)
            element.appendChild(marker)
        except Exception as exc:
            logger.warning(f"[FM5] derived source of '{snapshot.layer_id}' not rewritten in the project: {exc}")

    # --- unload -------------------------------------------------------------

    def restore_all(self, project: Optional[QgsProject] = None) -> int:
        """Put every derived layer back on its original source; returns the count.

        A layer goes back to its original source even when that source cannot
        be opened (moved file, offline share): invalid there, it still points
        at its data, not at a cache file removed right after. A point cloud
        keeps its subset when its original source accepts it.
        """
        project = project or QgsProject.instance()
        for layer in list(project.mapLayers().values()):
            try:
                if layer.id() not in self._derived:
                    self._adopt(layer)  # a copy made while the hooks were not connected
            except RuntimeError:
                continue
        restored = 0
        for layer_id, snapshot in list(self._derived.items()):
            layer = project.mapLayer(layer_id)
            if layer is None:
                continue
            try:
                if layer.source() != snapshot.source:
                    self._drop(layer)
                    continue
                self._put_back(layer, snapshot)
                restored += 1
            except Exception as exc:
                logger.warning(f"[FM5] '{layer_id}' not restored to its original source: {exc}")
        self._derived.clear()
        self._alpha.clear()
        return restored

    def _put_back(self, layer, snapshot: LayerSnapshot) -> None:
        """Original source of a derived layer, without going back when it cannot be opened."""
        subset = layer.subsetString() if _supports_subset(layer) else ''
        # A layer turning invalid keeps its style for the day its source is
        # repaired (``<originalStyle>`` in the project): FilterMate's state
        # (property, alpha band of the VRT) goes before the source changes.
        alpha, renderer = self._alpha.get(layer.id()), layer.renderer()
        if alpha is not None and renderer is not None:
            renderer.setAlphaBand(alpha)
        self.record(LayerSnapshot(layer.id(), snapshot.kind), layer)
        layer.setDataSource(snapshot.pristine_source, layer.name(), snapshot.pristine_provider,
                            QgsDataProvider.ProviderOptions(), False)
        if not layer.isValid():
            logger.warning(f"[FM5] '{layer.name()}' put back on its original source, which cannot be opened: "
                           f"{snapshot.pristine_source}")
        else:
            if snapshot.kind == LayerKind.RASTER.value:
                _sync_alpha_band(layer)
            if subset and not _set_subset(layer, subset):
                _set_subset(layer, '')  # HeightAboveGround of an enriched cloud: unknown to the original
        layer.triggerRepaint()


def _stored_snapshot(layer) -> Optional[LayerSnapshot]:
    """The ``filtermate/derived`` property of ``layer``; None when absent or unreadable."""
    raw = layer.customProperty(DERIVED_PROPERTY)
    if not raw:
        return None
    try:
        return LayerSnapshot.from_dict(json.loads(raw))
    except (TypeError, ValueError):
        return None


def _project_source(project: QgsProject, source: str, provider: str, write: bool) -> str:
    """``source`` with its file path relative to ``project`` (write) or absolute again (read).

    The path is taken out of the provider URI (``GPKG:<path>:<table>``,
    ``/vsizip/<path>/<member>``) the way QGIS does it for the layers it
    writes: ``QgsPathResolver`` alone leaves such a URI absolute.
    """
    resolver = project.pathResolver()
    convert = resolver.writePath if write else resolver.readPath
    try:
        providers = QgsProviderRegistry.instance()
        parts = providers.decodeUri(provider, source) if provider else {}
        if parts.get('path'):
            parts['path'] = convert(parts['path'])
            return providers.encodeUri(provider, parts)
    except Exception as exc:
        logger.debug(f"[FM5] '{source}' not decoded by the '{provider}' provider: {exc}")
    return convert(source)


def _set_text(element, document, tag: str, text: str) -> None:
    child = element.firstChildElement(tag)
    if child.isNull():
        return
    while child.hasChildNodes():
        child.removeChild(child.firstChild())
    child.appendChild(document.createTextNode(text))


def _set_custom_property(element, name: str, value: str) -> None:
    """Value of the custom property ``name`` in a written layer (QgsXmlUtils variant map)."""
    options = element.firstChildElement('customproperties').elementsByTagName('Option')
    for index in range(options.count()):
        option = options.at(index).toElement()
        if option.attribute('name') == name:
            option.setAttribute('value', value)


def _set_tree_layer_source(document, layer_id: str, source: str, provider: str) -> None:
    """Source of the layer tree node of a layer (written before the layers)."""
    nodes = document.elementsByTagName('layer-tree-layer')
    for index in range(nodes.count()):
        node = nodes.at(index).toElement()
        if node.attribute('id') == layer_id:
            node.setAttribute('source', source)
            if provider:
                node.setAttribute('providerKey', provider)


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
    subset = layer.subsetString() if _supports_subset(layer) else ''
    if kind is LayerKind.VECTOR:
        # A vector layer is only ever filtered through its subset; its source
        # (which embeds the subset for OGR / PostgreSQL) is not tracked, so a
        # restore never reloads the provider.
        return LayerSnapshot(layer.id(), kind.value, subset=subset)
    known = reg.get(layer.id())
    if known is not None and known.source == layer.source():
        return LayerSnapshot(layer.id(), kind.value, source=layer.source(), provider=layer.providerType(),
                             subset=subset, derived=True, original_source=known.original_source,
                             original_provider=known.original_provider, geometry_wkt=known.geometry_wkt,
                             side=known.side, nodata=known.nodata, enriched_source=known.enriched_source,
                             enriched_provider=known.enriched_provider, selection=known.selection)
    return LayerSnapshot(layer.id(), kind.value, source=layer.source(), provider=layer.providerType(), subset=subset)


def base_snapshot(snapshot: LayerSnapshot, subset: str = '') -> LayerSnapshot:
    """State Unfilter goes back to: the base source of ``snapshot``, with ``subset``.

    The base of a point cloud enriched with HeightAboveGround is its enriched
    file, in the session cache: that state is still derived, so the project
    is written, and unloading restores, the source it was enriched from.
    """
    if snapshot.derived and snapshot.enriched_source:
        return LayerSnapshot(snapshot.layer_id, snapshot.kind, source=snapshot.base_source,
                             provider=snapshot.base_provider, subset=subset, derived=True,
                             original_source=snapshot.base_source, original_provider=snapshot.base_provider,
                             enriched_source=snapshot.enriched_source, enriched_provider=snapshot.enriched_provider)
    return LayerSnapshot(snapshot.layer_id, snapshot.kind, source=snapshot.base_source,
                         provider=snapshot.base_provider, subset=subset)


def restore_snapshot(layer: QgsMapLayer, snapshot: LayerSnapshot,
                     derived_registry: Optional[DerivedSourceRegistry] = None) -> bool:
    """Put ``layer`` back in the state captured by ``snapshot`` (main thread).

    Returns:
        True when something changed.
    """
    reg = derived_registry or registry()
    changed = False
    if snapshot.kind != LayerKind.VECTOR.value and snapshot.source and (
            layer.source() != snapshot.source or layer.providerType() != snapshot.provider):
        if not swap_source(layer, snapshot.source, snapshot.provider, reg):
            raise RuntimeError(f"source '{snapshot.source}' could not be opened")
        changed = True
        if snapshot.kind == LayerKind.RASTER.value:
            _sync_alpha_band(layer)
            if snapshot.provider == 'virtualraster' and snapshot.nodata is not None:
                from .raster_adapter import set_user_nodata
                set_user_nodata(layer, snapshot.nodata)
    if _supports_subset(layer) and layer.subsetString() != (snapshot.subset or ''):
        _set_subset(layer, snapshot.subset or '')
        changed = True
    reg.record(snapshot, layer)
    if changed:
        layer.triggerRepaint()
    return changed


def _set_subset(layer, subset: str) -> bool:
    try:
        from ....infrastructure.database.sql_utils import safe_set_subset_string
        return bool(safe_set_subset_string(layer, subset))
    except ImportError:
        return bool(layer.setSubsetString(subset))


def swap_source(layer, source: str, provider: str, derived_registry: Optional[DerivedSourceRegistry] = None) -> bool:
    """``setDataSource`` that puts the previous source back when the new one is invalid."""
    (derived_registry or registry()).remember_alpha_band(layer)
    previous_source, previous_provider = layer.source(), layer.providerType()
    layer.setDataSource(source, layer.name(), provider, QgsDataProvider.ProviderOptions(), False)
    if layer.isValid():
        return True
    logger.warning(f"[FM5] '{layer.name()}': '{source}' could not be opened, previous source restored")
    layer.setDataSource(previous_source, layer.name(), previous_provider, QgsDataProvider.ProviderOptions(), False)
    return False


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


def pending_replays(project: Optional[QgsProject] = None):
    """Layers of ``project`` holding a derived filter that is not applied (project just opened).

    Returns:
        List of ``(layer, LayerSnapshot)``.
    """
    project = project or QgsProject.instance()
    pending = []
    for layer in project.mapLayers().values():
        try:
            raw = layer.customProperty(DERIVED_PROPERTY)
        except RuntimeError:
            continue
        if not raw:
            continue
        try:
            snapshot = LayerSnapshot.from_dict(json.loads(raw))
        except (TypeError, ValueError):
            layer.removeCustomProperty(DERIVED_PROPERTY)
            continue
        if registry().is_derived(layer.id()) or not (snapshot.geometry_wkt or snapshot.selection):
            continue
        # The project holds the source before any FilterMate change (that of
        # an enriched cloud too), relative when the project uses relative
        # paths: compared once resolved again, so a moved project replays.
        original = _project_source(project, snapshot.pristine_source, snapshot.pristine_provider, write=False)
        if layer.source() != original:
            continue  # the user changed the source since: the stored filter no longer applies
        pending.append((layer, dataclasses.replace(snapshot, original_source=layer.source(),
                                                   original_provider=layer.providerType(),
                                                   enriched_source='', enriched_provider='')))
    return pending
