# -*- coding: utf-8 -*-
"""
The PostgreSQL cleanup helpers shared by every FilterMate cleanup.

- identifiers are quoted (quotes doubled), never "sanitised": ``routes-2024`` and
  ``Routes Nat`` reach the server as they are;
- nothing is dropped with CASCADE, dependents go first, and an object counts as
  dropped only once the catalog no longer has it;
- a schema is dropped only if it is one of FilterMate's own and holds nothing else.
"""
import pytest

from infrastructure.database.temp_objects import (
    pg_drop_filtermate_schema,
    pg_drop_session_views,
    pg_drop_temp_objects,
    pg_find_temp_objects,
    pg_quote_ident,
    pg_schema_content,
)
from tests.unit.pg_fakes import FakeConnection, FakePgCatalog

pytestmark = pytest.mark.unit

SID = "ab12cd34"


def test_quoting_doubles_quotes_and_keeps_the_rest():
    assert pg_quote_ident("routes-2024") == '"routes-2024"'
    assert pg_quote_ident("Routes Nat") == '"Routes Nat"'
    assert pg_quote_ident('a"b') == '"a""b"'
    assert pg_quote_ident("Bâtiments") == '"Bâtiments"'


class TestFind:
    CATALOG = [
        ("matview", "filtermate_temp", f"fm_temp_mv_{SID}_abc"),
        ("table", "ref", "fm_temp_buf_routes-2024_ab12cd34"),
        ("table", "ref", "fm_temp_buf_Routes Nat_ab12cd34"),
        ("table", "public", "filtermate_catalog"),
        ("matview", "public", "mv_20231231_bati"),
        ("matview", "filter_mate_temp", f"mv_{SID}_legacy"),
    ]

    @pytest.mark.parametrize("overbroad", [False, True])
    def test_only_filtermate_objects_whatever_the_preselection_returns(self, overbroad):
        catalog = FakePgCatalog(self.CATALOG, overbroad=overbroad)
        found = pg_find_temp_objects(FakeConnection(catalog).cursor())
        assert sorted(found) == sorted([
            ("matview", "filtermate_temp", f"fm_temp_mv_{SID}_abc"),
            ("table", "ref", "fm_temp_buf_routes-2024_ab12cd34"),
            ("table", "ref", "fm_temp_buf_Routes Nat_ab12cd34"),
            ("matview", "filter_mate_temp", f"mv_{SID}_legacy"),
        ])


