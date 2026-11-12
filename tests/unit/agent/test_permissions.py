# -*- coding: utf-8 -*-
"""Risk classes of the tools, levels of autonomy, and what the chat does with them."""
import pytest

from core.agent.chat_engine import ChatEngine
from core.agent.messages import STOP_TOOL_USE, ToolCallPart
from core.agent.permissions import (
    ADVISOR, ADVISOR_REFUSAL, AGENT_OWN, ASK, AUTONOMOUS, BUFFER, CAREFUL, DEFAULT_LEVEL, LEVELS, LOCAL, OUTSIDE, PROJECT, READ,
    REFUSE, RUN, STANDARD, VIEW, PermissionPolicy, level_note, level_or_default, risk_of,
)
from core.agent.providers import create_provider
from core.agent.providers.base import ProviderConfig
from core.agent.session import AgentSession
from core.agent.tool_catalog import CHAT_ONLY, ToolSpec, chat_tools, load_catalog
from core.agent.tool_executor import DECLINED, ToolExecutor

from .test_chat_engine import Checkpoint, Listener, Transport, turn

pytestmark = pytest.mark.unit

EMPTY = {"type": "object", "properties": {}}
NAMED = {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}


def spec(name, **flags):
    return ToolSpec(name, "A tool.", EMPTY, **flags)


def tools_by_name():
    return {tool.name: tool for tool in chat_tools()}


class TestRiskClasses:
    def test_every_tool_of_the_chat_has_a_class(self):
        assert {risk_of(tool) for tool in chat_tools()} <= {READ, VIEW, PROJECT, BUFFER, LOCAL, OUTSIDE}

    @pytest.mark.parametrize("name, risk", [
        ("list_layers", READ), ("layer_statistics", READ), ("search_open_data", READ),  # a network read
        ("zoom_to", VIEW), ("select_features", VIEW), ("set_layers_visibility", VIEW), ("group_layers", VIEW),
        ("map_theme", VIEW), ("bookmark", VIEW), ("rename_layer", PROJECT),
        ("apply_filter", PROJECT), ("set_layer_style", PROJECT), ("run_algorithm", PROJECT),
        ("create_layout", PROJECT), ("set_project_crs", PROJECT),
        ("update_features", BUFFER), ("add_features", BUFFER), ("add_field", BUFFER), ("join_layers", PROJECT),
        ("delete_features", LOCAL), ("export_layers", LOCAL), ("export_layout", LOCAL), ("remove_layers", LOCAL),
        ("add_layer", OUTSIDE), ("add_service_layer", OUTSIDE),
    ])
    def test_class_of_the_tools_of_the_catalog(self, name, risk):
        assert risk_of(tools_by_name()[name]) == risk

    def test_a_connector_that_changes_something_is_outside(self):
        assert risk_of(spec("mcp_x_send", open_world=True)) == OUTSIDE
        assert risk_of(spec("mcp_x_read", open_world=True, read_only=True)) == READ

    def test_code_is_outside_whatever_its_flags(self):
        assert risk_of(spec("run_pyqgis")) == OUTSIDE
        assert risk_of(spec("run_pyqgis", read_only=True)) == OUTSIDE

    def test_an_unknown_tool_that_changes_something_is_a_project_change(self):
        assert risk_of(spec("something_new")) == PROJECT


