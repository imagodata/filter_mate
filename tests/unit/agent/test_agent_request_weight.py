# -*- coding: utf-8 -*-
"""The measuring bench of the token diet (scripts/agent_request_weight.py): what each request of a conversation sends,
and the start of it the cache of each provider can serve. No network."""
import importlib.util
import json
import socket
import sys
from pathlib import Path

import pytest

from core.agent.messages import ROLE_USER, Message, TextPart
from core.agent.tool_catalog import chat_tools

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def weight():
    spec = importlib.util.spec_from_file_location("agent_request_weight", ROOT / "scripts" / "agent_request_weight.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["agent_request_weight"] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop("agent_request_weight", None)


def user(text):
    return Message(ROLE_USER, (TextPart(text),))


TOOLS = chat_tools()[:2]


def test_common_prefix_counts_characters(weight):
    assert weight.common_prefix("département 31", "département 32") == 13


def _compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


@pytest.mark.parametrize("kind", ["anthropic", "openai"])
def test_cache_order_puts_the_tools_first(weight, kind):
    body = json.loads(weight.providers()[kind].build_request("sys", [user("é")], TOOLS).body)
    assert weight.cache_order(kind, body).startswith(_compact(body["tools"]))


def test_ollama_reads_the_instructions_then_the_tools(weight):
    body = json.loads(weight.providers()["ollama"].build_request("sys", [user("é")], TOOLS).body)
    system, rest = body["messages"][0], body["messages"][1:]
    assert system["role"] == "system"
    assert weight.cache_order("ollama", body) == _compact([system]) + _compact(body["tools"]) + _compact(rest)


def test_anthropic_reads_only_what_an_earlier_request_wrote(weight):
    """Its cache holds each earlier request whole (up to its last block): a request that adds a tool reads none."""
    first = {"tools": [{"name": "a"}], "system": [{"text": "s"}], "messages": [{"content": "m1"}]}
    more_tools = dict(first, tools=[{"name": "a"}, {"name": "b"}])
    longer = dict(first, messages=[{"content": "m1"}, {"content": "m2"}])
    assert weight.cached_prefix("anthropic", [first], more_tools) == 0
    assert weight.cached_prefix("openai", [first], more_tools) > 0
    assert weight.cached_prefix("anthropic", [first], longer) == len(weight.cache_order("anthropic", first)) - 1
    assert weight.cached_prefix("anthropic", [first, more_tools], longer) == len(weight.cache_order("anthropic", first)) - 1


def test_anthropic_reads_the_tools_and_the_instructions_after_a_rewrite(weight):
    """Lot 4: the instructions carry a breakpoint of their own; a history rewritten (a compaction) still reads them."""
    first = {"tools": [{"name": "a"}], "system": [{"text": "s", "cache_control": {"type": "ephemeral"}}],
             "messages": [{"content": "m1"}]}
    rewritten = dict(first, messages=[{"content": "summary"}])
    assert weight.cached_prefix("anthropic", [first], rewritten) == len(_compact(first["tools"]) + _compact(first["system"]))
    unmarked = dict(first, system=[{"text": "s"}])
    assert weight.cached_prefix("anthropic", [unmarked], dict(unmarked, messages=[{"content": "summary"}])) == 0


def test_a_new_conversation_reads_the_tools_and_the_instructions(weight):
    run = weight.replay()
    fresh = weight.next_conversation(run)
    instructions, tools, _ = weight.default_setup()
    body = json.loads(weight.providers()["anthropic"].build_request(instructions, [user("x")], tools).body)
    assert fresh["anthropic"] == len(_compact(body["tools"]) + _compact(body["system"]))


def test_a_start_that_changed_within_a_request_is_named(weight):
    def call(request, read, tools=3, num_ctx=16384):
        return weight.CallWeight(request, 10, 10, 10, tools, {"anthropic": read, "openai": read, "ollama": read},
                                 num_ctx, {"anthropic": 100, "openai": 100, "ollama": 100})
    assert weight.broken_starts([call(1, 0), call(1, 99)]) == []
    assert weight.broken_starts([call(1, 0), call(2, 5)]) == []  # another request: the context changed
    assert weight.broken_starts([call(1, 0), call(1, 0, tools=4)]) == []  # a tool added: its price is accepted
    assert len(weight.broken_starts([call(1, 0), call(1, 50)])) == 3
    assert weight.broken_starts(weight.replay().calls) == []


def test_a_tool_added_first_is_caught(weight, monkeypatch):
    """Review of lot 4: a tool put before the others breaks the start of OpenAI and Ollama, which read the tools
    before it; the bench must say so, not only Anthropic's cost."""
    from agent.session import AgentSession

    def offer_first(self, tools):
        known = {tool.name for tool in self._tools}
        self._tools = tuple(tool for tool in tools if tool.name not in known) + self._tools
    monkeypatch.setattr(AgentSession, "offer", offer_first)
    broken = weight.broken_starts(weight.replay().calls)
    assert any("openai" in line for line in broken) and any("ollama" in line for line in broken)


def test_the_instructions_of_a_conversation_never_change(weight):
    calls = weight.replay().calls
    assert len({call.system for call in calls}) == 1
    changed = [calls[0], weight.CallWeight(**dict(calls[1].__dict__, system="other"))]
    assert weight.broken_starts(changed) == [f"request {calls[1].request}: the instructions changed"]


def test_a_new_conversation_reads_what_it_should(weight):
    fresh = weight.next_conversation(weight.replay())
    for kind in ("anthropic", "openai", "ollama"):
        assert fresh[kind] >= fresh[kind + "_expected"] > 0


def test_ollama_prefix_is_lost_when_the_context_step_changes(weight):
    before = {"tools": [], "messages": [{"role": "user", "content": "a"}], "options": {"num_ctx": 16384}}
    after = dict(before, options={"num_ctx": 32768})
    assert weight.cached_prefix("ollama", [before], after) == 0
    assert weight.cached_prefix("openai", [before], after) > 0
    assert weight.cached_prefix("ollama", [], before) == 0


def test_estimated_cost(weight):
    first = weight.CallWeight(1, 400, 500, 100, 3, {"anthropic": 0, "openai": 0, "ollama": 0}, 16384)
    second = weight.CallWeight(1, 400, 500, 100, 3, {"anthropic": 900, "openai": 900, "ollama": 900}, 16384)
    assert first.sent == 1000
    assert weight.estimated_cost([first, second]) == pytest.approx(1250 + 90 + 125)


def test_conversation_runs_offline_and_cleanly(weight, monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("network")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    run = weight.replay()
    assert run.errors == []
    assert sorted({call.request for call in run.calls}) == list(range(1, 14))
    assert run.skills_loaded == []  # lot 1: set_layer_style comes by use_tools, no skill loaded for it
    assert all(value == 0 for value in run.calls[0].prefix.values())


def test_a_request_cut_short_is_reported(weight, monkeypatch):
    steps = tuple(("describe_layer", {"layer": "routes"}) for _ in range(20))  # past the 16 turns of a request
    monkeypatch.setattr(weight, "CONVERSATION", (("Décris les routes vingt fois.", steps),))
    assert any("request 1" in error for error in weight.replay().errors)


def test_within_a_request_the_whole_start_is_shared(weight):
    calls = weight.replay().calls
    compared = 0
    for before, after in zip(calls, calls[1:]):
        if after.request == before.request and after.tool_count == before.tool_count:
            assert after.prefix["anthropic"] == before.sent - 1  # all of the call before but the "]" of its messages
            compared += 1
    assert compared


def test_main_conversation_without_reference(weight, monkeypatch, capsys):
    monkeypatch.setattr(weight, "REFERENCE", None)
    assert weight.main(["--conversation"]) == 0
    assert "estimated cost" in capsys.readouterr().out


def test_a_reference_of_another_conversation_is_refused(weight, monkeypatch, capsys):
    monkeypatch.setattr(weight, "REFERENCE", {"fingerprint": "000000000000", "cost": 1e12, "largest": 10 ** 9})
    assert weight.main(["--conversation"]) == 1
    assert "another conversation" in capsys.readouterr().out


def test_a_rise_past_five_percent_fails(weight, monkeypatch):
    run = weight.replay()
    cost = weight.estimated_cost(run.calls)
    largest = max(call.sent for call in run.calls)
    reference = {"fingerprint": weight.fingerprint(), "cost": cost / 1.06, "largest": largest}
    monkeypatch.setattr(weight, "REFERENCE", reference)
    assert weight.main(["--conversation"]) == 1
    monkeypatch.setattr(weight, "REFERENCE", dict(reference, cost=cost / 1.04))
    assert weight.main(["--conversation"]) == 0


def test_the_bench_project_is_like_a_real_one(weight):
    """Lot 3 (2026-11-16): 14 layers like the network project of the user, notes and widgets, and requests that read
    data: without them, sending less of the state and of the data would not show."""
    project = weight.bench_project()
    assert len(project.layers) == 14 and all(len(project.layers[name]["fields"]) == 12 for name in weight.EXTRA_LAYERS)
    reads = [steps[0][0] for _text, steps in weight.CONVERSATION]
    assert len(weight.CONVERSATION) == 13
    assert {"describe_layer", "field_values", "sample_features"} <= set(reads)
    context = weight.bench_context(project, None)
    assert "Notes kept for this project" in context and "Widgets of the panel" in context


# --- the memory kept from one project to the next (core/agent/memory.py) --------------------------------------------------

def test_an_empty_memory_weighs_nothing(weight):
    project = weight.bench_project()
    assert weight.bench_context(project, None) == weight.bench_context(project, None, kept="")
    assert "from one project to the next" not in weight.bench_context(project, None)


def test_a_full_memory_fills_its_budget_and_is_sent_once(weight, capsys):
    from core.agent.memory import HEADER, MAX_MEMORY_BLOCK
    block = weight.full_memory_block(weight.bench_project())
    assert 0.8 * MAX_MEMORY_BLOCK < len(block) <= MAX_MEMORY_BLOCK and "Not sent: " in block.splitlines()[-1]
    run = weight.replay(with_memory=True)
    assert not run.errors and not weight.broken_starts(run.calls)  # the start of each request still shared
    firsts = [json.dumps(body, ensure_ascii=False).count(HEADER[:40]) for body in run.bodies["anthropic"]]
    assert set(firsts) == {1}  # in the first request, and carried by the history after: never said twice
    assert weight.main(["--conversation", "--memory"]) == 0
    printed = capsys.readouterr().out
    assert f"memory block: {len(block)} characters" in printed and "cost" in printed


def test_memory_goes_with_conversation(weight):
    with pytest.raises(SystemExit):
        weight.main(["--memory"])
