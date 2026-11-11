# -*- coding: utf-8 -*-
"""The layer tree and the map themes of the project: groups, names, saved views of the layers.

On the main thread, as the other controls of the project. Undone with the turn by ``adapters/agent/turn_effects.py``.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from .operations import resolve_layer

MAX_GROUP_DEPTH = 5
MAX_NAME = 200


def _root():
    from qgis.core import QgsProject
    return QgsProject.instance().layerTreeRoot()


def _path(text: str) -> List[str]:
    """``"Base/Roads"`` as its names, from the root; "" is the root itself."""
    names = [part.strip() for part in str(text or "").split("/") if part.strip()]
    if len(names) > MAX_GROUP_DEPTH:
        raise ValueError(f"a group is at most {MAX_GROUP_DEPTH} levels deep")
    if any(len(name) > MAX_NAME for name in names):
        raise ValueError(f"a group name has at most {MAX_NAME} characters")
    return names


def group_path(node) -> str:
    """The names of the groups above ``node``, from the root, joined by ``/``."""
    names = []
    parent = node.parent() if node is not None else None
    while parent is not None and parent.parent() is not None:
        names.append(parent.name())
        parent = parent.parent()
    return "/".join(reversed(names))


def ensure_group(path: Sequence[str]) -> Tuple[Any, List[str]]:
    """The group at ``path``, made where missing; and the paths of the groups made."""
    group = _root()
    made = []
    walked: List[str] = []
    for name in path:
        walked.append(name)
        child = group.findGroup(name)
        if child is None or child.parent() is not group:
            child = group.addGroup(name)
            made.append("/".join(walked))
        group = child
    return group, made


def move_layer(layer_id: str, group, index: int = 0) -> bool:
    """Put the node of a layer in ``group`` at ``index`` (0 first), keeping whether it is checked."""
    node = _root().findLayer(layer_id)
    if node is None:
        return False
    parent = node.parent()
    if parent is group and parent.children().index(node) == index:
        return True
    clone = node.clone()
    index = max(0, min(index, len(group.children())))
    group.insertChildNode(index, clone)
    parent.removeChildNode(node)
    return True


def group_layers(layers: List[str], group: str = "", at_top: bool = True, above: str = "") -> Dict[str, Any]:
    """Put ``layers`` in ``group`` (made where missing; "" is the top of the tree), first or last of it; or, with
    ``above``, just above that layer, in its group (drawn over it on the map).

    Raises:
        ValueError: No layer, a layer that is not in the tree, a group too deep, ``above`` not in the tree.
    """
    anchor = None
    if above:
        reference = resolve_layer(str(above))
        anchor = _root().findLayer(reference.id()) if reference is not None else None
        if anchor is None:
            raise ValueError(f"no layer {above!r} in the layer tree to put them above")
    path = _path(group_path(anchor) if anchor is not None else group)
    found, missing = [], []
    for reference in layers or []:
        layer = resolve_layer(str(reference))
        if layer is None or _root().findLayer(layer.id()) is None:
            missing.append(str(reference))
        else:
            found.append(layer)
    if not found:
        raise ValueError("no layer of the project among " + ", ".join(repr(item) for item in missing[:10]))
    target, made = ensure_group(path)
    moved = []
    for offset, layer in enumerate(found):
        if anchor is not None:
            if layer.id() == anchor.layerId():
                continue
            # Just above the anchor, in the order given: where it is now, then one further down for the next.
            index = target.children().index(anchor)
            node = _root().findLayer(layer.id())
            if node.parent() is target and target.children().index(node) < index:
                index -= 1  # the layer leaves a place above the anchor
            if move_layer(layer.id(), target, index):
                moved.append(layer.name())
            continue
        # First of the group in the order given, or each one appended after the last.
        if move_layer(layer.id(), target, offset if at_top else len(target.children())):
            moved.append(layer.name())
    return {'group': "/".join(path), 'groups_made': made, 'moved': moved, 'not_found': missing}


def rename_layer(layer: str, name: str, group: bool = False) -> Dict[str, Any]:
    """Give a layer of the project another name; its data does not change. With ``group``, ``layer`` is the path of
    a group of the layer tree (Base/Roads), renamed instead.

    Raises:
        ValueError: No such layer or group, or an empty or long name.
    """
    text = str(name or "").strip()
    if not text or len(text) > MAX_NAME:
        raise ValueError(f"a name has 1 to {MAX_NAME} characters")
    if group:
        if "/" in text:
            raise ValueError("a group name has no /")
        node = _find_group(_path(layer))
        if node is None:
            raise ValueError(f"no group {layer!r} in the layer tree")
        previous = node.name()
        node.setName(text)
        return {'layer_id': '', 'name': text, 'previous': previous}
    target = resolve_layer(str(layer))
    if target is None:
        raise ValueError(f"no layer {layer!r} in the project")
    previous = target.name()
    target.setName(text)
    return {'layer_id': target.id(), 'name': text, 'previous': previous}


def _find_group(path: Sequence[str]):
    """The group at ``path``, or None; never made."""
    group = _root()
    for name in path:
        child = group.findGroup(name)
        if child is None or child.parent() is not group:
            return None
        group = child
    return group if path else None


BOOKMARK_ACTIONS = ("list", "add", "zoom", "remove")
MAX_BOOKMARKS_LISTED = 100


def _bookmark_manager():
    from qgis.core import QgsProject
    return QgsProject.instance().bookmarkManager()


def _by_name(name: str):
    return next((item for item in _bookmark_manager().bookmarks() if item.name() == name), None)


def bookmark(action: str, name: str = "", extent_wkt: str = "", crs: str = "") -> Dict[str, Any]:
    """Spatial bookmarks of the project: list them, add one (the visible map, or ``extent_wkt``), zoom to one, remove
    one.

    Raises:
        ValueError: An unknown action or bookmark, no name, an extent that is not WKT, no map to zoom.
    """
    from qgis.core import QgsBookmark, QgsCoordinateReferenceSystem, QgsGeometry, QgsReferencedRectangle
    if action not in BOOKMARK_ACTIONS:
        raise ValueError("action is list, add, zoom or remove")
    text = str(name or "").strip()
    if action != "list" and (not text or len(text) > MAX_NAME):
        raise ValueError(f"give the name of the bookmark (1 to {MAX_NAME} characters)")
    manager = _bookmark_manager()
    answer: Dict[str, Any] = {'action': action, 'name': text}
    if action == "add":
        from qgis.core import QgsProject
        from .project_control import _canvas
        try:
            canvas = _canvas()
        except ValueError:  # no window: only an extent given
            canvas = None
        if extent_wkt:
            geometry = QgsGeometry.fromWkt(extent_wkt)
            if geometry is None or geometry.isNull():
                raise ValueError("extent_wkt is not a WKT geometry")
            target = QgsCoordinateReferenceSystem(crs) if crs else (
                canvas.mapSettings().destinationCrs() if canvas is not None else QgsProject.instance().crs())
            if not target.isValid():
                raise ValueError(f"{crs!r} is no CRS QGIS knows")
            extent = QgsReferencedRectangle(geometry.boundingBox(), target)
        elif canvas is not None:
            extent = QgsReferencedRectangle(canvas.extent(), canvas.mapSettings().destinationCrs())
        else:
            raise ValueError("no map to take the extent from: give extent_wkt")
        existing = _by_name(text)
        mark = QgsBookmark()
        mark.setName(text)
        mark.setExtent(extent)
        if existing is not None:
            mark.setId(existing.id())
            mark.setGroup(existing.group())
            manager.updateBookmark(mark)
        else:
            manager.addBookmark(mark)
        answer['replaced'] = existing is not None
    elif action in ("zoom", "remove"):
        found = _by_name(text)
        if found is None:
            known = ", ".join(repr(item.name()) for item in manager.bookmarks()[:20]) or "none"
            raise ValueError(f"no bookmark {text!r} (bookmarks: {known})")
        if action == "remove":
            manager.removeBookmark(found.id())
        else:
            from .project_control import zoom_to
            extent = found.extent()
            view = zoom_to(extent_wkt=extent.asWktPolygon(), crs=extent.crs().authid() or extent.crs().toWkt())
            answer['extent_wkt'] = view.get('extent_wkt', '')
    answer['bookmarks'] = [item.name() for item in manager.bookmarks()][:MAX_BOOKMARKS_LISTED]
    return answer


def bookmarks_xml() -> str:
    """The bookmarks of the project as XML, to bring them back as they were."""
    from qgis.PyQt.QtXml import QDomDocument
    document = QDomDocument("bookmarks")
    document.appendChild(_bookmark_manager().writeXml(document))
    return document.toString()


def set_bookmarks_xml(text: str) -> bool:
    from qgis.PyQt.QtXml import QDomDocument
    document = QDomDocument("bookmarks")
    result = document.setContent(text)
    if not (result[0] if isinstance(result, tuple) else result):
        return False
    manager = _bookmark_manager()
    manager.clear()
    return bool(manager.readXml(document.documentElement(), document))


def _model():
    """The model of the layer tree the user sees, or one of our own (headless, or before the interface)."""
    from qgis.core import QgsLayerTreeModel
    try:
        from qgis.utils import iface
        view = iface.layerTreeView() if iface is not None else None
        if view is not None and view.layerTreeModel() is not None:
            return view.layerTreeModel(), None
    except (ImportError, AttributeError, RuntimeError):
        pass
    model = QgsLayerTreeModel(_root())
    return model, model  # the second keeps it alive while it is used


def theme_names() -> List[str]:
    from qgis.core import QgsProject
    return list(QgsProject.instance().mapThemeCollection().mapThemes())


def map_theme(action: str, name: str = "") -> Dict[str, Any]:
    """List, save (the layers shown and their styles now), apply or remove a map theme of the project.

    Raises:
        ValueError: An unknown action, no name, or a theme that does not exist.
    """
    from qgis.core import QgsMapThemeCollection, QgsProject
    collection = QgsProject.instance().mapThemeCollection()
    text = str(name or "").strip()
    if action != "list" and (not text or len(text) > MAX_NAME):
        raise ValueError(f"give the name of the theme (1 to {MAX_NAME} characters)")
    answer: Dict[str, Any] = {'action': action, 'name': text}
    if action == "save":
        model, _keep = _model()
        record = QgsMapThemeCollection.createThemeFromCurrentState(_root(), model)
        answer['replaced'] = collection.hasMapTheme(text)
        if answer['replaced']:
            collection.update(text, record)
        else:
            collection.insert(text, record)
        answer['layers_shown'] = len(record.layerRecords())
    elif action in ("apply", "remove"):
        if not collection.hasMapTheme(text):
            known = ", ".join(repr(item) for item in theme_names()[:20]) or "none"
            raise ValueError(f"no map theme {text!r} (themes: {known})")
        if action == "apply":
            model, _keep = _model()
            collection.applyTheme(text, _root(), model)
            answer['layers_shown'] = len([node for node in _root().findLayers() if node.isVisible()])
        else:
            collection.removeMapTheme(text)
    elif action != "list":
        raise ValueError("action is list, save, apply or remove")
    answer['themes'] = theme_names()
    return answer


def themes_xml() -> str:
    """Every map theme of the project as XML, to bring them back as they were."""
    from qgis.core import QgsProject
    from qgis.PyQt.QtXml import QDomDocument
    document = QDomDocument("themes")
    root = document.createElement("qgis")
    document.appendChild(root)
    QgsProject.instance().mapThemeCollection().writeXml(document)
    return document.toString()


def set_themes_xml(text: str) -> bool:
    from qgis.core import QgsProject
    from qgis.PyQt.QtXml import QDomDocument
    document = QDomDocument("themes")
    result = document.setContent(text)
    if not (result[0] if isinstance(result, tuple) else result):
        return False
    collection = QgsProject.instance().mapThemeCollection()
    collection.clear()
    collection.readXml(document)
    return True


def current_style(layer) -> Optional[str]:
    """The name of the style of a layer its style manager has on, which a map theme may change."""
    manager = layer.styleManager() if layer is not None else None
    return manager.currentStyle() if manager is not None else None
