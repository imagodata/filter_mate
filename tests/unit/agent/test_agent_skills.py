# -*- coding: utf-8 -*-
"""Skills of the agent (core/agent/skills.py), the timings of diagnose_performance (core/agent/performance.py) and
the prompts and resources of the native MCP server."""
import json

import pytest
import re
import subprocess
import sys
from pathlib import Path

from core.agent.mcp_server import McpPrompt, McpProtocol, McpResource, RequestHead
from core.agent.performance import summary
from core.agent.settings_reference import read_settings
from core.agent.skills import SKILLS, agent_skill_file, load, skill_list
from core.agent.tool_catalog import LOAD_SKILL, SKILL_TOOLS, chat_tools, skill_tool

ROOT = Path(__file__).resolve().parents[3]


def test_every_setting_a_skill_names_exists():
    """A path written in a skill must lead somewhere: a renamed setting breaks this test, not the user."""
    paths = {row.path for row in read_settings(None)}
    sections = {path.rsplit(".", 1)[0] for path in paths} | {path.rsplit(".", 2)[0] for path in paths}
    for skill in SKILLS.values():
        for named in re.findall(r"APP(?:\.[A-Za-z_]+)+", skill.body):
            assert named in paths or named in sections, (skill.name, named)


def test_load_skill_lists_every_skill_and_loads_its_body():
    tool = next(tool for tool in SKILL_TOOLS if tool.name == LOAD_SKILL)
    plain = [name for name, skill in SKILLS.items() if "chat" in skill.audience and not skill.requires]
    assert tool.read_only and tool.input_schema["properties"]["name"]["enum"] == plain
    assert "configuration:" in skill_list() and skill_list() in tool.description
    # a skill that requires a tool is offered only with it: pyqgis with the expert mode
    assert "pyqgis" not in plain
    expert = skill_tool({"run_pyqgis"})
    assert "pyqgis" in expert.input_schema["properties"]["name"]["enum"] and "pyqgis:" in expert.description
    with pytest.raises(KeyError):
        load("pyqgis", offered={"list_layers"})
    assert load("pyqgis", offered={"run_pyqgis"})["skill"] == "pyqgis"
    loaded = load("configuration")
    assert loaded["instructions"].startswith("# Configure FilterMate")
    assert LOAD_SKILL in {tool.name for tool in chat_tools()}


def test_the_skill_never_tells_the_model_to_change_the_settings_of_the_agent():
    body = SKILLS["configuration"].body
    assert "never change" in body.lower() and "APP.OPTIONS.AGENT" in body and "run_pyqgis" in body


def test_agent_skill_files_are_up_to_date_and_have_a_front_matter():
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "export_agent_skills.py"), "--check"],
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stdout
    text = agent_skill_file(SKILLS["configuration"])
    head = text.split("---", 2)[1]
    assert "name: filtermate-configuration" in head and "description:" in head and len(head) < 1024


LOG = """\
2026-11-11 10:42:03 - FilterMate.Perf - INFO - ⏱ layer_change: 122 ms (batiment (GPKG))
2026-11-11 10:42:03 - FilterMate.Perf - INFO - ⏱ project_open: 566 ms (11 layers registered)
2026-11-11 10:43:00 - FilterMate.Perf - INFO - ⏱ cascade_filter: 41250 ms (3 layer(s) in the worker, slowest communes)
2026-11-11 10:43:01 - FilterMate.Perf - INFO - ⏱ layer_filter: 30100 ms (communes)
2026-11-11 10:43:02 - FilterMate.Perf - INFO - ⏱ layer_change: 80 ms (batiment (GPKG))
2026-11-11 10:50:06 - filter_mate.adapters.qgis.coverage_layers.cross_filter_task - INFO - ⏱ [FM5] source geometry (raster) in 0.01s {'kept_pixels': 5443}
2026-11-11 10:50:06 - filter_mate.x - WARNING - PostgreSQL query timed out after 60 s
2026-11-11 10:50:07 - filter_mate.x - ERROR - Filter failed
a line cut in two
"""


def test_performance_summary_reads_the_timings_timeouts_and_errors():
    answer = summary(LOG.splitlines())
    assert answer["timings"] == 6 and answer["timeouts_logged"] == 1 and answer["errors_logged"] == 1
    operations = {row["operation"]: row for row in answer["operations"]}
    assert operations["layer_change"]["count"] == 2 and operations["layer_change"]["max_ms"] == 122
    assert operations["layer_change"]["last_ms"] == 80
    assert operations["source geometry (raster)"]["max_ms"] == 10
    assert answer["operations"][0]["operation"] == "cascade_filter"
    assert answer["slowest"][0]["ms"] == 41250 and "communes" in answer["slowest"][0]["detail"]
    assert (answer["log_from"], answer["log_to"]) == ("2026-11-11 10:42:03", "2026-11-11 10:50:07")


