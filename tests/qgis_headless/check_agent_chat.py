# -*- coding: utf-8 -*-
"""The chat in a real QGIS: real network stack, authentication database, layers and widgets, a fake provider.

The provider is a local server that speaks the streaming format of the Messages API, so no model is called.
Run inside a qgis/qgis image, on a writable copy of the repository (the plugin writes its log there):

    docker run --rm --network none -v "$PWD:/src:ro" -e FM_REPO=/tmp/copy qgis/qgis:ltr bash -c \\
        'mkdir /tmp/copy; cp -r /src/. /tmp/copy; python3 /tmp/copy/tests/qgis_headless/check_agent_chat.py'

Prints one PASS / FAIL line per check; exits with 1 when one failed.
"""
import json
import os
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HOME = tempfile.mkdtemp()
os.environ["QGIS_CUSTOM_CONFIG_PATH"] = HOME
os.environ["QGIS_AUTH_DB_DIR_PATH"] = HOME

from qgis.core import (  # noqa: E402
    Qgis, QgsApplication, QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsSettings, QgsVectorFileWriter,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication, Qt, QTimer  # noqa: E402
from qgis.PyQt.QtTest import QTest  # noqa: E402
from qgis.PyQt.QtWidgets import QFrame, QLabel, QPushButton, QToolBox, QWidget  # noqa: E402

RESULTS = []
SECRET = "sk-test-do-not-log-0123456789"


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {detail}" if not condition else ""), flush=True)


def wait(condition, seconds=10.0):
    deadline = time.time() + seconds
    while time.time() < deadline:
        QCoreApplication.processEvents()
        if condition():
            return True
        time.sleep(0.005)
    return False


def sse(*events):
    return "".join(f"event: {e['type']}\ndata: {json.dumps(e, ensure_ascii=False)}\n\n" for e in events).encode("utf-8")


def text_turn(text):
    return sse(
        {"type": "message_start", "message": {"usage": {"input_tokens": 5, "output_tokens": 0}}},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text}},
        {"type": "content_block_stop", "index": 0},
        {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 3}},
        {"type": "message_stop"})


def tool_turn(name, arguments, call_id="toolu_1"):
    return sse(
        {"type": "message_start", "message": {"usage": {"input_tokens": 5, "output_tokens": 0}}},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": call_id, "name": name, "input": {}}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": json.dumps(arguments)}},
        {"type": "content_block_stop", "index": 0},
        {"type": "message_delta", "delta": {"stop_reason": "tool_use"}, "usage": {"output_tokens": 3}},
        {"type": "message_stop"})


class Provider:
    """Answers each POST with the next scripted response: (status, headers, body) or "hang"."""

    def __init__(self):
        self.script = []
        self.requests = []
        self.release = threading.Event()
        provider = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                provider.requests.append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()},
                                          "body": body})
                step = provider.script.pop(0) if provider.script else (500, {}, b"{}")
                if step == "hang":
                    provider.release.wait(30)
                    return
                status, headers, payload = step
                self.send_response(status)
                for name, value in headers.items():
                    self.send_header(name, value)
                self.end_headers()
                try:  # by pieces, cutting lines and characters anywhere
                    for start in range(0, len(payload), 37):
                        self.wfile.write(payload[start:start + 37])
                        self.wfile.flush()
                        time.sleep(0.001)
                except OSError:
                    pass

            def do_GET(self):
                provider.requests.append({"path": self.path, "headers": {}, "body": None})
                self.send_response(200)
                self.end_headers()

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def reset(self, *script):
        self.script = list(script)
        self.requests = []
        self.release.clear()


def make_layer(path):
    memory = QgsVectorLayer("Point?crs=EPSG:2154&field=pop:integer", "m", "memory")
    features = []
    for index in range(1, 61):
        feature = QgsFeature(memory.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(650000 + index, 6860000)))
        feature.setAttributes([index * 100])
        features.append(feature)
    memory.dataProvider().addFeatures(features)
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    QgsVectorFileWriter.writeAsVectorFormatV3(memory, path, QgsProject.instance().transformContext(), options)
    return QgsVectorLayer(path, "communes", "ogr")


def check_transport(provider, pkg):
    from filter_mate.adapters.agent.qt_transport import QtTransport
    from filter_mate.core.agent.messages import StreamFailure, TextDelta, TurnComplete
    from filter_mate.core.agent.providers import create_provider
    from filter_mate.core.agent.providers.base import ProviderConfig

    client = create_provider(ProviderConfig("anthropic", "m", base_url=provider.url, api_key=SECRET))

    def run(*script, idle=30000, url=None):
        provider.reset(*script)
        request = client.build_request("S", [], [])
        if url:
            request = type(request)(url, request.headers, request.body)
        events = []
        handle = QtTransport(idle_timeout_ms=idle).start(request, client.new_parser(), events.append)
        finished = wait(lambda: any(isinstance(e, (TurnComplete, StreamFailure)) for e in events))
        return events, handle, finished

    events, _, finished = run((200, {"Content-Type": "text/event-stream"}, text_turn("Bonjour é")))
    check("stream: a turn arrives", finished and isinstance(events[-1], TurnComplete), events)
    check("stream: text rebuilt from cut pieces", "".join(e.text for e in events if isinstance(e, TextDelta)) == "Bonjour é", events)
    check("stream: one final event", sum(isinstance(e, (TurnComplete, StreamFailure)) for e in events) == 1, events)
    check("stream: key sent in its header", provider.requests[0]["headers"].get("x-api-key") == SECRET)
    check("stream: valid body", provider.requests[0]["body"]["model"] == "m" and provider.requests[0]["path"] == "/v1/messages")
    wait(lambda: False, 0.1)
    from qgis.PyQt.QtCore import QObject
    parent = QObject()
    provider.reset((200, {}, text_turn("x")))
    seen = []
    QtTransport(parent).start(client.build_request("S", [], []), client.new_parser(), seen.append)
    wait(lambda: any(isinstance(e, TurnComplete) for e in seen))
    wait(lambda: False, 0.3)
    QCoreApplication.sendPostedEvents(None, 52)  # DeferredDelete
    wait(lambda: False, 0.1)
    check("stream: nothing kept after the response", len(parent.children()) == 0, parent.children())

    events, _, _ = run((401, {"Content-Type": "application/json"}, b'{"error":{"message":"invalid x-api-key"}}'))
    check("401 is an auth error", isinstance(events[-1], StreamFailure) and events[-1].error.kind == "auth", events)
    check("401 carries the message", events[-1].error.message == "invalid x-api-key", events)

    events, _, _ = run((429, {"Retry-After": "7"}, b'{"error":{"message":"slow"}}'))
    check("429 with its delay", events[-1].error.kind == "rate_limit" and events[-1].error.retry_after == 7.0, events)

    events, _, _ = run((529, {}, b'{"error":{"message":"overloaded"}}'))
    check("529 is a server error", events[-1].error.kind == "server", events)

    events, _, _ = run((302, {"Location": provider.url + "/elsewhere"}, b""))
    check("a redirection is not followed", isinstance(events[-1], StreamFailure) and len(provider.requests) == 1, provider.requests)

    events, _, _ = run(url="http://127.0.0.1:9/v1/messages")
    check("connection refused is a network error", isinstance(events[-1], StreamFailure) and events[-1].error.kind == "network", events)

    events, _, finished = run("hang", idle=300)
    check("silence ends the request", finished and events[-1].error.kind == "network", events)
    provider.release.set()

    provider.reset("hang")
    events = []
    handle = QtTransport().start(client.build_request("S", [], []), client.new_parser(), events.append)
    wait(lambda: provider.requests, 3)
    handle.abort()
    wait(lambda: False, 0.3)
    check("abort: no event afterwards", events == [], events)
    provider.release.set()

    events, _, finished = run((200, {}, b'{"not":"a stream"}'))
    check("a response that is no stream is a failure", finished and isinstance(events[-1], StreamFailure), events)


def check_hostile_connector():
    """What a remote server should not be able to do to QGIS."""
    from filter_mate.adapters.agent.bounded_http import HttpFailure, fetch
    from filter_mate.adapters.agent.mcp_connection import McpConnection
    from filter_mate.core.agent.mcp_client import McpError
    from filter_mate.core.agent.sources import make_source

    seen = []
    plan = {}

    class Hostile(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, *args):
            pass

        def _send(self, status, payload=b"", headers=()):
            self.send_response(status)
            for name, value in headers:
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            seen.append(("GET", self.path))
            self._send(200, b"ok")

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            method = body.get("method")
            seen.append((self.path, method, self.headers.get("Mcp-Session-Id")))
            if self.path == "/redirect":
                self._send(307, b"", [("Location", "/target")])
                return
            if "id" not in body:
                self._send(202)
                return
            def rpc(result):
                return ("data: " + json.dumps({"jsonrpc": "2.0", "id": body["id"], "result": result}) + "\n\n").encode()
            if method == "initialize":
                self._send(200, rpc({"protocolVersion": "2025-06-18", "capabilities": {}}), [("mcp-session-id", "lower-sess")])
                return
            if method == "tools/list":
                if self.path == "/drip":
                    self.send_response(200)
                    self.end_headers()
                    try:
                        for _ in range(60):
                            self.wfile.write(b": keepalive\n\n")
                            self.wfile.flush()
                            time.sleep(0.1)
                    except OSError:
                        pass
                    return
                if self.path == "/huge":
                    self.send_response(200)
                    self.end_headers()
                    try:
                        for _ in range(4000):
                            self.wfile.write(b"x" * 65536)
                    except OSError:
                        pass
                    return
                if self.path == "/open":  # answers, and never closes the stream
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(rpc({"tools": []}))
                    self.wfile.flush()
                    time.sleep(3)
                    return
                self._send(200, rpc({"tools": [
                    {"name": "bad", "inputSchema": {"required": 5, "properties": 3}},
                    {"name": "ok", "inputSchema": {"type": "object"}}]}))
                return
            if method == "tools/call":
                if plan.get("mode") == "error":
                    self._send(200, ("data: " + json.dumps({"jsonrpc": "2.0", "id": body["id"], "error": {"code": -32603, "message": "boom"}}) + "\n\n").encode())
                    return
                if plan.get("mode") == "lost" and not plan.get("lost_once"):
                    plan["lost_once"] = True
                    self._send(404)
                    return
                self._send(200, rpc({"content": [{"type": "text", "text": "done\u2028line"}]}))

    server = ThreadingHTTPServer(("127.0.0.1", 0), Hostile)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"

    def connection(path):
        return McpConnection(make_source(base + path, "mcp", "T"))

    seen.clear()
    try:
        connection("/redirect").connect()
        check("hostile: a redirect is refused", False)
    except McpError as exc:
        check("hostile: a redirect is refused", "redirect" in str(exc) and not any(item[0] == "/target" for item in seen), seen)

    link = connection("/ok")
    tools = link.list_tools()
    check("hostile: a session in lower case is kept", any(item[2] == "lower-sess" for item in seen if item[0] == "/ok"), seen)
    check("hostile: a malformed schema is cleaned", tools[0].spec.input_schema["type"] == "object" and len(tools) == 2, tools)
    plan["mode"] = "error"
    seen.clear()
    try:
        link.call_tool("ok", {})
        check("hostile: an error is not sent again", False)
    except McpError:
        check("hostile: an error is not sent again", sum(item[1] == "tools/call" for item in seen) == 1, seen)
    plan.update(mode="lost")
    seen.clear()
    text = link.call_tool("ok", {})
    check("hostile: a lost session is resumed", sum(item[1] == "tools/call" for item in seen) == 2 and "done" in text, seen)
    plan.clear()
    check("hostile: U+2028 does not break an answer", "\u2028" in link.call_tool("ok", {}))

    dripping = connection("/drip")
    dripping.timeout_ms = 800
    started = time.time()
    try:
        dripping.list_tools()
        check("hostile: a dripping stream is cut", False)
    except McpError:
        check("hostile: a dripping stream is cut", time.time() - started < 3, time.time() - started)

    started = time.time()
    try:
        connection("/huge").list_tools()
        check("hostile: an endless answer is cut", False)
    except McpError as exc:
        check("hostile: an endless answer is cut", "too much" in str(exc) and time.time() - started < 15, (str(exc), time.time() - started))

    started = time.time()
    connection("/open").list_tools()
    check("hostile: an answered stream that stays open does not hold QGIS", time.time() - started < 2, time.time() - started)

    from filter_mate.adapters.agent import bounded_http
    timer_hits = []
    QTimer.singleShot(100, lambda: timer_hits.append(1) or bounded_http.abort_active())
    started = time.time()
    try:
        fetch(base + "/drip", body=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode(), timeout_ms=5000)
        check("stop: it interrupts a wait", False)
    except HttpFailure:
        check("stop: it interrupts a wait", time.time() - started < 2 and timer_hits, time.time() - started)
    server.shutdown()
    server.server_close()


