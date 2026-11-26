from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from .test_agent_chat_lifecycle import FakeQgsProject, _load, _module, ctrl_module

pytestmark = pytest.mark.unit


@pytest.fixture
def data_ui(ctrl_module, monkeypatch):
    store = _module(monkeypatch, ".adapters.agent.data_store", pending_layers=lambda project: [])
    module = _load(monkeypatch, "ui.controllers.agent_data", "ui/controllers/agent_data.py")
    host = SimpleNamespace(panel=MagicMock(), chat_busy=lambda: False)
    ui = module.AgentDataController(host)
    return module, ui, host, store


def test_memory_choice_does_not_write_or_open_a_location_dialog(data_ui, monkeypatch):
    module, ui, host, store = data_ui
    layer = SimpleNamespace(id=lambda: "l1", source=lambda: "/vsimem/layer", name=lambda: "Rivers")
    store.pending_layers = lambda project: [layer]
    save = MagicMock()
    monkeypatch.setattr(ui, "save", save)
    ui.offer()
    ui.offer()
    host.panel.add_confirm_card.assert_called_once()
    callback = host.panel.add_confirm_card.return_value.answered.connect.call_args.args[0]
    callback("no")
    save.assert_not_called()
    callback("once")
    save.assert_called_once()


def test_an_old_card_cannot_save_a_different_project(data_ui, monkeypatch):
    _, ui, host, store = data_ui
    store.pending_layers = lambda project: [SimpleNamespace(id=lambda: "l1", source=lambda: "vsi", name=lambda: "Rivers")]
    save = MagicMock()
    monkeypatch.setattr(ui, "save", save)
    ui.offer()
    callback = host.panel.add_confirm_card.return_value.answered.connect.call_args.args[0]
    FakeQgsProject.project.cleared.emit()
    callback("once")
    save.assert_not_called()


def test_cancelled_destination_keeps_everything_in_memory(data_ui, monkeypatch):
    _, ui, host, store = data_ui
    ui.project.fileName = lambda: "/chosen/map.qgz"
    import sys
    widgets = sys.modules["qgis.PyQt.QtWidgets"]
    dialog = SimpleNamespace(getSaveFileName=MagicMock(return_value=("", "")))
    monkeypatch.setattr(widgets, "QFileDialog", dialog)
    assert ui.save() is False
    dialog.getSaveFileName.assert_called_once()
    store.persist.assert_not_called()


def test_saving_while_a_tool_runs_does_not_open_a_dialog_or_change_providers(data_ui):
    _, ui, host, store = data_ui
    host.chat_busy = lambda: True
    assert ui.save() is False
    store.persist.assert_not_called()
    host.panel.set_status.assert_called_once()


def test_saving_waits_for_a_filter_job_or_external_tool(data_ui):
    _, ui, host, store = data_ui
    host._checkpoint = SimpleNamespace(busy=lambda: 'a filter is running')
    assert ui.save() is False
    host._checkpoint = SimpleNamespace(busy=lambda: '')
    host._mcp = SimpleNamespace(busy=True)
    assert ui.save() is False
    store.persist.assert_not_called()


def test_unloading_the_panel_leaves_project_data_alive(data_ui):
    _, ui, _, store = data_ui
    ui.close()
    store.close.assert_not_called()
    assert not ui._connections