def test_performance_reads_other_timing_shapes_and_hides_connection_details():
    lines = [
        "2026-11-11 11:00:00 - FilterMate.Perf - INFO - ⏱ pg_direct_prepare: connection 12 ms, query 30 ms",
        "2026-11-11 11:00:01 - filter_mate.x - INFO - ⏱ [FM5] height above ground for 'x': ok=True 1.2s",
        "2026-11-11 11:00:02 - FilterMate.Perf - INFO - ⏱ pg_layer_connect: 40 ms (host=db.internal.example "
        "port=5432 dbname='cadastre' user=jeanne)",
        "2026-11-11 11:00:03 - filter_mate.x - WARNING - QUERY_TIMEOUTS timeout_seconds is 30 (configured)",
    ]
    answer = summary(lines)
    operations = {row["operation"]: row for row in answer["operations"]}
    assert operations["pg_direct_prepare"]["max_ms"] == 12
    assert operations["height above ground for 'x'"]["max_ms"] == 1200
    text = json.dumps(answer)
    assert "db.internal" not in text and "jeanne" not in text and "cadastre" not in text
    assert answer["timeouts_logged"] == 0  # a setting that names a timeout is not a query cut short
    assert any(entry["detail"] == "batiment (GPKG)" for entry in summary(LOG.splitlines()[:1])["slowest"])


def test_performance_summary_without_timings_says_what_to_do():
    answer = summary([])
    assert answer["timings"] == 0 and "hint" in answer


def _post(protocol, payload, session=None):
    headers = {"content-type": "application/json"}
    if session:
        headers["mcp-session-id"] = session
    head = RequestHead("POST", "/mcp", headers, 0, 0)
    response = protocol.handle(head, json.dumps(payload).encode("utf-8"))
    return response, json.loads(response.body.decode("utf-8")) if response.body else None


def test_native_mcp_serves_prompts_and_resources():
    prompt = McpPrompt("filtermate_configuration", "Configure FilterMate", "set it up", "# Configure FilterMate")
    resource = McpResource("filtermate://settings/reference", "settings", "Settings", "every setting",
                           "text/markdown", lambda: "# FilterMate — settings reference")
    protocol = McpProtocol(lambda: (), lambda tool, arguments, client: None, prompts=(prompt,), resources=(resource,))
    response, body = _post(protocol, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                      "params": {"protocolVersion": "2025-06-18"}})
    session = dict(response.headers)["Mcp-Session-Id"]
    assert set(body["result"]["capabilities"]) == {"tools", "prompts", "resources"}
    _, body = _post(protocol, {"jsonrpc": "2.0", "id": 2, "method": "prompts/list"}, session)
    assert body["result"]["prompts"][0]["name"] == "filtermate_configuration"
    _, body = _post(protocol, {"jsonrpc": "2.0", "id": 3, "method": "prompts/get",
                               "params": {"name": "filtermate_configuration"}}, session)
    assert body["result"]["messages"][0]["content"]["text"] == "# Configure FilterMate"
    _, body = _post(protocol, {"jsonrpc": "2.0", "id": 4, "method": "prompts/get", "params": {"name": "x"}}, session)
    assert "error" in body
    _, body = _post(protocol, {"jsonrpc": "2.0", "id": 5, "method": "resources/list"}, session)
    assert body["result"]["resources"][0]["mimeType"] == "text/markdown"
    _, body = _post(protocol, {"jsonrpc": "2.0", "id": 6, "method": "resources/read",
                               "params": {"uri": "filtermate://settings/reference"}}, session)
    assert body["result"]["contents"][0]["text"].startswith("# FilterMate")
    _, body = _post(protocol, {"jsonrpc": "2.0", "id": 7, "method": "resources/read", "params": {"uri": "x"}}, session)
    assert body["error"]["code"] == -32002
    _, body = _post(protocol, {"jsonrpc": "2.0", "id": 8, "method": "resources/read", "params": {"uri": ["x"]}}, session)
    assert body["error"]["code"] == -32002
    _, body = _post(protocol, {"jsonrpc": "2.0", "id": 9, "method": "prompts/get", "params": {"name": {}}}, session)
    assert "error" in body


def test_a_server_without_prompts_keeps_its_capabilities_and_says_method_not_found():
    protocol = McpProtocol(lambda: (), lambda tool, arguments, client: None)
    response, body = _post(protocol, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert body["result"]["capabilities"] == {"tools": {"listChanged": False}}
    session = dict(response.headers)["Mcp-Session-Id"]
    _, body = _post(protocol, {"jsonrpc": "2.0", "id": 2, "method": "prompts/list"}, session)
    assert body["error"]["code"] == -32601