def check_key_store():
    from filter_mate.adapters.agent import settings as agent_settings

    manager = QgsApplication.authManager()
    check("auth database ready", not manager.isDisabled() and manager.setMasterPassword("fm-test-master", True))
    authcfg = agent_settings.store_key(SECRET)
    check("key stored", bool(authcfg) and authcfg in manager.configIds(), authcfg)
    check("key read back", agent_settings.read_key(authcfg) == SECRET)
    check("key replaced in place", agent_settings.store_key("other-key", authcfg) == authcfg and
          agent_settings.read_key(authcfg) == "other-key")
    agent_settings.store_key(SECRET, authcfg)
    check("unknown id reads empty", agent_settings.read_key("nope123") == "")
    values = agent_settings.AgentSettings(preset="mistral", model="m", consent=True, send_values=False, authcfg=authcfg)
    agent_settings.save_settings(values)
    check("settings round trip", agent_settings.load_settings() == values, agent_settings.load_settings())
    QgsSettings().sync()
    leaked = []
    for folder, _, names in os.walk(HOME):
        for name in names:
            if name.endswith((".ini", ".json", ".conf")):
                with open(os.path.join(folder, name), "rb") as stream:
                    if SECRET.encode() in stream.read():
                        leaked.append(name)
    check("the key is in no settings file", not leaked, leaked)
    with open(os.path.join(HOME, "qgis-auth.db"), "rb") as stream:
        check("the key is encrypted at rest", SECRET.encode() not in stream.read())
    disposable = agent_settings.store_key("x")
    agent_settings.delete_key(disposable)
    check("key deleted", disposable not in manager.configIds())
    return authcfg


def check_checkpoint(layer):
    from filter_mate.adapters.agent.turn_checkpoint import TurnCheckpoint

    checkpoint = TurnCheckpoint()
    layer.setSubsetString('"pop" = 100')
    checkpoint.begin()
    layer.setSubsetString('"pop" > 1000')
    checkpoint.begin()  # a later change of the same turn keeps the first state
    layer.setSubsetString('"pop" > 2000')
    check("commit names what changed", list(checkpoint.commit()) == ["communes"])
    restored, skipped = checkpoint.undo()
    check("undo restores the first state", layer.subsetString() == '"pop" = 100' and restored == ["communes"] and not skipped,
          (layer.subsetString(), restored, skipped))
    checkpoint.begin()
    check("a turn without change records nothing", list(checkpoint.commit()) == [])
    checkpoint.begin()
    layer.setSubsetString('"pop" > 3000')
    checkpoint.commit()
    layer.setSubsetString('"pop" > 4000')  # the user filters afterwards
    restored, skipped = checkpoint.undo()
    check("newer work is left alone", layer.subsetString() == '"pop" > 4000' and skipped == ["communes"],
          (layer.subsetString(), skipped))
    layer.setSubsetString("")
    check("the commit outside a turn is harmless", list(TurnCheckpoint().commit()) == [])
    layer.setSubsetString('"pop" = 100')
    checkpoint.begin()
    layer.setSubsetString('"pop" > 1000')
    checkpoint.commit()
    layer.startEditing()  # a layer being edited refuses a filter
    restored, left = checkpoint.undo()
    check("a layer that refuses is not reported as restored", restored == [] and left == ["communes"], (restored, left))
    check("and the turn can be tried again", checkpoint.can_undo())
    layer.rollBack()
    restored, left = checkpoint.undo()
    check("once it can be restored", layer.subsetString() == '"pop" = 100' and restored == ["communes"],
          (layer.subsetString(), restored, left))
    layer.setSubsetString("")


