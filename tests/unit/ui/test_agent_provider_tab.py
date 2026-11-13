# -*- coding: utf-8 -*-
"""The Provider tab of the agent settings, on real Qt widgets (PyQt5, offscreen): where to get a key, Test, the models.

Loaded under a private package with ``qgis.PyQt`` pointing at PyQt5 for the import only (the root conftest mocks Qt
for the other tests), and ``qgis.core`` mocked: no request leaves, the tester is a fake. Skipped without PyQt5.
"""
import importlib
import json
import os
import pathlib
import sys
import types
import xml.etree.ElementTree as ElementTree
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
from PyQt5 import QtCore, QtGui  # noqa: E402

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_PKG = "fm_agent_provider_tab_test"


def _load():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    qt = {"qgis.PyQt": types.ModuleType("qgis.PyQt"), "qgis.PyQt.QtCore": QtCore, "qgis.PyQt.QtGui": QtGui,
          "qgis.PyQt.QtWidgets": QtWidgets, "qgis.PyQt.QtNetwork": MagicMock(), "qgis.PyQt.QtXml": MagicMock()}
    if "qgis.core" not in sys.modules:
        qt["qgis.core"] = MagicMock()
    saved = {name: sys.modules.get(name) for name in qt}
    sys.modules.update(qt)  # for the imports only: the modules loaded keep the real Qt classes
    try:
        for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.agent", _ROOT / "core" / "agent"),
                           (".adapters", _ROOT / "adapters"), (".adapters.agent", _ROOT / "adapters" / "agent"),
                           (".ui", _ROOT / "ui"), (".ui.widgets", _ROOT / "ui" / "widgets"),
                           (".ui.styles", _ROOT / "ui" / "styles")):
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]
            sys.modules[_PKG + name] = package
        return (app, importlib.import_module(f"{_PKG}.ui.widgets.agent_panel"),
                importlib.import_module(f"{_PKG}.adapters.agent.settings"),
                importlib.import_module(f"{_PKG}.core.agent.providers.model_list"))
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


_APP, panel_module, settings_module, model_list = _load()
AgentSettingsDialog = panel_module.AgentSettingsDialog
ollama_chat = importlib.import_module(f"{_PKG}.core.agent.providers.ollama_chat")
SECRET = "sk-test-0123456789abcdef"


class FakeTester:
    """Stands for AgentChatController._test_provider: records what it was asked, answers what it is told to."""

    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def __call__(self, preset, model, base_url, key):
        self.calls.append((preset, model, base_url, key))
        return self.answer(key) if callable(self.answer) else self.answer


def _dialog(preset="anthropic", tester=None, model="", **values):
    settings = settings_module.AgentSettings(preset=preset, model=model, **values)
    dialog = AgentSettingsDialog(settings, settings_module.target_of, None, provider_tester=tester)
    # No request leaves from a test: Ollama's list of installed models is another task's concern.
    dialog._fetch_ollama_models = lambda: None
    return dialog


def _labels(dialog):
    return [label.text() for label in dialog.findChildren(QtWidgets.QLabel)]


def _models(dialog):
    return [dialog.model.itemText(index) for index in range(dialog.model.count())]


def _hidden(dialog, widget):
    return not widget.isVisibleTo(dialog)


@pytest.mark.parametrize("preset", ["anthropic", "mistral", "openai"])
def test_each_cloud_provider_links_to_its_key_page(preset):
    dialog = _dialog(preset)
    dialog.preset.setCurrentIndex(dialog.preset.findData(preset))
    assert not _hidden(dialog, dialog.key_link)
    assert model_list.KEY_PAGES[preset] in dialog.key_link.text()


def test_the_key_link_follows_the_provider_and_is_hidden_for_ollama():
    dialog = _dialog("anthropic")
    dialog.preset.setCurrentIndex(dialog.preset.findData("openai"))
    assert model_list.KEY_PAGES["openai"] in dialog.key_link.text()
    assert model_list.KEY_PAGES["anthropic"] not in dialog.key_link.text()
    dialog.preset.setCurrentIndex(dialog.preset.findData("ollama"))
    assert _hidden(dialog, dialog.key_link)
    dialog.preset.setCurrentIndex(dialog.preset.findData("mistral"))
    assert not _hidden(dialog, dialog.key_link)


