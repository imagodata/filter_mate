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
from core.agent.session import AgentLimits, AgentSession, run_exchange
from core.agent.sql_guard import expression_problem, filter_problem, quoted_identifiers
from core.agent.tool_catalog import CHAT_ONLY, NOT_IN_CHAT, ToolSpec, chat_tools, load_catalog
from core.agent.tool_executor import MAX_RESULT_CHARS, ToolExecutor, ToolFailure, bounded_json

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = {"type": "object", "required": ["name"], "properties": {
    "name": {"type": "string", "minLength": 1}, "size": {"type": "number", "default": 2.5}}}
READ = ToolSpec("read", "Read something here.", SCHEMA, read_only=True)
EXPORT = ToolSpec("export", "Write a file there.", {"type": "object", "properties": {}}, destructive=True)


def session(limit=12):
    return AgentSession(create_provider(ProviderConfig("anthropic", "m")), [READ], "S", AgentLimits(limit))


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

    def test_abandon_only_forgets_the_current_request(self):
        chat = session()
        chat.add_user_text("first")
        chat.accept_turn(turn(STOP_END, TextPart("ok")))
        chat.add_user_text("second")
        chat.abandon_request()
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
        assert names == ({tool.name for tool in load_catalog()} - NOT_IN_CHAT) | {tool.name for tool in CHAT_ONLY}
        assert {"describe_layer", "field_values", "preview_filter", "map_context"} <= names

    def test_what_needs_confirmation(self):
        assert {tool.name for tool in load_catalog() if tool.requires_confirmation} == {
            "export_layers", "remove_layers", "add_layer", "add_service_layer"}
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
