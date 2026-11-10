# -*- coding: utf-8 -*-
"""The read routes added for the agent, the chat tools on an accessor, and catalog / MCP agreement."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from core.agent.messages import ToolCallPart
from core.agent.tool_catalog import CHAT_ONLY, chat_tools, load_catalog
from core.agent.tool_executor import ToolExecutor
from filtermate_api.accessor import (
    CrossFilterResult, FavoritesUnavailable, FieldValues, FilteredLayer, FilterPreview, FilterRejected,
    InMemoryAccessor, LayerDetails, LayerSummary, MapContext, OperationResult,
)
from filtermate_api.agent_tools import build_handlers
from filtermate_api.main_thread import QGISBusy

ROOT = Path(__file__).resolve().parents[2]


class Accessor(InMemoryAccessor):
    """Records what reaches QGIS, and lets a test choose the answers."""

    def __init__(self, **kwargs):
        super().__init__(layers=[LayerSummary("L1", "communes", "ogr", feature_count=9, crs_authid="EPSG:2154")])
        self.calls = []
        self.answers = kwargs

    def _answer(self, name, default, **seen):
        self.calls.append((name, seen))
        answer = self.answers.get(name, default)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def cross_filter(self, **kwargs):
        return self._answer("cross_filter", CrossFilterResult(filtered=["b"]), **kwargs)

    def cross_filter_by_geometry(self, **kwargs):
        return self._answer("geometry", CrossFilterResult(filtered=["b"]), **kwargs)

    def filter_point_clouds(self, **kwargs):
        return self._answer("point_clouds", OperationResult(done=["p"]), **kwargs)

    def clear_filters(self, **kwargs):
        return self._answer("clear", OperationResult(done=["a"]), **kwargs)

    def export_layers(self, **kwargs):
        return self._answer("export", OperationResult(done=["a"]), **kwargs)

    def get_filter_state(self):
        return self._answer("state", [FilteredLayer("L1", "communes", "vector", subset="a")])

    def describe_layer(self, layer):
        return self._answer("describe", InMemoryAccessor.describe_layer(self, layer), layer=layer)

    def field_values(self, layer, field_name, search="", limit=50):
        return self._answer("values", FieldValues("communes", field_name, ["x"]), layer=layer, search=search, limit=limit)

    def preview_filter(self, layer_name, expression):
        return self._answer("preview", FilterPreview(layer_name, expression, True, 4), expression=expression)

    def map_context(self):
        return self._answer("map", MapContext(available=True, extent_wkt="POLYGON((0 0))"))


@pytest.fixture
def api(tmp_path):
    return Accessor(), tmp_path


def run(accessor, root, name, **arguments):
    tools = chat_tools()
    result = ToolExecutor(tools, build_handlers(accessor, root, platforms=("datagouv", "ign_wfs", "earth_search"))).execute(
        ToolCallPart("c", name, arguments))
    return result.is_error, (result.content if result.is_error else json.loads(result.content))


class TestHandlers:
    def test_one_handler_per_chat_tool(self, tmp_path):
        # The tools of the chat alone (its own history) get their handler from the chat controller.
        assert set(build_handlers(Accessor(), tmp_path)) == {tool.name for tool in chat_tools()} - {tool.name for tool in CHAT_ONLY}

    def test_reads(self, api):
        accessor, root = api
        assert run(accessor, root, "list_layers")[1]["layers"][0]["name"] == "communes"
        assert run(accessor, root, "filter_state")[1]["layers"][0]["subset"] == "a"
        assert run(accessor, root, "describe_layer", layer="communes")[1]["layer_id"] == "L1"
        assert run(accessor, root, "map_context")[1]["available"] is True

    def test_field_values_defaults(self, api):
        accessor, root = api
        assert run(accessor, root, "field_values", layer="communes", field="nom")[1]["values"] == ["x"]
        assert accessor.calls[-1] == ("values", {"layer": "communes", "search": "", "limit": 50})

    def test_apply_filter_is_tagged_and_applied(self, api):
        accessor, root = api
        error, answer = run(accessor, root, "apply_filter", layer_name="communes", expression="a = 1", source="spoof")
        assert not error and answer["active_filters"] == {"communes": "a = 1"}
        assert accessor._last_applied_source == "agent_chat"

    def test_apply_filter_says_the_total_when_the_layer_had_no_filter(self, tmp_path):
        accessor = Accessor(describe=LayerDetails("L1", "communes", "vector", provider_type="postgres", feature_count=12))
        error, answer = run(accessor, tmp_path, "apply_filter", layer_name="communes", expression="a = 1")
        assert not error and answer["feature_count"] == 12 and answer["total_count"] == 12 and "warning" not in answer

    def test_apply_filter_has_no_total_on_a_layer_already_filtered(self, tmp_path):
        accessor = Accessor(describe=LayerDetails("L1", "communes", "vector", provider_type="postgres", feature_count=3,
                                                  subset="b = 2"))
        error, answer = run(accessor, tmp_path, "apply_filter", layer_name="communes", expression="a = 1")
        assert not error and answer["feature_count"] == 3 and "total_count" not in answer

    def test_apply_filter_that_keeps_nothing_says_so(self, tmp_path):
        accessor = Accessor(describe=LayerDetails("L1", "communes", "vector", provider_type="postgres", feature_count=0))
        error, answer = run(accessor, tmp_path, "apply_filter", layer_name="communes", expression="a = 1")
        assert not error and "No feature kept" in answer["warning"]

    def test_cross_filter_says_what_each_target_keeps_and_warns_on_none(self, tmp_path):
        accessor = Accessor(cross_filter=CrossFilterResult(filtered=["b", "c"], kept={"b": 0, "c": 7}))
        error, answer = run(accessor, tmp_path, "cross_filter", source_layer="a", target_layers=["b", "c"],
                            predicates=["Intersect"])
        assert not error, answer
        assert answer["kept"] == {"b": 0, "c": 7}
        assert "direction of the predicate" in answer["warnings"]["b"] and "c" not in answer["warnings"]

    def test_geometry_filter_warns_on_an_emptied_target(self, tmp_path):
        accessor = Accessor(geometry=CrossFilterResult(filtered=["b"], kept={"b": 0}))
        error, answer = run(accessor, tmp_path, "geometry_filter", wkt="POINT(0 0)", crs="EPSG:2154",
                            target_layers=["b"], predicates=["Intersect"])
        assert not error and "No feature kept" in answer["warnings"]["b"]

    @pytest.mark.parametrize("provider", ["ogr", "spatialite"])
    def test_invalid_sql_is_not_applied_where_the_provider_would_accept_it(self, tmp_path, provider):
        accessor = Accessor(describe=LayerDetails("L1", "communes", "vector", provider_type=provider),
                            preview=FilterPreview("communes", "bad", False, error="could not run"))
        assert run(accessor, tmp_path, "apply_filter", layer_name="communes", expression="bad") == (
            True, "Nothing was applied, the expression is invalid: could not run")
        assert not accessor._active

    def test_postgres_rejects_by_itself_so_no_trial_run(self, tmp_path):
        accessor = Accessor(describe=LayerDetails("L1", "communes", "vector", provider_type="postgres"))
        assert run(accessor, tmp_path, "apply_filter", layer_name="communes", expression="a = 1")[0] is False
        assert "preview" not in [name for name, _ in accessor.calls]

    def test_web_service_behind_ogr_is_applied_without_trial(self, tmp_path):
        accessor = Accessor(describe=LayerDetails("L1", "communes", "vector", provider_type="ogr"),
                            preview=FilterRejected("a web service"))
        assert run(accessor, tmp_path, "apply_filter", layer_name="communes", expression="a = 1")[0] is False
        assert accessor._active == {"communes": "a = 1"}

    def test_a_layer_id_is_applied_by_its_name(self, api):
        accessor, root = api
        error, answer = run(accessor, root, "apply_filter", layer_name="L1", expression="a = 1")
        assert not error and answer["layer_name"] == "communes" and accessor._active == {"communes": "a = 1"}

    def test_busy_after_the_change_does_not_look_like_a_failure(self, tmp_path):
        class Busy(Accessor):
            def get_active_filters(self):
                raise QGISBusy("task")

        accessor = Busy()
        error, answer = run(accessor, tmp_path, "apply_filter", layer_name="communes", expression="a = 1")
        assert not error and answer["success"] is True and answer["active_filters"] == {}

    def test_export_keeps_the_paths_of_this_machine(self, tmp_path):
        folder = (tmp_path / "export").resolve()
        accessor = Accessor(export=OperationResult(done=["a"], outputs={"a": str(folder / "a.gpkg")}))
        assert run(accessor, tmp_path, "export_layers", layers=["a"])[1]["outputs"] == {"a": "a.gpkg"}

    @pytest.mark.parametrize("tool,key", [("apply_filter", "layer_name"), ("preview_filter", "layer_name")])
    def test_a_second_statement_never_reaches_qgis(self, api, tool, key):
        accessor, root = api
        error, message = run(accessor, root, tool, **{key: "communes"}, expression="$a$'$a$ IS NULL; DROP TABLE x; --'")
        assert error and "WHERE" in message
        assert not accessor._active and not accessor.calls

    @pytest.mark.parametrize("tool,arguments,message", [
        ("describe_layer", {"layer": "x"}, "Layer not found."),
        ("field_values", {"layer": "x", "field": "y"}, "Layer or field not found."),
        ("preview_filter", {"layer_name": "x", "expression": "a"}, "Layer not found."),
    ])
    def test_nothing_found(self, tmp_path, tool, arguments, message):
        accessor = Accessor(describe=None, values=None, preview=None)
        assert run(accessor, tmp_path, tool, **arguments) == (True, message)

    def test_unknown_layer_on_apply(self, api):
        accessor, root = api
        assert run(accessor, root, "apply_filter", layer_name="x", expression="a")[0] is True

    def test_cross_filter_defaults_and_empty_criteria(self, api):
        accessor, root = api
        error, answer = run(accessor, root, "cross_filter", source_layer="a", target_layers=["b"],
                            point_cloud_criteria={"classes": []})
        assert not error and answer["filtered"] == ["b"]
        seen = accessor.calls[-1][1]
        assert seen["predicates"] == ["Intersect"] and seen["selected_only"] is True and seen["buffer"] == 0.0
        assert seen["point_cloud_criteria"] is None

    def test_cross_filter_source_missing_or_failed(self, tmp_path):
        assert run(Accessor(cross_filter=None), tmp_path, "cross_filter", source_layer="a", target_layers=["b"]) == (
            True, "Source layer not found.")
        failed = Accessor(cross_filter=CrossFilterResult(error="no selection"))
        assert run(failed, tmp_path, "cross_filter", source_layer="a", target_layers=["b"]) == (
            True, "Cross filter failed: no selection")

    def test_point_cloud_needs_a_criterion(self, api):
        accessor, root = api
        assert run(accessor, root, "point_cloud_filter", layers=["p"], criteria={})[0] is True
        assert not accessor.calls
        assert run(accessor, root, "point_cloud_filter", layers=["p"], criteria={"z_min": 0})[1]["done"] == ["p"]

    def test_geometry_and_clear(self, api):
        accessor, root = api
        assert run(accessor, root, "geometry_filter", wkt="POINT(0 0)", crs="EPSG:2154", target_layers=["b"])[0] is False
        assert run(accessor, root, "clear_filters", layers=["a"])[1]["done"] == ["a"]

    def test_remote_layers_follow_the_open_data_choice(self, tmp_path):
        accessor = Accessor()
        tools = chat_tools()
        closed = ToolExecutor(tools, build_handlers(accessor, tmp_path))  # closed unless opened
        result = closed.execute(ToolCallPart("c", "add_layer", {"source": "https://x.org/a.geojson"}))
        assert result.is_error and "open data" in result.content
        result = closed.execute(ToolCallPart("c", "add_layer", {"source": "/data/a.gpkg", "name": "a"}))
        assert not result.is_error and json.loads(result.content)["name"] == "a"
        opened = ToolExecutor(tools, build_handlers(accessor, tmp_path, allow_remote_sources=True))
        assert not opened.execute(ToolCallPart("c", "add_layer", {"source": "https://x.org/b.geojson"})).is_error

    def test_driving_tools(self, api):
        accessor, root = api
        assert run(accessor, root, "zoom_to", layer="communes", selected_only=True)[1]["scale"] == 10000.0
        assert run(accessor, root, "zoom_to", layer="nope")[0] is True
        assert run(accessor, root, "select_features", layer="communes", expression='"a" = 1')[1]["selected_count"] == 3
        assert run(accessor, root, "set_layers_visibility", layers=["communes", "x"], visible=False)[1]["failed"] == {"x": "layer not found"}
        assert run(accessor, root, "search_open_data", query="communes")[1]["count"] == 0
        assert run(accessor, root, "remove_layers", layers=["communes"])[1]["done"] == ["communes"]
        assert accessor.layers == []

    def test_only_enabled_platforms_can_be_searched(self, api):
        accessor, root = api
        failed, message = run(accessor, root, "search_open_data", query="x", platform="opendatasoft")
        assert failed and "not enabled" in message
        assert run(accessor, root, "search_imagery")[1]["platform"] == "earth_search"
        assert run(accessor, root, "add_service_layer", platform="ign_wfs", typename="A:b")[1]["name"] == "A:b"
        assert run(accessor, root, "add_service_layer", platform="prg_pl", typename="A:b")[0] is True

    def test_export_stays_below_the_root(self, api):
        accessor, root = api
        assert run(accessor, root, "export_layers", layers=["a"], subfolder="ok/sub")[0] is False
        assert accessor.calls[-1][1]["folder"].startswith(str(root.resolve()))
        accessor.calls.clear()
        for subfolder in ("../out", "/etc", "a/../../b"):
            assert run(accessor, root, "export_layers", layers=["a"], subfolder=subfolder) == (True, "Invalid subfolder.")
        assert not accessor.calls

    def test_unusable_export_root(self, tmp_path):
        target = tmp_path / "file"
        target.write_text("x")
        assert run(Accessor(), target, "export_layers", layers=["a"]) == (True, "The export folder is not available.")

    @pytest.mark.parametrize("error,fragment", [
        (QGISBusy("task running"), "busy"), (FilterRejected("bad sql"), "bad sql"), (FavoritesUnavailable("later"), "later"),
    ])
    def test_refusals_reach_the_model(self, tmp_path, error, fragment):
        accessor = Accessor(map=error)
        failed, message = run(accessor, tmp_path, "map_context")
        assert failed and fragment in message


@pytest.fixture
def make_client():
    from fastapi.testclient import TestClient
    from filtermate_api.config import APIConfig
    from filtermate_api.server import create_app
    return lambda accessor: TestClient(create_app(APIConfig(), accessor=accessor), base_url="http://127.0.0.1")


class TestRoutes:
    def test_details(self, client):
        response = client.get("/layers/details", params={"layer": "communes"})
        assert response.status_code == 200 and response.json()["layer_kind"] == "vector"
        assert client.get("/layers/details", params={"layer": "absent"}).status_code == 404

    def test_details_by_id_is_not_shadowed(self, client):
        assert client.get("/layers/details", params={"layer": "L1"}).json()["name"] == "communes"

    def test_field_values(self, client):
        response = client.get("/layers/field-values", params={"layer": "communes", "field": "nom"})
        assert response.status_code == 200 and response.json()["field"] == "nom"
        assert client.get("/layers/field-values", params={"layer": "x", "field": "y"}).status_code == 404

    @pytest.mark.parametrize("limit", [0, 201])
    def test_field_values_limit(self, client, limit):
        params = {"layer": "communes", "field": "nom", "limit": limit}
        assert client.get("/layers/field-values", params=params).status_code == 422

    def test_preview(self, client):
        response = client.post("/filters/preview", json={"layer_name": "communes", "expression": "a = 1"})
        assert response.status_code == 200 and response.json()["valid"] is True
        assert client.post("/filters/preview", json={"layer_name": "x", "expression": "a"}).status_code == 404
        assert client.post("/filters/preview", json={"layer_name": "communes", "expression": ""}).status_code == 422

    def test_driving_routes(self, client):
        assert client.post("/map/zoom", json={"layer": "communes"}).status_code == 200
        assert client.post("/map/zoom", json={"layer": "absent"}).status_code == 400
        assert client.post("/layers/select", json={"layer": "communes", "expression": '"a"=1'}).json()["selected_count"] == 3
        assert client.post("/layers/visibility", json={"layers": ["communes"], "visible": True}).json()["done"] == ["communes"]
        added = client.post("/layers/add", json={"source": "/data/a.gpkg", "name": "a"})
        assert added.status_code == 200 and added.json()["name"] == "a"
        assert client.post("/layers/add", json={"source": "/data/a.gpkg", "kind": "cube"}).status_code == 422
        assert client.post("/open-data/search", json={"query": "communes"}).json()["count"] == 0
        assert client.post("/open-data/search", json={"query": ""}).status_code == 422
        assert client.get("/open-data/search", params={"query": "x"}).status_code == 405  # a page cannot trigger it
        assert client.post("/layers/remove", json={"layers": ["a"]}).json()["done"] == ["a"]
        assert client.post("/layers/add-service", json={"platform": "ign_wfs", "typename": "A:b"}).json()["provider_type"] == "WFS"
        assert client.post("/open-data/imagery", json={"bbox": [1, 2, 3, 4]}).status_code == 200
        assert client.post("/open-data/imagery", json={"bbox": [1, 2]}).status_code == 422

    def test_map_context(self, client):
        response = client.get("/map/context")
        assert response.status_code == 200 and response.json()["available"] is False

    def test_rejection_is_a_400(self, make_client):
        client = make_client(Accessor(preview=FilterRejected("not a vector layer")))
        response = client.post("/filters/preview", json={"layer_name": "mnt", "expression": "a"})
        assert response.status_code == 400 and "not a vector layer" in response.text


def test_details_serialize_nested_values():
    details = LayerDetails("L", "n", "raster", bands=[{"band": 1, "name": "a", "classes": [{"value": 1, "label": "x"}]}],
                           pixel_size=0.25)
    assert replace(details, name="m").bands[0]["classes"][0]["label"] == "x"


def test_catalog_agrees_with_the_mcp_server():
    """Fails when a tool changes in filtermate_api/mcp/server.py and scripts/export_agent_tools.py was not run."""
    pytest.importorskip("mcp")
    import importlib.util
    spec = importlib.util.spec_from_file_location("export_agent_tools", ROOT / "scripts" / "export_agent_tools.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def shape(schema):
        """What a change in a tool alters, without what depends on the pydantic version."""
        return {"required": sorted(schema.get("required", [])), "properties": sorted(schema.get("properties", {})),
                "descriptions": {name: item.get("description") for name, item in schema.get("properties", {}).items()}}

    fresh = {entry["name"]: entry for entry in module.catalog_entries()}
    stored = {tool.name: tool for tool in load_catalog()}
    assert set(fresh) == set(stored)
    for name, tool in stored.items():
        assert fresh[name]["description"] == tool.description, name
        assert shape(fresh[name]["input_schema"]) == shape(tool.input_schema), name
        assert (fresh[name]["read_only"], fresh[name]["destructive"], fresh[name]["idempotent"]) == (
            tool.read_only, tool.destructive, tool.idempotent), name


class TestRestFiltersArePlainClauses:
    """REST and the stdio MCP server, which relays to it, take the filters the chat takes."""

    @pytest.mark.parametrize("route", ["/filters/apply", "/filters/preview"])
    @pytest.mark.parametrize("expression", [
        "1=1; DROP TABLE communes", "\"pop\" > (SELECT max(pop) FROM x)", "$$; DROP TABLE x; $$",
        "E'\\x27; DROP TABLE x'", "pg_sleep(10) IS NULL", "\"pop\" > 1 -- comment", "$area > 1e6",
    ])
    def test_refused_before_qgis(self, route, expression, make_client):
        calls = []

        class Watching(Accessor):
            def apply_filter(self, *args, **kwargs):
                calls.append(args)
                return True

            def preview_filter(self, *args, **kwargs):
                calls.append(args)
                return None

        response = make_client(Watching()).post(route, json={"layer_name": "communes", "expression": expression})
        assert response.status_code == 400 and "plain WHERE clause" in response.json()["detail"] and not calls

    def test_a_plain_filter_passes(self, make_client):
        response = make_client(Accessor()).post("/filters/apply", json={"layer_name": "communes", "expression": '"pop" > 1000 AND "nom" LIKE \'A%\''})
        assert response.status_code != 400, response.text
