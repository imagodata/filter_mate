# -*- coding: utf-8 -*-
"""The favorites of a saved project live in its .qgz; the SQLite of each computer keeps a working copy (2026-11-24).

Measured in QGIS 3.44 with two profiles before: the copy in the .qgz was written when the project was opened, never on
Ctrl+S, and read back only when the computer had no favorite for the project, so a favorite added on one computer
reached another one session late, and never when that computer had favorites of its own.
"""
import json

import pytest

from core.domain import project_favorites as pf

pytestmark = pytest.mark.unit


def fav(fid, name, updated="2026-11-20T10:00:00", **extra):
    return {"id": fid, "name": name, "expression": f'"rank" < {len(name)}', "updated_at": updated, **extra}


class TestPayload:
    def test_is_the_same_text_for_the_same_favorites(self):
        """Written at each change only when it differs: the project must not turn dirty for nothing."""
        first = pf.project_payload([fav("b", "B"), fav("a", "A")])
        assert first == pf.project_payload([fav("a", "A"), fav("b", "B")])

    def test_keeps_the_usage_of_each_computer_out(self):
        payload = json.loads(pf.project_payload([fav("a", "A", use_count=7, last_used_at="2026-11-23T09:00:00")]))
        assert payload["authoritative"] is True
        assert "use_count" not in payload["favorites"][0] and "last_used_at" not in payload["favorites"][0]

    def test_empty_values_give_the_same_text(self):
        """The SQLite gives None where a favorite made in memory has {}: written again at each opening otherwise."""
        assert pf.project_payload([fav("a", "A", remote_layers={}, tags=[], description="")]) == \
            pf.project_payload([fav("a", "A", remote_layers=None, tags=None, description=None)])

    def test_file_ids(self):
        assert pf.file_ids([fav("b", "B"), fav("a", "A"), {"name": "no id"}]) == ["a", "b"]
        assert pf.file_ids(None) == []

    def test_an_empty_list_is_said(self):
        """Every favorite removed: the other computers must remove theirs too, so the entry stays."""
        stored, authoritative = pf.read_payload(pf.project_payload([]))
        assert stored == [] and authoritative

    def test_the_readers_of_the_backup_still_find_the_favorites(self):
        """operations.py and the Processing algorithm read data['favorites']."""
        assert json.loads(pf.project_payload([fav("a", "A")]))["favorites"][0]["name"] == "A"


class TestRead:
    @pytest.mark.parametrize("text", ["", None, "not json", "[]", '{"favorites": "x"}'])
    def test_nothing_usable_is_no_entry(self, text):
        assert pf.read_payload(text) == (None, False)

    def test_a_favorite_without_expression_gets_an_empty_one(self):
        stored, _ = pf.read_payload(json.dumps({"favorites": [{"name": "N", "expression": None}]}))
        assert stored[0]["expression"] == ""

    def test_the_backup_of_before_is_not_authoritative(self):
        legacy = json.dumps({"version": "1.0", "backup_type": "project_file", "favorites": [fav("a", "A")]})
        stored, authoritative = pf.read_payload(legacy)
        assert [row["name"] for row in stored] == ["A"] and not authoritative


class TestReconcile:
    def test_no_entry_keeps_the_computer(self):
        local = [fav("a", "A")]
        assert pf.reconcile(local, None, False) == local

    def test_the_project_wins(self):
        """Option 1 (2026-11-24): removed on another computer, removed here; changed there, changed here."""
        local = [fav("a", "A"), fav("b", "B old")]
        stored = [fav("b", "B new"), fav("c", "C")]
        names = sorted(row["name"] for row in pf.reconcile(local, stored, True, known=["a", "b"]))
        assert names == ["B new", "C"]

    def test_a_favorite_made_here_and_never_saved_stays(self):
        """Review of 2026-11-24: QGIS closed without saving, or a project this computer cannot write, removed the
        favorites made here at the next opening. Only what the file had and no longer has goes."""
        local = [fav("a", "A"), fav("new", "made here")]
        names = sorted(row["name"] for row in pf.reconcile(local, [], True, known=["a"]))
        assert names == ["made here"]

    def test_the_project_wins_but_the_usage_stays_this_computers(self):
        local = [fav("a", "A", use_count=5, last_used_at="2026-11-22T08:00:00")]
        result = pf.reconcile(local, [fav("a", "A")], True)
        assert result[0]["use_count"] == 5 and result[0]["last_used_at"] == "2026-11-22T08:00:00"

    def test_the_backup_of_before_is_merged_without_copies(self):
        local = [fav("a", "A", updated="2026-11-20T10:00:00"), fav("b", "B")]
        stored = [fav("a", "A", updated="2026-11-21T10:00:00", expression="newer"),  # same id, newer
                  fav("x", "B", updated="2026-11-19T10:00:00", expression="older"),  # same name, older
                  fav("c", "C")]
        result = {row["name"]: row for row in pf.reconcile(local, stored, False)}
        assert sorted(result) == ["A", "B", "C"]
        assert result["A"]["expression"] == "newer"
        assert result["B"]["id"] == "b" and result["B"]["expression"] != "older"

    def test_a_newer_backup_of_the_same_name_keeps_the_id_of_this_computer(self):
        local = [fav("b", "B", updated="2026-11-19T10:00:00")]
        stored = [fav("x", "B", updated="2026-11-21T10:00:00", expression="newer")]
        [row] = pf.reconcile(local, stored, False)
        assert row["id"] == "b" and row["expression"] == "newer"

    def test_a_favorite_without_id_gets_one(self):
        [row] = pf.reconcile([], [{"name": "N", "expression": "1"}], True)
        assert row["id"]
