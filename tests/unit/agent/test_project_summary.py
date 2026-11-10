# -*- coding: utf-8 -*-
import json

import pytest

from core.agent.project_summary import HEADER, MAX_LAYERS, project_summary
from core.agent.providers import create_provider
from core.agent.providers.base import ProviderConfig
from core.agent.session import AgentSession

pytestmark = pytest.mark.unit


def test_layers_counts_filters_and_selection():
    text = project_summary([{"name": "communes", "layer_kind": "vector", "feature_count": 586,
                             "active_filter_expression": '"population" > 10000'},
                            {"name": "MNT", "layer_kind": "raster", "feature_count": -1}],
                           [{"name": "routes", "selected_count": 3}])
    assert text.splitlines() == [HEADER, '- communes (vector, 586 features, filter: "population" > 10000)',
                                 "- MNT (raster)", "Selected: routes (3)"]


def test_bounded():
    rows = [{"name": f"l{n}", "layer_kind": "vector", "active_filter_expression": "x" * 500} for n in range(80)]
    text = project_summary(rows)
    assert f"and {80 - MAX_LAYERS} more layers" in text and len(text) < 6000 and "Selected: nothing" in text


def test_no_layer_no_summary():
    assert project_summary([]) == ""


def test_the_summary_follows_the_request_in_its_message():
    session = AgentSession(create_provider(ProviderConfig("anthropic", "m")), [], "S")
    session.add_user_text("garde les communes", "Project when...")
    content = json.loads(session.next_request().body)["messages"][-1]["content"]
    assert [block["text"] for block in content] == ["garde les communes", "Project when..."]
    session.add_user_text("encore")
    assert len(session.messages[-1].parts) == 1  # no context, no empty block