class TestLevels:
    def test_standard_asks_exactly_what_the_chat_asked_before_the_levels(self):
        policy = PermissionPolicy(STANDARD)
        tools = list(load_catalog()) + list(CHAT_ONLY) + [spec("run_pyqgis", destructive=True),
                                                           spec("mcp_x", open_world=True)]
        for tool in tools:
            assert (policy.verdict(tool) == ASK) == tool.requires_confirmation, tool.name

    def test_default_level_is_standard(self):
        assert DEFAULT_LEVEL == STANDARD and PermissionPolicy().level == STANDARD
        assert level_or_default("anything") == STANDARD and level_or_default(None) == STANDARD

    @pytest.mark.parametrize("level, runs, asks", [
        (CAREFUL, {READ, VIEW}, {PROJECT, BUFFER, LOCAL, OUTSIDE}),
        (STANDARD, {READ, VIEW, PROJECT, BUFFER}, {LOCAL, OUTSIDE}),
        (AUTONOMOUS, {READ, VIEW, PROJECT, BUFFER, LOCAL}, {OUTSIDE}),
    ])
    def test_what_each_level_runs_alone(self, level, runs, asks):
        policy = PermissionPolicy(level)
        for tool in chat_tools():
            expected = RUN if risk_of(tool) in runs or tool.name in AGENT_OWN else ASK
            assert policy.verdict(tool) == expected, (level, tool.name)
            assert risk_of(tool) in runs | asks

    def test_advisor_only_reads(self):
        policy = PermissionPolicy(ADVISOR)
        names = tools_by_name()
        assert policy.verdict(names["layer_statistics"]) == RUN
        for name in ("zoom_to", "apply_filter", "update_features", "export_layers", "add_layer"):
            assert policy.verdict(names[name]) == REFUSE, name

    @pytest.mark.parametrize("level", LEVELS)
    def test_the_agent_own_notes_and_history_run_at_every_level(self, level):
        policy = PermissionPolicy(level)
        own = [tool for tool in CHAT_ONLY if tool.name in AGENT_OWN]
        assert {tool.name for tool in own} == AGENT_OWN
        for tool in own:
            assert policy.verdict(tool) == RUN

    def test_the_expert_code_and_the_image_of_the_map(self):
        tools = {tool.name: tool for tool in CHAT_ONLY}
        assert risk_of(tools["run_pyqgis"]) == OUTSIDE and not PermissionPolicy().grantable(tools["run_pyqgis"])
        assert PermissionPolicy(AUTONOMOUS).verdict(tools["run_pyqgis"]) == ASK
        assert risk_of(tools["view_map"]) == READ

    @pytest.mark.parametrize("level", LEVELS)
    def test_code_is_asked_at_every_level_but_advisor(self, level):
        expected = REFUSE if level == ADVISOR else ASK
        assert PermissionPolicy(level).verdict(spec("run_pyqgis", destructive=True)) == expected

    def test_level_note_only_off_the_usual_level(self):
        assert level_note(STANDARD) == "" and level_note("anything") == ""
        assert "advisor" in level_note(ADVISOR) and "careful" in level_note(CAREFUL)
        assert "autonomous" in level_note(AUTONOMOUS)


class TestAllowedForTheConversation:
    def test_a_tool_allowed_runs_for_the_rest_of_the_conversation(self):
        policy = PermissionPolicy(STANDARD)
        export = tools_by_name()["export_layers"]
        assert policy.verdict(export) == ASK
        policy.grant("export_layers")
        assert policy.verdict(export) == RUN
        assert policy.verdict(tools_by_name()["remove_layers"]) == ASK  # only that tool

    def test_code_is_never_allowed_for_a_conversation(self):
        policy = PermissionPolicy(AUTONOMOUS)
        code = spec("run_pyqgis", destructive=True)
        assert not policy.grantable(code)
        policy.grant("run_pyqgis")
        assert policy.verdict(code) == ASK

    def test_advisor_refuses_even_what_was_allowed(self):
        policy = PermissionPolicy(ADVISOR, granted=("apply_filter",))
        assert policy.verdict(tools_by_name()["apply_filter"]) == REFUSE

    def test_forgotten_with_a_new_level_kept_with_the_same(self):
        policy = PermissionPolicy(STANDARD, granted=("export_layers",))
        policy.set_level(STANDARD)
        assert policy.granted == {"export_layers"}
        policy.set_level(CAREFUL)
        assert policy.level == CAREFUL and not policy.granted
        policy.set_level("nonsense")
        assert policy.level == STANDARD
        policy.grant("x")
        policy.forget()
        assert not policy.granted


