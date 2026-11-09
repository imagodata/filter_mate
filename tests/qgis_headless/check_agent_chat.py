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
from qgis.PyQt.QtCore import QCoreApplication, Qt  # noqa: E402
from qgis.PyQt.QtTest import QTest  # noqa: E402
from qgis.PyQt.QtWidgets import QLabel, QToolBox  # noqa: E402

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

    check("off by default", agent_enabled({}) is False and agent_enabled({"APP": {"OPTIONS": {}}}) is False)
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
    check("nothing to undo: no button", not panel.undo_button.isVisible())

    def settings(**changes):
        values = dict(preset="anthropic", model="test-model", base_url=provider.url, consent=True, authcfg=authcfg,
                      consent_target=target_of("anthropic", provider.url), key_target=target_of("anthropic", provider.url))
        values.update(changes)
        save_settings(AgentSettings(**values))
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
    second = provider.requests[1]["body"]["messages"]
    check("the tool call goes back with its result", second[1]["content"][0]["type"] == "tool_use" and
          second[2]["content"][0]["tool_use_id"] == "toolu_1" and "communes" in second[2]["content"][0]["content"], second)
    check("the same prefix is sent each time", json.dumps(provider.requests[2]["body"]["messages"][:3]) == json.dumps(second))
    check("the answer is shown", "Il reste 50 communes." in panel.thread.toPlainText(), panel.thread.toPlainText())
    check("the question is shown", "garde les communes" in panel.thread.toPlainText())
    check("the change is reported", "communes" in panel.status.text(), panel.status.text())
    check("the input was emptied", panel.input.text() == "")
    check("undo is offered", panel.undo_button.isVisible())
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

    settings()
    provider.reset((401, {}, b'{"error":{"message":"invalid x-api-key"}}'))
    ask("salut")
    check("a refused key says where to go", "key" in panel.status.text().lower() and panel.fix_button.isVisible(), panel.status.text())
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
    settings(open_data=True)
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
    host.close()


def main():
    print(f"QGIS {Qgis.QGIS_VERSION}, Python {sys.version.split()[0]}", flush=True)
    work = tempfile.mkdtemp()
    provider = Provider()
    layer = make_layer(os.path.join(work, "communes.gpkg"))
    QgsProject.instance().addMapLayer(layer)
    check_transport(provider, None)
    authcfg = check_key_store()
    check_checkpoint(layer)
    check_chat(provider, layer, authcfg, work)


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
