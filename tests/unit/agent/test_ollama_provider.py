# -*- coding: utf-8 -*-
"""Ollama's own /api/chat format: the context size it asks for, and lines of JSON put back together."""
import json

import pytest

from core.agent.messages import (
    ROLE_ASSISTANT, ROLE_USER, STOP_END, STOP_MAX_TOKENS, STOP_TOOL_USE, Message, StreamFailure, TextDelta, TextPart,
    ToolCallPart, ToolResultPart, TurnComplete,
)
from core.agent.providers import KIND_OLLAMA, PRESETS, create_provider
from core.agent.providers.base import ProviderConfig
from core.agent.providers.ollama_chat import CONTEXT_STEPS, context_for, native_base
from core.agent.tool_catalog import FILTERING_NOTE, FILTERING_TOOLS, ToolSpec, chat_tools, filtering_only
from core.agent.system_prompt import SYSTEM_PROMPT

pytestmark = pytest.mark.unit

TOOL = ToolSpec("list_layers", "List the layers.", {"type": "object", "properties": {}})


def ollama(base_url="http://localhost:11434", **kwargs):
    return create_provider(ProviderConfig(KIND_OLLAMA, "qwen3:8b", base_url=base_url, **kwargs))


def lines(*payloads):
    return "".join(json.dumps(payload, ensure_ascii=False) + "\n" for payload in payloads).encode()


def run(parser, data, step=None):
    events = []
    step = step or len(data)
    for start in range(0, len(data), step):
        events.extend(parser.feed(data[start:start + step]))
    return events + parser.close()


def turn_of(events):
    return next(event for event in events if isinstance(event, TurnComplete))


TOOL_TURN = lines(
    {"model": "m", "message": {"role": "assistant", "content": "", "thinking": "je réfléchis"}, "done": False},
    {"model": "m", "message": {"role": "assistant", "content": "Je regarde é"}, "done": False},
    {"model": "m", "message": {"role": "assistant", "content": "", "tool_calls": [
        {"function": {"name": "apply_filter", "arguments": {"layer_name": "communes", "expression": "\"pop\" > 1"}}},
        {"function": {"name": "zoom_to", "arguments": "{\"layer\": \"communes\"}"}}]}, "done": False},
    {"model": "m", "message": {"role": "assistant", "content": ""}, "done": True, "done_reason": "stop",
     "prompt_eval_count": 18000, "eval_count": 42},
)


class TestRequest:
    def test_the_preset_is_the_native_api(self):
        kind, base_url = PRESETS["ollama"]
        assert kind == KIND_OLLAMA and base_url == "http://localhost:11434"

    def test_body_asks_for_enough_context(self):
        request = ollama().build_request("S", [Message(ROLE_USER, (TextPart("bonjour"),))], [TOOL])
        body = json.loads(request.body)
        assert request.url == "http://localhost:11434/api/chat"
        assert body["model"] == "qwen3:8b" and body["stream"] is True
        assert body["messages"] == [{"role": "system", "content": "S"}, {"role": "user", "content": "bonjour"}]
        assert body["tools"][0]["function"]["name"] == "list_layers"
        assert body["options"] == {"num_ctx": CONTEXT_STEPS[0]}
        assert "authorization" not in request.headers

    def test_every_tool_asks_for_32k_the_filtering_ones_for_16k(self):
        """The system prompt and every tool of the chat: about 73,000 characters, well past Ollama's 4096 tokens."""
        hello = [Message(ROLE_USER, (TextPart("bonjour"),))]
        request = ollama().build_request(SYSTEM_PROMPT, hello, chat_tools())
        assert len(request.body) > 60_000
        assert json.loads(request.body)["options"]["num_ctx"] == 32_768
        request = ollama().build_request(SYSTEM_PROMPT + FILTERING_NOTE, hello, filtering_only(chat_tools()))
        assert json.loads(request.body)["options"]["num_ctx"] == 16_384

    def test_the_filtering_tools_are_tools_of_the_chat_that_read_and_filter(self):
        names = {tool.name for tool in chat_tools()}
        assert FILTERING_TOOLS <= names
        kept = filtering_only(chat_tools())
        assert {tool.name for tool in kept} == FILTERING_TOOLS
        for missing in ("run_algorithm", "set_layer_style", "update_features", "remove_layers", "run_pyqgis",
                        "create_widget", "add_layer"):
            assert missing not in FILTERING_TOOLS
        assert "every tool" in FILTERING_NOTE

    def test_context_steps(self):
        assert CONTEXT_STEPS == (16_384, 32_768, 65_536)
        assert context_for(1_000) == CONTEXT_STEPS[0]
        assert context_for(75_000) == CONTEXT_STEPS[1]
        assert context_for(10_000_000) == CONTEXT_STEPS[-1]

    @pytest.mark.parametrize("url, base", [
        ("http://localhost:11434/v1", "http://localhost:11434"), ("http://localhost:11434/v1/", "http://localhost:11434"),
        ("http://localhost:11434", "http://localhost:11434"), ("http://gpu.lan:11434/", "http://gpu.lan:11434")])
    def test_an_address_of_the_openai_endpoint_still_works(self, url, base):
        assert native_base(url) == base
        assert ollama(base_url=url).build_request("S", [], []).url == base + "/api/chat"

    def test_history_round_trip(self):
        call = ToolCallPart("call_0", "apply_filter", {"layer_name": "c", "expression": "a = 1"})
        messages = [Message(ROLE_USER, (TextPart("filtre"),)), Message(ROLE_ASSISTANT, (TextPart("ok"), call)),
                    Message(ROLE_USER, (ToolResultPart("call_0", "{\"kept\": 3}", images=(("image/png", "AAA"),)),))]
        wire = json.loads(ollama().build_request("S", messages, []).body)["messages"]
        assert wire[2] == {"role": "assistant", "content": "ok", "tool_calls": [
            {"function": {"name": "apply_filter", "arguments": {"layer_name": "c", "expression": "a = 1"}}}]}
        assert wire[3] == {"role": "tool", "tool_name": "apply_filter", "content": "{\"kept\": 3}"}
        assert wire[4]["role"] == "user" and wire[4]["images"] == ["AAA"]

    def test_a_key_needs_https_off_this_machine(self):
        with pytest.raises(ValueError):
            ollama(base_url="http://gpu.lan:11434", api_key="k")
        assert ollama(base_url="http://localhost:11434", api_key="k").build_request("S", [], []).headers[
            "authorization"] == "Bearer k"