def check_chat(provider, layer, authcfg, work):
    from filter_mate.adapters.agent.settings import AgentSettings, load_settings, save_settings, target_of
    from filter_mate.adapters.public_api.filter_mate_public_api import FilterMatePublicAPI
    from filter_mate.ui.controllers.agent_chat_controller import AgentChatController, agent_enabled

    check("on by default", agent_enabled({}) is True and agent_enabled({"APP": {"OPTIONS": {}}}) is True)
    check("off when the user turns it off", agent_enabled({"APP": {"OPTIONS": {"AGENT": {"enabled": {"value": False}}}}}) is False)
    check("on when asked", agent_enabled({"APP": {"OPTIONS": {"AGENT": {"enabled": {"value": True}}}}}) is True)

    class Plugin:
        def get_public_api(self):
            return api

    api = FilterMatePublicAPI(None)
    save_settings(AgentSettings())  # as on a first use
    host = QToolBox()
    host.addItem(QLabel("filtering"), "FILTERING")
    answers = {"export": False}
    chat = AgentChatController(lambda page: host.insertItem(0, page, "AGENT"), Plugin(), host,
                               ask_user=lambda title, text: answers["export"])
    host.show()
    panel = chat.panel
    check("the section comes first", host.widget(0) is panel and host.itemText(0) == "AGENT")
    host.setCurrentWidget(panel)
    wait(lambda: panel.isVisible(), 2)
    check("the welcome shows first", panel.stack.currentIndex() == 0 and panel.welcome_title.isVisible())
    check("not set up: a way to set it up, no examples",
          panel.configure_button.isVisible() and not panel.example_buttons[0].isVisible())
    check("not set up: nothing can be asked yet (mockup: Welcome)", not panel.input.isEnabled()
          and not panel.send_button.isEnabled() and panel.more_button.isEnabled())
    check("nothing to undo: no button", not panel.undo_offered() and not panel.undo_button.isVisible())

    def settings(**changes):
        values = dict(preset="anthropic", model="test-model", base_url=provider.url, consent=True, authcfg=authcfg,
                      consent_target=target_of("anthropic", provider.url), key_target=target_of("anthropic", provider.url))
        values.update(changes)
        save_settings(AgentSettings(**values))
        chat._refresh_ready()  # as the settings dialog does once saved
        chat.new_conversation()

    def ask(text, seconds=10.0):
        panel.input.setText(text)
        panel.input.returnPressed.emit()
        return wait(lambda: not panel._working, seconds)

    chat.open_settings = lambda: False
    settings()
    chat._refresh_ready()
    wait(lambda: False, 0.05)
    check("set up: examples, no set-up button", panel.example_buttons[0].isVisible() and not panel.configure_button.isVisible())
    check("set up: the line takes a request", panel.input.isEnabled() and panel.send_button.isEnabled())
    check("says where requests go", "test-model" in panel.destination.text() and panel.destination.isVisible(), panel.destination.text())
    panel.example_buttons[1].click()
    check("an example fills the line", panel.input.text() == panel.example_buttons[1].text())
    panel.input.clear()
    settings(consent=False)
    chat._refresh_ready()
    provider.reset()
    ask("bonjour")
    check("nothing leaves without consent", provider.requests == [] and chat._engine is None)

    settings(model="")
    ask("bonjour")
    check("nothing leaves without a model", provider.requests == [])

    settings()
    provider.reset((200, {}, tool_turn("list_layers", {})),
                   (200, {}, tool_turn("apply_filter", {"layer_name": "communes", "expression": '"pop" > 1000'}, "toolu_2")),
                   (200, {}, text_turn("Il reste 50 communes.")))
    check("a filter request ends", ask("garde les communes de plus de 1000 habitants"))
    check("the filter is applied", layer.subsetString() == '"pop" > 1000', layer.subsetString())
    check("three model turns", len(provider.requests) == 3, len(provider.requests))
    first = provider.requests[0]["body"]["messages"][-1]["content"]
    check("the state of the project goes after the request", first[0]["text"].startswith("garde les communes")
          and len(first) == 2 and "communes" in first[1]["text"] and "Project when" in first[1]["text"], first)
    check("no change is said on a first request", "Changed in QGIS" not in first[1]["text"], first[1]["text"])
    check("the project is remembered as the answer leaves it", chat._seen is not None and
          [row["filter"] for row in chat._seen["layers"].values() if row["name"] == "communes"] == ['"pop" > 1000'],
          chat._seen)
    check("nothing changed since: nothing said", "Changed in QGIS" not in chat._project_context())
    from qgis.core import QgsCoordinateReferenceSystem as _Crs
    project_crs = QgsProject.instance().crs()
    QgsProject.instance().setCrs(_Crs("EPSG:2154"))
    check("the map goes with the layers", "\nMap: CRS EPSG:2154" in chat._project_context(), chat._project_context())
    QgsProject.instance().setCrs(project_crs)
    layer.selectByExpression('"pop" <= 1200')
    changed = chat._project_context()
    check("what the user did since the answer is said", "Changed in QGIS since your last answer" in changed
          and "- selection changed: communes (" in changed and "filter changed" not in changed, changed)
    layer.removeSelection()
    second = provider.requests[1]["body"]["messages"]
    check("the tool call goes back with its result", second[1]["content"][0]["type"] == "tool_use" and
          second[2]["content"][0]["tool_use_id"] == "toolu_1" and "communes" in second[2]["content"][0]["content"], second)
    check("the same prefix is sent each time", json.dumps(provider.requests[2]["body"]["messages"][:3]) == json.dumps(second))
    check("the answer is shown", "Il reste 50 communes." in panel.thread.toPlainText(), panel.thread.toPlainText())
    check("the question is shown", "garde les communes" in panel.thread.toPlainText())
    check("the change is reported in its card, not twice", "Filter on communes" in panel.thread.toPlainText()
          and panel.status.text() == "", (panel.status.text(), panel.thread.toPlainText()[-200:]))
    check("the input was emptied", panel.input.text() == "")
    check("undo is offered", panel.undo_offered())
    from qgis.PyQt.QtWidgets import QPushButton as _Button
    card_undo = [b for b in panel.thread.findChildren(_Button, "pushButton_agent_card_undo") if b.isVisibleTo(panel)]
    check("undo sits on the change card (mockup)", len(card_undo) == 1 and not panel.undo_button.isVisibleTo(panel), card_undo)
    check("the request is a bubble", panel.thread.findChild(QLabel, "label_agent_request") is not None)
    check("the steps give way to the cards", "Reading the layers" not in " ".join(
        label.text() for label in panel.thread.findChildren(QLabel)))
    check("the conversation replaced the welcome", panel.stack.currentIndex() == 1)
    check("the applied filter is listed with its expression", '"pop" > 1000' in panel.thread.toPlainText() and
          "✓" in panel.thread.toPlainText(), panel.thread.toPlainText())
    check("reading tools leave no line", "list layers" not in panel.thread.toPlainText().lower())
    panel.input.setFocus()
    QTest.keyClick(panel.input, Qt.Key.Key_Up)
    check("the arrow brings the request back", "garde les communes" in panel.input.text(), panel.input.text())
    panel.input.clear()
    panel.undo_button.click()
    check("undo this turn", layer.subsetString() == "", layer.subsetString())
    check("undo is reported", "communes" in panel.status.text(), panel.status.text())

    try:  # an algorithm of Processing through the chat, its layer undone with the turn
        sys.path.append("/usr/share/qgis/python/plugins")
        from processing.core.Processing import Processing
        Processing.initialize()
        processing_ready = True
    except ImportError:
        processing_ready = False
    check("processing is there", processing_ready)
    layers_before = set(QgsProject.instance().mapLayers())
    provider.reset((200, {}, tool_turn("run_algorithm", {"algorithm_id": "native:buffer",
                                                         "parameters": {"INPUT": "communes", "DISTANCE": 10}})),
                   (200, {}, text_turn("Zone faite.")))
    check("an algorithm through the chat", ask("tampon de 10 m autour des communes"))
    made = set(QgsProject.instance().mapLayers()) - layers_before
    result = provider.requests[1]["body"]["messages"][-1]["content"][0]
    check("its layer is added", len(made) == 1 and not result.get("is_error"), result)
    check("its card names the algorithm and its parameters", "Processing: native:buffer" in panel.thread.toPlainText()
          and "DISTANCE=10" in panel.thread.toPlainText(), panel.thread.toPlainText()[-300:])
    chat._on_undo()
    check("undoing the turn removes its layer", not set(QgsProject.instance().mapLayers()) - layers_before,
          set(QgsProject.instance().mapLayers()) - layers_before)

    renderer_before = layer.renderer().type()
    provider.reset((200, {}, tool_turn("set_layer_style", {"layer": "communes", "mode": "graduated", "field": "pop",
                                                           "classes": 3})),
                   (200, {}, tool_turn("set_labels", {"layer": "communes", "field": "pop"}, "toolu_2")),
                   (200, {}, text_turn("C'est fait.")))
    check("a style through the chat", ask("colore les communes par population et affiche leur nom"))
    check("the style and the labels are set", layer.renderer().type() == "graduatedSymbol" and layer.labelsEnabled(),
          (layer.renderer().type(), layer.labelsEnabled()))
    check("their cards say what changed", "graduated · pop" in panel.thread.toPlainText()
          and "Labels of communes" in panel.thread.toPlainText(), panel.thread.toPlainText()[-300:])
    chat._on_undo()
    check("undoing the turn brings the style back", layer.renderer().type() == renderer_before
          and not layer.labelsEnabled(), (layer.renderer().type(), layer.labelsEnabled()))

    from filter_mate.core.agent.compaction import SUMMARY_HEADER
    from filter_mate.core.agent.session import AgentLimits
    chat._engine._session._limits = AgentLimits(max_history_chars=2000)  # the conversation is long by now
    provider.reset((200, {}, text_turn("Bien.")))
    check("a long conversation is sent shorter", ask("et maintenant ?"))
    sent = provider.requests[0]["body"]["messages"]
    check("its oldest requests are summed up at its start", sent[0]["content"][0]["text"].startswith(SUMMARY_HEADER)
          and sent[-1]["content"][0]["text"] == "et maintenant ?", sent[0]["content"][0]["text"][:300])
    check("the thread says so", "summed up in a few lines" in panel.thread.toPlainText(), panel.thread.toPlainText()[-300:])
    chat._engine._session._limits = AgentLimits()

    provider.reset((200, {}, tool_turn("update_features", {"layer": "communes", "values": {"pop": 1},
                                                           "expression": '"pop" <= 300'})),
                   (200, {}, text_turn("Modifié, pas encore enregistré.")))
    check("an edit through the chat", ask("mets la population à 1 pour les petites communes"))
    check("it is in the edit buffer", layer.isEditable() and layer.isModified() and
          sorted(f["pop"] for f in layer.getFeatures())[:4] == [1, 1, 1, 400], sorted(f["pop"] for f in layer.getFeatures())[:4])
    check("its card says it is not saved", "(not saved)" in panel.thread.toPlainText() and "pop = 1" in
          panel.thread.toPlainText(), panel.thread.toPlainText()[-300:])
    chat._on_undo()
    check("undoing the turn takes the edit back", not layer.isModified() and
          sorted(f["pop"] for f in layer.getFeatures())[:3] == [100, 200, 300])
    was, answers["export"] = answers["export"], False  # one answer stands for every confirmation of this check
    provider.reset((200, {}, tool_turn("delete_features", {"layer": "communes", "expression": '"pop" = 100'})),
                   (200, {}, text_turn("D'accord.")))
    ask("supprime la commune de 100 habitants")
    result = provider.requests[1]["body"]["messages"][-1]["content"][0]
    check("a delete is confirmed first, and declined here", result.get("is_error") is True and "declined" in
          result["content"] and layer.featureCount() == 60, result)
    answers["export"] = was
    layer.rollBack()

    provider.reset((200, {}, tool_turn("create_layout", {"name": "Carte agent", "title": "Communes"})),
                   (200, {}, text_turn("Mise en page prête.")))
    check("a layout through the chat", ask("fais une mise en page des communes"))
    manager = QgsProject.instance().layoutManager()
    check("it is in the project", manager.layoutByName("Carte agent") is not None,
          [item.name() for item in manager.printLayouts()])
    check("its card names it", "Layout Carte agent" in panel.thread.toPlainText(), panel.thread.toPlainText()[-300:])
    was, answers["export"] = answers["export"], False
    provider.reset((200, {}, tool_turn("export_layout", {"name": "Carte agent", "format": "pdf"})),
                   (200, {}, text_turn("D'accord.")))
    ask("exporte-la en PDF")
    result = provider.requests[1]["body"]["messages"][-1]["content"][0]
    check("an export of a layout is confirmed first, and declined here", result.get("is_error") is True
          and "declined" in result["content"], result)
    answers["export"] = was
    chat._on_undo()
    check("undoing the turn removes the layout", manager.layoutByName("Carte agent") is None,
          [item.name() for item in manager.printLayouts()])

    from qgis.core import QgsCoordinateReferenceSystem as _Crs
    QgsProject.instance().setCrs(_Crs("EPSG:4326"))
    provider.reset((200, {}, tool_turn("set_project_crs", {"crs": "EPSG:2154"})), (200, {}, text_turn("Carte en Lambert-93.")))
    check("the CRS of the map through the chat", ask("passe la vue en Lambert 93"))
    check("the project is in Lambert-93", QgsProject.instance().crs().authid() == "EPSG:2154",
          QgsProject.instance().crs().authid())
    check("its card names it", "Project CRS: EPSG:2154" in panel.thread.toPlainText(), panel.thread.toPlainText()[-200:])
    chat._on_undo()
    check("undoing the turn brings the CRS back", QgsProject.instance().crs().authid() == "EPSG:4326",
          QgsProject.instance().crs().authid())

    offered = [tool.name for tool in chat.tools_and_handlers(load_settings())[0]]
    check("view_map is offered with a key of the user and shared values", "view_map" in offered, offered)
    settings(send_values=False)
    check("not when values are not shared", "view_map" not in
          [tool.name for tool in chat.tools_and_handlers(load_settings())[0]])
    settings()
    provider.reset((200, {}, tool_turn("view_map", {"layer": "communes", "width": 400})),
                   (200, {}, text_turn("Je vois les communes.")))
    check("a look at the map through the chat", ask("que montre la carte ?"))
    sent = provider.requests[1]["body"]["messages"][-1]["content"][0]
    image = sent["content"][1] if isinstance(sent.get("content"), list) and len(sent["content"]) > 1 else {}
    check("the model gets a JPEG of the map", image.get("type") == "image" and
          image.get("source", {}).get("media_type") == "image/jpeg" and len(image["source"]["data"]) > 1000,
          str(sent)[:300])
    provider.reset((200, {}, text_turn("ok")))
    ask("merci")
    check("and not again with the next request", '"type": "image"' not in json.dumps(provider.requests[0]["body"]))

    check("no Python without the expert mode", "run_pyqgis" not in
          [tool.name for tool in chat.tools_and_handlers(load_settings())[0]])
    settings(expert_python=True)
    check("the expert mode offers it", "run_pyqgis" in [tool.name for tool in chat.tools_and_handlers(load_settings())[0]])
    shown, verdict = [], {"run": False}

    def read_code(title, text, code):
        shown.append((text, code))
        return verdict["run"]
    chat._ask_code = read_code
    code = "project.writeEntry('FMcheck', 'ran', 'yes')\nprint('bonjour')\nresult = 6 * 7"
    provider.reset((200, {}, tool_turn("run_pyqgis", {"purpose": "Écrire une entrée de test", "code": code})),
                   (200, {}, text_turn("D'accord.")))
    ask("lance ce code")
    result = provider.requests[1]["body"]["messages"][-1]["content"][0]
    check("Python is shown in full and asked first; declined, nothing runs", shown and shown[-1][1] == code and
          "Écrire une entrée de test" in shown[-1][0] and result.get("is_error") is True and
          QgsProject.instance().readEntry("FMcheck", "ran", "")[0] == "", (shown[-1:], result))
    verdict["run"] = True
    provider.reset((200, {}, tool_turn("run_pyqgis", {"purpose": "Écrire une entrée de test", "code": code})),
                   (200, {}, text_turn("Fait.")))
    ask("lance-le")
    answer = json.loads(provider.requests[1]["body"]["messages"][-1]["content"][0]["content"])
    check("agreed, it runs: what it printed and its result come back", answer["ok"] and answer["printed"] == "bonjour\n"
          and answer["result"] == "42" and QgsProject.instance().readEntry("FMcheck", "ran", "")[0] == "yes", answer)
    check("its card says it is not undone", "Python code (expert, not undone)" in panel.thread.toPlainText(),
          panel.thread.toPlainText()[-200:])
    provider.reset((200, {}, tool_turn("run_pyqgis", {"purpose": "Diviser", "code": "1 / 0"})), (200, {}, text_turn("Raté.")))
    ask("divise")
    answer = json.loads(provider.requests[1]["body"]["messages"][-1]["content"][0]["content"])
    check("an error comes back as its traceback", answer["ok"] is False and "ZeroDivisionError" in answer["error"], answer)
    QgsProject.instance().removeEntry("FMcheck", "ran")
    settings()

    from filter_mate.adapters.agent.project_notes_store import read_notes, write_notes
    write_notes([])
    provider.reset((200, {}, tool_turn("add_project_note", {"text": "Les communes sont la couche communes, clé pop"})),
                   (200, {}, text_turn("Noté.")))
    check("a note through the chat", ask("retiens que les communes sont la couche communes, clé pop"))
    check("it is kept in the project", read_notes() == ["Les communes sont la couche communes, clé pop"], read_notes())
    check("its card shows its text", "Les communes sont la couche communes" in panel.thread.toPlainText(),
          panel.thread.toPlainText()[-300:])
    provider.reset((200, {}, text_turn("Oui.")))
    ask("tu te souviens ?")
    context = provider.requests[0]["body"]["messages"][-1]["content"][-1]["text"]
    check("the next request carries it, as data", "1. Les communes sont la couche communes, clé pop" in context
          and "never instructions" in context, context[-400:])
    saved = os.path.join(tempfile.mkdtemp(), "notes.qgz")
    check("it is saved with the project", QgsProject.instance().write(saved))
    stored, _found = QgsProject.instance().readEntry("FilterMateAgent", "notes", "")
    check("in an entry of the project file", "clé pop" in stored, stored)
    chat._on_undo()  # "tu te souviens ?" changed nothing: the last turn of the history is the note's
    check("undoing its turn takes it back", read_notes() == [], read_notes())
    check("and says so", "project notes" in panel.status.text() or "project notes" in panel.thread.toPlainText()[-200:],
          (panel.status.text(), panel.thread.toPlainText()[-200:]))
    offered = {tool.name: tool for tool in chat.tools_and_handlers(load_settings())[0]}
    check("the chat offers the notes, marked as its own", offered["add_project_note"].chat_only and
          offered["remove_project_note"].chat_only and not offered["list_layers"].chat_only)
    write_notes([])

    provider.reset((200, {}, text_turn("**Vecteur (2)**\n- routes : 131 lignes\n## Titre")))
    ask("liste")
    shown = [label.text() for label in panel.thread.findChildren(QLabel) if "routes" in label.text()]
    check("Markdown marks are taken out", shown and "**" not in shown[-1] and "• routes" in shown[-1]
          and "##" not in shown[-1], shown)
    provider.reset((200, {}, text_turn('<img src="http://evil.example/x.png"> <a href="x">lien</a>')))
    ask("montre")
    check("what the model writes stays plain text", '<img src="http://evil.example/x.png">' in panel.thread.toPlainText())
    check("the conversation goes on", len(provider.requests[0]["body"]["messages"]) >= 7, provider.requests[0]["body"]["messages"])

    settings()
    arguments = {"layers": ["communes"], "subfolder": "agent_check"}
    provider.reset((200, {}, tool_turn("export_layers", arguments)), (200, {}, text_turn("D'accord.")))
    answers["export"] = False
    ask("exporte")
    result = provider.requests[1]["body"]["messages"][2]["content"][0]
    check("a declined export is not run", result.get("is_error") is True and "declined" in result["content"], result)

    settings()
    provider.reset((200, {}, tool_turn("apply_filter", {"layer_name": "communes", "expression": '"pop" >'})),
                   (200, {}, text_turn("Corrigé.")))
    ask("filtre mal écrit")
    result = provider.requests[1]["body"]["messages"][2]["content"][0]
    check("an invalid filter is refused and explained", result.get("is_error") is True and "invalid" in result["content"], result)
    check("the layer stays as it was", layer.subsetString() == "", layer.subsetString())

    settings(send_values=False)
    provider.reset((200, {}, text_turn("ok")))
    ask("salut")
    names = [tool["name"] for tool in provider.requests[0]["body"]["tools"]]
    check("no attribute values when refused", "field_values" not in names and "describe_layer" in names, names)
    check("nor what reads the features", not {"layer_statistics", "sample_features", "identify_at"} & set(names), names)
    check("and the model is told", "layer_statistics, sample_features" in json.dumps(provider.requests[0]["body"]["system"]))
    settings()
    check("the reading tools are offered with the values", {"layer_statistics", "sample_features", "identify_at"}
          <= {tool.name for tool in chat.tools_and_handlers(load_settings())[0]})

    settings()
    provider.reset((401, {}, b'{"error":{"message":"invalid x-api-key"}}'))
    ask("salut")
    error_cards = panel.thread.findChildren(QFrame, "frame_agent_error")
    fix_buttons = panel.thread.findChildren(QPushButton, "pushButton_agent_error_action")
    check("a refused key says where to go, in a card of the thread (mockup)", error_cards and fix_buttons and
          "key" in panel.thread.toPlainText().splitlines()[-2].lower(), panel.thread.toPlainText()[-300:])
    settings_opened = []
    panel.settings_requested.disconnect()  # the controller's: the real settings are a modal dialog
    panel.settings_requested.connect(lambda: settings_opened.append(True))
    if fix_buttons:
        fix_buttons[-1].click()
    panel.settings_requested.disconnect()
    panel.settings_requested.connect(type(chat).open_settings.__get__(chat))
    check("its button opens the settings", settings_opened, settings_opened)
    check("the request comes back", panel.input.text() == "salut", panel.input.text())
    panel.input.clear()
    check("the panel is usable again", panel.input.isEnabled())

    settings()
    provider.reset("hang")
    panel.input.setText("longue question")
    panel.input.returnPressed.emit()
    wait(lambda: provider.requests, 3)
    check("while working, progress and stop", panel.progress.isVisible() and panel.send_button.isEnabled() and
          "Stop" in panel.send_button.toolTip())
    before = len(provider.requests)
    panel.input.setText("la suivante")
    panel.input.returnPressed.emit()
    wait(lambda: False, 0.1)
    check("the next request can be typed, not sent", len(provider.requests) == before and panel.input.text() == "la suivante")
    panel.input.clear()
    QTest.keyClick(panel.input, Qt.Key.Key_Escape)
    check("escape stops", wait(lambda: not panel._working, 3) and not panel.progress.isVisible())
    check("a stopped request comes back", panel.input.text() == "longue question", panel.input.text())
    panel.input.clear()
    provider.release.set()

    settings()
    provider.reset("hang")
    panel.input.setText("encore")
    panel.input.returnPressed.emit()
    wait(lambda: provider.requests, 3)
    chat.stop()
    check("closing the dock stops the request", wait(lambda: not panel._working, 3))
    provider.release.set()

    settings()
    provider.reset((200, {}, text_turn("un")), (200, {}, text_turn("deux")))
    ask("premier")
    QgsProject.instance().cleared.emit()
    ask("second")
    check("another project starts a new conversation", len(provider.requests[1]["body"]["messages"]) == 1,
          provider.requests[1]["body"]["messages"])
    check("no key in the conversation", SECRET not in panel.thread.toPlainText())

    # A key and a consent are for one server.
    settings(key_target="https://another.example/v1")
    provider.reset((200, {}, text_turn("non")))
    ask("salut")
    check("a key typed for another server is not sent", provider.requests == [] and panel.fix_button.isVisible(),
          [r["headers"].get("x-api-key") for r in provider.requests])
    settings(consent_target="https://another.example/v1")
    provider.reset((200, {}, text_turn("non")))
    ask("salut")
    check("a consent given for another server does not count", provider.requests == [])
    panel.input.clear()
    settings(preset="ollama", key_target=target_of("ollama", provider.url), consent_target=target_of("ollama", provider.url))
    provider.reset((200, {}, b"data: [DONE]\n\n"))
    ask("salut")
    check("a local model gets no key", provider.requests and "authorization" not in provider.requests[0]["headers"],
          provider.requests)
    panel.input.clear()

    from filter_mate.ui.widgets.agent_panel import AgentSettingsDialog
    values = load_settings()
    stored = AgentSettings(preset="anthropic", model="m", consent=True, authcfg=authcfg,
                           consent_target=target_of("anthropic", ""), key_target=target_of("anthropic", ""))
    dialog = AgentSettingsDialog(stored, target_of)
    dialog.show()
    wait(lambda: False, 0.05)
    check("settings: agreed for this provider", dialog.consent.isChecked() and dialog.forget_button.isVisible())
    dialog.preset.setCurrentIndex(dialog.preset.findData("mistral"))
    check("settings: another provider starts without consent nor key",
          not dialog.consent.isChecked() and not dialog.forget_button.isVisible() and dialog.key.placeholderText() == "")
    dialog.preset.setCurrentIndex(dialog.preset.findData("anthropic"))
    check("settings: back again", dialog.consent.isChecked())
    dialog.base_url.setText("https://relay.example.org")
    check("settings: another address starts without consent", not dialog.consent.isChecked())
    dialog.base_url.clear()
    dialog.preset.setCurrentIndex(dialog.preset.findData("ollama"))
    check("settings: a local model has no key field", not dialog.key.isVisible())
    dialog.close()
    save_settings(values)

    # Rich text never reaches a label, whatever a provider or a model writes.
    panel.set_status('<img src="file:///etc/passwd">', error=True)
    check("status is plain text", panel.status.textFormat() == Qt.TextFormat.PlainText)
    panel.set_status("")

    # --- history: list, redo, resend, transcript kept per project
    settings()
    layer.setSubsetString("")
    provider.reset((200, {}, tool_turn("apply_filter", {"layer_name": "communes", "expression": '"pop" > 2000'})),
                   (200, {}, text_turn("40 communes.")))
    ask("plus de 2000")
    turns = chat._checkpoint.turns()
    check("history: the turn is listed with its request", turns and turns[-1]["request"] == "plus de 2000" and
          turns[-1]["layers"] == ["communes"] and turns[-1]["applied"], turns)
    panel.history_action.trigger()
    check("history: the page shows", panel.history_shown and panel.history_list.count() == len(turns))
    check("history: undo offered, redo not", panel.history_undo_button.isEnabled() and not panel.history_redo_button.isEnabled())
    panel.history_undo_button.click()
    check("history: undone", layer.subsetString() == "" and not chat._checkpoint.turns()[-1]["applied"], layer.subsetString())
    check("history: redo offered", panel.history_redo_button.isEnabled())
    panel.history_redo_button.click()
    check("history: redone", layer.subsetString() == '"pop" > 2000', layer.subsetString())
    panel.history_list.setCurrentRow(panel.history_list.count() - 1)
    check("history: send again offered", panel.resend_button.isEnabled())
    provider.reset((200, {}, text_turn("encore")))
    panel.resend_button.click()
    check("history: sent again", wait(lambda: not panel._working, 5) and provider.requests and
          provider.requests[0]["body"]["messages"][-1]["content"][0]["text"] == "plus de 2000", provider.requests)
    check("history: back on the thread", not panel.history_shown)
    panel.back_button.click()
    layer.setSubsetString("")

    # Transcript: the project is saved, so what was shown comes back; the model starts afresh.
    project_path = os.path.join(work, "p.qgz")
    QgsProject.instance().setFileName(project_path)
    chat._restore_transcript()
    provider.reset((200, {}, text_turn("bonjour à toi")))
    ask("bonjour")
    before = panel.thread.toPlainText()
    from filter_mate.adapters.agent.transcript_store import project_key
    check("transcript: kept for the project", "bonjour à toi" in str(QgsSettings().value(
        "filter_mate/agent/transcripts/" + project_key(), "")))
    chat._restore_transcript()
    after = panel.thread.toPlainText()
    check("transcript: shown again", "bonjour" in after and "bonjour à toi" in after and "afresh" in after, after)
    check("transcript: no answer written twice", after.count("bonjour à toi") == 1, after)
    provider.reset((200, {}, text_turn("x")))
    ask("suite")
    check("transcript: the model does not get it back", len(provider.requests[0]["body"]["messages"]) == 1,
          provider.requests[0]["body"]["messages"])

    provider.reset((401, {}, b'{"error":{"message":"invalid x-api-key"}}'))
    ask("sans réponse")
    check("transcript: a failure adds no answer", chat._transcript[-1]["kind"] == "user", chat._transcript[-1])
    panel.input.clear()

    key = project_key()
    QgsProject.instance().cleared.emit()
    check("cleared: the conversation lets go of the project", chat._transcript_key == "" and chat._transcript == [])
    provider.reset((200, {}, text_turn("sans projet")))
    ask("projet vierge")
    check("cleared: nothing written to the former project", "projet vierge" not in str(QgsSettings().value(
        "filter_mate/agent/transcripts/" + key, "")))
    other_path = os.path.join(work, "other.qgz")
    QgsProject.instance().setFileName(other_path)
    check("first save: the conversation follows", "projet vierge" in str(QgsSettings().value(
        "filter_mate/agent/transcripts/" + project_key(), "")))
    chat.new_conversation()
    check("new conversation: forgotten for good", panel.thread.toPlainText() == "" and not str(QgsSettings().value(
        "filter_mate/agent/transcripts/" + project_key(), "")))
    settings()
    QgsProject.instance().setFileName("")
    QgsSettings().remove("filter_mate/agent/transcripts")

    # Open data: off by default, the tool is not offered and no remote layer is read.
    settings()
    provider.reset((200, {}, text_turn("ok")))
    ask("salut")
    names = [tool["name"] for tool in provider.requests[0]["body"]["tools"]]
    check("open data off: no search tool", "search_open_data" not in names and "add_layer" in names, names)
    provider.reset((200, {}, tool_turn("add_layer", {"source": "https://example.org/a.geojson"})), (200, {}, text_turn("ok")))
    answers["export"] = True
    ask("ajoute")
    result = provider.requests[1]["body"]["messages"][-1]["content"][0]
    check("open data off: a remote layer is refused", result.get("is_error") is True and "open data" in result["content"], result)
    settings(enabled_sources=("datagouv",))
    provider.reset((200, {}, text_turn("ok")))
    ask("salut")
    names = [tool["name"] for tool in provider.requests[0]["body"]["tools"]]
    check("open data on: the search tool is offered", "search_open_data" in names)
    asked = []
    chat._ask_user = lambda title, text: asked.append(text) or False
    provider.reset((200, {}, tool_turn("add_layer", {"source": "https://example.org/a.geojson"})), (200, {}, text_turn("ok")))
    ask("ajoute")
    check("open data on: adding a layer asks the user", asked and "example.org" in asked[0], asked)
    result = provider.requests[1]["body"]["messages"][-1]["content"][0]
    check("declined: nothing added", result.get("is_error") is True and "declined" in result["content"], result)
    provider.reset((200, {}, tool_turn("remove_layers", {"layers": ["communes"]})), (200, {}, text_turn("ok")))
    ask("retire")
    check("removing layers asks the user", len(asked) == 2 and "communes" in asked[1] and layer.isValid(), asked)
    chat._ask_user = lambda title, text: answers["export"]

    # --- MCP connectors and the Sources tab, against a server on this machine
    from filter_mate.core.agent.mcp_client import tool_name
    from filter_mate.core.agent.sources import custom_to_json, make_source
    from filter_mate.ui.widgets.agent_panel import AgentSettingsDialog as Dialog

    mcp_seen = []

    class Mcp(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            method = body.get("method")
            mcp_seen.append((method, self.headers.get("Mcp-Session-Id"), body.get("params")))
            if "id" not in body:
                self.send_response(202)
                self.end_headers()
                return
            result = {"initialize": {"protocolVersion": "2025-06-18", "capabilities": {}, "serverInfo": {"name": "x"}},
                      "tools/list": {"tools": [
                          {"name": "hello", "description": "Says hello", "annotations": {"readOnlyHint": True},
                           "inputSchema": {"type": "object", "properties": {"who": {"type": "string"}}, "required": ["who"]}},
                          {"name": "change", "description": "Changes", "inputSchema": {"type": "object", "properties": {}}}]},
                      "tools/call": {"content": [{"type": "text", "text": "Bonjour " + str((body.get("params") or {}).get("arguments"))}]}}[method]
            data = ("event: message\ndata: " + json.dumps({"jsonrpc": "2.0", "id": body["id"], "result": result}) + "\n\n").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            if method == "initialize":
                self.send_header("Mcp-Session-Id", "sess-1")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Mcp)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    source = make_source(f"http://127.0.0.1:{server.server_address[1]}/mcp", "mcp", "Local")
    hello = tool_name(source.id, "hello")
    settings(enabled_sources=(source.id,), custom_sources=custom_to_json([source]))
    provider.reset((200, {}, tool_turn(hello, {"who": "QGIS"})), (200, {}, text_turn("ok")))
    ask("dis bonjour")
    names = [tool["name"] for tool in provider.requests[0]["body"]["tools"]]
    check("connector: its tools are offered", hello in names and tool_name(source.id, "change") in names, names)
    result = provider.requests[1]["body"]["messages"][2]["content"][0]
    check("connector: the call is answered", not result.get("is_error") and "Bonjour" in result["content"] and "QGIS" in result["content"], result)
    check("connector: the session is kept", mcp_seen[-1][0] == "tools/call" and mcp_seen[-1][1] == "sess-1" and
          mcp_seen[-1][2]["name"] == "hello", mcp_seen[-1])
    check("connector: the call stays in the thread", "Local: hello" in panel.thread.toPlainText(), panel.thread.toPlainText())
    asked.clear()
    chat._ask_user = lambda title, text: asked.append(text) or False
    provider.reset((200, {}, tool_turn(tool_name(source.id, "change"), {})), (200, {}, text_turn("ok")))
    calls_before = sum(1 for item in mcp_seen if item[0] == "tools/call")
    ask("change")
    check("connector: a call not declared read-only asks first", asked and "Local" in asked[0] and
          sum(1 for item in mcp_seen if item[0] == "tools/call") == calls_before, asked)
    chat._ask_user = lambda title, text: answers["export"]
    server.shutdown()
    server.server_close()
    dead = make_source("http://127.0.0.1:9/mcp", "mcp", "Dead")
    settings(enabled_sources=(dead.id,), custom_sources=custom_to_json([dead]))
    provider.reset((200, {}, text_turn("sans connecteur")))
    ask("salut")
    check("connector: one that does not answer does not stop the chat", provider.requests and "Dead" in panel.thread.toPlainText(),
          panel.thread.toPlainText())

    check_hostile_connector()
    settings(enabled_sources=("datagouv_mcp",))
    chat._add_connectors = lambda active, tools, handlers: []
    provider.reset((200, {}, tool_turn("add_layer", {"source": "https://example.org/a.geojson"})), (200, {}, text_turn("ok")))
    answers["export"] = True
    ask("ajoute")
    result = provider.requests[1]["body"]["messages"][2]["content"][0]
    check("a connector alone does not open the web to add_layer", result.get("is_error") is True and "open data" in result["content"], result)
    del chat._add_connectors

    values = AgentSettings(preset="anthropic", model="m", enabled_sources=("ign_wfs",), custom_sources=custom_to_json([source]))
    tested = []
    dialog = Dialog(values, target_of, None, tester=lambda item: tested.append(item.id) or "12 tools")
    dialog.show()
    wait(lambda: False, 0.05)
    check("sources: nothing but what was ticked", dialog.chosen_sources() == ("ign_wfs",), dialog.chosen_sources())
    dialog.new_address.setText("http://evil.example.org/mcp")
    dialog.new_kind.setCurrentIndex(dialog.new_kind.findData("mcp"))
    dialog.add_button.click()
    check("sources: an address in clear is refused", "https" in dialog.source_result.text(), dialog.source_result.text())
    dialog.new_address.setText("https://mcp.example.org/mcp")
    dialog.add_button.click()
    check("sources: a connector can be added, ticked", make_source("https://mcp.example.org/mcp", "mcp").id in dialog.chosen_sources(), dialog.chosen_sources())
    check("sources: kept as JSON", "mcp.example.org" in dialog.chosen_custom_sources())
    tree = dialog.sources_tree
    group = next(tree.topLevelItem(i) for i in range(tree.topLevelItemCount()) if tree.topLevelItem(i).childCount() and
                 "mcp" in str(tree.topLevelItem(i).child(0).data(0, 256)).lower())
    tree.setCurrentItem(group.child(0))
    dialog.test_button.click()
    check("sources: test shows the answer", dialog.source_result.text() == "12 tools" and len(tested) == 1, dialog.source_result.text())
    dialog.close()
    check_steps(chat, provider, settings, ask, layer)
    check_autonomy(chat, provider, settings, ask, answers, layer)
    check_free_quota(chat, provider, settings, ask)
    check_native_mcp(chat, settings, answers, layer)
    host.close()


