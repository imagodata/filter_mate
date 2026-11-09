# -*- coding: utf-8 -*-
"""The official MCP Python SDK, as a real client, against the server built into the plugin.

Needs ``pip install -r requirements-mcp.txt`` and a QGIS serving it (tests/qgis_headless/serve_agent_mcp.py):

    python tests/mcp_client_check.py 17899 <token>
"""
import asyncio
import re
import sys

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

RESULTS = []


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {detail}" if not condition else ""), flush=True)


def field(item, camel):
    """mcp 2.x names fields in snake case, mcp 1.x as the protocol does."""
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", camel).lower()
    return getattr(item, snake) if hasattr(item, snake) else getattr(item, camel)


def text_of(result):
    return "".join(getattr(part, "text", "") for part in result.content)


async def run(port, token):
    url = f"http://127.0.0.1:{port}/mcp"
    async with httpx2.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=30) as http:
        async with streamable_http_client(url, http_client=http) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                init = await session.initialize()
                check("initialize: the server says who it is", field(init, "serverInfo").name == "filtermate", field(init, "serverInfo"))
                check("initialize: a version both speak", field(init, "protocolVersion") in ("2025-06-18", "2025-11-25", "2025-03-26"), field(init, "protocolVersion"))
                check("initialize: tools, nothing else", init.capabilities.tools is not None and init.capabilities.resources is None)
                tools = (await session.list_tools()).tools
                names = {tool.name for tool in tools}
                check("list: the tools of the chat", {"list_layers", "apply_filter", "preview_filter"} <= names, sorted(names))
                apply = next(tool for tool in tools if tool.name == "apply_filter")
                check("list: annotations read by the SDK", apply.annotations is not None and field(apply.annotations, "readOnlyHint") is False)
                layers = await session.call_tool("list_layers", {})
                check("call: a read", not field(layers, "isError") and "communes" in text_of(layers), text_of(layers)[:200])
                preview = await session.call_tool("preview_filter", {"layer_name": "communes", "expression": '"pop" > 5000'})
                check("call: a preview counts", not field(preview, "isError") and '"feature_count": 10' in text_of(preview), text_of(preview)[:200])
                done = await session.call_tool("apply_filter", {"layer_name": "communes", "expression": '"pop" > 5000'})
                check("call: a filter applies", not field(done, "isError"), text_of(done)[:200])
                refused = await session.call_tool("apply_filter", {"layer_name": "communes", "expression": "1=1; DROP TABLE x"})
                check("call: the SQL guard answers as a tool error", field(refused, "isError"), text_of(refused)[:200])
                declined = await session.call_tool("export_layers", {"layers": ["communes"]})
                check("call: a declined export is a tool error", field(declined, "isError") and "declined" in text_of(declined), text_of(declined)[:200])
                await session.send_ping()
                check("ping", True)
                try:
                    await session.call_tool("no_such_tool", {})
                    check("call: an unknown tool fails", False)
                except Exception as exc:  # the SDK raises on a JSON-RPC error
                    check("call: an unknown tool fails", "Unknown tool" in str(exc), str(exc)[:200])
                cleared = await session.call_tool("clear_filters", {"layers": ["communes"]})
                check("call: filters cleared", not field(cleared, "isError"), text_of(cleared)[:200])

    async with httpx2.AsyncClient(headers={"Authorization": "Bearer wrong"}, timeout=10) as http:
        try:
            async with streamable_http_client(url, http_client=http) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await asyncio.wait_for(session.initialize(), 10)
            check("a wrong token is refused", False)
        except BaseException as exc:  # an ExceptionGroup from the SDK's task group
            # The SDK reports the 401 as an error of the transport; anything but a session is a refusal.
            check("a wrong token is refused", not isinstance(exc, (KeyboardInterrupt, SystemExit)), repr(exc)[:300])


def main():
    asyncio.run(run(int(sys.argv[1]), sys.argv[2]))
    failed = RESULTS.count(False)
    print(f"{len(RESULTS) - failed}/{len(RESULTS)} passed", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
