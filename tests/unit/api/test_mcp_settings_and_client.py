# -*- coding: utf-8 -*-
"""Settings and HTTP client of the MCP server. Needs neither the ``mcp`` SDK nor FastAPI."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from filtermate_api.mcp.rest_client import FilterMateAPIError, FilterMateClient
from filtermate_api.mcp.settings import (
    DEFAULT_TIMEOUT_SECONDS,
    ConfigError,
    parse_settings,
)

DROP = "drop"            # see FakeRestApi in conftest.py
TRUNCATED = "truncated"
ROOT = Path(__file__).resolve().parents[3]


# --- settings -------------------------------------------------------------------

def test_defaults_read_the_key_from_the_environment():
    settings = parse_settings([], {"FILTERMATE_API_KEY": "secret"})
    assert settings.base_url == "http://127.0.0.1:8000"
    assert settings.api_key == "secret"
    assert settings.timeout == DEFAULT_TIMEOUT_SECONDS > 30
    assert settings.is_loopback
    assert "secret" not in repr(settings)


def test_no_key_refuses_to_start():
    with pytest.raises(ConfigError, match="FILTERMATE_API_KEY"):
        parse_settings([], {})
    with pytest.raises(ConfigError):
        parse_settings([], {"FILTERMATE_API_KEY": ""})
    with pytest.raises(ConfigError, match="whitespace"):
        parse_settings([], {"FILTERMATE_API_KEY": "   "})


def test_other_variable_name():
    settings = parse_settings(["--api-key-env", "MY_KEY"], {"MY_KEY": "k"})
    assert settings.api_key == "k"
    with pytest.raises(ConfigError, match="MY_KEY"):
        parse_settings(["--api-key-env", "MY_KEY"], {"FILTERMATE_API_KEY": "k"})


def test_a_key_given_as_variable_name_is_refused():
    with pytest.raises(ConfigError, match="NAME"):
        parse_settings(["--api-key-env", "abc-123.def"], {"abc-123.def": "x"})


def test_there_is_no_api_key_option():
    for args in (["--api-key", "s3cret"], ["--api-key=s3cret"], ["--api-key-envx", "s3cret"]):
        with pytest.raises(ConfigError, match="never accepted") as info:
            parse_settings(args, {"FILTERMATE_API_KEY": "k"})
        assert "s3cret" not in str(info.value)


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8000", "http://localhost:9000/", "http://[::1]:8000", "http://LOCALHOST:1", "https://localhost",
])
def test_loopback_urls_are_accepted(url):
    settings = parse_settings(["--url", url], {"FILTERMATE_API_KEY": "k"})
    assert settings.base_url == url.rstrip("/")


@pytest.mark.parametrize("url", ["http://192.168.1.10:8000", "https://qgis.example.org", "http://0.0.0.0:8000"])
def test_remote_urls_need_allow_remote(url):
    with pytest.raises(ConfigError, match="allow-remote"):
        parse_settings(["--url", url], {"FILTERMATE_API_KEY": "k"})
    settings = parse_settings(["--url", url, "--allow-remote"], {"FILTERMATE_API_KEY": "k"})
    assert not settings.is_loopback


@pytest.mark.parametrize("url", ["ftp://127.0.0.1", "127.0.0.1:8000", "http://", "http://u:p@127.0.0.1:8000",
                                 "http://127.0.0.1:8000?x=1", "http://127.0.0.1:99999"])
def test_malformed_urls_are_refused(url):
    with pytest.raises(ConfigError):
        parse_settings(["--url", url, "--allow-remote"], {"FILTERMATE_API_KEY": "k"})


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "601", "1e9"])
def test_timeout_must_be_finite_positive_and_bounded(value):
    with pytest.raises(ConfigError, match="--timeout"):
        parse_settings(["--timeout", value], {"FILTERMATE_API_KEY": "k"})
    assert parse_settings(["--timeout", "600"], {"FILTERMATE_API_KEY": "k"}).timeout == 600


@pytest.mark.parametrize("url", ["http://127.0.0.2:8000", "http://127.1:8000", "http://[::ffff:127.0.0.1]:8000"])
def test_only_the_loopback_names_of_the_api_count_as_loopback(url):
    with pytest.raises(ConfigError, match="allow-remote"):
        parse_settings(["--url", url], {"FILTERMATE_API_KEY": "k"})


@pytest.mark.parametrize("url", ["http://127.0.0.1:8000 ", "http://127.0.0.1 :8000", "http://127.0.0.1:8000/\n",
                                 "http://127.0.0.1/a b"])
def test_urls_with_whitespace_or_control_characters_are_refused(url):
    with pytest.raises(ConfigError, match="spaces or control"):
        parse_settings(["--url", url], {"FILTERMATE_API_KEY": "k"})


def test_the_key_is_not_stripped_but_stray_whitespace_is_refused():
    assert parse_settings([], {"FILTERMATE_API_KEY": "a b"}).api_key == "a b"
    for value in (" S3cret", "S3cret ", "S3cret\t"):
        with pytest.raises(ConfigError, match="whitespace|printable") as info:
            parse_settings([], {"FILTERMATE_API_KEY": value})
        assert "S3cret" not in str(info.value)


def test_a_key_mistaken_for_a_variable_name_is_not_echoed():
    secret = "NotARealKey" * 2  # must look like a variable name
    with pytest.raises(ConfigError) as info:
        parse_settings(["--api-key-env", secret], {})
    assert secret not in str(info.value)
    with pytest.raises(ConfigError, match="MY_KEY"):
        parse_settings(["--api-key-env", "MY_KEY"], {})


def test_key_with_control_characters_is_refused():
    with pytest.raises(ConfigError, match="ASCII"):
        parse_settings([], {"FILTERMATE_API_KEY": "a\nb"})


# --- client ---------------------------------------------------------------------

def make_client(fake_api, api_key, **kwargs):
    return FilterMateClient(fake_api.url, api_key, **kwargs)


def test_get_sends_the_key_and_decodes_json(fake_api, api_key):
    fake_api.respond("GET", "/layers", [{"name": "communes"}])
    assert make_client(fake_api, api_key).get("/layers") == [{"name": "communes"}]
    request = fake_api.requests[0]
    assert request["method"] == "GET" and request["path"] == "/layers"
    assert request["headers"]["x-api-key"] == api_key
    assert request["body"] is None


def test_post_sends_json(fake_api, api_key):
    fake_api.respond("POST", "/filters/clear", {"done": ["a"]})
    result = make_client(fake_api, api_key).post("/filters/clear", {"layers": ["a"]})
    assert result == {"done": ["a"]}
    request = fake_api.requests[0]
    assert request["body"] == {"layers": ["a"]}
    assert request["headers"]["content-type"] == "application/json"


def test_503_says_qgis_is_busy_and_nothing_changed(fake_api, api_key):
    fake_api.respond("POST", "/filters/undo", {"detail": "QGIS is busy: main thread"}, 503, {"Retry-After": "5"})
    with pytest.raises(FilterMateAPIError) as info:
        make_client(fake_api, api_key).post("/filters/undo")
    message = str(info.value)
    assert message.startswith("QGIS is busy: main thread") and "nothing was changed" in message and "5 s" in message
    assert info.value.status == 503


def test_503_of_the_favorites_store_keeps_its_own_detail(fake_api, api_key):
    fake_api.respond("GET", "/favorites", {"detail": "Favorites store not ready"}, 503, {"Retry-After": "30"})
    with pytest.raises(FilterMateAPIError, match="Favorites store not ready") as info:
        make_client(fake_api, api_key).get("/favorites")
    assert "30 s" in str(info.value)


@pytest.mark.parametrize("status", [401, 403])
def test_401_403_say_the_key_is_wrong(fake_api, api_key, status):
    fake_api.respond("GET", "/layers", {"detail": "Invalid or missing API key"}, status)
    fake_api.expected_key = None
    with pytest.raises(FilterMateAPIError, match="API key"):
        make_client(fake_api, api_key).get("/layers")


def test_wrong_key_is_a_401(fake_api):
    with pytest.raises(FilterMateAPIError, match=r"rejected the API key \(HTTP 401\)"):
        FilterMateClient(fake_api.url, "not-the-key").get("/layers")


def test_422_gives_where_and_why(fake_api, api_key):
    fake_api.respond("POST", "/filters/cross", {"detail": [
        {"type": "value_error", "loc": ["body", "raster_selection"], "msg": "Value error, a range needs a minimum"},
        {"type": "missing", "loc": ["body", "target_layers"], "msg": "Field required"},
    ]}, 422)
    with pytest.raises(FilterMateAPIError) as info:
        make_client(fake_api, api_key).post("/filters/cross", {})
    message = str(info.value)
    assert "422" in message
    assert "raster_selection: Value error, a range needs a minimum" in message
    assert "target_layers: Field required" in message


def test_422_with_a_text_detail(fake_api, api_key):
    fake_api.respond("POST", "/filters/cross", {"detail": "Unknown predicate"}, 422)
    with pytest.raises(FilterMateAPIError, match="Unknown predicate"):
        make_client(fake_api, api_key).post("/filters/cross", {})


@pytest.mark.parametrize("status,text", [(404, "Layer not found"), (409, "Nothing to undo"),
                                         (400, "Cross filter failed: boom"), (500, "Export root unavailable")])
def test_other_statuses_keep_the_detail(fake_api, api_key, status, text):
    fake_api.respond("POST", "/x", {"detail": text}, status)
    with pytest.raises(FilterMateAPIError, match=text) as info:
        make_client(fake_api, api_key).post("/x")
    assert info.value.status == status


def test_apply_404_names_both_causes(fake_api, api_key):
    fake_api.respond("POST", "/filters/apply", {"detail": "Layer not found"}, 404)
    with pytest.raises(FilterMateAPIError) as info:
        make_client(fake_api, api_key).post("/filters/apply", {"layer_name": "a", "expression": "x"})
    message = str(info.value)
    assert "vector layer not found by its name" in message and "refused by the data provider" in message


def test_route_not_found_means_an_older_api(fake_api, api_key):
    # The fake answers {"detail": "Not Found"} for any route it does not know, like FastAPI.
    with pytest.raises(FilterMateAPIError, match="older than this MCP server"):
        make_client(fake_api, api_key).post("/filters/cross", {})


def test_413_has_its_own_message(fake_api, api_key):
    fake_api.respond("POST", "/filters/geometry", {"detail": "Request body too large"}, 413)
    with pytest.raises(FilterMateAPIError, match="too large for the FilterMate REST API"):
        make_client(fake_api, api_key).post("/filters/geometry", {})


def test_dropped_connection_on_a_write_may_have_been_applied(fake_api, api_key):
    fake_api.respond("POST", "/filters/clear", DROP)
    with pytest.raises(FilterMateAPIError) as info:
        make_client(fake_api, api_key).post("/filters/clear", {"layers": ["a"]})
    assert "may have been applied" in str(info.value) and "filter_state" in str(info.value)


def test_dropped_connection_on_a_read_has_no_such_warning(fake_api, api_key):
    fake_api.respond("GET", "/layers", DROP)
    with pytest.raises(FilterMateAPIError) as info:
        make_client(fake_api, api_key).get("/layers")
    assert "connection to the FilterMate REST API" in str(info.value) and "may have been applied" not in str(info.value)


def test_truncated_answer_to_a_write_may_have_been_applied(fake_api, api_key):
    fake_api.respond("POST", "/filters/undo", TRUNCATED)
    with pytest.raises(FilterMateAPIError, match="may have been applied"):
        make_client(fake_api, api_key).post("/filters/undo")


def test_error_body_that_never_arrives_still_gives_the_status(fake_api, api_key):
    fake_api.respond("POST", "/filters/undo", TRUNCATED, 409)
    with pytest.raises(FilterMateAPIError, match="HTTP 409"):
        make_client(fake_api, api_key).post("/filters/undo")


def test_invalid_url_is_a_readable_error(api_key):
    with pytest.raises(FilterMateAPIError, match="only http and https"):
        FilterMateClient("ftp://127.0.0.1", api_key).get("/layers")


def test_non_ascii_text_is_sent_as_utf8_not_escaped(fake_api, api_key):
    fake_api.respond("POST", "/filters/apply", {"success": True})
    make_client(fake_api, api_key).post("/filters/apply", {"layer_name": "communes", "expression": "nom = 'Ménès'"})
    assert fake_api.requests[0]["body"]["expression"] == "nom = 'Ménès'"
    assert "Ménès".encode("utf-8") in fake_api.requests[0]["raw_body"]


def test_connection_refused_on_a_write_was_not_sent(api_key):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with pytest.raises(FilterMateAPIError) as info:
        FilterMateClient("http://127.0.0.1:%d" % port, api_key).post("/filters/clear", {"layers": ["a"]})
    assert "may have been applied" not in str(info.value)


def test_connection_refused_tells_how_to_start_the_api(api_key):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with pytest.raises(FilterMateAPIError) as info:
        FilterMateClient("http://127.0.0.1:%d" % port, api_key, timeout=5).get("/layers")
    message = str(info.value)
    assert "Cannot reach the FilterMate REST API" in message
    assert "Start the FilterMate REST API in QGIS" in message and "docs/AUTOMATION.md" in message


def test_timeout_on_a_write_warns_it_may_have_applied(fake_api, api_key):
    fake_api.respond("POST", "/filters/clear", {"done": []})
    fake_api.delay = 1.5
    with pytest.raises(FilterMateAPIError, match="filter_state before retrying"):
        make_client(fake_api, api_key, timeout=0.3).post("/filters/clear", {"layers": ["a"]})


def test_timeout_on_a_read(fake_api, api_key):
    fake_api.respond("GET", "/layers", [])
    fake_api.delay = 1.5
    with pytest.raises(FilterMateAPIError, match="busy on a long task"):
        make_client(fake_api, api_key, timeout=0.3).get("/layers")


def test_non_json_answer_is_not_the_filtermate_api(fake_api, api_key):
    fake_api.respond("GET", "/layers", b"<html>nope</html>")
    with pytest.raises(FilterMateAPIError, match="not the FilterMate REST API"):
        make_client(fake_api, api_key).get("/layers")


def test_redirects_are_not_followed(fake_api, api_key):
    fake_api.respond("GET", "/layers", {"detail": "moved"}, 307, {"Location": "http://example.invalid/layers"})
    with pytest.raises(FilterMateAPIError, match="HTTP 307"):
        make_client(fake_api, api_key).get("/layers")
    assert len(fake_api.requests) == 1


# --- isolation from the plugin ---------------------------------------------------

def test_importing_the_package_loads_neither_the_sdk_nor_qgis_nor_fastapi():
    code = (
        "import sys, filtermate_api, filtermate_api.mcp, filtermate_api.mcp.settings, "
        "filtermate_api.mcp.rest_client\n"
        "bad = [m for m in ('mcp', 'qgis', 'fastapi', 'httpx', 'requests') if m in sys.modules]\n"
        "assert not bad, bad\n"
    )
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    result = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT), capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr


def test_the_plugin_never_imports_the_api_or_the_mcp_server():
    for name in ("filter_mate.py", "filter_mate_app.py", "__init__.py"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "filtermate_api" not in text, name
    assert "mcp" not in (ROOT / "filtermate_api" / "__init__.py").read_text(encoding="utf-8")
