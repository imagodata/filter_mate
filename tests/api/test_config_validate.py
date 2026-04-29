"""S1 — APIConfig.validate refuses remotely exploitable configurations.

Issue: a fresh install with no FILTERMATE_API_KEY and a non-loopback bind
shipped a remotely-driveable QGIS session. validate() now refuses such
configs unless the operator opts in via FILTERMATE_API_ALLOW_INSECURE=1.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from filtermate_api.accessor import InMemoryAccessor  # noqa: E402
from filtermate_api.config import APIConfig, APIConfigError  # noqa: E402
from filtermate_api.server import create_app  # noqa: E402


class TestValidateAllowsLoopback:
    def test_loopback_127_no_auth_passes(self):
        APIConfig(host="127.0.0.1", api_key=None).validate()

    def test_loopback_localhost_no_auth_passes(self):
        APIConfig(host="localhost", api_key=None).validate()

    def test_loopback_ipv6_no_auth_passes(self):
        APIConfig(host="::1", api_key=None).validate()

    def test_loopback_with_wildcard_cors_passes(self):
        # On loopback, wildcard CORS is acceptable — create_app forces
        # allow_credentials=False so cookies/credentials cannot ride along.
        APIConfig(host="127.0.0.1", cors_origins=["*"], api_key=None).validate()


class TestValidateRejectsRemoteExposure:
    def test_zero_zero_zero_zero_no_auth_raises(self):
        cfg = APIConfig(host="0.0.0.0", api_key=None)
        with pytest.raises(APIConfigError, match="non-loopback"):
            cfg.validate()

    def test_lan_ip_no_auth_raises(self):
        cfg = APIConfig(host="192.168.1.10", api_key=None)
        with pytest.raises(APIConfigError, match="api_key is unset"):
            cfg.validate()

    def test_public_host_no_auth_raises(self):
        cfg = APIConfig(host="api.example.com", api_key=None)
        with pytest.raises(APIConfigError):
            cfg.validate()

    def test_non_loopback_with_auth_but_wildcard_cors_raises(self):
        cfg = APIConfig(
            host="0.0.0.0",
            api_key="secret-123",
            cors_origins=["*"],
        )
        with pytest.raises(APIConfigError, match="wildcard"):
            cfg.validate()

    def test_non_loopback_with_auth_and_explicit_origins_passes(self):
        APIConfig(
            host="0.0.0.0",
            api_key="secret-123",
            cors_origins=["https://app.example.com"],
        ).validate()


class TestInsecureOverride:
    def test_allow_insecure_true_bypasses_validation(self):
        cfg = APIConfig(host="0.0.0.0", api_key=None, cors_origins=["*"])
        # Should not raise.
        cfg.validate(allow_insecure=True)

    def test_env_var_bypasses_validation(self, monkeypatch):
        monkeypatch.setenv("FILTERMATE_API_ALLOW_INSECURE", "1")
        cfg = APIConfig(host="0.0.0.0", api_key=None)
        cfg.validate()

    def test_env_var_false_does_not_bypass(self, monkeypatch):
        monkeypatch.setenv("FILTERMATE_API_ALLOW_INSECURE", "false")
        cfg = APIConfig(host="0.0.0.0", api_key=None)
        with pytest.raises(APIConfigError):
            cfg.validate()

    def test_explicit_false_overrides_env(self, monkeypatch):
        monkeypatch.setenv("FILTERMATE_API_ALLOW_INSECURE", "1")
        cfg = APIConfig(host="0.0.0.0", api_key=None)
        with pytest.raises(APIConfigError):
            cfg.validate(allow_insecure=False)


class TestCreateAppPropagatesValidation:
    def test_create_app_refuses_insecure_config(self):
        cfg = APIConfig(host="0.0.0.0", api_key=None)
        with pytest.raises(APIConfigError):
            create_app(config=cfg, accessor=InMemoryAccessor())

    def test_create_app_with_explicit_override_succeeds(self):
        cfg = APIConfig(host="0.0.0.0", api_key=None)
        app = create_app(
            config=cfg,
            accessor=InMemoryAccessor(),
            allow_insecure=True,
        )
        client = TestClient(app)
        assert client.get("/").status_code == 200

    def test_create_app_default_loopback_still_works(self):
        # Regression guard: the existing dev-mode contract (api_key=None
        # on 127.0.0.1) must keep working without ceremony.
        app = create_app(
            config=APIConfig(),
            accessor=InMemoryAccessor(),
        )
        assert TestClient(app).get("/").status_code == 200


class TestWildcardCorsForcesNoCredentials:
    def test_wildcard_origin_disables_credentials_in_response(self):
        # When origins=["*"], the CORS middleware must not advertise
        # allow-credentials — even on loopback. Browsers ignore that
        # combination silently; we make the policy explicit.
        cfg = APIConfig(host="127.0.0.1", cors_origins=["*"])
        client = TestClient(create_app(config=cfg, accessor=InMemoryAccessor()))
        response = client.options(
            "/layers",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-credentials") != "true"

    def test_explicit_origin_allows_credentials(self):
        cfg = APIConfig(
            host="127.0.0.1",
            cors_origins=["https://trusted.example"],
        )
        client = TestClient(create_app(config=cfg, accessor=InMemoryAccessor()))
        response = client.options(
            "/layers",
            headers={
                "Origin": "https://trusted.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-credentials") == "true"
