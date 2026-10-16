# -*- coding: utf-8 -*-
"""Audit 2026-10 (FilterMate 5) — the REST API must not be drivable from a web page.

1. **No CORS by default** — a fresh config allows no origin; ``*`` needs a key.
2. **DNS rebinding** — on a loopback bind, only loopback ``Host`` headers are served.
3. **Middleware order** — CORS answers pre-flights before the API key check,
   and 401 responses carry the CORS headers of an allowed origin.
4. **Body cap counts bytes** — a chunked body without ``Content-Length`` is capped too.
5. **Field caps** — expressions and lists have a maximum length; NaN / Infinity refused.
6. **Export sub-folder** — no trailing newline (``fullmatch``).
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from filtermate_api.accessor import InMemoryAccessor, LayerSummary  # noqa: E402
from filtermate_api.config import APIConfig  # noqa: E402
from filtermate_api.routers.export import resolve_export_folder  # noqa: E402
from filtermate_api.server import create_app  # noqa: E402

LOOPBACK = "http://127.0.0.1:8000"
_LAYERS = [LayerSummary(layer_id="L1", name="communes", provider_type="postgres", feature_count=1,
                        geometry_type="Polygon", crs_authid="EPSG:2154")]


def _client(config=None, base_url=LOOPBACK, **kwargs) -> TestClient:
    app = create_app(config=config or APIConfig(), accessor=InMemoryAccessor(layers=list(_LAYERS)), **kwargs)
    return TestClient(app, base_url=base_url)


def _preflight(client, origin="https://evil.example", path="/filters/apply", headers="content-type"):
    return client.options(path, headers={"Origin": origin, "Access-Control-Request-Method": "POST",
                                         "Access-Control-Request-Headers": headers})


class TestNoCorsByDefault:
    def test_default_config_allows_no_origin(self):
        assert APIConfig().cors_origins == []

    def test_from_env_and_from_json_default_to_no_origin(self, tmp_path, monkeypatch):
        monkeypatch.delenv("FILTERMATE_API_CORS_ORIGINS", raising=False)
        assert APIConfig.from_env().cors_origins == []
        path = tmp_path / "config.json"
        path.write_text('{"API": {"host": "127.0.0.1"}}', encoding="utf-8")
        assert APIConfig.from_json(path).cors_origins == []

    def test_hostile_page_preflight_is_not_allowed(self):
        response = _preflight(_client())
        assert "access-control-allow-origin" not in response.headers

    def test_hostile_page_cannot_read_layers(self):
        response = _client().get("/layers", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in response.headers

    def test_listed_origin_is_allowed(self):
        client = _client(APIConfig(cors_origins=["https://app.example"]))
        response = _preflight(client, origin="https://app.example")
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "https://app.example"


class TestLoopbackHostCheck:
    @pytest.mark.parametrize("host", ["attacker.rebind.example", "attacker.rebind.example:8000",
                                      "127.0.0.1.nip.io", "192.168.1.10:8000", ""])
    def test_foreign_host_is_refused(self, host):
        response = _client().get("/layers", headers={"Host": host})
        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid host header"}

    @pytest.mark.parametrize("host", ["127.0.0.1", "127.0.0.1:8000", "localhost", "LOCALHOST:8000",
                                      "[::1]:8000", "[::1]"])
    def test_loopback_hosts_are_served(self, host):
        response = _client().get("/layers", headers={"Host": host})
        assert response.status_code == 200

    def test_foreign_host_preflight_is_refused_too(self):
        client = _client(APIConfig(cors_origins=["https://app.example"]), base_url="http://attacker.rebind.example")
        assert _preflight(client, origin="https://app.example").status_code == 400

    def test_non_loopback_bind_does_not_check_the_host(self):
        # Behind a LAN name the operator chose: the API key is the protection.
        client = _client(APIConfig(host="0.0.0.0", api_key="secret-123"), base_url="http://qgis-box.lan")
        assert client.get("/layers", headers={"X-API-Key": "secret-123"}).status_code == 200

    @pytest.mark.parametrize("header, expected", [
        ("localhost:8000", "localhost"), ("[::1]:8000", "::1"), ("::1", "::1"), ("127.0.0.1", "127.0.0.1"),
        ("[::1", ""), ("", ""),
    ])
    def test_host_name_parsing(self, header, expected):
        from filtermate_api.server import _host_name
        assert _host_name(header) == expected


class TestMiddlewareOrder:
    def _keyed(self) -> TestClient:
        return _client(APIConfig(api_key="secret-key-123", cors_origins=["https://app.example"]))

    def test_cors_is_outermost_after_the_host_check(self):
        app = create_app(config=APIConfig(api_key="k", cors_origins=["https://app.example"]),
                         accessor=InMemoryAccessor())
        names = [middleware.cls.__name__ for middleware in app.user_middleware]
        assert names == ["LoopbackHostMiddleware", "CORSMiddleware", "CrossSiteWriteGuard", "APIKeyMiddleware",
                         "BodySizeLimitMiddleware"]

    def test_preflight_without_key_is_answered_by_cors(self):
        response = _preflight(self._keyed(), origin="https://app.example", path="/layers", headers="x-api-key")
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "https://app.example"

    def test_401_carries_cors_headers_for_an_allowed_origin(self):
        response = self._keyed().get("/layers", headers={"Origin": "https://app.example"})
        assert response.status_code == 401
        assert response.headers["access-control-allow-origin"] == "https://app.example"

    def test_key_still_required_for_business_routes(self):
        client = self._keyed()
        assert client.get("/layers").status_code == 401
        assert client.get("/layers", headers={"X-API-Key": "secret-key-123"}).status_code == 200


class TestChunkedBodyCap:
    @staticmethod
    def _chunks(size):
        def generate():
            yield b'{"layer_name":"communes","expression":"'
            remaining = size
            while remaining > 0:
                step = min(remaining, 256 * 1024)
                yield b"a" * step
                remaining -= step
            yield b'"}'
        return generate()

    def test_chunked_body_over_the_cap_is_refused(self):
        response = _client().post("/filters/apply", content=self._chunks(3 * 1024 * 1024),
                                  headers={"content-type": "application/json"})
        assert response.status_code == 413
        assert response.json()["detail"] == "Request body too large"

    def test_small_chunked_body_is_served(self):
        response = _client().post("/filters/apply", content=self._chunks(10),
                                  headers={"content-type": "application/json"})
        assert response.status_code == 200
        assert response.json()["expression"] == "a" * 10

    def test_lying_content_length_cannot_skip_the_cap(self, monkeypatch):
        # The bytes received are counted, whatever Content-Length claims.
        monkeypatch.setenv("FILTERMATE_API_MAX_BODY_BYTES", "1024")
        response = _client().post("/filters/apply", content=self._chunks(4096),
                                  headers={"content-type": "application/json"})
        assert response.status_code == 413


class TestFieldCaps:
    def test_expression_over_the_cap_is_refused(self):
        response = _client().post("/filters/apply", json={"layer_name": "communes", "expression": "a" * 500_001})
        assert response.status_code == 422
        # The 422 says where and why, without echoing the 500 kB value back.
        assert "a" * 100 not in response.text
        assert response.json()["detail"][0]["loc"] == ["body", "expression"]

    def test_too_many_target_layers_are_refused(self):
        response = _client().post("/filters/cross", json={"source_layer": "communes",
                                                          "target_layers": ["x"] * 1001})
        assert response.status_code == 422

    @pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "1e8"])
    def test_buffer_must_be_finite_and_bounded(self, value):
        body = '{"wkt":"POINT(0 0)","crs":"EPSG:2154","target_layers":["communes"],"buffer":%s}' % value
        response = _client().post("/filters/geometry", content=body, headers={"content-type": "application/json"})
        assert response.status_code == 422

    def test_negative_buffer_still_accepted(self):
        response = _client().post("/filters/geometry", json={"wkt": "POINT(0 0)", "crs": "EPSG:2154",
                                                             "target_layers": ["communes"], "buffer": -5})
        assert response.status_code == 200

    def test_nan_raster_bound_is_refused(self):
        body = ('{"source_layer":"communes","target_layers":["communes"],'
                '"raster_selection":{"mode":"range","minimum":NaN,"maximum":5}}')
        response = _client().post("/filters/cross", content=body, headers={"content-type": "application/json"})
        assert response.status_code == 422

    def test_infinite_point_cloud_bound_is_refused(self):
        body = '{"layers":["x"],"criteria":{"z_min":-Infinity}}'
        response = _client().post("/filters/point-cloud", content=body, headers={"content-type": "application/json"})
        assert response.status_code == 422


class TestExportSubfolderFullmatch:
    @pytest.mark.parametrize("subfolder", ["a\n", "zone/a\n", "a\nb"])
    def test_newline_is_refused(self, tmp_path, subfolder):
        with pytest.raises(ValueError):
            resolve_export_folder(tmp_path, subfolder)

    def test_plain_subfolder_resolves_below_the_root(self, tmp_path):
        assert resolve_export_folder(tmp_path, "zone/2026-10") == (tmp_path / "zone" / "2026-10").resolve()
