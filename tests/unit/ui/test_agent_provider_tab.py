# -*- coding: utf-8 -*-
"""The Provider tab of the agent settings, on real Qt widgets (PyQt5, offscreen): where to get a key, Test, the models.

Loaded under a private package with ``qgis.PyQt`` pointing at PyQt5 for the import only (the root conftest mocks Qt
for the other tests), and ``qgis.core`` mocked: no request leaves, the tester is a fake. Skipped without PyQt5.
"""
import importlib
import os
import pathlib
import sys
import types
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