class TestExecutorVerdict:
    def test_an_invalid_call_runs_to_answer_its_mistake(self):
        executor = ToolExecutor([ToolSpec("export", "A tool.", NAMED, destructive=True)], {"export": lambda a: a})
        policy = PermissionPolicy(ADVISOR)
        assert executor.verdict(ToolCallPart("c", "export", {}), policy) == RUN
        assert executor.verdict(ToolCallPart("c", "export", {"name": "a"}, parse_error="x"), policy) == RUN
        assert executor.verdict(ToolCallPart("c", "nothing", {}), policy) == RUN
        assert executor.verdict(ToolCallPart("c", "export", {"name": "a"}), policy) == REFUSE
        assert executor.verdict(ToolCallPart("c", "export", {"name": "a"}), PermissionPolicy()) == ASK

    def test_refusal_tells_the_model_what_to_do(self):
        result = ToolExecutor.refused(ToolCallPart("c9", "apply_filter", {}))
        assert result.is_error and result.call_id == "c9" and result.content == ADVISOR_REFUSAL


def engine_with(policy, accept=True):
    tools = [spec("read", read_only=True), spec("write"), spec("export", destructive=True)]
    session = AgentSession(create_provider(ProviderConfig("anthropic", "m")), tools, "S")
    seen = []
    handlers = {tool.name: (lambda name: lambda a: seen.append(name) or {"ok": True})(tool.name) for tool in tools}
    transport, listener = Transport(), Listener(accept)
    engine = ChatEngine(session, ToolExecutor(tools, handlers), transport, listener, Checkpoint(), policy=policy)
    return engine, transport, listener, seen, session


def run_calls(policy, *names, accept=True):
    engine, transport, listener, seen, session = engine_with(policy, accept)
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, *(ToolCallPart(f"c{i}", name, {}) for i, name in enumerate(names))))
    return listener, seen, session


class TestEngineUnderALevel:
    def test_without_policy_the_engine_asks_as_before(self):
        listener, seen, _ = run_calls(None, "read", "write", "export")
        assert seen == ["read", "write", "export"]
        assert [entry for entry in listener.log if entry[0] == "confirm"] == [("confirm", "export")]

    def test_careful_asks_for_a_project_change(self):
        listener, seen, _ = run_calls(PermissionPolicy(CAREFUL), "read", "write", accept=False)
        assert seen == ["read"]
        assert ("confirm", "write") in listener.log

    def test_advisor_refuses_without_asking(self):
        listener, seen, session = run_calls(PermissionPolicy(ADVISOR), "read", "write", "export")
        assert seen == ["read"]
        assert not [entry for entry in listener.log if entry[0] == "confirm"]
        results = [part for part in session.messages[-1].parts]
        assert [part.content == ADVISOR_REFUSAL for part in results] == [False, True, True]

    def test_autonomous_exports_without_asking(self):
        listener, seen, _ = run_calls(PermissionPolicy(AUTONOMOUS), "export")
        assert seen == ["export"] and not [entry for entry in listener.log if entry[0] == "confirm"]

    def test_the_level_is_read_at_each_call(self):
        policy = PermissionPolicy(STANDARD)
        engine, transport, listener, seen, _ = engine_with(policy, accept=False)
        engine.send("go")
        transport.emit(turn(STOP_TOOL_USE, ToolCallPart("c1", "export", {})))
        assert seen == []
        policy.grant("export")
        transport.emit(turn(STOP_TOOL_USE, ToolCallPart("c2", "export", {})), index=-1)
        assert seen == ["export"]

    def test_declined_answer_is_unchanged(self):
        _, _, session = run_calls(PermissionPolicy(STANDARD), "export", accept=False)
        assert session.messages[-1].parts[0].content == DECLINED


class Protector:
    """Layers protected by id or name, as the adapter of the project answers."""

    def __init__(self, *names):
        self._names = list(names)

    def name_of(self, reference):
        reference = reference[:-3] if reference.endswith("_id") else reference
        return reference if reference in self._names else None

    def names(self):
        return list(self._names)


