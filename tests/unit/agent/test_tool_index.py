# -*- coding: utf-8 -*-
"""The one-line summary of each tool, and the index of the tools a conversation may add (token diet, lot 1)."""
import pytest

from core.agent.tool_catalog import ToolSpec, chat_tools
from core.agent.tool_index import INDEX_TITLE, MAX_INDEX, MAX_SUMMARY, SUMMARIES, index_block

pytestmark = pytest.mark.unit


def test_every_tool_of_the_chat_has_a_summary():
    for tool in chat_tools():
        assert tool.summary, tool.name
        assert len(tool.summary) <= MAX_SUMMARY == 60, (tool.name, len(tool.summary))
        assert not tool.summary.endswith(".") and "\n" not in tool.summary, tool.name


def test_no_summary_of_a_tool_that_is_gone():
    assert set(SUMMARIES) <= {tool.name for tool in chat_tools()} | {"use_tools"}


def test_index_lists_the_tools_in_order():
    tools = [ToolSpec("a", "A tool.", summary="Do a"), ToolSpec("b", "B tool.", summary="Do b")]
    assert index_block(tools) == INDEX_TITLE + "\n- a: Do a\n- b: Do b"


def test_index_of_every_tool_stays_small():
    assert len(index_block(chat_tools())) <= MAX_INDEX == 5100  # 4,800 until 2026-11-22: more tools since


def test_no_index_without_tool():
    assert index_block([]) == ""
