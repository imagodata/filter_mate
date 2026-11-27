"""Source discovery remains usable when the external search tools are absent."""
import pytest

from core.agent.skills import load, names

pytestmark = pytest.mark.unit


def test_datasets_is_available_even_when_all_external_search_tools_are_absent():
    offered = {'agent_options', 'show_settings_link'}
    assert 'datasets' in names(offered)
    skill = load('datasets', offered)
    assert 'disabled' in skill['instructions'] and 'never enables it' in skill['instructions']


def test_disabling_local_source_discovery_removes_its_dependent_skill():
    assert 'datasets' not in names({'show_settings_link'})
    with pytest.raises(KeyError):
        load('datasets', {'show_settings_link'})


def test_datasets_does_not_tell_external_mcp_clients_to_use_chat_only_settings_links():
    assert 'datasets' not in names({'agent_options', 'show_settings_link'}, audience='mcp')
