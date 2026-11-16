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
  ``("join", layer_id, spec, "removed", name)``: a join QGIS took away from a layer when the turn removed the layer it
  joined (undone, it comes back once that layer is back);
* ``("relation", "", xml, "", name)``: a relation of the project QGIS took away when the turn removed one of its
  layers, as XML (undone, it comes back once both layers are back);
* ``("tree", "", before, after)``: where each layer is in the layer tree and the groups, checked or not (JSON);
* ``("layer_name", layer_id, before, after)``: the name of a layer;
* ``("bookmarks", "", before, after)``: the spatial bookmarks of the project, as XML;
* ``("themes", "", before, after)``: the map themes of the project, as XML;
* ``("current_style", layer_id, before, after)``: the style of its style manager a layer has on (a theme sets it);
* ``("widgets", "", before, after)``: the widgets of the panel kept in the project (``core/agent/widgets.py``);
* ``("recipes", "", before, after)``: the recipes kept in the project (``core/agent/recipes.py``), as JSON;
* ``("edits", layer_id, before, after, name, opened)``: the index of the undo stack of a layer being edited, before
  and after the commands of the turn (``adapters/public_api/feature_edits.py``); ``opened``: the layer was not being
  edited before them (the turn put it in editing mode, and undoing the turn takes it out: ``_closable``);
* ``("layout", "", xml, "", name)``: a print layout the turn added to the project;
* ``("project_crs", "", before, after)``: the CRS of the project, as an authid or ``WKT:`` and its WKT;
* ``("settings", "", before, after, step)``: settings of FilterMate (config.json) the turn changed, as JSON
  ``{path: value}``, one effect per step that first changed them; ``step`` is the call of the turn (0, 1...) and,
  once committed, the number of recorded steps up to that call (TurnCheckpoint.commit), so that "back to before a
  step" restores the settings changed from it. Not of the project, but undone with the turn that changed them.
* ``("layer_options", layer_id, before, after, name)``: what a layer shows in EXPLORING and how it filters, in
  FilterMate's panel (``adapters/public_api/panel_options.py``): the options the turn changed only, before and after
  (``core.agent.panel_options.state_change``), as sorted JSON; the panel sets others itself;
* ``("export_options", "", before, after)``: the export options of the project in that panel, the same way.

A layer kept in memory has no definition that holds its features: removing it cannot be undone, and adding it
cannot be redone once undone (it would come back empty); both say so. The layers the agent makes are files.

