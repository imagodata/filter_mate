# -*- coding: utf-8 -*-
"""Contract test: the MCP server against the real FastAPI app (in-memory accessor), over real sockets.

Catches a drift between the MCP tools and the REST routers (renamed field, new validation, auth or host
middleware). Needs ``fastapi``, ``uvicorn`` and the ``mcp`` SDK; QGIS is not involved.
"""
from __future__ import annotations

import asyncio
import json
import sys
import threading
import time

import pytest

pytest.importorskip("mcp")
uvicorn = pytest.importorskip("uvicorn")

from mcp import StdioServerParameters  # noqa: E402

from filtermate_api.accessor import Favorite, InMemoryAccessor, LayerSummary  # noqa: E402
from filtermate_api.config import APIConfig  # noqa: E402
from filtermate_api.server import create_app  # noqa: E402

from ..unit.api.mcp_session import ROOT, McpSession, is_error, text_of  # noqa: E402

KEY = "contract-test-key-123"
SQUARE = "POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))"


@pytest.fixture(scope="module")
def api_url(tmp_path_factory):
    layers = [
        LayerSummary(layer_id="V1", name="batiment", provider_type="ogr"),
        LayerSummary(layer_id="R1", name="mnt", provider_type="gdal", layer_kind="raster"),
        LayerSummary(layer_id="P1", name="lhd", provider_type="copc", layer_kind="point_cloud"),
    ]
    favorites = [Favorite(favorite_id="fav-1", name="Fav", layer_name="batiment", expression='"a" = 1')]
    config = APIConfig(api_key=KEY, export_root=tmp_path_factory.mktemp("exports"))
    app = create_app(config=config, accessor=InMemoryAccessor(layers=layers, favorites=favorites))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning"))
    thread = threading.Thread(target=lambda: asyncio.run(server.serve()), daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not (server.started and server.servers) and time.time() < deadline:
        time.sleep(0.05)
    assert server.started, "uvicorn did not start"
    port = server.servers[0].sockets[0].getsockname()[1]
    yield "http://127.0.0.1:%d" % port
    server.should_exit = True
    thread.join(10)


def session_for(api_url, tmp_path, key=KEY):
    return McpSession(StdioServerParameters(
        command=sys.executable, args=["-m", "filtermate_api.mcp", "--url", api_url],
        env={"PYTHONPATH": str(ROOT), "FILTERMATE_API_KEY": key}, cwd=str(tmp_path)))


@pytest.fixture(scope="module")
def mcp(api_url, tmp_path_factory):
    with session_for(api_url, tmp_path_factory.mktemp("cwd")) as session:
        yield session


def test_reads(mcp):
    layers = json.loads(text_of(mcp.call("list_layers")))["layers"]
    assert {row["name"]: row["layer_kind"] for row in layers} == {
        "batiment": "vector", "mnt": "raster", "lhd": "point_cloud"}
    assert not is_error(mcp.call("filter_status"))
    assert not is_error(mcp.call("filter_state"))
    assert "fav-1" in text_of(mcp.call("list_favorites"))


def test_filters_and_clear(mcp):
    assert not is_error(mcp.call("apply_filter", {"layer_name": "batiment", "expression": '"a" = 1'}))
    result = mcp.call("geometry_filter", {"wkt": SQUARE, "crs": "EPSG:2154", "target_layers": ["mnt", "batiment"]})
    assert not is_error(result) and json.loads(text_of(result))["filtered"] == ["mnt", "batiment"]
    result = mcp.call("cross_filter", {"source_layer": "batiment", "target_layers": ["mnt", "lhd"],
                                       "predicates": ["Disjoint"], "buffer": 2})
    assert not is_error(result), text_of(result)
    result = mcp.call("point_cloud_filter", {"layers": ["lhd"], "criteria": {"classes": [6], "z_min": 1000}})
    assert json.loads(text_of(result))["done"] == ["lhd"]
    result = mcp.call("clear_filters", {"layers": ["lhd", "mnt"]})
    assert not is_error(result), text_of(result)
    assert not is_error(mcp.call("apply_favorite", {"favorite_id": "fav-1"}))


def test_export_writes_below_the_export_root(mcp):
    result = mcp.call("export_layers", {"layers": ["mnt"], "subfolder": "controle/2026-10"})
    assert not is_error(result), text_of(result)
    assert json.loads(text_of(result))["outputs"]["mnt"].endswith("controle/2026-10/mnt.tif")
    escaping = mcp.call("export_layers", {"layers": ["mnt"], "subfolder": "../etc"})
    assert is_error(escaping) and "422" in text_of(escaping)


def test_errors_of_the_real_api(mcp):
    nothing = mcp.call("redo_filter")
    assert is_error(nothing) and "Nothing to redo" in text_of(nothing)
    ghost = mcp.call("apply_filter", {"layer_name": "ghost", "expression": "1 = 1"})
    assert is_error(ghost) and "Layer not found" in text_of(ghost)
    missing_bound = mcp.call("cross_filter", {"source_layer": "mnt", "target_layers": ["batiment"],
                                              "raster_selection": {"mode": "range"}})
    assert is_error(missing_bound) and "a range needs a minimum, a maximum or both" in text_of(missing_bound)
    assert is_error(mcp.call("apply_favorite", {"favorite_id": "ghost"}))


def test_wrong_key_is_reported(api_url, tmp_path):
    with session_for(api_url, tmp_path, key="not-the-key") as session:
        result = session.call("list_layers")
    assert is_error(result) and "rejected the API key" in text_of(result)
    assert "not-the-key" not in text_of(result)
