# -*- coding: utf-8 -*-
"""Model capabilities and actual provider payloads for the optional effort control."""
import json

import pytest

from core.agent.messages import TextDelta, TurnComplete
from core.agent.providers import create_provider
from core.agent.providers.base import ProviderConfig
from core.agent.providers.effort import effort_levels, valid_effort

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('preset,model,levels', [
    ('anthropic', 'claude-haiku-5-5', ('low', 'medium', 'high', 'xhigh', 'max')),
    ('anthropic', 'claude-opus-4-5-20251101', ('low', 'medium', 'high')),
    ('anthropic', 'claude-sonnet-4-6', ('low', 'medium', 'high', 'max')),
    ('anthropic', 'claude-haiku-4-5', ()),
    ('anthropic', 'claude-sonnet-4-5', ()),
    ('anthropic', 'claude-unknown', ()),
    ('openai', 'gpt-5.4-2026-03-05', ('low', 'medium', 'high')),
    ('openai', 'o3-mini', ('low', 'medium', 'high')),
    ('openai', 'gpt-4o', ()),
    ('openai', 'gpt-5-pro', ()),
    ('openai', 'gpt-5.3-chat-latest', ()),
    ('mistral', 'mistral-small-2603', ('none', 'high')),
    ('mistral', 'mistral-large-4-0', ('low', 'medium', 'high')),
    ('mistral', 'zai-glm-5-3', ('low', 'high', 'max')),
    ('mistral', 'magistral-small-latest', ()),
    ('ollama', 'gpt-oss:20b', ('low', 'medium', 'high')),
    ('ollama', 'gpt-oss:120b-cloud', ('low', 'medium', 'high')),
    ('ollama', 'qwen3:8b', ()),  # on/off thinking is not a supported effort ladder
    ('unknown', 'gpt-5', ()),
])
def test_only_known_model_controls_are_offered(preset, model, levels):
    assert effort_levels(preset, model) == levels


def test_unsupported_or_stale_effort_is_the_provider_default():
    assert valid_effort('anthropic', 'claude-opus-4-5', 'max') == ''
    assert valid_effort('anthropic', 'claude-haiku-5-5', None) == ''
    assert valid_effort('openai', 'gpt-4o', 'high') == ''


@pytest.mark.parametrize('kind,model,url,effort,field,expected', [
    ('anthropic', 'claude-haiku-5-5', 'https://api.anthropic.com', 'xhigh', 'output_config', {'effort': 'xhigh'}),
    ('openai_compatible', 'gpt-5.4', 'https://api.openai.com/v1', 'low', 'reasoning_effort', 'low'),
    ('openai_compatible', 'mistral-small-2603', 'https://api.mistral.ai/v1', 'none', 'reasoning_effort', 'none'),
    ('ollama', 'gpt-oss:20b', 'http://localhost:11434', 'medium', 'think', 'medium'),
])
def test_selected_effort_uses_the_provider_wire_format(kind, model, url, effort, field, expected):
    provider = create_provider(ProviderConfig(kind, model, base_url=url, effort=effort))
    assert json.loads(provider.build_request('S', [], []).body)[field] == expected


@pytest.mark.parametrize('kind,model,url', [
    ('anthropic', 'claude-haiku-4-5', 'https://api.anthropic.com'),
    ('openai_compatible', 'gpt-4o', 'https://api.openai.com/v1'),
    ('ollama', 'qwen3:8b', 'http://localhost:11434'),
])
def test_an_unsupported_model_never_receives_an_effort_parameter(kind, model, url):
    provider = create_provider(ProviderConfig(kind, model, base_url=url, effort='high'))
    body = json.loads(provider.build_request('S', [], []).body)
    assert not {'output_config', 'reasoning_effort', 'think'} & body.keys()


def test_automatic_omits_the_parameter_instead_of_forcing_a_level():
    provider = create_provider(ProviderConfig('anthropic', 'claude-haiku-5-5'))
    assert 'output_config' not in json.loads(provider.build_request('S', [], []).body)


def test_mistral_thinking_chunks_are_not_shown_as_the_answer():
    provider = create_provider(ProviderConfig('openai_compatible', 'mistral-small-2603',
                                             base_url='https://api.mistral.ai/v1', effort='high'))
    payload = {'choices': [{'delta': {'content': [
        {'type': 'thinking', 'thinking': [{'type': 'text', 'text': 'private reasoning'}]},
        {'type': 'text', 'text': 'The answer.'},
    ]}, 'finish_reason': 'stop'}]}
    data = ('data: ' + json.dumps(payload) + '\n\ndata: [DONE]\n\n').encode()
    parser = provider.new_parser()
    events = []
    for index in range(0, len(data), 7):
        events.extend(parser.feed(data[index:index + 7]))
    events.extend(parser.close())
    assert ''.join(event.text for event in events if isinstance(event, TextDelta)) == 'The answer.'
    turn = next(event for event in events if isinstance(event, TurnComplete))
    assert turn.message.text == 'The answer.'
