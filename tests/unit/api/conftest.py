# -*- coding: utf-8 -*-
"""Fixtures of the MCP server tests: a fake FilterMate REST API on a real socket.

The fake is a stdlib ``http.server`` in a thread. It records every request
(method, path, headers, JSON body) and answers what the test configured, so
the tests exercise the real HTTP client and, through a stdio subprocess, the
real MCP server, without QGIS, FastAPI or any mock of urllib.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple

import pytest

API_KEY = "test-key-0123456789"


class FakeRestApi:
    """Records requests and replays configured answers."""

    def __init__(self) -> None:
        self.requests: List[Dict[str, Any]] = []
        self.responses: Dict[Tuple[str, str], Tuple[int, Any, Dict[str, str]]] = {}
        self.expected_key: Optional[str] = API_KEY
        self.delay = 0.0
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return "http://127.0.0.1:%d" % self._server.server_address[1]

    def start(self) -> "FakeRestApi":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    def reset(self) -> None:
        self.requests.clear()
        self.responses.clear()
        self.expected_key = API_KEY
        self.delay = 0.0

    def respond(self, method: str, path: str, body: Any = None, status: int = 200,
                headers: Optional[Dict[str, str]] = None) -> None:
        """Answer ``method path`` with ``status`` and JSON ``body``."""
        self.responses[(method, path)] = (status, body, headers or {})

    def _handler(self):
        api = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # silence
                pass

            def _serve(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                try:
                    body = json.loads(raw) if raw else None
                except ValueError:
                    body = raw
                api.requests.append({
                    "method": self.command, "path": self.path, "body": body,
                    "headers": {k.lower(): v for k, v in self.headers.items()},
                })
                if api.delay:
                    import time
                    time.sleep(api.delay)
                if api.expected_key is not None and self.headers.get("X-API-Key") != api.expected_key:
                    self._send(401, {"detail": "Invalid or missing API key", "header": "X-API-Key"}, {})
                    return
                status, payload, headers = api.responses.get(
                    (self.command, self.path), (404, {"detail": "Not Found"}, {}))
                self._send(status, payload, headers)

            def _send(self, status: int, payload: Any, headers: Dict[str, str]) -> None:
                data = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for key, value in headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST = _serve

        return Handler


@pytest.fixture(scope="module")
def _fake_api_server():
    api = FakeRestApi().start()
    yield api
    api.stop()


@pytest.fixture
def fake_api(_fake_api_server):
    """The fake REST API, emptied before each test."""
    _fake_api_server.reset()
    return _fake_api_server


@pytest.fixture
def api_key() -> str:
    return API_KEY