def test_mistral_suggests_its_models():
    dialog = _dialog("mistral")
    assert _models(dialog) == ["mistral-small-latest", "mistral-medium-latest", "mistral-large-latest"]


def test_test_is_off_without_a_tester():
    assert not _dialog("anthropic").provider_test_button.isEnabled()
    assert _dialog("anthropic", FakeTester((True, "", ()))).provider_test_button.isEnabled()


def test_provider_test_messages():
    tester = FakeTester((False, "Invalid API key.", ()))
    dialog = _dialog("openai", tester)
    dialog.key.setText(SECRET)
    dialog.provider_test_button.click()
    assert dialog.provider_result.text() == "Invalid API key."
    assert tester.calls == [("openai", "", "", SECRET)]
    assert all(SECRET not in text for text in _labels(dialog))


def test_a_key_echoed_by_the_provider_never_reaches_a_label():
    dialog = _dialog("openai", FakeTester(lambda key: (False, f"Incorrect API key provided: {key}.", ())))
    dialog.key.setText(SECRET)
    dialog.provider_test_button.click()
    assert SECRET not in dialog.provider_result.text() and "Incorrect API key provided" in dialog.provider_result.text()
    assert all(SECRET not in text for text in _labels(dialog))


def test_the_result_is_shown_as_plain_text():
    dialog = _dialog("openai", FakeTester((False, "<a href='https://evil.example'>click</a>", ())))
    dialog.provider_test_button.click()
    assert dialog.provider_result.textFormat() == QtCore.Qt.TextFormat.PlainText


def test_a_tester_that_fails_is_a_message_not_a_crash():
    def broken(key):
        raise RuntimeError("boom " + key)

    dialog = _dialog("openai", FakeTester(broken))
    dialog.key.setText(SECRET)
    dialog.provider_test_button.click()
    assert dialog.provider_result.text() and SECRET not in dialog.provider_result.text()
    assert dialog.provider_test_button.isEnabled()


def test_models_fetch_failure_keeps_typed_model():
    dialog = _dialog("anthropic", FakeTester((False, "No answer.", ())), model="my-model")
    dialog.provider_test_button.click()
    assert dialog.model.currentText() == "my-model"
    assert dialog.provider_result.text() == "No answer."


def test_models_from_test_fill_the_list():
    tester = FakeTester((True, "It answers.", ("a", "b")))
    dialog = _dialog("anthropic", tester, model="my-model")
    dialog.provider_test_button.click()
    assert _models(dialog) == ["a", "b"]
    assert dialog.model.currentText() == "my-model"
    assert tester.calls[0][:2] == ("anthropic", "my-model")


def test_models_listed_beside_a_failed_request_are_offered_too():
    """A wrong model name fails the request, yet the provider lists the right ones."""
    dialog = _dialog("openai", FakeTester((False, "The model does not exist.", ("gpt-x",))), model="gpt-y")
    dialog.provider_test_button.click()
    assert _models(dialog) == ["gpt-x"] and dialog.model.currentText() == "gpt-y"


def test_no_typed_model_stays_empty_and_the_list_is_offered():
    dialog = _dialog("mistral", FakeTester((True, "It answers.", ("m1", "m2"))))
    dialog.provider_test_button.click()
    assert dialog.model.currentText() == "" and _models(dialog) == ["m1", "m2"]


def test_models_of_another_provider_are_not_offered():
    """The user picked another provider while the request ran (the wait spins the event loop)."""
    holder = {}

    def tester(preset, model, base_url, key):
        holder["dialog"].preset.setCurrentIndex(holder["dialog"].preset.findData("mistral"))
        return True, "It answers.", ("claude-x",)

    dialog = holder["dialog"] = _dialog("anthropic", tester)
    dialog.provider_test_button.click()
    assert "claude-x" not in _models(dialog)


