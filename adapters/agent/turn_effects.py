# -*- coding: utf-8 -*-
"""What a turn of the agent changes beside the filters: layers added or removed, selections, visibility.

Kept as plain tuples in the operation of the turn, so undo and redo reach them with the filters:

* ``("added", layer_id, definition, place, name)`` and ``("removed", layer_id, definition, place, name)``:
  ``definition`` is the layer definition (QLR) text, ``place`` the names of its groups from the root and its index;
* ``("selection", layer_id, before, after)``: selected feature ids;
* ``("visibility", layer_id, before, after)``: checked in the layer tree or not;
* ``("style", layer_id, before, after, name)``: the symbology, labels and rendering of the layer, as XML;
* ``("notes", "", before, after)``: the notes of the agent kept in the project (lists of texts);
* ``("edits", layer_id, before, after, name)``: the index of the undo stack of a layer being edited, before and
  after the commands of the turn (``adapters/public_api/feature_edits.py``).

A layer kept in memory has no definition that holds its features: removing it cannot be undone, and adding it
cannot be redone once undone (it would come back empty); both say so. The layers the agent makes are files.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from qgis.core import QgsLayerDefinition, QgsProject, QgsReadWriteContext, QgsVectorLayer
from qgis.PyQt.QtXml import QDomDocument

logger = logging.getLogger("FilterMate.agent")

MAX_SELECTION = 100_000  # beyond, the selection is not kept: too much to hold for an undo
Place = Tuple[Tuple[str, ...], int]
# The tools that change how a layer is drawn: its style is kept before their first call in a turn.
STYLE_TOOLS = ("set_layer_style", "set_labels")
NOTE_TOOLS = ("add_project_note", "remove_project_note")
EDIT_TOOLS = ("update_features", "delete_features", "add_features")


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
        self._edits: Dict[str, int] = {}

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
            elif name in EDIT_TOOLS:
                layer = _resolve(project, arguments.get("layer"))
                if isinstance(layer, QgsVectorLayer) and layer.id() not in self._edits:
                    self._edits[layer.id()] = _edit_index(layer)
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
        for layer_id, before in self._edits.items():
            layer = project.mapLayer(layer_id)
            after = _edit_index(layer) if layer is not None else before
            if after != before:
                effects.append(("edits", layer_id, before, after, layer.name()))
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
