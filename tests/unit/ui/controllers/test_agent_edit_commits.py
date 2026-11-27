"""Durable source writes require a fresh click on the exact pending layer/group."""
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from .test_agent_chat_lifecycle import FakeSignal, _load, _module, ctrl_module  # noqa: F401

pytestmark = pytest.mark.unit


class Layer:
    def __init__(self, name):
        self.key, self.index, self.count = name, 1, 1
        self.editable, self.modified = True, True
        self.layerModified, self.editingStopped = FakeSignal(), FakeSignal()
        self.dataSourceChanged, self.willBeDeleted = FakeSignal(), FakeSignal()

    def id(self):
        return self.key

    def name(self):
        return self.key

    def source(self):
        return '/data/' + self.key

    def providerType(self):
        return 'ogr'

    def isEditable(self):
        return self.editable

    def isModified(self):
        return self.modified

    def undoStack(self):
        return SimpleNamespace(index=lambda: self.index, count=lambda: self.count)


@pytest.fixture
def commits(ctrl_module, monkeypatch):
    import sys
    modes = SimpleNamespace(Disabled=0, AutomaticGroups=1, BufferedGroups=2)
    monkeypatch.setattr(sys.modules['qgis.core'], 'Qgis', SimpleNamespace(TransactionMode=modes), raising=False)
    protection = _module(monkeypatch, '.adapters.agent.protected_layers', read_ids=MagicMock(return_value=[]))
    _module(monkeypatch, '.ui.cursors', CursorLease=lambda *args: nullcontext())
    module = _load(monkeypatch, 'ui.controllers.agent_edit_commits', 'ui/controllers/agent_edit_commits.py')
    layer, other = Layer('roads'), Layer('manual')
    layers = {item.id(): item for item in (layer, other)}
    project = SimpleNamespace(mapLayer=layers.get, transactionMode=lambda: modes.Disabled,
                              commitChanges=MagicMock(return_value=(True, [])))
    cards = []
    def card(*args):
        result = MagicMock()
        result.answered, result.destroyed = FakeSignal(), FakeSignal()
        cards.append(result)
        return result
    host = SimpleNamespace(panel=MagicMock(), _memory_generation=0, _refresh_history=MagicMock())
    host.panel.add_confirm_card.side_effect = card
    busy = MagicMock(return_value=False)
    ui = module.LayerEditCommits(host, project, busy)
    return SimpleNamespace(module=module, ui=ui, project=project, host=host, busy=busy,
                           layer=layer, other=other, cards=cards, modes=modes, protection=protection)


def test_an_edit_requires_a_distinct_click_and_no_conversation_permission(commits):
    c = commits
    c.ui.offer([('roads', 1)])
    c.project.commitChanges.assert_not_called()
    texts, body, repeated = c.host.panel.add_confirm_card.call_args.args
    assert repeated is False and 'manual edits' in body
    assert 'no longer' in texts['reversibility']
    c.cards[0].answered.emit('once')
    c.project.commitChanges.assert_called_once_with(True, c.layer)
    c.cards[0].answered.emit('once')
    c.project.commitChanges.assert_called_once()
    c.host._refresh_history.assert_called_once()
    assert not c.ui._tickets and not c.layer.layerModified.slots


@pytest.mark.parametrize('answer', ['no', 'conversation'])
def test_refusal_or_an_always_answer_never_commits_or_discards(commits, answer):
    c = commits
    c.ui.offer([('roads', 1)])
    c.cards[0].answered.emit(answer)
    c.project.commitChanges.assert_not_called()
    assert c.layer.isEditable() and c.layer.isModified()


@pytest.mark.parametrize('event', ['layerModified', 'editingStopped', 'dataSourceChanged', 'willBeDeleted'])
def test_new_edits_or_manual_save_or_deletion_cancel_the_old_confirmation(commits, event):
    c = commits
    c.ui.offer([('roads', 1)])
    getattr(c.layer, event).emit()
    c.cards[0].finish.assert_called_once_with('no')
    c.cards[0].answered.emit('once')
    c.project.commitChanges.assert_not_called()
    assert not c.layer.layerModified.slots


@pytest.mark.parametrize('change', ['generation', 'busy', 'removed', 'state', 'protected', 'unreadable'])
def test_changed_context_cannot_write_even_after_a_click(commits, change):
    c = commits
    c.ui.offer([('roads', 1)])
    if change == 'generation':
        c.host._memory_generation += 1
    elif change == 'busy':
        c.busy.return_value = True
    elif change == 'removed':
        c.project.mapLayer = lambda _key: None
    elif change == 'state':
        c.layer.index += 1
    elif change == 'protected':
        c.protection.read_ids.return_value = ['roads']
    elif change == 'unreadable':
        c.protection.read_ids.side_effect = ValueError('unreadable protection')
    c.cards[0].answered.emit('once')
    c.project.commitChanges.assert_not_called()
    if change == 'generation':
        c.host.panel.show_error.assert_not_called()  # feedback cannot enter another conversation
    else:
        c.host.panel.show_error.assert_called_once()


