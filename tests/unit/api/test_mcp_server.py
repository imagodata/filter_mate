# -*- coding: utf-8 -*-
"""The FilterMate MCP server end to end: a real MCP client over stdio, a fake REST API on a socket.

The server runs as a subprocess (``python -m filtermate_api.mcp``) started from an unrelated folder, exactly as
an MCP client would start it.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from mcp import StdioServerParameters  # noqa: E402

from .mcp_session import McpSession, _env, is_error, text_of, wire  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_TOOLS = {
    "list_layers", "apply_filter", "filter_status", "undo_filter", "redo_filter", "cross_filter", "geometry_filter",
    "point_cloud_filter", "clear_filters", "filter_state", "list_favorites", "apply_favorite", "export_layers",
}
READ_ONLY = {"list_layers", "filter_status", "filter_state", "list_favorites"}


@pytest.fixture(scope="module")
def mcp_session(_fake_api_server, tmp_path_factory):
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "filtermate_api.mcp", "--url", _fake_api_server.url],
        env={"PYTHONPATH": str(ROOT), "FILTERMATE_API_KEY": "test-key-0123456789"},
        cwd=str(tmp_path_factory.mktemp("elsewhere")))
    with McpSession(params) as session:
        yield session


@pytest.fixture
def mcp(mcp_session, fake_api):
    return mcp_session


# --- catalogue -----------------------------------------------------------------

def test_one_tool_per_endpoint_with_annotations(mcp):
    tools = {tool["name"]: tool for tool in map(wire, mcp.run(mcp.session.list_tools()).tools)}
    assert set(tools) == EXPECTED_TOOLS
    for name, tool in tools.items():
        assert tool["description"] and len(tool["description"]) > 40, name
        annotations = tool["annotations"]
        assert annotations is not None, name
        assert annotations["openWorldHint"] is False
        if name in READ_ONLY:
            assert annotations["readOnlyHint"] is True, name
        else:
            assert annotations["readOnlyHint"] is False, name
            assert annotations["destructiveHint"] is (name == "export_layers"), name
    assert tools["undo_filter"]["annotations"]["idempotentHint"] is False
    assert tools["redo_filter"]["annotations"]["idempotentHint"] is False
    assert tools["clear_filters"]["annotations"]["idempotentHint"] is True
    assert "overwritten" in tools["export_layers"]["description"]


def test_input_schemas_follow_the_rest_models(mcp):
    tools = {tool["name"]: tool for tool in map(wire, mcp.run(mcp.session.list_tools()).tools)}
    cross = tools["cross_filter"]["inputSchema"]
    assert set(cross["required"]) == {"source_layer", "target_layers"}
    assert set(cross["properties"]) == {
        "source_layer", "target_layers", "predicates", "buffer", "coverage_min", "operator", "selected_only",
        "raster_selection", "point_cloud_criteria", "filter_source"}
    dumped = json.dumps(cross)
    for predicate in ("Intersect", "Contain", "Disjoint", "Equal", "Touch", "Overlap", "Are within", "Cross"):
        assert predicate in dumped
    for derivative in ("slope_degrees", "slope_percent", "aspect", "hillshade", "roughness"):
        assert derivative in dumped
    assert set(tools["geometry_filter"]["inputSchema"]["required"]) == {"wkt", "crs", "target_layers"}
    assert set(tools["apply_filter"]["inputSchema"]["required"]) == {"layer_name", "expression"}
    export = tools["export_layers"]["inputSchema"]["properties"]
    assert "COPC" in json.dumps(export["point_cloud_format"]) and "FlatGeobuf" in json.dumps(export["vector_format"])
    assert tools["apply_favorite"]["inputSchema"]["required"] == ["favorite_id"]


# --- tools: method, path, body, key --------------------------------------------------

def last(fake_api):
    return fake_api.requests[-1]


def test_list_layers(mcp, fake_api):
    layers = [{"layer_id": "L1", "name": "communes", "layer_kind": "vector"}]
    fake_api.respond("GET", "/layers", layers)
    result = mcp.call("list_layers")
    assert not is_error(result)
    assert json.loads(text_of(result)) == {"layers": layers}
    request = last(fake_api)
    assert (request["method"], request["path"]) == ("GET", "/layers")
    assert request["headers"]["x-api-key"] == "test-key-0123456789"


@pytest.mark.parametrize("tool,path,payload,expected", [
    ("filter_status", "/filters/status", {"status": "idle", "active_filters": {}},
     {"status": "idle", "active_filters": {}}),
    ("filter_state", "/filters/state", [{"layer_id": "L1", "name": "a", "layer_kind": "vector", "subset": "x = 1"}],
     {"layers": [{"layer_id": "L1", "name": "a", "layer_kind": "vector", "subset": "x = 1"}]}),
    ("list_favorites", "/favorites", [{"favorite_id": "f1", "name": "Fav"}],
     {"favorites": [{"favorite_id": "f1", "name": "Fav"}]}),
])
def test_other_reads(mcp, fake_api, tool, path, payload, expected):
    fake_api.respond("GET", path, payload)
    result = mcp.call(tool)
    assert not is_error(result)
    assert json.loads(text_of(result)) == expected
    assert (last(fake_api)["method"], last(fake_api)["path"]) == ("GET", path)
    assert last(fake_api)["body"] is None


def test_apply_filter(mcp, fake_api):
    fake_api.respond("POST", "/filters/apply", {"success": True, "layer_name": "communes", "active_filters": {}})
    result = mcp.call("apply_filter", {"layer_name": "communes", "expression": '"population" > 10000'})
    assert not is_error(result)
    request = last(fake_api)
    assert (request["method"], request["path"]) == ("POST", "/filters/apply")
    assert request["body"] == {"layer_name": "communes", "expression": '"population" > 10000', "source": "mcp"}
    assert request["headers"]["x-api-key"] == "test-key-0123456789"


@pytest.mark.parametrize("tool,path", [("undo_filter", "/filters/undo"), ("redo_filter", "/filters/redo")])
def test_undo_redo(mcp, fake_api, tool, path):
    fake_api.respond("POST", path, {"status": "ok", "step": {"layer_name": "a", "expression": "", "is_clear": True}})
    assert not is_error(mcp.call(tool))
    request = last(fake_api)
    assert (request["method"], request["path"]) == ("POST", path)
    assert request["body"] == {}


def test_cross_filter_vector_defaults(mcp, fake_api):
    fake_api.respond("POST", "/filters/cross", {"filtered": ["parcelle"], "failed": {}, "skipped": {}})
    result = mcp.call("cross_filter", {"source_layer": "communes", "target_layers": ["parcelle"]})
    assert not is_error(result)
    assert "parcelle" in text_of(result)
    request = last(fake_api)
    assert (request["method"], request["path"]) == ("POST", "/filters/cross")
    assert request["body"] == {
        "source_layer": "communes", "target_layers": ["parcelle"], "predicates": ["Intersect"], "buffer": 0.0,
        "coverage_min": 0.0, "selected_only": True, "filter_source": False}


def test_cross_filter_raster_and_point_cloud_sources(mcp, fake_api):
    fake_api.respond("POST", "/filters/cross", {"filtered": ["parcelle", "lhd"], "failed": {}, "skipped": {}})
    mcp.call("cross_filter", {
        "source_layer": "mnt", "target_layers": ["parcelle", "lhd"], "predicates": ["Intersect", "Touch"],
        "buffer": 10, "coverage_min": 50, "operator": "AND NOT",
        "raster_selection": {"mode": "range", "minimum": 1200, "maximum": 1300, "derivative": "slope_degrees"},
        "point_cloud_criteria": {"classes": [6], "z_min": 1000},
        "filter_source": True})
    body = last(fake_api)["body"]
    assert body["operator"] == "AND NOT" and body["buffer"] == 10 and body["coverage_min"] == 50
    assert body["predicates"] == ["Intersect", "Touch"] and body["filter_source"] is True
    assert body["raster_selection"] == {
        "band": 1, "mode": "range", "minimum": 1200.0, "maximum": 1300.0, "classes": [],
        "expression": "", "derivative": "slope_degrees"}
    assert body["point_cloud_criteria"]["classes"] == [6] and body["point_cloud_criteria"]["z_min"] == 1000.0
    assert "z_max" not in body["point_cloud_criteria"]


def test_geometry_filter(mcp, fake_api):
    fake_api.respond("POST", "/filters/geometry", {"filtered": ["mnt"], "failed": {}, "skipped": {}})
    mcp.call("geometry_filter", {
        "wkt": "POLYGON((0 0,1 0,1 1,0 0))", "crs": "EPSG:2154", "target_layers": ["mnt"], "predicates": ["Are within"],
        "buffer": 5})
    request = last(fake_api)
    assert (request["method"], request["path"]) == ("POST", "/filters/geometry")
    assert request["body"] == {
        "wkt": "POLYGON((0 0,1 0,1 1,0 0))", "crs": "EPSG:2154", "target_layers": ["mnt"],
        "predicates": ["Are within"], "buffer": 5.0, "coverage_min": 0.0}


def test_point_cloud_filter(mcp, fake_api):
    fake_api.respond("POST", "/filters/point-cloud", {"done": ["t1", "t2"], "failed": {}, "skipped": {}})
    mcp.call("point_cloud_filter", {
        "layers": ["t1", "t2"], "criteria": {"classes": [3, 4, 5], "z_min": 1200}, "operator": "AND"})
    request = last(fake_api)
    assert (request["method"], request["path"]) == ("POST", "/filters/point-cloud")
    assert request["body"] == {"layers": ["t1", "t2"], "operator": "AND",
                               "criteria": {"classes": [3, 4, 5], "z_min": 1200.0, "expression": ""}}


def test_clear_filters(mcp, fake_api):
    fake_api.respond("POST", "/filters/clear", {"done": ["a"], "failed": {}, "skipped": {}})
    mcp.call("clear_filters", {"layers": ["a", "L2"]})
    request = last(fake_api)
    assert (request["method"], request["path"], request["body"]) == ("POST", "/filters/clear", {"layers": ["a", "L2"]})


def test_apply_favorite_quotes_the_id(mcp, fake_api):
    fake_api.respond("POST", "/favorites/fav-1/apply", {"status": "ok", "step": {"layer_name": "a", "expression": "x"}})
    assert not is_error(mcp.call("apply_favorite", {"favorite_id": "fav-1"}))
    request = last(fake_api)
    assert (request["method"], request["path"]) == ("POST", "/favorites/fav-1/apply")
    mcp.call("apply_favorite", {"favorite_id": "a b?c#d"})
    assert last(fake_api)["path"] == "/favorites/a%20b%3Fc%23d/apply"


def test_export_layers(mcp, fake_api):
    fake_api.respond("POST", "/export", {"done": ["a"], "outputs": {"a": "/x/a.gpkg"}, "failed": {}, "skipped": {}})
    result = mcp.call("export_layers", {"layers": ["a"], "subfolder": "controle/2026-10", "point_cloud_format": "COPC",
                                        "crs": "EPSG:2154"})
    assert "/x/a.gpkg" in text_of(result)
    request = last(fake_api)
    assert (request["method"], request["path"]) == ("POST", "/export")
    assert request["body"] == {
        "layers": ["a"], "subfolder": "controle/2026-10", "vector_format": "GPKG", "raster_format": "COG",
        "point_cloud_format": "COPC", "crs": "EPSG:2154"}


# --- errors become readable tool errors ---------------------------------------------

def test_busy_qgis(mcp, fake_api):
    fake_api.respond("POST", "/filters/clear", {"detail": "QGIS is busy: x"}, 503, {"Retry-After": "5"})
    result = mcp.call("clear_filters", {"layers": ["a"]})
    assert is_error(result)
    assert "QGIS is busy" in text_of(result) and "Retry" in text_of(result)


def test_wrong_key(mcp, fake_api):
    fake_api.expected_key = "another-key"
    result = mcp.call("list_layers")
    assert is_error(result)
    assert "rejected the API key" in text_of(result)
    assert "test-key-0123456789" not in text_of(result)


def test_validation_error_422(mcp, fake_api):
    fake_api.respond("POST", "/filters/cross", {"detail": [
        {"type": "value_error", "loc": ["body", "raster_selection"], "msg": "Value error, a range needs a minimum"}]},
        422)
    result = mcp.call("cross_filter", {"source_layer": "mnt", "target_layers": ["a"],
                                       "raster_selection": {"mode": "range"}})
    assert is_error(result)
    assert "a range needs a minimum" in text_of(result)


def test_conflict_and_not_found(mcp, fake_api):
    fake_api.respond("POST", "/filters/undo", {"detail": "Nothing to undo"}, 409)
    assert "Nothing to undo" in text_of(mcp.call("undo_filter"))
    fake_api.respond("POST", "/filters/apply", {"detail": "Layer not found"}, 404)
    result = mcp.call("apply_filter", {"layer_name": "ghost", "expression": "1=1"})
    assert is_error(result) and "Layer not found" in text_of(result)


def test_bad_arguments_are_refused_before_any_request(mcp, fake_api):
    for name, arguments in [
        ("cross_filter", {"source_layer": "a", "target_layers": []}),
        ("cross_filter", {"source_layer": "a", "target_layers": ["b"], "predicates": ["Near"]}),
        ("cross_filter", {"source_layer": "a", "target_layers": ["b"], "operator": "XOR"}),
        ("cross_filter", {"source_layer": "a", "target_layers": ["b"], "coverage_min": 150}),
        ("export_layers", {"layers": ["a"], "vector_format": "KML"}),
        ("apply_filter", {"layer_name": "a"}),
    ]:
        result = mcp.call(name, arguments)
        assert is_error(result), (name, arguments)
    assert fake_api.requests == []


def test_api_down_tells_how_to_start_it(tmp_path):
    import socket
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "filtermate_api.mcp", "--url", "http://127.0.0.1:%d" % port],
        env={"PYTHONPATH": str(ROOT), "FILTERMATE_API_KEY": "k"}, cwd=str(tmp_path))
    with McpSession(params) as session:
        result = session.call("list_layers")
    assert is_error(result)
    assert "Start the FilterMate REST API in QGIS" in text_of(result)


# --- resources ----------------------------------------------------------------------

def test_resources(mcp, fake_api):
    fake_api.respond("GET", "/layers", [{"name": "communes"}])
    fake_api.respond("GET", "/filters/state", [])
    uris = {str(resource.uri) for resource in mcp.run(mcp.session.list_resources()).resources}
    assert uris == {"filtermate://layers", "filtermate://state"}
    contents = mcp.run(mcp.session.read_resource("filtermate://layers")).contents
    assert json.loads(contents[0].text) == [{"name": "communes"}]
    assert json.loads(mcp.run(mcp.session.read_resource("filtermate://state")).contents[0].text) == []


# --- start-up ---------------------------------------------------------------------------

def run_server(*args, env=None, cwd=None):
    return subprocess.run([sys.executable, "-m", "filtermate_api.mcp", *args], env=env or _env(), cwd=cwd,
                          capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)


def test_refuses_to_start_without_a_key(tmp_path):
    result = run_server(cwd=str(tmp_path))
    assert result.returncode == 2
    assert "FILTERMATE_API_KEY" in result.stderr and "refuses to start" in result.stderr
    assert result.stdout == ""


def test_refuses_a_remote_url(tmp_path):
    result = run_server("--url", "http://192.168.0.5:8000", env=_env(FILTERMATE_API_KEY="k"), cwd=str(tmp_path))
    assert result.returncode == 2
    assert "allow-remote" in result.stderr and result.stdout == ""


def test_other_key_variable(tmp_path, _fake_api_server):
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "filtermate_api.mcp", "--url", _fake_api_server.url,
                                      "--api-key-env", "FM_SECRET"],
        env={"PYTHONPATH": str(ROOT), "FM_SECRET": "test-key-0123456789"}, cwd=str(tmp_path))
    _fake_api_server.reset()
    _fake_api_server.respond("GET", "/layers", [])
    with McpSession(params) as session:
        assert not is_error(session.call("list_layers"))


def test_runs_as_a_script_from_any_folder(tmp_path, _fake_api_server):
    script = ROOT / "filtermate_api" / "mcp" / "__main__.py"
    result = subprocess.run([sys.executable, str(script)], env={**_env(), "PYTHONPATH": ""}, cwd=str(tmp_path),
                            capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
    assert result.returncode == 2
    assert "FILTERMATE_API_KEY" in result.stderr
    assert "Traceback" not in result.stderr


def test_script_launch_serves_tools_without_pythonpath(tmp_path, _fake_api_server):
    """``python /path/to/filtermate_api/mcp/__main__.py`` works from any folder with no PYTHONPATH."""
    script = ROOT / "filtermate_api" / "mcp" / "__main__.py"
    _fake_api_server.reset()
    _fake_api_server.respond("GET", "/layers", [])
    params = StdioServerParameters(
        command=sys.executable, args=[str(script), "--url", _fake_api_server.url],
        env={"FILTERMATE_API_KEY": "test-key-0123456789"}, cwd=str(tmp_path))
    with McpSession(params) as session:
        assert not is_error(session.call("list_layers"))
    assert _fake_api_server.requests[0]["headers"]["x-api-key"] == "test-key-0123456789"


def test_script_launch_serves_tools_from_any_folder(tmp_path, _fake_api_server):
    """``python /path/to/filtermate_api/mcp/__main__.py`` with no PYTHONPATH, from an unrelated folder."""
    _fake_api_server.reset()
    _fake_api_server.respond("GET", "/layers", [{"name": "communes"}])
    script = ROOT / "filtermate_api" / "mcp" / "__main__.py"
    params = StdioServerParameters(
        command=sys.executable, args=[str(script), "--url", _fake_api_server.url],
        env={"FILTERMATE_API_KEY": "test-key-0123456789"}, cwd=str(tmp_path))
    with McpSession(params) as session:
        result = session.call("list_layers")
    assert not is_error(result)
    assert json.loads(text_of(result)) == {"layers": [{"name": "communes"}]}
