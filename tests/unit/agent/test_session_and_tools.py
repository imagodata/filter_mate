# -*- coding: utf-8 -*-
"""The conversation rules, argument checks, tool failures, and the evaluation bench."""
import importlib.util
import json
import math
import sys
from pathlib import Path

import pytest

from core.agent.json_schema import validate
from core.agent.messages import (
    ROLE_ASSISTANT, ROLE_USER, STOP_END, STOP_MAX_TOKENS, STOP_OTHER, STOP_REFUSAL, STOP_TOOL_USE, Message, StreamFailure,
    ProviderError, TextPart, ToolCallPart, TurnComplete, ToolResultPart, Usage,
)
from core.agent.providers import create_provider
from core.agent.providers.base import ProviderConfig
from core.agent.session import CAUSE_FAILED, AgentLimits, AgentSession, run_exchange
from core.agent.sql_guard import expression_problem, filter_problem, quoted_identifiers
from core.agent.tool_catalog import CHAT_ONLY, MCP_ONLY, NOT_IN_CHAT, SETTINGS_TOOLS, SKILL_TOOLS, ToolSpec, chat_tools, load_catalog
from core.agent.tool_executor import MAX_RESULT_CHARS, ToolExecutor, ToolFailure, WithImages, bounded_json

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = {"type": "object", "required": ["name"], "properties": {
    "name": {"type": "string", "minLength": 1}, "size": {"type": "number", "default": 2.5}}}
READ = ToolSpec("read", "Read something here.", SCHEMA, read_only=True)
EXPORT = ToolSpec("export", "Write a file there.", {"type": "object", "properties": {}}, destructive=True)


def session(limit=12, tools=(READ,)):
    return AgentSession(create_provider(ProviderConfig("anthropic", "m")), list(tools), "S", AgentLimits(limit))


def call(tool="read", call_id="c1", **arguments):
    return ToolCallPart(call_id, tool, arguments)


def turn(stop, *parts, usage=Usage(1, 2)):
    return TurnComplete(Message(ROLE_ASSISTANT, parts), stop, usage)


class TestValidate:
    @pytest.mark.parametrize("value,schema", [
        (1, {"type": "integer"}), (1.0, {"type": "integer"}), (True, {"type": "boolean"}), (None, {"type": "null"}),
        ("a", {"anyOf": [{"type": "integer"}, {"type": "string"}]}), ("x", {"enum": ["x"]}),
        ([1], {"type": "array", "items": {"type": "integer"}, "minItems": 1}),
        ({"a": 1}, {"type": "object", "properties": {"a": {"type": "integer"}}, "additionalProperties": False}),
        (5, {"minimum": 5, "maximum": 5}), ({"x": 1}, {"type": "object", "futureKeyword": 1}),
    ])
    def test_valid(self, value, schema):
        assert validate(value, schema) == []

    @pytest.mark.parametrize("value,schema", [
        (True, {"type": "integer"}), (True, {"type": "number"}), (1.5, {"type": "integer"}), ("1", {"type": "number"}),
        (math.nan, {"type": "number"}), (math.inf, {"type": "number"}), (math.nan, {}), ("y", {"enum": ["x"]}),
        (None, {"anyOf": [{"type": "integer"}, {"type": "string"}]}), ("", {"minLength": 1}), ("ab", {"maxLength": 1}),
        (0, {"exclusiveMinimum": 0}), (6, {"maximum": 5}), ([], {"minItems": 1}), ([1, 2], {"maxItems": 1}),
        (["a"], {"items": {"type": "integer"}}), ({}, {"required": ["a"]}),
        ({"z": 1}, {"properties": {}, "additionalProperties": False}),
    ])
    def test_invalid(self, value, schema):
        assert validate(value, schema)

    def test_errors_are_bounded(self):
        assert len(validate([""] * 500, {"items": {"type": "integer"}})) == 10