def test_group_confirmation_lists_manual_companions_and_commits_the_native_group_once(commits):
    c = commits
    c.project.transactionMode = lambda: c.modes.BufferedGroups
    members = [c.layer, c.other]
    c.project.editBufferGroup = lambda: SimpleNamespace(layers=lambda: members)
    c.ui.offer([('roads', 1), ('manual', 1)])
    assert len(c.cards) == 1
    texts, body, _ = c.host.panel.add_confirm_card.call_args.args
    assert set(texts['layers']) == {'roads', 'manual'} and 'saved together' in body
    c.cards[0].answered.emit('once')
    c.project.commitChanges.assert_called_once_with(True, c.layer)


def test_automatic_provider_transaction_expands_the_confirmation_scope(commits):
    c = commits
    c.project.transactionMode = lambda: c.modes.AutomaticGroups
    c.layer.dataProvider = lambda: SimpleNamespace(transaction=lambda: SimpleNamespace(connectionString=lambda: 'connection'))
    c.layer.providerType = lambda: 'postgres'
    c.project.transactionGroup = lambda *args: SimpleNamespace(layers=lambda: [c.layer, c.other])
    c.ui.offer([('roads', 1)])
    assert set(c.host.panel.add_confirm_card.call_args.args[0]['layers']) == {'roads', 'manual'}
    c.other.layerModified.emit()
    c.cards[0].answered.emit('once')
    c.project.commitChanges.assert_not_called()


def test_new_group_member_requires_a_new_confirmation(commits):
    c = commits
    c.project.transactionMode = lambda: c.modes.BufferedGroups
    members = [c.layer]
    c.project.editBufferGroup = lambda: SimpleNamespace(layers=lambda: members)
    c.ui.offer([('roads', 1)])
    members.append(c.other)
    c.cards[0].answered.emit('once')
    c.project.commitChanges.assert_not_called()


def test_a_failed_provider_commit_reports_errors_without_rollback_or_false_success(commits):
    c = commits
    c.project.commitChanges.return_value = (False, ['constraint violation'])
    c.ui.offer([('roads', 1)])
    c.cards[0].answered.emit('once')
    assert 'constraint violation' in c.host.panel.show_error.call_args.args[1]
    c.host.panel.add_note.assert_not_called()
    assert c.layer.isModified()


def test_unload_or_card_destruction_releases_callbacks_and_prevents_late_commit(commits):
    c = commits
    c.ui.offer([('roads', 1)])
    c.cards[0].destroyed.emit(None)
    assert not c.ui._tickets
    c.cards[0].answered.emit('once')
    c.ui.offer([('roads', 1)])
    c.ui.close()
    c.cards[1].answered.emit('once')
    c.project.commitChanges.assert_not_called()
    assert not c.layer.layerModified.slots


def test_no_change_or_an_outdated_edit_position_has_no_confirmation(commits):
    c = commits
    c.ui.offer([('roads', 0)])
    c.layer.modified = False
    c.ui.offer([('roads', 1)])
    c.ui.offer([('gone', 1)])
    assert not c.cards


def test_unknown_transaction_scope_is_refused_before_a_confirmation(commits):
    c = commits
    c.project.transactionMode = lambda: 99
    c.ui.offer([('roads', 1)])
    assert not c.cards
    c.host.panel.show_error.assert_called_once()


def test_project_closure_during_native_commit_cannot_update_the_next_projects_chat(commits):
    c = commits
    c.ui.offer([('roads', 1)])
    def commit(*args):
        c.ui.close()
        return True, []
    c.project.commitChanges.side_effect = commit
    c.cards[0].answered.emit('once')
    c.host.panel.add_note.assert_not_called()
    c.host._refresh_history.assert_not_called()


def test_ui_failure_after_a_successful_commit_does_not_claim_the_provider_failed(commits):
    c = commits
    c.host._refresh_history.side_effect = RuntimeError('panel removed')
    c.ui.offer([('roads', 1)])
    c.cards[0].answered.emit('once')
    c.host.panel.show_error.assert_not_called()


def test_legacy_qgis_without_grouped_buffering_uses_the_layer_commit(commits):
    c = commits
    del c.project.transactionMode
    del c.project.commitChanges
    c.project.autoTransaction = lambda: False
    c.layer.dataProvider = lambda: SimpleNamespace(transaction=lambda: None)
    c.layer.commitChanges = MagicMock(return_value=True)
    c.layer.commitErrors = lambda: []
    c.ui.offer([('roads', 1)])
    c.cards[0].answered.emit('once')
    c.layer.commitChanges.assert_called_once()


def test_committing_a_memory_layer_does_not_promise_a_durable_file(commits):
    c = commits
    c.layer.providerType = lambda: 'memory'
    c.ui.offer([('roads', 1)])
    assert 'stays in memory' in c.host.panel.add_confirm_card.call_args.args[1]
