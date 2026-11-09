# -*- coding: utf-8 -*-
"""The MCP server of the plugin: what it reads, who it lets in, what it answers."""
import json

import pytest

from core.agent.mcp_server import (
    DEFAULT_PORT, MAX_BODY, MAX_HEAD, HttpReject, HttpResponse, McpProtocol, RequestHead, check_access, claude_code_command,
    claude_desktop_config,
    client_config, client_name, new_token, read_head, render,
)
from core.agent.messages import ToolResultPart
from core.agent.tool_catalog import ToolSpec

pytestmark = pytest.mark.unit
TOKEN = "s3cret-token"
PORT = DEFAULT_PORT
GOOD = {"host": f"127.0.0.1:{PORT}", "authorization": f"Bearer {TOKEN}", "content-type": "application/json"}


def head(method="POST", target="/mcp", **changes):
    headers = {**GOOD, **{key.replace("_", "-"): value for key, value in changes.items() if value is not None}}
    for key, value in changes.items():
        if value is None:
            headers.pop(key.replace("_", "-"))
    return RequestHead(method, target, headers, 0, 0)


class TestReading:
    def request(self, *lines, body=b""):
        return ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + body

    def test_incomplete(self):
        assert read_head(b"POST /mcp HTTP/1.1\r\nHost: x") is None

    def test_complete(self):
        parsed = read_head(self.request("POST /mcp HTTP/1.1", "HOST: a:1", "Content-Length: 2", "X-Y:  z "))
        assert (parsed.method, parsed.target, parsed.content_length) == ("POST", "/mcp", 2)
        assert parsed.headers["host"] == "a:1" and parsed.headers["x-y"] == "z"

    @pytest.mark.parametrize("data,status", [
        (b"x" * (MAX_HEAD + 1), 431),
        (b"GET / HTTP/1.1\r\nA: " + b"b" * MAX_HEAD + b"\r\n\r\n", 431),
        (b"GET /\r\n\r\n", 400),
        (b"GET / HTTP/2\r\n\r\n", 400),
        (b"GET / HTTP/1.1\r\nno colon\r\n\r\n", 400),
        (b"GET / HTTP/1.1\r\nBad Name: x\r\n\r\n", 400),
        (b"GET / HTTP/1.1\r\nA: x\nB: y\r\n\r\n", 400),
        (b"GET / HTTP/1.1\r\nHost: a\r\nhost: b\r\n\r\n", 400),
        (b"POST / HTTP/1.1\r\nContent-Length: 1\r\nContent-Length: 2\r\n\r\n", 400),
        (b"POST / HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n", 501),
        (b"POST / HTTP/1.1\r\nContent-Length: +5\r\n\r\n", 400),
        (b"POST / HTTP/1.1\r\nContent-Length: abc\r\n\r\n", 400),
        (b"POST / HTTP/1.1\r\n\r\n", 411),
        (f"POST / HTTP/1.1\r\nContent-Length: {MAX_BODY + 1}\r\n\r\n".encode(), 413),
    ])
    def test_refused(self, data, status):
        with pytest.raises(HttpReject) as caught:
            read_head(data)
        assert caught.value.status == status

    def test_a_header_name_cannot_end_with_a_line_feed(self):
        with pytest.raises(HttpReject):
            read_head(b"GET / HTTP/1.1\r\nX\n: y\r\n\r\n")

    def test_the_token_stays_out_of_a_repr(self):
        assert "s3cret" not in repr(RequestHead("POST", "/mcp", {"authorization": "Bearer s3cret"}, 0, 0))

    def test_render(self):
        text = render(HttpResponse(200, b"{}", (("Mcp-Session-Id", "a"),)))
        assert text.startswith(b"HTTP/1.1 200 OK\r\n") and text.endswith(b"\r\n\r\n{}")
        assert b"Content-Length: 2\r\n" in text and b"Connection: close\r\n" in text and b"Mcp-Session-Id: a\r\n" in text