class TestProtectedLayers:
    def test_the_layers_a_call_changes(self):
        from core.agent.permissions import changed_layers
        assert changed_layers("apply_filter", {"layer_name": "communes"}) == ["communes"]
        assert changed_layers("cross_filter", {"source_layer": "routes", "target_layers": ["a", "b"]}) == ["a", "b"]
        assert changed_layers("join_layers", {"layer": "a", "join_layer": "b"}) == ["a"]
        assert changed_layers("zoom_to", {"layer": "a"}) == []
        assert changed_layers("rename_layer", {"layer": "Fond", "group": True}) == []
        assert changed_layers("clear_filters", {}) is None and changed_layers("clear_filters", {"layers": []}) is None

    @pytest.mark.parametrize("level", LEVELS)
    def test_a_change_of_a_protected_layer_is_refused_at_every_level(self, level):
        from core.agent.permissions import PROTECTED
        executor = ToolExecutor(chat_tools(), {})
        policy = PermissionPolicy(level, granted=("apply_filter",), protector=Protector("cadastre"))
        call = ToolCallPart("c", "apply_filter", {"layer_name": "cadastre_id", "expression": '"a" = 1'})
        assert executor.verdict(call, policy) == PROTECTED
        refusal = ToolExecutor.refused(call, policy).content
        assert "'cadastre'" in refusal and "protected" in refusal

    def test_reading_using_as_source_and_showing_stay_allowed(self):
        executor = ToolExecutor(chat_tools(), {})
        policy = PermissionPolicy(STANDARD, protector=Protector("cadastre"))
        for name, arguments in (
                ("cross_filter", {"source_layer": "cadastre", "target_layers": ["routes"], "predicates": ["Intersect"]}),
                ("zoom_to", {"layer": "cadastre"}), ("set_layers_visibility", {"layers": ["cadastre"], "visible": False}),
                ("join_layers", {"layer": "routes", "join_layer": "cadastre", "target_field": "a", "join_field": "a"})):
            call = ToolCallPart("c", name, arguments)
            assert executor.verdict(call, policy) == RUN, name

    def test_a_clear_is_refused_on_a_protected_layer_and_on_every_layer(self):
        from core.agent.permissions import PROTECTED
        executor = ToolExecutor(chat_tools(), {})
        call = ToolCallPart("c", "clear_filters", {"layers": ["routes", "cadastre"]})
        assert executor.verdict(call, PermissionPolicy(protector=Protector("cadastre"))) == PROTECTED
        assert executor.verdict(call, PermissionPolicy(protector=Protector())) == RUN
        # The chat asks for layers; another caller (REST) may clear them all: every protected layer counts then.
        assert "'cadastre'" in PermissionPolicy(protector=Protector("cadastre")).protection_refusal("clear_filters", {})

    def test_without_protector_nothing_changes_and_the_advisor_text_stays(self):
        call = ToolCallPart("c", "apply_filter", {"layer_name": "a", "expression": "1"})
        assert ToolExecutor.refused(call, PermissionPolicy(ADVISOR)).content == ADVISOR_REFUSAL
        assert ToolExecutor.refused(call).content == ADVISOR_REFUSAL

    def test_the_engine_answers_the_protection(self):
        tools = [spec("read", read_only=True), ToolSpec("apply_filter", "A tool.", EMPTY)]
        session = AgentSession(create_provider(ProviderConfig("anthropic", "m")), tools, "S")
        seen = []
        handlers = {"read": lambda a: seen.append("read") or {}, "apply_filter": lambda a: seen.append("f") or {}}
        transport, listener = Transport(), Listener(True)
        engine = ChatEngine(session, ToolExecutor(tools, handlers), transport, listener, Checkpoint(),
                            policy=PermissionPolicy(AUTONOMOUS, protector=Protector("cadastre")))
        engine.send("go")
        transport.emit(turn(STOP_TOOL_USE, ToolCallPart("c1", "apply_filter", {"layer_name": "cadastre"})))
        assert seen == [] and not [entry for entry in listener.log if entry[0] == "confirm"]
        assert "'cadastre'" in session.messages[-1].parts[0].content


