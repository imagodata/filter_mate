# -*- coding: utf-8 -*-
"""The state of the project, in a few lines, sent with each request of the user.

It goes in the user's message, after the request: the cached prefix (system prompt, tools, earlier turns)
stays the same, and the model starts from what the project holds now instead of an earlier answer.
It says where the map looks, what each layer is, and what the user changed since the last answer.
Plain Python: the caller reads the layers, the selections and the map.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

MAX_LAYERS = 30
MAX_FILTER_CHARS = 80
MAX_SELECTIONS = 10
MAX_FIELDS = 40  # of the active layer, in the state sent with a request
MAX_CHANGES = 12
MAX_NAMES = 5
# Only a tool of the core is named (core/agent/families.py): the others take a call to use_tools first.
HEADER = "Project when this request was sent (for reference; describe_layer gives the details of a layer):"
CHANGES_HEADER = "Changed in QGIS since your last answer (by the user, or another application):"
# Token diet, lot 3: a request after the first sends what changed only, or this line.
UNCHANGED = "Project unchanged since the last request."
# Two extents closer than this share of their size are the same view.
_SAME_VIEW = 1e-6


def _cut(text: str, size: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= size else text[:size] + "…"


def _extent(value: Any) -> Optional[List[float]]:
    """``[xmin, ymin, xmax, ymax]`` when ``value`` is four finite numbers."""
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        numbers = [float(item) for item in value]
    except (TypeError, ValueError):
        return None
    return numbers if all(math.isfinite(item) for item in numbers) else None


def _coordinates(extent: Sequence[float]) -> str:
    """Whole numbers for a projected extent, five decimals for one a few degrees wide."""
    span = max(extent[2] - extent[0], extent[3] - extent[1])
    digits = 0 if span >= 100 else 5
    return " ".join(f"{item:.{digits}f}" for item in extent)


def _map_line(view: Mapping[str, Any]) -> str:
    project_crs = str(view.get("project_crs") or "")
    parts: List[str] = [f"CRS {project_crs}"] if project_crs else []
    if view.get("available"):
        scale = view.get("scale")
        if isinstance(scale, (int, float)) and math.isfinite(scale) and scale > 0:
            parts.append(f"scale 1:{round(scale)}")
        extent = _extent(view.get("extent"))
        if extent is not None:
            canvas_crs = str(view.get("canvas_crs") or project_crs)
            parts.append(f"visible extent{f' ({canvas_crs})' if canvas_crs != project_crs else ''} "
                         f"xmin ymin xmax ymax = {_coordinates(extent)}")
        active = view.get("active_layer_name")
        if active:
            parts.append(f"active layer: {_cut(active, 100)}")
    return "Map: " + ", ".join(parts) if parts else ""


def _layer_line(row: Mapping[str, Any], project_crs: str) -> str:
    parts = [str(row.get("layer_kind") or "layer")]
    count = row.get("feature_count")
    if isinstance(count, int) and count >= 0:
        parts.append(f"{count} features")
    crs = str(row.get("crs_authid") or "")
    if crs and project_crs and crs != project_crs:
        parts.append(crs)
    group = row.get("group")
    if group:
        parts.append(f"group: {_cut(group, 60)}")
    if row.get("visible") is False:
        parts.append("hidden")
    expression = row.get("active_filter_expression") or ""
    if expression:
        parts.append(f"filter: {_cut(expression, MAX_FILTER_CHARS)}")
    return f"- {_cut(row.get('name', ''), 100)} ({', '.join(parts)})"


def project_state(layers: Iterable[Mapping[str, Any]], selections: Iterable[Mapping[str, Any]] = (),
                  view: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """What two requests are compared on: the layers with their filter and visibility, the selections, the view."""
    view = view or {}
    rows: Dict[str, Dict[str, Any]] = {}
    for row in layers:
        name = str(row.get("name", ""))
        rows[str(row.get("layer_id") or name)] = {
            "name": name, "filter": str(row.get("active_filter_expression") or ""),
            "visible": row.get("visible") is not False}
    selected = {str(item.get("layer_id") or item.get("name", "")): (str(item.get("name", "")),
                                                                     int(item.get("selected_count") or 0))
                for item in selections if isinstance(item, Mapping)}
    project_crs = str(view.get("project_crs") or "")
    return {"layers": rows, "selections": selected, "active": str(view.get("active_layer_name") or ""),
            "active_id": str(view.get("active_layer_id") or ""), "active_fields": _fields_text(view),
            "crs": project_crs, "canvas_crs": str(view.get("canvas_crs") or project_crs),
            "extent": _extent(view.get("extent")) if view.get("available") else None}


def _fields_text(view: Mapping[str, Any]) -> str:
    """The names of the fields of the active layer (``active_fields`` of the view), "" without any.

    The quality gate of the token diet (qwen3:8b, 2026-11-17): with the state of the project and no field in it, a
    small model wrote "dep", "department" or "code_dep" for the field "dept" in 11 runs of 12 instead of reading the
    fields first; with this line, it used the right field in 3 runs of 3. The values are never sent here."""
    names = [str(name) for name in (view.get("active_fields") or ()) if str(name)]
    if not names:
        return ""
    shown = ", ".join(_cut(name, 60) for name in names[:MAX_FIELDS])
    return shown if len(names) <= MAX_FIELDS else f"{shown} and {len(names) - MAX_FIELDS} more"


def _names(names: Sequence[str]) -> str:
    shown = ", ".join(_cut(name, 100) for name in names[:MAX_NAMES])
    return shown if len(names) <= MAX_NAMES else f"{shown} and {len(names) - MAX_NAMES} more"


def _moved(before: Optional[Sequence[float]], after: Optional[Sequence[float]]) -> bool:
    if before is None or after is None:
        return False
    size = max(abs(after[2] - after[0]), abs(after[3] - after[1]), abs(before[2] - before[0]),
               abs(before[3] - before[1]))
    return any(abs(a - b) > size * _SAME_VIEW for a, b in zip(before, after))


def _same_layer(before: Mapping[str, Any], after: Mapping[str, Any]) -> bool:
    """The active layer of two states is one layer: by id, by name for a state that has none."""
    if before.get("active_id") and after.get("active_id"):
        return before["active_id"] == after["active_id"]
    return before.get("active", "") == after.get("active", "")


def _view_changes(before: Mapping[str, Any], after: Mapping[str, Any]) -> List[str]:
    """The lines about the map and the active layer: CRS, active layer and its fields, where the view looks now.

    The model keeps the state of its first request in its history: what moved is said with its new value, a
    coordinate or a CRS it would otherwise go on assuming."""
    lines: List[str] = []
    crs, canvas = after.get("crs", ""), after.get("canvas_crs", "")
    project_moved = bool(crs and before.get("crs") and crs != before["crs"])
    if project_moved:
        lines.append(f"- project CRS is now: {crs}")
    was_canvas = before.get("canvas_crs", "")
    if canvas and was_canvas and canvas != was_canvas and not (project_moved and canvas == crs):
        lines.append(f"- map canvas CRS is now: {canvas}")
    fields = after.get("active_fields") or ""
    if not after.get("active"):
        if before.get("active"):
            lines.append("- no active layer now")
    elif not _same_layer(before, after):
        lines.append(f"- active layer is now: {_cut(after['active'], 100)}" + (f" (fields: {fields})" if fields else ""))
    elif fields != (before.get("active_fields") or ""):
        lines.append(f"- fields of the active layer are now: {fields or 'none'}")
    extent = after.get("extent")
    if _moved(before.get("extent"), extent):
        where = f" ({canvas})" if canvas and canvas != crs else ""
        lines.append(f"- the map view moved: visible extent{where} xmin ymin xmax ymax = {_coordinates(extent)}")
    return lines


def project_changes(before: Mapping[str, Any], after: Mapping[str, Any]) -> List[str]:
    """One line per kind of change between two ``project_state``: what the user did between two requests."""
    old, new = before.get("layers", {}), after.get("layers", {})
    lines: List[str] = []

    def say(label: str, names: List[str]) -> None:
        if names:
            lines.append(f"- {label}: {_names(names)}")

    say("layers added", [row["name"] for key, row in new.items() if key not in old])
    say("layers removed", [row["name"] for key, row in old.items() if key not in new])
    kept = [(old[key], row) for key, row in new.items() if key in old]
    # By id, so a renamed layer is not a removed one and a new one: the model calls it by its new name.
    say("layers renamed", [f"{_cut(was['name'], 100)} -> {row['name']}" for was, row in kept
                           if was["name"] != row["name"]])
    say("filter changed", [row["name"] for was, row in kept if row["filter"] and row["filter"] != was["filter"]])
    say("filter removed", [row["name"] for was, row in kept if was["filter"] and not row["filter"]])
    say("now shown", [row["name"] for was, row in kept if row["visible"] and not was["visible"]])
    say("now hidden", [row["name"] for was, row in kept if was["visible"] and not row["visible"]])
    was_selected, selected = before.get("selections", {}), after.get("selections", {})
    say("selection changed", [f"{name} ({count} selected)" for key, (name, count) in selected.items()
                              if key in new and was_selected.get(key, ("", 0))[1] != count])
    say("selection cleared", [name for key, (name, _) in was_selected.items() if key in new and key not in selected])
    lines.extend(_view_changes(before, after))
    return lines[:MAX_CHANGES]


def project_summary(layers: Iterable[Mapping[str, Any]], selections: Iterable[Mapping[str, Any]] = (),
                    view: Optional[Mapping[str, Any]] = None, before: Optional[Mapping[str, Any]] = None) -> str:
    """A short text: the map, each layer with its kind, count and filter, the selections. Empty without layers.

    Args:
        layers: Rows of ``list_layers``, in the order of the layer tree.
        selections: ``selections`` of ``map_context``.
        view: The rest of ``map_context`` (CRS, extent, scale, active layer); nothing is said of the map without it.
            Its ``drawn_objects`` adds a line when objects drawn in the dock select on a raster.
        before: ``project_state`` when the previous answer ended; what differs now is listed as changed since.
    """
    rows = list(layers)
    if not rows:
        return ""
    view = view or {}
    chosen = [item for item in selections if isinstance(item, Mapping)]
    lines: List[str] = [HEADER]
    map_line = _map_line(view)
    if map_line:
        lines.append(map_line)
    fields = _fields_text(view)
    if fields:
        lines.append(f"Fields of the active layer: {fields}")
    project_crs = str(view.get("project_crs") or "")
    lines.extend(_layer_line(row, project_crs) for row in rows[:MAX_LAYERS])
    if len(rows) > MAX_LAYERS:
        lines.append(f"- and {len(rows) - MAX_LAYERS} more layers")
    if chosen:
        lines.append("Selected: " + ", ".join(f"{_cut(item.get('name', ''), 100)} ({item.get('selected_count', 0)})"
                                              for item in chosen[:MAX_SELECTIONS]))
    else:
        lines.append("Selected: nothing")
    drawn = [item for item in (view.get("drawn_objects") or ()) if isinstance(item, Mapping) and item.get("count")]
    if drawn:
        lines.append("Objects drawn in the dock: " + ", ".join(
            f"{_cut(item.get('name', ''), 100)} ({item.get('count', 0)})" for item in drawn[:MAX_SELECTIONS]))
    if before is not None:
        changes = project_changes(before, project_state(rows, chosen, view))
        if changes:
            lines.extend([CHANGES_HEADER] + changes)
    return "\n".join(lines)


def project_update(layers: Iterable[Mapping[str, Any]], selections: Iterable[Mapping[str, Any]] = (),
                   view: Optional[Mapping[str, Any]] = None, before: Optional[Mapping[str, Any]] = None) -> str:
    """What changed in the project since ``before`` (``project_state`` when the last answer ended), or ``UNCHANGED``:
    the request after the first, whose history holds the whole state already (token diet, lot 3)."""
    rows = list(layers)
    chosen = [item for item in selections if isinstance(item, Mapping)]
    changes = project_changes(before or {}, project_state(rows, chosen, view or {}))
    return "\n".join([CHANGES_HEADER] + changes) if changes else UNCHANGED
