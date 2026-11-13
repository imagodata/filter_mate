# -*- coding: utf-8 -*-
"""The families of tools are on by default, under a new settings key: the old key, saved as off by every user who ever
saved their settings without having chosen it, is neither read nor written.

The settings module is loaded for real under a synthetic package (its relative imports reach ``core`` and
``filtermate_api``); QGIS stays mocked by the root conftest.
"""
import importlib
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_PKG = "fm_tool_families_test"


def _load():
    for name, path in (("", _ROOT),):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.adapters.agent.settings")


agent_settings = _load()


@pytest.fixture
def fake_qgs_settings(monkeypatch):
    """QgsSettings of the settings module backed by a dict, which is yielded."""
    store = {}

    class FakeQgsSettings:
        def value(self, key, default=None, type=None):
            return store.get(key, default)

        def setValue(self, key, value):
            store[key] = value

    monkeypatch.setattr(agent_settings, "QgsSettings", FakeQgsSettings)
    return store


def test_families_are_on_by_default_and_the_old_key_is_ignored(fake_qgs_settings):
    fake_qgs_settings["filter_mate/agent/tool_families"] = False  # saved by every user, never chosen
    assert agent_settings.AgentSettings().tool_families is True
    assert agent_settings.load_settings().tool_families is True


def test_families_are_saved_under_the_new_key(fake_qgs_settings):
    agent_settings.save_settings(agent_settings.AgentSettings(tool_families=False))
    assert fake_qgs_settings["filter_mate/agent/offer_tools_by_task"] is False
    assert "filter_mate/agent/tool_families" not in fake_qgs_settings
    assert agent_settings.load_settings().tool_families is False
