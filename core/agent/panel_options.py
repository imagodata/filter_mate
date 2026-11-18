# -*- coding: utf-8 -*-
"""The options of FilterMate's panels an agent may set, and the values each takes.

Plain Python: what a layer shows in EXPLORING and how it filters (``PROJECT_LAYERS[layer_id]["exploring"|
"filtering"]`` of the dock), and how the project exports (``CURRENT_PROJECT["EXPORTING"]``). The caller gives what it
read of QGIS (the layers, a check of an expression, of a CRS, of a folder); adapters/public_api/panel_options.py
writes the result as the panel does. Every change of a call is checked before any is written.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Collection, Dict, List, Mapping, Optional, Sequence, Tuple, Union

EXPRESSIONS = ("single_selection_expression", "multiple_selection_expression", "custom_selection_expression")
GROUPBOXES = ("single_selection", "multiple_selection", "custom_selection")
COMBINE_OPERATORS = ("AND", "AND NOT", "OR")
BUFFER_TYPES = ("Round", "Flat", "Square")
STYLE_FORMATS = ("QML", "SLD")
MAX_BUFFER = 1_000_000  # the bounds of the buffer spin box of the panel, in metres
MAX_SEGMENTS = 100
MAX_EXPRESSION = 1000
MAX_LAYERS_PER_CALL = 50

EXPLORING_KEYS = EXPRESSIONS + ("current_exploring_groupbox", "is_tracking", "is_linking")
FILTERING_KEYS = ("has_layers_to_filter", "layers_to_filter", "has_geometric_predicates", "geometric_predicates",
                  "has_combine_operator", "source_layer_combine_operator", "other_layers_combine_operator",
                  "has_buffer_value", "buffer_value", "has_buffer_type", "buffer_type", "buffer_segments")
# The name an agent uses -> the key the project keeps.
EXPORT_KEYS: Dict[str, str] = {name: name.upper() for name in (
    "has_layers_to_export", "layers_to_export", "has_projection_to_export", "projection_to_export",
    "has_styles_to_export", "styles_to_export", "has_datatype_to_export", "datatype_to_export",
    "has_output_folder_to_export", "output_folder_to_export", "has_zip_to_export", "zip_to_export",
    "batch_output_folder", "batch_zip")}
# A value set without its box in the same call ticks the box, as choosing a value in the panel does.
_FILTERING_BOXES = {"layers_to_filter": "has_layers_to_filter", "geometric_predicates": "has_geometric_predicates",
                    "source_layer_combine_operator": "has_combine_operator",
                    "other_layers_combine_operator": "has_combine_operator",
                    "buffer_value": "has_buffer_value", "buffer_type": "has_buffer_type"}
_EXPORT_BOXES = {name: "has_" + name for name in (
    "layers_to_export", "projection_to_export", "styles_to_export", "datatype_to_export", "output_folder_to_export",
    "zip_to_export")}
_EXPORT_FLAGS = tuple(_EXPORT_BOXES.values()) + ("batch_output_folder", "batch_zip")
_EXPLORING_FLAGS = ("is_tracking", "is_linking")
_FILTERING_FLAGS = ("has_layers_to_filter", "has_geometric_predicates", "has_combine_operator", "has_buffer_value",
                    "has_buffer_type")
# The panel keeps a field of the layer for these two, and puts its key field back otherwise when the layer is chosen
# (ui/controllers/exploring_controller.py, _reset_layer_expressions); an expression goes in the custom selection.
FIELD_ONLY = ("single_selection_expression", "multiple_selection_expression")


@dataclass(frozen=True)
class LayerFacts:
    """A layer of the project, as the checks need it."""

    layer_id: str
    name: str
    vector: bool
    listed_target: bool = False  # a raster or point cloud the panel lists as a target of a vector layer


def resolve_layer(reference: str, layers: Sequence[LayerFacts]) -> Optional[LayerFacts]:
    """The layer of id ``reference``, else of that exact name; None when none is, or two layers bear that name."""
    for layer in layers:
        if layer.layer_id == reference:
            return layer
    named = [layer for layer in layers if layer.name == reference]
    return named[0] if len(named) == 1 else None


def _layer_ids(key: str, references: Any, layers: Sequence[LayerFacts], problems: List[str],
               vector_only: bool = False, not_this: Optional[LayerFacts] = None) -> List[str]:
    if not isinstance(references, list) or not all(isinstance(item, str) for item in references):
        problems.append(f"{key}: a list of layer names or ids")
        return []
    ids: List[str] = []
    for reference in references:
        layer = resolve_layer(reference, layers)
        if layer is None:
            twins = sum(1 for item in layers if item.name == reference)
            problems.append(f"{key}: two layers are named {reference}, give its id" if twins > 1
                            else f"{key}: no layer {reference}")
        elif not_this is not None and layer.layer_id == not_this.layer_id:
            problems.append(f"{key}: not the layer itself")
        elif vector_only and not (layer.vector or layer.listed_target):
            problems.append(f"{key}: {layer.name} is not a vector layer")
        elif layer.layer_id not in ids:
            ids.append(layer.layer_id)
    return ids


def _flag(key: str, value: Any, problems: List[str]) -> Any:
    if not isinstance(value, bool):
        problems.append(f"{key}: true or false")
    return value


def _one_of(key: str, value: Any, allowed: Sequence[str], problems: List[str]) -> Any:
    if value not in allowed:
        problems.append(f"{key}: one of {', '.join(allowed)}")
    return value


def _number(key: str, value: Any, problems: List[str]) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        problems.append(f"{key}: a number")
        return 0.0
    if abs(value) > MAX_BUFFER:
        problems.append(f"{key}: between -{MAX_BUFFER} and {MAX_BUFFER}")
    return float(value)


def _ticked(values: Dict[str, Any], given: Mapping[str, Any], boxes: Mapping[str, str]) -> Dict[str, Any]:
    for key, box in boxes.items():
        if key in values and box not in given:
            values[box] = True
    return values


def check_layer_changes(exploring: Mapping[str, Any], filtering: Mapping[str, Any], *, layer: LayerFacts,
                        layers: Sequence[LayerFacts], predicates: Sequence[str],
                        expression_problem: Callable[[str], str],
                        fields: Collection[str]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """``({"exploring": {key: value}, "filtering": {...}}, problems)`` for the options of ``layer``; nothing when one
    is wrong. ``expression_problem``: why an expression does not hold for the layer, "" when it does; ``fields``: the
    names of its fields."""
    if not layer.vector:
        return {}, [f"{layer.name}: only a vector layer has these options"]
    problems: List[str] = []
    clean: Dict[str, Dict[str, Any]] = {"exploring": {}, "filtering": {}}
    for key, value in exploring.items():
        if key in EXPRESSIONS:
            if not isinstance(value, str) or not value.strip():
                problems.append(f"{key}: an expression")
            elif len(value) > MAX_EXPRESSION:
                problems.append(f"{key}: at most {MAX_EXPRESSION} characters")
            elif key in FIELD_ONLY and value.strip().strip('"') not in fields:
                problems.append(f"{key}: a field of the layer (the panel keeps a field here; an expression goes in "
                                "custom_selection_expression)")
            else:
                problem = expression_problem(value)
                if problem:
                    problems.append(f"{key}: {problem}")
        elif key == "current_exploring_groupbox":
            _one_of(key, value, GROUPBOXES, problems)
        elif key in _EXPLORING_FLAGS:
            _flag(key, value, problems)
        else:
            problems.append(f"{key}: not an option of EXPLORING" if key in FILTERING_KEYS
                            else f"{key}: not an option of a layer")
            continue
        clean["exploring"][key] = value
    for key, value in filtering.items():
        if key == "layers_to_filter":
            value = _layer_ids(key, value, layers, problems, vector_only=True, not_this=layer)
        elif key == "geometric_predicates":
            if not isinstance(value, list):
                problems.append(f"{key}: a list of {', '.join(predicates)}")
            else:
                for name in value:
                    if name not in predicates:
                        problems.append(f"{key}: {name} is not one of {', '.join(predicates)}")
        elif key in ("source_layer_combine_operator", "other_layers_combine_operator"):
            _one_of(key, value, COMBINE_OPERATORS, problems)
        elif key == "buffer_value":
            value = _number(key, value, problems)
        elif key == "buffer_type":
            _one_of(key, value, BUFFER_TYPES, problems)
        elif key == "buffer_segments":
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= MAX_SEGMENTS:
                problems.append(f"{key}: a whole number from 1 to {MAX_SEGMENTS}")
        elif key in _FILTERING_FLAGS:
            _flag(key, value, problems)
        else:
            problems.append(f"{key}: not an option of FILTERING" if key in EXPLORING_KEYS
                            else f"{key}: not an option of a layer")
            continue
        clean["filtering"][key] = value
    if problems:
        return {}, problems
    _ticked(clean["filtering"], filtering, _FILTERING_BOXES)
    return {group: values for group, values in clean.items() if values}, []


def _format(value: Any, formats: Union[Mapping[str, str], Collection[str]]) -> str:
    """The name the panel shows for ``value``, "" when FilterMate exports no such format."""
    if not isinstance(value, str):
        return ""
    names = formats if isinstance(formats, Mapping) else {name: name for name in formats}
    by_case = {alias.upper(): name for alias, name in names.items()}
    return names.get(value) or by_case.get(value.upper(), "")


def check_export_changes(changes: Mapping[str, Any], *, layers: Sequence[LayerFacts],
                         formats: Union[Mapping[str, str], Collection[str]],
                         crs_problem: Callable[[str], str],
                         folder_problem: Callable[[str], str]) -> Tuple[Dict[str, Any], List[str]]:
    """The export options of the project, under the keys the project keeps; nothing when one is wrong.
    ``formats``: those FilterMate exports, or its names and aliases -> the name its panel shows (kept under that name,
    whatever the case); ``crs_problem`` / ``folder_problem``: why a CRS or a folder does not do,
    "" when it does."""
    problems: List[str] = []
    clean: Dict[str, Any] = {}
    for key, value in changes.items():
        if key not in EXPORT_KEYS:
            problems.append(f"{key}: not an export option")
            continue
        if key == "layers_to_export":
            value = _layer_ids(key, value, layers, problems)
        elif key == "projection_to_export":
            problem = crs_problem(value) if isinstance(value, str) else "an authority id such as EPSG:2154"
            if problem:
                problems.append(f"{key}: {problem}")
        elif key == "styles_to_export":
            _one_of(key, value, STYLE_FORMATS, problems)
        elif key == "datatype_to_export":
            value = _format(value, formats)
            if not value:
                problems.append(f"{key}: {changes[key]} is not a format FilterMate exports")
        elif key == "output_folder_to_export":
            problem = folder_problem(value) if isinstance(value, str) else "a folder"
            if problem:
                problems.append(f"{key}: {problem}")
        elif key == "zip_to_export":
            if not isinstance(value, str) or not value.lower().endswith(".zip"):
                problems.append(f"{key}: a path ending in .zip")
            else:
                problem = folder_problem(value.replace("\\", "/").rsplit("/", 1)[0] or "/")
                if problem:
                    problems.append(f"{key}: {problem}")
        elif key in _EXPORT_FLAGS:
            _flag(key, value, problems)
        clean[key] = value
    if problems:
        return {}, problems
    _ticked(clean, changes, _EXPORT_BOXES)
    return {EXPORT_KEYS[key]: value for key, value in clean.items()}, []


# --- What a turn changed, for its undo (adapters/agent/turn_effects.py) ---------------------------------------------
# A part of a state: {"values": {group: {key: value}}, "absent": [[group, key], ...]}. Only the keys a turn changed are
# kept: the panel sets some options itself (on a change of layer, a box ticked with its value), and a whole state
# compared would take that for a change of the user.

def state_change(before: Mapping[str, Mapping[str, Any]],
                 after: Mapping[str, Mapping[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """The parts of ``before`` and ``after`` (states by group) where they differ."""
    was: Dict[str, Any] = {"values": {}, "absent": []}
    made: Dict[str, Any] = {"values": {}, "absent": []}
    for group in sorted(set(before) | set(after)):
        old, new = before.get(group) or {}, after.get(group) or {}
        for key in sorted(set(old) | set(new)):
            if key in old and key in new and old[key] == new[key]:
                continue
            for part, state in ((was, old), (made, new)):
                if key in state:
                    part["values"].setdefault(group, {})[key] = state[key]
                else:
                    part["absent"].append([group, key])
    return was, made


def state_part(state: Mapping[str, Mapping[str, Any]], like: Mapping[str, Any]) -> Dict[str, Any]:
    """``state`` read on the keys of the part ``like``, in its form: what to compare with it."""
    keys = [(group, key) for group, values in (like.get("values") or {}).items() for key in values]
    keys += [tuple(item) for item in like.get("absent") or ()]
    part: Dict[str, Any] = {"values": {}, "absent": []}
    for group, key in sorted(keys):
        values = state.get(group) or {}
        if key in values:
            part["values"].setdefault(group, {})[key] = values[key]
        else:
            part["absent"].append([group, key])
    return part
