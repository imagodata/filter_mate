# -*- coding: utf-8 -*-
"""Loading a connector (a connector-… entry of load_skill): asked once per conversation, at every level."""
import json

import pytest

from core.agent.chat_engine import ChatEngine
from core.agent.messages import STOP_TOOL_USE, ToolCallPart
from core.agent.permissions import ASK, LEVELS, REFUSE, RUN, PermissionPolicy
from core.agent.providers import create_provider
from core.agent.providers.base import ProviderConfig
from core.agent.session import AgentSession
from core.agent.tool_catalog import ToolSpec
from core.agent.tool_executor import DECLINED, ToolExecutor, ToolFailure, connector_gate

from .test_chat_engine import READ, WRITE, Checkpoint, Listener, Transport, turn
from .test_permissions import EMPTY

pytestmark = pytest.mark.unit

LOAD = ToolSpec("load_skill", "Load the instructions of a task.", {
    "type": "object", "required": ["name"],
    "properties": {"name": {"type": "string", "enum": ["connector-a", "connector-b", "configuration"]}}},
    read_only=True)


def load_call(name, call_id="c1"):
    return ToolCallPart(call_id, "load_skill", {"name": name})


class Many(Listener):
    """Says yes to one question for several calls, and logs it."""

    def confirm_many(self, calls):
        self.log.append(("many", [c.name for c in calls]))
        return self.accept


def engine_with(accept, handler=None, level="standard", listener=None):
    tools = [LOAD, WRITE]
    session = AgentSession(create_provider(ProviderConfig("anthropic", "m")), tools, "S")
    loads = []

    def load(arguments):
        loads.append(arguments["name"])
        return {"loaded": arguments["name"]}
    listener = listener if listener is not None else Listener(accept)
    listener.accept = accept
    policy = PermissionPolicy(level)
    transport = Transport()
    executor = ToolExecutor(tools, {"load_skill": handler or load, "write": lambda arguments: {}})
    engine = ChatEngine(session, executor, transport, listener, Checkpoint(), policy=policy)
    return engine, session, transport, listener, policy, loads


def tool_names(start):
    return [tool["name"] for tool in json.loads(start[0].body)["tools"]]


@pytest.mark.parametrize("level", LEVELS)
def test_a_connector_load_is_asked_at_every_level(level):
    executor = ToolExecutor([LOAD], {"load_skill": lambda arguments: {}})
    policy = PermissionPolicy(level, rules={"load_skill": "allow"})  # the rule of load_skill: not for connectors
    assert executor.verdict(load_call("connector-a"), policy) == ASK
    assert executor.verdict(load_call("configuration"), policy) == RUN
    assert connector_gate(load_call("configuration")) is None


@pytest.mark.parametrize("rule", ["never", "ask"])
def test_the_rules_of_load_skill_do_not_reach_the_connectors(rule):
    executor = ToolExecutor([LOAD], {"load_skill": lambda arguments: {}})
    policy = PermissionPolicy(rules={"load_skill": rule})
    assert executor.verdict(load_call("connector-a"), policy) == ASK
    policy.grant("connector-a")
    assert executor.verdict(load_call("connector-a"), policy) == RUN


def test_the_gate_names_the_connector_and_reaches_outside():
    gate = connector_gate(load_call("connector-a"))
    assert gate.name == "connector-a" and gate.open_world and not gate.read_only
    assert connector_gate(ToolCallPart("1", "write", {"name": "connector-a"})) is None
    assert connector_gate(ToolCallPart("1", "load_skill", {"name": 3})) is None


def test_a_connector_out_of_the_list_is_an_invalid_call_that_runs_and_says_so():
    executor = ToolExecutor([LOAD], {"load_skill": lambda arguments: {}})
    call = load_call("connector-nope")
    assert executor.verdict(call, PermissionPolicy()) == RUN
    assert executor.execute(call).is_error and "Invalid arguments" in executor.execute(call).content


def test_a_yes_holds_for_that_connector_only_and_for_the_conversation():
    engine, session, transport, listener, policy, loads = engine_with(True)
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, load_call("connector-a"), load_call("connector-a", "c2")))
    assert [entry for entry in listener.log if entry[0] == "confirm"] == [("confirm", "load_skill")]
    assert loads == ["connector-a", "connector-a"] and policy.granted == {"connector-a"}
    assert ToolExecutor([LOAD], {}).verdict(load_call("connector-b"), policy) == ASK


