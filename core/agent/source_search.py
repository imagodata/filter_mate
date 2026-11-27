"""Bounded, text-only discovery of candidate pages for data sources or skills; result sites are never visited."""
from html.parser import HTMLParser
from ipaddress import ip_address
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit

SEARCH_ENDPOINT = 'https://html.duckduckgo.com/html/'
MAX_BYTES = 2 * 1024 * 1024
TIMEOUT_MS = 20_000
MAX_RESULTS = 8


class SourceSearchError(ValueError):
    pass


def search_url(query):
    if not isinstance(query, str) or not query.strip() or len(query) > 400 or any(ord(char) < 32 for char in query):
        raise SourceSearchError('give a public search query of 1 to 400 characters')
    return SEARCH_ENDPOINT + '?' + urlencode({'q': query.strip()})


def _public_url(value):
    try:
        value = urljoin(SEARCH_ENDPOINT, value)
        parsed = urlsplit(value)
        host = (parsed.hostname or '').lower()
        if host == 'duckduckgo.com' or host.endswith('.duckduckgo.com'):
            if parsed.path.rstrip('/') != '/l':
                return ''
            value = (parse_qs(parsed.query).get('uddg') or [''])[0]
            parsed = urlsplit(value)
            host = (parsed.hostname or '').lower()
        if parsed.scheme not in ('http', 'https') or not host or parsed.username or parsed.password:
            return ''
        if any(ord(char) < 33 for char in value) or len(value) > 2000:
            return ''
        if '.' not in host or host.endswith(('.local', '.localhost', '.internal')):
            return ''
        try:
            if not ip_address(host).is_global:
                return ''
        except ValueError:
            pass
        return value
    except (ValueError, TypeError):
        return ''


class _Results(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.capture, self.depth = '', 0
        self.current = None
        self.blocked, self.empty = False, False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = (attributes.get('class') or '').split()
        if attributes.get('id') in ('anomaly-form', 'challenge-form') or '/anomaly' in (attributes.get('action') or ''):
            self.blocked = True
        if any('no-results' in part for part in classes):
            self.empty = True
        if tag == 'a' and 'result__a' in classes:
            self.current = None
            self.capture, self.depth = '', 0
            url = _public_url(attributes.get('href') or '')
            if url and len(self.rows) < 30:
                self.current = {'title': '', 'url': url, 'description': ''}
                self.rows.append(self.current)
                self.capture, self.depth = 'title', 1
        elif 'result__snippet' in classes and self.current is not None:
            self.capture, self.depth = 'description', 1
        elif self.capture and tag not in ('br', 'img', 'hr', 'input', 'meta', 'link', 'wbr'):
            self.depth += 1

    def handle_endtag(self, tag):
        if self.capture and tag not in ('br', 'img', 'hr', 'input', 'meta', 'link', 'wbr'):
            self.depth -= 1
            if self.depth <= 0:
                self.capture = ''

    def handle_data(self, value):
        if self.capture:
            row = self.current
            limit = 200 if self.capture == 'title' else 600
            row[self.capture] = (row[self.capture] + value)[:limit]


def parse_search_results(content, limit=5):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_RESULTS:
        raise SourceSearchError('limit is an integer from 1 to 8')
    if not isinstance(content, bytes) or len(content) > MAX_BYTES:
        raise SourceSearchError('the search answer is too large or unreadable')
    parser = _Results()
    parser.feed(content.decode('utf-8', 'replace'))
    if parser.blocked:
        raise SourceSearchError('The search engine requires a browser check. Open the search in your browser; no source was visited.')
    results, seen = [], set()
    from .sources import guess_source_kind
    for row in parser.rows:
        if row['url'] in seen or not row['title'].strip():
            continue
        seen.add(row['url'])
        row['title'] = ' '.join(row['title'].split())
        row['description'] = ' '.join(row['description'].split())
        results.append(dict(row, kind_hint=guess_source_kind(row['url']), verified=False))
        if len(results) == limit:
            break
    if not results and not parser.empty:
        raise SourceSearchError('The search answer was not recognized. Use the browser search; no source was visited.')
    return results
