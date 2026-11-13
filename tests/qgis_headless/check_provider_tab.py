# -*- coding: utf-8 -*-
"""The Provider tab of the agent settings in a real QGIS: the key link, the Test button, the models of the provider.

The providers are a local server that speaks the Messages API and the OpenAI-compatible API, so no model is called
and no key is real. The real network stack and the real bounded request of the plugin are used. Run inside a
qgis/qgis image, on a writable copy of the repository:

    docker run --rm --network none -v "$PWD:/src:ro" -e FM_REPO=/tmp/copy qgis/qgis:ltr bash -c \\
        'mkdir /tmp/copy; cp -r /src/. /tmp/copy; python3 /tmp/copy/tests/qgis_headless/check_provider_tab.py'

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

from qgis.core import Qgis, QgsApplication  # noqa: E402
from qgis.PyQt.QtCore import QCoreApplication  # noqa: E402
from qgis.PyQt.QtWidgets import QLabel  # noqa: E402

RESULTS = []
GOOD_KEY = "sk-test-good-0123456789"
BAD_KEY = "sk-test-bad-9876543210"


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


def _link(source, target):
    os.symlink(source, target)


def sse(*events):
    return "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()


CLAUDE_OK = sse({"type": "message_start", "message": {"usage": {}}},
                {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
                {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "OK"}},
                {"type": "content_block_stop", "index": 0},
                {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 2}},
                {"type": "message_stop"})
OPENAI_OK = b'data: {"choices":[{"delta":{"content":"OK"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'


class Provider:
    """Claude's paths under /v1, Mistral's under /m/v1: the key GOOD_KEY is the only valid one."""

    def __init__(self):
        self.requests = []
        provider = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, *args):
                pass

            def _answer(self, status, body, kind="application/json"):
                self.send_response(status)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _handle(self, body):
                headers = {k.lower(): v for k, v in self.headers.items()}
                provider.requests.append((self.command, self.path, headers, body))
                key = headers.get("x-api-key") or headers.get("authorization", "").replace("Bearer ", "")
                if key != GOOD_KEY:  # the way OpenAI words it: with the key it was sent
                    message = json.dumps({"error": {"message": f"Incorrect API key provided: {key}."}}).encode()
                    return self._answer(401, message)
                if self.path == "/v1/messages":
                    return self._answer(200, CLAUDE_OK, "text/event-stream")
                if self.path == "/v1/models?limit=100":
                    return self._answer(200, json.dumps({"data": [{"id": "claude-a"}, {"id": "claude-b"}]}).encode())
                if self.path == "/m/v1/chat/completions":
                    return self._answer(200, OPENAI_OK, "text/event-stream")
                if self.path == "/m/v1/models":
                    return self._answer(200, json.dumps({"data": [
                        {"id": "mistral-small-latest", "capabilities": {"completion_chat": True}},
                        {"id": "mistral-embed", "capabilities": {"completion_chat": False}}]}).encode())
                return self._answer(404, b"{}")

            def do_GET(self):  # noqa: N802 - http.server name
                self._handle(None)

            def do_POST(self):  # noqa: N802
                self._handle(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


def main():
    print(f"QGIS {Qgis.QGIS_VERSION}, Python {sys.version.split()[0]}", flush=True)
    from filter_mate.adapters.agent.settings import AgentSettings, target_of
    from filter_mate.core.agent.providers.model_list import KEY_PAGES
    from filter_mate.ui.controllers.agent_chat_controller import AgentChatController
    from filter_mate.ui.widgets.agent_panel import AgentSettingsDialog

    provider = Provider()
    dialog = AgentSettingsDialog(AgentSettings(preset="anthropic"), target_of, None,
                                 provider_tester=AgentChatController._test_provider)
    dialog._fetch_ollama_models = lambda: None  # no Ollama here
    dialog.show()
    wait(lambda: False, 0.05)

    def models():
        return [dialog.model.itemText(i) for i in range(dialog.model.count())]

    for name in ("anthropic", "mistral", "openai"):
        dialog.preset.setCurrentIndex(dialog.preset.findData(name))
        check(f"{name}: a link to its page of keys, and a Test button",
              dialog.key_link.isVisible() and KEY_PAGES[name] in dialog.key_link.text()
              and dialog.key_link.openExternalLinks() and dialog.provider_test_button.isVisible()
              and dialog.provider_test_button.isEnabled(), dialog.key_link.text())
    dialog.preset.setCurrentIndex(dialog.preset.findData("ollama"))
    check("ollama: no key, so no link; Test stays",
          not dialog.key_link.isVisible() and dialog.provider_test_button.isVisible())
    dialog.preset.setCurrentIndex(dialog.preset.findData("mistral"))
    check("mistral: its models are suggested",
          models() == ["mistral-small-latest", "mistral-medium-latest", "mistral-large-latest"], models())

    dialog.preset.setCurrentIndex(dialog.preset.findData("anthropic"))
    dialog.base_url.setText(provider.url)
    dialog.model.setEditText("claude-mine")
    dialog.key.setText(GOOD_KEY)
    dialog.provider_test_button.click()
    check("test: a key that works says so and lists the models, the typed name stays",
          dialog.provider_result.text() == "It answers." and models() == ["claude-a", "claude-b"]
          and dialog.model.currentText() == "claude-mine" and dialog.provider_test_button.isEnabled(),
          (dialog.provider_result.text(), models()))
    sent = [r for r in provider.requests if r[1] == "/v1/messages"][0]
    check("test: one short request of 16 tokens", sent[3]["max_tokens"] == 16 and sent[3]["stream"] is True
          and "Reply with OK." in json.dumps(sent[3]["messages"]), sent[3])

    provider.requests.clear()
    dialog.key.setText(BAD_KEY)
    dialog.provider_test_button.click()
    texts = [label.text() for label in dialog.findChildren(QLabel)]
    check("test: a refused key is said, and never shown",
          "refused the API key" in dialog.provider_result.text() and all(BAD_KEY not in t for t in texts), texts)
    check("test: nothing more is asked once the key is refused", len(provider.requests) == 1, provider.requests)

    dialog.preset.setCurrentIndex(dialog.preset.findData("mistral"))
    dialog.base_url.setText(provider.url + "/m/v1")
    dialog.model.setEditText("")
    dialog.key.setText(GOOD_KEY)
    check("changing provider clears the former result", dialog.provider_result.text() == "")
    dialog.provider_test_button.click()
    check("mistral, no model typed: the list is read and filtered to the chat models",
          "choose a model" in dialog.provider_result.text() and models() == ["mistral-small-latest"]
          and dialog.model.currentText() == "", (dialog.provider_result.text(), models()))
    dialog.model.setEditText("mistral-small-latest")
    dialog.provider_test_button.click()
    check("mistral with a model: through the OpenAI-compatible path", dialog.provider_result.text() == "It answers."
          and any(r[1] == "/m/v1/chat/completions" for r in provider.requests), dialog.provider_result.text())
    dialog.close()

    dialog = AgentSettingsDialog(AgentSettings(preset="anthropic"), target_of, None,
                                 provider_tester=AgentChatController._test_provider)
    dialog.base_url.setText("http://127.0.0.1:9")
    dialog.key.setText(GOOD_KEY)
    dialog.model.setEditText("m")
    dialog.provider_test_button.click()
    check("no server: it says the provider could not be reached",
          "could not be reached" in dialog.provider_result.text(), dialog.provider_result.text())
    dialog.close()


if __name__ == "__main__":
    app = QgsApplication([], True)
    app.initQgis()
    package_root = tempfile.mkdtemp()
    _link(os.environ.get("FM_REPO", "/src"), os.path.join(package_root, "filter_mate"))
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