def check_autonomy(chat, provider, settings, ask, answers, layer):
    """Levels of autonomy: what runs alone, what is asked, what is refused, and "yes for this conversation"."""
    from filter_mate.core.agent.permissions import ADVISOR_REFUSAL
    from filter_mate.ui.widgets.agent_panel import ANSWER_CONVERSATION, ANSWER_NO, AgentSettingsDialog
    from filter_mate.adapters.agent.settings import load_settings, target_of

    panel = chat.panel
    dialog = AgentSettingsDialog(load_settings(), target_of)
    check("autonomy: a tab, standard by default", dialog.chosen_autonomy() == "standard" and
          any(dialog.tabs.tabText(i) == "Autonomy" for i in range(dialog.tabs.count())))
    dialog.findChild(QWidget, "radioButton_agent_autonomy_advisor").setChecked(True)
    check("autonomy: the level chosen is read back", dialog.chosen_autonomy() == "advisor")
    dialog.close()

    filter_call = {"layer_name": "communes", "expression": '"pop" > 1000'}
    layer.setSubsetString("")
    settings(autonomy="advisor")
    shown = lambda: chat._header_label.text() if chat._header_label is not None else panel.destination.text()  # noqa: E731
    check("advisor: shown next to the model", "Advisor" in shown(), shown())
    asked = []
    chat._ask_user = lambda title, text: asked.append(text) or True
    provider.reset((200, {}, tool_turn("apply_filter", filter_call)), (200, {}, text_turn("je vous explique")))
    ask("filtre")
    result = provider.requests[1]["body"]["messages"][-1]["content"][0]
    check("advisor: a filter is refused, nobody asked", result.get("is_error") is True and
          result["content"] == ADVISOR_REFUSAL and not asked and layer.subsetString() == "", (result, asked))
    sent = json.dumps(provider.requests[0]["body"]["messages"][-1], ensure_ascii=False)
    check("advisor: the model is told the level", "advisor" in sent, sent[-400:])

    settings(autonomy="careful")
    provider.reset((200, {}, tool_turn("apply_filter", filter_call)), (200, {}, text_turn("ok")))
    asked.clear()
    chat._ask_user = lambda title, text: asked.append(text) or False
    ask("filtre")
    check("careful: a filter is asked first, with what it does", asked and "communes" in asked[0] and
          layer.subsetString() == "", asked)

    choices = []
    chat._ask_choice = lambda title, text: choices.append(text) or ANSWER_CONVERSATION
    provider.reset((200, {}, tool_turn("apply_filter", filter_call)), (200, {}, text_turn("ok")))
    ask("filtre")
    check("careful: yes for this conversation applies it", len(choices) == 1 and
          layer.subsetString() == '"pop" > 1000', (choices, layer.subsetString()))
    provider.reset((200, {}, tool_turn("apply_filter", {"layer_name": "communes", "expression": '"pop" > 2000'})),
                   (200, {}, text_turn("ok")))
    ask("encore")
    check("careful: not asked again in the conversation", len(choices) == 1 and
          layer.subsetString() == '"pop" > 2000', (choices, layer.subsetString()))
    chat.new_conversation()
    provider.reset((200, {}, tool_turn("apply_filter", filter_call)), (200, {}, text_turn("ok")))
    chat._ask_choice = lambda title, text: choices.append(text) or ANSWER_NO
    ask("filtre")
    check("careful: asked again in a new conversation", len(choices) == 2 and layer.subsetString() == '"pop" > 2000',
          (choices, layer.subsetString()))
    chat._ask_choice = lambda title, text: "once" if chat._ask_user(title, text) else "no"
    chat._ask_user = lambda title, text: answers["export"]
    layer.setSubsetString("")
    settings()
    check("standard: nothing shown next to the model", "Standard" not in shown() and "test-model" in shown(), shown())
    panel.clear_thread()


