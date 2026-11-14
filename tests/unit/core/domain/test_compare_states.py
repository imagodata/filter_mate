# -*- coding: utf-8 -*-
"""States before a filter operation for the Compare mode (core/domain/compare_states.py)."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from core.domain.compare_states import (BeforeMap, BeforeState, LayerState, MapState, before_layer_order,
                                        from_cross_operation, from_history_entry, map_from_history_entry,
                                        map_from_operation, map_from_pin, map_with_effects, pin_before)

pytestmark = pytest.mark.unit


def snapshot(layer_id, source="/data/a.tif", provider="gdal", subset=""):
    return SimpleNamespace(layer_id=layer_id, source=source, provider=provider, subset=subset)


def test_a_vector_filter_gives_the_former_subsets():
    entry = SimpleNamespace(previous_filters=(("a", '"pop" > 10'), ("b", None), ("a", "later")))
    assert from_history_entry(entry) == [BeforeState("a", '"pop" > 10'), BeforeState("b", "")]
    assert from_history_entry(SimpleNamespace()) == []


def test_a_cross_operation_gives_the_snapshots_before():
    operation = SimpleNamespace(changes=(
        (snapshot("v", "/d/v.gpkg", "ogr", '"x" = 1'), snapshot("v", "/d/v.gpkg", "ogr", '"x" = 2')),
        (snapshot("r", "/d/dem.tif"), snapshot("r", "/tmp/fm/dem_clip.tif")),
        (snapshot("v", "/d/v.gpkg", "ogr", "second"), snapshot("v", "/d/v.gpkg", "ogr", "third")),
    ))
    states = from_cross_operation(operation)
    assert states == [BeforeState("v", '"x" = 1'), BeforeState("r", "", "/d/dem.tif", "gdal")]
    assert not states[0].other_source and states[1].other_source
    assert from_cross_operation(SimpleNamespace(changes=None)) == []


# --- the map before a step ------------------------------------------------------------


def test_a_vector_entry_keeps_the_layers_undo_restores_and_its_description():
    entry = SimpleNamespace(previous_filters=(("a", "x"), ("b", "y")), description="Filter: x")
    assert map_from_history_entry(entry, {"a"}) == BeforeMap((BeforeState("a", "x"),), label="Filter: x")
    assert [state.layer_id for state in map_from_history_entry(entry).states] == ["a", "b"]
    assert map_from_history_entry(SimpleNamespace()).empty


def test_a_raster_operation_without_effects_is_its_snapshots():
    operation = SimpleNamespace(changes=((snapshot("r", "/d/dem.tif"), snapshot("r", "/tmp/clip.vrt")),),
                                description="raster selection")
    before = map_from_operation(operation)
    assert before.states == tuple(from_cross_operation(operation))
    assert (before.absent, before.present, before.missing, before.label) == (frozenset(), (), (), "raster selection")
    assert before.states[0].style is None and before.states[0].snapshot is operation.changes[0][0]


def test_a_turn_of_the_agent_draws_its_style_visibility_and_layers_before():
    operation = SimpleNamespace(
        changes=((snapshot("v", "/d/v.gpkg", "ogr", "a"), snapshot("v", "/d/v.gpkg", "ogr", "b")),),
        effects=(("style", "v", "<red/>", "<blue/>", "roads"),
                 ("style", "v", "<blue/>", "<green/>", "roads"),  # a second change: the first state is kept
                 ("style", "s", "<thin/>", "<thick/>", "rivers"),
                 ("visibility", "h", True, False),  # hidden by the turn: on the map before
                 ("visibility", "w", False, True),  # shown by the turn: not on it
                 ("visibility", "same", True, True),
                 ("added", "new", "<qlr/>", ((), 0), "buffer"),
                 ("style", "new", "<a/>", "<b/>", "buffer"),  # a layer not there before needs no clone
                 ("removed", "old", "<qlr/>", ((), 2), "parcels"),
                 ("selection", "v", (1,), (2,)),
                 ("notes", "", [], ["a note"])),
        description="Style the roads and add a buffer")
    before = map_from_operation(operation)
    assert [state.layer_id for state in before.states] == ["v", "s"]
    assert before.states[0] == BeforeState("v", "a", style="<red/>")
    assert before.states[1] == BeforeState("s", None, style="<thin/>")  # its filter kept
    assert before.present == ("h",)
    assert before.absent == frozenset({"w", "new"})
    assert before.missing == ("parcels",)
    assert before.label == "Style the roads and add a buffer" and before.pinned_at is None
    assert not before.empty


def test_an_undo_back_to_a_step_turns_its_effects_around():
    """``effects_reversed``: undoing the operation applies its effects again, the map before is the map after them."""
    operation = SimpleNamespace(changes=(), effects_reversed=True,
                                effects=(("style", "v", "<red/>", "<blue/>", "roads"),
                                         ("visibility", "h", True, False),
                                         ("added", "new", "<qlr/>", ((), 0), "buffer"),
                                         ("removed", "old", "<qlr/>", ((), 2), "parcels")))
    before = map_from_operation(operation)
    assert before.states == (BeforeState("v", None, style="<blue/>"),)
    assert before.absent == frozenset({"h", "old"})
    assert before.missing == ("buffer",)
    assert before.present == ()


def test_an_undo_back_to_a_step_keeps_the_last_state_of_each_layer():
    """Reversed, the map before the operation is the map after the last step: the last effect on a layer counts."""
    operation = SimpleNamespace(changes=(), effects_reversed=True, effects=(
        ("style", "L", "<a/>", "<b/>", "roads"), ("style", "L", "<b/>", "<c/>", "roads"),
        ("visibility", "V", True, False), ("visibility", "V", False, True),
        ("added", "T", "<qlr/>", ((), 0), "temp"), ("removed", "T", "<qlr/>", ((), 0), "temp")))
    before = map_from_operation(operation)
    assert before.states == (BeforeState("L", None, style="<c/>"),)
    assert before.present == ("V",)  # shown again by the last step: drawn
    assert before.absent == frozenset({"T"}) and before.missing == ()  # added then removed: neither there nor missed


def test_a_turn_keeps_the_first_state_of_each_layer():
    operation = SimpleNamespace(changes=(), effects=(
        ("visibility", "V", True, False), ("visibility", "V", False, True),
        ("added", "T", "<qlr/>", ((), 0), "temp"), ("removed", "T", "<qlr/>", ((), 0), "temp")))
    before = map_from_operation(operation)
    assert before.present == ("V",) and before.absent == frozenset({"T"}) and before.missing == ()


def test_what_a_turn_changed_and_is_not_drawn_is_named():
    operation = SimpleNamespace(changes=(), effects=(
        ("tree", "", "{}", "{}"), ("project_crs", "", "EPSG:2154", "EPSG:4326"),
        ("edits", "E", 0, 3, "parcels"), ("edits", "E", 3, 5, "parcels"), ("join", "J", {}, "", "roads"),
        ("current_style", "S", "default", "night"), ("layer_name", "N", "old", "new"),
        ("edits", "A", 0, 1, "buffer"), ("added", "A", "<qlr/>", ((), 0), "buffer"),
        ("notes", "", [], ["x"]), ("bookmarks", "", "", "")))
    before = map_from_operation(operation)
    assert before.unshown == (("tree", "", ""), ("project_crs", "", ""), ("edits", "E", "parcels"),
                              ("join", "J", "roads"), ("current_style", "S", ""), ("layer_name", "N", ""))
    assert before.empty is False and before.absent == frozenset({"A"})  # the layer it added is not named again
    assert map_from_operation(SimpleNamespace(changes=(), effects=(("tree", "", "", ""),))).empty


def test_an_operation_with_nothing_drawable_is_empty():
    assert map_from_operation(SimpleNamespace(changes=(), effects=(("notes", "", [], ["x"]),))).empty
    only_removed = map_from_operation(SimpleNamespace(changes=(), effects=(("removed", "old", "", ((), 0), "p"),)))
    assert only_removed.empty and only_removed.missing == ("p",)


def test_several_operations_keep_the_state_before_the_first_effect_on_each_layer():
    """The map before a step of the history: what the turns done since changed, before the first of them."""
    first = (("style", "v", "<red/>", "<blue/>", "roads"), ("visibility", "h", True, False))
    second = (("style", "v", "<blue/>", "<green/>", "roads"), ("visibility", "h", False, True),
              ("added", "new", "<qlr/>", ((), 0), "buffer"), ("visibility", "w", False, True))
    # An "undo back to here" that hid w again after the second turn showed it: reversed, it brings it back.
    third = (("visibility", "w", True, False),)
    before = map_with_effects([BeforeState("v", "a")], [(first, False), (second, False), (third, True)], "Step")
    assert before.states == (BeforeState("v", "a", style="<red/>"),)
    assert before.present == ("h",) and before.absent == frozenset({"new", "w"}) and before.label == "Step"
    assert map_with_effects([BeforeState("x", "a"), BeforeState("x", "b")], []).states == (BeforeState("x", "a"),)


# --- a pin of the map before a step ------------------------------------------------------


def test_a_pin_of_the_map_before_a_step_differs_by_the_layers_changed_since():
    from core.domain.filter_state import LayerSnapshot
    roads = LayerSnapshot("roads", "vector", "/d/v.gpkg|layername=roads", "ogr", subset='"type" = 2')
    dem = LayerSnapshot("dem", "raster", "/tmp/fm/dem_clip.vrt", "gdal", derived=True, original_source="/d/dem.tif")
    dem_then = LayerSnapshot("dem", "raster", "/d/dem.tif", "gdal")
    now = MapState((LayerState("roads", "Roads", roads, "<blue/>", True), LayerState("dem", "DEM", dem, "<r/>", True),
                    LayerState("added", "Buffer", None, "<s/>", True), LayerState("hidden", "Rivers", None, "<s/>", False),
                    LayerState("same", "Same", None, "<s/>", True)), 500.0)
    before = BeforeMap((BeforeState("roads", '"type" = 1', style="<red/>"),
                        BeforeState("dem", "", "/d/dem.tif", "gdal", dem_then)),
                       frozenset({"added"}), ("hidden",), ("Parcels",))
    pinned = pin_before(now, before, 100.0)
    assert pinned.taken_at == 100.0
    kept = {layer.layer_id: layer for layer in pinned.layers}
    assert kept["roads"].snapshot == replace(roads, subset='"type" = 1') and kept["roads"].style == "<red/>"
    assert kept["dem"].snapshot is dem_then and kept["dem"].style == "<r/>"
    assert not kept["added"].visible and kept["hidden"].visible and kept["same"] == now.layers[4]
    # Compared with the map now, the pin draws what the map before the step draws.
    compared = map_from_pin(pinned, now)
    assert {state.layer_id: (state.subset, state.source, state.style) for state in compared.states} == {
        "roads": ('"type" = 1', "", "<red/>"), "dem": ("", "/d/dem.tif", None)}
    assert compared.absent == frozenset({"added"}) and compared.present == ("hidden",)
    assert compared.missing == ("Parcels",) and compared.pinned_at == 100.0


def test_a_pin_before_a_step_keeps_a_filter_kept_and_names_a_layer_not_read():
    from core.domain.filter_state import LayerSnapshot
    roads = LayerSnapshot("roads", "vector", "/d/v.gpkg", "ogr", subset="x")
    now = MapState((LayerState("roads", "Roads", roads, "<blue/>", True), LayerState("unread", "U", None, None, True),
                    LayerState("gone_later", "G", None, None, True)))
    before = BeforeMap((BeforeState("roads", None, style="<red/>"), BeforeState("unread", "y")),
                       unshown=(("tree", "", ""), ("edits", "gone_later", "G")))
    pinned = pin_before(now, before, 1.0)
    assert pinned.layers[0].snapshot is roads and pinned.layers[0].style == "<red/>"
    # The filter of then cannot be kept on a layer not read: named, not dropped in silence; what the step changed
    # and a pin cannot hold is named too.
    assert pinned.layers[1].snapshot is None
    assert pinned.unshown == (("tree", "", ""), ("edits", "gone_later", "G"), ("filter", "unread", "U"))
    compared = map_from_pin(pinned, now)
    assert compared.states == (BeforeState("roads", None, style="<red/>"),) and compared.unshown == pinned.unshown
    # A layer removed since is named as missing, not twice.
    assert map_from_pin(pinned, MapState(now.layers[:2])).unshown == (("tree", "", ""), ("filter", "unread", "U"))


# --- a pin ------------------------------------------------------------------------------


def vector(subset=""):
    return SimpleNamespace(source="/d/v.gpkg|layername=v", provider="ogr", subset=subset, renderer_xml="")


def layer(layer_id, snap=None, style="<s/>", visible=True, name=None):
    return LayerState(layer_id, name or layer_id.upper(), snap if snap is not None else vector(), style, visible)


def test_nothing_changed_since_the_pin():
    pinned = MapState((layer("a"), layer("b", visible=False)), 100.0)
    before = map_from_pin(pinned, MapState((layer("a"), layer("b", visible=False)), 200.0))
    assert before.empty and before == BeforeMap(pinned_at=100.0)


def test_a_pin_draws_only_the_layers_that_differ():
    raster_then = SimpleNamespace(source="/d/dem.tif", provider="gdal", subset="", renderer_xml="")
    raster_now = SimpleNamespace(source="/tmp/dem_clip.vrt", provider="gdal", subset="", renderer_xml="")
    pinned = MapState((layer("filtered", vector("x = 1")), layer("styled", style="<red/>"), layer("same"),
                       layer("raster", raster_then), layer("both", vector("x = 1"), style="<red/>")), 10.0)
    now = MapState((layer("filtered", vector("x = 2")), layer("styled", style="<blue/>"), layer("same"),
                    layer("raster", raster_now), layer("both", vector(""), style="<blue/>")), 20.0)
    before = map_from_pin(pinned, now)
    states = {state.layer_id: state for state in before.states}
    assert list(states) == ["filtered", "styled", "raster", "both"]
    assert states["filtered"] == BeforeState("filtered", "x = 1") and states["filtered"].snapshot is pinned.layers[0].snapshot
    assert states["styled"] == BeforeState("styled", None, style="<red/>") and states["styled"].snapshot is None
    assert states["raster"] == BeforeState("raster", "", "/d/dem.tif", "gdal") and states["raster"].other_source
    assert states["both"] == BeforeState("both", "x = 1", style="<red/>")
    assert (before.absent, before.present, before.missing) == (frozenset(), (), ())
    assert before.pinned_at == 10.0 and before.label == ""


def test_a_pin_follows_the_layers_shown_hidden_added_and_removed():
    pinned = MapState((layer("hidden_since"), layer("shown_since", visible=False), layer("removed", name="Parcels"),
                       layer("removed_hidden", visible=False), layer("hidden_both", visible=False),
                       layer("hidden_restyled", style="<red/>")), 10.0)
    now = MapState((layer("hidden_since", visible=False), layer("shown_since"), layer("added"),
                    layer("added_hidden", visible=False), layer("hidden_both", vector("x = 9"), visible=False),
                    layer("hidden_restyled", style="<blue/>", visible=False)), 20.0)
    before = map_from_pin(pinned, now)
    assert before.present == ("hidden_since", "hidden_restyled")
    assert before.absent == frozenset({"shown_since", "added"})
    assert before.missing == ("Parcels",)  # a layer hidden then and removed since is not missed
    assert [state.layer_id for state in before.states] == ["hidden_restyled"]  # drawn as it was, though hidden now


def test_a_layer_not_read_is_not_compared():
    pinned = MapState((LayerState("a", "A", None, None, True),), 1.0)
    assert map_from_pin(pinned, MapState((layer("a"),), 2.0)).empty


def test_the_same_differences_give_the_same_map_before():
    """The comparison draws again only when what differs changed: equal maps before for the same differences."""
    pinned = MapState((layer("a", vector("x = 1")), layer("b")), 1.0)
    first = map_from_pin(pinned, MapState((layer("a", vector("x = 2")), layer("b")), 2.0))
    second = map_from_pin(pinned, MapState((layer("a", vector("x = 3")), layer("b")), 3.0))
    third = map_from_pin(pinned, MapState((layer("a", vector("x = 3")), layer("b", vector("y")),), 4.0))
    assert first == second and first != third


# --- the order of the layers before ----------------------------------------------------


def test_the_layers_before_keep_the_order_of_the_tree():
    order = ["top", "a", "hidden", "b", "bottom_hidden"]
    assert before_layer_order(["top", "a", "b"], order, set(), ["hidden"]) == ["top", "a", "hidden", "b"]
    assert before_layer_order(["top", "a", "b"], order, {"top"}, ["bottom_hidden"]) == ["a", "b", "bottom_hidden"]
    assert before_layer_order(["a", "b"], order, set(), ["top"]) == ["top", "a", "b"]
    assert before_layer_order(["a"], order, set(), ["a", "unknown"]) == ["a", "unknown"]
    assert before_layer_order(["x", "a"], order, set(), ["hidden"]) == ["x", "a", "hidden"]  # x is not in the tree
