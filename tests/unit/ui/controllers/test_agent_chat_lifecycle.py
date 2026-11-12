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
        self.layers = {}

    def mapLayers(self):
        return dict(self.layers)

    def mapLayer(self, layer_id):
        return self.layers.get(layer_id)


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

    def __init__(self):
        self.label, self.describe = "", None
        self.open, self.committed, self.discarded = False, 0, 0

    def begin(self, call=None):
        self.open = True

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
    busy = staticmethod(lambda: "")


class FakeBridge:
    def __init__(self, host, parent):
        self.listening, self.busy, self.error = False, False, ""
        self.close_error = None
        self.closed = 0

    def sync(self):
        pass

    def close(self):
        self.closed += 1
        if self.close_error is not None:
            raise self.close_error


SETTINGS = types.SimpleNamespace(autonomy="standard", rules={}, preset="anthropic", model="m", ready=True,
                                 has_consent=True, send_values=True, expert_python=False, custom_sources="[]",
                                 enabled_sources=[])


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
    _module(monkeypatch, ".adapters.agent.free_quota", FreeQuotaError=type("FreeQuotaError", (Exception,), {}))
    store = _module(monkeypatch, ".adapters.agent.transcript_store", project_key=lambda: "key", load=lambda key: [])
    store.saved = []
    store.save = lambda key, transcript: store.saved.append((key, list(transcript)))
    _module(monkeypatch, ".adapters.agent.project_notes_store", read_notes=lambda project=None: [])
    recipes = _module(monkeypatch, ".adapters.agent.recipes_store", recipes=[])
    recipes.read_recipes = lambda project=None: list(recipes.recipes)
    _module(monkeypatch, ".adapters.agent.turn_checkpoint", TurnCheckpoint=FakeCheckpoint)
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
    _module(monkeypatch, ".filtermate_api.config")
    _module(monkeypatch, ".filtermate_api.qgis_accessor")
    _module(monkeypatch, ".ui.controllers.agent_mcp_bridge", AgentMcpBridge=FakeBridge)
    _module(monkeypatch, ".ui.widgets.agent_panel", ANSWER_CONVERSATION="conversation", ANSWER_NO="no",
            ANSWER_ONCE="once", AgentPanel=lambda parent: MagicMock(), level_short=str, preset_label=str)
    _module(monkeypatch, ".ui.widgets.agent_widgets_strip", number_text=str)
    bounded_http = _load(monkeypatch, "adapters.agent.bounded_http", "adapters/agent/bounded_http.py")
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


# --- 4: a conversation is let go of only once really over -----------------------------------------------------


def test_settings_wait_for_the_end_of_the_turn(ctrl_module, controller, monkeypatch):
    dialogs = []
    monkeypatch.setattr(ctrl_module, "AgentSettingsDialog", lambda *args, **kwargs: dialogs.append(args))
    engine, _transport = _engine(ctrl_module, controller, lambda arguments: {})
    controller._on_send("go")
    assert controller.open_settings() is False  # the link of an earlier error card, clicked during the turn
    assert dialogs == [] and controller._engine is engine and engine.busy


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

    monkeypatch.setattr(controller, "tools_and_handlers", lambda values: ([write], {"write": tool}, []))
    ctrl_module._test_recipes.recipes = [{"id": "r1", "name": "R", "request": "", "steps": [
        {"tool": "write", "arguments": {"n": 1}, "label": "one"}, {"tool": "write", "arguments": {"n": 2}, "label": "two"}]}]
    controller.panel.reset_mock()
    assert controller.run_recipe("r1") is False
    assert ran == [1]  # stopped before its next step
    assert controller._checkpoint.committed == 0
    controller.panel.add_note.assert_not_called()  # its end is not written in the thread of the next project
    assert not controller.chat_busy()


def test_closing_the_dock_stops_a_recipe(ctrl_module, controller, monkeypatch):
    catalog = sys.modules[f"{_PKG}.core.agent.tool_catalog"]
    write = catalog.ToolSpec("write", "Change something here.", {"type": "object", "properties": {}})
    ran = []

    def tool(arguments):
        ran.append(arguments["n"])
        controller.stop()  # the dock closes during the first step
        return {"ok": True}

    monkeypatch.setattr(controller, "tools_and_handlers", lambda values: ([write], {"write": tool}, []))
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
    _module(monkeypatch, ".adapters.qgis.source_capability_probe",
            feature_count_or_none=lambda layer: None if layer.remote else layer.featureCount())
    rows = controller._layer_rows()
    assert wfs.counted == 0  # featureCount() of a web service can be a request to its server
    assert [(row["name"], row["feature_count"], row["active_filter_expression"], row["group"], row["visible"])
            for row in rows] == [("LOCAL", 12, "a > 1", "", True), ("WFS", -1, "", "Base", False)]


# --- 9: a controller half built, a shutdown that goes on -------------------------------------------------------


def test_a_controller_whose_page_failed_does_not_follow_the_project(ctrl_module, dock):
    def add_page(page):
        raise RuntimeError("no accordion")

    with pytest.raises(RuntimeError):
        ctrl_module.AgentChatController(add_page, MagicMock(), dock, ask_user=lambda title, text: True)
    project = FakeQgsProject.project
    assert not (project.cleared.slots or project.readProject.slots or project.fileNameChanged.slots)


def test_shutdown_goes_on_when_a_step_fails(ctrl_module, controller):
    project, stopped = FakeQgsProject.project, []
    forget = ctrl_module._test_bounded_http.on_abort(lambda: stopped.append("mcp client"))
    controller._mcp.close_error = RuntimeError("wrapped C/C++ object has been deleted")
    controller.shutdown()
    assert stopped == ["mcp client"]  # unloading, nothing may arrive afterwards
    assert controller._mcp.closed == 1
    assert not (project.cleared.slots or project.readProject.slots or project.fileNameChanged.slots)
    forget()