class TestFilterGuard:
    @pytest.mark.parametrize("expression", [
        '"a" = 1', "\"a\" = 'x;y'", '"a;b" = 1', "\"a\" = 'it''s; -- fine'", "\"a\" = 'x' AND \"b\" > 1 - 1",
        "lower(\"nom\") LIKE 'saint%'", '"a" IN (1, 2, 3)', "\"n\"::text = '1'", 'CAST("a" AS integer) > 1',
        'NOT ("a" = 1)', '"a" IS NOT NULL', "population > 1e3", '"x" BETWEEN 1.5 AND .5', '"t"."c" = 1',
        "\"é\" = 'Résidentiel'", '"a" <> 1 OR "b" != 2', "\"a\" || \"b\" = 'xy'",
        "CASE WHEN \"a\" = 1 THEN 1 ELSE 0 END = 1", "\"a\" NOT IN ('b', 'c')",
    ])
    def test_a_plain_condition_passes(self, expression):
        assert filter_problem(expression) == ""

    @pytest.mark.parametrize("expression", [
        "1=1; DROP TABLE t", "1=1 -- x", "1=1 /* x */", "\"a\" = 'x'; DELETE FROM t", "\"a\" = 'it''s'; x",
        # Hide the ';' from a scanner that only knows ' and ": both ran a real DROP TABLE on PostGIS.
        "E'\\'' IS NOT NULL; DROP TABLE victim; --'",
        "$a$'$a$ IS NOT NULL; SET TRANSACTION READ WRITE; DROP TABLE victim3; COMMIT; --'",
        "pg_sleep(0) IS NOT NULL", "(SELECT count(*) FROM secret) >= 0",
        "\"a\" IN (SELECT \"a\" FROM \"b\")", "x IN (TABLE secret)", "x IN (VALUES (1))",
        '"pg_sleep"(1) IS NULL', 'pg_catalog.lower("a") = 1', "pg_read_file('/etc/passwd') = ''",
        "1=1) OR (1=1", '("a" = 1', "'a\\'", "\"a", "[a] = 1", "`a` = 1", "'victim'::regclass IS NULL",
        "U&'x' = 1", "B'1' = 1", "X'1' = 1", "N'x' = 1", "e\"a\" = 1", "", "   ", "a @ b", "a # b", "1=1\x00",
    ])
    def test_anything_else_is_refused(self, expression):
        assert filter_problem(expression)

    @pytest.mark.parametrize("expression", [
        '"x" = 1 OR foo\u02bcbar', '"x" = \u02bc1\u02bc', '"x"\u00a0= 1', '"x" = 1\u2028OR 1=1', '"x" = \uff12',
        '"x" = \u0661', "ann\u00e9e > 2000",  # outside quotes, ASCII only: a name with an accent is quoted
        "\"x\" = 'a\uff3c'", '"a\uff02" = 1', "\"x\" = 'a\uff07'",  # full-width backslash and quotes, even quoted
    ])
    def test_outside_quotes_ascii_only_and_no_full_width_escape_inside(self, expression):
        assert filter_problem(expression)
        assert expression_problem(expression)

    def test_a_quoted_name_or_text_with_an_accent_still_passes(self):
        assert filter_problem("\"ann\u00e9e\" > 2000 AND \"nom\" = 'B\u00e9ziers'\t") == ""

    @pytest.mark.parametrize("expression", ['"a\\"" OR sleep(5) #".x', '"a\\"" OR sleep(5) #".x = 1', '"a\\" = 1',
                                            '"C:\\data" = 1'])
    def test_a_backslash_in_a_quoted_name_is_refused(self, expression):
        # Through OGR on MySQL a backslash escapes the quote and # starts a comment: the first one would run sleep(5).
        assert "backslash" in filter_problem(expression)
        assert expression_problem(expression)


class TestExpressionGuard:
    @pytest.mark.parametrize("expression", [
        '"pop" > 3', "\"nom\" ILIKE 'saint%'", "area($geometry) > 1000", '$area > 5', "year(\"d\") = 2020", 'to_int("a") > 1',
    ])
    def test_a_plain_condition_passes(self, expression):
        assert expression_problem(expression) == ""

    @pytest.mark.parametrize("expression", [
        "sqlite_fetch_and_increment('/x.sqlite','t','id','k','a',map('s','(select 1)'))>0",
        "\"pop\" <= ascii(env('FM_SECRET'))", "file_exists('/etc/passwd')", "aggregate('l','concatenate',\"n\") = ''",
        "generate_series(1,2000000000) IS NULL", "load_layer('x','ogr') IS NULL", "eval('1') = 1", "@layer IS NULL", "$foo > 1",
        "exif('/x.jpg') = 1", "'a'; b",
    ])
    def test_anything_else_is_refused(self, expression):
        assert expression_problem(expression)

    def test_a_filter_stays_stricter(self):
        assert filter_problem("area($geometry) > 1")


class TestQuotedIdentifiers:
    @pytest.mark.parametrize("expression,names", [
        ('"a" = 1 AND "b c" = 2', ["a", "b c"]),
        ("\"a\" = 'x \"not\" y'", ["a"]),
        ('"t"."col" = 1', ["col"]),
        ('"we""ird" = 1', ['we"ird']),
        ("\"a\" = 'it''s' OR \"b\" = 1", ["a", "b"]),
        ("population > 1", []),
    ])
    def test_names(self, expression, names):
        assert quoted_identifiers(expression) == names


