# -*- coding: utf-8 -*-
"""One list of what was done, from the three histories of FilterMate (core/domain/history_timeline.py)."""
from datetime import datetime
from types import SimpleNamespace

import pytest

from core.domain.compare_states import BeforeState
from core.domain.history_timeline import (
    KIND_AGENT, KIND_COVERAGE, KIND_STEP, KIND_VECTOR, counts, cross_items, latest, states_before, timeline, vector_items,
)

pytestmark = pytest.mark.unit

NAMES = {"roads": "Roads", "towns": "Towns", "dem": "DEM"}


def name_of(layer_id):
    return NAMES.get(layer_id, "")


def entry(seconds, layer_ids, previous, description="", expression="", **metadata):
    return SimpleNamespace(timestamp=datetime.fromtimestamp(seconds), layer_ids=tuple(layer_ids),
                           previous_filters=tuple(previous), description=description, expression=expression,
                           get_metadata_value=metadata.get)


def snap(layer_id, subset="", source="/d/a.tif", provider="gdal"):
    return SimpleNamespace(layer_id=layer_id, subset=subset, source=source, provider=provider)


def operation(seconds, pairs, description="", steps=(), effects=()):
    return SimpleNamespace(timestamp=seconds, changes=tuple(pairs), description=description, steps=tuple(steps),
                           effects=tuple(effects))


def test_the_vector_filters_of_the_dock_become_items_with_names_counts_and_states_before():
    first = entry(100, ["roads"], [("roads", "")], expression='"type" = 1', source_feature_count=12)
    second = entry(200, ["roads", "towns"], [("roads", '"type" = 1'), ("towns", None)], description="Roads in towns")
    undone = entry(300, ["towns"], [("towns", "x")], description="Later")
    items = vector_items([first, second], [undone], name_of)
    assert [(item.kind, item.label, item.layers, item.applied, item.count, item.position) for item in items] == [
        (KIND_VECTOR, '"type" = 1', ("Roads",), True, "12", 0),
        (KIND_VECTOR, "Roads in towns", ("Roads", "Towns"), True, "", 1),
        (KIND_VECTOR, "Later", ("Towns",), False, "", 0)]
    assert items[1].befores == (BeforeState("roads", '"type" = 1'), BeforeState("towns", ""))
    assert items[2].befores == ()  # undone: the map no longer holds it


def test_a_layer_gone_keeps_its_id_and_a_long_label_is_cut():
    item = vector_items([entry(1, ["gone"], [("gone", "")], description="a\n  b" + "x" * 500)], [], name_of)[0]
    assert item.layers == ("gone",) and item.label.startswith("a b") and len(item.label) == 200


def test_the_turns_of_the_agent_list_the_steps_of_the_last_one_applied_only():
    old = operation(100, [(snap("roads", "a"), snap("roads", "b"))], "First request",
                    steps=[("Filter", (snap("roads", "a"),)), ("Again", (snap("roads", "ab"),))])
    last = operation(200, [(snap("roads", "b"), snap("roads", "d"))], "Second request",
                     steps=[("Filter roads", (snap("roads", "b"),)), ("Filter towns", (snap("towns", ""),)),
                            ("Roads again", (snap("roads", "c"),))],
                     effects=[("added", "new1", "<qlr/>", (), "Parks"), ("visibility", "towns", True, False)])
    undone = operation(300, [(snap("dem"), snap("dem"))], "Undone", steps=[("x", ()), ("y", ())])
    items = cross_items("agent", [old, last], [undone], name_of, agent=True)
    assert [(item.kind, item.label, item.applied) for item in items] == [
        (KIND_AGENT, "First request", True), (KIND_AGENT, "Second request", True),
        (KIND_STEP, "Filter roads", True), (KIND_STEP, "Filter towns", True), (KIND_STEP, "Roads again", True),
        (KIND_AGENT, "Undone", False)]
    assert items[1].layers == ("Roads", "Parks")  # what it changed beside the filters is named too
    # Before the second step: towns as it was then, and roads as the third step found it.
    assert {state.layer_id: state.subset for state in items[3].befores} == {"towns": "", "roads": "c"}
    assert {state.layer_id: state.subset for state in items[2].befores} == {"roads": "b", "towns": ""}


def test_a_raster_operation_keeps_its_former_source():
    change = (snap("dem", source="/d/dem.tif"), snap("dem", source="/tmp/clip.tif"))
    item = cross_items("dem", [operation(50, [change], "Clip")], [], name_of)[0]
    assert item.kind == KIND_COVERAGE and item.key == "dem" and item.layers == ("DEM",)
    assert item.befores[0].other_source and item.befores[0].source == "/d/dem.tif"


def _three_histories():
    vector = vector_items([entry(100, ["roads"], [("roads", "")], description="V1"),
                           entry(400, ["roads"], [("roads", "agent")], description="V2")],
                          [entry(500, ["roads"], [("roads", "v2")], description="V3 undone")], name_of)
    raster = cross_items("dem", [operation(200, [(snap("dem", source="/d/dem.tif"), snap("dem", source="/t/1.tif"))],
                                           "R1")], [], name_of)
    turn = operation(300, [(snap("roads", "v1"), snap("roads", "agent")), (snap("towns", ""), snap("towns", "t"))],
                     "A1", steps=[("S1", (snap("roads", "v1"),)), ("S2", (snap("towns", ""),))])
    agent = cross_items("agent", [turn], [], name_of, agent=True)
    return vector, raster, agent


def test_one_list_newest_first_with_the_steps_under_their_turn():
    listed = timeline(*_three_histories())
    assert [item.label for item in listed] == ["V3 undone", "V2", "A1", "S1", "S2", "R1", "V1"]
    assert counts(listed) == (4, 1)
    assert latest(listed).label == "V2" and latest(listed, applied=False).label == "V3 undone"
    assert latest([]) is None and counts([]) == (0, 0)


def test_the_map_before_an_item_is_composed_across_the_histories():
    listed = timeline(*_three_histories())
    by_label = {item.label: item for item in listed}

    def before(label):
        return {state.layer_id: (state.source or state.subset) for state in states_before(listed, by_label[label])}
    assert before("V2") == {"roads": "agent"}
    # Before the turn of the agent: roads as the turn found it (not as V2 found it), towns unfiltered.
    assert before("A1") == {"roads": "v1", "towns": ""}
    # Before the raster operation: the DEM on its former source, and everything changed since as it was then.
    assert before("R1") == {"dem": "/d/dem.tif", "roads": "v1", "towns": ""}
    assert before("V1") == {"roads": "", "dem": "/d/dem.tif", "towns": ""}
    assert before("V3 undone") == {}


def test_before_a_step_the_other_steps_of_its_turn_are_not_counted_twice():
    listed = timeline(*_three_histories())
    by_label = {item.label: item for item in listed}
    second = {state.layer_id: state.subset for state in states_before(listed, by_label["S2"])}
    # Before S2, roads already held what S1 left: only V2, done after the turn, changed it since.
    assert second == {"towns": "", "roads": "agent"}
    first = {state.layer_id: state.subset for state in states_before(listed, by_label["S1"])}
    assert first == {"roads": "v1", "towns": ""}