class TestAccess:
    def status(self, request):
        answer = check_access(request, PORT, TOKEN)
        return answer.status if answer else None

    def test_good(self):
        assert self.status(head()) is None
        assert self.status(head(host=f"localhost:{PORT}", authorization=f"bearer {TOKEN}")) is None
        assert self.status(head(content_type="application/json; charset=utf-8")) is None
        assert self.status(head(origin="http://localhost:6274")) is None

    @pytest.mark.parametrize("host", ["evil.example.org", f"evil.example.org:{PORT}", "127.0.0.1", "127.0.0.1:1", None])
    def test_a_foreign_host_is_refused(self, host):
        assert self.status(head(host=host)) == 403

    @pytest.mark.parametrize("origin", ["https://evil.example.org", "null", "http://127.0.0.1.evil.org", "http://[bad"])
    def test_a_foreign_page_is_refused(self, origin):
        assert self.status(head(origin=origin)) == 403

    def test_elsewhere_is_not_found(self):
        assert self.status(head(target="/other")) == 404

    @pytest.mark.parametrize("value", [None, "", "Bearer", "Bearer wrong", "Basic " + TOKEN, "Bearer é", f"Bearer {TOKEN}x"])
    def test_without_the_token(self, value):
        answer = check_access(head(authorization=value), PORT, TOKEN)
        assert answer.status == 401 and ("WWW-Authenticate", "Bearer") in answer.headers

    @pytest.mark.parametrize("target", ["//[bad", "http://[x/mcp"])
    def test_a_malformed_target_does_not_raise(self, target):
        assert self.status(head(target=target)) == 404

    def test_the_token_comes_before_the_path(self):
        assert self.status(head(target="/other", authorization=None)) == 401

    def test_a_form_cannot_post(self):
        assert self.status(head(content_type="text/plain")) == 415
        assert self.status(head(content_type=None)) == 415

    def test_claude_desktop_goes_through_mcp_remote(self):
        server = json.loads(claude_desktop_config(1234, "t"))["mcpServers"]["filtermate"]
        assert server["command"] == "npx" and server["args"][:2] == ["mcp-remote", "http://127.0.0.1:1234/mcp"]
        assert not any(" " in arg for arg in server["args"])  # Windows does not quote them
        assert server["env"] == {"AUTH_HEADER": "Bearer t"} and "Authorization:${AUTH_HEADER}" in server["args"]

    def test_a_token_is_long_and_never_the_same(self):
        assert len(new_token()) >= 40 and new_token() != new_token()

    def test_what_is_copied(self):
        server = json.loads(client_config(1234, "t"))["mcpServers"]["filtermate"]
        assert server == {"type": "http", "url": "http://127.0.0.1:1234/mcp", "headers": {"Authorization": "Bearer t"}}
        assert claude_code_command(1234, "t") == ('claude mcp add --transport http filtermate http://127.0.0.1:1234/mcp '
                                                  '--header "Authorization: Bearer t"')


class TestClientName:
    @pytest.mark.parametrize("info,expected", [
        ({"name": "Claude Code"}, "Claude Code"),
        ({"name": "a\n\nFilterMate: approved"}, "a FilterMate: approved"),
        ({"name": "x‮evil"}, "x evil"),
        ({"name": "y" * 500}, "y" * 40),
        ({"name": 5}, "MCP client"),
        ({"name": "\n"}, "MCP client"),
        ("text", "MCP client"),
        (None, "MCP client"),
    ])
    def test_names(self, info, expected):
        assert client_name(info) == expected