def test_a_no_refuses_that_connector_for_the_conversation_without_asking_again():
    engine, session, transport, listener, policy, loads = engine_with(False)
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, load_call("connector-a"), load_call("connector-a", "c2")))
    answers = session.messages[-1].parts
    assert loads == [] and len([entry for entry in listener.log if entry[0] == "confirm"]) == 1
    assert all(part.is_error and "do not ask again in this conversation" in part.content for part in answers)
    assert "'connector-a'" in answers[0].content
    assert policy.declined == {"connector-a"}
    assert ToolExecutor([LOAD], {}).verdict(load_call("connector-a"), policy) == REFUSE
    assert ToolExecutor([LOAD], {}).verdict(load_call("connector-b"), policy) == ASK
    policy.forget()
    assert ToolExecutor([LOAD], {}).verdict(load_call("connector-a"), policy) == ASK


def test_a_failed_load_is_not_granted():
    def fails(arguments):
        raise ToolFailure("Local does not answer")
    engine, session, transport, listener, policy, _loads = engine_with(True, handler=fails)
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, load_call("connector-a")))
    assert not policy.granted and not policy.declined
    assert session.messages[-1].parts[0].content == "Local does not answer"


def test_a_connector_load_is_asked_alone():
    engine, session, transport, listener, policy, _loads = engine_with(True, level="careful", listener=Many())
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, load_call("connector-a"), ToolCallPart("w1", "write", {}),
                        ToolCallPart("w2", "write", {})))
    assert ("many", ["write", "write"]) in listener.log and ("confirm", "load_skill") in listener.log


def test_declined_without_a_policy_is_the_usual_answer():
    assert ToolExecutor.declined(load_call("connector-a")).content == DECLINED
    policy = PermissionPolicy()
    assert ToolExecutor.declined(ToolCallPart("1", "write", {}), policy).content == DECLINED
    assert not policy.declined


def test_tools_offered_later_come_with_their_handlers():
    remote = ToolSpec("mcp_a__t", "[External connector A] T", EMPTY, open_world=True)
    executor = ToolExecutor([READ], {"read": lambda arguments: "R"})
    executor.offer([remote], {"mcp_a__t": lambda arguments: "T", "read": lambda arguments: "other"})
    assert executor.execute(ToolCallPart("1", "mcp_a__t", {})).content == '"T"'
    assert executor.execute(ToolCallPart("2", "read", {})).content == '"R"'


def test_a_connector_tool_called_before_its_connector_is_loaded_says_how():
    result = ToolExecutor([LOAD], {}).execute(ToolCallPart("1", "mcp_datagouv_mcp__search", {}))
    assert result.is_error and "load_skill" in result.content and "connector-" in result.content
    assert "Unknown tool" in ToolExecutor([LOAD], {}).execute(ToolCallPart("1", "nope", {})).content


def test_the_engine_offers_tools_with_their_handlers_after_the_others():
    remote = ToolSpec("mcp_a__t", "[External connector A] T", EMPTY, open_world=True)
    holder = {}

    def load(arguments):
        holder["engine"].offer_tools([remote], {"mcp_a__t": lambda arguments: "T"})
        return {}
    engine, session, transport, listener, policy, _loads = engine_with(True, handler=load)
    holder["engine"] = engine
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, load_call("connector-a")))
    first, later = tool_names(transport.starts[0]), tool_names(transport.starts[-1])
    assert "mcp_a__t" not in first and later == first + ["mcp_a__t"]
    policy.grant("mcp_a__t")  # asked as any connector tool: allowed here to reach its handler
    transport.emit(turn(STOP_TOOL_USE, ToolCallPart("c2", "mcp_a__t", {})))
    assert session.messages[-1].parts[0].content == '"T"' and not session.messages[-1].parts[0].is_error


def test_at_the_advisor_level_a_connector_is_asked_then_loaded():
    """Decided by the user on 2026-11-14: the advisor level can use a connector, each call of its tools asked."""
    engine, session, transport, listener, policy, loads = engine_with(True, level="advisor")
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, load_call("connector-a")))
    assert loads == ["connector-a"] and policy.granted == {"connector-a"}
    assert [entry for entry in listener.log if entry[0] == "confirm"] == [("confirm", "load_skill")]


def test_another_level_keeps_a_no_and_asks_a_yes_again():
    policy = PermissionPolicy("standard")
    policy.decline("connector-a")
    policy.grant("connector-b")
    policy.set_level("careful")
    executor = ToolExecutor([LOAD], {})
    assert executor.verdict(load_call("connector-a"), policy) == REFUSE
    assert policy.granted == frozenset()


def test_a_yes_is_not_kept_when_the_conversation_ended_while_the_connector_loaded():
    """The policy outlives the conversation: a yes granted after it ended opened the connector in the next one."""
    made = {}

    def ends_the_conversation(arguments):
        made["engine"].cancel()
        made["policy"].forget()
        return {}
    engine, session, transport, listener, policy, _loads = engine_with(True, handler=ends_the_conversation)
    made.update(engine=engine, policy=policy)
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, load_call("connector-a")))
    assert policy.granted == frozenset()
