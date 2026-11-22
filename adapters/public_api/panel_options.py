# -*- coding: utf-8 -*-
"""The options of FilterMate's panels, read and set as the panel itself does it (agent mode).

Per layer, what EXPLORING shows and how the layer filters (``dock.PROJECT_LAYERS[layer_id]["exploring"|"filtering"]``);
for the project, how it exports (``CURRENT_PROJECT["EXPORTING"]``). Which keys and which values: core/agent/
panel_options.py. A change goes the way of the panel: the dict of the dock, then its signal that saves it
(``settingLayerVariable``: the database of FilterMate and the variables of the layer; ``settingProjectVariables``: the
project of FilterMate), then the widgets when they show it. The chat undoes it with the turn
(adapters/agent/turn_effects.py). Main thread only, plain dicts out, ValueError for a refusal.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Sequence

from ...core.agent.panel_options import (
    BUFFER_TYPES, COMBINE_OPERATORS, EXPLORING_KEYS, EXPORT_KEYS, FILTERING_KEYS, GROUPBOXES, MAX_LAYERS_PER_CALL,
    STYLE_FORMATS, LayerFacts, check_export_changes, check_layer_changes, resolve_layer,
)
from ...core.domain.api_requests import PREDICATES

NO_PANEL = "Open the FilterMate panel first: these options are those of its panels."
NOT_SAVED = ("Set for this session: the project has no file yet, and FilterMate saves these options with the project "
             "once the project is saved.")


def dock_problem(dock) -> str:
    """"" when the panel is there with its widgets; else why these options cannot be read or set."""
    return "" if dock is not None and getattr(dock, "widgets_initialized", False) else NO_PANEL


def _project(project):
    if project is not None:
        return project
    from qgis.core import QgsProject
    return QgsProject.instance()


def _is_vector(layer) -> bool:
    from qgis.core import QgsVectorLayer
    return isinstance(layer, QgsVectorLayer)


def _expression_problem(layer, text: str) -> str:
    """Why ``text`` is not an expression of ``layer``: a parse error or a field it does not have; "" when it is."""
    from qgis.core import QgsExpression
    expression = QgsExpression(text)
    if expression.hasParserError():
        return expression.parserErrorString()
    names = set(layer.fields().names())
    for column in sorted(expression.referencedColumns()):
        if column and not column.startswith("#!") and column not in names:
            return f"unknown field {column}"
    return ""


def _crs_problem(value: str) -> str:
    from qgis.core import QgsCoordinateReferenceSystem
    return "" if QgsCoordinateReferenceSystem(value).isValid() else f"{value} is not a valid CRS"


def _folder_problem(path: str) -> str:
    if not os.path.isdir(path):
        return "no such folder"
    return "" if os.access(path, os.W_OK) else "a folder FilterMate cannot write in"


def _driver_map() -> Dict[str, str]:
    from ...core.export.layer_exporter import LayerExporter
    return dict(LayerExporter.DRIVER_MAP)


def _formats() -> Dict[str, str]:
    """The export formats FilterMate takes, each name and alias -> the driver name its panel shows."""
    drivers = _driver_map()
    return dict({name: name for name in drivers.values()}, **drivers)


def _field_names(layer) -> List[str]:
    return list(layer.fields().names())


def _show(dock, layer) -> None:
    """The panel shows ``layer`` again from what it keeps, by its own change of layer: the FILTERING widgets synced
    from the options, EXPLORING reloaded, its active selection mode, the buttons (2026-11-16, review: a reset of the
    filtering buttons emptied the predicates and the buffer, and the next Filter read the empty widgets)."""
    dock.current_layer_changed(layer, manual_change=True)


def _is_current(dock, layer_id: str) -> bool:
    current = getattr(dock, "current_layer", None)
    try:
        return current is not None and current.id() == layer_id
    except RuntimeError:  # the layer of the panel was deleted meanwhile
        return False


def _project_saved() -> bool:
    """The project has a file, so FilterMate keeps its options with it (an unsaved one keeps them for the session)."""
    from qgis.core import QgsProject
    return bool(QgsProject.instance().absoluteFilePath())


def _is_listed_target(layer) -> bool:
    """A raster or point cloud the panel lists among the targets of a vector layer (the rule of its list, options of
    CROSS_FILTER included): the panel keeps them in ``layers_to_filter`` beside the vector layers."""
    from ..qgis.point_cloud_capability import is_listed_coverage_target
    return is_listed_coverage_target(layer, True)


def _facts(project) -> List[LayerFacts]:
    facts = []
    for layer_id, layer in project.mapLayers().items():
        vector = _is_vector(layer)
        facts.append(LayerFacts(layer_id, layer.name(), vector, not vector and _is_listed_target(layer)))
    return facts


def _found(reference: Any, facts: Sequence[LayerFacts]) -> LayerFacts:
    if not isinstance(reference, str) or not reference:
        raise ValueError("Each layer is given by its name or id.")
    layer = resolve_layer(reference, facts)
    if layer is None:
        twins = sum(1 for item in facts if item.name == reference)
        raise ValueError(f"Two layers are named {reference}: give its id." if twins > 1 else f"No layer {reference}.")
    return layer


def _props(dock, layer: LayerFacts) -> Dict[str, Any]:
    props = (getattr(dock, "PROJECT_LAYERS", None) or {}).get(layer.layer_id)
    if not isinstance(props, dict):
        raise ValueError(f"FilterMate has not read {layer.name} yet: select it once in the panel.")
    return props


def _names(ids: Any, project) -> List[str]:
    names = []
    for layer_id in ids if isinstance(ids, list) else []:
        layer = project.mapLayer(layer_id)
        names.append(layer.name() if layer is not None else layer_id)
    return names


def _checked(dock) -> None:
    problem = dock_problem(dock)
    if problem:
        raise ValueError(problem)


def _panel(dock, target: LayerFacts) -> Dict[str, Any]:
    """Whether EXPLORING shows ``target`` now, and then its rail as an agent drives it (exploring_drive.py); else the
    layer it shows."""
    from .exploring_drive import panel_state
    try:
        state = panel_state(dock)
    except (AttributeError, RuntimeError):  # a panel half made, or going away: the options are still read
        return {"shown": False}
    if state["layer_id"] != target.layer_id:
        return {"shown": False, "shows": state["layer_name"]}
    return {"shown": True, "in_view": state["in_view"], "kind": state["kind"], "tools": state["tools"]}


def layer_options(dock, layer: str, project=None) -> Dict[str, Any]:
    """What ``layer`` shows in EXPLORING and how it filters, with the values each option takes."""
    _checked(dock)
    project = _project(project)
    target = _found(layer, _facts(project))
    props = _props(dock, target)
    exploring = {key: value for key, value in (props.get("exploring") or {}).items() if key in EXPLORING_KEYS}
    filtering = {key: value for key, value in (props.get("filtering") or {}).items() if key in FILTERING_KEYS}
    if "layers_to_filter" in filtering:
        filtering["layers_to_filter"] = _names(filtering["layers_to_filter"], project)
    return {"layer_name": target.name, "layer_id": target.layer_id, "vector": target.vector,
            "exploring": exploring, "filtering": filtering, "panel": _panel(dock, target),
            "choices": {"current_exploring_groupbox": list(GROUPBOXES), "geometric_predicates": list(PREDICATES),
                        "combine_operators": list(COMBINE_OPERATORS), "buffer_types": list(BUFFER_TYPES)}}


def set_layer_options(dock, layers: List[Dict[str, Any]], project=None) -> Dict[str, Any]:
    """Set the options of several layers, all or none: ``layers`` is ``[{"layer", "exploring", "filtering"}]``."""
    _checked(dock)
    if not isinstance(layers, list) or not layers:
        raise ValueError("Give one layer at least.")
    if len(layers) > MAX_LAYERS_PER_CALL:
        raise ValueError(f"Give at most {MAX_LAYERS_PER_CALL} layers in one call.")
    project = _project(project)
    facts = _facts(project)
    planned, problems = [], []
    for item in layers:
        if not isinstance(item, dict):
            raise ValueError("Each layer is {layer, exploring, filtering}.")
        target = _found(item.get("layer"), facts)
        qgis_layer = project.mapLayer(target.layer_id)
        clean, found = check_layer_changes(
            item.get("exploring") or {}, item.get("filtering") or {}, layer=target, layers=facts, predicates=PREDICATES,
            expression_problem=lambda text, qgis_layer=qgis_layer: _expression_problem(qgis_layer, text),
            fields=_field_names(qgis_layer) if target.vector else ())
        problems += [problem if problem.startswith(f"{target.name}:") else f"{target.name}: {problem}"
                     for problem in found]
        if not found:
            planned.append((target, qgis_layer, _props(dock, target) if target.vector else None, clean))
    if problems:
        raise ValueError("; ".join(problems))
    changed, shown = [], False
    for target, qgis_layer, props, clean in planned:
        keys = []
        for group, values in clean.items():
            props.setdefault(group, {}).update(values)
            keys += [(group, key) for key in values]
        if keys:  # an empty list would save every option of the layer
            dock.settingLayerVariable.emit(qgis_layer, keys)
        if _is_current(dock, target.layer_id):
            _show(dock, qgis_layer)
            shown = True
        # What the panel keeps now (it may have put a value back), for the keys asked.
        said = {group: {key: props.get(group, {}).get(key) for key in values} for group, values in clean.items()}
        if "layers_to_filter" in said.get("filtering", {}):
            said["filtering"]["layers_to_filter"] = _names(said["filtering"]["layers_to_filter"], project)
        changed.append({"layer_name": target.name, **said})
    return {"changed": changed, "shown_in_panel": shown}


def _exporting(dock) -> Dict[str, Any]:
    exporting = dock.project_props.setdefault("EXPORTING", {})
    return exporting


def _apply_export(dock, values: Dict[str, Any], removed: Sequence[str] = ()) -> Dict[str, Any]:
    """Write export options the way the EXPORTING panel holds them, then save. The panel reads the state of a group
    from its box, not from the options (2026-11-16, review: a group left unticked put its defaults back over the
    values set): the boxes are ticked from the options first, the list of layers filled, then the widgets set."""
    exporting = _exporting(dock)
    exporting.update(values)
    for key in removed:
        exporting.pop(key, None)
    for key in EXPORT_KEYS.values():
        widget = ((getattr(dock, "widgets", None) or {}).get("EXPORTING", {}).get(key) or {}).get("WIDGET")
        if key.startswith("HAS_") and widget is not None:
            widget.blockSignals(True)
            try:
                widget.setChecked(bool(exporting.get(key)))
            finally:
                widget.blockSignals(False)
    dock.exporting_populate_combobox()
    dock.set_exporting_properties()
    dock.CONFIG_DATA["CURRENT_PROJECT"]["EXPORTING"] = exporting
    dock.setProjectVariablesEvent()  # saved last: what the panel holds once its widgets are set
    return exporting


def export_options(dock, project=None) -> Dict[str, Any]:
    """How the project exports from the EXPORTING panel, with the formats FilterMate takes."""
    _checked(dock)
    project = _project(project)
    exporting = _exporting(dock)
    answer = {name: exporting[key] for name, key in EXPORT_KEYS.items() if key in exporting}
    if "layers_to_export" in answer:
        answer["layers_to_export"] = _names(answer["layers_to_export"], project)
    return dict(answer, formats=sorted(set(_formats().values())), styles=list(STYLE_FORMATS), saved=_project_saved())


def set_export_options(dock, changes: Dict[str, Any], project=None) -> Dict[str, Any]:
    """Set export options of the project, all or none, as the EXPORTING panel does."""
    _checked(dock)
    if not isinstance(changes, dict) or not changes:
        raise ValueError("Give one export option at least.")
    project = _project(project)
    clean, problems = check_export_changes(changes, layers=_facts(project), formats=_formats(),
                                           crs_problem=_crs_problem, folder_problem=_folder_problem)
    if problems:
        raise ValueError("; ".join(problems))
    exporting = _apply_export(dock, clean)
    by_key = {key: name for name, key in EXPORT_KEYS.items()}
    said = {by_key[key]: exporting.get(key) for key in clean}  # what the panel keeps now
    if "layers_to_export" in said:
        said["layers_to_export"] = _names(said["layers_to_export"], project)
    saved = _project_saved()
    return dict({"changed": said, "saved": saved}, **({} if saved else {"note": NOT_SAVED}))


# --- What the turn of the agent keeps to undo these options (adapters/agent/turn_effects.py) --------------------------

def running_dock():
    """The dock of the running FilterMate, or None (headless, plugin not loaded, panel not made)."""
    try:
        from qgis.utils import plugins
        from ...core.domain.plugin_package import PLUGIN_PACKAGE
        dock = getattr(getattr(plugins.get(PLUGIN_PACKAGE), "app", None), "dockwidget", None)
    except Exception:
        return None
    return None if dock_problem(dock) else dock


def layer_state(dock, layer_id: str) -> Any:
    """The options of a layer an agent may set, as stored (layers by id); None without the panel or the layer."""
    if dock_problem(dock):
        return None
    props = (getattr(dock, "PROJECT_LAYERS", None) or {}).get(layer_id)
    if not isinstance(props, dict):
        return None
    return {"exploring": {key: value for key, value in (props.get("exploring") or {}).items() if key in EXPLORING_KEYS},
            "filtering": {key: value for key, value in (props.get("filtering") or {}).items() if key in FILTERING_KEYS}}


def restore_layer_state(dock, layer_id: str, part: Dict[str, Any], project=None) -> bool:
    """Put back a part of the options of a layer (``core.agent.panel_options.state_change``) the way set_layer_options
    writes them; False without the panel or the layer."""
    if dock_problem(dock):
        return False
    props = (getattr(dock, "PROJECT_LAYERS", None) or {}).get(layer_id)
    layer = _project(project).mapLayer(layer_id)
    if not isinstance(props, dict) or layer is None:
        return False
    allowed = {"exploring": EXPLORING_KEYS, "filtering": FILTERING_KEYS}
    keys, removed = [], []
    for group, values in (part.get("values") or {}).items():
        values = {key: value for key, value in values.items() if key in allowed.get(group, ())}
        props.setdefault(group, {}).update(values)
        keys += [(group, key) for key in values]
    for group, key in part.get("absent") or ():
        if key in allowed.get(group, ()) and key in props.get(group, {}):
            del props[group][key]  # an option the turn added
            removed.append((group, key))
    if keys:  # an empty list would save every option of the layer
        dock.settingLayerVariable.emit(layer, keys)
    if removed:  # out of FilterMate's database and the variables of the layer too
        dock.resettingLayerVariable.emit(layer, removed)
    if _is_current(dock, layer_id):
        _show(dock, layer)
    return True


def export_state(dock) -> Any:
    """The export options of the project an agent may set, under their stored keys; None without the panel."""
    if dock_problem(dock):
        return None
    exporting = _exporting(dock)
    return {key: exporting[key] for key in EXPORT_KEYS.values() if key in exporting}


def restore_export_state(dock, part: Dict[str, Any]) -> bool:
    """Put back a part of the export options (``state_change`` of ``{"EXPORTING": export_state}``) the way
    set_export_options writes them."""
    if dock_problem(dock):
        return False
    allowed = set(EXPORT_KEYS.values())
    values = {key: value for key, value in ((part.get("values") or {}).get("EXPORTING") or {}).items() if key in allowed}
    removed = [key for group, key in part.get("absent") or () if group == "EXPORTING" and key in allowed]
    _apply_export(dock, values, removed)
    return True
