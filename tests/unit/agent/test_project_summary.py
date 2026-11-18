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


def test_objects_drawn_in_the_dock_get_a_line():
    view = {"drawn_objects": [{"name": "ortho", "count": 4}, {"name": "empty", "count": 0}, "not a row"]}
    text = project_summary([{"name": "ortho", "layer_kind": "raster"}], [], view)
    assert text.splitlines()[-1] == "Objects drawn in the dock: ortho (4)"
    assert "Objects drawn" not in project_summary([{"name": "ortho", "layer_kind": "raster"}])
    # before what changed since the last answer, which stays last
    before = project_state([{"layer_id": "o", "name": "ortho"}])
    lines = project_summary([{"layer_id": "o", "name": "ortho"}, {"layer_id": "n", "name": "bati"}], [], view,
                            before=before).splitlines()
    assert lines[-3:] == ["Objects drawn in the dock: ortho (4)", CHANGES_HEADER, "- layers added: bati"]


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
        "- the map view moved: visible extent xmin ymin xmax ymax = 569000 6270000 590000 6280000"]
    text = project_summary(rows, selections, view, before=before)
    assert text.splitlines()[-9] == CHANGES_HEADER and text.endswith("6270000 590000 6280000")


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


def test_the_fields_of_the_active_layer_are_said():
    """The quality gate of the token diet (2026-11-17): without them, qwen3:8b guessed "dep" for the field "dept"."""
    view = {**VIEW, "active_fields": ["nom", "insee", "population", "dept"]}
    text = project_summary(_rows(), [], view)
    assert "Fields of the active layer: nom, insee, population, dept" in text.splitlines()
    assert "Fields of the active layer" not in project_summary(_rows(), [], VIEW)


def test_many_fields_are_bounded():
    from core.agent.project_summary import MAX_FIELDS
    view = {**VIEW, "active_fields": [f"f{index}" for index in range(MAX_FIELDS + 7)]}
    line = next(line for line in project_summary(_rows(), [], view).splitlines() if line.startswith("Fields"))
    assert line.endswith("and 7 more") and f"f{MAX_FIELDS - 1}," not in line.split(", ")[-1]


def test_another_active_layer_comes_with_its_fields():
    before = project_state(_rows(), [], {**VIEW, "active_fields": ["nom"]})
    after = project_state(_rows(), [], {**VIEW, "active_layer_name": "routes", "active_fields": ["type", "nom"]})
    assert project_changes(before, after) == ["- active layer is now: routes (fields: type, nom)"]
    same = project_state(_rows(), [], {**VIEW, "active_fields": ["nom"]})
    assert project_changes(before, same) == []  # the same layer, the same fields: nothing to say


# The audit of 2026-11-18: what the full state showed and the update did not say, so the model went on with the
# first state it had read (a name, a CRS, coordinates, a field that is no more).
def _state(rows=None, **view):
    return project_state(rows if rows is not None else _rows(), [], {**VIEW, **view})


def test_a_renamed_layer_is_said_by_its_old_and_new_name():
    renamed = _rows(c={"name": "villages"})
    assert project_changes(_state(), _state(renamed)) == ["- layers renamed: communes -> villages"]
    # the active layer renamed is one layer: said once, not as another active layer
    before = _state(active_layer_id="c")
    after = _state(renamed, active_layer_id="c", active_layer_name="villages")
    assert project_changes(before, after) == ["- layers renamed: communes -> villages"]


def test_a_new_project_crs_is_said_and_so_is_a_canvas_in_another_crs():
    assert project_changes(_state(), _state(project_crs="EPSG:4326", canvas_crs="EPSG:4326")) == [
        "- project CRS is now: EPSG:4326"]
    assert project_changes(_state(), _state(canvas_crs="EPSG:3857")) == ["- map canvas CRS is now: EPSG:3857"]
    assert project_changes(_state(), _state()) == []
    # no CRS read at one end: nothing to compare
    assert not any("CRS" in line for line in project_changes(project_state(_rows(), [], {}), _state()))


def test_the_new_view_comes_with_its_coordinates():
    lines = project_changes(_state(), _state(extent=[1.0, 43.0, 2.5, 44.25], project_crs="EPSG:4326",
                                             canvas_crs="EPSG:4326"))
    assert lines == ["- project CRS is now: EPSG:4326",
                     "- the map view moved: visible extent xmin ymin xmax ymax = 1.00000 43.00000 2.50000 44.25000"]
    other = project_changes(_state(), _state(extent=[0.0, 0.0, 10.0, 10.0], canvas_crs="EPSG:4326"))
    assert other[-1].startswith("- the map view moved: visible extent (EPSG:4326) xmin")


