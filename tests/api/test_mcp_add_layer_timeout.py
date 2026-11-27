# -*- coding: utf-8 -*-
"""The wait of the MCP client for a call that adds a layer outlasts the longest of the limits of the plugin.

2026-11-18: it was 330 s, and add_osm_features can last 90 s (Overpass) then 240 s (conversion), without the wait for
the main thread nor what follows: the client showed a timeout while the layers arrived, and a second call added them
again. The limits are read in the code, so that one that grows is noticed here.
"""
import ast
import pathlib
import pytest

pytest.importorskip('mcp')

from filtermate_api.mcp import server

ROOT = pathlib.Path(__file__).resolve().parents[2]
AFTER_THE_LAST_LIMIT = 60.0  # what the plugin does once its last limit is spent (the comment of ADD_LAYER_TIMEOUT)


def _constant(relative: str, name: str) -> float:
    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name
                                                for target in node.targets):
            return float(ast.literal_eval(node.value))
    raise AssertionError(f"{name} is no longer in {relative}")


def test_the_wait_outlasts_the_slowest_tool_that_adds_a_layer():
    queue = _constant("filtermate_api/main_thread.py", "_DEFAULT_TIMEOUT_SECONDS")
    conversion = _constant("adapters/public_api/terrain.py", "READ_TIMEOUT_S")
    chains = {
        "add_osm_features": _constant("adapters/public_api/osm_features.py", "REQUEST_TIMEOUT_MS") / 1000 + conversion,
        "add_elevation": _constant("adapters/public_api/terrain.py", "TILE_TIMEOUT_MS") / 1000 + conversion,
        "add_population": conversion,
        "contour_lines": conversion,
        "add_layer": 4 * 20.0 + _constant("adapters/public_api/project_control.py", "DOWNLOAD_TIMEOUT_MS") / 1000,
    }
    slowest = max(chains.values())
    assert chains["add_osm_features"] == slowest == 330.0
    assert server.ADD_LAYER_TIMEOUT >= queue + slowest + AFTER_THE_LAST_LIMIT, (server.ADD_LAYER_TIMEOUT, chains)
