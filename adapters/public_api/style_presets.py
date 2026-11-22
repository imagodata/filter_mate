# -*- coding: utf-8 -*-
"""Official styles for the agent: a layer of the BD TOPO of IGN or of OpenStreetMap drawn as its producer draws it.

Main thread only, plain dicts out. The styles are QML files made from the MapLibre styles of the producers
(``scripts/build_style_presets.py``) and listed in ``resources/styles/manifest.json``: no network is needed to apply
them. A preset is a style of a producer (``ign/bdtopo/classique``); each holds a QML per table of its data set, and the
table of a layer is found by its name or its fields (``core/agent/style_presets.py``). A variant (``gris``,
``sombre``) is computed from the colours of the QML when it is applied.

Only the categories Symbology, Labeling and Rendering of the layer change, as with set_layer_style; the chat captures
the style before the first change of a turn (``adapters/agent/turn_effects.py``), so undoing the turn brings it back.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Tuple

from ...core.agent.style_presets import (
    VARIANTS, fitting, missing_fields, names_table, recolor, recolor_expression, scale_words,
)
from ...core.domain.layer_kind import LayerKind
from .operations import layer_kind, resolve_layer

logger = logging.getLogger('FilterMate.StylePresets')

STYLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                          'resources', 'styles')
MAX_LISTED = 12
_SOURCE_KEYS = ('layerName', 'table', 'typename', 'typeName', 'layer')
_manifest_cache: Dict[str, Any] = {}


def _manifest() -> Dict[str, Any]:
    """The presets of ``resources/styles/manifest.json``: {id: preset}."""
    if not _manifest_cache:
        with open(os.path.join(STYLES_DIR, 'manifest.json'), encoding='utf-8') as stream:
            _manifest_cache.update(json.load(stream).get('presets') or {})
    return _manifest_cache


def _layer(reference: str):
    """The vector layer ``reference`` names; ValueError otherwise."""
    layer = resolve_layer(reference)
    if layer is None:
        raise ValueError(f"layer {reference!r} not found")
    if layer_kind(layer) is not LayerKind.VECTOR:
        raise ValueError(f"'{layer.name()}' is not a vector layer: official styles are for vector data")
    if not layer.isValid():
        raise ValueError(f"'{layer.name()}' is not available: its data source could not be opened")
    return layer


def _geometry(layer) -> str:
    """point, line or polygon; "" for a table."""
    from qgis.core import QgsWkbTypes
    kind = QgsWkbTypes.geometryType(layer.wkbType())
    types = getattr(QgsWkbTypes, 'GeometryType', QgsWkbTypes)
    for name, member in (('point', 'PointGeometry'), ('line', 'LineGeometry'), ('polygon', 'PolygonGeometry')):
        if kind == getattr(types, member, None):
            return name
    return ''


def _names(layer) -> List[str]:
    """The name of the layer and the table of its source (a layer of a GeoPackage, a table of PostGIS, a WFS type,
    the file of a shapefile)."""
    names = [layer.name()]
    try:
        from qgis.core import QgsProviderRegistry
        parts = QgsProviderRegistry.instance().decodeUri(layer.providerType(), layer.source()) or {}
    except (RuntimeError, TypeError, AttributeError):  # a provider that cannot read its own address
        parts = {}
    names += [str(parts[key]) for key in _SOURCE_KEYS if parts.get(key)]
    path = parts.get('path')
    if path:
        names.append(os.path.splitext(os.path.basename(str(path)))[0])
    return names


def _facts(layer) -> Tuple[List[str], List[str], str]:
    return _names(layer), [field.name() for field in layer.fields()], _geometry(layer)


def _row(preset_id: str, table: str) -> Dict[str, Any]:
    preset = _manifest()[preset_id]
    entry = preset['tables'][table]
    row = {'preset': preset_id, 'table': table, 'title': preset['title'], 'rules': entry['rules'],
           'labels': entry['labels']}
    if entry.get('scale'):
        row['drawn_from'] = scale_words(entry['scale'])
    return row


def list_style_presets(layer: str = '') -> Dict[str, Any]:
    """The official styles: every preset, or those with a table that fits ``layer``, best first.

    Raises:
        ValueError: An unknown layer, or one that is not a vector layer.
    """
    presets = _manifest()
    if not layer:
        return {'presets': [{'preset': preset_id, 'title': preset['title'], 'tables': sorted(preset['tables']),
                             'licence': preset['licence']} for preset_id, preset in presets.items()],
                'variants': VARIANTS,
                'note': "give a layer to list the presets whose tables fit it (by its name or its fields)"}
    found = _layer(layer)
    rows = fitting(presets, *_facts(found))
    answer: Dict[str, Any] = {'layer_name': found.name(), 'presets': [_row(*row) for row in rows[:MAX_LISTED]]}
    if rows:
        answer['variants'] = VARIANTS
    else:
        answer['note'] = ("no official style fits this layer: it is named as no table of the BD TOPO and lacks the "
                          "fields they read (an OSM layer needs the column of its key: highway, building, landuse...)")
    return answer


def _preset_and_table(found, preset: str) -> Tuple[str, str]:
    """The preset id and the table of the layer ``found`` that ``preset`` names (``ign/bdtopo/classique``, its end
    ``classique``, or with the table ``ign/bdtopo/classique/batiment``).

    Raises:
        ValueError: No such preset, a table not of it, or a layer that fits no table of it (its fields said).
    """
    presets = _manifest()
    wanted = preset.strip().strip('/').casefold()
    table = ''
    candidates = [key for key in presets if key == wanted or key.endswith('/' + wanted)]
    if not candidates and '/' in wanted:
        head, table = wanted.rsplit('/', 1)
        candidates = [key for key in presets if key == head or key.endswith('/' + head)]
    if len(candidates) != 1:
        some = ', '.join(sorted(presets))
        raise ValueError(f"{preset!r} names {'several' if candidates else 'no'} preset; they are: {some}")
    preset_id = candidates[0]
    tables = presets[preset_id]['tables']
    names, fields, geometry = _facts(found)
    if table:
        if table not in tables:
            raise ValueError(f"{preset_id} has no table {table!r}; it has: {', '.join(sorted(tables))}")
        return preset_id, table
    rows = fitting({preset_id: presets[preset_id]}, names, fields, geometry)
    if rows:
        return rows[0]
    # Named as a table but without its fields: say which.
    named = [name for name in tables if names_table(names, name)]
    if named:
        entry = tables[named[0]]
        lacking = missing_fields(entry.get('required') or (), fields)
        if lacking:
            raise ValueError(f"'{found.name()}' lacks the fields {', '.join(lacking)} that {preset_id} reads for "
                             f"{named[0]}: it is not drawn as its producer draws it")
        raise ValueError(f"'{found.name()}' is a layer of {geometry or 'no'} geometry; {named[0]} of {preset_id} is "
                         f"one of {entry['geometry']}")
    raise ValueError(f"no table of {preset_id} fits '{found.name()}' (by its name, its geometry and its fields): "
                     f"list_style_presets with the layer says which presets do, or name the table "
                     f"({preset_id}/<table>)")


def _check(found, preset_id: str, table: str) -> Dict[str, Any]:
    entry = _manifest()[preset_id]['tables'][table]
    geometry = _geometry(found)
    if geometry != entry['geometry']:
        raise ValueError(f"'{found.name()}' is a layer of {geometry or 'no'} geometry; {table} of {preset_id} is one "
                         f"of {entry['geometry']}")
    lacking = missing_fields(entry.get('required') or (), [field.name() for field in found.fields()])
    if lacking:
        raise ValueError(f"'{found.name()}' lacks the fields {', '.join(lacking)} that {preset_id} reads for {table}: "
                         f"nothing was changed")
    return entry


def _recolor_document(document, variant: str) -> int:
    """Rewrite the colours of a QML in ``variant``: attributes named for a colour (``textColor``,
    ``bufferColor``...), the options and properties of a symbol named for one, the colours written in an expression
    of a colour. How many were changed."""
    changed = 0
    stack = [document.documentElement()]
    while stack:
        element = stack.pop()
        attributes = element.attributes()
        for index in range(attributes.count()):
            attribute = attributes.item(index).toAttr()
            if 'color' in attribute.name().casefold():
                value = recolor(attribute.value(), variant)
                if value is not None:
                    attribute.setValue(value)
                    changed += 1
        tag = element.tagName()
        key, slot = {'Option': ('name', 'value'), 'prop': ('k', 'v')}.get(tag, ('', ''))
        if key and 'color' in element.attribute(key).casefold():
            value = recolor(element.attribute(slot), variant)
            if value is not None:
                element.setAttribute(slot, value)
                changed += 1
        elif tag == 'Option' and element.attribute('name') == 'expression':
            parent = element.parentNode().toElement()
            if 'color' in parent.attribute('name').casefold():
                text = element.attribute('value')
                value = recolor_expression(text, variant)
                if value != text:
                    element.setAttribute('value', value)
                    changed += 1
        child = element.firstChildElement()
        while not child.isNull():
            stack.append(child)
            child = child.nextSiblingElement()
    return changed


def _style_categories():
    from qgis.core import QgsMapLayer
    category = getattr(QgsMapLayer, 'StyleCategory', QgsMapLayer)
    return category.Symbology | category.Labeling | category.Rendering


def _every_scale(layer) -> None:
    """The scale ranges of the rules of the style dropped: drawn at every scale."""
    from qgis.core import QgsRuleBasedLabeling, QgsRuleBasedRenderer
    renderer = layer.renderer()
    if isinstance(renderer, QgsRuleBasedRenderer):
        for rule in renderer.rootRule().children():
            rule.setMinimumScale(0)
            rule.setMaximumScale(0)
    labeling = layer.labeling()
    if isinstance(labeling, QgsRuleBasedLabeling):
        for rule in labeling.rootRule().children():
            rule.setMinimumScale(0)
            rule.setMaximumScale(0)
    layer.setScaleBasedVisibility(False)


def _refresh(layer) -> None:
    layer.triggerRepaint()
    layer.emitStyleChanged()
    try:
        from qgis.utils import iface
        view = iface.layerTreeView() if iface is not None else None
        if view is not None:
            view.refreshLayerSymbology(layer.id())
    except (ImportError, AttributeError, RuntimeError):
        pass


def apply_style_preset(layer: str, preset: str, variant: str = '', all_scales: bool = False) -> Dict[str, Any]:
    """Draw ``layer`` with an official style: its symbols, labels and scale ranges, in a variant or not.

    ``all_scales``: drawn at every scale, the zoom levels the producer draws each class from dropped.

    Raises:
        ValueError: An unknown layer, preset or variant, a layer that fits no table of the preset, a table whose
            fields or geometry the layer lacks (said in words; nothing changed), a style that does not load.
    """
    from qgis.PyQt.QtXml import QDomDocument
    found = _layer(layer)
    if variant and variant not in VARIANTS:
        raise ValueError(f"variant is one of {', '.join(VARIANTS)}, or empty for the style as it is")
    preset_id, table = _preset_and_table(found, preset)
    entry = _check(found, preset_id, table)
    with open(os.path.join(STYLES_DIR, entry['file']), encoding='utf-8') as stream:
        text = stream.read()
    document = QDomDocument('qgis')
    if not document.setContent(text):
        raise ValueError(f"the style {entry['file']} could not be read")
    if variant:
        _recolor_document(document, variant)
    result = found.importNamedStyle(document, _style_categories())
    loaded, message = (result[0], result[1]) if isinstance(result, tuple) else (bool(result), '')
    if not loaded:
        raise ValueError(f"the style {preset_id}/{table} did not load: {message}")
    if all_scales:
        _every_scale(found)
    _refresh(found)
    preset_entry = _manifest()[preset_id]
    answer: Dict[str, Any] = {'layer_name': found.name(), 'preset': preset_id, 'table': table,
                              'variant': variant or 'none', 'rules': entry['rules'], 'labels': entry['labels'],
                              'attribution': preset_entry['attribution']}
    if entry.get('scale') and not all_scales:
        answer['drawn_from'] = scale_words(entry['scale'])
        answer['note'] = (f"as {preset_entry['title']} draws it: nothing shows when the map is further out than "
                          f"{scale_words(entry['scale'])}; all_scales draws it at every scale")
    return answer
