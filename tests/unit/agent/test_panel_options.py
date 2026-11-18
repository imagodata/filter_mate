# -*- coding: utf-8 -*-
"""The options of FilterMate's panels an agent may set (core/agent/panel_options.py): which keys, which values."""
import pytest

from core.agent.panel_options import LayerFacts, check_export_changes, check_layer_changes, resolve_layer
from core.domain.api_requests import PREDICATES

pytestmark = pytest.mark.unit

COMMUNES = LayerFacts("communes_a1", "communes", True)
ROUTES = LayerFacts("routes_c3", "routes", True)
MNT = LayerFacts("mnt_f6", "mnt", False)
LAYERS = [COMMUNES, ROUTES, MNT]
FIELDS = ["fid", "nom", "nmo_like", "insee"]


def no_problem(_):
    return ""


def test_exploring_values_are_kept_as_stored():
    clean, problems = check_layer_changes(
        {"single_selection_expression": '"nom"', "current_exploring_groupbox": "multiple_selection", "is_tracking": True},
        {}, layer=COMMUNES, layers=LAYERS, predicates=PREDICATES, expression_problem=no_problem, fields=FIELDS)
    assert problems == [] and clean["exploring"] == {"single_selection_expression": '"nom"',
                                                     "current_exploring_groupbox": "multiple_selection",
                                                     "is_tracking": True}


def test_bad_expression_refuses_the_whole_call():
    clean, problems = check_layer_changes(
        {"custom_selection_expression": '"nmo"', "is_tracking": True}, {}, layer=COMMUNES, layers=LAYERS,
        predicates=PREDICATES, expression_problem=lambda text: "unknown field nmo" if "nmo" in text else "",
        fields=FIELDS)
    assert clean == {} and problems == ["custom_selection_expression: unknown field nmo"]


def test_filtering_values_tick_their_box_and_store_ids():
    clean, problems = check_layer_changes(
        {}, {"layers_to_filter": ["routes"], "geometric_predicates": ["Intersect"], "buffer_value": 50},
        layer=COMMUNES, layers=LAYERS, predicates=PREDICATES, expression_problem=no_problem, fields=FIELDS)
    assert problems == []
    assert clean["filtering"] == {"layers_to_filter": ["routes_c3"], "has_layers_to_filter": True,
                                  "geometric_predicates": ["Intersect"], "has_geometric_predicates": True,
                                  "buffer_value": 50.0, "has_buffer_value": True}


def test_a_box_given_with_its_value_is_kept():
    clean, problems = check_layer_changes({}, {"buffer_type": "Flat", "has_buffer_type": False}, layer=COMMUNES,
                                          layers=LAYERS, predicates=PREDICATES, expression_problem=no_problem, fields=FIELDS)
    assert problems == [] and clean["filtering"] == {"buffer_type": "Flat", "has_buffer_type": False}


def test_a_listed_raster_target_is_kept():
    listed = LayerFacts("mnt_f6", "mnt", False, listed_target=True)
    clean, problems = check_layer_changes(
        {}, {"layers_to_filter": ["routes", "mnt"]}, layer=COMMUNES, layers=[COMMUNES, ROUTES, listed],
        predicates=PREDICATES, expression_problem=no_problem, fields=FIELDS)
    assert problems == [] and clean["filtering"]["layers_to_filter"] == ["routes_c3", "mnt_f6"]


@pytest.mark.parametrize("filtering, problem", [
    ({"layers_to_filter": ["communes"]}, "layers_to_filter: not the layer itself"),
    ({"layers_to_filter": ["mnt"]}, "layers_to_filter: mnt is not a target the panel lists for a vector layer"),
    ({"geometric_predicates": ["Near"]}, "geometric_predicates: Near is not one of"),
    ({"buffer_value": 2e6}, "buffer_value: between -1000000 and 1000000"),
    ({"buffer_value": "far"}, "buffer_value: a number"),
    ({"buffer_type": "Mitre"}, "buffer_type: one of Round, Flat, Square"),
    ({"buffer_segments": 0}, "buffer_segments: a whole number from 1 to 100"),
    ({"other_layers_combine_operator": "XOR"}, "other_layers_combine_operator: one of AND, AND NOT, OR"),
    ({"has_buffer_value": "yes"}, "has_buffer_value: true or false"),
    ({"bogus": 1}, "bogus: not an option of a layer"),
    ({"is_tracking": True}, "is_tracking: not an option of FILTERING"),
])
def test_filtering_refusals(filtering, problem):
    clean, problems = check_layer_changes({}, filtering, layer=COMMUNES, layers=LAYERS, predicates=PREDICATES,
                                          expression_problem=no_problem, fields=FIELDS)
    assert clean == {} and problems and problems[0].startswith(problem), problems


@pytest.mark.parametrize("exploring, problem", [
    ({"current_exploring_groupbox": "everything"}, "current_exploring_groupbox: one of single_selection"),
    ({"single_selection_expression": "x" * 1001}, "single_selection_expression: at most 1000 characters"),
    ({"is_selecting": True}, "is_selecting: not an option of a layer"),
    ({"has_layers_to_filter": True}, "has_layers_to_filter: not an option of EXPLORING"),
    ({"single_selection_expression": '"nom" || "insee"'}, "single_selection_expression: a field of the layer"),
])
def test_exploring_refusals(exploring, problem):
    clean, problems = check_layer_changes(exploring, {}, layer=COMMUNES, layers=LAYERS, predicates=PREDICATES,
                                          expression_problem=no_problem, fields=FIELDS)
    assert clean == {} and problems[0].startswith(problem), problems


def test_a_raster_layer_is_refused():
    clean, problems = check_layer_changes({"is_tracking": True}, {}, layer=MNT, layers=LAYERS, predicates=PREDICATES,
                                          expression_problem=no_problem, fields=FIELDS)
    assert clean == {} and problems == ["mnt: only a vector layer has these options"]


