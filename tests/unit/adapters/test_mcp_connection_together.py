# -*- coding: utf-8 -*-
"""The MCP connectors of a conversation, connected all at once (``adapters/agent/mcp_connection.py``).

2026-11-14: asked one after the other, mcp.data.gouv.fr (20 s without an answer) then a local connector that was not
started made the user wait for both, and one slow answer left a connector out of the whole conversation. The module is
loaded for real under a synthetic package; ``fetch_together`` is a stand-in that records what is sent together.
"""
import importlib
import json
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_PKG = "fm_mcp_connection_together_test"


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.agent", _ROOT / "core" / "agent"),
                       (".adapters", _ROOT / "adapters"), (".adapters.agent", _ROOT / "adapters" / "agent")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    stubbed = "qgis.PyQt.QtNetwork" not in sys.modules
    if stubbed:
        sys.modules["qgis.PyQt.QtNetwork"] = MagicMock()
    try:
        return importlib.import_module(f"{_PKG}.adapters.agent.mcp_connection")
    finally:
        if stubbed:
            sys.modules.pop("qgis.PyQt.QtNetwork", None)


mcp_connection = _load()
bounded_http = sys.modules[f"{_PKG}.adapters.agent.bounded_http"]
mcp_client = sys.modules[f"{_PKG}.core.agent.mcp_client"]
sources = sys.modules[f"{_PKG}.core.agent.sources"]


def _connection(name):
    return mcp_connection.McpConnection(sources.make_source(f"https://{name}.example.org/mcp", "mcp", name))


@pytest.fixture
def server(monkeypatch):
    """``fetch_together`` answering as MCP servers do. ``server.plan[host]`` lists what a host does to its next
    requests ("late", "refused"; nothing left: it answers); ``server.rounds`` is what was sent together, each
    request as (host, method, timeout)."""
    def fetch_together(requests):
        sent, outcomes = [], []
        for request in requests:
            host = request["url"].split("/")[2].split(".")[0]
            body = json.loads(request["body"])
            sent.append((host, body["method"], request["timeout_ms"]))
            todo = fetch_together.plan.get(host) or []
            what = todo.pop(0) if todo else "ok"
            if what == "late":
                outcomes.append(bounded_http.HttpFailure(bounded_http.TOO_LONG))
            elif what == "refused":
                outcomes.append(bounded_http.HttpFailure("Connection refused"))
            elif "id" not in body:
                outcomes.append(bounded_http.BoundedReply(202, {}, b""))
            else:
                result = {"tools": [{"name": "search", "inputSchema": {"type": "object"}}]} if body["method"] == "tools/list" else {}
                answer = json.dumps({"jsonrpc": "2.0", "id": body["id"], "result": result}).encode()
                outcomes.append(bounded_http.BoundedReply(200, {"mcp-session-id": "s-" + host}, answer))
        fetch_together.rounds.append(sent)
        return outcomes
    fetch_together.plan, fetch_together.rounds = {}, []
    monkeypatch.setattr(mcp_connection, "fetch_together", fetch_together)
    return fetch_together


def test_each_step_is_sent_to_every_connector_at_once(server):
    connections = [_connection("a"), _connection("b"), _connection("c")]
    found = mcp_connection.list_tools_together(connections)
    assert [[tool.remote_name for tool in tools] for tools in found] == [["search"]] * 3
    assert [[(host, method) for host, method, _ in sent] for sent in server.rounds] == [
        [(host, method) for host in "abc"] for method in ("initialize", "notifications/initialized", "tools/list")]


def test_a_connector_that_is_down_does_not_hold_the_others(server):
    server.plan["b"] = ["refused"]
    a, b = _connection("a"), _connection("b")
    tools, error = mcp_connection.list_tools_together([a, b])
    assert tools[0].remote_name == "search" and isinstance(error, mcp_client.McpError) and "refused" in str(error)
    assert all(host == "a" for sent in server.rounds[1:] for host, _, _ in sent)  # refused: not asked again


@pytest.mark.parametrize("late_at", [0, 2], ids=["initialize", "tools/list"])
def test_a_connector_that_took_too_long_is_tried_once_more_alone(server, late_at):
    server.plan["b"] = ["ok"] * late_at + ["late"]
    a, b = _connection("a"), _connection("b")
    found = mcp_connection.list_tools_together([a, b])
    assert [tools[0].remote_name for tools in found] == ["search", "search"]
    again = server.rounds[3:]
    short, long = mcp_connection.CONNECT_TIMEOUTS_MS
    assert short < long and [sent for sent in again] == [
        [("b", method, long)] for method in ("initialize", "notifications/initialized", "tools/list")]
    assert all(timeout == short for sent in server.rounds[:3] for _, _, timeout in sent)


def test_a_connector_that_never_answers_ends_as_an_error_after_two_tries(server):
    server.plan["a"] = ["late", "late", "late"]
    outcome = mcp_connection.list_tools_together([_connection("a")])[0]
    assert isinstance(outcome, mcp_client.McpTimeout) and len(server.rounds) == 2
    with pytest.raises(mcp_client.McpError, match="too long"):
        server.plan["a"] = ["late", "late"]
        _connection("a").list_tools()


def test_the_session_of_a_first_try_is_not_sent_with_the_second(server):
    server.plan["a"] = ["ok", "ok", "late"]
    seen = []
    inner = mcp_connection.fetch_together

    def spy(requests):
        seen.extend((json.loads(request["body"])["method"], request["headers"].get("Mcp-Session-Id")) for request in requests)
        return inner(requests)
    mcp_connection.fetch_together = spy
    try:
        mcp_connection.list_tools_together([_connection("a")])
    finally:
        mcp_connection.fetch_together = inner
    assert [session for method, session in seen if method == "initialize"] == [None, None]
    assert seen[-1] == ("tools/list", "s-a")


def test_stop_ends_it_all_no_step_and_no_second_try_after_it(server):
    """A review of 14/11: a connector that had only timed out was tried again, up to 60 s, after the user's Stop."""
    server.plan["a"] = ["late"]
    inner = mcp_connection.fetch_together

    def stop_during_the_first_step(requests):
        outcomes = inner(requests)
        bounded_http.abort_active()
        return outcomes
    mcp_connection.fetch_together = stop_during_the_first_step
    try:
        found = mcp_connection.list_tools_together([_connection("a"), _connection("b")])
    finally:
        mcp_connection.fetch_together = inner
    assert len(server.rounds) == 1 and all(isinstance(item, mcp_client.McpError) for item in found)
    assert "stopped" in str(found[0]) and "stopped" in str(found[1]) and bounded_http._ACTIVE == []


def test_a_connection_already_made_only_lists_again(server):
    a = _connection("a")
    a.list_tools()
    del server.rounds[:]
    assert a.list_tools()[0].remote_name == "search"
    assert [[method for _, method, _ in sent] for sent in server.rounds] == [["tools/list"]]
