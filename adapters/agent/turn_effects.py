# -*- coding: utf-8 -*-
"""What a turn of the agent changes beside the filters: layers added or removed, selections, visibility.

Kept as plain tuples in the operation of the turn, so undo and redo reach them with the filters:

* ``("added", layer_id, definition, place, name)`` and ``("removed", layer_id, definition, place, name)``:
  ``definition`` is the layer definition (QLR) text, ``place`` the names of its groups from the root and its index;
* ``("selection", layer_id, before, after)``: selected feature ids;
* ``("visibility", layer_id, before, after)``: checked in the layer tree or not;
* ``("style", layer_id, before, after, name)``: the symbology, labels and rendering of the layer, as XML;
* ``("notes", "", before, after)``: the notes of the agent kept in the project (lists of texts);
* ``("join", layer_id, spec, "", name)``: a join the turn added to a layer (``fields_joins.join_specs``);
* ``("tree", "", before, after)``: where each layer is in the layer tree and the groups, checked or not (JSON);
* ``("layer_name", layer_id, before, after)``: the name of a layer;
* ``("themes", "", before, after)``: the map themes of the project, as XML;
* ``("current_style", layer_id, before, after)``: the style of its style manager a layer has on (a theme sets it);
* ``("widgets", "", before, after)``: the widgets of the panel kept in the project (``core/agent/widgets.py``);
* ``("recipes", "", before, after)``: the recipes kept in the project (``core/agent/recipes.py``), as JSON;
* ``("edits", layer_id, before, after, name)``: the index of the undo stack of a layer being edited, before and
  after the commands of the turn (``adapters/public_api/feature_edits.py``);
* ``("layout", "", xml, "", name)``: a print layout the turn added to the project;
* ``("project_crs", "", before, after)``: the CRS of the project, as an authid or ``WKT:`` and its WKT.

A layer kept in memory has no definition that holds its features: removing it cannot be undone, and adding it
cannot be redone once undone (it would come back empty); both say so. The layers the agent makes are files.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from qgis.core import QgsLayerDefinition, QgsLayerTree, QgsProject, QgsReadWriteContext, QgsVectorLayer
from qgis.PyQt.QtXml import QDomDocument

logger = logging.getLogger("FilterMate.agent")

MAX_SELECTION = 100_000  # beyond, the selection is not kept: too much to hold for an undo
Place = Tuple[Tuple[str, ...], int]
# The tools that change how a layer is drawn: its style is kept before their first call in a turn.
STYLE_TOOLS = ("set_layer_style", "set_labels")
NOTE_TOOLS = ("add_project_note", "remove_project_note")
WIDGET_TOOLS = ("create_widget", "remove_widget")
RECIPE_TOOLS = ("save_recipe", "remove_recipe")
TREE_TOOLS = ("group_layers", "map_theme")
EDIT_TOOLS = ("update_features", "delete_features", "add_features", "add_field")
LAYOUT_TOOLS = ("create_layout",)
CRS_TOOLS = ("set_project_crs",)


def _crs_label() -> str:
    from qgis.PyQt.QtCore import QCoreApplication
    return QCoreApplication.translate("AgentChat", "project CRS")


def _layout_names(project: QgsProject) -> Set[str]:
    return {layout.name() for layout in project.layoutManager().printLayouts()}


def _tree_state(project: QgsProject) -> str:
    """Where each layer is in the tree, and the groups with whether they are checked, as JSON."""
    import json
    root = project.layerTreeRoot()
    layers = []
    for node in root.findLayers():
        path, index = _place(project, node.layerId())
        layers.append([node.layerId(), list(path), index])
    groups = []

    def walk(group, path):
        for child in group.children():
            if QgsLayerTree.isGroup(child):
                groups.append(["/".join(path + [child.name()]), bool(child.itemVisibilityChecked())])
                walk(child, path + [child.name()])
    walk(root, [])
    return json.dumps({"layers": layers, "groups": groups})


def _set_tree_state(project: QgsProject, text: str) -> None:
    """Put the layers back where ``text`` says, make or check its groups, and remove the empty groups it had not."""
    import json
    from ..public_api.layer_tree import ensure_group, move_layer
    state = json.loads(text)
    wanted = {path: checked for path, checked in state["groups"]}
    for path, checked in state["groups"]:
        group, _made = ensure_group(path.split("/"))
        group.setItemVisibilityChecked(checked)
    for layer_id, path, index in sorted(state["layers"], key=lambda row: (row[1], row[2])):
        if project.layerTreeRoot().findLayer(layer_id) is not None and index >= 0:
            move_layer(layer_id, ensure_group(path)[0] if path else project.layerTreeRoot(), index)
    stale = [path for path, _checked in json.loads(_tree_state(project))["groups"] if path not in wanted]
    for path in sorted(stale, key=lambda item: -item.count("/")):  # the deepest first
        group = _group(project, path.split("/"))
        if group is not project.layerTreeRoot() and not group.children():
            group.parent().removeChildNode(group)


def _tree_label() -> str:
    from qgis.PyQt.QtCore import QCoreApplication
    return QCoreApplication.translate("AgentChat", "layer tree")


def _themes_label() -> str:
    from qgis.PyQt.QtCore import QCoreApplication
    return QCoreApplication.translate("AgentChat", "map themes")


def _widgets_label() -> str:
    from qgis.PyQt.QtCore import QCoreApplication
    return QCoreApplication.translate("AgentChat", "widgets of the panel")


def _recipes_label() -> str:
    from qgis.PyQt.QtCore import QCoreApplication
    return QCoreApplication.translate("AgentChat", "recipes of the agent")


def _notes_label() -> str:
    from qgis.PyQt.QtCore import QCoreApplication
    return QCoreApplication.translate("AgentChat", "project notes")


def _resolve(project: QgsProject, reference: Any) -> Any:
    if not isinstance(reference, str) or not reference:
        return None
    layer = project.mapLayer(reference)
    if layer is not None:
        return layer
    named = project.mapLayersByName(reference)
    return named[0] if named else None


def _definition(layer: Any) -> str:
    try:
        return QgsLayerDefinition.exportLayerDefinitionLayers([layer], QgsReadWriteContext()).toString()
    except Exception:
        logger.debug("Layer definition not exported", exc_info=True)
        return ""


def _place(project: QgsProject, layer_id: str) -> Place:
    node = project.layerTreeRoot().findLayer(layer_id)
    if node is None:
        return (), -1
    path: List[str] = []
    parent = node.parent()
    index = parent.children().index(node) if parent is not None else -1
    while parent is not None and parent is not project.layerTreeRoot():
        path.insert(0, parent.name())
        parent = parent.parent()
    return tuple(path), index


def _group(project: QgsProject, path: Sequence[str]) -> Any:
    group = project.layerTreeRoot()
    for name in path:
        child = group.findGroup(name)
        if child is None:
            return project.layerTreeRoot()
        group = child
    return group


def _bring_back(project: QgsProject, layer_id: str, definition: str, place: Place) -> bool:
    """The layer from its definition, at its place in the tree; False when it could not come back."""
    if not definition or project.mapLayer(layer_id) is not None:
        return project.mapLayer(layer_id) is not None
    document = QDomDocument()
    document.setContent(definition)
    result = QgsLayerDefinition.loadLayerDefinition(document, project, project.layerTreeRoot(), QgsReadWriteContext())
    loaded = result[0] if isinstance(result, tuple) else bool(result)
    layer = project.mapLayer(layer_id)
    if not loaded or layer is None:
        return False
    path, index = place
    node = project.layerTreeRoot().findLayer(layer_id)
    group = _group(project, path)
    if node is not None and (group is not node.parent() or index >= 0):
        clone = node.clone()
        group.insertChildNode(max(0, min(index, len(group.children()))) if index >= 0 else 0, clone)
        node.parent().removeChildNode(node)
    return True


def _style_categories():
    """Symbology, labels and rendering (opacity, scales): what the style tools change, nothing of the data."""
    from qgis.core import QgsMapLayer
    category = getattr(QgsMapLayer, "StyleCategory", QgsMapLayer)
    return category.Symbology | category.Labeling | category.Rendering


def _style(layer: Any) -> Optional[str]:
    """The style of ``layer`` as XML; None when it cannot be read."""
    document = QDomDocument("qgis")
    try:
        error = layer.exportNamedStyle(document, QgsReadWriteContext(), _style_categories())
    except (RuntimeError, TypeError):
        logger.debug("Agent undo: style not read", exc_info=True)
        return None
    return None if error else document.toString()


def _set_style(layer: Any, xml: str) -> bool:
    document = QDomDocument("qgis")
    if not document.setContent(xml):
        return False
    result = layer.importNamedStyle(document, _style_categories())
    loaded = result[0] if isinstance(result, tuple) else bool(result)
    if loaded:
        layer.triggerRepaint()
        layer.emitStyleChanged()
    return bool(loaded)


def _edit_index(layer: Any) -> int:
    """Where the undo stack of a layer stands; 0 when it is not being edited (the stack starts empty then)."""
    stack = layer.undoStack() if layer.isEditable() else None
    return stack.index() if stack is not None else 0


def _visible(project: QgsProject, layer_id: str) -> Optional[bool]:
    node = project.layerTreeRoot().findLayer(layer_id)
    return None if node is None else bool(node.itemVisibilityChecked())


def _selection(layer: Any) -> Optional[Tuple[int, ...]]:
    if not isinstance(layer, QgsVectorLayer) or layer.selectedFeatureCount() > MAX_SELECTION:
        return None
    return tuple(sorted(layer.selectedFeatureIds()))


class EffectsRecorder:
    """Watches one turn: the state before its first touch of each thing, compared with the end of the turn."""

    def __init__(self) -> None:
        self._ids_before: Optional[Set[str]] = None
        self._removed: Dict[str, Tuple[str, Place, str, str]] = {}
        self._selection: Dict[str, Tuple[int, ...]] = {}
        self._visibility: Dict[str, bool] = {}
        self._styles: Dict[str, str] = {}
        self._notes: Optional[Tuple[str, ...]] = None
        self._widgets: Optional[str] = None
        self._recipes: Optional[str] = None
        self._tree: Optional[str] = None
        self._joins: Dict[str, Set[str]] = {}
        self._names: Dict[str, str] = {}
        self._themes: Optional[str] = None
        self._current_styles: Dict[str, Optional[str]] = {}
        self._edits: Dict[str, int] = {}
        self._layouts: Optional[Set[str]] = None
        self._crs: Optional[str] = None

    def before_call(self, call: Any) -> None:
        project = QgsProject.instance()
        if self._ids_before is None:
            self._ids_before = set(project.mapLayers())
        name = getattr(call, "name", "")
        arguments = getattr(call, "arguments", {}) or {}
        try:
            if name == "remove_layers":
                for reference in arguments.get("layers") or ():
                    layer = _resolve(project, reference)
                    if layer is not None and layer.id() not in self._removed:
                        self._removed[layer.id()] = (_definition(layer), _place(project, layer.id()), layer.providerType(),
                                                     layer.name())
            elif name == "select_features":
                layer = _resolve(project, arguments.get("layer"))
                selected = _selection(layer) if layer is not None else None
                if selected is not None and layer.id() not in self._selection:
                    self._selection[layer.id()] = selected
            elif name in CRS_TOOLS:
                if self._crs is None:
                    from ..public_api.project_control import crs_definition
                    self._crs = crs_definition(project.crs())
            elif name in LAYOUT_TOOLS:
                if self._layouts is None:
                    self._layouts = _layout_names(project)
            elif name in EDIT_TOOLS:
                layer = _resolve(project, arguments.get("layer"))
                if isinstance(layer, QgsVectorLayer) and layer.id() not in self._edits:
                    self._edits[layer.id()] = _edit_index(layer)
            elif name == "join_layers":
                layer = _resolve(project, arguments.get("layer"))
                if isinstance(layer, QgsVectorLayer) and layer.id() not in self._joins:
                    self._joins[layer.id()] = {join.joinLayerId() for join in layer.vectorJoins()}
            elif name == "rename_layer":
                layer = _resolve(project, arguments.get("layer"))
                if layer is not None and layer.id() not in self._names:
                    self._names[layer.id()] = layer.name()
            elif name in TREE_TOOLS:
                if self._tree is None:
                    self._tree = _tree_state(project)
                if name == "map_theme":
                    from ..public_api.layer_tree import current_style, themes_xml
                    if self._themes is None:
                        self._themes = themes_xml()
                    for layer_id, layer in project.mapLayers().items():  # a theme applied shows and styles any
                        visible = _visible(project, layer_id)
                        if visible is not None and layer_id not in self._visibility:
                            self._visibility[layer_id] = visible
                        if layer_id not in self._current_styles:
                            self._current_styles[layer_id] = current_style(layer)
            elif name in WIDGET_TOOLS:
                if self._widgets is None:
                    from .agent_widgets import read_widgets
                    from ...core.agent.widgets import dumps
                    self._widgets = dumps(read_widgets(project))
            elif name in RECIPE_TOOLS:
                if self._recipes is None:
                    from .recipes_store import read_recipes
                    from ...core.agent.recipes import dumps as recipes_dumps
                    self._recipes = recipes_dumps(read_recipes(project))
            elif name in NOTE_TOOLS:
                if self._notes is None:
                    from .project_notes_store import read_notes
                    self._notes = tuple(read_notes(project))
            elif name in STYLE_TOOLS:
                layer = _resolve(project, arguments.get("layer"))
                style = _style(layer) if layer is not None and layer.id() not in self._styles else None
                if style is not None:
                    self._styles[layer.id()] = style
            elif name == "set_layers_visibility":
                for reference in arguments.get("layers") or ():
                    layer = _resolve(project, reference)
                    visible = _visible(project, layer.id()) if layer is not None else None
                    if visible is not None and layer.id() not in self._visibility:
                        self._visibility[layer.id()] = visible
        except RuntimeError:  # a layer went away meanwhile: nothing to keep for it
            logger.debug("Agent undo: a layer could not be read before a step", exc_info=True)

    def finish(self) -> Tuple[Tuple[Any, ...], ...]:
        """What the turn did beside the filters, in the order to apply it again."""
        if self._ids_before is None:
            return ()
        project = QgsProject.instance()
        effects: List[Tuple[Any, ...]] = []
        now = set(project.mapLayers())
        for layer_id, (definition, place, provider, name) in self._removed.items():
            if layer_id not in now:
                effects.append(("removed", layer_id, "" if provider == "memory" else definition, place, name))
        for layer_id in sorted(now - self._ids_before):
            layer = project.mapLayer(layer_id)
            if layer is not None:
                # A layer kept in memory: its definition would bring it back empty.
                definition = "" if layer.providerType() == "memory" else _definition(layer)
                effects.append(("added", layer_id, definition, _place(project, layer_id), layer.name()))
        for layer_id, before in self._selection.items():
            layer = project.mapLayer(layer_id)
            after = _selection(layer) if layer is not None else None
            if after is not None and after != before:
                effects.append(("selection", layer_id, before, after))
        for layer_id, before in self._visibility.items():
            after = _visible(project, layer_id)
            if after is not None and after != before:
                effects.append(("visibility", layer_id, before, after))
        if self._crs is not None:
            from ..public_api.project_control import crs_definition
            after_crs = crs_definition(project.crs())
            if after_crs != self._crs:
                effects.append(("project_crs", "", self._crs, after_crs))
        if self._layouts is not None:
            from ..public_api.layouts import layout_xml
            for name in sorted(_layout_names(project) - self._layouts):
                layout = project.layoutManager().layoutByName(name)
                if layout is not None:
                    effects.append(("layout", "", layout_xml(layout), "", name))
        for layer_id, before in self._edits.items():
            layer = project.mapLayer(layer_id)
            after = _edit_index(layer) if layer is not None else before
            if after != before:
                effects.append(("edits", layer_id, before, after, layer.name()))
        for layer_id, before_joins in self._joins.items():
            layer = project.mapLayer(layer_id)
            if isinstance(layer, QgsVectorLayer):
                from ..public_api.fields_joins import join_specs
                for spec in join_specs(layer):
                    if spec["join_layer_id"] not in before_joins:
                        effects.append(("join", layer_id, spec, "", layer.name()))
        if self._tree is not None:
            after_tree = _tree_state(project)
            if after_tree != self._tree:
                effects.append(("tree", "", self._tree, after_tree))
        for layer_id, before in self._names.items():
            layer = project.mapLayer(layer_id)
            if layer is not None and layer.name() != before:
                effects.append(("layer_name", layer_id, before, layer.name()))
        if self._themes is not None:
            from ..public_api.layer_tree import current_style, themes_xml
            after_themes = themes_xml()
            if after_themes != self._themes:
                effects.append(("themes", "", self._themes, after_themes))
            for layer_id, before in self._current_styles.items():
                layer = project.mapLayer(layer_id)
                after = current_style(layer) if layer is not None else before
                if after != before and before is not None and after is not None:
                    effects.append(("current_style", layer_id, before, after))
        if self._widgets is not None:
            from .agent_widgets import read_widgets
            from ...core.agent.widgets import dumps
            after_widgets = dumps(read_widgets(project))
            if after_widgets != self._widgets:
                effects.append(("widgets", "", self._widgets, after_widgets))
        if self._recipes is not None:
            from .recipes_store import read_recipes
            from ...core.agent.recipes import dumps as recipes_dumps
            after_recipes = recipes_dumps(read_recipes(project))
            if after_recipes != self._recipes:
                effects.append(("recipes", "", self._recipes, after_recipes))
        if self._notes is not None:
            from .project_notes_store import read_notes
            after_notes = tuple(read_notes(project))
            if after_notes != self._notes:
                effects.append(("notes", "", self._notes, after_notes))
        for layer_id, before in self._styles.items():
            layer = project.mapLayer(layer_id)
            after = _style(layer) if layer is not None else None
            if after is not None and after != before:
                effects.append(("style", layer_id, before, after, layer.name()))
        self.__init__()
        return tuple(effects)


def apply_effects(effects: Sequence[Tuple[Any, ...]], undo: bool) -> Tuple[List[str], List[str]]:
    """Undo (or apply again) what a turn did beside the filters: names of what changed, and of what could not."""
    project = QgsProject.instance()
    done: List[str] = []
    left: List[str] = []
    for effect in (reversed(effects) if undo else effects):
        kind, layer_id = effect[0], effect[1]
        try:
            if kind in ("added", "removed"):
                definition, place = effect[2], effect[3]
                bring_back = (kind == "removed") == undo
                if bring_back:
                    if _bring_back(project, layer_id, definition, place):
                        done.append(project.mapLayer(layer_id).name())
                    else:
                        left.append(effect[4] if len(effect) > 4 else layer_id)
                else:
                    layer = project.mapLayer(layer_id)
                    if layer is not None:
                        done.append(layer.name())
                        project.removeMapLayer(layer_id)
            elif kind == "selection":
                layer = project.mapLayer(layer_id)
                if isinstance(layer, QgsVectorLayer):
                    layer.selectByIds(list(effect[2] if undo else effect[3]))
                    done.append(layer.name())
            elif kind == "visibility":
                node = project.layerTreeRoot().findLayer(layer_id)
                if node is not None:
                    node.setItemVisibilityChecked(bool(effect[2] if undo else effect[3]))
                    done.append(node.name())
            elif kind == "project_crs":
                from ..public_api.project_control import crs_from_definition
                wanted = crs_from_definition(effect[2] if undo else effect[3])
                if wanted.isValid() or not (effect[2] if undo else effect[3]):
                    project.setCrs(wanted)
                    done.append(_crs_label())
                else:
                    left.append(_crs_label())
            elif kind == "layout":
                manager = project.layoutManager()
                layout = manager.layoutByName(effect[4])
                if undo:
                    if layout is not None:
                        manager.removeLayout(layout)
                    done.append(effect[4])
                elif layout is None:
                    from ..public_api.layouts import layout_from_xml
                    (done if layout_from_xml(effect[2]) else left).append(effect[4])
                else:
                    left.append(effect[4])  # another layout took its name meanwhile
            elif kind == "edits":
                layer = project.mapLayer(layer_id)
                start, end = (effect[3], effect[2]) if undo else (effect[2], effect[3])
                stack = layer.undoStack() if isinstance(layer, QgsVectorLayer) and layer.isEditable() else None
                # Only over the commands of the turn: saved, discarded or edited since, the layer is left as it is.
                if stack is not None and stack.index() == start and stack.count() >= max(start, end):
                    stack.setIndex(end)
                    layer.triggerRepaint()
                    done.append(layer.name())
                else:
                    left.append(effect[4] if len(effect) > 4 else layer_id)
            elif kind == "join":
                from ..public_api.fields_joins import add_join, remove_join
                layer = project.mapLayer(layer_id)
                spec = effect[2]
                present = isinstance(layer, QgsVectorLayer) and any(
                    join.joinLayerId() == spec["join_layer_id"] for join in layer.vectorJoins())
                if not isinstance(layer, QgsVectorLayer):
                    left.append(effect[4])
                elif undo:
                    if present:
                        remove_join(layer, spec["join_layer_id"])
                    done.append(layer.name())
                elif present or add_join(layer, spec):
                    done.append(layer.name())
                else:
                    left.append(layer.name())  # the join layer went away meanwhile
            elif kind == "tree":
                _set_tree_state(project, effect[2] if undo else effect[3])
                done.append(_tree_label())
            elif kind == "layer_name":
                layer = project.mapLayer(layer_id)
                if layer is not None:
                    layer.setName(effect[2] if undo else effect[3])
                    done.append(layer.name())
                else:
                    left.append(effect[3] if undo else effect[2])
            elif kind == "themes":
                from ..public_api.layer_tree import set_themes_xml
                (done if set_themes_xml(effect[2] if undo else effect[3]) else left).append(_themes_label())
            elif kind == "current_style":
                layer = project.mapLayer(layer_id)
                manager = layer.styleManager() if layer is not None else None
                if manager is not None and manager.setCurrentStyle(effect[2] if undo else effect[3]):
                    done.append(layer.name())
                elif layer is not None:
                    left.append(layer.name())
            elif kind == "widgets":
                from .agent_widgets import write_widgets
                from ...core.agent.widgets import parse
                write_widgets(parse(effect[2] if undo else effect[3]), project)
                done.append(_widgets_label())
            elif kind == "recipes":
                from .recipes_store import write_recipes
                from ...core.agent.recipes import parse as recipes_parse
                write_recipes(recipes_parse(effect[2] if undo else effect[3]), project)
                done.append(_recipes_label())
            elif kind == "notes":
                from .project_notes_store import write_notes
                write_notes(list(effect[2] if undo else effect[3]), project)
                done.append(_notes_label())
            elif kind == "style":
                layer = project.mapLayer(layer_id)
                if layer is not None and _set_style(layer, effect[2] if undo else effect[3]):
                    done.append(layer.name())
                elif layer is not None:
                    left.append(layer.name())
        except RuntimeError:
            logger.debug("Agent undo: %s of %s not applied", kind, layer_id, exc_info=True)
            left.append(layer_id)
    return done, left
