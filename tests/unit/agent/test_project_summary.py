# -*- coding: utf-8 -*-
import json

import pytest

from core.agent.project_summary import (
    CHANGES_HEADER, HEADER, MAX_LAYERS, project_changes, project_state, project_summary)
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


VIEW = {"available": True, "project_crs": "EPSG:2154", "canvas_crs": "EPSG:2154", "scale": 24999.6,
        "extent": [569000.4, 6270000.0, 580000.0, 6280000.2], "active_layer_name": "communes"}


def test_the_map_and_the_place_of_each_layer():
    text = project_summary([{"name": "communes", "layer_kind": "vector", "feature_count": 586, "crs_authid": "EPSG:2154"},
                            {"name": "ortho", "layer_kind": "raster", "crs_authid": "EPSG:4326", "group": "Fonds",
                             "visible": False}], view=VIEW)
    assert text.splitlines()[1:4] == [
        "Map: CRS EPSG:2154, scale 1:25000, visible extent xmin ymin xmax ymax = 569000 6270000 580000 6280000, "
        "active layer: communes",
        "- communes (vector, 586 features)", "- ortho (raster, EPSG:4326, group: Fonds, hidden)"]


def test_a_view_in_degrees_keeps_its_decimals_and_names_its_crs():
    view = {**VIEW, "canvas_crs": "EPSG:4326", "extent": [1.3, 43.5, 1.5, 43.7]}
    line = project_summary([{"name": "a"}], view=view).splitlines()[1]
    assert "visible extent (EPSG:4326) xmin ymin xmax ymax = 1.30000 43.50000 1.50000 43.70000" in line


def test_without_a_canvas_only_the_crs():
    text = project_summary([{"name": "a"}], view={"available": False, "project_crs": "EPSG:2154",
                                                  "extent": [0, 0, 1, 1], "scale": 5.0})
    assert text.splitlines()[1] == "Map: CRS EPSG:2154"
    assert "Map:" not in project_summary([{"name": "a"}], view={"available": False})
    bad = project_summary([{"name": "a"}], view={**VIEW, "extent": [0, float("nan"), 1, 1], "scale": float("inf")})
    assert bad.splitlines()[1] == "Map: CRS EPSG:2154, active layer: communes"


def _rows(**changes):
    rows = {"c": {"layer_id": "c", "name": "communes", "active_filter_expression": ""},
            "r": {"layer_id": "r", "name": "routes", "active_filter_expression": '"type" = 1'},
            "o": {"layer_id": "o", "name": "ortho", "visible": False}}
    for key, change in changes.items():
        rows[key] = None if change is None else {**rows.get(key, {"layer_id": key, "name": key}), **change}
    return [row for row in rows.values() if row is not None]


def test_what_changed_since_the_last_answer():
    before = project_state(_rows(), [{"layer_id": "c", "name": "communes", "selected_count": 3},
                                     {"layer_id": "r", "name": "routes", "selected_count": 1}], VIEW)
    rows = _rows(c={"active_filter_expression": '"pop" > 5'}, r={"active_filter_expression": ""},
                 o={"visible": True}, n={"name": "bati"})
    selections = [{"layer_id": "c", "name": "communes", "selected_count": 7}]
    view = {**VIEW, "active_layer_name": "routes", "extent": [569000.4, 6270000.0, 590000.0, 6280000.2]}
    assert project_changes(before, project_state(rows, selections, view)) == [
        "- layers added: bati", "- filter changed: communes", "- filter removed: routes", "- now shown: ortho",
        "- selection changed: communes (7 selected)", "- selection cleared: routes", "- active layer is now: routes",
        "- the map view moved"]
    text = project_summary(rows, selections, view, before=before)
    assert text.splitlines()[-9] == CHANGES_HEADER and text.endswith("- the map view moved")


def test_nothing_changed_nothing_said():
    before = project_state(_rows(), [], VIEW)
    assert project_changes(before, project_state(_rows(), [], dict(VIEW))) == []
    assert CHANGES_HEADER not in project_summary(_rows(), [], VIEW, before=before)
    # a removed layer is said once, not again as a selection cleared
    gone = project_changes(project_state(_rows(), [{"layer_id": "r", "name": "routes", "selected_count": 1}], VIEW),
                           project_state(_rows(r=None), [], VIEW))
    assert gone == ["- layers removed: routes"]


def test_changes_are_bounded():
    before = project_state([{"layer_id": str(n), "name": f"l{n}"} for n in range(40)])
    lines = project_changes(before, project_state([{"layer_id": "x", "name": "x"}]))
    assert lines == ["- layers added: x", "- layers removed: l0, l1, l2, l3, l4 and 35 more"]
