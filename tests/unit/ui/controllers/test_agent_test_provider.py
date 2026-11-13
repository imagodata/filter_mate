# -*- coding: utf-8 -*-
"""The Test button of the Provider tab: AgentChatController._test_provider, with the network and the key store faked.

The controller is loaded for real under a synthetic package (as test_agent_settings_hardening does); QGIS stays
mocked by the root conftest, with the two Qt modules it does not mock.
"""
import importlib
import json
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_agent_test_provider_test"
SECRET = "sk-typed-0123456789"
STORED = "sk-stored-9876543210"


def _load():
    for name, path in (("", _ROOT), (".ui", _ROOT / "ui"), (".ui.controllers", _ROOT / "ui" / "controllers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    stubs = [name for name in ("qgis.PyQt.QtNetwork", "qgis.PyQt.QtXml") if name not in sys.modules]
    sys.modules.update({name: MagicMock() for name in stubs})
    try:
        return (importlib.import_module(f"{_PKG}.ui.controllers.agent_chat_controller"),
                importlib.import_module(f"{_PKG}.adapters.agent.bounded_http"),
                importlib.import_module(f"{_PKG}.adapters.agent.settings"))
    finally:
        for name in stubs:
            sys.modules.pop(name, None)


controller_module, http, settings = _load()
Controller = controller_module.AgentChatController


def sse(*events):
    return "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()


CLAUDE_OK = sse({"type": "message_start", "message": {"usage": {}}},
                {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
                {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "OK"}},
                {"type": "content_block_stop", "index": 0},
                {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 2}},
                {"type": "message_stop"})
OPENAI_OK = (b'data: {"choices":[{"delta":{"content":"OK"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n')
OLLAMA_OK = b'{"message":{"role":"assistant","content":"OK"},"done":true,"done_reason":"stop"}\n'
CLAUDE_LIST = json.dumps({"data": [{"id": "claude-haiku-5-5"}, {"id": "claude-sonnet-5-5"}]}).encode()
OPENAI_LIST = json.dumps({"data": [{"id": "gpt-x"}, {"id": "text-embedding-3-small"}]}).encode()


@pytest.fixture
def network(monkeypatch):
    """fetch() replaced: ``answers`` maps a URL suffix to a BoundedReply (or an HttpFailure to raise)."""
    state = types.SimpleNamespace(requests=[], answers={}, stored=STORED, values=settings.AgentSettings())

    def fetch(url, body=None, headers=None, max_bytes=0, timeout_ms=0, **kwargs):
        state.requests.append(types.SimpleNamespace(url=url, body=body, headers=dict(headers or {}),
                                                    timeout_ms=timeout_ms, max_bytes=max_bytes,
                                                    owner=http._OWNER[0]))
        for suffix, answer in state.answers.items():
            if url.endswith(suffix):
                if isinstance(answer, Exception):
                    raise answer
                return answer
        raise AssertionError(f"unexpected request {url}")

    monkeypatch.setattr(controller_module, "QCoreApplication", types.SimpleNamespace(translate=lambda ctx, text: text))
    monkeypatch.setattr(controller_module, "fetch", fetch)
    monkeypatch.setattr(controller_module, "load_settings", lambda: state.values)
    monkeypatch.setattr(controller_module, "read_key", lambda authcfg: state.stored if authcfg else "")
    return state


def reply(content, status=200, headers=None):
    return http.BoundedReply(status, headers or {}, content)


def test_anthropic_answers_and_lists_its_models(network):
    network.answers = {"/v1/messages": reply(CLAUDE_OK), "/v1/models?limit=100": reply(CLAUDE_LIST)}
    answers, message, models = Controller._test_provider("anthropic", "claude-haiku-5-5", "", SECRET)
    assert (answers, message, models) == (True, "It answers.", ("claude-haiku-5-5", "claude-sonnet-5-5"))
    chat, listing = network.requests
    body = json.loads(chat.body)
    assert body["max_tokens"] == 16 and body["model"] == "claude-haiku-5-5"
    assert body["messages"] == [{"role": "user", "content": [{"type": "text", "text": "Reply with OK."}]}]
    assert "tools" not in body  # an empty list is a 400 for OpenAI
    assert chat.timeout_ms == 30_000 and listing.timeout_ms <= 30_000
    assert chat.headers["x-api-key"] == SECRET and listing.headers["x-api-key"] == SECRET
    assert listing.body is None  # a GET
    assert "content-type" not in {name.lower() for name in listing.headers}


def test_openai_compatible_lists_through_its_models_path_and_keeps_chat_models(network):
    network.values = settings.AgentSettings(preset="openai")
    network.answers = {"/v1/chat/completions": reply(OPENAI_OK), "/v1/models": reply(OPENAI_LIST)}
    assert Controller._test_provider("openai", "gpt-x", "", SECRET) == (True, "It answers.", ("gpt-x",))
    assert [request.url for request in network.requests] == ["https://api.openai.com/v1/chat/completions",
                                                             "https://api.openai.com/v1/models"]
    assert network.requests[1].headers["authorization"] == f"Bearer {SECRET}"


def test_a_refused_key_is_worded_without_the_key_and_lists_nothing(network):
    body = json.dumps({"error": {"message": f"Incorrect API key provided: {SECRET}."}}).encode()
    network.answers = {"/v1/messages": reply(body, 401)}
    answers, message, models = Controller._test_provider("anthropic", "m", "", SECRET)
    assert answers is False and models == ()
    assert message == "The provider refused the API key: check it in the agent settings."
    assert len(network.requests) == 1  # no point in listing with a key that is refused


def test_a_problem_the_provider_words_never_carries_the_key(network):
    body = json.dumps({"error": {"message": f"The key {SECRET} is not allowed here."}}).encode()
    network.answers = {"/v1/messages": reply(body, 400), "/v1/models?limit=100": reply(CLAUDE_LIST)}
    answers, message, models = Controller._test_provider("anthropic", "m", "", SECRET)
    assert answers is False and SECRET not in message and "is not allowed here" in message
    assert models == ("claude-haiku-5-5", "claude-sonnet-5-5")  # a wrong model name: the list says which exist


def test_no_key_typed_uses_the_stored_one_for_the_same_server(network):
    network.values = settings.AgentSettings(preset="anthropic", authcfg="cfg", key_target="https://api.anthropic.com")
    network.answers = {"/v1/messages": reply(CLAUDE_OK), "/v1/models?limit=100": reply(CLAUDE_LIST)}
    assert Controller._test_provider("anthropic", "m", "", "")[0] is True
    assert network.requests[0].headers["x-api-key"] == STORED


def test_the_stored_key_is_not_sent_to_another_server(network):
    network.values = settings.AgentSettings(preset="anthropic", authcfg="cfg", key_target="https://api.anthropic.com")
    answers, message, models = Controller._test_provider("anthropic", "m", "https://relay.example.com", "")
    assert (answers, models) == (False, ()) and message == "Enter your API key first."
    assert network.requests == []


def test_no_key_at_all_asks_for_one(network):
    assert Controller._test_provider("mistral", "m", "", "") == (False, "Enter your API key first.", ())
    assert network.requests == []


def test_a_locked_key_store_is_said(network, monkeypatch):
    network.values = settings.AgentSettings(preset="anthropic", authcfg="cfg", key_target="https://api.anthropic.com")

    def locked(authcfg):
        raise settings.KeyStoreError("The authentication database is locked.")

    monkeypatch.setattr(controller_module, "read_key", locked)
    assert Controller._test_provider("anthropic", "m", "", "") == (False, "The authentication database is locked.", ())


def test_without_a_model_it_only_lists(network):
    network.answers = {"/v1/models": reply(OPENAI_LIST)}
    answers, message, models = Controller._test_provider("mistral", "", "https://api.mistral.ai/v1", SECRET)
    assert answers is True and models == ("gpt-x",) and "model" in message.lower()
    assert [request.url for request in network.requests] == ["https://api.mistral.ai/v1/models"]


def test_without_a_model_a_refused_key_is_still_said(network):
    network.answers = {"/v1/models": reply(b'{"error":"no"}', 401)}
    assert Controller._test_provider("mistral", "", "", SECRET) == (
        False, "The provider refused the API key: check it in the agent settings.", ())


def test_a_provider_that_does_not_answer_in_time(network):
    network.answers = {"/v1/messages": http.HttpFailure(http.TOO_LONG)}
    answers, message, models = Controller._test_provider("anthropic", "m", "", SECRET)
    assert (answers, models) == (False, ())
    assert message == "The provider could not be reached: " + http.TOO_LONG
    assert len(network.requests) == 1


def test_a_stream_that_fails_after_a_200_is_a_failure(network):
    cut = sse({"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}})
    network.answers = {"/v1/messages": reply(cut), "/v1/models?limit=100": reply(CLAUDE_LIST)}
    answers, message, _models = Controller._test_provider("anthropic", "m", "", SECRET)
    assert answers is False and "Overloaded" in message


def test_a_listing_that_fails_does_not_undo_an_answer(network):
    network.answers = {"/v1/messages": reply(CLAUDE_OK), "/v1/models?limit=100": reply(b"<html>", 200)}
    assert Controller._test_provider("anthropic", "m", "", SECRET) == (True, "It answers.", ())


def test_an_address_that_would_send_the_key_in_clear_is_refused_before_any_request(network):
    answers, message, models = Controller._test_provider("anthropic", "m", "http://gpu.lan:8000", SECRET)
    assert answers is False and models == () and SECRET not in message and network.requests == []


def test_ollama_needs_no_key_and_lists_its_installed_models(network):
    tags = json.dumps({"models": [{"name": "qwen3:4b", "details": {"family": "qwen3"}}]}).encode()
    network.answers = {"/api/chat": reply(OLLAMA_OK), "/api/tags": reply(tags)}
    assert Controller._test_provider("ollama", "qwen3:4b", "", "ignored") == (True, "It answers.", ("qwen3:4b",))
    assert [request.url for request in network.requests] == ["http://localhost:11434/api/chat",
                                                             "http://localhost:11434/api/tags"]
    assert all("authorization" not in request.headers for request in network.requests)


def test_a_key_never_ends_up_in_a_log_line(network, caplog):
    caplog.set_level("DEBUG")
    network.answers = {"/v1/messages": reply(b'{"error":"x"}', 401)}
    Controller._test_provider("anthropic", "m", "", SECRET)
    assert SECRET not in caplog.text


def test_the_openai_request_of_the_test_holds_no_tools_key(network):
    network.values = settings.AgentSettings(preset="openai")
    network.answers = {"/v1/chat/completions": reply(OPENAI_OK), "/v1/models": reply(OPENAI_LIST)}
    Controller._test_provider("openai", "gpt-x", "", SECRET)
    body = json.loads(network.requests[0].body)
    assert "tools" not in body and "tool_choice" not in body


@pytest.mark.parametrize("key", ["e", "It", "short12"])
def test_a_short_key_does_not_damage_the_message(network, key):
    """The key is hidden in the words of the provider, but a key of one letter would break any message."""
    body = json.dumps({"error": {"message": "It answers badly: the model does not exist."}}).encode()
    network.answers = {"/v1/messages": reply(body, 400), "/v1/models?limit=100": reply(CLAUDE_LIST)}
    _answers, message, _models = Controller._test_provider("anthropic", "m", "", key)
    assert "It answers badly: the model does not exist." in message


def test_a_key_of_eight_characters_is_still_hidden(network):
    body = json.dumps({"error": {"message": "The key 12345678 is not allowed here."}}).encode()
    network.answers = {"/v1/messages": reply(body, 400), "/v1/models?limit=100": reply(CLAUDE_LIST)}
    _answers, message, _models = Controller._test_provider("anthropic", "m", "", "12345678")
    assert "12345678" not in message and "is not allowed here" in message


def test_the_waits_of_the_test_belong_to_the_test_alone(network):
    """Stop of the chat must not end them, and closing the settings must end them (abort_active)."""
    network.answers = {"/v1/messages": reply(CLAUDE_OK), "/v1/models?limit=100": reply(CLAUDE_LIST)}
    Controller._test_provider("anthropic", "m", "", SECRET)
    assert [request.owner for request in network.requests] == [controller_module.PROVIDER_TEST_WAITS] * 2
    assert http._OWNER[0] == ""  # and only for the call


def test_a_cold_ollama_that_takes_too_long_still_lists_its_models(network):
    tags = json.dumps({"models": [{"name": "qwen3:4b", "details": {"family": "qwen3"}}]}).encode()
    network.answers = {"/api/chat": http.HttpFailure(http.TOO_LONG), "/api/tags": reply(tags)}
    answers, message, models = Controller._test_provider("ollama", "qwen3:4b", "", "")
    assert answers is False and models == ("qwen3:4b",) and message
    assert [request.url for request in network.requests] == ["http://localhost:11434/api/chat",
                                                             "http://localhost:11434/api/tags"]


@pytest.mark.parametrize("failure", [http.STOPPED, "connection refused"])
def test_ollama_that_does_not_answer_or_was_stopped_does_not_list(network, failure):
    network.answers = {"/api/chat": http.HttpFailure(failure)}
    answers, _message, models = Controller._test_provider("ollama", "qwen3:4b", "", "")
    assert (answers, models) == (False, ()) and len(network.requests) == 1


def test_ollama_test_asks_for_a_few_tokens_only(network):
    network.answers = {"/api/chat": reply(OLLAMA_OK), "/api/tags": reply(b'{"models":[]}')}
    Controller._test_provider("ollama", "qwen3:4b", "", "")
    assert json.loads(network.requests[0].body)["options"]["num_predict"] == controller_module.PROVIDER_TEST_TOKENS
