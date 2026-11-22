"""The tools of the chat, running inside QGIS on the same accessor as the REST routes.

They answer what the routes answer and keep their checks. No FastAPI, no pydantic:
the argument schemas are enforced by ``core.agent.tool_executor`` before a handler runs.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlsplit

from .accessor import FavoritesUnavailable, FilterMateAccessor, FilterRejected, LayerProtected
from .export_root import ExportRootError, prepare_export_root, resolve_export_folder
from .filter_combine import combined
from .layer_listing import select_layers, short_filter
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


MAX_LISTED_SELECTIONS = 50  # map_context lists at most this many layers with a selection (introspection.py)
NOTHING_KEPT = ("No feature kept. Check the direction of the predicate (the target is tested against the source), "
                "the buffer, and that the source holds the features meant (its selection, its filter).")


def _with_nothing_kept(answer: Dict[str, Any]) -> Dict[str, Any]:
    """A layer the filter emptied is said so: the model then checks its call instead of reporting success."""
    for name, count in (answer.get("kept") or {}).items():
        if count == 0:
            answer.setdefault("warnings", {})[name] = NOTHING_KEPT
    return answer


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
        except (FilterRejected, FavoritesUnavailable, LayerProtected) as exc:
            raise ToolFailure(str(exc)) from None
    return run


def _renamed(text: str, address: str, name: str) -> str:
    """``text`` with the address of a platform replaced by the name a model knows it by, whatever its case.

    And any other address of its server, then the name of that server alone: a request that failed is told by the
    address it was sent to, which is the one the user gave with a search added to it and still holds its key
    ("Error transferring https://api.example.org/search?apikey=...&q=Lyon"), and a server that could not be
    reached by its host ("Host overpass.example.org not found"). A model has no need of either (2026-11-15).
    """
    if not address or address.lower() == name.lower():
        return text
    text = re.sub(re.escape(address), lambda _match: name, text, flags=re.IGNORECASE)
    try:
        parts = urlsplit(address) if "://" in address else None
        host, server = (parts.hostname or "", parts.netloc.rsplit("@", 1)[-1]) if parts is not None else ("", "")
    except ValueError:
        host = server = ""
    if not host:
        return text
    # This machine holds other servers than the one named: there, only the same port is the same server.
    local = host in ("localhost", "127.0.0.1", "::1")
    there = re.escape(server) if local else re.escape(f"[{host}]" if ":" in host else host) + r"\.?(?::\d+)?"
    text = re.sub(r"https?://(?:[^/\s@]*@)?" + there + r"(?![\w.-])[^\s\"'<>]*", lambda _match: name, text,
                  flags=re.IGNORECASE)
    if not local and host.lower() != name.lower():
        text = re.sub(r"(?<![\w.-])" + re.escape(host) + r"\.?(?![\w-])", lambda _match: name, text, flags=re.IGNORECASE)
    return text


# The arguments of the tools that name a layer, by an id or a name.
LAYER_ARGUMENTS = ("layer", "layers", "layer_name", "source_layer", "target_layers", "extent_layer", "join_layer",
                   "raster", "guide_layer", "example_layer", "above")
# What set_layer_style takes besides the layer and the mode: always given (a default of the schema), or only when
# the model gave it.
_STYLE_DEFAULTS = ("field", "color", "ramp", "classes", "method", "invert", "band", "discrete", "blend",
                   "multidirectional")
_STYLE_OPTIONAL = ("opacity", "minimum", "maximum", "rules", "cut", "width", "z_factor", "per_dot", "center")
# What set_labels takes besides its first arguments: the look of the labels, passed only when the model gave it.
_LABEL_OPTIONS = ("visible_to_scale", "background", "background_opacity", "callouts", "font", "bold", "italic", "wrap",
                  "priority", "obstacle")


def _one_layer_per_name(accessor: FilterMateAccessor, handler: Handler) -> Handler:
    """Refuse a call that names a layer by a name several layers have: each tool picked one its own way, without a
    word (the first vector one, the first of the kind wanted, the first of any kind), and a call could reach another
    layer than the one before it. An id names one layer; list_layers gives it."""
    def run(arguments: Dict[str, Any]) -> Any:
        named = [str(value) for key in LAYER_ARGUMENTS
                 for value in (arguments.get(key) if isinstance(arguments.get(key), list) else [arguments.get(key)])
                 if isinstance(value, str) and value]
        if arguments.get("group") is True:  # rename_layer on a group: its "layer" is the name of a group
            named = []
        names = getattr(accessor, "layer_names", None)
        if named and names is not None:
            try:
                known = names()
            except QGISBusy:
                known = {}  # the tool itself says QGIS is busy
            for reference in dict.fromkeys(named):
                same = [layer_id for layer_id, name in known.items() if name == reference]
                if reference not in known and len(same) > 1:
                    raise ToolFailure(f"{len(same)} layers are named {reference!r}: name the one meant by its "
                                      f"layer_id ({', '.join(same[:6])}); list_layers and describe_layer tell them "
                                      "apart.")
        return handler(arguments)
    return run


def build_handlers(accessor: FilterMateAccessor, export_root: Path, allow_remote_sources: bool = False,
                   platforms: Sequence[str] = (), extra_domains: str = "", share_values: bool = True,
                   platform_aliases: Optional[Mapping[str, str]] = None) -> Dict[str, Handler]:
    """One handler per tool of the chat (see ``core.agent.tool_catalog.chat_tools``).

    ``allow_remote_sources`` False: no layer is read over the network. ``platforms``: the only ones that can be
    searched, each as the user enabled it; ``extra_domains`` says where the user's own portals are.
    ``share_values`` False: what an algorithm answers besides its layers (statistics) is not sent.
    """
    enabled_platforms = {name.lower() for name in platforms}

    def _allowed_platform(name: str) -> str:
        if name.lower() not in enabled_platforms:
            raise ToolFailure(f"{name!r} is not enabled in the agent sources. Enabled: "
                              f"{', '.join(sorted(enabled_platforms)) or 'none'}.")
        # A service the user added is named by its id: its address, which may hold a key, never goes to the model.
        return (platform_aliases or {}).get(name.lower(), name)

    def _asked(args: Dict[str, Any], call: Callable[[str], Any]) -> Any:
        """``call`` on the platform a model named; what it answers or refuses names the platform as the model did.

        2026-11-14: the id went in, and the address came back, in ``platform`` of the answer and in the words of a
        refusal ("https://api.example.org/search?apiKey=... did not answer").
        """
        named = args["platform"]
        resolved = _allowed_platform(named)
        try:
            answer = call(resolved)
        except FilterRejected as exc:
            raise FilterRejected(_renamed(str(exc), resolved, named)) from None
        if isinstance(answer, dict) and "platform" in answer:
            answer["platform"] = named
        return answer

    def list_layers(args: Dict[str, Any]) -> Dict[str, Any]:
        return select_layers((asdict(layer) for layer in accessor.list_layers()), args.get("kind"),
                             args.get("name_contains"), args.get("limit"))

    def filter_state(_: Dict[str, Any]) -> Dict[str, Any]:
        return {"layers": [short_filter(asdict(layer), "subset") for layer in accessor.get_filter_state()]}

    def list_favorites(_: Dict[str, Any]) -> Dict[str, Any]:
        return {"favorites": [asdict(favorite) for favorite in accessor.list_favorites()]}

    def describe_layer(args: Dict[str, Any]) -> Dict[str, Any]:
        return asdict(_found(accessor.describe_layer(args["layer"]), "Layer not found."))

    def field_values(args: Dict[str, Any]) -> Dict[str, Any]:
        values = accessor.field_values(args["layer"], args["field"], search=args["search"], limit=args["limit"])
        return asdict(_found(values, "Layer or field not found."))

    def layer_statistics(args: Dict[str, Any]) -> Dict[str, Any]:
        statistics = accessor.layer_statistics(
            args["layer"], field_name=args["field"], group_by=args["group_by"], measure=args["measure"],
            selected_only=args["selected_only"], limit=args["limit"])
        return asdict(_found(statistics, "Layer or field not found."))

    def sample_features(args: Dict[str, Any]) -> Dict[str, Any]:
        sample = accessor.sample_features(
            args["layer"], limit=args["limit"], fields=args.get("fields"), expression=args["expression"],
            selected_only=args["selected_only"], geometry=args["geometry"])
        return asdict(_found(sample, "Layer not found."))

    def identify_at(args: Dict[str, Any]) -> Dict[str, Any]:
        return asdict(accessor.identify_at(args["x"], args["y"], crs=args["crs"], layers=args.get("layers"),
                                           tolerance=args.get("tolerance"), limit=args["limit"]))

    def find_algorithms(args: Dict[str, Any]) -> Dict[str, Any]:
        return asdict(accessor.find_algorithms(args["query"], limit=args["limit"]))

    def describe_algorithm(args: Dict[str, Any]) -> Dict[str, Any]:
        return asdict(accessor.describe_algorithm(args["algorithm_id"]))

    def run_algorithm(args: Dict[str, Any]) -> Dict[str, Any]:
        answer = asdict(accessor.run_algorithm(args["algorithm_id"], parameters=args.get("parameters") or {},
                                               names=args.get("names"), share_values=share_values))
        counts = [row.get("feature_count") for row in answer["layers"]]
        if len(counts) == 1 and isinstance(counts[0], int):
            answer["feature_count"] = counts[0]  # what the card of the chat shows
        return answer

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

    def _resolved_layer(reference: str, expression: str,
                        operator: Optional[str]) -> Tuple[str, str, Optional[int], str, str]:
        """The layer an id or a name designates, once the expression passed a trial where one is needed.

        ``(target, name, total, applied, replaced)``: the id ``apply_filter`` applies to (the layer the protection
        checked: a name may be shared by several layers), the name the answer shows, the features of the layer when
        it had no filter yet (``None`` otherwise): the total to compare with; the expression to apply (the new
        condition combined with the current filter when ``operator`` says so), and the filter it replaces.
        """
        try:
            details = accessor.describe_layer(reference)
        except FilterRejected:  # memory layer, web service behind OGR: not tried, the apply says what it says
            details = None
        previous = details.subset if details is not None else (accessor.get_active_filters() or {}).get(reference, "")
        try:
            applied, replaced = combined(previous, expression, operator)
        except ValueError as exc:
            raise ToolFailure(str(exc)) from None
        if details is None:
            return reference, reference, None, applied, replaced
        if details.provider_type in _SILENT_SQL_PROVIDERS:
            try:
                preview = accessor.preview_filter(details.layer_id, applied)
            except FilterRejected:
                preview = None
            if preview is not None and not preview.valid:
                raise ToolFailure(f"Nothing was applied, the expression is invalid: {preview.error}")
        total = details.feature_count if not details.subset and details.feature_count >= 0 else None
        return details.layer_id, details.name, total, applied, replaced

    def apply_filter(args: Dict[str, Any]) -> Dict[str, Any]:
        expression = _checked_expression(args["expression"])
        target, name, total, applied, replaced = _resolved_layer(args["layer_name"], expression, args.get("operator"))
        if not accessor.apply_filter(target, applied, SOURCE):
            raise ToolFailure("Layer not found.")
        answer = {"success": True, "layer_name": name, "expression": applied, "active_filters": _active_after_change()}
        if replaced and replaced != applied:
            answer["replaced_filter"] = replaced  # the model sees a filter it may have meant to keep
        try:
            details = accessor.describe_layer(target)
        except (QGISBusy, FilterRejected):
            details = None
        if details is not None and details.feature_count >= 0:
            answer["feature_count"] = details.feature_count
            if total is not None:
                answer["total_count"] = total
            if details.feature_count == 0:
                answer["warning"] = "No feature kept: check the values and the field names (describe_layer, field_values)."
        return answer

    def _check_source_selection(source: str) -> None:
        """A vector source with no selection and no filter would be used whole: the model must mean it."""
        try:
            details = accessor.describe_layer(source)
            if details is None or details.layer_kind != "vector" or details.subset:
                return
            selections = accessor.map_context().selections
        except (QGISBusy, FilterRejected):
            return
        if len(selections) >= MAX_LISTED_SELECTIONS:  # the list is cut: it cannot tell
            return
        if not any(source in (item.get("layer_id"), item.get("name")) or details.layer_id == item.get("layer_id")
                   for item in selections):
            raise ToolFailure(
                f"Nothing is selected on '{details.name}' and it has no filter, so every feature would be used. Select "
                "the features meant with select_features first, or call again with selected_only false to use them all.")

    def cross_filter(args: Dict[str, Any]) -> Dict[str, Any]:
        if args["selected_only"] and not args.get("raster_selection") and not args.get("point_cloud_criteria"):
            _check_source_selection(args["source_layer"])
        result = accessor.cross_filter(
            source_layer=args["source_layer"], target_layers=args["target_layers"], predicates=args["predicates"],
            buffer=args["buffer"], coverage_min=args["coverage_min"], operator=args.get("operator"),
            selected_only=args["selected_only"], raster_selection=args.get("raster_selection"),
            point_cloud_criteria=_point_cloud_criteria(args.get("point_cloud_criteria")),
            filter_source=args["filter_source"])
        return _with_nothing_kept(_report("Cross filter", _found(result, "Source layer not found.")))

    def geometry_filter(args: Dict[str, Any]) -> Dict[str, Any]:
        return _with_nothing_kept(_report("Geometry filter", accessor.cross_filter_by_geometry(
            wkt=args["wkt"], crs=args["crs"], target_layers=args["target_layers"], predicates=args["predicates"],
            buffer=args["buffer"], coverage_min=args["coverage_min"], operator=args.get("operator"))))

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

    def set_layer_style(args: Dict[str, Any]) -> Dict[str, Any]:
        options = {key: args[key] for key in _STYLE_DEFAULTS}
        options.update({key: args.get(key) for key in _STYLE_OPTIONAL})
        # The light of a hillshade is no argument a model reads (the usual one is kept), but a recipe kept before,
        # or a client that knows them, still gives it: followed, and refused when it is no angle, never dropped
        # without a word. The schema no longer bounds them, so they are bounded here (not a number fails both ways).
        for key, top in (("azimuth", 360), ("altitude", 90)):
            value = args.get(key)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= top:
                raise ToolFailure(f"{key} is a number from 0 to {top}")
            options[key] = float(value)
        # A range read from the pixels of a raster is a value as much as a field: not told to a user who shares none.
        options["share_values"] = share_values
        answer = asdict(accessor.set_layer_style(args["layer"], args["mode"], **options))
        # What the call did not set is not told: a hillshade has no ramp, a vector no band.
        return {key: value for key, value in answer.items()
                if value not in (None, "") and not (key == "classes" and not value)}

    def set_labels(args: Dict[str, Any]) -> Dict[str, Any]:
        return asdict(accessor.set_labels(args["layer"], field=args["field"], enabled=args["enabled"],
                                          size=args.get("size"), color=args["color"], buffer=args["buffer"],
                                          expression=args["expression"],
                                          visible_from_scale=args.get("visible_from_scale"),
                                          placement=args["placement"],
                                          **{key: args[key] for key in _LABEL_OPTIONS if args.get(key) is not None}))

    def create_layout(args: Dict[str, Any]) -> Dict[str, Any]:
        options = {key: args[key] for key in ("title", "page", "orientation", "extent_layer", "legend", "scale_bar",
                                              "north_arrow")}
        if args.get("template"):
            options["template"] = args["template"]
        options.update({key: args.get(key) for key in ("layers", "extent")})
        return asdict(accessor.create_layout(args["name"], **options))

    def export_layout(args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            folder = resolve_export_folder(prepare_export_root(export_root), args["subfolder"])
        except ExportRootError as exc:
            logger.error("Agent export refused: %s (%s)", exc, export_root)
            raise ToolFailure("The export folder is not available.") from None
        except ValueError:
            raise ToolFailure("Invalid subfolder.") from None
        answer = asdict(accessor.export_layout(args["name"], str(folder), file_format=args["format"], dpi=args["dpi"],
                                               georeference=args.get("georeference", True),
                                               atlas=bool(args.get("atlas")),
                                               single_file=args.get("single_file", True)))
        answer["path"] = os.path.relpath(answer["path"], str(folder))  # the paths of this machine are not sent
        # What a single file of one page does not need to say.
        return {key: value for key, value in answer.items() if value or key not in ("files", "pages", "atlas")}

    def edit_layout(args: Dict[str, Any]) -> Dict[str, Any]:
        return accessor.edit_layout(args["layout"], [dict(change) for change in args["changes"]])

    def describe_layout(args: Dict[str, Any]) -> Dict[str, Any]:
        return accessor.describe_layout(args.get("name") or "")

    def set_atlas(args: Dict[str, Any]) -> Dict[str, Any]:
        options = {"coverage_layer": args.get("coverage_layer") or "", "enabled": args.get("enabled", True),
                   "filter_expression": args.get("filter") or "", "page_name": args.get("page_name") or "",
                   "sort_by": args.get("sort_by") or "", "descending": bool(args.get("descending")),
                   "hide_coverage": bool(args.get("hide_coverage")), "map_mode": args.get("map_mode") or "auto",
                   "margin": args.get("margin", 10), "file_name": args.get("file_name") or "",
                   "maps": args.get("maps")}
        return accessor.set_atlas(args["layout"], **options)

    def _edit_answer(result) -> Dict[str, Any]:
        answer = asdict(result)
        answer["feature_count"] = answer["changed"] + answer["deleted"] + answer["added"]  # what the card shows
        return answer

    def update_features(args: Dict[str, Any]) -> Dict[str, Any]:
        return _edit_answer(accessor.update_features(args["layer"], values=args.get("values"),
                                                     formulas=args.get("formulas"), expression=args["expression"],
                                                     selected_only=args["selected_only"]))

    def delete_features(args: Dict[str, Any]) -> Dict[str, Any]:
        return _edit_answer(accessor.delete_features(args["layer"], expression=args["expression"],
                                                     selected_only=args["selected_only"]))

    def add_features(args: Dict[str, Any]) -> Dict[str, Any]:
        return _edit_answer(accessor.add_features(args["layer"], features=args["features"], crs=args["crs"]))

    def set_project_crs(args: Dict[str, Any]) -> Dict[str, Any]:
        return asdict(accessor.set_project_crs(args["crs"]))

    def make_cartogram(args: Dict[str, Any]) -> Dict[str, Any]:
        return accessor.make_cartogram(args["layer"], args["field"], kind=args.get("kind") or "contiguous",
                                       iterations=args.get("iterations") or 8, name=args.get("name") or "")

    def suggest_crs(args: Dict[str, Any]) -> Dict[str, Any]:
        return accessor.suggest_crs(layers=args.get("layers"), purpose=args.get("purpose") or "general")

    def add_field(args: Dict[str, Any]) -> Dict[str, Any]:
        answer = asdict(accessor.add_field(args["layer"], args["name"], field_type=args["type"],
                                           length=args["length"], formula=args["formula"]))
        if not answer.get("formula_error"):
            answer.pop("formula_error", None)
        return answer

    def set_form(args: Dict[str, Any]) -> Dict[str, Any]:
        return accessor.set_form(args["layer"], [dict(entry) for entry in args["fields"]])

    def relations(args: Dict[str, Any]) -> Dict[str, Any]:
        return accessor.relations(args["action"], **{key: args[key] for key in (
            "name", "parent_layer", "parent_field", "child_layer", "child_field", "strength") if key in args})

    def join_layers(args: Dict[str, Any]) -> Dict[str, Any]:
        return asdict(accessor.join_layers(args["layer"], args["join_layer"], args["target_field"], args["join_field"],
                                           fields=args.get("fields"), prefix=args.get("prefix")))

    def group_layers(args: Dict[str, Any]) -> Dict[str, Any]:
        return asdict(accessor.group_layers(args["layers"], group=args["group"], at_top=args["at_top"],
                                            above=args.get("above", "")))

    def rename_layer(args: Dict[str, Any]) -> Dict[str, Any]:
        return asdict(accessor.rename_layer(args["layer"], args["name"], group=args.get("group", False)))

    def bookmark(args: Dict[str, Any]) -> Dict[str, Any]:
        return asdict(accessor.bookmark(args["action"], args["name"], extent_wkt=args.get("extent_wkt", ""),
                                        crs=args.get("crs", "")))

    def map_theme(args: Dict[str, Any]) -> Dict[str, Any]:
        return asdict(accessor.map_theme(args["action"], args["name"]))

    def set_layers_visibility(args: Dict[str, Any]) -> Dict[str, Any]:
        return _report("Visibility", accessor.set_layers_visibility(args["layers"], args["visible"]))

    def segment_objects(args: Dict[str, Any]) -> Dict[str, Any]:
        answer = asdict(accessor.segment_objects(args["raster"], args["guide_layer"], selected_only=args["selected_only"],
                                                 limit=args["limit"], name=args["name"]))
        return {key: value for key, value in answer.items() if value is not None}

    def similar_objects(args: Dict[str, Any]) -> Dict[str, Any]:
        if bool(args["example_layer"]) == bool(args["use_dock_object"]):
            raise ToolFailure("Give an example: example_layer (with its one feature selected) or use_dock_object, "
                              "one of them.")
        answer = asdict(accessor.similar_objects(
            args["raster"], example_layer=args["example_layer"], use_dock_object=args["use_dock_object"],
            extent_wkt=args["extent_wkt"], extent_crs=args["extent_crs"], same_shape=args["same_shape"],
            name=args["name"]))
        return {key: value for key, value in answer.items() if value is not None}

    def add_layer(args: Dict[str, Any]) -> Dict[str, Any]:
        problem = source_problem(args["source"], allow_remote_sources)
        if problem:
            raise ToolFailure(f"This layer cannot be added: {problem}.")
        return asdict(accessor.add_layer(args["source"], name=args["name"], kind=args["kind"]))

    def remove_layers(args: Dict[str, Any]) -> Dict[str, Any]:
        return _report("Remove", accessor.remove_layers(args["layers"]))

    def search_open_data(args: Dict[str, Any]) -> Dict[str, Any]:
        return _asked(args, lambda platform: asdict(accessor.search_open_data(
            args["query"], platform=platform, limit=args["limit"], extra_domains=extra_domains)))

    def search_imagery(args: Dict[str, Any]) -> Dict[str, Any]:
        return _asked(args, lambda platform: asdict(accessor.search_imagery(
            bbox=args.get("bbox"), start=args["start"], end=args["end"], max_cloud=args["max_cloud"],
            collections=args.get("collections"), limit=args["limit"], platform=platform,
            extra_domains=extra_domains)))

    def add_service_layer(args: Dict[str, Any]) -> Dict[str, Any]:
        return _asked(args, lambda platform: asdict(accessor.add_service_layer(
            platform, args["typename"], name=args["name"], extra_domains=extra_domains)))

    def find_place(args: Dict[str, Any]) -> Dict[str, Any]:
        return _asked(args, lambda platform: asdict(accessor.find_place(
            args["query"], platform=platform, limit=args["limit"], extra_domains=extra_domains)))

    def add_basemap(args: Dict[str, Any]) -> Dict[str, Any]:
        return _asked(args, lambda platform: asdict(accessor.add_basemap(
            platform, name=args["name"], extra_domains=extra_domains)))

    def add_elevation(args: Dict[str, Any]) -> Dict[str, Any]:
        answer = _asked(args, lambda platform: asdict(accessor.add_elevation(
            platform, extent_wkt=args["extent_wkt"], crs=args["crs"], resolution=args.get("resolution"),
            target_crs=args["target_crs"], name=args["name"], extra_domains=extra_domains)))
        return {key: value for key, value in answer.items() if value not in (None, "")}

    def add_population(args: Dict[str, Any]) -> Dict[str, Any]:
        answer = _asked(args, lambda platform: asdict(accessor.add_population(
            platform, extent_wkt=args["extent_wkt"], crs=args["crs"], resolution=args.get("resolution"),
            name=args["name"], extra_domains=extra_domains)))
        return {key: value for key, value in answer.items() if value not in (None, "")}

    def add_osm_features(args: Dict[str, Any]) -> Dict[str, Any]:
        answer = _asked(args, lambda platform: asdict(accessor.add_osm_features(
            platform, args["tags"], extent_wkt=args["extent_wkt"], crs=args["crs"], geometry=args["geometry"],
            name=args["name"], extra_domains=extra_domains)))
        answer["feature_count"] = sum(row.get("feature_count", 0) for row in answer["layers"])  # the card shows it
        return {key: value for key, value in answer.items() if value not in (None, "")}

    def contour_lines(args: Dict[str, Any]) -> Dict[str, Any]:
        answer = asdict(accessor.contour_lines(args["layer"], args["interval"],
                                               index_interval=args.get("index_interval"), band=args["band"],
                                               name=args["name"], min_length=args.get("min_length"),
                                               # The heights of a raster of the user are values of the project:
                                               # told neither in the answer nor in a refusal.
                                               share_values=share_values))
        return {key: value for key, value in answer.items() if value is not None}

    def duplicate_layer(args: Dict[str, Any]) -> Dict[str, Any]:
        return asdict(accessor.duplicate_layer(args["layer"], name=args["name"]))

    def local_copy(args: Dict[str, Any]) -> Dict[str, Any]:
        return asdict(accessor.local_copy(args["layer"], action=args["action"], extent_wkt=args["extent_wkt"],
                                          crs=args["crs"]))

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
            crs=args.get("crs"), styles=args.get("styles") or "none", single_file=bool(args.get("single_file")),
            zip_archive=bool(args.get("zip")), package_name=args.get("package_name") or "export"))

        def relative(path: str) -> str:
            """The paths of this machine are not sent to the provider; a name in the zip is relative already."""
            return os.path.relpath(path, str(folder)) if os.path.isabs(path) else path

        answer["outputs"] = {name: relative(path) for name, path in answer["outputs"].items()}
        answer["styles"] = {name: relative(path) for name, path in answer["styles"].items()}
        if answer["package"]:
            answer["package"] = relative(answer["package"])
        # What only a package or styles fill stays out of the answer otherwise.
        return {key: value for key, value in answer.items() if value or key not in ("package", "tables", "styles")}

    def layer_options(args: Dict[str, Any]) -> Dict[str, Any]:
        return accessor.layer_options(args["layer"])

    def set_layer_options(args: Dict[str, Any]) -> Dict[str, Any]:
        return accessor.set_layer_options(args["layers"])

    def set_exploring(args: Dict[str, Any]) -> Dict[str, Any]:
        return accessor.set_exploring(layer=args.get("layer") or "", tools=args.get("tools"),
                                      press=args.get("press"), show=bool(args.get("show")),
                                      raster=args.get("raster"), point_cloud=args.get("point_cloud"))

    def export_options(_: Dict[str, Any]) -> Dict[str, Any]:
        return accessor.export_options()

    def set_export_options(args: Dict[str, Any]) -> Dict[str, Any]:
        return accessor.set_export_options(args["changes"])

    handlers = {
        "list_layers": list_layers, "filter_state": filter_state, "list_favorites": list_favorites,
        "describe_layer": describe_layer, "field_values": field_values, "preview_filter": preview_filter,
        "layer_statistics": layer_statistics, "sample_features": sample_features, "identify_at": identify_at,
        "find_algorithms": find_algorithms, "describe_algorithm": describe_algorithm, "run_algorithm": run_algorithm,
        "set_layer_style": set_layer_style, "set_labels": set_labels,
        "update_features": update_features, "delete_features": delete_features, "add_features": add_features,
        "create_layout": create_layout, "export_layout": export_layout, "set_project_crs": set_project_crs,
        "suggest_crs": suggest_crs, "make_cartogram": make_cartogram,
        "describe_layout": describe_layout, "set_atlas": set_atlas, "edit_layout": edit_layout,
        "add_field": add_field, "join_layers": join_layers, "set_form": set_form, "relations": relations,
        "group_layers": group_layers, "rename_layer": rename_layer, "map_theme": map_theme,
        "bookmark": bookmark,
        "map_context": map_context, "apply_filter": apply_filter, "cross_filter": cross_filter,
        "geometry_filter": geometry_filter, "point_cloud_filter": point_cloud_filter,
        "clear_filters": clear_filters, "apply_favorite": apply_favorite, "export_layers": export_layers,
        "zoom_to": zoom_to, "select_features": select_features, "set_layers_visibility": set_layers_visibility,
        "add_layer": add_layer, "remove_layers": remove_layers, "search_open_data": search_open_data,
        "add_service_layer": add_service_layer, "add_basemap": add_basemap, "find_place": find_place, "search_imagery": search_imagery,
        "add_elevation": add_elevation, "contour_lines": contour_lines, "duplicate_layer": duplicate_layer,
        "local_copy": local_copy,
        "add_population": add_population,
        "add_osm_features": add_osm_features,
        "segment_objects": segment_objects, "similar_objects": similar_objects,
        "layer_options": layer_options, "set_layer_options": set_layer_options, "set_exploring": set_exploring,
        "export_options": export_options,
        "set_export_options": set_export_options,
    }
    return {name: _guarded(_one_layer_per_name(accessor, handler)) for name, handler in handlers.items()}
