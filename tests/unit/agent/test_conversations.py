"""Archive persistence and project identities without Qt or QGIS."""
import pytest

from core.agent.conversations import ConversationStore
from core.agent.transcript import entry

pytestmark = pytest.mark.unit


def test_restart_preserves_multiple_conversations_and_the_empty_active_one(tmp_path):
    path = tmp_path / 'profile' / 'conversations.sqlite3'
    store = ConversationStore(path)
    project = store.project('original-path')
    first = store.start(project, '/original.qgz')
    store.save(first, project, [entry('user', 'Bonjour'), entry('text', 'Réponse')], session='context')
    second = store.start(project)
    assert first != second
    reopened = ConversationStore(path)
    assert reopened.project('original-path') == project
    assert reopened.head(project)['id'] == second
    assert reopened.head(project)['transcript'] == []
    assert reopened.get(first)['session'] == 'context'
    assert [row['title'] for row in reopened.list()] == ['Bonjour']


def test_save_as_follows_a_stable_identity_and_does_not_merge_unsaved_projects(tmp_path):
    store = ConversationStore(tmp_path / 'archive.sqlite3')
    first, other = store.project(), store.project()
    assert first != other
    conversation = store.start(first)
    store.save(conversation, first, [entry('user', 'Unsaved')])
    store.alias('saved-path', first)
    assert store.project('saved-path') == first
    assert store.head(other) is None
    with pytest.raises(ValueError):
        store.save(conversation, other, [entry('user', 'Wrong project')])
    assert store.get(conversation)['transcript'][0]['text'] == 'Unsaved'


def test_saving_transcript_keeps_the_model_session_and_permissions_are_not_stored(tmp_path):
    store = ConversationStore(tmp_path / 'archive.sqlite3')
    project = store.project('p')
    conversation = store.start(project)
    store.save(conversation, project, [entry('user', 'Question')], session='old context')
    store.save(conversation, project, [entry('user', 'Question'), entry('text', 'Answer')])
    assert store.get(conversation)['session'] == 'old context'
    assert set(store.get(conversation)) == {
        'id', 'project', 'path', 'title', 'created', 'updated', 'transcript', 'session'}
    store.save(conversation, project, [entry('user', 'Question')], session='')
    assert store.get(conversation)['session'] == ''


def test_empty_restarts_do_not_evict_real_history_and_retention_keeps_the_active_head(tmp_path, monkeypatch):
    from core.agent import conversations
    monkeypatch.setattr(conversations, 'MAX_CONVERSATIONS', 3)
    store = ConversationStore(tmp_path / 'archive.sqlite3')
    project = store.project('p')
    first = store.start(project)
    store.save(first, project, [entry('user', 'First')])
    empty = store.start(project)
    for _ in range(10):
        assert store.start(project) == empty
    assert store.get(first) is not None
    for number in range(3):
        item = store.start(project)
        store.save(item, project, [entry('user', str(number))])
    assert len(store.list()) == 3
    assert store.get(first) is None
    assert store.head(project)['id'] == item


def test_failed_update_is_atomic(tmp_path):
    store = ConversationStore(tmp_path / 'archive.sqlite3')
    project = store.project('p')
    identifier = store.start(project)
    store.save(identifier, project, [entry('user', 'Kept')], session='kept')
    with pytest.raises(ValueError):
        store.save(identifier, project, [entry('user', 'Broken')], session='x' * 1_000_001)
    assert store.head(project)['transcript'][0]['text'] == 'Kept'
    assert store.get(identifier)['session'] == 'kept'