class TestProtectedFavorites:
    def test_a_favorite_on_a_protected_layer_is_refused(self):
        from core.agent.permissions import PROTECTED

        class WithFavorites(Protector):
            def favorite_layers(self, favorite_id):
                return {"fav-1": ["cadastre_id"], "fav-2": ["routes_id"]}.get(favorite_id, [])

        executor = ToolExecutor(chat_tools(), {})
        policy = PermissionPolicy(AUTONOMOUS, protector=WithFavorites("cadastre"))
        assert executor.verdict(ToolCallPart("c", "apply_favorite", {"favorite_id": "fav-1"}), policy) == PROTECTED
        assert executor.verdict(ToolCallPart("c", "apply_favorite", {"favorite_id": "fav-2"}), policy) == RUN
        assert "'cadastre'" in ToolExecutor.refused(ToolCallPart("c", "apply_favorite", {"favorite_id": "fav-1"}),
                                                    policy).content

    def test_a_protector_without_favorites_lets_them_run(self):
        executor = ToolExecutor(chat_tools(), {})
        policy = PermissionPolicy(protector=Protector("cadastre"))
        assert executor.verdict(ToolCallPart("c", "apply_favorite", {"favorite_id": "fav-1"}), policy) == RUN


class TestToolRules:
    def names(self):
        return {tool.name: tool for tool in chat_tools()}

    def test_never_turns_a_tool_off_at_every_level(self):
        from core.agent.permissions import TURNED_OFF
        for level in LEVELS:
            policy = PermissionPolicy(level, rules={"zoom_to": "never"})
            assert policy.verdict(self.names()["zoom_to"]) == TURNED_OFF, level
        executor = ToolExecutor(chat_tools(), {})
        call = ToolCallPart("c", "zoom_to", {})
        refusal = ToolExecutor.refused(call, PermissionPolicy(rules={"zoom_to": "never"})).content
        assert "turned the tool 'zoom_to' off" in refusal
        assert executor.verdict(call, PermissionPolicy(rules={"zoom_to": "never"})) == TURNED_OFF

    def test_ask_asks_at_every_call_and_cannot_be_allowed_for_a_conversation(self):
        policy = PermissionPolicy(AUTONOMOUS, granted=("apply_filter",), rules={"apply_filter": "ask"})
        filter_tool = self.names()["apply_filter"]
        assert policy.verdict(filter_tool) == ASK and not policy.grantable(filter_tool)
        assert PermissionPolicy(rules={"list_layers": "ask"}).verdict(self.names()["list_layers"]) == ASK
        assert PermissionPolicy(ADVISOR, rules={"apply_filter": "ask"}).verdict(filter_tool) == REFUSE
        assert PermissionPolicy(ADVISOR, rules={"list_layers": "ask"}).verdict(self.names()["list_layers"]) == ASK

    def test_allow_runs_without_asking_but_not_over_advisor_nor_for_code(self):
        export = self.names()["export_layers"]
        assert PermissionPolicy(STANDARD).verdict(export) == ASK
        assert PermissionPolicy(STANDARD, rules={"export_layers": "allow"}).verdict(export) == RUN
        assert PermissionPolicy(ADVISOR, rules={"export_layers": "allow"}).verdict(export) == REFUSE
        code = spec("run_pyqgis", destructive=True)
        assert PermissionPolicy(AUTONOMOUS, rules={"run_pyqgis": "allow"}).verdict(code) == ASK

    def test_rules_that_cannot_be_read_are_left_out(self):
        from core.agent.permissions import clean_rules
        assert clean_rules({"a": "never", "b": "maybe", "undo_agent_step": "never", "run_pyqgis": "allow",
                            "c": "ask"}) == {"a": "never", "c": "ask"}
        assert clean_rules("nope") == {} and clean_rules(None) == {}

    def test_the_agent_own_tools_ignore_rules(self):
        policy = PermissionPolicy(rules={"add_project_note": "never"})
        assert policy.verdict(next(tool for tool in CHAT_ONLY if tool.name == "add_project_note")) == RUN

    def test_protection_comes_before_a_rule_that_allows(self):
        from core.agent.permissions import PROTECTED
        executor = ToolExecutor(chat_tools(), {})
        policy = PermissionPolicy(AUTONOMOUS, protector=Protector("cadastre"), rules={"apply_filter": "allow"})
        call = ToolCallPart("c", "apply_filter", {"layer_name": "cadastre", "expression": "1"})
        assert executor.verdict(call, policy) == PROTECTED


