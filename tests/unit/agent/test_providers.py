# -*- coding: utf-8 -*-
"""The two wire formats: what is sent, and how a stream cut anywhere is put back together."""
import json

import pytest

from core.agent.messages import (
    ROLE_ASSISTANT, ROLE_USER, STOP_END, STOP_MAX_TOKENS, STOP_REFUSAL, STOP_TOOL_USE, Message, OpaquePart,
    StreamFailure, TextDelta, TextPart, ToolCallPart, ToolResultPart, TurnComplete,
)
from core.agent.providers import PRESETS, create_provider
from core.agent.providers.base import (
    ProviderConfig, SseDecoder, check_base_url, error_from_response, without_credentials)
from core.agent.tool_catalog import ToolSpec

pytestmark = pytest.mark.unit

TOOL = ToolSpec("list_layers", "List the layers.", {"type": "object", "properties": {}})
SECRET = "sk-secret-value"


def claude(model="claude-haiku-5-5", **kwargs):
    return create_provider(ProviderConfig("anthropic", model, api_key=SECRET, **kwargs))


def compatible(**kwargs):
    return create_provider(ProviderConfig("openai_compatible", "m", base_url="https://api.mistral.ai/v1",
                                          api_key=SECRET, **kwargs))


def sse(*events):
    return "".join(f"event: {e['type']}\ndata: {json.dumps(e, ensure_ascii=False)}\n\n" for e in events).encode()


def chunks(*payloads):
    return "".join(f"data: {json.dumps(p, ensure_ascii=False)}\n\n" for p in payloads).encode() + b"data: [DONE]\n\n"


def run(parser, data, step=None):
    events = []
    step = step or len(data)
    for start in range(0, len(data), step):
        events.extend(parser.feed(data[start:start + step]))
    return events + parser.close()


def turn_of(events):
    return next(event for event in events if isinstance(event, TurnComplete))


CLAUDE_TURN = sse(
    {"type": "message_start", "message": {"usage": {"input_tokens": 11, "cache_read_input_tokens": 5,
                                                    "cache_creation_input_tokens": 3, "output_tokens": 1}}},
    {"type": "ping"},
    {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", "thinking": "", "signature": ""}},
    {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "hmm"}},
    {"type": "content_block_delta", "index": 0, "delta": {"type": "signature_delta", "signature": "SIG"}},
    {"type": "content_block_stop", "index": 0},
    {"type": "content_block_start", "index": 1, "content_block": {"type": "text", "text": ""}},
    {"type": "content_block_delta", "index": 1, "delta": {"type": "text_delta", "text": "Je regarde é"}},
    {"type": "content_block_stop", "index": 1},
    {"type": "content_block_start", "index": 2, "content_block": {"type": "tool_use", "id": "t1", "name": "x", "input": {}}},
    {"type": "content_block_delta", "index": 2, "delta": {"type": "input_json_delta", "partial_json": "{\"a\":"}},
    {"type": "content_block_delta", "index": 2, "delta": {"type": "input_json_delta", "partial_json": " 1}"}},
    {"type": "content_block_stop", "index": 2},
    {"type": "message_delta", "delta": {"stop_reason": "tool_use"}, "usage": {"output_tokens": 42}},
    {"type": "message_stop"},
)


class TestAnthropicRequest:
    def test_body_and_headers(self):
        messages = [Message(ROLE_USER, (TextPart("bonjour"),))]
        request = claude().build_request("SYS", messages, [TOOL])
        body = json.loads(request.body)
        assert request.url == "https://api.anthropic.com/v1/messages"
        assert request.headers["x-api-key"] == SECRET
        assert request.headers["anthropic-version"] == "2026-10-21"
        assert body["stream"] is True and body["cache_control"] == {"type": "ephemeral"}
        assert body["system"] == [{"type": "text", "text": "SYS"}]
        assert body["tools"][0]["input_schema"] == TOOL.input_schema
        assert not {"temperature", "top_p", "top_k", "tool_choice"} & set(body)

    def test_same_conversation_same_bytes(self):
        messages = [Message(ROLE_USER, (TextPart("é"),))]
        assert claude().build_request("S", messages, [TOOL]).body == claude().build_request("S", messages, [TOOL]).body

    def test_fallback_only_on_covered_models_and_official_api(self):
        covered = claude("claude-opus-5-5").build_request("S", [], [])
        assert json.loads(covered.body)["fallbacks"] == "default"
        assert covered.headers["anthropic-beta"] == "server-side-fallback-2026-07-01"
        assert "fallbacks" not in json.loads(claude("claude-haiku-5-5").build_request("S", [], []).body)
        relay = claude("claude-opus-5-5", base_url="https://relay.example.org").build_request("S", [], [])
        assert "fallbacks" not in json.loads(relay.body)

    def test_history_round_trip(self):
        thinking = OpaquePart("anthropic", {"type": "thinking", "thinking": "x", "signature": "s"})
        foreign = OpaquePart("other", {"type": "whatever"})
        messages = [
            Message(ROLE_ASSISTANT, (thinking, foreign, TextPart(""), ToolCallPart("t1", "x", {"a": 1}))),
            Message(ROLE_USER, (ToolResultPart("t1", "ok"), ToolResultPart("t2", "no", is_error=True))),
        ]
        wire = json.loads(claude().build_request("S", messages, []).body)["messages"]
        assert wire[0]["content"] == [thinking.data, {"type": "tool_use", "id": "t1", "name": "x", "input": {"a": 1}}]
        assert wire[1]["content"] == [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"},
                                      {"type": "tool_result", "tool_use_id": "t2", "content": "no", "is_error": True}]

    def test_effort_is_optional(self):
        assert "output_config" not in json.loads(claude().build_request("S", [], []).body)
        assert json.loads(claude(effort="low").build_request("S", [], []).body)["output_config"] == {"effort": "low"}