def test_a_second_click_while_testing_is_ignored():
    holder, calls = {}, []

    def tester(preset, model, base_url, key):
        calls.append(preset)
        holder["enabled"] = holder["dialog"].provider_test_button.isEnabled()
        holder["dialog"]._on_test_provider()  # a click that the nested event loop let through
        return True, "It answers.", ()

    dialog = holder["dialog"] = _dialog("anthropic", tester)
    dialog.provider_test_button.click()
    assert calls == ["anthropic"] and holder["enabled"] is False
    assert dialog.provider_test_button.isEnabled()


def test_changing_provider_clears_the_result():
    dialog = _dialog("anthropic", FakeTester((False, "Invalid API key.", ())))
    dialog.provider_test_button.click()
    dialog.preset.setCurrentIndex(dialog.preset.findData("openai"))
    assert dialog.provider_result.text() == ""


def test_the_welcome_note_names_the_two_ways_in():
    note = panel_module.AgentPanel().welcome_note.text()
    assert note == ("It needs an AI provider: your own API key, or a local model with Ollama. "
                    "Nothing is sent before you agree.")


def test_a_removed_key_is_not_tested_as_if_it_were_still_there():
    """After Remove, the tester would still read the stored key and say it answers."""
    tester = FakeTester((True, "It answers.", ()))
    dialog = _dialog("openai", tester, authcfg="abc123", key_target="x")
    dialog._on_forget()
    dialog.provider_test_button.click()
    assert tester.calls == [] and dialog.provider_result.text() == "Enter your API key first."
    dialog.key.setText(SECRET)
    dialog.provider_test_button.click()
    assert len(tester.calls) == 1 and dialog.provider_result.text() == "It answers."


def test_the_key_typed_for_a_provider_does_not_follow_a_change_of_provider():
    tester = FakeTester((True, "It answers.", ()))
    dialog = _dialog("anthropic", tester)
    dialog.key.setText(SECRET)
    dialog.preset.setCurrentIndex(dialog.preset.findData("openai"))
    assert dialog.key.text() == ""
    dialog.provider_test_button.click()
    assert tester.calls[0][3] == ""


def test_the_key_typed_for_an_address_does_not_follow_a_change_of_address():
    dialog = _dialog("openai", FakeTester((True, "It answers.", ())))
    dialog.base_url.setText("https://one.example.com/v1")
    dialog.key.setText(SECRET)
    dialog.base_url.setText("https://two.example.com/v1")
    assert dialog.key.text() == ""


def test_the_key_stays_when_the_address_is_only_written_differently():
    dialog = _dialog("openai", FakeTester((True, "It answers.", ())))
    dialog.base_url.setText("https://one.example.com/v1")
    dialog.key.setText(SECRET)
    dialog.base_url.setText("https://one.example.com/v1/")  # the same server: a trailing slash is not a target
    assert dialog.key.text() == SECRET


def test_removing_the_stored_key_keeps_the_key_being_typed():
    dialog = _dialog("openai", FakeTester((True, "It answers.", ())), authcfg="abc123", key_target="x")
    dialog.key.setText(SECRET)
    dialog._on_forget()
    assert dialog.key.text() == SECRET


def test_the_model_of_the_former_provider_is_not_kept():
    dialog = _dialog("anthropic", model="claude-haiku-5-5")
    assert dialog.model.currentText() == "claude-haiku-5-5"
    dialog.preset.setCurrentIndex(dialog.preset.findData("mistral"))
    assert dialog.model.currentText() == "mistral-small-latest"
    dialog.preset.setCurrentIndex(dialog.preset.findData("openai"))
    assert dialog.model.currentText() == ""  # OpenAI suggests nothing and the model was Mistral's


def test_a_model_the_user_typed_stays_through_a_change_of_provider():
    dialog = _dialog("anthropic", model="my-own-model")
    dialog.preset.setCurrentIndex(dialog.preset.findData("openai"))
    assert dialog.model.currentText() == "my-own-model"


def test_a_model_the_former_provider_listed_is_not_kept():
    dialog = _dialog("openai", FakeTester((True, "It answers.", ("gpt-x", "gpt-y"))), model="gpt-x")
    dialog.provider_test_button.click()
    dialog.preset.setCurrentIndex(dialog.preset.findData("mistral"))
    assert dialog.model.currentText() == "mistral-small-latest"


