"""Search answers are bounded text candidates, never authenticated endpoints or automatic source additions."""
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest

from core.agent.source_search import MAX_BYTES, SourceSearchError, parse_search_results, search_url
from core.agent.sources import guess_source_kind, source_draft

pytestmark = pytest.mark.unit


def result(url, title='Geo portal', snippet='Official catalogue'):
    return (f'<div class="result"><a class="result__a" href="{url}">{title}</a>'
            f'<a class="result__snippet"><span>{snippet}</span></a></div>')


def test_search_stays_on_the_fixed_provider_with_an_encoded_public_query():
    url = urlsplit(search_url('Belgique WFS & eau'))
    assert url.scheme == 'https' and url.hostname == 'html.duckduckgo.com'
    assert parse_qs(url.query) == {'q': ['Belgique WFS & eau']}


@pytest.mark.parametrize('query', ['', ' ', None, 'x' * 401, 'query\nHeader: value'])
def test_bad_search_queries_are_rejected_before_a_request(query):
    with pytest.raises(SourceSearchError):
        search_url(query)


def test_redirect_wrappers_nested_text_and_snippets_are_read_without_visiting_results():
    endpoint = 'https://geo.example.org/ows?SERVICE=WFS'
    wrapper = '//duckduckgo.com/l/?' + urlencode({'uddg': endpoint})
    rows = parse_search_results(result(wrapper, 'Geo <b>WFS</b>', 'Water &amp; roads').encode())
    assert rows == [{'title': 'Geo WFS', 'url': endpoint, 'description': 'Water & roads',
                     'kind_hint': 'wfs', 'verified': False}]


def test_duplicate_results_and_the_requested_limit_are_respected():
    html = result('https://geo.example.org/wfs') * 2 + result('https://other.example.org/stac')
    assert len(parse_search_results(html.encode())) == 2
    assert len(parse_search_results(html.encode(), 1)) == 1


@pytest.mark.parametrize('url', ['javascript:alert(1)', 'file:///data/source', 'https://127.0.0.1/wfs',
                                 'http://169.254.169.254/latest', 'https://user:secret@example.org/wfs',
                                 'https://server.internal/wfs'])
def test_unsafe_result_links_are_not_returned(url):
    with pytest.raises(SourceSearchError):
        parse_search_results(result(url).encode())


def test_a_rejected_result_does_not_attach_its_description_to_the_previous_result():
    rows = parse_search_results((result('https://geo.example.org/wfs', snippet='Correct') +
                                 result('javascript:alert(1)', snippet='Wrong source')).encode())
    assert rows[0]['description'] == 'Correct'


def test_a_browser_challenge_or_unrecognized_page_is_an_error_not_a_successful_empty_search():
    for html in ('<form id="anomaly-form">challenge</form>', '<html>unexpected page</html>'):
        with pytest.raises(SourceSearchError):
            parse_search_results(html.encode())
    assert parse_search_results(b'<div class="no-results">No results</div>') == []


def test_a_large_response_and_invalid_limits_are_refused():
    with pytest.raises(SourceSearchError):
        parse_search_results(b'x' * (MAX_BYTES + 1))
    for limit in (True, 0, 9, '5'):
        with pytest.raises(SourceSearchError):
            parse_search_results(result('https://example.org').encode(), limit)


@pytest.mark.parametrize('url, kind', [
    ('https://geo.example.org/ows?SERVICE=WFS&REQUEST=GetCapabilities', 'wfs'),
    ('https://geo.example.org/ows?service=WmTs', 'wmts'), ('https://geo.example.org/wms', 'wms'),
    ('https://data.example.org/api/3/action/package_search', 'ckan'),
    ('https://data.example.org/api/explore/v2.1/catalog/datasets', 'opendatasoft'),
    ('https://imagery.example.org/stac/v1', 'stac'), ('https://example.org/mcp', 'mcp'),
    ('https://tiles.example.org/{z}/{x}/{y}.png', 'xyz'), ('https://example.org/geodata', ''),
])
def test_type_detection_uses_explicit_url_hints_without_guessing_from_site_names(url, kind):
    assert guess_source_kind(url) == kind


def test_a_capabilities_url_becomes_a_service_draft_without_duplicate_ogc_parameters():
    draft = source_draft('https://geo.example.org/ows?Service=WFS&REQUEST=GetCapabilities&VERSION=2.0.0&map=public',
                         title=' Water   data ')
    assert draft == {'address': 'https://geo.example.org/ows?map=public', 'kind': 'wfs', 'title': 'Water data'}
    assert source_draft('https://example.org/catalogue')['kind'] == ''


def test_a_source_draft_still_rejects_invalid_addresses_and_types():
    for address, kind in [('javascript:bad', 'auto'), ('https://user:secret@example.org/wfs', 'wfs'),
                          ('https://example.org', 'unknown')]:
        with pytest.raises(ValueError):
            source_draft(address, kind)


def test_api_links_become_portal_roots_and_mcp_keeps_its_trailing_slash():
    assert source_draft('https://data.example.org/catalogue/api/3/action/package_search')['address'] == 'https://data.example.org/catalogue'
    assert source_draft('https://data.example.org/api/explore/v2.1/catalog/datasets')['address'] == 'data.example.org'
    assert source_draft('example.org/mcp/')['address'] == 'https://example.org/mcp/'
