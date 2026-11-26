# -*- coding: utf-8 -*-
import json

import pytest

from core.agent.transcript import MAX_CHARS, MAX_RECAP_REQUESTS, RECAP_HEADER, entry, from_json, recap, to_json, trim

pytestmark = pytest.mark.unit


def test_round_trip_keeps_what_matters():
    entries = [entry("user", "a"), entry("action", "Filter on x", ok=False, detail='"a" = 1', count="3 / 9"),
               entry("text", "done"), entry("note", "n")]
    assert from_json(to_json(entries)) == entries


def test_output_links_round_trip_without_sending_local_paths_to_the_model():
    entries = [entry('user', 'exporte la carte'),
               entry('output', 'map.pdf', detail='/chosen/private/map.pdf')]
    assert from_json(to_json(entries)) == entries
    assert '/chosen/private' not in recap(entries) and 'map.pdf' not in recap(entries)


def test_odd_input_is_dropped_not_interpreted():
    assert from_json("not json") == []
    assert from_json(json.dumps([{"kind": "evil", "text": "x"}, {"kind": "user"}, "x", {"kind": "text", "text": "ok"}])) == [
        entry("text", "ok")]


def test_trim_keeps_the_newest_whole_entries():
    entries = [entry("text", str(index) * 100) for index in range(10)]
    kept = trim(entries, 450)
    assert kept == entries[-3:]
    assert trim([entry("text", "x" * 100)], 50) == []  # one entry too big for the budget: nothing
    assert len(entry("text", "x" * (MAX_CHARS * 2))["text"]) < MAX_CHARS  # a field is cut on its own


def test_unknown_kind_is_refused():
    with pytest.raises(ValueError):
        entry("other", "x")


def test_the_layer_names_in_bold_are_kept_and_bounded():
    item = entry("action", "Filter on communes by roads", strong=["communes", "roads", 3, ""] + ["x"] * 20)
    assert item["strong"][:2] == ["communes", "roads"] and len(item["strong"]) == 8
    assert "strong" not in entry("action", "Filter on communes")  # the stored form stays as it was without them
    assert from_json(to_json([item]))[0]["strong"] == item["strong"]
    assert "strong" not in from_json('[{"kind": "action", "text": "t", "strong": "communes"}]')[0]


def test_a_recap_says_what_was_asked_and_done_never_what_was_answered():
    entries = [entry("user", "Les communes de plus\nde 10000 habitants"), entry("action", "Filter applied on communes"),
               entry("text", "Voici: Toulouse 514819 habitants"), entry("note", "summed up"),
               entry("user", "Exporte-les"), entry("action", "Export", ok=False), entry("user", "Merci")]
    text = recap(entries)
    assert text.splitlines() == [
        RECAP_HEADER, "- asked: Les communes de plus de 10000 habitants | done: Filter applied on communes",
        "- asked: Exporte-les | done: Export (failed)", "- asked: Merci | done: no change"]
    assert "514819" not in text  # an answer may hold values of the data


def test_a_recap_keeps_the_last_requests_and_bounds_them():
    entries = [entry("action", "before any request")]
    for number in range(20):
        entries += [entry("user", f"request {number} " + "x" * 500)] + [entry("action", f"card {i}") for i in range(30)]
    lines = recap(entries).splitlines()
    assert len(lines) == 1 + MAX_RECAP_REQUESTS and lines[1].startswith("- asked: request 14 ") and "request 19" in lines[-1]
    assert all(len(line) < 1200 for line in lines) and lines[1].count("card ") == 6
    assert recap([]) == "" and recap([entry("text", "an answer"), entry("action", "a card")]) == ""


def test_a_recap_leaves_the_cards_out_for_a_user_who_does_not_share_values():
    """A card holds names the model chose, which can come from the data."""
    entries = [entry("user", "Cherche Dupont"), entry("action", "Layer added: Dupont Jean 0612345678"), entry("user", "Merci")]
    assert recap(entries, with_actions=False).splitlines() == [RECAP_HEADER, "- asked: Cherche Dupont", "- asked: Merci"]