def test_the_saved_model_is_what_the_dialog_opens_with():
    for preset, model in (("anthropic", "claude-opus-5-5"), ("mistral", "my-finetune"), ("openai", "gpt-x"),
                          ("anthropic", "")):
        assert _dialog(preset, model=model).chosen_model() == model


def test_a_short_key_does_not_damage_what_the_provider_said():
    dialog = _dialog("openai", FakeTester((True, "It answers.", ())))
    dialog.key.setText("e")
    dialog.provider_test_button.click()
    assert dialog.provider_result.text() == "It answers."


def test_a_key_of_eight_characters_is_hidden_in_what_the_provider_said():
    dialog = _dialog("openai", FakeTester(lambda key: (False, f"bad key {key}", ())))
    dialog.key.setText("12345678")
    dialog.provider_test_button.click()
    assert dialog.provider_result.text() == "bad key …"


def test_models_of_another_address_are_not_offered():
    holder = {}

    def tester(preset, model, base_url, key):
        holder["dialog"].base_url.setText("https://two.example.com/v1")
        return True, "It answers.", ("from-the-first-server",)

    dialog = holder["dialog"] = _dialog("openai", tester)
    dialog.base_url.setText("https://one.example.com/v1")
    dialog.provider_test_button.click()
    assert "from-the-first-server" not in _models(dialog)
    assert dialog.provider_result.text() == ""  # not left saying Testing…


def test_models_of_another_key_are_not_offered():
    holder = {}

    def tester(preset, model, base_url, key):
        holder["dialog"].key.setText("another-key-0123456789")
        return True, "It answers.", ("from-the-first-key",)

    dialog = holder["dialog"] = _dialog("openai", tester)
    dialog.key.setText(SECRET)
    dialog.provider_test_button.click()
    assert "from-the-first-key" not in _models(dialog) and dialog.provider_result.text() == ""


class _Application:
    """QCoreApplication for the panel, with what happens during processEvents() chosen by the test."""

    def __init__(self, during):
        self.during = during

    @staticmethod
    def translate(_context, text):
        return text

    def processEvents(self):
        self.during()


def test_closing_during_the_first_events_sends_nothing(monkeypatch):
    """A click on Save while the Testing… label is painted: the dialog is closed, no request leaves with the key."""
    tester = FakeTester((True, "It answers.", ()))
    dialog = _dialog("openai", tester)
    dialog.key.setText(SECRET)
    monkeypatch.setattr(panel_module, "QCoreApplication", _Application(lambda: dialog.done(0)))
    dialog.provider_test_button.click()
    assert tester.calls == []
    assert dialog.provider_test_button.isEnabled() and not dialog._testing


def test_closing_the_dialog_stops_the_test_that_is_waiting():
    stopped = []
    holder = {}

    def tester(preset, model, base_url, key):
        holder["dialog"].done(0)  # Save or Cancel, in the event loop the test spins
        return False, "stopped", ()

    settings = settings_module.AgentSettings(preset="openai")
    dialog = holder["dialog"] = AgentSettingsDialog(settings, settings_module.target_of, None, provider_tester=tester,
                                                    provider_stop=lambda: stopped.append(True))
    dialog._fetch_ollama_models = lambda: None
    dialog.provider_test_button.click()
    assert stopped == [True]


def test_closing_the_dialog_without_a_test_stops_nothing():
    stopped = []
    settings = settings_module.AgentSettings(preset="openai")
    dialog = AgentSettingsDialog(settings, settings_module.target_of, None,
                                 provider_tester=FakeTester((True, "", ())), provider_stop=lambda: stopped.append(True))
    dialog._fetch_ollama_models = lambda: None
    dialog.done(0)
    assert stopped == []


