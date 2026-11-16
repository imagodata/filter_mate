# -*- coding: utf-8 -*-
"""The measuring bench of the token diet (scripts/agent_request_weight.py): what each request of a conversation sends,
and the start of it the cache of each provider can serve. No network."""
import importlib.util
import json
import socket
import sys
from pathlib import Path

import pytest

from core.agent.messages import ROLE_USER, Message, TextPart
from core.agent.tool_catalog import chat_tools

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def weight():
    spec = importlib.util.spec_from_file_location("agent_request_weight", ROOT / "scripts" / "agent_request_weight.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["agent_request_weight"] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop("agent_request_weight", None)


def user(text):
    return Message(ROLE_USER, (TextPart(text),))


TOOLS = chat_tools()[:2]


def test_common_prefix_counts_characters(weight):
    assert weight.common_prefix("département 31", "département 32") == 13


@pytest.mark.parametrize("kind", ["anthropic", "openai", "ollama"])
def test_cache_order_puts_the_tools_first(weight, kind):
    body = json.loads(weight.providers()[kind].build_request("sys", [user("é")], TOOLS).body)
    tools = json.dumps(body["tools"], ensure_ascii=False, separators=(",", ":"))
    assert weight.cache_order(kind, body).startswith(tools)


def test_ollama_prefix_is_lost_when_the_context_step_changes(weight):
    before = {"tools": [], "messages": [{"role": "user", "content": "a"}], "options": {"num_ctx": 16384}}
    after = dict(before, options={"num_ctx": 32768})
    assert weight.cached_prefix("ollama", before, after) == 0
    assert weight.cached_prefix("openai", before, after) > 0
    assert weight.cached_prefix("ollama", None, before) == 0


def test_estimated_cost(weight):
    first = weight.CallWeight(1, 400, 500, 100, 3, {"anthropic": 0, "openai": 0, "ollama": 0}, 16384)
    second = weight.CallWeight(1, 400, 500, 100, 3, {"anthropic": 900, "openai": 900, "ollama": 900}, 16384)
    assert first.sent == 1000
    assert weight.estimated_cost([first, second]) == pytest.approx(1250 + 90 + 125)


def test_conversation_runs_offline_and_cleanly(weight, monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("network")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    run = weight.replay()
    assert run.errors == []
    assert sorted({call.request for call in run.calls}) == list(range(1, 11))
    assert run.skills_loaded == ["cartography"]
    assert all(value == 0 for value in run.calls[0].prefix.values())


def test_within_a_request_the_whole_start_is_shared(weight):
    calls = weight.replay().calls
    compared = 0
    for before, after in zip(calls, calls[1:]):
        if after.request == before.request and after.tool_count == before.tool_count:
            assert after.prefix["anthropic"] == before.sent - 1  # all of the call before but the "]" of its messages
            compared += 1
    assert compared


def test_main_conversation_without_reference(weight, monkeypatch, capsys):
    monkeypatch.setattr(weight, "REFERENCE", None)
    assert weight.main(["--conversation"]) == 0
    assert "estimated cost" in capsys.readouterr().out


def test_a_reference_of_another_conversation_is_refused(weight, monkeypatch, capsys):
    monkeypatch.setattr(weight, "REFERENCE", {"fingerprint": "000000000000", "cost": 1e12, "largest": 10 ** 9})
    assert weight.main(["--conversation"]) == 1
    assert "another conversation" in capsys.readouterr().out


def test_a_rise_past_five_percent_fails(weight, monkeypatch):
    run = weight.replay()
    cost = weight.estimated_cost(run.calls)
    largest = max(call.sent for call in run.calls)
    reference = {"fingerprint": weight.fingerprint(), "cost": cost / 1.06, "largest": largest}
    monkeypatch.setattr(weight, "REFERENCE", reference)
    assert weight.main(["--conversation"]) == 1
    monkeypatch.setattr(weight, "REFERENCE", dict(reference, cost=cost / 1.04))
    assert weight.main(["--conversation"]) == 0
