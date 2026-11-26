# -*- coding: utf-8 -*-
"""Basemap connection checks with real QGIS and local HTTP servers; no public service is contacted.

Run in an isolated QGIS process: proxy settings are changed in memory, never in the user's profile.
"""
import base64
import os
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from qgis.core import QgsApplication, QgsNetworkAccessManager  # noqa: E402
from qgis.PyQt.QtNetwork import QNetworkProxy, QNetworkProxyFactory  # noqa: E402
from qgis.PyQt.QtNetwork import QSslCertificate  # noqa: E402

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aZ1cAAAAASUVORK5CYII=")
RESULTS = []
REQUESTS = []


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        REQUESTS.append(self.path)
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.end_headers()
        self.wfile.write(PNG)

    def log_message(self, *args):
        pass


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {detail}" if not condition else ""), flush=True)


def check_certificates():
    from filter_mate.adapters.agent.bounded_http import HttpFailure, fetch

    work = tempfile.mkdtemp()
    certificate, key = os.path.join(work, "ca.pem"), os.path.join(work, "key.pem")
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                    "-subj", "/CN=127.0.0.1", "-addext", "subjectAltName=IP:127.0.0.1",
                    "-addext", "basicConstraints=critical,CA:TRUE", "-keyout", key, "-out", certificate],
                   check=True, capture_output=True)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate, key)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"https://127.0.0.1:{server.server_port}/1/0/0.png"
    try:
        try:
            fetch(url, timeout_ms=1500)
            check("an untrusted certificate is refused without a dialog", False)
        except HttpFailure as exc:
            check("an untrusted certificate is refused without a dialog", "certificate" in str(exc), str(exc))
        authority = QSslCertificate.fromPath(certificate)[0]
        auth = QgsApplication.authManager()
        check("test CA stored only in the isolated QGIS profile", auth.storeCertAuthority(authority))
        auth.rebuildCaCertsCache()
        auth.rebuildTrustedCaCertsCache()
        try:
            reply = fetch(url, timeout_ms=1500)
            check("a certificate trusted by QGIS also works for the basemap check", reply.content == PNG)
        except HttpFailure as exc:
            check("a certificate trusted by QGIS also works for the basemap check", False, str(exc))
        try:
            fetch(url.replace("127.0.0.1", "localhost"), timeout_ms=1500)
            check("a trusted certificate for the wrong host is still refused", False)
        except HttpFailure as exc:
            check("a trusted certificate for the wrong host is still refused", "certificate" in str(exc), str(exc))
    finally:
        server.shutdown()
        server.server_close()


def main():
    from filter_mate.adapters.agent.bounded_http import HttpFailure, fetch

    check_certificates()
    server = ThreadingHTTPServer(("0.0.0.0", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    network = QgsNetworkAccessManager.instance()
    # A non-loopback address: Qt always bypasses proxies for 127.0.0.1, hiding the exclusion-list defect.
    address = f"http://{socket.gethostbyname(socket.gethostname())}:{server.server_port}/"
    bad_proxy = QNetworkProxy(QNetworkProxy.ProxyType.HttpProxy, "127.0.0.1", 1)
    network.setFallbackProxyAndExcludes(bad_proxy, [], [address])

    def gets_tile(label, url):
        try:
            reply = fetch(url, timeout_ms=1500)
            check(label, reply.status == 200 and reply.content == PNG, reply.status)
        except HttpFailure as exc:
            check(label, False, str(exc))

    try:
        gets_tile("QGIS proxy exclusions also apply to the basemap check", address + "1/0/0.png")

        class Factory(QNetworkProxyFactory):
            def queryProxy(self, query):
                return [QNetworkProxy(QNetworkProxy.ProxyType.HttpProxy, "127.0.0.1", server.server_port)]

        factory = Factory()
        network.setProxyFactory(factory)
        # No DNS or public request: the configured proxy itself serves this tile.
        gets_tile("QGIS proxy factories also apply to the basemap check", "http://tiles.invalid/1/0/0.png")
        check("the configured proxy received the tile URL", "http://tiles.invalid/1/0/0.png" in REQUESTS)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    profile = tempfile.mkdtemp()
    os.environ["QGIS_CUSTOM_CONFIG_PATH"] = profile
    os.environ["QGIS_AUTH_DB_DIR_PATH"] = profile
    app = QgsApplication([], True)
    app.initQgis()
    root = tempfile.mkdtemp()
    os.symlink(os.environ.get("FM_REPO", "/src"), os.path.join(root, "filter_mate"))
    sys.path.insert(0, root)
    sys.dont_write_bytecode = True
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        RESULTS.append(False)
    print(f"{RESULTS.count(True)}/{len(RESULTS)} passed", flush=True)
    os._exit(1 if RESULTS.count(False) else 0)