class TestStream:
    @pytest.mark.parametrize("step", [None, 1, 7, 64])
    def test_turn_rebuilt_at_any_chunking(self, step):
        events = run(ollama().new_parser(), TOOL_TURN, step)
        turn = turn_of(events)
        assert "".join(event.text for event in events if isinstance(event, TextDelta)) == "Je regarde é"
        assert turn.stop_reason == STOP_TOOL_USE
        calls = turn.message.tool_calls
        assert [call.name for call in calls] == ["apply_filter", "zoom_to"]
        assert calls[1].arguments == {"layer": "communes"} and calls[0].call_id != calls[1].call_id
        assert turn.usage.input_tokens == 18000 and turn.usage.output_tokens == 42
        assert "réfléchis" not in turn.message.text  # the thoughts are not the answer

    def test_text_answer_and_length(self):
        done = {"message": {"role": "assistant", "content": "fini"}, "done": True, "done_reason": "stop"}
        assert turn_of(run(ollama().new_parser(), lines(done))).stop_reason == STOP_END
        done["done_reason"] = "length"
        assert turn_of(run(ollama().new_parser(), lines(done))).stop_reason == STOP_MAX_TOKENS

    def test_bad_calls_are_reported_or_dropped(self):
        events = run(ollama().new_parser(), lines({"message": {"content": "", "tool_calls": [
            {"function": {"name": "", "arguments": {}}}, {"function": {"name": "x", "arguments": "{bad"}},
            {"function": {"name": "y", "arguments": [1]}}, "odd"]}, "done": True}))
        calls = turn_of(events).message.tool_calls
        assert [call.name for call in calls] == ["x", "y"] and all(call.parse_error for call in calls)

    @pytest.mark.parametrize("data", [
        b'{"message": {"content": "a"}, "done": false}\n',  # cut before done
        b'{"error": "model \\"qwen3\\" not found, try pulling it first"}\n',
        b'not json\n',
        b'{"message": {"content": ""}, "done": true}\n',  # empty
    ])
    def test_failures(self, data):
        events = run(ollama().new_parser(), data)
        assert any(isinstance(event, StreamFailure) for event in events)
        assert not any(isinstance(event, TurnComplete) for event in events)

    def test_a_turn_that_only_thought_ends_the_request(self):
        data = lines({"message": {"content": "", "thinking": "rien à ajouter"}, "done": False},
                     {"message": {"content": ""}, "done": True, "done_reason": "stop"})
        turn = turn_of(run(ollama().new_parser(), data))
        assert turn.stop_reason == STOP_END and turn.message.parts == ()

    def test_last_line_without_newline(self):
        data = lines({"message": {"content": "ok"}, "done": True}).rstrip(b"\n")
        assert turn_of(run(ollama().new_parser(), data)).message.text == "ok"