def test_an_active_layer_cleared_is_said():
    assert project_changes(_state(), _state(active_layer_name="")) == ["- no active layer now"]
    assert project_changes(_state(active_layer_name=""), _state(active_layer_name="")) == []


def test_fields_added_or_removed_on_the_active_layer_are_said():
    before = _state(active_fields=["nom", "pop"])
    assert project_changes(before, _state(active_fields=["nom", "pop", "dept"])) == [
        "- fields of the active layer are now: nom, pop, dept"]


def test_the_update_after_a_rename_and_a_new_crs_says_both():
    """The scenario of the audit: roads renamed streets, the project passed to EPSG:4326, parcels added."""
    from core.agent.project_summary import project_update
    before = project_state([{"layer_id": "a", "name": "roads"}], [], {**VIEW})
    rows = [{"layer_id": "a", "name": "streets"}, {"layer_id": "b", "name": "parcels"}]
    text = project_update(rows, [], {**VIEW, "project_crs": "EPSG:4326", "canvas_crs": "EPSG:4326"}, before)
    assert text.splitlines() == [CHANGES_HEADER, "- layers added: parcels", "- layers renamed: roads -> streets",
                                 "- project CRS is now: EPSG:4326"]


def test_a_rename_keeps_its_new_name_whole_on_each_side():
    """Review 2026-11-18: the entry went through the cut of 100 characters of the names: two names of 60 characters
    lost the end of the new one, and an old name of 100 lost the new one altogether."""
    from core.agent.project_summary import project_update
    old, new = "BD TOPO batiments Toulouse Metropole filtre par commune 2024 v3", "Batiments de Toulouse Metropole " \
        "renommes pour la carte"
    before = project_state([{"layer_id": "a", "name": old}], [], VIEW)
    text = project_update([{"layer_id": "a", "name": new}], [], VIEW, before)
    assert f"-> {new}" in text and old[:60] in text
    huge = "O" * 100
    before = project_state([{"layer_id": "a", "name": huge}], [], VIEW)
    line = project_changes(before, project_state([{"layer_id": "a", "name": "Streets"}], [], VIEW))
    assert line == [f"- layers renamed: {'O' * 60}… -> Streets"]


def test_more_renames_than_the_line_names_send_the_whole_state_again():
    from core.agent.project_summary import MAX_NAMES, project_update
    before = project_state([{"layer_id": str(n), "name": f"old{n}"} for n in range(MAX_NAMES + 3)], [], VIEW)
    rows = [{"layer_id": str(n), "name": f"new{n}", "layer_kind": "vector"} for n in range(MAX_NAMES + 3)]
    text = project_update(rows, [], VIEW, before)
    assert text.splitlines()[0] == HEADER and CHANGES_HEADER not in text
    assert all(f"- new{n} (" in text for n in range(MAX_NAMES + 3))
    few = project_update(rows[:MAX_NAMES] + [{"layer_id": str(n), "name": f"old{n}"} for n in range(MAX_NAMES,
                                                                                                MAX_NAMES + 3)],
                         [], VIEW, before)
    assert few.startswith(CHANGES_HEADER) and few.count(" -> new") == MAX_NAMES


def test_a_new_order_of_the_fields_is_not_a_change_and_a_failed_reading_is_not_no_field():
    """Review 2026-11-18: "fields ... are now: y, x" for a reorder; "none" and then the whole list again after one
    reading of the fields that failed."""
    before = _state(active_fields=["x", "y"])
    assert project_changes(before, _state(active_fields=["y", "x"])) == []
    assert project_changes(before, _state(active_fields=[])) == []
    # the state kept after the failed reading still holds the fields the model was told
    kept = project_state(_rows(), [], {**VIEW, "active_fields": []}, previous=before)
    assert project_changes(kept, _state(active_fields=["x", "y"])) == []
    assert project_changes(kept, _state(active_fields=["x", "y", "z"])) == [
        "- fields of the active layer are now: x, y, z"]
    # another active layer is no reading to forget: its own fields come with it
    other = project_state(_rows(), [], {**VIEW, "active_layer_id": "r", "active_layer_name": "routes",
                                        "active_fields": []}, previous=_state(active_layer_id="c",
                                                                                 active_fields=["x"]))
    assert other["active_field_names"] == frozenset()