class TestProtocol:
    tool = ToolSpec("apply_filter", "Filter", {"type": "object", "properties": {}}, "Apply", read_only=False, destructive=False)

    def setup_method(self):
        self.calls = []

        def run(tool, arguments, client):
            self.calls.append((tool.name, arguments, client))
            return ToolResultPart("x", "done é", is_error=arguments.get("fail", False))
        self.protocol = McpProtocol(lambda: (self.tool,), run, "Hello", "9")

    def post(self, message, **headers):
        body = message if isinstance(message, bytes) else json.dumps(message).encode()
        return self.protocol.handle(RequestHead("POST", "/mcp", {key.replace("_", "-"): value for key, value in headers.items()}, 0, len(body)), body)

    def rpc(self, method, params=None, request_id=1, **headers):
        message = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            message["params"] = params
        return self.post(message, **headers)

    def session(self, name="Claude"):
        answer = self.rpc("initialize", {"protocolVersion": "2025-06-18", "clientInfo": {"name": name}})
        return dict(answer.headers)["Mcp-Session-Id"]

    def test_initialize(self):
        answer = self.rpc("initialize", {"protocolVersion": "2025-03-26"})
        result = json.loads(answer.body)["result"]
        assert result["protocolVersion"] == "2025-03-26" and result["capabilities"] == {"tools": {"listChanged": False}}
        assert result["serverInfo"]["name"] == "filtermate" and result["instructions"] == "Hello"

    def test_an_unknown_version_gets_ours(self):
        result = json.loads(self.rpc("initialize", {"protocolVersion": "1999-01-01"}).body)["result"]
        assert result["protocolVersion"] == "2025-06-18"

    def test_a_listing_has_the_annotations(self):
        tool = json.loads(self.rpc("tools/list").body)["result"]["tools"][0]
        assert tool["name"] == "apply_filter" and tool["inputSchema"]["type"] == "object"
        assert tool["annotations"]["readOnlyHint"] is False and tool["annotations"]["openWorldHint"] is False

    def test_a_call_says_who(self):
        session = self.session()
        answer = json.loads(self.rpc("tools/call", {"name": "apply_filter", "arguments": {"a": 1}}, mcp_session_id=session).body)
        assert answer["result"] == {"content": [{"type": "text", "text": "done é"}], "isError": False}
        assert self.calls == [("apply_filter", {"a": 1}, "Claude")]

    def test_a_call_without_a_session_is_anonymous(self):
        self.rpc("tools/call", {"name": "apply_filter"})
        assert self.calls == [("apply_filter", {}, "MCP client")]

    def test_a_failure_is_a_result(self):
        answer = json.loads(self.rpc("tools/call", {"name": "apply_filter", "arguments": {"fail": True}}).body)
        assert answer["result"]["isError"] is True

    def test_an_unknown_session_starts_again(self):
        assert self.rpc("tools/list", mcp_session_id="nope").status == 404

    def test_sessions_are_bounded(self):
        first = self.session()
        for _ in range(40):
            self.session()
        assert self.rpc("ping", mcp_session_id=first).status == 404

    def test_a_session_ends(self):
        session = self.session()
        ending = RequestHead("DELETE", "/mcp", {"mcp-session-id": session}, 0, 0)
        assert self.protocol.handle(ending, b"").status == 204 and self.protocol.handle(ending, b"").status == 404

    def test_no_stream(self):
        assert self.protocol.handle(RequestHead("GET", "/mcp", {}, 0, 0), b"").status == 405

    def test_ping_and_unknown_method(self):
        assert json.loads(self.rpc("ping").body)["result"] == {}
        assert json.loads(self.rpc("resources/list").body)["error"]["code"] == -32601

    @pytest.mark.parametrize("params", [{"name": "nope"}, {"name": 5}, {}, {"name": "apply_filter", "arguments": [1]}, {"name": "apply_filter", "arguments": 3}])
    def test_bad_calls_run_nothing(self, params):
        assert json.loads(self.rpc("tools/call", params).body)["error"]["code"] == -32602 and not self.calls

    def test_params_must_be_an_object(self):
        assert json.loads(self.post({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": [1]}).body)["error"]["code"] == -32602

    def test_notifications_and_replies(self):
        assert self.post({"jsonrpc": "2.0", "method": "notifications/initialized"}).status == 202
        assert self.post({"jsonrpc": "2.0", "id": 4, "result": {}}).status == 202

    @pytest.mark.parametrize("body", [b"{", b"\xff\xfe", b"[" * 200000])
    def test_not_json(self, body):
        assert self.post(body).status == 400

    @pytest.mark.parametrize("message", [[{"jsonrpc": "2.0", "id": 1, "method": "ping"}], {"id": 1, "method": "ping"}, 5, "x",
                                         {"jsonrpc": "2.0", "id": True, "method": "ping"}, {"jsonrpc": "2.0", "id": None, "method": "ping"},
                                         {"jsonrpc": "2.0", "id": [1], "method": "ping"}])
    def test_malformed(self, message):
        assert self.post(message).status == 400

    def test_a_lone_surrogate_in_a_result_is_sent(self):
        self.protocol = McpProtocol(lambda: (self.tool,), lambda *a: ToolResultPart("x", "a\ud800b"), "", "9")
        assert json.loads(self.rpc("tools/call", {"name": "apply_filter"}).body)["result"]["content"][0]["text"] == "a\ud800b"

    def test_a_newer_client_can_still_negotiate(self):
        answer = self.rpc("initialize", {"protocolVersion": "2030-01-01"}, mcp_protocol_version="2030-01-01")
        assert answer.status == 200 and json.loads(answer.body)["result"]["protocolVersion"] == "2025-06-18"

    def test_an_empty_message_is_malformed(self):
        assert self.post({"jsonrpc": "2.0"}).status == 400

    def test_only_a_tool_call_waits_for_tools(self):
        def quick(method):
            return McpProtocol.runs_no_tool(RequestHead("POST", "/mcp", {}, 0, 0), json.dumps({"method": method}).encode())
        assert quick("ping") and quick("tools/list") and quick("initialize") and not quick("tools/call")
        assert McpProtocol.runs_no_tool(RequestHead("GET", "/mcp", {}, 0, 0), b"")

    def test_a_string_id_comes_back(self):
        assert json.loads(self.rpc("ping", request_id="abc").body)["id"] == "abc"

    def test_a_protocol_version_it_does_not_speak(self):
        assert self.rpc("ping", mcp_protocol_version="1999-01-01").status == 400
        assert self.rpc("ping", mcp_protocol_version="2025-06-18").status == 200