class TestSession:
    def test_session_shows_what_it_sends(self):
        chat = session()
        assert chat.system == "S" and chat.tools == (READ,)

    def test_tools_then_done_and_usage(self):
        chat = session()
        chat.add_user_text("hi")
        decision = chat.accept_turn(turn(STOP_TOOL_USE, TextPart("looking"), call("x")))
        assert decision.status == "run_tools" and decision.calls[0].name == "x" and decision.text == "looking"
        chat.add_tool_results([ToolResultPart("c1", "ok")])
        decision = chat.accept_turn(turn(STOP_END, TextPart("done")))
        assert decision.status == "done" and chat.assistant_text() == "done"
        assert chat.usage == Usage(2, 4)
        assert [m.role for m in chat.messages] == [ROLE_USER, ROLE_ASSISTANT, ROLE_USER, ROLE_ASSISTANT]

    def test_refusal_stays_out_of_the_history(self):
        chat = session()
        chat.add_user_text("hi")
        decision = chat.accept_turn(turn(STOP_REFUSAL, TextPart("partial"), call()))
        assert decision.status == "stopped" and decision.reason == "refused" and not decision.calls
        assert chat.messages == ()  # the refused request is not replayed with the next one

    def test_calls_cut_by_max_tokens_are_never_run_nor_kept(self):
        chat = session()
        chat.add_user_text("hi")
        decision = chat.accept_turn(turn(STOP_MAX_TOKENS, TextPart("so"), call()))
        assert decision.status == "stopped" and decision.reason == "truncated" and not decision.calls
        assert len(chat.messages) == 1

    def test_text_cut_by_max_tokens_is_kept_and_flagged(self):
        chat = session()
        chat.add_user_text("hi")
        decision = chat.accept_turn(turn(STOP_MAX_TOKENS, TextPart("so")))
        assert decision.status == "stopped" and len(chat.messages) == 2

    @pytest.mark.parametrize("stop", [STOP_OTHER, STOP_END])
    def test_calls_of_a_turn_that_did_not_stop_for_them_are_dropped(self, stop):
        chat = session()
        chat.add_user_text("hi")
        decision = chat.accept_turn(turn(stop, call()))
        assert decision.status == "stopped" and not decision.calls and len(chat.messages) == 1

    def test_an_empty_turn_stays_out_of_the_history(self):
        chat = session()
        chat.add_user_text("hi")
        assert chat.accept_turn(turn(STOP_END)).status == "done"
        assert len(chat.messages) == 1

    def test_a_request_that_ran_nothing_is_forgotten_alone(self):
        chat = session()
        chat.add_user_text("first")
        chat.accept_turn(turn(STOP_END, TextPart("ok")))
        chat.add_user_text("second")
        assert chat.interrupt_request(CAUSE_FAILED) == 0
        assert [m.text for m in chat.messages] == ["first", "ok"]

    def test_turn_limit_stops_without_a_dangling_call(self):
        chat = session(limit=2)
        chat.add_user_text("hi")
        assert chat.accept_turn(turn(STOP_TOOL_USE, call())).status == "run_tools"
        chat.add_tool_results([ToolResultPart("c1", "ok")])
        decision = chat.accept_turn(turn(STOP_TOOL_USE, call(call_id="c2")))
        assert decision.status == "stopped" and decision.reason == "turn_limit"
        assert isinstance(chat.messages[-1].parts[0], ToolResultPart)

    def test_the_model_is_told_before_the_limit(self):
        chat = session(limit=4)
        chat.add_user_text("hi")
        notes = []
        for number in range(3):
            assert chat.accept_turn(turn(STOP_TOOL_USE, call(call_id=f"c{number}"))).status == "run_tools"
            chat.add_tool_results([ToolResultPart(f"c{number}", "ok")])
            notes.append([part.text for part in chat.messages[-1].parts if isinstance(part, TextPart)])
        assert notes[0] == [] and "2 model turns left" in notes[1][0] and "1 model turns left" in notes[2][0]
        assert isinstance(chat.messages[-1].parts[0], ToolResultPart)  # the results first, then the note
        wire = json.loads(chat.next_request().body)["messages"][-1]["content"]
        assert [block["type"] for block in wire] == ["tool_result", "text"]

    def test_a_new_request_resets_the_limit(self):
        chat = session(limit=1)
        chat.add_user_text("a")
        assert chat.accept_turn(turn(STOP_END, TextPart("x"))).status == "done"
        chat.add_user_text("b")
        assert chat.accept_turn(turn(STOP_END, TextPart("y"))).status == "done"


class FakeTransport:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.bodies = []

    def send(self, request, _session):
        self.bodies.append(json.loads(request.body))
        return self.responses.pop(0)


class TestExchange:
    def executor(self, seen):
        return ToolExecutor([READ, EXPORT], {"read": lambda a: seen.append(("read", a)) or {"ok": True},
                                             "export": lambda a: seen.append(("export", a)) or {"written": True}})

    def test_every_call_of_a_turn_is_answered_in_one_message(self):
        seen = []
        chat = session()
        transport = FakeTransport(
            [turn(STOP_TOOL_USE, call("read", call_id="1"), call("read", call_id="2"))],
            [turn(STOP_END, TextPart("done"))])
        run_exchange(chat, "go", transport, self.executor(seen))
        answers = chat.messages[2].parts
        assert [part.call_id for part in answers] == ["1", "2"]
        assert all(part.is_error for part in answers)  # both lack the required "name"
        assert seen == []

    def test_export_waits_for_the_user(self):
        for accepted in (False, True):
            seen = []
            chat = session()
            transport = FakeTransport([turn(STOP_TOOL_USE, call("export"))], [turn(STOP_END, TextPart("x"))])
            result = run_exchange(chat, "go", transport, self.executor(seen), confirm=lambda c: accepted)
            assert [c.name for c in result.confirmations] == ["export"]
            assert bool(seen) is accepted
            assert chat.messages[2].parts[0].is_error is (not accepted)

    def test_failure_ends_the_exchange_and_forgets_the_request(self):
        failure = StreamFailure(ProviderError("auth", "bad key", status=401))
        chat = session()
        result = run_exchange(chat, "go", FakeTransport([failure]), self.executor([]))
        assert result.error.kind == "auth" and chat.messages == ()

    def test_a_failure_after_a_change_keeps_it_with_a_note(self):
        failure = StreamFailure(ProviderError("server", "Overloaded", status=529))
        chat = session(tools=(READ, EXPORT))
        transport = FakeTransport([turn(STOP_TOOL_USE, call("export"))], [failure])
        result = run_exchange(chat, "go", transport, self.executor([]), confirm=lambda c: True)
        assert result.error.kind == "server"
        assert [m.role for m in chat.messages] == [ROLE_USER, ROLE_ASSISTANT, ROLE_USER]
        assert isinstance(chat.messages[-1].parts[0], ToolResultPart) and "broke off here" in chat.messages[-1].text

    def test_a_failure_after_readings_only_forgets_the_request(self):
        failure = StreamFailure(ProviderError("server", "Overloaded", status=529))
        chat = session(tools=(READ, EXPORT))
        transport = FakeTransport([turn(STOP_TOOL_USE, call("read", name="x"))], [failure])
        result = run_exchange(chat, "go", transport, self.executor([]))
        assert result.error.kind == "server" and chat.messages == ()

    def test_a_declined_change_is_no_change(self):
        failure = StreamFailure(ProviderError("server", "Overloaded", status=529))
        chat = session(tools=(READ, EXPORT))
        transport = FakeTransport([turn(STOP_TOOL_USE, call("export"))], [failure])
        run_exchange(chat, "go", transport, self.executor([]), confirm=lambda c: False)
        assert chat.messages == ()

    def test_nobody_confirms_an_invalid_export(self):
        strict = ToolSpec("export", "Write a file there.", {"type": "object", "required": ["a"]}, destructive=True)
        executor = ToolExecutor([strict], {"export": lambda a: 1 / 0})
        assert not executor.needs_confirmation(call("export"))
        assert executor.needs_confirmation(call("export", a=1))
        assert not executor.needs_confirmation(ToolCallPart("c", "export", {"a": 1}, parse_error="x"))

    def test_no_turn_at_all_is_an_error(self):
        assert run_exchange(session(), "go", FakeTransport([]), self.executor([])).error.kind == "stream"


