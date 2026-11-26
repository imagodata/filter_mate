"""Destination-bound audio credentials and preferences; no API key or recording in QgsSettings."""
import importlib
import json
import sys
import types
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def settings(monkeypatch):
    root = Path(__file__).resolve().parents[3]
    package = 'fm_speech_settings_test'
    for suffix in ('', '.core', '.core.agent', '.adapters', '.adapters.agent'):
        module = types.ModuleType(package + suffix)
        module.__path__ = [str(root.joinpath(*suffix.strip('.').split('.'))) if suffix else str(root)]
        monkeypatch.setitem(sys.modules, package + suffix, module)
    module = importlib.import_module(package + '.adapters.agent.speech_settings')
    data = {}
    monkeypatch.setattr(module, 'QgsSettings', lambda: SimpleNamespace(
        value=lambda key, default=None: data.get(key, default), setValue=data.__setitem__))
    monkeypatch.setattr(module, 'store_key', MagicMock(return_value='speech-authcfg'))
    monkeypatch.setattr(module, 'read_key', MagicMock(return_value='private-secret-key'))
    monkeypatch.setattr(module, 'delete_own_key', MagicMock())
    return module, data


def test_transcription_credentials_never_enter_the_settings_file(settings):
    module, data = settings
    values = module.SpeechSettings(service='openai')
    values = replace(values, accepted_target=values.target)
    saved = module.save_speech_settings(values, 'private-secret-key')
    assert saved.authcfg == 'speech-authcfg'
    assert 'private-secret-key' not in json.dumps(data)
    assert module.load_speech_settings() == saved
    assert module.speech_key(saved) == 'private-secret-key'


def test_a_stored_key_never_follows_an_address_change(settings):
    module, _data = settings
    values = module.SpeechSettings(service='openai', authcfg='old-key', key_target='https://original.example/v1')
    with pytest.raises(ValueError, match='another service'):
        module.speech_key(values)
    module.read_key.assert_not_called()


def test_reusing_the_chat_key_requires_the_same_provider_and_exact_destination(settings, monkeypatch):
    module, _data = settings
    values = module.SpeechSettings(service='openai', use_provider_key=True)
    current = SimpleNamespace(preset='openai', target=values.target, has_key=True, authcfg='chat-authcfg')
    monkeypatch.setattr(module, 'load_settings', lambda: current)
    saved = module.save_speech_settings(replace(values, accepted_target=values.target))
    assert saved.authcfg == '' and saved.use_provider_key
    module.read_key.assert_called_once_with('chat-authcfg')
    module.store_key.assert_not_called()
    module.read_key.reset_mock()
    with pytest.raises(ValueError, match='no stored key'):
        module.speech_key(replace(saved, base_url='https://another.example/v1'))
    module.read_key.assert_not_called()


def test_invalid_replacement_does_not_delete_the_previous_credential(settings):
    module, _data = settings
    values = module.SpeechSettings(service='openai')
    module.save_speech_settings(replace(values, accepted_target=values.target), 'private-secret-key')
    with pytest.raises(ValueError, match='needs an API key'):
        module.save_speech_settings(values, forget_key=True)
    module.delete_own_key.assert_not_called()


def test_corrupt_preferences_and_remote_local_services_do_not_become_configured(settings):
    module, data = settings
    for raw in ('not json', '[]', '{"service":"local","base_url":"http://remote.example/v1"}'):
        data[module.KEY] = raw
        assert not module.load_speech_settings().configured