def check_steps(chat, provider, settings, ask, layer):
    """Lot 2 of the undo plan: the steps of a turn, and "undo back to here"."""
    panel = chat.panel
    settings()
    layer.setSubsetString("")
    provider.reset((200, {}, tool_turn("apply_filter", {"layer_name": "communes", "expression": '"pop" > 1000'}, "toolu_a")),
                   (200, {}, tool_turn("apply_filter", {"layer_name": "communes", "expression": '"pop" > 2000'}, "toolu_b")),
                   (200, {}, text_turn("Deux filtres.")))
    ask("deux filtres")
    turns = [turn for turn in chat._checkpoint.turns() if turn.get("applied")]
    steps = turns[-1].get("steps", []) if turns else []
    check("steps: a turn of two changes keeps both", len(steps) == 2 and all("communes" in label for label in steps), steps)
    chat._show_history()
    items = [panel.history_list.item(index) for index in range(panel.history_list.count())]
    step_items = [item for item in items if item.data(Qt.ItemDataRole.UserRole + 1) is not None]
    check("steps: listed under the last request", len(step_items) == 2, [item.text() for item in items])
    panel.history_list.setCurrentItem(step_items[1])
    check("steps: undo back to here is offered on a step, send again is not", panel.step_button.isEnabled()
          and not panel.resend_button.isEnabled())
    panel.step_button.click()
    check("steps: back to before the second step", layer.subsetString() == '"pop" > 1000', layer.subsetString())
    chat._on_undo()
    check("steps: that is a step of the history too", layer.subsetString() == '"pop" > 2000', layer.subsetString())
    chat._on_undo()
    check("steps: and the turn still undoes whole", layer.subsetString() == "", layer.subsetString())
    panel.show_thread()

    # Lot 4: "undo what you just did" in the conversation.
    settings()
    provider.reset((200, {}, tool_turn("apply_filter", {"layer_name": "communes", "expression": '"pop" > 3000'}, "toolu_c")),
                   (200, {}, text_turn("Filtré.")))
    ask("filtre")
    check("undo tool: the filter is there", layer.subsetString() == '"pop" > 3000', layer.subsetString())
    provider.reset((200, {}, tool_turn("undo_agent_step", {}, "toolu_d")), (200, {}, text_turn("Annulé.")))
    ask("annule ce que tu viens de faire")
    check("undo tool: the last request is undone from the conversation", layer.subsetString() == "", layer.subsetString())
    answer = provider.requests[1]["body"]["messages"][-1]["content"][0]
    check("undo tool: the model is told what it undid", "filtre" in answer.get("content", "") and not answer.get("is_error"),
          answer)
    check("undo tool: the thread says it, no card to undo again", "Undone: filtre" in panel.thread.toPlainText(),
          panel.thread.toPlainText()[-200:])
    chat._on_redo()
    check("undo tool: the request undone can be redone", layer.subsetString() == '"pop" > 3000', layer.subsetString())
    provider.reset((200, {}, tool_turn("apply_filter", {"layer_name": "communes", "expression": '"pop" > 10'}, "toolu_e")),
                   (200, {}, tool_turn("undo_agent_step", {}, "toolu_f")), (200, {}, text_turn("Non.")))
    ask("filtre puis annule")
    refused = provider.requests[2]["body"]["messages"][-1]["content"][0]
    check("undo tool: refused after a change of the same request", refused.get("is_error") is True, refused)
    chat._on_undo()
    chat._on_undo()
    layer.setSubsetString("")


