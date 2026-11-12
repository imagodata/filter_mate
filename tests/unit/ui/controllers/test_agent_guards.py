# -*- coding: utf-8 -*-
"""What the agent checks before a call changes the project, outside the pure policy (core/agent/permissions.py).

The modules are loaded for real under a synthetic package (their relative imports reach ``core`` and ``adapters``);
QGIS stays mocked by the root conftest, with the two Qt modules it does not mock.
"""
import importlib
import pathlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from core.agent.messages import ToolCallPart
from core.agent.permissions import PROTECTION_UNREADABLE, PermissionPolicy

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_agent_guards_test"


def _load():
    for name, path in (("", _ROOT), (".ui", _ROOT / "ui"), (".ui.controllers", _ROOT / "ui" / "controllers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    stubs = [name for name in ("qgis.PyQt.QtNetwork", "qgis.PyQt.QtXml") if name not in sys.modules]
    sys.modules.update({name: MagicMock() for name in stubs})
    try:  # bound at import; taken out again so that no other test sees them
        return (importlib.import_module(f"{_PKG}.adapters.agent.protected_layers"),
                importlib.import_module(f"{_PKG}.ui.controllers.agent_chat_controller"),
                importlib.import_module(f"{_PKG}.ui.controllers.agent_mcp_bridge"),
                importlib.import_module(f"{_PKG}.adapters.public_api.layer_tree"))
    finally:
        for name in stubs:
            sys.modules.pop(name, None)


protected_layers, chat_controller, mcp_bridge, layer_tree = _load()


def _layer(layer_id, style="default"):
    return SimpleNamespace(id=lambda: layer_id, styleManager=lambda: SimpleNamespace(currentStyle=lambda: style))


def _record(layer, style=None, checked=None):
    """A layer of a map theme: its current style when it has several, its checked legend items when some are not."""
    return SimpleNamespace(layer=lambda: layer, usingCurrentStyle=style is not None, currentStyle=style or "",
                           usingLegendItems=checked is not None, checkedLegendItems=set(checked or ()))


class TestJoins:
    def test_the_layers_that_join_a_layer_by_its_id_or_any_layer_of_its_name(self, monkeypatch):
        def vector(layer_id, name, joined=()):
            joins = [SimpleNamespace(joinLayerId=lambda target=target: target) for target in joined]
            return SimpleNamespace(id=lambda: layer_id, name=lambda: name, vectorJoins=lambda: joins)
        owners, owners_bis = vector("owners_1", "owners"), vector("owners_2", "owners")
        cadastre, routes = vector("cadastre_id", "cadastre", ["owners_2"]), vector("routes_id", "routes", ["x"])
        mnt = SimpleNamespace(id=lambda: "mnt_id", name=lambda: "mnt")  # a raster: no joins
        layers = {item.id(): item for item in (owners, owners_bis, cadastre, routes, mnt)}
        project = SimpleNamespace(
            readEntry=lambda scope, key, default: ('["cadastre_id"]', True), mapLayer=layers.get,
            mapLayersByName=lambda name: [item for item in layers.values() if item.name() == name],
            mapLayers=lambda: layers)
        monkeypatch.setattr(protected_layers, "QgsProject", SimpleNamespace(instance=lambda: project))
        protection = protected_layers.ProjectProtection()
        assert protection.layers_joining(["owners"]) == ["cadastre_id"]
        assert protection.layers_joining(["owners_2"]) == ["cadastre_id"]
        assert protection.layers_joining(["owners_1", "mnt"]) == []
        assert "'cadastre'" in PermissionPolicy(protector=protection).protection_refusal(
            "remove_layers", {"layers": ["owners_2"]})


class TestMapThemes:
    @pytest.fixture
    def themes(self, monkeypatch):
        """``now``: the layers shown and their state; ``theme``: the records of the theme "Vue"."""
        state = {"now": [], "theme": []}
        collection = SimpleNamespace(hasMapTheme=lambda name: name == "Vue",
                                     mapThemeState=lambda name: SimpleNamespace(layerRecords=lambda: state["theme"]))
        core = sys.modules["qgis.core"]
        monkeypatch.setattr(core, "QgsProject", SimpleNamespace(
            instance=lambda: SimpleNamespace(mapThemeCollection=lambda: collection)), raising=False)
        monkeypatch.setattr(core, "QgsMapThemeCollection", SimpleNamespace(
            createThemeFromCurrentState=lambda root, model: SimpleNamespace(layerRecords=lambda: state["now"])),
            raising=False)
        monkeypatch.setattr(layer_tree, "_model", lambda: (None, None))
        monkeypatch.setattr(layer_tree, "_root", lambda: None)
        return state

    def test_the_layers_whose_style_or_legend_the_theme_would_change(self, themes):
        same, styled, legend, hidden = (_layer("same"), _layer("styled", "default"), _layer("legend"),
                                        _layer("hidden"))
        themes["now"] = [_record(same), _record(styled, "default"), _record(legend)]
        themes["theme"] = [_record(same), _record(styled, "night"), _record(legend, checked={"0"}), _record(hidden)]
        # hidden now: its legend items are not recorded, so it counts
        assert layer_tree.theme_changed_layers(" Vue ") == ["styled", "legend", "hidden"]

    def test_same_style_and_legend_change_nothing_and_an_unknown_theme_nothing(self, themes):
        layer = _layer("a", "night")
        themes["now"] = [_record(layer, "night", checked={"1", "2"})]
        themes["theme"] = [_record(layer, "night", checked={"2", "1"})]
        assert layer_tree.theme_changed_layers("Vue") == []
        assert layer_tree.theme_changed_layers("Ailleurs") == []

    def test_the_protection_reads_the_theme_only_when_something_is_protected(self, monkeypatch):
        fake = types.ModuleType("layer_tree")
        fake.theme_changed_layers = lambda name: ["cadastre_id"] if name == "Vue" else []
        monkeypatch.setitem(sys.modules, f"{_PKG}.adapters.public_api.layer_tree", fake)
        monkeypatch.setattr(protected_layers, "read_ids", lambda project=None, strict=False: ["cadastre_id"])
        assert protected_layers.ProjectProtection().theme_layers("Vue") == ["cadastre_id"]
        monkeypatch.setattr(protected_layers, "read_ids", lambda project=None, strict=False: [])
        assert protected_layers.ProjectProtection().theme_layers("Vue") == []


class TestProtectionFailsClosed:
    def test_favorites_that_cannot_be_read_are_not_taken_for_none(self, monkeypatch):
        monkeypatch.setattr(protected_layers, "read_ids", lambda project=None, strict=False: ["cadastre_id"])
        offline = types.ModuleType("operations")

        def favorite_layers(_favorite_id):
            raise RuntimeError("favorites store offline")
        offline.favorite_layers = favorite_layers
        monkeypatch.setitem(sys.modules, f"{_PKG}.adapters.public_api.operations", offline)
        protection = protected_layers.ProjectProtection()
        with pytest.raises(RuntimeError):
            protection.favorite_layers("fav-1")
        policy = PermissionPolicy(protector=protection)
        assert policy.protection_refusal("apply_favorite", {"favorite_id": "fav-1"}) == PROTECTION_UNREADABLE

    @pytest.mark.parametrize("stored", ['["cadastre_id"', '{"cadastre_id": 1}', '"cadastre_id"', '["a", 3]'])
    def test_an_entry_that_cannot_be_read_refuses_a_change(self, monkeypatch, stored):
        project = SimpleNamespace(readEntry=lambda scope, key, default: (stored, True), mapLayer=lambda reference: None,
                                  mapLayersByName=lambda reference: [])
        monkeypatch.setattr(protected_layers, "QgsProject", SimpleNamespace(instance=lambda: project))
        protection = protected_layers.ProjectProtection()
        with pytest.raises(ValueError):
            protection.name_of("cadastre")
        assert PermissionPolicy(protector=protection).protection_refusal("remove_layers", {"layers": ["routes"]}) \
            == PROTECTION_UNREADABLE
        assert isinstance(protected_layers.read_ids(project), list)  # the settings still open, with what reads

    def test_writing_again_mends_an_entry_that_cannot_be_read(self):
        writes = []
        project = SimpleNamespace(readEntry=lambda scope, key, default: ('["cadastre_id"', True),
                                  writeEntry=lambda scope, key, value: writes.append(("write", value)),
                                  removeEntry=lambda scope, key: writes.append(("remove",)))
        protected_layers.write_ids([], project)
        assert writes == [("remove",)]  # nothing ticked: the broken entry goes
        protected_layers.write_ids(["routes_id"], project)
        assert writes[-1] == ("write", '["routes_id"]')

    def test_nothing_protected_does_not_read_the_favorites(self, monkeypatch):
        monkeypatch.setattr(protected_layers, "read_ids", lambda project=None, strict=False: [])
        assert protected_layers.ProjectProtection().favorite_layers("fav-1") == []

    def test_the_controller_refuses_a_change_it_cannot_check_and_lets_a_read_run(self):
        class Broken:
            def turned_off(self, name):
                raise RuntimeError("the project is closing")

        host = SimpleNamespace(_policy=Broken())
        refusal = chat_controller.AgentChatController.protection_refusal
        assert refusal(host, ToolCallPart("c", "apply_filter", {"layer_name": "a", "expression": "1"})) \
            == PROTECTION_UNREADABLE
        assert refusal(host, ToolCallPart("c", "apply_favorite", {"favorite_id": "f"})) == PROTECTION_UNREADABLE
        assert refusal(host, ToolCallPart("c", "list_layers", {})) == ""


class _Host:
    """What the bridge asks of the chat: nothing protected, nothing turned off there, the user answers ``answer``."""

    def __init__(self, answer):
        self.answer = answer
        self.asked = []

    def chat_busy(self):
        return False

    def protection_refusal(self, call):
        return ""

    def confirm_external(self, call, client):
        self.asked.append(call.name)
        return self.answer

    def journal(self, call, result, client):
        pass


class TestMcpBridgeFollowsTheToolsTab:
    @pytest.fixture
    def bridge(self, monkeypatch):
        from core.agent.tool_catalog import chat_tools
        from core.agent.tool_executor import ToolExecutor

        def make(rules, answer=False):
            ran = []
            tools = {tool.name: tool for tool in chat_tools()}
            handlers = {name: (lambda arguments, name=name: ran.append(name) or {}) for name in tools}
            bridge = object.__new__(mcp_bridge.AgentMcpBridge)  # no server: _run alone
            bridge._host, bridge._declined, bridge.busy = _Host(answer), {}, False
            bridge._executor = ToolExecutor(tuple(tools.values()), handlers)
            bridge._server = SimpleNamespace(client_still_there=lambda: True)
            bridge._change = lambda call, client: bridge._executor.execute(call)  # no undo point here
            monkeypatch.setattr(mcp_bridge, "load_settings", lambda: SimpleNamespace(rules=dict(rules)))
            monkeypatch.setattr(mcp_bridge, "QApplication", SimpleNamespace(activeModalWidget=lambda: None))
            return bridge, tools, ran
        return make

    def test_always_ask_asks_even_for_what_the_standard_level_runs(self, bridge):
        server, tools, ran = bridge({"list_layers": "ask", "apply_filter": "ask"})
        for name, arguments in (("list_layers", {}), ("apply_filter", {"layer_name": "a", "expression": '"x" = 1'})):
            result = server._run(tools[name], arguments, "Claude")
            assert result.is_error and name in server._host.asked, name
        assert ran == []

    def test_never_refuses_without_asking(self, bridge):
        server, tools, ran = bridge({"zoom_to": "never"})
        result = server._run(tools["zoom_to"], {"layer": "a"}, "Claude")
        assert result.is_error and "turned the tool 'zoom_to' off" in result.content
        assert server._host.asked == [] and ran == []

    def test_always_allow_does_not_take_a_confirmation_away_from_another_application(self, bridge):
        server, tools, ran = bridge({"remove_layers": "allow"})
        result = server._run(tools["remove_layers"], {"layers": ["a"]}, "Claude")
        assert result.is_error and server._host.asked == ["remove_layers"] and ran == []

    def test_no_question_while_the_chat_works_or_a_dialog_is_open_even_for_a_read(self, bridge, monkeypatch):
        server, tools, ran = bridge({"list_layers": "ask"}, answer=True)
        server._host.chat_busy = lambda: True
        assert server._run(tools["list_layers"], {}, "Claude").content == mcp_bridge.CHAT_IS_WORKING
        server._host.chat_busy = lambda: False
        monkeypatch.setattr(mcp_bridge, "QApplication", SimpleNamespace(activeModalWidget=lambda: object()))
        assert server._run(tools["list_layers"], {}, "Claude").content == mcp_bridge.DIALOG_OPEN
        assert server._host.asked == [] and ran == []
        server._host.chat_busy = lambda: True  # a read nobody is asked about still runs
        assert not server._run(tools["describe_layer"], {"layer": "a"}, "Claude").is_error

    def test_without_rules_the_standard_level_stays(self, bridge):
        server, tools, ran = bridge({}, answer=True)
        assert not server._run(tools["list_layers"], {}, "Claude").is_error
        assert not server._run(tools["remove_layers"], {"layers": ["a"]}, "Claude").is_error
        assert server._host.asked == ["remove_layers"] and ran == ["list_layers", "remove_layers"]


def _snapshot(layer_id):
    return SimpleNamespace(layer_id=layer_id, kind="vector", same_state=lambda other: True)


class TestTheAgentUndoLeavesProtectedLayersAlone:
    """undo_agent_step puts back what changed during the turn: a layer protected since, or changed by the user meanwhile
    and protected, is left as it is."""

    def test_the_filters_of_a_kept_layer_are_not_restored(self, monkeypatch):
        checkpoint = sys.modules[f"{_PKG}.adapters.agent.turn_checkpoint"]
        operation = SimpleNamespace(changes=((_snapshot("cadastre_id"), _snapshot("cadastre_id")),
                                             (_snapshot("routes_id"), _snapshot("routes_id"))), effects=("e",))
        restored, effects = [], []

        def restore(pairs, use_before, project):
            restored.extend(before.layer_id for before, _after in pairs)
            return list(restored)

        history = SimpleNamespace(undo=lambda key: operation, redo=lambda key: None)
        service = SimpleNamespace(history=history, last_skipped=[], _restore=restore)
        names = {"cadastre_id": "cadastre", "routes_id": "routes"}
        project = SimpleNamespace(mapLayer=lambda layer_id: SimpleNamespace(name=lambda: names[layer_id]))
        monkeypatch.setattr(checkpoint, "_api_service", lambda: service)
        monkeypatch.setattr(checkpoint, "QgsProject", SimpleNamespace(instance=lambda: project))
        monkeypatch.setattr(checkpoint, "take_snapshot", lambda layer, kind: _snapshot("x"))

        def apply_effects(items, undo, keep=frozenset()):
            effects.append(keep)
            return [], []
        monkeypatch.setattr(checkpoint, "apply_effects", apply_effects)
        done, left = checkpoint.TurnCheckpoint().undo(keep=frozenset({"cadastre_id"}))
        assert restored == ["routes_id"] and done == ["routes"] and left == ["cadastre"]
        assert effects == [frozenset({"cadastre_id"})]

    def test_the_style_or_the_addition_of_a_kept_layer_is_not_undone(self, monkeypatch):
        effects_module = sys.modules[f"{_PKG}.adapters.agent.turn_effects"]
        touched = []
        project = SimpleNamespace(mapLayer=lambda layer_id: None, removeMapLayer=touched.append)
        monkeypatch.setattr(effects_module, "QgsProject", SimpleNamespace(instance=lambda: project))
        done, left = effects_module.apply_effects(
            (("added", "cadastre_id", "<qlr/>", ([], 0), "cadastre"),
             ("style", "cadastre_id", "<a/>", "<b/>", "cadastre")), undo=True, keep=frozenset({"cadastre_id"}))
        assert (done, left, touched) == ([], ["cadastre", "cadastre"], [])