def test_the_key_link_escapes_what_a_translation_says(monkeypatch):
    real = panel_module._tr
    monkeypatch.setattr(panel_module, "_tr", lambda text: "Create <b> & key" if text == "Create a key" else real(text))
    dialog = _dialog("openai")
    link = ElementTree.fromstring(dialog.key_link.text())  # one well-formed link: nothing leaked into the markup
    assert link.tag == "a" and link.attrib == {"href": model_list.KEY_PAGES["openai"]}
    assert link.text == "Create <b> & key" and len(link) == 0


# -- Ollama: where to install it, a model to download --------------------------------------------------------------


class FakeReply(QtCore.QObject):
    """A QNetworkReply that says what the test feeds it, as the real one does: readyRead, then finished."""

    readyRead = QtCore.pyqtSignal()  # noqa: N815 - Qt names
    finished = QtCore.pyqtSignal()
    downloadProgress = QtCore.pyqtSignal(int, int)  # noqa: N815

    def __init__(self):
        super().__init__()
        self.body, self.code, self.status, self.aborted, self.done = b"", 0, None, 0, False

    def read(self, _limit):
        return self.body

    def readAll(self):  # noqa: N802
        body, self.body = self.body, b""
        return body

    def error(self):
        return self.code

    def attribute(self, _attribute):
        return self.status

    def abort(self):
        self.aborted += 1
        self.code = 5
        self._finish()

    def deleteLater(self):  # noqa: N802
        pass

    def _finish(self):
        if not self.done:  # Qt says it once
            self.done = True
            self.finished.emit()

    def send(self, data):
        self.body += data
        self.readyRead.emit()

    def end(self, data=b""):
        self.body += data
        self._finish()


class FakeNetwork:
    """qgis.core.QgsNetworkAccessManager and the request classes of QtNetwork, recording what is sent."""

    def __init__(self):
        self.gets, self.posts = [], []

    def get(self, request):
        reply = FakeReply()
        self.gets.append((request, reply))
        return reply

    def post(self, request, data):
        reply = FakeReply()
        self.posts.append((request, bytes(data), reply))
        return reply

    @property
    def listing(self):
        return self.gets[-1][1]

    @property
    def download(self):
        return self.posts[-1][2]


class FakeRequest:
    KnownHeaders = SimpleNamespace(ContentTypeHeader="content-type")
    Attribute = SimpleNamespace(HttpStatusCodeAttribute="status", RedirectPolicyAttribute="redirect")
    RedirectPolicy = SimpleNamespace(ManualRedirectPolicy="manual")

    def __init__(self, url):
        self.url, self.headers, self.attributes, self.timeout = url.toString(), {}, {}, None

    def setHeader(self, name, value):  # noqa: N802
        self.headers[name] = value

    def setAttribute(self, name, value):  # noqa: N802
        self.attributes[name] = value

    def setTransferTimeout(self, ms):  # noqa: N802
        self.timeout = ms


@pytest.fixture
def network(monkeypatch):
    fake = FakeNetwork()
    monkeypatch.setitem(sys.modules, "qgis.core", SimpleNamespace(
        QgsNetworkAccessManager=SimpleNamespace(instance=lambda: fake)))
    monkeypatch.setitem(sys.modules, "qgis.PyQt.QtNetwork", SimpleNamespace(
        QNetworkRequest=FakeRequest,
        QNetworkReply=SimpleNamespace(NetworkError=SimpleNamespace(NoError=0, OperationCanceledError=5))))
    return fake


def _ollama(network, model="", base_url=""):
    """The dialog on Ollama; it asked for the list of the models, not answered yet."""
    settings = settings_module.AgentSettings(preset="ollama", model=model, base_url=base_url)
    dialog = AgentSettingsDialog(settings, settings_module.target_of, None, provider_tester=FakeTester((True, "", ())))
    assert len(network.gets) == 1
    return dialog


def _installed(*names, families=None):
    models = [{"name": name, "details": {"families": families or ["llama"]}} for name in names]
    return json.dumps({"models": models}).encode()


def _lines(*payloads):
    return b"".join(json.dumps(payload).encode() + b"\n" for payload in payloads)