class TestDropObjects:
    def test_names_are_quoted_not_sanitised(self):
        catalog = FakePgCatalog([("table", "Ref-2024", "fm_temp_buf_routes-2024_ab12cd34"),
                                 ("table", "ref", "fm_temp_buf_Routes Nat_ab12cd34")])
        connection = FakeConnection(catalog)

        dropped = pg_drop_temp_objects(connection, connection.cursor(), list(catalog.objects))

        assert len(dropped) == 2 and catalog.objects == []
        statements = catalog.statements()
        assert 'DROP TABLE "Ref-2024"."fm_temp_buf_routes-2024_ab12cd34"' in statements
        assert 'DROP TABLE "ref"."fm_temp_buf_Routes Nat_ab12cd34"' in statements

    def test_no_cascade_and_dependents_first(self):
        catalog = FakePgCatalog(
            [("matview", "filtermate_temp", f"fm_temp_mv_{SID}_abc"),
             ("matview", "filtermate_temp", f"fm_temp_mv_{SID}_abc_dump")],
            dependents={f"fm_temp_mv_{SID}_abc": [f"fm_temp_mv_{SID}_abc_dump"]})
        connection = FakeConnection(catalog)

        # listed in the wrong order on purpose: the retry passes cope
        objects = [("matview", "filtermate_temp", f"fm_temp_mv_{SID}_abc"),
                   ("matview", "filtermate_temp", f"fm_temp_mv_{SID}_abc_dump")]
        dropped = pg_drop_temp_objects(connection, connection.cursor(), objects)

        assert len(dropped) == 2 and catalog.objects == []
        assert all("CASCADE" not in s for s in catalog.statements())

    def test_user_objects_in_the_list_are_not_dropped(self):
        catalog = FakePgCatalog([("table", "public", "filtermate_catalog"),
                                 ("table", "ref", "fm_temp_buf_x_ab12cd34")])
        connection = FakeConnection(catalog)

        dropped = pg_drop_temp_objects(connection, connection.cursor(), list(catalog.objects))

        assert dropped == [("table", "ref", "fm_temp_buf_x_ab12cd34")]
        assert catalog.has("filtermate_catalog")

    def test_an_object_that_does_not_disappear_is_not_counted(self):
        catalog = FakePgCatalog([("table", "ref", "fm_temp_buf_x_ab12cd34")], ghosts=["fm_temp_buf_x_ab12cd34"])
        connection = FakeConnection(catalog)

        assert pg_drop_temp_objects(connection, connection.cursor(), list(catalog.objects)) == []

    def test_an_object_already_gone_is_not_counted(self):
        catalog = FakePgCatalog([("table", "ref", "fm_temp_buf_x_ab12cd34")])
        connection = FakeConnection(catalog)

        gone = [("table", "ref", "fm_temp_buf_vanished_ab12cd34")]
        assert pg_drop_temp_objects(connection, connection.cursor(), gone) == []
        assert connection.rollbacks >= 1

    def test_a_refused_drop_rolls_back_and_the_others_go_on(self):
        catalog = FakePgCatalog([("table", "ref", "fm_temp_buf_a_ab12cd34"), ("table", "ref", "fm_temp_buf_b_ab12cd34")],
                                undroppable=["fm_temp_buf_a_ab12cd34"])
        connection = FakeConnection(catalog)

        dropped = pg_drop_temp_objects(connection, connection.cursor(), list(catalog.objects))

        assert dropped == [("table", "ref", "fm_temp_buf_b_ab12cd34")]
        assert connection.rollbacks >= 1 and catalog.has("fm_temp_buf_a_ab12cd34")


class TestDropSchema:
    def test_a_schema_of_filtermate_objects_only_is_emptied_then_dropped_without_cascade(self):
        catalog = FakePgCatalog([("matview", "filter_mate_temp", f"fm_temp_mv_{SID}_x"),
                                 ("table", "filter_mate_temp", "fm_temp_src_sel_0123abcd")])
        result = pg_drop_filtermate_schema(FakeConnection(catalog), "filter_mate_temp")

        assert result["status"] == "dropped" and len(result["dropped"]) == 2
        assert "filter_mate_temp" not in catalog.schemas
        assert catalog.statements()[-1] == 'DROP SCHEMA "filter_mate_temp"'
        assert all("CASCADE" not in s for s in catalog.statements())

    def test_a_legacy_session_view_is_not_foreign(self):
        catalog = FakePgCatalog([("matview", "filter_mate_temp", f"mv_{SID}_legacy")])

        assert pg_drop_filtermate_schema(FakeConnection(catalog), "filter_mate_temp")["status"] == "dropped"

    def test_a_user_table_keeps_the_schema(self):
        catalog = FakePgCatalog([("matview", "filtermate_temp", f"fm_temp_mv_{SID}_x"),
                                 ("table", "filtermate_temp", "mine")])

        result = pg_drop_filtermate_schema(FakeConnection(catalog), "filtermate_temp")

        assert result["status"] == "foreign" and result["foreign"] == ["mine"]
        assert catalog.statements() == []

    def test_a_user_view_on_a_filtermate_object_keeps_the_schema_content(self):
        catalog = FakePgCatalog([("matview", "filtermate_temp", f"fm_temp_mv_{SID}_x"),
                                 ("view", "filtermate_temp", "user_view")])

        assert pg_drop_filtermate_schema(FakeConnection(catalog), "filtermate_temp")["status"] == "foreign"

    @pytest.mark.parametrize("schema", ["public", "ref", "Filtermate_temp", "filtermate_temp_old"])
    def test_other_schemas_are_refused(self, schema):
        catalog = FakePgCatalog([], schemas=[schema])

        assert pg_drop_filtermate_schema(FakeConnection(catalog), schema)["status"] == "not_filtermate_schema"
        assert catalog.statements() == []

    def test_an_absent_schema(self):
        assert pg_drop_filtermate_schema(FakeConnection(FakePgCatalog()), "filtermate_temp")["status"] == "absent"

    def test_a_schema_that_cannot_be_dropped_reports_an_error_and_rolls_back(self):
        catalog = FakePgCatalog([("table", "filtermate_temp", "fm_temp_tbl_x")], undroppable=["fm_temp_tbl_x"])
        connection = FakeConnection(catalog)

        assert pg_drop_filtermate_schema(connection, "filtermate_temp")["status"] == "error"
        assert connection.rollbacks >= 1 and "filtermate_temp" in catalog.schemas


