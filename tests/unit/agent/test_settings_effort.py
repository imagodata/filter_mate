# -*- coding: utf-8 -*-
"""Effort is saved for one model and server, never carried to an incompatible destination."""
from dataclasses import replace
import json

import pytest

from .test_settings_providers import agent_settings, fake_qgs_settings as _fake_qgs_settings

pytestmark = pytest.mark.unit
fake_qgs_settings = _fake_qgs_settings


def test_default_and_selected_effort_reach_the_provider_config(fake_qgs_settings):
    values = agent_settings.AgentSettings(model='claude-haiku-5-5')
    assert agent_settings.provider_config(values, '').effort is None
    agent_settings.write_effort(values, 'low')
    assert agent_settings.read_effort(values) == 'low'
    assert agent_settings.provider_config(values, '').effort == 'low'
    agent_settings.write_effort(values, '')
    assert agent_settings.provider_config(values, '').effort is None


def test_effort_is_isolated_by_model_and_server(fake_qgs_settings):
    first = agent_settings.AgentSettings(model='claude-haiku-5-5')
    agent_settings.write_effort(first, 'max')
    second = replace(first, model='claude-sonnet-5-5')
    server = replace(first, base_url='https://proxy.example.org')
    assert agent_settings.read_effort(second) == agent_settings.read_effort(server) == ''
    agent_settings.write_effort(second, 'low')
    assert agent_settings.read_effort(first) == 'max'
    assert agent_settings.read_effort(second) == 'low'


def test_unknown_and_unsupported_values_are_not_sent(fake_qgs_settings):
    values = agent_settings.AgentSettings(model='claude-opus-4-5')
    with pytest.raises(ValueError, match='Unsupported'):
        agent_settings.write_effort(values, 'max')
    key = agent_settings._effort_key(values)
    fake_qgs_settings['filter_mate/agent/effort_by_model'] = json.dumps({key: 'max'})
    assert agent_settings.provider_config(values, '').effort is None


@pytest.mark.parametrize('raw', ['{bad', 'null', '[]', '42'])
def test_invalid_preferences_preserve_the_default(fake_qgs_settings, raw):
    fake_qgs_settings['filter_mate/agent/effort_by_model'] = raw
    values = agent_settings.AgentSettings(model='claude-haiku-5-5')
    assert agent_settings.read_effort(values) == ''
