# -*- coding: utf-8 -*-
"""The measuring bench of the token diet (scripts/agent_request_weight.py): what each request of a conversation sends,
and the start of it the cache of each provider can serve. No network."""
import importlib.util
import json
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
