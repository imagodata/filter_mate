# -*- coding: utf-8 -*-
"""The checks of a call that drives the EXPLORING rail (core/agent/exploring_drive.py)."""
import pytest

from core.agent.exploring_drive import (
    HIDDEN, MAP_TOOLS, NOT_DRIVEN, OFF, ON, PRESS, UNAVAILABLE, actions_of, check_request, driven, toggles_of,
)
from core.domain.exploring_tools import KINDS, LOCKED, POINT_CLOUD, RASTER, VECTOR, tools_of

pytestmark = pytest.mark.unit


def rail(kind, **states):
    out = {name: OFF for name in toggles_of(kind)}
    out.update({name: PRESS for name in actions_of(kind)})
    out.update(states)
    return out


@pytest.mark.parametrize("kind", KINDS)
def test_every_button_of_the_rail_is_driven_or_left_to_the_user(kind):
    names = set(tools_of(kind))
    assert set(toggles_of(kind)) | set(actions_of(kind)) | set(NOT_DRIVEN) == names
    assert not set(toggles_of(kind)) & set(actions_of(kind))
    assert LOCKED <= set(NOT_DRIVEN)
    assert driven(kind) == tuple(name for name in tools_of(kind) if name not in NOT_DRIVEN)


def test_a_tool_turned_on_is_planned():
    plan, problems = check_request(RASTER, {"pipette": True}, [], rail(RASTER))
    assert problems == [] and plan == {"tools": [("pipette", True)], "press": []}


def test_what_is_already_as_asked_is_left():
    plan, problems = check_request(VECTOR, {"sync": True, "follow": False}, [], rail(VECTOR, sync=ON))
    assert problems == [] and plan == {"tools": [], "press": []}


def test_the_tools_put_down_go_first():
    """One tool on the map at a time: the one leaving goes before the one coming, whatever the order asked."""
    plan, _ = check_request(POINT_CLOUD, {"value_pipette": True, "identify": False}, [], rail(POINT_CLOUD, identify=ON))
    assert plan["tools"] == [("identify", False), ("value_pipette", True)]


def test_two_tools_for_the_map_are_refused():
    plan, problems = check_request(RASTER, {"pipette": True, "detector": True}, [], rail(RASTER))
    assert plan == {} and "one tool at a time" in problems[0]
    assert {"pipette", "detector"} <= MAP_TOOLS


def test_a_mode_and_a_tool_go_together():
    plan, problems = check_request(VECTOR, {"sync": True, "zone": True}, [], rail(VECTOR))
    assert problems == [] and plan["tools"] == [("sync", True), ("zone", True)]


def test_a_button_the_user_hid_is_refused_with_the_way_back():
    plan, problems = check_request(VECTOR, {"follow": True}, [], rail(VECTOR, follow=HIDDEN))
    assert plan == {} and "APP.DOCKWIDGET.EXPLORING_TOOLS.vector_hidden" in problems[0] and "right-click" in problems[0]


def test_turning_off_a_hidden_or_greyed_button_is_no_change():
    plan, problems = check_request(VECTOR, {"follow": False, "link": False}, [],
                                   rail(VECTOR, follow=HIDDEN, link=UNAVAILABLE))
    assert problems == [] and plan == {"tools": [], "press": []}


def test_a_greyed_button_says_why():
    _plan, problems = check_request(VECTOR, {"link": True}, [], rail(VECTOR, link=UNAVAILABLE),
                                    {"link": "Link   the single\nand multiple selections"})
    assert problems == ["link: not available now (Link the single and multiple selections)"]


def test_an_action_is_pressed_and_a_toggle_is_set():
    _plan, problems = check_request(VECTOR, {"zoom": True}, ["sync"], rail(VECTOR))
    assert "zoom: it runs once: name it in press" in problems
    assert "sync: it stays down: set it in tools" in problems
    plan, problems = check_request(VECTOR, {}, ["zoom", "identify", "zoom"], rail(VECTOR))
    assert problems == [] and plan["press"] == ["zoom", "identify"]


def test_the_users_own_buttons_are_never_driven():
    _plan, problems = check_request(VECTOR, {"more": True}, ["reset"], rail(VECTOR))
    assert len(problems) == 2 and all("not driven" in problem for problem in problems)