class TestAnthropicStream:
    @pytest.mark.parametrize("step", [None, 1, 7])
    def test_turn_rebuilt_at_any_chunking(self, step):
        events = run(claude().new_parser(), CLAUDE_TURN, step)
        assert "".join(e.text for e in events if isinstance(e, TextDelta)) == "Je regarde é"
        turn = turn_of(events)
        assert turn.stop_reason == STOP_TOOL_USE
        assert turn.usage.input_tokens == 11 and turn.usage.output_tokens == 42
        assert turn.usage.cache_read_tokens == 5 and turn.usage.cache_write_tokens == 3
        opaque, text, call = turn.message.parts
        assert opaque.data == {"type": "thinking", "thinking": "hmm", "signature": "SIG"}
        assert text.text == "Je regarde é"
        assert (call.call_id, call.name, call.arguments, call.parse_error) == ("t1", "x", {"a": 1}, None)

    def test_bad_arguments_are_reported_not_raised(self):
        data = sse({"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "t", "name": "x"}},
                   {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": "{oops"}},
                   {"type": "message_delta", "delta": {"stop_reason": "max_tokens"}},
                   {"type": "message_stop"})
        turn = turn_of(run(claude().new_parser(), data))
        assert turn.stop_reason == STOP_MAX_TOKENS
        assert turn.message.tool_calls[0].parse_error

    def test_cut_response_is_a_failure(self):
        data = sse({"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}})
        assert isinstance(run(claude().new_parser(), data)[-1], StreamFailure)

    def test_thinking_cut_before_its_signature_is_not_kept(self):
        data = sse({"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", "thinking": "", "signature": ""}},
                   {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "par"}},
                   {"type": "message_delta", "delta": {"stop_reason": "max_tokens"}},
                   {"type": "message_stop"})
        assert turn_of(run(claude().new_parser(), data)).message.parts == ()

    @pytest.mark.parametrize("line", [b"data: null\n\n", b"data: [1]\n\n"])
    def test_a_chunk_that_is_no_object_is_a_failure(self, line):
        assert isinstance(run(claude().new_parser(), line)[0], StreamFailure)
        assert isinstance(run(compatible().new_parser(), line)[0], StreamFailure)

    def test_a_lone_surrogate_does_not_break_the_request(self):
        messages = [Message(ROLE_ASSISTANT, (ToolCallPart("c", "x", {"a": "\ud83d"}),))]
        assert claude().build_request("S", messages, []).body

    def test_stream_error_kind(self):
        data = sse({"type": "error", "error": {"type": "overloaded_error", "message": "busy"}})
        event = run(claude().new_parser(), data)[0]
        assert isinstance(event, StreamFailure) and event.error.kind == "server" and event.error.message == "busy"

    def test_refusal(self):
        data = sse({"type": "message_delta", "delta": {"stop_reason": "refusal"}}, {"type": "message_stop"})
        assert turn_of(run(claude().new_parser(), data)).stop_reason == STOP_REFUSAL

    def test_mid_turn_fallback_drops_what_the_declined_model_did(self):
        data = sse(
            {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", "thinking": "a", "signature": "s"}},
            {"type": "content_block_start", "index": 1, "content_block": {"type": "text", "text": ""}},
            {"type": "content_block_delta", "index": 1, "delta": {"type": "text_delta", "text": "partial"}},
            {"type": "content_block_start", "index": 2, "content_block": {"type": "tool_use", "id": "t0", "name": "x", "input": {}}},
            {"type": "content_block_start", "index": 3, "content_block": {"type": "fallback", "from": {}, "to": {}}},
            {"type": "content_block_start", "index": 4, "content_block": {"type": "tool_use", "id": "t1", "name": "y", "input": {}}},
            {"type": "message_delta", "delta": {"stop_reason": "tool_use"}},
            {"type": "message_stop"})
        parts = turn_of(run(claude().new_parser(), data)).message.parts
        assert [type(part).__name__ for part in parts] == ["TextPart", "ToolCallPart"]
        assert parts[1].call_id == "t1"


class TestOpenAICompatible:
    def test_request(self):
        messages = [
            Message(ROLE_USER, (TextPart("hello"),)),
            Message(ROLE_ASSISTANT, (OpaquePart("anthropic", {"type": "thinking"}), TextPart("let me see"),
                                     ToolCallPart("c1", "x", {"a": "é"}))),
            Message(ROLE_USER, (ToolResultPart("c1", "result"),)),
        ]
        request = compatible().build_request("SYS", messages, [TOOL])
        body = json.loads(request.body)
        assert request.url == "https://api.mistral.ai/v1/chat/completions"
        assert request.headers["authorization"] == f"Bearer {SECRET}"
        assert "max_tokens" not in body
        assert [m["role"] for m in body["messages"]] == ["system", "user", "assistant", "tool"]
        assistant = body["messages"][2]
        assert assistant["content"] == "let me see"
        assert json.loads(assistant["tool_calls"][0]["function"]["arguments"]) == {"a": "é"}
        assert body["messages"][3] == {"role": "tool", "tool_call_id": "c1", "content": "result"}
        assert body["tools"][0]["function"]["parameters"] == TOOL.input_schema

    @pytest.mark.parametrize("step", [None, 3])
    def test_streamed_tool_call(self, step):
        data = chunks(
            {"choices": [{"delta": {"content": "ok "}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "c1", "function": {"name": "x", "arguments": "{\"a\""}}]}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": ":1}"}}]}}]},
            {"choices": [{"delta": {}, "finish_reason": "tool_calls"}],
             "usage": {"prompt_tokens": 20, "completion_tokens": 4, "prompt_tokens_details": {"cached_tokens": 15}}})
        turn = turn_of(run(compatible().new_parser(), data, step))
        assert turn.stop_reason == STOP_TOOL_USE and turn.message.text == "ok "
        assert turn.message.tool_calls[0].arguments == {"a": 1}
        assert turn.usage.input_tokens == 5 and turn.usage.cache_read_tokens == 15 and turn.usage.output_tokens == 4

    def test_whole_calls_sharing_an_index(self):
        data = chunks(
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "a", "function": {"name": "x", "arguments": "{}"}}]}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "b", "function": {"name": "y", "arguments": "{}"}}]}}]},
            {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]})
        assert [c.call_id for c in turn_of(run(compatible().new_parser(), data)).message.tool_calls] == ["a", "b"]

    def test_no_index_no_id_and_decoded_arguments(self):
        data = chunks(
            {"choices": [{"delta": {"tool_calls": [{"function": {"name": "x", "arguments": {"a": 1}}},
                                                   {"function": {"name": "y", "arguments": {"b": 2}}}]}}]},
            {"choices": [{"delta": {}, "finish_reason": "stop"}]})
        turn = turn_of(run(compatible().new_parser(), data))
        assert turn.stop_reason == STOP_TOOL_USE  # "stop" after calls, as Ollama says
        assert [(c.call_id, c.name, c.arguments) for c in turn.message.tool_calls] == [
            ("call_0", "x", {"a": 1}), ("call_1", "y", {"b": 2})]

    @pytest.mark.parametrize("reason", ["tool_call", "eos"])
    def test_complete_calls_with_an_unusual_finish_reason(self, reason):
        data = chunks({"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "a", "function": {"name": "x", "arguments": "{}"}}]}}]},
                      {"choices": [{"delta": {}, "finish_reason": reason}]})
        assert turn_of(run(compatible().new_parser(), data)).stop_reason == STOP_TOOL_USE

    def test_a_call_without_a_name_and_odd_arguments_are_dropped(self):
        data = chunks({"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "a", "function": {"arguments": ["x"]}}]}}]},
                      {"choices": [{"delta": {"content": "hi"}, "finish_reason": "stop"}]})
        turn = turn_of(run(compatible().new_parser(), data))
        assert turn.stop_reason == STOP_END and not turn.message.tool_calls

    def test_end_without_done(self):
        data = b'data: {"choices":[{"delta":{"content":"hi"},"finish_reason":"stop"}]}\n\n'
        turn = turn_of(run(compatible().new_parser(), data))
        assert turn.stop_reason == STOP_END and turn.message.text == "hi"

    def test_cut_and_error_chunk(self):
        assert isinstance(run(compatible().new_parser(), b'data: {"choices":[{"delta":{"content":"hi"}}]}\n\n')[-1],
                          StreamFailure)
        event = run(compatible().new_parser(), b'data: {"error":{"message":"nope"}}\n\n')[0]
        assert isinstance(event, StreamFailure) and event.error.message == "nope"


class TestShared:
    def test_sse_cut_inside_a_character(self):
        data = 'event: a\ndata: é\n\n'.encode()
        decoder = SseDecoder()
        out = []
        for index in range(len(data)):
            out.extend(decoder.feed(data[index:index + 1]))
        assert out == [("a", "é")]

    def test_sse_empty_data_line_is_nothing(self):
        assert SseDecoder().feed(b"data:\n\n") == []

    def test_sse_crlf_multiline_comment_and_no_final_blank_line(self):
        decoder = SseDecoder()
        assert decoder.feed(b": comment\r\ndata: a\r\ndata: b\r\n\r\ndata: c") == [("", "a\nb")]
        assert decoder.flush() == [("", "c")]

    @pytest.mark.parametrize("status,body,kind", [
        (401, b'{"error":{"message":"bad key"}}', "auth"),
        (402, b'{"detail":"free quota used"}', "quota"),
        (400, b'{"error":{"type":"invalid_request_error","message":"Your credit balance is too low"}}', "quota"),
        (429, b'{"error":{"code":"insufficient_quota","message":"You exceeded your current quota"}}', "quota"),
        (429, b'{"error":{"message":"slow down"}}', "rate_limit"),
        (400, b'{"error":{"message":"bad"}}', "bad_request"),
        (529, b"not json", "server"),
    ])
    def test_error_classes(self, status, body, kind):
        assert error_from_response(status, body).kind == kind

    def test_retry_after(self):
        assert error_from_response(429, b"", {"Retry-After": "12"}).retry_after == 12.0

    @pytest.mark.parametrize("url,key,allowed", [
        ("https://api.example.org/v1", "k", True),
        ("http://localhost:11434/v1", "k", True),
        ("http://192.168.1.5:11434/v1", "", True),
        ("http://192.168.1.5:11434/v1", "k", False),
        ("ftp://example.org", "", False),
        ("not a url", "", False),
    ])
    def test_base_url_rule(self, url, key, allowed):
        if allowed:
            check_base_url(url, key)
        else:
            with pytest.raises(ValueError):
                check_base_url(url, key)

    def test_a_relay_token_is_not_sent_in_clear_either(self):
        with pytest.raises(ValueError):
            create_provider(ProviderConfig("anthropic", "m", base_url="http://relay.example.org",
                                           extra_headers={"x-relay": SECRET}))

    @pytest.mark.parametrize("url, shown", [
        ("http://user:secret@gpu.lan:11434/api/tags", "http://gpu.lan:11434/api/tags"),
        ("https://a@b@host/x?q=@#f", "https://host/x?q=@#f"),  # up to the last @ of the address, not of the query
        ("http://u:secret@[::1", "http://[::1"),  # urlsplit refuses it: never shown whole for that
        ("http://localhost:11434/api/tags", "http://localhost:11434/api/tags"),
        ("http://user:pa/ss@gpu.lan:11434", "http://gpu.lan:11434"),  # a generated password holds "/"
        ("http://admin:p@ss/w0rd@gpu.lan/api", "http://gpu.lan/api"),
        ("user:secret@gpu.lan:11434", "gpu.lan:11434"),  # typed without http://
        ("http://host/path@x", "http://x"),  # a path holding "@" is shown short: never a password
        ("not a url", "not a url")])
    def test_an_address_shown_to_the_user_leaves_its_credentials_out(self, url, shown):
        assert without_credentials(url) == shown

    def test_the_refusal_of_an_address_does_not_repeat_its_password(self):
        with pytest.raises(ValueError) as refused:
            check_base_url("ftp://user:secret@host/x", None)
        assert "secret" not in str(refused.value) and "host/x" in str(refused.value)

    def test_key_never_in_repr(self):
        config = ProviderConfig("anthropic", "m", api_key=SECRET, extra_headers={"x-relay": SECRET})
        assert SECRET not in repr(config)
        request = claude().build_request("S", [], [])
        assert SECRET not in repr(request)

    def test_presets_build(self):
        for kind, base_url in PRESETS.values():
            create_provider(ProviderConfig(kind, "m", base_url=base_url))

    @pytest.mark.parametrize("config", [ProviderConfig("anthropic", ""), ProviderConfig("nope", "m"),
                                        ProviderConfig("openai_compatible", "m")])
    def test_bad_config(self, config):
        with pytest.raises(ValueError):
            create_provider(config)
