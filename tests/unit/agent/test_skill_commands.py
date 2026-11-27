"""Slash commands are explicit first-word requests, not paths, links or arbitrary tool dispatch."""
import pytest

from core.agent.skill_commands import completion_prefix, requested_skill

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('text,name', [('/brainstorm', 'brainstorm'), (' /Designer propose two maps', 'designer'),
                                     ('/datasets\nFind buildings', 'datasets'), ('/connector-data query', 'connector-data')])
def test_skill_command_at_the_start(text, name):
    assert requested_skill(text) == name


@pytest.mark.parametrize('text', ['/tmp/map.geojson', '/tmp/map', 'Use /designer for this',
                                 'https://host/designer', '/designer.svg', 'C:/data/map', '/../../etc', '//server/share'])
def test_paths_and_mentions_in_prose_are_not_commands(text):
    assert requested_skill(text) is None


def test_completion_only_in_the_first_command_word():
    assert completion_prefix('/') == ''
    assert completion_prefix(' /Bra') == 'bra'
    assert completion_prefix('/brainstorm compare') is None
    assert completion_prefix('use /bra') is None
    assert completion_prefix('/tmp/data') is None
