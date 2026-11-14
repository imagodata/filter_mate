# -*- coding: utf-8 -*-
"""One list of what was done, from the three histories of FilterMate (core/domain/history_timeline.py)."""
from datetime import datetime
from types import SimpleNamespace

import pytest

from core.domain.compare_states import BeforeMap, BeforeState
from core.domain.history_timeline import (
    KIND_AGENT, KIND_COVERAGE, KIND_STEP, KIND_VECTOR, UndoFocus, agent_item, counts, cross_items, label_of, latest,
    link, linked_pairs, map_before, mark, states_before, timeline, vector_items, walkable,
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


def test_a_turn_or_a_step_of_the_agent_is_found_by_its_rank_as_its_history_page_lists_it():
    first = operation(100, [(snap("roads", "a"), snap("roads", "b"))], "First", steps=[("Old step", ())])
    last = operation(200, [(snap("roads", "b"), snap("roads", "c"))], "Last",
                     steps=[("Filter roads", (snap("roads", "b"),)), ("Again", (snap("roads", "bc"),))])
    undone = operation(300, [(snap("dem"), snap("dem"))], "Undone")
    listed = timeline(cross_items("agent", [first, last], [undone], name_of, agent=True),
                      cross_items("dem", [operation(150, [], "Clip")], [], name_of))
    assert agent_item(listed, "agent", 0).label == "First"
    assert agent_item(listed, "agent", 1).label == "Last"
    assert agent_item(listed, "agent", 1, 1).label == "Again" and agent_item(listed, "agent", 1, 1).kind == KIND_STEP
    # The item of the list itself: the map before it is composed as the history panel composes it.
    found = agent_item(listed, "agent", 1, 0)
    assert found is next(item for item in listed if item.label == "Filter roads")
    assert {state.layer_id: state.subset for state in map_before(listed, found).states} == {"roads": "b"}
    assert agent_item(listed, "agent", 0, 0) is None  # the steps of an earlier turn are not listed
    assert agent_item(listed, "agent", 2) is None  # undone: its rank is not in the turns applied
    assert agent_item(listed, "agent", 1, 2) is None and agent_item(listed, "other", 0) is None
    assert agent_item(listed, "dem", 0) is None  # a raster operation is not a turn


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


def _turns_with_effects():
    """A vector filter, then two turns of the agent: the first adds a layer and restyles roads, the second restyles
    roads again and hides towns, in two steps."""
    vector = vector_items([entry(100, ["roads"], [("roads", "")], description="V1")], [], name_of)
    first = operation(200, [(snap("roads", "v1"), snap("roads", "a1"))], "A1",
                      effects=[("added", "parks", "<qlr/>", ((), 0), "Parks"),
                               ("style", "roads", "<red/>", "<blue/>", "Roads")])
    second = operation(300, [], "A2", steps=[("Style", ()), ("Hide towns", ())],
                       effects=[("style", "roads", "<blue/>", "<green/>", "Roads"), ("visibility", "towns", True, False)])
    second.step_effects = ((("style", "roads", "<blue/>", "<green/>", "Roads"),), (("visibility", "towns", True, False),))
    agent = cross_items("agent", [first, second], [], name_of, agent=True)
    return timeline(vector, agent)


def test_the_map_before_an_item_holds_what_the_turns_since_did_beside_the_filters():
    listed = _turns_with_effects()
    by_label = {item.label: item for item in listed}
    old = map_before(listed, by_label["V1"])
    # Before the vector filter: roads unfiltered and red, towns shown, parks not there yet.
    assert old.states == (BeforeState("roads", "", style="<red/>"),) and old.label == "V1"
    assert old.present == ("towns",) and old.absent == frozenset({"parks"})
    turn = map_before(listed, by_label["A1"])
    assert turn.states == (BeforeState("roads", "v1", style="<red/>"),) and turn.absent == frozenset({"parks"})
    assert map_before(listed, by_label["A2"]).states == (BeforeState("roads", None, style="<blue/>"),)
    # Before the second step of the last turn: towns shown, roads as the first step left it (its style is not undone).
    step = map_before(listed, by_label["Hide towns"])
    assert step.present == ("towns",) and step.absent == frozenset() and step.states == ()
    first_step = map_before(listed, by_label["Style"])
    assert first_step.states == (BeforeState("roads", None, style="<blue/>"),) and first_step.present == ("towns",)


def test_nothing_before_an_item_undone():
    undone = vector_items([], [entry(1, ["roads"], [("roads", "x")], description="U")], name_of)[0]
    assert map_before([undone], undone) == BeforeMap(label="U") and map_before([undone], undone).empty


def test_what_undo_and_redo_take_is_marked_and_counted():
    applied, scoped_out, top = (entry(seconds, ["roads"], [("roads", "")], description=f"E{seconds}")
                                for seconds in (1, 2, 3))
    redo = entry(4, ["roads"], [("roads", "")], description="R")
    items = vector_items([applied, scoped_out, top], [redo], name_of)
    focus = UndoFocus(KIND_VECTOR, undo=(top,), redo=(redo,), undo_left=1, redo_left=1)
    assert [mark(item, focus) for item in items] == ["", "", "undo", "redo"]
    assert mark(items[2], UndoFocus(KIND_VECTOR, redo=(top,))) == ""  # applied: never what Redo takes
    assert walkable([applied, scoped_out, top], lambda found: found is not scoped_out) == 1
    assert walkable([applied, top], lambda found: True) == 2 and walkable([], lambda found: True) == 0
    assert label_of(top) == "E3" and label_of(SimpleNamespace(expression=' "a"\n= 1')) == '"a" = 1'


def test_a_step_is_never_marked_alone():
    listed = _turns_with_effects()
    turn = next(item for item in listed if item.label == "A2")
    focus = UndoFocus(KIND_AGENT, undo=(turn.ref,))
    assert [item.label for item in listed if mark(item, focus)] == ["A2"]  # not its steps "Style", "Hide towns"


# --- an operation done while a turn of the agent was under way --------------------------------------------------


def _turn_under_way(step_times=(100, 140, 160), started=100):
    """A turn begun at 100 and recorded at 200: step 1 filters V and restyles A, step 2 filters the raster R through
    the API (its own operation, at 150), step 3 filters V again."""
    turn = operation(200, [(snap("V", ""), snap("V", "b")), (snap("R", source="/d/r.tif"), snap("R", source="/t/r.vrt"))],
                     "Turn", steps=[("S1", (snap("V", ""),)), ("S2", (snap("R", source="/d/r.tif"),)),
                                    ("S3", (snap("V", "a"),))],
                     effects=[("style", "A", "<old/>", "<new/>", "A")])
    turn.step_effects = ((("style", "A", "<old/>", "<new/>", "A"),), (), ())
    turn.started, turn.step_times = started, tuple(step_times)
    raster = cross_items("R", [operation(150, [(snap("R", source="/d/r.tif"), snap("R", source="/t/r.vrt"))],
                                         "Clip R")], [], name_of)
    return timeline(raster, cross_items("agent", [turn], [], name_of, agent=True))


def test_a_turn_under_way_counts_only_its_steps_begun_after_the_operation():
    listed = _turn_under_way()
    clip = next(item for item in listed if item.label == "Clip R")
    before = map_before(listed, clip)
    # V as step 3 found it (step 1 had filtered it already), A keeps the style step 1 gave it, R before the clip.
    assert {state.layer_id: (state.source or state.subset) for state in before.states} == {"R": "/d/r.tif", "V": "a"}
    assert all(state.style is None for state in before.states)


def test_a_turn_under_way_whose_steps_began_before_counts_for_nothing():
    listed = _turn_under_way(step_times=(100, 140, 145))
    clip = next(item for item in listed if item.label == "Clip R")
    assert {state.layer_id for state in map_before(listed, clip).states} == {"R"}
    # Without the times of its steps (an earlier record, a turn of one step), the turn under way is not counted.
    listed = _turn_under_way(step_times=())
    assert {state.layer_id for state in map_before(listed, next(i for i in listed if i.label == "Clip R")).states} == {"R"}


def test_a_turn_begun_after_the_operation_counts_whole():
    listed = _turn_under_way(started=150)
    clip = next(item for item in listed if item.label == "Clip R")
    before = map_before(listed, clip)
    assert {state.layer_id: state.subset for state in before.states if state.layer_id == "V"} == {"V": ""}
    assert any(state.layer_id == "A" and state.style == "<old/>" for state in before.states)


def test_a_turn_and_its_steps_begin_when_they_began():
    listed = _turn_under_way()
    by_label = {item.label: item for item in listed}
    assert by_label["Turn"].begun == 100 and by_label["Turn"].time == 200
    assert [by_label[name].begun for name in ("S1", "S2", "S3")] == [100, 140, 160]
    assert by_label["Clip R"].begun == 150  # no start of its own: when it was done
    # Listed under their turn all the same.
    assert [item.label for item in listed] == ["Turn", "S1", "S2", "S3", "Clip R"]


# --- a vector filter and the raster operation it ran with ------------------------------------------------------


def test_a_vector_filter_and_its_raster_operation_pair_as_undo_takes_them():
    first = entry(1, ["roads"], [("roads", "")], description="F1")
    other = entry(2, ["towns"], [("towns", "")], description="Other source")
    second = entry(3, ["roads"], [("roads", "a")], description="F2")
    third = entry(4, ["roads"], [("roads", "b")], description="F3, nothing clipped")
    ops = [SimpleNamespace(op_id=11), SimpleNamespace(op_id=12)]
    pairs = linked_pairs([first, other, second, third], "roads", [11, 12, None], ops)
    assert [(found.description, op.op_id) for found, op in pairs] == [("F2", 12), ("F1", 11)]
    # An operation forgotten since (a removed layer, the cache): its run pairs with nothing, the older one still does.
    assert [(found.description, op.op_id) for found, op in linked_pairs([first, second], "roads", [11, 12], ops[:1])] \
        == [("F1", 11)]
    assert linked_pairs([first], "roads", [], ops) == []


def test_the_map_before_a_filter_undoes_the_raster_operation_it_ran_with():
    """The raster task may end before the vector one: its operation is older on the clock, yet one step with it."""
    vector_entry = entry(100, ["roads"], [("roads", "")], description="Roads and DEM")
    clip = operation(90, [(snap("dem", source="/d/dem.tif"), snap("dem", source="/t/clip.vrt"))], "cross filter")
    clip.op_id = 7
    items = timeline(vector_items([vector_entry], [], name_of), cross_items("roads", [clip], [], name_of))
    linked = timeline(link(items, linked_pairs([vector_entry], "roads", [7], [clip])))
    by_label = {item.label: item for item in linked}
    expected = {"roads": "", "dem": "/d/dem.tif"}
    assert {s.layer_id: s.source or s.subset for s in map_before(linked, by_label["Roads and DEM"]).states} == expected
    assert {s.layer_id: s.source or s.subset for s in map_before(linked, by_label["cross filter"]).states} == expected
    assert by_label["cross filter"].time == by_label["Roads and DEM"].time
    # Not linked, the clock leaves the DEM clipped before the filter.
    unlinked = {item.label: item for item in items}
    assert {s.layer_id for s in map_before(items, unlinked["Roads and DEM"]).states} == {"roads"}
