# -*- coding: utf-8 -*-
"""Bounded display filters for basic vector tile renderers and labeling.

Tiles are targets only. Filters operate on the attributes and clipped
geometries present at the displayed zoom; they never query whole features.
"""
import dataclasses
import xml.etree.ElementTree as ET

MAX_VERTICES = 2000
MAX_FILTER_BYTES = 1000000


def tr(text):
    from qgis.PyQt.QtCore import QCoreApplication
    translated = QCoreApplication.translate('VectorTileFilter', text)
    return translated if isinstance(translated, str) else text


def is_vector_tile(layer):
    """Class check, including subclasses, without a provider read."""
    from qgis.core import QgsVectorTileLayer
    return isinstance(layer, QgsVectorTileLayer)


def rule_expression(original, expression):
    """Constrain a style rule without allowing OR to escape that rule."""
    if not expression:
        return original
    return f'({original}\n) AND ({expression}\n)' if original else expression


def bounded_wkt(geometry):
    """Refuse oversized geometry rather than silently changing a spatial filter."""
    if geometry.constGet().nCoordinates() > MAX_VERTICES:
        raise ValueError(tr('The tile selection exceeds the vertex budget (2000); use a smaller area'))
    wkt = geometry.asWkt()
    if len(wkt.encode('utf-8')) > MAX_FILTER_BYTES:
        raise ValueError(tr('The tile selection exceeds the expression budget (1 MB); use a smaller area'))
    return wkt


def _property_owners(symbol, path='symbol'):
    if symbol is None:
        return
    yield path, symbol
    for index in range(symbol.symbolLayerCount()):
        layer = symbol.symbolLayer(index)
        nested = f'{path}/{index}'
        yield nested, layer
        sub = layer.subSymbol()
        if sub is not None:
            yield from _property_owners(sub, nested + '/sub')


def style_xml(layer):
    labeling = layer.labeling()
    enabled = getattr(layer, 'labelsEnabled', lambda: labeling is not None)()
    return _serialize_style(layer.renderer(), labeling, enabled)


def _serialize_style(renderer, labeling, enabled, include_properties=True):
    """Serialize rules and numeric property keys, never layer custom properties."""
    from qgis.PyQt.QtXml import QDomDocument
    from qgis.core import QgsReadWriteContext, QgsXmlUtils
    document = QDomDocument('filtermate-tiles')
    root = document.createElement('filtermate-tiles'); document.appendChild(root)
    element = document.createElement('renderer'); root.appendChild(element)
    element.setAttribute('type', renderer.type())
    renderer.writeXml(element, QgsReadWriteContext())
    if labeling is not None:
        element = document.createElement('labeling'); root.appendChild(element)
        element.setAttribute('type', labeling.type())
        labeling.writeXml(element, QgsReadWriteContext())
    if include_properties:
        extra = document.createElement('numeric-properties'); root.appendChild(extra)
        for index, style in enumerate(renderer.styles()):
            for path, owner in _property_owners(style.symbol()):
                collection = owner.dataDefinedProperties()
                for key in sorted(collection.propertyKeys()):
                    element = document.createElement('property')
                    element.setAttribute('style', str(index)); element.setAttribute('path', path)
                    element.setAttribute('key', str(key))
                    element.appendChild(QgsXmlUtils.writeVariant(collection.property(key).toVariant(), document))
                    extra.appendChild(element)
    root.setAttribute('labelsEnabled', '1' if enabled else '0')
    return ET.canonicalize(document.toString(-1))


def _read_style(xml, restore_properties=True):
    from qgis.PyQt.QtXml import QDomDocument
    from qgis.core import QgsProperty, QgsReadWriteContext, QgsVectorTileBasicLabeling, QgsVectorTileBasicRenderer, QgsXmlUtils
    document = QDomDocument()
    parsed = document.setContent(xml)
    ok = parsed[0] if isinstance(parsed, tuple) else bool(parsed)
    root = document.documentElement()
    element = root.firstChildElement('renderer')
    if not ok or root.tagName() != 'filtermate-tiles' or element.attribute('type') != 'basic':
        raise ValueError(tr('The saved vector tile style is invalid'))
    renderer = QgsVectorTileBasicRenderer()
    renderer.readXml(element, QgsReadWriteContext())
    if restore_properties:
        styles = renderer.styles()
        owners = [{path: owner for path, owner in _property_owners(style.symbol())} for style in styles]
        properties = root.firstChildElement('numeric-properties').elementsByTagName('property')
        for index in range(properties.count()):
            element = properties.at(index).toElement()
            try:
                style_index = int(element.attribute('style'))
                owner = owners[style_index][element.attribute('path')]
                property_key = int(element.attribute('key'))
            except (IndexError, KeyError, ValueError) as exc:
                raise ValueError(tr('The saved vector tile symbol property is invalid')) from exc
            prop = QgsProperty()
            if not prop.loadVariant(QgsXmlUtils.readVariant(element.firstChildElement())):
                raise ValueError(tr('The saved vector tile symbol property is invalid'))
            collection = owner.dataDefinedProperties()
            collection.setProperty(property_key, prop)
            owner.setDataDefinedProperties(collection)
        renderer.setStyles(styles)
    element = root.firstChildElement('labeling')
    labeling = None
    if not element.isNull():
        if element.attribute('type') != 'basic':
            raise ValueError(tr('Vector tile filtering requires basic labeling'))
        labeling = QgsVectorTileBasicLabeling()
        labeling.readXml(element, QgsReadWriteContext())
    return renderer, labeling, root.attribute('labelsEnabled') == '1'


