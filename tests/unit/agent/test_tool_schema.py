# -*- coding: utf-8 -*-
"""What the model reads of a tool's schema: the plugin keeps the whole one to check a call (token diet, lot 2)."""
import copy
import json

import pytest

from core.agent.json_schema import validate
from core.agent.messages import ROLE_USER, Message, TextPart
from core.agent.providers.anthropic_messages import AnthropicProvider
from core.agent.providers.base import ProviderConfig
from core.agent.providers.ollama_chat import OllamaChatProvider as OllamaProvider
from core.agent.providers.openai_chat import OpenAIChatProvider as OpenAIProvider
from core.agent.tool_catalog import ToolSpec, chat_tools
from core.agent.tool_schema import for_model

pytestmark = pytest.mark.unit

SCHEMA = {"type": "object", "title": "Args", "additionalProperties": False, "required": ["layer"], "properties": {
    "layer": {"type": "string", "title": "Layer", "minLength": 1, "maxLength": 1000, "description": "Layer id or name"},
    "buffer": {"type": "number", "minimum": -10000000.0, "maximum": 10000000.0, "default": 0.0},
    "coverage": {"type": "number", "minimum": 0, "maximum": 100},
    "operator": {"anyOf": [{"enum": ["AND", "OR"], "type": "string"}, {"type": "null"}], "default": None,
                 "description": "Omit to replace"},
    "expression": {"type": "string", "default": "", "maxLength": 2000},
    "classes": {"type": "array", "items": {"type": "integer"}, "default": []},
    "selected_only": {"type": "boolean", "default": True},
    "predicates": {"type": "array", "items": {"enum": ["Intersect", "Touch"], "type": "string"},
                   "default": ["Intersect"], "maxItems": 8},
    "title": {"type": "string", "description": "a property named title stays"}}}


def test_bounds_and_titles_go():
    light = for_model(SCHEMA)
    assert "title" not in light and "additionalProperties" not in light
    assert light["properties"]["layer"] == {"type": "string", "description": "Layer id or name"}
    assert light["properties"]["buffer"] == {"type": "number", "default": 0.0}
    assert light["properties"]["coverage"] == {"type": "number", "minimum": 0, "maximum": 100}
    assert light["properties"]["title"] == {"type": "string", "description": "a property named title stays"}


def test_a_null_option_shows_as_its_type():
    assert for_model(SCHEMA)["properties"]["operator"] == {"enum": ["AND", "OR"], "type": "string",
                                                         "description": "Omit to replace"}
    assert validate({"layer": "a", "operator": None}, SCHEMA) == []  # a null still passes the whole schema


def test_defaults_that_guide_stay():
    properties = for_model(SCHEMA)["properties"]
    assert properties["selected_only"]["default"] is True and properties["predicates"]["default"] == ["Intersect"]
    assert "default" not in properties["expression"] and "default" not in properties["classes"]


def test_the_input_is_not_changed():
    before = copy.deepcopy(SCHEMA)
    for_model(SCHEMA)
    assert SCHEMA == before


def test_a_value_is_never_read_as_a_schema():
    schema = {"type": "object", "properties": {"style": {"type": "object", "default": {"title": "x", "maxLength": 3}},
                                               "kind": {"const": {"title": "y"}}}}
    properties = for_model(schema)["properties"]
    assert properties["style"]["default"] == {"title": "x", "maxLength": 3} and properties["kind"]["const"] == {"title": "y"}


def test_the_full_schema_still_validates():
    assert validate({"layer": "a" * 1001}, SCHEMA) and validate({"layer": "a", "predicates": ["Touch"] * 9}, SCHEMA)


def test_an_external_schema_goes_through():
    schema = {"type": "object", "required": ["maxItems"], "properties": {
        "maxItems": {"type": "integer", "maximum": 9}, "odd": {"anyOf": [{"type": "null"}, {"type": "null"}]}},
        "$defs": {"minLength": {"type": "string", "maxLength": 3}}}
    assert for_model(schema) == {"type": "object", "required": ["maxItems"], "properties": {
        "maxItems": {"type": "integer", "maximum": 9}, "odd": {"anyOf": [{"type": "null"}, {"type": "null"}]}},
        "$defs": {"minLength": {"type": "string"}}}


@pytest.mark.parametrize("provider, kind", [(AnthropicProvider, "anthropic"), (OpenAIProvider, "openai"),
                                            (OllamaProvider, "ollama")])
def test_each_provider_sends_the_light_form(provider, kind):
    config = ProviderConfig(kind=kind, model="m", base_url="http://localhost:11434" if kind == "ollama"
                            else ("https://api.openai.com/v1" if kind == "openai" else ""), api_key="k")
    tool = ToolSpec(name="t", description="d", input_schema=SCHEMA)
    body = json.loads(provider(config).build_request("s", [Message(ROLE_USER, (TextPart("hi"),))], [tool]).body)
    sent = body["tools"][0].get("input_schema") or body["tools"][0]["function"]["parameters"]
    assert sent == for_model(SCHEMA)


def test_every_chat_tool_goes_lighter():
    tools = chat_tools()
    before = sum(len(json.dumps(tool.input_schema)) for tool in tools)
    after = sum(len(json.dumps(for_model(tool.input_schema))) for tool in tools)
    assert after < before * 0.9