def test_ollama_not_answering_offers_install(network):
    dialog = _ollama(network, base_url="http://gpu.lan:11434")
    network.listing.end(b"")  # a closed port: no body
    assert not _hidden(dialog, dialog.ollama_install_row) and not _hidden(dialog, dialog.ollama_refresh_button)
    assert ollama_chat.OLLAMA_DOWNLOAD_PAGE in dialog.ollama_install_note.text()
    assert "http://gpu.lan:11434" in dialog.ollama_install_note.text()
    assert _hidden(dialog, dialog.ollama_download_button)
    dialog.ollama_refresh_button.click()  # asks again
    assert len(network.gets) == 2


def test_the_install_note_goes_when_ollama_answers(network):
    dialog = _ollama(network, model="qwen3:8b")
    network.listing.end(b"")
    dialog.ollama_refresh_button.click()
    network.listing.end(_installed("qwen3:8b"))
    assert _hidden(dialog, dialog.ollama_install_row) and _hidden(dialog, dialog.ollama_download_button)


def test_the_install_note_is_not_for_the_other_providers(network):
    dialog = _ollama(network)
    network.listing.end(b"")
    dialog.preset.setCurrentIndex(dialog.preset.findData("openai"))
    assert _hidden(dialog, dialog.ollama_install_row) and _hidden(dialog, dialog.ollama_download_row)


def test_ollama_without_the_model_offers_download(network):
    dialog = _ollama(network)
    network.listing.end(_installed("nomic-embed-text", families=["nomic-bert"]))  # no chat model at all
    assert dialog.model.currentText() == "qwen3.5:4b"
    assert not _hidden(dialog, dialog.ollama_download_button) and _hidden(dialog, dialog.ollama_install_row)


def test_ollama_with_a_model_proposes_that_one_and_no_download(network):
    dialog = _ollama(network)
    network.listing.end(_installed("qwen3:8b", "llama3"))
    assert dialog.model.currentText() == "qwen3:8b" and _hidden(dialog, dialog.ollama_download_button)


def test_a_typed_model_that_is_not_installed_offers_download(network):
    dialog = _ollama(network)
    network.listing.end(_installed("qwen3:8b"))
    dialog.model.setEditText("llama3")
    assert not _hidden(dialog, dialog.ollama_download_button)
    dialog.model.setEditText("qwen3:8b")
    assert _hidden(dialog, dialog.ollama_download_button)
    dialog.model.setEditText("")
    assert _hidden(dialog, dialog.ollama_download_button)


def test_download_asks_first(network, monkeypatch):
    questions = []
    monkeypatch.setattr(panel_module, "ask_plain", lambda parent, title, text: questions.append(text) or False)
    dialog = _ollama(network)
    network.listing.end(_installed())
    dialog.ollama_download_button.click()
    assert network.posts == [] and "qwen3.5:4b" in questions[0]
    assert dialog.ollama_cancel_button.isHidden() and dialog.preset.isEnabled()


def _downloading(network, monkeypatch, **kwargs):
    monkeypatch.setattr(panel_module, "ask_plain", lambda *args: True)
    dialog = _ollama(network, **kwargs)
    network.listing.end(_installed())
    dialog.ollama_download_button.click()
    return dialog


def test_download_posts_to_the_address_of_the_dialog_only(network, monkeypatch):
    dialog = _downloading(network, monkeypatch, base_url="http://gpu.lan:11434/v1")
    request, body, _reply = network.posts[0]
    assert request.url == "http://gpu.lan:11434/api/pull"
    assert json.loads(body) == {"model": "qwen3.5:4b", "stream": True}
    assert request.attributes["redirect"] == "manual"  # a redirection is not followed
    assert len(network.posts) == 1 and not _hidden(dialog, dialog.ollama_cancel_button)