What the user changed since in QGIS (the visibility of a layer, the CRS, a name, the style of a vector layer or the
style it has on) is theirs: undo and redo put back only what is still as the turn left it, and name the rest
(``_CHECKED``). Not checked: what is read as a whole collection (the tree, the bookmarks, the themes: a group ticked
or a theme of the user's elsewhere would keep the agent's from being undone, and QGIS writes the themes back in
another order), a selection (a filter empties it by itself), the style of a raster (its XML follows the filter), the
widgets and notes (the agent's own). The edits, recipes and settings check in their own way.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, FrozenSet, List, Optional, Sequence, Set, Tuple

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
SETTINGS_TOOLS = ("change_settings", "apply_settings_profile")
PANEL_TOOLS = ("set_layer_options",)
EXPORT_PANEL_TOOLS = ("set_export_options",)


def _export_options_label() -> str:
    from qgis.PyQt.QtCore import QCoreApplication
    return QCoreApplication.translate("AgentChat", "export options of the panel")


def _panel_json(value: Any) -> str:
    import json
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _settings_label() -> str:
    from qgis.PyQt.QtCore import QCoreApplication
    return QCoreApplication.translate("AgentChat", "settings of FilterMate")


def _setting_paths(arguments: Dict[str, Any]) -> List[str]:
    """The settings a change_settings call may change, as their full paths: an unknown one, or one the agent may
    not change (its own settings, private values), is left out, so an undo never writes it."""
    from .plugin_settings import planned_profile, settings_rows
    from ...core.agent.settings_reference import get, refusal
    rows = settings_rows()
    by_path = {row.path: row for row in rows}
    paths = []
    if "changes" not in arguments:  # apply_settings_profile: the settings of its file the profile may set
        try:
            return [row["path"] for row in planned_profile(arguments)[0]]
        except ValueError:
            return []
    for change in arguments.get("changes") or ():
        try:
            path = get(rows, str(change.get("path", "")))["path"]
        except (LookupError, AttributeError):
            continue
        if not refusal(by_path[path]):
            paths.append(path)
    return paths


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


def _bookmarks_label() -> str:
    from qgis.PyQt.QtCore import QCoreApplication
    return QCoreApplication.translate("AgentChat", "bookmarks")


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
    """The group at ``path`` from the root (direct children only, as the path was read), else the root."""
    from ..public_api.layer_tree import child_group
    group = project.layerTreeRoot()
    for name in path:
        child = child_group(group, name)
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


def _closable(layer: Any, effect: Tuple[Any, ...]) -> bool:
    """Whether undoing an ``edits`` effect takes its layer out of editing mode: the turn put it in (``opened``), its
    undo stack is back where it began with the commands of the turn still above (not saved since), and nothing else
    is pending. QGIS refuses a filter on a layer being edited; leaving the editing mode drops the undo stack, so the
    commands of the turn cannot be applied again afterwards."""
    if len(effect) < 6 or not effect[5] or effect[2] != 0:
        return False
    if not isinstance(layer, QgsVectorLayer) or not layer.isEditable():
        return False
    stack = layer.undoStack()
    return stack.index() == 0 and stack.count() >= effect[3] and not layer.isModified()


def _relation_xml(relation: Any) -> str:
    document = QDomDocument()
    root = document.createElement("relations")
    document.appendChild(root)
    relation.writeXml(root, document)
    return document.toString()


def _relation_of(project: QgsProject, xml: str) -> Any:
    """The relation ``xml`` holds, read against the layers of the project now: invalid while one of them is missing."""
    from qgis.core import QgsRelation, QgsRelationContext
    document = QDomDocument()
    document.setContent(xml)
    node = document.documentElement().firstChildElement("relation")
    return QgsRelation.createFromXml(node, QgsReadWriteContext(), QgsRelationContext(project))


def _visible(project: QgsProject, layer_id: str) -> Optional[bool]:
    node = project.layerTreeRoot().findLayer(layer_id)
    return None if node is None else bool(node.itemVisibilityChecked())


def _selection(layer: Any) -> Optional[Tuple[int, ...]]:
    if not isinstance(layer, QgsVectorLayer) or layer.selectedFeatureCount() > MAX_SELECTION:
        return None
    return tuple(sorted(layer.selectedFeatureIds()))


class EffectsRecorder:
    """Watches one turn: the state before its first touch of each thing, compared with the end of the turn."""

    def __init__(self, settings: bool = True) -> None:
        # False for the recorder of one step: the settings of a turn are recorded per call by the recorder of the turn,
        # which alone takes what the agent applied (take_applied empties it).
        self._record_settings = settings
        self._ids_before: Optional[Set[str]] = None
        # The layers that came during a call (``after_call``): a layer the user loads while the model thinks is not
        # one the turn added. None while no call was closed; ``_call_ids``: the layers when the call under way began.
        self._added_in_calls: Optional[Set[str]] = None
        self._call_ids: Optional[Set[str]] = None
        self._unclosed = False  # a call began before the one before it was closed: the whole turn is compared
        self._removed: Dict[str, Tuple[str, Place, str, str]] = {}
        # What QGIS takes away with a layer removed: the joins of other layers to it (removed id, layer, spec, name),
        # the relations of the project that cite it (by relation id: removed id, XML, name).
        self._unjoined: List[Tuple[str, str, Dict[str, Any], str]] = []
        self._relations: Dict[str, Tuple[str, str, str]] = {}
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
        self._bookmarks: Optional[str] = None
        self._current_styles: Dict[str, Optional[str]] = {}
        self._edits: Dict[str, Tuple[int, bool]] = {}  # index of the undo stack, and not being edited then
        self._layouts: Optional[Set[str]] = None
        self._crs: Optional[str] = None
        # (call of the turn, path, value before that call), in order: a setting changed twice has two records.
        self._settings_calls: List[Tuple[int, str, Any]] = []
        # The options of FilterMate's panels before the turn first set them: by layer id (JSON, name), and the export
        # ones (JSON).
        self._panel_layers: Dict[str, Tuple[str, str]] = {}
        self._export_panel: Optional[str] = None

    def before_call(self, call: Any, step: int = 0) -> None:
        project = QgsProject.instance()
        if self._ids_before is None:
            self._ids_before = set(project.mapLayers())
        if self._call_ids is not None:
            self._unclosed = True
        self._call_ids = set(project.mapLayers())
        name = getattr(call, "name", "")
        arguments = getattr(call, "arguments", {}) or {}
        try:
            if name == "remove_layers":
                for reference in arguments.get("layers") or ():
                    layer = _resolve(project, reference)
                    if layer is not None and layer.id() not in self._removed:
                        self._removed[layer.id()] = (_definition(layer), _place(project, layer.id()), layer.providerType(),
                                                     layer.name())
                        self._taken_with(project, layer.id())
            elif name == "select_features":
                layer = _resolve(project, arguments.get("layer"))
                selected = _selection(layer) if layer is not None else None
                if selected is not None and layer.id() not in self._selection:
                    self._selection[layer.id()] = selected
            elif name in SETTINGS_TOOLS and self._record_settings:
                from .plugin_settings import current_values
                paths = _setting_paths(arguments)
                values = current_values(paths)
                self._settings_calls.extend((step, path, values[path]) for path in paths if path in values)
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
                    self._edits[layer.id()] = (_edit_index(layer), not layer.isEditable())
            elif name == "join_layers":
                layer = _resolve(project, arguments.get("layer"))
                if isinstance(layer, QgsVectorLayer) and layer.id() not in self._joins:
                    self._joins[layer.id()] = {join.joinLayerId() for join in layer.vectorJoins()}
            elif name == "bookmark":
                if self._bookmarks is None:
                    from ..public_api.layer_tree import bookmarks_xml
                    self._bookmarks = bookmarks_xml()
            elif name == "rename_layer" and arguments.get("group"):
                if self._tree is None:  # a group renamed: its path changes, the tree brings it back
                    self._tree = _tree_state(project)
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
            elif name in PANEL_TOOLS:
                from ..public_api.panel_options import layer_state, running_dock
                dock = running_dock()
                for item in arguments.get("layers") or ():
                    layer = _resolve(project, item.get("layer")) if isinstance(item, dict) else None
                    state = layer_state(dock, layer.id()) if layer is not None else None
                    if state is not None and layer.id() not in self._panel_layers:
                        self._panel_layers[layer.id()] = (_panel_json(state), layer.name())
            elif name in EXPORT_PANEL_TOOLS:
                from ..public_api.panel_options import export_state, running_dock
                state = export_state(running_dock())
                if state is not None and self._export_panel is None:
                    self._export_panel = _panel_json({"EXPORTING": state})
            elif name == "set_layers_visibility":
                for reference in arguments.get("layers") or ():
                    layer = _resolve(project, reference)
                    visible = _visible(project, layer.id()) if layer is not None else None
                    if visible is not None and layer.id() not in self._visibility:
                        self._visibility[layer.id()] = visible
        except RuntimeError:  # a layer went away meanwhile: nothing to keep for it
            logger.debug("Agent undo: a layer could not be read before a step", exc_info=True)

    def after_call(self) -> None:
        """The call under way ended: the layers that came during it are those the turn added."""
        if self._call_ids is None:
            return
        came = set(QgsProject.instance().mapLayers()) - self._call_ids
        self._added_in_calls = (self._added_in_calls or set()) | came
        self._call_ids = None

    def _added_ids(self, now: Set[str]) -> Set[str]:
        """The layers the turn added: those that came during its calls when each was closed (``after_call``), else
        every layer that came since its first call (who runs the calls does not say when they end)."""
        if self._added_in_calls is None or self._unclosed or self._call_ids is not None:
            return now - (self._ids_before or set())
        return now & self._added_in_calls

    def _taken_with(self, project: QgsProject, layer_id: str) -> None:
        """What QGIS takes away when the layer ``layer_id`` is removed: the joins of the other layers to it and the
        relations of the project that cite it."""
        from ..public_api.fields_joins import join_specs
        for owner in project.mapLayers().values():
            if isinstance(owner, QgsVectorLayer) and owner.id() != layer_id:
                self._unjoined.extend((layer_id, owner.id(), spec, owner.name()) for spec in join_specs(owner)
                                      if spec["join_layer_id"] == layer_id)
        for relation_id, relation in project.relationManager().relations().items():
            if layer_id in (relation.referencingLayerId(), relation.referencedLayerId()) \
                    and relation_id not in self._relations:
                self._relations[relation_id] = (layer_id, _relation_xml(relation), relation.name())

    def finish(self) -> Tuple[Tuple[Any, ...], ...]:
        """What the turn did beside the filters, in the order to apply it again."""
        if self._ids_before is None:
            return ()
        project = QgsProject.instance()
        effects: List[Tuple[Any, ...]] = []
        now = set(project.mapLayers())
        # What QGIS took away with a layer removed goes before the layer in the list: undone (the list is read from
        # its end), the layer comes back first, then the joins to it and the relations that cite it.
        for removed_id, owner_id, spec, owner_name in self._unjoined:
            owner = project.mapLayer(owner_id)
            if removed_id not in now and isinstance(owner, QgsVectorLayer) and not any(
                    join.joinLayerId() == removed_id for join in owner.vectorJoins()):
                effects.append(("join", owner_id, spec, "removed", owner_name))
        relations = project.relationManager().relations() if self._relations else {}
        for relation_id, (removed_id, xml, name) in self._relations.items():
            if removed_id not in now and relation_id not in relations:
                effects.append(("relation", "", xml, "", name))
        for layer_id, (definition, place, provider, name) in self._removed.items():
            if layer_id not in now:
                effects.append(("removed", layer_id, "" if provider == "memory" else definition, place, name))
        for layer_id in sorted(self._added_ids(now)):
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
        applied: Dict[str, Any] = {}
        if self._record_settings:
            from .plugin_settings import take_applied
            applied = take_applied()  # what the agent set: a value the user put meanwhile stays theirs at undo
        if self._settings_calls:
            import json
            # Each call of the turn from the value before it to the value before the next call of the same setting
            # (the last one: what the agent applied): undo walks them back, "back to a step" stops in between.
            by_path: Dict[str, List[Tuple[int, Any]]] = {}
            for step, path, before in self._settings_calls:
                by_path.setdefault(path, []).append((step, before))
            by_step: Dict[int, Tuple[Dict[str, Any], Dict[str, Any]]] = {}
            for path, calls in by_path.items():
                if path not in applied:
                    continue
                for index, (step, before) in enumerate(calls):
                    after = calls[index + 1][1] if index + 1 < len(calls) else applied[path]
                    if before != after:
                        befores, afters = by_step.setdefault(step, ({}, {}))
                        befores[path], afters[path] = before, after
            for step, (befores, afters) in sorted(by_step.items()):
                effects.append(("settings", "", json.dumps(befores), json.dumps(afters), step))
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
        for layer_id, (before, opened) in self._edits.items():
            layer = project.mapLayer(layer_id)
            after = _edit_index(layer) if layer is not None else before
            if after != before:
                effects.append(("edits", layer_id, before, after, layer.name(), opened))
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
        if self._bookmarks is not None:
            from ..public_api.layer_tree import bookmarks_xml
            after_bookmarks = bookmarks_xml()
            if after_bookmarks != self._bookmarks:
                effects.append(("bookmarks", "", self._bookmarks, after_bookmarks))
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
        if self._panel_layers or self._export_panel is not None:
            import json
            from ..public_api.panel_options import export_state, layer_state, running_dock
            from ...core.agent.panel_options import state_change
            dock = running_dock()
            for layer_id, (before, name) in self._panel_layers.items():
                state = layer_state(dock, layer_id)
                was, made = state_change(json.loads(before), state) if state is not None else (None, None)
                if made and (made["values"] or made["absent"]):
                    effects.append(("layer_options", layer_id, _panel_json(was), _panel_json(made), name))
            state = export_state(dock) if self._export_panel is not None else None
            if state is not None:
                was, made = state_change(json.loads(self._export_panel), {"EXPORTING": state})
                if made["values"] or made["absent"]:
                    effects.append(("export_options", "", _panel_json(was), _panel_json(made)))
        self.__init__(self._record_settings)
        return tuple(effects)


# What the user may change in QGIS after a turn: put back only when still as the turn left it.
_CHECKED = frozenset({"visibility", "project_crs", "layer_name", "current_style", "style", "layer_options",
                      "export_options"})
_GONE = object()  # the layer of an effect is no longer in the project


def _same(first: Any, second: Any) -> bool:
    """Equal, a list and a tuple of the same items included (an effect may have gone through JSON)."""
    def plain(value):
        return tuple(plain(item) for item in value) if isinstance(value, (list, tuple)) else value
    return plain(first) == plain(second)


def _now(project: QgsProject, effect: Tuple[Any, ...]) -> Any:
    """What the thing of a ``_CHECKED`` effect is now, read as the recorder reads it; ``_GONE`` without its layer."""
    kind, layer_id = effect[0], effect[1]
    if kind == "project_crs":
        from ..public_api.project_control import crs_definition
        return crs_definition(project.crs())
    if kind == "visibility":
        visible = _visible(project, layer_id)
        return _GONE if visible is None else visible
    if kind in ("layer_options", "export_options"):
        import json
        from ..public_api.panel_options import export_state, layer_state, running_dock
        from ...core.agent.panel_options import state_part
        dock = running_dock()
        state = layer_state(dock, layer_id) if kind == "layer_options" else export_state(dock)
        if state is None:
            return _GONE
        # the keys the turn changed only, read as the effect keeps them
        return _panel_json(state_part(state if kind == "layer_options" else {"EXPORTING": state}, json.loads(effect[2])))
    layer = project.mapLayer(layer_id)
    if layer is None:
        return _GONE
    if kind == "layer_name":
        return layer.name()
    if kind == "current_style":
        from ..public_api.layer_tree import current_style
        return current_style(layer)
    # style: the XML of a raster follows its filter (a clip adds an alpha band), so only a vector one tells
    return _style(layer) if isinstance(layer, QgsVectorLayer) else _GONE


def _as_left(project: QgsProject, effect: Tuple[Any, ...]) -> str:
    """The name of what an effect touched, as a list of what is left as it is says it."""
    if effect[0] == "project_crs":
        return _crs_label()
    if effect[0] == "export_options":
        return _export_options_label()
    if not effect[1]:
        return effect[0]
    layer = project.mapLayer(effect[1])
    return layer.name() if layer is not None else effect[1]


def _where(project: QgsProject, effect: Tuple[Any, ...], undo: bool) -> str:
    """"there" when the thing of a ``_CHECKED`` effect is already as wanted, "changed" when the user changed it
    since the turn (or since it was undone), "" when it is as the turn left it, its layer is gone (the kind says what
    then) or it cannot be read (put back as before these checks)."""
    wanted, left_as = (effect[2], effect[3]) if undo else (effect[3], effect[2])
    try:
        now = _now(project, effect)
    except Exception:  # noqa: BLE001 - a check that fails must not stop an undo half way
        logger.debug("Agent undo: %s not checked", effect[0], exc_info=True)
        return ""
    if now is _GONE:
        return ""
    if _same(now, wanted):
        return "there"
    return "" if _same(now, left_as) else "changed"


# What changes a layer itself (protected layers are left as they are); a selection or visibility only shows it.
_LAYER_CHANGES = frozenset({"added", "removed", "style", "join", "layer_name", "current_style", "edits",
                            "layer_options"})


def apply_effects(effects: Sequence[Tuple[Any, ...]], undo: bool, keep: FrozenSet[str] = frozenset(),
                  presence: Optional[bool] = None, edits: Optional[bool] = None,
                  close: FrozenSet[str] = frozenset()) -> Tuple[List[str], List[str]]:
    """Undo (or apply again) what a turn did beside the filters: names of what changed, and of what could not.

    What would change a layer whose id is in ``keep`` (protected from the agent) is left as it is. ``presence``: only
    the layers added or removed (True), only the rest (False), or all (None): the layers come back before their
    filters, and a selection after them (a filter empties it). ``edits``: only the edits (True), all but them (False),
    or all (None): undone, they go before the filters (a layer being edited refuses a filter). ``close``: the ids of
    the layers whose filter is restored next: undone, such a layer leaves the editing mode the turn put it in
    (``_closable``), and its edits can no longer be applied again; any other layer stays in editing mode, where
    applying the turn again finds its commands.
    """
    project = QgsProject.instance()
    done: List[str] = []
    left: List[str] = []
    for effect in (reversed(effects) if undo else effects):
        kind, layer_id = effect[0], effect[1]
        if presence is not None and (kind in ("added", "removed")) != presence:
            continue
        if edits is not None and (kind == "edits") != edits:
            continue
        if kind in _LAYER_CHANGES and layer_id in keep:
            layer = project.mapLayer(layer_id)
            left.append(layer.name() if layer is not None else (effect[4] if len(effect) > 4 else layer_id))
            continue
        try:
            if kind in _CHECKED:
                where = _where(project, effect, undo)
                if where == "changed":
                    left.append(_as_left(project, effect))
                if where:  # already as wanted: nothing done, nothing to say
                    continue
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
                    if undo and layer_id in close and _closable(layer, effect):
                        layer.rollBack()  # out of the editing mode the turn opened: a filter can change again
                    layer.triggerRepaint()
                    done.append(layer.name())
                else:  # also applying again after an undo that left the editing mode: its undo stack went with it
                    left.append(effect[4] if len(effect) > 4 else layer_id)
            elif kind == "join":
                from ..public_api.fields_joins import add_join, remove_join
                layer = project.mapLayer(layer_id)
                spec = effect[2]
                present = isinstance(layer, QgsVectorLayer) and any(
                    join.joinLayerId() == spec["join_layer_id"] for join in layer.vectorJoins())
                # A join the turn added goes with an undo; one QGIS took away with the layer removed comes back.
                wanted = (effect[3] == "removed") == undo
                if not isinstance(layer, QgsVectorLayer):
                    left.append(effect[4])
                elif not wanted:
                    if present:
                        remove_join(layer, spec["join_layer_id"])
                    done.append(layer.name())
                elif present or add_join(layer, spec):
                    done.append(layer.name())
                else:
                    left.append(layer.name())  # the join layer went away meanwhile
            elif kind == "relation":
                manager = project.relationManager()
                document = QDomDocument()
                document.setContent(effect[2])
                relation_id = document.documentElement().firstChildElement("relation").attribute("id")
                if not undo:  # removed again with its layer: QGIS takes it away by itself
                    if relation_id in manager.relations():
                        manager.removeRelation(relation_id)
                    done.append(effect[4])
                elif relation_id in manager.relations():
                    done.append(effect[4])
                else:
                    relation = _relation_of(project, effect[2])
                    if relation.isValid():
                        manager.addRelation(relation)
                        done.append(effect[4])
                    else:
                        left.append(effect[4])  # one of its layers did not come back
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
            elif kind == "bookmarks":
                from ..public_api.layer_tree import set_bookmarks_xml
                (done if set_bookmarks_xml(effect[2] if undo else effect[3]) else left).append(_bookmarks_label())
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
                from .recipes_store import read_recipes, write_recipes
                from ...core.agent.recipes import dumps as recipes_dumps, parse as recipes_parse
                # Kept or removed from the menu since: that is the user's, left as it is.
                if recipes_dumps(read_recipes(project)) != (effect[3] if undo else effect[2]):
                    left.append(_recipes_label())
                else:
                    write_recipes(recipes_parse(effect[2] if undo else effect[3]), project)
                    done.append(_recipes_label())
            elif kind == "settings":
                import json
                from .plugin_settings import apply_values, current_values, settings_rows
                from ...core.agent.settings_reference import refusal
                wanted, expected = json.loads(effect[2] if undo else effect[3]), json.loads(effect[3] if undo else effect[2])
                allowed = {row.path for row in settings_rows() if not refusal(row)}
                # A setting the user changed since is theirs: left as it is, the others put back. Never one the
                # agent may not change, whatever the history holds.
                now = current_values(wanted)
                kept = {path: value for path, value in wanted.items()
                        if path in allowed and now.get(path) == expected.get(path)}
                try:
                    apply_values(kept)
                except Exception:  # apply_settings put the configuration back: the history stays in step
                    logger.warning("Agent undo: settings of FilterMate not restored", exc_info=True)
                    left.append(_settings_label())
                else:
                    (done if len(kept) == len(wanted) else left).append(_settings_label())
            elif kind in ("layer_options", "export_options"):
                import json
                from ..public_api.panel_options import restore_export_state, restore_layer_state, running_dock
                state = json.loads(effect[2] if undo else effect[3])
                if kind == "layer_options":
                    (done if restore_layer_state(running_dock(), layer_id, state) else left).append(effect[4])
                else:
                    (done if restore_export_state(running_dock(), state) else left).append(_export_options_label())
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
            left.append(layer_id or kind)
    label = _settings_label()  # one settings effect per step: their label once
    return _once(done, label), _once(left, label)


def _once(names: List[str], label: str) -> List[str]:
    kept, seen = [], False
    for name in names:
        if name == label:
            if seen:
                continue
            seen = True
        kept.append(name)
    return kept