def test_export_values_map_to_the_stored_keys():
    clean, problems = check_export_changes(
        {"layers_to_export": ["communes"], "datatype_to_export": "GPKG", "zip_to_export": "/tmp/out/a.zip"},
        layers=LAYERS, formats={"GPKG", "GeoJSON"}, crs_problem=no_problem, folder_problem=no_problem)
    assert problems == [] and clean == {"LAYERS_TO_EXPORT": ["communes_a1"], "HAS_LAYERS_TO_EXPORT": True,
                                        "DATATYPE_TO_EXPORT": "GPKG", "HAS_DATATYPE_TO_EXPORT": True,
                                        "ZIP_TO_EXPORT": "/tmp/out/a.zip", "HAS_ZIP_TO_EXPORT": True}


@pytest.mark.parametrize("changes, problem", [
    ({"datatype_to_export": "DXF"}, "datatype_to_export: DXF is not a format FilterMate exports"),
    ({"styles_to_export": "LYRX"}, "styles_to_export: one of QML, SLD"),
    ({"zip_to_export": "/tmp/out/a.tar"}, "zip_to_export: a path ending in .zip"),
    ({"layers_to_export": ["nowhere"]}, "layers_to_export: no layer nowhere"),
    ({"projection_to_export": "EPSG:0"}, "projection_to_export: bad crs"),
    ({"output_folder_to_export": "/nope"}, "output_folder_to_export: no such folder"),
    ({"batch_zip": 1}, "batch_zip: true or false"),
    ({"format": "GPKG"}, "format: not an export option"),
])
def test_export_refusals(changes, problem):
    clean, problems = check_export_changes(changes, layers=LAYERS, formats={"GPKG"},
                                           crs_problem=lambda value: "bad crs" if value == "EPSG:0" else "",
                                           folder_problem=lambda value: "no such folder" if value == "/nope" else "")
    assert clean == {} and problems[0].startswith(problem), problems


def test_two_layers_of_one_name_are_named_as_such():
    twins = [COMMUNES, LayerFacts("communes_b2", "communes", True)]
    assert resolve_layer("communes", twins) is None and resolve_layer("communes_b2", twins).layer_id == "communes_b2"
    clean, problems = check_layer_changes({}, {"layers_to_filter": ["communes"]}, layer=ROUTES, layers=twins + [ROUTES],
                                          predicates=PREDICATES, expression_problem=no_problem, fields=FIELDS)
    assert clean == {} and problems == ["layers_to_filter: two layers are named communes, give its id"]


def test_the_chat_offers_the_tools_of_the_panels():
    from core.agent.tool_catalog import chat_tools
    from filtermate_api.accessor import InMemoryAccessor
    from filtermate_api.agent_tools import build_handlers
    names = {"layer_options", "set_layer_options", "export_options", "set_export_options"}
    assert names <= {tool.name for tool in chat_tools()}
    assert names <= set(build_handlers(InMemoryAccessor(), export_root=None))


PANEL_TOOLS = {"layer_options", "set_layer_options", "export_options", "set_export_options"}


def test_the_tools_of_the_panels_come_with_their_skill():
    """The token diet (2026-11-16): a new tool must not weigh on the first request; the skill panels brings them."""
    from core.agent.families import bringing
    from core.agent.skills import SKILLS
    from core.agent.tool_catalog import chat_tools
    held = bringing(chat_tools(), SKILLS.values())
    assert all(held.get(name) == ["panels"] for name in PANEL_TOOLS), {name: held.get(name) for name in PANEL_TOOLS}


def test_the_bench_simulates_the_tools_of_the_panels():
    import importlib.util
    import sys
    from pathlib import Path
    path = Path(__file__).resolve().parents[3] / "scripts" / "agent_eval.py"
    spec = importlib.util.spec_from_file_location("agent_eval_panels", path)
    bench = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = bench
    try:
        spec.loader.exec_module(bench)
        project = bench.SimulatedProject()
        handlers = project.handlers()
        assert PANEL_TOOLS <= set(handlers)
        changed = handlers["set_layer_options"]({"layers": [{"layer": "communes", "exploring": {"is_tracking": True}}]})
        assert changed["changed"][0]["layer_name"] == "communes"
        assert handlers["layer_options"]({"layer": "communes"})["exploring"]["is_tracking"] is True
        assert bench._touched({"layers": [{"layer": "communes_a1"}]}, project.by_ref) == ["communes"]
    finally:
        sys.modules.pop(spec.name, None)


def test_a_change_keeps_only_the_keys_the_turn_changed():
    """2026-11-16, real panel: on a change of layer the panel set has_buffer_type itself; compared whole, the state
    looked changed by the user and the undo left the layer as it was."""
    from core.agent.panel_options import state_change, state_part
    before = {"filtering": {"buffer_value": 0.0, "has_buffer_type": False}, "exploring": {"is_tracking": False}}
    after = {"filtering": {"buffer_value": 25.0, "has_buffer_type": False, "has_buffer_value": True},
             "exploring": {"is_tracking": False}}
    was, made = state_change(before, after)
    assert was == {"values": {"filtering": {"buffer_value": 0.0}}, "absent": [["filtering", "has_buffer_value"]]}
    assert made == {"values": {"filtering": {"buffer_value": 25.0, "has_buffer_value": True}}, "absent": []}
    now = {"filtering": {"buffer_value": 25.0, "has_buffer_type": True, "has_buffer_value": True}}  # the panel's own
    assert state_part(now, made) == made and state_part(now, was) != was
    assert state_change(before, before) == ({"values": {}, "absent": []}, {"values": {}, "absent": []})
