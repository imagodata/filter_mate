# -*- coding: utf-8 -*-
"""FilterMate 5 REST API — second review round (audit 2026-10).

* CSRF: a page's form post / no-cors fetch reaches the routes with no
  pre-flight: refused (403) unless its origin is the API's own or listed;
  a body must be JSON (415).
* A client gone mid-body gets an answer (no 500 from the key middleware).
* ``Host``: absent accepted (HTTP/1.0), only a numeric port after the host.
* ``cors_origins`` given as a string is split, never tested by substring.
* ``filtermate_api.server`` imports whatever the config (``app`` is lazy).
* List items have a maximum length.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from filtermate_api.accessor import Favorite, InMemoryAccessor, LayerSummary  # noqa: E402
from filtermate_api.config import APIConfig, APIConfigError  # noqa: E402
from filtermate_api.server import create_app  # noqa: E402

LOOPBACK = "http://127.0.0.1:8000"
_ROOT = Path(__file__).resolve().parents[2]


def _accessor():
    accessor = InMemoryAccessor(
        layers=[LayerSummary(layer_id="L1", name="communes", provider_type="ogr")],
        favorites=[Favorite(favorite_id="fav-1", name="F", layer_name="communes", expression="x = 1")])
    accessor.apply_filter("communes", "x = 1", "test")  # something to undo
    return accessor


def _client(config=None) -> TestClient:
    return TestClient(create_app(config=config or APIConfig(), accessor=_accessor()), base_url=LOOPBACK)


_FORM = {"Origin": "https://evil.example", "Content-Type": "application/x-www-form-urlencoded"}


class TestCrossSiteWrites:
    @pytest.mark.parametrize("route", ["/filters/undo", "/filters/redo", "/favorites/fav-1/apply"])
    def test_form_post_from_another_site_is_refused(self, route):
        response = _client().post(route, content=b"", headers=_FORM)
        assert response.status_code == 403

    @pytest.mark.parametrize("route", ["/filters/undo", "/filters/redo", "/favorites/fav-1/apply"])
    def test_no_cors_fetch_without_body_is_refused(self, route):
        response = _client().post(route, headers={"Origin": "https://evil.example"})
        assert response.status_code == 403

    def test_cross_site_without_origin_header_is_refused(self):
        response = _client().post("/filters/undo", headers={"Sec-Fetch-Site": "cross-site"})
        assert response.status_code == 403

    def test_undo_actually_untouched(self):
        client = _client()
        client.post("/filters/undo", headers=_FORM)
        assert client.get("/filters/status").json()["active_filters"] == {"communes": "x = 1"}

    def test_listed_origin_is_served(self):
        client = _client(APIConfig(cors_origins=["https://app.example"]))
        response = client.post("/filters/undo", headers={"Origin": "https://app.example"})
        assert response.status_code == 200

    def test_the_api_own_page_is_served(self):
        # Swagger UI at /docs posts with the API's own origin.
        response = _client().post("/filters/undo", headers={"Origin": LOOPBACK, "Sec-Fetch-Site": "same-origin"})
        assert response.status_code == 200

    def test_scripts_without_origin_are_served(self):
        client = _client()
        assert client.post("/filters/undo").status_code == 200
        assert client.post("/filters/apply", json={"layer_name": "communes", "expression": "y = 2"}).status_code == 200

    def test_reads_are_not_concerned(self):
        assert _client().get("/layers", headers={"Origin": "https://evil.example"}).status_code == 200

    @pytest.mark.parametrize("content_type", ["text/plain", "application/x-www-form-urlencoded",
                                              "multipart/form-data; boundary=x"])
    def test_body_must_be_json(self, content_type):
        response = _client().post("/filters/apply", content=b'{"layer_name":"communes","expression":"y = 2"}',
                                  headers={"Content-Type": content_type})
        assert response.status_code == 415

    def test_body_without_content_type_is_refused(self):
        response = _client().post("/filters/apply", content=b'{"layer_name":"communes","expression":"y = 2"}')
        assert response.status_code == 415

    def test_json_variants_accepted(self):
        response = _client().post("/filters/apply", content=b'{"layer_name":"communes","expression":"y = 2"}',
                                  headers={"Content-Type": "application/json; charset=utf-8"})
        assert response.status_code == 200


class TestClientGoneMidBody:
    def test_answered_without_500(self):
        app = create_app(config=APIConfig(api_key="k"), accessor=_accessor())
        messages = iter([{"type": "http.request", "body": b'{"layer_name":', "more_body": True},
                         {"type": "http.disconnect"}])
        sent = []

        async def receive():
            return next(messages, {"type": "http.disconnect"})

        async def send(message):
            sent.append(message)

        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST",
                 "scheme": "http", "path": "/filters/apply", "raw_path": b"/filters/apply", "root_path": "",
                 "query_string": b"", "server": ("127.0.0.1", 8000), "client": ("127.0.0.1", 5000),
                 "headers": [(b"host", b"127.0.0.1:8000"), (b"x-api-key", b"k"),
                             (b"content-type", b"application/json"), (b"transfer-encoding", b"chunked")]}
        asyncio.run(app(scope, receive, send))
        assert sent[0]["type"] == "http.response.start" and sent[0]["status"] == 400


class TestHostHeader:
    @pytest.mark.parametrize("header, expected", [
        ("[::1]evil", ""), ("127.0.0.1:abc", ""), ("localhost:", ""), ("[::1]:8000x", ""),
        ("[::1]:8000", "::1"), ("LOCALHOST:65535", "localhost"),
    ])
    def test_only_a_numeric_port_follows_the_host(self, header, expected):
        from filtermate_api.server import _host_name
        assert _host_name(header) == expected

    @pytest.mark.parametrize("host", ["[::1]evil", "127.0.0.1:abc"])
    def test_malformed_loopback_lookalike_refused(self, host):
        assert _client().get("/layers", headers={"Host": host}).status_code == 400

    def test_request_without_host_is_served(self):
        app = create_app(config=APIConfig(), accessor=_accessor())
        sent = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            sent.append(message)

        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.0", "method": "GET",
                 "scheme": "http", "path": "/layers", "raw_path": b"/layers", "root_path": "", "query_string": b"",
                 "server": ("127.0.0.1", 8000), "client": ("127.0.0.1", 5000), "headers": []}
        asyncio.run(app(scope, receive, send))
        assert sent[0]["status"] == 200


class TestCorsOriginsShape:
    def test_string_is_split(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text('{"API": {"cors_origins": "http://localhost:3000, https://app.example"}}', encoding="utf-8")
        assert APIConfig.from_json(path).cors_origins == ["http://localhost:3000", "https://app.example"]

    def test_string_never_allows_a_substring(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text('{"API": {"cors_origins": "http://localhost:3000"}}', encoding="utf-8")
        client = TestClient(create_app(config=APIConfig.from_json(path), accessor=_accessor()), base_url=LOOPBACK)
        response = client.options("/layers", headers={"Origin": "http://local", "Access-Control-Request-Method": "GET"})
        assert "access-control-allow-origin" not in response.headers

    @pytest.mark.parametrize("value", ['{"a": 1}', "42", '["https://a.example", 3]'])
    def test_other_types_refused(self, tmp_path, value):
        path = tmp_path / "config.json"
        path.write_text('{"API": {"cors_origins": %s}}' % value, encoding="utf-8")
        with pytest.raises(APIConfigError, match="cors_origins"):
            APIConfig.from_json(path)


class TestLazyApp:
    def test_insecure_config_does_not_break_the_import(self):
        env = dict(os.environ, FILTERMATE_API_CORS_ORIGINS="*", FILTERMATE_API_KEY="")
        env.pop("FILTERMATE_API_ALLOW_INSECURE", None)
        code = ("import filtermate_api.server as server\n"
                "from filtermate_api.config import APIConfigError\n"
                "assert callable(server.create_app)\n"
                "try:\n    server.app\nexcept APIConfigError:\n    print('refused')\n")
        result = subprocess.run([sys.executable, "-c", code], cwd=str(_ROOT), env=env, capture_output=True, text=True,
                                timeout=120)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "refused"

    def test_app_built_once_on_demand(self):
        import filtermate_api.server as server
        assert server.app is server.app


class TestListItemCaps:
    @pytest.mark.parametrize("route, body", [
        ("/filters/cross", {"source_layer": "communes", "target_layers": ["x" * 1001]}),
        ("/filters/cross", {"source_layer": "communes", "target_layers": ["roads"], "predicates": ["I" * 33]}),
        ("/filters/point-cloud", {"layers": ["x" * 1001], "criteria": {"classes": [2]}}),
        ("/filters/clear", {"layers": ["x" * 1001]}),
        ("/export", {"layers": ["x" * 1001]}),
    ])
    def test_overlong_item_refused(self, route, body, tmp_path):
        client = _client(APIConfig(export_root=tmp_path / "exports"))
        assert client.post(route, json=body).status_code == 422
