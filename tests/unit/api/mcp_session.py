# -*- coding: utf-8 -*-
"""Helpers shared by the MCP server tests: a stdio client session kept open on its own event loop thread."""
from __future__ import annotations

import asyncio
import os
import threading
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[3]


def _env(**extra):
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    env.pop("FILTERMATE_API_KEY", None)
    env.update(extra)
    return env


class McpSession:
    """One stdio client session kept open on a private event loop thread."""

    def __init__(self, params: StdioServerParameters):
        self._params = params
        self._loop = asyncio.new_event_loop()
        self._ready = threading.Event()
        self._stop = None
        self._error = None
        self.session = None
        self.init_result = None
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        self._loop.run_until_complete(self._main())

    async def _main(self):
        self._stop = asyncio.Event()
        try:
            async with stdio_client(self._params) as (read, write):
                async with ClientSession(read, write) as session:
                    self.init_result = await session.initialize()
                    self.session = session
                    self._ready.set()
                    await self._stop.wait()
        except BaseException as exc:  # reported to the test that waits for the session
            self._error = exc
            self._ready.set()

    def __enter__(self):
        self._thread.start()
        assert self._ready.wait(60), "MCP server did not start"
        if self._error is not None:
            raise self._error
        return self

    def __exit__(self, *exc):
        self._loop.call_soon_threadsafe(self._stop.set)
        self._thread.join(30)

    def run(self, coroutine):
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop).result(60)

    def call(self, name, arguments=None):
        return self.run(self.session.call_tool(name, arguments or {}))


def wire(model) -> dict:
    """A protocol object as on the wire (camelCase keys: mcp 1.x and 2.x name their attributes differently)."""
    return model.model_dump(by_alias=True, mode="json")


def is_error(result) -> bool:
    return bool(wire(result).get("isError"))


def text_of(result) -> str:
    return "".join(block.text for block in result.content if getattr(block, "type", "") == "text")
