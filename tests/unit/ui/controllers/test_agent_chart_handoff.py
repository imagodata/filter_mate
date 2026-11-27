import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from .test_agent_chat_lifecycle import _PKG, _module, controller, ctrl_module, dock

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("webengine,expert", [(False, False), (False, True), (True, False), (True, True)])
def test_standard_charts_remain_available_without_webengine(ctrl_module, controller, monkeypatch, webengine, expert):
    monkeypatch.setattr(controller, "_accessor", lambda: SimpleNamespace(configured_domains=lambda: {}))
    monkeypatch.setattr(ctrl_module, "qgis_databases", lambda: ())
    monkeypatch.setattr(ctrl_module, "_holds_web_service_layers", lambda: False)
    _module(monkeypatch, ".adapters.agent.chart_renderer", available=lambda: webengine)
    gui_names = ("open_layout", "preview_atlas", "flash_features", "set_active_layer", "show_message")
    gui_handlers = {name: MagicMock(name=name) for name in gui_names}
    _module(monkeypatch, ".adapters.public_api.gui_control", chat_handlers=lambda: gui_handlers)
    catalogue = ctrl_module.chat_tools
    tool_spec = sys.modules[f"{_PKG}.core.agent.tool_catalog"].ToolSpec

    def with_gui_tools():
        tools = list(catalogue())
        names = {tool.name for tool in tools}
        return tools + [tool_spec(name, "GUI action", {"type": "object"}) for name in gui_names if name not in names]

    monkeypatch.setattr(ctrl_module, "chat_tools", with_gui_tools)
    values = SimpleNamespace(**vars(ctrl_module.load_settings()))
    values.expert_python = expert
    tools, handlers, _connectors = controller.tools_and_handlers(values)
    names = {tool.name for tool in tools}
    assert {"show_chart", "export_chart", "add_chart_to_layout"} <= names
    assert set(gui_names) <= names
    assert {'qgis_capabilities', 'control_qgis'} <= names
    assert {'qgis_capabilities', 'control_qgis'} <= handlers.keys()
    assert all(handlers[name] is gui_handlers[name] for name in gui_names)
    assert ("run_chart_code" in names) == (webengine and expert)
    assert {"show_infographic", "export_infographic"} <= handlers.keys()
    assert handlers['control_qgis']({'action': 'properties', 'layer': 'communes'}) == {'requested': True}


@pytest.mark.parametrize("kind", ["chart", "infographic"])
@pytest.mark.parametrize("destination", ["", "/tmp/chosen"])
def test_pdf_dialog_routes_the_correct_id_and_cancel_writes_nothing(
        ctrl_module, controller, monkeypatch, kind, destination):
    controller._charts = MagicMock()
    dialogs = []

    def choose(*args):
        dialogs.append(args)
        return destination, ""

    qtwidgets = sys.modules["qgis.PyQt.QtWidgets"]
    monkeypatch.setattr(qtwidgets, "QFileDialog", SimpleNamespace(getSaveFileName=choose))
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsSettings", lambda: SimpleNamespace(
        value=lambda *args, **kwargs: "/tmp", setValue=lambda *args: None))
    monkeypatch.setattr(ctrl_module, "file_stem", lambda title: "graph")
    getattr(controller._charts, kind).return_value = SimpleNamespace(request=SimpleNamespace(title="graph"))
    save = controller._charts.save_as if kind == "chart" else controller._charts.save_infographic_as
    getattr(controller, "_save_" + kind)("c7", "pdf")
    assert dialogs[0][-1] == "PDF document (*.pdf)"
    if destination:
        save.assert_called_once_with("c7", destination + ".pdf")
    else:
        save.assert_not_called()
    controller._charts.run_chart_code.assert_not_called()


def test_infographic_card_has_no_layout_action_and_saves_its_own_id(ctrl_module, controller, monkeypatch):
    messages = sys.modules[f"{_PKG}.core.agent.messages"]
    controller._charts.pending_infographic = SimpleNamespace(
        request=SimpleNamespace(title="Overview", caption="", source="project", chart_ids=("c1", "c2")),
        infographic_id="i7", svg="<svg/>")
    saved = []
    monkeypatch.setattr(controller, "_save_infographic", lambda ident, extension: saved.append((ident, extension)))
    controller._show_infographic_card(messages.ToolCallPart("call", "show_infographic", {}),
                                      messages.ToolResultPart("call", "{}"))
    assert controller._charts.pending_infographic is None
    assert controller.panel.add_chart.call_args.kwargs["on_layout"] is None
    controller.panel.add_chart.call_args.kwargs["on_save"]("pdf")
    assert saved == [("i7", "pdf")]
