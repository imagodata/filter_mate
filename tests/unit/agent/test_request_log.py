# -*- coding: utf-8 -*-
"""The log of the requests of the agent in every project (core/agent/request_log.py)."""
import pytest

from core.agent import request_log as log

pytestmark = pytest.mark.unit


def test_an_entry_is_bounded_and_its_outcome_known():
    item = log.entry(1.5, "x" * 900, "Estavar", "/p/estavar.qgz", [f"l{i}" for i in range(30)], "weird")
    assert item["request"] == "x" * 900 and len(item["layers"]) == log.MAX_LAYERS
    assert item["outcome"] == "unchanged" and item["project"] == "Estavar" and item["time"] == 1.5
    assert len(log.entry(0, "y" * 9000, "", "", (), "changed")["request"]) == log.MAX_STORED


def test_short_shows_the_first_lines_with_an_ellipsis():
    assert log.short("abc") == "abc"
    assert log.short("x" * log.MAX_REQUEST) == "x" * log.MAX_REQUEST
    shown = log.short("x" * (log.MAX_REQUEST + 10))
    assert shown == "x" * log.MAX_REQUEST + "…" and len(shown) == log.MAX_REQUEST + 1


def test_the_oldest_go_beyond_the_limit():
    entries = []
    for number in range(5):
        entries = log.appended(entries, log.entry(number, f"r{number}", "p", "", (), "changed"), limit=3)
    assert [item["request"] for item in entries] == ["r2", "r3", "r4"]


def test_a_round_trip_keeps_the_entries():
    entries = [log.entry(10, "garde les communes", "Toulouse", "/t.qgz", ["communes"], "changed")]
    assert log.from_json(log.to_json(entries)) == entries


@pytest.mark.parametrize("text", ["", "not json", "{}", "[1, \"a\", {\"request\": \"\"}]", "[{\"time\": \"x\", \"request\": \"r\"}]"])
def test_what_is_not_an_entry_is_left_out(text):
    assert log.from_json(text) == []


def test_an_entry_of_an_older_shape_is_read():
    assert log.from_json('[{"request": "r", "time": 3}]') == [log.entry(3, "r", "", "", (), "")]