def test_download_shows_its_progress_and_closes_the_way_for_nothing_else(network, monkeypatch):
    dialog = _downloading(network, monkeypatch)
    bar = dialog.ollama_progress
    assert not _hidden(dialog, bar) and bar.maximum() == 0  # busy: no size yet
    assert not (dialog.preset.isEnabled() or dialog.model.isEnabled() or dialog.provider_test_button.isEnabled())
    assert _hidden(dialog, dialog.ollama_download_button)
    network.download.send(_lines({"status": "pulling manifest"}))
    assert bar.maximum() == 0 and "pulling manifest" in dialog.provider_result.text()
    network.download.send(_lines({"status": "pulling a1b2", "total": 3_400_000_000, "completed": 1_700_000_000}))
    assert (bar.minimum(), bar.maximum(), bar.value()) == (0, 1000, 500)
    assert dialog.provider_result.text() == "Downloading qwen3.5:4b: 1.7 GB of 3.4 GB"
    dialog.provider_test_button.click()  # nothing is tested meanwhile
    assert dialog.provider_result.text().startswith("Downloading")


def test_a_line_cut_between_two_chunks_is_read_whole(network, monkeypatch):
    dialog = _downloading(network, monkeypatch)
    line = json.dumps({"status": "pulling x", "total": 2_000_000, "completed": 1_000_000}).encode()
    network.download.send(line[:20])
    assert dialog.ollama_progress.maximum() == 0
    network.download.send(line[20:] + b"\n")
    assert dialog.ollama_progress.value() == 500 and "1 MB of 2 MB" in dialog.provider_result.text()


def test_download_success_reads_the_list_again_and_selects_the_model(network, monkeypatch):
    dialog = _downloading(network, monkeypatch)
    network.download.send(_lines({"status": "pulling a", "total": 10, "completed": 10}, {"status": "success"}))
    assert network.download.aborted == 1  # nothing more is read
    assert dialog.provider_result.text() == "qwen3.5:4b is downloaded."
    assert dialog.preset.isEnabled() and dialog.model.isEnabled() and dialog.provider_test_button.isEnabled()
    assert _hidden(dialog, dialog.ollama_cancel_button) and _hidden(dialog, dialog.ollama_progress)
    assert len(network.gets) == 2  # the list, again
    network.listing.end(_installed("qwen3.5:4b"))
    assert dialog.model.currentText() == "qwen3.5:4b" and _models(dialog) == ["qwen3.5:4b"]
    assert _hidden(dialog, dialog.ollama_download_button) and _hidden(dialog, dialog.ollama_download_row)


def test_an_error_line_of_the_stream_is_shown(network, monkeypatch):
    dialog = _downloading(network, monkeypatch)
    network.download.send(_lines({"status": "pulling manifest"}, {"error": "pull model manifest: file does not exist"}))
    assert dialog.provider_result.text() == (
        "Ollama could not download qwen3.5:4b: pull model manifest: file does not exist")
    assert dialog.preset.isEnabled() and dialog.model.isEnabled() and len(network.gets) == 1
    assert not _hidden(dialog, dialog.ollama_download_button)  # the model is still missing: try again


def test_an_error_answered_with_a_status_is_shown(network, monkeypatch):
    dialog = _downloading(network, monkeypatch)
    network.download.status, network.download.code = 404, 203
    network.download.end(_lines({"error": "pull model manifest: file does not exist"}))
    assert "file does not exist" in dialog.provider_result.text() and dialog.preset.isEnabled()


def test_cancel_stops_the_download(network, monkeypatch):
    dialog = _downloading(network, monkeypatch)
    network.download.send(_lines({"status": "pulling a", "total": 10, "completed": 3}))
    dialog.ollama_cancel_button.click()
    assert network.download.aborted == 1 and dialog.provider_result.text() == "Download cancelled."
    assert dialog.preset.isEnabled() and dialog.provider_test_button.isEnabled() and len(network.gets) == 1
    assert _hidden(dialog, dialog.ollama_cancel_button) and not _hidden(dialog, dialog.ollama_download_button)
    network.download.send(_lines({"status": "success"}))  # a late chunk is not read
    assert dialog.provider_result.text() == "Download cancelled."


def test_closing_the_dialog_aborts_the_download(network, monkeypatch):
    dialog = _downloading(network, monkeypatch)
    dialog.done(0)
    assert network.download.aborted == 1 and len(network.gets) == 1 and dialog._pull_reply is None
    assert not dialog._pull_idle.isActive()


