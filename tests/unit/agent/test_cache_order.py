# -*- coding: utf-8 -*-
"""The start of a request stays the same for the prompt cache of each provider (token diet, lot 4, 2026-11-16)."""
import json

import pytest

from core.agent.chat_setup import SETTING_TOOLS, chat_instructions, stable_order
from core.agent.messages import ROLE_USER, Message, TextPart
from core.agent.providers.anthropic_messages import AnthropicProvider
from core.agent.providers.base import ProviderConfig
from core.agent.providers.ollama_chat import CONTEXT_STEPS, OllamaChatProvider
from core.agent.session import AgentSession
from core.agent.sources import BUILT_IN
from core.agent.system_prompt import SYSTEM_PROMPT
from core.agent.tool_catalog import ToolSpec, chat_tools
from core.agent.tool_index import index_block

pytestmark = pytest.mark.unit


def hello(text="hi"):
    return [Message(ROLE_USER, (TextPart(text),))]


def test_what_a_setting_says_comes_after_the_index():
    """The way of working and the index first: two conversations of other sources start alike up to there."""
    index = [tool for tool in chat_tools() if tool.name not in SETTING_TOOLS][:5]
    plain = chat_instructions([], available=index)
    every = chat_instructions(list(BUILT_IN), available=index)
    start = SYSTEM_PROMPT + index_block(index)
    assert plain.startswith(start) and every.startswith(start) and plain != every


def test_the_tools_a_setting_brings_come_last():
    tools = chat_tools()
    ordered = stable_order(tools)
    names = [tool.name for tool in ordered]
    assert sorted(names) == sorted(tool.name for tool in tools)
    first_setting = next(i for i, name in enumerate(names) if name in SETTING_TOOLS)
    assert all(name in SETTING_TOOLS for name in names[first_setting:])
    kept = [tool.name for tool in tools if tool.name not in SETTING_TOOLS]
    assert names[:len(kept)] == kept  # the others keep their order


def test_ticking_a_source_does_not_move_the_tools_before_it():
    tools = chat_tools()
    without = stable_order([tool for tool in tools if tool.name not in SETTING_TOOLS])
    with_place = stable_order([tool for tool in tools if tool.name not in SETTING_TOOLS or tool.name == "find_place"])
    assert [tool.name for tool in with_place][:len(without)] == [tool.name for tool in without]


def test_a_tool_added_goes_at_the_end():
    a, b, c = (ToolSpec(name, name, {"type": "object", "properties": {}}) for name in "abc")
    session = AgentSession(provider=None, tools=[a, b], system="S", core={"a", "b"})
    session.offer([c, a])
    assert session.tool_names == ("a", "b", "c")


def test_anthropic_reads_the_tools_and_the_instructions_again():
    """Two breakpoints of the same TTL: the instructions (after the tools) and the end of the request."""
    provider = AnthropicProvider(ProviderConfig(kind="anthropic", model="m", base_url="", api_key="k"))
    body = json.loads(provider.build_request("SYS", hello(), []).body)
    assert body["cache_control"] == {"type": "ephemeral"}
    assert body["system"][-1]["cache_control"] == {"type": "ephemeral"}
    assert json.dumps(body).count('"cache_control"') == 2  # 4 at most


def test_ollama_never_asks_a_smaller_context_in_a_conversation():
    provider = OllamaChatProvider(ProviderConfig(kind="ollama", model="m", base_url="http://localhost:11434",
                                                 api_key=""))

    def num_ctx(text):
        return json.loads(provider.build_request("S", hello(text), []).body)["options"]["num_ctx"]

    assert num_ctx("short") == CONTEXT_STEPS[0]
    assert num_ctx("x" * 80_000) == CONTEXT_STEPS[1]
    assert num_ctx("short again, after a compaction") == CONTEXT_STEPS[1]  # no reload of the model
    fresh = OllamaChatProvider(ProviderConfig(kind="ollama", model="m", base_url="http://localhost:11434", api_key=""))
    assert json.loads(fresh.build_request("S", hello(), []).body)["options"]["num_ctx"] == CONTEXT_STEPS[0]
