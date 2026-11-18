# -*- coding: utf-8 -*-
"""How FilterMate works, told in the AGENT thread: what is said, and which links, from what the panel shows."""
from __future__ import annotations

from core.agent import tour


def _keys(facts, kind):
    return [key for what, key in tour.steps(facts) if what == kind]


def test_every_section_then_the_panels_then_the_buttons():
    facts = tour.DockFacts(rail=True, panels=True, can_move=True)
    assert _keys(facts, tour.TEXT) == ["intro", "rail", "exploring", "filtering", "exporting", "agent",
                                       "configuration", "panels", "groups", "buttons"]
    assert "rail" not in _keys(tour.DockFacts(panels=True), tour.TEXT)  # a panel without rails says nothing of them
    assert _keys(facts, tour.LINK) == ["detach_all", "setup", "connect"]


def test_the_links_follow_what_was_just_said():
    told = tour.steps(tour.DockFacts(rail=True, panels=True, can_move=True))
    assert told[told.index((tour.TEXT, "groups")) + 1] == (tour.LINK, "detach_all")
    stacked = tour.steps(tour.DockFacts(panels=True, can_move=True))  # the same link after the other words
    assert stacked[stacked.index((tour.TEXT, "groups_headers")) + 1] == (tour.LINK, "detach_all")
    assert told[told.index((tour.TEXT, "buttons")) + 1] == (tour.LINK, "setup")


def test_a_section_turned_off_is_named_not_described():
    facts = tour.DockFacts(off=("filtering",), panels=True, can_move=True)
    texts = _keys(facts, tour.TEXT)
    assert "filtering" not in texts and "exporting" in texts
    assert texts.index("off") == texts.index("configuration") + 1


def test_the_links_move_only_what_can_move():
    every_one_apart = tour.DockFacts(panels=True, apart=("agent", "filtering", "exporting", "configuration"))
    assert _keys(every_one_apart, tour.LINK)[:1] == ["attach_all"]
    some = tour.DockFacts(panels=True, apart=("filtering",), can_move=True)
    assert _keys(some, tour.LINK)[:2] == ["detach_all", "attach_all"]
    assert "detach_all" not in _keys(tour.DockFacts(panels=True), tour.LINK)  # nothing can leave the panel


def test_a_panel_that_cannot_split_says_nothing_of_panels():
    facts = tour.DockFacts(can_move=True, apart=("agent",))
    assert "panels" not in _keys(facts, tour.TEXT) and "groups" not in _keys(facts, tour.TEXT)
    assert _keys(facts, tour.LINK) == ["setup", "connect"]


def test_with_the_headers_stacked_the_panels_are_told_with_headers():
    stacked = tour.DockFacts(rail=False, panels=True, can_move=True)
    assert "panels_headers" in _keys(stacked, tour.TEXT) and "panels" not in _keys(stacked, tour.TEXT)
    assert "groups_headers" in _keys(stacked, tour.TEXT) and "groups" not in _keys(stacked, tour.TEXT)
    assert "rail" not in _keys(stacked, tour.TEXT)
    rails = tour.DockFacts(rail=True, panels=True, can_move=True)
    assert "panels" in _keys(rails, tour.TEXT) and "panels_headers" not in _keys(rails, tour.TEXT)
    assert "groups" in _keys(rails, tour.TEXT) and "groups_headers" not in _keys(rails, tour.TEXT)


def test_a_model_connected_is_not_offered_again():
    assert "connect" not in _keys(tour.DockFacts(model_ready=True), tour.LINK)
    assert "connect" in _keys(tour.DockFacts(), tour.LINK)
