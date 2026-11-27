import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from .test_agent_chat_lifecycle import _PKG, _load, _module, controller, ctrl_module, dock  # noqa: F401

pytestmark = pytest.mark.unit


@pytest.fixture
def search(ctrl_module, controller, monkeypatch):
    module = importlib.import_module(_PKG + '.core.agent.source_search')
    call = MagicMock(return_value={'results': [{'url': 'https://geo.example.org/wfs', 'verified': False}]})
    _module(monkeypatch, '.adapters.agent.source_search', search_data_sources=call)
    values = SimpleNamespace(**vars(ctrl_module.load_settings()))
    monkeypatch.setattr(ctrl_module, 'load_settings', lambda: values)
    return SimpleNamespace(ctrl=controller, call=call, values=values, error=module.SourceSearchError)


def test_disabled_web_search_is_refused_even_if_its_handler_is_called_directly(search, ctrl_module):
    with pytest.raises(ctrl_module.ToolFailure, match='disabled'):
        search.ctrl._search_data_sources_tool({'query': 'water WFS Belgium'})
    search.call.assert_not_called()


def test_enabled_search_returns_candidates_without_activating_any_of_them(search):
    search.values.enabled_sources = ['web_search']
    answer = search.ctrl._search_data_sources_tool({'query': 'water WFS Belgium'})
    assert answer['results'][0]['verified'] is False
    search.call.assert_called_once_with('water WFS Belgium', 5)
    assert search.values.enabled_sources == ['web_search']


def test_a_blocked_search_has_no_fake_results_and_only_offers_a_browser_link(search, ctrl_module):
    search.values.enabled_sources = ['web_search']
    search.call.side_effect = search.error('browser check')
    with pytest.raises(ctrl_module.ToolFailure, match='browser check'):
        search.ctrl._search_data_sources_tool({'query': 'water WFS Belgium'})
    search.ctrl.panel.add_link.assert_called_once()
    assert callable(search.ctrl.panel.add_link.call_args.args[1])


def test_source_suggestion_only_opens_a_prefilled_form_after_the_user_clicks(controller, monkeypatch):
    open_settings = MagicMock()
    monkeypatch.setattr(controller, 'open_settings', open_settings)
    controller._settings_link_tool({'target': 'sources', 'source': {
        'address': 'https://geo.example.org/ows?service=WFS&request=GetCapabilities', 'title': 'Water data'}})
    open_settings.assert_not_called()
    label, click = controller.panel.add_link.call_args.args
    assert 'Water data' in label
    click()
    open_settings.assert_called_once_with(tab='sources', source_draft={
        'address': 'https://geo.example.org/ows', 'kind': 'wfs', 'title': 'Water data'})


def test_a_source_draft_is_refused_for_other_settings_tabs(controller, ctrl_module):
    with pytest.raises(ctrl_module.ToolFailure):
        controller._settings_link_tool({'target': 'provider', 'source': {'address': 'https://example.org/wfs'}})
    controller.panel.add_link.assert_not_called()


@pytest.fixture
def adapter(ctrl_module, monkeypatch):
    http = _module(monkeypatch, '.adapters.agent.bounded_http', fetch=MagicMock(),
                   HttpFailure=type('HttpFailure', (Exception,), {}))
    module = _load(monkeypatch, 'adapters.agent.source_search', 'adapters/agent/source_search.py')
    return module, http


def test_network_search_is_bounded_and_visits_only_the_search_provider(adapter):
    module, http = adapter
    http.fetch.return_value = SimpleNamespace(status=200, content=(
        b'<a class="result__a" href="https://geo.example.org/wfs">WFS</a>'
        b'<a class="result__snippet">Reference data</a>'))
    answer = module.search_data_sources('water WFS Belgium')
    assert answer['results'][0]['url'] == 'https://geo.example.org/wfs'
    http.fetch.assert_called_once()
    args, kwargs = http.fetch.call_args
    assert args[0].startswith('https://html.duckduckgo.com/html/?')
    assert kwargs['max_bytes'] <= 2 * 1024 * 1024 and kwargs['timeout_ms'] <= 20_000


@pytest.mark.parametrize('code', [202, 302, 403, 429, 500])
def test_http_failure_never_follows_redirects_or_claims_results(adapter, code):
    module, http = adapter
    http.fetch.return_value = SimpleNamespace(status=code, content=b'challenge')
    with pytest.raises(module.SourceSearchError, match='HTTP'):
        module.search_data_sources('public WFS')
    http.fetch.assert_called_once()


def test_invalid_arguments_and_transport_cancellation_have_no_fallback_requests(adapter):
    module, http = adapter
    for query, limit in [('', 2), ('public data', 0)]:
        with pytest.raises(module.SourceSearchError):
            module.search_data_sources(query, limit)
    http.fetch.assert_not_called()
    http.fetch.side_effect = http.HttpFailure('stopped')
    with pytest.raises(module.SourceSearchError, match='stopped'):
        module.search_data_sources('public data')
    http.fetch.assert_called_once()