def test_a_tool_turned_off_and_left_out_is_still_answered_why():
    from core.agent.permissions import TURNED_OFF
    executor = ToolExecutor([spec("read", read_only=True)], {"read": lambda a: {}})
    call = ToolCallPart("c", "apply_filter", {"layer_name": "a", "expression": "1"})
    policy = PermissionPolicy(rules={"apply_filter": "never"})
    assert executor.verdict(call, policy) == TURNED_OFF
    assert "turned the tool 'apply_filter' off" in ToolExecutor.refused(call, policy).content
    assert executor.verdict(call, PermissionPolicy()) == RUN  # unknown, and answered as unknown


class ManyListener(Listener):
    def __init__(self, accept=True):
        super().__init__(accept)
        self.many = []

    def confirm_many(self, calls):
        self.many.append([c.name for c in calls])
        return self.accept


def run_with(listener, policy, *calls):
    tools = [spec("read", read_only=True), spec("write"), spec("other"), spec("run_pyqgis", destructive=True)]
    session = AgentSession(create_provider(ProviderConfig("anthropic", "m")), tools, "S")
    seen = []
    handlers = {tool.name: (lambda name: lambda a: seen.append(name) or {})(tool.name) for tool in tools}
    transport = Transport()
    engine = ChatEngine(session, ToolExecutor(tools, handlers), transport, listener, Checkpoint(), policy=policy)
    engine.send("go")
    transport.emit(turn(STOP_TOOL_USE, *calls))
    return seen, session


class TestOneQuestionForATurn:
    def test_several_calls_asked_together(self):
        listener = ManyListener(True)
        seen, _ = run_with(listener, PermissionPolicy(CAREFUL), ToolCallPart("c1", "read", {}),
                           ToolCallPart("c2", "write", {}), ToolCallPart("c3", "other", {}))
        assert listener.many == [["write", "other"]] and seen == ["read", "write", "other"]
        assert not [entry for entry in listener.log if entry[0] == "confirm"]

    def test_declined_together_runs_none_of_them(self):
        listener = ManyListener(False)
        seen, session = run_with(listener, PermissionPolicy(CAREFUL), ToolCallPart("c1", "write", {}),
                                 ToolCallPart("c2", "other", {}))
        assert seen == [] and [part.content for part in session.messages[-1].parts] == [DECLINED, DECLINED]

    def test_a_single_call_is_asked_alone_and_code_keeps_its_own_dialog(self):
        listener = ManyListener(True)
        seen, _ = run_with(listener, PermissionPolicy(CAREFUL), ToolCallPart("c1", "write", {}),
                           ToolCallPart("c2", "run_pyqgis", {}))
        assert listener.many == [] and [entry for entry in listener.log if entry[0] == "confirm"] == [
            ("confirm", "write"), ("confirm", "run_pyqgis")]

    def test_a_listener_without_it_is_asked_call_by_call(self):
        listener = Listener(True)
        seen, _ = run_with(listener, PermissionPolicy(CAREFUL), ToolCallPart("c1", "write", {}),
                           ToolCallPart("c2", "other", {}))
        assert [entry for entry in listener.log if entry[0] == "confirm"] == [("confirm", "write"), ("confirm", "other")]
