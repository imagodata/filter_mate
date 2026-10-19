"""Small offline OGC API Features fixture for the dock's remote-read checks."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit


class FeatureService:
    """An HTTP service with deterministic points, pagination and delayed reads."""

    def __init__(self):
        service = self
        self.reads = 0
        self.delay = 0.15
        self.features = [
            {'type': 'Feature', 'id': i, 'geometry': {'type': 'Point', 'coordinates': [i, i]},
             'properties': {'id': i, 'name': 'Place {}'.format(i)}} for i in range(1, 26)
        ]

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                parsed = urlsplit(self.path)
                path = parsed.path.rstrip('/')
                query = parse_qs(parsed.query)
                root = service.url
                collection = {'id': 'places', 'title': 'Places', 'itemType': 'feature',
                              'extent': {'spatial': {'bbox': [[1, 1, 25, 25]],
                                                     'crs': 'http://www.opengis.net/def/crs/OGC/1.3/CRS84'}},
                              'links': [{'href': root + '/collections/places/items', 'rel': 'items',
                                         'type': 'application/geo+json'}]}
                kind = 'application/json'
                if path.endswith('/items'):
                    service.reads += 1
                    time.sleep(service.delay)
                    limit = int(query.get('limit', ['10'])[0])
                    offset = int(query.get('offset', ['0'])[0])
                    rows = service.features[offset:offset + limit]
                    links = []
                    if offset + limit < len(service.features):
                        links.append({'href': root + '/collections/places/items?limit={}&offset={}'.format(limit, offset + limit),
                                      'rel': 'next', 'type': 'application/geo+json'})
                    result = {'type': 'FeatureCollection', 'features': rows, 'numberMatched': len(service.features),
                              'numberReturned': len(rows), 'links': links}
                    kind = 'application/geo+json'
                elif path.endswith('/collections/places'):
                    result = collection
                elif path.endswith('/collections'):
                    result = {'collections': [collection], 'links': []}
                elif path.endswith('/conformance'):
                    result = {'conformsTo': ['http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/core',
                                            'http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/geojson']}
                elif path.endswith('/api'):
                    result = {'openapi': '3.0.0', 'info': {'title': 'Offline places', 'version': '1'},
                              'paths': {}, 'components': {}}
                elif '/items/' in path:
                    try:
                        result = service.features[int(path.rsplit('/', 1)[1]) - 1]
                    except (IndexError, ValueError):
                        self.send_error(404)
                        return
                    kind = 'application/geo+json'
                else:
                    result = {'title': 'Offline places', 'links': [
                        {'href': root + '/api', 'rel': 'service-desc', 'type': 'application/vnd.oai.openapi+json;version=3.0'},
                        {'href': root + '/conformance', 'rel': 'conformance', 'type': 'application/json'},
                        {'href': root + '/collections', 'rel': 'data', 'type': 'application/json'}]}
                data = json.dumps(result).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', kind)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = 'http://127.0.0.1:{}'.format(self.server.server_address[1])
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
