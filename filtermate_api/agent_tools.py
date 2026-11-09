"""The tools of the chat, running inside QGIS on the same accessor as the REST routes.

They answer what the routes answer and keep their checks. No FastAPI, no pydantic:
the argument schemas are enforced by ``core.agent.tool_executor`` before a handler runs.
"""

from __future__ import annotations

import logging
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence

from .accessor import FavoritesUnavailable, FilterMateAccessor, FilterRejected
from .export_root import ExportRootError, prepare_export_root, resolve_export_folder
from .main_thread import QGISBusy

try:
    from ..core.agent.open_data import source_problem
    from ..core.agent.sql_guard import filter_problem
    from ..core.agent.tool_executor import ToolFailure
except ImportError:  # the API package loaded on its own, with the plugin root on the path
    from core.agent.open_data import source_problem
    from core.agent.sql_guard import filter_problem
    from core.agent.tool_executor import ToolFailure

logger = logging.getLogger("filtermate_api")
Handler = Callable[[Dict[str, Any]], Any]
SOURCE = "agent_chat"
# They accept invalid SQL in setSubsetString: the layer then just shows nothing.
_SILENT_SQL_PROVIDERS = ("ogr", "spatialite")


def _checked_expression(expression: str) -> str:
    problem = filter_problem(expression)
    if problem:
        raise ToolFailure(f"An expression is a single plain WHERE clause: {problem}.")
    return expression


