# -*- coding: utf-8 -*-
"""An image in a tool result: how each provider sends it, and that it goes with its own request only."""
import json

import pytest

from core.agent.messages import ROLE_ASSISTANT, ROLE_USER, ImageData, Message, TextPart, ToolCallPart, ToolResultPart
from core.agent.providers import create_provider
from core.agent.providers.base import ProviderConfig
from core.agent.session import IMAGE_GONE, AgentSession
from core.agent.tool_catalog import VIEW_MAP, ToolSpec, chat_tools
from core.agent.tool_executor import ImageAnswer, ToolExecutor

pytestmark = pytest.mark.unit

IMAGE = ImageData("image/jpeg", "AAAA")
LOOK = ToolSpec(name="look", description="Look", input_schema={"type": "object", "properties": {}}, read_only=True)


def conversation():
    return [Message(ROLE_USER, (TextPart("montre la carte"),)),
            Message(ROLE_ASSISTANT, (ToolCallPart("c1", "look", {}),)),
            Message(ROLE_USER, (ToolResultPart("c1", '{"width": 1024}', images=(IMAGE,)),))]


def body(preset, messages, base_url=""):
    kind = {"openai": "openai_compatible"}.get(preset, preset)
    provider = create_provider(ProviderConfig(kind, "m", base_url=base_url, api_key="k"))
    return json.loads(provider.build_request("S", messages, [LOOK]).body)


def test_claude_gets_the_image_in_the_tool_result():
    result = body("anthropic", conversation())["messages"][-1]["content"][0]
    assert result["type"] == "tool_result" and result["content"] == [
        {"type": "text", "text": '{"width": 1024}'},
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "AAAA"}}]


def test_an_openai_server_gets_it_in_a_user_message_after_the_tool_message():
    messages = body("openai", conversation(), "https://api.openai.com/v1")["messages"]
    assert messages[-2] == {"role": "tool", "tool_call_id": "c1", "content": '{"width": 1024}'}
    assert messages[-1]["role"] == "user" and messages[-1]["content"][1] == {
        "type": "image_url", "image_url": {"url": "data:image/jpeg;base64,AAAA"}}


def test_a_result_without_image_is_sent_as_before():
    plain = [Message(ROLE_USER, (TextPart("x"),)), Message(ROLE_ASSISTANT, (ToolCallPart("c1", "look", {}),)),
             Message(ROLE_USER, (ToolResultPart("c1", "{}"),))]
    assert body("anthropic", plain)["messages"][-1]["content"][0]["content"] == "{}"
    assert body("openai", plain, "https://api.openai.com/v1")["messages"][-1]["role"] == "tool"


def test_a_handler_answers_with_an_image():
    executor = ToolExecutor([LOOK], {"look": lambda args: ImageAnswer({"width": 512}, IMAGE)})
    result = executor.execute(ToolCallPart("c1", "look", {}))
    assert not result.is_error and json.loads(result.content) == {"width": 512} and result.images == (IMAGE,)


def test_an_image_goes_with_its_own_request_only():
    session = AgentSession(create_provider(ProviderConfig("anthropic", "m")), [LOOK], "S")
    session._messages.extend(conversation())
    first = json.loads(session.next_request().body)["messages"][-1]["content"][0]["content"]
    assert isinstance(first, list)  # sent while the request it belongs to goes on
    session.add_user_text("et maintenant ?")
    result = session.messages[2].parts[0]
    assert result.images == () and result.content.endswith(IMAGE_GONE)
    assert "AAAA" not in session.next_request().body.decode("utf-8") if isinstance(session.next_request().body, bytes) \
        else "AAAA" not in session.next_request().body


def test_view_map_belongs_to_the_chat_and_only_reads():
    tool = {item.name: item for item in chat_tools()}[VIEW_MAP]
    assert tool.chat_only and tool.read_only and not tool.requires_confirmation
    assert tool.input_schema["properties"]["width"]["maximum"] == 1568
