"""Network adapter for the single enabled web-search provider; bounded, cancellable and without visited results."""
from ...core.agent.source_search import MAX_BYTES, TIMEOUT_MS, SourceSearchError, parse_search_results, search_url
from .bounded_http import HttpFailure, fetch


def search_data_sources(query, limit=5):
    url = search_url(query)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 8:
        raise SourceSearchError('limit is an integer from 1 to 8')
    try:
        reply = fetch(url, max_bytes=MAX_BYTES, timeout_ms=TIMEOUT_MS,
                      headers={'Accept': 'text/html', 'User-Agent': 'FilterMate-QGIS-plugin'})
    except HttpFailure as exc:
        raise SourceSearchError(str(exc)) from None
    if reply.status != 200:
        raise SourceSearchError(f'The web search answered HTTP {reply.status}. Use the browser search; no source was visited.')
    return {'provider': 'DuckDuckGo', 'query': query.strip(), 'search_url': url,
            'results': parse_search_results(reply.content, limit),
            'note': 'Unverified candidate pages. Result sites were not visited, added or enabled. Verify the service before adding it.'}