def _point_cloud_criteria(values: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """``None`` when the criteria keep nothing in particular."""
    if not values:
        return None
    meaningful = (values.get(key) is not None for key in
                  ("z_min", "z_max", "intensity_min", "intensity_max", "return_number"))
    if values.get("classes") or (values.get("expression") or "").strip() or any(meaningful):
        return values
    return None


def _report(operation: str, result: Any) -> Dict[str, Any]:
    if result.error:
        raise ToolFailure(f"{operation} failed: {result.error}")
    return asdict(result)


def _found(value: Any, message: str) -> Any:
    if value is None:
        raise ToolFailure(message)
    return value


def _guarded(handler: Handler) -> Handler:
    """Turn what the accessor refuses into messages the model can act on."""
    def run(arguments: Dict[str, Any]) -> Any:
        try:
            return handler(arguments)
        except QGISBusy as exc:
            raise ToolFailure(f"QGIS is busy, nothing was changed: {exc}. Wait and try again.") from None
        except (FilterRejected, FavoritesUnavailable) as exc:
            raise ToolFailure(str(exc)) from None
    return run


def build_handlers(accessor: FilterMateAccessor, export_root: Path, allow_remote_sources: bool = False,
                   platforms: Sequence[str] = (), extra_domains: str = "") -> Dict[str, Handler]:
    """One handler per tool of the chat (see ``core.agent.tool_catalog.chat_tools``).

    ``allow_remote_sources`` False: no layer is read over the network. ``platforms``: the only ones that can be
    searched, each as the user enabled it; ``extra_domains`` says where the user's own portals are.
    """
    enabled_platforms = {name.lower() for name in platforms}

    def _allowed_platform(name: str) -> str:
        if name.lower() not in enabled_platforms:
            raise ToolFailure(f"{name!r} is not enabled in the agent sources. Enabled: "
                              f"{', '.join(sorted(enabled_platforms)) or 'none'}.")
        return name

    def list_layers(_: Dict[str, Any]) -> Dict[str, Any]:
        return {"layers": [asdict(layer) for layer in accessor.list_layers()]}

    def filter_state(_: Dict[str, Any]) -> Dict[str, Any]:
        return {"layers": [asdict(layer) for layer in accessor.get_filter_state()]}

    def list_favorites(_: Dict[str, Any]) -> Dict[str, Any]:
        return {"favorites": [asdict(favorite) for favorite in accessor.list_favorites()]}

    def describe_layer(args: Dict[str, Any]) -> Dict[str, Any]:
        return asdict(_found(accessor.describe_layer(args["layer"]), "Layer not found."))

    def field_values(args: Dict[str, Any]) -> Dict[str, Any]:
        values = accessor.field_values(args["layer"], args["field"], search=args["search"], limit=args["limit"])
        return asdict(_found(values, "Layer or field not found."))

    def preview_filter(args: Dict[str, Any]) -> Dict[str, Any]:
        preview = accessor.preview_filter(args["layer_name"], _checked_expression(args["expression"]))
        return asdict(_found(preview, "Layer not found."))

    def map_context(_: Dict[str, Any]) -> Dict[str, Any]:
        return asdict(accessor.map_context())

    def _active_after_change() -> Dict[str, str]:
        """``{}`` when QGIS is too busy to read it back: the change is done, it must not look failed."""
        try:
            return accessor.get_active_filters()
        except QGISBusy:
            return {}

    def _resolved_name(reference: str, expression: str) -> str:
        """Name ``apply_filter`` needs for an id or a name, once the expression passed a trial where one is needed."""
        try:
            details = accessor.describe_layer(reference)
            if details is None:
                return reference
            if details.provider_type in _SILENT_SQL_PROVIDERS:
                preview = accessor.preview_filter(details.name, expression)
                if preview is not None and not preview.valid:
                    raise ToolFailure(f"Nothing was applied, the expression is invalid: {preview.error}")
            return details.name
        except FilterRejected:  # memory layer, web service behind OGR: not tried, the apply says what it says
            return reference

    def apply_filter(args: Dict[str, Any]) -> Dict[str, Any]:
        expression = _checked_expression(args["expression"])
        name = _resolved_name(args["layer_name"], expression)
        if not accessor.apply_filter(name, expression, SOURCE):
            raise ToolFailure("Layer not found.")
        answer = {"success": True, "layer_name": name, "expression": expression, "active_filters": _active_after_change()}
        try:
            details = accessor.describe_layer(name)
        except (QGISBusy, FilterRejected):
            details = None
        if details is not None and details.feature_count >= 0:
            answer["feature_count"] = details.feature_count
        return answer

    def cross_filter(args: Dict[str, Any]) -> Dict[str, Any]:
        result = accessor.cross_filter(
            source_layer=args["source_layer"], target_layers=args["target_layers"], predicates=args["predicates"],
            buffer=args["buffer"], coverage_min=args["coverage_min"], operator=args.get("operator"),
            selected_only=args["selected_only"], raster_selection=args.get("raster_selection"),
            point_cloud_criteria=_point_cloud_criteria(args.get("point_cloud_criteria")),
            filter_source=args["filter_source"])
        return _report("Cross filter", _found(result, "Source layer not found."))

    def geometry_filter(args: Dict[str, Any]) -> Dict[str, Any]:
        return _report("Geometry filter", accessor.cross_filter_by_geometry(
            wkt=args["wkt"], crs=args["crs"], target_layers=args["target_layers"], predicates=args["predicates"],
            buffer=args["buffer"], coverage_min=args["coverage_min"], operator=args.get("operator")))

    def point_cloud_filter(args: Dict[str, Any]) -> Dict[str, Any]:
        criteria = _point_cloud_criteria(args["criteria"])
        if criteria is None:
            raise ToolFailure("At least one criterion is required.")
        return _report("Point cloud filter", accessor.filter_point_clouds(
            layers=args["layers"], criteria=criteria, operator=args.get("operator")))

    def clear_filters(args: Dict[str, Any]) -> Dict[str, Any]:
        return _report("Clear", accessor.clear_filters(layers=args["layers"]))

    def apply_favorite(args: Dict[str, Any]) -> Dict[str, Any]:
        step = _found(accessor.apply_favorite(args["favorite_id"]), "Favorite not found.")
        return {"step": asdict(step), "active_filters": _active_after_change()}

    def zoom_to(args: Dict[str, Any]) -> Dict[str, Any]:
        return asdict(accessor.zoom_to(layer=args.get("layer"), extent_wkt=args.get("extent_wkt"), crs=args.get("crs"),
                                       selected_only=args["selected_only"]))

    def select_features(args: Dict[str, Any]) -> Dict[str, Any]:
        return asdict(accessor.select_features(args["layer"], expression=args["expression"], clear=args["clear"],
                                               add=args["add"]))

    def set_layers_visibility(args: Dict[str, Any]) -> Dict[str, Any]:
        return _report("Visibility", accessor.set_layers_visibility(args["layers"], args["visible"]))

    def add_layer(args: Dict[str, Any]) -> Dict[str, Any]:
        problem = source_problem(args["source"], allow_remote_sources)
        if problem:
            raise ToolFailure(f"This layer cannot be added: {problem}.")
        return asdict(accessor.add_layer(args["source"], name=args["name"], kind=args["kind"]))

    def remove_layers(args: Dict[str, Any]) -> Dict[str, Any]:
        return _report("Remove", accessor.remove_layers(args["layers"]))

    def search_open_data(args: Dict[str, Any]) -> Dict[str, Any]:
        return asdict(accessor.search_open_data(args["query"], platform=_allowed_platform(args["platform"]),
                                                limit=args["limit"], extra_domains=extra_domains))

    def search_imagery(args: Dict[str, Any]) -> Dict[str, Any]:
        return asdict(accessor.search_imagery(
            bbox=args.get("bbox"), start=args["start"], end=args["end"], max_cloud=args["max_cloud"],
            collections=args.get("collections"), limit=args["limit"], platform=_allowed_platform(args["platform"]),
            extra_domains=extra_domains))

    def add_service_layer(args: Dict[str, Any]) -> Dict[str, Any]:
        return asdict(accessor.add_service_layer(_allowed_platform(args["platform"]), args["typename"],
                                                 name=args["name"], extra_domains=extra_domains))

    def export_layers(args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            folder = resolve_export_folder(prepare_export_root(export_root), args["subfolder"])
        except ExportRootError as exc:
            logger.error("Agent export refused: %s (%s)", exc, export_root)
            raise ToolFailure("The export folder is not available.") from None
        except ValueError:
            raise ToolFailure("Invalid subfolder.") from None
        answer = _report("Export", accessor.export_layers(
            layers=args["layers"], folder=str(folder), vector_format=args["vector_format"],
            raster_format=args["raster_format"], point_cloud_format=args["point_cloud_format"],
            crs=args.get("crs")))
        # The paths of this machine are not sent to the provider.
        answer["outputs"] = {name: os.path.relpath(path, str(folder)) for name, path in answer["outputs"].items()}
        return answer

    handlers = {
        "list_layers": list_layers, "filter_state": filter_state, "list_favorites": list_favorites,
        "describe_layer": describe_layer, "field_values": field_values, "preview_filter": preview_filter,
        "map_context": map_context, "apply_filter": apply_filter, "cross_filter": cross_filter,
        "geometry_filter": geometry_filter, "point_cloud_filter": point_cloud_filter,
        "clear_filters": clear_filters, "apply_favorite": apply_favorite, "export_layers": export_layers,
        "zoom_to": zoom_to, "select_features": select_features, "set_layers_visibility": set_layers_visibility,
        "add_layer": add_layer, "remove_layers": remove_layers, "search_open_data": search_open_data,
        "add_service_layer": add_service_layer, "search_imagery": search_imagery,
    }
    return {name: _guarded(handler) for name, handler in handlers.items()}
