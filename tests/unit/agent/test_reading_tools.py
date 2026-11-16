# -*- coding: utf-8 -*-
"""The reading tools return less by default, and say what they left out (token diet, lot 3, 2026-11-16)."""
import pytest

from core.agent.field_rows import field_row
from core.agent.tool_catalog import chat_tools

pytestmark = pytest.mark.unit


def test_describe_layer_writes_alias_and_filterable_only_when_they_say_something():
    assert field_row("nom", "String", "", True) == {"name": "nom", "type": "String"}
    assert field_row("pop", "Integer", "Population", True) == {"name": "pop", "type": "Integer", "alias": "Population"}
    assert field_row("double_pop", "Real", "", False) == {"name": "double_pop", "type": "Real", "filterable": False}


@pytest.mark.parametrize("name, default", [("field_values", 20), ("layer_statistics", 10), ("sample_features", 3)])
def test_the_reading_tools_return_less_by_default(name, default):
    tool = next(tool for tool in chat_tools() if tool.name == name)
    assert tool.input_schema["properties"]["limit"]["default"] == default