def check_free_quota(chat, provider, settings, ask):
    """The relay that offers free requests, with a fake of it: no model is called."""
    from filter_mate.adapters.agent import free_quota
    from filter_mate.adapters.agent.settings import AgentSettings, provider_config, target_of
    from filter_mate.config import config
    from filter_mate.core.agent.providers import FREE_MODEL, FREE_PRESET
    from filter_mate.ui.widgets.agent_panel import AgentSettingsDialog

    panel = chat.panel
    agent = config.ENV_VARS.setdefault("CONFIG_DATA", {}).setdefault("APP", {}).setdefault("OPTIONS", {}).setdefault("AGENT", {})
    from filter_mate.adapters.agent import settings as settings_module
    released = settings_module.FREE_QUOTA_URL
    check("free: the release points to an https relay", released.startswith("https://"), released)
    settings_module.FREE_QUOTA_URL = ""  # the fake relay only: these checks must never reach the real one

    dialog = AgentSettingsDialog(AgentSettings(), target_of, None, free_available=False)
    check("free: not offered without a relay", dialog.preset.findData(FREE_PRESET) == -1)
    dialog.close()
    try:
        provider_config(AgentSettings(preset=FREE_PRESET, model=FREE_MODEL), "fmq1.x.y")
        check("free: no relay, no request to the official API", False)
    except ValueError:
        check("free: no relay, no request to the official API", True)

    agent["free_quota_url"] = {"value": provider.url + "/"}
    dialog = AgentSettingsDialog(AgentSettings(), target_of, None, free_available=True)
    dialog.show()
    check("free: offered first, chosen on a first use", dialog.preset.itemData(0) == FREE_PRESET and dialog.chosen_preset() == FREE_PRESET)
    check("free: no key, no model, no address to fill", not dialog.key.isVisible() and not dialog.model.isVisible() and not dialog.base_url.isVisible())
    check("free: it says what it is", dialog.free_notice.isVisible())
    check("free: its model", dialog.chosen_model() == FREE_MODEL)
    check("free: the consent is for the relay", dialog.chosen_target() == provider.url, dialog.chosen_target())
    dialog.preset.setCurrentIndex(dialog.preset.findData("anthropic"))
    check("free: the other providers come back", dialog.key.isVisible() and dialog.model.isVisible() and not dialog.free_notice.isVisible())
    dialog.close()

    def use_free():
        settings(preset=FREE_PRESET, model=FREE_MODEL, base_url="https://not-this-one.example.org", authcfg="", key_target="",
                 consent_target=target_of(FREE_PRESET, ""))

    free_quota.forget_token()
    use_free()
    token = "fmq1.abc.def"
    provider.reset((200, {}, json.dumps({"token": token}).encode()), (200, {}, text_turn("free answer")))
    ask("bonjour")
    check("free: a token is asked for once", [item["path"] for item in provider.requests] == ["/v1/register", "/v1/messages"], [item["path"] for item in provider.requests])
    check("free: the token goes with the request", provider.requests[1]["headers"].get("x-api-key") == token)
    check("free: the answer shows", "free answer" in panel.thread.toPlainText())

    use_free()
    provider.reset((200, {}, text_turn("again")))
    ask("encore")
    check("free: the token is kept", [item["path"] for item in provider.requests] == ["/v1/messages"], [item["path"] for item in provider.requests])

    use_free()
    provider.reset((402, {}, json.dumps({"type": "error", "error": {"type": "insufficient_quota", "message": "used up"}}).encode()))
    ask("encore")
    check("free: used up, it says what to do", "own API key" in panel.thread.toPlainText()[-400:], panel.thread.toPlainText()[-400:])
    check("free: the request comes back in the line", panel.input.text() == "encore", panel.input.text())
    panel.input.clear()

    use_free()
    provider.reset((401, {}, b'{"error":{"type":"authentication_error","message":"Invalid access token."}}'))
    ask("encore")
    panel.input.clear()
    provider.reset((200, {}, json.dumps({"token": "fmq1.new.one"}).encode()), (200, {}, text_turn("renewed")))
    ask("encore")
    check("free: an unknown token is replaced", [item["path"] for item in provider.requests] == ["/v1/register", "/v1/messages"]
          and provider.requests[1]["headers"].get("x-api-key") == "fmq1.new.one", [item["path"] for item in provider.requests])

    free_quota.forget_token()
    use_free()
    provider.reset((429, {}, b"{}"))
    ask("encore")
    check("free: refused an account, no request follows", [item["path"] for item in provider.requests] == ["/v1/register"], provider.requests)
    panel.input.clear()
    free_quota.forget_token()
    use_free()
    provider.reset((200, {}, b'{"token": "sk-not-ours"}'))
    ask("encore")
    check("free: a strange answer is not kept", [item["path"] for item in provider.requests] == ["/v1/register"] and not QgsSettings().value("filter_mate/agent/free_token", ""))
    panel.input.clear()

    agent["free_quota_url"] = {"value": ""}
    provider.reset()
    use_free()
    ask("encore")
    check("free: the relay removed, nothing is sent", provider.requests == [] and chat._engine is None, provider.requests)
    panel.input.clear()
    settings()
    settings_module.FREE_QUOTA_URL = released