def without_property_backup(xml):
    """Strip only the backup, retaining native properties to detect user edits."""
    root = ET.fromstring(xml)
    for element in list(root.findall('numeric-properties')):
        root.remove(element)
    return ET.canonicalize(ET.tostring(root, encoding='unicode'))


def is_native_reload(current, saved):
    """Recognize native property loss without discarding changed property values."""
    if without_property_backup(current) != native_style_xml(saved):
        return False

    def properties(xml):
        return {(p.get('style'), p.get('path'), p.get('key')): ET.canonicalize(ET.tostring(p, encoding='unicode'))
                for p in ET.fromstring(xml).findall('numeric-properties/property')}
    old = properties(saved)
    return all(old.get(key) == value for key, value in properties(current).items())


def native_style_xml(xml):
    """QGIS native round trip, without the property repair (reload comparison)."""
    return _serialize_style(*_read_style(xml, restore_properties=False), include_properties=False)


def _set_style(layer, renderer, labeling, enabled):
    layer.setRenderer(renderer)
    layer.setLabeling(labeling)
    setter = getattr(layer, 'setLabelsEnabled', None)
    if setter is not None:
        setter(enabled)


def restore_style(layer, xml):
    _set_style(layer, *_read_style(xml))
    layer.triggerRepaint()


def supported(layer):
    renderer = layer.renderer()
    if renderer is None or renderer.type() != 'basic':
        raise ValueError(tr('Vector tile filtering requires a basic renderer'))
    labeling = layer.labeling()
    if labeling is not None and labeling.type() != 'basic':
        raise ValueError(tr('Vector tile filtering requires basic labeling'))


def edited_snapshot(layer, known):
    """Keep user symbology edits while separating any surviving display filter."""
    if not known.tile_filter:
        return None
    renderer, labels, enabled = _read_style(style_xml(layer))
    found = False
    for owner in (renderer, labels):
        if owner is None:
            continue
        styles = owner.styles()
        for style in styles:
            expression = style.filterExpression()
            original = strip_filter(expression, known.tile_filter)
            if original != expression:
                found = True
                style.setFilterExpression(original)
        owner.setStyles(styles)
    if not found:
        return None  # a foreign style without our expression is the user's new base
    return dataclasses.replace(known, renderer_xml=style_xml(layer),
                               original_renderer_xml=_serialize_style(renderer, labels, enabled))


def strip_filter(expression, added):
    """Remove only the exact envelope appended by rule_expression."""
    if expression == added:
        return ''
    suffix = '\n) AND (' + added + '\n)'
    if expression.startswith('(') and expression.endswith(suffix):
        return expression[1:-len(suffix)]
    return expression


def snapshot(layer, reg):
    from ....core.domain.filter_state import LayerSnapshot
    supported(layer)
    known = reg.get(layer.id())
    if known is None:
        known = reg._adopt(layer)  # plugin activated after the project was read
    xml = style_xml(layer)
    if known is not None and known.renderer_xml != xml:
        if is_native_reload(xml, known.renderer_xml):
            restore_style(layer, known.renderer_xml)
            xml = style_xml(layer)
            known = dataclasses.replace(known, renderer_xml=xml)
        else:
            known = edited_snapshot(layer, known)
        if known is None:
            reg.forget(layer.id())
            from .snapshots import DERIVED_PROPERTY
            layer.removeCustomProperty(DERIVED_PROPERTY)
        else:
            reg.record(known, layer)
    return LayerSnapshot(layer.id(), 'vector_tile', source=layer.source(), provider=layer.providerType(),
                         renderer_xml=xml, original_renderer_xml=known.original_renderer_xml if known else xml,
                         tile_filter=known.tile_filter if known else '', derived=bool(known and known.derived))


