# -*- coding: utf-8 -*-
"""
Capture and restore the filter state of a layer of any kind, and keep track of
layers whose data source was swapped for a FilterMate derived file.

A project file must not depend on a derived source: the registry listens to
``QgsProject.writeMapLayer`` and writes the original source back in the
saved layer (``<maplayer>``, with a ``<filtermate_derived>`` element marking
it) and in its layer tree node, while the layer itself keeps showing the
filtered data. When the plugin unloads,
:meth:`DerivedSourceRegistry.restore_all` puts every layer back on its
original source.

Limits, QGIS giving no hook there:

* references written after the layers keep the cache path: the legend of a
  layout with its own layer tree, a layout map with locked layers, the
  terrain of the project, elevation profiles. They find their layer by id
  first, so they keep working as long as the layer is in the project;
* a layer definition file (``.qlr``, also what copy / paste of layers goes
  through) is written by ``QgsLayerDefinition`` without any project signal:
  a derived layer exported that way keeps its cache path. Pasted in the same
  session, the copy is recognized and registered (``layersAdded``); a
  ``.qlr`` opened after the session ended points at a removed file.
"""
import base64
import dataclasses
import functools
import json
import logging
import re
import weakref
import zlib
from typing import Callable, Dict, List, Optional, Tuple

from qgis.core import QgsDataProvider, QgsMapLayer, QgsProject, QgsProviderRegistry

from ....core.domain.filter_state import LayerSnapshot
from ....core.domain.layer_kind import LayerKind
from . import cache

logger = logging.getLogger(__name__)

DERIVED_PROPERTY = 'filtermate/derived'
# Keys of the property beside the LayerSnapshot fields (from_dict ignores them).
_ALPHA_KEY = 'original_alpha_band'
_ABSOLUTE_KEY = 'original_absolute_source'  # the relative original_source needs the project folder of the save
# Dimension added by a height above ground run (hag_task): the original cloud has none.
HAG_DIMENSION = 'HeightAboveGround'


def _supports_subset(layer: QgsMapLayer) -> bool:
    return hasattr(layer, 'subsetString') and hasattr(layer, 'setSubsetString')


def _redacted_source(source: str) -> str:
    return re.sub(r'https?://[^\s\"<>]+', '[remote source]', source, flags=re.IGNORECASE)


def _same_source(a: str, b: str) -> bool:
    """Same source, also for a file of the cache session spelled differently (link, separators)."""
    if a == b:
        return True
    tail = cache.session_relative(a)
    return tail is not None and tail == cache.session_relative(b)


def _reference(project: QgsProject) -> Callable[[], Optional[QgsProject]]:
    # The current project lives as long as QGIS (its Python wrapper may be
    # rebuilt); the hooks never keep any other project alive.
    if project is QgsProject.instance():
        return lambda: project
    return weakref.ref(project)


