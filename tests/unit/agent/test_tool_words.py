# -*- coding: utf-8 -*-
"""Words of the tools that a shorter wording lost (review of the token diet, 2026-11-16), each one a way for the
model to do the wrong thing:

- preview_filter read "Try what apply_filter would do", while it has no operator: for "among them" the model
  passes AND with the new condition alone, previews that condition on the whole layer and tells a wrong count;
- the operator of apply_filter no longer said what OR and AND NOT do;
- the crs of add_osm_features no longer said that an empty one is the CRS of the map: an extent read from
  map_context was sent as EPSG:4326, the only value named.
"""
import pytest

from core.agent.tool_catalog import chat_tools

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def tools():
    return {tool.name: tool for tool in chat_tools()}


def test_preview_filter_says_it_tries_the_expression_alone(tools):
    described = tools["preview_filter"].description
    assert "never combined with its filter" in described
    assert "what apply_filter would do" not in described
    assert "operator" not in tools["preview_filter"].input_schema["properties"]  # the day it takes one, say so


def test_the_operator_of_apply_filter_says_what_each_one_does(tools):
    described = tools["apply_filter"].input_schema["properties"]["operator"]["description"]
    for words in ("AND narrows", "OR widens", "AND NOT takes the condition out", "omit to replace"):
        assert words in described, words


def test_the_extents_of_the_sources_say_which_crs_an_empty_one_is(tools):
    for name in ("add_osm_features", "add_elevation", "add_population"):
        described = tools[name].input_schema["properties"]["crs"]["description"]
        assert "EPSG:4326 for find_place" in described and "the CRS of the map when empty" in described, name
