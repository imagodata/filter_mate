# -*- coding: utf-8 -*-
"""
AgentChatController across the life of a request: settings, another project, recipes, Stop, shutdown.

The controller is loaded by path under a private package: the pure modules of ``core`` are the real ones (the
conversation engine and its session included), ``bounded_http`` is the real one, and everything that needs QGIS or
Qt (panel, settings store, MCP bridge, turn checkpoint) is a stand-in.
"""
import importlib.util
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_agent_chat_lifecycle_test"


class _Stub(types.ModuleType):
    """A module whose names not set are mocks."""

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        value = MagicMock(name=f"{self.__name__}.{name}")
        setattr(self, name, value)
        return value


class FakeSignal:
    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def disconnect(self, slot):
        if slot not in self.slots:
            raise TypeError("not connected")
        self.slots.remove(slot)

    def emit(self, *args):
        for slot in list(self.slots):
            slot(*args)


class FakeProject:
    def __init__(self):
        self.cleared, self.readProject, self.fileNameChanged = FakeSignal(), FakeSignal(), FakeSignal()
        self.layersAdded, self.layersRemoved = FakeSignal(), FakeSignal()  # followed for the live recipes
        self.layers = {}

    def mapLayers(self):
        return dict(self.layers)

    def mapLayer(self, layer_id):
        return self.layers.get(layer_id)

    def mapLayersByName(self, name):
        return [layer for layer in self.layers.values() if getattr(layer, "name", lambda: "")() == name]


class FakeQgsProject:
    project = None

    @classmethod
    def instance(cls):
        return cls.project


class QObject:
    def __init__(self, parent=None):
        pass


class FakeCheckpoint:
    """The undo point of a turn: what was committed, and whether it was discarded."""

    def pending_edit_commits(self):
        return ()

    def __init__(self):
        self.label, self.describe, self.on_open, self.recorded = "", None, None, None
        self.open, self.committed, self.discarded = False, 0, 0

    def begin(self, call=None):
        self.open = True

    def step_of(self, call):
        return None

    def commit(self):
        if self.open:
            self.committed += 1
        self.open = False
        return ()

    def discard(self):
        self.discarded += 1
        self.open = False

    can_undo = staticmethod(lambda: True)
    can_redo = staticmethod(lambda: False)
    turns = staticmethod(lambda: [])
    applied = staticmethod(lambda: ())
    busy = staticmethod(lambda: "")


class FakeBridge:
    made = []

    def __init__(self, host, parent):
        self.listening, self.busy, self.error = False, False, ""
        self.close_error = None
        self.closed = self.forgotten = 0
        FakeBridge.made.append(self)

    def forget_change(self):
        self.forgotten += 1

    def sync(self):
        pass

    def close(self):
        self.closed += 1
        if self.close_error is not None:
            raise self.close_error


SETTINGS = types.SimpleNamespace(autonomy="standard", rules={}, preset="anthropic", model="m", ready=True,
                                 has_consent=True, send_values=True, expert_python=False, custom_sources="[]",
                                 enabled_sources=[], memory=True)


def _module(monkeypatch, name, **attrs):
    module = _Stub(f"{_PKG}{name}")
    module.__path__ = []
    for key, value in attrs.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    parent, _, child = module.__name__.rpartition(".")
    if parent in sys.modules:
        monkeypatch.setattr(sys.modules[parent], child, module, raising=False)
    return module