def test_a_silence_ends_the_download(network, monkeypatch):
    dialog = _downloading(network, monkeypatch)
    assert dialog._pull_idle.isActive() and dialog._pull_idle.interval() == 60_000  # no total timeout, only silence
    dialog._pull_idle.timeout.emit()
    assert network.download.aborted == 1 and "60 seconds" in dialog.provider_result.text()
    assert dialog.preset.isEnabled()


def test_download_that_cannot_reach_ollama_says_so(network, monkeypatch):
    dialog = _downloading(network, monkeypatch, base_url="http://gpu.lan:11434")
    network.download.code = 1
    network.download.end()
    assert dialog.provider_result.text() == "Ollama could not be reached at http://gpu.lan:11434."
    assert dialog.model.isEnabled()


def test_the_download_has_the_silence_limit_as_its_transfer_timeout(network, monkeypatch):
    _downloading(network, monkeypatch)
    # A QGIS default (60 s, for the whole transfer on some builds) must never cut a download of several GB.
    assert network.posts[0][0].timeout == panel_module.OLLAMA_PULL_IDLE_MS


def test_a_stream_cut_with_status_200_says_the_connection_was_lost(network, monkeypatch):
    dialog = _downloading(network, monkeypatch)
    network.download.send(_lines({"status": "pulling a", "total": 10, "completed": 3}))
    network.download.status, network.download.code = 200, 4  # RemoteHostClosedError: the server went away
    network.download.end()
    assert dialog.provider_result.text() == "The connection to Ollama was lost during the download of qwen3.5:4b."


@pytest.mark.parametrize("status", [404, 500])
def test_a_refusal_with_an_http_status_says_ollama_refused(network, monkeypatch, status):
    dialog = _downloading(network, monkeypatch)
    network.download.status, network.download.code = status, 203
    network.download.end()
    assert dialog.provider_result.text() == "Ollama refused the download of qwen3.5:4b."


def test_the_install_note_and_the_errors_show_the_address_typed_without_credentials(network, monkeypatch):
    dialog = _ollama(network, base_url="http://user:secret@gpu.lan:11434/")
    network.listing.end(b"")
    note = dialog.ollama_install_note.text()
    assert "at http://gpu.lan:11434: install" in note and "/api/" not in note and "secret" not in note
    assert "http://gpu.lan:11434" in dialog.model.toolTip() and "/api/" not in dialog.model.toolTip()
    monkeypatch.setattr(panel_module, "ask_plain", lambda *args: True)
    dialog.ollama_refresh_button.click()
    network.listing.end(_installed())
    dialog.model.setEditText("qwen3.5:4b")
    dialog.ollama_download_button.click()
    network.download.code = 1
    network.download.end()
    assert dialog.provider_result.text() == "Ollama could not be reached at http://gpu.lan:11434."


def test_download_is_refused_while_a_test_runs(network, monkeypatch):
    questions = []
    monkeypatch.setattr(panel_module, "ask_plain", lambda parent, title, text: questions.append(text) or True)
    holder = {}

    def tester(preset, model, base_url, key):
        holder["dialog"]._on_download_model()  # a click that the nested event loop let through
        return True, "It answers.", ()

    settings = settings_module.AgentSettings(preset="ollama", model="", base_url="")
    dialog = holder["dialog"] = AgentSettingsDialog(settings, settings_module.target_of, None, provider_tester=tester)
    network.listing.end(_installed())
    dialog.provider_test_button.click()
    assert questions == [] and network.posts == [] and dialog._pull_reply is None
    assert dialog.provider_result.text() == "It answers."


def test_a_stream_that_stops_without_success_is_said(network, monkeypatch):
    dialog = _downloading(network, monkeypatch)
    network.download.send(_lines({"status": "pulling a", "total": 10, "completed": 3}))
    network.download.end()
    assert dialog.provider_result.text() == "The download ended before its end."
    assert dialog.preset.isEnabled()


def test_a_line_that_never_ends_is_not_kept(network, monkeypatch):
    dialog = _downloading(network, monkeypatch)
    network.download.send(b"x" * (panel_module.OLLAMA_PULL_MAX_LINE + 1))
    assert network.download.aborted == 1 and "could not be read" in dialog.provider_result.text()
