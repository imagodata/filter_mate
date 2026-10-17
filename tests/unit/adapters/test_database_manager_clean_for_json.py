# -*- coding: utf-8 -*-
"""
DatabaseManager._clean_for_json feeds config.json AND the project_settings
column of the FilterMate database. CONFIG_DATA["CURRENT_PROJECT"]["OPTIONS"]
["ACTIVE_POSTGRESQL"] held the whole URI of a PostgreSQL layer without
authcfg (password='...' included) in place of a connection: it must never be
written, and a password in any other string is masked as a second line of
defence. Method extracted with ast.
"""
import ast
import json
import types
from pathlib import Path
from typing import Any

import pytest

from infrastructure.logging.redaction import mask_uri_secrets

pytestmark = pytest.mark.unit

_MODULE = Path(__file__).resolve().parents[3] / "adapters" / "database_manager.py"
SOURCE = "dbname='gis' host=db user='bob' password='s3cret' table=\"public\".\"roads\" (geom)"


def _cleaner():
    tree = ast.parse(_MODULE.read_text(encoding="utf-8"))
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == "_clean_for_json":
                ns = {"json": json, "Any": Any, "mask_uri_secrets": mask_uri_secrets}
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(_MODULE), "exec"), ns)
                holder = types.SimpleNamespace()
                holder._clean_for_json = types.MethodType(ns["_clean_for_json"], holder)
                return holder._clean_for_json
    raise AssertionError("_clean_for_json not found")


class _Connection:
    def cursor(self):
        return object()


def test_connection_objects_are_dropped():
    clean = _cleaner()
    assert clean({"OPTIONS": {"ACTIVE_POSTGRESQL": _Connection()}}) == {"OPTIONS": {"ACTIVE_POSTGRESQL": None}}


@pytest.mark.parametrize("leftover", [SOURCE, [SOURCE], {"/proj/" + SOURCE: [SOURCE]}, ""])
def test_active_postgresql_is_never_written_as_anything_but_none_or_empty(leftover):
    clean = _cleaner()
    cleaned = clean({"CURRENT_PROJECT": {"OPTIONS": {"ACTIVE_POSTGRESQL": leftover, "IS_ACTIVE_POSTGRESQL": True}}})
    options = cleaned["CURRENT_PROJECT"]["OPTIONS"]
    assert options["ACTIVE_POSTGRESQL"] in (None, "")
    assert options["IS_ACTIVE_POSTGRESQL"] is True
    assert "s3cret" not in json.dumps(cleaned)


def test_a_password_in_any_string_is_masked():
    clean = _cleaner()
    cleaned = clean({"APP": {"note": f"source was {SOURCE}", "list": [SOURCE], "n": 3, "ok": True}})
    dumped = json.dumps(cleaned)
    assert "s3cret" not in dumped
    assert cleaned["APP"]["n"] == 3 and cleaned["APP"]["ok"] is True
    assert "dbname='gis'" in cleaned["APP"]["note"]


def test_plain_settings_are_untouched():
    clean = _cleaner()
    data = {"a": 1, "b": [1, 2, {"c": "text"}], "d": None, "e": 1.5}
    assert clean(data) == data


def test_an_expression_that_mentions_a_passwd_column_is_not_altered():
    clean = _cleaner()
    expression = '"passwd" = \'abc\' AND passwd = \'abc\' AND "pwd"=1'
    assert clean({"filter": expression, "list": [expression]}) == {"filter": expression, "list": [expression]}


def test_a_url_with_credentials_is_masked():
    clean = _cleaner()
    cleaned = clean({"remote": "https://user:hunter2@github.com/org/repo.git"})
    assert "hunter2" not in json.dumps(cleaned) and "github.com" in cleaned["remote"]