def _load(monkeypatch, name, rel):
    spec = importlib.util.spec_from_file_location(f"{_PKG}.{name}", _ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


class FakeCharts:
    """The d3 charts of the chat: none drawn, no layout followed."""

    def __init__(self, is_dark, parent=None):
        self.pending = None

    def watch_layers(self):
        pass

    def unwatch_all(self):
        pass

    def forget(self):
        pass


@pytest.fixture
def ctrl_module(monkeypatch):
    for name in ("qgis.PyQt.QtCore", "qgis.PyQt.QtWidgets", "qgis.PyQt.QtNetwork"):
        monkeypatch.setitem(sys.modules, name, _Stub(name))
    qtcore = sys.modules["qgis.PyQt.QtCore"]
    qtcore.QObject = QObject
    qtcore.QCoreApplication = types.SimpleNamespace(translate=lambda context, text: text)
    FakeQgsProject.project = FakeProject()
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsProject", FakeQgsProject, raising=False)
    _module(monkeypatch, "")
    core = types.ModuleType(f"{_PKG}.core")
    core.__path__ = [str(_ROOT / "core")]  # pure Python: the real modules
    monkeypatch.setitem(sys.modules, core.__name__, core)
    for name in (".adapters", ".adapters.agent", ".adapters.public_api", ".adapters.qgis",
                 ".adapters.qgis.coverage_layers", ".filtermate_api", ".ui", ".ui.controllers", ".ui.widgets"):
        _module(monkeypatch, name)
    _module(monkeypatch, ".adapters.agent.settings", load_settings=lambda: SETTINGS,
            KeyStoreError=type("KeyStoreError", (Exception,), {}))
    _module(monkeypatch, '.adapters.agent.conversation_store', open_store=lambda: None)
    _module(monkeypatch, '.adapters.public_api.qgis_interface', chat_handlers=lambda schedule=None: {
        'qgis_capabilities': lambda arguments: {'available': False},
        'control_qgis': lambda arguments: {'requested': True},
    })
    store = _module(monkeypatch, ".adapters.agent.transcript_store", project_key=lambda: "key", load=lambda key: [])
    store.saved = []
    store.save = lambda key, transcript: store.saved.append((key, list(transcript)))
    _module(monkeypatch, ".adapters.agent.project_notes_store", read_notes=lambda project=None: [])
    # The notes kept from one project to the next: none, unless a test gives some (``memory.held``).
    memory = _module(monkeypatch, ".adapters.agent.memory_store", held=None, sources=([], ""), changed=[],
                     memory_path=lambda: None)
    memory.read_memory = lambda path=None: memory.held if memory.held is not None else types.SimpleNamespace(notes=())
    memory.project_sources = lambda layer_ids=None, active_id="", project=None: memory.sources
    memory.change_memory = lambda changes, path=None, today="": memory.changed.append(list(changes))
    recipes = _module(monkeypatch, ".adapters.agent.recipes_store", recipes=[])
    recipes.read_recipes = lambda project=None: list(recipes.recipes)
    _module(monkeypatch, ".adapters.agent.turn_checkpoint", TurnCheckpoint=FakeCheckpoint)
    _module(monkeypatch, ".adapters.agent.plugin_settings", settings_handlers=lambda offered=None, approve=None: {}, set_applier=lambda applier: None,
            clear_applier=lambda applier: None,
            planned=lambda arguments: [])
    protection = types.SimpleNamespace(name_of=lambda reference: None, names=lambda: [],
                                       favorite_layers=lambda favorite_id: [])
    _module(monkeypatch, ".adapters.agent.protected_layers", ProjectProtection=lambda: protection,
            read_ids=lambda: [])
    _module(monkeypatch, ".adapters.agent.agent_widgets", read_widgets=lambda project=None: [])
    _module(monkeypatch, ".adapters.agent.mcp_connection")
    _module(monkeypatch, ".adapters.agent.qt_transport")
    _module(monkeypatch, ".filtermate_api.agent_tools", build_handlers=lambda *args, **kwargs: {})
    _module(monkeypatch, ".filtermate_api.accessor", FilterRejected=type("FilterRejected", (Exception,), {}))
    _module(monkeypatch, ".filtermate_api.main_thread", QGISBusy=type("QGISBusy", (Exception,), {}))
    _module(monkeypatch, ".filtermate_api.config", _qgis_profile_dir=lambda: '')
    _load(monkeypatch, 'filtermate_api.export_root', 'filtermate_api/export_root.py')
    _module(monkeypatch, ".filtermate_api.qgis_accessor")
    _module(monkeypatch, ".ui.controllers.agent_mcp_bridge", AgentMcpBridge=FakeBridge)
    _module(monkeypatch, ".ui.controllers.agent_charts", AgentCharts=FakeCharts, file_stem=str)
    _module(monkeypatch, ".ui.controllers.agent_data", AgentDataController=MagicMock())
    _module(monkeypatch, ".ui.controllers.agent_outputs", AgentOutputsController=MagicMock())
    _module(monkeypatch, ".ui.widgets.agent_panel", ANSWER_CONVERSATION="conversation", ANSWER_NO="no",
            ANSWER_ONCE="once", AgentPanel=lambda parent: MagicMock(), level_short=str, preset_label=str)
    _module(monkeypatch, ".ui.widgets.agent_widgets_strip", number_text=str)
    bounded_http = _load(monkeypatch, "adapters.agent.bounded_http", "adapters/agent/bounded_http.py")
    _load(monkeypatch, "ui.controllers.history_tips", "ui/controllers/history_tips.py")
    _load(monkeypatch, "ui.controllers.setup_wizard", "ui/controllers/setup_wizard.py")
    _load(monkeypatch, "ui.controllers.welcome_tour", "ui/controllers/welcome_tour.py")
    module = _load(monkeypatch, "ui.controllers.agent_chat_controller", "ui/controllers/agent_chat_controller.py")
    module._test_bounded_http = bounded_http
    module._test_store = store
    module._test_recipes = recipes
    return module


@pytest.fixture
def dock():
    return types.SimpleNamespace(undoRedoStateRequested=FakeSignal())


@pytest.fixture
def controller(ctrl_module, dock):
    return ctrl_module.AgentChatController(lambda page: None, MagicMock(), dock, ask_user=lambda title, text: True)


@pytest.fixture
def activity_state(controller):
    state = {"phase": "thinking"}
    controller.panel.set_activity_phase.side_effect = lambda phase: state.update(phase=phase)
    controller.panel.activity_phase.side_effect = lambda: state["phase"]
    return state


def test_activity_follows_tools_text_and_provider_retry(ctrl_module, controller, activity_state):
    catalog = sys.modules[f"{_PKG}.core.agent.tool_catalog"]
    messages = sys.modules[f"{_PKG}.core.agent.messages"]
    controller._tools = {
        "read": catalog.ToolSpec("read", "Read", {}, read_only=True),
        "write": catalog.ToolSpec("write", "Write", {}),
        "fetch": catalog.ToolSpec("fetch", "Fetch", {}, open_world=True),
    }
    for name, phase in (("read", "reading"), ("write", "working"), ("fetch", "fetching")):
        controller.on_tool_start(messages.ToolCallPart(name, name, {}))
        assert activity_state["phase"] == phase
    controller.on_text("Answer")
    assert activity_state["phase"] == "responding"
    controller.on_retry(2, messages.ProviderError(messages.ERROR_SERVER, "busy"))
    assert activity_state["phase"] == "retry"


def test_waiting_activity_restores_the_step_after_a_question_or_exception(controller, activity_state):
    controller._set_activity("working")
    with controller._activity("waiting"):
        assert activity_state["phase"] == "waiting"
    assert activity_state["phase"] == "working"
    with pytest.raises(ValueError):
        with controller._activity("waiting"):
            raise ValueError("closed")
    assert activity_state["phase"] == "working"


@pytest.mark.parametrize('tool, phase', [
    ('search_open_data', 'searching'), ('run_algorithm', 'processing'), ('update_features', 'editing'),
    ('export_layers', 'exporting'), ('set_layer_style', 'designing'), ('zoom_to', 'navigating'),
])
def test_the_activity_identifies_the_actual_tool_task(controller, ctrl_module, tool, phase):
    call = ctrl_module.ToolCallPart('activity', tool, {})
    assert controller._tool_activity(call) == phase


def test_waiting_activity_does_not_overwrite_stop_or_a_new_conversation(controller, activity_state):
    with controller._activity("waiting"):
        controller._on_stop()
    assert activity_state["phase"] == "stopping"
    with controller._activity("waiting"):
        controller._memory_generation += 1
        controller._set_activity("thinking")
    assert activity_state["phase"] == "thinking"


def _engine(ctrl_module, controller, handler):
    """A real conversation engine on a transport the test feeds, with one tool that changes something."""
    chat_engine = sys.modules[f"{_PKG}.core.agent.chat_engine"]
    session_module = sys.modules[f"{_PKG}.core.agent.session"]
    providers = sys.modules[f"{_PKG}.core.agent.providers"]
    catalog = sys.modules[f"{_PKG}.core.agent.tool_catalog"]
    executor = sys.modules[f"{_PKG}.core.agent.tool_executor"]
    write = catalog.ToolSpec("write", "Change something here.", {"type": "object", "properties": {}})
    session = session_module.AgentSession(providers.create_provider(providers.ProviderConfig("anthropic", "m")),
                                          [write], "S")

    class Transport:
        def __init__(self):
            self.starts = []

        def start(self, request, parser, on_event):
            self.starts.append(on_event)
            return types.SimpleNamespace(abort=lambda: None)

    transport = Transport()
    engine = chat_engine.ChatEngine(session, executor.ToolExecutor([write], {"write": handler}), transport,
                                    controller, controller._checkpoint)
    controller._engine = engine
    return engine, transport


def _tool_turn(ctrl_module):
    messages = sys.modules[f"{_PKG}.core.agent.messages"]
    return messages.TurnComplete(messages.Message(messages.ROLE_ASSISTANT, (messages.ToolCallPart("c1", "write", {}),)),
                                 messages.STOP_TOOL_USE)


def _end_turn(ctrl_module):
    messages = sys.modules[f"{_PKG}.core.agent.messages"]
    return messages.TurnComplete(messages.Message(messages.ROLE_ASSISTANT, (messages.TextPart("done"),)),
                                 messages.STOP_END)


@pytest.mark.parametrize('finish', ['done', 'stop', 'project'])
def test_interface_handoffs_wait_for_commit_and_disappear_on_stop_or_project_change(
        ctrl_module, controller, activity_state, finish):
    seen = []
    def handoff():
        assert not controller._checkpoint.open
        assert controller._checkpoint.committed
        assert activity_state['phase'] == 'waiting'
        seen.append('opened')
    def tool(arguments):
        controller._schedule_interface_handoff(handoff)
        return {'scheduled': True}
    engine, transport = _engine(ctrl_module, controller, tool)
    controller._on_send('open properties after the work')
    transport.starts[-1](_tool_turn(ctrl_module))
    assert seen == []
    if finish == 'done':
        transport.starts[-1](_end_turn(ctrl_module))
        assert seen == ['opened']
    elif finish == 'stop':
        controller._on_stop()
        assert not seen and not controller._interface_handoffs
    else:
        FakeQgsProject.project.cleared.emit()
        assert not seen and not controller._interface_handoffs


def test_edit_save_confirmation_is_offered_after_the_engine_records_the_turn(ctrl_module, controller):
    engine, transport = _engine(ctrl_module, controller, lambda arguments: {})
    def edits():
        assert not controller._checkpoint.open and controller._checkpoint.committed
        return (('roads', 2),)
    controller._checkpoint.pending_edit_commits = edits
    controller._on_send('edit this layer')
    transport.starts[-1](_tool_turn(ctrl_module))
    controller._data.offer_edits.assert_not_called()
    transport.starts[-1](_end_turn(ctrl_module))
    controller._data.offer_edits.assert_called_once_with((('roads', 2),))


def test_push_steers_the_same_engine_and_keeps_its_permissions(ctrl_module, controller):
    engine, transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller.panel.input.text.return_value = ""
    controller._on_send("original request")
    level = controller._policy.level
    controller.panel.input.text.return_value = "use blue instead"
    assert controller._on_push("use blue instead")
    assert controller._engine is engine and engine.busy and len(transport.starts) == 2
    assert controller._policy.level == level
    assert controller._last_request == "original request\n\nuse blue instead"
    controller.panel.clear_input.assert_called_once()
    controller.panel.add_user.assert_called_with("use blue instead")
    assert len(transport.starts) == 2 and engine.session.messages[-1].text == "use blue instead"
    transport.starts[-1](_end_turn(ctrl_module))


def test_push_preserves_a_different_draft(ctrl_module, controller):
    _engine(ctrl_module, controller, lambda arguments: {})
    controller.panel.input.text.return_value = "unfinished draft"
    controller._on_send("original request")
    assert controller._on_push("correction")
    controller.panel.clear_input.assert_not_called()


def test_push_while_idle_starts_a_regular_exchange(ctrl_module, controller):
    engine, transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller.panel.input.text.return_value = ""
    assert controller._on_push("new request")
    assert engine.busy and len(transport.starts) == 1
    assert engine.session.messages[0].parts[0].text == "new request"


def test_push_during_recipe_is_refused_without_consuming_draft(ctrl_module, controller):
    engine, _transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller._replaying = True
    assert not controller._on_push("correction")
    controller.panel.clear_input.assert_not_called()
    assert not engine.busy


def test_stop_before_delivery_returns_the_original_request_and_push_together(ctrl_module, controller):
    _engine(ctrl_module, controller, lambda arguments: {})
    controller.panel.input.text.return_value = ""
    controller._on_send("original request")
    controller._on_push("correction")
    controller._on_stop()
    controller.panel.input.setText.assert_called_with("original request\n\ncorrection")
    controller.panel.restore_queued.assert_not_called()


def test_provider_failure_gives_back_the_combined_request(ctrl_module, controller):
    engine, transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller.panel.input.text.return_value = ""
    controller._on_send("original request")
    controller._on_push("correction")
    messages = sys.modules[f"{_PKG}.core.agent.messages"]
    transport.starts[-1](messages.StreamFailure(messages.ProviderError("auth", "refused")))
    controller.panel.input.setText.assert_called_with("original request\n\ncorrection")
    controller.panel.restore_queued.assert_not_called()
    assert not engine.busy


def test_stop_after_changes_returns_undelivered_push_to_the_paused_queue(ctrl_module, controller):
    engine, transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller.panel.input.text.return_value = ""
    controller._on_send("original request")
    # Stop while a provider response is in flight, after the first write completed.
    transport.starts[-1](_tool_turn(ctrl_module))
    engine._defer = lambda step: None  # stop before the new provider request can consume the corrections
    controller._on_push("first correction")
    controller._on_push("second correction")
    controller._on_stop()
    assert [call.args for call in controller.panel.restore_queued.call_args_list] == [
        ("second correction", controller._request_posture), ("first correction", controller._request_posture)]
    assert not engine.busy


def test_queued_push_preserves_even_an_identical_draft(ctrl_module, controller):
    engine, transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller.panel.input.text.return_value = "correction"
    controller._on_send("original request")
    controller._on_queued_push("correction", controller._request_posture)
    assert engine.busy and len(transport.starts) == 2
    assert engine.session.messages[-1].text == "correction"
    controller.panel.clear_input.assert_not_called()
    controller.panel.restore_queued.assert_not_called()


@pytest.mark.parametrize('posture', ['respond', 'propose'])
def test_push_in_a_different_posture_is_queued_without_using_the_active_permissions(ctrl_module, controller, posture):
    engine, transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller._on_send('original request', 'act')
    controller._posture = posture
    controller.panel.input.text.return_value = 'only discuss this'
    assert controller._on_push('only discuss this')
    controller.panel.queue_message.assert_called_once_with('only discuss this', posture, first=False)
    assert len(transport.starts) == 1 and controller._last_request == 'original request'
    assert controller._request_posture == 'act' and engine.busy
    assert all(message.text != 'only discuss this' for message in engine.session.messages)
    controller.panel.clear_input.assert_called_once()


def test_promoting_a_queued_message_respects_its_saved_posture(ctrl_module, controller):
    engine, transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller._on_send('original request', 'act')
    controller._posture = 'act'
    controller.panel.input.text.return_value = 'draft'
    controller._on_queued_push('question', 'respond')
    controller.panel.queue_message.assert_called_once_with('question', 'respond', first=True)
    controller.panel.clear_input.assert_not_called()
    assert len(transport.starts) == 1 and engine.busy


def test_queued_push_while_idle_uses_the_saved_posture(ctrl_module, controller):
    engine, transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller.panel.input.text.return_value = "draft"
    controller._on_queued_push("waiting request", "respond")
    assert engine.busy and len(transport.starts) == 1
    assert controller._request_posture == "respond"
    controller.panel.clear_input.assert_not_called()


def test_rejected_queued_push_is_restored_with_its_posture(ctrl_module, controller):
    _engine(ctrl_module, controller, lambda arguments: {})
    controller._on_send("original request")
    controller._replaying = True
    controller._on_queued_push("waiting request", "respond")
    controller.panel.restore_queued.assert_called_once_with("waiting request", "respond")


# --- 4: a conversation is let go of only once really over -----------------------------------------------------


def test_settings_wait_for_the_end_of_the_turn(ctrl_module, controller, monkeypatch):
    dialogs = []
    monkeypatch.setattr(ctrl_module, "AgentSettingsDialog", lambda *args, **kwargs: dialogs.append(args))
    engine, _transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller._on_send("go")
    assert controller.open_settings() is False  # the link of an earlier error card, clicked during the turn
    assert dialogs == [] and controller._engine is engine and engine.busy


def test_settings_wait_for_the_conversation_being_made(ctrl_module, controller, monkeypatch):
    dialogs = []
    monkeypatch.setattr(ctrl_module, "AgentSettingsDialog", lambda *args, **kwargs: dialogs.append(args))

    def build():  # the connectors are listed: the event loop runs, an old error card is clicked
        assert controller.open_settings() is False
        return None

    monkeypatch.setattr(controller, "_build_engine", build)
    controller._on_send("go")
    assert dialogs == []


def test_a_conversation_left_while_its_tool_runs_ends_before_another_starts(ctrl_module, controller):
    seen = {}

    def tool(arguments):  # a tool that spins the event loop: the user starts a new conversation meanwhile
        controller.new_conversation()
        seen["busy"] = controller.chat_busy()
        controller._on_send("second")  # refused: the first request has not ended
        return {"ok": True}

    engine, transport = _engine(ctrl_module, controller, tool)
    controller._on_send("first")
    controller.panel.reset_mock()
    transport.starts[0](_tool_turn(ctrl_module))
    assert seen["busy"] is True
    assert len(transport.starts) == 1  # no second request beside the first
    assert not engine.busy and controller._engine is None  # let go of once over
    controller.panel.add_action.assert_not_called()  # its card does not land in the new conversation
    assert not controller.chat_busy()


# --- 5: another project during a request ------------------------------------------------------------------------


def test_another_project_during_a_tool_records_no_turn(ctrl_module, controller):
    project = FakeQgsProject.project
    controller._journal_later.append(("call", "result", "client"))

    def tool(arguments):
        project.cleared.emit()  # the user opens another project while the tool waits
        project.readProject.emit()
        return {"ok": True}

    engine, transport = _engine(ctrl_module, controller, tool)
    controller._on_send("go")
    transport.starts[0](_tool_turn(ctrl_module))
    checkpoint = controller._checkpoint
    assert checkpoint.discarded == 1 and checkpoint.committed == 0  # nothing compared with the next project
    assert controller._journal_later == []  # the lines of the closed project do not reach the next thread
    assert not engine.busy and controller._engine is None


def test_another_project_stops_a_recipe_quietly(ctrl_module, controller, monkeypatch):
    catalog = sys.modules[f"{_PKG}.core.agent.tool_catalog"]
    write = catalog.ToolSpec("write", "Change something here.", {"type": "object", "properties": {}})
    project, ran = FakeQgsProject.project, []

    def tool(arguments):
        ran.append(arguments["n"])
        project.cleared.emit()  # another project opened during the first step
        return {"ok": True}

    monkeypatch.setattr(controller, "tools_and_handlers", lambda values, for_chat=True: ([write], {"write": tool}, []))
    ctrl_module._test_recipes.recipes = [{"id": "r1", "name": "R", "request": "", "steps": [
        {"tool": "write", "arguments": {"n": 1}, "label": "one"}, {"tool": "write", "arguments": {"n": 2}, "label": "two"}]}]
    controller.panel.reset_mock()
    assert controller.run_recipe("r1") is False
    assert ran == [1]  # stopped before its next step
    assert controller._checkpoint.committed == 0
    controller.panel.add_note.assert_not_called()  # its end is not written in the thread of the next project
    assert not controller.chat_busy()


def test_another_project_ends_what_the_chat_waits_for(ctrl_module, controller):
    """2026-11-12: the tool left behind went on waiting (Processing has no time limit) in the closed project."""
    bounded_http, stopped = ctrl_module._test_bounded_http, []

    def tool(arguments):
        forget = bounded_http.on_abort(lambda: stopped.append("chat"))
        FakeQgsProject.project.cleared.emit()
        forget()
        return {"ok": True}

    engine, transport = _engine(ctrl_module, controller, controller._chat_owned({"write": tool})["write"])
    controller._on_send("go")
    transport.starts[0](_tool_turn(ctrl_module))
    assert stopped == ["chat"]


def test_another_project_forgets_the_change_of_another_application(ctrl_module, controller):
    FakeQgsProject.project.cleared.emit()
    assert controller._mcp.forgotten == 1  # its undo point is not recorded either


def test_a_change_of_another_application_during_another_project_is_not_recorded(ctrl_module, monkeypatch):
    """2026-11-12: committed after the project changed, every layer of the new project was "added" by the change."""
    _module(monkeypatch, ".adapters.agent.native_mcp")
    _module(monkeypatch, ".adapters.public_api.map_images", handlers=lambda: {})
    bridge_module = _load(monkeypatch, "ui.controllers.real_agent_mcp_bridge", "ui/controllers/agent_mcp_bridge.py")
    catalog = sys.modules[f"{_PKG}.core.agent.tool_catalog"]
    executor = sys.modules[f"{_PKG}.core.agent.tool_executor"]
    messages = sys.modules[f"{_PKG}.core.agent.messages"]
    made = []
    monkeypatch.setattr(bridge_module, "TurnCheckpoint", lambda: made.append(FakeCheckpoint()) or made[-1])
    host = types.SimpleNamespace(describe_call=str, label_of=lambda call, client: client, history_changed=lambda: None)
    bridge = bridge_module.AgentMcpBridge(host, None)
    write = catalog.ToolSpec("write", "Change something here.", {"type": "object", "properties": {}})

    def tool(arguments):
        bridge.forget_change()  # what the chat does when the project is cleared during the change
        return {"ok": True}

    bridge._executor = executor.ToolExecutor([write], {"write": tool})
    bridge._change(messages.ToolCallPart("c1", "write", {}), "client")
    assert made[0].discarded == 1 and made[0].committed == 0
    bridge.forget_change()  # between two changes: nothing to forget
    bridge._executor = executor.ToolExecutor([write], {"write": lambda arguments: {"ok": True}})
    bridge._change(messages.ToolCallPart("c2", "write", {}), "client")
    assert made[1].committed == 1


def test_an_abandoned_recipe_lets_the_lines_of_other_applications_through(ctrl_module, controller, monkeypatch):
    catalog = sys.modules[f"{_PKG}.core.agent.tool_catalog"]
    write = catalog.ToolSpec("write", "Change something here.", {"type": "object", "properties": {}})
    project, flushed = FakeQgsProject.project, []
    monkeypatch.setattr(controller, "_log_action", lambda call, result, label, keep=True: flushed.append(label))
    monkeypatch.setattr(controller, "label_of", lambda call, client: client)

    def tool(arguments):
        project.cleared.emit()
        project.readProject.emit()
        controller.journal(types.SimpleNamespace(name="apply_filter"), "result", "client")  # queued: the chat works
        return {"ok": True}

    monkeypatch.setattr(controller, "tools_and_handlers", lambda values, for_chat=True: ([write], {"write": tool}, []))
    ctrl_module._test_recipes.recipes = [{"id": "r1", "name": "R", "request": "", "steps": [
        {"tool": "write", "arguments": {"n": 1}, "label": "one"}]}]
    controller.run_recipe("r1")
    assert controller._journal_later == [] and flushed == ["client"]


def test_closing_the_dock_stops_a_recipe(ctrl_module, controller, monkeypatch):
    catalog = sys.modules[f"{_PKG}.core.agent.tool_catalog"]
    write = catalog.ToolSpec("write", "Change something here.", {"type": "object", "properties": {}})
    ran = []

    def tool(arguments):
        ran.append(arguments["n"])
        controller.stop()  # the dock closes during the first step
        return {"ok": True}

    monkeypatch.setattr(controller, "tools_and_handlers", lambda values, for_chat=True: ([write], {"write": tool}, []))
    ctrl_module._test_recipes.recipes = [{"id": "r1", "name": "R", "request": "", "steps": [
        {"tool": "write", "arguments": {"n": 1}, "label": "one"}, {"tool": "write", "arguments": {"n": 2}, "label": "two"}]}]
    assert controller.run_recipe("r1") is False
    assert ran == [1] and controller._checkpoint.committed == 1  # the step that ran stays, undoable


# --- 6: Undo of the action bar during a turn --------------------------------------------------------------------


def test_the_action_bar_follows_the_turn(ctrl_module, controller, dock):
    states = []
    dock.undoRedoStateRequested.connect(lambda: states.append(controller.undo_state()["can_undo"]))
    _engine_, transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller._on_send("go")
    assert states[-1] is False  # Undo and Ctrl+Z are off while the agent works
    transport.starts[0](_end_turn(ctrl_module))
    assert states[-1] is True


# --- 6b: a request that breaks off after steps keeps them, and does not come back whole ---------------------------


def _failure(ctrl_module, kind="stream"):
    messages = sys.modules[f"{_PKG}.core.agent.messages"]
    return messages.StreamFailure(messages.ProviderError(kind, "The response was cut before its end."))


def test_a_failure_after_steps_says_they_stay_and_keeps_the_request_out_of_the_line(ctrl_module, controller):
    _engine_, transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller.panel.input.text.return_value = ""
    controller._on_send("add the parks")
    transport.starts[0](_tool_turn(ctrl_module))
    transport.starts[1](_failure(ctrl_module))
    detail = controller.panel.show_error.call_args[0][1]
    assert "stopped midway. Steps already done" in detail and "): 1." in detail and "go on" in detail
    controller.panel.input.setText.assert_not_called()
    assert controller.panel.show_error.call_args[0][3] == "Continue"
    controller.panel.show_error.call_args[0][4]()
    assert controller._last_request == "Go on with what is left of the request."


@pytest.mark.parametrize("kind", ["auth", "quota", "bad_request"])
def test_a_failure_after_steps_that_settings_or_a_refusal_make_vain_gives_the_request_back(ctrl_module, controller, kind):
    _engine_, transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller.panel.input.text.return_value = ""
    controller._on_send("add the parks")
    transport.starts[0](_tool_turn(ctrl_module))
    transport.starts[1](_failure(ctrl_module, kind))
    detail = controller.panel.show_error.call_args[0][1]
    assert detail.startswith("The 1 steps before stay, and can be undone. The request is back in the line below")
    assert "stopped midway" not in detail and "ask for what is left" not in detail
    assert ("fix the settings" in detail) is (kind != "bad_request")
    assert controller.panel.show_error.call_args[0][2] is (kind != "bad_request")
    controller.panel.input.setText.assert_called_with("add the parks")


def test_a_failure_before_any_step_gives_the_request_back(ctrl_module, controller):
    _engine_, transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller.panel.input.text.return_value = ""
    controller._on_send("add the parks")
    transport.starts[0](_failure(ctrl_module))
    assert "back in the line below" in controller.panel.show_error.call_args[0][1]
    controller.panel.input.setText.assert_called_with("add the parks")


def test_stop_after_steps_says_they_stay(ctrl_module, controller):
    engine, transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller.panel.input.text.return_value = ""
    controller._on_send("add the parks")
    transport.starts[0](_tool_turn(ctrl_module))
    engine.cancel()
    said = controller.panel.set_status.call_args[0][0]
    assert said.startswith("Stopped midway. Steps already done") and "): 1." in said
    controller.panel.input.setText.assert_not_called()


def test_a_busy_provider_is_said_while_the_agent_waits(ctrl_module, controller):
    messages = sys.modules[f"{_PKG}.core.agent.messages"]
    controller.on_retry(5.6, messages.ProviderError("server", "Overloaded", status=529))
    assert controller.panel.set_status.call_args[0][0] == "The provider is busy, trying again in 6 s…"


def test_a_new_try_says_thinking_again_before_it_starts(ctrl_module, controller):
    _engine_, transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller._on_send("add the parks")  # the chat is busy: the engine waits for the model
    log = []
    controller.panel.set_status.side_effect = lambda text: log.append(("status", text))
    controller._again(lambda: log.append(("step",)))()
    assert log == [("status", "Thinking…"), ("step",)]


def test_a_new_try_after_the_end_of_the_chat_only_runs_the_step(ctrl_module, controller):
    log = []
    controller.panel.set_status.side_effect = lambda text: log.append(("status", text))
    assert not controller.chat_busy()
    controller._again(lambda: log.append(("step",)))()
    assert log == [("step",)]


def test_a_new_try_of_an_abandoned_request_says_nothing(ctrl_module, controller):
    _engine_, transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller._on_send("add the parks")
    controller._abandoned = True
    log = []
    controller.panel.set_status.side_effect = lambda text: log.append(("status", text))
    controller._again(lambda: log.append(("step",)))()
    assert log == [("step",)]


# --- 7: Stop ends the waits of the chat, not those of another application ------------------------------------


@pytest.mark.parametrize("stop", ["_on_stop", "stop"])
def test_stop_leaves_the_calls_of_other_applications(ctrl_module, controller, stop):
    bounded_http = ctrl_module._test_bounded_http
    stopped = []
    forget_client = bounded_http.on_abort(lambda: stopped.append("mcp client"))  # answered by the MCP server

    def tool(arguments):
        forget = bounded_http.on_abort(lambda: stopped.append("chat"))
        getattr(controller, stop)()  # Stop pressed, or the dock closed, while the tool waits
        forget()
        return {}

    controller._chat_owned({"tool": tool})["tool"]({})
    assert stopped == ["chat"]
    bounded_http.abort_active()  # without an owner: every wait, as before
    assert stopped == ["chat", "mcp client"]
    forget_client()


# --- 8: the summary of a request does not count web services ---------------------------------------------------


def test_the_summary_does_not_count_a_web_service(ctrl_module, controller, monkeypatch):
    kinds = sys.modules[f"{_PKG}.core.domain.layer_kind"].LayerKind

    class Layer:
        def __init__(self, layer_id, remote, subset=""):
            self._id, self.remote, self.subset, self.counted = layer_id, remote, subset, 0

        def id(self):
            return self._id

        def name(self):
            return self._id.upper()

        def isValid(self):
            return True

        def featureCount(self):
            self.counted += 1
            return 12

        def subsetString(self):
            return self.subset

        def crs(self):
            return types.SimpleNamespace(authid=lambda: "EPSG:2154")

    local, wfs = Layer("local", False, "a > 1"), Layer("wfs", True)
    FakeQgsProject.project.layers = {"wfs": wfs, "local": local}
    _module(monkeypatch, ".adapters.public_api.introspection",
            tree_places=lambda: {"local": (0, "", True), "wfs": (1, "Base", False)})
    _module(monkeypatch, ".adapters.public_api.operations", layer_kind=lambda layer: kinds.VECTOR)
    _module(monkeypatch, ".adapters.qgis.coverage_layers.snapshots", registry=lambda: {})
    _module(monkeypatch, ".adapters.qgis.source_capability_probe", counts_cheaply=lambda layer: not layer.remote)
    _module(monkeypatch, ".adapters.qgis.feature_count", COUNT_BUDGET=1.0,
            exact_feature_count=lambda layer, budget: 7 if budget > 0 else None, table_seconds=lambda: 0.0)
    rows = controller._layer_rows()
    assert wfs.counted == 0  # featureCount() of a web service can be a request to its server
    # The count of a filtered GeoPackage can be the count of its whole table (feature_count.py): not read.
    assert local.counted == 0
    assert [(row["name"], row["feature_count"], row["active_filter_expression"], row["group"], row["visible"])
            for row in rows] == [("LOCAL", 7, "a > 1", "", True), ("WFS", -1, "", "Base", False)]


def test_the_memory_goes_with_the_context_of_a_request(ctrl_module, controller, monkeypatch):
    """The notes for every project and those of the sources of the project, once; nothing when the option is off, when
    none is kept, or when the file cannot be read."""
    core_memory = sys.modules[f"{_PKG}.core.agent.memory"]
    store = sys.modules[f"{_PKG}.adapters.agent.memory_store"]
    assert controller._memory_part(None) == ""  # nothing kept: not a character more
    kept, _note = core_memory.added(core_memory.Memory(), "MRO = zone de mutualisation")
    kept, _note = core_memory.added(kept, "aérien = type_infra 'AER'", "source", "ogr::troncons", with_values=True)
    store.held, store.sources = kept, ([("ogr::troncons", "Tronçons")], "ogr::troncons")
    block = controller._memory_part(([{"layer_id": "t1"}], [], {"active_layer_id": "t1"}))
    assert block.splitlines() == [core_memory.HEADER, core_memory.USER_TITLE, "- m1: MRO = zone de mutualisation",
                                  "For the layer Tronçons:", "- m2: aérien = type_infra 'AER'"]
    assert block in controller._project_context(full=True)
    controller._context_memory.sent()
    monkeypatch.setattr(controller, "_seen", {}, raising=False)  # an answer ended: the next request says what changed
    monkeypatch.setattr(controller, "_read_project", lambda: None)
    assert core_memory.HEADER not in controller._project_context(full=False)  # sent once, then when it changed
    store.held, _note = core_memory.added(kept, "réponds en mètres")
    assert "- m3: réponds en mètres" in controller._project_context(full=False)
    monkeypatch.setattr(ctrl_module, "load_settings", lambda: types.SimpleNamespace(memory=True, send_values=False))
    assert "- aérien" not in controller._memory_part(([{"layer_id": "t1"}], [], {}))  # values no longer shared
    monkeypatch.setattr(ctrl_module, "load_settings", lambda: types.SimpleNamespace(memory=False, send_values=True))
    assert controller._memory_part(None) == ""
    monkeypatch.setattr(ctrl_module, "load_settings", lambda: SETTINGS)

    def unreadable(path=None):
        raise core_memory.UnreadableMemory("it is not JSON")
    monkeypatch.setattr(ctrl_module, "read_memory", unreadable)  # the name the controller bound at import
    assert controller._memory_part(None) == ""  # the request goes without it; the Memory tab says why


def test_the_range_selection_goes_with_the_context_when_values_are_shared(ctrl_module, controller, monkeypatch):
    """The bounds a range widget holds go with the request; without shared values they stay out (2026-11-25: an
    UnboundLocalError emptied the widgets of the request silently, the try/except hiding it)."""
    stub = sys.modules[f"{_PKG}.adapters.agent.agent_widgets"]
    model = sys.modules[f"{_PKG}.core.agent.widgets"]
    widget = model.make([], "range", "L1", "communes", "", field="pop", minimum=0, maximum=10)
    monkeypatch.setattr(stub, "read_widgets", lambda project=None: [widget])
    assert '"high": 10' in controller._project_context(full=True)
    monkeypatch.setattr(ctrl_module, "load_settings", lambda: types.SimpleNamespace(memory=True, send_values=False))
    assert '"high": 10' not in controller._project_context(full=True)
    monkeypatch.setattr(ctrl_module, "load_settings", lambda: SETTINGS)


# --- 9: a controller half built, a shutdown that goes on -------------------------------------------------------


def test_a_controller_whose_page_failed_does_not_follow_the_project(ctrl_module, dock):
    def add_page(page):
        raise RuntimeError("no accordion")

    with pytest.raises(RuntimeError):
        ctrl_module.AgentChatController(add_page, MagicMock(), dock, ask_user=lambda title, text: True)
    project = FakeQgsProject.project
    assert not (project.cleared.slots or project.readProject.slots or project.fileNameChanged.slots)


def test_a_controller_failing_at_its_end_leaves_no_server_and_does_not_follow_the_project(ctrl_module, dock,
                                                                                           monkeypatch):
    def broken(self):
        raise RuntimeError("no settings")

    monkeypatch.setattr(ctrl_module.AgentChatController, "_refresh_ready", broken)
    with pytest.raises(RuntimeError):
        ctrl_module.AgentChatController(lambda page: None, MagicMock(), dock, ask_user=lambda title, text: True)
    project = FakeQgsProject.project
    assert not (project.cleared.slots or project.readProject.slots or project.fileNameChanged.slots)
    assert FakeBridge.made[-1].closed == 1


def test_shutdown_goes_on_when_a_step_fails(ctrl_module, controller):
    project, stopped = FakeQgsProject.project, []
    forget = ctrl_module._test_bounded_http.on_abort(lambda: stopped.append("mcp client"))
    controller._mcp.close_error = RuntimeError("wrapped C/C++ object has been deleted")
    controller.shutdown()
    assert stopped == ["mcp client"]  # unloading, nothing may arrive afterwards
    assert controller._mcp.closed == 1
    assert not (project.cleared.slots or project.readProject.slots or project.fileNameChanged.slots)
    forget()


def _recipe_tools(monkeypatch, controller, ran, names=("add_layer", "remove_layers", "export_layers", "apply_filter")):
    catalog = sys.modules[f"{_PKG}.core.agent.tool_catalog"]
    tools = [tool for tool in catalog.chat_tools() if tool.name in names]
    handlers = {tool.name: (lambda name: lambda arguments: ran.append(name) or {"ok": True})(tool.name) for tool in tools}
    monkeypatch.setattr(controller, "tools_and_handlers", lambda values, for_chat=True: (tools, handlers, []))


def test_a_recipe_that_cannot_be_read_frees_the_panel(ctrl_module, controller, monkeypatch):
    """2026-11-13: the steps asked together were read before the try; an error there (RecursionError on a forged
    recipe) left the panel busy until QGIS restarted: no request, no undo, no recipe."""
    ran = []
    _recipe_tools(monkeypatch, controller, ran)

    def broken(*args, **kwargs):
        raise RecursionError("maximum recursion depth exceeded")

    monkeypatch.setattr(ctrl_module, "stale_reference", broken)
    ctrl_module._test_recipes.recipes = [{"id": "r1", "name": "R", "request": "", "steps": [
        {"tool": "apply_filter", "arguments": {"layer_name": "A", "expression": "1"}, "label": "one"}]}]
    controller.panel.reset_mock()
    assert controller.run_recipe("r1") is False
    assert ran == []
    assert not controller.chat_busy() and not controller._replaying
    controller.panel.set_working.assert_called_with(False)
    note = controller.panel.add_note.call_args[0][0]
    assert "Step 1 was not run" in note and "recursion" not in note  # said in the thread; why is in the log


def test_a_recipe_runs_with_every_tool_not_the_lighter_set_of_a_local_model(ctrl_module, controller, monkeypatch):
    """No model runs a recipe: "only the tools that filter", for a small model in the chat, stopped its steps."""
    ran, asked = [], []
    _recipe_tools(monkeypatch, controller, ran)
    chat_tools = controller.tools_and_handlers
    monkeypatch.setattr(controller, "tools_and_handlers",
                        lambda values, for_chat=True: asked.append(for_chat) or chat_tools(values, for_chat))
    ctrl_module._test_recipes.recipes = [{"id": "r1", "name": "R", "request": "", "steps": [
        {"tool": "apply_filter", "arguments": {"layer_name": "A", "expression": "1"}, "label": "one"}]}]
    controller.run_recipe("r1")
    assert asked == [False]


@pytest.mark.parametrize("name", ["turn_off_agent_options", "turn_on_agent_options", "ask_user"])
def test_a_recipe_never_runs_a_tool_of_the_chat_alone(ctrl_module, controller, monkeypatch, name):
    """A recipe of a received project turned the sources of the agent off, without a question."""
    ran = []
    _recipe_tools(monkeypatch, controller, ran, names=("apply_filter", name))
    ctrl_module._test_recipes.recipes = [{"id": "r1", "name": "R", "request": "", "steps": [
        {"tool": "apply_filter", "arguments": {"layer_name": "A", "expression": "1"}, "label": "one"},
        {"tool": name, "arguments": {"sources": ["datagouv"]}, "label": "two"}]}]
    controller.panel.reset_mock()
    assert controller.run_recipe("r1") is False
    assert ran == ["apply_filter"]  # the second step is not run
    assert "Step 2 needs a tool" in controller.panel.add_note.call_args[0][0]


def test_a_panel_that_fails_at_the_start_of_a_recipe_is_not_left_busy(ctrl_module, controller, monkeypatch):
    ran = []
    _recipe_tools(monkeypatch, controller, ran)
    ctrl_module._test_recipes.recipes = [{"id": "r1", "name": "R", "request": "", "steps": [
        {"tool": "apply_filter", "arguments": {"layer_name": "A", "expression": "1"}, "label": "one"}]}]
    controller.panel.add_user.side_effect = RuntimeError("wrapped C/C++ object has been deleted")
    assert controller.run_recipe("r1") is False
    assert ran == [] and not controller.chat_busy()


def test_what_fails_after_a_step_ran_does_not_say_the_step_failed(ctrl_module, controller, monkeypatch):
    ran = []
    _recipe_tools(monkeypatch, controller, ran)
    ctrl_module._test_recipes.recipes = [{"id": "r1", "name": "R", "request": "", "steps": [
        {"tool": "apply_filter", "arguments": {"layer_name": "A", "expression": "1"}, "label": "one"},
        {"tool": "apply_filter", "arguments": {"layer_name": "B", "expression": "1"}, "label": "two"}]}]

    def broken(*args, **kwargs):
        raise RuntimeError("the journal is closed")

    monkeypatch.setattr(controller, "_log_action", broken)
    controller.panel.reset_mock()
    assert controller.run_recipe("r1") is False
    assert ran == ["apply_filter"]  # the first step ran, the run stopped there
    note = controller.panel.add_note.call_args[0][0]
    assert "Stopped before step 2" in note and "failed" not in note
    assert "The 1 steps before stay" in note
    assert not controller.chat_busy()


def test_no_to_the_list_of_a_recipe_runs_and_asks_nothing_more(ctrl_module, controller, monkeypatch):
    """A recipe went on after the no: the source asked alone was asked again, and added."""
    asked, ran = [], []
    controller._ask_user = lambda title, text: asked.append(text) or False
    _recipe_tools(monkeypatch, controller, ran)
    ctrl_module._test_recipes.recipes = [{"id": "r1", "name": "R", "request": "", "steps": [
        {"tool": "add_layer", "arguments": {"source": "https://tracker.example/p.geojson", "name": "Parks"}, "label": "x"},
        {"tool": "remove_layers", "arguments": {"layers": ["A"]}, "label": "y"},
        {"tool": "export_layers", "arguments": {"layers": ["A"]}, "label": "z"}]}]
    controller.panel.reset_mock()
    assert controller.run_recipe("r1") is False
    assert ran == [] and len(asked) == 1
    assert "Step 2 was not run" in controller.panel.add_note.call_args[0][0]


def test_a_recipe_asks_a_deletion_alone_with_its_expression(ctrl_module, controller, monkeypatch):
    asked, ran = [], []
    controller._ask_user = lambda title, text: asked.append(text) or True
    _recipe_tools(monkeypatch, controller, ran, names=("delete_features", "remove_layers", "export_layers"))
    ctrl_module._test_recipes.recipes = [{"id": "r1", "name": "R", "request": "", "steps": [
        {"tool": "remove_layers", "arguments": {"layers": ["A"]}, "label": "y"},
        {"tool": "export_layers", "arguments": {"layers": ["B"]}, "label": "z"},
        {"tool": "delete_features", "arguments": {"layer": "parcels", "expression": '"owner" = 7'}, "label": "x"}]}]
    assert controller.run_recipe("r1") is True
    assert len(asked) == 2 and '"owner" = 7' in asked[1] and '"owner" = 7' not in asked[0]


def test_a_question_never_approves_more_than_it_lists(ctrl_module, dock):
    asked = []
    controller = ctrl_module.AgentChatController(lambda page: None, MagicMock(), dock,
                                                 ask_user=lambda title, text: asked.append(text) or True)
    call = sys.modules[f"{_PKG}.core.agent.messages"].ToolCallPart
    limit = sys.modules[f"{_PKG}.core.agent.permissions"].MAX_ASKED_TOGETHER
    calls = [call(str(number), "remove_layers", {"layers": [f"L{number}"]}) for number in range(limit + 1)]
    assert controller.confirm_many(calls) is False and asked == []
    assert controller.confirm_many(calls[:limit]) is True and f"L{limit - 1}" in asked[0]


def test_a_recipe_asks_a_remote_source_alone_with_its_address(ctrl_module, controller, monkeypatch):
    """2026-11-13: one question listed "Layer added: Parks" and "Layers removed: A": the address was never shown."""
    asked, ran = [], []
    controller._ask_user = lambda title, text: asked.append(text) or True
    _recipe_tools(monkeypatch, controller, ran)
    ctrl_module._test_recipes.recipes = [{"id": "r1", "name": "R", "request": "", "steps": [
        {"tool": "add_layer", "arguments": {"source": "https://tracker.example/p.geojson", "name": "Parks"}, "label": "x"},
        {"tool": "remove_layers", "arguments": {"layers": ["A"]}, "label": "y"},
        {"tool": "export_layers", "arguments": {"layers": ["A"]}, "label": "z"}]}]
    assert controller.run_recipe("r1") is True
    assert ran == ["add_layer", "remove_layers", "export_layers"]
    together, alone = asked[0], asked[1]  # the list first, then the source when its step comes
    assert len(asked) == 2 and "tracker.example" in alone and "tracker.example" not in together
    assert "Parks" not in together


def test_a_confirm_card_names_the_layers_and_how_reversible_they_are(ctrl_module, controller):  # noqa: F811
    call = sys.modules[f"{_PKG}.core.agent.messages"].ToolCallPart
    deleted = call("1", "delete_features", {"layer": "parcels", "expression": '"owner" = 7'})
    assert controller._confirm_layers(deleted) == ["parcels"]
    assert "saved" in controller._reversibility_text(deleted)
    assert controller._confirm_text(deleted).count("edit buffer") == 1  # own wording, no duplicate line
    removed = call("2", "remove_layers", {"layers": ["A", "B", "A"]})
    assert controller._confirm_layers(removed) == ["A", "B"]
    assert "Final" in controller._reversibility_text(removed)
    assert "Final" in controller._confirm_text(removed)
    filtered = call("3", "apply_filter", {"layer_name": "roads", "expression": '"kind" = 1'})
    assert controller._confirm_layers(filtered) == ["roads"]
    assert "Undo" in controller._reversibility_text(filtered)


def test_no_card_asks_each_action_while_nothing_runs(ctrl_module, controller):  # noqa: F811
    call = sys.modules[f"{_PKG}.core.agent.messages"].ToolCallPart
    assert controller.confirm_each([call("1", "remove_layers", {"layers": ["A"]})]) is None


def test_the_error_card_sends_the_last_request_again(ctrl_module, controller, monkeypatch):  # noqa: F811
    sent = []
    monkeypatch.setattr(controller, "_on_send", lambda text, mode="", queued=False: sent.append((text, mode, queued)))
    controller.panel.input.text.return_value = "unfinished draft"
    request, generation = controller._memory_request, controller._memory_generation
    controller._retry_failed("filter the parcels", "propose", request, generation)
    assert sent == [("filter the parcels", "propose", True)]
    controller._memory_request += 1
    controller._retry_failed("filter the parcels", "act", request, generation)
    assert len(sent) == 1
    controller._memory_request = request
    controller._memory_generation += 1
    controller._retry_failed("filter the parcels", "act", request, generation)
    assert len(sent) == 1


def test_the_question_for_several_actions_shows_their_arguments(ctrl_module, dock):
    """As the single question does for a tool without words of its own: the arguments as they are."""
    asked = []
    controller = ctrl_module.AgentChatController(lambda page: None, MagicMock(), dock,
                                                 ask_user=lambda title, text: asked.append(text) or True)
    call = sys.modules[f"{_PKG}.core.agent.messages"].ToolCallPart
    controller.confirm_many([call("1", "apply_filter", {"layer_name": "roads", "expression": '"kind" = 1'}),
                             call("2", "export_layers", {"layers": ["roads"], "format": "gpkg"})])
    assert '\\"kind\\" = 1' in asked[0] and "gpkg" in asked[0]


# --- 10: the setup with the agent, offered once per version -----------------------------------------------------


class FakeSettings:
    """QgsSettings: one store for every instance."""

    values = {}

    def value(self, key, default=None):
        return FakeSettings.values.get(key, default)

    def setValue(self, key, value):  # noqa: N802 - Qt name
        FakeSettings.values[key] = value


class FakeCard:
    """A card of the thread with its two buttons (ui/widgets/agent_thread.SettingsCard)."""

    def __init__(self):
        self.apply_requested, self.cancel_requested = FakeSignal(), FakeSignal()
        self.done, self.accepted = False, None

    def finish(self, accepted):
        if not self.done:
            self.done, self.accepted = True, accepted


@pytest.fixture
def offer(ctrl_module, controller, dock, monkeypatch):
    """A controller whose dock has the AGENT section folded, as it is when the plugin opens."""
    FakeSettings.values = {}
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsSettings", FakeSettings, raising=False)
    state = types.SimpleNamespace(cards=[], opened=[], sent=[], agent_open=False, key=controller.SETUP_OFFERED_KEY)
    controller.panel.add_settings_card = lambda texts, lines, reason: state.cards.append(FakeCard()) or state.cards[-1]
    dock._fm_sections = types.SimpleNamespace(is_open=lambda key: state.agent_open,
                                              open_top=lambda key: state.opened.append(key))
    controller._on_send = state.sent.append
    # The setup asks with cards, no request (ui/controllers/setup_wizard.py): its start counts as what was sent.
    controller._wizard = types.SimpleNamespace(start=lambda: state.sent.append("setup"), forget=lambda: None,
                                               offer_back_again=lambda: state.sent.append("back link"))
    return state


def test_the_setup_sends_nothing_to_a_model(controller, offer):
    assert controller.start_setup() is True
    assert offer.sent == ["setup"]


def test_refining_the_setup_asks_the_model(controller, offer):
    assert controller.start_model_setup() is True
    assert len(offer.sent) == 1 and offer.sent[0] != "setup"


def test_an_offer_nobody_saw_is_not_kept_as_made(controller, offer):
    """2026-11-13: the card went in the folded AGENT section and the version was kept as offered at once."""
    assert controller.offer_setup_once("9.9.9") is True
    assert len(offer.cards) == 1 and offer.key not in FakeSettings.values
    assert controller.offer_setup_once("9.9.9") is False and len(offer.cards) == 1  # one card, not one per call

    controller._on_panel_shown()  # shown behind another tab, as QGIS restores a panel: nobody saw the card
    assert offer.key not in FakeSettings.values

    offer.agent_open = True
    controller._on_panel_shown()  # the user opens AGENT: the card is in view
    assert FakeSettings.values[offer.key] == "9.9.9"
    assert controller.offer_setup_once("9.9.9") is False


def test_an_offer_made_in_the_open_section_is_kept_at_once(controller, offer):
    offer.agent_open = True
    assert controller.offer_setup_once("9.9.9") is True
    assert FakeSettings.values[offer.key] == "9.9.9"


def test_an_offer_in_a_panel_just_put_back_waits_for_the_tabs_to_be_laid_out(controller, offer, dock):
    """2026-11-16, review: AGENT in its own panel, put back behind the tab of the dock when QGIS starts. Qt had
    not laid the tabs out yet: the panel read as in view and the offer was kept as seen."""
    dock._fm_sections.detached = {"agent"}
    offer.agent_open = True  # what Qt says before the layout
    assert controller.offer_setup_once("9.9.9") is True
    assert offer.key not in FakeSettings.values  # asked again a moment later (QTimer), and when its tab comes

    offer.agent_open = False  # laid out: behind the tab of the dock
    controller._on_panel_shown()
    assert offer.key not in FakeSettings.values
    offer.agent_open = True  # the user clicks its tab
    controller._on_panel_shown()
    assert FakeSettings.values[offer.key] == "9.9.9"


def test_in_view_is_asked_of_a_dock_that_knows_it(controller, offer, dock):
    """Open in the dock is not in view when the dock is behind the tab of another panel of QGIS."""
    offer.agent_open = True
    dock._fm_sections.in_view = lambda key: False
    dock._fm_sections.bring_in_view = lambda key: offer.opened.append(("in view", key))
    assert controller._agent_shown() is False
    controller._show_agent()
    assert offer.opened == [("in view", "agent")]


def test_an_offer_nobody_saw_comes_back_in_the_thread_of_another_project(controller, offer):
    """Opening a project empties the thread: the card went with it, for good."""
    controller.offer_setup_once("9.9.9")
    project = FakeQgsProject.project
    project.cleared.emit()
    project.readProject.emit()
    assert len(offer.cards) >= 2 and not offer.cards[-1].done and offer.key not in FakeSettings.values
    assert "back link" in offer.sent  # what puts the settings of the setup back returns with the thread

    offer.agent_open = True
    controller._on_panel_shown()
    shown = len(offer.cards)
    project.cleared.emit()
    project.readProject.emit()
    assert len(offer.cards) == shown  # seen once: it does not come back


def test_start_during_a_request_leaves_the_offer_open(controller, offer):
    """The card read "Setup started." while the panel said to wait: nothing to start it again from."""
    controller.offer_setup_once("9.9.9")
    card = offer.cards[0]
    controller._building = True
    card.apply_requested.emit()
    assert not card.done and offer.sent == []
    assert "Wait" in controller.panel.set_status.call_args.args[0]

    controller._building = False
    card.apply_requested.emit()
    assert card.done and card.accepted is True and len(offer.sent) == 1
    assert FakeSettings.values[offer.key] == "9.9.9"


def test_the_agent_section_opens_before_the_setup_says_to_wait(controller, offer):
    """Started from the QGIS menu during a request: the message was said in the folded section."""
    controller._building = True
    assert controller.start_setup() is False
    assert offer.opened == ["agent"] and offer.sent == []


def test_a_setup_started_from_a_menu_closes_the_offer(controller, offer):
    """The first opening of a version from the menu entry left a card to start what was already running."""
    controller.offer_setup_once("9.9.9")
    assert controller.start_setup() is True
    card = offer.cards[0]
    assert card.done and card.accepted is True and len(offer.sent) == 1
    assert FakeSettings.values[offer.key] == "9.9.9"


def test_not_now_without_a_provider_gives_the_welcome_back(ctrl_module, controller, offer, monkeypatch):
    """The card replaced the welcome and its "Connect a provider" button: after "Not now" the panel showed a closed
    card above an input that takes nothing."""
    monkeypatch.setattr(ctrl_module, "load_settings", lambda: types.SimpleNamespace(**{**vars(SETTINGS), "ready": False}))
    controller.offer_setup_once("9.9.9")
    controller.panel.clear_thread.reset_mock()
    offer.cards[0].cancel_requested.emit()
    controller.panel.clear_thread.assert_called_once_with()
    assert "Not now" in controller.panel.set_status.call_args.args[0]
    assert FakeSettings.values[offer.key] == "9.9.9"


def test_not_now_with_a_provider_keeps_the_card_and_what_it_says(controller, offer):
    controller.offer_setup_once("9.9.9")
    controller.panel.clear_thread.reset_mock()
    card = offer.cards[0]
    card.cancel_requested.emit()
    assert card.done and card.accepted is False
    controller.panel.clear_thread.assert_not_called()
    assert FakeSettings.values[offer.key] == "9.9.9"


def test_a_new_conversation_does_not_bring_the_offer_back(controller, offer):
    """The user asked for an empty thread: the offer is not put in it again at the next project."""
    controller.offer_setup_once("9.9.9")
    controller.new_conversation()
    assert FakeSettings.values[offer.key] == "9.9.9"
    shown = len(offer.cards)
    FakeQgsProject.project.cleared.emit()
    FakeQgsProject.project.readProject.emit()
    assert len(offer.cards) == shown


def test_other_tools_under_the_same_provider_keep_the_thread(controller):
    """A source ticked on the advice of the agent used to clear the thread, its advice with it (audit of 14/11)."""
    controller._engine = types.SimpleNamespace(busy=False)
    controller._transcript = [{"kind": "user", "text": "ajoute un fond"}]
    controller._recap_from = 0
    controller._policy.grant("export_layers")
    controller.panel.clear_thread = MagicMock()
    controller._restart_engine()
    assert controller._engine is None and not controller.panel.clear_thread.called
    assert controller._policy.granted == {"export_layers"}  # what was allowed for the conversation stays
    assert controller._recap_from == 0  # the next conversation with the model is told what the thread holds
    controller._engine = types.SimpleNamespace(busy=False)
    controller._reset_view()  # another provider: nothing of it goes on
    assert controller.panel.clear_thread.called and not controller._policy.granted
    assert controller._recap_from == len(controller._transcript)


@pytest.fixture
def saved_conversations(ctrl_module, controller, monkeypatch):
    stored = {}
    monkeypatch.setattr(ctrl_module, "session_store", types.SimpleNamespace(
        load=lambda key: stored.get(key, ""), save=lambda key, text: stored.__setitem__(key, text)))
    controller._transcript_key = "project-a"
    return stored


def test_reset_view_cannot_restore_the_conversation_it_just_left(ctrl_module, controller, saved_conversations):
    engine, _transport = _engine(ctrl_module, controller, lambda arguments: {})
    engine.session.add_user_text("private context of the previous conversation")
    controller._engine_identity = (SETTINGS.preset, SETTINGS.model)
    controller._engine_context = controller._session_context(SETTINGS)
    controller._reset_view()  # provider/account changed, even if preset and model still match
    next_engine, _transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller._resume_session(next_engine.session, SETTINGS)
    assert next_engine.session.messages == ()


@pytest.mark.parametrize("changes", [{"base_url": "https://another-server.example/v1"},
                                      {"authcfg": "another-account"}, {"send_values": False}])
def test_stored_conversation_does_not_cross_server_account_or_sharing_settings(
        ctrl_module, controller, saved_conversations, changes):
    engine, _transport = _engine(ctrl_module, controller, lambda arguments: {})
    engine.session.add_user_text("private context of this destination")
    controller._engine_identity = (SETTINGS.preset, SETTINGS.model)
    controller._engine_context = controller._session_context(SETTINGS)
    controller._save_session()
    assert saved_conversations["project-a"]
    next_engine, _transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller._resume_session(next_engine.session, types.SimpleNamespace(**(vars(SETTINGS) | changes)))
    assert next_engine.session.messages == ()


def test_same_destination_resumes_after_tools_restart(ctrl_module, controller, saved_conversations):
    engine, _transport = _engine(ctrl_module, controller, lambda arguments: {})
    engine.session.add_user_text("keep working on these communes")
    controller._engine_identity = (SETTINGS.preset, SETTINGS.model)
    controller._engine_context = controller._session_context(SETTINGS)
    controller._restart_engine()
    next_engine, _transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller._resume_session(next_engine.session, SETTINGS)
    assert [message.text for message in next_engine.session.messages] == ["keep working on these communes"]


@pytest.fixture
def archive(ctrl_module, controller, saved_conversations, tmp_path, monkeypatch):
    from core.agent.conversations import ConversationStore
    store = ConversationStore(tmp_path / 'conversations.sqlite3')
    controller._conversations = store
    controller._conversation_project = store.project('project-a')
    controller._conversation_path = '/p/source.qgz'
    controller._conversation_id = store.start(controller._conversation_project, controller._conversation_path)
    monkeypatch.setattr(FakeQgsProject.project, 'fileName', lambda: '/p/source.qgz', raising=False)
    monkeypatch.setattr(ctrl_module.transcript_store, 'project_key', lambda: 'project-a')
    return store


def test_new_conversation_is_archived_and_reopened_without_replaying_tools(ctrl_module, controller, archive):
    engine, _transport = _engine(ctrl_module, controller, lambda arguments: pytest.fail('tool was replayed'))
    engine.session.add_user_text('Original context')
    controller._engine_identity = (SETTINGS.preset, SETTINGS.model)
    controller._engine_context = controller._session_context(SETTINGS)
    controller._record('user', 'Original request')
    controller._record('action', 'Filter applied')
    controller._policy.grant('export_layers')
    identifier = controller._conversation_id
    controller.new_conversation()
    assert controller._conversation_id != identifier
    assert controller._transcript == []
    assert archive.get(identifier)['session']
    assert not controller._policy.granted
    controller._record('user', 'Second request')
    second = controller._conversation_id
    controller._open_conversation(identifier)
    assert archive.get(second)['transcript'][0]['text'] == 'Second request'
    assert [entry['text'] for entry in controller._transcript] == ['Original request', 'Filter applied']
    assert archive.head(controller._conversation_project)['id'] == identifier
    next_engine, _transport = _engine(ctrl_module, controller, lambda arguments: pytest.fail('tool was replayed'))
    controller._resume_session(next_engine.session, SETTINGS)
    assert [message.text for message in next_engine.session.messages] == ['Original context']


def test_another_project_conversation_is_read_only(controller, archive):
    other_project = archive.project('another-project')
    other = archive.start(other_project, '/p/other.qgz')
    archive.save(other, other_project, [{'kind': 'user', 'text': 'Other question'}])
    active = controller._conversation_id
    controller._record('user', 'Current question')
    controller._open_conversation(other)
    assert controller._conversation_id == active
    assert controller._transcript[0]['text'] == 'Current question'
    assert archive.head(controller._conversation_project)['id'] == active


def test_save_as_retains_identity_and_closing_cannot_transfer_old_context(
        ctrl_module, controller, archive, monkeypatch):
    controller._record('user', 'Saved under a new name')
    previous = controller._conversation_id
    monkeypatch.setattr(ctrl_module.transcript_store, 'project_key', lambda: 'saved-as')
    controller._on_file_name_changed()
    assert archive.project('saved-as') == controller._conversation_project
    engine, _transport = _engine(ctrl_module, controller, lambda arguments: {})
    engine.session.add_user_text('Private context of the old project')
    controller._engine_identity = (SETTINGS.preset, SETTINGS.model)
    controller._engine_context = controller._session_context(SETTINGS)
    controller._on_project_cleared()
    assert archive.get(previous)['session']
    assert controller._stored_session() == ''
    assert archive.head(controller._conversation_project) is None


def test_reset_to_another_provider_archives_but_does_not_resume_its_context(
        ctrl_module, controller, archive):
    engine, _transport = _engine(ctrl_module, controller, lambda arguments: {})
    engine.session.add_user_text('Private provider context')
    controller._engine_identity = (SETTINGS.preset, SETTINGS.model)
    controller._engine_context = controller._session_context(SETTINGS)
    controller._record('user', 'Private provider question')
    previous = controller._conversation_id
    controller._reset_view()
    assert archive.get(previous)['session']
    assert controller._stored_session() == ''
    assert controller._conversation_id != previous


def test_archive_write_failure_keeps_the_conversation_open(controller, archive, monkeypatch):
    controller._record('user', 'Do not lose this conversation')
    identifier = controller._conversation_id
    controller.panel.clear_thread.reset_mock()
    def failed_save(*args, **kwargs):
        raise OSError('disk full')
    monkeypatch.setattr(archive, 'save', failed_save)
    controller.new_conversation()
    assert controller._conversation_id == identifier
    assert controller._transcript[0]['text'] == 'Do not lose this conversation'
    controller.panel.clear_thread.assert_not_called()


def test_reading_a_project_does_not_overwrite_its_existing_archive_identity(controller, archive):
    controller._record('user', 'Conversation of the saved project')
    controller._save_transcript()
    project, identifier = controller._conversation_project, controller._conversation_id
    controller._on_project_cleared()
    controller._on_file_name_changed()  # QGIS emits this while reading, before readProject
    controller._on_project_read()
    assert controller._conversation_project == project
    assert controller._conversation_id == identifier
    assert controller._transcript[0]['text'] == 'Conversation of the saved project'


@pytest.mark.parametrize('changes', [{'send_values': False}, {'authcfg': 'another-account'},
                                      {'base_url': 'https://another-server.example/v1'}])
def test_an_incompatible_archive_cannot_send_its_private_context_as_a_recap(
        ctrl_module, controller, archive, monkeypatch, changes):
    engine, _transport = _engine(ctrl_module, controller, lambda arguments: {})
    engine.session.add_user_text('Private history of the original destination')
    controller._engine_identity = (SETTINGS.preset, SETTINGS.model)
    controller._engine_context = controller._session_context(SETTINGS)
    controller._record('user', 'Private transcript of the original destination')
    controller._save_session()
    wanted = types.SimpleNamespace(**(vars(SETTINGS) | changes))
    monkeypatch.setattr(ctrl_module, 'load_settings', lambda: wanted)
    controller._restore_transcript()
    assert controller._transcript[0]['text'] == 'Private transcript of the original destination'
    assert controller._recap_from == len(controller._transcript)


# --- the context of a request taken out of the conversation is sent again ----------------------------------------

ROW = {"layer_id": "c1", "name": "communes", "layer_kind": "vector", "feature_count": 10,
       "active_filter_expression": ""}


def _sent_texts(engine):
    """The text of every message of the user the model would be sent now."""
    messages = sys.modules[f"{_PKG}.core.agent.messages"]
    return [message.text for message in engine._session._messages if message.role == messages.ROLE_USER]


def _news(engine):
    """How many messages of the user carry the change of the project, and the protected layer."""
    texts = _sent_texts(engine)
    return (sum("communes" in text and "Changed in QGIS" in text for text in texts),
            sum("Communes" in text for text in texts))


@pytest.fixture
def news(ctrl_module, controller):
    """A first request done; then the user filtered a layer and protected another: news for the next request."""
    state = {"rows": [dict(ROW)]}
    controller._read_project = lambda: (state["rows"], [], {})
    engine, transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller.panel.input.text.return_value = ""
    controller._on_send("first")
    transport.starts[-1](_end_turn(ctrl_module))
    state["rows"] = [dict(ROW, active_filter_expression='"dept" = \'31\'')]
    controller._protection.names = lambda: ["Communes"]
    return engine, transport


def test_stop_before_any_step_sends_the_news_of_the_request_again(controller, news):
    engine, _transport = news
    controller._on_send("second")  # carries the news
    assert _news(engine) == (1, 1)
    engine.cancel()  # nothing ran: the request leaves the conversation with its news
    assert _news(engine) == (0, 0)
    controller._on_send("third")
    assert _news(engine) == (1, 1), "the model never learned of the change"


def test_a_refusal_before_any_step_sends_the_news_of_the_request_again(ctrl_module, controller, news):
    messages = sys.modules[f"{_PKG}.core.agent.messages"]
    engine, transport = news
    controller._on_send("second")
    transport.starts[-1](messages.TurnComplete(messages.Message(messages.ROLE_ASSISTANT, ()), messages.STOP_REFUSAL))
    assert _news(engine) == (0, 0)
    controller._on_send("third")
    assert _news(engine) == (1, 1), "the model never learned of the change"


def test_stop_after_a_step_keeps_the_news_it_carried(ctrl_module, controller, news):
    engine, transport = news
    controller._on_send("second")
    transport.starts[-1](_tool_turn(ctrl_module))
    engine.cancel()  # a step ran: the request stays in the conversation, with its news
    assert _news(engine) == (1, 1)
    controller._on_send("third")
    assert _news(engine) == (1, 1)  # told once, not again


@pytest.mark.parametrize("how", ["stop", "refusal", "failure"])
def test_a_removal_is_told_after_a_request_that_left_the_conversation(ctrl_module, controller, monkeypatch, how):
    """Level back to standard and protection removed, then a request taken out: the history still holds the advisor
    note and the protected layer of the first request, and the next request must say both are gone."""
    messages = sys.modules[f"{_PKG}.core.agent.messages"]
    monkeypatch.setattr(SETTINGS, "autonomy", "advisor")
    controller._read_project = lambda: ([dict(ROW)], [], {})  # a project that can be read: deltas, not full states
    controller._protection.names = lambda: ["Communes"]
    engine, transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller.panel.input.text.return_value = ""
    controller._on_send("first")
    transport.starts[-1](_end_turn(ctrl_module))
    monkeypatch.setattr(SETTINGS, "autonomy", "standard")
    controller._protection.names = lambda: []
    controller._on_send("second")
    assert any("standard again" in text for text in _sent_texts(engine))
    if how == "stop":
        engine.cancel()
    elif how == "refusal":
        transport.starts[-1](messages.TurnComplete(messages.Message(messages.ROLE_ASSISTANT, ()),
                                                   messages.STOP_REFUSAL))
    else:
        transport.starts[-1](_failure(ctrl_module))
    assert not any("standard again" in text for text in _sent_texts(engine))
    controller._on_send("third")
    last = _sent_texts(engine)[-1]
    assert "standard again" in last and "No layer is protected" in last


def test_a_request_taken_out_after_a_compaction_sends_everything_again(ctrl_module, controller):
    """A compaction during the request may have taken the context of the earlier ones: the next request is full."""
    engine, transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller.panel.input.text.return_value = ""
    controller._on_send("first")
    transport.starts[-1](_end_turn(ctrl_module))
    controller._on_send("second")
    engine._session.rewritten = True  # as add_user_text sets it when it summed the history up
    engine.cancel()
    assert controller._context_memory.empty


def test_the_recap_of_a_thread_taken_up_again_survives_a_refusal(ctrl_module, controller):
    messages = sys.modules[f"{_PKG}.core.agent.messages"]
    engine, transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller.panel.input.text.return_value = ""
    controller._recap = "Earlier in this thread: ..."
    controller._on_send("first")
    assert controller._recap == ""  # sent with the request
    transport.starts[-1](messages.TurnComplete(messages.Message(messages.ROLE_ASSISTANT, ()), messages.STOP_REFUSAL))
    assert controller._recap == "Earlier in this thread: ..."  # the message that carried it left the conversation
    controller._on_send("again")
    assert "Earlier in this thread" in _sent_texts(engine)[-1]


@pytest.mark.parametrize("how", ["stop", "failure"])
def test_the_cards_answered_come_back_when_the_request_left_the_conversation(ctrl_module, controller, how):
    engine, transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller.panel.input.text.return_value = ""
    controller._settings_outcomes = ["declined: theme"]
    controller._on_send("first")
    assert controller._settings_outcomes == [] and "declined: theme" in _sent_texts(engine)[-1]
    if how == "stop":
        engine.cancel()
    else:
        transport.starts[-1](_failure(ctrl_module))
    assert controller._settings_outcomes == ["declined: theme"]
    controller._on_send("second")
    assert "declined: theme" in _sent_texts(engine)[-1]


def test_the_cards_answered_stay_said_when_the_request_stays(ctrl_module, controller):
    engine, transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller.panel.input.text.return_value = ""
    controller._settings_outcomes = ["declined: theme"]
    controller._on_send("first")
    transport.starts[-1](_end_turn(ctrl_module))
    assert controller._settings_outcomes == []


@pytest.mark.parametrize("steps, kind", [(False, "stream"), (True, "bad_request")])
def test_a_failure_that_took_the_request_out_sends_its_news_again(ctrl_module, controller, news, steps, kind):
    """No step kept, or the server refused what the history holds (the request is forgotten whole): the news of the
    project that the request carried are told again, and the state seen does not move."""
    engine, transport = news
    controller._on_send("second")
    if steps:
        transport.starts[-1](_tool_turn(ctrl_module))
    transport.starts[-1](_failure(ctrl_module, kind))
    assert _news(engine) == (0, 0)
    controller._on_send("third")
    assert _news(engine) == (1, 1), "the model never learned of the change"


# --- the setup reads each switch as the plugin does ---------------------------------------------------------------

READ_VALUES = [1, 0, None, "maybe", "true", "false", True, False, "", " Off ", 0.0, 2, "yes"]


@pytest.mark.parametrize("written", READ_VALUES, ids=repr)
def test_the_setup_reads_each_switch_as_the_plugin_does(ctrl_module, monkeypatch, written):
    """Each kind of switch of the setup, run on the same value as the reader the plugin uses for it: the sections
    (section_enabled), AGENT (agent_enabled), the others (_get_option_bool)."""
    from core.agent import setup_wizard as wizard
    from ui.layout.dock_chrome import section_enabled
    for name in (".core.optimization", ".core.optimization.config_provider"):
        _module(monkeypatch, name, get_optimization_thresholds=MagicMock())
    _module(monkeypatch, ".config")
    config = _load(monkeypatch, "config.config", "config/config.py")

    def config_of(path, value):
        _app, _options, section, key = path.split(".")
        return {"APP": {"OPTIONS": {section: {key: {"value": value}}}}}

    for path in (wizard.FILTERING_ON, wizard.EXPORTING_ON):
        assert wizard.read_switch(path, written) is section_enabled(config_of(path, written), path.split(".")[2].lower()), path
    assert wizard.read_switch(wizard.AGENT_ON, written) is ctrl_module.agent_enabled(config_of(wizard.AGENT_ON, written))
    # Not in config.json at all: the readers' default (section_enabled, agent_enabled, _get_option_bool)
    assert wizard.read_switch(wizard.AGENT_ON) is ctrl_module.agent_enabled({}) is True
    assert wizard.read_switch(wizard.FILTERING_ON) is section_enabled({}, "filtering") is True
    for path in sorted(wizard.SWITCHES - wizard.SECTION_READ - {wizard.AGENT_ON}):
        default = path not in wizard._UNSET_OFF
        assert wizard.read_switch(path, written) is config._get_option_bool(written, default), path
        assert wizard.read_switch(path, None) is default, path


class TestRangeReadings:
    """The field of a range widget: read once for a state of its layer, not out of view, its numbers read wide open
    kept for the bars outside its bounds."""

    @pytest.fixture
    def setup(self, controller):
        stub = sys.modules[f"{_PKG}.adapters.agent.agent_widgets"]
        model = sys.modules[f"{_PKG}.core.agent.widgets"]
        state = types.SimpleNamespace(widget=model.make([], "range", "L1", "communes", "", field="pop", minimum=0,
                                                        maximum=10), subset="", values=[1, 2, 9, None], reads=0)
        layer = types.SimpleNamespace(id=lambda: "L1", subsetString=lambda: state.subset)

        def reading(widget):
            state.reads += 1
            return model.read_range(state.values, widget["minimum"], widget["maximum"])
        stub.read_widgets = lambda project=None: [state.widget]
        stub.widget_layer = lambda widget: layer
        stub.opened_filter = lambda widgets, widget: ""
        stub.range_reading = reading
        controller.panel.isVisible.return_value = True
        return state, model

    @staticmethod
    def shown(controller):
        return controller.panel.widgets_strip.set_bars.call_args[0][1]

    def test_read_once_until_the_layer_changes_and_not_while_out_of_view(self, controller, setup):
        state, _model = setup
        controller._refresh_widgets()
        assert state.reads == 0  # at the next turn of the stat timer, not at once
        controller._refresh_stats()
        controller._refresh_stats()
        assert state.reads == 1
        controller._on_layer_changed("L1")  # a feature edited
        controller._refresh_stats()
        assert state.reads == 2
        controller.panel.isVisible.return_value = False
        controller._on_layer_changed("L1")
        controller._refresh_stats()
        assert state.reads == 2 and controller._stats_waiting
        controller.panel.isVisible.return_value = True
        controller._stat_timer.start.reset_mock()
        controller._on_panel_shown()
        controller._stat_timer.start.assert_called()
        controller._refresh_stats()
        assert state.reads == 3

    def test_narrowed_the_bars_read_wide_open_stay_until_a_feature_changes(self, controller, setup):
        state, model = setup
        controller._refresh_stats()
        opened = self.shown(controller)
        assert sum(opened["counts"]) == 3 and opened["empty"] == 1 and opened["unknown"] == []
        state.widget = dict(state.widget, low=5.0)  # narrowed: the layer filtered by it
        state.subset, state.values = '"pop" >= 5.0', [9]
        controller._refresh_stats()
        assert self.shown(controller) == opened
        controller._on_layer_changed("L1")  # an edit: what was read wide open is forgotten
        controller._refresh_stats()
        now = self.shown(controller)
        assert sum(now["counts"]) == 1 and now["unknown"] == model.unknown_bins(state.widget)
        assert "w1" not in controller._opened