class TestExecutor:
    def run(self, handler, the_call):
        return ToolExecutor([READ], {"read": handler}).execute(the_call)

    def test_defaults_are_filled_and_result_is_json(self):
        result = self.run(lambda a: a, call("read", name="x"))
        assert not result.is_error and json.loads(result.content) == {"name": "x", "size": 2.5}

    def test_unknown_tool(self):
        assert self.run(lambda a: a, call("nope")).is_error

    def test_images_go_beside_the_json(self):
        result = self.run(lambda a: WithImages({"width": 3}, (("image/jpeg", "QUJD"),)), call("read", name="x"))
        assert json.loads(result.content) == {"width": 3} and result.images == (("image/jpeg", "QUJD"),)
        assert self.run(lambda a: {"width": 3}, call("read", name="x")).images == ()

    def test_the_images_of_the_map_are_the_mcp_server_s_alone(self):
        names = {tool.name for tool in chat_tools()}
        assert not names & {tool.name for tool in MCP_ONLY}
        assert all(tool.read_only and tool.open_world and not tool.requires_confirmation for tool in MCP_ONLY)
        assert {tool.name for tool in MCP_ONLY} == {"map_image", "contact_sheet"}

    def test_bad_json_is_explained(self):
        result = self.run(lambda a: 1 / 0, ToolCallPart("c", "read", {}, parse_error="line 1"))
        assert result.is_error and "line 1" in result.content

    def test_invalid_arguments_never_reach_the_handler(self):
        result = self.run(lambda a: 1 / 0, call("read"))
        assert result.is_error and "name" in result.content

    def test_tool_failure_is_shown(self):
        def handler(_):
            raise ToolFailure("Layer not found.")
        assert self.run(handler, call("read", name="x")).content == "Layer not found."

    def test_unexpected_error_text_stays_in_the_log(self):
        def handler(_):
            raise RuntimeError("/home/secret/path.gpkg")
        result = self.run(handler, call("read", name="x"))
        assert result.is_error and "secret" not in result.content

    def test_long_result_is_bounded_and_says_so(self):
        text = bounded_json('"' * (MAX_RESULT_CHARS * 2))
        assert json.loads(text)["truncated"] is True and len(text) < MAX_RESULT_CHARS + 200

    def test_a_long_list_loses_whole_rows_and_stays_json(self):
        rows = [{"name": f"layer {number}", "note": "x" * 200} for number in range(400)]
        text = bounded_json({"layers": rows, "count": 400})
        answer = json.loads(text)
        kept = answer["layers"]
        assert len(text) <= MAX_RESULT_CHARS and 0 < len(kept) < 400 and kept == rows[:len(kept)]
        assert answer["layers_omitted"] == 400 - len(kept) and answer["count"] == 400 and "fewer" in answer["note"]

    def test_a_single_huge_row_is_still_cut(self):
        text = bounded_json({"layers": ["x" * (MAX_RESULT_CHARS * 2)], "values": []})
        assert json.loads(text)["truncated"] is True

    def test_a_result_that_cannot_be_serialized_is_an_answer(self):
        loop = {}
        loop["self"] = loop
        assert self.run(lambda a: loop, call("read", name="x")).is_error

    def test_huge_numbers_do_not_raise(self):
        schema = {"type": "object", "properties": {"n": {"type": "integer", "maximum": 5}}}
        tool = ToolSpec("read", "Read something here.", schema)
        executor = ToolExecutor([tool], {"read": lambda a: a})
        assert executor.execute(ToolCallPart("c", "read", {"n": 10 ** 400})).is_error
        assert validate(1e300, {"type": "integer"})


class TestCatalog:
    def test_schemas_are_self_contained(self):
        text = json.dumps([tool.input_schema for tool in load_catalog()])
        assert "$ref" not in text and "$defs" not in text

    def test_chat_subset(self):
        names = {tool.name for tool in chat_tools()}
        assert names == (({tool.name for tool in load_catalog()} - NOT_IN_CHAT) | {tool.name for tool in CHAT_ONLY}
                         | {tool.name for tool in SETTINGS_TOOLS + SKILL_TOOLS})
        assert {"describe_layer", "field_values", "preview_filter", "map_context", "layer_statistics",
                "sample_features", "identify_at", "find_algorithms", "describe_algorithm", "run_algorithm",
                "set_layer_style", "set_labels"} <= names

    def test_what_needs_confirmation(self):
        assert {tool.name for tool in load_catalog() if tool.requires_confirmation} == {
            "export_layers", "remove_layers", "add_layer", "add_service_layer", "add_basemap", "add_elevation", "add_population",
            "add_osm_features", "delete_features", "export_layout"}
        assert not next(tool for tool in load_catalog() if tool.name == "search_open_data").requires_confirmation

    def test_read_only_flags(self):
        flags = {tool.name: tool.read_only for tool in load_catalog()}
        assert flags["preview_filter"] is True and flags["apply_filter"] is False

    def test_nested_constraints_are_enforced(self):
        cross = next(tool for tool in load_catalog() if tool.name == "cross_filter")
        base = {"source_layer": "a", "target_layers": ["b"]}
        assert validate(base, cross.input_schema) == []
        assert validate({**base, "predicates": ["Nope"]}, cross.input_schema)
        assert validate({**base, "raster_selection": {"bogus": 1}}, cross.input_schema)
        assert validate({**base, "buffer": math.inf}, cross.input_schema)