def test_schema_content_splits_filtermate_and_foreign():
    catalog = FakePgCatalog([("matview", "filtermate_temp", f"fm_temp_mv_{SID}_x"),
                             ("table", "filtermate_temp", "mine"),
                             ("matview", "filtermate_temp", f"mv_{SID}_legacy")])

    objects, foreign = pg_schema_content(FakeConnection(catalog).cursor(), "filtermate_temp")

    assert sorted(n for _k, _s, n in objects) == sorted([f"fm_temp_mv_{SID}_x", f"mv_{SID}_legacy"])
    assert foreign == ["mine"]


class TestDropSessionViews:
    """The session cleanup at unload: this session's views in FilterMate's schemas, no CASCADE."""

    OBJECTS = [
        ("matview", "filter_mate_temp", f"fm_temp_mv_{SID}_a"),
        ("matview", "filter_mate_temp", f"fm_temp_mv_{SID}_a_dump"),
        ("matview", "filtermate_temp", f"fm_temp_mv_{SID}_old_schema"),
        ("matview", "filter_mate_temp", f"mv_{SID}_legacy"),
        ("matview", "filter_mate_temp", "fm_temp_mv_99999999_other_session"),
        ("matview", "filter_mate_temp", f"fm_temp_mvXab12cd34_x"),
        ("matview", "public", f"mv_{SID}_in_public"),               # legacy name outside our schemas
        ("view", "filter_mate_temp", "user_view"),
    ]

    def test_only_this_sessions_views_of_the_temp_schemas_go(self):
        catalog = FakePgCatalog(self.OBJECTS, dependents={f"fm_temp_mv_{SID}_a": [f"fm_temp_mv_{SID}_a_dump"]})
        connection = FakeConnection(catalog)

        dropped = pg_drop_session_views(connection, connection.cursor(), ["filter_mate_temp", "filtermate_temp"], SID)

        assert sorted(n for _k, _s, n in dropped) == sorted([
            f"fm_temp_mv_{SID}_a", f"fm_temp_mv_{SID}_a_dump", f"fm_temp_mv_{SID}_old_schema", f"mv_{SID}_legacy"])
        assert sorted(n for _k, _s, n in catalog.objects) == sorted([
            "fm_temp_mv_99999999_other_session", "fm_temp_mvXab12cd34_x", f"mv_{SID}_in_public", "user_view"])
        assert all("CASCADE" not in s for s in catalog.statements())

    def test_a_session_id_with_like_characters_matches_nothing_else(self):
        catalog = FakePgCatalog([("matview", "filter_mate_temp", f"fm_temp_mv_{SID}_a")])
        connection = FakeConnection(catalog)

        assert pg_drop_session_views(connection, connection.cursor(), ["filter_mate_temp"], "%") == []
        assert pg_drop_session_views(connection, connection.cursor(), ["filter_mate_temp"], "ab12_d34") == []
        assert catalog.has(f"fm_temp_mv_{SID}_a")