def test_a_name_of_another_rail_lists_those_of_this_one():
    _plan, problems = check_request(VECTOR, {"pipette": True}, [], rail(VECTOR))
    assert problems[0].startswith("pipette: not a button of the rail of a vector layer")
    assert "sync, follow, zone, link" in problems[0] and "zoom, identify" in problems[0]


@pytest.mark.parametrize("tools, press", [("pipette", []), ({"pipette": "yes"}, []), ({}, "zoom"), ({1: True}, [])])
def test_malformed_arguments_are_refused(tools, press):
    plan, problems = check_request(RASTER, tools, press, rail(RASTER))
    assert plan == {} and problems


def test_nothing_asked_is_nothing_planned():
    assert check_request(RASTER, None, None, rail(RASTER)) == ({"tools": [], "press": []}, [])


def test_one_problem_plans_nothing():
    plan, problems = check_request(RASTER, {"preview": True, "pipette": True}, [], rail(RASTER, pipette=HIDDEN))
    assert plan == {} and len(problems) == 1


@pytest.mark.parametrize("expression", ['"pop" > 1000', '"pop">=1000', '"h" < -2.5', '"annee" BETWEEN 1950 AND 1975',
                                        '"a" = \'x\' AND "surface" <= 10000', '"z" > 0.5'])
def test_a_threshold_is_offered_to_tune(expression):
    from core.agent.exploring_drive import TUNING_OFFER, tuning_offer
    assert tuning_offer(expression) == TUNING_OFFER


@pytest.mark.parametrize("expression", ['"nom" = \'Muret\'', '"a" <> 3', '"a" != 3', '"code" IN (1, 2)', '"x" -> 2',
                                        '"nom" > \'M\'', '', None, 42])
def test_no_threshold_no_offer(expression):
    from core.agent.exploring_drive import tuning_offer
    assert tuning_offer(expression) == ""


# --- the values of the panel of a raster and of a point cloud ---------------------------------------------------------

def test_a_raster_range_is_checked():
    from core.agent.exploring_drive import check_raster_values
    assert check_raster_values({"minimum": 1200, "maximum": None}, [1]) == ({"minimum": 1200.0, "maximum": None}, [])
    assert check_raster_values({"band": 2, "quantity": "slope_degrees"}, [1, 2])[0] == {"band": 2,
                                                                                          "quantity": "slope_degrees"}
    for values, words in (({"band": 3}, "one of 1, 2"), ({"quantity": "ndvi"}, "one of value"),
                          ({"minimum": 5, "maximum": 1}, "minimum above maximum"), ({"minimum": "5"}, "a number"),
                          ({"minimum": float("nan")}, "a number"), ({"colour": 1}, "not a value"), ({}, "an object")):
        clean, problems = check_raster_values(values, [1, 2])
        assert clean == {} and any(words in problem for problem in problems), (values, problems)


def test_a_rendered_raster_has_no_range():
    from core.agent.exploring_drive import check_raster_values
    clean, problems = check_raster_values({"minimum": 1}, [1, 2, 3], rendered=True)
    assert clean == {} and "pipette" in problems[0]


def test_point_cloud_classes_or_ranges_are_checked():
    from core.agent.exploring_drive import check_point_cloud_values
    holds, attributes = [1, 2, 6], ["Z", "Intensity"]
    assert check_point_cloud_values({"classes": [6, 2, 6]}, holds, attributes) == ({"classes": [2, 6]}, [])
    clean, _ = check_point_cloud_values({"ranges": [{"attribute": "Z", "minimum": 100}]}, holds, attributes)
    assert clean == {"ranges": [{"attribute": "Z", "minimum": 100.0, "maximum": None}]}
    for values, words in (({"classes": [9]}, "9 not in this point cloud"), ({"classes": []}, "a list of class codes"),
                          ({"classes": [2], "ranges": []}, "not both"),
                          ({"ranges": [{"attribute": "Red", "minimum": 1}]}, "not an attribute"),
                          ({"ranges": [{"attribute": "Z"}]}, "needs a minimum or a maximum"),
                          ({"ranges": [{"attribute": "Z", "minimum": 9, "maximum": 1}]}, "minimum above maximum"),
                          ({"z": 1}, "not a value")):
        clean, problems = check_point_cloud_values(values, holds, attributes)
        assert clean == {} and any(words in problem for problem in problems), (values, problems)