def apply_filter(layer, expression, operator=None):
    """Apply an attribute expression to every style/label rule; return a snapshot.

    This entry point and its UI dialog run on the main thread, without
    downloading tiles. Spatial jobs call it only after their worker finishes.
    """
    from qgis.core import QgsExpression
    from ....core.domain.layer_kind import LayerKind
    from .snapshots import registry, take_snapshot
    supported(layer)
    parsed = QgsExpression(expression)
    if expression and parsed.hasParserError():
        raise ValueError(tr('Invalid vector tile filter expression'))
    reg = registry()
    before = take_snapshot(layer, LayerKind.VECTOR_TILE)
    op = (operator or '').strip().upper()
    if before.tile_filter and op in ('AND', 'OR', 'AND NOT'):
        combined = f'({before.tile_filter}\n) {op} ({expression or "TRUE"}\n)'
    else:
        combined = expression
    if len(combined.encode('utf-8')) > MAX_FILTER_BYTES:
        raise ValueError(tr('The vector tile filter exceeds the expression budget (1 MB)'))
    # Work on detached original styles; reapplying never stacks over the old
    # display expression or changes a style rule's own zoom/geometry filter.
    renderer, labels, enabled = _read_style(before.original_renderer_xml)
    styles = renderer.styles()
    rule_count = len(styles) + (len(labels.styles()) if labels is not None else 0)
    if len(combined.encode('utf-8')) * max(1, rule_count) > MAX_FILTER_BYTES:
        raise ValueError(tr('The vector tile filter exceeds the total style expression budget (1 MB); use a smaller area'))
    for style in styles:
        style.setFilterExpression(rule_expression(style.filterExpression(), combined))
    renderer.setStyles(styles)
    if labels is not None:
        styles = labels.styles()
        for style in styles:
            style.setFilterExpression(rule_expression(style.filterExpression(), combined))
        labels.setStyles(styles)
    _set_style(layer, renderer, labels, enabled)
    after = dataclasses.replace(before, renderer_xml=style_xml(layer), tile_filter=combined, derived=True)
    reg.install()
    reg.record(after, layer)
    layer.triggerRepaint()
    return after


def append_targets(widget, project, selected=()):
    """Append tile targets even though they are absent from PROJECT_LAYERS."""
    from qgis.PyQt.QtCore import Qt
    from qgis.core import QgsApplication
    existing = set()
    for index in range(widget.count()):
        data = widget.itemData(index)
        if isinstance(data, dict):
            existing.add(data.get('layer_id'))
    for layer in project.mapLayers().values():
        if not is_vector_tile(layer) or not layer.isValid() or layer.id() in existing:
            continue
        widget.addItem(QgsApplication.getThemeIcon('/mIconVectorTileLayer.svg'),
                       f'{layer.name()} [{tr("Vector tiles")}]',
                       {'layer_id': layer.id(), 'layer_geometry_type': 'VectorTile'})
        item = widget.model().item(widget.count() - 1)
        item.setCheckState(Qt.CheckState.Checked if layer.id() in selected else Qt.CheckState.Unchecked)
        item.setToolTip(tr('Target only. Attributes depend on zoom. Objects split across tiles may be filtered differently.'))
    _install_attribute_menu(widget, project)


def _install_attribute_menu(widget, project):
    """A target attribute filter is edited without making the tile layer current."""
    if getattr(widget, '_filtermate_tile_menu', False):
        return
    from qgis.PyQt.QtCore import Qt
    from qgis.PyQt.QtWidgets import QInputDialog, QMenu, QMessageBox

    def edit(position):
        layers = [layer for layer in project.mapLayers().values() if is_vector_tile(layer) and layer.isValid()]
        if not layers:
            return
        menu = QMenu(widget)
        actions = {}
        for layer in layers:
            submenu = menu.addMenu(layer.name())
            for mode, title in (('edit', tr('Filter vector tile attributes')), ('undo', tr('Undo vector tile filter')),
                                ('redo', tr('Redo vector tile filter')), ('clear', tr('Unfilter vector tiles'))):
                actions[submenu.addAction(title)] = (layer, mode)
        chosen = menu.exec(widget.mapToGlobal(position))
        choice = actions.get(chosen)
        if choice is None:
            return
        layer, mode = choice
        from .snapshots import registry, take_snapshot
        from ....core.domain.layer_kind import LayerKind
        try:
            from ....core.services.cross_filter_service import get_cross_filter_service
            service = get_cross_filter_service()
            if mode == 'undo':
                service.undo(layer.id())
                return
            if mode == 'redo':
                service.redo(layer.id())
                return
            if mode == 'clear':
                service.unfilter(layer.id(), [layer.id()], {layer.id(): LayerKind.VECTOR_TILE})
                return
            before = take_snapshot(layer, LayerKind.VECTOR_TILE)
            expression, ok = QInputDialog.getMultiLineText(widget, tr('Filter vector tile attributes'),
                                                          tr('QGIS expression (attributes depend on zoom):'), before.tile_filter)
            if not ok:
                return
            after = apply_filter(layer, expression)
            from ....core.domain.filter_state import CrossOperation
            service.history.push(CrossOperation(layer.id(), ((before, after),), tr('Vector tile attribute filter')))
            registry().record(after, layer)
        except ValueError as exc:
            QMessageBox.warning(widget, tr('Vector tile filter'), str(exc))

    existing_menu = getattr(widget, 'context_menu', None)
    if isinstance(existing_menu, QMenu):
        action = existing_menu.addAction(tr('Vector tile filters'))
        action.triggered.connect(lambda: edit(widget.rect().center()))
    else:
        widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        widget.customContextMenuRequested.connect(edit)
    widget._filtermate_tile_menu = True