class DerivedSourceRegistry:
    """Layers currently showing a derived source, keyed by layer id."""

    def __init__(self) -> None:
        self._derived: Dict[str, LayerSnapshot] = {}
        # Alpha band of the raster renderer on the original source: a clipped
        # VRT may add one (integer raster without NoData), which the original
        # source written in the project does not have.
        self._alpha: Dict[str, int] = {}
        # Projects the hooks are connected to: (reference, writeMapLayer slot).
        self._hooks: List[Tuple[Callable[[], Optional[QgsProject]], Callable]] = []

    # --- bookkeeping --------------------------------------------------------

    def get(self, layer_id: str) -> Optional[LayerSnapshot]:
        return self._derived.get(layer_id)

    def is_derived(self, layer_id: str) -> bool:
        return layer_id in self._derived

    def record(self, snapshot: LayerSnapshot, layer: Optional[QgsMapLayer] = None) -> None:
        """Remember (or forget, for a non derived snapshot) the state of a layer.

        The state is also kept as the ``filtermate/derived`` custom property of
        the layer, saved with the project, so the filter can be rebuilt when the
        project is opened again (see :func:`replay_project_filters`), with the
        alpha band of the original source for a copy of the layer.
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
                if (snapshot.derived and (snapshot.geometry_wkt or snapshot.selection)) or (snapshot.kind == 'vector_tile' and snapshot.renderer_xml):
                    state = snapshot.to_dict()
                    if snapshot.layer_id in self._alpha:
                        state[_ALPHA_KEY] = self._alpha[snapshot.layer_id]
                    raw = json.dumps(state)
                    if snapshot.kind == 'vector_tile':
                        # Large Mapbox styles otherwise produce multi-megabyte
                        # escaped XML strings in a QGIS custom property.
                        raw = 'zlib:' + base64.b64encode(zlib.compress(raw.encode('utf-8'))).decode('ascii')
                    layer.setCustomProperty(DERIVED_PROPERTY, raw)
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

    def original_alpha_band(self, layer_id: str) -> Optional[int]:
        """Alpha band the raster had on its original source; None when unknown."""
        return self._alpha.get(layer_id)

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
        when the file belongs to the current session (sources compared with
        :func:`_same_source`: a copy read back from a ``.qlr`` may spell the
        cache path differently).
        """
        source = layer.source()
        if not source:
            return None
        stored = _snapshot_of(_stored_state(layer))
        if stored is not None and stored.kind == 'vector_tile' and stored.renderer_xml:
            from .vector_tile_filters import edited_snapshot, is_native_reload, restore_style, style_xml, _read_style, _serialize_style
            current = style_xml(layer)
            if current != stored.renderer_xml:
                if is_native_reload(current, stored.renderer_xml):
                    restore_style(layer, stored.renderer_xml)  # repair native property-name loss on reload
                else:
                    stored = edited_snapshot(layer, stored)
                    if stored is None:
                        layer.removeCustomProperty(DERIVED_PROPERTY)
                        return None
            snapshot = dataclasses.replace(stored, layer_id=layer.id(), source=source, provider=layer.providerType(),
                                           renderer_xml=style_xml(layer),
                                           original_renderer_xml=_serialize_style(*_read_style(stored.original_renderer_xml)))
            self.record(snapshot, layer)
            return snapshot
        model = next((known for known in self._derived.values() if _same_source(known.source, source)), None)
        if model is not None and model.kind == 'vector_tile':
            return None  # tile layers sharing a URI can have independent styles
        alpha = self._alpha.get(model.layer_id) if model is not None else None
        if model is None and cache.in_session(source):
            state = _stored_state(layer)
            stored = _snapshot_of(state)
            if stored is not None and stored.derived and _same_source(stored.source, source):
                model, alpha = stored, state.get(_ALPHA_KEY)
        if model is None:
            return None
        if alpha is not None:
            self._alpha[layer.id()] = alpha
        snapshot = dataclasses.replace(model, layer_id=layer.id(), source=source, provider=layer.providerType(),
                                       subset=layer.subsetString() if _supports_subset(layer) else '')
        self.record(snapshot, layer)
        logger.info(f"[FM5] '{layer.name()}' is a copy of a filtered layer: its original source is kept")
        return snapshot

    # --- project file -------------------------------------------------------

    def install(self, project: Optional[QgsProject] = None) -> None:
        """Connect the hooks to ``project`` (the current project by default).

        Every project gets its own hooks: installing them on another project
        (automation with ``project=``) keeps those of the current project, and
        does not keep that project alive.
        """
        project = project or QgsProject.instance()
        self._hooks = [(reference, slot) for reference, slot in self._hooks if reference() is not None]
        if any(reference() is project for reference, _ in self._hooks):
            return
        reference = _reference(project)
        slot = functools.partial(self._on_write_map_layer, reference)
        project.writeMapLayer.connect(slot)
        project.layersAdded.connect(self._on_layers_added)
        project.layersWillBeRemoved.connect(self._on_layers_removed)
        self._hooks.append((reference, slot))

    def uninstall(self) -> None:
        for project, slot in self._live_hooks():
            try:
                connections = ((project.writeMapLayer, slot), (project.layersAdded, self._on_layers_added),
                               (project.layersWillBeRemoved, self._on_layers_removed))
            except RuntimeError:
                continue  # deleted by QGIS: so are its connections
            for signal, connected in connections:
                try:
                    signal.disconnect(connected)
                except (TypeError, RuntimeError):
                    pass
        self._hooks = []

    def _live_hooks(self) -> List[Tuple[QgsProject, Callable]]:
        """``(project, writeMapLayer slot)`` of the hooked projects still alive."""
        return [(project, slot) for project, slot in ((reference(), slot) for reference, slot in self._hooks)
                if project is not None]

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

    def _is_the_users(self, layer, snapshot: LayerSnapshot) -> bool:
        """True when the user changed the data source of a derived layer since (Change Data Source…)."""
        current = layer.source()
        return not _same_source(current, snapshot.source) and not cache.in_session(current)

    def _on_write_map_layer(self, reference, layer, element, document) -> None:
        if any(base.__name__ == 'QgsVectorTileLayer' for base in type(layer).__mro__):
            # Both styles are already portable in the custom property. Never
            # re-enter renderer serialization from QGIS's writeMapLayer hook.
            return
        project = reference()
        try:
            snapshot = self._derived.get(layer.id()) or self._adopt(layer)
            if snapshot is None or not snapshot.pristine_source or project is None:
                return
            if self._is_the_users(layer, snapshot):
                # The source written is the user's; QGIS wrote the custom
                # properties before this signal: the stored filter goes too.
                self._drop(layer)
                _remove_custom_property(element, DERIVED_PROPERTY)
                return
        except Exception as exc:
            logger.debug(f"[FM5] layer not checked for a derived source when written: {exc}")
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
                # The original cloud would reject it: its other terms stay.
                _set_text(element, document, 'subset', without_terms(subset.text(), HAG_DIMENSION))
            if snapshot.geometry_wkt or snapshot.selection:
                # What opening the project needs to clip the layer again
                # (pending_replays): the original source as written, no cache
                # path, and absolute for a project saved elsewhere before that.
                state = portable_snapshot(snapshot, source).to_dict()
                state[_ABSOLUTE_KEY] = snapshot.pristine_source
                _set_custom_property(element, document, DERIVED_PROPERTY, json.dumps(state))
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

        Args:
            project: Only this project; by default the current project and
                every other project the hooks are connected to.
        """
        if project is not None:
            projects = [project]
        else:
            current = QgsProject.instance()
            projects = [current] + [other for other, _ in self._live_hooks() if other is not current]
        restored = 0
        for each in projects:
            try:
                restored += self._restore_project(each)
            except RuntimeError as exc:
                logger.debug(f"[FM5] project gone before its layers were restored: {exc}")
        self._derived.clear()
        self._alpha.clear()
        return restored

    def _restore_project(self, project: QgsProject) -> int:
        for layer in list(project.mapLayers().values()):
            try:
                if layer.id() not in self._derived:
                    self._adopt(layer)  # a copy made while the hooks were not connected
            except Exception as exc:
                logger.debug(f"[FM5] layer not checked for a derived source on unload: {exc}")
        restored = 0
        for layer_id, snapshot in list(self._derived.items()):
            layer = project.mapLayer(layer_id)
            if layer is None:
                continue
            try:
                if self._is_the_users(layer, snapshot):
                    self._drop(layer)
                    continue
                self._put_back(layer, snapshot)
                restored += 1
            except Exception as exc:
                logger.warning(f"[FM5] '{layer_id}' not restored to its original source: {exc}")
        return restored

    def _put_back(self, layer, snapshot: LayerSnapshot) -> None:
        """Original source of a derived layer, without going back when it cannot be opened."""
        if snapshot.kind == 'vector_tile':
            current = take_snapshot(layer, LayerKind.VECTOR_TILE, self)
            if not current.derived:
                return
            restore_snapshot(layer, base_snapshot(current), self)
            return
        subset = layer.subsetString() if _supports_subset(layer) else ''
        # A layer turning invalid keeps its style for the day its source is
        # repaired (``<originalStyle>`` in the project): FilterMate's state
        # (property, alpha band of the VRT) goes before the source changes.
        alpha = self._alpha.get(layer.id())
        if alpha is not None:
            _restore_alpha_band(layer, alpha)
        self.record(LayerSnapshot(layer.id(), snapshot.kind), layer)
        layer.setDataSource(snapshot.pristine_source, layer.name(), snapshot.pristine_provider,
                            QgsDataProvider.ProviderOptions(), False)
        if not layer.isValid():
            logger.warning(f"[FM5] '{layer.name()}' put back on its original source, which cannot be opened: "
                           f"{_redacted_source(snapshot.pristine_source)}")
        else:
            if snapshot.kind == LayerKind.RASTER.value:
                _restore_alpha_band(layer, alpha)
            if subset and not _set_subset(layer, subset):
                # HeightAboveGround of an enriched cloud, unknown to the original: the other terms stay.
                reduced = without_terms(subset, HAG_DIMENSION)
                if not (reduced and reduced != subset and _set_subset(layer, reduced)):
                    _set_subset(layer, '')
        layer.triggerRepaint()


def _stored_state(layer) -> Optional[dict]:
    """The ``filtermate/derived`` property of ``layer`` as a dict; None when absent or unreadable."""
    raw = layer.customProperty(DERIVED_PROPERTY)
    if not raw:
        return None
    try:
        if isinstance(raw, str) and raw.startswith('zlib:'):
            raw = zlib.decompress(base64.b64decode(raw[5:], validate=True)).decode('utf-8')
        state = json.loads(raw)
    except (TypeError, ValueError, zlib.error):
        return None
    return state if isinstance(state, dict) else None


def _snapshot_of(state: Optional[dict]) -> Optional[LayerSnapshot]:
    if state is None:
        return None
    try:
        return LayerSnapshot.from_dict(state)
    except TypeError:
        return None


def portable_snapshot(snapshot: LayerSnapshot, original_source: str = '') -> LayerSnapshot:
    """``snapshot`` without the session cache, to clip the layer again later (project file, favorite).

    A derived snapshot keeps its filter (kept area, side, raster selection)
    and gets the source before any FilterMate change as its original, or
    ``original_source`` (that source as written in a project).
    """
    if snapshot.kind == 'vector_tile':
        return dataclasses.replace(snapshot, source='', provider='', original_source='', original_provider='')
    if not snapshot.derived:
        return snapshot
    return dataclasses.replace(snapshot, source='', provider='',
                               original_source=original_source or snapshot.pristine_source,
                               original_provider=snapshot.pristine_provider,
                               enriched_source='', enriched_provider='')


def without_terms(expression: str, word: str) -> str:
    """``expression`` without the top-level ``AND`` terms naming ``word``.

    Returns '' when ``expression`` is not a plain conjunction (a top-level
    ``OR``) or when every term names ``word``. Quotes and parentheses are
    honored: ``A AND (B OR word > 2)`` keeps ``A``.
    """
    terms, depth, quote, start, index = [], 0, None, 0, 0
    while index < len(expression):
        char = expression[index]
        if quote:
            if char == quote:
                quote = None  # a doubled quote reopens at once
        elif char in '\'"':
            quote = char
        elif char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        elif depth == 0 and (index == 0 or not (expression[index - 1].isalnum() or expression[index - 1] == '_')):
            match = _BOOLEAN_WORD.match(expression, index)
            if match:
                if match.group(1).upper() == 'OR':
                    return ''
                terms.append(expression[start:index])
                index = start = match.end()
                continue
        index += 1
    terms.append(expression[start:])
    kept = [term.strip() for term in terms if word not in term]
    return '' if any(not term for term in kept) else ' AND '.join(kept)


_BOOLEAN_WORD = re.compile(r'(AND|OR)\b', re.IGNORECASE)


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
        logger.debug(f"[FM5] '{_redacted_source(source)}' not decoded by the '{provider}' provider: {exc}")
    return convert(source)


def _set_text(element, document, tag: str, text: str) -> None:
    child = element.firstChildElement(tag)
    if child.isNull():
        return
    while child.hasChildNodes():
        child.removeChild(child.firstChild())
    child.appendChild(document.createTextNode(text))


def _custom_property_options(element, name: str) -> list:
    """``<Option name=...>`` elements of the custom property ``name`` in a written layer."""
    options = element.firstChildElement('customproperties').elementsByTagName('Option')
    found = [options.at(index).toElement() for index in range(options.count())]
    return [option for option in found if option.attribute('name') == name]


def _set_custom_property(element, document, name: str, value: str) -> None:
    """Value of the custom property ``name`` in a written layer (QgsXmlUtils variant map), added when absent."""
    options = _custom_property_options(element, name)
    for option in options:
        option.setAttribute('value', value)
    if options:
        return
    properties = element.firstChildElement('customproperties')
    if properties.isNull():
        properties = document.createElement('customproperties')
        element.appendChild(properties)
    variant_map = properties.firstChildElement('Option')
    if variant_map.isNull():
        variant_map = document.createElement('Option')
        properties.appendChild(variant_map)
    variant_map.setAttribute('type', 'Map')  # an empty map is written as <Option/>
    option = document.createElement('Option')
    for attribute, text in (('type', 'QString'), ('name', name), ('value', value)):
        option.setAttribute(attribute, text)
    variant_map.appendChild(option)


def _remove_custom_property(element, name: str) -> None:
    for option in _custom_property_options(element, name):
        option.parentNode().removeChild(option)


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
    if kind is LayerKind.VECTOR_TILE:
        from .vector_tile_filters import snapshot
        return snapshot(layer, reg)
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
                             enriched_provider=known.enriched_provider, selection=known.selection,
                             bounded_enrichment=known.bounded_enrichment)
    return LayerSnapshot(layer.id(), kind.value, source=layer.source(), provider=layer.providerType(), subset=subset)


def base_snapshot(snapshot: LayerSnapshot, subset: str = '') -> LayerSnapshot:
    """State Unfilter goes back to: the base source of ``snapshot``, with ``subset``.

    The base of a point cloud enriched with HeightAboveGround is its enriched
    file, in the session cache: that state is still derived, so the project
    is written, and unloading restores, the source it was enriched from.
    """
    if snapshot.kind == 'vector_tile':
        return dataclasses.replace(snapshot, derived=False, renderer_xml=snapshot.original_renderer_xml, tile_filter='')
    if snapshot.bounded_enrichment:
        return LayerSnapshot(snapshot.layer_id, snapshot.kind, source=snapshot.pristine_source,
                             provider=snapshot.pristine_provider, subset=subset)
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
    if snapshot.kind == 'vector_tile':
        from .vector_tile_filters import restore_style, style_xml
        changed = style_xml(layer) != snapshot.renderer_xml
        if changed:
            restore_style(layer, snapshot.renderer_xml)
        reg.record(dataclasses.replace(snapshot, renderer_xml=style_xml(layer)), layer)
        return changed
    changed = False
    if snapshot.kind != LayerKind.VECTOR.value and snapshot.source and (
            layer.source() != snapshot.source or layer.providerType() != snapshot.provider):
        if not swap_source(layer, snapshot.source, snapshot.provider, reg):
            from .target_appliers import translate
            raise RuntimeError(translate('LayerSnapshot', 'The saved source could not be opened'))
        changed = True
        if snapshot.kind == LayerKind.RASTER.value:
            # Back on the original source: the alpha band it had (the user's choice).
            _restore_alpha_band(layer, None if snapshot.derived else reg.original_alpha_band(layer.id()))
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
    """``setDataSource`` that puts the previous source back when the new one is invalid.

    The previous subset goes back with it: a new provider has none, and a
    point cloud left without its own filter had no history entry to recover it.
    """
    (derived_registry or registry()).remember_alpha_band(layer)
    previous_source, previous_provider = layer.source(), layer.providerType()
    previous_subset = layer.subsetString() if _supports_subset(layer) else ''
    layer.setDataSource(source, layer.name(), provider, QgsDataProvider.ProviderOptions(), False)
    if layer.isValid():
        return True
    logger.warning(f"[FM5] '{layer.name()}': '{_redacted_source(source)}' could not be opened, previous source restored")
    layer.setDataSource(previous_source, layer.name(), previous_provider, QgsDataProvider.ProviderOptions(), False)
    if previous_subset and not _set_subset(layer, previous_subset):
        logger.warning(f"[FM5] '{layer.name()}': its filter could not be put back: {previous_subset[:120]}")
    return False


def _restore_alpha_band(layer, alpha: Optional[int]) -> None:
    """Alpha band ``alpha`` (the one of the original source), or the one of the current source when None."""
    if alpha is None:
        _sync_alpha_band(layer)
        return
    renderer = layer.renderer()
    if renderer is not None and hasattr(renderer, 'setAlphaBand'):
        renderer.setAlphaBand(alpha)


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
        state = _stored_state(layer)
        snapshot = _snapshot_of(state)
        if snapshot is None:
            layer.removeCustomProperty(DERIVED_PROPERTY)
            continue
        if registry().is_derived(layer.id()) or not (snapshot.geometry_wkt or snapshot.selection):
            continue
        # The project holds the source before any FilterMate change (that of
        # an enriched cloud too), relative when the project uses relative
        # paths: resolved again, so a moved project replays; the absolute one
        # serves a project saved elsewhere since (Save As before the replay).
        candidates = {_project_source(project, snapshot.pristine_source, snapshot.pristine_provider, write=False),
                      state.get(_ABSOLUTE_KEY) or ''}
        current = layer.source().replace('\\', '/')
        if not any(candidate and candidate.replace('\\', '/') == current for candidate in candidates):
            continue  # the user changed the source since: the stored filter no longer applies
        pending.append((layer, dataclasses.replace(snapshot, original_source=layer.source(),
                                                   original_provider=layer.providerType(),
                                                   enriched_source='', enriched_provider='')))
    return pending
