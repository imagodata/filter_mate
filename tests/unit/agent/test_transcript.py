# -*- coding: utf-8 -*-
import json

import pytest

from core.agent.transcript import MAX_CHARS, entry, from_json, to_json, trim

pytestmark = pytest.mark.unit


def test_round_trip_keeps_what_matters():
    entries = [entry("user", "a"), entry("action", "Filter on x", ok=False, detail='"a" = 1', count="3 / 9"),
               entry("text", "done"), entry("note", "n")]
    assert from_json(to_json(entries)) == entries


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