def check_native_mcp(chat, settings, answers, layer):
    """Another application, over a real socket, under the rules of the chat."""
    from http.client import HTTPConnection
    import socket as raw_socket

    from filter_mate.adapters.agent import native_mcp
    from filter_mate.adapters.agent.settings import AgentSettings, load_settings
    from filter_mate.ui.widgets.agent_panel import AgentSettingsDialog
    from filter_mate.adapters.agent.settings import target_of

    from filter_mate.filtermate_api.config import _default_export_root

    def export_files():
        root = _default_export_root()
        return (path for path in root.rglob("*") if path.is_file()) if root.exists() else ()

    panel = chat.panel
    TOKEN = "local-token-0123456789"
    probe = raw_socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    check("mcp: off by default", not chat._mcp.listening and load_settings().mcp_enabled is False)
    settings(mcp_enabled=True, mcp_port=port, mcp_token=TOKEN)
    chat._sync_mcp()
    check("mcp: listens once turned on", chat._mcp.listening, chat._mcp.error)
    chat._refresh_ready()

    def http(method="POST", body=b"", headers=None, path="/mcp"):
        """A real client, on another thread: the server is on this one and must keep running."""
        answer = {}

        def run():
            try:
                connection = http_client(port)
                connection.request(method, path, body=body, headers=headers or {})
                reply = connection.getresponse()
                answer.update(status=reply.status, headers={k.lower(): v for k, v in reply.getheaders()}, body=reply.read())
                connection.close()
            except Exception as exc:  # the check reads it
                answer.update(status=0, headers={}, body=str(exc).encode())
        threading.Thread(target=run, daemon=True).start()
        wait(lambda: "status" in answer, 15)
        return answer

    def http_client(number):
        return HTTPConnection("127.0.0.1", number, timeout=12)

    def auth(session=None):
        headers = {"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if session:
            headers["Mcp-Session-Id"] = session
        return headers

    next_id = [0]

    def rpc(method, params=None, session=None):
        next_id[0] += 1
        return http(body=json.dumps({"jsonrpc": "2.0", "id": next_id[0], "method": method, "params": params or {}}).encode(), headers=auth(session))

    check("mcp: no token, no answer", http(body=b"{}", headers={"Content-Type": "application/json"})["status"] == 401)
    check("mcp: a foreign host is refused", http(body=b"{}", headers={**auth(), "Host": "evil.example.org"})["status"] == 403)
    check("mcp: a foreign page is refused", http(body=b"{}", headers={**auth(), "Origin": "https://evil.example.org"})["status"] == 403)
    check("mcp: elsewhere is not found", http(body=b"{}", headers=auth(), path="/admin")["status"] == 404)
    check("mcp: no stream", http("GET", headers=auth())["status"] == 405)

    opened = rpc("initialize", {"protocolVersion": "2025-06-18", "clientInfo": {"name": "Test Client"}})
    session = opened["headers"].get("mcp-session-id")
    check("mcp: a session is given", opened["status"] == 200 and session and json.loads(opened["body"])["result"]["serverInfo"]["name"] == "filtermate", opened)
    check("mcp: a notification has no answer", http(body=json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}).encode(), headers=auth(session))["status"] == 202)
    listed = json.loads(rpc("tools/list", session=session)["body"])["result"]["tools"]
    names = {tool["name"] for tool in listed}
    check("mcp: the tools of the chat", {"list_layers", "apply_filter", "export_layers"} <= names and "undo_filter" not in names, sorted(names))
    check("mcp: the ticks apply", "search_imagery" not in names and "add_service_layer" not in names, sorted(names))
    check("mcp: it says what is read-only", next(t for t in listed if t["name"] == "list_layers")["annotations"]["readOnlyHint"] is True)

    def tool(name, arguments=None):
        return json.loads(rpc("tools/call", {"name": name, "arguments": arguments or {}}, session)["body"])["result"]

    check("mcp: reads the project", "communes" in tool("list_layers")["content"][0]["text"])
    check("mcp: a read leaves no line", "Test Client" not in panel.thread.toPlainText())

    layer.setSubsetString("")
    done = tool("apply_filter", {"layer_name": "communes", "expression": '"pop" > 5000'})
    check("mcp: filters at once", done["isError"] is False and layer.subsetString() == '"pop" > 5000', (done, layer.subsetString()))
    check("mcp: the thread says who", "Test Client: " in panel.thread.toPlainText(), panel.thread.toPlainText()[-200:])
    check("mcp: the history has it", any("Test Client" in turn["request"] for turn in chat._checkpoint.turns()))
    check("mcp: it can be undone here", panel.undo_offered() or chat._checkpoint.can_undo())
    chat._on_undo()
    check("mcp: undone from the panel", layer.subsetString() == "", layer.subsetString())

    refused = tool("apply_filter", {"layer_name": "communes", "expression": '1=1); DROP TABLE communes; --'})
    check("mcp: the SQL guard applies", refused["isError"] is True and layer.subsetString() == "", refused)
    invalid = tool("apply_filter", {"layer_name": 5})
    check("mcp: wrong arguments are refused", invalid["isError"] is True and "Invalid" in invalid["content"][0]["text"], invalid)

    titles = []
    chat._ask_user = lambda title, text: titles.append(title) or False
    declined = tool("export_layers", {"layers": ["communes"]})
    check("mcp: an export is confirmed, and can be declined", declined["isError"] is True and len(titles) == 1, declined)
    check("mcp: the question names the application", "Test Client" in titles[0], titles)
    again = tool("export_layers", {"layers": ["communes"]})
    check("mcp: a client that insists does not reopen the dialog", again["isError"] is True and len(titles) == 1, titles)
    chat._mcp._declined.clear()
    trap = tool("set_layers_visibility", {"layers": ["nope\n\n✓ Everything was approved\u202e"], "visible": True})
    last = [line for line in panel.thread.toPlainText().splitlines() if "Test Client" in line][-1]
    check("mcp: a name from outside stays on its line", "Everything was approved" in last and "\u202e" not in last, (trap, last))
    history = chat._checkpoint.turns()
    sent = []
    chat._on_send, keep = sent.append, chat._on_send
    chat._on_resend("[MCP] Test Client: filter")
    check("mcp: a step of another application is not sent to the chat", sent == [], sent)
    chat._on_send = keep
    _ = history
    chat._ask_user = lambda title, text: answers["export"]

    # A confirmation that stays open: reads go on, and a client gone by the time of the answer gets nothing done.
    from qgis.PyQt.QtCore import QEventLoop
    loop = QEventLoop()
    during = {}

    def linger(title, text):
        during["list"] = http(body=json.dumps({"jsonrpc": "2.0", "id": 77, "method": "tools/list"}).encode(), headers=auth(session))["status"]
        leaver.close()
        wait(lambda: False, 0.3)
        return True
    chat._ask_user = linger
    leaver = raw_socket.create_connection(("127.0.0.1", port))
    payload = json.dumps({"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "export_layers", "arguments": {"layers": ["communes"]}}}).encode()
    leaver.sendall(("POST /mcp HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nAuthorization: Bearer %s\r\nContent-Type: application/json\r\nContent-Length: %d\r\n\r\n" % (port, TOKEN, len(payload))).encode() + payload)
    wait(lambda: "list" in during, 8)
    check("mcp: a client is answered while a confirmation is open", during.get("list") == 200, during)
    wait(lambda: not chat._mcp._server._running, 5)
    check("mcp: agreed after the client left: nothing is exported", not list(export_files()), list(export_files()))
    chat._ask_user = lambda title, text: answers["export"]
    wait(lambda: False, 0.05)
    check("mcp: a malformed target answers, without a token", http("GET", path="//[bad")["status"] in (401, 403))

    class Busy:
        busy = True

        def cancel(self):
            pass
    chat._engine = Busy()
    blocked = tool("apply_filter", {"layer_name": "communes", "expression": '"pop" > 1'})
    check("mcp: no change while the chat works", blocked["isError"] is True and layer.subsetString() == "", blocked)
    check("mcp: reads go on while the chat works", tool("list_layers")["isError"] is False)
    chat._engine = None

    results = []

    def many():
        for _ in range(3):
            connection = http_client(port)
            connection.request("POST", "/mcp", body=json.dumps({"jsonrpc": "2.0", "id": 9, "method": "tools/list"}), headers=auth(session))
            results.append(connection.getresponse().status)
            connection.close()
    workers = [threading.Thread(target=many, daemon=True) for _ in range(4)]
    for worker in workers:
        worker.start()
    wait(lambda: len(results) == 12, 15)
    check("mcp: clients at the same time are all answered", results == [200] * 12, results)

    native_mcp.RECEIVE_TIMEOUT_MS = 200
    slow = raw_socket.create_connection(("127.0.0.1", port))
    slow.settimeout(5)
    slow.sendall(b"POST /mcp HTTP/1.1\r\nHost: x")
    chunks = []

    def drain():
        try:
            chunks.append(slow.recv(200))
        except OSError:
            chunks.append(b"")
    threading.Thread(target=drain, daemon=True).start()
    check("mcp: a client that never finishes is cut", wait(lambda: chunks, 4) and b"408" in chunks[0], chunks)
    slow.close()
    native_mcp.RECEIVE_TIMEOUT_MS = 5000
    idle = [raw_socket.create_connection(("127.0.0.1", port)) for _ in range(native_mcp.MAX_CONNECTIONS)]
    wait(lambda: False, 0.1)
    check("mcp: idle sockets do not lock clients out", tool("list_layers")["isError"] is False)
    for item in idle:
        item.close()
    wait(lambda: False, 0.1)

    gone = raw_socket.create_connection(("127.0.0.1", port))
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode()
    gone.sendall(("POST /mcp HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nAuthorization: Bearer %s\r\nContent-Type: application/json\r\nContent-Length: %d\r\n\r\n" % (port, TOKEN, len(payload))).encode() + payload)
    gone.close()
    wait(lambda: False, 0.1)
    check("mcp: a client that leaves does not matter", tool("list_layers")["isError"] is False)

    other = raw_socket.socket()
    other.setsockopt(raw_socket.SOL_SOCKET, raw_socket.SO_REUSEADDR, 1)
    other.bind(("127.0.0.1", 0))
    other.listen(1)
    taken = other.getsockname()[1]
    settings(mcp_enabled=True, mcp_port=taken, mcp_token=TOKEN)
    chat._sync_mcp()
    check("mcp: a port already taken is said", chat._mcp.error and not chat._mcp.listening, chat._mcp.error)
    other.close()

    values = load_settings()
    dialog = AgentSettingsDialog(values, target_of, None)
    check("mcp: the tab shows the state", dialog.mcp_enabled.isChecked() and dialog.mcp_port.value() == taken)
    dialog.copy_config_button.click()
    from qgis.PyQt.QtWidgets import QApplication
    check("mcp: the configuration is copied", TOKEN in QApplication.clipboard().text() and str(taken) in QApplication.clipboard().text())
    dialog.copy_desktop_button.click()
    check("mcp: the Claude Desktop entry is copied", '"mcp-remote"' in QApplication.clipboard().text() and TOKEN in QApplication.clipboard().text())
    dialog.copy_command_button.click()
    check("mcp: the command is copied", QApplication.clipboard().text().startswith("claude mcp add --transport http"))
    dialog.new_token_button.click()
    check("mcp: a new token", dialog.chosen_mcp_token() != TOKEN)
    dialog.close()
    check("mcp: the token stays out of a repr", TOKEN not in repr(values))
    check("mcp: first use gets a token", _first_token(AgentSettingsDialog, target_of, AgentSettings))

    settings(mcp_enabled=True, mcp_port=port, mcp_token=TOKEN)
    chat._sync_mcp()
    check("mcp: comes back on another port", chat._mcp.listening)
    settings(mcp_enabled=False, mcp_port=port, mcp_token=TOKEN)
    chat._sync_mcp()
    refused_after = http(body=b"{}", headers=auth())
    check("mcp: turned off, it no longer answers", not chat._mcp.listening and refused_after["status"] == 0, refused_after)
    settings(mcp_enabled=True, mcp_port=port, mcp_token=TOKEN)
    chat._sync_mcp()
    chat.shutdown()
    closed = http(body=b"{}", headers=auth())
    check("mcp: nothing listens after the plugin unloads", closed["status"] == 0, closed)


def _first_token(dialog_class, target, values_class):
    dialog = dialog_class(values_class(), target, None)
    dialog.mcp_enabled.setChecked(True)
    token = dialog.chosen_mcp_token()
    dialog.close()
    return len(token) >= 40


def check_effects(layer_id):
    """Lot 3 of the undo plan: what a turn does beside the filters is undone and redone with them."""
    from filter_mate.adapters.agent.turn_checkpoint import TurnCheckpoint
    from filter_mate.core.agent.messages import ToolCallPart

    project = QgsProject.instance()
    layer = project.mapLayer(layer_id)
    group = project.layerTreeRoot().addGroup("effects")
    node = project.layerTreeRoot().findLayer(layer_id)
    group.insertChildNode(0, node.clone())
    node.parent().removeChildNode(node)
    count = layer.featureCount()

    turn = TurnCheckpoint()
    turn.label = "selection and visibility"
    turn.begin(ToolCallPart("e1", "select_features", {"layer": "communes", "expression": '"pop" > 5000'}))
    layer.selectByIds([1, 2, 3])
    turn.begin(ToolCallPart("e2", "set_layers_visibility", {"layers": ["communes"], "visible": False}))
    project.layerTreeRoot().findLayer(layer_id).setItemVisibilityChecked(False)
    turn.commit()
    check("effects: a turn of selection and visibility only is a step", TurnCheckpoint.can_undo())
    turn.undo()
    check("effects: the selection comes back", layer.selectedFeatureCount() == 0, layer.selectedFeatureIds())
    check("effects: the visibility comes back", project.layerTreeRoot().findLayer(layer_id).itemVisibilityChecked())
    turn.redo()
    check("effects: and both again on redo", layer.selectedFeatureCount() == 3
          and not project.layerTreeRoot().findLayer(layer_id).itemVisibilityChecked())
    project.layerTreeRoot().findLayer(layer_id).setItemVisibilityChecked(True)

    turn.label = "remove communes"
    turn.begin(ToolCallPart("e3", "remove_layers", {"layers": ["communes"]}))
    project.removeMapLayer(layer_id)
    names = turn.commit()
    check("effects: a removed layer is named in the turn", "communes" in names, names)
    restored, left = turn.undo()
    back = project.mapLayer(layer_id)
    check("effects: a removed layer comes back, same id, same features", back is not None and back.featureCount() == count
          and not left, (restored, left))
    check("effects: at its place in its group", group.findLayer(layer_id) is not None)
    turn.redo()
    check("effects: and goes again on redo", project.mapLayer(layer_id) is None)
    turn.undo()

    memory = QgsVectorLayer("Point?crs=EPSG:2154&field=a:integer", "scratch", "memory")
    turn.label = "add a layer"
    turn.begin(ToolCallPart("e4", "add_layer", {"source": "/data/a.gpkg"}))
    project.addMapLayer(memory)
    memory_id = memory.id()
    turn.commit()
    turn.undo()
    check("effects: an added layer goes on undo", project.mapLayer(memory_id) is None)
    redone = turn.redo()
    # It would come back empty: a layer held in memory is not brought back on redo, and that is said (#302).
    check("effects: a layer in memory is not brought back empty on redo, and says so",
          project.mapLayer(memory_id) is None and "scratch" in redone[1], redone)
    memory = QgsVectorLayer("Point?crs=EPSG:2154&field=a:integer", "scratch", "memory")
    project.addMapLayer(memory)
    memory_id = memory.id()
    turn.label = "remove scratch"
    turn.begin(ToolCallPart("e5", "remove_layers", {"layers": ["scratch"]}))
    project.removeMapLayer(memory_id)
    turn.commit()
    restored, left = turn.undo()
    check("effects: a layer in memory cannot come back, and says so", project.mapLayer(memory_id) is None
          and "scratch" in left, (restored, left))


def check_thread_markup():
    """The bold of the cards: whole layer names only, everything else escaped."""
    from filter_mate.ui.widgets.agent_thread import strong_markup
    check("bold: the layer names", strong_markup("Filter on communes by roads", ["communes", "roads"])
          == "Filter on <b>communes</b> by <b>roads</b>")
    check("bold: a short name is not bolded inside other words", strong_markup("Filter on a by an area", ["a"])
          == "Filter on <b>a</b> by an area", strong_markup("Filter on a by an area", ["a"]))
    check("bold: a name holding markup is escaped", strong_markup('Filter on <img src="x">', ['<img src="x">'])
          == "Filter on <b>&lt;img src=&quot;x&quot;&gt;</b>", strong_markup('Filter on <img src="x">', ['<img src="x">']))
    check("bold: no name, plain escaped text", strong_markup("a < b", []) == "a &lt; b")


def check_thread_theme():
    """A conversation drawn before the dock had its theme takes the right one afterwards (light dock, dark cards)."""
    from filter_mate.ui.styles.mockup_design import tokens
    from filter_mate.ui.widgets.agent_thread import AgentThread
    dark = [True]
    thread = AgentThread(lambda: tokens(dark[0]), lambda: dark[0], lambda: None)
    thread.add_user("mnt 1")
    thread.add_card("Filter on MNT", True, "", "")
    thread.add_card("Filter on MNT by MNT", False, "", "")
    thread.add_step("Reading the layers")
    thread.finish_steps()
    thread.add_error("Refused", "Try again", "Settings", lambda: None)
    thread.add_text("La couche est visible.")
    thread.add_note("Earlier conversation")
    dark[0] = False
    thread.refresh_look()
    light, night = tokens(False), tokens(True)
    sheets = " ".join(widget.styleSheet() for widget in thread.widget().findChildren(QWidget))
    bubble = thread.widget().findChild(QLabel, "label_agent_request")
    check("theme: the bubble takes the light colors", light["fm_active"] in bubble.styleSheet()
          and night["fm_active"] not in bubble.styleSheet(), bubble.styleSheet())
    cards = thread.widget().findChildren(QFrame, "frame_agent_card")
    check("theme: the cards take the light background", cards and all(light["fm_group"] in card.styleSheet()
                                                                       for card in cards), [c.styleSheet() for c in cards])
    check("theme: every text has a light color, none of the dark theme", light["fm_text"] in sheets and not any(
        night[key] in sheets for key in ("fm_text", "fm_group", "fm_active", "fm_list") if night[key] != light[key]))
    step = [label for label in thread.widget().findChildren(QLabel) if "Reading the layers" in label.text()]
    check("theme: a done step keeps its text and takes the light green", step and "#146a55" in step[0].text(),
          [label.text() for label in step])


def check_dialect(layer):
    """The language of a filter, as describe_layer gives it to the model."""
    from filter_mate.adapters.public_api.introspection import sql_dialect
    check("dialect: a GeoPackage is read by SQLite", sql_dialect(layer) == "sqlite", sql_dialect(layer))
    memory = QgsVectorLayer("Point?crs=EPSG:2154&field=a:integer", "scratch", "memory")
    check("dialect: a memory layer by QGIS", sql_dialect(memory) == "qgis_expression", sql_dialect(memory))


def main():
    print(f"QGIS {Qgis.QGIS_VERSION}, Python {sys.version.split()[0]}", flush=True)
    check_thread_markup()
    check_thread_theme()
    work = tempfile.mkdtemp()
    provider = Provider()
    layer = make_layer(os.path.join(work, "communes.gpkg"))
    QgsProject.instance().addMapLayer(layer)
    check_dialect(layer)
    check_transport(provider, None)
    authcfg = check_key_store()
    check_checkpoint(layer)
    check_chat(provider, layer, authcfg, work)
    check_effects(layer.id())


if __name__ == "__main__":
    app = QgsApplication([], True)
    app.initQgis()
    package_root = tempfile.mkdtemp()
    os.symlink(os.environ.get("FM_REPO", "/src"), os.path.join(package_root, "filter_mate"))
    sys.path.insert(0, package_root)
    sys.dont_write_bytecode = True
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        RESULTS.append(False)
    failed = RESULTS.count(False)
    print(f"{len(RESULTS) - failed}/{len(RESULTS)} passed", flush=True)
    os._exit(1 if failed else 0)
