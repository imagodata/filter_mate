from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from .test_agent_chat_lifecycle import FakeQgsProject, _load, _module, ctrl_module

pytestmark = pytest.mark.unit


@pytest.fixture
def data_ui(ctrl_module, monkeypatch):
    store = _module(monkeypatch, ".adapters.agent.data_store", pending_layers=lambda project: [])
    _module(monkeypatch, ".adapters.agent.save_location",
            suggested_project_path=MagicMock(return_value="/chosen/Rivers.qgz"), remember_project_folder=MagicMock())
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
    module, ui, host, store = data_ui
    ui.project.fileName = lambda: "/chosen/map.qgz"
    import sys
    widgets = sys.modules["qgis.PyQt.QtWidgets"]
    dialog = SimpleNamespace(getSaveFileName=MagicMock(return_value=("", "")))
    monkeypatch.setattr(widgets, "QFileDialog", dialog)
    assert ui.save() is False
    dialog.getSaveFileName.assert_called_once()
    assert dialog.getSaveFileName.call_args.args[2] == "/chosen/Rivers.qgz"
    store.persist.assert_not_called()
    module.remember_project_folder.assert_not_called()


def test_save_offer_shows_the_project_and_shared_layer_folder(data_ui):
    _, ui, host, store = data_ui
    store.pending_layers = lambda project: [SimpleNamespace(id=lambda: "r", source=lambda: "vsi", name=lambda: "Rivers")]
    ui.offer()
    text = host.panel.add_confirm_card.call_args.args[1]
    assert "Suggested project: /chosen/Rivers.qgz" in text
    assert "Project and layers folder: /chosen" in text


@pytest.mark.parametrize("failure", [False, True])
def test_only_a_successful_save_remembers_the_shared_folder(data_ui, monkeypatch, failure):
    import sys
    module, ui, host, store = data_ui
    dialog = SimpleNamespace(getSaveFileName=MagicMock(return_value=("/chosen/Analysis", "")))
    monkeypatch.setattr(sys.modules["qgis.PyQt.QtWidgets"], "QFileDialog", dialog)
    store.persist.return_value = "/chosen"
    if failure:
        store.persist.side_effect = OSError("disk full")
    assert ui.save() is not failure
    store.persist.assert_called_once_with(ui.project, "/chosen/Analysis.qgz")
    if failure:
        module.remember_project_folder.assert_not_called()
    else:
        module.remember_project_folder.assert_called_once_with("/chosen/Analysis.qgz")


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