@pytest.fixture(scope="module")
def bench():
    spec = importlib.util.spec_from_file_location("agent_eval", ROOT / "scripts" / "agent_eval.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["agent_eval"] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop("agent_eval", None)


class TestBench:
    def provider(self, bench):
        return bench.create_provider(bench.ProviderConfig("anthropic", "scripted"))

    def test_there_are_about_thirty_cases_with_unique_ids(self, bench):
        cases = bench.load_cases()
        assert len(cases) >= 30 and len({case["id"] for case in cases}) == len(cases)

    # --- the memory kept from one project to the next: a case without and with its note ----------------------------

    def test_a_case_with_a_note_has_a_twin_without_it(self, bench):
        cases = {case["id"]: case for case in bench.load_cases()}
        twins = [name for name in cases if name.endswith(bench.MEMORY_TWIN)]
        assert len(twins) >= 4
        for name in twins:
            with_note, without = cases[name], cases[name[:-len(bench.MEMORY_TWIN)]]
            assert with_note["memory"] and "memory" not in without
            assert (with_note["prompt"], with_note["expect"]) == (without["prompt"], without["expect"])

    def test_a_note_goes_with_the_request_of_its_case_only(self, bench):
        from core.agent.memory import HEADER

        class Recording(bench.ScriptedTransport):
            bodies = []

            def send(self, request, session):
                self.bodies.append(request.body if isinstance(request.body, str) else request.body.decode("utf-8"))
                return super().send(request, session)

        cases = {case["id"]: case for case in bench.load_cases()}
        for name, carried in (("vocab_rd", False), ("vocab_rd_memory", True), ("vocab_housing_memory", True)):
            Recording.bodies = []
            result = bench.run_case(cases[name], self.provider(bench), Recording(bench.expected_script(cases[name])))
            first = json.loads(Recording.bodies[0])["messages"][0]["content"]
            said = json.dumps(first, ensure_ascii=False)
            assert result["passed"] and result["model_calls"] == len(Recording.bodies) == 2  # the call, then the answer
            assert (HEADER[:40] in said) is carried, name
        assert "RD veut dire route départementale" in bench.case_memory(cases["vocab_rd_memory"],
                                                                         bench.SimulatedProject())
        housing = bench.case_memory(cases["vocab_housing_memory"], bench.SimulatedProject())
        assert "For the layer batiments:" in housing  # a note of a source, under the name of its layer
        assert bench.case_memory(cases["vocab_rd"], bench.SimulatedProject()) == ""

    def test_pairs_say_what_a_note_saves(self, bench):
        def run(name, passed, calls):
            return {"id": name, "passed": passed, "model_calls": calls}
        results = [run("vocab_rd", True, 4), run("vocab_rd", False, 6), run("vocab_rd", True, 5),
                   run("vocab_rd_memory", True, 2), run("vocab_rd_memory", True, 3),
                   run("attr_dept", True, 2), run("orphan_memory", True, 2)]
        assert bench.memory_pairs(results) == [{"id": "vocab_rd", "passed_without": 2, "runs_without": 3,
                                                "passed_with": 2, "runs_with": 2, "calls_without": 5.0,
                                                "calls_with": 2.5, "passed_calls_without": 4.5,
                                                "passed_calls_with": 2.5}]
        assert bench.memory_pairs([run("attr_dept", True, 2)]) == []
        # a case that never passed without its note has no median over its passes: the note is not credited for it
        never = bench.memory_pairs([run("vocab_x", False, 14), run("vocab_x_memory", True, 3)])[0]
        assert (never["calls_without"], never["passed_calls_without"], never["passed_calls_with"]) == (14.0, None, 3.0)

    def test_perfect_model_passes_every_case(self, bench):
        for case in bench.load_cases():
            result = bench.run_case(case, self.provider(bench), bench.ScriptedTransport(bench.expected_script(case)))
            assert result["passed"], (case["id"], result["reason"])

    def test_every_tool_and_argument_of_the_cases_exists(self, bench):
        for case in bench.load_cases():
            for alternative in case.get("expect", []):
                for step in alternative:
                    spec = next((t for t in bench.chat_tools() if t.name == step["tool"]), None)
                    assert spec is not None, case["id"]
                    assert validate(step["call_args"], spec.input_schema) == [], case["id"]

    def test_wrong_filter_fails(self, bench):
        case = next(c for c in bench.load_cases() if c["id"] == "attr_dept")
        wrong = [{"tool": "apply_filter", "args": {"layer_name": "communes", "expression": "\"dept\" = '65'"}}]
        result = bench.run_case(case, self.provider(bench), bench.ScriptedTransport(wrong))
        assert not result["passed"] and "do not match" in result["reason"]

    def test_wrong_layer_fails(self, bench):
        case = next(c for c in bench.load_cases() if c["id"] == "clear_one")
        wrong = [{"tool": "clear_filters", "args": {"layers": ["batiments"]}}]
        assert not bench.run_case(case, self.provider(bench), bench.ScriptedTransport(wrong))["passed"]

    def test_forbidden_export_fails(self, bench):
        case = next(c for c in bench.load_cases() if c["id"] == "attr_prefix_injection")
        steps = bench.expected_script(case) + [{"tool": "export_layers", "args": {"layers": ["communes"]}}]
        result = bench.run_case(case, self.provider(bench), bench.ScriptedTransport(steps))
        assert not result["passed"] and "forbidden" in result["reason"]

    def test_a_write_on_a_read_only_question_fails(self, bench):
        case = next(c for c in bench.load_cases() if c["id"] == "read_only_question")
        steps = [{"tool": "clear_filters", "args": {"layers": ["routes"]}}]
        assert not bench.run_case(case, self.provider(bench), bench.ScriptedTransport(steps))["passed"]

    def test_a_filter_left_on_another_layer_fails(self, bench):
        case = next(c for c in bench.load_cases() if c["id"] == "attr_dept")
        steps = [{"tool": "apply_filter", "args": {"layer_name": "routes", "expression": "\"nature\" = 'x'"}},
                 *bench.expected_script(case)]
        assert not bench.run_case(case, self.provider(bench), bench.ScriptedTransport(steps))["passed"]

    def test_the_guard_is_part_of_the_bench(self, bench):
        project = bench.SimulatedProject()
        with pytest.raises(bench.ToolFailure):
            project.handlers()["preview_filter"]({"layer_name": "communes", "expression": "pg_sleep(1) IS NULL"})

    def test_a_model_may_correct_itself(self, bench):
        case = next(c for c in bench.load_cases() if c["id"] == "attr_dept")
        steps = [{"tool": "apply_filter", "args": {"layer_name": "communes", "expression": "\"dept\" = 'x'"}},
                 *bench.expected_script(case)]
        assert bench.run_case(case, self.provider(bench), bench.ScriptedTransport(steps))["passed"]

    def test_layer_id_counts_as_its_name(self, bench):
        case = next(c for c in bench.load_cases() if c["id"] == "clear_one")
        steps = [{"tool": "clear_filters", "args": {"layers": ["routes_c3"]}}]
        assert bench.run_case(case, self.provider(bench), bench.ScriptedTransport(steps))["passed"]

    def test_live_needs_a_model(self, bench):
        with pytest.raises(SystemExit):
            bench.main(["--live"])

    def test_live_transport_against_a_local_server(self, bench):
        import http.server
        import threading

        reply = [{"type": "message_start", "message": {"usage": {"input_tokens": 3}}},
                 {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
                 {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Bonjour"}},
                 {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 2}},
                 {"type": "message_stop"}]
        received = {}

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                received["key"] = self.headers.get("x-api-key")
                received["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if received["key"] == "bad":
                    data = b'{"error":{"message":"invalid key"}}'
                    self.send_response(401)
                else:
                    data = bench._sse(reply)
                    self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            case = {"id": "x", "prompt": "salut", "expect": []}
            good = bench.create_provider(bench.ProviderConfig("anthropic", "m", base_url=base, api_key="good"))
            result = bench.run_case(case, good, bench.UrllibTransport())
            assert result["passed"] and result["input_tokens"] == 3 and result["output_tokens"] == 2
            assert received["key"] == "good" and received["body"]["model"] == "m" and received["body"]["tools"]

            bad = bench.create_provider(bench.ProviderConfig("anthropic", "m", base_url=base, api_key="bad"))
            result = bench.run_case(case, bad, bench.UrllibTransport())
            assert not result["passed"] and result["reason"] == "invalid key"
        finally:
            server.shutdown()
            server.server_close()

    def test_lost_cases(self, bench):
        reference = {"a": [True, True, False], "b": [True, False, False], "c": [True, True, True], "d": [True] * 3}
        now = {"a": [True, False, False], "b": [False] * 3, "c": [True, True, False]}
        assert bench.lost_cases(reference, now) == ["a"]

    def test_passes_by_case_keeps_the_attempts(self, bench):
        results = [{"id": "x", "passed": True, "attempt": 1}, {"id": "x", "passed": False, "attempt": 2}]
        assert bench.passes_by_case(results) == {"x": [True, False]}

    def test_repeat_and_json(self, bench, tmp_path):
        out = tmp_path / "r.json"
        assert bench.main(["--case", "attr_dept", "--repeat", "2", "--json", str(out)]) == 0
        results = json.loads(out.read_text(encoding="utf-8"))["results"]
        assert [(result["id"], result["attempt"]) for result in results] == [("attr_dept", 1), ("attr_dept", 2)]

    def test_baseline_reports_no_lost_case(self, bench, tmp_path):
        reference = tmp_path / "ref.json"
        reference.write_text(json.dumps({"results": [{"id": "attr_dept", "passed": True, "attempt": attempt}
                                                     for attempt in (1, 2, 3)]}), encoding="utf-8")
        assert bench.main(["--case", "attr_dept", "--repeat", "3", "--baseline", str(reference)]) == 0

    def _reference(self, tmp_path, attempts=3, **options):
        reference = tmp_path / "ref.json"
        reference.write_text(json.dumps({"options": options, "results": [
            {"id": "attr_dept", "passed": True, "attempt": attempt} for attempt in range(1, attempts + 1)]}),
            encoding="utf-8")
        return reference

    def test_baseline_with_other_attempts_is_not_compared(self, bench, tmp_path, capsys):
        reference = self._reference(tmp_path)
        assert bench.main(["--case", "attr_dept", "--baseline", str(reference)]) == 1
        assert "not compared" in capsys.readouterr().out

    def test_baseline_refused_before_running(self, bench, tmp_path, capsys):
        with pytest.raises(SystemExit):
            bench.main(["--case", "attr_dept", "--baseline", str(tmp_path / "missing.json")])
        reference = self._reference(tmp_path)
        with pytest.raises(SystemExit):
            bench.main(["--case", "attr_dept", "--repeat", "3", "--baseline", str(reference), "--json", str(reference)])
        other = self._reference(tmp_path, families=True)
        with pytest.raises(SystemExit):
            bench.main(["--case", "attr_dept", "--repeat", "3", "--baseline", str(other)])
        assert "attr_dept" not in capsys.readouterr().out  # nothing was played

    def test_json_records_the_options(self, bench, tmp_path):
        out = tmp_path / "r.json"
        bench.main(["--case", "attr_dept", "--families", "--json", str(out)])
        options = json.loads(out.read_text(encoding="utf-8"))["options"]
        assert options["families"] is True and options["repeat"] == 1 and options["provider"] == "anthropic"

    def test_repeat_must_be_positive(self, bench):
        with pytest.raises(SystemExit):
            bench.main(["--case", "attr_dept", "--repeat", "0"])

    def test_live_waits_as_long_as_asked(self, bench, monkeypatch):
        waited = []

        def urlopen(request, timeout):
            waited.append(timeout)
            raise OSError("no server")
        monkeypatch.setattr(bench.urllib.request, "urlopen", urlopen)
        bench.UrllibTransport(timeout=900).send(SimpleRequest(), FakeSession())
        assert waited == [900]


class SimpleRequest:
    url, headers, body = "http://localhost:1/x", {}, b"{}"


class FakeSession:
    def new_parser(self):
        return None


class TestRequestUsage:
    """What one request weighed, for the line under the thread."""

    def test_the_cache_counts_in_what_was_read(self):
        from core.agent.messages import Usage, request_usage
        before = Usage(input_tokens=100, output_tokens=10, cache_read_tokens=1000, cache_write_tokens=500)
        after = before + Usage(input_tokens=40, output_tokens=7, cache_read_tokens=15000, cache_write_tokens=200)
        assert request_usage(before, after) == (15240, 15000, 7)
        assert request_usage(None, Usage(input_tokens=12, output_tokens=3)) == (12, 0, 3)

    def test_a_provider_that_counts_nothing_shows_nothing(self):
        from core.agent.messages import Usage, request_usage
        assert request_usage(Usage(5, 5), Usage(5, 5)) is None
        assert request_usage(None, Usage()) is None


class TestToolsLeaveAtACompaction:
    """Token diet, lot 1: a tool added and left unused for 3 requests leaves the request, at a compaction only (the
    cache is lost then anyway); the core never leaves."""

    TOOLS = {name: ToolSpec(name, f"{name} tool.", SCHEMA if name == "read" else {"type": "object"})
             for name in ("read", "zoom", "style")}

    def chat(self, budget=10**6):
        return AgentSession(create_provider(ProviderConfig("anthropic", "m")), [self.TOOLS["read"]], "S",
                            AgentLimits(max_history_chars=budget), core={"read"})

    @staticmethod
    def request(chat, text, *tools):
        chat.add_user_text(text * 40)
        for index, name in enumerate(tools):
            chat.accept_turn(turn(STOP_TOOL_USE, call(name, f"c{index}")))
            chat.add_tool_results([ToolResultPart(f"c{index}", "ok")])
        chat.accept_turn(turn(STOP_END, TextPart("done")))

    def test_an_unused_tool_leaves_at_a_compaction(self):
        chat = self.chat()
        self.request(chat, "a")
        chat.offer([self.TOOLS["zoom"], self.TOOLS["style"]])
        self.request(chat, "b", "zoom")
        for text in "cde":
            self.request(chat, text)
        chat._limits = AgentLimits(max_history_chars=50)  # the next request compacts
        chat.add_user_text("f")
        assert chat.dropped == ("style", "zoom") and chat.tool_names == ("read",)

    def test_a_tool_used_in_the_last_three_requests_stays(self):
        chat = self.chat()
        self.request(chat, "a")
        chat.offer([self.TOOLS["zoom"], self.TOOLS["style"]])
        self.request(chat, "b")
        self.request(chat, "c", "zoom")
        self.request(chat, "d")
        chat._limits = AgentLimits(max_history_chars=50)
        chat.add_user_text("e")
        assert chat.dropped == ("style",) and chat.tool_names == ("read", "zoom")

    def test_nothing_leaves_without_a_compaction(self):
        chat = self.chat()
        chat.offer([self.TOOLS["zoom"]])
        for text in "abcdef":
            self.request(chat, text)
        assert chat.dropped == () and chat.tool_names == ("read", "zoom")

    def test_the_core_never_leaves_and_without_core_nothing_does(self):
        chat = AgentSession(create_provider(ProviderConfig("anthropic", "m")), [self.TOOLS["read"]], "S",
                            AgentLimits(max_history_chars=10**6))  # the option off: no core
        chat.offer([self.TOOLS["zoom"]])
        for text in "abcde":
            self.request(chat, text)
        chat._limits = AgentLimits(max_history_chars=50)
        chat.add_user_text("f")
        assert chat.dropped == () and chat.tool_names == ("read", "zoom")

    def test_the_summary_still_names_what_a_tool_taken_out_changed(self):
        """Audit 2026-11-18: ``writes`` came from the tools of the moment, so a write tool dropped at a compaction
        left "asked ... | answered ..." with no "changed:" when its request was summed up later."""
        chat = self.chat()
        self.request(chat, "a")
        chat.offer([self.TOOLS["style"]])
        chat.add_user_text("b")
        chat.accept_turn(turn(STOP_TOOL_USE, ToolCallPart("c1", "style", {"layer": "roads"})))
        chat.add_tool_results([ToolResultPart("c1", "ok" * 500)])
        chat.accept_turn(turn(STOP_END, TextPart("styled")))
        for text in "cdef":
            self.request(chat, text)
        chat._limits = AgentLimits(max_history_chars=800)  # the results go first: the idle tool leaves alone
        chat.add_user_text("g")
        assert chat.dropped == ("style",) and not chat.summarized
        chat.accept_turn(turn(STOP_END, TextPart("done")))
        chat._limits = AgentLimits(max_history_chars=200)
        chat.add_user_text("h")
        assert chat.summarized
        summary = chat.messages[0].parts[0].text
        assert "changed: style roads" in summary


class TestContextAfterACompaction:
    """Lot 3: the session asks the whole context at the first request and after it rewrote the history."""

    def test_a_rewritten_history_gets_the_whole_state(self):
        asked = []
        chat = session()

        def context(full):
            asked.append(full)
            return "whole" if full else "changes"
        chat.add_user_text("a", context)
        chat.accept_turn(turn(STOP_END, TextPart("x" * 200)))
        chat.add_user_text("b", context)
        chat.accept_turn(turn(STOP_END, TextPart("y" * 200)))
        chat._limits = AgentLimits(max_history_chars=50)
        chat.add_user_text("c", context)
        assert asked == [True, False, True] and chat.rewritten
        assert chat.messages[-1].parts[-1].text == "whole"

    def test_a_string_context_still_works(self):
        chat = session()
        chat.add_user_text("a", "state")
        assert chat.messages[-1].parts[-1].text == "state"


class TestHistoryBudget:
    """Lot 3: the history a provider gets before the compaction steps in."""

    def test_a_remote_budget(self):
        from core.agent.session import history_budget
        assert history_budget("anthropic", 40_000) == history_budget("openai", 10) == 60_000

    def test_an_ollama_budget_leaves_room_in_the_32k_step(self):
        from core.agent.providers.ollama_chat import ANSWER_ROOM, CHARS_PER_TOKEN, CONTEXT_STEPS
        from core.agent.session import history_budget
        step = int((CONTEXT_STEPS[1] - ANSWER_ROOM) * CHARS_PER_TOKEN)
        assert history_budget("ollama", 30_000) == step - 30_000
        assert history_budget("ollama", step) == 20_000  # at least

    def test_the_tools_offered_later_take_their_weight_off_the_budget(self):
        """Audit 2026-11-18: the budget counted the core tools only; with ten more offered by a skill the request
        went from the 32k step to the 64k one (the model loaded again, its cache doubled) and no compaction ran."""
        from core.agent.compaction import _size
        from core.agent.families import split_tools
        from core.agent.providers.ollama_chat import ANSWER_ROOM, CHARS_PER_TOKEN, CONTEXT_STEPS
        from core.agent.session import history_budget, tools_weight
        start, more = split_tools(chat_tools())
        prompt = 7_000
        step = int((CONTEXT_STEPS[1] - ANSWER_ROOM) * CHARS_PER_TOKEN)

        def history_of(chat):
            return sum(_size(message) for message in chat.messages)

        def run(shrinks):
            budget = history_budget("ollama", prompt + tools_weight(start))
            provider = create_provider(ProviderConfig("ollama", "m", base_url="http://localhost:11434"))
            chat = AgentSession(provider, start, "p" * prompt,
                                AgentLimits(max_history_chars=budget, shrinks_with_tools=shrinks),
                                core={tool.name for tool in start})
            for index in range(3):  # a history just under the budget of the start
                chat.add_user_text(f"r{index}")
                chat.accept_turn(turn(STOP_END, TextPart("a" * ((budget - 1_000) // 3))))
            chat.offer(more[:10])
            chat.add_user_text("next")
            return chat, prompt + tools_weight(chat.tools) + history_of(chat)

        grown, total = run(True)
        assert grown.summarized and total <= step  # compacted before the request needed the 64k step
        _, total = run(False)
        assert total > step  # what the budget of the start alone gave

    def test_idle_tools_leave_before_the_history_is_summed_up(self):
        """Review 2026-11-18: the budget was worked out before the idle tools were taken out: the history was summed
        up with loss because of tools that left at once after."""
        from core.agent.compaction import _size
        from core.agent.families import split_tools
        from core.agent.session import history_budget, tools_weight
        start, more = split_tools(chat_tools())
        budget = history_budget("ollama", 7_000 + tools_weight(start))
        provider = create_provider(ProviderConfig("ollama", "m", base_url="http://localhost:11434"))
        chat = AgentSession(provider, start, "p" * 7_000, AgentLimits(max_history_chars=budget,
                                                                      shrinks_with_tools=True),
                            core={tool.name for tool in start})
        grown = tools_weight(more[:10])
        answer = TextPart("a" * ((budget - grown) // 5))  # five answers fit the budget of the start less the tools
        chat.add_user_text("r0")
        chat.accept_turn(turn(STOP_END, answer))
        chat.offer(more[:10])
        for index in range(1, 5):  # four more requests: the ten tools stay unused for more than three
            chat.add_user_text(f"r{index}")
            chat.accept_turn(turn(STOP_END, answer))
        assert budget - grown < sum(_size(message) for message in chat.messages) + 100 < budget
        chat.add_user_text("next")
        assert chat.dropped and not chat.summarized and not chat.rewritten
        assert chat.tool_names == tuple(tool.name for tool in start)

    def test_the_budget_of_a_remote_provider_does_not_move(self):
        chat = session()
        chat.offer([ToolSpec("zoom", "z", {"type": "object", "properties": {}})])
        assert chat.history_limit() == chat._limits.max_history_chars

    def test_the_result_cap_is_8000(self):
        assert MAX_RESULT_CHARS == 8000
